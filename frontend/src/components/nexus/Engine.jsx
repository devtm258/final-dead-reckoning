import React from 'react';
import ScreenShell from './ScreenShell';
import EnginePanel from './EnginePanel';
const fmt=(n,d=2)=>n==null?'—':Number(n).toFixed(d);
export default function Engine({model,simulation}){
 const m=simulation?.metrics;
 return <ScreenShell eyebrow="02 / DIAGNOSTICS" title="Engine diagnostics" right={<span className="text-route">{m?'● RECORDED REPLAY':'○ NO REPLAY'}</span>}>
 <div className="grid md:grid-cols-2 gap-4">
  <EnginePanel index="1" title="Alignment & calibration" status={m?'MEASURED':'PENDING'}><div className="hud-label">GNSS prefix, phone IMU only</div><p className="mt-3 text-sm">Heading RMSE: {fmt(m?.heading_rmse_deg)}° · {m?.heading_reference_samples??'—'} reference samples</p><p className="text-xs text-dust mt-2">{m?.heading_calibration?.warnings?.join(' ')||'Run inference on a paired recording for calibration diagnostics.'}</p></EnginePanel>
  <EnginePanel index="2" title="AI speed & vibration filter" status={model?'SAVED MODEL':'NONE'}><div className="font-display text-3xl">{model?.family_name||model?.kind||'—'}</div><p className="text-xs text-dust">Validation MAE {fmt(model?.validation?.mae,3)} m/s · flagged samples {m?.quality_flagged_samples??'—'}</p></EnginePanel>
  <EnginePanel index="3" title="Map match & constraints" status="FILTER NHC"><p className="text-sm">Adaptive nonholonomic constraint and conservative stationary updates are applied in the replay filter.</p><p className="text-xs text-dust mt-3">Offline road matching requires a supplied road GeoJSON and is a diagnostic path, not a fused or independently scored constraint.</p></EnginePanel>
  <EnginePanel index="4" title="GNSS + INS fusion" status={m?'EVALUATED':'PENDING'}><div className="flex gap-4"><div className="bg-panel p-3 rounded-xl"><div className="hud-label">FUSED ENDPOINT</div><div className="font-display text-3xl">{fmt(m?.fused_final_drift_m)} m</div></div><div className="bg-panel p-3 rounded-xl"><div className="hud-label">INS BASELINE</div><div className="font-display text-3xl">{fmt(m?.ins_final_drift_m)} m</div></div></div><p className="text-xs mt-3">Eligible: {m?String(m.benchmark_eligible):'—'} · Target pass: {m?String(m.meets_isro_target):'—'}</p></EnginePanel>
 </div>
 {m&&<div className="mt-4 bg-land text-ink p-4 rounded-xl"><h2 className="font-semibold">Measured drift</h2><p>{fmt(m.fused_drift_pct)}% endpoint / {fmt(m.ins_drift_pct)}% baseline · {fmt(m.blackout_distance_m)} m reference distance · {fmt(m.blackout_duration_s,0)} s blackout</p></div>}
 </ScreenShell>
}
