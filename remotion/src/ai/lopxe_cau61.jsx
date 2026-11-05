import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền lòng suối cạn trơ sỏi đá'),
  anhBui: z.string().describe('Lớp bụi mù cuộn (tách nền)'),
  anhMua: z.string().describe('Màn mưa xối xả (tách nền)'),
  anhLu: z.string().describe('Cột lũ quét bùn đỏ (tách nền)'),
  doDamNen: z.number().describe('Độ đậm tối đa của bầu trời xám đen'),
  doDamBui: z.number().describe('Độ đậm lớp bụi mù'),
  doDamMua: z.number().describe('Độ đậm màn mưa'),
  doDamLu: z.number().describe('Độ đậm cột lũ quét'),
  rungBienDo: z.number().describe('Biên độ rung lắc khung hình khi mưa (px)'),
  phongNen: z.number().describe('Mức punch-in nền khi lũ ập tới'),
});

/* ---------- NỀN: lòng suối cạn, tối dần, punch-in khi lũ tới ---------- */
const LopNen = ({anh, phong, rung}) => {
  const f = useCurrentFrame();
  const punch = interpolate(f, [216, 355], [1, phong], {...kep, easing: Easing.inOut(Easing.quad)});
  const amp = interpolate(f, [113, 130, 355], [0, 1, 0.55], kep);
  const sx = Math.sin(f * 1.9) * rung * amp;
  const sy = Math.cos(f * 2.7) * rung * 0.7 * amp;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `scale(${punch}) translate(${sx}px, ${sy}px)`,
        transformOrigin: '50% 52%',
      }}
    >
      <AnhNen anh={anh} tu={1} den={1.1} goc="50% 48%" toi={0} />
    </div>
  );
};

/* ---------- BẦU TRỜI TỐI SẦM ---------- */
const ToiTroi = ({doDam}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 45, 95, 350], [0, doDam * 0.45, doDam, doDam * 0.92], kep);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        opacity: op,
        background:
          'linear-gradient(180deg, rgba(22,25,31,0.95) 0%, rgba(36,40,46,0.60) 40%, rgba(62,54,42,0.08) 100%)',
      }}
    />
  );
};

/* ---------- BỤI MÙ CUỘN TỪ HẬU CẢNH RA TIỀN CẢNH ---------- */
const LopBui = ({anh, doDam}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 190], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  const x = interpolate(p, [0, 1], [500, -760]);
  const y = interpolate(p, [0, 1], [-70, 400]);
  const sc = interpolate(p, [0, 1], [1, 3.2]);
  const op = interpolate(f, [0, 22, 118, 190], [0, doDam, doDam * 0.65, 0], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        position: 'absolute',
        left: 660,
        top: 150,
        width: 700,
        height: 383,
        transform: `translate(${x}px, ${y}px) scale(${sc})`,
        transformOrigin: '50% 50%',
        opacity: op,
      }}
    />
  );
};

/* ---------- MƯA XỐI XẢ ---------- */
const LopMua = ({anh, doDam}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 14], [0, doDam], kep);
  const y = interpolate(f, [0, 242], [-150, 150], kep);
  const x = interpolate(f, [0, 242], [70, -70], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        position: 'absolute',
        left: -440,
        top: -164,
        width: 2800,
        height: 1408,
        transform: `translate(${x}px, ${y}px)`,
        opacity: op,
      }}
    />
  );
};

/* ---------- NHÒE ƯỚT MẶT KÍNH ---------- */
const UotKinh = () => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 20], [0, 1], kep);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        opacity: op,
        background:
          'radial-gradient(120% 90% at 50% 50%, rgba(198,212,222,0) 34%, rgba(158,178,194,0.26) 72%, rgba(110,132,150,0.46) 100%)',
      }}
    />
  );
};

/* ---------- CHỚP LÓE ---------- */
const ChopLoE = () => {
  const f = useCurrentFrame();
  const a = interpolate(f, [0, 2, 4, 7, 12, 58, 61, 66], [0, 0.42, 0.10, 0.30, 0, 0, 0.22, 0], kep);
  return <div style={{position: 'absolute', inset: 0, backgroundColor: '#eaf2ff', opacity: a}} />;
};

/* ---------- LŨ QUÉT BÙN ĐỎ ẬP TỚI ---------- */
const LuQuet = ({anh, doDam}) => {
  const f = useCurrentFrame();
  const sc = interpolate(f, [0, 138], [0.95, 5.2], {...kep, easing: Easing.in(Easing.quad)});
  const tx = interpolate(f, [0, 138], [70, -360], kep);
  const ty = interpolate(f, [0, 138], [-30, 330], kep);
  const op = interpolate(f, [0, 8], [0, doDam], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        position: 'absolute',
        left: 1000,
        top: 300,
        width: 700,
        height: 319,
        transform: `translate(${tx}px, ${ty}px) scale(${sc})`,
        transformOrigin: '50% 50%',
        opacity: op,
      }}
    />
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#2a2622'}}>
      <Interactive.Div
        name="Lòng suối cạn"
        from={0}
        durationInFrames={355}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopNen anh={props.anhNen} phong={props.phongNen} rung={props.rungBienDo} />
      </Interactive.Div>

      <Interactive.Div
        name="Trời tối sầm"
        from={5}
        durationInFrames={350}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <ToiTroi doDam={props.doDamNen} />
      </Interactive.Div>

      <Interactive.Div
        name="Bụi mù cuộn"
        from={5}
        durationInFrames={195}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopBui anh={props.anhBui} doDam={props.doDamBui} />
      </Interactive.Div>

      <Interactive.Div
        name="Mưa xối xả"
        from={113}
        durationInFrames={242}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopMua anh={props.anhMua} doDam={props.doDamMua} />
      </Interactive.Div>

      <Interactive.Div
        name="Nhòe ướt ống kính"
        from={113}
        durationInFrames={242}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <UotKinh />
      </Interactive.Div>

      <Interactive.Div
        name="Chớp lóe"
        from={113}
        durationInFrames={242}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <ChopLoE />
      </Interactive.Div>

      <Interactive.Div
        name="Lũ quét bùn đỏ"
        from={216}
        durationInFrames={139}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LuQuet anh={props.anhLu} doDam={props.doDamLu} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
