import React from 'react';
export default function EnginePanel({ index, title, status, children }) {
  return <section className="bg-recess border border-hairline rounded-xl overflow-hidden">
    <div className="border-b border-hairline px-4 py-3 flex justify-between items-center">
      <div className="flex items-center gap-2.5"><span className="font-mono text-[10px] text-route">0{index}</span><h2 className="font-sans font-semibold text-sm text-ivory">{title}</h2></div>
      <span className="font-mono text-[9px] flex items-center gap-1" style={{ color: '#4A5C2E' }}><i className="inline-block w-1.5 h-1.5 bg-match" />{status}</span>
    </div>
    <div className="p-4">{children}</div>
  </section>;
}