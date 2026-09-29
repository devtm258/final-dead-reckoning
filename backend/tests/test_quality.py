from copy import deepcopy
import numpy as np
import pytest
from idr.quality import SensorQuality, adaptation
from idr.navigation import simulate, PlanarESKF
from test_engine import replay_dataset, FixedPredictor


def test_causal_spike_and_reset():
    q=SensorQuality()
    for _ in range(12):q.step([0,0,0],[0,0,0],.1)
    filtered,flags=q.step([10,0,0],[0,0,0],.1)
    assert flags['accel_flag'] and not flags['gyro_flag']
    assert 0 < filtered[0] < 10
    with pytest.raises(ValueError):q.step([0,0,0],[0,0,0],1.)
    after,_=q.step([1,2,3],[0,0,0],.1)
    assert np.array_equal(after,[1,2,3,0,0,0])
    with pytest.raises(ValueError):q.step([np.nan,0,0],[0,0,0],.1)


def test_future_samples_cannot_change_quality_prefix():
    rng=np.random.default_rng(1);values=rng.normal(size=(60,6))
    changed=values.copy();changed[30:]*=100
    def run(x):
        q=SensorQuality();return [q.step(v[:3],v[3:],.1) for v in x]
    a,b=run(values),run(changed)
    for (x,f),(y,g) in zip(a[:30],b[:30]):
        assert np.array_equal(x,y) and f==g


def test_observation_unchanged_and_baseline_preserved():
    ds=replay_dataset();p=FixedPredictor()
    ds.frame.loc[1100,'lax']=20
    off=simulate(ds,p,100,130,quality_mode='off')
    observe=simulate(ds,p,100,130,quality_mode='observe')
    adapted=simulate(ds,p,100,130,quality_mode='adaptive',smoothing=True)
    assert off['trajectories']==observe['trajectories']
    assert off['trajectories']['ins_raw']==adapted['trajectories']['ins_raw']
    assert off['velocity_series']['ml']==adapted['velocity_series']['ml']
    assert observe['metrics']['quality_flagged_samples']>0
    assert observe['metrics']['adapted_samples']==0
    assert adapted['metrics']['adapted_samples']>0
    assert len(adapted['velocity_series']['baseline'])==len(adapted['velocity_series']['t'])
    assert len(adapted['error_series']['baseline_m'])==len(adapted['error_series']['t'])


def test_adaptation_never_reads_reference_or_blackout_gnss():
    ds=replay_dataset();p=FixedPredictor();changed=deepcopy(ds)
    mask=(changed.frame.t>=100)&(changed.frame.t<=130)
    changed.frame.loc[mask,['ref_lat','ref_heading','lat','lon','phone_speed','course']]=[10,270,10,10,50,180]
    a=simulate(ds,p,100,130,quality_mode='adaptive',smoothing=True)
    b=simulate(changed,p,100,130,quality_mode='adaptive',smoothing=True)
    assert a['trajectories']['fused']==b['trajectories']['fused']
    assert a['quality_series']==b['quality_series']


def test_heading_conventions_and_covariance_scales():
    # Navigation state yaw is counterclockwise from East; GNSS course is clockwise from North.
    for course,expected in [(0,[0,10]),(90,[10,0]),(180,[0,-10]),(270,[-10,0])]:
        f=PlanarESKF([0,0],10,np.deg2rad(90-course),'off',False)
        for _ in range(10):f.step(.1,[0,0],0)
        assert np.allclose(f.x[:2],expected)
    q=adaptation({'accel_flag':True,'gyro_flag':False},.5,[0,0])
    assert q=={'accel_process_scale':4.,'gyro_process_scale':1.,'nhc_scale':4.,'speed_scale':1.}
