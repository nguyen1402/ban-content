import React from 'react';
import { AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { src, kep, FONT, VANG, EM, AnhNen, SoDem } from './thu_vien.jsx';

export const schema = z.object({
  bgImage1: z.string().describe('Ảnh nền 1 - Bản đồ Florida'),
  bgImage2: z.string().describe('Ảnh nền 2 - Thợ lặn quân đội Mỹ'),
  yearText: z.string().describe('Văn bản năm'),
  counterUnit: z.string().describe('Đơn vị bộ đếm'),
});

export const Canh = (props) => {
  const { bgImage1, bgImage2, yearText, counterUnit } = props;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Word Timing Highlights & Beats:
  // 2007 - 2009 text: 0..87 (light sweep effect)
  // Transition to Diver photo: frame 87 (word "các") -> luot-qua (slide effect)
  // Punch-in frame 218 (word "biển")
  // Counter 0 to 72.000: frame 255 ("khoảng") to 294 ("lốp.")

  // Light sweep calculation for year text (frames 0 - 70)
  const sweepProgress = interpolate(frame, [10, 75], [-100, 200], kep);

  // Transition between map and diver photo at frame 87
  const slideProgress = spring({
    frame: frame - 87,
    fps,
    config: { damping: 18, stiffness: 120, mass: 0.8 },
  });
  const slideX = interpolate(slideProgress, [0, 1], [1920, 0], kep);

  // Punch-in zoom effect at frame 218 ("biển")
  const punchSpring = spring({
    frame: frame - 218,
    fps,
    config: { damping: 12, stiffness: 180 },
  });
  const punchScale = interpolate(punchSpring, [0, 1], [1, 1.25], kep);

  // Counter frame triggers: frame 255 ("khoảng") to frame 294 ("lốp.")
  const counterFrame = Math.max(0, frame - 255);

  return (
    <AbsoluteFill style={{ backgroundColor: '#03101e', fontFamily: FONT }}>
      {/* BACKGROUND 1: Bản đồ định vị Florida (frames 0 - 95) */}
      <Interactive.Div name="Bản đồ Florida" from={0} durationInFrames={95} style={{ position: 'absolute', width: '100%', height: '100%' }}>
        <AnhNen anh={src(bgImage1)} tu={1.0} den={1.12} goc="50% 50%" toi={0.2} />
        
        {/* Năm 2007 - 2009 với hiệu ứng Light Sweep */}
        <Interactive.Div
          name="Thẻ năm 2007 - 2009"
          from={10}
          durationInFrames={77}
          style={{
            position: 'absolute',
            left: 120,
            top: 120,
            padding: '20px 48px',
            borderRadius: 16,
            background: 'rgba(3, 16, 30, 0.75)',
            border: `3px solid ${VANG}`,
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            overflow: 'hidden',
          }}
        >
          <span
            style={{
              fontSize: 100,
              fontWeight: 900,
              color: '#FFFFFF',
              letterSpacing: 2,
              display: 'block',
              position: 'relative',
            }}
          >
            {yearText}
          </span>
          {/* Light Sweep Layer */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              background: `linear-gradient(120deg, transparent 0%, transparent 40%, rgba(255, 255, 255, 0.8) 50%, transparent 60%, transparent 100%)`,
              transform: `translateX(${sweepProgress}%)`,
              pointerEvents: 'none',
            }}
          />
        </Interactive.Div>
      </Interactive.Div>

      {/* BACKGROUND 2: Thợ lặn quân đội Mỹ dưới nước (chuyển cảnh lướt qua từ frame 87) */}
      <Interactive.Div
        name="Ảnh thợ lặn Mỹ"
        from={87}
        durationInFrames={226}
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          transform: `translateX(${frame < 87 ? 1920 : slideX}px)`,
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            transform: `scale(${punchScale})`,
            transformOrigin: '50% 60%',
          }}
        >
          <AnhNen anh={src(bgImage2)} tu={1.05} den={1.18} goc="50% 50%" toi={0.25} />
        </div>
      </Interactive.Div>

      {/* BỘ ĐẾM SỐ: Khoảng 72.000 chiếc lốp (từ frame 255) */}
      <Interactive.Div
        name="Bộ đếm 72.000 chiếc lốp"
        from={255}
        durationInFrames={58}
        style={{
          position: 'absolute',
          left: 100,
          top: 650,
          padding: '30px 60px',
          borderRadius: 24,
          background: 'rgba(5, 20, 38, 0.85)',
          border: '4px solid #38BDF8',
          boxShadow: '0 25px 50px rgba(0,0,0,0.8)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
          <SoDem so={72000} giay={1.3} co={120} don_vi="" />
          <span style={{ fontSize: 60, fontWeight: 800, color: '#38BDF8', marginLeft: 24 }}>
            {counterUnit}
          </span>
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
