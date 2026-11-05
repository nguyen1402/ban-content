import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhBanDo: z.string().describe('Ảnh nền bản đồ địa hình Arizona'),
  anhInset: z.string().describe('Ảnh minh họa đập lốp xe'),
  anhHoSo: z.string().describe('Ảnh hồ sơ lưu trữ sơ đồ đập'),
  mauGhim: z.string().describe('Màu ghim mốc dự án'),
  mauMoc: z.string().describe('Màu dấu mộc đỏ'),
  chuMoc: z.string().describe('Chữ trên dấu mộc'),
  phongToCuoi: z.number().describe('Độ phóng to cuối cùng của hồ sơ'),
  gocPhong: z.string().describe('Tâm phóng to của hồ sơ'),
  toiBanDo: z.number().describe('Độ tối lớp phủ bản đồ'),
});

const GhimSvg = ({co, mau}) => (
  <svg width={co} height={co * 1.333} viewBox="0 0 60 80" style={{display: 'block'}}>
    <path
      d="M30 4 C15.6 4 4 15.6 4 30 C4 49.5 30 76 30 76 C30 76 56 49.5 56 30 C56 15.6 44.4 4 30 4 Z"
      fill={mau}
      stroke="#fdfaf1"
      strokeWidth={3}
    />
    <circle cx="30" cy="30" r="10" fill="#fdfaf1" />
  </svg>
);

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---- Camera trượt chậm trên mặt bàn / bản đồ (chạy suốt shot) ----
  const camScale = interpolate(frame, [0, 149, 296], [1.0, 1.08, 1.16], kep);
  const camX = interpolate(frame, [0, 149, 296], [-36, 30, 76], kep);
  const camY = interpolate(frame, [0, 149, 296], [22, -26, -58], kep);

  // ---- 3 ghim dự án cắm xuống bản đồ (nửa đầu) ----
  const g1 = spring({frame: frame - 4, fps, config: {damping: 15, mass: 0.7, stiffness: 110}});
  const g2 = spring({frame: frame - 55, fps, config: {damping: 15, mass: 0.7, stiffness: 110}});
  const g3 = spring({frame: frame - 95, fps, config: {damping: 15, mass: 0.7, stiffness: 110}});

  // ---- Hồ sơ lưu trữ trượt vào + camera punch-in (nửa sau, từ frame 149) ----
  const vaoF = interpolate(frame, [149, 186], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const tyF = (1 - vaoF) * 1120;
  const scF = interpolate(frame, [149, 178, 296], [1.02, 1.06, props.phongToCuoi], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });

  // ---- Dấu mộc đỏ dập xuống ----
  const stS = spring({frame: frame - 250, fps, config: {damping: 16, mass: 0.6, stiffness: 220}});
  const stScale = interpolate(stS, [0, 1], [2.0, 1]);
  const stOp = interpolate(frame, [250, 253], [0, 0.88], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#171310'}}>
      {/* ================= LỚP BẢN ĐỒ + GHIM ================= */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
          transform: `translate(${camX}px, ${camY}px) scale(${camScale})`,
          transformOrigin: '50% 50%',
        }}
      >
        <Interactive.Div
          name="Bản đồ Arizona"
          from={0}
          durationInFrames={296}
          style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
        >
          <AnhNen anh={props.anhBanDo} tu={1.02} den={1.1} goc="50% 50%" toi={props.toiBanDo} />
        </Interactive.Div>

        {/* Ghim 2 */}
        <Interactive.Div
          name="Ghim dự án 2"
          from={55}
          durationInFrames={241}
          style={{position: 'absolute', left: 1120, top: 250, width: 120, height: 160}}
        >
          <div
            style={{
              position: 'absolute',
              left: 24,
              top: 0,
              opacity: g2,
              transform: `translateY(${(1 - g2) * -60}px) scale(${0.5 + 0.5 * g2})`,
              transformOrigin: '50% 0%',
            }}
          >
            <GhimSvg co={72} mau={props.mauGhim} />
          </div>
        </Interactive.Div>

        {/* Ghim 3 */}
        <Interactive.Div
          name="Ghim dự án 3"
          from={95}
          durationInFrames={201}
          style={{position: 'absolute', left: 1390, top: 570, width: 120, height: 160}}
        >
          <div
            style={{
              position: 'absolute',
              left: 24,
              top: 0,
              opacity: g3,
              transform: `translateY(${(1 - g3) * -60}px) scale(${0.5 + 0.5 * g3})`,
              transformOrigin: '50% 0%',
            }}
          >
            <GhimSvg co={72} mau={props.mauGhim} />
          </div>
        </Interactive.Div>

        {/* Ghim 1 + ảnh minh họa đập lốp xe */}
        <Interactive.Div
          name="Ghim dự án 1 và ảnh đập lốp xe"
          from={4}
          durationInFrames={292}
          style={{position: 'absolute', left: 200, top: 408, width: 660, height: 400}}
        >
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 660,
              height: 400,
              opacity: g1,
              transform: `translateY(${(1 - g1) * 60}px) scale(${0.55 + 0.45 * g1})`,
              transformOrigin: '50% 8%',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 70,
                width: 660,
                height: 326,
                boxSizing: 'border-box',
                background: '#f7f0de',
                border: '10px solid #fdfaf1',
                boxShadow: '0 22px 44px rgba(0,0,0,0.42)',
                transform: 'rotate(-2.5deg)',
              }}
            >
              <Img
                src={src(props.anhInset)}
                name="Ảnh đập lốp xe"
                style={{width: '100%', height: '100%', objectFit: 'contain'}}
              />
            </div>
            <div style={{position: 'absolute', left: 294, top: 0}}>
              <GhimSvg co={72} mau={props.mauGhim} />
            </div>
          </div>
        </Interactive.Div>
      </div>

      {/* ================= LỚP HỒ SƠ LƯU TRỮ ================= */}
      <Interactive.Div
        name="Hồ sơ lưu trữ công văn"
        from={149}
        durationInFrames={147}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateY(${tyF}px) scale(${scF})`,
            transformOrigin: props.gocPhong,
            boxShadow: '0 -40px 90px rgba(0,0,0,0.55)',
          }}
        >
          <Img
            src={src(props.anhHoSo)}
            name="Sơ đồ hồ sơ Dam #2"
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />

          <Interactive.Div
            name="Dấu mộc đỏ huỷ dự án"
            from={250}
            durationInFrames={46}
            style={{position: 'absolute', left: 740, top: 342, width: 440, height: 440}}
          >
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: 440,
                height: 440,
                opacity: stOp,
                mixBlendMode: 'multiply',
                transform: `scale(${stScale}) rotate(-13deg)`,
                transformOrigin: '50% 50%',
              }}
            >
              <svg width={440} height={440} viewBox="0 0 440 440">
                <circle cx="220" cy="220" r="196" fill="none" stroke={props.mauMoc} strokeWidth="14" />
                <circle cx="220" cy="220" r="166" fill="none" stroke={props.mauMoc} strokeWidth="5" />
                <text
                  x="220"
                  y="248"
                  textAnchor="middle"
                  fontFamily={FONT}
                  fontSize="78"
                  fontWeight="900"
                  letterSpacing="6"
                  fill={props.mauMoc}
                >
                  {props.chuMoc}
                </text>
              </svg>
            </div>
          </Interactive.Div>
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
