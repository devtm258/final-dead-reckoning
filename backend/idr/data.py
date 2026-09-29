"""Explicit IO-VNBD adapters. Reference telemetry is never a model feature."""
from __future__ import annotations
import hashlib, io, re
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter1d

CHANNELS = ['lax','lay','laz','wx','wy','wz']
EARTH = 6378137.0
ADAPTER_VERSION = 'raw-device-causal-v3'


def _nearest_reference(times, query):
    """Nearest timestamp, without extending reference coverage past its endpoints."""
    right = np.searchsorted(times, query).clip(1, len(times) - 1)
    left = right - 1
    index = np.where(abs(times[left] - query) <= abs(times[right] - query), left, right)
    valid = ((query >= times[0]) & (query <= times[-1]) &
             (abs(times[index] - query) <= .15))
    return index, valid


def _pair_by_time(d, reference_time, yaw_rate, phone_time, alignment, report,
                  clock_offset_s=None):
    """Synchronize labels by clocks; recording pauses never become row offsets.

    Optional motion calibration only uses the leading part of each sensor segment.
    Reference telemetry remains label preparation, never a navigation input.
    """
    vt = np.asarray(reference_time, dtype=float).copy()
    if len(vt) < 2 or not np.isfinite(vt).all():
        raise ValueError('VBOX timestamps must contain finite seconds of day.')
    # A genuine midnight rollover is different from a recording-clock reset.
    rollover = np.r_[0, np.cumsum(np.diff(vt) < -43200)]
    vt += rollover * 86400
    if np.any(np.diff(vt) <= 0):
        raise ValueError('VBOX timestamps repeat or run backwards. Split the reference into chronological recordings.')
    if clock_offset_s is None:
        # Local phone date versus reference time may differ by a timezone.
        # Refuse to guess when file starts cannot support a near-timezone offset.
        start_difference = float(phone_time[0] - vt[0])
        offset = round(start_difference / 900) * 900.
        if abs(start_difference - offset) > 120:
            raise ValueError('Recording start times are ambiguous. Supply clock_offset_s (phone minus VBOX seconds) or correctly trimmed timestamped files.')
    else:
        offset = float(clock_offset_s)
        if not np.isfinite(offset):
            raise ValueError('clock_offset_s must be finite.')
    report['clock_offset_s'] = offset
    report['adapter_version'] = ADAPTER_VERSION
    report['pairing'] = 'timestamp nearest neighbour; 150 ms tolerance'
    warnings = report['warnings']
    index = np.zeros(len(d), dtype=int)
    valid = np.zeros(len(d), dtype=bool)
    gyro = d[['wx', 'wy', 'wz']].to_numpy()
    for segment in np.unique(d.segment):
        ids = np.flatnonzero(d.segment.to_numpy() == segment)
        a, b = int(ids[0]), int(ids[-1]) + 1
        stop = min(b, a + max(200, min(3000, (b - a) // 5)))
        best_corr, best_lag, best_axis = 0., 0., 'unknown'
        accepted = False
        if alignment == 'motion' and stop - a >= 200 and np.isfinite(yaw_rate).all():
            sample = np.arange(a + 50, stop - 50)
            smooth = uniform_filter1d(gyro[a:stop], 5, axis=0)[50:-50]
            # Interpolation is for lag diagnosis only. Final labels use actual
            # timestamp matches and the strict coverage mask below.
            for lag in np.arange(-4., 4.001, .1):
                q = phone_time[sample] - offset + lag
                nearest, covered = _nearest_reference(vt, q)
                if covered.sum() < max(100, .9 * len(sample)):
                    continue
                y = np.interp(q[covered], vt, yaw_rate)
                if np.std(y) < .003:
                    continue
                for axis in range(3):
                    x = smooth[covered, axis]
                    if np.std(x) < .003:
                        continue
                    corr = float(abs(np.corrcoef(x, y)[0, 1]))
                    if corr > best_corr:
                        best_corr, best_lag, best_axis = corr, float(lag), 'xyz'[axis]
            # A peak at the search edge does not establish the actual lag.
            accepted = best_corr >= .65 and abs(best_lag) < 3.95
        lag = best_lag if accepted else 0.
        q = phone_time[ids] - offset + lag
        ii, good = _nearest_reference(vt, q)
        index[ids], valid[ids] = ii, good
        report['alignment'].append({
            'segment': int(segment), 'lag_seconds': round(lag, 4),
            'lag_samples': int(round(lag / report['median_dt'])),
            'abs_correlation': round(best_corr, 4), 'axis': best_axis,
            'accepted': accepted, 'calibration_rows': [a, stop],
            'matched_rows': int(good.sum()), 'unmatched_rows': int((~good).sum()),
            'clock_residual_p95_s': float(np.quantile(abs(vt[ii[good]] - q[good]), .95)) if good.any() else None,
        })
        if alignment == 'motion' and not accepted:
            warnings.append(f'Segment {segment}: motion lag inconclusive; timestamp pairing retained, not row pairing.')
    report['reference_matched_rows'] = int(valid.sum())
    report['reference_unmatched_rows'] = int((~valid).sum())
    if not valid.any():
        raise ValueError('No reference timestamps overlap the phone recording. Check clocks and file pairing.')
    if not valid.all():
        warnings.append(f'{int((~valid).sum())} samples have no timestamp-matched VBOX reference; excluded from supervised training and scoring.')
    return index, valid

def norm(s):
    return re.sub('[^a-z0-9]', '', str(s).lower().replace('²','2').split('(')[0])

def read(raw):
    if not isinstance(raw, bytes): raw = open(raw, 'rb').read()
    if raw[:2]==b'\x1f\x8b':
        import gzip
        raw=gzip.decompress(raw)
    try: text=raw.decode('utf-8-sig')
    except UnicodeDecodeError: text=raw.decode('cp1252')
    d=pd.read_csv(io.StringIO(text)); d.columns=[str(c).strip() for c in d.columns]
    if len(d)<200: raise ValueError('At least 200 sensor samples are required.')
    return d, hashlib.sha256(raw).hexdigest()

def column(d, names, required=True, default=np.nan):
    matches=[c for c in d.columns if norm(c) in {norm(n) for n in names}]
    if len(matches)>1: raise ValueError(f'Ambiguous columns for {names}: {matches}')
    if not matches:
        if required: raise ValueError(f'Missing column: {names[0]}')
        return np.full(len(d),default)
    return pd.to_numeric(d[matches[0]], errors='coerce').to_numpy(float)

def enu(lat,lon,origin):
    return np.column_stack((np.radians(np.asarray(lon)-origin[1])*EARTH*np.cos(np.radians(origin[0])),np.radians(np.asarray(lat)-origin[0])*EARTH))

def geographic(xy,origin):
    a=np.asarray(xy)
    return np.column_stack((origin[0]+np.degrees(a[:,1]/EARTH),origin[1]+np.degrees(a[:,0]/(EARTH*np.cos(np.radians(origin[0]))))))

@dataclass
class Dataset:
    frame: pd.DataFrame
    report: dict
    fingerprint: str


def load_pair(sraw, vraw=None, speed_unit='auto', alignment='motion', clock_offset_s=None):
    s,sh=read(sraw); n=len(s); out={}; warnings=[]
    for key,name in [('lat','GPS LATITUDE'),('lon','GPS LONGITUDE'),('phone_speed','GPS SPEED'),('elapsed','TIME SINCE START')]:
        out[key]=column(s,[name])
    for axis in 'xyz':
        out['a'+axis]=column(s,['ACCELEROMETER '+axis])
        out['g'+axis]=column(s,['GRAVITY '+axis],False, 9.80665 if axis=='z' else 0)
    # Legacy files name channels by yaw/pitch/roll. Preserve their documented yaw channel as z.
    for axis,legacy in [('x','Roll'),('y','Pitch'),('z','Yaw')]:
        out['w'+axis]=column(s,['GYROSCOPE '+axis,'GYROSCOPE '+legacy])
    out['course']=column(s,['GPS ORIENTATION'],False)
    out['accuracy']=column(s,['GPS ACCURACY'],False,10)
    datecols=[c for c in s if norm(c)=='date']
    if datecols:
        dt=pd.to_datetime(s[datecols[0]],format='%Y-%m-%d %H:%M:%S:%f',errors='coerce')
        if dt.isna().any(): raise ValueError('Invalid wall-clock date; repair dates before importing.')
        wall=(dt-dt.iloc[0]).dt.total_seconds().to_numpy()
        sod=(dt-dt.iloc[0].normalize()).dt.total_seconds().to_numpy()
    else:
        wall=(out['elapsed']-out['elapsed'][0])/1000; sod=None
    if np.any(np.diff(wall)<=0):
        if sod is None:
            raise ValueError('Phone elapsed time is not strictly increasing; DATE timestamps are required when the recording clock resets.')
        raise ValueError('Wall-clock timestamps must be strictly increasing; split or repair the recording.')
    elapsed_delta=np.diff(out['elapsed'])/1000
    dt=np.r_[.1,np.diff(wall)]
    breaks=np.r_[False,(elapsed_delta<=0)|(np.diff(wall)>.5)]
    segment=np.cumsum(breaks)
    finite=np.ones(n,bool)
    for key,val in out.items():
        if key not in ('course','accuracy'): finite &= np.isfinite(val)
    # Bad samples create boundaries. Keep time coordinates, never bridge missing runs with windows.
    segment += np.cumsum(np.r_[False,~finite[:-1]])
    out.update(t=wall,dt=dt,segment=segment)
    d=pd.DataFrame(out)
    # Preserve the raw device-frame channels used by saved model weights.
    # Legacy Yaw/Pitch/Roll exports are not guaranteed physical XYZ vectors;
    # rotating them by a gravity-derived matrix silently changes their meaning.
    for axis in 'xyz':
        d['la'+axis] = out['a'+axis] - out['g'+axis]
    gps_changed=np.r_[True,np.any(np.diff(d[['lat','lon']].to_numpy(),axis=0)!=0,axis=1)]
    d['gps_fresh']=gps_changed
    d['gps_age']=wall-np.maximum.accumulate(np.where(gps_changed,wall,0))
    d['gps_valid']=finite & (np.abs(d.lat)<=90)&(np.abs(d.lon)<=180)&(d.accuracy>0)&(d.accuracy<=30)
    report={'rows_original':n,'segments':int(segment.max()+1),'reset_count':int((elapsed_delta<=0).sum()),'median_dt':float(np.median(dt[1:])), 'gps_changed_fraction':float(gps_changed.mean()),'alignment':[], 'warnings':warnings}
    if report['reset_count']: warnings.append('Elapsed clock reset detected; sequence windows are split at resets.')
    if gps_changed.mean()<.1: warnings.append('Repeated GPS fixes: updates are applied only when the fix changes. Fix timestamps are unavailable; stale-fix latency remains a limitation.')
    vh='none'
    d['ref_speed']=np.nan;d['ref_lat']=np.nan;d['ref_lon']=np.nan;d['ref_heading']=np.nan
    d['ref_valid']=False
    if vraw is not None:
        v,vh=read(vraw)
        # Some VBOX exports repeat a timestamp once while advancing the vehicle
        # less than the instrument resolution. Retain the last observation only
        # when the duplicate is locally consistent; never reorder a clock reset.
        times=column(v,['Time Since Start of Day'])
        duplicate=np.flatnonzero(np.diff(times)==0)
        if len(duplicate):
            latv=column(v,['Latitude']);lonv=column(v,['Longitude'])
            xy=enu(latv,lonv,(latv[0],lonv[0]))
            speedv=column(v,['Velocity'])/3.6
            if np.any(np.linalg.norm(xy[duplicate+1]-xy[duplicate],axis=1)>3) or np.any(abs(speedv[duplicate+1]-speedv[duplicate])>1):
                raise ValueError('Conflicting VBOX fixes share a timestamp; split or repair the reference.')
            v=v.loc[~v.index.isin(duplicate)].reset_index(drop=True)
            warnings.append(f'Removed {len(duplicate)} locally consistent duplicate VBOX timestamps.')
        vt=column(v,['Time Since Start of Day']); rv=column(v,['Velocity'])/3.6
        rlat=column(v,['Latitude']);rlon=column(v,['Longitude']);rh=column(v,['Heading'])
        yr=np.deg2rad(column(v,['Yaw Rate'],False))
        if sod is not None:
            ii, good = _pair_by_time(d, vt, yr, sod, alignment, report, clock_offset_s)
        else:
            # Without wall-clock dates, only verify a continuous supplied pair.
            # Never infer row pairing from equal length alone.
            if len(v) != n or np.any(breaks) or np.any(np.diff(vt) <= 0):
                raise ValueError('Phone DATE timestamps are required to align files with gaps, clock resets or unequal lengths.')
            mismatch = (vt - vt[0]) - wall
            if not np.isfinite(mismatch).all() or np.max(abs(mismatch)) > .15:
                raise ValueError('Supplied rows are not synchronized. Include phone DATE timestamps for time matching.')
            ii = np.arange(n)
            good = np.ones(n, bool)
            report['pairing'] = 'supplied rows verified against continuous relative timestamps'
            report['adapter_version'] = ADAPTER_VERSION
            warnings.append('No phone DATE timestamps: relative timing verified, absolute clock alignment is not established.')
        d['ref_speed']=rv[ii];d['ref_lat']=rlat[ii];d['ref_lon']=rlon[ii];d['ref_heading']=rh[ii]
        d['ref_valid']=good & np.isfinite(rv[ii]) & np.isfinite(rlat[ii]) & np.isfinite(rlon[ii]) & (np.abs(rlat[ii])<=90) & (np.abs(rlon[ii])<=180) & (rv[ii]>=0)&(rv[ii]<60)
        d.loc[~d.ref_valid, ['ref_speed', 'ref_lat', 'ref_lon', 'ref_heading']] = np.nan
        # Unit diagnosis is import metadata, never an inference feature or navigation calibration.
        moving=d.ref_valid & (d.ref_speed>3)
        errors={u:float(np.median(abs(d.phone_speed[moving]*scale-d.ref_speed[moving]))) if moving.any() else 1e9 for u,scale in [('m/s',1),('km/h',1/3.6)]}
        if speed_unit=='auto':
            speed_unit=min(errors,key=errors.get)
            warnings.append(f'Phone speed interpreted as {speed_unit} from paired-reference unit diagnostic; verify source metadata.')
        report['speed_unit_diagnostic_median_error']=errors
    if speed_unit=='auto':
        speed_unit='km/h';warnings.append('No paired reference: assumed header unit km/h. Select explicit unit if incorrect; benchmark unavailable.')
    d['phone_speed']=d.phone_speed*(1 if speed_unit=='m/s' else 1/3.6)
    report['phone_speed_unit']=speed_unit
    # Strictly no target-dependent values in CHANNELS. Missing samples excluded and segment boundaries retained.
    d=d.loc[finite].reset_index(drop=True)
    if len(d)<200:raise ValueError('Too few finite IMU samples after validation.')
    report['rows_valid']=len(d);report['reference']='vbox' if vraw is not None else 'none'
    report['source_id']=sh
    report['sample_hz']=round(1/report['median_dt'],3)
    return Dataset(d,report,hashlib.sha256((sh+vh+speed_unit+alignment+ADAPTER_VERSION+str(clock_offset_s)).encode()).hexdigest())


def sequence_indices(d, window):
    seg=d.segment.to_numpy();t=d.t.to_numpy()
    ids=np.arange(window-1,len(d))
    return ids[(seg[ids]==seg[ids-window+1]) & ((t[ids]-t[ids-window+1])<window*.16)]


def windows(d,ids,window):
    x=d[CHANNELS].to_numpy(np.float32)
    return x[ids[:,None]-np.arange(window-1,-1,-1)].transpose(0,2,1).copy()


def tree_features(w):
    # w: N,C,T. All features causal and only IMU-derived.
    mag=np.sqrt(np.sum(w[:,:3]**2,axis=1,keepdims=True))
    rot=np.sqrt(np.sum(w[:,3:]**2,axis=1,keepdims=True));x=np.concatenate([w,mag,rot],axis=1)
    return np.concatenate([x.mean(2),x.std(2),x.min(2),x.max(2),np.sqrt((x*x).mean(2)),x[:,:,-1]-x[:,:,0]],axis=1)

FEATURE_NAMES=[f'{c}_{s}' for s in ['mean','std','min','max','rms','change'] for c in CHANNELS+['acc_norm','gyro_norm']]
