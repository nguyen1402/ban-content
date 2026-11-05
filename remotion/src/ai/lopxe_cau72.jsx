import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

/* ---------- Nhịp 2: wipe mềm từ lòng rãnh khô sang thảm xanh ---------- */
const LopXanh = ({anh, daiWipe}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, daiWipe], [0, 1], {...CL, easing: Easing.inOut(Easing.cubic)});
  const x = interpolate(p, [0, 1], [-30, 130], CL);
  const clip = `polygon(0% 0%, ${x}% 0%, ${x - 16}% 100%, 0% 100%)`;
  const bandOp = interpolate(p, [0, 0.1, 0.88, 1], [0, 0.9, 0.9, 0], CL);
  return (
    <>
      <div style={{position: 'absolute', inset: 0, clipPath: clip, WebkitClipPath: clip}}>
        <AnhNen anh={anh} tu={1.2} den={1.0} goc="48% 52%" toi={0.06} />
      </div>
      <div
        style={{
          position: 'absolute',
          top: '-10%',
          height: '120%',
          width: 300,
          left: `${x}%`,
          transform: 'translateX(-50%) skewX(-9deg)',
          background:
            'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,248,214,0.72) 50%, rgba(255,255,255,0) 100%)',
          opacity: bandOp,
          mixBlendMode: 'screen',
          pointerEvents: 'none',
        }}
      />
    </>
  );
};

/* ---------- Nhịp 2: đường viền ranh giới + nhãn diện tích ---------- */
const DUONG_VIEN =
  'M 240 560 C 250 440, 400 360, 620 352 C 860 344, 1050 400, 1130 500 C 1200 590, 1150 720, 960 770 C 780 818, 480 812, 330 740 C 230 690, 232 640, 240 560 Z';

const RanhGioi = ({chu, mau, coChu}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ve = interpolate(f, [0, 36], [0, 1], {...CL, easing: Easing.inOut(Easing.cubic)});
  const hien = interpolate(f, [0, 8], [0, 1], CL);
  const tr = spring({frame: Math.max(0, f - 24), fps, config: {damping: 200, mass: 0.8}});
  const ty = interpolate(tr, [0, 1], [46, 0], CL);
  const opText = interpolate(f, [24, 40], [0, 1], CL);
  const dayOp = interpolate(f, [32, 48], [0, 1], CL);

  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: 'absolute', left: 0, top: 0}}>
        <path
          d={DUONG_VIEN}
          fill="none"
          stroke={mau}
          strokeWidth={7}
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - ve}
          opacity={hien * 0.95}
        />
      </svg>
      <div style={{position: 'absolute', left: 132, top: 112, opacity: opText, transform: `translateY(${ty}px)`}}>
        <div
          style={{
            fontFamily: FONT,
            fontSize: coChu,
            fontWeight: 800,
            color: mau,
            letterSpacing: 3,
            lineHeight: 1,
            textShadow: '0 8px 26px rgba(0,0,0,0.45)',
            whiteSpace: 'nowrap',
          }}
        >
          {chu}
        </div>
        <div
          style={{
            marginTop: 20,
            width: 268,
            height: 7,
            background: mau,
            borderRadius: 4,
            opacity: dayOp,
            transform: `scaleX(${dayOp})`,
            transformOrigin: 'left center',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

/* ---------- Nhịp 3: cửa sổ đồ họa mặt cắt kỹ thuật ---------- */
const SoDoCat = ({anh, rong, cao}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200, mass: 0.9}});
  const tx = interpolate(vao, [0, 1], [300, 0], CL);
  const op = interpolate(f, [0, 12], [0, 1], CL);
  const zoom = interpolate(f, [0, 140], [1.0, 1.09], CL);
  const vien = interpolate(f, [6, 26], [0, 1], CL);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: rong,
        height: cao,
        transform: `translateX(${tx}px)`,
        opacity: op,
        borderRadius: 16,
        overflow: 'hidden',
        background: 'linear-gradient(160deg, rgba(12,20,26,0.58), rgba(6,12,16,0.76))',
        boxShadow: '0 34px 90px rgba(0,0,0,0.5)',
      }}
    >
      <div style={{position: 'absolute', inset: 0, transform: `scale(${zoom})`, transformOrigin: '58% 50%'}}>
        <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}} />
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          border: '3px solid rgba(255,255,255,0.9)',
          borderRadius: 16,
          opacity: vien,
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};

/* ---------- Cảnh ---------- */
export const schema = z.object({
  anhKho: z.string().describe('Ảnh lòng rãnh xói lở khô cằn dưới nắng'),
  anhXanh: z.string().describe('Ảnh thảm xanh phục hồi'),
  anhSoDo: z.string().describe('Ảnh sơ đồ mặt cắt hãm tốc dòng lũ'),
  chuDienTich: z.string().describe('Nhãn diện tích hiển thị'),
  mauVien: z.string().describe('Màu đường viền ranh giới và nhãn'),
  coChuDienTich: z.number().describe('Cỡ chữ nhãn diện tích (px)'),
  daiWipe: z.number().describe('Số frame của cú wipe chuyển cảnh'),
  rongSoDo: z.number().describe('Chiều rộng cửa sổ sơ đồ (px)'),
  caoSoDo: z.number().describe('Chiều cao cửa sổ sơ đồ (px)'),
});

export const Canh = (props) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f12'}}>
      {/* Nhịp 1 — frame 4: lòng rãnh xói lở, camera trôi nhẹ, giữ tới frame cuối (369) */}
      <Interactive.Div
        name="Lòng rãnh xói lở khô cằn"
        from={0}
        durationInFrames={369}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhKho} tu={1.0} den={1.12} goc="50% 45%" toi={0.08} />
      </Interactive.Div>

      {/* Nhịp 2 — frame 138: wipe mềm sang thảm xanh, kéo lùi dần tới cuối */}
      <Interactive.Div
        name="Thảm xanh phục hồi"
        from={138}
        durationInFrames={231}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopXanh anh={props.anhXanh} daiWipe={props.daiWipe} />
      </Interactive.Div>

      {/* Nhịp 2 — frame 140: đường viền ranh giới + '2 ha' */}
      <Interactive.Div
        name="Ranh giới và diện tích"
        from={140}
        durationInFrames={229}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <RanhGioi chu={props.chuDienTich} mau={props.mauVien} coChu={props.coChuDienTich} />
      </Interactive.Div>

      {/* Nhịp 3 — frame 234: cửa sổ sơ đồ mặt cắt kỹ thuật mở ra */}
      <Interactive.Div
        name="Sơ đồ mặt cắt hãm tốc dòng lũ"
        from={234}
        durationInFrames={135}
        style={{position: 'absolute', left: 1050, top: 540, width: 800, height: 450}}
      >
        <SoDoCat anh={props.anhSoDo} rong={props.rongSoDo} cao={props.caoSoDo} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
