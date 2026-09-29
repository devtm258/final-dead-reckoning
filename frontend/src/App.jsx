import React,{useState} from 'react';
import Boot from './components/nexus/Boot';
import Dock from './components/nexus/Dock';
import ModeSelect from './components/nexus/ModeSelect';
import Calibration from './components/nexus/Calibration';
import Navigate from './components/nexus/Navigate';
import Engine from './components/nexus/Engine';
import Train from './components/nexus/Train';
import Replay from './components/nexus/Replay';
import Settings from './components/nexus/Settings';
export default function App(){
 const [boot,setBoot]=useState(false),[mode,setMode]=useState('train'),[tab,setTab]=useState('Data');
 const [selected,setSelected]=useState(null),[model,setModel]=useState(null),[simulation,setSimulation]=useState(null),[benchmark,setBenchmark]=useState(null);
 const switchMode=()=>{setMode(null);setTab('Align')};
 if(boot)return <Boot onDone={()=>setBoot(false)}/>;
 if(!mode)return <ModeSelect onChoose={m=>{setMode(m);setTab(m==='live'?'Align':'Data')}}/>;
 const common={selected,setSelected,model,setModel,simulation,setSimulation,benchmark,setBenchmark};
 return <div className="font-body bg-ink text-ivory selection:bg-route/40 min-h-dvh">
  {mode==='live'&&tab==='Align'&&<Calibration onStart={()=>setTab('Navigate')}/>}
  {mode==='live'&&tab==='Navigate'&&<Navigate/>}
  {mode==='train'&&<div hidden={!['Data','Test','Train'].includes(tab)}><Train {...common} page={tab} onNavigate={setTab}/></div>}
  {mode==='train'&&tab==='Diagnostics'&&<Engine {...common}/>}
  {tab==='Replay'&&<Replay {...common} onTest={()=>setTab(mode==='train'?'Test':'Navigate')}/>}
  {tab==='More'&&<Settings onSwitchMode={switchMode} onDiagnostics={()=>setTab('Diagnostics')}/>}
  <Dock mode={mode} tab={tab} setTab={setTab} onSwitchMode={switchMode}/>
 </div>;
}
