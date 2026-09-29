import React,{useState} from 'react';
export default function MetricPlot({title,t=[],series=[],unit='m',note='',blackout}){
 const [hidden,setHidden]=useState({});
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const values=series.filter(s=>!hidden[s.key]).flatMap(s=>s.values||[]).filter(finite);
 if(!t.length)return <section className="result-panel"><h3>{title}</h3><p className="text-dust text-sm mt-3">Not available for this result. Run a new test with the updated backend.</p></section>;
 const low=Math.min(0,...values),high=Math.max(low+1,...values),start=t[0],end=t.at(-1);
 const X=v=>55+470*(v-start)/Math.max(.001,end-start),Y=v=>175-140*(v-low)/(high-low);
 return <section className="result-panel"><h3 className="font-semibold">{title}</h3><svg viewBox="0 0 550 220" className="w-full" role="img" aria-label={title}>
 {blackout&&<rect x={X(Math.max(start,blackout[0]))} y="30" width={Math.max(0,X(Math.min(end,blackout[1]))-X(Math.max(start,blackout[0])))} height="145" fill="#E6B800" opacity=".08"/>}
 {[0,.5,1].map(f=><g key={f}><line x1="55" x2="525" y1={Y(low+f*(high-low))} y2={Y(low+f*(high-low))} stroke="#5C6E60" strokeOpacity=".4"/><text x="50" y={Y(low+f*(high-low))+4} textAnchor="end" fontSize="10" fill="#A8B5A0">{(low+f*(high-low)).toFixed(1)}</text></g>)}
 {series.filter(s=>!hidden[s.key]).map(s=>{let pen=false,path='';(s.values||[]).forEach((v,i)=>{if(!finite(v)||!finite(t[i])){pen=false;return;}path+=`${pen?'L':'M'}${X(t[i]).toFixed(2)},${Y(v).toFixed(2)} `;pen=true});return <path key={s.key} d={path} fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dash}/>})}
 <text x="55" y="197" fill="#A8B5A0" fontSize="10">{start.toFixed(1)} s</text><text x="525" y="197" textAnchor="end" fill="#A8B5A0" fontSize="10">{end.toFixed(1)} s</text><text x="290" y="215" textAnchor="middle" fill="#A8B5A0" fontSize="10">Recording time (seconds) · {unit}</text></svg>
 <div className="flex flex-wrap gap-3 text-xs">{series.map(s=><label key={s.key} className="flex gap-1 items-center"><input type="checkbox" checked={!hidden[s.key]} onChange={()=>setHidden({...hidden,[s.key]:!hidden[s.key]})}/><span style={{color:s.color}}>{s.label}</span></label>)}</div><p className="text-xs text-dust mt-3">{note}</p></section>;
}
