import React from 'react';
import { AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { src, kep, FONT, VANG, AnhNen, HienDan } from './thu_vien.jsx';

export const schema = z.object({
  suoiTuNhienPath: z.string().describe('Hình nền dòng suối tự nhiên'),
  reCayPath: z.string().describe('Hình cắt lớp rễ cây tiền cảnh'),
  datKhoNutNePath: z.string().describe('Hình nền đất khô nứt nẻ'),
  tuNghienTitle: z.string().describe('Tiêu đề phân đoạn tự nhiên'),
  cangThangTitle: z.string().describe('Tiêu đề phân đoạn căng thẳng'),
});

export const Canh = (props) => {
  const { suoiTuNhienPath, reCayPath, datKhoNutNePath, cangThangTitle } = props;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- Beat 1: Frame 4 -> 151 (Natural Stream & Parallax Root) ---
  // Frame 57: Roots parallax overlay enters smoothly
  const reCayOpacity = interpolate(frame, [57, 75], [0, 1], kep);
  const reCayY = interpolate(frame, [57, 400], [40, -60], kep);
  const reCayScale = interpolate(frame, [57, 400], [1.05, 1.15], kep);

  // --- Beat 3: Frame 151 (Whip-pan Transition to Document Card of Dry Cracked Earth) ---
  const transitionProgress = spring({
    frame: frame - 151,
    fps,
    config: { damping: 18, stiffness: 120, mass: 0.9 },
  });

  // Slide translation for whip-pan effect
  const cardSlideX = interpolate(transitionProgress, [0, 1], [1920, 0], kep);

  // Beat 4: Frame 253 (Punch-in zoom on dry cracks)
  const punchZoom = spring({
    frame: frame - 253,
    fps,
    config: { damping: 14, stiffness: 140, mass: 0.7 },
  });

  // Card scale combines initial card size with frame 253 punch-in zoom (+12%)
  const cardScale = interpolate(punchZoom, [0, 1], [1.0, 1.12], kep);

  // Tension accent border animation starting at beat 4
  const borderProgress = interpolate(frame, [253, 290], [0, 1], kep);

  return (
    <AbsoluteFill style={{ backgroundColor: '#0c140d', overflow: 'hidden' }}>
      {/* BASE LAYER: Smooth flowing natural stream background */}
      <Interactive.Div
        name="Lớp nền Dòng suối"
        from={0}
        durationInFrames={400}
        style={{ position: 'absolute', width: '100%', height: '100%', left: 0, top: 0 }}
      >
        <AnhNen anh={suoiTuNhienPath} tu={1.0} den={1.12} goc="50% 50%" toi={0.15} />
      </Interactive.Div>

      {/* FOREGROUND LAYER: Parallax Root System (Beat 2: frame 57) */}
      <Interactive.Div
        name="Tiền cảnh Rễ cây Parallax"
        from={57}
        durationInFrames={343}
        style={{
          position: 'absolute',
          right: -40,
          bottom: -50,
          width: 950,
          height: 580,
          opacity: reCayOpacity,
          transform: `translateY(${reCayY}px) scale(${reCayScale})`,
          transformOrigin: 'bottom right',
          zIndex: 10,
          filter: 'drop-shadow(0 20px 30px rgba(0, 0, 0, 0.6))',
        }}
      >
        <Img
          src={src(reCayPath)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
        />
      </Interactive.Div>

      {/* DOCUMENT CARD LAYER: Rigid Tension & Dry Cracked Soil (Beat 3 & 4: frame 151+) */}
      <Interactive.Div
        name="Thẻ tài liệu Đất khô nứt nẻ"
        from={151}
        durationInFrames={249}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translateX(${cardSlideX}px)`,
          zIndex: 20,
        }}
      >
        {/* Outer Card Frame with subtle shadow and border */}
        <div
          style={{
            position: 'absolute',
            left: 120,
            top: 90,
            width: 1680,
            height: 900,
            borderRadius: 24,
            overflow: 'hidden',
            boxShadow: '0 30px 80px rgba(0, 0, 0, 0.75)',
            border: '2px solid rgba(255, 255, 255, 0.15)',
            backgroundColor: '#1a1412',
            transform: `scale(${cardScale})`,
            transformOrigin: '50% 50%',
          }}
        >
          {/* Cracked earth standard background inside card */}
          <AnhNen anh={datKhoNutNePath} tu={1.0} den={1.06} goc="50% 50%" toi={0.2} />

          {/* Document overlay vignette framing */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              boxShadow: 'inset 0 0 100px rgba(0, 0, 0, 0.7)',
              pointerEvents: 'none',
            }}
          />

          {/* Punch-in focus accent ring / stress border highlighting tension */}
          <div
            style={{
              position: 'absolute',
              inset: 20,
              borderRadius: 16,
              border: `2px dashed ${VANG}`,
              opacity: borderProgress * 0.7,
              pointerEvents: 'none',
            }}
          />

          {/* Single short label — the only on-screen text besides numbers/names */}
          <HienDan vao={200} het={400}>
            <div
              style={{
                position: 'absolute',
                bottom: 60,
                left: 60,
                padding: '16px 36px',
                backgroundColor: 'rgba(25, 18, 15, 0.85)',
                backdropFilter: 'blur(12px)',
                borderLeft: `6px solid ${VANG}`,
                borderRadius: '4px',
                color: '#ffffff',
                fontFamily: FONT,
                fontSize: 42,
                fontWeight: 700,
                letterSpacing: '1.5px',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
              }}
            >
              {cangThangTitle}
            </div>
          </HienDan>
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
