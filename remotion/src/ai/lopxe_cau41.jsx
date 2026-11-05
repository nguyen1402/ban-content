import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

/* ---------- mũi tên lực vẽ dần ---------- */
const MuiTenLuc = ({x1, y1, x2, y2, p, mau, day}) => {
  const len = Math.hypot(x2 - x1, y2 - y1) || 1;
  const ang = Math.atan2(y2 - y1, x2 - x1);
  const dau = 42;
  const L = Math.max(len - dau * 0.8, 1);
  const ex = x2 - Math.cos(ang) * dau * 0.8;
  const ey = y2 - Math.sin(ang) * dau * 0.8;
  const hx1 = x2 - Math.cos(ang - 0.42) * dau;
  const hy1 = y2 - Math.sin(ang - 0.42) * dau;
  const hx2 = x2 - Math.cos(ang + 0.42) * dau;
  const hy2 = y2 - Math.sin(ang + 0.42) * dau;
  const opDau = interpolate(p, [0.6, 0.95], [0, 1], CL);
  return (
    <g>
      <line
        x1={x1}
        y1={y1}
        x2={ex}
        y2={ey}
        stroke={mau}
        strokeWidth={day}
        strokeLinecap="round"
        strokeDasharray={`${L} ${L}`}
        strokeDashoffset={L * (1 - p)}
      />
      <polygon points={`${x2},${y2} ${hx1},${hy1} ${hx2},${hy2}`} fill={mau} opacity={opDau} />
    </g>
  );
};

/* ---------- lớp cắt kết cấu chịu lực (mở từ trên xuống) ---------- */
const LopCat = ({anh, rong, cao, mau}) => {
  const f = useCurrentFrame();
  const mo = interpolate(f, [0, 26], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const truot = interpolate(f, [0, 34], [70, 0], {...CL, easing: Easing.out(Easing.cubic)});
  const hien = interpolate(f, [0, 8], [0, 1], CL);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: rong,
        height: cao,
        opacity: hien,
        transform: `translateY(${truot}px) scale(${0.95 + 0.05 * mo})`,
        clipPath: `inset(0% 0% ${(1 - mo) * 100}% 0%)`,
      }}
    >
      <Img
        name="Kết cấu chịu lực"
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          filter: 'drop-shadow(0 30px 60px rgba(0,0,0,0.6))',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: cao * mo - 2,
          width: rong,
          height: 4,
          background: mau,
          opacity: (1 - mo) * 0.85,
        }}
      />
    </div>
  );
};

/* ---------- cận cảnh phế phẩm + sơ đồ lực + punch-in ---------- */
const ChiTiet = ({anh, mau, toi}) => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [110, 170], [1, 1.17], {...CL, easing: Easing.inOut(Easing.cubic)});
  const pA = interpolate(f, [2, 28], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const pB = interpolate(f, [6, 32], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const pC = interpolate(f, [12, 40], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const sang = interpolate(f, [110, 150], [0, 1], {...CL, easing: Easing.inOut(Easing.cubic)});

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        transform: `scale(${zoom})`,
        transformOrigin: '50% 52%',
      }}
    >
      <AnhNen anh={anh} tu={1.0} den={1.12} goc="50% 52%" toi={toi} />

      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          opacity: sang,
          mixBlendMode: 'screen',
          background:
            'radial-gradient(circle at 50% 52%, rgba(255,247,214,0.50) 0%, rgba(255,247,214,0.16) 22%, rgba(255,247,214,0) 46%)',
        }}
      />

      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        <MuiTenLuc x1={1252} y1={328} x2={1012} y2={498} p={pA} mau={mau} day={10} />
        <MuiTenLuc x1={668} y1={306} x2={908} y2={492} p={pB} mau={mau} day={10} />
        <MuiTenLuc x1={960} y1={642} x2={960} y2={892} p={pC} mau={mau} day={10} />
      </svg>

      <div style={{position: 'absolute', left: 820, top: 420, width: 280, height: 280}}>
        <VongBut w={280} h={280} />
      </div>
    </div>
  );
};

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền bãi rác công nghiệp'),
  anh_ket_cau: z.string().describe('Ảnh lớp cắt kết cấu chịu lực (tách nền)'),
  anh_can: z.string().describe('Ảnh cận cảnh chi tiết phế phẩm'),
  mau_luc: z.string().describe('Màu đường sơ đồ lực'),
  toi_nen: z.number().describe('Độ tối ảnh nền bãi rác (0–0.5)'),
  toi_can: z.number().describe('Độ tối ảnh cận cảnh (0–0.5)'),
  rong_cat: z.number().describe('Chiều rộng lớp cắt kết cấu (px)'),
  cao_cat: z.number().describe('Chiều cao lớp cắt kết cấu (px)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const xSweep = interpolate(frame, [0, 158], [-1700, 2200], {
    ...CL,
    easing: Easing.inOut(Easing.sin),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0d0c0a'}}>
      {/* BEAT 1 — frame 4: bãi rác công nghiệp, ánh sáng lướt qua
          (giữ ảnh nền tới tận frame cuối 324 để không lộ nền trống / ảnh cũ) */}
      <Interactive.Div
        name="Bãi rác công nghiệp"
        from={0}
        durationInFrames={324}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <AnhNen anh={props.anh_nen} tu={1.0} den={1.14} goc="50% 58%" toi={props.toi_nen} />
        <div
          style={{
            position: 'absolute',
            left: -260,
            top: -120,
            width: 2440,
            height: 1320,
            transform: `translateX(${xSweep}px)`,
            background:
              'linear-gradient(100deg, rgba(255,236,190,0) 36%, rgba(255,236,190,0.14) 46%, rgba(255,248,222,0.34) 50%, rgba(255,236,190,0.14) 54%, rgba(255,236,190,0) 64%)',
          }}
        />
      </Interactive.Div>

      {/* BEAT 2 — frame 95: mở lớp cắt kết cấu chịu lực */}
      <Interactive.Div
        name="Lớp cắt kết cấu chịu lực"
        from={95}
        durationInFrames={70}
        style={{position: 'absolute', left: 380, top: 250, width: props.rong_cat, height: props.cao_cat}}
      >
        <LopCat anh={props.anh_ket_cau} rong={props.rong_cat} cao={props.cao_cat} mau={props.mau_luc} />
      </Interactive.Div>

      {/* BEAT 3 + 4 — frame 154: cận cảnh phế phẩm + sơ đồ lực; frame 264: punch-in
          (ảnh cận cảnh chạy tới frame 324 = frame cuối của cảnh) */}
      <Interactive.Div
        name="Cận cảnh phế phẩm"
        from={154}
        durationInFrames={170}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <ChiTiet anh={props.anh_can} mau={props.mau_luc} toi={props.toi_can} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
