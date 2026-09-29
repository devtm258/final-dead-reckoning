import React from 'react';
const S = ({ size = 18, className = '', children, fill = 'none', stroke = true }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke ? 'currentColor' : 'none'} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">{children}</svg>
);
export const Align = (p) => <S {...p}><circle cx="12" cy="12" r="9" /><path d="M12 3v18M3 12h18" /><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" /></S>;
export const NavIcon = (p) => <S {...p}><path d="M12 2 19 21 12 17 5 21Z" /></S>;
export const Gauge = (p) => <S {...p}><path d="M12 20a8 8 0 1 1 8-8" /><path d="M12 12l4-4" /></S>;
export const ReplayIcon = (p) => <S {...p}><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 3v4h4" /></S>;
export const More = (p) => <S {...p}><circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" /><circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none" /></S>;
export const Check = (p) => <S {...p}><path d="M4 12l5 5L20 6" /></S>;
export const Alert = (p) => <S {...p}><path d="M12 3 22 20H2Z" /><path d="M12 10v5M12 18v.5" /></S>;
export const Satellite = (p) => <S {...p}><path d="M5 5l3 3M16 16l3 3M9 9l6 6" /><circle cx="12" cy="12" r="2.4" /><path d="M2 12h2M20 12h2M12 2v2M12 20v2" /></S>;
export const Radio = (p) => <S {...p}><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" /><path d="M7.5 7.5a6.5 6.5 0 0 0 0 9M16.5 7.5a6.5 6.5 0 0 1 0 9M4.5 4.5a11 11 0 0 0 0 15M19.5 4.5a11 11 0 0 1 0 15" /></S>;
export const Crosshair = (p) => <S {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 1v5M12 18v5M1 12h5M18 12h5" /><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" /></S>;
export const ChevronUp = (p) => <S {...p}><path d="M6 15l6-6 6 6" /></S>;
export const ChevronDown = (p) => <S {...p}><path d="M6 9l6 6 6-6" /></S>;
export const Locate = (p) => <S {...p}><circle cx="12" cy="12" r="2.6" /><path d="M12 2v4M12 18v4M2 12h4M18 12h4" /></S>;
export const Layers = (p) => <S {...p}><path d="M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5" /></S>;
export const Bolt = (p) => <S {...p} fill="currentColor" stroke={false}><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" /></S>;
export const Rotate = (p) => <S {...p}><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 3v4h4" /></S>;
export const ChevronRight = (p) => <S {...p}><path d="M9 6l6 6-6 6" /></S>;
export const Activity = (p) => <S {...p}><path d="M3 12h4l3 8 4-16 3 8h4" /></S>;
export const Shield = (p) => <S {...p}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" /></S>;
export const Play = (p) => <S {...p} fill="currentColor" stroke={false}><path d="M6 4l14 8-14 8z" /></S>;
export const Pause = (p) => <S {...p} fill="currentColor" stroke={false}><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></S>;
export const MapIcon = (p) => <S {...p}><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14" /></S>;
export const Phone = (p) => <S {...p}><rect x="7" y="2" width="10" height="20" rx="1" /><path d="M11 18h2" /></S>;
export const Compass = (p) => <S {...p}><circle cx="12" cy="12" r="9" /><path d="M15 9l-2 6-4 2 2-6 4-2z" fill="currentColor" stroke="none" /></S>;
export const Grid = (p) => <S {...p}><rect x="3" y="3" width="8" height="8" rx="1" /><rect x="13" y="3" width="8" height="8" rx="1" /><rect x="3" y="13" width="8" height="8" rx="1" /><rect x="13" y="13" width="8" height="8" rx="1" /></S>;