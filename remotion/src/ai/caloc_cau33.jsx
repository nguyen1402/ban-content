import React from 'react';
import { AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { src, kep, FONT, VANG, Nhan, HienDan } from './thu_vien.jsx';

export const schema = z.object({
  bgImage: z.string().describe('Ảnh nền mô phỏng mặt cắt âu thuyền'),
  boatImage: z.string().describe('Hình ảnh con thuyền gỗ'),
  gateImage: z.string().describe('Hình ảnh cánh cổng gỗ'),
  text1: z.string().describe('Nhãn bước 1'),
  text2: z.string().describe('Nhãn bước 2'),
  
  // Dynamic Retiming & Positioning controls via schema
  text1From: z.number().describe('Frame xuất hiện nhãn 1 (Khóa cổng)'),
  text2From: z.number().describe('Frame xuất hiện nhãn 2 (Cân bằng mực nước)'),
  waterRiseFrom: z.number().describe('Frame bắt đầu dâng nước'),
  waterRiseTo: z.number().describe('Frame kết thúc dâng nước'),
  boatEnterFrom: z.number().describe('Frame thuyền bắt đầu vào'),
  boatEnterTo: z.number().describe('Frame thuyền vào vị trí'),
  
  lowWaterLevel: z.number().describe('Mực nước thấp (Y px)'),
  highWaterLevel: z.number().describe('Mực nước cao (Y px)'),
});

export const Canh = ({
  bgImage,
  boatImage,
  gateImage,
  text1,
  text2,
  text1From,
  text2From,
  waterRiseFrom,
  waterRiseTo,
  boatEnterFrom,
  boatEnterTo,
  lowWaterLevel,
  highWaterLevel,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 1. Thuyền lướt ngang vào khoang (2.58s -> 3.36s => frame 77 -> 101)
  const boatX = interpolate(
    frame,
    [boatEnterFrom, boatEnterTo],
    [-600, 610],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad) }
  );

  // 2. Cửa hạ lưu (phía sau) đóng sập xuống tại 3.86s - 4.85s (frame 116 -> 146)
  const gateDownProgress = interpolate(
    frame,
    [116, 146],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bounce }
  );
  const gateY = interpolate(gateDownProgress, [0, 1], [-400, 480]);

  // 3. Mực nước & thuyền nâng cao dần lên (5.81s -> 8.77s => frame 174 -> 263)
  const riseProgress = interpolate(
    frame,
    [waterRiseFrom, waterRiseTo],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) }
  );

  const currentWaterY = interpolate(riseProgress, [0, 1], [lowWaterLevel, highWaterLevel]);
  
  // Tính độ dâng của thuyền theo mực nước
  const boatYOffset = interpolate(riseProgress, [0, 1], [0, highWaterLevel - lowWaterLevel]);

  // Hiệu ứng bọt nước cuồn cuộn khi dâng nước (frame 174 -> 263)
  const isRising = frame >= waterRiseFrom && frame <= waterRiseTo;
  const bubbleOpacity = interpolate(
    frame,
    [waterRiseFrom, waterRiseFrom + 15, waterRiseTo - 15, waterRiseTo],
    [0, 0.8, 0.8, 0],
    kep
  );

  // Cửa thượng lưu hé mở khi mặt nước bằng nhau (frame 285 -> 320)
  const topGateOpen = interpolate(
    frame,
    [285, 320],
    [0, -120],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.ease) }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: '#1a1008', overflow: 'hidden' }}>
      {/* 1. Nền mặt cắt âu thuyền gỗ & đất đá */}
      <Interactive.Div name="Nền Âu Thuyền" from={0} durationInFrames={326}>
        <Img
          src={src(bgImage)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'brightness(0.95)',
          }}
        />
      </Interactive.Div>

      {/* 2. Cánh cổng gỗ hạ lưu (phía sau khoang) */}
      <Interactive.Div
        name="Cánh Cổng Hạ Lưu"
        from={0}
        durationInFrames={326}
        style={{
          position: 'absolute',
          left: 360,
          top: gateY,
          width: 220,
          height: 520,
          zIndex: 3,
        }}
      >
        <Img
          src={src(gateImage)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            transform: 'scaleX(-1)', // Xoay hướng cổng
          }}
        />
      </Interactive.Div>

      {/* 3. Khối Nước Trong Khoang Âu Thuyền (Nâng cao dần) */}
      <Interactive.Div
        name="Mặt Nước Âu Thuyền"
        from={0}
        durationInFrames={326}
        style={{
          position: 'absolute',
          left: 550,
          top: currentWaterY,
          width: 820,
          height: 1080 - lowWaterLevel,
          backgroundColor: 'rgba(34, 140, 200, 0.65)',
          borderTop: '5px solid #7be3ff',
          boxShadow: '0 0 20px rgba(123, 227, 255, 0.5)',
          zIndex: 4,
        }}
      >
        {/* Hiệu ứng bọt nước cuộn dâng */}
        {isRising && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              opacity: bubbleOpacity,
              background: 'radial-gradient(circle, rgba(255,255,255,0.4) 10%, transparent 60%)',
              backgroundSize: '40px 40px',
              animation: 'px',
            }}
          />
        )}
      </Interactive.Div>

      {/* 4. Con Thuyền Gỗ Lịch Sử */}
      <Interactive.Div
        name="Thuyền Gỗ"
        from={boatEnterFrom}
        durationInFrames={326 - boatEnterFrom}
        style={{
          position: 'absolute',
          left: boatX,
          top: 610 + boatYOffset,
          width: 650,
          height: 170,
          zIndex: 5,
        }}
      >
        <Img
          src={src(boatImage)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
        />
      </Interactive.Div>

      {/* 5. Cánh cổng gỗ thượng lưu (phía trước) - hé mở ở cuối */}
      <Interactive.Div
        name="Cánh Cổng Thượng Lưu"
        from={0}
        durationInFrames={326}
        style={{
          position: 'absolute',
          right: 340,
          top: 360 + topGateOpen,
          width: 220,
          height: 520,
          zIndex: 6,
        }}
      >
        <Img
          src={src(gateImage)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
        />
      </Interactive.Div>

      {/* 6. Nhãn Text 1: 1. Khóa cổng (Xuất hiện 3.86s / frame 116) */}
      {frame >= text1From && frame < text2From && (
        <Interactive.Div
          name="Nhãn 1 - Khóa cổng"
          from={text1From}
          durationInFrames={text2From - text1From}
          style={{
            position: 'absolute',
            left: 380,
            top: 320,
            zIndex: 10,
          }}
        >
          <HienDan vao={10} het={15}>
            <Nhan
              chu={text1}
              dx={80}
              dy={-90}
              co={58}
            />
          </HienDan>
        </Interactive.Div>
      )}

      {/* 7. Đường gióng màu xanh nối phẳng lì hai mặt nước + Nhãn Text 2 (Xuất hiện 8.77s / frame 263) */}
      {frame >= text2From && (
        <>
          {/* Đường gióng chấm bi màu xanh */}
          <Interactive.Div
            name="Đường Gióng Cân Bằng"
            from={text2From}
            durationInFrames={326 - text2From}
            style={{
              position: 'absolute',
              left: 200,
              top: highWaterLevel,
              width: 1520,
              height: 0,
              borderTop: '6px dashed #00e5ff',
              boxShadow: '0 0 12px #00e5ff',
              zIndex: 9,
            }}
          />

          {/* Nhãn 2: 2. Cân bằng mực nước */}
          <Interactive.Div
            name="Nhãn 2 - Cân bằng mực nước"
            from={text2From}
            durationInFrames={326 - text2From}
            style={{
              position: 'absolute',
              left: 960,
              top: highWaterLevel - 20,
              zIndex: 10,
            }}
          >
            <HienDan vao={8} het={15}>
              <Nhan
                chu={text2}
                dx={120}
                dy={-140}
                co={62}
              />
            </HienDan>
          </Interactive.Div>
        </>
      )}
    </AbsoluteFill>
  );
};
