import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhSuoi: z.string().describe('Ảnh hậu cảnh bờ suối xanh'),
  anhCoDai: z.string().describe('Ảnh cắt lớp cỏ dại tiền cảnh'),
  anhDongCo: z.string().describe('Ảnh hậu cảnh đồng cỏ trang trại'),
  anhDanBo: z.string().describe('Ảnh cắt lớp đàn bò tiền cảnh'),
  frameChuyen: z.number().describe('Frame bắt đầu chuyển sang đồng cỏ trang trại'),
  daiNenSuoi: z.number().describe('Số frame hậu cảnh bờ suối còn hiển thị'),
  daiCoDai: z.number().describe('Số frame lớp cỏ dại còn hiển thị'),
  zoomSuoiDau: z.number().describe('Tỉ lệ zoom đầu của hậu cảnh bờ suối'),
  zoomSuoiCuoi: z.number().describe('Tỉ lệ zoom cuối của hậu cảnh bờ suối'),
  zoomDongCoDau: z.number().describe('Tỉ lệ zoom đầu của hậu cảnh đồng cỏ'),
  zoomDongCoCuoi: z.number().describe('Tỉ lệ zoom cuối của hậu cảnh đồng cỏ'),
  coNang: z.number().describe('Độ cao cỏ dại vươn lên (px)'),
  boNang: z.number().describe('Độ cao đàn bò trồi lên (px)'),
  toiNen: z.number().describe('Độ tối lớp phủ hậu cảnh'),
  nhipCo: z.number().describe('Số frame cỏ dại vươn lên'),
  nhipBo: z.number().describe('Số frame đàn bò trồi lên'),
  daiChuyen: z.number().describe('Số frame chuyển cảnh mượt'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fChuyen = props.frameChuyen;

  // Chuyển cảnh mượt: hậu cảnh đồng cỏ hiện dần đè lên hậu cảnh bờ suối
  const opDongCo = interpolate(frame, [fChuyen - 2, fChuyen - 2 + props.daiChuyen], [0, 1], kep);

  // Cỏ dại vươn lên từ frame 2 + trôi chậm suốt beat
  const moc = spring({
    frame: frame - 2,
    fps,
    config: {damping: 200, mass: 1},
    durationInFrames: props.nhipCo,
  });
  const coY =
    interpolate(moc, [0, 1], [props.coNang, 0], kep) +
    interpolate(frame, [2, 100], [26, -28], kep);
  const coScale = interpolate(moc, [0, 1], [1.09, 1], kep);
  const opCo = interpolate(frame, [fChuyen + 2, fChuyen + 16], [1, 0], kep);

  // Đàn bò gặm cỏ trồi lên từ frame chuyển cảnh + trôi chậm tới cuối
  const boLen = spring({
    frame: frame - fChuyen,
    fps,
    config: {damping: 200, mass: 1},
    durationInFrames: props.nhipBo,
  });
  const boY =
    interpolate(boLen, [0, 1], [props.boNang, 0], kep) +
    interpolate(frame, [fChuyen, 282], [24, -28], kep);
  const boScale = interpolate(boLen, [0, 1], [1.12, 1.02], kep);
  const opBo = interpolate(frame, [fChuyen, fChuyen + 12], [0, 1], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#101a12'}}>
      {/* 1. Hậu cảnh bờ suối — nền chính từ đầu tới sau khi chuyển cảnh */}
      <Interactive.Div
        name="Hậu cảnh bờ suối"
        from={0}
        durationInFrames={props.daiNenSuoi}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anhSuoi}
          tu={props.zoomSuoiDau}
          den={props.zoomSuoiCuoi}
          goc="50% 48%"
          toi={props.toiNen}
        />
      </Interactive.Div>

      {/* 2. Hậu cảnh đồng cỏ trang trại — hiện dần, giữ tới frame cuối */}
      <Interactive.Div
        name="Hậu cảnh đồng cỏ trang trại"
        from={82}
        durationInFrames={200}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          opacity: opDongCo,
        }}
      >
        <AnhNen
          anh={props.anhDongCo}
          tu={props.zoomDongCoDau}
          den={props.zoomDongCoCuoi}
          goc="50% 55%"
          toi={props.toiNen}
        />
      </Interactive.Div>

      {/* 3. Lớp tiền cảnh cỏ dại vươn lên (parallax chậm) */}
      <Interactive.Div
        name="Lớp cỏ dại tiền cảnh"
        from={2}
        durationInFrames={props.daiCoDai}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <Img
          name="Cỏ dại vươn lên"
          src={src(props.anhCoDai)}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            objectFit: 'cover',
            opacity: opCo,
            transform: `translateY(${coY}px) scale(${coScale})`,
            transformOrigin: '50% 100%',
          }}
        />
      </Interactive.Div>

      {/* 4. Lớp tiền cảnh đàn bò gặm cỏ — tạo chiều sâu */}
      <Interactive.Div
        name="Lớp đàn bò gặm cỏ"
        from={84}
        durationInFrames={198}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <Img
          name="Đàn bò gặm cỏ"
          src={src(props.anhDanBo)}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            objectFit: 'cover',
            opacity: opBo,
            transform: `translateY(${boY}px) scale(${boScale})`,
            transformOrigin: '50% 100%',
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
