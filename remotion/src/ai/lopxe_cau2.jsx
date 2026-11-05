import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền suối lốp'),
  anh_nong_dan: z.string().describe('Hình cắt người nông dân'),
  chu_doan_1: z.string().describe('Chữ phần 1: Không ai tin'),
  chu_doan_2: z.string().describe('Chữ phần 2: Tạo nên trò trống gì?'),
  nhan_so_lop: z.string().optional().describe('Số lượng lốp xe phế liệu (không dùng)'),
});

const TieuDeDoan3 = ({chu}) => {
  const f = useCurrentFrame();
  const words = String(chu).trim().split(/\s+/);

  return (
    <div style={{position: 'relative'}}>
      {/* Scrim tối phía sau để bảo đảm độ tương phản tối đa trên nền cát sa mạc */}
      <div
        style={{
          position: 'absolute',
          left: -40,
          top: -30,
          width: 1250,
          height: 250,
          background: 'radial-gradient(ellipse at 30% 45%, rgba(10, 8, 6, 0.8) 0%, rgba(10, 8, 6, 0.45) 60%, transparent 85%)',
          borderRadius: 20,
          pointerEvents: 'none',
        }}
      />
      <div style={{position: 'relative', display: 'flex', flexDirection: 'column', gap: 14}}>
        <div style={{display: 'flex', flexWrap: 'wrap', gap: '0 24px', alignItems: 'baseline'}}>
          {words.map((w, i) => {
            const delay = i * 2.5;
            const p = interpolate(f, [delay, delay + 5], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
            const isHighlight = /^(trò|trống|gì\??)$/i.test(w);
            return (
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  opacity: p,
                  transform: `translateY(${(1 - p) * 14}px)`,
                  fontFamily: FONT,
                  fontWeight: 900,
                  fontSize: 100,
                  color: isHighlight ? VANG : '#ffffff',
                  letterSpacing: '-1px',
                  lineHeight: 1.15,
                  textShadow: '0 4px 18px rgba(0, 0, 0, 0.95), 0 8px 36px rgba(0, 0, 0, 0.95), 0 2px 4px #000',
                }}
              >
                {w}
              </span>
            );
          })}
        </div>
        {/* Vạch gạch chân vàng nằm BÊN DƯỚI chữ, hoàn toàn không cắt ngang thân chữ */}
        <div
          style={{
            width: interpolate(f, [4, 18], [0, 260], {...kep, easing: Easing.out(Easing.cubic)}),
            height: 8,
            backgroundColor: VANG,
            borderRadius: 4,
            boxShadow: '0 2px 12px rgba(0,0,0,0.7)',
          }}
        />
      </div>
    </div>
  );
};

export const Canh = ({
  anh_nen,
  anh_nong_dan,
  chu_doan_1 = 'Không ai tin',
  chu_doan_2 = 'Tạo nên trò trống gì?',
  nhan_so_lop,
}) => {
  const frame = useCurrentFrame();

  // Chuyển động camera đẩy góc nhìn xuống đống lốp:
  // 0 - 22 (0.0s - 0.72s): Khung hình tĩnh, bao quát người nông dân và bờ suối
  // 22 - 85 (0.72s - 2.8s): Camera push-in / zoom sâu xuống đống 1500 lốp xe dưới lòng suối
  const scaleCamera = interpolate(
    frame,
    [0, 22, 85],
    [1.0, 1.0, 1.30],
    {...kep, easing: Easing.bezier(0.25, 0.1, 0.25, 1)}
  );
  const translateYCamera = interpolate(
    frame,
    [0, 22, 85],
    [0, 0, -40],
    {...kep, easing: Easing.bezier(0.25, 0.1, 0.25, 1)}
  );

  // Hiệu ứng ánh nắng chói chang chiếu trực diện từ frame 44 (1.5s) đỉnh điểm ở từ 'trò trống' (frame 56 - 72)
  const doChoiSang = interpolate(
    frame,
    [42, 58, 72, 90],
    [0, 0.45, 0.4, 0.25],
    kep
  );

  // Người nông dân:
  // 0 - 5: Hiện dần rõ nét
  // 5 - 21: Đứng vững chãi trên bờ suối, 100% đặc (không trong suốt bóng ma)
  // 21 - 27: Trượt nhẹ sang trái và mờ dần khi camera bắt đầu lao xuống đống lốp
  const nongDanOpacity = interpolate(
    frame,
    [0, 5, 21, 27],
    [0, 1, 1, 0],
    kep
  );
  const nongDanTranslateX = interpolate(
    frame,
    [21, 27],
    [0, -100],
    kep
  );

  return (
    <AbsoluteFill style={{backgroundColor: '#1a140e', overflow: 'hidden', fontFamily: FONT}}>
      {/* Khung cảnh suối lốp có camera đẩy góc nhìn xuống lòng suối */}
      <Interactive.Div
        name="Khung cảnh suối lốp"
        from={0}
        durationInFrames={90}
        style={{
          position: 'absolute',
          inset: 0,
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: 1920,
            height: 1080,
            transformOrigin: '50% 74%',
            transform: `scale(${scaleCamera}) translateY(${translateYCamera}px)`,
          }}
        >
          <Img
            src={src(anh_nen)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />

          {/* Lớp ánh nắng gắt chiếu rọi trực diện xuống đống lốp ở đoạn sau */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(circle at 58% 70%, rgba(255, 235, 180, 0.9) 0%, rgba(255, 185, 50, 0.35) 45%, transparent 75%)',
              mixBlendMode: 'screen',
              opacity: doChoiSang,
              pointerEvents: 'none',
            }}
          />
        </div>
      </Interactive.Div>

      {/* Bóng người nông dân đứng trên bờ suối (0.0s đến 0.72s) */}
      <Interactive.Div
        name="Bóng nông dân hoài nghi"
        from={0}
        durationInFrames={28}
        style={{
          position: 'absolute',
          left: 100,
          top: 260,
          opacity: nongDanOpacity,
          transform: `translateX(${nongDanTranslateX}px)`,
          filter: 'drop-shadow(-15px 20px 25px rgba(0, 0, 0, 0.85)) contrast(1.05) brightness(0.9)',
        }}
      >
      </Interactive.Div>

      {/* Đoạn 1 (0.0s - 0.72s): Khung hình tĩnh, dòng chữ tối giản "Không ai tin" */}
      <Interactive.Div
        name="Tiêu đề: Không ai tin"
        from={0}
        durationInFrames={22}
        style={{
          position: 'absolute',
          left: 140,
          top: 110,
        }}
      >
        {/* Scrim tối để chữ trắng nổi bật trên nền trời và cát */}
        <div
          style={{
            position: 'absolute',
            left: -40,
            top: -30,
            width: 850,
            height: 220,
            background: 'radial-gradient(ellipse at 25% 45%, rgba(12, 10, 8, 0.75) 0%, rgba(12, 10, 8, 0.35) 55%, transparent 80%)',
            borderRadius: 16,
            pointerEvents: 'none',
          }}
        />
        <div style={{position: 'relative', display: 'flex', flexDirection: 'column', gap: 14}}>
          <h1
            style={{
              margin: 0,
              fontSize: 104,
              fontWeight: 900,
              color: '#ffffff',
              letterSpacing: '-1px',
              textTransform: 'uppercase',
              textShadow: '0 4px 20px rgba(0,0,0,0.95), 0 8px 32px rgba(0,0,0,0.85)',
              fontFamily: FONT,
            }}
          >
            {chu_doan_1}
          </h1>
          <div
            style={{
              width: 140,
              height: 8,
              backgroundColor: VANG,
              borderRadius: 4,
              boxShadow: '0 2px 10px rgba(0,0,0,0.6)',
            }}
          />
        </div>
      </Interactive.Div>

      {/* Đoạn 3 (1.52s - 2.35s+): Ánh nắng gắt, câu hỏi hoài nghi "Tạo nên trò trống gì?" */}
      <Interactive.Div
        name="Tiêu đề: Tạo nên trò trống gì?"
        from={46}
        durationInFrames={44}
        style={{
          position: 'absolute',
          left: 140,
          top: 120,
        }}
      >
        <TieuDeDoan3 chu={chu_doan_2} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
