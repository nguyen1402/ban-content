import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  bgImage: z.string().describe('Hình nền cột nước biển/sông'),
  salmonImage: z.string().describe('Ảnh cắt cá hồi'),
  eelImage: z.string().describe('Ảnh cắt lươn'),
  larvaeImage: z.string().describe('Ảnh cắt ấu trùng mù lòa'),
  title1: z.string().describe('Tiêu đề tầng nước giữa'),
  title2: z.string().describe('Tiêu đề sát đáy bùn cát'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();

  // 0.0s - 1.88s: Salmon swimming across middle water (frames 0 to 56)
  const salmonProgress = interpolate(frame, [0, 56], [-300, 2200], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const salmonOpacity = interpolate(frame, [0, 10, 50, 56], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // 2.44s - 6.57s: Eel gliding down to the bottom and burrowing (frames 73 to 197)
  const eelX = interpolate(frame, [73, 132, 197], [200, 800, 950], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const eelY = interpolate(frame, [73, 132, 197], [200, 650, 750], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const eelRotate = interpolate(frame, [73, 132, 197], [10, 45, 75], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const eelOpacity = interpolate(frame, [70, 73, 190, 197], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // 7.05s - 9.79s: Camera zoom & Blind larvae reveal (frames 212 to 294)
  const zoomScale = interpolate(frame, [212, 250, 294], [1, 1.4, 1.6], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const larvaeOpacity = interpolate(frame, [212, 230, 294], [0, 1, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#050b14', overflow: 'hidden'}}>
      {/* Background with slow push */}
      <Interactive.Div name="Nền cột nước" from={0} durationInFrames={314} style={{position: 'absolute', inset: 0, transform: `scale(${zoomScale})`, transformOrigin: '1000px 800px'}}>
        <AnhNen anh={props.bgImage} tu={0.9} den={1.1} goc={0} toi={0.2} />
      </Interactive.Div>

      {/* Salmon Section */}
      {frame >= 0 && frame <= 65 && (
        <Interactive.Div name="Cá hồi bơi tầng giữa" from={0} durationInFrames={65} style={{position: 'absolute', left: salmonProgress, top: 350, opacity: salmonOpacity}}>
          <Img src={src(props.salmonImage)} style={{width: 700, height: 243, transform: 'scale(1.5)'}} />
        </Interactive.Div>
      )}

      {/* Salmon text highlight */}
      {frame >= 0 && frame <= 65 && (
        <Interactive.Div name="Chữ tầng nước giữa" from={0} durationInFrames={65} style={{position: 'absolute', left: 100, top: 100}}>
          <ChuNoi chu={props.title1} co={90} />
        </Interactive.Div>
      )}

      {/* Eel Section */}
      {frame >= 70 && frame <= 200 && (
        <Interactive.Div name="Lươn lướt xuống đáy" from={70} durationInFrames={130} style={{position: 'absolute', left: eelX, top: eelY, opacity: eelOpacity}}>
          <Img src={src(props.eelImage)} style={{width: 700, height: 264, transform: `rotate(${eelRotate}deg)`}} />
        </Interactive.Div>
      )}

      {/* Eel text highlight */}
      {frame >= 73 && frame <= 200 && (
        <Interactive.Div name="Chữ sát đáy bùn cát" from={73} durationInFrames={127} style={{position: 'absolute', left: 100, top: 100}}>
          <ChuNoi chu={props.title2} co={90} />
        </Interactive.Div>
      )}

      {/* Blind Larvae Section (Hidden under sand, revealed by zoom) */}
      {frame >= 210 && (
        <Interactive.Div name="Ấu trùng mù lòa ẩn nấp" from={210} durationInFrames={104} style={{position: 'absolute', left: 750, top: 650, opacity: larvaeOpacity, transform: `scale(${zoomScale})`}}>
          <Img src={src(props.larvaeImage)} style={{width: 600, height: 314}} />
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};
