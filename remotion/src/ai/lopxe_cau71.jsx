import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh đại cảnh thượng nguồn khô hạn Arizona'),
  anh_giao_su: z.string().describe('Ảnh cắt giáo sư Honig đang khảo sát thực địa'),
  anh_dat_am: z.string().describe('Ảnh cận cảnh đất ẩm ven suối với mầm xanh'),
  chu_moc: z.string().describe('Dòng chữ mốc thời gian ở góc trên'),
  co_chu_moc: z.number().describe('Cỡ chữ của mốc thời gian (px)'),
  mau_chu_moc: z.string().describe('Màu chữ mốc thời gian'),
  mau_gach: z.string().describe('Màu gạch nhấn dưới mốc thời gian'),
  rong_gach: z.number().describe('Độ dài gạch nhấn (px)'),
  zoom_nen_tu: z.number().describe('Tỉ lệ zoom đầu của đại cảnh thượng nguồn'),
  zoom_nen_den: z.number().describe('Tỉ lệ zoom cuối của đại cảnh thượng nguồn'),
  toi_nen: z.number().describe('Độ tối lớp đại cảnh (0..0.5)'),
  lech_troi_giao_su: z.number().describe('Quãng trôi ngang của giáo sư khi bước đi (px)'),
  zoom_dat_tu: z.number().describe('Tỉ lệ zoom đầu của cận cảnh đất ẩm'),
  zoom_dat_den: z.number().describe('Tỉ lệ zoom cuối của cận cảnh đất ẩm'),
  toi_dat: z.number().describe('Độ tối lớp cận cảnh đất ẩm'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---------- Mốc thời gian (beat 4) ----------
  const fM = Math.max(0, frame - 4);
  const opM = interpolate(fM, [0, 12], [0, 1], kep) * interpolate(fM, [110, 130], [1, 0], kep);
  const yM =
    interpolate(fM, [0, 18], [-28, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }) + interpolate(fM, [0, 130], [0, -14], kep);
  const wGach = interpolate(fM, [8, 36], [0, props.rong_gach], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const opGach = interpolate(fM, [6, 20], [0, 1], kep);

  // ---------- Giáo sư Honig (beat 31) ----------
  const fGS = Math.max(0, frame - 28);
  const vaoGS = spring({frame: fGS, fps, config: {damping: 24, mass: 0.9, stiffness: 80}});
  const xGS =
    interpolate(vaoGS, [0, 1], [240, 0]) + interpolate(fGS, [22, 122], [0, -props.lech_troi_giao_su], kep);
  const opGS =
    interpolate(fGS, [0, 16], [0, 1], kep) * interpolate(fGS, [106, 122], [1, 0], kep);
  const scaleGS = interpolate(fGS, [0, 122], [1, 1.045], kep);

  // ---------- Cận cảnh đất ẩm (beat 143) ----------
  const fDat = Math.max(0, frame - 140);
  const pDat = interpolate(fDat, [0, 16], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const yDat = (1 - pDat) * 1080;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0b0b', overflow: 'hidden'}}>
      {/* Đại cảnh thượng nguồn khô hạn — push-in chậm suốt beat 1 & 2 */}
      <Interactive.Div
        name="Đại cảnh thượng nguồn khô hạn"
        from={0}
        durationInFrames={156}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anh_nen}
          tu={props.zoom_nen_tu}
          den={props.zoom_nen_den}
          goc="50% 60%"
          toi={props.toi_nen}
        />
      </Interactive.Div>

      {/* Mốc thời gian thanh nhã ở góc trên */}
      <Interactive.Div
        name="Mốc thời gian 3 NĂM SAU"
        from={4}
        durationInFrames={130}
        style={{position: 'absolute', left: 140, top: 138, width: 1000, height: 230}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, opacity: opM, transform: `translateY(${yM}px)`}}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: props.co_chu_moc,
              fontWeight: 800,
              letterSpacing: '0.055em',
              lineHeight: 1,
              color: props.mau_chu_moc,
              whiteSpace: 'nowrap',
              textShadow: '0 6px 30px rgba(0,0,0,0.6)',
            }}
          >
            {props.chu_moc}
          </div>
          <div
            style={{
              marginTop: 24,
              height: 8,
              width: wGach,
              opacity: opGach,
              background: props.mau_gach,
              borderRadius: 4,
            }}
          />
        </div>
      </Interactive.Div>

      {/* Lớp cắt giáo sư Honig quan sát thực địa ngược sáng */}
      <Interactive.Div
        name="Giáo sư Honig khảo sát thực địa"
        from={28}
        durationInFrames={122}
        style={{position: 'absolute', left: 1130, top: 250, width: 320, height: 830}}
      >
        <Img
          name="Giáo sư Honig"
          src={src(props.anh_giao_su)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            objectPosition: 'bottom center',
            opacity: opGS,
            transform: `translateX(${xGS}px) scale(${scaleGS})`,
            transformOrigin: '50% 100%',
            filter: 'contrast(1.04) saturate(0.96)',
          }}
        />
      </Interactive.Div>

      {/* Cận cảnh đất ẩm ven suối — máy hạ xuống mặt đất */}
      <Interactive.Div
        name="Cận cảnh đất ẩm và mầm xanh"
        from={140}
        durationInFrames={97}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateY(${yDat}px)`,
          }}
        >
          <AnhNen
            anh={props.anh_dat_am}
            tu={props.zoom_dat_tu}
            den={props.zoom_dat_den}
            goc="50% 72%"
            toi={props.toi_dat}
          />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
