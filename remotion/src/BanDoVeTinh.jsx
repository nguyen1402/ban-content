// 20/10 user: nền BẢN ĐỒ VỆ TINH cho CanhMoTa. Python (ban_do.py) đã tra toạ độ thật (OpenStreetMap), tính camera
// cho từng khung (cam[f] = [x, y, zoom], x/y là px thế giới ở zoom 0) và tải sẵn ô ảnh vệ tinh vào public/ban_do/.
// Ở đây chỉ chiếu + vẽ: ô ảnh (mức tz-1 lót dưới, tz trên), viền vùng, đường nối, ghim + nhãn, dòng ghi nguồn.
// Công thức chọn ô PHẢI giống ban_do.o_can; chỉ vẽ ô có trong bd.o (không bao giờ tải mạng lúc dựng).
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';

const W = 1920, H = 1080;
const FONT = '"Segoe UI", "Be Vietnam Pro", Arial, sans-serif';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

function chieu(lat, lon) {
  const la = Math.max(-85, Math.min(85, lat)), s = Math.sin(la * Math.PI / 180);
  return [(lon + 180) / 360 * 256, (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 256];
}

function lenMan(cam, lat, lon) {
  const [x, y] = chieu(lat, lon), k = Math.pow(2, cam[2]);
  return [(x - cam[0]) * k + W / 2, (y - cam[1]) * k + H / 2];
}

function hien(f, fps, vao, ra, tong) {
  const a = Math.round(vao * fps), b = Math.round(ra * fps);
  if (f < a || f > b) return 0;
  const vo = interpolate(f, [a, a + 0.4 * fps], [0, 1], clamp);
  return ra >= tong - 0.05 ? vo : Math.min(vo, interpolate(f, [b - 0.3 * fps, b + 1], [1, 0], clamp));   // tới cuối cảnh: không mờ đi
}

export const BanDoVeTinh = ({bd}) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const tong = durationInFrames / fps;
  const cam = bd.cam[Math.min(f, bd.cam.length - 1)];
  const co = new Set(bd.o || []);
  const tz = Math.max(1, Math.min(bd.zmax || 13, Math.ceil(cam[2])));
  const o = [];
  for (const lv of [tz - 1, tz]) {
    const n = Math.pow(2, lv), k = Math.pow(2, cam[2] - lv), kt = 256 * k;
    const cx = cam[0] * n, cy = cam[1] * n;
    const x0 = (cx - W / 2 / k) / 256, x1 = (cx + W / 2 / k) / 256, y0 = (cy - H / 2 / k) / 256, y1 = (cy + H / 2 / k) / 256;
    for (let ty = Math.max(0, Math.floor(y0)); ty <= Math.min(n - 1, Math.floor(y1)); ty++) {
      for (let tx = Math.floor(x0); tx <= Math.floor(x1); tx++) {
        const key = `${lv}_${((tx % n) + n) % n}_${ty}`;
        if (!co.has(key)) continue;
        o.push(<Img key={`${lv}/${tx}/${ty}`} src={staticFile(`ban_do/${key}.jpg`)} style={{position: 'absolute',
          left: (tx * 256 - cx) * k + W / 2, top: (ty * 256 - cy) * k + H / 2, width: kt + 0.8, height: kt + 0.8}} />);
      }
    }
  }
  const diem = bd.diem || [];
  // 20/10 user: mặc định chỉ icon vị trí + tên địa danh bên trên. 22/10 user ("đánh dấu lãnh thổ"): điểm được yêu cầu
  // KHOANH (Python chỉ gửi d.vien khi khoanh) -> vẽ viền lãnh thổ chạy dần + tô mờ.
  const vien = diem.map((d, i) => {
    const a = hien(f, fps, d.vao ?? 0, d.ra ?? tong, tong);
    if (!a || !d.vien) return null;
    const ve = interpolate(f - (d.vao ?? 0) * fps, [0, 1.2 * fps], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
    const pts = d.vien.map(([la, lo]) => lenMan(cam, la, lo).map((v) => v.toFixed(1)).join(',')).join(' ');
    return <polygon key={`v${i}`} points={pts} pathLength={1} fill={`rgba(255,213,79,${0.18 * ve})`} stroke="#ffd54f"
      strokeWidth={5} strokeLinejoin="round" strokeDasharray="1" strokeDashoffset={1 - ve} opacity={a} />;
  });
  const duong = (bd.duong || []).map((d, i) => {
    const A = diem[d.tu], B = diem[d.den];
    if (!A || !B) return null;
    const a = hien(f, fps, d.vao ?? 0, d.ra ?? tong, tong);
    if (!a) return null;
    const p = interpolate(f - (d.vao ?? 0) * fps, [0, 1.2 * fps], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
    const [x1, y1] = lenMan(cam, A.lat, A.lon), [x2, y2] = lenMan(cam, B.lat, B.lon);
    return <line key={`d${i}`} x1={x1} y1={y1} x2={x1 + (x2 - x1) * p} y2={y1 + (y2 - y1) * p} stroke="#ff5252"
      strokeWidth={7} strokeDasharray="22 14" strokeLinecap="round" opacity={a} />;
  });
  const hop = [];                                            // khung các nhãn đã đặt (tránh chồng nhau)
  const PW = 54, PH = 74;                                    // icon vị trí: mũi nhọn chạm đúng toạ độ
  const ghim = diem.map((d, i) => {
    const a = hien(f, fps, d.vao ?? 0, d.ra ?? tong, tong);
    if (!a) return null;
    const [x, y] = lenMan(cam, d.lat, d.lon);
    if (x < -400 || x > W + 400 || y < -300 || y > H + 300) return null;
    const rw = String(d.nhan || '').length * 23 + 40, rh = 60;
    const khung = (day) => [x - rw / 2, y - day - rh, x + rw / 2, y - day];
    let day = PH + 10;                                       // nhãn luôn NGAY TRÊN icon của nó; đụng nhãn khác -> nâng lên một tầng
    while (d.nhan && day < 600 && hop.some((q) => { const r = khung(day); return r[0] < q[2] && r[2] > q[0] && r[1] < q[3] && r[3] > q[1]; })) day += rh + 12;
    if (d.nhan) hop.push(khung(day));
    const nay = interpolate(f - (d.vao ?? 0) * fps, [0, 0.4 * fps], [0, 1], {...clamp, easing: Easing.out(Easing.back(2.2))});
    const roi = interpolate(f - (d.vao ?? 0) * fps, [0, 0.4 * fps], [-40, 0], {...clamp, easing: Easing.out(Easing.cubic)});
    return (
      <div key={`g${i}`} style={{position: 'absolute', left: x, top: y, opacity: a}}>
        <svg width={PW} height={PH} viewBox="0 0 24 33" style={{position: 'absolute', left: -PW / 2, top: -PH + roi,
          overflow: 'visible', filter: 'drop-shadow(0 4px 6px rgba(0,0,0,.6))'}}>
          <path d="M12 0C5.4 0 0 5.3 0 11.9 0 20.8 12 33 12 33s12-12.2 12-21.1C24 5.3 18.6 0 12 0z" fill="#e53935"
            stroke="#fff" strokeWidth="1.4" />
          <circle cx="12" cy="11.8" r="4.6" fill="#fff" />
        </svg>
        {d.nhan && day > PH + 10 ? <div style={{position: 'absolute', left: -1.5, top: -day + roi, width: 3,
          height: day - PH, background: '#fff', opacity: nay, boxShadow: '0 0 4px rgba(0,0,0,.6)'}} /> : null}
        {d.nhan ? <div style={{position: 'absolute', left: 0, top: -day + roi, transform: `translate(-50%, -100%) scale(${nay})`,
          transformOrigin: '50% 100%', whiteSpace: 'nowrap', fontFamily: FONT, fontSize: 40, fontWeight: 800, color: '#fff',
          background: 'rgba(0,0,0,.62)', padding: '6px 18px', borderRadius: 8}}>{d.nhan}</div> : null}
      </div>);
  });
  return (
    <AbsoluteFill style={{background: '#05070b', overflow: 'hidden'}}>
      {o}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>{vien}{duong}</svg>
      {ghim}
      {bd.ghi_nguon ? <div style={{position: 'absolute', right: 14, bottom: 10, fontFamily: FONT, fontSize: 15,
        color: 'rgba(255,255,255,.75)', textShadow: '0 1px 3px #000'}}>{bd.ghi_nguon}</div> : null}
    </AbsoluteFill>);
};
