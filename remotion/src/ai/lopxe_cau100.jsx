import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, AnhNen, ChuNoi} from './thu_vien.jsx';

export const schema = z.object({
  anhLop: z.string().describe('Đường dẫn ảnh bãi rác lốp xe Florida'),
  anhRan: z.string().describe('Đường dẫn ảnh rạn san hô nhân tạo dưới biển'),
  tieuDe: z.string().describe('Tiêu đề ngắn hiện ở đầu cảnh'),
  coTieuDe: z.number().describe('Cỡ chữ tiêu đề (px)'),
  mauMuiTen: z.string().describe('Màu mũi tên đồ họa'),
  mauVong: z.string().describe('Màu vòng mục tiêu'),
  netMuiTen: z.number().describe('Độ dày nét mũi tên'),
  toiLop: z.number().describe('Độ tối ảnh bãi lốp (0-0.5)'),
  toiRan: z.number().describe('Độ tối ảnh rạn san hô (0-0.5)'),
  zoomLop: z.number().describe('Mức zoom cuối của ảnh bãi lốp'),
  zoomRan: z.number().describe('Mức zoom cuối của ảnh rạn san hô'),
});

/* ---------- Ảnh bãi lốp xe: zoom chậm + punch-in ở frame 43 ---------- */
const LopXe = ({anh, toi, zoom}) => {
  const f = useCurrentFrame();
  const punch = interpolate(f, [43, 52, 62], [0, 0.16, 0.09], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `scale(${1 + punch})`,
        transformOrigin: '50% 55%',
      }}
    >
      <AnhNen anh={anh} tu={1} den={zoom} goc="50% 55%" toi={toi} />
    </div>
  );
};

/* ---------- Tiêu đề ngắn ---------- */
const TieuDe = ({chu, co}) => {
  return <ChuNoi chu={chu} co={co} />;
};

/* ---------- Mũi tên tách đôi, hai vòng mục tiêu ---------- */
const MuiTenChiaHai = ({mau, mauVong, net}) => {
  const f = useCurrentFrame();

  const p1 = interpolate(f, [0, 16], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p2 = interpolate(f, [12, 36], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p3 = interpolate(f, [30, 44], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const r1 = interpolate(f, [17, 31], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const r2 = interpolate(f, [21, 35], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  const netVe = {
    fill: 'none',
    stroke: mau,
    strokeWidth: net,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    pathLength: 1,
    strokeDasharray: 1,
  };

  return (
    <svg
      width={1920}
      height={1080}
      viewBox="0 0 1920 1080"
      style={{position: 'absolute', left: 0, top: 0}}
    >
      <circle
        cx={1500}
        cy={300}
        r={140}
        fill="none"
        stroke={mauVong}
        strokeWidth={10}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - r1}
        opacity={0.95}
      />
      <circle
        cx={1500}
        cy={780}
        r={140}
        fill="none"
        stroke={mauVong}
        strokeWidth={10}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - r2}
        opacity={0.95}
      />

      <path d="M 220 540 L 880 540" {...netVe} strokeDashoffset={1 - p1} />
      <path d="M 880 540 C 1090 540 1200 420 1380 325" {...netVe} strokeDashoffset={1 - p2} />
      <path d="M 880 540 C 1090 540 1200 660 1380 755" {...netVe} strokeDashoffset={1 - p2} />
      <path d="M 1294 323 L 1380 325 L 1334 397" {...netVe} strokeDashoffset={1 - p3} />
      <path d="M 1294 757 L 1380 755 L 1334 683" {...netVe} strokeDashoffset={1 - p3} />
    </svg>
  );
};

/* ---------- Rạn san hô: trượt vào từ phải, sau đó zoom chậm vào đàn cá ---------- */
const RanSanHo = ({anh, toi, zoom}) => {
  const f = useCurrentFrame();
  const slide = interpolate(f, [0, 26], [1920, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const z = interpolate(f, [65, 126], [1, 1.16], {...kep, easing: Easing.inOut(Easing.quad)});

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translateX(${slide}px) scale(${z})`,
        transformOrigin: '55% 62%',
      }}
    >
      <AnhNen anh={anh} tu={1} den={zoom} goc="55% 62%" toi={toi} />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#05070a', fontFamily: FONT}}>
      <Interactive.Div
        name="Bãi rác lốp xe Florida"
        from={0}
        durationInFrames={200}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopXe anh={src(props.anhLop)} toi={props.toiLop} zoom={props.zoomLop} />
      </Interactive.Div>

      <Interactive.Div
        name="Tiêu đề Florida"
        from={5}
        durationInFrames={195}
        style={{position: 'absolute', left: 110, top: 96}}
      >
        <TieuDe chu={props.tieuDe} co={props.coTieuDe} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên trúng hai đích"
        from={43}
        durationInFrames={160}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <MuiTenChiaHai mau={props.mauMuiTen} mauVong={props.mauVong} net={props.netMuiTen} />
      </Interactive.Div>

      <Interactive.Div
        name="Rạn san hô nhân tạo"
        from={176}
        durationInFrames={126}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <RanSanHo anh={src(props.anhRan)} toi={props.toiRan} zoom={props.zoomRan} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
