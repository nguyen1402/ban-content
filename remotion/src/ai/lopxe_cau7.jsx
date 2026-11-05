import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  nenKhoCan: z.string().describe('Hình nền đất khô cằn'),
  tachReCayKho: z.string().describe('Hình rễ cây khô'),
  keyText: z.string().describe('Chữ chính trên màn hình'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  const {
    nenKhoCan = 'nhan_y/06f57debd56752.jpg',
    tachReCayKho = 'nhan_y/226f6fc387a583.png',
    keyText = 'Đất khô cằn',
  } = props || {};

  // --- 1. Transition: lush fertile sponge -> drying ash gray (frame 10 to 32) ---
  // Fertile moist ground & moss tint (prominent in early frames, transitioning through frame 18)
  const mossTintOpacity = interpolate(frame, [10, 32], [0.9, 0], kep);
  const moistDarkness = interpolate(frame, [10, 32], [0.75, 0], kep);
  const moistBlur = interpolate(frame, [10, 30], [3, 0], kep);
  const baseGrayscale = interpolate(frame, [12, 32], [0.0, 0.85], kep);
  const baseBrightness = interpolate(frame, [12, 32, 60], [0.88, 1.02, 1.12], kep);
  const baseContrast = interpolate(frame, [12, 32], [1.02, 1.12], kep);

  // Topsoil moist organic layer evaporates (frame 41 to 61)
  const moistLayerOpacity = interpolate(frame, [41, 61], [1, 0], kep);

  // --- 2. Cracks appear (frame 15 - 24) and spread across frame (frame 24 to 36) ---
  // Surface displacement along soil fractal noise (scale 0 to 12)
  const dispScale = interpolate(frame, [0, 14, 24, 36], [0, 0, 3.5, 12], kep);

  // Natural fissure blend mask: deepens actual ground cracks, spreading organically
  const crackBlendOpacity = interpolate(frame, [0, 14, 24, 36], [0, 0.15, 0.35, 0.65], kep);
  const crackMaskRadius = interpolate(frame, [14, 24, 36], [0, 15, 100], kep);

  // --- 3. Root sponge: lush mossy sponge -> drying ash gray -> shrivels & evaporates ---
  // Starts as a vibrant, hydrated, lush moss-covered root sponge (frame 0 to 10)
  const rootHue = interpolate(frame, [10, 32], [52, 0], kep);
  const rootSepia = interpolate(frame, [10, 32], [0.5, 0], kep);
  const rootSaturate = interpolate(frame, [10, 32], [2.8, 0.1], kep);
  const rootBrightness = interpolate(frame, [10, 32], [0.85, 1.08], kep);
  const rootContrast = interpolate(frame, [10, 32], [1.2, 1.05], kep);
  const rootGlowOpacity = interpolate(frame, [10, 28], [0.55, 0], kep);

  // Shrivel & evaporate (1.38s to 2.03s, frame 41 to 61)
  const rootOpacity = interpolate(frame, [41, 61], [1, 0], kep);
  const rootScale = interpolate(frame, [0, 10, 32, 41, 61], [1.06, 1.06, 1.0, 1.0, 0.85], {...kep, easing: Easing.in(Easing.cubic)});
  const rootBlur = interpolate(frame, [41, 61], [0, 22], kep);
  const rootTranslateY = interpolate(frame, [41, 61], [0, -32], kep);

  // Evaporating dust haze animation
  const dustOpacity = interpolate(frame, [41, 49, 58, 66], [0, 0.6, 0.35, 0], kep);
  const dustY = interpolate(frame, [41, 66], [0, -45], kep);
  const dustScale = interpolate(frame, [41, 66], [0.95, 1.25], kep);

  // --- 4. Key text smooth appearance (starts frame 24, slides in smoothly without glyph slicing) ---
  const textOpacity = interpolate(frame, [24, 34], [0, 1], kep);
  const textTranslateY = interpolate(frame, [24, 34], [16, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const textScale = interpolate(frame, [24, 34], [0.96, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const barScale = interpolate(frame, [28, 42], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', overflow: 'hidden'}}>
      {/* 1. Background scene with realistic soil cracking and moisture transition */}
      <Interactive.Div
        name="Nền cảnh quay"
        from={0}
        durationInFrames={90}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        {/* SVG filter for natural surface displacement */}
        <svg width="0" height="0" style={{position: 'absolute', pointerEvents: 'none'}}>
          <defs>
            <filter id="fissureDisplace" x="-10%" y="-10%" width="120%" height="120%">
              <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" result="noise" />
              <feDisplacementMap in="SourceGraphic" in2="noise" scale={dispScale} xChannelSelector="R" yChannelSelector="G" />
            </filter>
          </defs>
        </svg>

        {/* Base cracked earth with 40px bleed margin to prevent edge sampling artifacts */}
        <div
          style={{
            position: 'absolute',
            left: -40,
            top: -40,
            width: 2000,
            height: 1160,
            filter: dispScale > 0.5 ? 'url(#fissureDisplace)' : undefined,
          }}
        >
          <div
            style={{
              width: '100%',
              height: '100%',
              filter: `grayscale(${baseGrayscale}) brightness(${baseBrightness}) contrast(${baseContrast})`,
            }}
          >
            <AnhNen anh={src(nenKhoCan)} tu={1} den={1.06} goc="50% 50%" />
          </div>
        </div>

        {/* Moist fertile organic layer (green-moss & dark humus) */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: moistLayerOpacity,
            filter: moistBlur > 0.2 ? `blur(${moistBlur}px)` : undefined,
            pointerEvents: 'none',
          }}
        >
          {/* Dark peat & organic moisture */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              background: 'radial-gradient(ellipse at 50% 50%, rgba(20, 16, 10, 0.5) 0%, rgba(10, 8, 5, 0.75) 100%)',
              mixBlendMode: 'multiply',
              opacity: moistDarkness,
            }}
          />
          {/* Lush mossy green organic tint */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              background: 'radial-gradient(ellipse at 50% 50%, rgba(45, 95, 30, 0.58) 0%, rgba(60, 50, 22, 0.6) 60%, rgba(22, 18, 10, 0.78) 100%)',
              mixBlendMode: 'color',
              opacity: mossTintOpacity,
            }}
          />
        </div>

        {/* Natural fissure blend mask: multiplies deep real soil cracks, spreading organically */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            mixBlendMode: 'multiply',
            opacity: crackBlendOpacity,
            WebkitMaskImage: `radial-gradient(ellipse 95% 85% at 50% 50%, black ${crackMaskRadius}%, transparent ${crackMaskRadius + 25}%)`,
            maskImage: `radial-gradient(ellipse 95% 85% at 50% 50%, black ${crackMaskRadius}%, transparent ${crackMaskRadius + 25}%)`,
            filter: 'contrast(320%) brightness(55%) grayscale(100%)',
            pointerEvents: 'none',
          }}
        >
          <AnhNen anh={src(nenKhoCan)} tu={1} den={1.06} goc="50% 50%" />
        </div>
      </Interactive.Div>

      {/* 2. Root sponge cut-out: fertile -> ash gray -> shrivels & evaporates */}
      <Interactive.Div
        name="Tấm rễ cây trù phú"
        from={0}
        durationInFrames={65}
        style={{
          position: 'absolute',
          left: 340,
          top: 130,
          width: 1240,
          height: 660,
          pointerEvents: 'none',
        }}
      >
        <Img
          src={src(tachReCayKho)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            transform: `scale(${rootScale}) translateY(${rootTranslateY}px)`,
            filter: `brightness(${rootBrightness}) contrast(${rootContrast}) saturate(${rootSaturate}) sepia(${rootSepia}) hue-rotate(${rootHue}deg) blur(${rootBlur}px) drop-shadow(0 15px 35px rgba(0, 0, 0, 0.65)) ${rootGlowOpacity > 0.05 ? `drop-shadow(0 0 25px rgba(65, 140, 35, ${rootGlowOpacity}))` : ''}`,
            opacity: rootOpacity,
          }}
        />
      </Interactive.Div>

      {/* 3. Evaporating dust haze (frame 40 to 68) */}
      <Interactive.Div
        name="Bụi mờ bốc hơi"
        from={40}
        durationInFrames={28}
        style={{
          position: 'absolute',
          left: 460,
          top: 220,
          width: 1000,
          height: 500,
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            background: 'radial-gradient(ellipse at 50% 50%, rgba(215, 185, 145, 0.4) 0%, rgba(185, 155, 115, 0.22) 45%, transparent 72%)',
            filter: 'blur(26px)',
            opacity: dustOpacity,
            transform: `translateY(${dustY}px) scale(${dustScale})`,
          }}
        />
      </Interactive.Div>

      {/* 4. Key text (smooth fade-in and slide, no glyph tearing) */}
      <Interactive.Div
        name="Chữ tiêu đề"
        from={24}
        durationInFrames={66}
        style={{
          position: 'absolute',
          left: 360,
          top: 860,
          width: 1200,
          height: 140,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            opacity: textOpacity,
            transform: `translateY(${textTranslateY}px) scale(${textScale})`,
          }}
        >
          <div
            style={{
              position: 'relative',
              padding: '12px 42px 18px',
              background: 'rgba(10, 10, 12, 0.76)',
              borderRadius: 16,
              border: '1px solid rgba(255, 210, 63, 0.4)',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
              backdropFilter: 'blur(10px)',
              display: 'inline-block',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontWeight: 900,
                fontSize: 76,
                color: '#ffffff',
                letterSpacing: '3px',
                lineHeight: 1.1,
                textShadow: '0 4px 20px rgba(0, 0, 0, 0.95)',
                whiteSpace: 'nowrap',
              }}
            >
              {keyText}
            </div>
            {/* Golden accent indicator underline */}
            <div
              style={{
                position: 'absolute',
                bottom: 8,
                left: 30,
                right: 30,
                height: 4,
                background: VANG,
                borderRadius: 2,
                boxShadow: `0 0 14px ${VANG}`,
                transformOrigin: 'center',
                transform: `scaleX(${barScale})`,
              }}
            />
          </div>
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
