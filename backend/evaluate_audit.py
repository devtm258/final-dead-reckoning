"""Deterministic development replay. Select cases using sensor time, not error."""
import argparse,json
from pathlib import Path
import numpy as np
from idr import storage as st
from idr.navigation import simulate

def scenarios(ds):
    t=ds.frame.t.to_numpy();segments=ds.frame.segment.to_numpy()
    for duration in (10.,30.,60.):
        intervals=[]
        for seg in np.unique(segments):
            q=t[segments==seg];lo=q[0]+120;hi=q[-1]-duration-1
            if hi>lo:intervals.append((lo,hi))
        if not intervals:continue
        lengths=np.array([b-a for a,b in intervals]);total=lengths.sum()
        for fraction in (.1,.5,.9):
            target=fraction*total
            for (a,b),length in zip(intervals,lengths):
                if target<=length:
                    yield float(a+target),float(a+target+duration);break
                target-=length

def summary(rows):
    values=[r['fused_drift_pct'] for r in rows if r.get('scorable')]
    return {'attempted':len(rows),'scorable':len(values),'skipped':sum('error' in r for r in rows),
            'under_50_count':sum(v<50 for v in values),'under_10_count':sum(v<10 for v in values),
            'all_scorable_under_50':bool(values) and all(v<50 for v in values),
            'median_pct':float(np.median(values)) if values else None,'worst_pct':max(values) if values else None}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--datasets',nargs='*');args=parser.parse_args()
    model=st.get_model('e95a44ff893b4342');rows=[]
    ids=args.datasets or sorted(p.name for p in (st.ROOT/'datasets').iterdir() if (p/'metadata.json').exists())
    for sid in ids:
        ds=st.get_dataset(sid)
        if not ds.frame.ref_valid.any():continue
        for start,end in scenarios(ds):
            for estimator in ('legacy','vehicle'):
                row={'dataset_id':sid,'estimator':estimator,'blackout_start_s':start,'blackout_end_s':end}
                try:
                    result=simulate(ds,model,start,end,split='exploration',estimator=estimator)
                    row.update(result['metrics']);row['scorable']=row['reference_coverage']>=.95 and row['blackout_distance_m']>=5
                except ValueError as exc:row.update(error=str(exc),scorable=False)
                rows.append(row)
                print(sid,estimator,round(start,1),round(end-start),round(row.get('fused_drift_pct') or 0,2),row.get('error',''),flush=True)
                report={'protocol':'10/30/60s; 10/50/90 percent of sensor-only eligible intervals; 120s prefix; no error-based selection',
                        'evaluation':'development replay; inspected drives, no fresh final-test claim',
                        'model_id':model.meta['model_id'],'runs':rows,
                        'summary':{e:summary([r for r in rows if r['estimator']==e]) for e in ('legacy','vehicle')}}
                Path(args.output).parent.mkdir(parents=True,exist_ok=True)
                Path(args.output).write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report['summary'],indent=2))
if __name__=='__main__':main()
