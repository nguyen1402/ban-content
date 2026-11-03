import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// 03/11 user: NHẤN Ý cho câu ví von / câu then chốt — chuyển động BÁM TỪNG CỤM TỪ của câu đang đọc (nhịp do
// chinh_sua/nhan_y.py tính từ giờ từng chữ của giọng đọc), trên MỘT ảnh AI vẽ riêng cho câu đó (vùng của từng vật đã dò
// bằng SigLIP), chữ nổi lên đúng lúc. User chê kiểu sticker lắc lắc + đóng băng khung -> bỏ; không rung / lắc.
// props: {giay, anh, nen (khung footage ngay trước, để vào cảnh liền mạch), vao: 'mo'|'xuyen'|'cheo',
//         vung: {ten: [x0, y0, x1, y1] 0..1 trên ảnh}, nhip: [{t, lam, vung, chu, so, den}]}
//   lam: toan_canh | phong_vao (vung) | khoanh (vung) | mui_ten (vung -> den) | chu (chu) | so_dem (so, chu)
const src = (s) => (!s ? '' : /^(https?:|data:|file:)/.test(s) ? s : staticFile(s));
const kep = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const FONT = '"Segoe UI", "Be Vietnam Pro", Arial, sans-serif';
const VANG = '#ffd23f';
const EM = Easing.bezier(0.45, 0, 0.2, 1);
const W = 1920, H = 1080;

// khung nhìn (x, y, w) theo tỉ lệ 16:9 ôm vùng [x0, y0, x1, y1], có chừa lề
const khungNhin = (v, le = 1.2) => {
  if (!v) return {x: 0, y: 0, w: 1};
  const cx = (v[0] + v[2]) / 2, cy = (v[1] + v[3]) / 2;
  const w = Math.min(1, Math.max(0.3, (v[2] - v[0]) * le, (v[3] - v[1]) * le));
  return {x: Math.min(1 - w, Math.max(0, cx - w / 2)), y: Math.min(1 - w, Math.max(0, cy - w / 2)), w};
};

// camera: từ khung nhìn của nhịp trước trượt êm sang khung của nhịp phong_vao / toan_canh hiện tại (0,7 s)
const camera = (f, fps, nhip, vung, D) => {
  const moc = [{t: 0, k: {x: 0.04, y: 0.04, w: 0.92}}];
  // 03/11 user ("đoạn đầu đã phải zoom to vào người đỡ bị nhìn thấy núi thịt"): nhịp đầu là phóng vào một vật -> mở
  // cảnh ngay ở khung đó, không lộ toàn cảnh trước
  const CAM = ['phong_vao', 'toan_canh', 'khoanh', 'mui_ten', 'roi_xep', 'nhan_ban'];
  const dau = nhip.find((n) => CAM.includes(n.lam));                 // nhịp camera đầu tiên, dù rơi vào giây nào
  if (dau && dau.lam === 'phong_vao' && vung[dau.vung]) moc[0] = {t: 0, k: khungNhin(vung[dau.vung])};
  // toàn cảnh ngay trước cú rơi làm lộ khoảng trống chờ sẵn -> bỏ (cú rơi tự lùi camera ra)
  nhip = nhip.filter((n, i) => !(n.lam === 'toan_canh' && nhip.slice(i + 1).some((m) =>
    (m.lam === 'roi_xep' || m.lam === 'nhan_ban') && m.t - n.t < 3)));
  let cuoi = dau && dau.lam === 'phong_vao' ? vung[dau.vung] : null;    // vùng camera đang ôm
  const hop = (a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])];
  for (const n of nhip) {
    // 03/11 user (núi thịt): vật rơi -> camera LÙI RA ôm cả đống lẫn thứ đang nhìn, cho thấy tầm vóc
    if ((n.lam === 'roi_xep' || n.lam === 'nhan_ban') && vung[n.vung]) {
      const v = cuoi ? hop(cuoi, vung[n.vung]) : vung[n.vung];
      moc.push({t: n.t, k: khungNhin([v[0], Math.min(v[1], 0.12), v[2], v[3]], 1.15)});
      cuoi = v;
    }
    if (n.lam === 'phong_vao' && vung[n.vung]) { moc.push({t: n.t, k: khungNhin(vung[n.vung])}); cuoi = vung[n.vung]; }
    if (n.lam === 'toan_canh') moc.push({t: n.t, k: {x: 0, y: 0, w: 1}});
    // 03/11 (xem thử caloc): vòng khoanh / mũi tên ở ngoài khung đang nhìn chỉ lộ một mép -> camera lùi ra ôm vật trước
    if (n.lam === 'khoanh' && vung[n.vung]) moc.push({t: n.t, k: khungNhin(vung[n.vung], 2.0)});
    if (n.lam === 'mui_ten' && vung[n.vung] && vung[n.den]) {
      const a = vung[n.vung], b = vung[n.den];
      moc.push({t: n.t, k: khungNhin([Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])], 1.25)});
    }
  }
  let k = moc[0].k;
  for (let i = 1; i < moc.length; i++) {
    const a = moc[i - 1].k, b = moc[i].k, t0 = moc[i].t * fps;
    const p = interpolate(f, [t0, t0 + 0.7 * fps], [0, 1], {...kep, easing: EM});
    if (p <= 0) break;
    k = {x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, w: a.w + (b.w - a.w) * p};
  }
  const troi = interpolate(f, [0, D], [1, 0.965]);                     // đẩy vào rất chậm suốt cảnh (không lắc)
  const w = k.w * troi;
  return {x: k.x + (k.w - w) / 2, y: k.y + (k.w - w) / 2, w};
};

// vòng bút vẽ dần quanh một vùng (toạ độ ẢNH, nằm trong lớp camera nên bám theo ảnh)
const Khoanh = ({v, t, fps}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [t * fps, t * fps + 14], [0, 1], {...kep, easing: Easing.bezier(0.3, 0, 0.2, 1)});
  const cx = (v[0] + v[2]) / 2 * W, cy = (v[1] + v[3]) / 2 * H;
  const rx = (v[2] - v[0]) / 2 * W * 1.12 + 14, ry = (v[3] - v[1]) / 2 * H * 1.12 + 14;
  const pts = [];
  for (let i = 0; i <= 72; i++) {
    const a = -Math.PI * 0.6 + (i / 72) * Math.PI * 2.1;
    pts.push(`${cx + Math.cos(a) * rx},${cy + Math.sin(a) * ry}`);
  }
  const L = Math.PI * (rx + ry) * 1.1;
  return <polyline points={pts.join(' ')} fill="none" stroke={VANG} strokeWidth={8} strokeLinecap="round"
    strokeDasharray={L} strokeDashoffset={L * (1 - p)} style={{filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.6))'}} />;
};

// mũi tên cong vẽ dần từ vùng a sang vùng b
const MuiTen = ({a, b, t, fps}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [t * fps, t * fps + 16], [0, 1], {...kep, easing: Easing.bezier(0.3, 0, 0.2, 1)});
  const x1 = (a[0] + a[2]) / 2 * W, y1 = (a[1] + a[3]) / 2 * H, x2 = (b[0] + b[2]) / 2 * W, y2 = (b[1] + b[3]) / 2 * H;
  const mx = (x1 + x2) / 2, my = Math.min(y1, y2) - Math.abs(x2 - x1) * 0.22 - 40;
  const L = Math.hypot(x2 - x1, y2 - y1) * 1.25 + 80;
  const g = Math.atan2(y2 - my, x2 - mx);
  const dau = [[0, 0], [-34, -16], [-34, 16]].map(([u, w]) => `${x2 + u * Math.cos(g) - w * Math.sin(g)},${y2 + u * Math.sin(g) + w * Math.cos(g)}`);
  return (
    <g style={{filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.6))'}}>
      <path d={`M${x1},${y1} Q${mx},${my} ${x2},${y2}`} fill="none" stroke={VANG} strokeWidth={9} strokeLinecap="round"
        strokeDasharray={L} strokeDashoffset={L * (1 - p)} />
      <polygon points={dau.join(' ')} fill={VANG} opacity={p > 0.92 ? 1 : 0} />
    </g>
  );
};

// chữ nổi: từng chữ trượt lên khỏi mặt nạ, vạch vàng quét dưới cả dòng
const Chu = ({chu, t, het, fps, to = false}) => {
  const f = useCurrentFrame();
  const t0 = t * fps, t1 = het * fps;
  if (f < t0 - 1 || f > t1 + 6) return null;
  const tu = String(chu).split(/\s+/);
  const ra = interpolate(f, [t1 - 2, t1 + 6], [1, 0], kep);
  const vach = interpolate(f, [t0 + 4, t0 + 4 + 10 + tu.length * 2], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: to ? 380 : 120, display: 'flex', justifyContent: 'center',
      opacity: ra}}>
      <div style={{position: 'relative', padding: '6px 26px', maxWidth: 1500, textAlign: 'center'}}>
        <div style={{position: 'absolute', left: 10, right: 10, bottom: 10, height: to ? 40 : 26, background: VANG, opacity: 0.85,
          transformOrigin: '0 50%', transform: `scaleX(${vach})`}} />
        {tu.map((w, i) => {
          const p = interpolate(f, [t0 + i * 2, t0 + i * 2 + 9], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
          return (
            <span key={i} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom', marginRight: 18}}>
              <span style={{display: 'inline-block', transform: `translateY(${(1 - p) * 110}%)`, fontFamily: FONT,
                fontWeight: 900, fontSize: to ? 130 : 104, color: '#fff', letterSpacing: 1, lineHeight: 1.1,
                textShadow: '0 4px 18px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.9)'}}>{w}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
};

// số đếm lên (1.200 -> chấm ngăn nghìn kiểu Việt) + nhãn nhỏ
const SoDem = ({so, chu, t, het, fps}) => {
  const f = useCurrentFrame();
  if (f < t * fps - 1 || f > het * fps + 6) return null;
  const n = Number(so) || 0;
  const p = interpolate(f, [t * fps, t * fps + 1.1 * fps], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const le = Math.abs(n) < 100 && n % 1 !== 0 ? 1 : 0;
  const s = (n * p).toFixed(le).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: interpolate(f, [het * fps - 2, het * fps + 6], [1, 0], kep)}}>
      <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 230, color: '#fff', lineHeight: 1,
        textShadow: '0 8px 30px rgba(0,0,0,0.85)', transform: `scale(${interpolate(f, [t * fps, t * fps + 8], [0.7, 1], {...kep, easing: Easing.out(Easing.back(1.6))})})`}}>{s}</div>
      {chu ? <div style={{marginTop: 10, fontFamily: FONT, fontWeight: 800, fontSize: 72, color: VANG,
        textShadow: '0 4px 16px rgba(0,0,0,0.85)', opacity: interpolate(f, [t * fps + 8, t * fps + 16], [0, 1], kep)}}>{chu}</div> : null}
    </AbsoluteFill>
  );
};

// 03/11 user: vật tách nền RƠI từ trên xuống, xếp thành đống / chồng / tường (hoặc bật ra nhân bản) — vị trí do
// nhan_y.py tính sẵn; rơi nhanh dần, chạm thì nén nhẹ rồi đứng yên (không lắc). Toạ độ ẢNH: bám theo camera.
const XepRoi = ({src: s, ti, o, t, roi}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return o.map((it, i) => {
    const bd = (t + it.d) * fps, xong = bd + (it.roi ? roi * fps : 7);
    const w = it.w * W, h = w / ti;
    const yDich = it.y * H - h / 2;
    if (it.tinh) {                                                     // diễn viên đứng sẵn trên mặt đất
      return <Img key={i} src={src(s)} style={{position: 'absolute', left: it.x * W - w / 2, top: yDich, width: w, height: h,
        filter: 'drop-shadow(0 14px 14px rgba(0,0,0,0.5))'}} />;
    }
    if (f < bd) return null;
    let y = yDich, sc = 1, xoay = it.r;
    if (it.roi) {
      const p = interpolate(f, [bd, xong], [0, 1], {...kep, easing: Easing.in(Easing.quad)});
      y = -h - 40 + (yDich + h + 40) * p;
      xoay = it.r + (1 - p) * (it.r >= 0 ? 14 : -14);
      sc = 1 - interpolate(f, [xong, xong + 3, xong + 7], [0, 0.08, 0], kep);    // nén khi chạm
    } else {
      sc = interpolate(f, [bd, xong], [0, 1], {...kep, easing: Easing.out(Easing.back(1.8))});
    }
    return <Img key={i} src={src(s)} style={{position: 'absolute', left: it.x * W - w / 2, top: y, width: w, height: h,
      transformOrigin: '50% 100%', transform: `rotate(${xoay}deg) scale(${it.roi ? 1 : sc}, ${sc})`,
      filter: 'drop-shadow(0 10px 12px rgba(0,0,0,0.45))'}} />;
  });
};

// vào cảnh từ khung footage ngay trước: mờ chéo / lao xuyên qua / đường chéo quét
const VaoCanh = ({nen, vao}) => {
  const f = useCurrentFrame();
  if (!nen || f > 18) return null;
  const anh = {position: 'absolute', width: '100%', height: '100%', objectFit: 'cover'};
  if (vao === 'xuyen') {
    const lao = interpolate(f, [0, 11], [0, 1], {...kep, easing: Easing.in(Easing.cubic)});
    return <AbsoluteFill style={{opacity: interpolate(f, [7, 13], [1, 0], kep)}}>
      {[0, 1, 2].map((k) => <Img key={k} src={src(nen)} style={{...anh, transform: `scale(${1 + lao * (4 + k * 1.5)})`,
        opacity: k === 0 ? 1 : 0.3}} />)}
    </AbsoluteFill>;
  }
  if (vao === 'cheo') {
    const p = interpolate(f, [0, 14], [0, 1], {...kep, easing: EM});
    return <AbsoluteFill style={{clipPath: `polygon(0 0, ${(1 - p) * 130 - 20}% 0, ${(1 - p) * 130 - 40}% 100%, 0 100%)`}}>
      <Img src={src(nen)} style={anh} />
    </AbsoluteFill>;
  }
  return <Img src={src(nen)} style={{...anh, opacity: interpolate(f, [0, 12], [1, 0], kep)}} />;
};

export const NhanY = ({anh, nen, vao = 'mo', vung = {}, nhip = [], xep = [], roi = 0.5}) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames: D} = useVideoConfig();
  const c = camera(f, fps, nhip, vung, D);
  const s = 1 / c.w;
  const ve = nhip.filter((n) => (n.lam === 'khoanh' && vung[n.vung]) || (n.lam === 'mui_ten' && vung[n.vung] && vung[n.den]));
  const chu = nhip.map((n, i) => ({...n, het: (nhip.slice(i + 1).find((m) => m.lam === 'chu' || m.lam === 'so_dem') || {t: D / fps}).t}))
    .filter((n) => n.lam === 'chu' || n.lam === 'so_dem');
  const toi = Math.max(0, ...chu.filter((n) => n.lam === 'so_dem').map((n) =>
    interpolate(f, [n.t * fps, n.t * fps + 6, n.het * fps, n.het * fps + 6], [0, 0.45, 0.45, 0], kep)));
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden',
      opacity: interpolate(f, [D - 8, D], [1, 0], kep)}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0',
        transform: `translate(${-c.x * W * s}px, ${-c.y * H * s}px) scale(${s})`}}>
        <Img src={src(anh)} style={{position: 'absolute', width: W, height: H, objectFit: 'cover'}} />
        {xep.map((x, i) => <XepRoi key={i} src={x.src} ti={x.ti} o={x.o} t={x.t} roi={roi} />)}
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          {ve.map((n, i) => n.lam === 'khoanh'
            ? <Khoanh key={i} v={vung[n.vung]} t={n.t + 0.45} fps={fps} />
            : <MuiTen key={i} a={vung[n.vung]} b={vung[n.den]} t={n.t + 0.45} fps={fps} />)}
        </svg>
      </div>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)'}} />
      <AbsoluteFill style={{background: '#000', opacity: toi}} />
      {chu.map((n, i) => n.lam === 'so_dem'
        ? <SoDem key={i} so={n.so} chu={n.chu} t={n.t} het={n.het} fps={fps} />
        : <Chu key={i} chu={n.chu} t={n.t} het={n.het} fps={fps} />)}
      <VaoCanh nen={nen} vao={vao} />
    </AbsoluteFill>
  );
};
