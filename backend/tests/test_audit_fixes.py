from copy import deepcopy
import io
import numpy as np
import pandas as pd
import pytest
from idr.data import load_pair, CHANNELS
from idr.vehicle import VehicleDR,fit_transfer
from idr.navigation import simulate
from test_engine import synthetic_csv,replay_dataset,FixedPredictor


def test_reference_never_rotates_imported_imu():
    s=pd.read_csv(io.BytesIO(synthetic_csv(500)))
    s['ACCELEROMETER X']=np.sin(np.arange(500)/20)
    s['GRAVITY X']=.01
    v=pd.DataFrame({'Time Since Start of Day':np.arange(500)*.1,'Velocity':np.full(500,36.),
                    'Latitude':s['GPS LATITUDE'],'Longitude':s['GPS LONGITUDE'],
                    'Heading':np.arange(500)*.1,'Yaw Rate':1.})
    a=load_pair(s.to_csv(index=False).encode(),v.to_csv(index=False).encode(),speed_unit='m/s',alignment='timestamp')
    v['Heading']=np.arange(500)*.5;v['Velocity']=70+np.sin(np.arange(500)/20)*10
    b=load_pair(s.to_csv(index=False).encode(),v.to_csv(index=False).encode(),speed_unit='m/s',alignment='timestamp')
    np.testing.assert_array_equal(a.frame[CHANNELS],b.frame[CHANNELS])
    np.testing.assert_allclose(a.frame.lax,s['ACCELEROMETER X']-.01)
    np.testing.assert_allclose(a.frame.wx,s['GYROSCOPE X'])


def test_vehicle_constant_turn_midpoint_integration():
    calibration={'gyro':np.array([0,0,1,0]),'accel':np.zeros(4)}
    f=VehicleDR([0,0],10,0,calibration)
    for _ in range(100):f.step(.1,[0,0,0],[0,0,.1])
    np.testing.assert_allclose(f.position,[100*np.sin(1),100*(1-np.cos(1))],atol=.01)
    assert abs(f.speed-10)<1e-9
    with pytest.raises(ValueError):f.step(1,[0,0,0],[0,0,0])


def test_transfer_uses_only_phone_columns():
    d=replay_dataset().frame
    a=fit_transfer(d)
    b=fit_transfer(d.drop(columns=[c for c in d if c.startswith('ref_')]))
    np.testing.assert_array_equal(a['gyro'],b['gyro'])
    np.testing.assert_array_equal(a['accel'],b['accel'])


@pytest.mark.parametrize('change',['reference','phone_blackout','future'])
def test_vehicle_blackout_is_causal(change):
    ds=replay_dataset();p=FixedPredictor()
    r=simulate(ds,p,100,130,estimator='vehicle')
    other=deepcopy(ds);mask=(other.frame.t>=100)&(other.frame.t<=130)
    if change=='reference':
        other.frame.loc[:,['ref_lat','ref_lon','ref_speed','ref_heading']]=[52.01,-1.01,40,270]
    elif change=='phone_blackout':
        other.frame.loc[mask,['lat','lon','phone_speed','course','gps_fresh','gps_valid']]=[10,10,55,180,True,True]
    else:
        other.frame.loc[other.frame.t>130,['course','lax','lay','laz','wx','wy','wz']]=999
    q=simulate(other,p,100,130,estimator='vehicle')
    ix=np.array(r['velocity_series']['t'])<=130
    np.testing.assert_allclose(np.array(r['trajectories']['fused'])[ix],np.array(q['trajectories']['fused'])[ix])


def test_requested_target_does_not_replace_official_target():
    r=simulate(replay_dataset(),FixedPredictor(),100,130,estimator='vehicle')['metrics']
    assert r['target_drift_pct']==10
    assert r['meets_requested_50pct']==(r['benchmark_eligible'] and r['fused_drift_pct']<50)


def test_sparse_course_wrap_preserves_turn_direction():
    d=replay_dataset().frame.copy();d['phone_speed']=10.;d['course']=(90-np.degrees(d.t*.4))%360
    d[['wx','wy']]=0.;d['wz']=.4
    d['gps_fresh']=(np.arange(len(d))%90)==0
    fit=fit_transfer(d)
    assert fit['intervals']>5
    assert abs(np.r_[0.,0.,.4,1.]@fit['gyro']-.4)<.001


def test_vehicle_does_not_silently_ignore_filter_settings():
    with pytest.raises(ValueError,match='Smoothing'):
        simulate(replay_dataset(),FixedPredictor(),100,130,estimator='vehicle',smoothing=True)


def test_insufficient_heading_calibration_is_explicit():
    d=replay_dataset().frame.iloc[:50].copy();d['gps_fresh']=False
    result=fit_transfer(d)
    np.testing.assert_array_equal(result['gyro'],np.zeros(4))
    assert result['warnings']
