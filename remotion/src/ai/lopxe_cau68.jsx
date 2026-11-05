import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  bg_lop_xe: z.string().describe('Hình nền đập lốp xe'),
  tach_lop_chan: z.string().describe('Hình cắt lốp xe chắn parallax'),
  can_lop_cat: z.string().describe('Cận cảnh mặt cắt lớp phù sa'),
  tach_chong_lop: z.string().describe('Hình cắt chồng 5 lốp xe so sánh'),
  nhan_phu_sa: z.string().describe('Chữ nhãn lớp đất đọng'),
  nhan_chieu_cao: z.string().describe('Chữ tiêu đề so sánh chiều cao'),
});

export const Canh = ({
  bg_lop_xe,
  tach_lop_chan,
  can_lop_cat,
  tach_chong_lop,
  nhan_phu_sa,
  nhan_chieu_cao,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // --- GIAI ĐOẠN 1: 0 -> 162 (0s - 5.4s) Khám phá mặt sau đập lốp xe & bồi tụ phù sa ---
  // Camera lia ngang và hạ góc nhìn xuống nền cát đọng
  const panBgX = interpolate(frame, [0, 65, 162], [0, -100, -180], kep);
  const panBgY = interpolate(frame, [0, 65, 162], [0, 15, -45], kep);
  const zoomBg = interpolate(frame, [0, 65, 162], [1.02, 1.08, 1.15], kep);

  // Parallax layer lốp xe chắn trượt mạnh sang trái hé lộ lòng đập (từ frame 20 "ngay phía sau")
  const lopChanX = interpolate(frame, [20, 75], [1150, -420], {
    ...kep,
    easing: Easing.bezier(0.25, 0.1, 0.25, 1),
  });
  const lopChanY = interpolate(frame, [20, 75], [520, 560], kep);

  // Ánh sáng ban mai quét nhẹ qua mặt đất đọng phù sa (frame 65 -> 136)
  const lightSweepX = interpolate(frame, [65, 125], [-600, 2200], kep);
  const lightOpacity = interpolate(frame, [65, 80, 115, 136], [0, 0.45, 0.45, 0], kep);

  // --- GIAI ĐOẠN 2: 162 -> 334 (5.4s - 11.1s) Cận cảnh địa tầng & thước đo 0.9m & 5 lốp xe ---
  // Punch-in dứt khoát vào mặt cắt lớp cát
  const punchScale = spring({
    frame: frame - 162,
    fps,
    config: {damping: 15, stiffness: 120, mass: 0.8},
  });
  const canZoom = interpolate(punchScale, [0, 1], [1.0, 1.14]);
  const canY = interpolate(frame, [162, 334], [0, -40], kep);

  // Thước đo neon thẳng đứng vẽ từ đáy (frame 176 "lớp cát dày" -> 218)
  const rulerProgress = interpolate(frame, [176, 218], [0, 1], {
    ...kep,
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const rulerHeight = rulerProgress * 540; // 540px đại diện cho gần 1 mét địa tầng

  // Bộ số đếm nhảy vọt từ 0.0m lên 0.9m
  const meterVal = interpolate(frame, [176, 218], [0, 0.9], kep).toFixed(1);

  // Nhãn text: 'LỚP PHÙ SA ĐỌNG LẠI' xuất hiện nảy nhẹ tại frame 213
  const nhanSpring = spring({
    frame: frame - 213,
    fps,
    config: {damping: 12, stiffness: 160},
  });

  // Chồng 5 lốp xe (tach_chong_lop) rơi xếp chồng / trượt vào màn hình (từ frame 267 "với năm chiếc lốp xe")
  const stackSpring = spring({
    frame: frame - 267,
    fps,
    config: {damping: 14, stiffness: 100},
  });
  const stackY = interpolate(stackSpring, [0, 1], [300, 0]);
  const stackOpacity = interpolate(stackSpring, [0, 0.2], [0, 1], kep);

  // Tiêu đề chốt: 'CHIỀU CAO ~ 1 MÉT' sáng bừng tại frame 298
  const tieuDeSpring = spring({
    frame: frame - 298,
    fps,
    config: {damping: 13, stiffness: 140},
  });
  const tieuDeScale = interpolate(tieuDeSpring, [0, 1], [0.85, 1]);
  const tieuDeGlow = interpolate(frame, [298, 315, 334], [0, 25, 12], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#0c0f12', fontFamily: FONT, overflow: 'hidden'}}>
      {/* ---------------- SCENE 1: CON ĐẬP & MẶT SAU NỀN CÁT (0 - 162) ---------------- */}
      {frame < 165 && (
        <Interactive.Div
          name="Nhóm cảnh 1 đập lốp xe"
          from={0}
          durationInFrames={165}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: frame >= 162 ? interpolate(frame, [162, 165], [1, 0], kep) : 1,
          }}
        >
          {/* Nền cảnh đập lốp xe với chuyển động camera lia */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              transform: `scale(${zoomBg}) translate(${panBgX}px, ${panBgY}px)`,
              transformOrigin: '50% 60%',
            }}
          >
            <AnhNen anh={bg_lop_xe} tu={1} den={1.06} toi={0.12} />
          </div>

          {/* Lớp lốp xe tiền cảnh trượt Parallax hé lộ phía sau */}
          <Interactive.Div
            name="Lốp xe cắt ngang Parallax"
            from={0}
            durationInFrames={162}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              transform: `translate(${lopChanX}px, ${lopChanY}px) scale(1.35)`,
              zIndex: 10,
              filter: 'drop-shadow(0 20px 30px rgba(0,0,0,0.7))',
            }}
          >
            <Img
              src={src(tach_lop_chan)}
              style={{
                width: 700,
                height: 366,
                objectFit: 'contain',
              }}
            />
          </Interactive.Div>

          {/* Dải sáng ban mai quét qua bề mặt đất phù sa đọng */}
          {lightOpacity > 0 && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: lightSweepX,
                width: 480,
                opacity: lightOpacity,
                transform: 'skewX(-26deg)',
                background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,245,210,0.45) 50%, rgba(255,255,255,0) 100%)',
                pointerEvents: 'none',
                mixBlendMode: 'screen',
                zIndex: 8,
              }}
            />
          )}
        </Interactive.Div>
      )}

      {/* ---------------- SCENE 2: ĐỊA TẦNG PHÙ SA & THƯỚC ĐO & 5 LỐP XE (162 - 334) ---------------- */}
      {frame >= 162 && (
        <Interactive.Div
          name="Nhóm cảnh 2 địa tầng phù sa"
          from={162}
          durationInFrames={172}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
          }}
        >
          {/* Cận cảnh mặt cắt lớp cát bồi tụ */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              transform: `scale(${canZoom}) translateY(${canY}px)`,
              transformOrigin: '40% 60%',
            }}
          >
            <AnhNen anh={can_lop_cat} tu={1} den={1.05} toi={0.15} />
          </div>

          {/* Vùng tối nhẹ bên phải để tôn rõ đồ hoạ so sánh */}
          <div
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              bottom: 0,
              width: 1100,
              background: 'linear-gradient(90deg, rgba(8,12,18,0) 0%, rgba(8,12,18,0.72) 40%, rgba(8,12,18,0.88) 100%)',
              pointerEvents: 'none',
            }}
          />

          {/* THƯỚC ĐO ĐỒ HOẠ NEON VÀNG VÀ CHỈ SỐ ĐO */}
          {frame >= 176 && (
            <Interactive.Div
              name="Thước đo địa tầng neon"
              from={176}
              durationInFrames={158}
              style={{
                position: 'absolute',
                left: 680,
                top: 310,
                width: 320,
                height: 600,
                zIndex: 20,
              }}
            >
              {/* Trục thước dọc vẽ từ đáy lên */}
              <div
                style={{
                  position: 'absolute',
                  left: 30,
                  bottom: 50,
                  width: 8,
                  height: rulerHeight,
                  backgroundColor: VANG,
                  boxShadow: `0 0 16px ${VANG}, 0 0 32px rgba(255,215,0,0.5)`,
                  borderRadius: 4,
                }}
              >
                {/* Vạch chia độ trên thước */}
                {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
                  const yPos = pct * 540;
                  if (yPos > rulerHeight) return null;
                  const isMain = pct === 0 || pct === 1;
                  return (
                    <div
                      key={idx}
                      style={{
                        position: 'absolute',
                        bottom: yPos,
                        left: -12,
                        width: isMain ? 32 : 18,
                        height: isMain ? 4 : 2,
                        backgroundColor: '#ffffff',
                        boxShadow: '0 0 8px #ffffff',
                      }}
                    />
                  );
                })}
              </div>

              {/* Hộp số đếm thời gian thực: '0.0m' -> '0.9m' */}
              <div
                style={{
                  position: 'absolute',
                  left: 65,
                  bottom: Math.max(50, rulerHeight + 15),
                  display: 'flex',
                  alignItems: 'baseline',
                  background: 'rgba(10, 16, 26, 0.88)',
                  padding: '8px 24px',
                  borderRadius: 12,
                  border: `2px solid ${VANG}`,
                  boxShadow: `0 8px 30px rgba(0,0,0,0.6), 0 0 20px ${VANG}44`,
                }}
              >
                <span
                  style={{
                    color: VANG,
                    fontSize: 72,
                    fontWeight: 900,
                    letterSpacing: -1,
                    textShadow: `0 0 15px ${VANG}`,
                  }}
                >
                  {meterVal}
                </span>
                <span
                  style={{
                    color: '#ffffff',
                    fontSize: 44,
                    fontWeight: 800,
                    marginLeft: 6,
                  }}
                >
                  m
                </span>
              </div>

              {/* Nhãn text: 'LỚP PHÙ SA ĐỌNG LẠI' */}
              {frame >= 213 && (
                <div
                  style={{
                    position: 'absolute',
                    left: 65,
                    bottom: Math.max(0, rulerHeight - 75),
                    transform: `scale(${nhanSpring})`,
                    transformOrigin: 'left center',
                    opacity: nhanSpring,
                  }}
                >
                  <div
                    style={{
                      background: 'rgba(235, 185, 30, 0.18)',
                      borderLeft: `6px solid ${VANG}`,
                      padding: '10px 22px',
                      borderRadius: '0 8px 8px 0',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    <div
                      style={{
                        color: '#ffffff',
                        fontSize: 34,
                        fontWeight: 800,
                        letterSpacing: 2,
                        textTransform: 'uppercase',
                        textShadow: '0 2px 10px rgba(0,0,0,0.8)',
                      }}
                    >
                      {nhan_phu_sa}
                    </div>
                  </div>
                </div>
              )}
            </Interactive.Div>
          )}

          {/* ĐỐI TƯỢNG SO SÁNH: 5 CHIẾC LỐP XE XẾP CHỒNG (tach_chong_lop) */}
          {frame >= 267 && (
            <Interactive.Div
              name="Chồng 5 lốp xe so sánh"
              from={267}
              durationInFrames={67}
              style={{
                position: 'absolute',
                left: 1160,
                bottom: 85,
                transform: `translateY(${stackY}px)`,
                opacity: stackOpacity,
                zIndex: 22,
                filter: 'drop-shadow(0 25px 40px rgba(0,0,0,0.8))',
              }}
            >
              <Img
                src={src(tach_chong_lop)}
                style={{
                  width: 500,
                  height: 660,
                  objectFit: 'contain',
                }}
              />

              {/* Đường gióng ngang từ đỉnh lớp cát sang đỉnh 5 lốp xe */}
              <div
                style={{
                  position: 'absolute',
                  top: 95,
                  left: -440,
                  width: 440,
                  height: 3,
                  borderTop: `3px dashed ${VANG}`,
                  opacity: 0.85,
                  filter: `drop-shadow(0 0 6px ${VANG})`,
                }}
              />
            </Interactive.Div>
          )}

          {/* DÒNG TEXT TIÊU ĐỀ CHỐT TRÊN CÙNG: CHIỀU CAO ~ 1 MÉT */}
          {frame >= 298 && (
            <Interactive.Div
              name="Tiêu đề chốt chiều cao"
              from={298}
              durationInFrames={36}
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                top: 90,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                transform: `scale(${tieuDeScale})`,
                zIndex: 30,
              }}
            >
              <div
                style={{
                  background: 'rgba(12, 18, 28, 0.85)',
                  border: `3px solid ${VANG}`,
                  borderRadius: 18,
                  padding: '16px 54px',
                  boxShadow: `0 12px 40px rgba(0,0,0,0.8), 0 0 ${tieuDeGlow}px ${VANG}88`,
                  backdropFilter: 'blur(12px)',
                }}
              >
                <span
                  style={{
                    color: VANG,
                    fontSize: 74,
                    fontWeight: 900,
                    letterSpacing: 3,
                    textTransform: 'uppercase',
                    textShadow: `0 0 20px ${VANG}`,
                  }}
                >
                  {nhan_chieu_cao}
                </span>
              </div>
            </Interactive.Div>
          )}
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};
