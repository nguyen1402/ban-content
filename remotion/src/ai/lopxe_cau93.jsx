import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền bãi lốp xe khổng lồ'),
  anh_cong_nhan: z.string().describe('Ảnh cắt công nhân ở tiền cảnh'),
  so_luong: z.number().describe('Con số lốp hiển thị (1.500)'),
  co_so: z.number().describe('Cỡ chữ của số đếm (px)'),
  mau_so: z.string().describe('Màu của số đếm'),
  vi_tri_so_x: z.number().describe('Vị trí ngang của số đếm (px)'),
  vi_tri_so_y: z.number().describe('Vị trí dọc của số đếm (px)'),
  do_toi_nen: z.number().describe('Độ tối phủ lên ảnh nền (0..0.5)'),
  do_toi_cuoi: z.number().describe('Độ tối ám màu ở nhịp cuối (0..1)'),
  le_vao: z.number().describe('Quãng trượt vào của lớp công nhân (px)'),
  phong_nen: z.number().describe('Tỉ lệ zoom chậm của ảnh nền'),
  do_phong_cong_nhan: z.number().describe('Độ phóng cuối của lớp công nhân'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Camera toàn cảnh: trượt nhẹ rồi đẩy dần vào theo từng nhịp
  const camera = interpolate(
    frame,
    [0, 120, 160, 231, 376],
    [1, 1.03, 1.07, 1.11, 1.15],
    {...kep, easing: Easing.inOut(Easing.quad)}
  );

  // Lớp cắt công nhân tiền cảnh
  const vao = spring({frame: frame - 4, fps, config: {damping: 24, mass: 1, stiffness: 80}});
  const truotX = interpolate(vao, [0, 1], [-props.le_vao, 0]);
  const truotY = interpolate(frame, [0, 376], [8, -12], {...kep, easing: Easing.linear});
  const hien = interpolate(frame, [4, 26], [0, 1], kep);
  const phong = interpolate(
    frame,
    [0, 120, 160, 215, 231, 376],
    [1, 1, 1.1, 1.24, 1.26, props.do_phong_cong_nhan],
    {...kep, easing: Easing.inOut(Easing.quad)}
  );

  // Số đếm 1.500 hiện lên ở góc trái rồi đứng yên
  const soVal = Math.round(
    interpolate(frame, [60, 78], [0, props.so_luong], {...kep, easing: Easing.out(Easing.cubic)})
  );
  const soOp = interpolate(frame, [60, 72], [0, 1], kep);
  const soY = interpolate(frame, [60, 78], [34, 0], {...kep, easing: Easing.out(Easing.cubic)});

  // Nhịp cuối: chậm lại, ám màu trầm
  const toi = interpolate(frame, [231, 268], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0806'}}>
      <Interactive.Div
        name="Ảnh nền bãi lốp"
        from={0}
        durationInFrames={376}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `scale(${camera})`,
          transformOrigin: '50% 50%',
        }}
      >
        <AnhNen
          anh={props.anh_nen}
          tu={1}
          den={props.phong_nen}
          goc="50% 45%"
          toi={props.do_toi_nen}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Công nhân tiền cảnh"
        from={4}
        durationInFrames={372}
        style={{position: 'absolute', left: 690, top: 420, width: 1000, height: 720}}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            opacity: hien,
            transform: `translate(${truotX}px, ${truotY}px) scale(${phong})`,
            transformOrigin: '50% 32%',
          }}
        >
          <Img
            src={src(props.anh_cong_nhan)}
            name="Công nhân"
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      <Interactive.Div
        name="Số đếm 1.500"
        from={60}
        durationInFrames={316}
        style={{position: 'absolute', left: props.vi_tri_so_x, top: props.vi_tri_so_y}}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: props.co_so,
            fontWeight: 900,
            color: props.mau_so,
            lineHeight: 1,
            letterSpacing: '-3px',
            whiteSpace: 'nowrap',
            opacity: soOp,
            transform: `translateY(${soY}px)`,
            textShadow: '0 8px 28px rgba(0,0,0,0.65)',
          }}
        >
          {soVal.toLocaleString('vi-VN')}
        </div>
      </Interactive.Div>

      <Interactive.Div
        name="Ám màu nặng nhọc cuối cảnh"
        from={231}
        durationInFrames={145}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill
          style={{
            background:
              'linear-gradient(180deg, rgba(18,12,6,0.50) 0%, rgba(10,7,4,0.32) 100%)',
            opacity: toi * props.do_toi_cuoi,
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
