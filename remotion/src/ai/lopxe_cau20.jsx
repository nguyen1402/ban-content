import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Interactive,
  interpolate,
  spring,
  random,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const KING_RATIO = 320 / 700; // rộng / cao của ảnh cắt lớp ông John King
const UI_RATIO = 700 / 387; // rộng / cao của ảnh cắt lớp máy ủi

export const schema = z.object({
  anhNen1: z.string().describe('Ảnh nền con đường trang trại bị bùn cát vùi lấp'),
  anhJohn: z.string().describe('Ảnh cắt lớp ông John King quay lưng'),
  anhMayUi: z.string().describe('Ảnh cắt lớp máy ủi hạng nặng'),
  anhNen2: z.string().describe('Ảnh nền con đường ngập tuyết trong bão'),
  anhXucTuyet: z.string().describe('Ảnh người công nhân cặm cụi xúc tuyết'),

  johnLeft: z.number().describe('Vị trí ngang của ông John King (px)'),
  johnTop: z.number().describe('Vị trí dọc của ông John King (px)'),
  johnHeight: z.number().describe('Chiều cao ông John King (px)'),

  mayUiLeft: z.number().describe('Vị trí ngang của máy ủi (px)'),
  mayUiTop: z.number().describe('Vị trí dọc của máy ủi (px)'),
  mayUiWidth: z.number().describe('Chiều rộng máy ủi (px)'),

  whipStart: z.number().describe('Khung hình bắt đầu cú whip-pan sang cảnh tuyết'),
  whipDur: z.number().describe('Độ dài cú whip-pan (khung hình)'),

  nen1ZoomTu: z.number().describe('Độ phóng nền bùn cát lúc bắt đầu'),
  nen1ZoomDen: z.number().describe('Độ phóng nền bùn cát lúc kết thúc'),
  nen2ZoomTu: z.number().describe('Độ phóng nền tuyết lúc bắt đầu'),
  nen2ZoomDen: z.number().describe('Độ phóng nền tuyết lúc kết thúc'),

  uiDay: z.number().describe('Quãng máy ủi trượt ngang khi gạt bùn cát (px)'),
  xucPunch: z.number().describe('Độ phóng mạnh khi punch-in người xúc tuyết'),

  toiNen1: z.number().describe('Độ tối nền bùn cát (0..0.5)'),
  toiNen2: z.number().describe('Độ tối nền tuyết (0..0.5)'),
});

/* ---------------- Ông John King: cắt lớp, hiện lên rồi trôi rất chậm ---------------- */
const OngKing = ({anh}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f, fps, config: {damping: 200, mass: 0.6, stiffness: 120}});
  const drift = interpolate(f, [0, 220], [0, -18], CL);
  return (
    <Img
      src={src(anh)}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'contain',
        opacity: interpolate(p, [0, 0.55], [0, 1], CL),
        transform: `translateY(${(1 - p) * 60 + drift}px)`,
      }}
    />
  );
};

/* ---------------- Máy ủi: push-in, rồi trượt ngang gạt bùn cát ---------------- */
const MayUi = ({anh, day}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f, fps, config: {damping: 200, mass: 0.8, stiffness: 110}});
  const push = interpolate(f, [0, 16], [0.8, 1], {easing: Easing.out(Easing.cubic), ...CL});
  const creep = interpolate(f, [16, 135], [0, 0.05], CL);
  const slide = interpolate(f, [50, 74], [0, day], {easing: Easing.inOut(Easing.cubic), ...CL});
  const drift = interpolate(f, [0, 135], [0, 26], CL);
  const scale = push + creep;
  return (
    <Img
      src={src(anh)}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'contain',
        opacity: interpolate(p, [0, 0.5], [0, 1], CL),
        transform: `translateX(${slide + drift}px) scale(${scale})`,
        transformOrigin: '50% 100%',
      }}
    />
  );
};

/* ---------------- Người xúc tuyết: punch-in mạnh rồi pull-back ---------------- */
const XucTuyet = ({anh, punch}) => {
  const f = useCurrentFrame();
  const scale = interpolate(f, [0, 16, 62, 135], [1, punch, punch + 0.04, 1], {
    easing: Easing.out(Easing.cubic),
    ...CL,
  });
  const x = interpolate(f, [0, 135], [0, -24], CL);
  const y = interpolate(f, [0, 135], [0, 12], CL);
  return (
    <Img
      src={src(anh)}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        transform: `translate(${x}px, ${y}px) scale(${scale})`,
        transformOrigin: '50% 55%',
      }}
    />
  );
};

export const Canh = (props) => {
  const frame = useCurrentFrame();

  /* Cú whip-pan: cảnh bùn cát trượt sang trái, cảnh tuyết trượt vào từ bên phải */
  const whipP = interpolate(frame, [props.whipStart, props.whipStart + props.whipDur], [0, 1], {
    easing: Easing.out(Easing.cubic),
    ...CL,
  });
  const whipOut = -whipP * 1920;
  const whipIn = (1 - whipP) * 1920;

  const johnW = props.johnHeight * KING_RATIO;
  const mayUiH = props.mayUiWidth / UI_RATIO;

  return (
    <AbsoluteFill style={{backgroundColor: '#1a1410'}}>
      {/* ---------- GIAI ĐOẠN 1: ĐƯỜNG TRANG TRẠI BÙN CÁT ---------- */}
      <Interactive.Div
        name="Nền đường trang trại bùn cát"
        from={0}
        durationInFrames={222}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${whipOut}px)`,
        }}
      >
        <AnhNen
          anh={props.anhNen1}
          tu={props.nen1ZoomTu}
          den={props.nen1ZoomDen}
          goc="50% 45%"
          toi={props.toiNen1}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Ông John King quay lưng"
        from={3}
        durationInFrames={219}
        style={{
          position: 'absolute',
          left: props.johnLeft,
          top: props.johnTop,
          width: johnW,
          height: props.johnHeight,
          transform: `translateX(${whipOut}px)`,
        }}
      >
        <OngKing anh={props.anhJohn} />
      </Interactive.Div>

      <Interactive.Div
        name="Máy ủi hạng nặng ủi bùn cát"
        from={87}
        durationInFrames={135}
        style={{
          position: 'absolute',
          left: props.mayUiLeft,
          top: props.mayUiTop,
          width: props.mayUiWidth,
          height: mayUiH,
          transform: `translateX(${whipOut}px)`,
        }}
      >
        <MayUi anh={props.anhMayUi} day={props.uiDay} />
      </Interactive.Div>

      {/* ---------- GIAI ĐOẠN 2: LỐI ĐI NGẬP TUYẾT ---------- */}
      <Interactive.Div
        name="Nền bão tuyết trắng"
        from={206}
        durationInFrames={171}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${whipIn}px)`,
        }}
      >
        <AnhNen
          anh={props.anhNen2}
          tu={props.nen2ZoomTu}
          den={props.nen2ZoomDen}
          goc="50% 50%"
          toi={props.toiNen2}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Người công nhân xúc tuyết"
        from={242}
        durationInFrames={135}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
        }}
      >
        <XucTuyet anh={props.anhXucTuyet} punch={props.xucPunch} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export const defaultProps = {
  anhNen1: 'nhan_y/cd2c719e2b2e4d.jpg',
  anhJohn: 'nhan_y/c22221f3f1eae7.png',
  anhMayUi: 'nhan_y/4ae87635091f4c.png',
  anhNen2: 'nhan_y/e6332335a67a92.jpg',
  anhXucTuyet: 'nhan_y/0fa32f5286dba4.jpg',
  johnLeft: 1318,
  johnTop: 262,
  johnHeight: 818,
  mayUiLeft: 430,
  mayUiTop: 556,
  mayUiWidth: 880,
  whipStart: 206,
  whipDur: 16,
  nen1ZoomTu: 1.04,
  nen1ZoomDen: 1.18,
  nen2ZoomTu: 1.06,
  nen2ZoomDen: 1.16,
  uiDay: 200,
  xucPunch: 1.32,
  toiNen1: 0.12,
  toiNen2: 0.1,
};
