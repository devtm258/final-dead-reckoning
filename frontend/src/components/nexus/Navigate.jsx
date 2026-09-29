import React from 'react';
import ScreenShell from './ScreenShell';
export default function Navigate(){return <ScreenShell eyebrow="02 / LIVE CAR NAVIGATION" title="Navigate" right={<span className="text-blackout">○ NO PHONE STREAM</span>}>
 <div className="bg-land text-ink border border-hairline rounded-xl h-[55vh] min-h-[340px] grid place-items-center text-center p-8"><div><div className="font-display text-4xl">POSITION UNAVAILABLE</div><p className="max-w-md text-sm mt-3">Connect a device IMU and GNSS adapter for actual live navigation. Training and recorded route replay remain available under Model Training.</p></div></div>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">{['SPEED','GNSS','HEADING','DRIFT'].map(label=><div key={label} className="bg-panel border border-hairline rounded-xl p-3"><div className="hud-label">{label}</div><div className="font-display text-2xl mt-1">—</div></div>)}</div>
 </ScreenShell>}
