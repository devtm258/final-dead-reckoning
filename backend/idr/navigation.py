"""Causal planar error-state navigation. No reference columns accepted by the filter.
State: east,north,v_e,v_n,yaw,b_a_forward,b_a_left,b_gyro (8 errors).
This road-plane approximation does not estimate parking floor / full 3D attitude.
"""
from collections import deque
import time
import numpy as np
import json
from pathlib import Path
from .data import enu, geographic
from .quality import SensorQuality, adaptation
from .results import comparison_outputs
from .mapmatch import RoadMatcher
from . import storage as st

def wrap(a):return (a+np.pi)%(2*np.pi)-np.pi

def calibrate(prefix):
    """GNSS-available prefix only; estimates vehicle yaw-rate projection and forward acceleration direction.
    Does NOT access VBOX/reference fields. Weak excitation yields explicit low-confidence defaults.
    """
    w=prefix[['wx','wy','wz']].to_numpy();la=prefix[['lax','lay','laz']].to_numpy();t=prefix.t.to_numpy()
    dt=np.r_[0,np.diff(t)];ids=np.flatnonzero(prefix.gps_fresh.to_numpy() & prefix.gps_valid.to_numpy() & (prefix.phone_speed.to_numpy()>2))
    proj=np.array([0.,0.,-1.]);fwd=np.array([1.,0.,0.]);warnings=[]
    if len(ids)>=4:
        courses=np.unwrap(np.deg2rad(90-prefix.course.to_numpy()[ids]));speed=prefix.phone_speed.to_numpy()[ids]
        iw=np.vstack([np.sum(w[a+1:b+1]*dt[a+1:b+1,None],axis=0) for a,b in zip(ids[:-1],ids[1:])]);yaw=np.diff(courses)
        ok=np.isfinite(yaw)&(abs(yaw)<2.)&(np.linalg.norm(iw,axis=1)>1e-4)
        if ok.sum()>=3 and np.std(yaw[ok])>.03:
            # Select physically plausible axis/sign, fit only a small scale correction.
            vals=[]
            for ax in range(3):
                den=iw[ok,ax]@iw[ok,ax]+1e-6;scale=float(iw[ok,ax]@yaw[ok]/den)
                if .5<abs(scale)<1.5:vals.append((np.mean((iw[ok,ax]*scale-yaw[ok])**2),ax,scale))
            if vals:
                _,ax,scale=min(vals);proj=np.zeros(3);proj[ax]=scale
            else:warnings.append('Yaw-axis calibration lacks a physically plausible solution; explicit device calibration recommended.')
        else:warnings.append('Insufficient turn excitation for yaw-axis calibration.')
        ia=np.vstack([np.sum(la[a+1:b+1]*dt[a+1:b+1,None],axis=0) for a,b in zip(ids[:-1],ids[1:])]);dv=np.diff(speed)
        good=np.isfinite(dv)&(np.abs(dv)<12)
        if good.sum()>=3 and np.std(dv[good])>.5:
            f=np.linalg.solve(ia[good].T@ia[good]+np.eye(3)*.1,ia[good].T@dv[good]);f[2]=0
            if np.linalg.norm(f)>.1:fwd=f/np.linalg.norm(f)
            else:warnings.append('Forward-axis calibration inconclusive.')
        else:warnings.append('Insufficient acceleration excitation for forward-axis calibration.')
    else:warnings.append('Too few fresh moving GNSS fixes: default mount axes used. Do not claim mount-independent accuracy.')
    # IO-VNBD's legacy Yaw/Pitch/Roll labels are not a rigid 3D gyro vector:
    # its Y channel often predicts turn rate even while GRAVITY Z is constant.
    # Fit lateral acceleration to v * change_in_course from *phone GNSS only*.
    # This avoids treating a semantic gyro channel as a physical vertical axis.
    forward=fwd/np.linalg.norm(fwd)
    left=np.array([-forward[1],forward[0],0.])
    if np.linalg.norm(left)<.15:left=np.array([0.,1.,0.])
    left/=np.linalg.norm(left)
    if len(ids)>=4:
        turn=np.diff(np.unwrap(np.deg2rad(90-prefix.course.to_numpy()[ids])))
        speed=prefix.phone_speed.to_numpy()[ids]
        ia=np.vstack([np.sum(la[a+1:b+1]*dt[a+1:b+1,None],axis=0) for a,b in zip(ids[:-1],ids[1:])])
        lateral=.5*(speed[1:]+speed[:-1])*turn
        good=np.isfinite(lateral)&(abs(turn)<1.)&(abs(lateral)<15.)
        if good.sum()>=5 and np.std(lateral[good])>.3:
            fit=np.linalg.solve(ia[good].T@ia[good]+np.eye(3)*.5,ia[good].T@lateral[good])
            fit-=forward*(fit@forward)
            predicted=ia[good]@fit
            correlation=np.corrcoef(predicted,lateral[good])[0,1] if np.std(predicted)>1e-5 else 0.
            if np.linalg.norm(fit)>.15 and correlation>.45:
                left=fit/np.linalg.norm(fit)
            else:warnings.append('Lateral axis lacks turn excitation; using planar fallback.')
        else:warnings.append('Too few measured turns for lateral-axis calibration.')
    return {'gyro_projection':proj.tolist(),'forward_projection':forward.tolist(),'left_projection':left.tolist(),
            'warnings':warnings,'prefix_end_s':float(t[-1])}

class PlanarESKF:
    def __init__(self,position,speed,yaw,nhc='adaptive',zupt=True):
        self.x=np.array([*position,speed*np.cos(yaw),speed*np.sin(yaw),yaw,0,0,0.],float)
        # Initial phone course may be stale while stationary. Preserve enough
        # yaw uncertainty for a subsequent moving GNSS course to correct it.
        self.P=np.diag([16,16,4,4,2.25,.1,.1,.005]);self.nhc=nhc;self.zupt=zupt
        self.rejected=0;self.zupt_count=0;self.quiet=0.;self.last_gnss_speed=speed;self.since_gnss=0.;self.history=deque(maxlen=20)
    def update(self,z,h,H,R,gate=16.):
        residual=np.atleast_1d(z)-np.atleast_1d(h);S=H@self.P@H.T+R
        nis=float(residual@np.linalg.solve(S,residual))
        if gate and nis>gate:self.rejected+=1;return False
        K=np.linalg.solve(S,(self.P@H.T).T).T;self.x+=K@residual;self.x[4]=wrap(self.x[4]);A=np.eye(8)-K@H
        self.P=A@self.P@A.T+K@R@K.T;self.P=(self.P+self.P.T)*.5
        return True
    def step(self,dt,accel,yaw_rate,ml=None,gnss=None,quality=None):
        if not 0<dt<=.5:raise ValueError('Sensor gap/reset: reinitialize the navigation state.')
        self.since_gnss+=dt;p=self.x[4];c,s=np.cos(p),np.sin(p);R2=np.array([[c,-s],[s,c]])
        a=np.asarray(accel)-self.x[5:7];an=R2@a
        self.x[:2]+=self.x[2:4]*dt+.5*an*dt*dt;self.x[2:4]+=an*dt;self.x[4]=wrap(p+(yaw_rate-self.x[7])*dt)
        F=np.eye(8);F[:2,2:4]=np.eye(2)*dt;F[2:4,4]=R2@np.array([-a[1],a[0]])*dt;F[2:4,5:7]=-R2*dt;F[4,7]=-dt
        Q=np.diag([.001,.001,.4,.4,.002,.0002,.0002,.00002])*dt
        if quality:
            Q[2:4,2:4] *= quality['accel_process_scale']
            Q[4,4] *= quality['gyro_process_scale']
        # Gyro bias random walk with tighter process noise for observability
        # during continuous motion (NHC + turns provide observability)
        Q[7,7] *= 0.1  # Tighter bias process noise: bias changes slowly
        self.P=F@self.P@F.T+Q
        c,s=np.cos(self.x[4]),np.sin(self.x[4]);forward=np.array([c,s]);left=np.array([-s,c]);v=self.x[2:4]
        if ml is not None and np.isfinite(ml[0]):
            H=np.zeros((1,8));H[0,2:4]=forward;H[0,4]=left@v
            self.update([ml[0]],[forward@v],H,np.array([[max(.25,ml[1])]]),gate=25)

        if self.nhc!='off':
            H=np.zeros((1,8));H[0,2:4]=left;H[0,4]=-forward@self.x[2:4]
            var=.1 if self.nhc=='fixed' else .1+2*abs(yaw_rate)+.1*min(np.linalg.norm(accel),20)**2
            if quality:var *= quality['nhc_scale']
            self.update([0],[left@self.x[2:4]],H,np.array([[var]]),gate=25)
        self.history.append(np.linalg.norm(accel))
        stopped=(ml is not None and ml[0]<.25 and ml[1]<1. and self.last_gnss_speed<.5 and abs(yaw_rate)<.025 and len(self.history)>=10 and np.std(self.history)<.12 and np.mean(self.history)<.25)
        self.quiet=self.quiet+dt if stopped else 0
        if self.zupt and self.quiet>=1.:
            H=np.zeros((2,8));H[:,2:4]=np.eye(2);self.update([0,0],self.x[2:4].copy(),H,np.eye(2)*.02,gate=16)
            H=np.zeros((1,8));H[0,7]=1;self.update([yaw_rate],[self.x[7]],H,np.array([[.0004]]),gate=16);self.zupt_count+=1
        if gnss is not None:
            pos,speed,course,accuracy=gnss
            H=np.zeros((2,8));H[:,:2]=np.eye(2)
            accepted=self.update(pos,self.x[:2].copy(),H,np.eye(2)*max(4,accuracy**2),gate=25)
            if accepted:
                self.since_gnss=0.;self.last_gnss_speed=speed
                if speed>2 and np.isfinite(course):
                    H=np.zeros((1,8));H[0,4]=1;self.update([self.x[4]+wrap(course-self.x[4])],[self.x[4]],H,np.array([[.08]]),gate=25)
                if np.isfinite(speed):
                    f=np.array([np.cos(self.x[4]),np.sin(self.x[4])]);H=np.zeros((1,8));H[0,2:4]=f
                    self.update([speed],[f@self.x[2:4]],H,np.array([[1.]]),gate=25)
        return self.x.copy()


def simulate(ds,predictor,start,end,nhc='adaptive',zupt=True,split='test',ml_enabled=True,quality_mode='observe',smoothing=False,cutoff_hz=2.,estimator="legacy"):
    if estimator not in ("legacy", "vehicle"):raise ValueError("Unknown estimator")
    if quality_mode not in ('off','observe','adaptive'):raise ValueError('Invalid quality mode.')
    if estimator=='vehicle' and (smoothing or quality_mode=='adaptive'):
        raise ValueError('Smoothing and quality adaptation are supported by the planar ESKF comparison. Vehicle mode currently uses raw sensor transfer calibration and observation-only flags.')
    overall_start=time.perf_counter()
    if abs(ds.report['sample_hz']-predictor.meta['sample_hz'])>1:raise ValueError('Recording rate differs from model training rate; use a validated causal resampling adapter.')
    d=ds.frame;t=d.t.to_numpy()
    if not np.isfinite([start,end]).all() or not (t[0]<=start<end<=t[-1]):raise ValueError('Blackout must be a finite interval inside this recording.')
    ids=np.flatnonzero((t>=start)&(t<=end))
    if len(ids)<2:raise ValueError('Blackout needs at least two samples.')
    if d.segment.iloc[ids].nunique()!=1:raise ValueError('Blackout crosses a reset/gap; choose a single acquisition segment.')
    ranges=predictor.meta.get('source_splits',{}).get(ds.report.get('source_id'),predictor.meta['dataset_splits'].get(ds.fingerprint,{}))
    if split=='test' and ranges:
        rg=ranges.get('test')
        if not rg or start<rg[0]+predictor.window*.1 or end>rg[1]:raise ValueError('Benchmark interval must be inside the saved held-out test range, after model warmup. Select exploration mode for other intervals.')
    sg=d.segment.iloc[ids[0]];segids=np.flatnonzero(d.segment.to_numpy()==sg)
    warm=max(int(segids[0]),int(np.searchsorted(t,start-90)))
    a=ids[0]
    if a-warm<100:raise ValueError('At least 10 seconds of pre-blackout calibration data is required in the same segment.')
    # Prefix reference data not passed to calibration. Calibration bounded to pre-blackout history.
    sensorcols=['t','wx','wy','wz','lax','lay','laz','gps_fresh','gps_valid','phone_speed','course']
    cal=calibrate(d.iloc[warm:a][sensorcols]);b=min(int(segids[-1])+1,int(np.searchsorted(t,end+10)))
    origin=(float(d.lat.iloc[warm]),float(d.lon.iloc[warm]));gps=enu(d.lat.to_numpy(),d.lon.to_numpy(),origin)
    course=np.deg2rad(90-d.course.to_numpy())
    initial_fixes=np.flatnonzero(d.gps_fresh.to_numpy()[warm:a] & d.gps_valid.to_numpy()[warm:a] & (d.phone_speed.to_numpy()[warm:a]>2))
    initial_idx=warm+int(initial_fixes[0]) if len(initial_fixes) else warm
    p0=course[initial_idx] if np.isfinite(course[initial_idx]) else 0
    initial_speed=float(d.phone_speed.iloc[warm]);f=PlanarESKF(gps[warm],initial_speed,p0,nhc,zupt);baseline=PlanarESKF(gps[warm],initial_speed,p0,'off',False)
    # At the outage boundary initialize velocity and yaw from the most recent
    # fresh, moving phone GNSS fix. Its course is observed more accurately than
    # the initial course after a 90-second warmup on these recordings. Keep the
    # filter's position and calibrated biases; no VBOX value enters this step.
    recent=np.flatnonzero(d.gps_fresh.to_numpy()[warm:a] & d.gps_valid.to_numpy()[warm:a]
                          & (d.phone_speed.to_numpy()[warm:a]>2) & np.isfinite(course[warm:a]))
    boundary_idx=warm+int(recent[-1]) if len(recent) else None
    cal['initial_course_deg']=float(d.course.iloc[initial_idx]) if np.isfinite(d.course.iloc[initial_idx]) else None
    cal['initial_speed_mps']=initial_speed
    cal['heading_convention']='GNSS clockwise from North; filter yaw counterclockwise from East, radians.'
    cal['boundary_gnss_course_s']=float(t[boundary_idx]) if boundary_idx is not None and start-t[boundary_idx]<=2.5 else None
    if not np.isfinite(course[warm]) or initial_speed<=2:
        cal['warnings'].append('Initial course is missing or at low speed; heading may be unreliable until moving GNSS updates are accepted.')
    vehicle=None; transfer=None
    if estimator == 'vehicle':
        from .vehicle import fit_transfer, VehicleDR
        history_start=max(int(segids[0]),int(np.searchsorted(t,start-600)))
        transfer=fit_transfer(d.iloc[history_start:a][sensorcols+['segment']])
        cal['vehicle_transfer']={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in transfer.items()}
        cal['warnings'].extend(transfer['warnings'])
        # A last fix may be older than the displayed blackout. Propagate through
        # its entire age instead of resetting to a stale position at the boundary.
        usable=np.flatnonzero(d.gps_fresh.to_numpy()[history_start:a] & d.gps_valid.to_numpy()[history_start:a]
                              & np.isfinite(course[history_start:a]))
        vehicle_fix=history_start+int(usable[-1]) if len(usable) else warm
        vehicle=VehicleDR(gps[vehicle_fix],float(d.phone_speed.iloc[vehicle_fix]),
                          float(course[vehicle_fix]) if np.isfinite(course[vehicle_fix]) else p0,transfer)
        cal['vehicle_fix_age_s']=float(start-t[vehicle_fix])
        if start-t[vehicle_fix]>15:cal['warnings'].append('Last operational fix is over 15 seconds old; outage includes pre-existing GNSS loss.')
    # Only local interval inference; no O(n) prediction of a multi-hour drive per simulation.
    local=d.iloc[max(int(segids[0]),warm-predictor.window):b].reset_index(drop=True)
    lp,lv=predictor.sequence(local);offset=max(int(segids[0]),warm-predictor.window)
    gnss_updates=[];states=[];base=[];speeds=[];preds=[];flags=[];times=[];latencies=[];last_ml=-1e9
    speed_residuals=deque(maxlen=30);speed_bias_at_outage=None
    detector=SensorQuality(cutoff_hz);quality_rows=[];processing_latencies=[]
    # Materialize numeric arrays once, outside the real-time loop.
    linear_acc=d[['lax','lay','laz']].to_numpy()
    angular_rate=d[['wx','wy','wz']].to_numpy()
    fresh=d.gps_fresh.to_numpy();valid_gps=d.gps_valid.to_numpy()
    phone_speed=d.phone_speed.to_numpy();accuracy=d.accuracy.to_numpy()
    for i in range(warm,b):
        tick=time.perf_counter()
        dt=.1 if i==warm else t[i]-t[i-1];blk=start<=t[i]<=end
        la=linear_acc[i];gyro=angular_rate[i]
        acc=np.array([la@cal['forward_projection'],la@cal['left_projection']]);rate=float(gyro@cal['gyro_projection'])
        raw_acc,raw_rate=acc.copy(),rate
        qflags={'accel_flag':False,'gyro_flag':False,'timing_flag':False}
        scales={'accel_process_scale':1.,'gyro_process_scale':1.,'nhc_scale':1.,'speed_scale':1.}
        if quality_mode!='off' or smoothing:
            filtered,qflags=detector.step(la,gyro,dt)
            if smoothing:
                acc=np.array([filtered[:3]@cal['forward_projection'],filtered[:3]@cal['left_projection']])
                rate=float(filtered[3:]@cal['gyro_projection'])
            if quality_mode=='adaptive':scales=adaptation(qflags,raw_rate,raw_acc)
        quality_rows.append({'t':float(t[i]),**qflags,**scales})
        gnss=None
        if not blk and fresh[i] and valid_gps[i]:gnss=(gps[i],float(phone_speed[i]),float(course[i]),float(accuracy[i]))
        if gnss is not None and np.isfinite(lp[i-offset]) and np.isfinite(phone_speed[i]):
            speed_residuals.append(float(phone_speed[i]-lp[i-offset]))
        if i==a:
            speed_bias_at_outage=float(np.median(speed_residuals)) if len(speed_residuals)>=3 else None
        if i==a and boundary_idx is not None and start-t[boundary_idx]<=2.5:
            for filter_state in (f,baseline):
                yaw=float(course[boundary_idx]);speed=float(phone_speed[boundary_idx])
                age=max(0.,float(t[i]-t[boundary_idx]))
                # Re-anchor a rejected or drifting warmup state to the last
                # operational phone fix at the outage boundary. This is a
                # causal GNSS initialization, never reference alignment.
                filter_state.x[:2]=gps[boundary_idx]+age*speed*np.array([np.cos(yaw),np.sin(yaw)])
                filter_state.x[4]=yaw
                filter_state.x[2:4]=speed*np.array([np.cos(yaw),np.sin(yaw)])
                filter_state.P[:2,:2]=np.eye(2)*max(4.,float(accuracy[boundary_idx])**2+age**2)
                filter_state.P[:2,2:]=0.;filter_state.P[2:,:2]=0.
                filter_state.P[4,4]=.08
                filter_state.P[2:4,2:4]=np.eye(2)*1.
        ml=None
        if ml_enabled and t[i]-last_ml>=.49 and np.isfinite(lp[i-offset]):
            bias=float(np.median(speed_residuals)) if len(speed_residuals)>=3 else 0.
            spread=float(np.median(abs(np.array(speed_residuals)-bias))) if len(speed_residuals)>=3 else 3.
            ml=(float(np.clip(lp[i-offset]+np.clip(bias,-20,20),0,60)),
                float(max(lv[i-offset]*2,4.+spread**2)))
            last_ml=t[i]
        ts=time.perf_counter();x=f.step(dt,acc,rate,ml,gnss,scales if quality_mode=='adaptive' else None)

        if vehicle is not None and i>=a:
            bias=float(np.median(speed_residuals)) if len(speed_residuals)>=3 else 0.
            residuals=np.array(speed_residuals)
            spread=float(1.4826*np.median(abs(residuals-bias))) if len(residuals)>=5 else 8.
            # Trust comes from actual errors at earlier phone fixes. Calibrated
            # residual variance prevents an over-conservative global variance
            # from ignoring correct stop/acceleration predictions on this drive.
            variance=max(1.,spread**2)
            if i==a:
                last_prefix_ml=-1e9
                for j in range(vehicle_fix+1,a):
                    pm=None
                    if ml_enabled and j>=offset and np.isfinite(lp[j-offset]) and t[j]-last_prefix_ml>=.49:
                        pm=(float(np.clip(lp[j-offset]+np.clip(bias,-20,20),0,60)),variance)
                        last_prefix_ml=t[j]
                    vehicle.step(float(t[j]-t[j-1]),linear_acc[j],angular_rate[j],pm)
            vehicle_ml=(ml[0],variance) if ml is not None else None
            x=vehicle.step(dt,la,gyro,vehicle_ml)
            if gnss is not None:
                vehicle.position=np.array(gnss[0]);vehicle.speed=gnss[1]
                if gnss[1]>2:vehicle.yaw=gnss[2]
                x=np.array([*vehicle.position,vehicle.speed*np.cos(vehicle.yaw),vehicle.speed*np.sin(vehicle.yaw),vehicle.yaw,0,0,0])
        latencies.append((time.perf_counter()-ts)*1000)
        y=baseline.step(dt,raw_acc,raw_rate,None,gnss)
        processing_latencies.append((time.perf_counter()-tick)*1000)
        gnss_updates.append(gnss is not None)
        states.append(x);base.append(y);speeds.append(float(np.linalg.norm(x[2:4])));preds.append(float(lp[i-offset]) if np.isfinite(lp[i-offset]) else None);flags.append(blk);times.append(float(t[i]))
    states=np.array(states);base=np.array(base);flags=np.array(flags);ix=np.arange(warm,b);evalmask=flags & d.ref_valid.to_numpy()[ix]
    if evalmask.sum()<2:raise ValueError('No independent valid position reference in blackout; upload paired VBOX for scored simulation.')
    reference=enu(d.ref_lat.to_numpy()[ix],d.ref_lon.to_numpy()[ix],origin);ref=reference[evalmask]
    length=float(np.sum(np.linalg.norm(np.diff(ref,axis=0),axis=1)));e=states[evalmask,:2]-ref;eb=base[evalmask,:2]-ref
    err=np.linalg.norm(e,axis=1);errb=np.linalg.norm(eb,axis=1);valid_ratio=float(evalmask.sum()/flags.sum());pct=float(100*err[-1]/length) if length>=5 else None
    psi=np.deg2rad(90-d.ref_heading.to_numpy()[ix][evalmask]);along=e[:,0]*np.cos(psi)+e[:,1]*np.sin(psi);cross=-e[:,0]*np.sin(psi)+e[:,1]*np.cos(psi)
    heading_ok=np.isfinite(psi)&(d.ref_speed.to_numpy()[ix][evalmask]>2)
    heading_error=np.degrees(wrap(states[evalmask,4]-psi))
    eligible=split=='test' and valid_ratio>=.95 and length>=5
    metrics={'blackout_start_s':start,'blackout_end_s':end,'blackout_duration_s':end-start,'blackout_distance_m':length,'fused_final_drift_m':float(err[-1]),'fused_drift_pct':pct,'fused_rmse_m':float(np.sqrt(np.mean(err**2))),'fused_max_err_m':float(err.max()),'start_position_error_m':float(err[0]),'start_heading_error_deg':float(heading_error[0]) if heading_ok[0] else None,'online_speed_bias_mps':speed_bias_at_outage,'preblackout_fix_age_s':float(start-t[boundary_idx]) if boundary_idx is not None else None,'ins_final_drift_m':float(errb[-1]),'ins_drift_pct':float(100*errb[-1]/length) if length>=5 else None,'ins_rmse_m':float(np.sqrt(np.mean(errb**2))),'ins_max_err_m':float(errb.max()),'target_drift_pct':10.,'meets_isro_target':bool(eligible and pct<10),'benchmark_eligible':eligible,'reference_coverage':valid_ratio,'evaluation_mode':split,'along_track_rmse_m':float(np.sqrt(np.mean(along**2))),'cross_track_rmse_m':float(np.sqrt(np.mean(cross**2))),'filter_latency_p95_ms':float(np.quantile(latencies,.95)),'zupt_updates':f.zupt_count,'rejected_updates':f.rejected,'heading_calibration':cal,'full_sih_compliance':False}
    metrics.update(vehicle_ml_updates=vehicle.ml_updates if vehicle is not None else None, vehicle_ml_rejected=vehicle.ml_rejected if vehicle is not None else None, estimator=estimator, meets_requested_50pct=bool(eligible and pct<50), quality_mode=quality_mode,smoothing=smoothing,cutoff_hz=cutoff_hz,
                   heading_rmse_deg=float(np.sqrt(np.mean(heading_error[heading_ok]**2))) if heading_ok.any() else None,
                   heading_reference_samples=int(heading_ok.sum()),
                   quality_flagged_samples=sum(int(q['accel_flag'] or q['gyro_flag'] or q['timing_flag']) for q in quality_rows),
                   adapted_samples=sum(int(max(q['accel_process_scale'],q['gyro_process_scale'],q['nhc_scale'])>1) for q in quality_rows),
                   replay_step_p95_ms=float(np.quantile(processing_latencies,.95)),
                   replay_total_ms=(time.perf_counter()-overall_start)*1000)
    outputs=comparison_outputs(times,states,base,reference,d.ref_valid.to_numpy()[ix],flags,
        np.deg2rad(90-d.ref_heading.to_numpy()[ix]),d.ref_speed.to_numpy()[ix],gnss_updates,
        processing_latencies,metrics['replay_total_ms'],ds.report['sample_hz'],split)
    summary=outputs['summary']
    # Keep the legacy API fields consistent with native-rate output metrics.
    metrics.update(blackout_distance_m=summary['reference_distance_m'],benchmark_eligible=summary['eligible'],
        meets_isro_target=summary['under_10_endpoint'],unscorable_reasons=summary['reasons'])
    for prefix,key in [('fused','aided'),('ins','baseline')]:
        v=summary[key]
        metrics.update({prefix+'_final_drift_m':v['endpoint_error_m'],prefix+'_drift_pct':v['endpoint_drift_pct'],
            prefix+'_mean_err_m':v['mean_error_m'],prefix+'_max_error_pct':v['max_error_pct'],
            prefix+'_distance_m':v['distance_m'],prefix+'_distance_error_m':v['distance_error_m'],
            prefix+'_distance_error_pct':v['distance_error_pct']})
    metrics['meets_requested_50pct']=bool(summary['eligible'] and summary['aided']['endpoint_drift_pct']<50)
    select=np.unique(np.r_[np.linspace(0,len(ix)-1,min(800,len(ix))).astype(int),np.flatnonzero(flags)[[0,-1]]]);bi=np.flatnonzero(flags[select])
    def pts(x):return geographic(x,origin).tolist()
    return {'outputs':outputs,'dataset_report':ds.report,'trajectory_times':np.array(times)[select].tolist(),'reference_valid':d.ref_valid.to_numpy()[ix][select].tolist(),'metrics':metrics,'model_id':predictor.meta['model_id'],'trajectories':{'ground_truth':pts(reference[select]),'ins_raw':pts(base[select,:2]),'fused':pts(states[select,:2])},'blackout_indices':[int(bi[0]),int(bi[-1])],'velocity_series':{'t':np.array(times)[select].tolist(),'gps':d.ref_speed.to_numpy()[ix][select].tolist(),'ml':[preds[j] for j in select],'fused':np.array(speeds)[select].tolist(),'baseline':np.linalg.norm(base[select,2:4],axis=1).tolist(),'blackout_flag':flags[select].astype(int).tolist()},'error_series':{'t':np.array(times)[evalmask].tolist(),'position_m':err.tolist(),'baseline_m':errb.tolist(),'heading_error_deg':[float(v) if ok else None for v,ok in zip(heading_error,heading_ok)],'along_m':along.tolist(),'cross_m':cross.tolist()},'quality_series':quality_rows,'notes':['No post-blackout reference alignment. Smartphone GNSS only supplies operational fixes.','Planar road model; 3D/parking-floor accuracy is not established.','Import synchronization uses reference telemetry only to construct aligned labels; engine calibration uses phone GNSS only.','Quality flags are heuristic suspicions, not verified sensor faults. ML inputs are unchanged.','Replay-step latency includes both estimators and quality processing, but excludes batched ML inference. Total replay time includes inference; neither measures phone latency.']}


def compare_variants(ds,predictor,start,end,split='test'):
    variants=[('Planar ESKF reference','off',False),('Smoothing only','off',True),
              ('Quality adaptation','adaptive',False),('Smoothing + adaptation','adaptive',True)]
    results=[]
    for name,mode,smooth in variants:
        result=simulate(ds,predictor,start,end,split=split,quality_mode=mode,smoothing=smooth)
        results.append({'name':name,**result['metrics']})
    vehicle_result=simulate(ds,predictor,start,end,split=split,estimator='vehicle')
    results.append({'name':'Calibrated vehicle + local speed trust',**vehicle_result['metrics']})
    return {'runs':results,'model_id':predictor.meta['model_id'],'note':'Same recording, model and blackout. First four variants use the planar ESKF; the fifth uses a rigid no-side-slip vehicle model with local speed trust. Exploratory comparison, not a new benchmark certification.'}


def benchmark(ds,predictor,durations=(10,30,60),starts_per_duration=3,estimator="vehicle"):
    rg=predictor.meta.get('source_splits',{}).get(ds.report.get('source_id'),predictor.meta['dataset_splits'].get(ds.fingerprint,{})).get('test',[float(ds.frame.t.iloc[0]),float(ds.frame.t.iloc[-1])])
    rows=[];skipped=[]
    for duration in durations:
        lo=rg[0]+max(15,predictor.window*.1);hi=rg[1]-duration-1
        if hi<=lo:
            skipped.append({'start':None,'duration':duration,'reason':'Recording/test range too short for this duration and calibration warmup.'});continue
        for start in np.linspace(lo,hi,starts_per_duration):
            try:r=simulate(ds,predictor,float(start),float(start+duration),estimator=estimator);rows.append(r['metrics'])
            except ValueError as exc:skipped.append({'start':float(start),'duration':duration,'reason':str(exc)})
    pct=[r['fused_drift_pct'] for r in rows if r['benchmark_eligible']]
    return {'model_id':predictor.meta['model_id'],'runs':rows,'skipped':skipped,'estimator':estimator,'attempted_runs':len(rows)+len(skipped),'under_10_count':sum(v<10 for v in pct),'failed_count':sum(v>=10 for v in pct),'unscorable_count':sum(not r['benchmark_eligible'] for r in rows)+len(skipped),'under_50_count':sum(v<50 for v in pct),'all_under_50':bool(pct) and all(v<50 for v in pct),'worst_drift_pct':max(pct) if pct else None,'eligible_runs':len(pct),'pass_rate':float(np.mean(np.array(pct)<10)) if pct else None,'median_drift_pct':float(np.median(pct)) if pct else None,'p95_drift_pct':float(np.quantile(pct,.95)) if pct else None,'claim':'Exploratory recorded-data evaluation; not official SIH certification.'}
