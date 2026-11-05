import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Hình nền thung lũng Altar và dòng suối'),
  anh_bui_co: z.string().describe('Tách nền bụi cỏ sacaton cao'),
  anh_dan_bo: z.string().describe('Tách nền đàn bò gặm cỏ phía xa'),
  tieu_de_suoi: z.string().default('DÒNG SUỐI NÔNG UỐN LƯỢN').describe('Tiêu đề dòng suối nông'),
  nhan_suoi: z.string().default('Suối nông đáy sỏi').describe('Nhãn chỉ con suối nông đáy sỏi'),
  tieu_de_co: z.string().describe('Tiêu đề đồng cỏ sacaton'),
  nhan_dan_bo: z.string().describe('Nhãn chỉ đàn bò bị che khuất'),
});

export const Canh = ({
  anh_nen,
  anh_bui_co,
  anh_dan_bo,
  tieu_de_suoi = 'DÒNG SUỐI NÔNG UỐN LƯỢN',
  nhan_suoi = 'Suối nông đáy sỏi',
  tieu_de_co = 'CỎ SACATON CAO QUÁ ĐẦU BÒ',
  nhan_dan_bo = 'ĐÀN BÒ BỊ CHE KHUẤT',
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // Chuyển động máy quay mượt mà 2 giai đoạn:
  // 1) 0-42f (0.0-1.4s): Góc cao (high-angle shot) bao quát thung lũng Altar & con suối nông đáy sỏi uốn lượn
  // 2) 42-123f (1.4-4.1s): Hạ thấp cao độ, đâm xuyên vào thảm cỏ sacaton rậm rạp cao quá đầu đàn bò
  const scaleNen = interpolate(frame, [0, 42, 123], [1.02, 1.06, 1.24], {
    ...kep,
    easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
  });
  const translateYNen = interpolate(frame, [0, 42, 123], [0, -12, -50], {
    ...kep,
    easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
  });
  const translateXNen = interpolate(frame, [0, 42, 123], [0, -8, -25], {
    ...kep,
    easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
  });

  // Tiến trình máy quay hạ thấp và đâm xuyên vào thảm cỏ (frames 42 - 62)
  const enterCo = interpolate(frame, [42, 62], [0, 1], {
    ...kep,
    easing: Easing.bezier(0.2, 0.0, 0.2, 1.0),
  });

  // Đung đưa tự nhiên của bụi cỏ trong gió (nhẹ nhàng, hữu cơ)
  const gio1 = Math.sin(frame * 0.08) * 3.5;
  const gio2 = Math.cos(frame * 0.07) * 4.0;
  const gio3 = Math.sin(frame * 0.06 + 1.5) * 3.0;

  // Đàn bò phía xa: scale và vị trí chìm nhẹ trong đồng cỏ
  const boScale = interpolate(frame, [44, 123], [0.94, 1.0], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0d0a', overflow: 'hidden'}}>
      {/* 1. NỀN: Toàn cảnh thung lũng Altar & con suối nông đáy sỏi uốn lượn (Bao quát 1920x1080) */}
      <Interactive.Div
        name="Nền thung lũng Altar"
        from={0}
        durationInFrames={123}
        style={{
          position: 'absolute',
          inset: 0,
          overflow: 'hidden',
        }}
      >
        <Img
          src={src(anh_nen)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transformOrigin: '55% 65%',
            transform: `scale(${scaleNen}) translate(${translateXNen}px, ${translateYNen}px)`,
          }}
        />
      </Interactive.Div>

      {/* 2. TIÊU ĐỀ GIAI ĐOẠN 1: Dòng suối nông uốn lượn giữa thung lũng */}
      <Interactive.Div
        name="Tiêu đề suối nông"
        from={4}
        durationInFrames={38}
        style={{
          position: 'absolute',
          left: 90,
          top: 80,
          opacity: interpolate(frame, [4, 10, 36, 42], [0, 1, 1, 0], kep),
        }}
      >
        <ChuNoi chu={tieu_de_suoi} co={76} />
      </Interactive.Div>

      {/* 3. NHÃN CHÚ THÍCH SUỐI CẠN ĐÁY SỎI (Chỉ đúng vệt suối và bờ sỏi) */}
      <Interactive.Div
        name="Nhãn suối cạn đáy sỏi"
        from={10}
        durationInFrames={32}
        style={{
          position: 'absolute',
          left: 860,
          top: 660,
          opacity: interpolate(frame, [10, 16, 36, 42], [0, 1, 1, 0], kep),
        }}
      >
        <Nhan chu={nhan_suoi} dx={200} dy={-90} co={56} />
      </Interactive.Div>

      {/* 4. LỚP CỎ HẬU CẢNH TRÁI (Nằm sau đàn bò, tạo nền cỏ xa) */}
      <Interactive.Div
        name="Lớp cỏ hậu cảnh trái"
        from={42}
        durationInFrames={81}
        style={{
          position: 'absolute',
          left: 360,
          top: 360,
          opacity: enterCo,
          transformOrigin: 'bottom center',
          transform: `translateY(${(1 - enterCo) * 140}px) rotate(${gio1 * 0.4}deg)`,
          filter: 'brightness(0.86) contrast(0.95)',
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(anh_bui_co)}
          style={{
            width: 720,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 5. LỚP CỎ HẬU CẢNH PHẢI (Nằm sau đàn bò, nối dài thảm cỏ) */}
      <Interactive.Div
        name="Lớp cỏ hậu cảnh phải"
        from={42}
        durationInFrames={81}
        style={{
          position: 'absolute',
          left: 920,
          top: 370,
          opacity: enterCo,
          transformOrigin: 'bottom center',
          transform: `translateY(${(1 - enterCo) * 140}px) rotate(${gio2 * 0.4}deg)`,
          filter: 'brightness(0.88) contrast(0.95)',
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(anh_bui_co)}
          style={{
            width: 660,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 6. ĐÀN BÒ GẶM CỎ PHÍA XA (Đứng tự nhiên trên mặt đất giữa thảm cỏ) */}
      <Interactive.Div
        name="Đàn bò gặm cỏ phía xa"
        from={44}
        durationInFrames={79}
        style={{
          position: 'absolute',
          left: 540,
          top: 450,
          opacity: enterCo,
          transform: `translateY(${(1 - enterCo) * 100}px) scale(${boScale})`,
          filter: 'brightness(1.02) contrast(1.06)',
        }}
      >
        <Img
          src={src(anh_dan_bo)}
          style={{
            width: 750,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 7. LỚP CỎ TRUNG CẢNH CHE THÂN ĐÀN BÒ (Cỏ cao vượt đầu và lưng đàn bò) */}
      <Interactive.Div
        name="Lớp cỏ che thân đàn bò"
        from={44}
        durationInFrames={79}
        style={{
          position: 'absolute',
          left: 450,
          top: 370,
          opacity: enterCo,
          transformOrigin: 'bottom center',
          transform: `translateY(${(1 - enterCo) * 180}px) rotate(${gio1 * 0.7}deg)`,
          filter: 'brightness(0.96)',
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(anh_bui_co)}
          style={{
            width: 840,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 8. BỤI CỎ TIỀN CẢNH TRÁI (Lớn, cắm sát mép dưới, đung đưa theo gió) */}
      <Interactive.Div
        name="Bụi cỏ tiền cảnh trái"
        from={44}
        durationInFrames={79}
        style={{
          position: 'absolute',
          left: -90,
          bottom: -50,
          transformOrigin: 'bottom left',
          transform: `translateY(${(1 - enterCo) * 500}px) rotate(${gio1}deg)`,
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(anh_bui_co)}
          style={{
            width: 960,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 9. BỤI CỎ TIỀN CẢNH PHẢI (Lớn, cắm sát mép dưới, không lỗi mép) */}
      <Interactive.Div
        name="Bụi cỏ tiền cảnh phải"
        from={44}
        durationInFrames={79}
        style={{
          position: 'absolute',
          right: -90,
          bottom: -50,
          transformOrigin: 'bottom right',
          transform: `translateY(${(1 - enterCo) * 500}px) rotate(${gio2}deg)`,
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(anh_bui_co)}
          style={{
            width: 960,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 10. BỤI CỎ TIỀN CẢNH GIỮA (Ôm sát tầm mắt, làm nổi bật độ rậm rạp) */}
      <Interactive.Div
        name="Bụi cỏ tiền cảnh giữa"
        from={46}
        durationInFrames={77}
        style={{
          position: 'absolute',
          left: 380,
          bottom: -110,
          transformOrigin: 'bottom center',
          transform: `translateY(${(1 - enterCo) * 550}px) rotate(${gio3}deg)`,
          filter: 'brightness(1.04)',
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(anh_bui_co)}
          style={{
            width: 1100,
            height: 'auto',
          }}
        />
      </Interactive.Div>

      {/* 11. TIÊU ĐỀ GIAI ĐOẠN 2: Thảm cỏ sacaton cao quá đầu đàn bò */}
      <Interactive.Div
        name="Tiêu đề thảm cỏ cao"
        from={46}
        durationInFrames={77}
        style={{
          position: 'absolute',
          left: 90,
          top: 80,
          opacity: interpolate(frame, [46, 54], [0, 1], kep),
        }}
      >
        <ChuNoi chu={tieu_de_co} co={82} />
      </Interactive.Div>

      {/* 12. NHÃN CHỈ ĐÀN BÒ BỊ CHE KHUẤT PHÍA XA */}
      <Interactive.Div
        name="Nhãn đàn bò bị che khuất"
        from={72}
        durationInFrames={51}
        style={{
          position: 'absolute',
          left: 820,
          top: 480,
          opacity: interpolate(frame, [72, 80], [0, 1], kep),
        }}
      >
        <Nhan chu={nhan_dan_bo} dx={180} dy={-90} co={56} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
