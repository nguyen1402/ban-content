import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh1895: z.string().describe('Ảnh tư liệu sepia trang trại King Anvil 1895'),
  anhAltar: z.string().describe('Ảnh bản đồ vệ tinh thung lũng Altar'),
  anhDC: z.string().describe('Bản đồ thủ đô Washington D.C. (PNG nền trong suốt)'),
  nam: z.string().describe('Năm hiển thị trên ảnh tư liệu'),
  soHa: z.number().describe('Diện tích trang trại (héc ta)'),
  donVi: z.string().describe('Đơn vị diện tích'),
  mauVang: z.string().describe('Màu vàng gold của chữ năm'),
  mauVien: z.string().describe('Màu đỏ của đường ranh giới'),
  coChuNam: z.number().describe('Cỡ chữ năm 1895 (px)'),
  coDem: z.number().describe('Cỡ chữ bộ đếm diện tích (px)'),
  rongDC: z.number().describe('Chiều rộng bản đồ Washington D.C. (px)'),
});

const D_FARM = 'M430,290 L880,215 L1450,265 L1520,610 L1420,900 L800,930 L450,800 Z';

/* ---------- Lớp 1: ảnh tư liệu 1895 ---------- */

const KhoiAnh1895 = ({anh}) => (
  <AnhNen anh={anh} tu={1.0} den={1.13} goc="50% 45%" toi={0.16} />
);

const KhoiChu1895 = ({f, nam, mau, co}) => {
  const op = interpolate(f, [3, 24], [0, 1], kep);
  const sp = spring({frame: f - 3, fps: 30, config: {damping: 200, stiffness: 90}});
  const drift = interpolate(f, [3, 140], [26, -26], kep);
  const lineW = interpolate(f, [10, 40], [0, co * 2.35], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{opacity: op, transform: `translateY(${drift}px) scale(${0.92 + 0.08 * sp})`, transformOrigin: 'left bottom'}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 800,
          lineHeight: 1,
          letterSpacing: 10,
          color: mau,
          textShadow: '0 10px 46px rgba(0,0,0,0.6)',
          whiteSpace: 'nowrap',
        }}
      >
        {nam}
      </div>
      <div style={{width: lineW, height: 9, background: mau, marginTop: 18, opacity: 0.92}} />
    </div>
  );
};

/* ---------- Lớp 2: bản đồ vệ tinh Altar Valley ---------- */

const KhoiBanDoAltar = ({f, anh}) => {
  const op = interpolate(f, [124, 138], [0, 1], kep);
  return (
    <div style={{position: 'absolute', inset: 0, opacity: op}}>
      <AnhNen anh={anh} tu={1.17} den={1.02} goc="50% 50%" toi={0.12} />
    </div>
  );
};

const KhoiVienDo = ({f, mau}) => {
  const reveal = interpolate(f, [124, 161], [0, 1920], {...kep, easing: Easing.inOut(Easing.cubic)});
  const dash = interpolate(f, [124, 333], [0, -0.72], kep);
  const fillOp = interpolate(f, [124, 168], [0, 0.11], kep);
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <defs>
        <mask id="vienFarmMask">
          <rect x={0} y={0} width={reveal} height={1080} fill="#ffffff" />
        </mask>
      </defs>
      <path d={D_FARM} fill={mau} fillOpacity={fillOp} mask="url(#vienFarmMask)" />
      <path
        d={D_FARM}
        fill="none"
        stroke={mau}
        strokeWidth={10}
        strokeLinejoin="round"
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray="0.016 0.011"
        strokeDashoffset={dash}
        mask="url(#vienFarmMask)"
      />
    </svg>
  );
};

const KhoiDemDienTich = ({f, so, donVi, co}) => {
  const op = interpolate(f, [161, 176], [0, 1], kep);
  const sp = spring({frame: f - 161, fps: 30, config: {damping: 13, stiffness: 130, mass: 0.9}});
  const punch = interpolate(sp, [0, 1], [0.8, 1]);
  const move = interpolate(f, [212, 238], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const ty = -382 * move;
  const shrink = interpolate(move, [0, 1], [1, 0.68]);
  return (
    <div
      style={{
        opacity: op,
        transform: `translateY(${ty}px) scale(${punch * shrink})`,
        transformOrigin: 'center center',
        textAlign: 'center',
      }}
    >
      <SoDem so={so} don_vi={donVi} giay={2.2} co={co} />
    </div>
  );
};

/* ---------- Lớp 3: bản đồ Washington D.C. chồng đè ---------- */

const KhoiWashington = ({f, anh, rong}) => {
  const sp = spring({frame: f - 214, fps: 30, config: {damping: 19, stiffness: 88, mass: 1}});
  const ty = interpolate(sp, [0, 1], [640, 0]);
  const op = interpolate(f, [214, 230], [0, 1], kep);
  const drift = interpolate(f, [214, 333], [1.0, 1.04], kep);
  return (
    <div
      style={{
        opacity: op,
        transform: `translateY(${ty}px) scale(${drift})`,
        transformOrigin: '50% 50%',
      }}
    >
      <Img
        src={src(anh)}
        style={{width: rong, height: 'auto', display: 'block', filter: 'drop-shadow(0 18px 40px rgba(0,0,0,0.5))'}}
      />
    </div>
  );
};

/* ---------- Vệt sáng chuyển cảnh ---------- */

const KhoiVetSang = ({f}) => {
  const x = interpolate(f, [124, 150], [-720, 2500], {...kep, easing: Easing.inOut(Easing.quad)});
  const op = interpolate(f, [124, 133, 150], [0, 0.8, 0], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: -120,
        width: 540,
        height: 1320,
        opacity: op,
        background:
          'linear-gradient(90deg, rgba(255,246,222,0) 0%, rgba(255,246,222,0.92) 50%, rgba(255,246,222,0) 100%)',
      }}
    />
  );
};

/* ---------- Cảnh ---------- */

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  return (
    <AbsoluteFill style={{backgroundColor: '#120d08'}}>
      {/* Lớp 1 — ảnh tư liệu sepia 1895 */}
      <Interactive.Div
        name="Ảnh tư liệu trang trại King Anvil 1895"
        from={0}
        durationInFrames={140}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiAnh1895 anh={props.anh1895} />
      </Interactive.Div>

      <Interactive.Div
        name="Chữ năm 1895 màu vàng gold"
        from={3}
        durationInFrames={137}
        style={{position: 'absolute', left: 150, top: 672, width: 900, height: 320}}
      >
        <KhoiChu1895 f={frame} nam={props.nam} mau={props.mauVang} co={props.coChuNam} />
      </Interactive.Div>

      {/* Lớp 2 — bản đồ vệ tinh thung lũng Altar */}
      <Interactive.Div
        name="Bản đồ vệ tinh thung lũng Altar"
        from={124}
        durationInFrames={209}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiBanDoAltar f={frame} anh={props.anhAltar} />
      </Interactive.Div>

      <Interactive.Div
        name="Vệt sáng chuyển cảnh"
        from={124}
        durationInFrames={26}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiVetSang f={frame} />
      </Interactive.Div>

      <Interactive.Div
        name="Ranh giới đỏ trang trại"
        from={124}
        durationInFrames={209}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiVienDo f={frame} mau={props.mauVien} />
      </Interactive.Div>

      <Interactive.Div
        name="Bộ đếm diện tích 17.700 ha"
        from={161}
        durationInFrames={172}
        style={{position: 'absolute', left: 640, top: 452, width: 640, height: 220}}
      >
        <KhoiDemDienTich f={frame} so={props.soHa} donVi={props.donVi} co={props.coDem} />
      </Interactive.Div>

      {/* Lớp 3 — bản đồ Washington D.C. chồng đè */}
      <Interactive.Div
        name="Bản đồ thủ đô Washington D.C."
        from={214}
        durationInFrames={119}
        style={{position: 'absolute', left: 690, top: 330, width: 560, height: 560}}
      >
        <KhoiWashington f={frame} anh={props.anhDC} rong={props.rongDC} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
