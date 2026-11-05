import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhLop: z.string().describe('Ảnh cận cảnh đống lốp cũ giữ đất bùn trên lòng suối cạn'),
  anhBan: z.string().describe('Ảnh tư liệu bàn làm việc với hồ sơ ngân sách và bản vẽ đập dang dở'),
  mauNetCat: z.string().describe('Màu nét phác thảo mặt cắt cơ chế đọng nước'),
  doDamNet: z.number().describe('Độ dày nét phác thảo (px)'),
  mauTem: z.string().describe('Màu mực đỏ của tem dấu lưu trữ'),
  chuTem: z.string().describe('Chữ trên tem dấu lưu trữ'),
  coChuTem: z.number().describe('Cỡ chữ tem dấu (px)'),
  gocTem: z.number().describe('Độ nghiêng của tem dấu (độ)'),
  doMoAnh: z.number().describe('Độ tối phủ lên ảnh nền (0..0.5)'),
});

const LopXe = ({anh, toi}) => {
  const f = useCurrentFrame();
  // cú đẩy máy nhẹ bắt đầu quanh nhịp "Vậy mà" (frame 4 toàn cục)
  const punch = interpolate(f, [2, 18], [1, 1.055], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <AbsoluteFill style={{transform: `scale(${punch})`}}>
      <AnhNen anh={anh} tu={1.0} den={1.07} goc="50% 58%" toi={toi} />
    </AbsoluteFill>
  );
};

const NetCat = ({mau, dam}) => {
  const f = useCurrentFrame();
  const p1 = interpolate(f, [0, 12], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const p2 = interpolate(f, [8, 21], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const p3 = interpolate(f, [17, 31], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const ve = (p) => ({pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - p});
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: 'absolute', left: 0, top: 0}}>
        <g stroke={mau} fill="none" strokeWidth={dam} strokeLinecap="round" strokeLinejoin="round">
          {/* đường mặt cắt ngang cấu trúc lốp */}
          <path d="M 320 558 L 1620 558" opacity={0.9} {...ve(p1)} />
          <path d="M 320 558 L 320 618" opacity={0.9} {...ve(p1)} />
          <path d="M 1620 558 L 1620 618" opacity={0.9} {...ve(p1)} />

          {/* mũi tên nước ngấm xuống */}
          <path d="M 700 566 L 700 726" opacity={0.95} {...ve(p2)} />
          <path d="M 674 696 L 700 728 L 726 696" opacity={0.95} {...ve(p2)} />
          <path d="M 1240 566 L 1240 726" opacity={0.95} {...ve(p2)} />
          <path d="M 1214 696 L 1240 728 L 1266 696" opacity={0.95} {...ve(p2)} />

          {/* vòng khoanh chỗ đất giữ ẩm / mầm cỏ */}
          <ellipse cx={890} cy={858} rx={178} ry={112} opacity={0.95} {...ve(p3)} />
          <path d="M 1050 800 L 1150 748" opacity={0.95} {...ve(p3)} />
        </g>
      </svg>
    </AbsoluteFill>
  );
};

const BanLamViec = ({anh, toi}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 18], [1920, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <AbsoluteFill style={{transform: `translateX(${x}px)`}}>
      <AnhNen anh={anh} tu={1.12} den={1.0} goc="50% 45%" toi={toi} />
    </AbsoluteFill>
  );
};

const TemDau = ({chu, mau, co, goc}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 13, mass: 0.55, stiffness: 130}});
  const scale = interpolate(s, [0, 1], [1.85, 1]);
  const op = interpolate(f, [0, 4], [0, 1], kep);
  const troi = interpolate(f, [10, 96], [1, 1.04], kep);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div
        style={{
          transform: `rotate(${goc}deg) scale(${scale * troi})`,
          opacity: op,
          border: `14px solid ${mau}`,
          outline: `4px solid ${mau}`,
          outlineOffset: 14,
          borderRadius: 10,
          padding: '20px 46px',
          color: mau,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: co,
          letterSpacing: 10,
          whiteSpace: 'nowrap',
          background: 'rgba(250,246,238,0.08)',
        }}
      >
        {chu}
      </div>
    </AbsoluteFill>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#12100e'}}>
      <Interactive.Div
        name="Cận cảnh đống lốp cũ trong thung lũng khô"
        from={0}
        durationInFrames={112}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <LopXe anh={props.anhLop} toi={props.doMoAnh} />
      </Interactive.Div>

      <Interactive.Div
        name="Nét phác thảo mặt cắt cơ chế đọng nước"
        from={71}
        durationInFrames={41}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NetCat mau={props.mauNetCat} dam={props.doDamNet} />
      </Interactive.Div>

      <Interactive.Div
        name="Bàn làm việc hồ sơ ngân sách và bản vẽ đập"
        from={88}
        durationInFrames={185}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <BanLamViec anh={props.anhBan} toi={props.doMoAnh} />
      </Interactive.Div>

      <Interactive.Div
        name="Tem dấu lưu trữ UNRESOLVED"
        from={177}
        durationInFrames={96}
        style={{position: 'absolute', left: 460, top: 400, width: 1000, height: 280}}
      >
        <TemDau chu={props.chuTem} mau={props.mauTem} co={props.coChuTem} goc={props.gocTem} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
