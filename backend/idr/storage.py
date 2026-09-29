"""Disk-backed sessions and model IDs, with atomic JSON writes and bounded RAM cache."""
import json,os,re,uuid
from pathlib import Path
from functools import lru_cache
import pandas as pd
from .data import Dataset
from .models import Predictor
ROOT=Path(os.getenv('IDR_DATA_DIR',Path(__file__).resolve().parents[1]/'state')).resolve()
for p in ('datasets','models','jobs','reports'): (ROOT/p).mkdir(parents=True,exist_ok=True)
def safe(value):
    if not re.fullmatch('[a-f0-9]{16,64}',value):raise ValueError('Invalid identifier')
    return value

def write_json(path,value):
    path=Path(path);tmp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False));os.replace(tmp,path)

def store_dataset(ds):
    sid=ds.fingerprint[:16];folder=ROOT/'datasets'/sid;folder.mkdir(exist_ok=True)
    if (folder/'data.csv.gz').exists() and (folder/'metadata.json').exists():return sid
    # CSV.gz avoids optional parquet dependency and does not deserialize Python objects.
    tmp=folder/(uuid.uuid4().hex+'.tmp.csv.gz');ds.frame.to_csv(tmp,index=False,compression='gzip');os.replace(tmp,folder/'data.csv.gz')
    write_json(folder/'metadata.json',{'report':ds.report,'fingerprint':ds.fingerprint})
    get_dataset.cache_clear();return sid

@lru_cache(maxsize=3)
def get_dataset(sid):
    folder=ROOT/'datasets'/safe(sid)
    if not (folder/'metadata.json').exists():raise ValueError('Dataset not found')
    m=json.loads((folder/'metadata.json').read_text())
    if 'mount_yaw_deg' in m['report']:
        raise ValueError('This dataset used reference-derived mounting calibration. Re-import the original S/V pair with the corrected importer before training or scoring.')
    return Dataset(pd.read_csv(folder/'data.csv.gz'),m['report'],m['fingerprint'])

@lru_cache(maxsize=3)
def get_model(mid):return Predictor(ROOT/'models'/safe(mid))

def list_models():
    result=[]
    for p in sorted((ROOT/'models').glob('*/metadata.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        meta=json.loads(p.read_text())
        if meta.get('training_status')=='complete':result.append(meta)
    return result

def associate(sid,mid):write_json(ROOT/'datasets'/safe(sid)/'model.json',{'model_id':safe(mid)})
def associated(sid):
    p=ROOT/'datasets'/safe(sid)/'model.json'
    if not p.exists():raise ValueError('Train or attach a saved model first')
    return get_model(json.loads(p.read_text())['model_id'])
