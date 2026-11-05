import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền toàn cảnh trang trại khô cằn'),
  anh_nguoi: z.string().describe('Ảnh cắt lớp nhà nghiên cứu'),
  anh_dat: z.string().describe('Ảnh bãi đất xói lở'),
  anh_lop: z.string().describe('Ảnh chồng lốp xe cũ'),
  chu_dau: z.string().describe('Chữ trên con dấu'),
  quang_pan: z.number().describe('Quãng trượt ngang của ảnh nền (px)'),
  do_zoom_nen: z.number().describe('Độ phóng của ảnh nền'),
  do_toi_nen: z.number().describe('Độ tối ảnh nền (0 - 0.5)'),
  co_dau: z.number().describe('Cỡ chữ con dấu (px)'),
  mau_dau: z.string().describe('Màu con dấu'),
  mau_noi: z.string().describe('Màu đường nối vàng'),
  rong_khung: z.number().describe('Chiều rộng mỗi khung ảnh khi tách đôi (px)'),
  cao_khung: z.number().describe('Chiều cao mỗi khung ảnh khi tách đôi (px)'),
  do_toi_khung_phai: z.number().describe('Độ tối nền khung lốp xe (0 - 0.5)'),
});

/* ---------- Ảnh cắt lớp nhà nghiên cứu trượt vào từ bên phải ---------- */
const ChanDung = ({anh}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 22, stiffness: 92, mass: 1}});
  const tx = interpolate(vao, [0, 1], [620, 0]);
  const op = interpolate(f, [0, 5, 58, 70], [0, 1, 1, 0], kep);
  const sweep = interpolate(f, [8, 42], [-820, 1100], kep);
  return (
    <div
      style={{
        position: 'relative',
        width: 685,
        height: 900,
        overflow: 'hidden',
        transform: `translateX(${tx}px)`,
        opacity: op,
        filter: 'drop-shadow(0 34px 60px rgba(0,0,0,0.55))',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
      <div
        style={{
          position: 'absolute',
          top: -420,
          left: 0,
          width: 300,
          height: 1800,
          background:
            'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.62) 50%, rgba(255,255,255,0) 100%)',
          transform: `translateX(${sweep}px) rotate(14deg)`,
          mixBlendMode: 'screen',
        }}
      />
    </div>
  );
};

/* ---------- Con dấu "KHÔNG" mờ hiện ra rồi lướt mờ đi ---------- */
const ConDau = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 13, stiffness: 150, mass: 0.7}});
  const op = interpolate(f, [0, 4, 34, 52], [0, 0.92, 0.92, 0], kep);
  const blur = interpolate(f, [0, 10, 34, 52], [18, 0, 0, 18], kep);
  const ty = interpolate(f, [34, 52], [0, -80], kep);
  const sc = interpolate(vao, [0, 1], [1.55, 1]);
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '6px 44px 14px 44px',
        border: `14px solid ${mau}`,
        borderRadius: 22,
        color: mau,
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: co,
        letterSpacing: 10,
        lineHeight: 1.05,
        transform: `rotate(-11deg) scale(${sc}) translateY(${ty}px)`,
        opacity: op,
        filter: `blur(${blur}px)`,
      }}
    >
      {chu}
    </div>
  );
};

/* ---------- Khung ảnh trái: bãi đất xói lở ---------- */
const KhungDat = ({anh, vien}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 20, stiffness: 110, mass: 0.9}});
  const zoom = interpolate(f, [0, 90], [1.04, 1.16], kep);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        border: vien,
        borderRadius: 10,
        boxShadow: '0 30px 80px rgba(0,0,0,0.55)',
        transform: `scale(${interpolate(s, [0, 1], [0.86, 1])})`,
        opacity: s,
      }}
    >
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${zoom})`,
        }}
      />
    </div>
  );
};

/* ---------- Khung ảnh phải: chồng lốp xe cũ ---------- */
const KhungLop = ({anh, vien, toi}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 20, stiffness: 110, mass: 0.9}});
  const zoom = interpolate(f, [0, 90], [1.0, 1.09], kep);
  const ty = interpolate(f, [0, 90], [0, -22], kep);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        border: vien,
        borderRadius: 10,
        boxShadow: '0 30px 80px rgba(0,0,0,0.55)',
        transform: `scale(${interpolate(s, [0, 1], [0.86, 1])})`,
        opacity: s,
      }}
    >
      <div style={{position: 'absolute', inset: 0, background: `rgba(16,12,8,${toi})`}} />
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 740,
          height: 'auto',
          transform: `translate(-50%, -50%) translateY(${ty}px) scale(${zoom})`,
        }}
      />
    </div>
  );
};

/* ---------- Đường vẽ vàng nối hai khung ảnh ---------- */
const DuongNoi = ({mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f, fps, config: {damping: 200}, durationInFrames: 26});
  const path = 'M 250 660 C 720 510, 1200 810, 1670 620';
  return (
    <svg
      width={1920}
      height={1080}
      viewBox="0 0 1920 1080"
      style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}
    >
      <path
        d={path}
        fill="none"
        stroke="rgba(0,0,0,0.4)"
        strokeWidth={28}
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray="1"
        strokeDashoffset={1 - p}
      />
      <path
        d={path}
        fill="none"
        stroke={mau}
        strokeWidth={15}
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray="1"
        strokeDashoffset={1 - p}
      />
      <circle cx={250} cy={660} r={17} fill={mau} opacity={p} />
      <circle cx={1670} cy={620} r={17} fill={mau} opacity={p} />
    </svg>
  );
};

/* ---------- Vệt sáng lướt ngang (phủ định kế hoạch vĩ mô) ---------- */
const VetSang = () => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 44], [-900, 2400], kep);
  const op = interpolate(f, [0, 8, 34, 44], [0, 1, 1, 0], kep);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: op}}>
      <div
        style={{
          position: 'absolute',
          top: -680,
          left: 0,
          width: 620,
          height: 2500,
          background:
            'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.34) 50%, rgba(255,255,255,0) 100%)',
          transform: `translateX(${x}px) rotate(14deg)`,
          mixBlendMode: 'screen',
        }}
      />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#1a1410'}}>
      {/* NỀN: toàn cảnh trang trại khô cằn, trượt ngang chậm suốt shot */}
      <Interactive.Div
        name="Nền trang trại khô cằn"
        from={0}
        durationInFrames={304}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia
          anh={props.anh_nen}
          huong="trai"
          quang={props.quang_pan}
          phong={props.do_zoom_nen}
          toi={props.do_toi_nen}
        />
      </Interactive.Div>

      {/* BEAT 62: vệt sáng lướt qua */}
      <Interactive.Div
        name="Vệt sáng phủ định"
        from={62}
        durationInFrames={48}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <VetSang />
      </Interactive.Div>

      {/* BEAT 62: con dấu KHÔNG */}
      <Interactive.Div
        name="Con dấu KHÔNG"
        from={62}
        durationInFrames={56}
        style={{position: 'absolute', left: 650, top: 400}}
      >
        <ConDau chu={props.chu_dau} co={props.co_dau} mau={props.mau_dau} />
      </Interactive.Div>

      {/* BEAT 158: nhà nghiên cứu trượt vào từ bên phải */}
      <Interactive.Div
        name="Nhà nghiên cứu quan sát đất"
        from={150}
        durationInFrames={70}
        style={{position: 'absolute', left: 1150, top: 110}}
      >
        <ChanDung anh={props.anh_nguoi} />
      </Interactive.Div>

      {/* BEAT 220: màn hình tách đôi - khung đất xói lở */}
      <Interactive.Div
        name="Khung đất xói lở"
        from={220}
        durationInFrames={84}
        style={{position: 'absolute', left: 130, top: 160, width: 760, height: 760}}
      >
        <KhungDat anh={props.anh_dat} vien={`8px solid ${props.mau_noi}`} />
      </Interactive.Div>

      {/* BEAT 220: màn hình tách đôi - khung lốp xe cũ */}
      <Interactive.Div
        name="Khung lốp xe cũ"
        from={220}
        durationInFrames={84}
        style={{position: 'absolute', left: 1030, top: 160, width: 760, height: 760}}
      >
        <KhungLop anh={props.anh_lop} vien={`8px solid ${props.mau_noi}`} toi={props.do_toi_khung_phai} />
      </Interactive.Div>

      {/* BEAT 222: đường vàng nối hai mảnh ghép */}
      <Interactive.Div
        name="Đường nối vàng"
        from={222}
        durationInFrames={82}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DuongNoi mau={props.mau_noi} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
