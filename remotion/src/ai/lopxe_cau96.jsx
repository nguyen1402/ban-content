import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anhNenSuoi: z.string().describe('Ảnh nền dòng suối ngổn ngang lốp xe cũ'),
  anhGiaoSu: z.string().describe('Ảnh tách bóng lưng vị giáo sư'),
  anhCanLop: z.string().describe('Ảnh cận cảnh cụm lốp xe bùn lầy'),
  anhBeTong: z.string().describe('Ảnh texture lớp bê tông xám mịn'),
  punchScale: z.number().describe('Độ phóng punch-in vào cụm lốp xe'),
  sweepOpacity: z.number().describe('Độ sáng của vệt quét ánh sáng'),
  sweepAngle: z.number().describe('Góc nghiêng của vệt sáng (độ)'),
  toiNen: z.number().describe('Độ tối lớp phủ lên ảnh nền'),
  concreteZoom: z.number().describe('Độ phóng của lớp bê tông ở cuối cảnh'),
  giaoSuZoom: z.number().describe('Độ phóng chậm của bóng giáo sư'),
  giaoSuMo: z.number().describe('Độ đậm bóng giáo sư'),
  vienRong: z.number().describe('Độ dày viền khung cận cảnh'),
  vienMau: z.string().describe('Màu viền khung cận cảnh'),
  boGoc: z.number().describe('Bo góc khung cận cảnh'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---- BEAT 201: punch-in cực mạnh vào cụm lốp xe ----
  const punch = interpolate(frame, [201, 216], [1, props.punchScale], {
    easing: Easing.out(Easing.cubic),
    ...kep,
  });
  const drift = interpolate(frame, [216, 377], [0, 0.03], kep);
  const bgScale = punch + drift;

  // ---- BEAT 86: vệt sáng quét qua lòng suối ----
  const sweepX = interpolate(frame, [86, 160], [-1400, 2500], {
    easing: Easing.inOut(Easing.quad),
    ...kep,
  });
  const sweepO = interpolate(frame, [86, 102, 142, 160], [0, props.sweepOpacity, props.sweepOpacity, 0], kep);

  // ---- BEAT 201: khung cận cảnh inset trượt vào góc trái ----
  const insetIn = spring({frame: frame - 201, fps, config: {damping: 200, mass: 0.8}, durationInFrames: 18});
  const insetX = interpolate(insetIn, [0, 1], [-820, 0]);
  const insetWipe = interpolate(frame, [282, 304], [0, 100], {
    easing: Easing.inOut(Easing.cubic),
    ...kep,
  });

  // ---- BEAT 282: lớp bê tông tràn từ dưới lên ----
  const concreteTop = interpolate(frame, [282, 333], [100, 0], {
    easing: Easing.inOut(Easing.cubic),
    ...kep,
  });
  const concreteScale = interpolate(frame, [282, 377], [1, props.concreteZoom], kep);

  // ---- Bóng giáo sư trôi rất chậm ----
  const profScale = interpolate(frame, [2, 377], [1, props.giaoSuZoom], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#1b1a17', overflow: 'hidden'}}>
      {/* NỀN: dòng suối lốp xe + slow push + punch-in */}
      <Interactive.Div
        name="Nền dòng suối lốp xe"
        from={0}
        durationInFrames={377}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `scale(${bgScale})`,
            transformOrigin: '44% 64%',
          }}
        >
          <AnhNen anh={props.anhNenSuoi} tu={1.02} den={1.14} goc="50% 55%" toi={props.toiNen} />
        </div>
      </Interactive.Div>

      {/* BEAT 86: vệt sáng quét */}
      <Interactive.Div
        name="Vệt sáng quét qua lòng suối"
        from={86}
        durationInFrames={76}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: -600,
            width: 900,
            height: 2300,
            opacity: sweepO,
            transform: `translateX(${sweepX}px) rotate(${props.sweepAngle}deg)`,
            background:
              'linear-gradient(90deg, rgba(255,248,224,0) 0%, rgba(255,248,224,0.55) 50%, rgba(255,248,224,0) 100%)',
          }}
        />
      </Interactive.Div>

      {/* BEAT 282: lớp bê tông tràn từ dưới lên che kín lốp xe */}
      <Interactive.Div
        name="Lớp bê tông phủ từ dưới lên"
        from={282}
        durationInFrames={95}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
          clipPath: `inset(${concreteTop}% 0% 0% 0%)`,
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `scale(${concreteScale})`,
            transformOrigin: '50% 80%',
          }}
        >
          <AnhNen anh={props.anhBeTong} tu={1.0} den={1.06} goc="50% 70%" toi={0.04} />
        </div>
      </Interactive.Div>

      {/* BEAT 201: khung ảnh inset cận cảnh cụm lốp xe, góc trái */}
      <Interactive.Div
        name="Khung cận cảnh cụm lốp xe"
        from={201}
        durationInFrames={176}
        style={{
          position: 'absolute',
          left: 110,
          top: 300,
          width: 820,
          height: 500,
          transform: `translateX(${insetX}px)`,
          clipPath: `inset(0% 0% 0% ${insetWipe}%)`,
          borderRadius: props.boGoc,
          overflow: 'hidden',
          boxShadow: '0 22px 46px rgba(0,0,0,0.5)',
        }}
      >
        <Img
          name="Cận cảnh lốp xe"
          src={src(props.anhCanLop)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
            border: `${props.vienRong}px solid ${props.vienMau}`,
            boxSizing: 'border-box',
            borderRadius: props.boGoc,
          }}
        />
      </Interactive.Div>

      {/* Bóng lưng giáo sư ở góc phải */}
      <Interactive.Div
        name="Bóng lưng giáo sư"
        from={2}
        durationInFrames={375}
        style={{position: 'absolute', left: 1480, top: 250, width: 380, height: 790}}
      >
        <Img
          name="Giáo sư"
          src={src(props.anhGiaoSu)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            opacity: props.giaoSuMo,
            transform: `scale(${profScale})`,
            transformOrigin: '50% 100%',
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
