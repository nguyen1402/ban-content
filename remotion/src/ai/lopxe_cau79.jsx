import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền cận cảnh sỏi cát ven suối'),
  anhMach: z.string().describe('Ảnh cut-out mạch nước ngầm'),
  anhDat: z.string().describe('Ảnh cấu trúc đất ngậm nước'),
  zoomNenTu: z.number().describe('Độ phóng nền lúc bắt đầu'),
  zoomNenDen: z.number().describe('Độ phóng nền lúc kết thúc'),
  toiNen: z.number().describe('Độ tối lớp nền (0..0.5)'),
  machRong: z.number().describe('Chiều rộng cut-out mạch nước (px)'),
  machCao: z.number().describe('Chiều cao cut-out mạch nước (px)'),
  machTrai: z.number().describe('Toạ độ trái cut-out mạch nước (px)'),
  machTren: z.number().describe('Toạ độ trên cut-out mạch nước (px)'),
  theTrai: z.number().describe('Toạ độ trái thẻ ảnh cấu trúc đất (px)'),
  theTren: z.number().describe('Toạ độ trên thẻ ảnh cấu trúc đất (px)'),
  theRong: z.number().describe('Chiều rộng thẻ ảnh cấu trúc đất (px)'),
  theCao: z.number().describe('Chiều cao thẻ ảnh cấu trúc đất (px)'),
  mauVien: z.string().describe('Màu viền thẻ ảnh'),
  mauQuet: z.string().describe('Màu vệt sáng quét'),
  doDaiQuet: z.number().describe('Số khung hình vệt sáng quét qua'),
});

/* ---------- vệt sáng quét ---------- */
const VetSang = ({mau, dai}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, dai], [-760, 2160], {...kep, easing: Easing.inOut(Easing.ease)});
  const opa = interpolate(f, [0, 10, dai - 18, dai], [0, 0.8, 0.8, 0], kep);
  return (
    <AbsoluteFill style={{overflow: 'hidden', opacity: opa}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: -320,
          width: 520,
          height: 1740,
          transform: `translateX(${x}px) rotate(13deg)`,
          background: `linear-gradient(90deg, rgba(255,244,214,0) 0%, ${mau} 50%, rgba(255,244,214,0) 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};

/* ---------- cut-out mạch nước ngầm ---------- */
const MachNuoc = ({anh, rong, cao}) => {
  const f = useCurrentFrame();
  const mo = interpolate(f, [0, 26], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const truot = interpolate(mo, [0, 1], [-330, 0]);
  const clip = interpolate(mo, [0, 1], [0, 100]);
  const opa = interpolate(f, [0, 16], [0, 1], kep);
  const driftX = interpolate(f, [0, 254], [-16, 44], kep);
  const driftY = interpolate(f, [0, 254], [12, -36], kep);
  const scale = interpolate(f, [0, 254], [1.05, 0.96], kep);
  return (
    <div
      style={{
        width: rong,
        height: cao,
        opacity: opa,
        transform: `translate(${truot + driftX}px, ${driftY}px) scale(${scale})`,
        clipPath: `inset(0% ${100 - clip}% 0% 0%)`,
        filter: 'drop-shadow(0 22px 42px rgba(0,0,0,0.45))',
      }}
    >
      <Img
        name="Mạch nước ngầm"
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'contain'}}
      />
    </div>
  );
};

/* ---------- thẻ ảnh cấu trúc đất ngậm nước ---------- */
const TheAnh = ({anh, trai, tren, rong, cao, mauVien}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200, mass: 0.9}});
  const moRong = interpolate(f, [59, 90], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const left = interpolate(moRong, [0, 1], [trai, 0]);
  const top = interpolate(moRong, [0, 1], [tren, 0]);
  const w = interpolate(moRong, [0, 1], [rong, 1920]);
  const h = interpolate(moRong, [0, 1], [cao, 1080]);
  const dx = interpolate(vao, [0, 1], [520, 0]);
  const opa = interpolate(f, [0, 12], [0, 1], kep);
  const vien = interpolate(moRong, [0, 1], [4, 0]);
  const banKinh = interpolate(moRong, [0, 1], [26, 0]);
  const zoomAnh = interpolate(f, [0, 101], [1.16, 1.0], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left,
        top,
        width: w,
        height: h,
        opacity: opa,
        transform: `translateX(${dx}px)`,
        borderRadius: banKinh,
        border: `${vien}px solid ${mauVien}`,
        overflow: 'hidden',
        boxShadow: '0 30px 80px rgba(0,0,0,0.45)',
      }}
    >
      <Img
        name="Cấu trúc đất ngậm nước"
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoomAnh})`}}
      />
    </div>
  );
};

/* ---------- cảnh ---------- */
export const Canh = (props) => {
  const {anhNen, anhMach, anhDat, zoomNenTu, zoomNenDen, toiNen, machRong, machCao, machTrai, machTren,
    theTrai, theTren, theRong, theCao, mauVien, mauQuet, doDaiQuet} = props;

  return (
    <AbsoluteFill style={{backgroundColor: '#211a14'}}>
      {/* Nền sỏi cát ven suối – push-in chậm suốt shot */}
      <Interactive.Div
        name="Nền sỏi cát ven suối"
        from={0}
        durationInFrames={346}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anhNen} tu={zoomNenTu} den={zoomNenDen} goc="50% 45%" toi={toiNen} />
      </Interactive.Div>

      {/* Thẻ ảnh cấu trúc đất ngậm nước (trượt vào rồi mở rộng toàn khung) */}
      <Interactive.Div
        name="Thẻ ảnh cấu trúc đất ngậm nước"
        from={245}
        durationInFrames={101}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <TheAnh
          anh={anhDat}
          trai={theTrai}
          tren={theTren}
          rong={theRong}
          cao={theCao}
          mauVien={mauVien}
        />
      </Interactive.Div>

      {/* Cut-out mạch nước ngầm trượt mở bên trái */}
      <Interactive.Div
        name="Mạch nước ngầm"
        from={92}
        durationInFrames={254}
        style={{position: 'absolute', left: machTrai, top: machTren, width: machRong, height: machCao}}
      >
        <MachNuoc anh={anhMach} rong={machRong} cao={machCao} />
      </Interactive.Div>

      {/* Vệt sáng quét qua lớp sỏi cát ngầm */}
      <Interactive.Div
        name="Vệt sáng quét lớp sỏi cát"
        from={189}
        durationInFrames={62}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <VetSang mau={mauQuet} dai={doDaiQuet} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
