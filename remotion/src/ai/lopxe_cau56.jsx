import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  nenTuongPath: z.string().describe('Ảnh nền tường lốp xe'),
  nenNuocSietPath: z.string().describe('Ảnh nền nước chảy siết'),
  canThamQuaPath: z.string().describe('Ảnh nền nước thấm qua'),
  tieuDe: z.string().describe('Tiêu đề chính trên màn hình'),
  tocDDBanDau: z.number().describe('Tốc độ dòng chảy ban đầu (m/s)'),
  tocDDSau: z.number().describe('Tốc độ dòng chảy sau khi hãm (m/s)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
      {/* Background 1: Tường lốp xe (0 - 36) */}
      <Interactive.Div name="Nền tường lốp" from={0} durationInFrames={36} style={{position: 'absolute', width: 1920, height: 1080}}>
        <AnhNen anh={src(props.nenTuongPath)} tu={1.0} den={1.05} goc="50% 50%" toi={0.2} />
      </Interactive.Div>

      {/* Background 2: Nước siết (35 - 135) */}
      <Interactive.Div name="Nền nước siết" from={35} durationInFrames={101} style={{position: 'absolute', width: 1920, height: 1080}}>
        {(() => {
          const localFrame = frame - 35;
          const slideX = interpolate(localFrame, [0, 100], [-30, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic)
          });
          return (
            <div style={{transform: `translateX(${slideX}px)`, width: '100%', height: '100%', position: 'absolute'}}>
              <AnhNen anh={src(props.nenNuocSietPath)} tu={1.02} den={1.08} goc="50% 50%" toi={0.25} />
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Background 3: Nước thấm qua với hiệu ứng punch-in +10% trong 6 frame (135 - 160) */}
      <Interactive.Div name="Nền nước thấm qua" from={135} durationInFrames={25} style={{position: 'absolute', width: 1920, height: 1080}}>
        {(() => {
          const localFrame = frame - 135;
          const scale = interpolate(localFrame, [0, 6, 25], [1, 1.1, 1.12], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic)
          });
          const slideX = interpolate(localFrame, [0, 25], [20, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic)
          });
          return (
            <div style={{transform: `scale(${scale}) translateX(${slideX}px)`, width: '100%', height: '100%', position: 'absolute'}}>
              <AnhNen anh={src(props.canThamQuaPath)} tu={1.0} den={1.04} goc="50% 50%" toi={0.15} />
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Main Title Overlay (HÃM DÒNG CHẢY) */}
      <Interactive.Div name="Tiêu đề chính" from={0} durationInFrames={160} style={{position: 'absolute', left: 100, top: 80}}>
        {(() => {
          const fadeIn = interpolate(frame, [0, 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return (
            <div style={{
              opacity: fadeIn,
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(0,0,0,0.65)',
              padding: '16px 36px',
              borderRadius: '12px',
              borderLeft: '8px solid #FFD700',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
            }}>
              <span style={{
                fontFamily: FONT,
                fontSize: '96px',
                fontWeight: 900,
                color: '#FFFFFF',
                letterSpacing: '3px',
                lineHeight: 1.1
              }}>
                {props.tieuDe}
              </span>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Speed Counter / Label */}
      <Interactive.Div name="Nhãn tốc độ" from={35} durationInFrames={125} style={{position: 'absolute', left: 1380, top: 80}}>
        {(() => {
          const localFrame = frame - 35;
          const fadeIn = interpolate(localFrame, [0, 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          
          const currentSpeed = interpolate(localFrame, [0, 100], [props.tocDDBanDau, props.tocDDSau], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic)
          });

          return (
            <div style={{
              opacity: fadeIn,
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              padding: '20px 32px',
              borderRadius: '16px',
              border: '2px solid rgba(255, 255, 255, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
            }}>
              <span style={{fontFamily: FONT, fontSize: '24px', color: '#AAAAAA', textTransform: 'uppercase', letterSpacing: '1.5px'}}>
                Vận tốc dòng chảy
              </span>
              <div style={{display: 'flex', alignItems: 'baseline', gap: '12px', marginTop: '6px'}}>
                <span style={{fontFamily: FONT, fontSize: '64px', fontWeight: 900, color: currentSpeed > 5 ? '#FF4500' : '#00FF7F'}}>
                  {currentSpeed.toFixed(1)}
                </span>
                <span style={{fontFamily: FONT, fontSize: '32px', color: '#FFFFFF', fontWeight: 700}}>
                  m/s
                </span>
              </div>
            </div>
          );
        })()}
      </Interactive.Div>
    </AbsoluteFill>
  );
};
