import React from 'react';
import {AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {tinhHieuUng, kieuBoc} from './hieu_ung_tinh.js';

// 03/11 user: THƯ VIỆN DÙNG CHUNG cho các cảnh nhấn ý do AI tự viết code (remotion/src/ai/<dự án>_cau<n>.jsx). Mọi thành
// phần chạy theo khung hình CỤC BỘ (đặt trong <Interactive.Div from=… durationInFrames=…>: khung 0 = lúc nó xuất hiện),
// không rung / lắc, dùng được ngay mà không cần tự viết lại. Kiểu đã được user duyệt (nhãn có đường dẫn, chữ nổi có vạch
// vàng, số đếm, vòng bút, mũi tên vẽ dần).
// 03/11 (chạy thử cả bài: AI hay ghi '/public/nhan_y/…' -> staticFile báo lỗi): bỏ tiền tố '/public/', 'public/', '/'
export const src = (s) => (!s ? '' : /^(https?:|data:|file:)/.test(s) ? s : staticFile(String(s).replace(/^\/?(public\/)?/, '')));
export const kep = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
export const FONT = '"Segoe UI", "Be Vietnam Pro", Arial, sans-serif';
export const VANG = '#ffd23f';
export const EM = Easing.bezier(0.45, 0, 0.2, 1);

// ảnh phủ kín khung, đẩy chậm từ `tu` tới `den` lần phóng (Ken Burns, không lắc); goc = điểm phóng "50% 50%"
// 04/11 (lopxe 4/6 cảnh nền nhoè nâu): AI hay hiểu tu/den là SỐ KHUNG (tu=0 den=190 -> phóng 190 lần) và goc là số
// -> giá trị vô lý thì về mặc định (phóng hợp lý chỉ trong 0.5..3)
const _phong = (v, mac) => (typeof v === 'number' && v >= 0.5 && v <= 3 ? v : mac);
export const AnhNen = ({anh, tu: tu0 = 1.0, den: den0 = 1.08, goc: goc0 = '50% 50%', toi = 0, style}) => {
  const f = useCurrentFrame();
  const {durationInFrames: D} = useVideoConfig();
  const tu = _phong(tu0, 1.0), den = _phong(den0, tu * 1.08);
  const goc = typeof goc0 === 'string' && goc0.trim() ? goc0 : '50% 50%';
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover', transformOrigin: goc,
        transform: `scale(${interpolate(f, [0, D], [tu, den], kep)})`, filter: toi ? `brightness(${1 - toi})` : undefined}} />
    </AbsoluteFill>
  );
};

// 04/11 user ("ảnh nền cứ phóng to dần, 1 màu"): ảnh phủ kín khung LIA chậm theo huong ('trai' | 'phai' | 'len' | 'xuong'),
// quang = số px đi được trong cả khối; ảnh phóng sẵn `phong` lần để không lộ mép
export const AnhLia = ({anh, huong = 'trai', quang = 160, phong = 1.15, toi = 0, style}) => {
  const f = useCurrentFrame();
  const {durationInFrames: D} = useVideoConfig();
  const q = Math.min(Math.abs(quang), 1920 * (phong - 1) / 2 - 4);
  const d = interpolate(f, [0, D], [-q, q], {...kep, easing: Easing.inOut(Easing.quad)});
  const [x, y] = huong === 'phai' ? [-d, 0] : huong === 'len' ? [0, d] : huong === 'xuong' ? [0, -d] : [d, 0];
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover',
        transform: `translate(${x}px, ${y}px) scale(${phong})`, filter: toi ? `brightness(${1 - toi})` : undefined}} />
    </AbsoluteFill>
  );
};

// chữ lớn nổi lên từng chữ, vạch vàng quét dưới (co = cỡ chữ px)
export const ChuNoi = ({chu, co = 96, mau = '#fff', vach = true}) => {
  const f = useCurrentFrame();
  const tu = String(chu).split(/\s+/);
  const v = interpolate(f, [4, 14 + tu.length * 2], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'relative', display: 'inline-block', padding: '6px 22px', whiteSpace: 'nowrap'}}>
      {vach ? <div style={{position: 'absolute', left: 10, right: 10, bottom: 10, height: co * 0.26, background: VANG, opacity: 0.85,
        transformOrigin: '0 50%', transform: `scaleX(${v})`}} /> : null}
      {tu.map((w, i) => {
        const p = interpolate(f, [i * 2, i * 2 + 9], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
        return (
          <span key={i} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom', marginRight: co * 0.2}}>
            <span style={{display: 'inline-block', transform: `translateY(${(1 - p) * 110}%)`, fontFamily: FONT, fontWeight: 900,
              fontSize: co, color: mau, lineHeight: 1.1, textShadow: '0 4px 18px rgba(0,0,0,0.85)'}}>{w}</span>
          </span>
        );
      })}
    </div>
  );
};

// số đếm lên trong `giay` giây (ngăn nghìn bằng dấu chấm kiểu Việt), nhãn đơn vị vàng bên dưới
export const SoDem = ({so, don_vi = '', giay = 1.2, co = 200, tu = 0}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = interpolate(f, [0, giay * fps], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const n = tu + (Number(so) - tu) * p;
  const le = Math.abs(Number(so)) < 100 && Number(so) % 1 !== 0 ? 1 : 0;
  const s = n.toFixed(le).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return (
    <div data-so={so} data-dv={don_vi} style={{textAlign: 'center', fontFamily: FONT}}>
      <div style={{fontWeight: 900, fontSize: co, color: '#fff', lineHeight: 1, textShadow: '0 8px 30px rgba(0,0,0,0.85)',
        transform: `scale(${interpolate(f, [0, 8], [0.7, 1], {...kep, easing: Easing.out(Easing.back(1.6))})})`}}>{s}</div>
      {don_vi ? <div style={{marginTop: 8, fontWeight: 800, fontSize: co * 0.32, color: VANG, textShadow: '0 4px 16px rgba(0,0,0,0.85)',
        opacity: interpolate(f, [8, 16], [0, 1], kep)}}>{don_vi}</div> : null}
    </div>
  );
};

// nhãn chú thích: chấm tại điểm (0, 0) của khối + đường dẫn tới hộp chữ ở (dx, dy) px
export const Nhan = ({chu, dx = 220, dy = -120, co = 50}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 10], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const pn = interpolate(f, [6, 16], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const phai = dx >= 0;
  return (
    <div style={{position: 'relative', width: 0, height: 0}}>
      <svg width={1} height={1} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <g style={{filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.8))'}}>
          <line x1={0} y1={0} x2={dx * p} y2={dy * p} stroke="#fff" strokeWidth={4} />
          <circle cx={0} cy={0} r={8} fill="#fff" />
        </g>
      </svg>
      <div style={{position: 'absolute', left: phai ? dx + 10 : undefined, right: phai ? undefined : -dx + 10, top: dy - co * 0.8,
        opacity: pn, whiteSpace: 'nowrap', fontFamily: FONT, fontWeight: 800, fontSize: co, color: '#fff', padding: '8px 22px',
        background: 'rgba(10,12,14,0.74)', [phai ? 'borderLeft' : 'borderRight']: `7px solid ${VANG}`,
        boxShadow: '0 8px 24px rgba(0,0,0,0.45)'}}>{chu}</div>
    </div>
  );
};

// vòng bút vàng vẽ dần ôm khối rộng w × cao h (tâm khối = tâm vòng)
export const VongBut = ({w = 300, h = 200, day = 8, mau = VANG}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 14], [0, 1], {...kep, easing: Easing.bezier(0.3, 0, 0.2, 1)});
  const rx = w / 2, ry = h / 2, L = Math.PI * (rx + ry) * 1.12;
  const pts = [];
  for (let i = 0; i <= 72; i++) {
    const a = -Math.PI * 0.6 + (i / 72) * Math.PI * 2.1;
    pts.push(`${rx + Math.cos(a) * rx},${ry + Math.sin(a) * ry}`);
  }
  return (
    <svg width={w} height={h} style={{overflow: 'visible', display: 'block'}}>
      <polyline points={pts.join(' ')} fill="none" stroke={mau} strokeWidth={day} strokeLinecap="round"
        strokeDasharray={L} strokeDashoffset={L * (1 - p)} style={{filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.6))'}} />
    </svg>
  );
};

// mũi tên cong vẽ dần từ (0, 0) tới (dx, dy) px; cong = độ võng (px)
export const MuiTen = ({dx = 400, dy = 0, cong = -120, day = 9, mau = VANG}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 16], [0, 1], {...kep, easing: Easing.bezier(0.3, 0, 0.2, 1)});
  const mx = dx / 2, my = dy / 2 + cong;
  const L = Math.hypot(dx, dy) * 1.3 + Math.abs(cong);
  const g = Math.atan2(dy - my, dx - mx);
  const dau = [[0, 0], [-34, -16], [-34, 16]].map(([u, v]) => `${dx + u * Math.cos(g) - v * Math.sin(g)},${dy + u * Math.sin(g) + v * Math.cos(g)}`);
  return (
    <svg width={1} height={1} style={{overflow: 'visible', display: 'block'}}>
      <g style={{filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.6))'}}>
        <path d={`M0,0 Q${mx},${my} ${dx},${dy}`} fill="none" stroke={mau} strokeWidth={day} strokeLinecap="round"
          strokeDasharray={L} strokeDashoffset={L * (1 - p)} />
        <polygon points={dau.join(' ')} fill={mau} opacity={p > 0.92 ? 1 : 0} />
      </g>
    </svg>
  );
};

// hiện dần (mờ + phóng nhẹ) khi khối xuất hiện, mờ đi ở `het` khung cuối
export const HienDan = ({children, vao = 8, het = 0}) => {
  const f = useCurrentFrame();
  const {durationInFrames: D} = useVideoConfig();
  const o = interpolate(f, [0, vao], [0, 1], kep) * (het ? interpolate(f, [D - het, D], [1, 0], kep) : 1);
  return <div style={{opacity: o, transform: `scale(${interpolate(f, [0, vao], [0.94, 1], {...kep, easing: Easing.out(Easing.cubic)})})`}}>{children}</div>;
};

// 03/11 user ("lúc sửa tôi không nghe thấy nó đọc thế nào thì sao mà sửa"): bọc cảnh với ĐÚNG đoạn giọng đọc của câu —
// nghe được trong Studio và trong video xem trước 🖼; clip trên bản nháp CapCut vẫn tắt tiếng (đã có track giọng riêng)
// 05/11 user (sửa hiệu ứng trong 🎚 Sửa lớp): bọc NỘI DUNG một lớp Interactive.Div — hiệu ứng vào / ra / chuyển động liên
// tục theo khung CỤC BỘ của lớp (công thức chung với trình sửa lớp: hieu_ung_tinh.js). kieu 'day' = phóng quanh tâm lớp,
// 'goc' = lớp dời góc (chữ / thẻ nhỏ) — phóng quanh góc trên trái.
export const HieuUng = ({vao = '', ra = '', khung = 12, lien = '', kieu = 'day', children}) => {
  const f = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return <div style={{...kieuBoc(kieu), ...tinhHieuUng(f, durationInFrames, {vao, ra, khung, lien})}}>{children}</div>;
};

export const coGiong = (C, giong) => {
  const CoGiong = (p) => (<>{React.createElement(C, p)}{giong ? <Audio src={src(giong)} /> : null}</>);
  return CoGiong;
};
