import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền bãi đất trống quận Pima'),
  anhLop: z.string().describe('Ảnh cắt rời chồng lốp xe cũ'),
  chuDiaDanh: z.string().describe('Tên địa danh hiện trên màn hình'),
  soLop: z.number().describe('Số lốp xe đếm tới'),
  donViLop: z.string().describe('Đơn vị của bộ đếm'),
  giayDem: z.number().describe('Thời gian chạy bộ đếm (giây)'),
  coChuDiaDanh: z.number().describe('Cỡ chữ tên địa danh'),
  coSoDem: z.number().describe('Cỡ chữ bộ đếm'),
  rongLop: z.number().describe('Chiều rộng ảnh lốp xe (px)'),
  doToiNen: z.number().describe('Độ tối lớp phủ trên ảnh nền (0-0.5)'),
  zoomDau: z.number().describe('Tỉ lệ zoom đầu của ảnh nền'),
  zoomCuoi: z.number().describe('Tỉ lệ zoom cuối của ảnh nền'),
});

/* ---------- Lớp lốp xe cũ trượt vào và trôi chậm tới hết cảnh ---------- */
const LopXe = ({anh, rong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200, mass: 0.9}});
  const x = interpolate(vao, [0, 1], [520, 0], kep);
  const rot = interpolate(vao, [0, 1], [13, -2], kep);
  const troi = interpolate(f, [0, 121], [10, -26], kep);
  const phong = interpolate(f, [0, 121], [1.0, 1.07], kep);
  const hien = interpolate(f, [0, 7], [0, 1], kep);

  return (
    <div
      style={{
        transform: `translate(${x}px, ${troi}px) rotate(${rot}deg) scale(${phong})`,
        transformOrigin: '50% 60%',
        opacity: hien,
      }}
    >
      <Img
        src={src(anh)}
        name="Ảnh lốp xe cũ"
        style={{width: rong, height: (rong * 487) / 700, objectFit: 'contain', display: 'block'}}
      />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0d0d0d', fontFamily: FONT}}>
      {/* Nền bãi đất trống quận Pima: pull-back chậm suốt cảnh */}
      <AnhNen
        anh={props.anhNen}
        tu={props.zoomDau}
        den={props.zoomCuoi}
        goc="50% 45%"
        toi={props.doToiNen}
      />

      {/* Nhịp 1 — frame 4: tên địa danh hiện ra */}
      <Interactive.Div
        name="Tên địa danh"
        from={4}
        durationInFrames={162}
        style={{position: 'absolute', left: 110, top: 120}}
      >
        <ChuNoi chu={props.chuDiaDanh} co={props.coChuDiaDanh} />
      </Interactive.Div>

      {/* Nhịp 2 — frame 45: chồng lốp xe cũ đè lên nền */}
      <Interactive.Div
        name="Chồng lốp xe cũ"
        from={45}
        durationInFrames={121}
        style={{position: 'absolute', left: 980, top: 215}}
      >
        <LopXe anh={props.anhLop} rong={props.rongLop} />
      </Interactive.Div>

      {/* Nhịp 2 — frame 45: bộ đếm 0 → 1.500 */}
      <Interactive.Div
        name="Bộ đếm số lốp"
        from={45}
        durationInFrames={121}
        style={{position: 'absolute', left: 110, top: 700}}
      >
        <SoDem so={props.soLop} don_vi={props.donViLop} giay={props.giayDem} co={props.coSoDem} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
