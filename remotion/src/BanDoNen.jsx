import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const W = 1920;
const H = 1080;
const FONT = '"Montserrat", "Plus Jakarta Sans", "Inter", -apple-system, system-ui, sans-serif';
const R0 = 156543.03392;

const mpp = (lat, z) => (R0 * Math.cos((lat * Math.PI) / 180)) / 2 ** z;
const wx = (lon, z) => ((lon + 180) / 360) * 256 * 2 ** z;
const wy = (lat, z) => {
  const s = Math.sin((lat * Math.PI) / 180);
  return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 256 * 2 ** z;
};
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const mem = (x) => x * x * (3 - 2 * x);

// Vector Icon phương tiện hiện đại (thay thế emoji hệ thống trẻ con)
const VehicleIcon = ({ type, color = '#ffd400' }) => {
  if (type === 'may_bay') {
    return (
      <g filter="url(#glow)">
        <path
          d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"
          fill={color}
          transform="translate(-24, -24) scale(2.0)"
        />
      </g>
    );
  }
  if (type === 'tau_thuy') {
    return (
      <g filter="url(#glow)">
        <path
          d="M20 21c-1.39 0-2.78-.47-4-1.32-2.44 1.71-5.56 1.71-8 0C6.78 20.53 5.39 21 4 21H2v2h2c1.38 0 2.74-.35 4-.99 2.53 1.28 5.47 1.28 8 0 1.26.64 2.62.99 4 .99h2v-2h-2zM3.95 19H4c1.6 0 3.02-.88 4-2 .98 1.12 2.4 2 4 2s3.02-.88 4-2c.98 1.12 2.4 2 4 2h.05l1.89-6.68c.08-.26.06-.54-.06-.78s-.34-.42-.6-.47L20 11.02V4c0-.55-.45-1-1-1h-6c-.55 0-1 .45-1 1v2.5l-4.5 1.5L4 8l-.05 1L2 12.32 3.95 19z"
          fill={color}
          transform="translate(-22, -22) scale(1.8)"
        />
      </g>
    );
  }
  // Mặc định: Radar navigation marker tinh tế với hiệu ứng phát sáng
  return (
    <g filter="url(#glow)">
      <circle r="18" fill="rgba(255, 212, 0, 0.22)" />
      <circle r="9" fill={color} stroke="#ffffff" strokeWidth="2.5" />
      <circle r="3.5" fill="#ffffff" />
    </g>
  );
};

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
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(6,10,18,0.7) 100%)'}} />
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <defs>
          <filter id="glow"><feGaussianBlur stdDeviation="3.5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        {tuyenVe.map((r, k) => {
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
          const mau = phuong_tien === 'tau_thuy' ? '#38bdf8' : '#facc15';
          const net = phuong_tien === 'may_bay' || phuong_tien === 'tau_thuy' ? '18 12' : undefined;
          return (
            <g key={'r' + k}>
              <mask id={'m' + k} maskUnits="userSpaceOnUse" x="0" y="0" width={W} height={H}>
                <path d={d} stroke="#fff" strokeWidth="16" fill="none" pathLength="1" strokeDasharray="1"
                  strokeDashoffset={1 - ve} strokeLinecap="round" />
              </mask>
              <path d={d} stroke={mau} strokeWidth="5" fill="none" strokeDasharray={net} strokeLinecap="round"
                mask={`url(#m${k})`} filter="url(#glow)" />
              {ve >= 0.995 && (
                <g transform={`translate(${bx},${by}) rotate(${gocCuoi})`}>
                  <path d="M -30 -16 L 6 0 L -30 16 Z" fill={mau} stroke="#10202e" strokeWidth="2.5" filter="url(#glow)" />
                </g>
              )}
              {r.den.ten && ve > 0.6 && (
                <g opacity={clamp((ve - 0.6) / 0.3, 0, 1)} transform={`translate(${bx + 24}, ${by - 20})`}>
                  <rect x="-8" y="-30" width={r.den.ten.length * 20 + 28} height="40" rx="8"
                    fill="rgba(11, 17, 30, 0.85)" stroke="rgba(255, 255, 255, 0.2)" strokeWidth="1.5" />
                  <text x="6" y="-4" fontSize="24" fontWeight="700" fill="#ffffff" letterSpacing="1"
                    fontFamily={FONT} dominantBaseline="middle">{r.den.ten}</text>
                </g>
              )}
              {ve > 0 && ve < 0.995 && (
                <g transform={bay ? `translate(${px},${py}) rotate(${goc + 45})` : `translate(${px},${py})`}>
                  <VehicleIcon type={phuong_tien} color={mau} />
                </g>
              )}
            </g>
          );
        })}
        {vien.length === 0 && (
          <circle cx={diem[0]} cy={diem[1]} r={60 + 5 * Math.sin(f / 6)} fill="rgba(250,204,21,0.12)" stroke="#facc15" strokeWidth="4"
            pathLength="1" strokeDasharray="1" strokeDashoffset={1 - veNet} filter="url(#glow)" />
        )}
        {vien.map((v, i) => (
          <g key={i}>
            <path d={duongViền(v)} fill={veTinh ? `rgba(250,204,21,${0.14 * veNet})` : `rgba(239,68,68,${0.18 * veNet})`} stroke="none" />
            <path d={duongViền(v)} fill="none" stroke={veTinh ? '#facc15' : '#ef4444'} strokeWidth={veTinh ? 4 : 5} strokeLinejoin="round"
              pathLength="1" strokeDasharray="1" strokeDashoffset={1 - veNet} filter="url(#glow)" />
          </g>
        ))}
        {diemDau.map((m, i) => (
          <g key={i} opacity={hien(i)}>
            {(m.vien || []).map((v, j) => (
              <path key={j} d={duongViền(v)} fill="rgba(250,204,21,0.15)" stroke="#facc15" strokeWidth="4" pathLength="1"
                strokeDasharray="1" strokeDashoffset={1 - hien(i)} />
            ))}
            <circle cx={m.p[0]} cy={m.p[1]} r="11" fill="#facc15" stroke="#10202e" strokeWidth="2.5" />
            <text x={m.p[0] + 20} y={m.p[1] + 8} fontSize="34" fontWeight="700" fill="#fff" stroke="#10202e"
              strokeWidth="6" paintOrder="stroke" fontFamily={FONT}>{m.ten}</text>
          </g>
        ))}
        {!(veTinh && vien.length) && <circle cx={diem[0]} cy={diem[1]} r={32 * pulse} fill="rgba(239,68,68,0.2)" />}
        {!(veTinh && vien.length) && <circle cx={diem[0]} cy={diem[1]} r="11" fill="#ef4444" stroke="#fff" strokeWidth="3" />}
      </svg>
      {tenVung ? (
        <div style={{
          position: 'absolute', left: tenVung.x, top: tenVung.y,
          background: 'rgba(11, 15, 25, 0.82)', backdropFilter: 'blur(16px)',
          border: '1.5px solid rgba(250, 204, 21, 0.4)', borderRadius: 28,
          padding: '16px 36px',
          boxShadow: '0 12px 36px rgba(0,0,0,0.65), 0 0 20px rgba(250, 204, 21, 0.15)',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          transform: `translate(-50%, -50%) scale(${0.85 + 0.15 * clamp((veNet - 0.85) / 0.15, 0, 1)})`,
          opacity: clamp((veNet - 0.85) / 0.15, 0, 1)
        }}>
          <span style={{color: '#facc15', fontSize: 16, fontWeight: 800, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 4}}>
            VỊ TRÍ ĐỊA LÝ
          </span>
          <span style={{color: '#ffffff', fontSize: Math.min(tenVung.co, 60), fontWeight: 900, letterSpacing: 1.5, whiteSpace: 'nowrap', textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>
            {dia_diem}
          </span>
        </div>
      ) : (
        <div style={{
          position: 'absolute', left: 70, top: 60,
          background: 'rgba(11, 15, 25, 0.8)', backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.18)', borderRadius: 20,
          padding: '16px 32px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
          display: 'flex', flexDirection: 'column',
          opacity: interpolate(f, [0, 18], [0, 1])
        }}>
          <span style={{color: '#facc15', fontSize: 15, fontWeight: 800, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 4}}>
            BẢN ĐỒ VỆ TINH
          </span>
          <span style={{color: '#ffffff', fontSize: 46, fontWeight: 900, letterSpacing: 1}}>
            {dia_diem}
          </span>
        </div>
      )}
      {nam !== null && (
        <div style={{position: 'absolute', right: 80, bottom: 78, color: '#facc15', fontSize: 170, fontWeight: 900,
          textShadow: '0 6px 20px rgba(0,0,0,0.8)', letterSpacing: 4, fontFamily: FONT}}>{nam}</div>
      )}
      <div style={{position: 'absolute', left: 70, bottom: 78, display: 'flex', flexDirection: 'column', gap: 14}}>
        {chu_thich.map((c, i) => (
          <div key={i} style={{opacity: hien(i, 0.32), transform: `translateX(${(1 - hien(i, 0.32)) * -50}px)`, color: '#fff',
            fontSize: 36, fontWeight: 700, background: 'rgba(11, 15, 25, 0.8)', backdropFilter: 'blur(12px)',
            padding: '12px 26px', borderRadius: 14, border: '1px solid rgba(255,255,255,0.15)',
            maxWidth: 1100, borderLeft: '6px solid #facc15', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', fontFamily: FONT}}>{c}</div>
        ))}
      </div>
      <div style={{position: 'absolute', right: 14, bottom: 8, color: 'rgba(255,255,255,0.75)', fontSize: veTinh ? 15 : 18}}>
        {ghi_nguon}
      </div>
    </AbsoluteFill>
  );
};
