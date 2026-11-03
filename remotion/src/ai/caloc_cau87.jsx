import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG} from './thu_vien.jsx';

export const schema = z.object({
  nenSuoi: z.string().describe('Hình nền mặt cắt suối'),
  anhDapTran: z.string().describe('Ảnh tách nền đập tràn'),
  anhCaMutDa: z.string().describe('Ảnh tách nền cá mút đá'),
  anhCaBanDia: z.string().describe('Ảnh tách nền cá bản địa'),
  tieuDePhacThao: z.string().describe('Tiêu đề phác thảo kỹ thuật'),
  nhanDoCao: z.string().describe('Nhãn đo đạc chênh lệch bậc tràn'),
  nhanChanCaMutDa: z.string().describe('Nhãn ngăn cá mút đá'),
  nhanCaBanDiaNhay: z.string().describe('Nhãn cá bản địa vượt đập'),
  nhanCuaDan: z.string().describe('Nhãn cửa dẫn riêng biệt'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Smooth camera pan revealing the fishway flume on the right (frames 335 -> 396)
  const panX = interpolate(frame, [335, 385], [0, -260], kep);

  // 1. Concrete Dam Animation (appears frame 56, firmly placed by frame 85)
  const damSpring = spring({
    frame: frame - 56,
    fps,
    config: {damping: 14, stiffness: 85},
  });
  const damY = interpolate(damSpring, [0, 1], [-260, 0]);
  const damOpacity = interpolate(frame, [56, 68], [0, 1], kep);

  // 2. Blueprint overlay opacity (frames 19 -> 68)
  const sketchOpacity = interpolate(
    frame,
    [19, 30, 52, 68],
    [0, 0.95, 0.95, 0],
    kep
  );

  // 3. Measurement Callout Opacity (frames 115 -> 170)
  const measureOpacity = interpolate(
    frame,
    [115, 125, 162, 170],
    [0, 1, 1, 0],
    kep
  );

  // 4. Sea Lamprey Choreography (frames 170 -> 256)
  // Phase 1 (170-198): Swims up from downstream toward weir face
  // Phase 2 (198-222): Clings to crest face trying to climb
  // Phase 3 (222-254): Sucker slips, washed downstream tumbling in whitewater!
  let lampreyX = 1420;
  let lampreyY = 720;
  let lampreyRot = -22;

  if (frame < 198) {
    const p1 = interpolate(frame, [170, 198], [0, 1], {
      ...kep,
      easing: Easing.bezier(0.2, 0.8, 0.4, 1),
    });
    lampreyX = interpolate(p1, [0, 1], [1420, 980]);
    lampreyY = interpolate(p1, [0, 1], [720, 530]);
    lampreyRot = interpolate(p1, [0, 1], [-20, -38]) + Math.sin(frame * 0.5) * 3;
  } else if (frame < 222) {
    const p2 = interpolate(frame, [198, 222], [0, 1], kep);
    lampreyX = interpolate(p2, [0, 1], [980, 890]);
    lampreyY = interpolate(p2, [0, 1], [530, 475]);
    lampreyRot = -42 + Math.sin(frame * 1.2) * 5; // Struggling to latch onto wet crest
  } else {
    // Sucker slips! Tumbling backwards downstream
    const p3 = interpolate(frame, [222, 252], [0, 1], {
      ...kep,
      easing: Easing.bezier(0.35, 0.1, 0.25, 1),
    });
    lampreyX = interpolate(p3, [0, 1], [890, 1280]);
    lampreyY = interpolate(p3, [0, 1], [475, 680]);
    lampreyRot = interpolate(p3, [0, 1], [-42, 28]); // Twisting & tumbling
  }

  const lampreyOpacity = interpolate(
    frame,
    [170, 178, 248, 256],
    [0, 1, 1, 0],
    kep
  );

  // 5. Native Trout Leap Choreography (frames 256 -> 336)
  // Horizontal flip ensures fish head points upstream (left).
  // Fish leaps from downstream (x: 1260, y: 720), arches over crest (x: 820, y: 280),
  // and dives safely into upstream pool (x: 460, y: 530).
  const jumpProgress = interpolate(frame, [264, 324], [0, 1], kep);
  const troutX = interpolate(jumpProgress, [0, 0.5, 1], [1280, 820, 440]);
  const troutY = interpolate(
    jumpProgress,
    [0, 0.45, 1],
    [720, 260, 520],
    {
      easing: Easing.bezier(0.18, 0.85, 0.35, 1),
    }
  );
  // Rotation for flipped fish: +45 deg (snout up-left), 0 deg (crest), -24 deg (diving down-left)
  const troutRot = interpolate(
    jumpProgress,
    [0, 0.25, 0.5, 0.8, 1],
    [48, 35, 5, -20, -30]
  );
  const troutOpacity = interpolate(
    frame,
    [258, 266, 324, 332],
    [0, 1, 1, 0],
    kep
  );

  // 6. Fishway Swimming Animation (frames 335 -> 396)
  const flumeFishP = interpolate(frame, [338, 396], [0, 1], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#0a1726', overflow: 'hidden'}}>
      {/* 1. Camera Pan Canvas */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '2400px',
          height: '1080px',
          transform: `translateX(${panX}px)`,
        }}
      >
        {/* Full stream cross-section photographic background */}
        <div style={{position: 'absolute', left: 0, top: 0, width: '2400px', height: '1080px', overflow: 'hidden'}}>
          <Img
            src={src(props.nenSuoi)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${interpolate(frame, [0, 396], [1.0, 1.05], kep)})`,
              transformOrigin: '50% 50%',
            }}
          />
        </div>

        {/* 2. Concrete Weir Dam */}
        <Interactive.Div
          name="Đập tràn bê tông"
          from={56}
          durationInFrames={340}
          style={{
            position: 'absolute',
            left: 620,
            top: 450 + damY,
            opacity: damOpacity,
            zIndex: 10,
          }}
        >
          <Img
            src={src(props.anhDapTran)}
            style={{
              width: '760px',
              height: 'auto',
              filter: 'drop-shadow(0 20px 28px rgba(0,0,0,0.75))',
            }}
          />
        </Interactive.Div>

        {/* 3. Blueprint Engineering Overlay (frames 19 -> 68) */}
        {frame >= 19 && frame <= 68 && (
          <Interactive.Div
            name="Phác thảo kỹ thuật màu xanh lơ"
            from={19}
            durationInFrames={49}
            style={{
              position: 'absolute',
              left: 620,
              top: 420,
              width: '760px',
              height: '350px',
              opacity: sketchOpacity,
              zIndex: 15,
              pointerEvents: 'none',
            }}
          >
            <svg width="760" height="350" viewBox="0 0 760 350">
              <defs>
                <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
                  <path d="M 28 0 L 0 0 0 28" fill="none" stroke="rgba(0,220,255,0.35)" strokeWidth="1" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
              <polygon
                points="40,310 160,35 480,35 720,310"
                fill="rgba(0,180,255,0.2)"
                stroke="#00f0ff"
                strokeWidth="4"
                strokeDasharray="10 6"
              />
              <line x1="20" y1="35" x2="740" y2="35" stroke="#00f0ff" strokeWidth="2.5" strokeDasharray="5 5" />
              <text x="380" y="28" fill="#00f0ff" fontSize="28" fontFamily={FONT} textAnchor="middle" fontWeight="bold">
                {props.tieuDePhacThao}
              </text>
            </svg>
          </Interactive.Div>
        )}

        {/* 4. Measurement Indicator: 45-50 cm (frames 115 -> 170) */}
        {frame >= 115 && frame <= 170 && (
          <Interactive.Div
            name="Đo đạc chênh lệch độ cao"
            from={115}
            durationInFrames={55}
            style={{
              position: 'absolute',
              left: 1060,
              top: 420,
              opacity: measureOpacity,
              zIndex: 25,
            }}
          >
            <div style={{display: 'flex', alignItems: 'center', gap: '22px'}}>
              {/* Technical dimension bracket */}
              <svg width="60" height="240" viewBox="0 0 60 240" style={{overflow: 'visible'}}>
                <line x1="30" y1="12" x2="30" y2="216" stroke="#FFE600" strokeWidth="5" strokeDasharray="6 4" />
                <line x1="10" y1="12" x2="50" y2="12" stroke="#FFE600" strokeWidth="5" />
                <line x1="10" y1="216" x2="50" y2="216" stroke="#FFE600" strokeWidth="5" />
                <polygon points="30,12 21,34 39,34" fill="#FFE600" />
                <polygon points="30,216 21,194 39,194" fill="#FFE600" />
              </svg>

              {/* High-visibility info card */}
              <div
                style={{
                  background: 'rgba(5, 20, 36, 0.94)',
                  borderLeft: '7px solid #FFE600',
                  borderRadius: '10px',
                  padding: '16px 28px',
                  boxShadow: '0 12px 32px rgba(0,0,0,0.75)',
                  backdropFilter: 'blur(10px)',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: '58px',
                    fontWeight: 900,
                    color: '#FFE600',
                    lineHeight: 1.1,
                    letterSpacing: '1px',
                    textShadow: '0 4px 16px rgba(0,0,0,0.8)',
                  }}
                >
                  45 – 50 cm
                </div>
                <div
                  style={{
                    marginTop: '8px',
                    fontFamily: FONT,
                    fontSize: '32px',
                    fontWeight: 700,
                    color: '#FFFFFF',
                    letterSpacing: '0.5px',
                  }}
                >
                  {props.nhanDoCao}
                </div>
              </div>
            </div>
          </Interactive.Div>
        )}

        {/* 5. Sea Lamprey Climbing and Tumbling Downstream (frames 170 -> 256) */}
        {frame >= 170 && frame <= 256 && (
          <Interactive.Div
            name="Cá mút đá trườn và trượt ngã"
            from={170}
            durationInFrames={86}
            style={{
              position: 'absolute',
              left: lampreyX,
              top: lampreyY,
              transform: `rotate(${lampreyRot}deg)`,
              opacity: lampreyOpacity,
              zIndex: 22,
            }}
          >
            <Img
              src={src(props.anhCaMutDa)}
              style={{
                width: '520px',
                height: 'auto',
                filter: 'drop-shadow(0 16px 24px rgba(0,0,0,0.85))',
              }}
            />

            {/* Whitewater churn & bubbles when slipping backwards */}
            {frame >= 222 && (
              <div
                style={{
                  position: 'absolute',
                  left: '40px',
                  top: '10px',
                  width: '280px',
                  height: '110px',
                  background: 'radial-gradient(ellipse at center, rgba(255,255,255,0.7) 0%, rgba(180,230,255,0.4) 50%, rgba(255,255,255,0) 80%)',
                  borderRadius: '50%',
                  filter: 'blur(6px)',
                  pointerEvents: 'none',
                }}
              />
            )}
          </Interactive.Div>
        )}

        {/* Warning Callout for Lamprey Slipping (frames 216 -> 254) */}
        {frame >= 216 && frame <= 254 && (
          <Interactive.Div
            name="Nhãn cá mút đá bị chặn"
            from={216}
            durationInFrames={39}
            style={{
              position: 'absolute',
              left: 820,
              top: 310,
              zIndex: 35,
              opacity: interpolate(frame, [216, 224, 246, 254], [0, 1, 1, 0], kep),
            }}
          >
            <div
              style={{
                background: 'linear-gradient(135deg, rgba(215, 25, 25, 0.95) 0%, rgba(145, 10, 10, 0.95) 100%)',
                border: '3px solid #FFE600',
                borderRadius: '12px',
                padding: '14px 34px',
                color: '#FFFFFF',
                fontFamily: FONT,
                fontSize: '56px',
                fontWeight: 900,
                boxShadow: '0 12px 35px rgba(0,0,0,0.85), 0 0 24px rgba(255,30,30,0.5)',
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              {props.nhanChanCaMutDa}
            </div>
            {/* Directional slip arrow pointing down the spillway */}
            <svg width="240" height="110" style={{overflow: 'visible', position: 'absolute', left: '160px', top: '104px'}}>
              <path d="M 20,10 Q 80,30 150,75" fill="none" stroke="#FFE600" strokeWidth="6" strokeDasharray="10 6" />
              <polygon points="150,75 130,62 144,52" fill="#FFE600" />
            </svg>
          </Interactive.Div>
        )}

        {/* 6. Native Trout Leap Over Weir (frames 256 -> 336) */}
        {frame >= 256 && frame <= 336 && (
          <Interactive.Div
            name="Cá hồi bản địa nhảy vượt đập"
            from={256}
            durationInFrames={80}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              zIndex: 30,
            }}
          >
            {/* Leap trajectory guide arc */}
            <svg width="1800" height="1080" style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
              <path
                d="M 1280,720 Q 820,140 440,520"
                fill="none"
                stroke="rgba(0, 240, 255, 0.75)"
                strokeWidth="5"
                strokeDasharray="14 10"
              />
            </svg>

            {/* Fish container with trajectory rotation */}
            <div
              style={{
                position: 'absolute',
                left: troutX,
                top: troutY,
                transform: `rotate(${troutRot}deg)`,
                opacity: troutOpacity,
                transformOrigin: 'center center',
              }}
            >
              {/* scaleX(-1) correctly points the fish head upstream (left) */}
              <Img
                src={src(props.anhCaBanDia)}
                style={{
                  width: '350px',
                  height: 'auto',
                  transform: 'scaleX(-1)',
                  filter: 'drop-shadow(0 16px 26px rgba(0,0,0,0.7))',
                }}
              />
            </div>
          </Interactive.Div>
        )}

        {/* 7. Realistic Engineered Fishway Flume (frames 335 -> 396) */}
        {frame >= 335 && (
          <Interactive.Div
            name="Máng cá cửa dẫn riêng biệt"
            from={335}
            durationInFrames={61}
            style={{
              position: 'absolute',
              left: 1260,
              top: 480,
              zIndex: 20,
            }}
          >
            {/* Fishway Structure Container */}
            <div
              style={{
                width: '620px',
                height: '280px',
                position: 'relative',
                borderRadius: '10px',
                overflow: 'hidden',
                boxShadow: '0 16px 40px rgba(0,0,0,0.8)',
                border: '3px solid #38bdf8',
                background: 'rgba(8, 24, 42, 0.92)',
              }}
            >
              {/* Concrete top curb */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  width: '100%',
                  height: '22px',
                  background: 'linear-gradient(180deg, #64748b 0%, #334155 100%)',
                  borderBottom: '2px solid #94a3b8',
                }}
              />

              {/* Flowing water channel */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: '22px',
                  width: '100%',
                  height: '232px',
                  background: 'linear-gradient(90deg, rgba(14,116,144,0.7) 0%, rgba(2,132,199,0.55) 50%, rgba(14,116,144,0.7) 100%)',
                }}
              />

              {/* Vertical baffles (resting slots) */}
              {[120, 240, 360, 480].map((bx, i) => (
                <div
                  key={i}
                  style={{
                    position: 'absolute',
                    left: `${bx}px`,
                    top: i % 2 === 0 ? '22px' : '90px',
                    width: '14px',
                    height: '164px',
                    background: 'linear-gradient(180deg, #475569 0%, #1e293b 100%)',
                    borderRadius: '4px',
                    boxShadow: '0 4px 10px rgba(0,0,0,0.6)',
                  }}
                />
              ))}

              {/* Entrance Specialized Filter Grating (Blocks Lampreys) */}
              <div
                style={{
                  position: 'absolute',
                  right: '16px',
                  top: '26px',
                  width: '70px',
                  height: '220px',
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '2px solid #38bdf8',
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-evenly',
                  padding: '4px 0',
                }}
              >
                {Array.from({length: 5}).map((_, idx) => (
                  <div
                    key={idx}
                    style={{
                      width: '4px',
                      height: '100%',
                      background: '#7dd3fc',
                      borderRadius: '2px',
                      opacity: 0.85,
                    }}
                  />
                ))}
              </div>

              {/* Flow indicator arrows */}
              <div
                style={{
                  position: 'absolute',
                  left: '20px',
                  bottom: '36px',
                  display: 'flex',
                  gap: '120px',
                  opacity: 0.6,
                }}
              >
                {[0, 1, 2].map((k) => (
                  <svg key={k} width="40" height="20" viewBox="0 0 40 20">
                    <line x1="35" y1="10" x2="5" y2="10" stroke="#7dd3fc" strokeWidth="3" />
                    <polyline points="15,4 5,10 15,16" fill="none" stroke="#7dd3fc" strokeWidth="3" />
                  </svg>
                ))}
              </div>

              {/* Concrete bottom base */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  bottom: 0,
                  width: '100%',
                  height: '26px',
                  background: 'linear-gradient(180deg, #334155 0%, #0f172a 100%)',
                  borderTop: '2px solid #475569',
                }}
              />
            </div>

            {/* School of Native Fish swimming through the fishway flume */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: '620px',
                height: '280px',
                pointerEvents: 'none',
              }}
            >
              {/* Fish 1: Lead fish heading upstream (swimming right to left) */}
              <div
                style={{
                  position: 'absolute',
                  left: interpolate(flumeFishP, [0, 1], [520, 60]),
                  top: 75 + Math.sin(frame * 0.3) * 6,
                }}
              >
                <Img
                  src={src(props.anhCaBanDia)}
                  style={{
                    width: '140px',
                    height: 'auto',
                    transform: 'scaleX(-1)',
                    filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.6))',
                  }}
                />
              </div>

              {/* Fish 2: Follower fish */}
              <div
                style={{
                  position: 'absolute',
                  left: interpolate(flumeFishP, [0, 1], [620, 180]),
                  top: 135 + Math.cos(frame * 0.35) * 5,
                }}
              >
                <Img
                  src={src(props.anhCaBanDia)}
                  style={{
                    width: '110px',
                    height: 'auto',
                    transform: 'scaleX(-1)',
                    filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.6))',
                  }}
                />
              </div>

              {/* Fish 3: Smallest trailing fish */}
              <div
                style={{
                  position: 'absolute',
                  left: interpolate(flumeFishP, [0, 1], [700, 290]),
                  top: 95 + Math.sin(frame * 0.4) * 4,
                }}
              >
                <Img
                  src={src(props.anhCaBanDia)}
                  style={{
                    width: '85px',
                    height: 'auto',
                    transform: 'scaleX(-1)',
                    filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.6))',
                  }}
                />
              </div>
            </div>
          </Interactive.Div>
        )}
      </div>

      {/* 8. Top-level Callout Badges */}
      {/* Badge: Native Fish Leaping */}
      {frame >= 260 && frame <= 335 && (
        <Interactive.Div
          name="Nhãn cá bản địa vượt bậc"
          from={260}
          durationInFrames={75}
          style={{
            position: 'absolute',
            left: 200,
            top: 100,
            zIndex: 40,
            opacity: interpolate(frame, [260, 270, 325, 335], [0, 1, 1, 0], kep),
          }}
        >
          <div
            style={{
              padding: '16px 40px',
              background: 'rgba(4, 20, 38, 0.94)',
              border: '3px solid #00F0FF',
              borderRadius: '14px',
              color: '#FFFFFF',
              fontFamily: FONT,
              fontSize: '56px',
              fontWeight: 900,
              boxShadow: '0 12px 35px rgba(0, 240, 255, 0.35), 0 8px 24px rgba(0,0,0,0.8)',
              letterSpacing: '1px',
            }}
          >
            {props.nhanCaBanDiaNhay}
          </div>
        </Interactive.Div>
      )}

      {/* Badge: Fishway Bypass Channel */}
      {frame >= 338 && (
        <Interactive.Div
          name="Nhãn lối đi riêng"
          from={338}
          durationInFrames={58}
          style={{
            position: 'absolute',
            left: 1000,
            top: 180,
            zIndex: 40,
            opacity: interpolate(frame, [338, 348], [0, 1], kep),
          }}
        >
          <div
            style={{
              padding: '16px 36px',
              background: 'rgba(4, 20, 38, 0.95)',
              border: '3px solid #FFE600',
              borderRadius: '14px',
              boxShadow: '0 14px 35px rgba(0,0,0,0.85)',
            }}
          >
            <div
              style={{
                color: '#FFE600',
                fontFamily: FONT,
                fontSize: '56px',
                fontWeight: 900,
                letterSpacing: '1px',
              }}
            >
              {props.nhanCuaDan}
            </div>
            <div
              style={{
                marginTop: '6px',
                color: '#E0F2FE',
                fontFamily: FONT,
                fontSize: '28px',
                fontWeight: 600,
              }}
            >
              Máng dẫn có lưới lọc – Cá bản địa thoải mái qua lại
            </div>
          </div>
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};
