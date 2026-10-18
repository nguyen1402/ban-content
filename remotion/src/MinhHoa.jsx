import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// MINH HOẠ THEO LỜI (13/10 user): sơ đồ nét phẳng trên nền CHÍNH đoạn video đang chiếu, phủ một lớp TỐI để sơ đồ nổi.
// kieu: cau_tao | quy_trinh | vong_doi | mo_phong. Mốc t (giây, tính từ đầu clip) do Python căn theo giọng đọc.
const W = 1920;
const H = 1080;
const FONT = '"Montserrat", "Plus Jakarta Sans", "Inter", -apple-system, system-ui, sans-serif';
const EMOJI = '"Segoe UI Emoji", "Noto Color Emoji", sans-serif';
const GOLD = '#facc15';
const CAM = GOLD;
const CYAN = '#38bdf8';
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const mem = (x) => x * x * (3 - 2 * x);

const Nen = ({nen, mo = true}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#0d1217'}}>
      <AbsoluteFill style={{filter: mo ? 'brightness(0.72) saturate(0.85) blur(2.5px)' : 'brightness(0.82) saturate(0.9)', transform: 'scale(1.02)'}}>
        {nen.map((c, i) => (
          <Sequence key={i} from={Math.round(c.tu * fps)} durationInFrames={Math.max(1, Math.round(c.dai * fps) + 2)}>
            {c.anh
              ? <Img src={staticFile(c.src)} style={{width: W, height: H, objectFit: 'cover'}} />
              : <OffthreadVideo src={staticFile(c.src)} muted style={{width: W, height: H, objectFit: 'cover'}} />}
          </Sequence>
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(11,15,25,0.85) 0%, rgba(11,15,25,0.35) 50%, rgba(11,15,25,0.1) 100%)'}} />
    </AbsoluteFill>
  );
};

// độ "bật" (0..1, nảy) của một phần tử xuất hiện ở giây t
const useBat = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (t) => (f < t * fps ? 0 : spring({frame: f - t * fps, fps, config: {damping: 14, stiffness: 130}}));
};

const TieuDe = ({chu}) => {
  const f = useCurrentFrame();
  if (!chu) return null;
  const a = mem(clamp(f / 12, 0, 1));
  return (
    <div style={{position: 'absolute', top: 70, width: W, textAlign: 'center', opacity: a,
      transform: `translateY(${(1 - a) * -20}px)`}}>
      <span style={{color: '#ffffff', fontSize: 44, fontWeight: 900, fontFamily: FONT, letterSpacing: 2,
        textTransform: 'uppercase', textShadow: '0 4px 24px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)'}}>{chu}</span>
    </div>
  );
};

const O = ({x, y, r, icon, chu, b, nho = false}) => (
  <g transform={`translate(${x},${y}) scale(${0.4 + 0.6 * b})`} opacity={clamp(b * 1.6, 0, 1)}>
    <circle r={r} fill="rgba(11,15,25,0.65)" stroke="rgba(255,255,255,0.3)" strokeWidth="3.5" filter="drop-shadow(0 6px 16px rgba(0,0,0,0.4))" />
    {icon && <text y={4} fontSize={r * 1.0} textAnchor="middle" dominantBaseline="central" style={{fontFamily: EMOJI}}>{icon}</text>}
    {chu && (
      <foreignObject x={-240} y={r + 16} width={480} height={160}>
        <div style={{color: '#fff', fontFamily: FONT, fontSize: nho ? 36 : 42, fontWeight: 700, textAlign: 'center', lineHeight: 1.2,
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

const Vat = ({src, x, y, s, op, cao, rong = 900, xoay = 0, rung = 0, do_ = 0, ten = ''}) => (
  op <= 0.01 || !src ? null : (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -50%) rotate(${xoay}deg) scale(${s})`,
      opacity: op, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      <Img src={staticFile(src)} style={{maxHeight: cao, maxWidth: rong, objectFit: 'contain',
        filter: do_ > 0 ? `${NET} drop-shadow(0 0 ${24 * do_}px rgba(255,40,30,${0.9 * do_})) sepia(${0.5 * do_}) saturate(${1 + 2 * do_}) hue-rotate(${-25 * do_}deg)` : NET}} />
      {ten && <div style={{marginTop: 12, color: '#fff', fontFamily: FONT, fontSize: 38, fontWeight: 800, whiteSpace: 'nowrap',
        maxWidth: rong, overflow: 'hidden', textOverflow: 'ellipsis', background: 'rgba(0,0,0,0.55)', padding: '4px 16px',
        borderRadius: 12}}>{ten}</div>}
    </div>
  )
);

// 14/10 user: khuôn con số (đếm lên + "?" đi liền), so sánh (cột theo tỉ lệ), cơ chế (kính lúp), hành động, trước->sau
const soDem = (chu, p) => {                                // "3 triệu con" -> đếm 0 -> 3; "12.000 lán" -> 0 -> 12.000; "90%"
  const m = String(chu).match(/^([\d.,]+)(.*)$/);
  if (!m) return chu;
  const raw = m[1];
  const vn = /^\d{1,3}(\.\d{3})+$/.test(raw);            // 12.000 = mười hai nghìn (dấu chấm phân nghìn kiểu Việt)
  const v = vn ? parseFloat(raw.replace(/\./g, '')) : parseFloat(raw.replace(',', '.'));
  if (!isFinite(v)) return chu;
  const cur = v * p;
  const thap = (raw.split(/[.,]/)[1] || '').length;
  const txt = vn ? Math.round(cur).toLocaleString('de-DE') : (thap && !vn ? cur.toFixed(thap).replace('.', ',') : String(Math.round(cur)));
  return txt + m[2];
};

const DienCanh = ({vai, hanh_dong, bo_cuc = '', khuon = '', so = '', hoi = false, t_so = 0.6, gia_tri = [], nhan_gt = [],
  chu_tq = ''}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const bat = useBat();
  const now = f / fps;
  const {durationInFrames: N_} = useVideoConfig();
  // 14/10 user "nháy liên tục": hiện ra = mờ dần vào + trượt nhẹ lên (không phóng/nảy); không rung rinh liên tục
  const hien = (t, d = 0.5) => mem(clamp((now - t) / d, 0, 1));
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
  let rongO = nDau <= 1 ? 900 : nDau === 2 ? 620 : nDau === 3 ? 500 : 400;
  const coSo = khuon === 'con_so' && !!so;
  if (n === 1 && !coSo) { cao = 700; rongO = 1300; }       // 14/10 user: vật đứng MỘT MÌNH thì to ra
  if (bo_cuc === 'liet_ke') {                               // 14/10 user: liệt kê = các mục chia CỘT đều, cùng cỡ
    cao = n <= 2 ? 440 : n === 3 ? 400 : n === 4 ? 320 : 260;
    rongO = (W / Math.max(1, n)) * 0.82;
  }
  // 13/10 user: "không tấn công mà cứ đè vật thể lên nhau" -> tiến lại thì chỉ tới SÁT CẠNH (khoảng cách tâm KC theo bề
  // rộng ô), không chồng lên; chỉ tan_cong (lao vào rồi lùi), an, ket_hop, mang_di mới được chạm/chồng.
  const KC = rongO * 0.8;
  const toiCanh = (a, b, ty) => {                          // điểm đứng sát cạnh b về phía a đang đứng
    const dau_ = a.x <= b.x ? -1 : 1;
    const tx = b.x + dau_ * KC;
    return Math.abs(tx - a.x) < 40 ? a.x : a.x + (tx - a.x) * ty;
  };
  // 14/10 user: LIỆT KÊ — mục VỪA được nhắc to ở giữa phía trước; mục nhắc trước thu nhỏ, lùi ra hàng sau (trên), mờ đi.
  const lietKe = bo_cuc === 'liet_ke';
  const lanNhac = vai.map((v, i) => {
    const ts = [];
    if (v.vao != null) ts.push(v.vao);
    hanh_dong.forEach((h) => { if (h.ai === i || h.toi === i) ts.push(h.t); });
    return ts.length ? Math.min(...ts) : null;
  });
  // trạng thái "sau" (đích bien_thanh) thừa hưởng LƯỢT của vật "trước"; vật "trước" đã đổi xong thì không giữ chỗ nữa
  const nguon = {}, doiLuc = {};
  hanh_dong.forEach((h) => { if (h.lam === 'bien_thanh' && h.toi != null) { nguon[h.toi] = h.ai; doiLuc[h.ai] = h.t; } });
  const luot = (i) => (nguon[i] != null ? luot(nguon[i]) : lanNhac[i]);
  const viTriLK = (t) => {                                  // vị trí từng vai theo thứ tự đã được nhắc tới thời điểm t
    const da = vai.map((v, i) => i)
      .filter((i) => lanNhac[i] != null && lanNhac[i] <= t && !(doiLuc[i] != null && doiLuc[i] <= t))
      .sort((a, b) => luot(a) - luot(b) || lanNhac[a] - lanNhac[b]);
    const r = {};
    const cu = da.slice(0, -1);
    // hàng sau: dạt sang HAI BÊN phía trên (chừa giữa cho mục chính), nhỏ 0,45; mục chính thấp hơn ở giữa
    const ben = [[-560, 230], [560, 230], [-820, 330], [820, 330], [-300, 170], [300, 170]];
    cu.slice().reverse().forEach((i, k) => { const [dx, y] = ben[Math.min(k, ben.length - 1)]; r[i] = {x: W / 2 + dx, y, s: 0.45, op: 0.7}; });
    if (da.length) r[da[da.length - 1]] = {x: W / 2, y: 620, s: 1.15, op: 1};
    hanh_dong.forEach((h) => {                             // bản "trước" đang biến: đứng CHUNG chỗ với bản "sau" (hoà tan tại chỗ)
      if (h.lam === 'bien_thanh' && h.toi != null && h.t <= t && r[h.toi]) r[h.ai] = {...r[h.toi]};
    });
    return r;
  };
  let lkNay = null, lkTruoc = null, lkE = 1;
  if (lietKe) {
    // mốc bố cục đổi = lúc có vật mới được nhắc; trượt mượt 0,7 s từ bố cục NGAY TRƯỚC mốc đó sang bố cục mới
    const moc = [...new Set(lanNhac.filter((t) => t != null && t <= now))].sort((a, b) => a - b);
    const tNay = moc.length ? moc[moc.length - 1] : now;
    lkNay = viTriLK(now);
    lkTruoc = moc.length > 1 ? viTriLK(tNay - 0.001) : lkNay;
    lkE = mem(clamp((now - tNay) / 0.7, 0, 1));
  }
  const st = vai.map((v, i) => {
    // 13/10: vai hiện đúng lúc giọng nhắc tới (v.vao, giây) — không hiện sẵn từ đầu cảnh rồi đứng im
    const vao = an.has(i) || v.vao == null ? 0 : hien(v.vao);
    const base = {x: cho[i], y: 540 + (an.has(i) ? 0 : 30 * (1 - vao)), s: 0.94 + 0.06 * vao, op: vao, xoay: 0, rung: 0};
    if (lietKe && lkNay[i]) {
      const A = lkTruoc[i] || lkNay[i], B = lkNay[i];
      if (an.has(i)) { base.s = 1; base.op = 1; }
      base.x = A.x + (B.x - A.x) * lkE; base.y = A.y + (B.y - A.y) * lkE;
      base.s *= A.s + (B.s - A.s) * lkE; base.op *= A.op + (B.op - A.op) * lkE;
    }
    return base;
  });
  if (lietKe) {                                              // cột đều nhau, hiện mờ dần + trượt nhẹ lên, đứng yên
    st.forEach((a, i) => {
      const q = hien(vai[i].vao ?? 0.3);
      a.x = W * (i + 0.5) / n; a.y = 500 + 30 * (1 - q); a.s = 0.94 + 0.06 * q; a.op = q; a.xoay = 0;
    });
  }
  const coChe = khuon === 'co_che';
  const KL = {x: 1290, y: 500, r: 300};                   // kính lúp của khuôn cơ chế
  if (coChe) {
    st.forEach((a, i) => {
      if (i === 0) { a.x = 560; a.y = 540; return; }
      const trong = vai.length - 1;
      a.x = KL.x + (trong > 1 ? ((i - 1) / (trong - 1) - 0.5) * 300 : 0); a.y = KL.y + 30; a.s *= 0.55;
    });
  } else if (coSo) {
    st.forEach((a, i) => { if (i === 0) { a.x = W / 2; a.y = 360 + (a.y - 540); a.s *= 0.85; a.anTen = true; } });   // số nói thay tên
  } else if (khuon === 'so_sanh') {
    st.forEach((a, i) => { if (i < 2) { a.x = i === 0 ? 640 : 1280; a.y = 380; } });
  }
  const them = [];
  let nhan = null;
  // 14/10 user: "không chạy chuyển động nữa — chỉ HIỆN RA ĐÚNG THỨ TỰ; bị tấn công thì hiệu ứng bị tấn công" (nhiều chỗ
  // chuyển động trông "ngáo"). Vai đứng YÊN ở chỗ của mình; mỗi nhịp chỉ đổi trạng thái tại chỗ:
  //   xuất hiện = mờ dần vào; biến thành / thay thế = hoà tan tại chỗ; tấn công / gặm / ăn = đích RUNG ngắn + ỬNG ĐỎ
  //   (bị ăn thì mờ dần sau cú đánh); rời đi (biến mất, kéo đi, bỏ chạy, mang đi, vỡ) = mờ dần tại chỗ;
  //   lớn lên / thu nhỏ = đổi cỡ tại chỗ; sinh sôi / lan ra / bao vây = bản sao HIỆN dần quanh vai, đứng yên;
  //   bay tới / kết hợp = không di chuyển (nhịp chỉ đưa tiêu điểm về hai vai).
  hanh_dong.forEach((h, k) => {
    const a = st[h.ai];
    if (!a || now < h.t) return;
    if (h.nhan) nhan = {chu: h.nhan, t: h.t};
    const b = h.toi != null ? st[h.toi] : null;
    const src = vai[h.ai].src;
    const q = hien(h.t);
    const d = now - h.t;
    if (h.lam === 'xuat_hien') {
      if (lietKe) { a.op *= q; a.s *= 0.94 + 0.06 * q; a.y += 30 * (1 - q); }   // liệt kê: giữ cỡ/độ mờ theo bố cục
      else { a.op = q; a.s = 0.94 + 0.06 * q; a.y += 30 * (1 - q); }
    } else if (h.lam === 'bien_thanh' && b) {
      const q2 = hien(h.t, 0.7);                            // hoà tan tại chỗ: bản trước mờ dần, bản sau hiện dần
      if (lietKe) { a.x = b.x; a.y = b.y; b.op *= q2; a.s = b.s; }
      else { b.x = a.x; b.y = a.y; b.s = a.s; b.op = q2; }
      a.op *= 1 - q2;
    } else if (h.lam === 'thay_the' && b) {                 // vai mới hiện ĐÚNG CHỖ vai cũ, vai cũ mờ đi (không trượt)
      const q2 = hien(h.t, 0.7);
      a.x = b.x; a.y = b.y; a.s = b.s; a.op = q2;
      b.op *= 1 - q2;
    } else if (['tan_cong', 'gam', 'an'].includes(h.lam) && b) {
      b.rung = Math.max(b.rung, clamp(1 - d / 0.8, 0, 1));          // cú đánh: rung ngắn rồi thôi
      b.do_ = Math.max(b.do_ || 0, clamp(1 - d / 1.4, 0, 1));       // ửng đỏ rồi nhạt dần
      if (h.lam === 'an') b.op *= 1 - clamp((d - 0.7) / 0.7, 0, 1); // bị ăn: mờ dần sau cú đánh
    } else if (['bien_mat', 'keo_di', 'bo_chay', 'tach_ra'].includes(h.lam)) {
      a.op *= 1 - q;
    } else if (h.lam === 'mang_di') {
      a.op *= 1 - q;
      if (b) b.op *= 1 - q;
    } else if (h.lam === 'thu_nho') {
      a.s *= 1 - 0.38 * q;
    } else if (h.lam === 'lon_len') {
      a.s *= 1 + 0.45 * q;
    } else if (['sinh_soi', 'lan_ra', 'bao_vay'].includes(h.lam)) {
      const g0 = b || a;
      const so = h.lam === 'sinh_soi' ? 8 : 6;
      for (let j2 = 0; j2 < so; j2++) {
        const g = (j2 / so) * 2 * Math.PI + 0.3, rr = 230 + 40 * (j2 % 2);
        const q3 = hien(h.t + j2 * 0.12, 0.4);             // bản sao hiện LẦN LƯỢT, đứng yên
        if (q3 > 0) them.push({k: `sao${k}_${j2}`, src, x: g0.x + Math.cos(g) * rr * 1.3, y: g0.y + Math.sin(g) * rr * 0.6,
          s: 0.34, op: q3});
      }
    }
  });
  // 13/10 user: TIÊU ĐIỂM THEO LỜI — vai VỪA được nhắc (vừa hiện ra, hoặc là ai/toi của nhịp vừa bắt đầu) to + rõ; vai đã
  // nhắc từ trước nhỏ lại + mờ nhẹ. Chuyển mượt 0,4 s giữa hai lần nhắc. Chỉ khi trên khung có >= 2 vai.
  // ĐÀN: vai "dan" (nhiều con cùng làm) vẽ thêm một bầy bản sao nhỏ quanh nó, bám theo nó
  vai.forEach((v, i) => {
    const a = st[i];
    if (!v.dan || a.op <= 0.05 || true) return;            // 14/10 user: bỏ bầy bản sao xoay quanh (ảnh đã vẽ cả đàn)
    const trongKL = coChe && i > 0;                       // cơ chế: bầy nằm GỌN trong kính lúp, nhỏ hơn
    for (let j = 0; j < 7; j++) {
      const g = j * 0.9 + now * 0.25, rr = (trongKL ? 55 : 120) + (trongKL ? 18 : 30) * (j % 3);
      let x = a.x + Math.cos(g) * rr * 1.3, y = a.y + 40 + Math.sin(g) * rr * 0.55;
      if (trongKL) {
        const dx = x - KL.x, dy = y - KL.y, d = Math.hypot(dx, dy), lim = KL.r - 60;
        if (d > lim) { x = KL.x + dx / d * lim; y = KL.y + dy / d * lim; }
      }
      them.push({k: `dan${i}_${j}`, src: v.src, x, y, s: (trongKL ? 0.3 : 0.42) * a.s});
    }
  });
  const suKien = [];
  vai.forEach((v, i) => { if (v.vao != null && !an.has(i)) suKien.push({t: v.vao, ds: [i]}); });
  hanh_dong.forEach((h) => suKien.push({t: h.t, ds: [h.ai, h.toi].filter((x) => x != null)}));
  suKien.sort((x, y) => x.t - y.t);
  const kHien = suKien.filter((e) => e.t <= now);
  const hienTren = st.filter((a) => a.op > 0.3).length;
  if (!lietKe && kHien.length && hienTren >= 2) {
    const cur = kHien[kHien.length - 1];
    const tr = kHien.length > 1 ? kHien[kHien.length - 2] : null;
    const e = mem(clamp((now - cur.t) / 0.7, 0, 1));
    st.forEach((a, i) => {
      const truoc = tr ? (tr.ds.includes(i) ? 1.12 : 0.78) : 1.0;
      const nay = cur.ds.includes(i) ? 1.12 : 0.78;
      const k = truoc + (nay - truoc) * e;
      a.s *= k;
      a.op *= 0.7 + 0.3 * clamp((k - 0.78) / 0.34, 0, 1);  // vai lùi về sau mờ còn ~70%
    });
  }
  // 13/10: TRÁNH ĐƯỜNG — vai KHÔNG thuộc nhịp hiện tại bị vai khác lấn chỗ (bay tới đáp cạnh vai kia, ngang qua chỗ nó)
  // thì dạt xuống dưới đủ khoảng trống; lượng dạt tính liên tục theo độ lấn nên chuyển động mượt. Cặp được phép chạm
  // (tan_cong, an, ket_hop, mang_di) không đẩy nhau.
  const nhipNay = [...hanh_dong].filter((h) => h.t <= now).pop();
  const dangCham = nhipNay && ['tan_cong', 'an', 'ket_hop', 'mang_di'].includes(nhipNay.lam) && now - nhipNay.t < 1.6
    ? new Set([nhipNay.ai, nhipNay.toi]) : new Set();
  const trongNhip = new Set(nhipNay ? [nhipNay.ai, nhipNay.toi].filter((x) => x != null) : []);
  st.forEach((a, i) => {
    if (true || lietKe || a.op <= 0.3 || trongNhip.has(i)) return;   // 14/10: vai đứng yên -> không cần dạt
    let day = 0;
    st.forEach((b, j) => {
      if (j === i || b.op <= 0.3 || (dangCham.has(i) && dangCham.has(j))) return;
      const lan = KC * 0.9 - Math.abs(a.x - b.x);             // lấn bao nhiêu px theo chiều ngang
      if (lan > 0 && trongNhip.has(j)) day = Math.max(day, mem(Math.min(1, lan / (KC * 0.45))));
    });
    a.y -= day * cao * 1.05;                                // dạt LÊN khoảng trống phía trên (dưới là dải nhãn)
    a.s *= 1 - 0.15 * day;
    a.y = Math.max(a.y, cao * a.s / 2 + 20);               // không bị đẩy lọt khỏi mép trên khung
  });
  if (coChe) {                                              // vai trong kính lúp không ra khỏi vòng
    st.forEach((a, i) => {
      if (i === 0) return;
      const dx = a.x - KL.x, dy = a.y - KL.y, d = Math.hypot(dx, dy), lim = KL.r - 90;
      if (d > lim) { a.x = KL.x + dx / d * lim; a.y = KL.y + dy / d * lim; }
    });
  }
  // 14/10 user: không rung lắc nữa (nhìn như nháy) — bị tác động chỉ ửng đỏ
  // NHÃN KHÔNG ĐÈ NHAU: hai vai đứng quá sát -> ẩn nhãn của vai nhỏ hơn
  st.forEach((a, i) => st.forEach((b, j) => {
    if (i < j && a.op > 0.3 && b.op > 0.3 && Math.abs(a.x - b.x) < 260 && Math.abs(a.y - b.y) < 150) {
      (a.s < b.s ? a : b).anTen = true;
    }
  }));
  const nhanA = nhan ? mem(clamp((now - nhan.t) / 0.35, 0, 1)) : 0;
  const klA = coChe ? mem(clamp((now - (Math.min(...hanh_dong.map((h) => h.t)) - 0.4)) / 0.5, 0, 1)) : 0;
  const soA = khuon === 'con_so' ? hien(Math.min(t_so, ...hanh_dong.map((h) => h.t), vai[0]?.vao ?? 1e9)) : 0;   // số + ảnh hiện cùng lúc          // 14/10 user: số hiện thẳng giá trị cuối, không đếm, không "?"
  const maxGT = Math.max(1e-9, ...(gia_tri || []).map((v) => Math.abs(v)));
  const zoom = 1 + 0.03 * clamp(f / Math.max(1, N_ - 1), 0, 1);
  return (
    <AbsoluteFill style={{transform: `scale(${zoom})`}}>
      {coChe && klA > 0 && (
        <svg width={W} height={H} style={{position: 'absolute'}} opacity={klA}>
          <line x1={720} y1={470} x2={KL.x - KL.r * 0.97} y2={KL.y - 60} stroke="#fff" strokeWidth="4" strokeDasharray="12 10" />
          <line x1={720} y1={610} x2={KL.x - KL.r * 0.97} y2={KL.y + 60} stroke="#fff" strokeWidth="4" strokeDasharray="12 10" />
          <circle cx={KL.x} cy={KL.y} r={KL.r * (0.6 + 0.4 * klA)} fill="rgba(12,18,24,0.88)" stroke="#fff" strokeWidth="8" />
          <circle cx={KL.x} cy={KL.y} r={KL.r * (0.6 + 0.4 * klA) + 10} fill="none" stroke={CAM} strokeWidth="4" />
        </svg>
      )}
      {them.map((e) => (e.vun
        ? <div key={e.k} style={{position: 'absolute', left: e.x - 7, top: e.y - 7, width: 14, height: 14, borderRadius: 4,
            background: '#f3efe6', opacity: e.op, boxShadow: '0 2px 6px rgba(0,0,0,0.5)'}} />
        : e.sang
        ? <div key={e.k} style={{position: 'absolute', left: e.x - e.r, top: e.y - e.r, width: 2 * e.r, height: 2 * e.r,
            borderRadius: '50%', border: `6px solid rgba(255,214,120,${e.op})`, boxShadow: `0 0 40px rgba(255,200,90,${e.op})`}} />
        : <Vat key={e.k} src={e.src} x={e.x} y={e.y} s={e.s} op={e.op ?? 1} cao={cao} rong={rongO} />))}
      {vai.map((v, i) => i < 6 && <Vat key={i} src={v.src} x={st[i].x} y={st[i].y} s={st[i].s} op={st[i].op} cao={cao}
        rong={rongO} xoay={st[i].xoay} rung={st[i].rung} do_={st[i].do_ || 0} ten={st[i].anTen ? '' : v.ten} />)}
      {/* 14/10 user: bỏ dải chữ giai đoạn ở đáy khung diễn cảnh */}
      {khuon === 'tong_quat' && chu_tq && (
        <div style={{position: 'absolute', top: 925, width: W, textAlign: 'center', opacity: hien(vai[0]?.vao ?? 0.3)}}>
          <span style={{fontFamily: FONT, fontWeight: 900, fontSize: 54, color: '#fff', background: 'rgba(0,0,0,0.55)',
            padding: '8px 28px', borderRadius: 14, textShadow: '0 3px 12px #000'}}>{chu_tq}</span>
        </div>
      )}
      {khuon === 'con_so' && so && soA > 0 && (
        <div style={{position: 'absolute', top: 680, width: W, textAlign: 'center', fontFamily: FONT, fontWeight: 900,
          fontSize: 132, color: '#ffd400', letterSpacing: 2, opacity: soA,
          transform: `translateY(${20 * (1 - soA)}px)`,
          textShadow: '0 0 4px #000, 0 6px 28px rgba(0,0,0,0.9)'}}>
          {so}
        </div>
      )}
      {khuon === 'so_sanh' && gia_tri.length === 2 && [0, 1].map((i) => {
        const a = st[i];
        if (!a || a.op < 0.05) return null;
        const t0 = Math.min(...hanh_dong.filter((h) => h.ai === i || h.toi === i).map((h) => h.t), vai[i]?.vao ?? 0.3);
        const g = mem(clamp((now - t0 - 0.3) / 0.9, 0, 1));
        const cao_ = 300 * Math.abs(gia_tri[i]) / maxGT * g;
        return (
          <div key={'cot' + i} style={{position: 'absolute', left: a.x - 70, top: 1020 - cao_, width: 140, height: cao_,
            background: i === 0 ? CAM : '#5aa9ff', borderRadius: '10px 10px 0 0', boxShadow: '0 6px 20px rgba(0,0,0,0.5)'}}>
            <div style={{position: 'absolute', top: -64, width: 300, left: -80, textAlign: 'center', color: '#fff', fontFamily: FONT,
              fontSize: 46, fontWeight: 900, textShadow: '0 3px 12px #000', opacity: g}}>{nhan_gt[i] || ''}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};


// ---------------------------------------------------------------- BẢN ĐỒ AI VẼ (14/10 user): địa điểm nhắc nhanh
// Ảnh bản đồ phủ khung + máy quay chậm (4 kiểu theo nơi), ghim thả xuống ở giữa (AI vẽ nơi đó ở giữa), vòng sáng lan,
// nhãn tên tiếng Việt (mình tự viết — AI không viết chữ Việt đúng).
const TAM_BDV = 0.5 / 0.83;                                // ảnh bản đồ đã cắt mép phải/dưới -> tâm vùng ở ~60% khung
const BanDoVe = ({anh, ten, bien_the = 0}) => {
  const CX = W * TAM_BDV, CY = H * TAM_BDV;
  const f = useCurrentFrame();
  const {fps, durationInFrames: N} = useVideoConfig();
  const p = f / Math.max(1, N - 1);
  // 18/10 user: không cho hiệu ứng mờ dần lúc xuất hiện và kết thúc
  const aOut = 1.0;
  const cam = [
    {s: [1.0, 1.14], x: [0, 0], y: [0, 0], r: [0, 0]},
    {s: [1.18, 1.02], x: [0, 0], y: [0, 0], r: [0, 0]},
    {s: [1.12, 1.12], x: [-50, 50], y: [0, -10], r: [0, 0]},
    {s: [1.06, 1.16], x: [20, -20], y: [15, -15], r: [-1.2, 0.6]},
  ][bien_the % 4];
  const L = (v) => v[0] + (v[1] - v[0]) * mem(p);
  const ghim = spring({frame: f - Math.round(0.45 * fps), fps, config: {damping: 11, stiffness: 120}});
  const nhanA = mem(clamp((f / fps - 0.9) / 0.4, 0, 1));
  const song = ((f / fps) % 1.6) / 1.6;
  return (
    <AbsoluteFill style={{background: '#0d1217', overflow: 'hidden', opacity: aOut}}>
      <AbsoluteFill style={{transformOrigin: `${CX}px ${CY}px`,
        transform: `translate(${L(cam.x) * 0.5}px, ${L(cam.y) * 0.5}px) scale(${L(cam.s)}) rotate(${L(cam.r)}deg)`}}>
        <Img src={staticFile(anh)} style={{width: W, height: H, objectFit: 'cover'}} />
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.55) 100%)'}} />
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {ghim > 0.05 && [0, 0.5].map((d, i) => {
          const q = (song + d) % 1;
          return <circle key={i} cx={CX} cy={CY} r={30 + 170 * q} fill="none" stroke="#ffd400" strokeWidth={5 * (1 - q)}
            opacity={(1 - q) * clamp(ghim, 0, 1)} />;
        })}
        <g transform={`translate(${CX}, ${CY - 260 * (1 - clamp(ghim, 0, 1.2))})`} opacity={clamp(ghim * 2, 0, 1)}>
          <ellipse cx={0} cy={6} rx={22} ry={7} fill="rgba(0,0,0,0.45)" />
          <path d="M0,0 C-10,-22 -30,-34 -30,-58 A30,30 0 1 1 30,-58 C30,-34 10,-22 0,0 Z" fill="#ff4d3d" stroke="#fff" strokeWidth="5" />
          <circle cx={0} cy={-58} r={11} fill="#fff" />
        </g>
      </svg>
      {ten && (
        <div style={{position: 'absolute', left: Math.min(CX + 46, W - 520), top: CY - 120, opacity: nhanA,
          transform: `translateX(${(1 - nhanA) * 30}px)`, display: 'flex', alignItems: 'center'}}>
          <div style={{width: 40 * nhanA, height: 4, background: '#ffd400', marginRight: 10}} />
          <div style={{background: 'rgba(255,255,255,0.95)', color: '#1d1a16', fontFamily: FONT, fontSize: 56, fontWeight: 900,
            padding: '10px 30px', borderRadius: 14, borderLeft: `12px solid ${CAM}`, boxShadow: '0 10px 30px rgba(0,0,0,0.55)',
            whiteSpace: 'nowrap'}}>{ten}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- BẢNG MÀU ĐA DẠNG CHO BIỂU ĐỒ & ĐỒ THỊ (MINIMALIST EDITORIAL)
const THEMES = [
  // 0: Classic Pearl & Slate Sky
  {
    colA: {main: '#38bdf8', dark: '#0369a1', text: '#f8fafc', label: '#94a3b8'},
    colB: {main: '#f43f5e', dark: '#9f1239', text: '#f8fafc', label: '#94a3b8'},
    waveA: '#38bdf8', waveB: '#f43f5e'
  },
  // 1: Emerald Slate & Champagne Gold
  {
    colA: {main: '#10b981', dark: '#047857', text: '#f8fafc', label: '#94a3b8'},
    colB: {main: '#f59e0b', dark: '#b45309', text: '#f8fafc', label: '#94a3b8'},
    waveA: '#10b981', waveB: '#f59e0b'
  },
  // 2: Soft Cyan & Royal Indigo
  {
    colA: {main: '#06b6d4', dark: '#0e7490', text: '#f8fafc', label: '#94a3b8'},
    colB: {main: '#818cf8', dark: '#4338ca', text: '#f8fafc', label: '#94a3b8'},
    waveA: '#06b6d4', waveB: '#818cf8'
  },
  // 3: Warm Coral & Slate Gray
  {
    colA: {main: '#fb923c', dark: '#c2410c', text: '#f8fafc', label: '#94a3b8'},
    colB: {main: '#94a3b8', dark: '#475569', text: '#f8fafc', label: '#cbd5e1'},
    waveA: '#fb923c', waveB: '#94a3b8'
  }
];

function hashStr(str = '') {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

// ---------------------------------------------------------------- HUD COMPONENTS: So sánh / Đồ thị sóng / Con số đơn, Sự kiện, Giải thích, Tái hiện AI
const SoSanhHUD = ({tieu_de, ben_a, ben_b, gia_tri = [], nhan_gt = [], vai = [], dang = '', theme = null}) => {
  const f = useCurrentFrame();
  const {durationInFrames: N} = useVideoConfig();
  // 18/10 user: không cho hiệu ứng mờ dần lúc xuất hiện và kết thúc
  const aIn = 1.0;
  const aOut = 1.0;
  const a = 1.0;

  const tenA = ben_a?.ten || nhan_gt[0] || 'TỔNG SỐ LƯỢNG';
  const valA = ben_a?.gia_tri || (gia_tri[0] != null ? String(gia_tri[0]) : '');
  const tenB = ben_b?.ten || nhan_gt[1] || '';
  const valB = ben_b?.gia_tri || (gia_tri[1] != null ? String(gia_tri[1]) : '');

  // Tự động chọn kiểu hiển thị linh hoạt (không bị gò bó 1 màu, 1 kiểu)
  let kieuDang = dang;
  if (!kieuDang) {
    const txt = (tieu_de + ' ' + tenA + ' ' + tenB + ' ' + valA + ' ' + valB).toLowerCase();
    if (!valB || valB.trim() === '' || !tenB) {
      kieuDang = 'con_so';
    } else if (txt.includes('hiệu suất') || txt.includes('tỷ lệ') || txt.includes('phần trăm') || txt.includes('%') || txt.includes('lọc') || txt.includes('sóng') || txt.includes('mức')) {
      kieuDang = 'song';
    } else {
      kieuDang = 'cot';
    }
  }

  // Chọn bộ màu biến thiên dựa trên tiêu đề / props (tránh bị 1 màu)
  const themeIdx = theme !== null ? (theme % THEMES.length) : (hashStr(tieu_de + tenA) % THEMES.length);
  const themeObj = THEMES[themeIdx];

  // Animation vươn cột & vẽ sóng
  const growA = mem(clamp((f - 4) / 18, 0, 1));
  const growB = mem(clamp((f - 10) / 18, 0, 1));
  const growWave = mem(clamp((f - 4) / 22, 0, 1));

  const maxH = 210;
  const hA = Math.max(50, maxH * 0.72 * growA);
  const hB = Math.max(50, maxH * 0.95 * growB);

  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: a, fontFamily: FONT}}>
      {/* 1. TIÊU ĐỀ Ở ĐỈNH (chỉ chữ trắng tinh tế, đổ bóng sâu, không khung viền) */}
      {tieu_de && kieuDang !== 'con_so' && (
        <div style={{
          position: 'absolute', top: 70, left: 0, right: 0,
          display: 'flex', justifyContent: 'center', pointerEvents: 'none',
          opacity: aIn, transform: `translateY(${(1 - aIn) * -16}px)`, zIndex: 30
        }}>
          <span style={{
            color: '#ffffff', fontSize: 34, fontWeight: 900, letterSpacing: 2, textTransform: 'uppercase',
            textShadow: '0 4px 24px rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.85)'
          }}>
            {tieu_de}
          </span>
        </div>
      )}

      {/* 2. CHẾ ĐỘ: ĐỒ THỊ LƯỢN SÓNG (WAVE TREND CHART) */}
      {kieuDang === 'song' && (
        <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: 90}}>
          <svg width={1400} height={500} viewBox="0 0 1400 500" style={{overflow: 'visible'}}>
            <defs>
              <linearGradient id={`waveGrad_${themeIdx}`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={themeObj.waveA} stopOpacity="0.85" />
                <stop offset="100%" stopColor={themeObj.waveB} stopOpacity="0.95" />
              </linearGradient>
              <linearGradient id={`areaGrad_${themeIdx}`} x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor={themeObj.waveB} stopOpacity="0.22" />
                <stop offset="65%" stopColor={themeObj.waveA} stopOpacity="0.05" />
                <stop offset="100%" stopColor="transparent" stopOpacity="0" />
              </linearGradient>
            </defs>

            {/* Trục hoành & lưới tọa độ đứt nét */}
            <line x1="100" y1="390" x2="1300" y2="390" stroke="rgba(255,255,255,0.2)" strokeWidth="2" />
            <line x1="100" y1="260" x2="1300" y2="260" stroke="rgba(255,255,255,0.08)" strokeWidth="1" strokeDasharray="6 6" />
            <line x1="100" y1="130" x2="1300" y2="130" stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="6 6" />

            {/* Đường dóng dọc tại điểm A & B */}
            <line x1="420" y1="240" x2="420" y2="390" stroke={themeObj.waveA} strokeWidth="1.5" strokeDasharray="5 5" opacity={growA * 0.7} />
            <line x1="980" y1="130" x2="980" y2="390" stroke={themeObj.waveB} strokeWidth="1.5" strokeDasharray="5 5" opacity={growB * 0.7} />

            {/* Diện tích sóng mờ gradient */}
            <path
              d="M 100,390 L 100,350 C 240,350 300,240 420,240 C 600,240 760,130 980,130 C 1140,130 1200,170 1300,170 L 1300,390 Z"
              fill={`url(#areaGrad_${themeIdx})`}
              opacity={growWave}
            />
            {/* Đường cong sóng thanh mảnh, sắc nét */}
            <path
              d="M 100,350 C 240,350 300,240 420,240 C 600,240 760,130 980,130 C 1140,130 1200,170 1300,170"
              fill="none"
              stroke={`url(#waveGrad_${themeIdx})`}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={1500}
              strokeDashoffset={1500 * (1 - growWave)}
            />

            {/* Điểm nút A */}
            <g transform="translate(420, 240)" opacity={growA}>
              <circle r="14" fill={themeObj.waveA} opacity="0.25" />
              <circle r="7" fill="#fff" stroke={themeObj.waveA} strokeWidth="3.5" />
            </g>

            {/* Điểm nút B */}
            <g transform="translate(980, 130)" opacity={growB}>
              <circle r="16" fill={themeObj.waveB} opacity="0.25" />
              <circle r="8" fill="#fff" stroke={themeObj.waveB} strokeWidth="4" />
            </g>
          </svg>

          {/* Nhãn HTML định vị an toàn tuyệt đối - KHÔNG KHUNG HỘP */}
          <div style={{position: 'absolute', width: 1400, height: 500, pointerEvents: 'none'}}>
            {/* Nhãn giá trị A */}
            <div style={{
              position: 'absolute', left: 420, top: 140, transform: 'translateX(-50%)',
              display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: growA
            }}>
              <span style={{
                fontSize: 52, fontWeight: 900, color: '#ffffff', letterSpacing: 1,
                textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.85)'
              }}>
                {valA}
              </span>
            </div>
            <div style={{
              position: 'absolute', left: 420, top: 412, transform: 'translateX(-50%)',
              width: 380, textAlign: 'center', opacity: growA
            }}>
              <span style={{
                color: 'rgba(255,255,255,0.78)', fontSize: 24, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 2,
                textShadow: '0 2px 14px rgba(0,0,0,0.95)'
              }}>
                {tenA}
              </span>
            </div>

            {/* Nhãn giá trị B */}
            <div style={{
              position: 'absolute', left: 980, top: 35, transform: 'translateX(-50%)',
              display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: growB
            }}>
              <span style={{
                fontSize: 56, fontWeight: 900, color: '#ffffff', letterSpacing: 1,
                textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.85)'
              }}>
                {valB}
              </span>
            </div>
            <div style={{
              position: 'absolute', left: 980, top: 412, transform: 'translateX(-50%)',
              width: 380, textAlign: 'center', opacity: growB
            }}>
              <span style={{
                color: 'rgba(255,255,255,0.78)', fontSize: 24, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 2,
                textShadow: '0 2px 14px rgba(0,0,0,0.95)'
              }}>
                {tenB}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 3. CHẾ ĐỘ: HIỂN THỊ CON SỐ ĐƠN LẺ TINH GỌN (KHÔNG KHUNG HỘP, GIỐNG KIỂU CỦA NĂM) */}
      {kieuDang === 'con_so' && (
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none'}}>
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
            opacity: growA, transform: `scale(${0.92 + 0.08 * growA}) translateY(${(1 - growA) * 12}px)`
          }}>
            {/* Nhãn thể loại nhỏ ở trên (nếu có tieu_de riêng) */}
            {tieu_de && (
              <div style={{
                color: 'rgba(255,255,255,0.7)', fontSize: 26, fontWeight: 800,
                letterSpacing: 3, textTransform: 'uppercase', marginBottom: 16,
                textShadow: '0 2px 14px rgba(0,0,0,0.95)'
              }}>
                {tieu_de}
              </div>
            )}
            {/* Giá trị số lớn trắng tinh, đổ bóng sâu y hệt SuKienHUD */}
            <div style={{
              fontSize: 130, fontWeight: 900, color: '#ffffff',
              letterSpacing: 2, lineHeight: 1.05,
              textShadow: '0 4px 24px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.85)'
            }}>
              {valA || valB}
            </div>
            {/* Chú thích phía dưới màu xám bạc thanh lịch, không khung */}
            {(tenA || tenB) && (
              <div style={{
                color: 'rgba(255,255,255,0.78)', fontSize: 32, fontWeight: 700,
                letterSpacing: 2.5, textTransform: 'uppercase', marginTop: 18, maxWidth: 840,
                textShadow: '0 3px 16px rgba(0,0,0,0.95)'
              }}>
                {tenA || tenB}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. CHẾ ĐỘ: BIỂU ĐỒ CỘT SO SÁNH TINH GỌN (MINIMALIST BAR CHART) */}
      {kieuDang === 'cot' && (
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: 120, paddingBottom: 150}}>
          {/* CỘT A */}
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', width: 380}}>
            <div style={{
              fontSize: 52, fontWeight: 900, color: '#ffffff',
              marginBottom: 16, textAlign: 'center',
              textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.85)',
              opacity: growA, transform: `translateY(${(1 - growA) * 16}px)`
            }}>
              {valA}
            </div>
            <div style={{
              width: 140, height: hA,
              background: `linear-gradient(180deg, ${themeObj.colA.main} 0%, ${themeObj.colA.dark} 100%)`,
              borderRadius: '10px 10px 0 0',
              boxShadow: '0 12px 28px rgba(0,0,0,0.4)',
              border: '1px solid rgba(255,255,255,0.18)', borderBottom: 'none'
            }} />
            <div style={{width: 320, height: 2, background: 'rgba(255,255,255,0.22)', marginTop: 2}} />
            <div style={{
              color: 'rgba(255,255,255,0.78)', fontSize: 24, fontWeight: 700,
              letterSpacing: 2, textTransform: 'uppercase', marginTop: 16, textAlign: 'center',
              textShadow: '0 2px 14px rgba(0,0,0,0.95)'
            }}>
              {tenA}
            </div>
          </div>

          {/* CỘT B */}
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', width: 380}}>
            <div style={{
              fontSize: 52, fontWeight: 900, color: '#ffffff',
              marginBottom: 16, textAlign: 'center',
              textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.85)',
              opacity: growB, transform: `translateY(${(1 - growB) * 16}px)`
            }}>
              {valB}
            </div>
            <div style={{
              width: 140, height: hB,
              background: `linear-gradient(180deg, ${themeObj.colB.main} 0%, ${themeObj.colB.dark} 100%)`,
              borderRadius: '10px 10px 0 0',
              boxShadow: '0 12px 28px rgba(0,0,0,0.4)',
              border: '1px solid rgba(255,255,255,0.18)', borderBottom: 'none'
            }} />
            <div style={{width: 320, height: 2, background: 'rgba(255,255,255,0.22)', marginTop: 2}} />
            <div style={{
              color: 'rgba(255,255,255,0.78)', fontSize: 24, fontWeight: 700,
              letterSpacing: 2, textTransform: 'uppercase', marginTop: 16, textAlign: 'center',
              textShadow: '0 2px 14px rgba(0,0,0,0.95)'
            }}>
              {tenB}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const SuKienHUD = ({nam, tieu_de, cac_nam}) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames: N} = useVideoConfig();
  const now = f / fps;

  // 18/10 user: không cho hiệu ứng mờ dần lúc xuất hiện và kết thúc
  const aOut = 1.0;

  if (cac_nam && cac_nam.length > 1) {
    return (
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        pointerEvents: 'none', opacity: aOut
      }}>
        <div style={{display: 'flex', alignItems: 'center', gap: 36}}>
          {cac_nam.map((it, idx) => {
            const isShown = now >= it.t;
            if (!isShown) return null;
            const itemFrame = Math.max(0, f - Math.round(it.t * fps));
            const itemIn = mem(clamp(itemFrame / 8, 0, 1));
            const itemScale = 0.88 + 0.12 * itemIn;
            return (
              <React.Fragment key={idx}>
                {idx > 0 && (
                  <span style={{
                    fontSize: 60, color: 'rgba(255,255,255,0.45)',
                    opacity: itemIn, transform: `scale(${itemIn})`,
                    textShadow: '0 2px 10px rgba(0,0,0,0.8)'
                  }}>
                    •
                  </span>
                )}
                <span style={{
                  fontSize: 130, fontWeight: 900, fontFamily: FONT, letterSpacing: 4,
                  color: '#ffffff',
                  textShadow: '0 4px 24px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)',
                  opacity: itemIn, transform: `scale(${itemScale})`
                }}>
                  {it.nam}
                </span>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    );
  }

  // Mốc sự kiện đơn (không có khung border đen, chỉ chữ trắng tinh trên nền tối)
  const aIn = 1.0;
  const a = 1.0;
  const scale = 1.0;
  const chuMoc = nam || tieu_de || '';

  return (
    <div style={{
      position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      pointerEvents: 'none'
    }}>
      <div style={{
        textAlign: 'center', opacity: a, transform: `scale(${scale}) translateY(${(1 - aIn) * 16}px)`
      }}>
        <div style={{
          fontSize: 130, fontWeight: 900, fontFamily: FONT, letterSpacing: 4, textTransform: 'uppercase',
          color: '#ffffff',
          textShadow: '0 4px 24px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)'
        }}>
          {chuMoc}
        </div>
      </div>
    </div>
  );
};

const GiaiThichHUD = ({tieu_de, cac_buoc = [], muc = []}) => {
  const f = useCurrentFrame();
  // 18/10 user: không cho hiệu ứng mờ dần lúc xuất hiện và kết thúc
  const a = 1.0;
  const bat = useBat();
  const ds = cac_buoc && cac_buoc.length ? cac_buoc : muc;
  const n = Math.min(4, Math.max(2, ds.length));

  return (
    <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      {tieu_de && (
        <div style={{marginBottom: 44, opacity: a, transform: `translateY(${(1 - a) * -20}px)`}}>
          <span style={{color: '#ffffff', fontSize: 38, fontWeight: 900, fontFamily: FONT, letterSpacing: 2, textTransform: 'uppercase',
            textShadow: '0 4px 24px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.8)'}}>{tieu_de}</span>
        </div>
      )}
      <div style={{display: 'flex', alignItems: 'center', gap: 32, maxWidth: 1800, padding: '0 40px'}}>
        {ds.slice(0, n).map((m, i) => {
          const t = m.t != null ? m.t : 0.3 * i;
          const b = bat(t);
          const chu = m.chu || m.text || '';
          return (
            <React.Fragment key={i}>
              <div style={{
                flex: 1, minWidth: 280, textAlign: 'center',
                transform: `translateY(${(1 - b) * 24}px) scale(${0.9 + 0.1 * b})`, opacity: b
              }}>
                <div style={{
                  color: '#38bdf8', fontSize: 24, fontWeight: 900, letterSpacing: 2, marginBottom: 12,
                  textShadow: '0 2px 12px rgba(0,0,0,0.9)'
                }}>
                  BƯỚC {i + 1}
                </div>
                <div style={{color: '#ffffff', fontSize: 34, fontWeight: 800, lineHeight: 1.35, fontFamily: FONT,
                  textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.8)'}}>
                  {chu}
                </div>
              </div>
              {i < n - 1 && (
                <div style={{opacity: b, transform: `scale(${b})`}}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="#ffffff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- TÁI HIỆN TƯ LIỆU AI ĐA PHÂN CẢNH (SEQUENTIAL MONTAGE - KHÔNG CHỮ, CHUYỂN CẢNH MƯỢT KHỚP VOICE)
const TaiHienHUD = ({anh, ds_anh = [], diem_chuyen = []}) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const list = (ds_anh && ds_anh.length) ? ds_anh : (anh ? [anh] : []);
  const n = Math.max(1, list.length);

  // 18/10 user: Không cho hiệu ứng mờ dần lúc xuất hiện và kết thúc
  const aOut = 1.0;

  // 1 ảnh đơn: zoom lia máy Ken Burns chậm rãi
  if (n === 1) {
    const progress = f / Math.max(1, durationInFrames - 1);
    const zoom = 1.0 + 0.08 * progress;
    return (
      <AbsoluteFill style={{background: '#0d1217', overflow: 'hidden'}}>
        <AbsoluteFill style={{transform: `scale(${zoom})`, transformOrigin: 'center center'}}>
          <Img src={staticFile(list[0])} style={{width: W, height: H, objectFit: 'cover'}} />
        </AbsoluteFill>
        <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.48) 100%)', pointerEvents: 'none'}} />
      </AbsoluteFill>
    );
  }

  // Chuỗi nhiều ảnh (2-3 tấm): Sequential Montage khớp chính xác theo từng mốc hành động của lời đọc
  // Thời gian hòa tan crossfade mượt mà (0.5s - 0.6s)
  const fadeFrames = Math.min(Math.round(fps * 0.55), Math.max(8, Math.round((durationInFrames / n) * 0.3)));
  const halfFade = Math.round(fadeFrames / 2);

  const shotStarts = list.map((_, i) => {
    if (diem_chuyen && diem_chuyen[i] != null && diem_chuyen[i] >= 0) {
      return Math.round(diem_chuyen[i] * fps);
    }
    return Math.round(i * (durationInFrames / n));
  });

  return (
    <AbsoluteFill style={{background: '#0d1217', overflow: 'hidden'}}>
      {list.map((src, i) => {
        const startFrame = shotStarts[i];
        const nextStart = (i < n - 1) ? Math.max(startFrame + fadeFrames, shotStarts[i + 1]) : durationInFrames;
        const shotDuration = Math.max(1, nextStart - startFrame);
        const shotProgress = clamp((f - startFrame) / shotDuration, 0, 1);

        // Chuyển động lia máy Ken Burns chậm rãi (slow motion) nối tiếp nhau theo từng góc quay
        // Shot 0: Zoom in nhẹ nhàng + pan phải
        // Shot 1: Zoom out nhẹ nhàng + pan trái
        // Shot 2: Push in trực diện cận cảnh
        const zoom = (i % 2 === 0) ? (1.0 + 0.07 * shotProgress) : (1.06 - 0.05 * shotProgress);
        const panX = (i === 1) ? (-18 + 36 * shotProgress) : (i === 2) ? (16 - 32 * shotProgress) : (8 * shotProgress);

        // Hòa tan chéo đón đầu voice: chuyển cảnh bắt đầu trước mốc voice halfFade frame
        // để ngay đúng lúc giọng đọc nói đến hành động đó thì ảnh mới đã hiện rõ nét
        let opacity = 1.0;
        if (i > 0) {
          const transStart = Math.max(0, startFrame - halfFade);
          const transProgress = clamp((f - transStart) / Math.max(1, fadeFrames), 0, 1);
          // Đường cong hòa tan mượt mà (sinusoidal ease)
          const easeIn = 0.5 - 0.5 * Math.cos(Math.PI * transProgress);
          opacity = Math.min(opacity, easeIn);
        }
        if (i < n - 1) {
          const transOutStart = Math.max(0, nextStart - halfFade);
          const transOutProgress = clamp((f - transOutStart) / Math.max(1, fadeFrames), 0, 1);
          const easeOut = 0.5 + 0.5 * Math.cos(Math.PI * transOutProgress);
          opacity = Math.min(opacity, easeOut);
        }

        const renderStart = (i > 0) ? startFrame - halfFade - 2 : 0;
        const renderEnd = (i < n - 1) ? nextStart + halfFade + 2 : durationInFrames + 2;
        if (f < renderStart || f > renderEnd) return null;

        return (
          <AbsoluteFill key={i} style={{opacity, transform: `scale(${zoom}) translate(${panX}px, 0)`, transformOrigin: 'center center'}}>
            <Img src={staticFile(src)} style={{width: W, height: H, objectFit: 'cover'}} />
          </AbsoluteFill>
        );
      })}
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.48) 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};

export const MinhHoa = ({
  chu_tq = '', khuon = '', so = '', hoi = false, t_so = 0.6, gia_tri = [], nhan_gt = [], bo_cuc = '',
  anh = '', ten = '', bien_the = 0, nen_mo = true, giay = 6, nen = [], kieu = 'quy_trinh', tieu_de = '',
  chu_the = '', bieu_tuong = '', muc = [], vai = [], hanh_dong = [],
  ben_a = null, ben_b = null, nam = '', cac_buoc = [], mo_ta = '', ds_anh = [], diem_chuyen = [],
  dang = '', theme = null, cac_nam = null
}) => (
  <AbsoluteFill style={{fontFamily: FONT, overflow: 'hidden'}}>
    {kieu !== 'ban_do_ve' && kieu !== 'tai_hien' && <Nen nen={nen} mo={nen_mo} />}
    {kieu === 'tai_hien' && <TaiHienHUD anh={anh} ds_anh={ds_anh} diem_chuyen={diem_chuyen} />}
    {(kieu === 'so_sanh' || kieu === 'song' || kieu === 'con_so') && (
      <SoSanhHUD tieu_de={tieu_de} ben_a={ben_a} ben_b={ben_b} gia_tri={gia_tri} nhan_gt={nhan_gt} vai={vai} dang={dang || (kieu !== 'so_sanh' ? kieu : '')} theme={theme} />
    )}
    {kieu === 'su_kien' && <SuKienHUD nam={nam || so} tieu_de={tieu_de || chu_tq} cac_nam={cac_nam} anh={anh} />}
    {kieu === 'giai_thich' && <GiaiThichHUD tieu_de={tieu_de} cac_buoc={cac_buoc} muc={muc} />}
    {kieu === 'cau_tao' && <CauTao chu_the={chu_the} bieu_tuong={bieu_tuong} muc={muc} />}
    {kieu === 'quy_trinh' && <GiaiThichHUD tieu_de={tieu_de} muc={muc} />}
    {kieu === 'vong_doi' && <VongDoi muc={muc} giay={giay} />}
    {kieu === 'dien_canh' && (
      khuon === 'so_sanh' ? <SoSanhHUD tieu_de={tieu_de} ben_a={ben_a} ben_b={ben_b} gia_tri={gia_tri} nhan_gt={nhan_gt} vai={vai} dang={dang} theme={theme} /> :
      khuon === 'con_so' ? <SoSanhHUD tieu_de={tieu_de} ben_a={ben_a || {ten: nhan_gt[0] || tieu_de, gia_tri: so || gia_tri[0]}} dang="con_so" theme={theme} /> :
      khuon === 'su_kien' ? <SuKienHUD nam={nam || so} tieu_de={tieu_de || chu_tq} cac_nam={cac_nam} anh={anh} /> :
      <DienCanh vai={vai} hanh_dong={hanh_dong} bo_cuc={bo_cuc} khuon={khuon} so={so} hoi={hoi} t_so={t_so} gia_tri={gia_tri} nhan_gt={nhan_gt} chu_tq={chu_tq} />
    )}
    {kieu === 'ban_do_ve' && <BanDoVe anh={anh} ten={ten} bien_the={bien_the} />}
  </AbsoluteFill>
);
