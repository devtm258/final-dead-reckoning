import React, { useEffect, useState } from 'react';
import Brand from './Brand';
const LINES = ['ALIGNING FRAME', 'IMU BIAS EST', 'MAP GRAPH WARM', 'FUSION READY'];
export default function Boot({ onDone }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (i >= LINES.length) { const t = setTimeout(onDone, 500); return () => clearTimeout(t); }
    const t = setTimeout(() => setI(i + 1), 600);
    return () => clearTimeout(t);
  }, [i, onDone]);
  return <div className="fixed inset-0 bg-ink text-ivory flex flex-col items-center justify-center px-6">
    <Brand large />
    <div className="w-56 h-px bg-hairline my-8" />
    <div className="w-72 space-y-2 font-mono text-[12px] text-dust">
      {LINES.map((l, idx) => <div key={l} className={`flex justify-between transition-opacity duration-200 ${idx <= i ? 'opacity-100' : 'opacity-0'}`}><span>{l}</span>{idx < i && <span style={{ color: '#3D5C45' }}>OK</span>}</div>)}
    </div>
    <button onClick={onDone} className="absolute bottom-8 right-6 min-h-[44px] px-4 text-[12px] text-dust border border-hairline rounded-xl">SKIP</button>
  </div>;
}