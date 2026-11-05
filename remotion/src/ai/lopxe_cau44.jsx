import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh: z.string().describe('Đường dẫn ảnh tư liệu bãi lốp năm 1996'),
  nam: z.string().describe('Năm hiển thị ở góc trái'),
  namX: z.number().describe('Toạ độ X của năm (px)'),
  namY: z.number().describe('Toạ độ Y của năm (px)'),
  coNam: z.number().describe('Cỡ chữ năm'),
  mauNam: z.string().describe('Màu chữ năm'),
  zoomDau: z.number().describe('Tỷ lệ phóng toàn cảnh lúc mở'),
  zoomCuoi: z.number().describe('Tỷ lệ phóng toàn cảnh lúc kết'),
  toiNen: z.number().describe('Độ tối phủ lên ảnh nền (0-0.5)'),
  insetX: z.number().describe('Toạ độ X khung phóng đại'),
  insetY: z.number().describe('Toạ độ Y khung phóng đại'),
  insetSize: z.number().describe('Cạnh khung phóng đại'),
  insetZoom: z.number().describe('Độ phóng của khung chi tiết'),
  diemX: z.number().describe('Vị trí ngang của Joshua Minyard trên ảnh (0-1)'),
  diemY: z.number().describe('Vị trí dọc của Joshua Minyard trên ảnh (0-1)'),
  netDay: z.number().describe('Độ dày đường chỉ định vị'),
  mauNet: z.string().describe('Màu đường chỉ định vị'),
});

/* ---------- Năm 1996 ở góc trái ---------- */
function ChuNam({nam, co, mau}) {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 16], [0, 1], kep);
  const y = interpolate(f, [0, 24], [26, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const gach = interpolate(f, [12, 42], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});

  return (
    <div style={{opacity: op, transform: `translateY(${y}px)`}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 300,
          color: mau,
          letterSpacing: co * 0.07,
          lineHeight: 1,
          textShadow: '0 8px 46px rgba(0,0,0,0.6)',
          whiteSpace: 'nowrap',
        }}
      >
        {nam}
      </div>
      <div
        style={{
          marginTop: co * 0.18,
          height: 4,
          width: co * 2.7,
          backgroundColor: VANG,
          opacity: 0.9,
          transform: `scaleX(${gach})`,
          transformOrigin: 'left center',
        }}
      />
    </div>
  );
}

/* ---------- Khung phóng đại chi tiết Joshua Minyard ---------- */
function KhungPhongDai({anh, size, zoom, px, py}) {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  const vao = spring({frame: f, fps, config: {damping: 200, mass: 0.8}, durationInFrames: 34});
  const op = interpolate(f, [0, 12], [0, 1], kep);
  const sc = interpolate(vao, [0, 1], [0.84, 1], kep);
  const troi = interpolate(f, [0, 203], [0, -16], kep);

  const imgW = 1920 * zoom;
  const imgH = 1080 * zoom;

  return (
    <div
      style={{
        width: size,
        height: size,
        opacity: op,
        transform: `scale(${sc})`,
        transformOrigin: '50% 50%',
        borderRadius: 26,
        overflow: 'hidden',
        border: '3px solid rgba(246,242,232,0.92)',
        boxShadow: '0 36px 90px rgba(0,0,0,0.6)',
        position: 'relative',
      }}
    >
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          width: imgW,
          height: imgH,
          maxWidth: 'none',
          left: size / 2 - px * imgW + troi,
          top: size / 2 - py * imgH,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: size,
          height: size,
          boxShadow: 'inset 0 0 100px rgba(0,0,0,0.38)',
        }}
      />
    </div>
  );
}

/* ---------- Đường chỉ mảnh nối Joshua với khung phóng đại ---------- */
function DuongChi({px, py, dichX, dichY, netDay, mauNet, batDau, zoomDau, zoomCuoi}) {
  const f = useCurrentFrame();
  const g = batDau + f;

  const s = interpolate(g, [0, 283], [zoomDau, zoomCuoi], kep);
  const x = 960 + (px * 1920 - 960) * s;
  const y = 540 + (py * 1080 - 540) * s;

  const p = interpolate(f, [0, 28], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const op = interpolate(f, [0, 10], [0, 1], kep);

  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, opacity: op, pointerEvents: 'none'}}>
      <path
        d={`M ${x} ${y} L ${dichX} ${dichY}`}
        fill="none"
        stroke={mauNet}
        strokeWidth={netDay}
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray="1"
        strokeDashoffset={1 - p}
      />
      <circle cx={x} cy={y} r={17} fill="none" stroke={mauNet} strokeWidth={netDay} opacity={p} />
      <circle cx={x} cy={y} r={5} fill={mauNet} opacity={p} />
    </svg>
  );
}

export const Canh = (props) => {
  const {
    anh,
    nam,
    namX,
    namY,
    coNam,
    mauNam,
    zoomDau,
    zoomCuoi,
    toiNen,
    insetX,
    insetY,
    insetSize,
    insetZoom,
    diemX,
    diemY,
    netDay,
    mauNet,
  } = props;

  const dichX = insetX - 8;
  const dichY = insetY + insetSize * 0.5;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0b0b', fontFamily: FONT}}>
      {/* Toàn cảnh ảnh tư liệu — push-in cực chậm suốt cả cảnh */}
      <Interactive.Div
        name="Ảnh nền bãi lốp 1996"
        from={0}
        durationInFrames={283}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anh} tu={zoomDau} den={zoomCuoi} goc="50% 52%" toi={toiNen} />
      </Interactive.Div>

      {/* Vệt tối nhẹ góc trái dưới cho năm dễ đọc */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          background: 'radial-gradient(1000px 680px at 6% 94%, rgba(0,0,0,0.46), rgba(0,0,0,0) 72%)',
          pointerEvents: 'none',
        }}
      />

      {/* Năm 1996 */}
      <Interactive.Div
        name="Năm 1996"
        from={2}
        durationInFrames={281}
        style={{position: 'absolute', left: namX, top: namY}}
      >
        <ChuNam nam={nam} co={coNam} mau={mauNam} />
      </Interactive.Div>

      {/* Khung phóng đại chi tiết Joshua Minyard */}
      <Interactive.Div
        name="Khung phóng đại Joshua Minyard"
        from={80}
        durationInFrames={203}
        style={{position: 'absolute', left: insetX, top: insetY}}
      >
        <KhungPhongDai anh={anh} size={insetSize} zoom={insetZoom} px={diemX} py={diemY} />
      </Interactive.Div>

      {/* Đường chỉ định vị */}
      <Interactive.Div
        name="Đường chỉ định vị"
        from={80}
        durationInFrames={203}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <DuongChi
          px={diemX}
          py={diemY}
          dichX={dichX}
          dichY={dichY}
          netDay={netDay}
          mauNet={mauNet}
          batDau={80}
          zoomDau={zoomDau}
          zoomCuoi={zoomCuoi}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
