import React, { useState } from 'react';
import Brand from './Brand';
import { Check } from './Icons';
const CARDS = [
  { id: 'live', title: 'LIVE CAR NAVIGATION', sub: 'Phone sensor adapter required · live state unavailable', tag: 'DEVICE WORKSPACE' },
  { id: 'train', title: 'MODEL TRAINING', sub: 'IO-VNBD inference · train / val / test · position plots · engine diagnostics', tag: 'WORKSPACE' },
];
export default function ModeSelect({ onChoose }) {
  const [sel, setSel] = useState(null);
  return <div className="min-h-dvh bg-ink text-ivory flex flex-col">
    <div className="flex-1 flex flex-col items-center justify-center px-5 py-12">
      <Brand large />
      <p className="font-sans text-dust mt-4 text-center max-w-md">Research workspace for GNSS-denied navigation.</p>
      <div className="w-full max-w-3xl mt-10 grid md:grid-cols-2 gap-4">
        {CARDS.map(c => { const active = sel === c.id;
          return <button key={c.id} onClick={() => setSel(c.id)} className={`text-left p-5 rounded-xl min-h-[190px] flex flex-col justify-between border transition-colors duration-150 ${active ? 'border-route bg-panel' : 'border-hairline bg-panel/60'}`}>
            <div className="flex justify-between items-start">
              <span className="hud-label" style={{ color: active ? '#E6B800' : '#A8B5A0' }}>{c.tag}</span>
              {active && <span className="w-5 h-5 rounded-xl bg-route grid place-items-center"><Check size={13} className="text-ink" /></span>}
            </div>
            <div>
              <h2 className="font-display text-3xl tracking-wide text-ivory leading-none">{c.title}</h2>
              <p className="font-sans text-[13px] text-dust mt-2 leading-snug">{c.sub}</p>
            </div>
          </button>;
        })}
      </div>
      <button disabled={!sel} onClick={() => onChoose(sel)} className="mt-8 min-h-[52px] px-8 bg-route text-ink font-sans font-semibold text-[14px] tracking-wide rounded-xl disabled:opacity-40">ENTER IO-VNBD</button>
    </div>
  </div>;
}
