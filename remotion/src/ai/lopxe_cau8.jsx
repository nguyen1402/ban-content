import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh bình nguyên King Anvil (nền)'),
  anh_nguoi: z.string().describe('Ảnh tách nền Stewart Honig'),
  anh_xoi: z.string().describe('Ảnh mạng lưới rãnh xói mòn (nền)'),
  anh_can: z.string().describe('Ảnh cận cảnh vách đất xói lở (inset)'),
  anh_cuoi: z.string().describe('Ảnh lòng suối Brawley Wash (nền)'),
  quang_nen: z.number().describe('Độ trượt ngang của bình nguyên King Anvil (px)'),
  nguoi_cao: z.number().describe('Chiều cao bóng Stewart Honig (px)'),
  so_km: z.number().describe('Mốc km hiển thị trên bộ đếm'),
  giay_dem: z.number().describe('Thời gian chạy bộ đếm (giây)'),
  co_dem: z.number().describe('Cỡ chữ bộ đếm (px)'),
  nhan_dem: z.string().describe('Nhãn dưới bộ đếm'),
  mau_do_dac: z.string().describe('Màu đường đo đạc'),
  quang_cuoi: z.number().describe('Độ trượt dọc của lòng suối Brawley Wash (px)'),
});

/* ---------- Bóng lưng Stewart Honig (tiền cảnh, parallax) ---------- */
const NguoiStewart = ({anh, cao}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 10, 110, 130], [0, 1, 1, 0], kep);
  const tx = interpolate(f, [0, 130], [0, -54], {...kep, easing: Easing.inOut(Easing.quad)});
  const ty = interpolate(f, [0, 130], [0, 7], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        height: cao,
        width: 'auto',
        display: 'block',
        opacity: op,
        transform: `translate(${tx}px, ${ty}px)`,
        filter: 'brightness(0.74) contrast(1.06) saturate(0.92)',
      }}
    />
  );
};

/* ---------- Reveal mask: mặt đất nứt toác lộ mạng lưới rãnh xói mòn ---------- */
const MangLuoiXoiMon = ({anh}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [3, 30], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const e = (1 - p) * 46;
  const clip = `inset(${e}% ${e}% ${e}% ${e}%)`;
  return (
    <div style={{position: 'absolute', inset: 0, clipPath: clip, WebkitClipPath: clip}}>
      <AnhNen anh={anh} tu={1.12} den={1.02} goc="50% 45%" toi={0.05} />
    </div>
  );
};

/* ---------- Inset card: cận cảnh độ sâu vách đất ---------- */
const InsetVachDat = ({anh}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200, mass: 0.9}, durationInFrames: 26});
  const tx = (1 - vao) * 640;
  const hien = interpolate(f, [0, 8, 74, 92], [0, 1, 1, 0], kep);
  const sc = interpolate(f, [74, 92], [1, 1.07], kep);
  return (
    <div
      style={{
        width: 560,
        height: 360,
        opacity: hien,
        transform: `translateX(${tx}px) scale(${sc})`,
        transformOrigin: '100% 50%',
        border: '2px solid rgba(255,255,255,0.55)',
        boxShadow: '0 18px 46px rgba(0,0,0,0.42)',
        overflow: 'hidden',
        backgroundColor: '#111',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}} />
    </div>
  );
};

/* ---------- Đường viền đo đạc thanh mảnh chạy dọc các nhánh chính ---------- */
const DuongDoDac = ({mau}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 38], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  const dash = 1500;
  const off = (1 - p) * dash;
  const op = interpolate(f, [0, 5, 50, 64], [0, 1, 1, 0], kep);
  const ringP = interpolate(f, [34, 50], [0, 1], kep);
  const ringC = 2 * Math.PI * 26;
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, opacity: op}}>
      <g
        fill="none"
        stroke={mau}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={dash}
        strokeDashoffset={off}
        opacity={0.9}
      >
        <path d="M 246 232 C 470 402, 762 566, 1178 802" />
        <path d="M 432 154 C 642 372, 878 558, 1178 802" />
        <path d="M 1734 292 C 1522 470, 1320 646, 1178 802" />
        <path d="M 232 884 C 520 910, 878 858, 1178 802" />
      </g>
      <circle
        cx={1178}
        cy={802}
        r={26}
        fill="none"
        stroke={mau}
        strokeWidth={3}
        strokeDasharray={ringC}
        strokeDashoffset={(1 - ringP) * ringC}
        opacity={ringP > 0.02 ? 0.95 : 0}
      />
    </svg>
  );
};

/* ---------- Bộ đếm 90 KM ---------- */
const BoDem = ({so, donVi, giay, co, nhan}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 12], [0, 1], kep);
  const ty = interpolate(f, [0, 16], [26, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{opacity: op, transform: `translateY(${ty}px)`}}>
      <div style={{fontFamily: FONT, color: '#FFFFFF', fontWeight: 700, letterSpacing: 2, textShadow: '0 4px 20px rgba(0,0,0,0.65)'}}>
        <SoDem so={so} don_vi={donVi} giay={giay} co={co} />
      </div>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 52,
          fontWeight: 600,
          letterSpacing: 8,
          color: VANG,
          marginTop: 10,
          textShadow: '0 3px 14px rgba(0,0,0,0.65)',
        }}
      >
        {nhan}
      </div>
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0b0d'}}>
      {/* BEAT 1 — bình nguyên King Anvil, camera trượt ngang chậm */}
      <Interactive.Div
        name="Bình nguyên King Anvil"
        from={0}
        durationInFrames={136}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={props.anh_nen} huong="phai" quang={props.quang_nen} toi={0.1} />
      </Interactive.Div>

      {/* BEAT 1 — bóng lưng Stewart Honig ở mỏm đất tiền cảnh */}
      <Interactive.Div
        name="Bóng lưng Stewart Honig"
        from={0}
        durationInFrames={132}
        style={{position: 'absolute', left: 300, top: 330}}
      >
        <NguoiStewart anh={props.anh_nguoi} cao={props.nguoi_cao} />
      </Interactive.Div>

      {/* BEAT 2 — reveal mask mở ra mạng lưới rãnh xói mòn */}
      <Interactive.Div
        name="Mạng lưới rãnh xói mòn"
        from={108}
        durationInFrames={150}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <MangLuoiXoiMon anh={props.anh_xoi} />
      </Interactive.Div>

      {/* BEAT 2 — inset card cận cảnh vách đất trượt vào góc phải */}
      <Interactive.Div
        name="Cận cảnh vách đất xói lở"
        from={118}
        durationInFrames={92}
        style={{position: 'absolute', left: 1250, top: 130}}
      >
        <InsetVachDat anh={props.anh_can} />
      </Interactive.Div>

      {/* BEAT 4 — lòng suối Brawley Wash, máy trượt theo dòng chảy */}
      <Interactive.Div
        name="Lòng suối Brawley Wash"
        from={246}
        durationInFrames={86}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: interpolate(useCurrentFrame(), [0, 12], [0, 1], kep),
          }}
        >
          <AnhLia anh={props.anh_cuoi} huong="xuong" quang={props.quang_cuoi} toi={0.08} />
        </div>
      </Interactive.Div>

      {/* BEAT 3 — đường đo đạc thanh mảnh chạy dọc các nhánh chính */}
      <Interactive.Div
        name="Đường đo đạc mạng lưới"
        from={202}
        durationInFrames={66}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DuongDoDac mau={props.mau_do_dac} />
      </Interactive.Div>

      {/* BEAT 3 — bộ đếm 90 KM + nhãn GẦN 90 KM */}
      <Interactive.Div
        name="Bộ đếm 90 KM"
        from={202}
        durationInFrames={130}
        style={{position: 'absolute', left: 120, top: 700}}
      >
        <BoDem
          so={props.so_km}
          donVi="KM"
          giay={props.giay_dem}
          co={props.co_dem}
          nhan={props.nhan_dem}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
