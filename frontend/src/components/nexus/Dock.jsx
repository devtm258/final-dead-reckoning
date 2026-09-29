import React from 'react';
import { Align, NavIcon, Gauge, Activity, ReplayIcon, More, Grid } from './Icons';
const MODE_TAB = { id: 'Mode', label: 'Mode', Icon: Grid, switch: true };
const LIVE = [
  { id: 'Align', label: 'Align', Icon: Align },
  { id: 'Navigate', label: 'Navigate', Icon: NavIcon },
  { id: 'Replay', label: 'Replay', Icon: ReplayIcon },
  { id: 'More', label: 'More', Icon: More },
  MODE_TAB,
];
const TRAIN = [
 {id:'Data',label:'Data',Icon:Grid},
 {id:'Test',label:'Test',Icon:NavIcon},
 {id:'Replay',label:'Results',Icon:ReplayIcon},
 {id:'Train',label:'Train',Icon:Gauge},
 {id:'More',label:'More',Icon:More},
];
export default function Dock({ mode, tab, setTab, onSwitchMode }) {
  const TABS = mode === 'train' ? TRAIN : LIVE;
  return <nav className="fixed bottom-0 left-0 right-0 z-40 bg-ink border-t border-hairline">
    <div className="max-w-[1600px] mx-auto grid" style={{ gridTemplateColumns: `repeat(${TABS.length}, minmax(0, 1fr))` }}>
      {TABS.map(({ id, label, Icon, switch: isSwitch }) => { const active = tab === id;
        return <button aria-current={active?'page':undefined} key={id} onClick={() => isSwitch ? onSwitchMode() : setTab(id)} className="relative min-h-[56px] flex flex-col items-center justify-center gap-1 py-2">
          {active && <span className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-[2px] bg-route" />}
          <Icon size={20} className={active ? 'text-ivory' : 'text-quiet'} />
          <span className={`text-[11px] font-sans ${active ? 'text-ivory' : 'text-quiet'}`}>{label}</span>
        </button>;
      })}
    </div>
  </nav>;
}