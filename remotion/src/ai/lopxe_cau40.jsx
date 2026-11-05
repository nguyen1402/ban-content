import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhKySu: z.string().describe('Ảnh cắt lớp kỹ sư điện'),
  anhMach: z.string().describe('Ảnh bảng vi mạch điện tử'),
  rongKySu: z.number().describe('Chiều rộng ảnh kỹ sư (px)'),
  diChuyenKySu: z.number().describe('Độ dịch sang trái của kỹ sư ở nhịp 2 (px)'),
  doPhong: z.number().describe('Mức phóng to khi trượt vào vi mạch'),
  zoomNhe: z.number().describe('Mức zoom chậm của nền trong suốt shot'),
  toiNen: z.number().describe('Độ tối lớp phủ nền (0 - 0.5)'),
  mauNeon: z.string().describe('Màu đường mạch neon'),
  mauDiemSang: z.string().describe('Màu điểm sáng vi mạch'),
});

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

/* ---------- NỀN: bảng vi mạch full-frame, zoom chậm + cú push-in ở nhịp 2 ---------- */
const NenMach = ({anh, toi, doPhong, zoomNhe}) => {
  const f = useCurrentFrame();
  const push = interpolate(f, [46, 132], [0, 1], {...CL, easing: Easing.inOut(Easing.cubic)});
  const scale = 1 + zoomNhe * (f / 133) + push * doPhong;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        transform: `scale(${scale})`,
        transformOrigin: '50% 50%',
      }}
    >
      <AnhNen anh={anh} tu={1} den={1.05} goc="50% 50%" toi={toi} />
    </div>
  );
};

/* ---------- ĐƯỜNG MẠCH NEON vẽ dần (nhịp 1) ---------- */
const DUONG = [
  'M -40 260 H 300 V 150 H 620',
  'M 1980 160 H 1560 V 300 H 1330',
  'M 1200 1120 V 880 H 980 V 720',
  'M 1980 640 H 1700 V 500 H 1520',
  'M 760 -40 V 120 H 900',
];
const DAU = [
  {x: 620, y: 150},
  {x: 1330, y: 300},
  {x: 980, y: 720},
  {x: 1520, y: 500},
  {x: 900, y: 120},
];

const DuongMach = ({mau}) => {
  const f = useCurrentFrame();
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      {DUONG.map((d, i) => {
        const p = interpolate(f, [i * 3, i * 3 + 24], [0, 1], {...CL, easing: Easing.inOut(Easing.cubic)});
        return (
          <path
            key={`p${i}`}
            d={d}
            fill="none"
            stroke={mau}
            strokeWidth={4}
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={1}
            strokeDasharray="1 1"
            strokeDashoffset={1 - p}
            opacity={0.85}
          />
        );
      })}
      {DAU.map((d, i) => {
        const p = interpolate(f, [i * 3 + 16, i * 3 + 34], [0, 1], {...CL});
        return <circle key={`d${i}`} cx={d.x} cy={d.y} r={9} fill={mau} opacity={p * 0.9} />;
      })}
    </svg>
  );
};

/* ---------- KỸ SƯ ĐIỆN (cut-out tiền cảnh) ---------- */
const KySuDien = ({anh, rong, diChuyen}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 18], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const x = interpolate(f, [43, 78], [0, diChuyen], {...CL, easing: Easing.inOut(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${x}px, ${(1 - vao) * 46}px) scale(${0.96 + 0.04 * vao})`,
        transformOrigin: '50% 100%',
        opacity: vao,
      }}
    >
      <Img
        src={src(anh)}
        style={{
          width: rong,
          height: 'auto',
          display: 'block',
          filter: 'drop-shadow(0 26px 48px rgba(0,0,0,0.55))',
        }}
      />
    </div>
  );
};

/* ---------- ĐIỂM SÁNG VI MẠCH nhấp nháy (nhịp 2) ---------- */
const DIEM = [
  {x: 1180, y: 250, r: 16},
  {x: 1520, y: 470, r: 12},
  {x: 990, y: 700, r: 14},
  {x: 1680, y: 800, r: 10},
  {x: 820, y: 380, r: 11},
  {x: 1400, y: 930, r: 15},
  {x: 660, y: 830, r: 9},
];

const DiemSang = ({mau}) => {
  const f = useCurrentFrame();
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      {DIEM.map((d, i) => {
        const pha = (f + i * 11) % 48;
        const rin = interpolate(pha, [0, 48], [d.r * 0.7, d.r * 3.6], CL);
        const rop = interpolate(pha, [0, 48], [0.55, 0], CL);
        const nhap = interpolate(f, [0, 14], [0, 1], CL);
        const rCore = d.r * (0.85 + 0.28 * Math.sin(f * 0.16 + i));
        const opCore = 0.4 + 0.6 * Math.abs(Math.sin(f * 0.11 + i * 1.3));
        return (
          <g key={i} opacity={nhap}>
            <circle cx={d.x} cy={d.y} r={rin} fill="none" stroke={mau} strokeWidth={2.5} opacity={rop} />
            <circle cx={d.x} cy={d.y} r={rCore} fill={mau} opacity={opCore} />
          </g>
        );
      })}
    </svg>
  );
};

/* ---------- CẢNH ---------- */
export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#04121c'}}>
      <Interactive.Div
        name="Nền bảng vi mạch"
        from={0}
        durationInFrames={133}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <NenMach anh={props.anhMach} toi={props.toiNen} doPhong={props.doPhong} zoomNhe={props.zoomNhe} />
      </Interactive.Div>

      <Interactive.Div
        name="Đường mạch neon"
        from={3}
        durationInFrames={130}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DuongMach mau={props.mauNeon} />
      </Interactive.Div>

      <Interactive.Div
        name="Kỹ sư điện"
        from={3}
        durationInFrames={130}
        style={{position: 'absolute', left: 240, top: 340, width: 820, height: 560}}
      >
        <KySuDien anh={props.anhKySu} rong={props.rongKySu} diChuyen={props.diChuyenKySu} />
      </Interactive.Div>

      <Interactive.Div
        name="Điểm sáng vi mạch"
        from={46}
        durationInFrames={87}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DiemSang mau={props.mauDiemSang} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
