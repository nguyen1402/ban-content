import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền toàn cảnh đập lốp xe nhìn từ góc cao chếch 3/4'),
  anh_xe: z.string().describe('Ảnh cắt trong suốt chiếc xe đầu kéo nhìn từ góc cao'),
  chu: z.string().describe('Nhãn số đo duy nhất trên khung hình (ngắn: số / năm / tên)'),
  mau: z.string().describe('Màu vàng của nét gióng và chữ số đo'),
  co_chu: z.number().describe('Cỡ chữ của nhãn số đo (px)'),
  do_day: z.number().describe('Độ dày nét gióng (px)'),
  rong_xe: z.number().describe('Chiều rộng ảnh xe đầu kéo khi đặt vào khung (px)'),
  do_day_nen: z.number().describe('Độ tối phủ lên ảnh nền (0..0.5)'),
});

const L_X1 = 400, L_Y1 = 760, L_X2 = 1142, L_Y2 = 562;
const L_LEN = Math.hypot(L_X2 - L_X1, L_Y2 - L_Y1);
const L_ANG = (Math.atan2(L_Y2 - L_Y1, L_X2 - L_X1) * 180) / Math.PI;

const C_X1 = 400, C_Y1 = 760, C_X2 = 428, C_Y2 = 887;
const C_LEN = Math.hypot(C_X2 - C_X1, C_Y2 - C_Y1);

const R_X1 = 1142, R_Y1 = 562, R_X2 = 1214, R_Y2 = 884;
const R_LEN = Math.hypot(R_X2 - R_X1, R_Y2 - R_Y1);

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const kieuNhan = {
    fontFamily: FONT,
    fontWeight: 800,
    fontSize: props.co_chu,
    color: props.mau,
    lineHeight: 1,
    whiteSpace: 'nowrap',
    letterSpacing: '0.01em',
    textShadow: '0 6px 24px rgba(0,0,0,0.85), 0 2px 6px rgba(0,0,0,0.6)',
  };

  // ---------- BEAT 1 : vạch chiều cao (from frame 2) ----------
  const fCao = frame - 2;
  const pCao = interpolate(fCao, [0, 24], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const oCao = interpolate(fCao, [14, 30], [0, 1], {...kep, easing: Easing.out(Easing.quad)});

  // ---------- BEAT 2 : vạch chiều dài (from frame 113) ----------
  const fDai = frame - 113;
  const pDai = interpolate(fDai, [0, 30], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const oDai = interpolate(fDai, [24, 40], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const xDai = interpolate(fDai, [24, 40], [-40, 0], {...kep, easing: Easing.out(Easing.cubic)});

  // ---------- BEAT 3 : xe đầu kéo trượt vào (from frame 162) ----------
  const fXe = frame - 162;
  const spXe = spring({frame: fXe, fps, config: {damping: 22, stiffness: 78, mass: 1.15}});
  const txXe = interpolate(spXe, [0, 1], [-460, 0]);
  const oXe = interpolate(fXe, [0, 18], [0, 1], {...kep, easing: Easing.out(Easing.quad)});

  // ---------- BEAT 4 : vạch bề rộng (from frame 252) ----------
  const fRong = frame - 252;
  const pRong = interpolate(fRong, [0, 26], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const oRong = interpolate(fRong, [18, 34], [0, 1], {...kep, easing: Easing.out(Easing.quad)});

  const rongXe = props.rong_xe;
  const caoTruck = Math.round(rongXe * (419 / 700));

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f0c'}}>
      {/* ---------- NỀN : toàn cảnh đập lốp xe, góc cao 3/4, trôi chậm ---------- */}
      <Interactive.Div
        name="Nền toàn cảnh đập lốp xe góc cao"
        from={0}
        durationInFrames={330}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anh_nen} tu={1.02} den={1.13} goc="52% 44%" toi={props.do_day_nen} />
      </Interactive.Div>

      {/* ---------- BEAT 1 : vạch gióng chiều cao (không chữ) ---------- */}
      <Interactive.Div
        name="Vạch gióng chiều cao"
        from={2}
        durationInFrames={328}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg
          width={1920}
          height={1080}
          style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}
        >
          <line
            x1={C_X1}
            y1={C_Y1}
            x2={C_X2}
            y2={C_Y2}
            stroke={props.mau}
            strokeWidth={props.do_day}
            strokeLinecap="round"
            strokeDasharray={C_LEN}
            strokeDashoffset={C_LEN * (1 - pCao)}
          />
          <g opacity={oCao} stroke={props.mau} strokeWidth={props.do_day} strokeLinecap="round">
            <line x1={380.5} y1={764.3} x2={419.5} y2={755.7} />
            <line x1={408.5} y1={891.3} x2={447.5} y2={882.7} />
          </g>
        </svg>
      </Interactive.Div>

      {/* ---------- BEAT 2 : vạch gióng chiều dài + nhãn số đo DUY NHẤT ---------- */}
      <Interactive.Div
        name="Vạch gióng chiều dài và nhãn số đo"
        from={113}
        durationInFrames={217}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg
          width={1920}
          height={1080}
          style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}
        >
          <line
            x1={L_X1}
            y1={L_Y1}
            x2={L_X2}
            y2={L_Y2}
            stroke={props.mau}
            strokeWidth={props.do_day}
            strokeLinecap="round"
            strokeDasharray={L_LEN}
            strokeDashoffset={L_LEN * (1 - pDai)}
          />
          <g opacity={oDai} stroke={props.mau} strokeWidth={props.do_day} strokeLinecap="round">
            <line x1={394.3} y1={738.8} x2={405.7} y2={781.3} />
            <line x1={1136.3} y1={540.8} x2={1147.7} y2={583.3} />
          </g>
        </svg>
        <div
          style={{
            position: 'absolute',
            left: 1162,
            top: 492,
            ...kieuNhan,
            opacity: oDai,
            transform: `translateX(${xDai}px)`,
          }}
        >
          {props.chu}
        </div>
      </Interactive.Div>

      {/* ---------- BEAT 3 : xe đầu kéo trượt vào, song song thân đập ---------- */}
      <Interactive.Div
        name="Xe đầu kéo cắt ghép so sánh chiều dài"
        from={162}
        durationInFrames={168}
        style={{position: 'absolute', left: 315, top: 160, width: rongXe, height: caoTruck}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: rongXe,
            height: caoTruck,
            transform: `translateX(${txXe}px) rotate(${L_ANG}deg)`,
            transformOrigin: 'center center',
            opacity: oXe,
          }}
        >
          <Img
            src={src(props.anh_xe)}
            name="Xe đầu kéo"
            from={162}
            durationInFrames={168}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              filter: 'drop-shadow(0 18px 34px rgba(0,0,0,0.55))',
            }}
          />
        </div>
      </Interactive.Div>

      {/* ---------- BEAT 4 : vạch bề rộng (không chữ) ---------- */}
      <Interactive.Div
        name="Vạch gióng bề rộng"
        from={252}
        durationInFrames={78}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg
          width={1920}
          height={1080}
          style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}
        >
          <line
            x1={R_X1}
            y1={R_Y1}
            x2={R_X2}
            y2={R_Y2}
            stroke={props.mau}
            strokeWidth={props.do_day}
            strokeLinecap="round"
            strokeDasharray={R_LEN}
            strokeDashoffset={R_LEN * (1 - pRong)}
          />
          <g opacity={oRong} stroke={props.mau} strokeWidth={props.do_day} strokeLinecap="round">
            <line x1={1120.5} y1={566.8} x2={1163.5} y2={557.2} />
            <line x1={1192.5} y1={888.8} x2={1235.5} y2={879.2} />
          </g>
        </svg>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
