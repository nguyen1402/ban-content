import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {z} from 'zod';
import {kep, FONT, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh tư liệu thợ lặn trục vớt lốp dưới đáy biển'),
  soLuong: z.number().describe('Số lốp vớt lên được trong đợt đầu'),
  coSo: z.number().describe('Cỡ chữ bộ đếm số lốp'),
  mauSo: z.string().describe('Màu chữ bộ đếm'),
  mauVang: z.string().describe('Màu vàng nhấn'),
  toiNen: z.number().describe('Độ tối lớp phủ trên ảnh nền (0..0.5)'),
});

/* ---------- Ảnh nền: trượt nhẹ + pull-back chậm suốt shot ---------- */
const NenAnh = ({anh, toi}) => {
  const f = useCurrentFrame();
  const tx = interpolate(f, [0, 52], [80, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const ty = interpolate(f, [0, 52], [30, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        left: -80,
        top: -40,
        width: 2080,
        height: 1160,
        transform: `translate(${tx}px, ${ty}px)`,
      }}
    >
      <AnhNen anh={anh} tu={1.16} den={1.04} goc="50% 45%" toi={toi} />
    </div>
  );
};

/* ---------- Bộ đếm số lốp (chỉ một dòng chữ duy nhất trên màn hình) ---------- */
const BoDem = ({so, co, mau, mauVang}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sp = spring({frame: f, fps, config: {damping: 15, mass: 0.8, stiffness: 120}});
  const sc = interpolate(sp, [0, 1], [0.72, 1]);
  const op = interpolate(f, [0, 8], [0, 1], kep);
  const barW = interpolate(f, [3, 28], [0, 230], {...kep, easing: Easing.out(Easing.cubic)});
  const val = Math.round(
    interpolate(f, [8, 70], [0, so], {...kep, easing: Easing.out(Easing.cubic)})
  );
  const txt = val.toLocaleString('vi-VN');
  return (
    <div
      style={{
        opacity: op,
        transform: `scale(${sc})`,
        transformOrigin: 'left bottom',
        fontFamily: FONT,
      }}
    >
      <div
        style={{
          width: barW,
          height: 14,
          background: mauVang,
          borderRadius: 7,
          marginBottom: 24,
          boxShadow: '0 10px 30px rgba(0,0,0,0.45)',
        }}
      />
      <span
        style={{
          display: 'block',
          fontSize: co,
          fontWeight: 900,
          color: mau,
          lineHeight: 0.88,
          letterSpacing: '-6px',
          textShadow: '0 14px 38px rgba(0,0,0,0.68)',
        }}
      >
        {txt}
      </span>
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#04121b', overflow: 'hidden'}}>
      {/* 3 — ảnh nền thợ lặn trục vớt lốp */}
      <Interactive.Div
        name="Ảnh nền thợ lặn trục vớt lốp"
        from={3}
        durationInFrames={247}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <NenAnh anh={props.anhNen} toi={props.toiNen} />
      </Interactive.Div>

      {/* 42 — bộ đếm 1.600 chiếc */}
      <Interactive.Div
        name="Bộ đếm số lốp"
        from={42}
        durationInFrames={208}
        style={{position: 'absolute', left: 120, top: 640}}
      >
        <BoDem so={props.soLuong} co={props.coSo} mau={props.mauSo} mauVang={props.mauVang} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
