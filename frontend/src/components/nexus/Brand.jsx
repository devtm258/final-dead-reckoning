import React from 'react';
export default function Brand({ large = false }) {
  return <div className="flex items-center gap-2.5">
    <svg width={large ? 44 : 26} height={large ? 44 : 26} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="34" height="34" stroke="#1B3D2F" strokeWidth="1" />
      <path d="M20 8 L28 28 L20 23 L12 28 Z" fill="#E6B800" />
      <circle cx="20" cy="20" r="1.8" fill="#F5F0E6" />
    </svg>
    <div>
      <div className={`font-display font-medium tracking-[0.08em] leading-none text-ivory ${large ? 'text-4xl' : 'text-[22px]'}`}>IO-VNBD</div>
      {large && <div className="hud-mono mt-1">INERTIAL NAVIGATION SYSTEM</div>}
    </div>
  </div>;
}