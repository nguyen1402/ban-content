import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi} from './thu_vien.jsx';

export const schema = z.object({
  anh_rung: z.string().describe('Ảnh nền rừng nguyên sinh'),
  anh_tho_san: z.string().describe('Ảnh cắt thợ săn đang đặt bẫy'),
  anh_suoi: z.string().describe('Ảnh nền dòng suối vắng'),
  anh_bay_trong: z.string().describe('Ảnh chiếc bẫy trống trên bờ đất'),
  chu_moc: z.string().describe('Dòng chữ mốc thời gian'),
  co_chu_moc: z.number().describe('Cỡ chữ mốc thời gian'),
  zoom_rung_tu: z.number().describe('Độ zoom đầu của nền rừng'),
  zoom_rung_den: z.number().describe('Độ zoom cuối của nền rừng'),
  zoom_suoi: z.number().describe('Độ phóng của nền suối vắng'),
  quang_suoi: z.number().describe('Quãng lia của nền suối (px)'),
  rong_tho_san: z.number().describe('Chiều rộng lớp cắt thợ săn (px)'),
  x_tho_san: z.number().describe('Toạ độ X lớp thợ săn'),
  y_tho_san: z.number().describe('Toạ độ Y lớp thợ săn'),
  mau_wipe: z.string().describe('Màu vệt sáng lướt qua'),
  do_sepia: z.number().describe('Độ sepia cuối cùng'),
  do_toi: z.number().describe('Độ sáng còn lại của nền cuối'),
  co_flash: z.number().describe('Độ chớp sáng của dòng chữ'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const fps = 30;

  /* ---------------- LỚP THỢ SĂN (2 → 64) ---------------- */
  const fTS = frame - 2;
  const vaoTS = spring({frame: fTS, fps, config: {damping: 200, stiffness: 90}, durationInFrames: 18});
  const raTS = interpolate(frame, [54, 64], [1, 0], kep);
  const opacityTS = Math.max(0, Math.min(vaoTS, raTS));
  const scaleTS = interpolate(vaoTS, [0, 1], [0.9, 1], kep);
  const dxTS = interpolate(frame, [26, 62], [0, -130], kep);
  const dyTS = interpolate(fTS, [0, 62], [26, 0], kep);

  /* ---------------- VỆT LƯỚT SÁNG (26) ---------------- */
  const fW = frame - 26;
  const wipeX = interpolate(fW, [0, 18], [0, 2900], {
    easing: Easing.inOut(Easing.quad),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const wipeO = interpolate(fW, [0, 4, 13, 18], [0, 0.9, 0.7, 0], kep);

  /* ---------------- PUNCH-IN BẪY TRỐNG (93 → hết) ---------------- */
  const f3 = frame - 93;
  const punch = interpolate(f3, [0, 6], [1, 1.1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const drift = interpolate(f3, [6, 133], [0, 0.07], kep);
  const scale3 = punch + drift;

  /* ---------------- SEPIA TỐI (127) ---------------- */
  const sep = interpolate(f3, [34, 58], [0, props.do_sepia], kep);
  const bright = interpolate(f3, [34, 58], [1, props.do_toi], kep);

  /* ---------------- CHỚP SÁNG CHỮ (154) ---------------- */
  const flashO = interpolate(frame, [154, 156, 165], [0, props.co_flash, 0], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#0d0b08', fontFamily: FONT, overflow: 'hidden'}}>
      {/* ============ NỀN 1 : RỪNG NGUYÊN SINH ============ */}
      <Interactive.Div
        name="Nền rừng nguyên sinh"
        from={0}
        durationInFrames={78}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <AnhNen
          anh={props.anh_rung}
          tu={props.zoom_rung_tu}
          den={props.zoom_rung_den}
          goc="50% 45%"
          toi={0.06}
        />
      </Interactive.Div>

      {/* ============ NỀN 2 : SUỐI VẮNG ============ */}
      <Interactive.Div
        name="Nền dòng suối vắng"
        from={64}
        durationInFrames={42}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <AnhLia
          anh={props.anh_suoi}
          huong="trai"
          quang={props.quang_suoi}
          phong={props.zoom_suoi}
          toi={0.06}
        />
      </Interactive.Div>

      {/* ============ NỀN 3 : BẪY TRỐNG TRÊN BỜ ĐẤT ============ */}
      <Interactive.Div
        name="Bẫy trống trên bờ đất"
        from={93}
        durationInFrames={133}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `scale(${scale3})`,
            transformOrigin: '52% 62%',
            filter: `sepia(${sep}) brightness(${bright})`,
          }}
        >
          <AnhNen
            anh={props.anh_bay_trong}
            tu={1.0}
            den={1.06}
            goc="52% 62%"
            toi={0.04}
          />
        </div>
      </Interactive.Div>

      {/* ============ LỚP CẮT : THỢ SĂN ĐẶT BẪY ============ */}
      <Interactive.Div
        name="Thợ săn đặt bẫy"
        from={2}
        durationInFrames={64}
        style={{position: 'absolute', left: props.x_tho_san, top: props.y_tho_san, width: props.rong_tho_san}}
      >
        <div
          style={{
            width: '100%',
            opacity: opacityTS,
            transform: `translate(${dxTS}px, ${dyTS}px) scale(${scaleTS})`,
            transformOrigin: '50% 100%',
            filter: 'drop-shadow(0 18px 26px rgba(0,0,0,0.45))',
          }}
        >
          <Img
            src={src(props.anh_tho_san)}
            style={{width: '100%', height: 'auto', display: 'block'}}
          />
        </div>
      </Interactive.Div>

      {/* ============ VỆT LƯỚT SÁNG LAN RỘNG (26) ============ */}
      <Interactive.Div
        name="Vệt lướt sáng"
        from={26}
        durationInFrames={22}
        style={{position: 'absolute', left: -700, top: 0, width: 700, height: 1080}}
      >
        <div
          style={{
            width: 700,
            height: 1080,
            opacity: wipeO,
            transform: `translateX(${wipeX}px)`,
            background: `linear-gradient(90deg, rgba(255,244,214,0) 0%, ${props.mau_wipe} 50%, rgba(255,244,214,0) 100%)`,
          }}
        />
      </Interactive.Div>

      {/* ============ MỐC THỜI GIAN (154) ============ */}
      <Interactive.Div
        name="Mốc thời gian đầu thế kỷ XX"
        from={154}
        durationInFrames={72}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            background: '#ffffff',
            opacity: flashO,
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 450,
            width: 1920,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <ChuNoi chu={props.chu_moc} co={props.co_chu_moc} />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
