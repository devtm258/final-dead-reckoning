import React,{useEffect,useRef,useState} from 'react';
import 'leaflet/dist/leaflet.css';
const styles={ground_truth:{color:'#6F9D90',weight:3},ins_raw:{color:'#E16A63',weight:3,dashArray:'7 5'},fused:{color:'#E6B800',weight:4},matched:{color:'#3478bd',weight:3,dashArray:'3 6'}};
const labels={ground_truth:'VBOX reference',ins_raw:'Baseline dead reckoning',fused:'AI-aided navigation',matched:'Road-matched diagnostic'};
export default function RouteMap({simulation,matched,progress=100}){
 const el=useRef(null),mapRef=useRef(null),groups=useRef({}),cursor=useRef(null),fit=useRef(null);
 const [hidden,setHidden]=useState({}),[tiles,setTiles]=useState(true),[error,setError]=useState('');
 useEffect(()=>{let disposed=false;setError('');
 import('leaflet').then(module=>{if(disposed)return;const L=module.default||module;
 const map=L.map(el.current,{scrollWheelZoom:false,attributionControl:true});mapRef.current=map;
 if(tiles)L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).on('tileerror',()=>{if(!disposed)setError('Map tiles could not load. Trajectories still work; switch off the background for an offline view.')}).addTo(map);
 const traces={...simulation.trajectories,...(matched?{matched:matched.trajectory}:{})},all=[];
 groups.current={};
 Object.entries(traces).forEach(([key,points])=>{if(!styles[key])return;let parts=[],part=[];
 points.forEach((p,i)=>{const valid=Array.isArray(p)&&p.every(Number.isFinite)&&(key!=='ground_truth'||simulation.reference_valid?.[i]!==false);if(valid){part.push(p);all.push(p)}else if(part.length){parts.push(part);part=[]}});if(part.length)parts.push(part);
 const layer=L.layerGroup(parts.flatMap(p=>key==='fused'?[L.polyline(p,{color:'#172B22',weight:6}),L.polyline(p,styles[key])]:[L.polyline(p,styles[key])]));groups.current[key]=layer;if(!hidden[key])layer.addTo(map);});
 if(all.length){fit.current=()=>map.fitBounds(L.latLngBounds(all),{padding:[25,25],maxZoom:17});fit.current()}else map.setView([0,0],2);
 const indices=simulation.blackout_indices||[];
 indices.forEach((i,j)=>{const p=simulation.trajectories?.fused?.[i];if(p?.every(Number.isFinite))L.circleMarker(p,{radius:7,color:j?'#C62828':'#267844',fillOpacity:1}).bindTooltip(j?'Blackout end (AI position)':'Blackout start (AI position)',{direction:j?'bottom':'top'}).addTo(map)});
 const path=simulation.trajectories?.fused||[];const p=path[Math.round((path.length-1)*progress/100)];if(p?.every(Number.isFinite))cursor.current=L.circleMarker(p,{radius:6,color:'#fff',fillColor:'#E6B800',fillOpacity:1}).bindTooltip('AI vehicle position').addTo(map);
 }).catch(e=>{if(!disposed)setError('Interactive map unavailable: '+e.message)});
 return()=>{disposed=true;mapRef.current?.remove();mapRef.current=null;groups.current={};cursor.current=null};
 },[simulation,matched,tiles]);
 useEffect(()=>{const map=mapRef.current;if(!map)return;Object.entries(groups.current).forEach(([key,layer])=>{if(hidden[key])map.removeLayer(layer);else layer.addTo(map)})},[hidden]);
 useEffect(()=>{const path=simulation.trajectories?.fused||[],p=path[Math.round((path.length-1)*progress/100)];if(p?.every(Number.isFinite))cursor.current?.setLatLng(p)},[progress,simulation]);
 return <section className="result-panel"><div className="flex flex-wrap items-center justify-between gap-3 mb-3"><h2 className="font-semibold">Route comparison</h2><button className="secondary-action" onClick={()=>fit.current?.()}>Fit all routes</button></div><div className="flex flex-wrap gap-3 text-xs mb-3">{Object.keys(styles).filter(k=>k!=='matched'||matched).map(k=><label key={k}><input type="checkbox" checked={!hidden[k]} onChange={()=>setHidden({...hidden,[k]:!hidden[k]})}/> <span style={{color:styles[k].color}}>━</span> {labels[k]}</label>)}<label><input type="checkbox" checked={tiles} onChange={e=>setTiles(e.target.checked)}/> OpenStreetMap background</label></div>
 <div ref={el} className="route-map" aria-label="OpenStreetMap route comparison"/>{error&&<p role="status" className="text-xs text-dust mt-3">{error}</p>}<p className="text-xs text-dust mt-3">Green marker: blackout start; red marker: blackout end (AI positions). Hover or tap a marker for its label. Background tiles require internet; calculations and uploaded road geometry remain local. The map background does not snap or modify the estimates.</p></section>;
}
