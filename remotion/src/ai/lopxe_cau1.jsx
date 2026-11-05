import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhSaMac: z.string().describe('Ảnh nền lòng suối cạn giữa sa mạc Arizona'),
  anhLongSuoi: z.string().describe('Ảnh nền lòng suối cạn nhìn dọc theo bờ'),
  anhBaiLop: z.string().describe('Ảnh nền bãi lốp xe giữa hoang mạc'),
  anhCumLop: z.string().describe('Ảnh tách nền cụm lốp xe trút xuống'),
  soLop: z.number().describe('Số lốp xe hiện trên bộ đếm'),
  coSoDem: z.number().describe('Cỡ chữ bộ đếm'),
  giayDem: z.number().describe('Thời gian bộ đếm chạy (giây)'),
  doToiSaMac: z.number().describe('Độ tối nền sa mạc nhịp mở'),
  doToiLongSuoi: z.number().describe('Độ tối nền lòng suối nhịp chuyển'),
  doToiBaiLop: z.number().describe('Độ tối nền bãi lốp nhịp kết'),
  doDamBui: z.number().describe('Độ đậm của bụi đất khi lốp chạm đáy'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // ---- Nhịp 2: cụm lốp trút xuống (bắt đầu đúng frame 64) ----
  const roiY = interpolate(frame, [64, 100, 112, 124], [-760, 330, 292, 322], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });
  const nghieng = interpolate(frame, [64, 104], [-6, 0], kep);
  const moLop = interpolate(frame, [166, 180], [1, 0], kep);

  // Bụi đất khi lốp đập xuống đáy rãnh
  const buiMo = interpolate(frame, [96, 106, 152], [0, props.doDamBui, 0], kep);
  const buiPhong = interpolate(frame, [96, 154], [0.55, 1.55], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#2a2118', fontFamily: FONT}}>

      {/* ===== NHỊP MỞ (frame 0 → 70): đại cảnh lòng suối cạn Arizona, trôi chậm ===== */}
      <Interactive.Div
        name="Nền sa mạc Arizona trôi chậm"
        from={0}
        durationInFrames={70}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia
          anh={props.anhSaMac}
          huong="phai"
          quang={80}
          phong={1.08}
          toi={props.doToiSaMac}
        />
      </Interactive.Div>

      {/* ===== NHỊP CHUYỂN (frame 64 → 180): góc thấp dọc lòng suối cạn ===== */}
      <Interactive.Div
        name="Lòng suối cạn nhìn dọc theo bờ"
        from={64}
        durationInFrames={116}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anhLongSuoi}
          tu={1.02}
          den={1.14}
          goc="50% 58%"
          toi={props.doToiLongSuoi}
        />
      </Interactive.Div>

      {/* ===== NHỊP KẾT (frame 176 → 281): pull-back ra bãi lốp mênh mông ===== */}
      <Interactive.Div
        name="Bãi lốp giữa hoang mạc (pull-back)"
        from={176}
        durationInFrames={105}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anhBaiLop}
          tu={1.2}
          den={1.0}
          goc="50% 50%"
          toi={props.doToiBaiLop}
        />
      </Interactive.Div>

      {/* ===== Cụm lốp phế liệu trút rơi xuống lòng suối ===== */}
      <Interactive.Div
        name="Cụm lốp xe trút xuống"
        from={64}
        durationInFrames={116}
        style={{position: 'absolute', left: 470, top: 0, width: 980, height: 662}}
      >
        <Img
          src={src(props.anhCumLop)}
          style={{
            position: 'absolute',
            left: 0,
            top: roiY,
            width: 980,
            height: 662,
            objectFit: 'contain',
            opacity: moLop,
            transform: `rotate(${nghieng}deg)`,
            transformOrigin: '50% 50%',
          }}
        />
      </Interactive.Div>

      {/* ===== Bụi đất mù mịt khi lốp chạm đáy rãnh ===== */}
      <Interactive.Div
        name="Bụi đất bốc lên"
        from={96}
        durationInFrames={72}
        style={{position: 'absolute', left: 380, top: 690, width: 1120, height: 380}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1120,
            height: 380,
            opacity: buiMo,
            transform: `scale(${buiPhong})`,
            transformOrigin: '50% 62%',
            background:
              'radial-gradient(ellipse at 50% 62%, rgba(196,172,136,0.85) 0%, rgba(184,158,120,0.55) 38%, rgba(170,146,110,0.0) 72%)',
          }}
        />
      </Interactive.Div>

      {/* ===== Bộ đếm số lượng 0 → 1.500 ===== */}
      <Interactive.Div
        name="Bộ đếm số lốp xe"
        from={66}
        durationInFrames={108}
        style={{position: 'absolute', left: 108, top: 772}}
      >
        <div
          style={{
            position: 'absolute',
            left: -26,
            top: -22,
            width: 470,
            height: 214,
            borderRadius: 18,
            background: 'rgba(14,11,8,0.34)',
          }}
        />
        <SoDem
          so={props.soLop}
          don_vi=""
          giay={props.giayDem}
          co={props.coSoDem}
        />
      </Interactive.Div>

    </AbsoluteFill>
  );
};
