import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anhToanCanh: z.string().describe('Ảnh toàn cảnh lòng suối Brawley Wash khô cằn'),
  anhBanDo: z.string().describe('Ảnh bản đồ định vị bang Arizona (khung inset)'),
  anhLopXe: z.string().describe('Ảnh cụm lốp xe cũ nhồi đầy sỏi'),
  anhThanhThep: z.string().describe('Ảnh các thanh thép liên kết cụm lốp'),
  anhCatLop: z.string().describe('Ảnh lát cắt cấu trúc lốp chôn sâu dưới lòng suối'),
  anhLuQuet: z.string().describe('Ảnh lũ quét mùa hè tại Brawley Wash'),
  chuChinh: z.string().describe('Chữ chính duy nhất của cảnh'),
  coChu: z.number().describe('Cỡ chữ chính (px)'),
  mauChu: z.string().describe('Màu chữ chính'),
  mauGach: z.string().describe('Màu gạch chân dưới chữ'),
  mauNet: z.string().describe('Màu nét vẽ chú thích (vòng, mũi tên, đường định vị)'),
  doDayNet: z.number().describe('Độ dày nét chú thích (px)'),
  rongGachChan: z.number().describe('Chiều dài gạch chân (px)'),
  zoomNhe: z.number().describe('Mức zoom nhẹ của ảnh nền'),
  zoomManh: z.number().describe('Mức zoom mạnh (cú đẩy vào) của ảnh nền'),
  quangPan: z.number().describe('Quãng lia ngang của ảnh nhịp 3 (px)'),
  doToi: z.number().describe('Độ tối phủ lên ảnh nền (0..0.5)'),
});

/* ---------- khối chữ lớn hiện từng từ ---------- */
const ChuLon = ({chu, co, mau, mauGach, rongGach}) => {
  const f = useCurrentFrame();
  const words = String(chu).split(' ');
  const gachP = interpolate(f, [16, 40], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'relative'}}>
      <div style={{display: 'flex', alignItems: 'flex-end'}}>
        {words.map((w, i) => {
          const p = interpolate(f, [i * 10, i * 10 + 14], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
          return (
            <span
              key={i}
              style={{
                fontFamily: FONT,
                fontSize: co,
                fontWeight: 900,
                color: mau,
                letterSpacing: 6,
                marginRight: 34,
                whiteSpace: 'nowrap',
                opacity: p,
                transform: `translateY(${(1 - p) * 44}px)`,
                textShadow: '0 8px 28px rgba(0,0,0,0.65)',
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
      <div
        style={{
          height: 12,
          width: rongGach * gachP,
          background: mauGach,
          borderRadius: 6,
          marginTop: 10,
          boxShadow: '0 4px 18px rgba(0,0,0,0.45)',
        }}
      />
    </div>
  );
};

/* ---------- khung bản đồ inset ---------- */
const BanDo = ({anh, mauNet}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 102], [1.0, 1.14], CL);
  const vao = interpolate(f, [0, 16], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        width: 520,
        height: 340,
        overflow: 'hidden',
        border: `5px solid ${mauNet}`,
        borderRadius: 12,
        boxShadow: '0 20px 55px rgba(0,0,0,0.5)',
        opacity: vao,
        transform: `translateY(${(1 - vao) * 34}px)`,
        position: 'relative',
      }}
    >
      <Img
        name="Anh ban do Arizona"
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${s})`}}
      />
    </div>
  );
};

/* ---------- đường định vị mảnh ---------- */
const DuongDinhVi = ({mau, day}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 24], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const dot = interpolate(f, [20, 34], [0, 1], CL);
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <polyline
        points="630,810 900,762 1180,642"
        fill="none"
        stroke={mau}
        strokeWidth={day}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={900}
        strokeDashoffset={900 * (1 - p)}
        opacity={0.9}
      />
      <circle cx={1180} cy={642} r={13} fill={mau} opacity={dot} />
      <circle cx={1180} cy={642} r={30} fill="none" stroke={mau} strokeWidth={3} opacity={dot * 0.75} />
    </svg>
  );
};

/* ---------- vòng vẽ tay dạng ellipse ---------- */
const VongTron = ({cx, cy, rx, ry, batDau, mau, day}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + 24], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const C = 2 * Math.PI * Math.sqrt((rx * rx + ry * ry) / 2);
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <ellipse
        cx={cx}
        cy={cy}
        rx={rx}
        ry={ry}
        fill="none"
        stroke={mau}
        strokeWidth={day}
        strokeLinecap="round"
        strokeDasharray={C}
        strokeDashoffset={C * (1 - p)}
        opacity={0.92}
        transform={`rotate(-4 ${cx} ${cy})`}
      />
    </svg>
  );
};

/* ---------- mũi tên thẳng vẽ dần ---------- */
const MuiTenThang = ({x1, y1, x2, y2, batDau, mau, day}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + 18], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const hx = x1 + (x2 - x1) * p;
  const hy = y1 + (y2 - y1) * p;
  const ang = Math.atan2(y2 - y1, x2 - x1);
  const headP = interpolate(p, [0.72, 1], [0, 1], CL);
  const hs = 30;
  const ax = x2 - hs * Math.cos(ang - 0.5);
  const ay = y2 - hs * Math.sin(ang - 0.5);
  const bx = x2 - hs * Math.cos(ang + 0.5);
  const by = y2 - hs * Math.sin(ang + 0.5);
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <line x1={x1} y1={y1} x2={hx} y2={hy} stroke={mau} strokeWidth={day} strokeLinecap="round" opacity={0.95} />
      <polygon points={`${x2},${y2} ${ax},${ay} ${bx},${by}`} fill={mau} opacity={headP} />
    </svg>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0b0b', overflow: 'hidden'}}>
      {/* ===== NHỊP 1 — toàn cảnh lòng suối Brawley Wash ===== */}
      <Interactive.Div
        name="Nhip 1 - Toan canh long suoi Brawley Wash"
        from={0}
        durationInFrames={106}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhToanCanh} tu={1.02} den={1.12} goc="50% 45%" toi={props.doToi} />
      </Interactive.Div>

      <Interactive.Div
        name="Ban do Arizona inset"
        from={4}
        durationInFrames={102}
        style={{position: 'absolute', left: 110, top: 640, width: 520, height: 340}}
      >
        <BanDo anh={props.anhBanDo} mauNet={props.mauNet} />
      </Interactive.Div>

      <Interactive.Div
        name="Duong dinh vi tren ban do"
        from={10}
        durationInFrames={96}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DuongDinhVi mau={props.mauNet} day={props.doDayNet} />
      </Interactive.Div>

      <Interactive.Div
        name="Chu BRAWLEY WASH"
        from={4}
        durationInFrames={102}
        style={{position: 'absolute', left: 680, top: 760, width: 1180}}
      >
        <ChuLon
          chu={props.chuChinh}
          co={props.coChu}
          mau={props.mauChu}
          mauGach={props.mauGach}
          rongGach={props.rongGachChan}
        />
      </Interactive.Div>

      {/* ===== NHỊP 2 — cụm lốp xe nhồi đầy sỏi ===== */}
      <Interactive.Div
        name="Nhip 2 - Cum lop xe nhoi day soi"
        from={106}
        durationInFrames={82}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhLopXe} tu={props.zoomManh} den={props.zoomNhe} goc="50% 50%" toi={props.doToi} />
      </Interactive.Div>

      <Interactive.Div
        name="Vong khoanh cum lop"
        from={116}
        durationInFrames={72}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <VongTron cx={960} cy={540} rx={470} ry={330} batDau={6} mau={props.mauNet} day={props.doDayNet} />
      </Interactive.Div>

      {/* ===== NHỊP 3 — thanh thép liên kết ===== */}
      <Interactive.Div
        name="Nhip 3 - Thanh thep lien ket"
        from={188}
        durationInFrames={40}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={props.anhThanhThep} huong="phai" quang={props.quangPan} phong={1.12} toi={props.doToi} />
      </Interactive.Div>

      <Interactive.Div
        name="Mui ten chi thanh thep"
        from={192}
        durationInFrames={36}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <MuiTenThang x1={330} y1={830} x2={880} y2={590} batDau={4} mau={props.mauNet} day={props.doDayNet} />
      </Interactive.Div>

      {/* ===== NHỊP 4 — chôn sâu dưới lòng suối ===== */}
      <Interactive.Div
        name="Nhip 4 - Lat cat cau truc chon duoi long suoi"
        from={228}
        durationInFrames={73}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhCatLop} tu={props.zoomManh} den={1.0} goc="50% 55%" toi={props.doToi} />
      </Interactive.Div>

      {/* ===== NHỊP 5 — lũ quét mùa hè ===== */}
      <Interactive.Div
        name="Nhip 5 - Lu quet mua he tren long suoi"
        from={301}
        durationInFrames={119}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhLuQuet} tu={props.zoomManh} den={1.0} goc="50% 50%" toi={props.doToi} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
