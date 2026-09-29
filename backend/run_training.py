"""CLI uses the same protected training engine as the website.

python run_training.py --plan plan.json
python run_training.py --resume-run RUN_ID
Plan JSON has the same fields as POST /api/pipeline/train (see /docs).
Upload/register datasets first. Stop the backend before running this CLI.
"""
import argparse
import json
from pathlib import Path
from idr import registry as reg
from idr.training import prepare_plan, reserve, run_training

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--plan')
    group.add_argument('--resume-run')
    args = parser.parse_args()
    reg.bootstrap()
    if args.plan:
        from server import TrainIn
        request = TrainIn.model_validate(json.loads(Path(args.plan).read_text())).model_dump()
        job = reserve(prepare_plan(request))
        rid = job['job_id']
    else:
        rid = args.resume_run
        if reg.run(rid)['status'] not in ('interrupted', 'paused', 'failed'):
            raise SystemExit('Only interrupted, paused or failed runs can resume.')
    print('Run:', rid, flush=True)
    try:
        result = run_training(rid, epoch_hook=lambda ep: print('Saved epoch', ep, flush=True))
        print(json.dumps(result.meta, indent=2))
    except KeyboardInterrupt:
        print('Interrupted. Resume this run from its last completed epoch:', rid)
