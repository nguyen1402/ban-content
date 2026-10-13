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
// icon phương tiện (emoji hệ thống). Máy bay gốc hướng lên-phải (xoay theo hướng bay); tàu/xe gốc hướng TRÁI.
const ICON = {may_bay: '✈️', tau_thuy: '🚢', tau_hoa: '🚆', xe: '🚚', di_bo: '🚶'};

// props: {giay, dia_diem, lat, lon, rong_km, nam_tu, nam_den, dau[{ten,lat,lon,vien}], noi, chu_thich[], lop[], vien[]}
export const BanDoNen = ({
  dia_diem = '', lat = 0, lon = 0, rong_km = 20, nam_tu = null, nam_den = null,
  dau = [], noi = false, tuyen = null, phuong_tien = '', chu_thich = [], lop = [], vien = [], nguon = 'osm', ghi_nguon = '© OpenStreetMap contributors', cam_lat = null, cam_lon = null,
}) => {
  const veTinh = nguon === 'vetinh';
  const f = useCurrentFrame();
  const {durationInFrames: N} = useVideoConfig();
  const lopGan = lop[lop.length - 1];
  const lopRong = lop[0];

  // Camera: từ lớp rộng (phủ kín) phóng vào lớp gần theo logarit, có ease.
  // camera: mặc định căn vào điểm chính; bản đồ ĐƯỜNG ĐI căn vào giữa hai điểm (cam_lat/cam_lon)
  const cLat = cam_lat ?? lat;
  const cLon = cam_lon ?? lon;
  const mppRong = mpp(cLat, lopRong.z);
  const mppDau = mppRong * (veTinh ? 0.6 : 0.62);      // vệ tinh: bắt đầu từ rất xa (lớp rộng 6 ô = 1536px phải phủ kín 1920px: <= 0.8)
  const mppCuoi = (rong_km * 1000) / W;
  const k = Easing.inOut(Easing.cubic)(clamp(f / (N * 0.78), 0, 1));
  const mppCam = Math.exp(interpolate(k, [0, 1], [Math.log(mppDau), Math.log(Math.max(mppCuoi, 0.5))]));

  // Chiếu (lon,lat) -> màn hình theo cùng camera (dựa trên hệ pixel mức zoom lớp gần).
  const zc = lopGan.z;
  const sc = mpp(cLat, zc) / mppCam;
  const cx = wx(cLon, zc);
  const cy = wy(cLat, zc);
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
  // 13/10 user: khoanh xong thì GHI TÊN vào giữa vùng khoanh (thay tiêu đề ở góc)
  const vongLon = vien.length ? vien.reduce((a, b) => (b.length > a.length ? b : a)) : null;
  let tenVung = null;
  if (vongLon) {
    const ps = vongLon.map(([lo, la]) => toScreen(lo, la));
    const xs = ps.map((q) => q[0]), ys = ps.map((q) => q[1]);
    const x0 = Math.max(60, Math.min(...xs)), x1 = Math.min(W - 60, Math.max(...xs));
    const y0 = Math.max(60, Math.min(...ys)), y1 = Math.min(H - 60, Math.max(...ys));
    tenVung = {x: (x0 + x1) / 2, y: (y0 + y1) / 2, co: clamp((x1 - x0) / Math.max(4, dia_diem.length * 0.62), 46, 110)};
  }
  const diemDau = dau.map((m) => ({...m, p: toScreen(m.lon, m.lat)}));
  // tuyến vẽ: props.tuyen [{tu:{lat,lon}, den:{lat,lon,ten}}] (lan_rong); bản cũ noi + dau[0] -> 1 tuyến tới điểm chính
  const tuyenVe = tuyen || (noi && dau[0] ? [{tu: dau[0], den: {lat, lon}}] : []);

  return (
    <AbsoluteFill style={{background: '#1b2733', fontFamily: FONT, overflow: 'hidden'}}>
      <AbsoluteFill style={{filter: veTinh ? 'contrast(1.08) saturate(1.15) brightness(0.95)' : 'grayscale(0.35) sepia(0.3) contrast(1.06) brightness(0.9) saturate(1.1)'}}>
        {lop.map((l, i) => {
          const m = mpp(cLat, l.z);
          const s = m / mppCam;
          const lx = wx(cLon, l.z) - l.ox;
          const ly = wy(cLat, l.z) - l.oy;
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
        {tuyenVe.map((r, k) => {
          // 13/10 user: đường đi có MŨI TÊN ở đích + ICON PHƯƠNG TIỆN chạy dọc đường (máy bay xoay theo hướng bay;
          // tàu/xe lật trái-phải theo hướng đi). lan_rong: nhiều tuyến toả ra lần lượt.
          const [ax, ay] = toScreen(r.tu.lon, r.tu.lat);
          const [bx, by] = toScreen(r.den.lon, r.den.lat);
          const bay = phuong_tien === 'may_bay';
          const cao = bay ? 0.3 : 0.16;
          const mx = (ax + bx) / 2, my = (ay + by) / 2 - Math.hypot(bx - ax, by - ay) * cao;
          const d = `M${ax},${ay} Q${mx},${my} ${bx},${by}`;
          const t0 = 0.26 + 0.11 * k, dt = tuyenVe.length > 1 ? 0.3 : 0.42;
          const ve = mem(clamp((f / N - t0) / dt, 0, 1));
          const P = (t) => [(1 - t) * (1 - t) * ax + 2 * (1 - t) * t * mx + t * t * bx,
            (1 - t) * (1 - t) * ay + 2 * (1 - t) * t * my + t * t * by];
          const [px, py] = P(ve);
          const [qx, qy] = P(Math.min(1, ve + 0.01));
          const [ux, uy] = P(0.98);
          const goc = Math.atan2(qy - py, qx - px) * 180 / Math.PI;
          const gocCuoi = Math.atan2(by - uy, bx - ux) * 180 / Math.PI;
          const icon = ICON[phuong_tien];
          const mau = phuong_tien === 'tau_thuy' ? '#7fd8ff' : '#ffd400';
          const net = phuong_tien === 'may_bay' || phuong_tien === 'tau_thuy' ? '22 16' : undefined;
          return (
            <g key={'r' + k}>
              <mask id={'m' + k} maskUnits="userSpaceOnUse" x="0" y="0" width={W} height={H}>
                <path d={d} stroke="#fff" strokeWidth="16" fill="none" pathLength="1" strokeDasharray="1"
                  strokeDashoffset={1 - ve} strokeLinecap="round" />
              </mask>
              <path d={d} stroke={mau} strokeWidth="7" fill="none" strokeDasharray={net} strokeLinecap="round"
                mask={`url(#m${k})`} filter="url(#glow)" />
              {ve >= 0.995 && (
                <g transform={`translate(${bx},${by}) rotate(${gocCuoi})`}>
                  <path d="M -34 -20 L 6 0 L -34 20 Z" fill={mau} stroke="#10202e" strokeWidth="3" filter="url(#glow)" />
                </g>
              )}
              {r.den.ten && ve > 0.6 && (
                <text x={bx + 26} y={by - 22} fontSize="40" fontWeight="700" fill="#fff" stroke="#10202e" strokeWidth="8"
                  paintOrder="stroke" opacity={clamp((ve - 0.6) / 0.3, 0, 1)}>{r.den.ten}</text>
              )}
              {ve > 0 && ve < 0.995 && (icon
                ? <text x={0} y={0} fontSize="78" textAnchor="middle" dominantBaseline="central"
                    style={{fontFamily: '"Segoe UI Emoji", "Noto Color Emoji", sans-serif'}}
                    transform={bay ? `translate(${px},${py}) rotate(${goc + 45})`
                      : `translate(${px},${py}) scale(${qx < px ? 1 : -1},1)`}>{icon}</text>
                : <circle cx={px} cy={py} r="14" fill="#fff" stroke="#ffd400" strokeWidth="5" filter="url(#glow)" />)}
            </g>
          );
        })}
        {vien.length === 0 && (
          <circle cx={diem[0]} cy={diem[1]} r={70 + 6 * Math.sin(f / 6)} fill="rgba(255,59,48,0.12)" stroke="#ff3b30" strokeWidth="7"
            pathLength="1" strokeDasharray="1" strokeDashoffset={1 - veNet} filter="url(#glow)" />
        )}
        {vien.map((v, i) => (
          <g key={i}>
            <path d={duongViền(v)} fill={veTinh ? `rgba(255,214,0,${0.16 * veNet})` : `rgba(230,40,40,${0.22 * veNet})`} stroke="none" />
            <path d={duongViền(v)} fill="none" stroke={veTinh ? '#ffd400' : '#ff3b30'} strokeWidth={veTinh ? 5 : 7} strokeLinejoin="round"
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
        {!(veTinh && vien.length) && <circle cx={diem[0]} cy={diem[1]} r={38 * pulse} fill="rgba(255,59,48,0.22)" />}
        {!(veTinh && vien.length) && <circle cx={diem[0]} cy={diem[1]} r="13" fill="#ff3b30" stroke="#fff" strokeWidth="4" />}
      </svg>
      {tenVung ? (
        <div style={{position: 'absolute', left: tenVung.x, top: tenVung.y, color: '#fff', fontSize: tenVung.co, fontWeight: 900,
          whiteSpace: 'nowrap', textShadow: '0 0 6px #000, 0 4px 18px rgba(0,0,0,0.9)', letterSpacing: 1,
          opacity: clamp((veNet - 0.85) / 0.15, 0, 1),
          transform: `translate(-50%, -50%) scale(${0.85 + 0.15 * clamp((veNet - 0.85) / 0.15, 0, 1)})`}}>{dia_diem}</div>
      ) : (
        <div style={{position: 'absolute', left: 70, top: 54, color: '#fff', fontSize: 64, fontWeight: 800,
          textShadow: '0 4px 16px rgba(0,0,0,0.8)', opacity: interpolate(f, [0, 18], [0, 1])}}>{dia_diem}</div>
      )}
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
      <div style={{position: 'absolute', right: 14, bottom: 8, color: 'rgba(255,255,255,0.75)', fontSize: veTinh ? 15 : 18}}>
        {ghi_nguon}
      </div>
    </AbsoluteFill>
  );
};
