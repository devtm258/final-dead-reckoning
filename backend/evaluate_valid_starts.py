"""Supplementary outage benchmark with phone-GNSS initialization guards.

Starts are selected from phone measurements before inspecting VBOX labels or scoring.
Usage: python backend/evaluate_valid_starts.py DATASET_ID MODEL_ID OUTPUT.json
"""
import json,sys
from pathlib import Path
import numpy as np
from idr import storage as st
from idr.navigation import simulate

def main(sid,mid,out):
 ds=st.get_dataset(sid);model=st.get_model(mid);d=ds.frame;t=d.t.to_numpy()
 fresh=d.gps_fresh.to_numpy()&d.gps_valid.to_numpy()&(d.phone_speed.to_numpy()>3)
 last=np.maximum.accumulate(np.where(fresh,t,-1e9));segments=d.segment.to_numpy()
 rows=[];skipped=[]
 for duration in (10,30,60):
  candidates=np.flatnonzero((t-t[0]>90)&(t-t[0]<t[-1]-duration-15)&
     (t-last<=1.5)&(d.phone_speed.to_numpy()>3)&
     (segments==segments[np.minimum(np.searchsorted(t,t+duration).clip(max=len(t)-1),len(t)-1)]))
  # Spaced across the drive, deterministic and fixed before any VBOX error is read.
  selected=np.unique(candidates[np.linspace(0,len(candidates)-1,min(3,len(candidates)),dtype=int)]) if len(candidates) else []
  for ix in selected:
   start=float(t[ix])
   try:rows.append(simulate(ds,model,start,start+duration)['metrics'])
   except ValueError as exc:skipped.append({'start':start,'duration':duration,'reason':str(exc)})
 pct=[r['fused_drift_pct'] for r in rows if r['benchmark_eligible']]
 result={'model_id':mid,'start_selection':'predefined phone GNSS freshness <=1.5 s, speed >3 m/s, >=90 s prefix, three evenly spaced candidates per duration; reference not used for selection',
  'runs':rows,'skipped':skipped,'eligible_runs':len(pct),'pass_rate':float(np.mean(np.array(pct)<10)) if pct else None,'median_drift_pct':float(np.median(pct)) if pct else None,'p95_drift_pct':float(np.quantile(pct,.95)) if pct else None,'claim':'Supplementary recorded-data evaluation, not official SIH certification.'}
 Path(out).write_text(json.dumps(result,indent=2))
 print({k:result[k] for k in ('eligible_runs','pass_rate','median_drift_pct','p95_drift_pct')})
if __name__=='__main__':main(*sys.argv[1:])
