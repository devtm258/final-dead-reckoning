"""Causal, prefix-calibrated planar vehicle dead reckoning.

Only phone measurements enter calibration. Regression is a sensor transfer model,
not a claim that legacy yaw/pitch/roll channels form a rigid orthogonal IMU.
No reference positions, future fixes, map snaps, or post-hoc alignment are used.
"""
import numpy as np


def robust_fit(x, y, prior, ridge):
    weights = np.ones(len(y))
    for _ in range(5):
        fit = np.linalg.solve(x.T @ (weights[:, None]*x) + np.diag(ridge),
                              x.T @ (weights*y) + np.asarray(ridge)*prior)
        residual = y-x@fit
        scale = max(float(np.median(abs(residual-np.median(residual)))*1.4826), .02)
        weights = np.minimum(1., 1.5*scale/np.maximum(abs(residual), 1e-8))
    return fit, float(np.sqrt(np.mean(residual**2)))


def fit_transfer(prefix):
    t = prefix.t.to_numpy()
    imu = prefix[['wx','wy','wz','lax','lay','laz']].to_numpy()
    dt = np.r_[0., np.diff(t)]
    fixes = np.flatnonzero(prefix.gps_fresh.to_numpy() & prefix.gps_valid.to_numpy()
        & np.isfinite(prefix.course.to_numpy()) & (prefix.phone_speed.to_numpy()>2))
    result = {'gyro':np.array([0.,0.,-1.,0.]), 'accel':np.zeros(4),
              'gyro_rmse':None, 'accel_rmse':None, 'intervals':0,
              'warnings':[], 'prefix_end_s':float(t[-1])}
    if len(fixes)<6:
        result['gyro']=np.zeros(4)
        result['warnings'].append('Insufficient moving phone fixes for full calibration; provisional heading propagation only.')
        # One scalar turn cannot identify a three-axis mounting transform.
        # Use a bounded single-axis hypothesis if a turn was actually observed;
        # otherwise keep course constant rather than inventing a vertical axis.
        if len(fixes)>=2:
            a,b=fixes[0],fixes[-1]
            integral=np.sum(imu[a+1:b+1,:3]*dt[a+1:b+1,None],axis=0)
            turn=np.deg2rad(prefix.course.iloc[a]-prefix.course.iloc[b])
            turn=(turn+np.pi)%(2*np.pi)-np.pi
            candidates=[]
            if abs(turn)>.05:
                for axis in range(3):
                    if abs(integral[axis])<.02:continue
                    scale=turn/integral[axis]
                    if .5<=abs(scale)<=1.5:candidates.append((abs(np.log(abs(scale))),axis,scale))
            if candidates:
                _,axis,scale=min(candidates);result['gyro'][axis]=scale
        return result
    pairs = [(a,b) for a,b in zip(fixes[:-1], fixes[1:])
             if .5<t[b]-t[a]<=20 and prefix.segment.iloc[a]==prefix.segment.iloc[b]]
    if len(pairs)<5:
        result['warnings'].append('Insufficient continuous phone-fix intervals.')
        return result
    integrals = np.array([np.sum(imu[a+1:b+1]*dt[a+1:b+1,None],axis=0) for a,b in pairs])
    duration = np.array([t[b]-t[a] for a,b in pairs])
    course=np.deg2rad(90-prefix.course.to_numpy());speed=prefix.phone_speed.to_numpy()
    turns=np.array([(course[b]-course[a]+np.pi)%(2*np.pi)-np.pi for a,b in pairs])
    changes=np.array([speed[b]-speed[a] for a,b in pairs])
    gx=np.c_[integrals[:,:3],duration]; ax=np.c_[integrals[:,3:],duration]
    # Choose a regularization prior from phone data, including unknown signs.
    candidates=[]
    for i in range(3):
        for sign in (-1.,1.):
            p=np.zeros(4);p[i]=sign
            residual=(gx@p-turns+np.pi)%(2*np.pi)-np.pi
            candidates.append((np.median(abs(residual)),p))
    prior=min(candidates,key=lambda z:z[0])[1]
    # Course is modulo 2*pi. A full turn between sparse fixes must not
    # be fitted as an opposite-direction turn. Resolve near the sensor prior.
    gf=prior.copy()
    for _ in range(3):
        unwrapped=turns+2*np.pi*np.round((gx@gf-turns)/(2*np.pi))
        gf,ge=robust_fit(gx,unwrapped,prior,[.1,.1,.1,30.])
    if np.linalg.norm(gf[:3])<=3 and abs(gf[3])<.05:
        result['gyro']=gf;result['gyro_rmse']=ge
    else:
        result['gyro']=prior
        result['warnings'].append('Gyro transfer fit outside conservative bounds; axis prior used.')
    af,ae=robust_fit(ax,changes,np.zeros(4),[2.,2.,2.,100.])
    if np.linalg.norm(af[:3])<=2 and abs(af[3])<.5:
        result['accel']=af;result['accel_rmse']=ae
    else: result['warnings'].append('Acceleration transfer not reliable; speed propagation uses zero acceleration.')
    if ge>.25:result['warnings'].append('High phone/gyro calibration residual; heading estimate has low confidence.')
    if ae>2:result['warnings'].append('High phone/acceleration calibration residual; speed changes may be inaccurate.')
    result['intervals']=len(pairs)
    return result


class VehicleDR:
    """Scalar speed and heading enforce the planar no-side-slip model directly."""
    def __init__(self, position, speed, yaw, calibration):
        self.position=np.array(position,dtype=float);self.speed=float(speed);self.yaw=float(yaw)
        self.cal=calibration;self.speed_variance=1.;self.last_ml=-1e9
        self.ml_updates=0;self.ml_rejected=0
    def step(self, dt, accel, gyro, ml=None):
        if not 0<dt<=.5:raise ValueError('Reinitialize vehicle estimator across sensor gaps.')
        omega=float(np.clip(np.r_[gyro,1.]@self.cal['gyro'],-1.5,1.5))
        acceleration=float(np.clip(np.r_[accel,1.]@self.cal['accel'],-6.,4.))
        previous_speed=self.speed
        self.speed=float(np.clip(self.speed+acceleration*dt,0.,60.))
        self.speed_variance+=1.*dt
        if ml is not None and np.isfinite(ml).all():
            value,variance=ml;variance=max(float(variance),1.)
            residual=value-self.speed
            if residual**2 < 9*(self.speed_variance+variance):
                gain=min(.5,self.speed_variance/(self.speed_variance+variance))
                self.speed=max(0.,self.speed+gain*residual)
                self.speed_variance*=1-gain;self.ml_updates+=1
            else:self.ml_rejected+=1
        middle=self.yaw+omega*dt/2
        self.position+=.5*(previous_speed+self.speed)*dt*np.array([np.cos(middle),np.sin(middle)])
        self.yaw=(self.yaw+omega*dt+np.pi)%(2*np.pi)-np.pi
        return np.array([*self.position,self.speed*np.cos(self.yaw),self.speed*np.sin(self.yaw),self.yaw,0,0,0])
