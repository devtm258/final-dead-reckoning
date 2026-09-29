import React,{useState} from 'react';
const palette={gps:'#3D3D3D',baseline:'#C62828',fused:'#E6B800',ml:'#3979AD'};
export default function SeriesPlot({simulation,kind}){
 const [hidden,setHidden]=useState({ml:true});
 const speed=kind==='speed',source=speed?simulation.velocity_series:simulation.error_series;
 if(!source?.t?.length)return null;
 const t=source.t,series=speed?{gps:source.gps,baseline:source.baseline,fused:source.fused,ml:source.ml}:{baseline:source.baseline_m,fused:source.position_m};
 const labels={gps:'VBOX reference',baseline:'Inertial baseline',fused:'AI-aided navigation',ml:'Raw learned speed'};
 const values=Object.entries(series).filter(([k])=>!hidden[k]).flatMap(([,v])=>v||[]).filter(Number.isFinite);
 const min=Math.min(0,...values),max=Math.max(1,...values),a=t[0],b=t.at(-1);
 const X=v=>45+450*(v-a)/Math.max(.1,b-a),Y=v=>175-140*(v-min)/Math.max(1,max-min);
 const bs=Math.max(a,simulation.metrics.blackout_start_s),be=Math.min(b,simulation.metrics.blackout_end_s);
 return <section className="border border-hairline rounded-xl p-3 bg-land text-ink"><h3 className="text-sm font-semibold">{speed?'Speed (m/s)':'Position error (m)'}</h3>
 <svg viewBox="0 0 520 210" className="w-full" role="img" aria-label={speed?'Three speed estimates and optional raw learned speed':'Baseline and aided position error against VBOX'}>
  <rect x={X(bs)} y="30" width={Math.max(0,X(be)-X(bs))} height="145" fill="#C62828" opacity=".09"/>
  {[0,.5,1].map(f=><g key={f}><line x1="45" x2="495" y1={Y(min+f*(max-min))} y2={Y(min+f*(max-min))} stroke="#888" strokeOpacity=".4"/><text x="40" y={Y(min+f*(max-min))+4} textAnchor="end" fontSize="10">{(min+f*(max-min)).toFixed(1)}</text></g>)}
  {Object.entries(series).filter(([k,v])=>!hidden[k]&&v).map(([k,v])=>{
   let path='',pen=false;v.forEach((y,i)=>{if(!Number.isFinite(y)){pen=false;return;}path+=`${pen?'L':'M'}${X(t[i]).toFixed(2)},${Y(y).toFixed(2)} `;pen=true});
   return <path key={k} d={path} fill="none" stroke={palette[k]} strokeWidth="2" strokeDasharray={k==='baseline'?'5 4':undefined}/>;
  })}
  <text x="45" y="195" fontSize="10">{a.toFixed(1)} s</text><text x="495" y="195" fontSize="10" textAnchor="end">{b.toFixed(1)} s</text>
 </svg>
 <div className="flex flex-wrap gap-2 text-xs">{Object.keys(series).map(k=><label key={k}><input type="checkbox" checked={!hidden[k]} onChange={()=>setHidden({...hidden,[k]:!hidden[k]})}/><span style={{color:palette[k]}}> {labels[k]}</span></label>)}</div><p className="text-xs mt-2">Shaded interval: simulated blackout.</p></section>
}
