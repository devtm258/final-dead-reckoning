import React from 'react';
import Brand from './Brand';
export default function ScreenShell({ eyebrow, title, children, right }) {
  return <div className="min-h-dvh bg-ink text-ivory pb-28">
    <div className="max-w-6xl mx-auto px-5 md:px-10">
      <header className="h-20 flex items-center justify-between border-b border-hairline">
        <Brand />
        <div className="flex items-center gap-2 text-[10px] font-mono tracking-widest text-dust">{right || <><span className="inline-block h-1.5 w-1.5 bg-gnss" /> SIMULATOR ONLINE</>}</div>
      </header>
      <div className="pt-7 pb-6">
        <p className="hud-label mb-2" style={{ color: '#E6B800' }}>{eyebrow}</p>
        <h1 className="font-display font-medium text-4xl md:text-5xl tracking-wide">{title}</h1>
      </div>
      {children}
    </div>
  </div>;
}