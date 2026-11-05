import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anh1: z.string().describe('Ảnh cận cảnh lớp đất mùn xốp ẩm (beat 1)'),
  anh2: z.string().describe('Ảnh mặt đất khô nứt nẻ dưới mưa lớn (beat 2)'),
  anh3: z.string().describe('Ảnh dòng nước đục chảy xiết xói mòn (beat 3)'),
  toi1: z.number().describe('Độ tối ảnh beat 1 (0..0.5)'),
  toi2: z.number().describe('Độ tối ảnh beat 2 (0..0.5)'),
  toi3: z.number().describe('Độ tối ảnh beat 3 (0..0.5)'),
  soLo: z.number().describe('Số khoang giữ nước vẽ chồng lên ảnh đất xốp'),
  mauLo: z.string().describe('Màu đồ họa khoang giữ nước'),
  doMoLo: z.number().describe('Độ mờ tổng của lớp khoang giữ nước'),
  soHatMua: z.number().describe('Số hạt mưa parallax'),
  mauMua: z.string().describe('Màu hạt mưa'),
  gocMua: z.number().describe('Góc nghiêng của mưa (radian)'),
  doDaiTruot: z.number().describe('Số frame trượt ngang khi chuyển cảnh (frame)'),
});

/* ---------- Trượt ngang vào khung hình (dùng frame cục bộ trong Interactive.Div) ---------- */
const TruotVao = ({doDai, children}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, doDai], [1920, 0], {
    ...CL,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: `translateX(${x}px)`}}>
      {children}
    </div>
  );
};

/* ---------- Lớp đồ họa khoang giữ nước (bọt biển) ---------- */
const LopLoHong = ({soLo, mau, doMo}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items = [];
  for (let i = 0; i < soLo; i++) {
    const s = 'lo-' + i;
    const cx = 130 + random(s + 'x') * 1660;
    const cy = 110 + random(s + 'y') * 860;
    const r = 38 + random(s + 'r') * 76;
    const bat = 4 + i * 2.2;
    const sc = spring({frame: f - bat, fps, config: {damping: 15, mass: 0.7, stiffness: 90}});
    const mo = interpolate(f, [54, 72], [1, 0], CL);
    const op = sc * mo * doMo;
    if (op <= 0.002) continue;
    items.push(
      <g key={i} opacity={op} transform={`translate(${cx} ${cy}) scale(${sc})`}>
        <circle r={r} fill={mau} fillOpacity={0.1} />
        <circle r={r} fill="none" stroke={mau} strokeWidth={3} strokeDasharray="9 13" strokeOpacity={0.9} />
      </g>
    );
  }
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      {items}
    </svg>
  );
};

/* ---------- Mưa parallax nhiều lớp chiều sâu ---------- */
const MuaParallax = ({soLuong, mau, goc}) => {
  const f = useCurrentFrame();
  const items = [];
  for (let i = 0; i < soLuong; i++) {
    const s = 'mua-' + i;
    const lop = random(s + 'l'); // 0 = xa, 1 = gần
    const x0 = random(s + 'x') * 2240 - 160;
    const speed = 16 + lop * 46;
    const dai = 90 + lop * 210;
    const day = 1.5 + lop * 3;
    const alpha = 0.16 + lop * 0.46;
    const y = ((random(s + 'y') * 1600 + f * speed) % 1600) - 320;
    const dx = dai * Math.sin(goc);
    const dy = dai * Math.cos(goc);
    items.push(
      <line
        key={i}
        x1={x0}
        y1={y}
        x2={x0 - dx}
        y2={y + dy}
        stroke={mau}
        strokeWidth={day}
        strokeOpacity={alpha}
        strokeLinecap="round"
      />
    );
  }
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      {items}
    </svg>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#1a1206', overflow: 'hidden'}}>
      {/* ============ BEAT 1 : đất xốp giữ nước (frame 2) ============ */}
      <Interactive.Div
        name="Ảnh đất mùn xốp ẩm"
        from={0}
        durationInFrames={115}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anh1} tu={1.02} den={1.16} goc="50% 45%" toi={props.toi1} />
      </Interactive.Div>

      <Interactive.Div
        name="Đồ họa khoang giữ nước"
        from={2}
        durationInFrames={100}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopLoHong soLo={props.soLo} mau={props.mauLo} doMo={props.doMoLo} />
      </Interactive.Div>

      {/* ============ BEAT 2 : mặt đất nứt nẻ dưới mưa (frame 99) ============ */}
      <Interactive.Div
        name="Ảnh đất nứt nẻ dưới mưa"
        from={99}
        durationInFrames={92}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <TruotVao doDai={props.doDaiTruot}>
          <AnhNen anh={props.anh2} tu={1.16} den={1.02} goc="50% 30%" toi={props.toi2} />
        </TruotVao>
      </Interactive.Div>

      <Interactive.Div
        name="Mưa parallax"
        from={99}
        durationInFrames={92}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <MuaParallax soLuong={props.soHatMua} mau={props.mauMua} goc={props.gocMua} />
      </Interactive.Div>

      {/* ============ BEAT 3 : dòng nước xiết xói mòn (frame 169) ============ */}
      <Interactive.Div
        name="Ảnh dòng nước chảy xiết"
        from={169}
        durationInFrames={145}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <TruotVao doDai={props.doDaiTruot}>
          <AnhNen anh={props.anh3} tu={1.05} den={1.18} goc="50% 55%" toi={props.toi3} />
        </TruotVao>
      </Interactive.Div>

      {/* Mũi tên chỉ hướng dòng chảy */}
      <Interactive.Div
        name="Mũi tên dòng chảy 1"
        from={172}
        durationInFrames={142}
        style={{position: 'absolute', left: 300, top: 420}}
      >
        <MuiTen dx={380} dy={130} cong={-0.3} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên dòng chảy 2"
        from={181}
        durationInFrames={133}
        style={{position: 'absolute', left: 760, top: 330}}
      >
        <MuiTen dx={420} dy={160} cong={-0.28} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên dòng chảy 3"
        from={188}
        durationInFrames={126}
        style={{position: 'absolute', left: 1180, top: 470}}
      >
        <MuiTen dx={380} dy={120} cong={-0.3} />
      </Interactive.Div>

      {/* Mũi tên chỉ lực xói mòn khoét sâu */}
      <Interactive.Div
        name="Mũi tên xói mòn 1"
        from={220}
        durationInFrames={94}
        style={{position: 'absolute', left: 620, top: 520}}
      >
        <MuiTen dx={150} dy={330} cong={0.18} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên xói mòn 2"
        from={233}
        durationInFrames={81}
        style={{position: 'absolute', left: 1080, top: 500}}
      >
        <MuiTen dx={170} dy={320} cong={-0.18} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên xói mòn 3"
        from={248}
        durationInFrames={66}
        style={{position: 'absolute', left: 380, top: 560}}
      >
        <MuiTen dx={160} dy={300} cong={0.15} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
