import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

// Con vật/đối tượng ĐÃ TÁCH NỀN (PNG trong suốt) + viền sáng + chuyển động nhẹ trên nền là chính ảnh gốc làm mờ.
// props: {anh, nen, kieu: 'trai'|'phai'|'giua', vien: '#fff', giay}
export const NhanVat = ({anh, nen, kieu = 'giua', vien = '#ffffff'}) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames: D, width: W, height: H} = useVideoConfig();
  const t = f / fps;
  const vao = spring({frame: f, fps, config: {damping: 16, stiffness: 90}});           // 0 -> 1, hơi nảy
  const huong = kieu === 'trai' ? -1 : kieu === 'phai' ? 1 : 0;
  const dx = huong * (1 - vao) * 520;                                                  // trượt vào từ mép
  const dy = (1 - vao) * (huong === 0 ? 90 : 0) + Math.sin(t * 1.6) * 9;                // thở nhẹ
  const zoom = interpolate(f, [0, D], [1.0, 1.1]) * (0.86 + 0.14 * vao);                // phóng dần suốt cảnh
  const xoay = Math.sin(t * 0.9) * 0.9 + (1 - vao) * huong * 4;
  const nenZoom = interpolate(f, [0, D], [1.15, 1.3]);
  const nenTrai = interpolate(f, [0, D], [0, -60]);
  const o = 5;                                                                         // độ dày viền (px)
  const vienLoc = [[o, 0], [-o, 0], [0, o], [0, -o], [o, o], [-o, -o], [o, -o], [-o, o]]
    .map(([x, y]) => `drop-shadow(${x}px ${y}px 0 ${vien})`).join(' ');
  return (
    <AbsoluteFill style={{background: '#0d1410'}}>
      {nen ? <Img src={nen} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover',
        transform: `translateX(${nenTrai}px) scale(${nenZoom})`, filter: 'blur(26px) brightness(0.55) saturate(1.1)'}} /> : null}
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 35%, rgba(0,0,0,0.55) 100%)'}} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <Img src={anh} style={{
          maxWidth: W * 0.62, maxHeight: H * 0.78, objectFit: 'contain',
          transform: `translate(${dx}px, ${dy}px) scale(${zoom}) rotate(${xoay}deg)`,
          filter: `${vienLoc} drop-shadow(0 26px 34px rgba(0,0,0,0.55))`,
          opacity: Math.min(1, vao * 1.6)}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
