import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  nen1: z.string().describe('Ảnh nền 1 - bãi lốp cũ ngập nước Florida'),
  can1: z.string().describe('Ảnh cận 1 - cận cảnh đống lốp phế liệu bỏ hoang'),
  tieuDeKhoa: z.string().describe('Chữ nhấn chính khi bị đóng băng'),
  mauBang: z.string().describe('Màu sắc ánh xanh băng giá'),
});

export const Canh = ({nen1, can1, tieuDeKhoa, mauBang}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Timing các mốc quan trọng (tính theo frame):
  // Beat 1: 0 - 66 (0s - 2.2s)
  // Beat 2: 66 - 126 (2.2s - 4.2s)
  // Beat 3: 126 - 225 (4.2s - 7.5s, từ 'đóng băng' bắt đầu từ frame 177)

  // Hiệu ứng chuyển cảnh Whoosh giữa Beat 1 và Beat 2 tại frame 66 (từ vụ tai tiếng...)
  const whooshProgress = interpolate(frame, [62, 72], [0, 1], kep);
  const whooshX = interpolate(whooshProgress, [0, 1], [0, -1920], {
    easing: Easing.bezier(0.25, 0.1, 0.25, 1),
  });

  // Hiệu ứng màng băng lạnh lẽo mờ mờ ở Beat 1 (định kiến môi trường)
  const bangOverlayBeat1 = interpolate(frame, [24, 60], [0, 0.42], kep);

  // Hiệu ứng đông cứng/đóng băng toàn khung hình ở Beat 3 (từ frame 173 đến 195)
  const dongBangTienTrinh = interpolate(frame, [173, 195], [0, 1], kep);
  const opacityLopBang = interpolate(dongBangTienTrinh, [0, 1], [0, 0.48]);
  const vienBangWipe = interpolate(dongBangTienTrinh, [0, 1], [0, 100]);

  // Spring xuất hiện cho Text chính 'BỊ ĐÓNG BĂNG SUỐT NHIỀU NĂM'
  const textSpring = spring({
    frame: frame - 177,
    fps,
    config: {damping: 12, mass: 0.9, stiffness: 100},
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0a1118', overflow: 'hidden'}}>
      {/* Beat 1: Bãi lốp xe ngập nước Florida (0 - 66 frames) */}
      <Interactive.Div
        name="Beat 1"
        from={0}
        durationInFrames={72}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${whooshX}px)`,
        }}
      >
        <AnhNen anh={nen1} tu={1.0} den={1.08} goc="50% 40%" toi={0.25} />

        {/* Lớp màng sương lạnh / phủ băng râm râm Beat 1 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(135deg, rgba(160,216,239,0.35) 0%, rgba(20,50,70,0.5) 100%)',
            opacity: bangOverlayBeat1,
            mixBlendMode: 'screen',
            pointerEvents: 'none',
          }}
        />
      </Interactive.Div>

      {/* Beat 2 & Beat 3: Cận cảnh lốp phế liệu bỏ hoang ngoài trời (bắt đầu từ frame 66) */}
      <Interactive.Div
        name="Beat 2 và 3"
        from={66}
        durationInFrames={159}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
        }}
      >
        {/* Slow zoom đẩy vào chủ thể đống lốp xe */}
        <AnhNen anh={can1} tu={1.02} den={1.12} goc="50% 50%" toi={0.3} />

        {/* Lớp sương giá và màng băng tuyết đóng cứng toàn bộ khung hình ở Beat 3 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: opacityLopBang,
            background: `radial-gradient(circle at center, rgba(186,230,253,0.2) 30%, rgba(125,211,252,0.6) 80%, rgba(56,189,248,0.7) 100%)`,
            mixBlendMode: 'screen',
            pointerEvents: 'none',
          }}
        />

        {/* Khung viền băng tuyết buốt giá kết tinh bao quanh viền màn hình */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            border: `${interpolate(dongBangTienTrinh, [0, 1], [0, 24])}px solid ${mauBang}`,
            opacity: opacityLopBang,
            boxShadow: `inset 0 0 ${interpolate(dongBangTienTrinh, [0, 1], [0, 80])}px rgba(224,242,254,0.7)`,
            pointerEvents: 'none',
          }}
        />

        {/* Vệt rạn nứt / mảng băng sắc nhọn dạng đồ họa SVG bao phủ khi đóng băng */}
        {dongBangTienTrinh > 0 && (
          <svg
            style={{
              position: 'absolute',
              inset: 0,
              width: 1920,
              height: 1080,
              opacity: dongBangTienTrinh * 0.75,
              pointerEvents: 'none',
            }}
          >
            <path
              d="M0 0 L420 380 L350 490 L680 620 M1920 0 L1540 280 L1620 420 L1300 580 M0 1080 L480 820 L590 910 L750 720 M1920 1080 L1490 850 L1400 950 L1180 770"
              stroke="#e0f2fe"
              strokeWidth="4"
              strokeDasharray="6 3"
              fill="none"
              style={{
                strokeDashoffset: (1 - dongBangTienTrinh) * 400,
              }}
            />
          </svg>
        )}
      </Interactive.Div>

      {/* Beat 3: Text chính xuất hiện tại từ khóa 'bị đóng băng' (frame 177) */}
      <Interactive.Div
        name="Chữ Nhấn"
        from={177}
        durationInFrames={48}
        style={{
          position: 'absolute',
          left: 120,
          top: 760,
          width: 1680,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          transform: `scale(${interpolate(textSpring, [0, 1], [0.88, 1])}) translateY(${interpolate(
            textSpring,
            [0, 1],
            [30, 0]
          )}px)`,
          opacity: textSpring,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 96,
            fontWeight: 900,
            color: '#f8fafc',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            textShadow: '0 8px 30px rgba(0, 0, 0, 0.9), 0 0 40px rgba(56, 189, 248, 0.8)',
            lineHeight: 1.15,
            borderLeft: `14px solid ${mauBang}`,
            paddingLeft: 36,
          }}
        >
          {tieuDeKhoa}
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
