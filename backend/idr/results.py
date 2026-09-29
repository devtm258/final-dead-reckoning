"""Evaluation-only outputs. Never feed reference data back into navigation.
Distances use native-rate horizontal positions and identical adjacent valid
reference intervals. Missing reference intervals are never bridged.
"""
import platform
import numpy as np


def comparison_outputs(times, states, baseline, reference, valid, flags, heading, ref_speed, gnss_updates, processing_ms, total_ms, sample_hz, split):
    t=np.asarray(times); ids=np.flatnonzero(flags); bt=t[ids]
    truth=np.asarray(reference)[ids]; aided=np.asarray(states)[ids]; base=np.asarray(baseline)[ids]
    ok=np.asarray(valid,dtype=bool)[ids] & np.isfinite(truth).all(axis=1)
    edge=ok[1:] & ok[:-1]
    def distance(points):
        increments=np.linalg.norm(np.diff(points[:,:2],axis=0),axis=1)
        return np.r_[0.,np.cumsum(np.where(edge,increments,0.))]
    distances={k:distance(p) for k,p in [('reference',truth),('baseline',base),('aided',aided)]}
    length=float(distances['reference'][-1]); full=bool(ok.all()); usable=length>=5
    errors={k:np.where(ok,np.linalg.norm(p[:,:2]-truth,axis=1),np.nan) for k,p in [('baseline',base),('aided',aided)]}
    reasons=[]
    if split!='test':reasons.append('Exploration: this is not a held-out benchmark run.')
    if not full:reasons.append('Missing reference samples: distances cover valid adjacent intervals only; complete blackout scoring unavailable.')
    if not usable:reasons.append('Reference travel is below 5 m; percentage metrics are not scored.')
    def clean(values):return [float(x) if np.isfinite(x) else None for x in values]
    def percentage(x):return float(x/length*100) if usable and x is not None else None
    summary={}
    for key in ('baseline','aided'):
        e=errors[key]; good=e[np.isfinite(e)]; endpoint=float(e[-1]) if ok[-1] else None
        delta=float(distances[key][-1]-length)
        summary[key]={'distance_m':float(distances[key][-1]),'distance_error_m':delta,
            'distance_error_pct':percentage(delta),'absolute_distance_error_m':abs(delta),
            'mean_error_m':float(np.mean(good)) if len(good) else None,
            'rmse_m':float(np.sqrt(np.mean(good**2))) if len(good) else None,
            'max_error_m':float(np.max(good)) if len(good) else None,
            'endpoint_error_m':endpoint,'endpoint_drift_pct':percentage(endpoint),
            'max_error_pct':percentage(float(np.max(good))) if len(good) else None}
    psi=np.asarray(heading)[ids]; speed=np.asarray(ref_speed)[ids]
    hok=ok & np.isfinite(psi) & (speed>2)
    heading_series={'t':bt.tolist(),'reference':clean(np.where(hok,(90-np.degrees(psi))%360,np.nan))}
    for key,p in [('baseline',base),('aided',aided)]:
        heading_series[key]=clean((90-np.degrees(p[:,4]))%360)
        e=np.degrees((p[:,4]-psi+np.pi)%(2*np.pi)-np.pi)
        heading_series[key+'_error']=clean(np.where(hok,e,np.nan))
        summary[key]['heading_rmse_deg']=float(np.sqrt(np.mean(e[hok]**2))) if hok.any() else None
    # Contiguous mode intervals derived from actual GNSS updates. Absence of a
    # fresh update outside the requested blackout is not represented as recovery.
    modes=[]; last_fix=None
    for i,now in enumerate(t):
        if gnss_updates[i]:last_fix=float(now)
        mode='Blackout · dead reckoning' if flags[i] else ('GNSS update available' if gnss_updates[i] else 'Between fixes · inertial propagation')
        if not modes or modes[-1]['mode']!=mode:modes.append({'start_s':float(now),'end_s':float(now),'mode':mode})
        modes[-1]['end_s']=float(t[i+1]) if i+1<len(t) else float(now)
    post=[float(t[i]) for i in range(len(t)) if t[i]>bt[-1] and gnss_updates[i]]
    pct=summary['aided']['endpoint_drift_pct']
    return {'summary':{'reference_distance_m':length,**summary,'reference_coverage':float(ok.mean()),
                'distance_complete':full,'covered_duration_s':float(np.sum(np.diff(bt)[edge])),
                'sample_start_s':float(bt[0]),'sample_end_s':float(bt[-1]),
                'endpoint_reference_valid':bool(ok[-1]),'eligible':not reasons,'reasons':reasons,
                'under_10_endpoint':bool(not reasons and pct is not None and pct<10),
                'method':'Horizontal path length at native sample rate, over shared adjacent valid reference intervals. No map snapping or speed integration. Positive distance error means overestimation.'},
            'distance_series':{'t':bt.tolist(),**{k:v.tolist() for k,v in distances.items()},
                'baseline_error':(distances['baseline']-distances['reference']).tolist(),
                'aided_error':(distances['aided']-distances['reference']).tolist(),'reference_valid':ok.tolist()},
            'position_series':{'t':bt.tolist(),**{k:clean(v) for k,v in errors.items()}},
            'heading_series':heading_series,
            'mode_timeline':modes,'first_post_blackout_gnss_s':post[0] if post else None,
            'performance':{'device':f'{platform.system()} {platform.machine()} · desktop/server Python',
                'input_sample_hz':float(sample_hz),'processed_samples':len(t),'replay_total_ms':float(total_ms),
                'replay_throughput_hz':float(len(t)*1000/total_ms) if total_ms>0 else None,
                'step_mean_ms':float(np.mean(processing_ms)),'step_p95_ms':float(np.quantile(processing_ms,.95)),
                'step_max_ms':float(np.max(processing_ms)),'phone_update_hz':None,'edge_update_hz':None,
                'note':'Offline replay throughput includes batched model inference and warmup. Step latency excludes batched model inference. Neither measures live phone update rate, per-sample end-to-end latency, or transition latency.'}}
