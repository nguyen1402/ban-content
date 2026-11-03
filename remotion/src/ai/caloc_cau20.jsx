import React from 'react';
import { AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { src, kep, FONT, VANG, EM } from './thu_vien.jsx';

export const schema = z.object({
  anh_nen_dia_hinh: z.string().describe('Đường dẫn ảnh nền mặt cắt địa hình'),
  anh_toa_nha: z.string().describe('Đường dẫn cut-out tòa nhà 30 tầng'),
  nhan_do_cao: z.string().describe('Chữ hiển thị vạch đo độ cao'),
  nhan_tang_nha: z.string().describe('Chữ hiển thị nhãn tòa nhà'),
  nhan_ho_erie: z.string().describe('Nhãn hồ trên (Hồ Erie)'),
  nhan_ho_ontario: z.string().describe('Nhãn hồ dưới (Hồ Ontario)'),
  mau_thuoc_do: z.string().describe('Màu phát sáng của thước đo kỹ thuật số'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Camera dolly-in nhẹ từ 1.36s (frame 41) đến cuối
  const cameraScale = interpolate(frame, [0, 41, 140, 249], [1.0, 1.0, 1.08, 1.12], kep);
  const cameraY = interpolate(frame, [41, 140, 249], [0, -25, -35], kep);

  // Vạch đo xuất hiện đúng chữ "chênh lệch" (frame 111)
  const tienDoThuoc = spring({
    frame: frame - 111,
    fps,
    config: { damping: 18, stiffness: 90, mass: 0.8 },
  });
  const chieuDaiThuoc = interpolate(tienDoThuoc, [0, 1], [0, 520], kep);

  // Số đo nhảy dứt khoát lên ~99 m từ frame 111 tới frame 145
  const giaTriSo = Math.round(interpolate(frame, [111, 145], [0, 99], kep));

  // Tòa nhà 30 tầng trượt dọc vút lên đúng chữ "tòa nhà" (frame 206)
  const tienDoToaNha = spring({
    frame: frame - 206,
    fps,
    config: { damping: 16, stiffness: 100, mass: 0.9 },
  });
  const viTriYToaNha = interpolate(tienDoToaNha, [0, 1], [580, 0], kep);
  const doMoToaNha = interpolate(tienDoToaNha, [0, 0.2, 1], [0, 1, 1], kep);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000', overflow: 'hidden', fontFamily: FONT }}>
      {/* Nền mặt cắt địa hình với camera dolly-in */}
      <div
        style={{
          width: 1920,
          height: 1080,
          transform: `scale(${cameraScale}) translateY(${cameraY}px)`,
          transformOrigin: '55% 55%',
        }}
      >
        <Img
          src={src(props.anh_nen_dia_hinh)}
          style={{ width: 1920, height: 1080, objectFit: 'cover' }}
        />

        {/* Lớp hơi sương bốc mù mịt chân thác Niagara */}
        <div
          style={{
            position: 'absolute',
            left: 800,
            top: 620,
            width: 480,
            height: 220,
            background: 'radial-gradient(ellipse at center, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0) 75%)',
            opacity: interpolate(frame, [41, 75], [0.2, 0.8], kep),
            pointerEvents: 'none',
          }}
        />

        {/* Nhãn Hồ Erie (Thềm cao bên trái) */}
        <Interactive.Div
          name="Nhãn Hồ Erie"
          from={0}
          durationInFrames={249}
          style={{ position: 'absolute', left: 160, top: 210 }}
        >
          <div
            style={{
              padding: '12px 28px',
              backgroundColor: 'rgba(10, 25, 45, 0.82)',
              borderLeft: `6px solid ${VANG}`,
              borderRadius: 8,
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              opacity: interpolate(frame, [0, 20], [0, 1], kep),
            }}
          >
            <span style={{ fontSize: 56, fontWeight: 800, color: '#ffffff', letterSpacing: 1 }}>
              {props.nhan_ho_erie}
            </span>
          </div>
        </Interactive.Div>

        {/* Nhãn Hồ Ontario (Vực trũng bên phải) */}
        <Interactive.Div
          name="Nhãn Hồ Ontario"
          from={0}
          durationInFrames={249}
          style={{ position: 'absolute', left: 1420, top: 760 }}
        >
          <div
            style={{
              padding: '12px 28px',
              backgroundColor: 'rgba(10, 25, 45, 0.82)',
              borderLeft: `6px solid ${props.mau_thuoc_do}`,
              borderRadius: 8,
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              opacity: interpolate(frame, [0, 20], [0, 1], kep),
            }}
          >
            <span style={{ fontSize: 56, fontWeight: 800, color: '#ffffff', letterSpacing: 1 }}>
              {props.nhan_ho_ontario}
            </span>
          </div>
        </Interactive.Div>

        {/* Thước kỹ thuật số đo mực nước chênh lệch (từ frame 111) */}
        <Interactive.Div
          name="Thước đo độ cao"
          from={111}
          durationInFrames={138}
          style={{ position: 'absolute', left: 930, top: 260 }}
        >
          {frame >= 111 && (
            <div style={{ position: 'relative', width: 280, height: 560 }}>
              {/* Vạch ngang mực nước trên */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: -35,
                  width: 90,
                  height: 4,
                  backgroundColor: props.mau_thuoc_do,
                  boxShadow: `0 0 14px ${props.mau_thuoc_do}`,
                }}
              />

              {/* Vạch kẻ đứng phát sáng kéo dài xuống */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 10,
                  width: 4,
                  height: chieuDaiThuoc,
                  backgroundColor: props.mau_thuoc_do,
                  boxShadow: `0 0 16px ${props.mau_thuoc_do}`,
                }}
              />

              {/* Vạch ngang mực nước dưới */}
              <div
                style={{
                  position: 'absolute',
                  top: chieuDaiThuoc,
                  left: -35,
                  width: 90,
                  height: 4,
                  backgroundColor: props.mau_thuoc_do,
                  boxShadow: `0 0 14px ${props.mau_thuoc_do}`,
                  opacity: interpolate(tienDoThuoc, [0.8, 1], [0, 1], kep),
                }}
              />

              {/* Hộp nhãn số liệu ~99 m nổi bật */}
              <div
                style={{
                  position: 'absolute',
                  left: 36,
                  top: 210,
                  backgroundColor: 'rgba(6, 20, 36, 0.92)',
                  border: `3px solid ${props.mau_thuoc_do}`,
                  padding: '10px 24px',
                  borderRadius: 12,
                  boxShadow: `0 0 28px rgba(0, 240, 255, 0.45)`,
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 8,
                  transform: `scale(${interpolate(tienDoThuoc, [0, 1], [0.6, 1], kep)})`,
                  opacity: interpolate(tienDoThuoc, [0, 0.5, 1], [0, 1, 1], kep),
                }}
              >
                <span
                  style={{
                    fontSize: 92,
                    fontWeight: 900,
                    color: props.mau_thuoc_do,
                    lineHeight: 1,
                    textShadow: `0 0 20px ${props.mau_thuoc_do}`,
                  }}
                >
                  ~{giaTriSo}
                </span>
                <span
                  style={{
                    fontSize: 58,
                    fontWeight: 800,
                    color: '#ffffff',
                    lineHeight: 1,
                  }}
                >
                  m
                </span>
              </div>
            </div>
          )}
        </Interactive.Div>

        {/* Cut-out Tòa nhà chọc trời 30 tầng trượt vút lên đối chiếu 1:1 (từ frame 206) */}
        <Interactive.Div
          name="Tòa nhà 30 tầng"
          from={206}
          durationInFrames={43}
          style={{ position: 'absolute', left: 1045, top: 180 }}
        >
          {frame >= 206 && (
            <div
              style={{
                position: 'relative',
                transform: `translateY(${viTriYToaNha}px)`,
                opacity: doMoToaNha,
              }}
            >
              {/* Nhãn 30 tầng ở đỉnh tòa nhà */}
              <div
                style={{
                  position: 'absolute',
                  top: -55,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  whiteSpace: 'nowrap',
                  backgroundColor: VANG,
                  color: '#0d1520',
                  padding: '6px 22px',
                  borderRadius: 10,
                  fontSize: 58,
                  fontWeight: 900,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                  border: '2px solid #ffffff',
                }}
              >
                {props.nhan_tang_nha}
              </div>

              {/* Ảnh cut-out tòa nhà */}
              <Img
                src={src(props.anh_toa_nha)}
                style={{
                  width: 230,
                  height: 615,
                  objectFit: 'contain',
                  filter: 'drop-shadow(0 12px 30px rgba(0,0,0,0.85)) drop-shadow(0 0 15px rgba(255,255,255,0.3))',
                }}
              />
            </div>
          )}
        </Interactive.Div>
      </div>
    </AbsoluteFill>
  );
};
