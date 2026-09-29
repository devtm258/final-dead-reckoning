"""Local FastAPI service. CPU jobs serialized; saved inference does not depend on a session process."""
import asyncio,json,os
from pathlib import Path
from contextlib import asynccontextmanager
import numpy as np
from fastapi import FastAPI,UploadFile,File,Form,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,ConfigDict
from typing import Literal
from idr import storage as st
from idr.data import load_pair,FEATURE_NAMES
from idr import registry as reg
from idr.training import TrainingManager
from idr.navigation import simulate,benchmark,compare_variants
MAX_BYTES=100*1024*1024

@asynccontextmanager
async def lifespan(app):
    reg.bootstrap()
    app.state.training=TrainingManager()
    yield
    app.state.training.close()

app=FastAPI(title='Tesseracts IDR',version='3.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.exception_handler(ValueError)
async def bad_request(req,exc):return JSONResponse(status_code=400,content={'detail':str(exc)})

class Strict(BaseModel):model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
class Assignment(Strict):
    session_id:str
    role:Literal['train','validation','test']
class TrainIn(Strict):
    session_id:str|None=None
    mode:Literal['create','continue']='create'
    name:str=Field('CNN-GRU-35',min_length=1,max_length=80)
    assignments:list[Assignment]=Field(min_length=1,max_length=100)
    replay:bool=True
    kind:Literal['extra_trees','random_forest','tcn','cnn_gru']='cnn_gru'
    window:int=Field(35,ge=10,le=100)
    n_estimators:int=Field(60,ge=10,le=150)
    epochs:int=Field(20,ge=1,le=100)
    max_windows:int=Field(30000,ge=1000,le=100000)
    parent_id:str|None=None
class SimIn(Strict):
    session_id:str
    blackout_start_s:float
    blackout_end_s:float
    nhc:Literal['off','fixed','adaptive']='adaptive'
    zupt:bool=True
    split:Literal['test','exploration']='test'
    ml_enabled:bool=True
    estimator:Literal['legacy','vehicle']='vehicle'
    quality_mode:Literal['off','observe','adaptive']='observe'
    smoothing:bool=False
    cutoff_hz:float=Field(2.,gt=0,le=4)
class SessionIn(Strict):session_id:str
class BenchmarkIn(SessionIn):
    estimator:Literal['legacy','vehicle']='vehicle'
class CompareIn(Strict):
    session_id:str
    blackout_start_s:float
    blackout_end_s:float
    split:Literal['test','exploration']='test'
class AttachIn(SessionIn):model_id:str
class DatasetEdit(Strict):
    name:str=Field(min_length=1,max_length=160)
    acquisition:str=Field(min_length=1,max_length=160)


def finite_json(x):
    if isinstance(x,dict):return {k:finite_json(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [finite_json(v) for v in x]
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    if isinstance(x,np.integer):return int(x)
    return x

def describe(sid):
    ds=st.get_dataset(sid);d=ds.frame;idx=np.linspace(0,len(d)-1,min(400,len(d))).astype(int);ss=d.iloc[idx]
    res={'session_id':sid,'n_samples':len(d),'duration_s':float(d.t.iloc[-1]),'lat0':float(d.lat.iloc[0]),'lon0':float(d.lon.iloc[0]),'has_vbox':bool(d.ref_valid.any()),'gt_source':ds.report['reference'],'quality_report':ds.report,'preview':d.head(8).to_dict('records'),'sensor_series':{'t':ss.t.tolist(),'ax':ss.ax.tolist(),'ay':ss.ay.tolist(),'az':ss.az.tolist(),'speed':ss.phone_speed.tolist(),'gt_v':ss.ref_speed.tolist()},'trained':False}
    try:res['model_id']=st.associated(sid).meta['model_id'];res['trained']=True
    except (ValueError,FileNotFoundError):pass
    return finite_json(res)

def train_result(sid,model):
    ds=st.get_dataset(sid);d=ds.frame;meta=model.meta
    # Preview a contiguous tail, with true causal history; no separate predictions on sparse rows.
    local=d.tail(min(3000,len(d))).reset_index(drop=True);p,v=model.sequence(local);ix=np.linspace(0,len(local)-1,min(400,len(local))).astype(int)
    ranges=meta.get('source_splits',{}).get(ds.report.get('source_id'),meta['dataset_splits'].get(ds.fingerprint,{}))
    return finite_json({**meta,**meta['validation'],'velocity_preview':{'t':local.t.to_numpy()[ix].tolist(),'gps_speed':local.ref_speed.to_numpy()[ix].tolist(),'ml_pred':p[ix].tolist()},'test_range':ranges.get('test') if ranges else [0,float(d.t.iloc[-1])], 'evaluation_roles':list(ranges)})

@app.get('/api/')
def health():return {'service':'Tesseracts IDR','status':'online','version':'3.0.0','device_benchmark_verified':False,'active_model':reg.active()}
@app.get('/api/features')
def features():return {'feature_names':FEATURE_NAMES}
@app.post('/api/dataset/load-preset')
async def preset():
    root=Path(__file__).resolve().parents[1]/'data'/'raw'
    s=root/'S-M.csv.gz';v=root/'V-M.csv.gz'
    if not s.exists():
        # Lean distribution already includes the aligned M recording in the
        # durable registry; avoid shipping a duplicate raw S/V pair.
        existing=next((r for r in reg.datasets() if r['name']=='M (Driver B)'),None)
        if existing:return describe(existing['session_id'])
        raise ValueError('Preset missing: place S-M.csv.gz and V-M.csv.gz in data/raw or upload a pair.')
    ds=await asyncio.to_thread(load_pair,str(s),str(v) if v.exists() else None)
    sid=await asyncio.to_thread(st.store_dataset,ds)
    reg.register_dataset(sid,'S-M / V-M','m-driver-b')
    if not (st.ROOT/'datasets'/sid/'model.json').exists() and (st.ROOT/'models'/'5953a00cc3994cd1'/'metadata.json').exists():st.associate(sid,'5953a00cc3994cd1')
    return describe(sid)
@app.post('/api/dataset/upload')
async def upload(smartphone:UploadFile=File(...),vbox:UploadFile|None=File(None),speed_unit:Literal['auto','m/s','km/h']=Form('auto'),alignment:Literal['motion','paired']=Form('motion')):
    async def read_limit(f):
        b=await f.read(MAX_BYTES+1)
        if len(b)>MAX_BYTES:raise HTTPException(413,'CSV exceeds 100 MiB limit')
        return b
    s=await read_limit(smartphone);v=await read_limit(vbox) if vbox else None
    ds=await asyncio.to_thread(load_pair,s,v,speed_unit,alignment);sid=await asyncio.to_thread(st.store_dataset,ds)
    reg.register_dataset(sid,smartphone.filename)
    return describe(sid)
@app.get('/api/datasets')
def datasets():
    return reg.datasets()
@app.post('/api/dataset/{sid}/metadata')
def edit_dataset(sid:str,p:DatasetEdit):return reg.edit_dataset(sid,p.name,p.acquisition)
@app.get('/api/families/{fid}')
def family(fid:str):return reg.family(st.safe(fid))
@app.get('/api/dataset/{sid}')
def dataset(sid:str):return describe(sid)
@app.get('/api/models')
def models():return st.list_models()
@app.post('/api/models/attach')
async def attach(p:AttachIn):
    st.get_dataset(p.session_id);m=st.get_model(p.model_id);st.associate(p.session_id,p.model_id)
    reg.set_active(p.model_id)
    return await asyncio.to_thread(train_result,p.session_id,m)
@app.post('/api/pipeline/train')
def submit(p:TrainIn):
    return app.state.training.submit(p.model_dump())
@app.get('/api/jobs')
def jobs():return reg.runs()
@app.get('/api/jobs/{jid}')
def job(jid:str):
    return reg.run(jid)
@app.post('/api/jobs/{jid}/pause')
def pause(jid:str):return app.state.training.pause(st.safe(jid))
@app.post('/api/jobs/{jid}/resume')
def resume(jid:str):return app.state.training.resume(st.safe(jid))

def protect_evaluation(sid,model):
    """Reject related clips whose group is known to be train/validation, even if uploaded later."""
    if 'family_id' not in model.meta:return
    record=reg.dataset(sid)
    if record['acquisition'].startswith('unassigned-'):
        raise ValueError('Assign the recording acquisition group before held-out evaluation.')
    fam=reg.family(model.meta['family_id'])
    for entry in fam['assignments']:
        if (record['acquisition']==entry['acquisition'] or record['source']==entry['source']) and entry['role']!='test':
            raise ValueError('This acquisition belongs to training/validation. Use exploration, or choose a test acquisition.')
@app.post('/api/pipeline/simulate')
async def simulation(p:SimIn):
    ds=st.get_dataset(p.session_id);m=st.associated(p.session_id)
    if p.split=='test':protect_evaluation(p.session_id,m)
    r=await asyncio.to_thread(simulate,ds,m,p.blackout_start_s,p.blackout_end_s,p.nhc,p.zupt,p.split,p.ml_enabled,p.quality_mode,p.smoothing,p.cutoff_hz,p.estimator)
    r['test_info']={'session_id':p.session_id,'recording':reg.dataset(p.session_id)['name'],'model_name':m.meta.get('family_name',m.meta.get('kind')),'model_version':m.meta.get('version',1)}
    r['simulation_id']=__import__('uuid').uuid4().hex
    r=finite_json(r);st.write_json(st.ROOT/'datasets'/p.session_id/'simulation.json',r);return r
@app.post('/api/pipeline/benchmark')
async def bench(p:BenchmarkIn):
    model=st.associated(p.session_id);protect_evaluation(p.session_id,model)
    r=await asyncio.to_thread(benchmark,st.get_dataset(p.session_id),model,estimator=p.estimator);r=finite_json(r)
    r['session_id']=p.session_id;r['recording']=reg.dataset(p.session_id)['name']
    st.write_json(st.ROOT/'reports'/f'{p.session_id}-{r["model_id"]}.json',r);return r
@app.post('/api/pipeline/compare')
async def comparison(p:CompareIn):
    model=st.associated(p.session_id)
    if p.split=='test':protect_evaluation(p.session_id,model)
    r=await asyncio.to_thread(compare_variants,st.get_dataset(p.session_id),model,p.blackout_start_s,p.blackout_end_s,p.split)
    return finite_json(r)
@app.post('/api/ai/summary')
def summary(p:SessionIn):
    path=st.ROOT/'datasets'/st.safe(p.session_id)/'simulation.json'
    if not path.exists():raise ValueError('Run simulation first')
    r=json.loads(path.read_text());m=r['metrics'];pct=m['fused_drift_pct']
    endpoint=f"{m['fused_final_drift_m']:.2f} m" if m['fused_final_drift_m'] is not None else 'unavailable (missing endpoint reference)'
    return {'summary':f"Recorded-data {m['evaluation_mode']} run. Model {r['model_id']}.\nBlackout: {m['blackout_duration_s']:.1f} s over {m['blackout_distance_m']:.1f} m.\nFinal error: {endpoint}; drift: {str(round(pct,2))+'%' if pct is not None else 'undefined for short/stationary travel'}. Maximum error: {m['fused_max_err_m']:.2f} m.\nEligible held-out endpoint target pass: {m['meets_isro_target']}.\nThis does not certify lane-level accuracy, mobile latency, or all SIH requirements. No cloud LLM is used.", 'source':'deterministic local metrics'}

@app.post('/api/dataset/{sid}/roads')
async def roads(sid:str,roads:UploadFile=File(...)):
    ds=st.get_dataset(sid);raw=await roads.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:raise HTTPException(413,'Road GeoJSON limit is 10 MiB')
    from idr.mapmatch import RoadMatcher
    geo=json.loads(raw);RoadMatcher(geo,(float(ds.frame.lat.iloc[0]),float(ds.frame.lon.iloc[0])))
    st.write_json(st.ROOT/'datasets'/sid/'roads.json',geo)
    return {'status':'saved','note':'Local road geometry, independent of optional online background tiles.'}

@app.post('/api/dataset/{sid}/match')
def match(sid:str,simulation_id:str|None=None):
    st.get_dataset(sid);folder=st.ROOT/'datasets'/sid
    if not (folder/'roads.json').exists() or not (folder/'simulation.json').exists():raise ValueError('Upload roads and run simulation first.')
    from idr.mapmatch import RoadMatcher
    from idr.data import enu
    sim=json.loads((folder/'simulation.json').read_text())
    if simulation_id and sim.get('simulation_id')!=simulation_id:raise ValueError('The saved result changed. Run this test again before matching roads.')
    pts=sim['trajectories']['fused'];origin=pts[0];xy=enu(np.array(pts)[:,0],np.array(pts)[:,1],origin);matcher=RoadMatcher(json.loads((folder/'roads.json').read_text()),origin)
    out=[]
    for i,p in enumerate(xy):
        delta=p-xy[max(0,i-1)];out.append(matcher.step(p,float(np.arctan2(delta[1],delta[0])),float(np.linalg.norm(delta))))
    return {'trajectory':[v['position'] for v in out],'matched_fraction':float(np.mean([v['matched'] for v in out])),'note':'Diagnostic causal beam matcher on displayed points; not fused or scored as independent truth.'}

# Serve the packaged redesigned UI after API routes; no Node process required.
from fastapi.staticfiles import StaticFiles
_dist=Path(__file__).resolve().parents[1]/'frontend'/'dist'
if _dist.exists():app.mount('/',StaticFiles(directory=_dist,html=True),name='frontend')
