"""Recreate the two-start-per-duration 10/30/60-second diagnostic protocol."""
import json,sys
from pathlib import Path
from idr import storage as st
from idr.navigation import benchmark

def main(dataset_id,model_id,output):
 report=benchmark(st.get_dataset(dataset_id),st.get_model(model_id),starts_per_duration=2)
 Path(output).parent.mkdir(parents=True,exist_ok=True)
 Path(output).write_text(json.dumps(report,indent=2,allow_nan=False))
 print(json.dumps({key:report[key] for key in ('eligible_runs','pass_rate','median_drift_pct','p95_drift_pct')},indent=2))
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: python -m evaluate_release DATASET_ID MODEL_ID OUTPUT.json')
 main(*sys.argv[1:])
