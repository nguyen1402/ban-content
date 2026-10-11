import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const W = 1920;
const H = 1080;
const FONT = '"Segoe UI", Arial, sans-serif';

// props: {giay, tieu_de, don_vi, diem: [{nam, gia_tri, nhan?}]}
export const BieuDo = ({tieu_de = '', don_vi = '', diem = []}) => {
  const f = useCurrentFrame();
  const {durationInFrames: N} = useVideoConfig();
  const x0 = 220;
  const x1 = W - 160;
  const y0 = 880;
  const y1 = 260;
  const vmax = Math.max(1, ...diem.map((d) => d.gia_tri)) * 1.15;
  const n = diem.length;
  const bw = Math.min(180, ((x1 - x0) / Math.max(n, 1)) * 0.6);
  const gap = n > 1 ? (x1 - x0 - bw) / (n - 1) : 0;
  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg,#10243b,#1d3d5e)', fontFamily: FONT}}>
      <div style={{position: 'absolute', left: 80, top: 60, color: '#fff', fontSize: 64, fontWeight: 800}}>{tieu_de}</div>
      <div style={{position: 'absolute', left: 80, top: 150, color: '#9fc4e8', fontSize: 36}}>{don_vi}</div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <line x1={x0 - 30} y1={y0} x2={x1 + 40} y2={y0} stroke="rgba(255,255,255,0.5)" strokeWidth="3" />
        {diem.map((d, i) => {
          const ti = (i + 0.4) / (n + 0.4);
          const p = interpolate(f, [N * ti * 0.75, N * (ti * 0.75 + 0.2)], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
          });
          const h = (y0 - y1) * (d.gia_tri / vmax) * p;
          const x = x0 + i * gap;
          return (
            <g key={i}>
              <rect x={x} y={y0 - h} width={bw} height={Math.max(h, 0)} rx="10"
                fill={i === n - 1 ? '#ffd400' : '#3fa7ff'} />
              <text x={x + bw / 2} y={y0 - h - 18} fontSize="52" fontWeight="800" fill="#fff"
                textAnchor="middle" opacity={p}>{d.nhan ?? Math.round(d.gia_tri * p)}</text>
              <text x={x + bw / 2} y={y0 + 56} fontSize="44" fill="#cfe3f7" textAnchor="middle">{d.nam}</text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
