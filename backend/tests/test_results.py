import numpy as np
import pytest
from idr.results import comparison_outputs
from idr.navigation import simulate
from test_engine import replay_dataset, FixedPredictor


def fixture(valid=None):
    t=np.arange(4,dtype=float)
    truth=np.c_[t*10,np.zeros(4)]
    aided=np.zeros((4,8));aided[:,0]=t*12
    baseline=np.zeros((4,8));baseline[:,1]=t*10
    return comparison_outputs(t,aided,baseline,truth,np.ones(4,bool) if valid is None else valid,
        np.ones(4,bool),np.zeros(4),np.ones(4)*10,[False]*4,[1,2,3,4],20,10,'test')


def test_travel_distance_is_not_position_error():
    r=fixture();s=r['summary']
    assert s['reference_distance_m']==30
    assert s['aided']['distance_m']==36
    assert s['aided']['distance_error_m']==6
    assert s['aided']['distance_error_pct']==20
    assert s['aided']['endpoint_error_m']==6
    assert s['aided']['mean_error_m']==3
    assert s['aided']['rmse_m']==pytest.approx(np.sqrt(14))
    assert s['baseline']['distance_error_m']==0
    assert s['baseline']['endpoint_error_m']==pytest.approx(np.sqrt(1800))
    assert r['distance_series']['reference']==[0,10,20,30]
    assert r['performance']['replay_throughput_hz']==200
    assert r['performance']['phone_update_hz'] is None


def test_reference_gap_not_bridged_and_endpoint_missing():
    r=fixture(np.array([True,False,True,True]));s=r['summary']
    assert s['reference_distance_m']==10
    assert s['covered_duration_s']==1
    assert r['position_series']['aided'][1] is None
    assert not s['eligible'] and not s['distance_complete']
    r=fixture(np.array([True,True,True,False]))
    assert r['summary']['aided']['endpoint_error_m'] is None
    assert r['summary']['aided']['endpoint_drift_pct'] is None


def test_simulation_full_rate_output():
    r=simulate(replay_dataset(),FixedPredictor(),100,130)
    o=r['outputs'];assert len(o['distance_series']['t'])==301
    assert len(r['trajectory_times'])==len(r['trajectories']['fused'])
    assert o['summary']['aided']['endpoint_error_m']==r['metrics']['fused_final_drift_m']
    assert o['summary']['reference_distance_m']==r['metrics']['blackout_distance_m']
    assert o['summary']['baseline']['max_error_m']==r['metrics']['ins_max_err_m']
    assert len(o['heading_series']['aided'])==301
    assert not any(x is not None for x in o['heading_series']['reference'])
    assert o['first_post_blackout_gnss_s']>130


def test_stationary_percentages_are_unscorable():
    t=np.arange(4,dtype=float);p=np.zeros((4,8))
    r=comparison_outputs(t,p,p,p[:,:2],np.ones(4,bool),np.ones(4,bool),np.zeros(4),np.zeros(4),[False]*4,[1]*4,4,10,'test')
    assert r['summary']['aided']['distance_error_pct'] is None
    assert r['summary']['aided']['endpoint_drift_pct'] is None
    assert not r['summary']['eligible']


def test_text_summary_handles_missing_endpoint(tmp_path,monkeypatch):
    import json
    from server import summary,SessionIn
    from idr import storage as st
    monkeypatch.setattr(st,'ROOT',tmp_path)
    sid='a'*16;folder=tmp_path/'datasets'/sid;folder.mkdir(parents=True)
    (folder/'simulation.json').write_text(json.dumps({'model_id':'b'*16,'metrics':{
        'evaluation_mode':'exploration','blackout_duration_s':30,'blackout_distance_m':100,
        'fused_final_drift_m':None,'fused_drift_pct':None,'fused_max_err_m':10,'meets_isro_target':False}}))
    assert 'unavailable (missing endpoint reference)' in summary(SessionIn(session_id=sid))['summary']
