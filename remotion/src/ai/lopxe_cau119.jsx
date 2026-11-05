import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền tâm hồn tĩnh lặng'),
  anhNguoi: z.string().describe('Ảnh tách người ngồi nghiêng ôm ngọc trước ngực'),
  anhNgoc: z.string().describe('Ảnh cận cảnh lõi ngọc hổ phách rực sáng'),
  anhKim: z.string().describe('Ảnh tách bóng kim đồng hồ cổ'),
  anhNuoc: z.string().describe('Ảnh dòng nước trong xanh xoa dịu'),
  toiNen: z.number().describe('Độ tối của lớp nền (0..0.5)'),
  dayNen: z.number().describe('Độ phóng của ảnh nền tới cuối cảnh'),
  punch: z.number().describe('Hệ số punch-in của viên ngọc'),
  sweepRong: z.number().describe('Bề rộng vệt sáng quét qua viên ngọc (px)'),
});

/* ---------- Lớp 1: người ôm ngọc (tiền cảnh) ---------- */
const NguoiOmNgoc = ({anh}) => {
  const frame = useCurrentFrame(); // local 0 = frame 4
  const day = interpolate(frame, [0, 40], [1, 1.07], kep);
  const dot = interpolate(frame, [26, 36], [1, 1.2], {...kep, easing: Easing.in(Easing.cubic)});
  const mo = interpolate(frame, [30, 38], [1, 0], kep);
  return (
    <AbsoluteFill style={{opacity: mo, transform: `scale(${day * dot})`, transformOrigin: '50% 62%'}}>
      <Img
        name="Người ôm ngọc"
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'contain'}}
      />
    </AbsoluteFill>
  );
};

/* ---------- Lớp 2: punch-in lõi ngọc + light sweep ---------- */
const LoiNgoc = ({anh, punch, sweepRong}) => {
  const frame = useCurrentFrame(); // local 0 = frame 34
  const vao = interpolate(frame, [0, 3], [0, 1], kep);
  const dam = interpolate(frame, [0, 7], [1, punch], {...kep, easing: Easing.out(Easing.cubic)});
  const troi = interpolate(frame, [7, 116], [1, 1.06], kep);
  const x = interpolate(frame, [2, 28], [-780, 2150], {...kep, easing: Easing.inOut(Easing.cubic)});
  const sweepMo = interpolate(frame, [0, 4, 22, 30], [0, 0.9, 0.9, 0], kep);
  return (
    <AbsoluteFill
      style={{
        opacity: vao,
        transform: `scale(${dam * troi})`,
        transformOrigin: '50% 50%',
        overflow: 'hidden',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      <div
        style={{
          position: 'absolute',
          left: x,
          top: -260,
          width: sweepRong,
          height: 1620,
          transform: 'rotate(10deg)',
          background:
            'linear-gradient(100deg, rgba(255,226,150,0) 0%, rgba(255,230,160,0.35) 38%, rgba(255,248,214,0.9) 50%, rgba(255,230,160,0.35) 62%, rgba(255,226,150,0) 100%)',
          mixBlendMode: 'screen',
          opacity: sweepMo,
        }}
      />
    </AbsoluteFill>
  );
};

/* ---------- Lớp 3: bóng kim đồng hồ cổ + tia sáng thời gian ---------- */
const KimThoiGian = ({anhKim}) => {
  const frame = useCurrentFrame(); // local 0 = frame 80
  const xoay = interpolate(frame, [0, 46], [-26, 44], {...kep, easing: Easing.inOut(Easing.cubic)});
  const truot = interpolate(frame, [0, 46], [-300, 260], kep);
  const hien = interpolate(frame, [0, 8, 34, 46], [0, 0.85, 0.85, 0], kep);
  const ray = interpolate(frame, [0, 46], [-24, 30], kep);
  const rayMo = interpolate(frame, [0, 8, 34, 46], [0, 0.3, 0.3, 0], kep);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: rayMo,
          transform: `rotate(${ray}deg)`,
          mixBlendMode: 'screen',
          background:
            'conic-gradient(from 0deg at 50% 50%, rgba(255,214,140,0) 0deg, rgba(255,214,140,0.5) 10deg, rgba(255,214,140,0) 22deg, rgba(255,214,140,0) 70deg, rgba(255,214,140,0.4) 82deg, rgba(255,214,140,0) 96deg, rgba(255,214,140,0) 168deg, rgba(255,214,140,0.45) 180deg, rgba(255,214,140,0) 194deg, rgba(255,214,140,0) 268deg, rgba(255,214,140,0.35) 280deg, rgba(255,214,140,0) 294deg, rgba(255,214,140,0) 360deg)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 360,
          top: 250,
          width: 1200,
          height: 571,
          opacity: hien,
          transform: `translateX(${truot}px) rotate(${xoay}deg)`,
          transformOrigin: '50% 50%',
        }}
      >
        <Img src={src(anhKim)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
      </div>
    </AbsoluteFill>
  );
};

/* ---------- Lớp 4: nước trong xoa dịu (wipe mềm) ---------- */
const NuocXoaDiu = ({anh}) => {
  const frame = useCurrentFrame(); // local 0 = frame 100
  const p = interpolate(frame, [0, 26], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const edge = p * 150 - 25;
  const zoom = interpolate(frame, [0, 51], [1.04, 1.13], kep);
  const am = interpolate(frame, [4, 30], [0, 1], kep);
  const mask = `linear-gradient(90deg, #000 ${edge - 22}%, rgba(0,0,0,0) ${edge}%)`;
  return (
    <AbsoluteFill style={{WebkitMaskImage: mask, maskImage: mask}}>
      <Img
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoom})`}}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: am,
          mixBlendMode: 'screen',
          background:
            'radial-gradient(ellipse at 50% 42%, rgba(255,214,132,0.55) 0%, rgba(255,198,110,0.22) 45%, rgba(255,180,90,0) 78%)',
        }}
      />
    </AbsoluteFill>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#120c07', fontFamily: FONT}}>
      {/* Nền tâm hồn: phủ kín khung từ frame 0 tới 150, push-in chậm */}
      <AnhNen anh={props.anhNen} tu={1} den={props.dayNen} goc="50% 42%" toi={props.toiNen} />

      {/* 4 → 42: người ngồi nghiêng ôm chặt luồng sáng lõi trước ngực */}
      <Interactive.Div
        name="Người ôm ngọc"
        from={4}
        durationInFrames={38}
        style={{position: 'absolute', left: 620, top: 230, width: 680, height: 820}}
      >
        <NguoiOmNgoc anh={props.anhNguoi} />
      </Interactive.Div>

      {/* 34 → 150: punch-in cận cảnh lõi ngọc hổ phách + light sweep */}
      <Interactive.Div
        name="Cận cảnh lõi ngọc"
        from={34}
        durationInFrames={117}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LoiNgoc anh={props.anhNgoc} punch={props.punch} sweepRong={props.sweepRong} />
      </Interactive.Div>

      {/* 80 → 125: bóng kim đồng hồ cổ quét qua khung hình */}
      <Interactive.Div
        name="Bóng kim thời gian"
        from={80}
        durationInFrames={46}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KimThoiGian anhKim={props.anhKim} />
      </Interactive.Div>

      {/* 100 → 150: wipe nước trong tràn phủ, tone vàng ấm êm đềm */}
      <Interactive.Div
        name="Nước trong xoa dịu"
        from={100}
        durationInFrames={51}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NuocXoaDiu anh={props.anhNuoc} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
