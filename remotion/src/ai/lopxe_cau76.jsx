import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNenRung: z.string().describe('Ảnh nền rừng rậm có lối mòn'),
  anhNenVuong: z.string().describe('Ảnh nền vũng nước đọng trong rừng'),
  anhHuou: z.string().describe('Ảnh cắt đàn hươu rừng'),
  anhChoSon: z.string().describe('Ảnh cắt chó sói đồng cỏ'),
  anhPeccary: z.string().describe('Ảnh cắt đàn lợn rừng peccary'),

  bgZoomTu: z.number().describe('Độ phóng nền rừng lúc bắt đầu'),
  bgZoomDen: z.number().describe('Độ phóng nền rừng lúc kết thúc'),
  nuocZoomTu: z.number().describe('Độ phóng nền vũng nước lúc bắt đầu'),
  nuocZoomDen: z.number().describe('Độ phóng nền vũng nước lúc kết thúc'),

  huouRong: z.number().describe('Chiều rộng đàn hươu (px)'),
  huouCao: z.number().describe('Chiều cao đàn hươu (px)'),
  huouX0: z.number().describe('Vị trí ngang đàn hươu lúc đầu (px)'),
  huouX1: z.number().describe('Vị trí ngang đàn hươu lúc cuối (px)'),
  huouY: z.number().describe('Vị trí dọc đàn hươu (px)'),

  choRong: z.number().describe('Chiều rộng chó sói đồng cỏ (px)'),
  choCao: z.number().describe('Chiều cao chó sói đồng cỏ (px)'),
  choX: z.number().describe('Vị trí ngang chó sói (px)'),
  choY: z.number().describe('Vị trí dọc chó sói (px)'),

  pecRong: z.number().describe('Chiều rộng đàn peccary (px)'),
  pecCao: z.number().describe('Chiều cao đàn peccary (px)'),
  pecX: z.number().describe('Vị trí ngang đàn peccary (px)'),
  pecY: z.number().describe('Vị trí dọc đàn peccary (px)'),

  frameTruot: z.number().describe('Khung hình bắt đầu trượt cảnh'),
  daiTruot: z.number().describe('Số frame trượt cảnh'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const fTruot = props.frameTruot;
  const fTruotHet = fTruot + props.daiTruot;

  // Camera lướt sang trái: nền rừng trôi sang trái, vũng nước lướt vào từ phải
  const slide = interpolate(frame, [fTruot, fTruotHet], [0, -1920], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const slideIn = interpolate(frame, [fTruot, fTruotHet], [1920, 0], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });

  // Đàn hươu men theo lối mòn, trượt chậm từ trái sang phải
  const huouT = interpolate(frame, [2, 140], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const huouX = interpolate(huouT, [0, 1], [props.huouX0, props.huouX1]);
  const huouY = props.huouY + interpolate(frame, [2, 140], [0, 18], {...kep});

  // Chó sói đồng cỏ xuất hiện bên bờ nước
  const choT = interpolate(frame, [98, 122], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const choX = (1 - choT) * 110 - interpolate(frame, [122, 278], [0, 26], {...kep});
  const choOp = choT;

  // Đàn peccary bước vào từ góc phải
  const pecT = interpolate(frame, [139, 174], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const pecX = (1 - pecT) * 860 - interpolate(frame, [174, 278], [0, 24], {...kep});
  const pecOp = interpolate(frame, [139, 152], [0, 1], {...kep});

  return (
    <AbsoluteFill style={{backgroundColor: '#16210f', overflow: 'hidden'}}>
      {/* NỀN 1: rừng rậm có lối mòn */}
      <Interactive.Div
        name="Nền rừng lối mòn"
        from={0}
        durationInFrames={278}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${slide}px)`,
        }}
      >
        <AnhNen anh={props.anhNenRung} tu={props.bgZoomTu} den={props.bgZoomDen} goc="50% 55%" toi={0.1} />
      </Interactive.Div>

      {/* ĐÀN HƯƠU RỪNG trên lối mòn */}
      <Interactive.Div
        name="Đàn hươu rừng"
        from={2}
        durationInFrames={276}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${slide}px)`,
        }}
      >
        <Img
          name="Đàn hươu"
          src={src(props.anhHuou)}
          style={{
            position: 'absolute',
            left: huouX,
            top: huouY,
            width: props.huouRong,
            height: props.huouCao,
            objectFit: 'contain',
          }}
        />
      </Interactive.Div>

      {/* NỀN 2: vũng nước đọng (lướt vào từ phải) */}
      <Interactive.Div
        name="Vũng nước đọng"
        from={92}
        durationInFrames={186}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${slideIn}px)`,
        }}
      >
        <AnhNen anh={props.anhNenVuong} tu={props.nuocZoomTu} den={props.nuocZoomDen} goc="50% 45%" toi={0.07} />
      </Interactive.Div>

      {/* CHÓ SÓI ĐỒNG CỎ bên bờ nước */}
      <Interactive.Div
        name="Chó sói đồng cỏ"
        from={98}
        durationInFrames={180}
        style={{
          position: 'absolute',
          left: props.choX,
          top: props.choY,
        }}
      >
        <Img
          name="Chó sói"
          src={src(props.anhChoSon)}
          style={{
            width: props.choRong,
            height: props.choCao,
            objectFit: 'contain',
            opacity: choOp,
            transform: `translateX(${choX}px)`,
          }}
        />
      </Interactive.Div>

      {/* ĐÀN LỢN RỪNG PECCARY bước vào từ phải */}
      <Interactive.Div
        name="Đàn lợn rừng peccary"
        from={139}
        durationInFrames={139}
        style={{
          position: 'absolute',
          left: props.pecX,
          top: props.pecY,
        }}
      >
        <Img
          name="Đàn peccary"
          src={src(props.anhPeccary)}
          style={{
            width: props.pecRong,
            height: props.pecCao,
            objectFit: 'contain',
            opacity: pecOp,
            transform: `translateX(${pecX}px)`,
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
