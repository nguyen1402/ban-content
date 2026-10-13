import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// MINH HOẠ THEO LỜI (13/10 user): sơ đồ nét phẳng trên nền CHÍNH đoạn video đang chiếu, phủ một lớp TỐI để sơ đồ nổi.
// kieu: cau_tao | quy_trinh | vong_doi | mo_phong. Mốc t (giây, tính từ đầu clip) do Python căn theo giọng đọc.
const W = 1920;
const H = 1080;
const FONT = '"Segoe UI", Arial, sans-serif';
const EMOJI = '"Segoe UI Emoji", "Noto Color Emoji", sans-serif';
const CAM = '#ff9a3c';
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const mem = (x) => x * x * (3 - 2 * x);

const Nen = ({nen, mo = true}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#0d1217'}}>
      <AbsoluteFill style={{filter: mo ? 'brightness(0.32) saturate(0.7) blur(7px)' : 'brightness(0.32) saturate(0.7)', transform: 'scale(1.06)'}}>
        {nen.map((c, i) => (
          <Sequence key={i} from={Math.round(c.tu * fps)} durationInFrames={Math.max(1, Math.round(c.dai * fps) + 2)}>
            {c.anh
              ? <Img src={staticFile(c.src)} style={{width: W, height: H, objectFit: 'cover'}} />
              : <OffthreadVideo src={staticFile(c.src)} muted style={{width: W, height: H, objectFit: 'cover'}} />}
          </Sequence>
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.2) 30%, rgba(0,0,0,0.6) 100%)'}} />
    </AbsoluteFill>
  );
};

// độ "bật" (0..1, nảy) của một phần tử xuất hiện ở giây t
const useBat = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (t) => (f < t * fps ? 0 : spring({frame: f - t * fps, fps, config: {damping: 13, stiffness: 140}}));
};

const TieuDe = ({chu}) => {
  const f = useCurrentFrame();
  if (!chu) return null;
  const a = mem(clamp(f / 12, 0, 1));
  return (
    <div style={{position: 'absolute', top: 70, width: W, textAlign: 'center', opacity: a,
      transform: `translateY(${(1 - a) * -20}px)`}}>
      <span style={{color: '#fff', fontSize: 66, fontWeight: 800, fontFamily: FONT, textShadow: '0 4px 18px rgba(0,0,0,0.8)',
        borderBottom: `8px solid ${CAM}`, paddingBottom: 8}}>{chu}</span>
    </div>
  );
};

const O = ({x, y, r, icon, chu, b, nho = false}) => (
  <g transform={`translate(${x},${y}) scale(${0.4 + 0.6 * b})`} opacity={clamp(b * 1.6, 0, 1)}>
    <circle r={r} fill="rgba(255,255,255,0.12)" stroke="#fff" strokeWidth="5" />
    {icon && <text y={4} fontSize={r * 1.05} textAnchor="middle" dominantBaseline="central" style={{fontFamily: EMOJI}}>{icon}</text>}
    {chu && (
      <foreignObject x={-240} y={r + 16} width={480} height={160}>
        <div style={{color: '#fff', fontFamily: FONT, fontSize: nho ? 40 : 48, fontWeight: 700, textAlign: 'center', lineHeight: 1.15,
          textShadow: '0 3px 10px rgba(0,0,0,0.9)'}}>{chu}</div>
      </foreignObject>
    )}
  </g>
);

const MuiTen = ({x1, y1, x2, y2, ve, cong = 0}) => {
  if (ve <= 0) return null;
  const mx = (x1 + x2) / 2 - (y2 - y1) * cong, my = (y1 + y2) / 2 + (x2 - x1) * cong;
  const d = `M${x1},${y1} Q${mx},${my} ${x2},${y2}`;
  const g = Math.atan2(y2 - my, x2 - mx) * 180 / Math.PI;
  return (
    <g>
      <path d={d} stroke={CAM} strokeWidth="8" fill="none" strokeLinecap="round" pathLength="1" strokeDasharray="1"
        strokeDashoffset={1 - ve} />
      {ve >= 0.98 && <path d="M -26 -16 L 4 0 L -26 16 Z" fill={CAM} transform={`translate(${x2},${y2}) rotate(${g})`} />}
    </g>
  );
};

// ---------------------------------------------------------------- cấu tạo: chủ thể giữa, nhãn bộ phận toả quanh
const CauTao = ({chu_the, bieu_tuong, muc}) => {
  const bat = useBat();
  const cx = W / 2, cy = 600, R = 185;
  const n = muc.length;
  const bo = muc.map((m, i) => {
    const g = (-90 + (360 / n) * i + (n % 2 ? 0 : 180 / n)) * Math.PI / 180;
    return {...m, x: cx + Math.cos(g) * 600, y: cy + Math.sin(g) * 330, g};
  });
  return (
    <svg width={W} height={H} style={{position: 'absolute'}}>
      {bo.map((m, i) => {
        const b = bat(m.t);
        const x1 = cx + Math.cos(m.g) * (R + 12), y1 = cy + Math.sin(m.g) * (R + 12);
        const ve = clamp(b, 0, 1);
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x1 + (m.x - x1) * ve} y2={y1 + (m.y - y1) * ve} stroke={CAM} strokeWidth="5"
              strokeDasharray="14 10" />
            <g opacity={clamp(b * 1.5, 0, 1)} transform={`translate(${m.x},${m.y}) scale(${0.5 + 0.5 * b})`}>
              <foreignObject x={-300} y={-56} width={600} height={112}>
                <div style={{display: 'flex', justifyContent: 'center'}}>
                  <div style={{background: 'rgba(255,255,255,0.95)', color: '#1d1a16', fontFamily: FONT, fontSize: 50, fontWeight: 800,
                    padding: '16px 34px', borderRadius: 46, borderLeft: `12px solid ${CAM}`, whiteSpace: 'nowrap',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.5)'}}>{m.chu}</div>
                </div>
              </foreignObject>
            </g>
          </g>
        );
      })}
      <O x={cx} y={cy} r={R} icon={bieu_tuong} b={bat(0.15)} />
      {chu_the && (
        <text x={cx} y={cy + R + 64} textAnchor="middle" fontSize="58" fontWeight="800" fill="#fff" fontFamily={FONT}
          stroke="rgba(0,0,0,0.7)" strokeWidth="8" paintOrder="stroke" opacity={clamp(bat(0.3) * 1.5, 0, 1)}>{chu_the}</text>
      )}
    </svg>
  );
};

// ---------------------------------------------------------------- quy trình: các bước hàng ngang nối mũi tên
const QuyTrinh = ({muc}) => {
  const bat = useBat();
  const n = muc.length;
  const buoc = Math.min(470, 1700 / n);
  const x0 = W / 2 - (buoc * (n - 1)) / 2, y = 540, r = Math.min(150, buoc * 0.32);
  return (
    <svg width={W} height={H} style={{position: 'absolute'}}>
      {muc.map((m, i) => i > 0 && (
        <MuiTen key={'a' + i} x1={x0 + buoc * (i - 1) + r + 18} y1={y} x2={x0 + buoc * i - r - 22} y2={y}
          ve={mem(clamp(bat(m.t) * 1.2, 0, 1))} />
      ))}
      {muc.map((m, i) => <O key={i} x={x0 + buoc * i} y={y} r={r} icon={m.bieu_tuong} chu={m.chu} b={bat(m.t)} nho={n > 4} />)}
    </svg>
  );
};

// ---------------------------------------------------------------- vòng đời: các bước xếp vòng, mũi tên cong nối vòng
const VongDoi = ({muc, giay}) => {
  const bat = useBat();
  const n = muc.length;
  const cx = W / 2, cy = 610, Rx = n <= 3 ? 450 : 560, Ry = 300, r = 120;
  const p = muc.map((m, i) => {
    const g = (-90 + (360 / n) * i) * Math.PI / 180;
    return [cx + Math.cos(g) * Rx, cy + Math.sin(g) * Ry];
  });
  const cuoi = Math.max(...muc.map((m) => m.t)) + 0.7;
  const noi = (i, j, t) => {
    const [x1, y1] = p[i], [x2, y2] = p[j];
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy);
    return (
      <MuiTen key={'a' + i} x1={x1 + dx / L * (r + 16)} y1={y1 + dy / L * (r + 16)} x2={x2 - dx / L * (r + 22)}
        y2={y2 - dy / L * (r + 22)} cong={-0.18} ve={mem(clamp(bat(t) * 1.2, 0, 1))} />
    );
  };
  return (
    <svg width={W} height={H} style={{position: 'absolute'}}>
      {muc.map((m, i) => i > 0 && noi(i - 1, i, m.t))}
      {n > 2 && cuoi < giay - 0.3 && noi(n - 1, 0, cuoi)}
      {muc.map((m, i) => <O key={i} x={p[i][0]} y={p[i][1]} r={r} icon={m.bieu_tuong} chu={m.chu} b={bat(m.t)} nho />)}
    </svg>
  );
};

// ---------------------------------------------------------------- mô phỏng: icon nhân vật diễn hành động
const VI_TRI = [[560, 560], [1360, 560], [960, 800]];
const MoPhong = ({vai, hanh_dong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const bat = useBat();
  const now = f / fps;
  const n = vai.length;
  const goc = vai.map((v, i) => (n === 1 ? [960, 600] : VI_TRI[i]));
  // trạng thái từng vai: vị trí, cỡ, hướng, độ hiện; cộng dồn các hành động đã bắt đầu
  const st = vai.map((v, i) => ({x: goc[i][0], y: goc[i][1], s: 1, lat: 1, op: 1, rung: 0}));
  const them = [];                                           // icon phụ (bầy, toả ra, sinh sôi) + tia va chạm
  hanh_dong.forEach((h, k) => {
    const a = st[h.ai];
    if (!a || now < h.t) return;
    const p = mem(clamp((now - h.t) / 1.1, 0, 1));
    const b = h.toi != null ? st[h.toi] : null;
    const icon = vai[h.ai].bieu_tuong;
    if (b) a.lat = b.x > a.x ? -1 : 1;                       // emoji gốc nhìn TRÁI: quay mặt về phía mục tiêu
    if (h.lam === 'bay_toi' && b) {
      a.x += (b.x - a.x) * 0.55 * p; a.y += (b.y - a.y) * 0.55 * p - Math.sin(p * Math.PI) * 90;
    } else if (h.lam === 'bay_toi') {                       // không có mục tiêu: bay vút lên, đi xa dần
      const q = mem(clamp((now - h.t) / 1.8, 0, 1));
      a.lat = -1; a.x += 700 * q; a.y -= 320 * q; a.s *= 1 - 0.45 * q; a.op = 1 - clamp((q - 0.75) / 0.25, 0, 1);
    } else if (h.lam === 'tan_cong' && b) {
      const lao = Math.sin(clamp((now - h.t) / 0.7, 0, 1) * Math.PI);
      const tx = a.x + (b.x - a.x) * 0.72, ty = a.y + (b.y - a.y) * 0.72;
      a.x += (tx - a.x) * lao; a.y += (ty - a.y) * lao;
      if (now - h.t > 0.3) { b.rung = Math.max(b.rung, 1 - clamp((now - h.t - 0.3) / 0.9, 0, 1)); }
      if (now - h.t > 0.3 && now - h.t < 1.2) them.push({k: 'va' + k, icon: '💥', x: b.x - 40 * a.lat * -1, y: b.y - 60, s: 0.9 + 0.3 * Math.sin((now - h.t) * 20)});
    } else if (h.lam === 'bao_vay' && b) {
      for (let j = 0; j < 6; j++) {
        const g = (j / 6) * 2 * Math.PI + now * 1.2;
        const rr = 230 * p + 40;
        them.push({k: `bv${k}_${j}`, icon, x: b.x + Math.cos(g) * rr, y: b.y + Math.sin(g) * rr * 0.7, s: 0.55 * p});
      }
    } else if (h.lam === 'lan_ra') {
      for (let j = 0; j < 9; j++) {
        const g = (-150 + j * 37.5) * Math.PI / 180, q = mem(clamp((now - h.t - j * 0.08) / 1.3, 0, 1));
        them.push({k: `lr${k}_${j}`, icon, x: a.x + Math.cos(g) * 520 * q, y: a.y + Math.sin(g) * 300 * q, s: 0.5 * (q > 0 ? 1 : 0)});
      }
    } else if (h.lam === 'sinh_soi') {
      for (let j = 0; j < 10; j++) {
        const q = bat(h.t + j * 0.12);
        them.push({k: `ss${k}_${j}`, icon, x: a.x - 300 + (j % 5) * 150, y: a.y + 170 + Math.floor(j / 5) * 120, s: 0.5 * q});
      }
    } else if (h.lam === 'bo_chay') {
      const huong = b ? (a.x >= b.x ? 1 : -1) : 1;
      a.lat = -huong; a.x += huong * 900 * p; a.op = 1 - clamp((p - 0.7) / 0.3, 0, 1);
    } else if (h.lam === 'an' && b) {
      a.x += (b.x - a.x) * 0.5 * p; b.s = Math.min(b.s, 1 - p); a.s = 1 + 0.15 * Math.sin(p * Math.PI * 3);
    } else if (h.lam === 'mang_di' && b) {
      const q = mem(clamp((now - h.t - 0.5) / 1.4, 0, 1));
      a.x += (b.x - a.x) * 0.6 * p; b.x = a.x + 60; b.y = a.y + 70; b.s = Math.min(b.s, 0.6);
      a.x += 900 * q; b.x += 900 * q; a.lat = -1;
    }
  });
  return (
    <svg width={W} height={H} style={{position: 'absolute'}}>
      {them.map((e) => (
        <text key={e.k} x={0} y={0} fontSize={150} textAnchor="middle" dominantBaseline="central" style={{fontFamily: EMOJI}}
          transform={`translate(${e.x},${e.y}) scale(${e.s})`}>{e.icon}</text>
      ))}
      {vai.map((v, i) => {
        const a = st[i];
        const vao = bat(0.1 + 0.15 * i);
        const rx = a.rung ? Math.sin(f * 2.2) * 16 * a.rung : 0;
        return (
          <g key={i} opacity={a.op * clamp(vao * 1.5, 0, 1)} transform={`translate(${a.x + rx},${a.y})`}>
            {a.rung > 0 && <circle r={120} fill="none" stroke="#ff4d3d" strokeWidth={8 * a.rung} opacity={a.rung} />}
            <text x={0} y={0} fontSize={210} textAnchor="middle" dominantBaseline="central" style={{fontFamily: EMOJI}}
              transform={`scale(${a.lat * a.s * (0.4 + 0.6 * vao)},${a.s * (0.4 + 0.6 * vao)})`}>{v.bieu_tuong}</text>
            {a.s > 0.3 && (
              <text y={175} textAnchor="middle" fontSize="50" fontWeight="800" fill="#fff" fontFamily={FONT} stroke="rgba(0,0,0,0.75)"
                strokeWidth="8" paintOrder="stroke">{v.ten}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
};


// ---------------------------------------------------------------- DIỄN CẢNH: ảnh thật đã tách nền diễn theo lời (13/10 user)
const VT_DC = {1: [[960, 540]], 2: [[620, 540], [1300, 540]], 3: [[400, 540], [960, 540], [1520, 540]]};
const O_TEN = {trai: 400, giua: 960, phai: 1520};
const O_RONG = {1: 900, 2: 600, 3: 500};                   // bề ngang tối đa của mỗi vai (px) — không lấn sang vai bên
const NET = 'drop-shadow(0 0 2px #fff) drop-shadow(0 0 2px #fff) drop-shadow(0 14px 22px rgba(0,0,0,0.65))';

const Vat = ({src, x, y, s, op, cao, rong = 900, xoay = 0, rung = 0, ten = ''}) => (
  op <= 0.01 || !src ? null : (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -50%) rotate(${xoay}deg) scale(${s})`,
      opacity: op, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      {rung > 0 && <div style={{position: 'absolute', width: cao * 1.15, height: cao * 1.15, borderRadius: '50%',
        border: `${10 * rung}px solid rgba(255,77,61,${rung})`, top: '50%', left: '50%', transform: 'translate(-50%,-50%)'}} />}
      <Img src={staticFile(src)} style={{maxHeight: cao, maxWidth: rong, objectFit: 'contain', filter: NET}} />
      {ten && <div style={{marginTop: 12, color: '#fff', fontFamily: FONT, fontSize: 38, fontWeight: 800, whiteSpace: 'nowrap',
        maxWidth: rong, overflow: 'hidden', textOverflow: 'ellipsis', background: 'rgba(0,0,0,0.55)', padding: '4px 16px',
        borderRadius: 12}}>{ten}</div>}
    </div>
  )
);

const DienCanh = ({vai, hanh_dong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const bat = useBat();
  const now = f / fps;
  const n = vai.length;
  const n3 = Math.min(3, Math.max(1, n));
  const vt = VT_DC[n3];
  const rong = O_RONG[n3];
  let cao = n <= 1 ? 470 : n === 2 ? 400 : 340;
  // vai "ra sau": ai của xuat_hien / thay_the, hoặc toi của bien_thanh -> ẩn tới lúc đó, đứng ở chỗ vai nó thế / biến từ
  const an = new Set();
  hanh_dong.forEach((h) => {
    if (h.lam === 'xuat_hien' || h.lam === 'thay_the') an.add(h.ai);
    if (h.lam === 'bien_thanh' && h.toi != null) an.add(h.toi);
  });
  // chỗ đứng: theo vi_tri ChatGPT chọn; vai hiện từ đầu chưa có vi_tri thì lấp các chỗ còn trống (trái -> phải)
  const dau = vai.map((v, i) => i).filter((i) => !an.has(i));
  const nDau = Math.max(1, Math.min(4, dau.length));
  const cho = {};
  const dung = new Set();
  vai.forEach((v, i) => { if (v.vi_tri && O_TEN[v.vi_tri] && !an.has(i)) { cho[i] = O_TEN[v.vi_tri]; dung.add(v.vi_tri); } });
  if (nDau >= 4) {                                          // 4 vai đứng cùng lúc: 4 chỗ cách đều, bỏ vi_tri
    dau.forEach((i, k) => { cho[i] = [300, 740, 1180, 1620][Math.min(k, 3)]; });
  }
  const tu_do = (nDau === 1 ? ['giua'] : nDau === 2 ? ['trai', 'phai'] : ['trai', 'giua', 'phai']).filter((k) => !dung.has(k));
  dau.forEach((i) => { if (cho[i] == null) cho[i] = O_TEN[tu_do.shift() || 'giua']; });
  vai.forEach((v, i) => { if (cho[i] == null) cho[i] = O_TEN[v.vi_tri] || 960; });
  cao = nDau <= 1 ? 480 : nDau === 2 ? 420 : nDau === 3 ? 350 : 300;   // cỡ theo số vai ĐANG đứng, không tính vai vào sau
  const rongO = nDau <= 1 ? 900 : nDau === 2 ? 620 : nDau === 3 ? 500 : 400;
  // 13/10 user: "không tấn công mà cứ đè vật thể lên nhau" -> tiến lại thì chỉ tới SÁT CẠNH (khoảng cách tâm KC theo bề
  // rộng ô), không chồng lên; chỉ tan_cong (lao vào rồi lùi), an, ket_hop, mang_di mới được chạm/chồng.
  const KC = rongO * 0.8;
  const toiCanh = (a, b, ty) => {                          // điểm đứng sát cạnh b về phía a đang đứng
    const dau_ = a.x <= b.x ? -1 : 1;
    const tx = b.x + dau_ * KC;
    return Math.abs(tx - a.x) < 40 ? a.x : a.x + (tx - a.x) * ty;
  };
  const st = vai.map((v, i) => {
    // 13/10: vai hiện đúng lúc giọng nhắc tới (v.vao, giây) — không hiện sẵn từ đầu cảnh rồi đứng im
    const vao = an.has(i) || v.vao == null ? 0 : bat(v.vao);
    return {x: cho[i], y: 540 + Math.sin(now * 2.1 + i) * 8, s: 0.5 + 0.5 * vao, op: clamp(vao * 1.5, 0, 1),
      xoay: Math.sin(now * 1.6 + i * 2) * 2.5, rung: 0};
  });
  const them = [];
  let nhan = null;
  hanh_dong.forEach((h, k) => {
    const a = st[h.ai];
    if (!a || now < h.t) return;
    if (h.nhan) nhan = {chu: h.nhan, t: h.t};
    const p = mem(clamp((now - h.t) / 1.0, 0, 1));
    const b = h.toi != null ? st[h.toi] : null;
    const src = vai[h.ai].src;
    if (h.lam === 'xuat_hien') {
      const q = bat(h.t);
      a.op = clamp(q * 1.5, 0, 1); a.s = 0.4 + 0.6 * q;
    } else if (h.lam === 'bien_thanh' && b) {
      const q = bat(h.t + 0.25);
      b.x = a.x; b.y = a.y; b.op = clamp(q * 1.4, 0, 1); b.s = 0.5 + 0.5 * q;
      a.op *= 1 - p; a.s *= 1 - 0.35 * p; a.xoay += 25 * p;
      if (p < 1) them.push({k: 'sang' + k, sang: true, x: a.x, y: a.y, r: 120 + 260 * p, op: 1 - p});
    } else if (h.lam === 'tach_ra') {                       // vỡ / bị cắt thành mảnh nhỏ bắn ra
      a.op *= 1 - p; a.s *= 1 - 0.3 * p;
      for (let j = 0; j < 8; j++) {
        const g = (j / 8) * 2 * Math.PI + 0.4, q = mem(clamp((now - h.t - 0.1) / 1.1, 0, 1));
        if (q > 0) them.push({k: `tr${k}_${j}`, src, x: a.x + Math.cos(g) * 260 * q, y: a.y + Math.sin(g) * 170 * q,
          s: 0.28 * (1 - 0.4 * q)});
      }
    } else if (h.lam === 'ket_hop' && b) {                  // nhập vào nhau: hai vật tiến lại, loé sáng
      a.x += (b.x - a.x) * 0.42 * p; b.x += (a.x - b.x) * 0.3 * p; a.y += (b.y - a.y) * 0.42 * p;
      if (p > 0.6 && p < 1) them.push({k: 'kh' + k, sang: true, x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, r: 80 + 200 * (p - 0.6) / 0.4,
        op: 1 - (p - 0.6) / 0.4});
    } else if (h.lam === 'gam' && b) {                      // gặm dần: áp sát, mổ nhiều lần, mục tiêu rung nhẹ + vụn bay
      const lai = mem(clamp((now - h.t) / 0.5, 0, 1));
      const mo = now - h.t > 0.5 ? Math.abs(Math.sin((now - h.t) * 9)) : 0;
      const sat = toiCanh(a, b, lai);                       // áp SÁT cạnh rồi mổ nhẹ vào mép, không đè hẳn lên
      a.x = sat + (b.x > sat ? 1 : -1) * 0.12 * rongO * mo; a.y += (b.y - a.y) * 0.42 * lai;
      if (now - h.t > 0.5) {
        b.rung = Math.max(b.rung, 0.25);
        for (let j = 0; j < 5; j++) {
          const q = ((now - h.t) * 1.4 + j / 5) % 1;
          them.push({k: `gm${k}_${j}`, vun: true, x: (a.x + b.x) / 2 + Math.cos(j * 1.7) * 140 * q,
            y: (a.y + b.y) / 2 - 40 + Math.sin(j * 2.3) * 60 * q + 160 * q * q, op: 1 - q});
        }
      }
    } else if (h.lam === 'keo_di') {                        // bị kéo / lấy đi khỏi khung
      const q = mem(clamp((now - h.t) / 1.2, 0, 1));
      const huong = a.x >= 960 ? 1 : -1;
      a.x += huong * 1100 * q; a.y -= 140 * q; a.xoay += huong * 18 * q;
    } else if (h.lam === 'thay_the' && b) {                 // trượt vào đúng chỗ của toi, toi bị đẩy ra
      const q = mem(clamp((now - h.t) / 1.1, 0, 1));
      const x0 = cho[h.toi], y0 = 540;                     // CHỖ ĐỨNG BAN ĐẦU của vai bị thế (dù nó đã bị kéo đi)
      const huong = x0 >= 960 ? 1 : -1;
      b.x += huong * 1100 * q; b.op *= 1 - clamp((q - 0.6) / 0.4, 0, 1);
      a.x = x0 - huong * 1100 * (1 - q); a.y = y0; a.op = 1; a.s = 1;
    } else if (h.lam === 'thu_nho') {
      a.s *= 1 - 0.38 * p;
    } else if (h.lam === 'lon_len') {
      a.s *= 1 + 0.55 * p;
    } else if (h.lam === 'bien_mat') {
      a.op *= 1 - p; a.s *= 1 - 0.5 * p;
    } else if (h.lam === 'bay_toi' && b) {                  // tới SÁT CẠNH b, không đè
      a.x = toiCanh(a, b, p); a.y += (b.y - a.y) * 0.5 * p - Math.sin(p * Math.PI) * 90;
    } else if (h.lam === 'bay_toi') {                       // không có đích: lướt ngang TRONG khung (không ra mép)
      const q = mem(clamp((now - h.t) / 1.6, 0, 1));
      const huong = a.x > 960 ? -1 : 1;                      // lượn trong khoảng trống của chính nó (không lấn vai bên)
      a.x += huong * Math.min(420, rongO * 0.3) * Math.sin(q * Math.PI); a.y -= Math.sin(q * Math.PI) * 160;
    } else if (h.lam === 'tan_cong' && b) {
      const lao = Math.sin(clamp((now - h.t) / 0.7, 0, 1) * Math.PI);
      a.x += (b.x - a.x) * 0.62 * lao; a.y += (b.y - a.y) * 0.62 * lao; a.xoay += 12 * lao;
      if (now - h.t > 0.3) b.rung = Math.max(b.rung, 1 - clamp((now - h.t - 0.3) / 0.9, 0, 1));
    } else if (h.lam === 'bao_vay' && b) {
      for (let j = 0; j < 6; j++) {
        const g = (j / 6) * 2 * Math.PI + now * 1.1, rr = 250 * p + 40;
        them.push({k: `bv${k}_${j}`, src, x: b.x + Math.cos(g) * rr, y: b.y + Math.sin(g) * rr * 0.7, s: 0.42 * p});
      }
    } else if (h.lam === 'lan_ra') {
      for (let j = 0; j < 9; j++) {
        const g = (-150 + j * 37.5) * Math.PI / 180, q = mem(clamp((now - h.t - j * 0.08) / 1.3, 0, 1));
        if (q > 0) them.push({k: `lr${k}_${j}`, src, x: a.x + Math.cos(g) * 560 * q, y: a.y + Math.sin(g) * 320 * q, s: 0.36});
      }
    } else if (h.lam === 'sinh_soi') {
      for (let j = 0; j < 12; j++) {
        const q = bat(h.t + j * 0.1);
        const g = j * 2.4, rr = 170 + 26 * j;
        if (q > 0) them.push({k: `ss${k}_${j}`, src, x: a.x + Math.cos(g) * rr, y: a.y + Math.sin(g) * rr * 0.6, s: 0.32 * q});
      }
    } else if (h.lam === 'bo_chay') {
      const huong = b ? (a.x >= b.x ? 1 : -1) : 1;
      a.x += huong * 900 * p; a.op *= 1 - clamp((p - 0.7) / 0.3, 0, 1);
    } else if (h.lam === 'an' && b) {
      a.x += (b.x - a.x) * 0.5 * p; b.s *= 1 - p; b.op *= 1 - p; a.s *= 1 + 0.12 * Math.sin(p * Math.PI * 3);
    } else if (h.lam === 'mang_di' && b) {
      const q = mem(clamp((now - h.t - 0.5) / 1.4, 0, 1));
      a.x += (b.x - a.x) * 0.6 * p; b.x = a.x + 70; b.y = a.y + 90; b.s *= 0.55;
      a.x += 900 * q; b.x += 900 * q;
    }
  });
  const nhanA = nhan ? mem(clamp((now - nhan.t) / 0.35, 0, 1)) : 0;
  return (
    <AbsoluteFill>
      {them.map((e) => (e.vun
        ? <div key={e.k} style={{position: 'absolute', left: e.x - 7, top: e.y - 7, width: 14, height: 14, borderRadius: 4,
            background: '#f3efe6', opacity: e.op, boxShadow: '0 2px 6px rgba(0,0,0,0.5)'}} />
        : e.sang
        ? <div key={e.k} style={{position: 'absolute', left: e.x - e.r, top: e.y - e.r, width: 2 * e.r, height: 2 * e.r,
            borderRadius: '50%', border: `6px solid rgba(255,214,120,${e.op})`, boxShadow: `0 0 40px rgba(255,200,90,${e.op})`}} />
        : <Vat key={e.k} src={e.src} x={e.x} y={e.y} s={e.s} op={1} cao={cao} rong={rongO} />))}
      {vai.map((v, i) => i < 4 && <Vat key={i} src={v.src} x={st[i].x} y={st[i].y} s={st[i].s} op={st[i].op} cao={cao}
        rong={rongO} xoay={st[i].xoay} rung={st[i].rung} ten={v.ten} />)}
      {nhan && (
        <div style={{position: 'absolute', bottom: 90, width: W, display: 'flex', justifyContent: 'center', opacity: nhanA,
          transform: `translateY(${(1 - nhanA) * 24}px)`}}>
          <div key={nhan.chu} style={{background: 'rgba(255,255,255,0.95)', color: '#1d1a16', fontFamily: FONT, fontSize: 54,
            fontWeight: 800, padding: '14px 40px', borderRadius: 50, borderLeft: `14px solid ${CAM}`,
            boxShadow: '0 10px 28px rgba(0,0,0,0.55)'}}>{nhan.chu}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const MinhHoa = ({nen_mo = true, giay = 6, nen = [], kieu = 'quy_trinh', tieu_de = '', chu_the = '', bieu_tuong = '', muc = [], vai = [],
  hanh_dong = []}) => (
  <AbsoluteFill style={{fontFamily: FONT, overflow: 'hidden'}}>
    <Nen nen={nen} mo={nen_mo} />
    <TieuDe chu={kieu === 'cau_tao' || kieu === 'dien_canh' ? '' : tieu_de} />
    {kieu === 'cau_tao' && <CauTao chu_the={chu_the} bieu_tuong={bieu_tuong} muc={muc} />}
    {kieu === 'quy_trinh' && <QuyTrinh muc={muc} />}
    {kieu === 'vong_doi' && <VongDoi muc={muc} giay={giay} />}
    {kieu === 'mo_phong' && <MoPhong vai={vai} hanh_dong={hanh_dong} />}
    {kieu === 'dien_canh' && <DienCanh vai={vai} hanh_dong={hanh_dong} />}
  </AbsoluteFill>
);
