import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhFlorida: z.string().describe('Ảnh nền bờ biển Fort Lauderdale 1972'),
  anhTroiBien: z.string().describe('Ảnh nền trời biển Đại Tây Dương'),
  anhBien: z.string().describe('Ảnh nền mặt biển Đại Tây Dương'),
  anhLopDo: z.string().describe('Ảnh cảnh lốp xe đổ ụp xuống biển'),
  anhKhinhKhiCau: z.string().describe('Ảnh tách khinh khí cầu Goodyear'),
  anhSaLan: z.string().describe('Ảnh tách đoàn sà lan chở lốp xe'),
  nhanNgay: z.string().describe('Nhãn ngày hiển thị ở góc màn hình'),
  coNhanNgay: z.number().describe('Cỡ chữ nhãn ngày (px)'),
  mauNhanNgay: z.string().describe('Màu chữ nhãn ngày'),
  coKhinhKhiCau: z.number().describe('Chiều rộng khinh khí cầu (px)'),
  coSaLan: z.number().describe('Chiều rộng đoàn sà lan (px)'),
  doToiNen: z.number().describe('Độ tối phủ lên ảnh nền (0 - 0.5)'),
  doToiCanh: z.number().describe('Độ tối phủ lên cảnh lốp xe đổ (0 - 0.5)'),
});

/* ---------- Nhãn ngày góc màn hình ---------- */
const NhanNgayEl = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 10, 78, 95], [0, 1, 1, 0], kep);
  const y = interpolate(f, [0, 14], [16, 0], kep);
  return (
    <div
      style={{
        opacity: op,
        transform: `translateY(${y}px)`,
        display: 'flex',
        alignItems: 'center',
        gap: 26,
        fontFamily: FONT,
        fontSize: co,
        lineHeight: 1,
        fontWeight: 500,
        letterSpacing: 8,
        color: mau,
        textShadow: '0 6px 26px rgba(0,0,0,0.6)',
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{width: 9, height: co * 0.92, background: VANG, borderRadius: 5, display: 'inline-block'}} />
      <span>{chu}</span>
    </div>
  );
};

/* ---------- Khinh khí cầu trôi ---------- */
const KhinhKhiCau = ({anh, rong}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 118], [110, -80], kep);
  const y = interpolate(f, [0, 118], [18, -14], kep) + Math.sin(f / 24) * 8;
  const q = interpolate(f, [0, 118], [-3.5, 1.5], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        width: rong,
        height: 'auto',
        transform: `translate(${x}px, ${y}px) rotate(${q}deg)`,
        filter: 'drop-shadow(0 22px 34px rgba(0,0,0,0.35))',
      }}
    />
  );
};

/* ---------- Đoàn sà lan tiến vào giữa khung ---------- */
const DoanSaLan = ({anh, rong}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 90], [0.94, 1.06], kep);
  const x = interpolate(f, [0, 90], [80, -30], kep);
  const y = interpolate(f, [0, 90], [64, -22], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        width: rong,
        height: 'auto',
        transformOrigin: '50% 60%',
        transform: `translate(${x}px, ${y}px) scale(${s})`,
        filter: 'drop-shadow(0 26px 42px rgba(0,0,0,0.42))',
      }}
    />
  );
};

/* Khung phủ kín màn hình cho mọi lớp nền */
const KHUNG_NEN = {
  position: 'absolute',
  left: 0,
  top: 0,
  width: 1920,
  height: 1080,
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a1418'}}>
      {/* BEAT 1 — frame 3 : toàn cảnh bờ biển Florida 1972 */}
      <Interactive.Div
        name="Nền bờ biển Florida 1972"
        from={0}
        durationInFrames={104}
        style={KHUNG_NEN}
      >
        <AnhNen anh={props.anhFlorida} tu={1.14} den={1.38} goc="50% 58%" toi={props.doToiNen} />
      </Interactive.Div>

      {/* BEAT 2 — frame 102 : trời biển + khinh khí cầu Goodyear */}
      <Interactive.Div
        name="Nền trời biển Đại Tây Dương"
        from={102}
        durationInFrames={119}
        style={KHUNG_NEN}
      >
        <AnhNen anh={props.anhTroiBien} tu={1.16} den={1.02} goc="50% 42%" toi={props.doToiNen} />
      </Interactive.Div>

      <Interactive.Div
        name="Khinh khí cầu Goodyear"
        from={102}
        durationInFrames={118}
        style={{position: 'absolute', left: 540, top: 56}}
      >
        <KhinhKhiCau anh={props.anhKhinhKhiCau} rong={props.coKhinhKhiCau} />
      </Interactive.Div>

      {/* Nhãn ngày — giữ 3 giây đầu */}
      <Interactive.Div
        name="Nhãn ngày 01.04.1972"
        from={3}
        durationInFrames={96}
        style={{position: 'absolute', left: 112, top: 92}}
      >
        <NhanNgayEl chu={props.nhanNgay} co={props.coNhanNgay} mau={props.mauNhanNgay} />
      </Interactive.Div>

      {/* BEAT 3 — frame 219 : tilt xuống mặt biển, sà lan chở lốp xe */}
      <Interactive.Div
        name="Nền mặt biển Đại Tây Dương"
        from={219}
        durationInFrames={90}
        style={KHUNG_NEN}
      >
        <AnhLia anh={props.anhBien} huong="xuong" quang={150} phong={1.14} toi={props.doToiNen} />
      </Interactive.Div>

      <Interactive.Div
        name="Đoàn sà lan chở lốp xe"
        from={219}
        durationInFrames={90}
        style={{position: 'absolute', left: 350, top: 402}}
      >
        <DoanSaLan anh={props.anhSaLan} rong={props.coSaLan} />
      </Interactive.Div>

      {/* BEAT 4 — frame 306 : sàn sà lan trút lốp xuống biển, bọt trắng xoá */}
      <Interactive.Div
        name="Cảnh lốp xe đổ ụp xuống biển"
        from={306}
        durationInFrames={64}
        style={KHUNG_NEN}
      >
        <AnhNen anh={props.anhLopDo} tu={1.08} den={1.32} goc="50% 52%" toi={props.doToiCanh} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
