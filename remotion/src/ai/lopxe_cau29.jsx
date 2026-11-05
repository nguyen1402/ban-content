import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền bãi lốp xe thập niên 90'),
  nhan1990: z.string().describe('Nhãn mốc thời gian hiện ở góc trái'),
  soLuong: z.number().describe('Số lốp xe thải ra mỗi năm'),
  donVi: z.string().describe('Đơn vị của bộ đếm'),
  giayDem: z.number().describe('Thời gian bộ đếm chạy (giây)'),
  coSoDem: z.number().describe('Cỡ chữ bộ đếm'),
  chuTyLe: z.string().describe('Con số tỷ lệ tái chế hiện trong tâm biểu đồ'),
  coChuTyLe: z.number().describe('Cỡ chữ tỷ lệ'),
  mauDo: z.string().describe('Màu đỏ trầm của tỷ lệ và cung biểu đồ'),
  mauVong: z.string().describe('Màu vòng tròn nền của biểu đồ'),
  banKinh: z.number().describe('Bán kính vòng biểu đồ tròn (px)'),
  tyLe: z.number().describe('Tỷ lệ tái chế (0..1) để vẽ cung đỏ'),
  doDam: z.number().describe('Độ tối lớp phủ trên ảnh nền (0..0.5)'),
  quangPan: z.number().describe('Quãng pan của ảnh nền (px)'),
  phongNen: z.number().describe('Độ phóng của ảnh nền'),
});

const Nhan1990 = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const vao = spring({frame: f, fps: 30, config: {damping: 200, mass: 0.9}});
  const ra = interpolate(f, [62, 88], [1, 0], {...kep, easing: Easing.in(Easing.cubic)});
  const x = interpolate(vao, [0, 1], [-60, 0]);
  return (
    <div
      style={{
        opacity: vao * ra,
        transform: `translateX(${x}px)`,
        fontFamily: FONT,
        fontSize: co,
        fontWeight: 800,
        color: mau,
        letterSpacing: 6,
        lineHeight: 1,
        whiteSpace: 'nowrap',
        textShadow: '0 8px 36px rgba(0,0,0,0.65)',
      }}
    >
      {chu}
    </div>
  );
};

const BoDem = ({so, donVi, giay, co}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 10], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const ra = interpolate(f, [98, 122], [1, 0], {...kep, easing: Easing.in(Easing.cubic)});
  const y = interpolate(vao, [0, 1], [46, 0]);
  const sc = interpolate(vao, [0, 1], [0.94, 1]);
  return (
    <div style={{opacity: vao * ra, transform: `translateY(${y}px) scale(${sc})`}}>
      <SoDem so={so} don_vi={donVi} giay={giay} co={co} />
    </div>
  );
};

const BieuDo = ({tyLe, banKinh, mauVong, mauDo}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 14], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p = interpolate(f, [6, 40], [0, tyLe], {...kep, easing: Easing.out(Easing.cubic)});
  const sc = interpolate(f, [0, 26], [0.9, 1], {...kep, easing: Easing.out(Easing.cubic)});

  const R2 = banKinh + 40;
  const size = (R2 + 60) * 2;
  const c = size / 2;
  const C1 = 2 * Math.PI * banKinh;
  const C2 = 2 * Math.PI * R2;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{opacity: vao, transform: `scale(${sc})`, transformOrigin: '50% 50%'}}
    >
      <circle cx={c} cy={c} r={banKinh} fill="none" stroke={mauVong} strokeWidth={34} />
      <circle
        cx={c}
        cy={c}
        r={R2}
        fill="none"
        stroke={mauDo}
        strokeWidth={30}
        strokeDasharray={C2}
        strokeDashoffset={C2 * (1 - p)}
        transform={`rotate(-90 ${c} ${c})`}
      />
    </svg>
  );
};

const ChuTyLe = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 22], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const sc = interpolate(f, [0, 30], [0.96, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        opacity: op,
        transform: `scale(${sc})`,
        fontFamily: FONT,
        fontSize: co,
        fontWeight: 800,
        color: mau,
        letterSpacing: 2,
        lineHeight: 1,
        textShadow: '0 6px 30px rgba(0,0,0,0.55)',
        whiteSpace: 'nowrap',
      }}
    >
      {chu}
    </div>
  );
};

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const sizeBD = (props.banKinh + 40 + 60) * 2;
  const leftBD = 960 - sizeBD / 2;
  const topBD = 540 - sizeBD / 2;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0b0b', overflow: 'hidden'}}>
      <Interactive.Div
        name="Nền bãi lốp xe 90s"
        from={0}
        durationInFrames={302}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={props.anhNen} huong="phai" quang={props.quangPan} phong={props.phongNen} toi={props.doDam} />
      </Interactive.Div>

      <Interactive.Div
        name="Nhãn mốc 1990s"
        from={3}
        durationInFrames={92}
        style={{position: 'absolute', left: 120, top: 620}}
      >
        <Nhan1990 chu={props.nhan1990} co={150} mau="#FFFFFF" />
      </Interactive.Div>

      <Interactive.Div
        name="Bộ đếm số lốp thải ra"
        from={77}
        durationInFrames={125}
        style={{position: 'absolute', left: 0, top: 400, width: 1920, textAlign: 'center'}}
      >
        <BoDem so={props.soLuong} donVi={props.donVi} giay={props.giayDem} co={props.coSoDem} />
      </Interactive.Div>

      <Interactive.Div
        name="Biểu đồ tỷ lệ tái chế"
        from={190}
        durationInFrames={112}
        style={{position: 'absolute', left: leftBD, top: topBD}}
      >
        <BieuDo tyLe={props.tyLe} banKinh={props.banKinh} mauVong={props.mauVong} mauDo={props.mauDo} />
      </Interactive.Div>

      <Interactive.Div
        name="Con số tỷ lệ dưới 10%"
        from={238}
        durationInFrames={64}
        style={{
          position: 'absolute',
          left: leftBD,
          top: 450,
          width: sizeBD,
          height: 180,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <ChuTyLe chu={props.chuTyLe} co={props.coChuTyLe} mau={props.mauDo} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
