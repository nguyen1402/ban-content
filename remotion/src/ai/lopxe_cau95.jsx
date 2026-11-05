import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  tieuDe: z.string().describe('Tiêu đề chính trọng tâm màn hình'),
  nhanSoLuong: z.string().describe('Nhãn bộ đếm số lượng lốp'),
  soToiDa: z.number().describe('Số lượng lốp tối đa'),
  anhNen: z.string().describe('Đường dẫn ảnh nền nhà xưởng'),
  anhLop: z.string().describe('Đường dẫn ảnh lốp xe'),
  anhDayThep: z.string().describe('Đường dẫn ảnh dây thép'),
  anhXengSoi: z.string().describe('Đường dẫn ảnh xẻng sỏi'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Hiệu ứng punch-in và chớp sáng tại từ 'khổng lồ' (frame 330)
  const isPunch = frame >= 330;
  const punchProgress = isPunch ? spring({frame: frame - 330, fps, config: {damping: 12, stiffness: 220}}) : 0;
  const scale = 1 + punchProgress * 0.12;
  const flashOpacity = frame >= 330 && frame <= 336 ? interpolate(frame, [330, 333, 336], [0, 0.7, 0]) : 0;

  return (
    <AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden', transform: `scale(${scale})`, transformOrigin: 'center center'}}>
      {/* Nền nhà xưởng toàn cảnh xuyên suốt */}
      <Interactive.Div name="Nền nhà xưởng" from={0} durationInFrames={356} style={{position: 'absolute', width: '100%', height: '100%'}}>
        <AnhNen anh={props.anhNen} tu={1} den={1.08} goc="50% 50%" toi={0.3} />
      </Interactive.Div>

      {/* Lớp xe xếp chồng (Parallax layer 1) */}
      <Interactive.Div
        name="Lốp xe xếp chồng"
        from={0}
        durationInFrames={356}
        style={{
          position: 'absolute',
          left: 120,
          top: 100,
        }}
      >
        {(() => {
          const transY = interpolate(frame, [0, 356], [0, -35], {extrapolateRight: 'clamp'});
          return (
            <div style={{transform: `translateY(${transY}px)`}}>
              <Img
                name="Ảnh lốp xe"
                from={0}
                durationInFrames={356}
                src={src(props.anhLop)}
                style={{
                  width: 520,
                  height: 714,
                  objectFit: 'contain',
                  filter: 'drop-shadow(0px 25px 35px rgba(0,0,0,0.8))',
                }}
              />
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Bộ đếm số lượng xuất hiện từ từ 'nghìn' (frame 62) */}
      <Interactive.Div
        name="Bộ đếm số lượng"
        from={62}
        durationInFrames={294}
        style={{
          position: 'absolute',
          left: 1100,
          top: 140,
          backgroundColor: 'rgba(10, 10, 10, 0.85)',
          padding: '35px 55px',
          borderRadius: '16px',
          border: `3px solid ${VANG}`,
          boxShadow: '0 20px 45px rgba(0,0,0,0.9)',
        }}
      >
        {(() => {
          const countProgress = interpolate(frame, [62, 145], [0, props.soToiDa], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic),
          });
          const currentSo = Math.round(countProgress);
          return (
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: 90, fontWeight: 'bold', color: VANG, fontFamily: FONT, lineHeight: 1}}>
                {currentSo.toLocaleString('en-US')}
              </div>
              <div style={{fontSize: 38, color: '#fff', fontFamily: FONT, marginTop: 15, textTransform: 'uppercase', letterSpacing: '2px'}}>
                {props.nhanSoLuong}
              </div>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Cận cảnh dây thép kích hoạt từ từ 'dây thép' (frame 135) */}
      <Interactive.Div
        name="Cận cảnh dây thép"
        from={135}
        durationInFrames={221}
        style={{
          position: 'absolute',
          left: 1040,
          top: 470,
        }}
      >
        {(() => {
          const slideIn = spring({frame: frame - 135, fps, config: {damping: 16}});
          const x = interpolate(slideIn, [0, 1], [350, 0]);
          const opacity = interpolate(slideIn, [0, 1], [0, 1]);
          return (
            <div style={{transform: `translateX(${x}px)`, opacity, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
              <Img
                name="Ảnh dây thép"
                from={135}
                durationInFrames={221}
                src={src(props.anhDayThep)}
                style={{
                  width: 740,
                  height: 444,
                  objectFit: 'contain',
                  borderRadius: '12px',
                  border: '2px solid rgba(255,255,255,0.4)',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.7)',
                }}
              />
              <div
                style={{
                  marginTop: 15,
                  backgroundColor: 'rgba(0,0,0,0.85)',
                  padding: '12px 30px',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: 34,
                  fontFamily: FONT,
                  borderLeft: `6px solid ${VANG}`,
                  letterSpacing: '1px',
                }}
              >
                CHẰNG BUỘC DÂY THÉP
              </div>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Cận cảnh xẻng sỏi kích hoạt từ từ 'xẻng sỏi' (frame 183) */}
      <Interactive.Div
        name="Cận cảnh xẻng sỏi"
        from={183}
        durationInFrames={173}
        style={{
          position: 'absolute',
          left: 140,
          top: 500,
        }}
      >
        {(() => {
          const slideIn = spring({frame: frame - 183, fps, config: {damping: 16}});
          const x = interpolate(slideIn, [0, 1], [-350, 0]);
          const opacity = interpolate(slideIn, [0, 1], [0, 1]);
          return (
            <div style={{transform: `translateX(${x}px)`, opacity, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
              <Img
                name="Ảnh xẻng sỏi"
                from={183}
                durationInFrames={173}
                src={src(props.anhXengSoi)}
                style={{
                  width: 740,
                  height: 496,
                  objectFit: 'contain',
                  borderRadius: '12px',
                  border: '2px solid rgba(255,255,255,0.4)',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.7)',
                }}
              />
              <div
                style={{
                  marginTop: 15,
                  backgroundColor: 'rgba(0,0,0,0.85)',
                  padding: '12px 30px',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: 34,
                  fontFamily: FONT,
                  borderLeft: `6px solid ${VANG}`,
                  letterSpacing: '1px',
                }}
              >
                NHỒI TỪNG XẺNG SỎI
              </div>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Tiêu đề trọng tâm 'Khổng lồ' xuất hiện tại frame 330 */}
      <Interactive.Div
        name="Tiêu đề trọng tâm"
        from={330}
        durationInFrames={26}
        style={{
          position: 'absolute',
          left: 960,
          top: 910,
          transform: 'translateX(-50%)',
        }}
      >
        {(() => {
          const pop = spring({frame: frame - 330, fps, config: {damping: 10, stiffness: 280}});
          const scaleText = interpolate(pop, [0, 1], [0.6, 1]);
          return (
            <div
              style={{
                transform: `scale(${scaleText})`,
                backgroundColor: VANG,
                padding: '18px 60px',
                borderRadius: '14px',
                boxShadow: '0 15px 40px rgba(0,0,0,0.9)',
              }}
            >
              <div style={{fontSize: 95, fontWeight: 'bold', color: '#000', fontFamily: FONT, textAlign: 'center', textTransform: 'uppercase', letterSpacing: '2px'}}>
                {props.tieuDe}
              </div>
            </div>
          );
        })()}
      </Interactive.Div>

      {/* Hiệu ứng chớp sáng mạnh nhấn mạnh quy mô */}
      {flashOpacity > 0 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: '#ffffff',
            opacity: flashOpacity,
            pointerEvents: 'none',
          }}
        />
      )}
    </AbsoluteFill>
  );
};
