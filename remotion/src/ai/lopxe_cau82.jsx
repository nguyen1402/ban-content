import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {src, kep, VANG, AnhNen, MuiTen, VongBut} from './thu_vien.jsx';

/* ---------- LỚP BẢN ĐỒ PHÂN VÙNG SINH THÁI (vẽ bằng SVG, không vẽ lại ảnh) ---------- */
const BanDo = ({mau, doDay}) => {
  const f = useCurrentFrame();
  const p1 = interpolate(f, [0, 22], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p2 = interpolate(f, [5, 27], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p3 = interpolate(f, [11, 33], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p4 = interpolate(f, [16, 38], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const mo = interpolate(f, [8, 30], [0, 1], kep);
  const drift = interpolate(f, [0, 44], [12, -12], kep);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        transform: `translateY(${drift}px)`,
      }}
    >
      <svg width={1920} height={1080}>
        {/* vùng sinh thái 1 */}
        <polygon
          points="300,250 900,175 1245,305 1180,645 700,725 320,600"
          fill={mau}
          fillOpacity={0.12 * mo}
          stroke="none"
        />
        {/* vùng sinh thái 2 */}
        <polygon
          points="700,725 1180,645 1420,765 1330,985 820,1015"
          fill={mau}
          fillOpacity={0.09 * mo}
          stroke="none"
        />
        {/* ranh giới vùng 1 */}
        <path
          d="M 300 250 L 900 175 L 1245 305 L 1180 645 L 700 725 L 320 600 Z"
          fill="none"
          stroke={mau}
          strokeWidth={doDay}
          strokeLinejoin="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - p1}
        />
        {/* ranh giới vùng 2 */}
        <path
          d="M 700 725 L 1180 645 L 1420 765 L 1330 985 L 820 1015 Z"
          fill="none"
          stroke={mau}
          strokeWidth={doDay}
          strokeLinejoin="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - p2}
        />
        {/* đường phân vùng đứt nét chạy ngang */}
        <path
          d="M 210 520 Q 700 450 1180 555 T 1740 470"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={5}
          strokeDasharray="26 20"
          strokeLinecap="round"
          pathLength={1}
          strokeDashoffset={1 - p3}
        />
        {/* đường bình độ phụ */}
        <path
          d="M 380 340 Q 760 280 1120 380"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={3}
          strokeOpacity={0.75}
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - p4}
        />
        <path
          d="M 860 860 Q 1120 800 1330 900"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={3}
          strokeOpacity={0.75}
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - p4}
        />
      </svg>
    </div>
  );
};

/* ---------- KHUNG KÍNH PHÓNG TO CHI TIẾT THỰC VẬT ---------- */
const Kinh = ({size, mau}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 24], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const s = interpolate(f, [0, 20], [0.9, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const sweep = interpolate(f, [8, 74], [-420, 900], kep);
  const c = size / 2;
  const r = c - 26;
  const goc = 54;

  return (
    <div style={{position: 'absolute', left: 0, top: 0, transform: `scale(${s})`, transformOrigin: '50% 50%'}}>
      <svg width={size} height={size}>
        <defs>
          <clipPath id="kinhClip">
            <circle cx={c} cy={c} r={r} />
          </clipPath>
          <linearGradient id="kinhSweep" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(255,255,255,0)" />
            <stop offset="50%" stopColor="rgba(255,255,255,0.42)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>

        <circle cx={c} cy={c} r={r} fill="rgba(255,255,255,0.06)" />

        <g clipPath="url(#kinhClip)">
          <rect
            x={sweep}
            y={-200}
            width={170}
            height={size + 400}
            fill="url(#kinhSweep)"
            transform={`rotate(18 ${c} ${c})`}
          />
        </g>

        <circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={7}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - p}
        />
        <circle
          cx={c}
          cy={c}
          r={r - 22}
          fill="none"
          stroke={mau}
          strokeWidth={3}
          strokeOpacity={0.85}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - p}
        />

        {/* bốn góc ngoặc của khung kính */}
        <g stroke={mau} strokeWidth={9} strokeLinecap="square" opacity={p}>
          <path d={`M ${c - goc} 6 L 12 6 L 12 ${c - goc}`} fill="none" />
          <path d={`M ${c + goc} 6 L ${size - 12} 6 L ${size - 12} ${c - goc}`} fill="none" />
          <path d={`M ${c - goc} ${size - 6} L 12 ${size - 6} L 12 ${c + goc}`} fill="none" />
          <path d={`M ${c + goc} ${size - 6} L ${size - 12} ${size - 6} L ${size - 12} ${c + goc}`} fill="none" />
        </g>
      </svg>
    </div>
  );
};

/* ---------- SCHEMA ---------- */
export const schema = z.object({
  anhBeTong: z.string().describe('Ảnh nền cấu trúc bê tông khô cằn'),
  anhRung: z.string().describe('Ảnh rừng nguyên sinh nhìn từ trên cao'),
  anhThucVat: z.string().describe('Ảnh thảm thực vật phục hồi'),
  mauNhan: z.string().describe('Màu vàng nhấn cho mũi tên, bản đồ và khung kính'),
  muiTenDx: z.number().describe('Độ lệch ngang của mũi tên chỉ dẫn'),
  muiTenDy: z.number().describe('Độ lệch dọc của mũi tên chỉ dẫn'),
  muiTenCong: z.number().describe('Độ cong của mũi tên chỉ dẫn'),
  vongW: z.number().describe('Chiều rộng vòng khoanh vùng tàn phá'),
  vongH: z.number().describe('Chiều cao vòng khoanh vùng tàn phá'),
  kinhSize: z.number().describe('Kích thước khung kính phóng to'),
  netBanDo: z.number().describe('Độ dày nét vẽ bản đồ phân vùng'),
});

/* ---------- CẢNH ---------- */
export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#101010', overflow: 'hidden'}}>
      {/* ===== NHỊP 1 — frame 4: bê tông khô cằn + mũi tên chỉ vùng đất tàn phá ===== */}
      <Interactive.Div
        name="Nền bê tông khô cằn"
        from={0}
        durationInFrames={136}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        <AnhNen anh={src(props.anhBeTong)} tu={1.02} den={1.16} goc="50% 58%" toi={0.12} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên chỉ vùng đất tàn phá"
        from={4}
        durationInFrames={132}
        style={{
          position: 'absolute',
          left: 520,
          top: 690,
          transform: 'scale(1.6)',
          transformOrigin: '0% 50%',
        }}
      >
        <MuiTen dx={props.muiTenDx} dy={props.muiTenDy} cong={props.muiTenCong} />
      </Interactive.Div>

      <Interactive.Div
        name="Vòng khoanh vùng tàn phá"
        from={20}
        durationInFrames={116}
        style={{
          position: 'absolute',
          left: 900,
          top: 250,
          transform: 'scale(1.5)',
          transformOrigin: '50% 50%',
        }}
      >
        <VongBut w={props.vongW} h={props.vongH} />
      </Interactive.Div>

      {/* ===== NHỊP 2 — frame 132: bản đồ phân vùng sinh thái trên tán rừng nguyên sinh ===== */}
      <Interactive.Div
        name="Nền rừng nguyên sinh từ trên cao"
        from={132}
        durationInFrames={44}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        <AnhNen anh={src(props.anhRung)} tu={1.16} den={1.04} goc="50% 50%" toi={0.1} />
      </Interactive.Div>

      <Interactive.Div
        name="Lớp bản đồ phân vùng sinh thái"
        from={132}
        durationInFrames={44}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <BanDo mau={props.mauNhan} doDay={props.netBanDo} />
      </Interactive.Div>

      {/* ===== NHỊP 3 — frame 170: thảm thực vật phục hồi + khung kính phóng to ===== */}
      <Interactive.Div
        name="Nền thảm thực vật phục hồi"
        from={170}
        durationInFrames={100}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        <AnhNen anh={src(props.anhThucVat)} tu={1.02} den={1.16} goc="50% 55%" toi={0.08} />
      </Interactive.Div>

      <Interactive.Div
        name="Khung kính phóng to chi tiết thực vật"
        from={170}
        durationInFrames={100}
        style={{
          position: 'absolute',
          left: 1010,
          top: 190,
          transform: 'scale(1.15)',
          transformOrigin: '50% 50%',
        }}
      >
        <Kinh size={props.kinhSize} mau={props.mauNhan} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
