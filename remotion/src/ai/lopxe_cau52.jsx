import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhXuong: z.string().describe('Ảnh nền xưởng cơ khí thập niên cũ'),
  anhGoodyear: z.string().describe('Ảnh nền kho lốp Goodyear'),
  anhPhelps: z.string().describe('Ảnh nền mỏ khai khoáng Phelps Dodge'),
  anhLop: z.string().describe('Cutout lốp xe tải'),
  anhGoong: z.string().describe('Cutout xe goòng mỏ'),
  soTien: z.number().describe('Số tiền đích của bộ đếm'),
  donVi: z.string().describe('Đơn vị tiền hiển thị cạnh bộ đếm'),
  giayDem: z.number().describe('Số giây bộ đếm chạy lên'),
  chuThe1: z.string().describe('Thẻ chữ số tiền'),
  chuGoodyear: z.string().describe('Nhãn chữ Goodyear'),
  chuPhelps: z.string().describe('Nhãn chữ Phelps Dodge'),
  coSo: z.number().describe('Cỡ chữ bộ đếm số tiền'),
  coThe: z.number().describe('Cỡ chữ thẻ số tiền'),
  coNhan: z.number().describe('Cỡ chữ nhãn gọi chú thích'),
  mauNen: z.string().describe('Màu nền thẻ chữ'),
  mauChu: z.string().describe('Màu chữ trong thẻ'),
  mauNhan: z.string().describe('Màu viền / màu nhấn'),
  quangXuong: z.number().describe('Quãng trượt ngang của nền xưởng (px)'),
  toiXuong: z.number().describe('Độ tối nền xưởng (0-0.5)'),
  toiGoodyear: z.number().describe('Độ tối nền Goodyear (0-0.5)'),
  toiPhelps: z.number().describe('Độ tối nền Phelps (0-0.5)'),
});

const AnhCat = ({anh, w, h, tuX, soKhung}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 14, mass: 0.9, stiffness: 90}});
  const op = interpolate(f, [0, 8], [0, 1], kep);
  const tx = interpolate(s, [0, 1], [tuX, 0]);
  const zoom = interpolate(f, [0, Math.max(soKhung, 1)], [1.07, 1], kep);
  return (
    <div style={{transform: `translateX(${tx}px) scale(${zoom})`, opacity: op, transformOrigin: 'center center'}}>
      <Img
        src={src(anh)}
        style={{
          width: w,
          height: h,
          objectFit: 'contain',
          display: 'block',
          filter: 'drop-shadow(0 24px 38px rgba(0,0,0,0.55))',
        }}
      />
    </div>
  );
};

const TheNoi = ({chu, co, mauNen, mauChu, mauVien}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 15, mass: 0.8, stiffness: 120}});
  return (
    <div
      style={{
        transform: `translateY(${interpolate(s, [0, 1], [46, 0])}px) scale(${interpolate(s, [0, 1], [0.82, 1])})`,
        opacity: interpolate(f, [0, 7], [0, 1], kep),
        background: mauNen,
        border: `6px solid ${mauVien}`,
        borderRadius: 16,
        padding: '16px 44px',
        fontFamily: FONT,
        fontSize: co,
        fontWeight: 800,
        color: mauChu,
        letterSpacing: 3,
        whiteSpace: 'nowrap',
        boxShadow: '0 18px 50px rgba(0,0,0,0.5)',
      }}
    >
      {chu}
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#101010'}}>
      {/* ---------- NHỊP 1 : xưởng cơ khí + bộ đếm tiền (0 - 82) ---------- */}
      <Interactive.Div
        name="Nền xưởng cơ khí trượt ngang"
        from={0}
        durationInFrames={82}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={props.anhXuong} huong="phai" quang={props.quangXuong} toi={props.toiXuong} />
      </Interactive.Div>

      <Interactive.Div
        name="Bộ đếm số tiền"
        from={2}
        durationInFrames={80}
        style={{position: 'absolute', left: 150, top: 330}}
      >
        <SoDem so={props.soTien} don_vi={props.donVi} giay={props.giayDem} co={props.coSo} />
      </Interactive.Div>

      <Interactive.Div
        name="Thẻ chữ số tiền"
        from={2}
        durationInFrames={80}
        style={{position: 'absolute', left: 150, top: 660}}
      >
        <TheNoi
          chu={props.chuThe1}
          co={props.coThe}
          mauNen={props.mauNen}
          mauChu={props.mauChu}
          mauVien={props.mauNhan}
        />
      </Interactive.Div>

      {/* ---------- NHỊP 2 : kho lốp Goodyear (82 - 148) ---------- */}
      <Interactive.Div
        name="Nền kho lốp Goodyear"
        from={82}
        durationInFrames={66}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhGoodyear} tu={1.02} den={1.14} goc="60% 50%" toi={props.toiGoodyear} />
      </Interactive.Div>

      <Interactive.Div
        name="Lốp xe tải"
        from={82}
        durationInFrames={66}
        style={{position: 'absolute', left: 1140, top: 330}}
      >
        <AnhCat anh={props.anhLop} w={700} h={419} tuX={240} soKhung={66} />
      </Interactive.Div>

      <Interactive.Div
        name="Nhãn Goodyear"
        from={82}
        durationInFrames={66}
        style={{position: 'absolute', left: 1180, top: 520}}
      >
        <Nhan chu={props.chuGoodyear} dx={-600} dy={-150} co={props.coNhan} />
      </Interactive.Div>

      {/* ---------- NHỊP 3 : mỏ Phelps Dodge (148 - 230) ---------- */}
      <Interactive.Div
        name="Nền mỏ khai khoáng Phelps Dodge"
        from={148}
        durationInFrames={82}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhPhelps} tu={1.14} den={1.02} goc="40% 55%" toi={props.toiPhelps} />
      </Interactive.Div>

      <Interactive.Div
        name="Xe goòng mỏ"
        from={148}
        durationInFrames={82}
        style={{position: 'absolute', left: 130, top: 330}}
      >
        <AnhCat anh={props.anhGoong} w={720} h={552} tuX={-260} soKhung={82} />
      </Interactive.Div>

      <Interactive.Div
        name="Nhãn Phelps Dodge"
        from={148}
        durationInFrames={82}
        style={{position: 'absolute', left: 520, top: 600}}
      >
        <Nhan chu={props.chuPhelps} dx={620} dy={-200} co={props.coNhan} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
