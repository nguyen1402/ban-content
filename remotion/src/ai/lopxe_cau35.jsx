import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhKho: z.string().describe('Ảnh nền kho chứa lốp xe cũ'),
  anhManh: z.string().describe('Ảnh cắt mảnh cao su tái chế (nền trong suốt)'),
  anhDap: z.string().describe('Ảnh nền con đập xếp bằng lốp xe cũ'),
  tuKho: z.number().describe('Tỉ lệ zoom đầu của nền kho cao su'),
  denKho: z.number().describe('Tỉ lệ zoom cuối của nền kho cao su'),
  toiKho: z.number().describe('Độ tối lớp phủ nền kho (0..0.5)'),
  rongManhA: z.number().describe('Chiều rộng mảnh cao su lớp trước (px)'),
  rongManhB: z.number().describe('Chiều rộng mảnh cao su lớp sau (px)'),
  tuDap: z.number().describe('Tỉ lệ zoom đầu của nền con đập'),
  denDap: z.number().describe('Tỉ lệ zoom cuối của nền con đập'),
  doMoDap: z.number().describe('Độ đậm cuối của nền con đập (0..1)'),
});

// Mốc nhịp (frame) — dùng trực tiếp cho from / durationInFrames
const F_NHIP1 = 4;
const F_NHIP2 = 68;
// Cảnh dài 194 khung: mọi khối nền phải sống tới khung cuối, không khối nào được cắt sớm
const DAI_CANH = 194;
const DAI_NEN_KHO = 194; // nền kho giữ suốt cảnh (đã mờ hẳn từ khung 84 nên không lộ ảnh cũ)
const DAI_MANH = 72;
const DAI_DAP = 126; // 194 - 68: nhịp con đập giữ đúng tới khung cuối của cảnh

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const f1 = frame - F_NHIP1;
  const f2 = frame - F_NHIP2;

  // Nhịp 1 -> nhịp 2: nền kho tan dần (khối vẫn giữ nguyên, không mount lại)
  const opKho = interpolate(frame, [F_NHIP2, F_NHIP2 + 16], [1, 0], kep);

  // Nhịp 2: con đập trượt vào + hạ zoom, giữ tới khung cuối
  const opDap = interpolate(f2, [0, 18], [0, props.doMoDap], kep);
  const scaleDap = interpolate(f2, [0, DAI_DAP], [props.tuDap, props.denDap], {
    ...kep,
    easing: Easing.out(Easing.quad),
  });
  const xDap = interpolate(f2, [0, 22], [80, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const yDap = interpolate(f2, [0, 22], [-24, 0], {...kep, easing: Easing.out(Easing.cubic)});

  // Mảnh cao su lớp trước (A)
  const spA = spring({frame: f1, fps, config: {damping: 20, mass: 1.2, stiffness: 90}});
  const xA = interpolate(f1, [0, DAI_MANH], [-140, 130], kep);
  const yA = interpolate(f1, [0, DAI_MANH], [40, -34], kep);
  const rotA = interpolate(f1, [0, DAI_MANH], [-12, -3], kep);
  const scA = 0.86 + 0.14 * spA;
  const opA = interpolate(f1, [0, 12, 58, DAI_MANH], [0, 1, 1, 0], kep);

  // Mảnh cao su lớp sau (B)
  const spB = spring({frame: f1 - 6, fps, config: {damping: 22, mass: 1, stiffness: 80}});
  const xB = interpolate(f1, [0, DAI_MANH], [170, -70], kep);
  const yB = interpolate(f1, [0, DAI_MANH], [-28, 44], kep);
  const rotB = interpolate(f1, [0, DAI_MANH], [14, 5], kep);
  const scB = 0.86 + 0.14 * spB;
  const opB = interpolate(f1, [4, 16, 58, DAI_MANH], [0, 1, 1, 0], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#221b16'}}>
      {/* Nhịp 1 — nền kho cao su (một khối duy nhất, chỉ mờ dần chứ không mount lại).
          Giữ khối tới khung cuối cảnh để không bị cắt sớm / lộ lại ảnh cũ. */}
      <Interactive.Div
        name="Nền kho cao su"
        from={0}
        durationInFrames={194}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: opKho}}>
          <AnhNen anh={props.anhKho} tu={props.tuKho} den={props.denKho} goc="50% 45%" toi={props.toiKho} />
        </AbsoluteFill>
      </Interactive.Div>

      {/* Nhịp 2 — con đập lốp xe: một khối duy nhất, phủ đúng tới khung cuối (68 + 126 = 194) */}
      <Interactive.Div
        name="Nền con đập lốp xe"
        from={68}
        durationInFrames={126}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: opDap}}>
          <Img
            src={src(props.anhDap)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `translate(${xDap}px, ${yDap}px) scale(${scaleDap})`,
              transformOrigin: '50% 50%',
            }}
          />
        </AbsoluteFill>
      </Interactive.Div>

      {/* Mảnh cao su tái chế: MỘT khối duy nhất chứa cả hai lớp, ảnh chỉ mount một lần */}
      <Interactive.Div
        name="Mảnh cao su tái chế"
        from={4}
        durationInFrames={72}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill>
          {/* Lớp sau */}
          <div
            style={{
              position: 'absolute',
              left: 1060,
              top: 80,
              opacity: opB,
              transform: `translate(${xB}px, ${yB}px) rotate(${rotB}deg) scale(${scB})`,
              transformOrigin: '50% 50%',
            }}
          >
            <Img
              src={src(props.anhManh)}
              style={{width: props.rongManhB, height: 'auto', display: 'block'}}
            />
          </div>

          {/* Lớp trước */}
          <div
            style={{
              position: 'absolute',
              left: 40,
              top: 470,
              opacity: opA,
              transform: `translate(${xA}px, ${yA}px) rotate(${rotA}deg) scale(${scA})`,
              transformOrigin: '50% 50%',
            }}
          >
            <Img
              src={src(props.anhManh)}
              style={{width: props.rongManhA, height: 'auto', display: 'block'}}
            />
          </div>
        </AbsoluteFill>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
