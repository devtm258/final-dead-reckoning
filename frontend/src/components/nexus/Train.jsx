import React,{useCallback,useEffect,useState} from 'react';
import ScreenShell from './ScreenShell';
import {Play} from './Icons';
import {json,listDatasets,listModels,listJobs,pairFiles,uploadPair} from './api';
const fmt=n=>n!=null&&Number.isFinite(Number(n))?Number(n).toFixed(3):'—';
export default function Train({selected,setSelected,model,setModel,simulation,setSimulation,page,onNavigate,benchmark,setBenchmark}){
 const [estimator,setEstimator]=useState('vehicle'),[blackoutStart,setBlackoutStart]=useState(300),[blackoutDuration,setBlackoutDuration]=useState(30);
 const [search,setSearch]=useState(''),[records,setRecords]=useState([]),[models,setModels]=useState([]),[jobs,setJobs]=useState([]);
 const [assign,setAssign]=useState(()=>{try{return JSON.parse(localStorage.getItem('idr_split_draft')||'{}')}catch{return {}}}),[groups,setGroups]=useState({}),[names,setNames]=useState({});
 const [kind,setKind]=useState('cnn_gru'),[window,setWindow]=useState(35),[epochs,setEpochs]=useState(20),[name,setName]=useState('CNN-GRU-35');
 const [parent,setParent]=useState(''),[jobId,setJobId]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const refresh=useCallback(async()=>{try{const [ds,ms,js]=await Promise.all([listDatasets(),listModels(),listJobs()]);setRecords(ds);setModels(ms);setJobs(js);if(!selected&&ds[0])setSelected(ds[0].session_id)}catch(e){setError(e.message)}},[selected,setSelected]);
 useEffect(()=>{refresh();const timer=setInterval(refresh,2500);return()=>clearInterval(timer)},[refresh]);
 useEffect(()=>localStorage.setItem('idr_split_draft',JSON.stringify(assign)),[assign]);
 const active=jobs.find(j=>['queued','running','pausing'].includes(j.status));
 const job=jobs.find(j=>j.job_id===jobId)||jobs[0];
 async function upload(files){setBusy(true);setError('');try{const pairs=pairFiles([...files]);if(!pairs.length)throw Error('Select paired S-*.csv and V-*.csv files or an extracted dataset folder.');for(const pair of pairs){const d=await uploadPair(pair.smartphone,pair.vbox);const root=pair.dir.split('/')[0]||'new-drive';const driver=root.match(/\(Driver\s+([^)]+)\)/i);const group=driver?`driver-${driver[1].toLowerCase()}`:root.toLowerCase();await json(`/dataset/${d.session_id}/metadata`,{name:pair.dir,acquisition:group});setSelected(d.session_id);setModel(null);setSimulation(null);setMessage(`Imported ${pair.dir}. Choose Test to run a saved model.`)}await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function saveIdentity(r){setBusy(true);setError('');try{await json(`/dataset/${r.session_id}/metadata`,{name:names[r.session_id]??r.name,acquisition:groups[r.session_id]??r.acquisition});await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function start(){setBusy(true);setError('');try{
  const assignments=records.filter(r=>assign[r.session_id]).map(r=>({session_id:r.session_id,role:assign[r.session_id]}));
  const payload={session_id:selected||null,mode:parent?'continue':'create',name,kind,window:Number(window),epochs:Number(epochs),n_estimators:60,replay:true,assignments,parent_id:parent||null};
  const j=await json('/pipeline/train',payload);setJobId(j.job_id);setMessage(`Queued ${j.job_id}`);await refresh();
 }catch(e){setError(e.message)}finally{setBusy(false)}}
 async function control(action){setBusy(true);setError('');try{await json(`/jobs/${job.job_id}/${action}`,{});await refresh()}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function attach(mid=model?.model_id){setBusy(true);setError('');try{if(!selected||!mid)throw Error('Select a recording and saved model.');const m=await json('/models/attach',{session_id:selected,model_id:mid});setModel(m);setSimulation(null);setBenchmark(null);setMessage(`Activated ${mid}`)}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function inference(){setBusy(true);setError('');try{
  if(!selected||!model)throw Error('Select a recording and activate a saved model first.');
  const start=Number(blackoutStart),end=start+Number(blackoutDuration);
  if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)throw Error('Enter a valid blackout start and positive duration.');
  const result=await json('/pipeline/simulate',{session_id:selected,blackout_start_s:start,blackout_end_s:end,estimator,split:model.evaluation_roles?.includes('test')?'test':'exploration'});
  setSimulation(result);onNavigate('Replay');setMessage(`Inference complete: ${fmt(result.metrics.fused_drift_pct)}% endpoint drift. See Results for the three trajectories.`);
 }catch(e){setError(e.message)}finally{setBusy(false)}}
 async function benchmarkTest(){setBusy(true);setError('');try{
  if(!selected||!model?.evaluation_roles?.includes('test'))throw Error('Activate the saved model on its held-out Test recording first.');
  const result=await json('/pipeline/benchmark',{session_id:selected,estimator});setBenchmark(result);onNavigate('Replay');
  setMessage(`Benchmark: ${result.eligible_runs} eligible trials, ${(100*(result.pass_rate||0)).toFixed(0)}% pass fraction. Result saved by backend.`);
 }catch(e){setError(e.message)}finally{setBusy(false)}}
 const chooseRecording=id=>{setSelected(id);setModel(null);setSimulation(null);setBenchmark(null)};
 const current=records.find(r=>r.session_id===selected);
 const filtered=records.filter(r=>(r.name||'').toLowerCase().includes(search.toLowerCase()));
 const panel='bg-recess border border-hairline rounded-xl p-4 md:p-5';
 return <ScreenShell eyebrow="RECORDED NAVIGATION WORKSPACE" title={page==='Data'?'Your recordings':page==='Train'?'Train a model':'Test a recording'} right={<span>{active?'● TRAINING':'○ READY'}</span>}>
 <p className="text-dust text-sm mb-5">{page==='Data'?'Upload your smartphone and VBOX files, then choose a recording.':page==='Train'?'Create a model or continue learning from a saved version.':'Choose your data and model, set a blackout, then view the route comparison.'}</p>
 <div className="workflow mb-5">{[['Data','1','Add data'],['Test','2','Run a test'],['Replay','3','View results']].map(([id,n,label])=><button key={id} onClick={()=>onNavigate(id)} aria-current={page===id?'step':undefined} className={page===id?'current':''}><span>{n}</span>{label}</button>)}</div>
 {error&&<p role="alert" className="p-3 mb-3 border border-blackout rounded-xl">{error}</p>}
 {message&&<p role="status" className="mb-3 text-route text-sm">{message}</p>}
 {busy&&<p role="status" className="text-dust mb-3">Working… please wait.</p>}
 <div hidden={page!=='Data'}>
 <section className={panel}><h2 className="text-lg font-semibold">Add a recording</h2><p className="text-sm text-dust mt-1">Select both files together, for example S-S1.csv and V-S1.csv, or choose their extracted folder.</p>
 <div className="flex flex-wrap gap-3 mt-4"><label className="secondary-action cursor-pointer">Choose CSV pairs<input className="sr-only" type="file" multiple accept=".csv,.gz" disabled={busy} onChange={e=>{upload(e.target.files);e.target.value=''}}/></label><label className="secondary-action cursor-pointer">Choose extracted folder<input className="sr-only" type="file" multiple webkitdirectory="" directory="" disabled={busy} onChange={e=>{upload(e.target.files);e.target.value=''}}/></label></div></section>
 <section className={`${panel} mt-4`}><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">Saved recordings · {records.length}</h2><input aria-label="Search recordings" placeholder="Search recordings…" className="bg-panel p-3 rounded-xl" value={search} onChange={e=>setSearch(e.target.value)}/></div>
 {!records.length&&<p className="text-dust py-6">No recordings yet. Upload a CSV pair above to begin.</p>}
 {records.length>0&&!filtered.length&&<p className="text-dust py-6">No matching recordings.</p>}
 <div className="grid md:grid-cols-2 gap-3 mt-4">{filtered.map(r=><div key={r.session_id} className={`border rounded-xl p-4 ${selected===r.session_id?'border-route':'border-hairline'}`}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="font-semibold break-words">{r.name}</h3><p className="text-xs text-dust mt-1">{r.report?.samples?`${r.report.samples.toLocaleString()} samples`:'Saved recording'}</p></div><button disabled={busy} onClick={()=>{chooseRecording(r.session_id);onNavigate('Test')}} className="secondary-action shrink-0">Test this</button></div>
 <details className="mt-3"><summary>Training role & recording details</summary><p className="text-xs text-dust my-3">Clips from the same drive must share an acquisition group. Keep validation and test data out of training.</p><label className="field-label">Recording name<input value={names[r.session_id]??r.name} onChange={e=>setNames({...names,[r.session_id]:e.target.value})}/></label><label className="field-label">Acquisition group<input value={groups[r.session_id]??r.acquisition??''} onChange={e=>setGroups({...groups,[r.session_id]:e.target.value})}/></label><button disabled={busy} className="secondary-action my-2" onClick={()=>saveIdentity(r)}>Save details</button><label className="field-label">Training role<select value={assign[r.session_id]||''} onChange={e=>setAssign({...assign,[r.session_id]:e.target.value})}><option value="">Unassigned</option><option value="train">Train</option><option value="validation">Validation</option><option value="test">Test</option></select></label></details></div>)}</div></section></div>
 <div hidden={page!=='Test'} className="space-y-4">
 <section className={panel}><h2 className="text-lg font-semibold mb-4">1. Choose data & model</h2><div className="grid md:grid-cols-2 gap-4"><label className="field-label">Recording<select disabled={busy} value={selected||''} onChange={e=>chooseRecording(e.target.value)}><option value="" disabled>Select a recording</option>{records.map(r=><option value={r.session_id} key={r.session_id}>{r.name}</option>)}</select></label><label className="field-label">Saved model<select disabled={busy||!selected} value={model?.model_id||''} onChange={e=>attach(e.target.value)}><option value="" disabled>Select a saved model</option>{models.map(m=><option key={m.model_id} value={m.model_id}>{m.family_name||m.kind} · v{m.version||1}</option>)}</select></label></div>
 {!records.length&&<button className="secondary-action mt-3" onClick={()=>onNavigate('Data')}>Add your first recording</button>}{!models.length&&<button className="secondary-action mt-3" onClick={()=>onNavigate('Train')}>Create your first model</button>}
 </section>
 <section className={panel}><h2 className="text-lg font-semibold mb-2">2. Set the GNSS blackout</h2><p className="text-sm text-dust mb-4">This simulates losing the phone’s satellite signal. VBOX stays the independent reference.</p><div className="grid md:grid-cols-2 gap-4"><label className="field-label">Start at (seconds)<input type="number" min="10" value={blackoutStart} onChange={e=>setBlackoutStart(e.target.value)}/></label><label className="field-label">Duration (seconds)<input type="number" min="1" value={blackoutDuration} onChange={e=>setBlackoutDuration(e.target.value)}/></label></div>
 <div className="flex items-center gap-2 mt-3 text-xs text-dust">Duration:{[10,30,60].map(n=><button aria-pressed={Number(blackoutDuration)===n} className={`secondary-action ${Number(blackoutDuration)===n?'text-route border-route':''}`} key={n} onClick={()=>setBlackoutDuration(n)}>{n}s</button>)}</div><p className="text-xs text-dust mt-3">Allow at least 120 seconds before the blackout for calibration when possible. The interval must fit inside the recording without crossing a gap.</p>
 <details className="mt-4"><summary>Advanced test settings</summary><label className="field-label mt-3">Navigation estimator<select value={estimator} onChange={e=>setEstimator(e.target.value)}><option value="vehicle">Calibrated vehicle + learned speed</option><option value="legacy">Planar ESKF comparison</option></select></label><p className="text-xs text-dust my-3">The multi-interval benchmark requires a recording held out as Test in this model’s saved split.</p><button disabled={busy||!model?.evaluation_roles?.includes('test')} onClick={benchmarkTest} className="secondary-action">Benchmark 10 / 30 / 60 s</button></details></section>
 <section className={`${panel} flex flex-wrap items-center justify-between gap-4`}><div><p className="font-semibold">Ready to compare three trajectories?</p><p className="text-xs text-dust mt-1">{!selected?'Choose a recording first.':!model?'Choose a saved model to enable testing.':`${current?.name||'Recording'} · ${model.evaluation_roles?.includes('test')?'Held-out test':'Exploration'}`}</p></div><button disabled={busy||!selected||!model} onClick={inference} className="primary-action"><Play size={16}/>{busy?'Working…':'Run test & view results'}</button></section>
 {benchmark&&<p className="text-sm text-dust">Benchmark: {benchmark.under_50_count} / {benchmark.eligible_runs} eligible trials below 50% · median {fmt(benchmark.median_drift_pct)}% · worst {fmt(benchmark.worst_drift_pct)}%.</p>}
 </div>
 <div hidden={page!=='Train'}><section className={panel}><div className="flex flex-wrap gap-3 items-center justify-between mb-4"><h2 className="text-lg font-semibold">Training setup</h2><button className="secondary-action" onClick={()=>onNavigate('Data')}>Manage training data</button></div><div className="flex gap-4 flex-wrap text-xs text-dust mb-4">{[['train','Train'],['validation','Validation'],['test','Test']].map(([role,label])=><span key={role}>{label}: {records.filter(r=>assign[r.session_id]===role).length}</span>)}</div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
     <label className="text-xs">Architecture<select className="w-full bg-panel p-2" disabled={!!parent||!!active} value={kind} onChange={e=>setKind(e.target.value)}>{[['cnn_gru','CNN + GRU'],['tcn','Causal TCN'],['extra_trees','Extra Trees'],['random_forest','Random Forest']].map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>
     <label className="text-xs">Window samples<input className="w-full bg-panel p-2" type="number" min="10" max="100" value={window} disabled={!!parent||!!active} onChange={e=>setWindow(e.target.value)}/></label>
     <label className="text-xs">Epochs<input className="w-full bg-panel p-2" type="number" min="1" max="100" value={epochs} onChange={e=>setEpochs(e.target.value)}/></label>
     <label className="text-xs">Model name<input className="w-full bg-panel p-2" value={name} onChange={e=>setName(e.target.value)}/></label>
    </div>
    <label className="text-xs">Start from<select className="w-full bg-panel p-2 mb-3" value={parent} onChange={e=>{setParent(e.target.value);const m=models.find(x=>x.model_id===e.target.value);if(m){setKind(m.kind);setWindow(m.window);setName(m.family_name||m.kind)}}}><option value="">Create a new model</option>{models.map(m=><option key={m.model_id} value={m.model_id}>{m.family_name||m.kind} v{m.version||1} ({m.model_id.slice(0,7)})</option>)}</select></label>
    <div className="font-mono text-[13px] leading-relaxed text-ivory space-y-1">
     <div className="flex justify-between"><span className="text-dust">epoch</span><span>{job?.epoch??'—'} / {job?.plan?.epochs??'—'}</span></div>
     <div className="flex justify-between"><span className="text-dust">training loss</span><span className="text-route">{fmt(job?.history?.at(-1)?.loss)}</span></div>
     <div className="flex justify-between"><span className="text-dust">validation MAE</span><span>{fmt(job?.history?.at(-1)?.validation_mae)} m/s</span></div>
     <div className="flex justify-between"><span className="text-dust">validation RMSE</span><span>{fmt(job?.result?.validation?.rmse)} m/s</span></div>
     <div className="flex justify-between"><span className="text-dust">status</span><span>{job?.status?.toUpperCase()||'NO RUN'}</span></div>
    </div>
    <div className="h-1.5 bg-ink mt-4 rounded-xl overflow-hidden"><div className="h-full bg-route" style={{width:`${Math.max(0,Math.min(100,(job?.progress||0)*100))}%`}}/></div>
<div className="flex flex-wrap gap-2 mt-4"><button disabled={busy||!!active||!Object.values(assign).includes('train')} onClick={start} className="primary-action"><Play size={16}/>{parent?'Continue training':'Train & save'}</button>
{job&&['running','queued'].includes(job.status)&&<button disabled={busy} onClick={()=>control('pause')} className="secondary-action">Pause training</button>}
{job&&['interrupted','paused','failed'].includes(job.status)&&<button disabled={busy} onClick={()=>control('resume')} className="secondary-action">Resume interrupted run</button>}</div>
<p className="text-xs text-dust mt-3">{job?.message||'Assign separate recordings to Train, Validation and Test on the Data page first.'}</p>
<p className="text-xs text-dust mt-3">Continued training replays earlier training recordings automatically. Keep the same validation and test groups.</p>
</section><details className={`${panel} mt-4`}><summary>Saved model versions · {models.length}</summary><div className="space-y-3 mt-3">{models.map(m=><div key={m.model_id} className="border-b border-hairline py-2"><p>{m.family_name||m.kind} · version {m.version||1}</p><p className="text-xs text-dust">Validation speed error: {fmt(m.validation?.mae)} m/s · {m.model_id}</p></div>)}</div></details></div>
 </ScreenShell>;
}
