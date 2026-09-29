import numpy as np
import pandas as pd
import pytest
from idr.data import load_pair,sequence_indices
from idr.models import make_net,np_forward
from idr.navigation import PlanarESKF
from idr.eskf3d import ESKF3D
from idr.mapmatch import RoadMatcher


def synthetic_csv(n=500):
 t=np.arange(n)*100
 s=pd.DataFrame({'GPS LATITUDE':52+np.arange(n)*.000001,'GPS LONGITUDE':np.full(n,-1.),'GPS SPEED':np.full(n,3.6),'TIME SINCE START':t,'GPS ORIENTATION':np.zeros(n)})
 for a in 'XYZ':s['ACCELEROMETER '+a]=9.80665 if a=='Z' else 0.;s['GRAVITY '+a]=9.80665 if a=='Z' else 0.;s['GYROSCOPE '+a]=np.arange(n)*1e-6+ord(a)*1e-4
 return s.to_csv(index=False).encode()

def test_explicit_axis_mapping():
 ds=load_pair(synthetic_csv(),speed_unit='km/h')
 assert np.allclose(ds.frame.phone_speed,1)
 assert not np.allclose(ds.frame.wx,ds.frame.wy)
 assert not ds.frame.ref_valid.any()

def test_no_window_crosses_gap():
 d=load_pair(synthetic_csv()).frame;d.loc[250:,'segment']=1
 ids=sequence_indices(d,30)
 assert not np.any((ids>=250)&(ids<279))

def test_reject_backwards_clock():
 s=pd.read_csv(__import__('io').BytesIO(synthetic_csv()));s.loc[250,'TIME SINCE START']=0
 with pytest.raises(ValueError,match='strictly increasing'):load_pair(s.to_csv(index=False).encode())

@pytest.mark.parametrize('kind',['tcn','cnn_gru'])
def test_numpy_matches_torch_and_is_causal(kind):
 torch=pytest.importorskip('torch');torch.manual_seed(5);net=make_net(kind).eval()
 x=torch.randn(2,6,30)
 with torch.no_grad():y=net(x).numpy();x2=x.clone();x2[:,:,20:]+=20;y2=net(x2).numpy()
 assert np.allclose(y[:,:20],y2[:,:20],atol=1e-6)
 weights={k:v.detach().numpy() for k,v in net.state_dict().items()}
 assert np.allclose(np_forward(kind,x.numpy(),weights),y,atol=2e-5)

def test_planar_stationary_and_moving():
 f=PlanarESKF([0,0],10,0,'adaptive',True)
 for i in range(100):f.step(.1,[0,0],0,(10,.25) if i%5==0 else None)
 assert np.allclose(f.x[:2],[100,0],atol=.01)
 assert f.zupt_count==0
 assert np.min(np.linalg.eigvalsh(f.P))>-1e-9

def test_3d_stationary_and_constant_velocity():
 f=ESKF3D(velocity=[5,0,0])
 for i in range(200):f.predict([0,0,9.80665],[0,0,0],.005);f.nhc()
 assert np.allclose(f.p,[5,0,0],atol=.001)
 assert np.min(np.linalg.eigvalsh(f.P))>-1e-8
 assert np.allclose(f.R.T@f.R,np.eye(3))

def test_gnss_outlier_gated():
 f=ESKF3D();assert not f.position([1e6,0,0]);assert np.allclose(f.p,0)

def test_offline_matcher():
 roads={'features':[{'geometry':{'type':'LineString','coordinates':[[-1,52],[-.99,52]]},'properties':{}}]}
 m=RoadMatcher(roads,(52,-1));assert m.step([20,5],0,1)['matched'];assert not m.step([10000,10000],0,1)['matched']

class FixedPredictor:
    window=20
    meta={'model_id':'0'*16,'sample_hz':10.,'dataset_splits':{}}
    def sequence(self,d):return np.full(len(d),5.),np.full(len(d),.5)

def replay_dataset():
    ds=load_pair(synthetic_csv(2000),speed_unit='km/h');d=ds.frame
    d['ref_speed']=1.;d['ref_lat']=d.lat;d['ref_lon']=d.lon;d['ref_heading']=0.;d['ref_valid']=True
    return ds

def test_reference_blackout_values_cannot_change_prediction():
    from copy import deepcopy
    from idr.navigation import simulate
    ds=replay_dataset();r1=simulate(ds,FixedPredictor(),100,130)
    changed=deepcopy(ds);mask=(changed.frame.t>=100)&(changed.frame.t<=130)
    changed.frame.loc[mask,'ref_lat']+=.001;changed.frame.loc[mask,'ref_speed']=50
    r2=simulate(changed,FixedPredictor(),100,130)
    assert np.allclose(r1['trajectories']['fused'],r2['trajectories']['fused'])
    assert r1['metrics']['fused_final_drift_m']!=r2['metrics']['fused_final_drift_m']

def test_blackout_phone_gnss_does_not_change_prediction():
    from copy import deepcopy
    from idr.navigation import simulate
    ds=replay_dataset();r1=simulate(ds,FixedPredictor(),100,130)
    changed=deepcopy(ds);mask=(changed.frame.t>=100)&(changed.frame.t<=130)
    changed.frame.loc[mask,['lat','lon','phone_speed','course']]=[10,10,55,180]
    r2=simulate(changed,FixedPredictor(),100,130)
    assert np.allclose(r1['trajectories']['fused'],r2['trajectories']['fused'])

def test_future_heading_not_used_in_blackout():
    from copy import deepcopy
    from idr.navigation import simulate
    ds=replay_dataset();r1=simulate(ds,FixedPredictor(),100,130)
    changed=deepcopy(ds);changed.frame.loc[changed.frame.t>130,'course']=180
    r2=simulate(changed,FixedPredictor(),100,130)
    ix=np.array(r1['velocity_series']['t'])<=130
    assert np.allclose(np.array(r1['trajectories']['fused'])[ix],np.array(r2['trajectories']['fused'])[ix])

def test_invalid_blackout_cannot_pass():
    from idr.navigation import simulate
    with pytest.raises(ValueError):simulate(replay_dataset(),FixedPredictor(),1000,1100)
    with pytest.raises(ValueError):simulate(replay_dataset(),FixedPredictor(),100,90)

def test_holdout_restriction():
    from idr.navigation import simulate
    ds=replay_dataset();p=FixedPredictor();p.meta={**p.meta,'dataset_splits':{ds.fingerprint:{'test':[170,199.9]}}}
    with pytest.raises(ValueError,match='held-out'):simulate(ds,p,100,130)

def test_api_contract():
    from fastapi.testclient import TestClient
    from server import app
    c=TestClient(app)
    assert c.get('/api/').status_code==200
    assert c.post('/api/pipeline/train',json={'session_id':'0'*16,'window':1}).status_code==422
    assert c.get('/api/dataset/not-an-id').status_code==400
    assert c.post('/api/pipeline/simulate',json={'session_id':'0'*16,'blackout_start_s':1,'blackout_end_s':2,'unknown':True}).status_code==422


def test_compressed_preset_preserves_data_and_identity():
    import gzip
    raw=synthetic_csv()
    plain=load_pair(raw,speed_unit='km/h')
    compressed=load_pair(gzip.compress(raw),speed_unit='km/h')
    assert plain.fingerprint==compressed.fingerprint
    pd.testing.assert_frame_equal(plain.frame,compressed.frame)
