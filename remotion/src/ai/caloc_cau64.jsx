import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT} from './thu_vien.jsx';

export const schema = z.object({
  mapBgPath: z.string().describe('Đường dẫn ảnh nền bản đồ giấy da'),
  redArrowPath: z.string().describe('Đường dẫn hình mũi tên đỏ tách nền'),
  tieudeBeat1: z.string().describe('Tiêu đề Beat 1: Xâm nhập Huron'),
  tieudeBeat2: z.string().describe('Tiêu đề Beat 2: Lan tới Superior'),
  tieudeBeat3: z.string().describe('Tiêu đề kết: Hoàn tất xâm chiếm Ngũ Hồ'),
  mauDoMuc: z.string().describe('Màu đỏ thẫm nét vẽ bản đồ cổ'),
  mauGiayDa: z.string().describe('Màu nền bảng nhãn giấy da cổ'),
  mauChuDam: z.string().describe('Màu chữ chính trên nhãn'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Camera chuyển động tự nhiên: nhẹ nhàng trôi ở Beat 1 & 2, sau đó zoom punch vào Hồ Superior ở Beat 3 (từ frame 210 trở đi)
  const cameraScale = interpolate(
    frame,
    [0, 110, 210, 307],
    [1.0, 1.05, 1.08, 1.25],
    {
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      ...kep,
    }
  );

  const cameraTranslateX = interpolate(
    frame,
    [0, 210, 307],
    [0, -20, 80],
    {
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      ...kep,
    }
  );

  const cameraTranslateY = interpolate(
    frame,
    [0, 210, 307],
    [0, -10, 70],
    {
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      ...kep,
    }
  );

  // Mũi tên 1: Hồ Michigan -> Hồ Huron (Beat 1: frame 0 -> 109)
  const progressArrow1 = interpolate(frame, [15, 80], [0, 1], {
    easing: Easing.out(Easing.cubic),
    ...kep,
  });

  // Mũi tên 2: Nối dài từ Hồ Huron lên Hồ Superior (Beat 2: frame 110 -> 210)
  const progressArrow2 = interpolate(frame, [125, 195], [0, 1], {
    easing: Easing.out(Easing.cubic),
    ...kep,
  });

  // Hiệu ứng gợn sóng nước hồ Superior đậm hơn tại Beat 3 (frame 210 - 307)
  const beat3Progress = interpolate(frame, [210, 250], [0, 1], kep);
  const pulseRipples = Math.sin((frame - 210) * 0.18) * 0.15;
  const rippleScale = 1 + (frame > 210 ? pulseRipples : 0);

  // Hiệu ứng hiện các bảng tiêu đề
  const label1Spring = spring({
    frame: frame - 10,
    fps,
    config: {damping: 14, stiffness: 100},
  });

  const label2Spring = spring({
    frame: frame - 120,
    fps,
    config: {damping: 14, stiffness: 100},
  });

  const label3Spring = spring({
    frame: frame - 225,
    fps,
    config: {damping: 12, stiffness: 90},
  });

  // Độ mờ nhãn Hồ Huron: tự động fade-out khi camera zoom vào Hồ Superior (từ frame 210)
  const huronOpacity = interpolate(frame, [40, 55, 210, 230], [0, 1, 1, 0], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#1b140e', overflow: 'hidden'}}>
      {/* Khối Camera Zoom & Pan toàn bộ thế giới bản đồ */}
      <div
        style={{
          width: 1920,
          height: 1080,
          position: 'absolute',
          transformOrigin: '55% 40%',
          transform: `scale(${cameraScale}) translate(${cameraTranslateX}px, ${cameraTranslateY}px)`,
        }}
      >
        {/* Bản đồ nền giấy da Ngũ Hồ Bắc Mỹ */}
        <Interactive.Div
          name="Bản đồ nền cổ"
          from={0}
          durationInFrames={307}
          style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
        >
          <Img
            src={src(props.mapBgPath)}
            style={{
              width: 1920,
              height: 1080,
              objectFit: 'cover',
              filter: 'sepia(0.2) contrast(1.08) brightness(0.96)',
            }}
          />
        </Interactive.Div>

        {/* Lớp minh họa gợn sóng nước nổi bật tại Hồ Superior ở Beat 3 */}
        {frame >= 210 && (
          <Interactive.Div
            name="Gợn sóng Hồ Superior"
            from={210}
            durationInFrames={97}
            style={{
              position: 'absolute',
              left: 650,
              top: 260,
              width: 440,
              height: 220,
              pointerEvents: 'none',
              opacity: beat3Progress * 0.85,
              transform: `scale(${rippleScale})`,
              transformOrigin: 'center center',
            }}
          >
            <svg width="440" height="220" viewBox="0 0 440 220" fill="none">
              <path
                d="M 30,80 Q 90,50 160,75 T 310,70 T 410,95"
                stroke="#1a4c6e"
                strokeWidth="7"
                strokeLinecap="round"
                opacity="0.8"
              />
              <path
                d="M 60,120 Q 140,95 230,115 T 380,110"
                stroke="#1a4c6e"
                strokeWidth="6"
                strokeLinecap="round"
                opacity="0.7"
              />
              <path
                d="M 110,160 Q 180,140 270,155 T 360,150"
                stroke="#0f344d"
                strokeWidth="5"
                strokeLinecap="round"
                opacity="0.6"
              />
            </svg>
          </Interactive.Div>
        )}

        {/* Mũi tên và đường hành quân vẽ tay đồ họa SVG đồng bộ chất liệu mực cổ xuyên suốt */}
        <svg
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            pointerEvents: 'none',
          }}
        >
          <defs>
            <marker
              id="arrowHead1"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill={props.mauDoMuc} />
            </marker>
            <marker
              id="arrowHead2"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill={props.mauDoMuc} />
            </marker>
            <filter id="handDrawnSketch">
              <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise" />
              <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G" />
            </filter>
          </defs>

          {/* Đường vẽ đứt khúc xâm lấn Beat 1: Hồ Michigan -> Hồ Huron */}
          <path
            d="M 770 650 Q 820 540 980 535"
            fill="none"
            stroke={props.mauDoMuc}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray="300"
            strokeDashoffset={300 * (1 - progressArrow1)}
            markerEnd={progressArrow1 > 0.95 ? 'url(#arrowHead1)' : ''}
            filter="url(#handDrawnSketch)"
            opacity={0.92}
          />

          {/* Đường vẽ đứt khúc xâm lấn Beat 2: Hồ Huron -> Hồ Superior cùng phong cách mực vẽ tay */}
          {frame >= 115 && (
            <path
              d="M 980 535 Q 920 400 780 360"
              fill="none"
              stroke={props.mauDoMuc}
              strokeWidth="13"
              strokeLinecap="round"
              strokeDasharray="340"
              strokeDashoffset={340 * (1 - progressArrow2)}
              markerEnd={progressArrow2 > 0.95 ? 'url(#arrowHead2)' : ''}
              filter="url(#handDrawnSketch)"
              opacity={0.92}
            />
          )}
        </svg>

        {/* Điểm neo đỏ tại Hồ Michigan xuất phát */}
        <Interactive.Div
          name="Điểm gốc Hồ Michigan"
          from={0}
          durationInFrames={307}
          style={{
            position: 'absolute',
            left: 760,
            top: 642,
            width: 24,
            height: 24,
            borderRadius: '50%',
            backgroundColor: props.mauDoMuc,
            boxShadow: '0 0 10px rgba(160, 20, 20, 0.7)',
          }}
        />

        {/* Nhãn mác định vị Hồ Huron trên bản đồ - Fade out khi bắt đầu zoom Beat 3 */}
        {frame >= 40 && frame < 235 && (
          <Interactive.Div
            name="Nhãn vị trí Hồ Huron"
            from={40}
            durationInFrames={195}
            style={{
              position: 'absolute',
              left: 1040,
              top: 510,
              padding: '8px 24px',
              backgroundColor: 'rgba(244, 233, 210, 0.85)',
              border: `3px solid ${props.mauDoMuc}`,
              borderRadius: 6,
              boxShadow: '2px 4px 12px rgba(0,0,0,0.3)',
              opacity: huronOpacity,
              transform: `scale(${interpolate(frame, [40, 55], [0.8, 1], kep)})`,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 34,
                fontWeight: 800,
                color: props.mauChuDam,
                letterSpacing: 2,
                textTransform: 'uppercase',
              }}
            >
              HỒ HURON
            </div>
          </Interactive.Div>
        )}

        {/* Nhãn mác định vị Hồ Superior trên bản đồ - Chuyển vào giữa lòng hồ tránh bị banner đè */}
        {frame >= 160 && (
          <Interactive.Div
            name="Nhãn vị trí Hồ Superior"
            from={160}
            durationInFrames={147}
            style={{
              position: 'absolute',
              left: 760,
              top: 310,
              padding: '8px 26px',
              backgroundColor: 'rgba(244, 233, 210, 0.9)',
              border: `3px solid ${props.mauDoMuc}`,
              borderRadius: 6,
              boxShadow: '2px 4px 12px rgba(0,0,0,0.35)',
              opacity: interpolate(frame, [160, 175], [0, 1], kep),
              transform: `scale(${interpolate(frame, [160, 175], [0.8, 1], kep)})`,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 34,
                fontWeight: 800,
                color: props.mauChuDam,
                letterSpacing: 2,
                textTransform: 'uppercase',
              }}
            >
              HỒ SUPERIOR
            </div>
          </Interactive.Div>
        )}
      </div>

      {/* LỚP TIÊU ĐỀ THUYẾT MINH PHIM TÀI LIỆU */}

      {/* Beat 1 Text: '1937: Hồ Huron' */}
      {frame >= 10 && frame < 125 && (
        <Interactive.Div
          name="Tiêu đề Beat 1"
          from={10}
          durationInFrames={115}
          style={{
            position: 'absolute',
            left: 100,
            top: 100,
            transform: `scale(${label1Spring})`,
            transformOrigin: 'top left',
            opacity: interpolate(frame, [105, 125], [1, 0], kep),
          }}
        >
          <div
            style={{
              backgroundColor: props.mauGiayDa,
              borderLeft: `14px solid ${props.mauDoMuc}`,
              padding: '24px 44px',
              boxShadow: '0 16px 36px rgba(0,0,0,0.4)',
              borderRadius: '0 12px 12px 0',
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 76,
                fontWeight: 900,
                color: props.mauChuDam,
                lineHeight: 1.1,
                letterSpacing: 1.5,
              }}
            >
              {props.tieudeBeat1}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 32,
                fontWeight: 600,
                color: props.mauDoMuc,
                marginTop: 8,
                letterSpacing: 3,
                textTransform: 'uppercase',
              }}
            >
              Đợt xâm nhập lần thứ hai
            </div>
          </div>
        </Interactive.Div>
      )}

      {/* Beat 2 Text: '1938: Hồ Superior' */}
      {frame >= 120 && frame < 220 && (
        <Interactive.Div
          name="Tiêu đề Beat 2"
          from={120}
          durationInFrames={100}
          style={{
            position: 'absolute',
            left: 100,
            top: 100,
            transform: `scale(${label2Spring})`,
            transformOrigin: 'top left',
            opacity: interpolate(frame, [205, 220], [1, 0], kep),
          }}
        >
          <div
            style={{
              backgroundColor: props.mauGiayDa,
              borderLeft: `14px solid ${props.mauDoMuc}`,
              padding: '24px 44px',
              boxShadow: '0 16px 36px rgba(0,0,0,0.4)',
              borderRadius: '0 12px 12px 0',
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 76,
                fontWeight: 900,
                color: props.mauChuDam,
                lineHeight: 1.1,
                letterSpacing: 1.5,
              }}
            >
              {props.tieudeBeat2}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 32,
                fontWeight: 600,
                color: props.mauDoMuc,
                marginTop: 8,
                letterSpacing: 3,
                textTransform: 'uppercase',
              }}
            >
              Tiến vào vùng nước sâu lạnh giá
            </div>
          </div>
        </Interactive.Div>
      )}

      {/* Beat 3 Text Kết: Đã tối ưu kích thước khung và co chữ nằm gọn trên 1 dòng */}
      {frame >= 220 && (
        <Interactive.Div
          name="Tiêu đề chốt Beat 3"
          from={220}
          durationInFrames={87}
          style={{
            position: 'absolute',
            left: 120,
            bottom: 80,
            transform: `scale(${label3Spring})`,
            transformOrigin: 'bottom left',
          }}
        >
          <div
            style={{
              backgroundColor: 'rgba(247, 239, 220, 0.96)',
              border: `4px solid ${props.mauDoMuc}`,
              borderLeft: `18px solid ${props.mauDoMuc}`,
              padding: '24px 38px',
              borderRadius: 8,
              boxShadow: '0 20px 45px rgba(0,0,0,0.45)',
              display: 'inline-block',
              maxWidth: 1200,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 66,
                fontWeight: 900,
                color: props.mauDoMuc,
                lineHeight: 1.1,
                textTransform: 'uppercase',
                letterSpacing: 1.5,
                whiteSpace: 'nowrap',
              }}
            >
              {props.tieudeBeat3}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 30,
                fontWeight: 700,
                color: '#2a1a08',
                marginTop: 8,
                letterSpacing: 1.2,
                whiteSpace: 'nowrap',
              }}
            >
              Toàn bộ hệ sinh thái Ngũ Hồ đã thất thủ (1938)
            </div>
          </div>
        </Interactive.Div>
      )}

      {/* Khung viền mờ tối phong cách bản đồ lưu trữ lịch sử cổ */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          boxShadow: 'inset 0 0 140px rgba(35, 20, 8, 0.75)',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
