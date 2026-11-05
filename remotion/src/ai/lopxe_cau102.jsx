import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhToanCanh: z.string().describe('Ảnh toàn cảnh lốp xe dưới đáy biển'),
  anhTrungCanh: z.string().describe('Ảnh trung cảnh đống lốp chìm'),
  anhMacro: z.string().describe('Ảnh cận cảnh bề mặt cao su'),
  chuChinh: z.string().describe('Dòng chữ hiện ở góc màn hình'),
  coChu: z.number().describe('Cỡ chữ Osborne (px)'),
  mauNhan: z.string().describe('Màu vàng nhấn'),
  doDaiGach: z.number().describe('Độ dài gạch chân vàng (px)'),
  toiAnh1: z.number().describe('Độ tối ảnh toàn cảnh (0..0.5)'),
  toiAnh2: z.number().describe('Độ tối ảnh trung cảnh (0..0.5)'),
  toiAnh3: z.number().describe('Độ tối ảnh macro (0..0.5)'),
  daiChuyen: z.number().describe('Số frame hiệu ứng wipe chuyển cảnh'),
  quangPan: z.number().describe('Quãng pan ảnh macro (px)'),
});

// ---- Lớp wipe chuyển cảnh (dùng frame cục bộ bên trong Interactive.Div) ----
const LopAnh = ({children, kieu, dai}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, dai], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const clip =
    kieu === 'phai'
      ? `inset(0px 0px 0px ${(1 - p) * 100}%)`
      : kieu === 'xuong'
        ? `inset(${(1 - p) * 100}% 0px 0px 0px)`
        : `inset(0px ${(1 - p) * 100}% 0px 0px)`;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        clipPath: clip,
        WebkitClipPath: clip,
      }}
    >
      {children}
    </div>
  );
};

// ---- Dòng chữ Osborne (góc dưới bên trái) ----
const ChuOsborne = ({chu, co, mau, doDaiGach}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 18, stiffness: 110}, durationInFrames: 24});
  const mo = interpolate(f, [0, 8], [0, 1], kep);
  const gach = interpolate(f, [10, 34], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{opacity: mo, transform: `translateY(${(1 - vao) * 46}px)`}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 800,
          letterSpacing: 4,
          color: '#FFFFFF',
          lineHeight: 1,
          textShadow: '0 8px 26px rgba(0,0,0,0.6)',
        }}
      >
        {chu}
      </div>
      <div
        style={{
          marginTop: 18,
          height: 12,
          width: Math.max(0, doDaiGach * gach),
          background: mau,
          borderRadius: 8,
        }}
      />
    </div>
  );
};

// ---- Khung đồ họa cấu trúc kết nối (vẽ dần bằng SVG) ----
const KhungCauTruc = ({mau, rong, cao}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const nut = [
    [120, 150],
    [400, 110],
    [440, 330],
    [250, 420],
    [95, 340],
    [310, 520],
  ];
  const noi = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 4],
    [4, 0],
    [3, 5],
    [1, 3],
  ];
  const vien = interpolate(f, [0, 26], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <svg width={rong} height={cao} viewBox={`0 0 ${rong} ${cao}`}>
      <rect
        x={5}
        y={5}
        width={rong - 10}
        height={cao - 10}
        rx={30}
        fill="rgba(8,14,18,0.42)"
        stroke={mau}
        strokeWidth={5}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - vien}
      />
      {noi.map(([a, b], i) => {
        const p = interpolate(f, [12 + i * 4, 36 + i * 4], [0, 1], {
          ...kep,
          easing: Easing.out(Easing.cubic),
        });
        return (
          <line
            key={`l-${i}`}
            x1={nut[a][0]}
            y1={nut[a][1]}
            x2={nut[b][0]}
            y2={nut[b][1]}
            stroke="#FFFFFF"
            strokeWidth={4}
            strokeLinecap="round"
            opacity={0.85}
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - p}
          />
        );
      })}
      {nut.map(([x, y], i) => {
        const s = spring({
          frame: Math.max(0, f - (18 + i * 5)),
          fps,
          config: {damping: 14, stiffness: 120},
        });
        const sc = Math.max(0.001, s);
        return (
          <g key={`n-${i}`} transform={`translate(${x} ${y}) scale(${sc})`}>
            <circle r={24} fill="rgba(8,14,18,0.85)" stroke={mau} strokeWidth={5} />
            <circle r={7} fill={mau} />
          </g>
        );
      })}
    </svg>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0d10'}}>
      {/* NHỊP 1 — toàn cảnh lốp xe (0 → 92) */}
      <Interactive.Div
        name="Ảnh toàn cảnh lốp xe"
        from={0}
        durationInFrames={92}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhToanCanh} tu={1} den={1.12} goc="50% 45%" toi={props.toiAnh1} />
      </Interactive.Div>

      <Interactive.Div
        name="Chữ Osborne"
        from={5}
        durationInFrames={86}
        style={{position: 'absolute', left: 110, top: 690}}
      >
        <ChuOsborne
          chu={props.chuChinh}
          co={props.coChu}
          mau={props.mauNhan}
          doDaiGach={props.doDaiGach}
        />
      </Interactive.Div>

      {/* NHỊP 2 — trung cảnh đống lốp (77 → 210) */}
      <Interactive.Div
        name="Ảnh trung cảnh đống lốp"
        from={77}
        durationInFrames={134}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopAnh kieu="phai" dai={props.daiChuyen}>
          <AnhNen anh={props.anhTrungCanh} tu={1.14} den={1} goc="50% 55%" toi={props.toiAnh2} />
        </LopAnh>
      </Interactive.Div>

      <Interactive.Div
        name="Khung đồ họa cấu trúc"
        from={88}
        durationInFrames={108}
        style={{position: 'absolute', left: 1290, top: 250}}
      >
        <KhungCauTruc mau={props.mauNhan} rong={540} cao={580} />
      </Interactive.Div>

      {/* NHỊP 3 — macro bề mặt cao su (194 → hết) */}
      <Interactive.Div
        name="Ảnh macro bề mặt cao su"
        from={194}
        durationInFrames={136}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopAnh kieu="xuong" dai={props.daiChuyen}>
          <AnhLia
            anh={props.anhMacro}
            huong="phai"
            quang={props.quangPan}
            phong={1.08}
            toi={props.toiAnh3}
          />
        </LopAnh>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
