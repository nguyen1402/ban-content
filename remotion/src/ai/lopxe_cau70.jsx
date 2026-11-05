import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, Nhan, MuiTen} from './thu_vien.jsx';

export const schema = z.object({
  anhPhuSa: z.string().describe('Hình ảnh đất phù sa'),
  anhDongChay: z.string().describe('Hình ảnh dòng chảy'),
  anhHienTruong: z.string().describe('Hình ảnh nền hiện trường'),
  anhQuanChuc: z.string().describe('Hình ảnh cắt hai quan chức'),
  nhanPhuSa: z.string().describe('Nhãn đồ họa phù sa'),
  nhanThanhCong: z.string().describe('Nhãn đồ họa giữ đất thành công'),
});

export const Canh = ({
  anhPhuSa,
  anhDongChay,
  anhHienTruong,
  anhQuanChuc,
  nhanPhuSa,
  nhanThanhCong,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Shot 1: 0.0s - 2.8s (frames 0 - 84)
  // Shot 2: 2.8s - 4.8s (frames 84 - 144)
  // Shot 3: 4.8s - 6.8s (frames 144 - 204)
  // Shot 4: 6.8s - 10.7s (frames 204 - 322)

  // 1.4s = frame 42 (Light sweep & label "PHÙ SA MÀU MỠ")
  const sweepProgress = interpolate(frame, [42, 65], [0, 1], {clamped: true});

  // Whip pan transition at 2.8s (frame 84)
  const whipPanX = interpolate(
    frame,
    [80, 84, 88],
    [0, -1920, 0],
    {clamped: true, easing: Easing.bezier(0.8, 0, 0.2, 1)}
  );

  // Red Arrow progression from frame 96 ("cuốn") to frame 130
  const arrowProgress = interpolate(frame, [96, 130], [0, 1], {clamped: true, easing: Easing.out(Easing.quad)});

  // Vignette / dark cold layer at frame 148 ("không bao giờ")
  const vignetteOpacity = interpolate(frame, [144, 155], [0, 0.65], kep);

  // Cross lines draw animation (frames 148 - 170)
  const crossProgress = interpolate(frame, [148, 170], [0, 1], kep);

  // Wipe transition for Shot 4 at 6.8s (frame 204 / "Các quan chức")
  const wipeProgress = interpolate(frame, [204, 222], [0, 100], {
    clamped: true,
    easing: Easing.bezier(0.25, 1, 0.5, 1),
  });

  // Punch-in camera scale at frame 292 ("rất hài lòng")
  const punchInSpring = spring({
    frame: frame - 292,
    fps,
    config: {damping: 14, stiffness: 120},
  });
  const shot4Scale = frame >= 292 ? 1 + 0.12 * punchInSpring : 1;

  // Tick mark scale in shot 4
  const tickSpring = spring({
    frame: frame - 297,
    fps,
    config: {damping: 12, stiffness: 180},
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
      {/* SHOT 1: PHÙ SA MÀU MỠ (0 to 84 frames) */}
      {frame < 88 && (
        <Interactive.Div
          name="Cảnh 1: Phù sa màu mỡ"
          from={0}
          durationInFrames={88}
          style={{
            position: 'absolute',
            width: 1920,
            height: 1080,
            transform: `translateX(${frame >= 80 ? whipPanX : 0}px)`,
          }}
        >
          <AnhNen anh={anhPhuSa} tu={1.0} den={1.12} goc="50% 50%" toi={0.1} />

          {/* Light sweep effect */}
          {frame >= 42 && (
            <div
              style={{
                position: 'absolute',
                top: -200,
                left: -200,
                width: 600,
                height: 1500,
                background: 'linear-gradient(90deg, transparent, rgba(255, 235, 170, 0.35), transparent)',
                transform: `rotate(25deg) translateX(${sweepProgress * 2200}px)`,
                pointerEvents: 'none',
              }}
            />
          )}

          {/* Label: PHÙ SA MÀU MỠ */}
          {frame >= 42 && (
            <Interactive.Div
              name="Nhãn Phù Sa"
              from={42}
              durationInFrames={46}
              style={{position: 'absolute', left: 240, top: 400}}
            >
              <Nhan chu={nhanPhuSa} dx={140} dy={-90} co={56} />
            </Interactive.Div>
          )}
        </Interactive.Div>
      )}

      {/* SHOT 2 & SHOT 3: DÒNG CHẢY CUỐN TRÔI & MẤT MÁT (80 to 204 frames) */}
      {frame >= 80 && frame < 204 && (
        <Interactive.Div
          name="Cảnh 2 & 3: Dòng chảy & Mất mát"
          from={80}
          durationInFrames={124}
          style={{
            position: 'absolute',
            width: 1920,
            height: 1080,
            transform: frame < 88 ? `translateX(${whipPanX + 1920}px)` : 'none',
          }}
        >
          <AnhNen anh={anhDongChay} tu={1.05} den={1.2} goc="60% 40%" toi={0.15} />

          {/* Graphic Red Arrow plunging down following the river current */}
          {frame >= 96 && frame < 150 && (
            <Interactive.Div
              name="Mũi tên cuốn trôi"
              from={96}
              durationInFrames={54}
              style={{
                position: 'absolute',
                left: 1100,
                top: 250,
                opacity: arrowProgress,
                transform: `scale(${arrowProgress})`,
              }}
            >
              <svg width="600" height="600" viewBox="0 0 600 600" style={{overflow: 'visible'}}>
                <defs>
                  <marker id="red-arrowhead" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto">
                    <polygon points="0 0, 10 5, 0 10" fill="#EF4444" />
                  </marker>
                </defs>
                <path
                  d="M 50 50 Q 250 150 450 450"
                  fill="none"
                  stroke="#EF4444"
                  strokeWidth="24"
                  strokeLinecap="round"
                  strokeDasharray="700"
                  strokeDashoffset={700 * (1 - arrowProgress)}
                  markerEnd="url(#red-arrowhead)"
                />
              </svg>
            </Interactive.Div>
          )}

          {/* SHOT 3: Dark cold vignette & Red Cross effect (144s / frame 144 to 204) */}
          {frame >= 144 && (
            <>
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'radial-gradient(circle, rgba(15, 23, 42, 0.2) 20%, rgba(15, 23, 42, 0.85) 100%)',
                  opacity: vignetteOpacity,
                  pointerEvents: 'none',
                }}
              />

              {/* Faded Red Cross Overlay */}
              {frame >= 148 && (
                <Interactive.Div
                  name="Dấu gạch chéo mất mát"
                  from={148}
                  durationInFrames={56}
                  style={{
                    position: 'absolute',
                    left: 660,
                    top: 240,
                    width: 600,
                    height: 600,
                    pointerEvents: 'none',
                  }}
                >
                  <svg width="600" height="600" viewBox="0 0 600 600">
                    <line
                      x1="100"
                      y1="100"
                      x2="500"
                      y2="500"
                      stroke="#DC2626"
                      strokeWidth="28"
                      strokeLinecap="round"
                      opacity={0.6}
                      strokeDasharray="600"
                      strokeDashoffset={600 * (1 - crossProgress)}
                    />
                    <line
                      x1="500"
                      y1="100"
                      x2="100"
                      y2="500"
                      stroke="#DC2626"
                      strokeWidth="28"
                      strokeLinecap="round"
                      opacity={0.6}
                      strokeDasharray="600"
                      strokeDashoffset={600 * (1 - crossProgress)}
                    />
                  </svg>
                </Interactive.Div>
              )}
            </>
          )}
        </Interactive.Div>
      )}

      {/* SHOT 4: QUAN CHỨC THỰC ĐỊA & THÀNH CÔNG (204 to 322 frames) */}
      {frame >= 204 && (
        <Interactive.Div
          name="Cảnh 4: Quan chức & Kiểm tra"
          from={204}
          durationInFrames={118}
          style={{
            position: 'absolute',
            inset: 0,
            clipPath: `polygon(0 0, ${wipeProgress}% 0, ${wipeProgress}% 100%, 0 100%)`,
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              transform: `scale(${shot4Scale})`,
              transformOrigin: '70% 40%',
            }}
          >
            {/* Background image: Riverbank field */}
            <AnhNen anh={anhHienTruong} tu={1.0} den={1.08} goc="50% 50%" toi={0.1} />

            {/* Cut-out experts inspecting sediment */}
            <Interactive.Div
              name="Quan chức cắt phông"
              from={204}
              durationInFrames={118}
              style={{
                position: 'absolute',
                right: 150,
                bottom: 0,
                height: 820,
              }}
            >
              <Img
                src={src(anhQuanChuc)}
                style={{
                  height: '100%',
                  width: 'auto',
                  filter: 'drop-shadow(0 15px 30px rgba(0,0,0,0.5))',
                  objectFit: 'contain',
                }}
              />
            </Interactive.Div>

            {/* Success Label + Green Checkmark at frame 297 */}
            {frame >= 292 && (
              <Interactive.Div
                name="Thành công Badge"
                from={292}
                durationInFrames={30}
                style={{
                  position: 'absolute',
                  left: 120,
                  top: 140,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 24,
                  backgroundColor: 'rgba(15, 23, 42, 0.85)',
                  padding: '24px 40px',
                  borderRadius: 20,
                  border: '3px solid #22C55E',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
                  transform: `scale(${tickSpring})`,
                }}
              >
                {/* Green Check Icon */}
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: '50%',
                    backgroundColor: '#22C55E',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FFF" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>

                <span
                  style={{
                    fontFamily: FONT,
                    fontWeight: 800,
                    fontSize: 56,
                    color: '#FFFFFF',
                    letterSpacing: '0.02em',
                  }}
                >
                  {nhanThanhCong}
                </span>
              </Interactive.Div>
            )}
          </div>
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};
