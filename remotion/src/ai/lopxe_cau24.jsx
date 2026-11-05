import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const KEP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anh_nguoi_linh: z.string().describe('Ảnh tư liệu người lính thủy quân lục chiến (nhìn từ phía sau)'),
  huy_hieu: z.string().describe('Huy hiệu Thủy quân lục chiến Hoa Kỳ (cut-out)'),
  anh_berkeley: z.string().describe('Ảnh khuôn viên tháp Sather Tower - UC Berkeley'),
  bang_tien_si: z.string().describe('Bằng tiến sĩ cuộn da vintage (cut-out)'),
  anh_lab: z.string().describe('Ảnh phòng thí nghiệm kỹ thuật điện retro'),
  anh_vi_mach: z.string().describe('Ảnh cận cảnh bàn tay đo vi mạch'),
  chu_berkeley: z.string().describe('Chữ Berkeley hiện dưới tấm bằng'),
  chu_tucson: z.string().describe('Chữ Tucson ở góc dưới màn hình'),
  so_bang_sang_che: z.number().describe('Số bằng sáng chế hiển thị lớn ở giữa'),
  co_chu_berkeley: z.number().describe('Cỡ chữ Berkeley (px)'),
  co_chu_tucson: z.number().describe('Cỡ chữ Tucson (px)'),
  co_so_7: z.number().describe('Cỡ con số 7 (px)'),
  mau_vang: z.string().describe('Màu vàng ánh kim của con số 7'),
  do_toi_nen: z.number().describe('Độ tối lớp phủ khi các bản vẽ xuất hiện (0-0.5)'),
});

/* ---------- vệt sáng lướt ---------- */
const LuotSang = ({bat_dau, ket_thuc, mau}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [bat_dau, ket_thuc], [0, 1], KEP);
  if (p <= 0 || p >= 1) return null;
  const x = interpolate(p, [0, 1], [-900, 2900]);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          top: -400,
          left: x,
          width: 340,
          height: 1900,
          transform: 'rotate(16deg)',
          background: `linear-gradient(90deg, rgba(255,255,255,0) 0%, ${mau} 45%, rgba(255,255,255,0) 100%)`,
        }}
      />
    </div>
  );
};

/* ---------- một bản vẽ bằng sáng chế (sơ đồ kỹ thuật trừu tượng) ---------- */
const BanVe = ({i}) => {
  const v = i % 3;
  return (
    <svg width={280} height={380} viewBox="0 0 280 380">
      <rect x={1.5} y={1.5} width={277} height={377} fill="rgba(9,24,46,0.94)" stroke="#7fc0f5" strokeWidth={3} />
      <rect x={14} y={14} width={252} height={352} fill="none" stroke="rgba(127,192,245,0.35)" strokeWidth={1.5} />
      <rect x={30} y={34} width={150} height={9} fill="#9ad2ff" opacity={0.85} />
      <rect x={30} y={50} width={104} height={6} fill="rgba(154,210,255,0.55)" />

      {v === 0 && (
        <g stroke="#9ad2ff" fill="none">
          <circle cx={140} cy={190} r={58} strokeWidth={2.5} />
          <circle cx={140} cy={190} r={22} strokeWidth={2} />
          <line x1={82} y1={190} x2={198} y2={190} strokeWidth={1.6} strokeDasharray="6 6" />
          <line x1={140} y1={132} x2={140} y2={248} strokeWidth={1.6} strokeDasharray="6 6" />
        </g>
      )}
      {v === 1 && (
        <g stroke="#9ad2ff" fill="none">
          <rect x={62} y={128} width={156} height={124} rx={6} strokeWidth={2.5} />
          <rect x={92} y={158} width={96} height={64} rx={4} strokeWidth={1.8} />
          <line x1={62} y1={128} x2={30} y2={106} strokeWidth={1.6} />
          <line x1={218} y1={252} x2={250} y2={274} strokeWidth={1.6} />
          <line x1={92} y1={190} x2={188} y2={190} strokeWidth={1.4} strokeDasharray="5 5" />
        </g>
      )}
      {v === 2 && (
        <g stroke="#9ad2ff" fill="none">
          <path d="M40 240 L110 150 L180 240 Z" strokeWidth={2.5} />
          <circle cx={110} cy={150} r={12} strokeWidth={2} />
          <line x1={110} y1={162} x2={110} y2={252} strokeWidth={1.6} strokeDasharray="6 6" />
          <line x1={40} y1={240} x2={180} y2={240} strokeWidth={2} />
        </g>
      )}

      <rect x={30} y={310} width={220} height={5} fill="rgba(154,210,255,0.4)" />
      <rect x={30} y={324} width={170} height={5} fill="rgba(154,210,255,0.4)" />
      <rect x={30} y={338} width={120} height={5} fill="rgba(154,210,255,0.25)" />
    </svg>
  );
};

const VI_TRI = [
  {left: 400, top: 560, rot: -22},
  {left: 515, top: 470, rot: -14},
  {left: 660, top: 410, rot: -7},
  {left: 820, top: 380, rot: 0},
  {left: 980, top: 410, rot: 7},
  {left: 1125, top: 470, rot: 14},
  {left: 1240, top: 560, rot: 22},
];

const FanBangVe = ({fps, so}) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      {VI_TRI.slice(0, Math.max(0, Math.min(7, Math.round(so)))).map((it, i) => {
        const s = spring({frame: Math.max(0, f - i * 2), fps, config: {damping: 14, mass: 0.9}});
        const left = interpolate(s, [0, 1], [820, it.left]);
        const top = interpolate(s, [0, 1], [330, it.top]);
        const rot = interpolate(s, [0, 1], [0, it.rot]);
        const op = interpolate(s, [0, 0.35], [0, 1], KEP);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left,
              top,
              width: 280,
              height: 380,
              transform: `rotate(${rot}deg)`,
              opacity: op,
            }}
          >
            <BanVe i={i} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const Canh = (props) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---- whip-pan sang Berkeley (frame 104) ---- */
  const txB = interpolate(f, [104, 118], [1500, 0], {...KEP, easing: Easing.out(Easing.cubic)});

  /* ---- wipe sang phòng lab (frame 188) ---- */
  const pW = interpolate(f, [188, 203], [0, 1], {...KEP, easing: Easing.inOut(Easing.cubic)});
  const clipLab = `inset(0% ${(1 - pW) * 100}% 0% 0%)`;

  /* ---- làm tối nền khi các bản vẽ bay ra (frame 281) ---- */
  const doToi = interpolate(f, [281, 298], [0, props.do_toi_nen], KEP);

  /* ---- tấm bằng tiến sĩ (frame 104) ---- */
  const sDip = spring({frame: Math.max(0, f - 104), fps, config: {damping: 14, mass: 0.8}});
  const dipScale = interpolate(sDip, [0, 1], [0.72, 1]);
  const dipOp = interpolate(sDip, [0, 0.5], [0, 1], KEP);
  const dipFloat = interpolate(f, [104, 210], [0, -16], KEP);

  /* ---- chữ Berkeley (frame 142) ---- */
  const sB = spring({frame: Math.max(0, f - 142), fps, config: {damping: 12, mass: 0.6}});
  const scaleB = interpolate(sB, [0, 1], [1.45, 1]);
  const opB = interpolate(f, [142, 147], [0, 1], KEP);
  const flashB = interpolate(f, [142, 152], [26, 0], KEP);

  /* ---- chữ Tucson (frame 238) ---- */
  const opT = interpolate(f, [238, 247], [0, 1], KEP);
  const yT = interpolate(f, [238, 250], [46, 0], {...KEP, easing: Easing.out(Easing.cubic)});

  /* ---- khung ảnh vi mạch (frame 190) ---- */
  const txV = interpolate(f, [190, 206], [160, 0], {...KEP, easing: Easing.out(Easing.cubic)});
  const opV = interpolate(f, [190, 200], [0, 1], KEP);

  /* ---- huy hiệu USMC (frame 66) ---- */
  const txH = interpolate(f, [66, 80], [-540, 0], {...KEP, easing: Easing.out(Easing.cubic)});
  const opH = interpolate(f, [66, 74], [0, 1], KEP);

  /* ---- con số 7 (frame 281) ---- */
  const s7 = spring({frame: Math.max(0, f - 281), fps, config: {damping: 11, mass: 0.6, stiffness: 180}});
  const scale7 = interpolate(s7, [0, 1], [2.4, 1]);
  const op7 = interpolate(s7, [0, 0.3], [0, 1], KEP);

  return (
    <AbsoluteFill style={{backgroundColor: '#05070d', fontFamily: FONT}}>
      {/* ================= 1. ẢNH NGƯỜI LÍNH (frame 0) ================= */}
      <Interactive.Div
        name="Ảnh người lính thủy quân lục chiến"
        from={0}
        durationInFrames={120}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <AnhNen anh={props.anh_nguoi_linh} tu={1} den={1.14} goc="50% 45%" toi={0.3} />
      </Interactive.Div>

      {/* ================= 2. NỀN BERKELEY trượt vào (frame 104) ================= */}
      <Interactive.Div
        name="Nền khuôn viên Berkeley"
        from={104}
        durationInFrames={106}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${txB}px)`,
          }}
        >
          <AnhNen anh={props.anh_berkeley} tu={1.12} den={1} goc="50% 55%" toi={0.12} />
        </div>
      </Interactive.Div>

      {/* ================= 3. BẰNG TIẾN SĨ (frame 104) ================= */}
      <Interactive.Div
        name="Bằng tiến sĩ Berkeley"
        from={104}
        durationInFrames={106}
        style={{position: 'absolute', left: 560, top: 250, width: 800, height: 350}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateY(${dipFloat}px) scale(${dipScale})`,
            opacity: dipOp,
          }}
        >
          <Img
            name="Bằng tiến sĩ"
            from={104}
            src={src(props.bang_tien_si)}
            style={{width: 800, height: 345, objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      {/* ================= 4. CHỮ BERKELEY (frame 142) ================= */}
      <Interactive.Div
        name="Chữ Berkeley"
        from={142}
        durationInFrames={68}
        style={{position: 'absolute', left: 0, top: 640, width: 1920, height: 200}}
      >
        <div
          style={{
            width: 1920,
            textAlign: 'center',
            fontSize: props.co_chu_berkeley,
            fontWeight: 800,
            letterSpacing: 6,
            color: '#ffffff',
            opacity: opB,
            transform: `scale(${scaleB})`,
            textShadow: `0 0 ${flashB}px rgba(255,255,255,0.95), 0 8px 28px rgba(0,0,0,0.75)`,
          }}
        >
          {props.chu_berkeley}
        </div>
      </Interactive.Div>

      {/* ================= 5. NỀN PHÒNG LAB - wipe (frame 188) ================= */}
      <Interactive.Div
        name="Nền phòng thí nghiệm điện"
        from={188}
        durationInFrames={164}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div style={{position: 'absolute', inset: 0, clipPath: clipLab, WebkitClipPath: clipLab}}>
          <AnhNen anh={props.anh_lab} tu={1.2} den={1} goc="45% 50%" toi={0.18} />
        </div>
      </Interactive.Div>

      {/* ================= 6. KHUNG ẢNH VI MẠCH (frame 190) ================= */}
      <Interactive.Div
        name="Khung ảnh đo vi mạch"
        from={190}
        durationInFrames={162}
        style={{position: 'absolute', left: 1040, top: 190, width: 760, height: 428}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateX(${txV}px)`,
            opacity: opV,
            border: '4px solid rgba(240,245,255,0.9)',
            boxShadow: '0 18px 46px rgba(0,0,0,0.55)',
            overflow: 'hidden',
            backgroundColor: '#0b1220',
          }}
        >
          <Img
            name="Cận cảnh vi mạch"
            from={190}
            src={src(props.anh_vi_mach)}
            style={{width: 760, height: 428, objectFit: 'cover'}}
          />
        </div>
      </Interactive.Div>

      {/* ================= 7. CHỮ TUCSON (frame 238) ================= */}
      <Interactive.Div
        name="Chữ Tucson"
        from={238}
        durationInFrames={114}
        style={{position: 'absolute', left: 1130, top: 852, width: 700, height: 150}}
      >
        <div
          style={{
            fontSize: props.co_chu_tucson,
            fontWeight: 800,
            letterSpacing: 4,
            color: '#ffffff',
            opacity: opT,
            transform: `translateY(${yT}px)`,
            textShadow: '0 8px 26px rgba(0,0,0,0.8)',
          }}
        >
          {props.chu_tucson}
        </div>
      </Interactive.Div>

      {/* ================= 8. HUY HIỆU USMC (frame 66) ================= */}
      <Interactive.Div
        name="Huy hiệu Thủy quân lục chiến"
        from={66}
        durationInFrames={54}
        style={{position: 'absolute', left: 80, top: 200, width: 480, height: 556, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateX(${txH}px)`,
            opacity: opH,
          }}
        >
          <Img
            name="Huy hiệu USMC"
            from={66}
            src={src(props.huy_hieu)}
            style={{width: 480, height: 556, objectFit: 'contain'}}
          />
          <LuotSang bat_dau={4} ket_thuc={20} mau="rgba(255,255,255,0.55)" />
        </div>
      </Interactive.Div>

      {/* ================= 9. LỚP TỐI NỀN (frame 281) ================= */}
      <Interactive.Div
        name="Lớp làm tối nền"
        from={281}
        durationInFrames={71}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div style={{position: 'absolute', inset: 0, backgroundColor: '#05070d', opacity: doToi}} />
      </Interactive.Div>

      {/* ================= 10. 7 BẢN VẼ BẰNG SÁNG CHẾ (frame 281) ================= */}
      <Interactive.Div
        name="Bảy bản vẽ bằng sáng chế"
        from={281}
        durationInFrames={71}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <FanBangVe fps={fps} so={props.so_bang_sang_che} />
      </Interactive.Div>

      {/* ================= 11. CON SỐ 7 (frame 281) ================= */}
      <Interactive.Div
        name="Con số 7"
        from={281}
        durationInFrames={71}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            fontSize: props.co_so_7,
            fontWeight: 900,
            lineHeight: 1,
            color: props.mau_vang,
            WebkitTextStroke: '10px rgba(8,14,26,0.9)',
            opacity: op7,
            transform: `scale(${scale7})`,
          }}
        >
          {props.so_bang_sang_che}
        </div>
      </Interactive.Div>

      {/* ================= 12. VỆT SÁNG CUỐI (frame 306) ================= */}
      <Interactive.Div
        name="Vệt sáng kết thúc"
        from={306}
        durationInFrames={46}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LuotSang bat_dau={0} ket_thuc={32} mau="rgba(255,246,214,0.62)" />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
