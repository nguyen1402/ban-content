import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_cat: z.string().describe('Ảnh nền lớp cát phù sa đọng lại'),
  anh_lop_xe: z.string().describe('Ảnh tách các lớp lốp xe chồng lên nhau'),
  anh_ha_luu: z.string().describe('Ảnh dòng nước chảy xiết ở hạ lưu'),
  so_lop: z.number().describe('Số lớp lốp xe xếp chồng'),
  quang_nen: z.number().describe('Quãng lướt ngang của ảnh nền cát (px)'),
  toi_nen: z.number().describe('Độ tối phủ lên ảnh nền cát (0..0.5)'),
  lech_lop_xe: z.number().describe('Quãng trượt vào của ảnh lốp xe (px)'),
  phong_lop_xe: z.number().describe('Độ phóng chậm của ảnh lốp xe'),
  cao_thuoc: z.number().describe('Chiều cao thước đo (px)'),
  mau_thuoc: z.string().describe('Màu thước đo'),
  chu_thuoc: z.string().describe('Nhãn chiều cao trên thước đo'),
  co_chu_thuoc: z.number().describe('Cỡ chữ nhãn thước đo (px)'),
  co_so: z.number().describe('Cỡ chữ số lốp xe (px)'),
  mau_so: z.string().describe('Màu số lốp xe'),
  thoi_gian_xoa: z.number().describe('Số frame wipe mở ảnh hạ lưu'),
  toi_ha_luu: z.number().describe('Độ tối phủ lên ảnh hạ lưu (0..0.5)'),
});

/* ---------- ảnh lốp xe trượt vào rồi phóng chậm ---------- */
const LopXe = ({anh, lech, phong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200, mass: 1.1}, durationInFrames: 26});
  const tx = interpolate(vao, [0, 1], [-lech, 0]);
  const hien = interpolate(f, [0, 9], [0, 1], kep);
  const ph = interpolate(f, [26, 317], [1, phong], kep);
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        opacity: hien,
        transform: `translateX(${tx}px) scale(${ph})`,
        transformOrigin: '50% 100%',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

/* ---------- thước đo 1 mét với 5 vạch chia ---------- */
const Thuoc = ({cao, so_lop, mau, chu, co_chu}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 28], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const rong = 240;
  const vach = [];
  for (let i = 0; i <= so_lop; i++) {
    const y = cao - (cao / so_lop) * i;
    const dau = (i / so_lop) * 0.8;
    const tp = interpolate(p, [dau, dau + 0.2], [0, 1], kep);
    vach.push(
      <line
        key={i}
        x1={40}
        y1={y}
        x2={40 + 62 * tp}
        y2={y}
        stroke={mau}
        strokeWidth={8}
        strokeLinecap="round"
        opacity={tp}
      />
    );
  }
  const nhan = interpolate(p, [0.72, 1], [0, 1], kep);
  return (
    <svg width={rong} height={cao} viewBox={`0 0 ${rong} ${cao}`}>
      <line
        x1={40}
        y1={cao}
        x2={40}
        y2={cao - cao * p}
        stroke={mau}
        strokeWidth={9}
        strokeLinecap="round"
      />
      {vach}
      <text
        x={106}
        y={52}
        fontFamily={FONT}
        fontSize={co_chu}
        fontWeight={900}
        fill="#FFFFFF"
        stroke="rgba(0,0,0,0.6)"
        strokeWidth={9}
        paintOrder="stroke"
        opacity={nhan}
      >
        {chu}
      </text>
    </svg>
  );
};

/* ---------- số lốp xe đếm lên ---------- */
const SoLop = ({so, co, mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const v = Math.round(interpolate(f, [0, 32], [0, so], {...kep, easing: Easing.out(Easing.cubic)}));
  const bung = spring({frame: Math.max(0, f - 32), fps, config: {damping: 9, mass: 0.7}});
  const hien = interpolate(f, [0, 6], [0, 1], kep);
  const ph = 1 + 0.18 * bung + 0.05 * interpolate(f, [45, 281], [0, 1], kep);
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: hien,
        transform: `scale(${ph})`,
      }}
    >
      <span
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 900,
          color: mau,
          lineHeight: 1,
          WebkitTextStroke: '7px rgba(0,0,0,0.55)',
        }}
      >
        {v}
      </span>
    </div>
  );
};

/* ---------- wipe mở ảnh hạ lưu ---------- */
const HaLuu = ({anh, xoa, toi}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, xoa], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const cat = (1 - p) * 100;
  const ph = interpolate(f, [0, 133], [1, 1.08], kep);
  const tx = interpolate(f, [0, 133], [0, -26], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        clipPath: `inset(0% ${cat}% 0% 0%)`,
        WebkitClipPath: `inset(0% ${cat}% 0% 0%)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${tx}px) scale(${ph})`,
        }}
      >
        <AnhNen anh={anh} tu={1.16} den={1.02} goc="50% 50%" toi={toi} />
      </div>
    </div>
  );
};

export const Canh = (props) => {
  const {
    anh_cat,
    anh_lop_xe,
    anh_ha_luu,
    so_lop,
    quang_nen,
    toi_nen,
    lech_lop_xe,
    phong_lop_xe,
    cao_thuoc,
    mau_thuoc,
    chu_thuoc,
    co_chu_thuoc,
    co_so,
    mau_so,
    thoi_gian_xoa,
    toi_ha_luu,
  } = props;

  return (
    <AbsoluteFill style={{backgroundColor: '#3a2a18'}}>
      {/* 0 – 397 : nền cát phù sa đọng lại, lướt chậm sang phải */}
      <Interactive.Div
        name="Nền cát phù sa đọng lại"
        from={0}
        durationInFrames={397}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={anh_cat} huong="phai" quang={quang_nen} toi={toi_nen} />
      </Interactive.Div>

      {/* 80 – 397 : năm chiếc lốp xe xếp chồng trượt vào */}
      <Interactive.Div
        name="Năm lốp xe xếp chồng"
        from={80}
        durationInFrames={317}
        style={{position: 'absolute', left: 560, top: 130, width: 559, height: 890}}
      >
        <LopXe anh={anh_lop_xe} lech={lech_lop_xe} phong={phong_lop_xe} />
      </Interactive.Div>

      {/* 88 – 397 : thước đo 1 mét vẽ dần */}
      <Interactive.Div
        name="Thước đo một mét"
        from={88}
        durationInFrames={309}
        style={{position: 'absolute', left: 1180, top: 130, width: 240, height: 890}}
      >
        <Thuoc
          cao={cao_thuoc}
          so_lop={so_lop}
          mau={mau_thuoc}
          chu={chu_thuoc}
          co_chu={co_chu_thuoc}
        />
      </Interactive.Div>

      {/* 116 – 397 : số lốp xe đếm lên */}
      <Interactive.Div
        name="Số lốp xe"
        from={116}
        durationInFrames={281}
        style={{position: 'absolute', left: 1470, top: 150, width: 340, height: 260}}
      >
        <SoLop so={so_lop} co={co_so} mau={mau_so} />
      </Interactive.Div>

      {/* 264 – 397 : wipe mở dòng nước hạ lưu */}
      <Interactive.Div
        name="Dòng nước hạ lưu"
        from={264}
        durationInFrames={133}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <HaLuu anh={anh_ha_luu} xoa={thoi_gian_xoa} toi={toi_ha_luu} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
