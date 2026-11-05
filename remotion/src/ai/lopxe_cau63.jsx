import React from 'react';
import { AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { src, kep, FONT, VANG, EM, AnhNen, ChuNoi, Nhan, HienDan } from './thu_vien.jsx';

export const schema = z.object({
  nenSuoiNui: z.string().describe('Hình nền dòng suối và sườn đồi'),
  tachBunDo: z.string().describe('Cắt lớp bùn đỏ tràn qua'),
  canDapLopXe: z.string().describe('Cận cảnh đập lốp xe đang thi công'),
  nenThungLungArizona: z.string().describe('Hình nền thung lũng Arizona'),
  textChinh: z.string().describe('Chữ chính xuất hiện đoạn giữa'),
  textLichSu: z.string().describe('Thẻ thông tin giai đoạn lịch sử'),
  labelViTri: z.string().describe('Nhãn địa điểm thung lũng')
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Đảm bảo chỉ dùng đường dẫn cục bộ hợp lệ, tránh lỗi CancelledError khi tải URL ngoài
  const safeImg = (val, fallback) => (val && !val.startsWith('http') ? val : fallback);
  const nenSuoiNui = safeImg(props.nenSuoiNui, 'nhan_y/6fce4ddc2b1952.jpg');
  const tachBunDo = safeImg(props.tachBunDo, 'nhan_y/414e50332ee083.png');
  const canDapLopXe = safeImg(props.canDapLopXe, 'nhan_y/818dde32603e2d.jpg');
  const nenThungLungArizona = safeImg(props.nenThungLungArizona, 'nhan_y/75f73ad04759a9.jpg');
  const textChinh = props.textChinh || 'Đập Lốp Xe Đang Thi Công Bị Đe Dọa';
  const textLichSu = props.textLichSu || '1972 • THƯỜNG XUYÊN XẢY RA LŨ QUÉT';
  const labelViTri = props.labelViTri || 'Thung lũng Arizona';

  // Timing constants from prompt
  // "lũ bùn đất" @ ~15f (0.5s)
  // "lao thẳng vào" / cut to dam @ 122f (~4.07s)
  // "Ông John King" / cut to historical Arizona @ 208f (~6.95s)
  // "hung hãn" / punch-in @ 333f (11.1s)

  // Cut-out mud transition animation (starts around frame 15)
  const bunProgress = spring({
    frame: frame - 15,
    fps,
    config: { damping: 14, stiffness: 80 }
  });

  const bunX = interpolate(bunProgress, [0, 1], [-700, 250], kep);
  const bunY = interpolate(bunProgress, [0, 1], [600, 380], kep);
  const bunScale = interpolate(bunProgress, [0, 1], [0.8, 1.35], kep);
  const bunRotate = interpolate(bunProgress, [0, 1], [-20, 5], kep);

  // Transition "luot-qua" wipe effect around frame 122 (Shot 1 -> Shot 2)
  const luotQuaProgress = interpolate(frame, [118, 126], [100, -100], kep);

  // Punch-in effect on Shot 3 at frame 333 ("hung hãn")
  const punchInSpring = spring({
    frame: frame - 333,
    fps,
    config: { damping: 10, stiffness: 200 }
  });
  const shot3Scale = interpolate(punchInSpring, [0, 1], [1.0, 1.28], kep);
  const shot3X = interpolate(punchInSpring, [0, 1], [0, -60], kep);
  const shot3Y = interpolate(punchInSpring, [0, 1], [0, -30], kep);

  // Historical shadow overlay opacity
  const shadowOpacity = interpolate(frame, [208, 240], [0, 0.45], kep);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000', overflow: 'hidden' }}>
      
      {/* ================= SHOT 1: Dòng suối + Sườn đồi + Bùn tràn (Frames 0 -> 122) ================= */}
      {frame < 125 && (
        <Interactive.Div
          name="Phân cảnh 1: Suối đồi và Lũ bùn"
          from={0}
          durationInFrames={125}
          style={{ position: 'absolute', width: '100%', height: '100%' }}
        >
          {/* Nền suối đồi đẩy chậm */}
          <AnhNen anh={nenSuoiNui} tu={1.0} den={1.12} goc="50% 50%" toi={0.15} />

          {/* Cắt lớp bùn đỏ tràn qua từ frame 15 */}
          {frame >= 12 && (
            <Interactive.Div
              name="Cắt lớp bùn đỏ"
              from={12}
              durationInFrames={113}
              style={{
                position: 'absolute',
                left: bunX,
                top: bunY,
                transform: `scale(${bunScale}) rotate(${bunRotate}deg)`,
                transformOrigin: 'bottom left',
                filter: 'drop-shadow(10px 15px 25px rgba(0,0,0,0.6))',
                zIndex: 10
              }}
            >
              <Img src={src(tachBunDo)} style={{ width: 850, height: 'auto' }} />
            </Interactive.Div>
          )}

          {/* Tiêu đề dòng lũ */}
          <Interactive.Div
            name="Nhãn Dòng lũ bùn đất"
            from={15}
            durationInFrames={110}
            style={{ position: 'absolute', left: 100, top: 120, zIndex: 20 }}
          >
            <ChuNoi chu="LŨ BÙN ĐẤT ĐỎ" co={96} />
          </Interactive.Div>
        </Interactive.Div>
      )}

      {/* ================= SHOT 2: Cận cảnh đập lốp xe thi công dở (Frames 122 -> 208) ================= */}
      {frame >= 120 && frame < 210 && (
        <Interactive.Div
          name="Phân cảnh 2: Cận cảnh Đập lốp xe"
          from={120}
          durationInFrames={90}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            clipPath: frame < 128 ? `polygon(${100 + luotQuaProgress}% 0, 100% 0, 100% 100%, ${luotQuaProgress}% 100%)` : 'none',
            zIndex: 30
          }}
        >
          {/* Nền cận cảnh đập lốp xe */}
          <AnhNen anh={canDapLopXe} tu={1.05} den={1.18} goc="60% 40%" toi={0.2} />

          {/* Text chính: Đập lốp xe bị đe dọa */}
          <Interactive.Div
            name="Chữ chính Đập lốp xe bị đe dọa"
            from={130}
            durationInFrames={78}
            style={{ position: 'absolute', left: 100, top: 460, zIndex: 40 }}
          >
            <div
              style={{
                backgroundColor: 'rgba(15, 10, 5, 0.85)',
                padding: '24px 45px',
                borderRadius: '16px',
                borderLeft: `12px solid ${VANG}`,
                boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
              }}
            >
              <span
                style={{
                  fontFamily: FONT,
                  fontSize: 100,
                  fontWeight: 900,
                  color: '#FFFFFF',
                  textTransform: 'uppercase',
                  letterSpacing: '2px',
                  lineHeight: 1.1
                }}
              >
                {textChinh}
              </span>
            </div>
          </Interactive.Div>

          {/* Calling out specific feature */}
          <Interactive.Div
            name="Nhãn Thi công dở"
            from={145}
            durationInFrames={63}
            style={{ position: 'absolute', left: 1200, top: 350, zIndex: 40 }}
          >
            <Nhan chu="Đang thi công dở" dx={-120} dy={-80} co={56} />
          </Interactive.Div>
        </Interactive.Div>
      )}

      {/* ================= SHOT 3: Phong cách Tài liệu Lịch sử Arizona (Frames 208 -> 357) ================= */}
      {frame >= 205 && (
        <Interactive.Div
          name="Phân cảnh 3: Tư liệu Lịch sử Arizona"
          from={205}
          durationInFrames={152}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            transform: `scale(${shot3Scale}) translate(${shot3X}px, ${shot3Y}px)`,
            transformOrigin: '50% 50%',
            zIndex: 50
          }}
        >
          {/* Nền Thung lũng Arizona */}
          <AnhNen anh={nenThungLungArizona} tu={1.0} den={1.12} goc="40% 60%" toi={0.25} />

          {/* Lớp filter phong cách tài liệu lịch sử giữa thế kỷ 20 */}
          <Interactive.Div
            name="Bộ lọc tài liệu lịch sử"
            from={205}
            durationInFrames={152}
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(180, 130, 70, 0.18)',
              mixBlendMode: 'overlay',
              pointerEvents: 'none'
            }}
          />

          {/* Bóng người mờ từ phía sau (John King quan sát thung lũng) */}
          <Interactive.Div
            name="Bóng người quan sát (John King)"
            from={208}
            durationInFrames={149}
            style={{
              position: 'absolute',
              right: 80,
              bottom: -50,
              width: 550,
              height: 750,
              background: 'radial-gradient(ellipse at center, rgba(15,10,5,0.95) 0%, rgba(15,10,5,0) 70%)',
              opacity: shadowOpacity,
              borderRadius: '50%',
              transform: 'scaleX(0.7) rotate(-10deg)',
              filter: 'blur(35px)',
              pointerEvents: 'none'
            }}
          />

          {/* Thẻ ghi chép chứng nhân lịch sử */}
          <Interactive.Div
            name="Thẻ Nhân chứng John King"
            from={212}
            durationInFrames={145}
            style={{ position: 'absolute', left: 100, top: 120, zIndex: 60 }}
          >
            <div
              style={{
                backgroundColor: 'rgba(25, 20, 15, 0.9)',
                border: '2px solid rgba(230, 200, 120, 0.5)',
                padding: '20px 36px',
                borderRadius: '12px',
                display: 'inline-flex',
                flexDirection: 'column',
                gap: '6px'
              }}
            >
              <span style={{ fontFamily: FONT, fontSize: 32, color: VANG, fontWeight: 700, letterSpacing: '3px' }}>
                {textLichSu}
              </span>
              <span style={{ fontFamily: FONT, fontSize: 64, color: '#FFFFFF', fontWeight: 900 }}>
                Ông John King kể lại
              </span>
            </div>
          </Interactive.Div>

          {/* Label địa điểm thung lũng */}
          <Interactive.Div
            name="Nhãn Thung lũng Arizona"
            from={245}
            durationInFrames={112}
            style={{ position: 'absolute', left: 350, top: 780, zIndex: 60 }}
          >
            <Nhan chu={labelViTri} dx={140} dy={-60} co={56} />
          </Interactive.Div>

          {/* Text nhấn mạnh khi punch-in "hung hãn" */}
          {frame >= 330 && (
            <Interactive.Div
              name="Chữ nhấn mạnh Hung hãn"
              from={330}
              durationInFrames={27}
              style={{ position: 'absolute', right: 150, top: 420, zIndex: 70 }}
            >
              <div
                style={{
                  backgroundColor: EM,
                  color: '#FFF',
                  fontFamily: FONT,
                  fontSize: 90,
                  fontWeight: 900,
                  padding: '16px 40px',
                  borderRadius: '12px',
                  boxShadow: '0 15px 35px rgba(0,0,0,0.6)',
                  letterSpacing: '4px',
                  transform: 'rotate(-3deg)'
                }}
              >
                VÔ CÙNG HUNG HÃN
              </div>
            </Interactive.Div>
          )}
        </Interactive.Div>
      )}

      {/* Flash nhẹ khi chuyển cảnh punch-in cuối */}
      {frame >= 333 && frame <= 336 && (
        <Interactive.Div
          name="Chớp sáng punch-in"
          from={333}
          durationInFrames={4}
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: '#FFF',
            opacity: interpolate(frame, [333, 336], [0.35, 0], kep),
            pointerEvents: 'none',
            zIndex: 100
          }}
        />
      )}
    </AbsoluteFill>
  );
};
