import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anhNuoc: z.string().describe('Ảnh nền nguồn nước với lốp xe cao su chìm'),
  anhFort: z.string().describe('Ảnh tư liệu vùng biển Fort Lauderdale 1972'),
  nhanDiaDanh: z.string().describe('Nhãn địa danh kèm mốc năm duy nhất'),
  coNhan: z.number().describe('Cỡ chữ nhãn địa danh (px)'),
  mauNhan: z.string().describe('Màu chữ nhãn địa danh'),
  mauApLuc: z.string().describe('Màu khung áp lực đồ họa'),
  doToiNen1: z.number().describe('Độ tối nền nguồn nước (0-0.5)'),
  doToiNen2: z.number().describe('Độ tối nền tư liệu (0-0.5)'),
  doDayThanh: z.number().describe('Độ dày thanh ngang khung áp lực'),
  doDayMuiTen: z.number().describe('Độ dày thân mũi tên áp lực'),
  doDayDuongNoi: z.number().describe('Độ dày đường nối nhãn địa danh'),
});

export const Canh = ({
  anhNuoc = 'nhan_y/5c8be7eb892413.jpg',
  anhFort = 'nhan_y/93274bc0f0c0ec.jpg',
  nhanDiaDanh = 'Fort Lauderdale, Florida - 1972',
  coNhan = 90,
  mauNhan = '#FFFFFF',
  mauApLuc = VANG,
  doToiNen1 = 0.32,
  doToiNen2 = 0.22,
  doDayThanh = 10,
  doDayMuiTen = 12,
  doDayDuongNoi = 4,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- NỀN NGUỒN NƯỚC : 0 -> 252 (mờ dần trong crossfade) ---------- */
  const opNen1 = interpolate(frame, [214, 250], [1, 0], CL);

  /* ---------- NỀN TƯ LIỆU : 214 -> 395 ---------- */
  const opNen2 = interpolate(frame, [214, 252], [0, 1], CL);

  /* ---------- BEAT 2 @86 : vệt sáng quét trên bề mặt lốp ---------- */
  const quetX = interpolate(frame, [86, 208], [-780, 2520], {...CL, easing: Easing.inOut(Easing.ease)});
  const quetOp = interpolate(frame, [86, 110, 184, 208], [0, 0.42, 0.42, 0], CL);

  /* ---------- BEAT 1 @2 : khung áp lực; BEAT 2 @86 : đậm lên ---------- */
  const apVao = interpolate(frame, [2, 26], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const apRa = interpolate(frame, [208, 244], [1, 0], CL);
  const luc = interpolate(frame, [86, 120], [0, 1], {...CL, easing: Easing.inOut(Easing.ease)});
  const troi = interpolate(frame, [2, 246], [0, 30], CL);
  const opApLuc = apVao * apRa;
  const phong = 1 + 0.05 * luc;

  /* ---------- BEAT 4 @307 : nhãn địa danh + mốc năm ---------- */
  const nhanVao = interpolate(frame, [307, 332], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const veDuong = interpolate(frame, [307, 342], [0, 1], {...CL, easing: Easing.inOut(Easing.ease)});
  const truotNhan = interpolate(frame, [313, 346], [0, 1], {...CL, easing: Easing.out(Easing.cubic)});
  const tPulse = Math.max(0, frame - 307);
  const chuKy = (tPulse % 54) / 54;
  const banKinh = 18 + 34 * chuKy;
  const opVong = 0.55 * (1 - chuKy);

  return (
    <AbsoluteFill style={{backgroundColor: '#05080b'}}>

      {/* ================= LỚP 1 : NGUỒN NƯỚC + LỐP XE ================= */}
      <Interactive.Div
        name="Nền nguồn nước lốp xe chìm"
        from={0}
        durationInFrames={252}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: opNen1}}
      >
        <AnhNen anh={anhNuoc} tu={1.05} den={1.19} goc="50% 58%" toi={doToiNen1} />
      </Interactive.Div>

      {/* ================= LỚP 1b : VỆT SÁNG QUÉT @86 ================= */}
      <Interactive.Div
        name="Vệt sáng quét bề mặt lốp"
        from={86}
        durationInFrames={124}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          opacity: quetOp,
          mixBlendMode: 'screen',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: quetX,
            top: -420,
            width: 640,
            height: 1920,
            transform: 'rotate(16deg)',
            background:
              'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(214,238,255,0.55) 50%, rgba(255,255,255,0) 100%)',
            filter: 'blur(16px)',
          }}
        />
      </Interactive.Div>

      {/* ================= LỚP 2 : KHUNG ÁP LỰC ĐỒ HỌA @2 ================= */}
      <Interactive.Div
        name="Khung áp lực đồ họa đè từ trên xuống"
        from={2}
        durationInFrames={244}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: opApLuc}}
      >
        <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: 'absolute', left: 0, top: 0}}>
          <g
            transform={`translate(960 300) scale(${phong}) translate(-960 -300) translate(0 ${troi})`}
          >
            {/* thanh ngang của khung áp lực */}
            <line
              x1={380}
              y1={150}
              x2={1540}
              y2={150}
              stroke={mauApLuc}
              strokeWidth={doDayThanh + 5 * luc}
              strokeLinecap="round"
              opacity={0.9}
            />
            {/* hai đầu mút */}
            <line x1={380} y1={150} x2={380} y2={216} stroke={mauApLuc} strokeWidth={8} strokeLinecap="round" opacity={0.65} />
            <line x1={1540} y1={150} x2={1540} y2={216} stroke={mauApLuc} strokeWidth={8} strokeLinecap="round" opacity={0.65} />
            {/* thân mũi tên */}
            <line
              x1={960}
              y1={150}
              x2={960}
              y2={352}
              stroke={mauApLuc}
              strokeWidth={doDayMuiTen + 5 * luc}
              strokeLinecap="round"
              opacity={0.95}
            />
            {/* đầu mũi tên đè xuống */}
            <path
              d="M 850 348 L 1070 348 L 960 488 Z"
              fill={mauApLuc}
              fillOpacity={0.12 + 0.24 * luc}
              stroke={mauApLuc}
              strokeWidth={7 + 5 * luc}
              strokeLinejoin="round"
            />
          </g>
        </svg>
      </Interactive.Div>

      {/* ================= LỚP 3 : TƯ LIỆU FORT LAUDERDALE @214 ================= */}
      <Interactive.Div
        name="Tư liệu vùng biển Fort Lauderdale"
        from={214}
        durationInFrames={181}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: opNen2}}
      >
        <AnhNen anh={anhFort} tu={1.22} den={1.0} goc="50% 46%" toi={doToiNen2} />
      </Interactive.Div>

      {/* ================= LỚP 4 : ĐIỂM ĐÁNH DẤU @307 ================= */}
      <Interactive.Div
        name="Điểm đánh dấu vị trí trên bản đồ"
        from={307}
        durationInFrames={88}
        style={{position: 'absolute', left: 1240, top: 600, opacity: nhanVao}}
      >
        <svg
          width={1920}
          height={1080}
          viewBox="0 0 1920 1080"
          style={{position: 'absolute', left: -1240, top: -600, overflow: 'visible'}}
        >
          {/* đường nối tới nhãn */}
          <path
            d="M 1240 624 L 1240 700 L 1800 700 L 1800 714"
            fill="none"
            stroke={mauApLuc}
            strokeWidth={doDayDuongNoi}
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - veDuong}
            opacity={0.92}
          />
          {/* vòng lan toả */}
          <circle cx={1240} cy={600} r={banKinh} fill="none" stroke={mauApLuc} strokeWidth={3} opacity={opVong} />
          {/* chấm vị trí */}
          <circle cx={1240} cy={600} r={20} fill="none" stroke={mauApLuc} strokeWidth={4} opacity={0.9} />
          <circle cx={1240} cy={600} r={10} fill={mauApLuc} />
        </svg>
      </Interactive.Div>

      {/* ================= LỚP 5 : NHÃN ĐỊA DANH + NĂM @307 ================= */}
      <Interactive.Div
        name="Nhãn địa danh và mốc năm 1972"
        from={307}
        durationInFrames={88}
        style={{position: 'absolute', left: 400, top: 718, width: 1400}}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: coNhan,
            fontWeight: 700,
            color: mauNhan,
            textAlign: 'right',
            letterSpacing: 1,
            whiteSpace: 'nowrap',
            lineHeight: 1.1,
            opacity: truotNhan,
            transform: `translateX(${(1 - truotNhan) * 46}px)`,
            textShadow: '0 6px 28px rgba(0,0,0,0.8)',
          }}
        >
          {nhanDiaDanh}
        </div>
        <div
          style={{
            marginTop: 16,
            marginLeft: 'auto',
            width: 880 * truotNhan,
            height: 6,
            borderRadius: 3,
            background: mauApLuc,
            opacity: truotNhan,
          }}
        />
      </Interactive.Div>

    </AbsoluteFill>
  );
};
