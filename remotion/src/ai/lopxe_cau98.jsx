import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhSuoiLop: z.string().describe('Ảnh suối lốp cũ'),
  anhBaiRac: z.string().describe('Ảnh bãi rác suối'),
  anhBeTong: z.string().describe('Ảnh bê tông lốp xe'),
  textThamMy: z.string().describe('Nhãn text thẩm mỹ dòng suối'),
  textGiaiPhap: z.string().describe('Nhãn text giải pháp bê tông'),
});

export const defaultProps = {
  anhSuoiLop: 'nhan_y/f2644e057d7620.jpg',
  anhBaiRac: 'nhan_y/7d30bd55751e05.jpg',
  anhBeTong: 'nhan_y/ad48222b977475.jpg',
  textThamMy: 'Thẩm mỹ dòng suối',
  textGiaiPhap: 'Giải pháp bê tông',
};

export const Canh = (props) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#000', fontFamily: FONT}}>
      {/* Segment 1: 0.0s to 3.74s (Frames 0 - 112) */}
      <Interactive.Div name="AnhSuoiLop" from={0} durationInFrames={115} style={{position: 'absolute', inset: 0}}>
        <AnhNen anh={props.anhSuoiLop} tu={1} den={1.08} goc="50% 50%" toi={0.2} />
        {/* Callout text at 1.8s (Frame 54) */}
        <Interactive.Div name="NhanThamMy" from={54} durationInFrames={61} style={{position: 'absolute', left: 100, top: 120}}>
          <Nhan chu={props.textThamMy} dx={120} dy={-60} co={64} />
        </Interactive.Div>
      </Interactive.Div>

      {/* Segment 2: 3.74s to 8.19s (Frames 112 - 246) */}
      <Interactive.Div name="AnhBaiRac" from={112} durationInFrames={134} style={{position: 'absolute', inset: 0}}>
        {/* Slide transition and punch-in effect at 7.59s (Frame 228) */}
        {(() => {
          const localFrame = frame - 112;
          const isPunchIn = localFrame >= 228 - 112; // frame 116 local
          const punchSpring = isPunchIn ? spring({frame: localFrame - (228 - 112), fps: 30, config: {damping: 12}}) : 0;
          const scale = 1 + punchSpring * 0.12;
          const slideProgress = interpolate(localFrame, [0, 15], [100, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

          return (
            <div style={{position: 'absolute', inset: 0, transform: `translateX(${slideProgress}%) scale(${scale})`, transformOrigin: 'center center'}}>
              <AnhNen anh={props.anhBaiRac} tu={1.02} den={1.1} goc="50% 50%" toi={0.25} />
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Segment 3: 8.19s to 12.0s (Frames 246 - 359) */}
      <Interactive.Div name="AnhBeTong" from={246} durationInFrames={114} style={{position: 'absolute', inset: 0}}>
        {/* Light sweep transition at 8.19s */}
        {(() => {
          const localFrame = frame - 246;
          const sweepProgress = interpolate(localFrame, [0, 20], [-100, 200], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

          return (
            <div style={{position: 'absolute', inset: 0}}>
              <AnhNen anh={props.anhBeTong} tu={1} den={1.06} goc="50% 50%" toi={0.15} />
              {/* Light sweep overlay */}
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
                transform: `translateX(${sweepProgress}%)`,
                pointerEvents: 'none'
              }} />
              {/* Text Giải pháp bê tông at 9.33s (Frame 280) */}
              <Interactive.Div name="NhanBeTong" from={34} durationInFrames={80} style={{position: 'absolute', left: 120, top: 140}}>
                <Nhan chu={props.textGiaiPhap} dx={140} dy={-60} co={64} />
              </Interactive.Div>
            </div>
          );
        })()}
      </Interactive.Div>
    </AbsoluteFill>
  );
};
