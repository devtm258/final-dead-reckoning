import React,{useState} from 'react';
const COLORS={ground_truth:'#3D3D3D',ins_raw:'#C62828',fused:'#E6B800'};
export default function ReplayPlot({simulation,progress}){
 const [hidden,setHidden]=useState({});
 const traces=simulation?.trajectories;if(!traces)return <div className="bg-land border border-hairline rounded-xl h-[300px] grid place-items-center text-ink">Run a test to see the three route comparisons.</div>;
 const paths=Object.entries(traces).filter(([key])=>COLORS[key]&&!hidden[key]).map(([key,points])=>({key,points}));
 const coords=paths.flatMap(p=>p.points.filter(v=>v?.every(Number.isFinite)));
 if(!coords.length)return <button onClick={()=>setHidden({})}>Show route traces</button>;
 const minLon=Math.min(...coords.map(p=>p[1])),maxLon=Math.max(...coords.map(p=>p[1]));
 const minLat=Math.min(...coords.map(p=>p[0])),maxLat=Math.max(...coords.map(p=>p[0]));
 const lonFactor=Math.cos((minLat+maxLat)/2*Math.PI/180);
 const scale=Math.max((maxLon-minLon)*lonFactor/520,(maxLat-minLat)/245,1e-9);
 const toXY=p=>[(p[1]-minLon)*lonFactor/scale+35,275-(p[0]-minLat)/scale];
 const pos=traces.fused[Math.min(traces.fused.length-1,Math.floor((progress/100)*(traces.fused.length-1)))];
 return <div className="bg-land border border-hairline rounded-xl overflow-hidden"><div className="px-3 py-2 hud-label text-ink">PAIRED REFERENCE / POSITION TRACE</div><div className="flex gap-3 px-3 text-xs text-ink">{Object.keys(COLORS).map(k=><label key={k}><input type="checkbox" checked={!hidden[k]} onChange={()=>setHidden({...hidden,[k]:!hidden[k]})}/> {{ground_truth:"VBOX",ins_raw:"Baseline",fused:"AI-aided"}[k]}</label>)}</div><svg viewBox="0 0 590 300" preserveAspectRatio="xMidYMid meet" className="w-full h-[265px] md:h-[370px]" aria-label="Measured reference, inertial baseline and fused trajectories"><defs><pattern id="rpgrid" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="#3D5C45" strokeOpacity="0.35" strokeWidth="0.5"/></pattern></defs><rect width="590" height="300" fill="url(#rpgrid)"/>{paths.map(({key,points})=><polyline key={key} points={points.map(p=>toXY(p).join(',')).join(' ')} stroke={COLORS[key]} fill="none" strokeWidth={key==='fused'?3.5:2} strokeDasharray={key==='ins_raw'?'5 5':undefined}/>)}{pos&&<circle cx={toXY(pos)[0]} cy={toXY(pos)[1]} r="6" fill="#E6B800" stroke="#1A1A1A"/>}</svg></div>
}
