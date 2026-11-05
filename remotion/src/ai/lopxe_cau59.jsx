import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anhTaiLieu: z.string().describe('Ảnh trang tài liệu lưu trữ tạp chí'),
  anhThungLung: z.string().describe('Ảnh toàn cảnh thung lũng sa mạc khô cằn'),
  anhThanDap: z.string().describe('Ảnh cắt bờ đập bê tông dang dở lộ cốt thép'),
  anhBao: z.string().describe('Ảnh bầu trời dông đen kịt'),
  anhLu: z.string().describe('Ảnh cắt dòng lũ quét bùn đỏ cuồn cuộn'),
  conDau: z.string().describe('Chữ trên con dấu mốc thời gian'),
  coConDau: z.number().describe('Cỡ chữ con dấu (px)'),
  mauConDau: z.string().describe('Màu mực con dấu'),
  rongThanDap: z.number().describe('Chiều rộng ảnh bờ đập (px)'),
  rongDongLu: z.number().describe('Chiều rộng ảnh dòng lũ (px)'),
  mauMuiTen: z.string().describe('Màu mũi tên cảnh báo hướng dòng chảy'),
  doDam: z.number().describe('Độ tối lớp phủ bầu trời dông (0 - 0.5)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- hoà tan giữa các ảnh nền ---------- */
  const opThungLung = interpolate(frame, [162, 170], [0, 1], kep);
  const opBao = interpolate(frame, [278, 286], [0, 1], kep);

  /* ---------- beat 1: con dấu 11/1996 ---------- */
  const lenConDau = spring({
    frame: frame - 3,
    fps,
    config: {damping: 13, mass: 0.7, stiffness: 120},
  });
  const tanConDau = interpolate(frame, [156, 168], [1, 0], kep);
  const opConDau = Math.min(Math.max(lenConDau, 0), 1) * tanConDau;

  /* ---------- beat 2: bờ đập dang dở ---------- */
  const dapScale = interpolate(frame, [170, 396], [1, 1.1], kep);
  const veMuiTen = interpolate(frame, [166, 202], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  /* ---------- beat 3: dông và lũ quét ---------- */
  const lu = interpolate(frame, [283, 372], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });
  const toiTroi = interpolate(frame, [283, 340], [0, props.doDam], kep);

  const luLeft = -280 + 660 * lu;
  const luTop = -240 + 560 * lu;
  const luScale = 0.9 + 0.35 * lu;

  return (
    <AbsoluteFill style={{backgroundColor: '#141210'}}>
      {/* ================= 1. TRANG TÀI LIỆU LƯU TRỮ ================= */}
      <Interactive.Div
        name="Trang tài liệu lưu trữ"
        from={0}
        durationInFrames={170}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhTaiLieu} tu={1} den={1.09} goc="50% 45%" toi={0.06} />
      </Interactive.Div>

      {/* con dấu mốc thời gian */}
      <Interactive.Div
        name="Con dấu mốc thời gian"
        from={3}
        durationInFrames={167}
        style={{position: 'absolute', left: 1130, top: 330}}
      >
        <div
          style={{
            opacity: opConDau,
            transform: `rotate(-9deg) scale(${0.68 + 0.32 * lenConDau})`,
            transformOrigin: '50% 50%',
            border: `10px solid ${props.mauConDau}`,
            outline: `3px solid ${props.mauConDau}`,
            outlineOffset: '10px',
            borderRadius: 12,
            padding: '16px 46px 22px 46px',
            color: props.mauConDau,
            fontFamily: FONT,
            fontSize: props.coConDau,
            fontWeight: 900,
            letterSpacing: 8,
            whiteSpace: 'nowrap',
            background: 'rgba(255,255,255,0.05)',
          }}
        >
          {props.conDau}
        </div>
      </Interactive.Div>

      {/* ================= 2. THUNG LŨNG SA MẠC ================= */}
      <Interactive.Div
        name="Toàn cảnh thung lũng"
        from={162}
        durationInFrames={128}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: opThungLung}}>
          <AnhNen anh={props.anhThungLung} tu={1.16} den={1} goc="50% 62%" toi={0.05} />
        </AbsoluteFill>
      </Interactive.Div>

      {/* ================= 3. BẦU TRỜI DÔNG ================= */}
      <Interactive.Div
        name="Bầu trời dông"
        from={278}
        durationInFrames={118}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: opBao}}>
          <AnhNen anh={props.anhBao} tu={1} den={1.13} goc="50% 38%" toi={0.08} />
        </AbsoluteFill>
      </Interactive.Div>

      {/* tối dần bầu trời */}
      <Interactive.Div
        name="Bầu trời sẫm tối"
        from={283}
        durationInFrames={113}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{backgroundColor: '#0b0d14', opacity: toiTroi}} />
      </Interactive.Div>

      {/* ================= BỜ ĐẬP DANG DỞ (giữ tới cuối) ================= */}
      <Interactive.Div
        name="Bờ đập dang dở"
        from={166}
        durationInFrames={230}
        style={{position: 'absolute', left: 540, top: 250}}
      >
        <div style={{transform: `scale(${dapScale})`, transformOrigin: '50% 60%'}}>
          <Img src={src(props.anhThanDap)} style={{width: props.rongThanDap}} />
        </div>
      </Interactive.Div>

      {/* mũi tên cảnh báo hướng dòng chảy */}
      <Interactive.Div
        name="Mũi tên cảnh báo dòng chảy"
        from={166}
        durationInFrames={130}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
          <path
            d="M 300 780 Q 460 620 720 585"
            fill="none"
            stroke={props.mauMuiTen}
            strokeWidth={18}
            strokeLinecap="round"
            strokeDasharray={620}
            strokeDashoffset={620 * (1 - veMuiTen)}
          />
          <polygon
            points="762,580 704,564 698,612"
            fill={props.mauMuiTen}
            opacity={interpolate(veMuiTen, [0.82, 1], [0, 1], kep)}
          />
        </svg>
      </Interactive.Div>

      {/* ================= DÒNG LŨ QUÉT ================= */}
      <Interactive.Div
        name="Dòng lũ quét"
        from={283}
        durationInFrames={113}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: luLeft,
            top: luTop,
            transform: `scale(${luScale})`,
            transformOrigin: '50% 50%',
          }}
        >
          <Img src={src(props.anhLu)} style={{width: props.rongDongLu}} />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
