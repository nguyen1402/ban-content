import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen1: z.string().describe('Ảnh nền thượng nguồn sa mạc'),
  anhNen2: z.string().describe('Ảnh nhà khoa học từ sau'),
  anhNen3: z.string().describe('Ảnh cận cảnh đất thay đổi'),
  tieuDe: z.string().describe('Tiêu đề chính trên màn hình'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#000', fontFamily: FONT}}>
      {/* Cảnh 1: 0.0s - 0.9s (frames 0 - 27) - Ảnh nền sa mạc cằn cỗi */}
      {frame < 28 && (
        <Interactive.Div name="Nền Sa Mạc" from={0} durationInFrames={28} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
          <AnhNen anh={props.anhNen1} tu={1} den={1.05} goc="50% 50%" toi={0.2} />
        </Interactive.Div>
      )}

      {/* Chữ số '3 năm sau' trượt nhẹ vào màn hình từ 0.0s đến 0.8s */}
      {frame < 28 && (
        <Interactive.Div
          name="Tiêu đề 3 năm sau"
          from={0}
          durationInFrames={28}
          style={{
            position: 'absolute',
            left: 100,
            top: 850,
            transform: `translateX(${interpolate(frame, [0, 24], [-50, 0], kep)}px)`,
            opacity: interpolate(frame, [0, 15], [0, 1], kep),
          }}
        >
          <div style={{fontSize: 96, fontWeight: 'bold', color: '#fff', textShadow: '2px 2px 10px rgba(0,0,0,0.8)'}}>
            {props.tieuDe}
          </div>
        </Interactive.Div>
      )}

      {/* Cảnh 2: Từ 0.9s đến 3.3s (frames 27 - 99) - Nhà khoa học đi bộ (pan chậm) */}
      {frame >= 27 && frame < 150 && (
        <Interactive.Div name="Nhà Khoa Học Nền" from={27} durationInFrames={123} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
          <AnhNen
            anh={props.anhNen2}
            tu={1.0}
            den={1.08}
            goc={interpolate(frame, [27, 150], [40, 60], kep) + '% 50%'}
            toi={0.15}
          />
        </Interactive.Div>
      )}

      {/* Cảnh 3: Từ 5.1s (frame 153) trở đi - Punch-in nhanh (zoom 10%) kết hợp flash sáng nhẹ */}
      {frame >= 150 && (
        <Interactive.Div name="Cận Cảnh Đất Thay Đổi" from={150} durationInFrames={68} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
          <AnhNen
            anh={props.anhNen3}
            tu={interpolate(frame, [150, 158], [1.0, 1.1], kep)}
            den={1.12}
            goc="50% 60%"
            toi={0.1}
          />
          {/* Flash sáng nhẹ lúc 5.1s */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: '#fff',
              opacity: interpolate(frame, [150, 155, 162], [0, 0.4, 0], kep),
              pointerEvents: 'none',
            }}
          />
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};
