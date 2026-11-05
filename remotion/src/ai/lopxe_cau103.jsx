import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  title1: z.string().describe('Tiêu đề Beat 1'),
  title2: z.string().describe('Tiêu đề Beat 2'),
  title3: z.string().describe('Tiêu đề Beat 3'),
  image1: z.string().describe('Ảnh nền Beat 1'),
  image2: z.string().describe('Ảnh nền Beat 2'),
  image3: z.string().describe('Ảnh cần Beat 3'),
});

export const defaultProps = {
  title1: '1-2 triệu lốp xe',
  title2: 'Nhấn chìm 20m dưới biển',
  title3: 'Khóa thép',
  image1: 'nhan_y/fb02a4353e2e57.jpg',
  image2: 'nhan_y/4a6a5b97afef87.jpg',
  image3: 'nhan_y/64e7736fa96150.jpg',
};

export const Canh = (props) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#000', fontFamily: FONT, overflow: 'hidden'}}>
      {/* Beat 1: 0.0s - 2.0s (Frames 0 - 60) */}
      <Interactive.Div name="Beat 1 Bg" from={0} durationInFrames={65} style={{position: 'absolute', width: '100%', height: '100%'}}>
        <AnhNen anh={src(props.image1)} tu={1} den={1.08} goc="50% 50%" toi={0.1} />
        <Interactive.Div name="Text Beat 1" from={18} durationInFrames={47} style={{position: 'absolute', left: 100, top: 120}}>
          <div style={{fontSize: 88, fontWeight: 900, color: '#fff', textShadow: '0 4px 20px rgba(0,0,0,0.8)'}}>
            {props.title1}
          </div>
          <div style={{width: interpolate(frame - 18, [0, 20], [0, 350], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), height: 6, backgroundColor: VANG, marginTop: 10}} />
        </Interactive.Div>
      </Interactive.Div>

      {/* Beat 2: 2.0s - 5.0s (Frames 60 - 150) */}
      <Interactive.Div name="Beat 2 Bg" from={60} durationInFrames={95} style={{position: 'absolute', width: '100%', height: '100%'}}>
        <AnhNen anh={src(props.image2)} tu={1.05} den={1.12} goc="50% 60%" toi={0.2} />
        <Interactive.Div name="Text Beat 2" from={60} durationInFrames={95} style={{position: 'absolute', right: 100, bottom: 100, textAlign: 'right'}}>
          <div style={{fontSize: 72, fontWeight: 800, color: '#E0F7FA', textShadow: '0 4px 20px rgba(0,0,0,0.9)'}}>
            {props.title2}
          </div>
        </Interactive.Div>
      </Interactive.Div>

      {/* Beat 3: 5.35s - 7.69s+ (Frames 160 - 250) */}
      <Interactive.Div name="Beat 3 Bg" from={155} durationInFrames={95} style={{position: 'absolute', width: '100%', height: '100%'}}>
        <AnhNen anh={src(props.image3)} tu={1} den={1.06} goc="50% 50%" toi={0.3} />
        <Interactive.Div name="Text Beat 3" from={160} durationInFrames={90} style={{position: 'absolute', left: 120, bottom: 140}}>
          {(() => {
            const f3 = frame - 160;
            const scale = interpolate(f3, [0, 8, 20], [0.5, 1.2, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            const flash = interpolate(f3, [0, 5, 15], [0.8, 0, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            return (
              <div style={{position: 'relative'}}>
                <div style={{
                  fontSize: 110,
                  fontWeight: 900,
                  color: VANG,
                  transform: `scale(${scale})`,
                  transformOrigin: 'left center',
                  textShadow: '0 6px 30px rgba(0,0,0,0.9)'
                }}>
                  {props.title3}
                </div>
                {flash > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: -50,
                    left: -50,
                    right: -50,
                    bottom: -50,
                    backgroundColor: '#fff',
                    opacity: flash,
                    pointerEvents: 'none',
                    mixBlendMode: 'overlay'
                  }} />
                )}
              </div>
            );
          })()}
        </Interactive.Div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
