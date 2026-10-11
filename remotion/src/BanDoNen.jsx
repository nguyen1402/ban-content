import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const W = 1920;
const H = 1080;
const FONT = '"Segoe UI", Arial, sans-serif';
const R0 = 156543.03392;

const mpp = (lat, z) => (R0 * Math.cos((lat * Math.PI) / 180)) / 2 ** z;
const wx = (lon, z) => ((lon + 180) / 360) * 256 * 2 ** z;
const wy = (lat, z) => {
  const s = Math.sin((lat * Math.PI) / 180);
  return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 256 * 2 ** z;
};
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const mem = (x) => x * x * (3 - 2 * x);

// props: {giay, dia_diem, lat, lon, rong_km, nam_tu, nam_den, dau[{ten,lat,lon,vien}], noi, chu_thich[], lop[], vien[]}
export const BanDoNen = ({
  dia_diem = '', lat = 0, lon = 0, rong_km = 20, nam_tu = null, nam_den = null,
  dau = [], noi = false, chu_thich = [], lop = [], vien = [],
}) => {
  const f = useCurrentFrame();
  const {durationInFrames: N} = useVideoConfig();
  const lopGan = lop[lop.length - 1];
  const lopRong = lop[0];

  // Camera: từ lớp rộng (phủ kín) phóng vào lớp gần theo logarit, có ease.
  const mppRong = mpp(lat, lopRong.z);
  const mppDau = mppRong * 0.62;
  const mppCuoi = (rong_km * 1000) / W;
  const k = Easing.inOut(Easing.cubic)(clamp(f / (N * 0.78), 0, 1));
  const mppCam = Math.exp(interpolate(k, [0, 1], [Math.log(mppDau), Math.log(Math.max(mppCuoi, 0.5))]));

  // Chiếu (lon,lat) -> màn hình theo cùng camera (dựa trên hệ pixel mức zoom lớp gần).
  const zc = lopGan.z;
  const sc = mpp(lat, zc) / mppCam;
  const cx = wx(lon, zc);
  const cy = wy(lat, zc);
  const toScreen = (lo, la) => [W / 2 + (wx(lo, zc) - cx) * sc, H / 2 + (wy(la, zc) - cy) * sc];

  const nam = nam_tu != null && nam_den != null
    ? Math.round(interpolate(f, [N * 0.1, N * 0.9], [nam_tu, nam_den], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}))
    : null;
  const hien = (i, t0 = 0.3) => clamp((f / N - (t0 + 0.09 * i)) / 0.09, 0, 1);

  // Đường viền chạy nét: bắt đầu khi camera gần tới nơi.
  const veNet = mem(clamp((f / N - 0.55) / 0.22, 0, 1));
  const pulse = 1 + 0.2 * Math.sin(f / 4);

  const duongViền = (vong) => 'M' + vong.map(([lo, la]) => toScreen(lo, la).map((v) => v.toFixed(1)).join(',')).join('L') + 'Z';
  const diem = toScreen(lon, lat);
  const diemDau = dau.map((m) => ({...m, p: toScreen(m.lon, m.lat)}));

  return (
    <AbsoluteFill style={{background: '#1b2733', fontFamily: FONT, overflow: 'hidden'}}>
      <AbsoluteFill style={{filter: 'grayscale(0.35) sepia(0.3) contrast(1.06) brightness(0.9) saturate(1.1)'}}>
        {lop.map((l, i) => {
          const m = mpp(lat, l.z);
          const s = m / mppCam;
          const lx = wx(lon, l.z) - l.ox;
          const ly = wy(lat, l.z) - l.oy;
          // lớp mịn hơn mờ dần vào khi đã phủ kín màn hình (s >= ~1.1)
          const sCov = (W * 1.03) / l.w;            // tỉ lệ tối thiểu để lớp này phủ kín bề ngang màn hình
          const op = i === 0 ? 1 : mem(clamp((s - sCov) / (0.4 * sCov), 0, 1));
          return (
            <div key={i} style={{position: 'absolute', left: W / 2 - lx * s, top: H / 2 - ly * s,
              width: l.w * s, height: l.h * s, opacity: op}}>
              <Img src={l.src} style={{width: '100%', height: '100%'}} />
            </div>
          );
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)'}} />
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <defs>
          <filter id="glow"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        {noi && diemDau[0] && (
          <path d={`M${diemDau[0].p[0]},${diemDau[0].p[1]} L${diem[0]},${diem[1]}`} stroke="#ffd400" strokeWidth="6"
            strokeDasharray="22 16" strokeDashoffset={-f * 2.2} fill="none" opacity={hien(0, 0.45)} filter="url(#glow)" />
        )}
        {vien.length === 0 && (
          <circle cx={diem[0]} cy={diem[1]} r={70 + 6 * Math.sin(f / 6)} fill="rgba(255,59,48,0.12)" stroke="#ff3b30" strokeWidth="7"
            pathLength="1" strokeDasharray="1" strokeDashoffset={1 - veNet} filter="url(#glow)" />
        )}
        {vien.map((v, i) => (
          <g key={i}>
            <path d={duongViền(v)} fill={`rgba(230,40,40,${0.22 * veNet})`} stroke="none" />
            <path d={duongViền(v)} fill="none" stroke="#ff3b30" strokeWidth="7" strokeLinejoin="round"
              pathLength="1" strokeDasharray="1" strokeDashoffset={1 - veNet} filter="url(#glow)" />
          </g>
        ))}
        {diemDau.map((m, i) => (
          <g key={i} opacity={hien(i)}>
            {(m.vien || []).map((v, j) => (
              <path key={j} d={duongViền(v)} fill="rgba(255,212,0,0.18)" stroke="#ffd400" strokeWidth="5" pathLength="1"
                strokeDasharray="1" strokeDashoffset={1 - hien(i)} />
            ))}
            <circle cx={m.p[0]} cy={m.p[1]} r="13" fill="#ffd400" stroke="#222" strokeWidth="3" />
            <text x={m.p[0] + 24} y={m.p[1] + 10} fontSize="40" fontWeight="700" fill="#fff" stroke="#10202e"
              strokeWidth="8" paintOrder="stroke">{m.ten}</text>
          </g>
        ))}
        <circle cx={diem[0]} cy={diem[1]} r={38 * pulse} fill="rgba(255,59,48,0.22)" />
        <circle cx={diem[0]} cy={diem[1]} r="13" fill="#ff3b30" stroke="#fff" strokeWidth="4" />
      </svg>
      <div style={{position: 'absolute', left: 70, top: 54, color: '#fff', fontSize: 64, fontWeight: 800,
        textShadow: '0 4px 16px rgba(0,0,0,0.8)', opacity: interpolate(f, [0, 18], [0, 1])}}>{dia_diem}</div>
      {nam !== null && (
        <div style={{position: 'absolute', right: 80, bottom: 78, color: '#ffd400', fontSize: 190, fontWeight: 900,
          textShadow: '0 6px 20px rgba(0,0,0,0.8)', letterSpacing: 4}}>{nam}</div>
      )}
      <div style={{position: 'absolute', left: 70, bottom: 78, display: 'flex', flexDirection: 'column', gap: 14}}>
        {chu_thich.map((c, i) => (
          <div key={i} style={{opacity: hien(i, 0.32), transform: `translateX(${(1 - hien(i, 0.32)) * -50}px)`, color: '#fff',
            fontSize: 44, fontWeight: 600, background: 'rgba(0,0,0,0.6)', padding: '10px 22px', borderRadius: 10,
            maxWidth: 1100, borderLeft: '8px solid #ff3b30'}}>{c}</div>
        ))}
      </div>
      <div style={{position: 'absolute', right: 14, bottom: 8, color: 'rgba(255,255,255,0.75)', fontSize: 18}}>
        © OpenStreetMap contributors
      </div>
    </AbsoluteFill>
  );
};
