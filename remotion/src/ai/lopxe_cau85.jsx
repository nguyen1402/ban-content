import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  mapImage: z.string().describe('Ảnh bản đồ lịch sử 1825'),
  explorerImage: z.string().describe('Ảnh nhà thám hiểm James Ohio Pattie'),
  riverImage: z.string().describe('Ảnh sông San Pedro thực tế'),
  beaverCutout: z.string().describe('Ảnh tách nền con hải ly'),
  manyBeaversImage: z.string().describe('Ảnh nhiều hải ly sinh sống'),
  mainTitle: z.string().describe('Tiêu đề chính trên màn hình'),
  yearText: z.string().describe('Năm mở màn'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  return (
    <AbsoluteFill style={{backgroundColor: '#111', fontFamily: FONT}}>
      {/* 1. Bản đồ lịch sử & Năm 1825 (Frames 0 - 70) */}
      <Interactive.Div name="Bản đồ mở màn" from={0} durationInFrames={70} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={src(props.mapImage)} tu={1} den={1.05} goc="50% 50%" toi={0.2} />
        
        {/* Số năm chạy tăng dần */}
        {(() => {
          const localF = frame;
          const currentYear = Math.round(interpolate(localF, [0, 35], [1780, 1825], {extrapolateRight: 'clamp'}));
          const opacity = interpolate(localF, [50, 68], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return (
            <div style={{
              position: 'absolute',
              left: 100,
              top: 100,
              fontSize: 160,
              fontWeight: 900,
              color: VANG,
              opacity,
              textShadow: '0 4px 24px rgba(0,0,0,0.85)',
            }}>
              {currentYear}
            </div>
          );
        })()}

        {/* Hiệu ứng ánh sáng quét ngang */}
        {(() => {
          const localF = frame;
          const sweepX = interpolate(localF, [0, 45], [-400, 2400], {extrapolateRight: 'clamp'});
          return (
            <div style={{
              position: 'absolute',
              left: sweepX,
              top: 0,
              width: 300,
              height: 1080,
              background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent)',
              transform: 'skewX(-20deg)',
              pointerEvents: 'none',
            }} />
          );
        })()}
      </Interactive.Div>

      {/* 2. Nhà thám hiểm James Ohio Pattie (Frames 50 - 140) */}
      <Interactive.Div name="Nhà thám hiểm" from={50} durationInFrames={90} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        {(() => {
          const localF = frame - 50;
          const opacity = interpolate(localF, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
          const fadeOut = interpolate(localF, [75, 90], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return (
            <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: Math.min(opacity, fadeOut)}}>
              <AnhNen anh={src(props.explorerImage)} tu={1} den={1.08} goc="60% 40% " toi={0.15} />
              <div style={{
                position: 'absolute',
                left: 120,
                bottom: 120,
                backgroundColor: 'rgba(0,0,0,0.78)',
                padding: '24px 48px',
                borderRadius: 14,
                borderLeft: `8px solid ${VANG}`,
              }}>
                <div style={{fontSize: 64, color: '#fff', fontWeight: 700}}>James Ohio Pattie</div>
                <div style={{fontSize: 36, color: VANG, marginTop: 8}}>Nhà thám hiểm thế kỷ 19</div>
              </div>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* 3. Dòng sông San Pedro & Mũi tên bản đồ (Frames 130 - 215) */}
      <Interactive.Div name="Sông San Pedro" from={130} durationInFrames={85} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        {(() => {
          const localF = frame - 130;
          const opacity = interpolate(localF, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
          const fadeOut = interpolate(localF, [70, 85], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return (
            <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: Math.min(opacity, fadeOut)}}>
              <AnhNen anh={src(props.riverImage)} tu={1.02} den={1.1} goc="50% 50%" toi={0.12} />
              
              {/* Mũi tên chỉ dòng sông */}
              <div style={{position: 'absolute', left: 1150, top: 520}}>
                <MuiTen dx={-320} dy={-160} cong={0.25} />
              </div>

              <div style={{
                position: 'absolute',
                left: 1050,
                bottom: 140,
                backgroundColor: 'rgba(0,0,0,0.82)',
                padding: '20px 40px',
                borderRadius: 12,
                borderLeft: `6px solid ${VANG}`,
              }}>
                <div style={{fontSize: 56, color: '#fff', fontWeight: 700}}>Khúc sông San Pedro</div>
              </div>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* 4 & 5. Vương quốc hải ly & Bảng đếm số (Frames 205 - 300) */}
      <Interactive.Div name="Vương quốc hải ly" from={205} durationInFrames={95} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        {(() => {
          const localF = frame - 205;
          const opacity = interpolate(localF, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
          // Hiệu ứng punch-in phóng to 15% kết hợp flash nhẹ
          const scale = interpolate(localF, [0, 18], [1.15, 1], {easing: Easing.out(Easing.cubic), extrapolateRight: 'clamp'});
          const flashOpacity = interpolate(localF, [0, 8], [0.4, 0], {extrapolateRight: 'clamp'});

          return (
            <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity, transform: `scale(${scale})`, transformOrigin: 'center center'}}>
              <AnhNen anh={src(props.manyBeaversImage)} tu={1} den={1.06} goc="50% 50%" toi={0.18} />
              
              {/* Flash trắng nhẹ khi punch-in */}
              <div style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: 1920,
                height: 1080,
                backgroundColor: '#ffffff',
                opacity: flashOpacity,
                pointerEvents: 'none',
              }} />

              {/* Hình ảnh tách nền con hải ly bên gốc cây */}
              <Img src={src(props.beaverCutout)} style={{
                position: 'absolute',
                left: 960,
                top: 320,
                height: 580,
                filter: 'drop-shadow(0 24px 32px rgba(0,0,0,0.65))',
              }} />

              {/* Tiêu đề chính */}
              <div style={{
                position: 'absolute',
                left: 100,
                top: 80,
                maxWidth: 1100,
              }}>
                <ChuNoi chu={props.mainTitle} co={96} />
              </div>

              {/* Bảng đếm số lượng hải ly sinh sống đông đúc */}
              <div style={{
                position: 'absolute',
                left: 100,
                bottom: 100,
                backgroundColor: 'rgba(0,0,0,0.86)',
                padding: '24px 48px',
                borderRadius: 16,
                border: `3px solid ${VANG}`,
                display: 'flex',
                alignItems: 'center',
                gap: 24,
              }}>
                <div style={{fontSize: 48, color: '#fff', fontWeight: 600}}>Mật độ loài:</div>
                <SoDem so={Math.round(interpolate(localF, [15, 75], [0, 4850], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}))} don_vi="con" giay={2} co={72} />
              </div>
            </div>
          );
        })()}
      </Interactive.Div>
    </AbsoluteFill>
  );
};
