import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const CL_EASE = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)};

/* ------------------------------------------------------------------ */
/*  LỚP 1 — PHÒNG LÀM VIỆC CŨ (0 → 96)                                 */
/* ------------------------------------------------------------------ */
const LopPhongLamViec = ({anh}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 66, 94], [1, 1, 0], CL);
  return (
    <AbsoluteFill style={{opacity: op}}>
      <AnhNen anh={anh} tu={1} den={1.1} goc="50% 45%" toi={0.1} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  LỚP 2 — BẢN ĐỒ THỦY LỢI (82 → 420)                                 */
/* ------------------------------------------------------------------ */
const LopBanDo = ({anh}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 22], [0, 1], CL);
  return (
    <AbsoluteFill style={{opacity: op}}>
      <AnhNen anh={anh} tu={1.02} den={1.16} goc="45% 50%" toi={0.05} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  LỚP 3 — VẠCH GẠCH CHÉO ĐỎ (bế tắc)                                  */
/* ------------------------------------------------------------------ */
const VachCheoBeTac = ({mau, day, so}) => {
  const f = useCurrentFrame();
  const net = [];

  for (let i = 0; i < so; i++) {
    const st = 2 + i * 14;
    const p = interpolate(f, [st, st + 20], [0, 1], CL_EASE);
    if (p <= 0) continue;
    const x1 = 960 + i * 64;
    const y1 = 452;
    net.push({d: `M ${x1} ${y1} L ${x1 + 156} ${y1 + 258}`, p});
  }

  const dai = [
    {d: 'M 700 902 L 1508 372', st: 118, du: 30},
    {d: 'M 742 292 L 1626 872', st: 146, du: 30},
  ];
  dai.forEach((l) => {
    const p = interpolate(f, [l.st, l.st + l.du], [0, 1], CL_EASE);
    if (p > 0) net.push({d: l.d, p});
  });

  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: 'absolute', left: 0, top: 0}}>
        {net.map((n, i) => (
          <path
            key={i}
            d={n.d}
            fill="none"
            stroke={mau}
            strokeWidth={day}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1"
            strokeDashoffset={1 - n.p}
            opacity={0.82}
          />
        ))}
      </svg>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  LỚP 4 — LÀM TỐI NỀN BẢN ĐỒ (218 → 420)                             */
/* ------------------------------------------------------------------ */
const LamToiBanDo = ({doToi}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 45], [0, 1], CL);
  const trong = doToi * 0.3;
  const ngoai = doToi;
  return (
    <AbsoluteFill
      style={{
        opacity: op,
        background: `radial-gradient(circle at 40% 46%, rgba(0,0,0,${trong}) 0%, rgba(0,0,0,${ngoai}) 78%)`,
      }}
    />
  );
};

/* ------------------------------------------------------------------ */
/*  LỚP 5 — MỐC THỜI GIAN 1996 (4 → 100)                               */
/* ------------------------------------------------------------------ */
const MocThoiGian = ({chu, co}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 200, mass: 1}});
  const op = interpolate(f, [0, 12, 78, 96], [0, 1, 1, 0], CL);
  const y = interpolate(s, [0, 1], [26, 0]);
  const gach = interpolate(f, [10, 34], [0, 1], CL_EASE);

  return (
    <div style={{position: 'absolute', left: 0, top: 0, opacity: op, transform: `translateY(${y}px)`}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 800,
          letterSpacing: '14px',
          color: '#f6e7bd',
          lineHeight: 1,
          textShadow: '0 12px 34px rgba(0,0,0,0.75)',
        }}
      >
        {chu}
      </div>
      <div
        style={{
          marginTop: 16,
          width: 330,
          height: 6,
          background: VANG,
          transform: `scaleX(${gach})`,
          transformOrigin: 'left center',
          opacity: 0.9,
        }}
      />
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  LỚP 6 — CHÂN DUNG NHÂN VẬT MỚI (218 → 420)                          */
/* ------------------------------------------------------------------ */
const ChanDungNhanVat = ({anh, cao}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 200, mass: 1.2}});
  const tx = (1 - s) * 800;
  const rot = (1 - s) * -4;
  const drift = interpolate(f, [0, 202], [0, -18], CL);
  const rong = cao * (585 / 700);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: rong,
        height: cao,
        transform: `translate(${tx}px, ${drift}px) rotate(${rot}deg)`,
        filter: 'drop-shadow(-26px 20px 46px rgba(0,0,0,0.85))',
      }}
    >
      <Img
        src={src(anh)}
        name="Chân dung nhân vật mới"
        style={{width: '100%', height: '100%', objectFit: 'contain'}}
      />
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  LỚP 7 — BẰNG CẤP NGOÀI NGÀNH (300 → 420)                           */
/* ------------------------------------------------------------------ */
const BangCapNgoaiNganh = ({anh, rong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const cao = (rong * 430) / 700;

  const s = spring({frame: f, fps, config: {damping: 24, mass: 0.9, stiffness: 95}});
  const tx = (1 - s) * -860;
  const rotBase = interpolate(s, [0, 1], [-15, -5], CL);
  const rotDrift = interpolate(f, [0, 120], [0, 1.6], CL);

  const stampF = Math.max(0, f - 40);
  const stamp = spring({frame: stampF, fps, config: {damping: 13, mass: 0.65, stiffness: 190}});

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: rong,
        height: cao,
        transform: `translateX(${tx}px) rotate(${rotBase + rotDrift}deg)`,
        background: '#efe6d2',
        padding: 10,
        boxSizing: 'border-box',
        boxShadow: '0 34px 70px rgba(0,0,0,0.7), 0 0 0 2px rgba(255,255,255,0.18)',
      }}
    >
      <div style={{position: 'absolute', left: 10, top: 10, right: 10, bottom: 10, overflow: 'hidden'}}>
        <Img
          src={src(anh)}
          name="Bằng cấp ngoài ngành"
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
      </div>

      <div
        style={{
          position: 'absolute',
          right: 42,
          bottom: 34,
          width: 176,
          height: 176,
          borderRadius: '50%',
          border: '7px solid rgba(124,48,34,0.5)',
          boxShadow: 'inset 0 0 0 7px rgba(255,255,255,0.14), inset 0 0 22px rgba(124,48,34,0.4)',
          transform: `scale(${stamp}) rotate(-9deg)`,
          opacity: Math.min(1, stamp * 1.4),
          mixBlendMode: 'multiply',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 20,
            top: 20,
            right: 20,
            bottom: 20,
            borderRadius: '50%',
            border: '3px solid rgba(124,48,34,0.42)',
          }}
        />
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  SCHEMA                                                            */
/* ------------------------------------------------------------------ */
export const schema = z.object({
  anhPhongLamViec: z.string().describe('Ảnh phòng làm việc nông nghiệp cũ'),
  anhBanDo: z.string().describe('Ảnh bản đồ quy hoạch thủy lợi trên bàn'),
  anhNhanVat: z.string().describe('Ảnh tách nền chân dung nhân vật mới'),
  anhBangCap: z.string().describe('Ảnh bằng cấp ngành nghề khác biệt'),
  namMoc: z.string().describe('Năm mốc thời gian hiển thị'),
  coNam: z.number().describe('Cỡ chữ năm mốc (px)'),
  mauVach: z.string().describe('Màu vạch gạch chéo đỏ'),
  doDamVach: z.number().describe('Độ dày nét vạch chéo (px)'),
  soVach: z.number().describe('Số vạch gạch chéo ngắn'),
  coNhanVat: z.number().describe('Chiều cao chân dung nhân vật (px)'),
  viTriNhanVat: z.number().describe('Toạ độ trái của chân dung (px)'),
  coBangCap: z.number().describe('Chiều rộng khung bằng cấp (px)'),
  doToiNen: z.number().describe('Độ tối lớp phủ nền bản đồ (0–0.5)'),
});

/* ------------------------------------------------------------------ */
/*  CẢNH                                                              */
/* ------------------------------------------------------------------ */
export const Canh = (props) => {
  const {
    anhPhongLamViec,
    anhBanDo,
    anhNhanVat,
    anhBangCap,
    namMoc,
    coNam,
    mauVach,
    doDamVach,
    soVach,
    coNhanVat,
    viTriNhanVat,
    coBangCap,
    doToiNen,
  } = props;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0906'}}>
      {/* 1. Phòng làm việc cũ */}
      <Interactive.Div
        name="Phòng làm việc cũ"
        from={0}
        durationInFrames={96}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopPhongLamViec anh={anhPhongLamViec} />
      </Interactive.Div>

      {/* 2. Bản đồ thủy lợi */}
      <Interactive.Div
        name="Bản đồ thủy lợi"
        from={82}
        durationInFrames={338}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopBanDo anh={anhBanDo} />
      </Interactive.Div>

      {/* 3. Vạch gạch chéo đỏ */}
      <Interactive.Div
        name="Vạch gạch chéo bế tắc"
        from={82}
        durationInFrames={338}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <VachCheoBeTac mau={mauVach} day={doDamVach} so={soVach} />
      </Interactive.Div>

      {/* 4. Làm tối nền bản đồ */}
      <Interactive.Div
        name="Làm tối nền bản đồ"
        from={218}
        durationInFrames={202}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LamToiBanDo doToi={doToiNen} />
      </Interactive.Div>

      {/* 5. Mốc thời gian 1996 */}
      <Interactive.Div
        name="Mốc thời gian"
        from={4}
        durationInFrames={96}
        style={{position: 'absolute', left: 130, top: 96}}
      >
        <MocThoiGian chu={namMoc} co={coNam} />
      </Interactive.Div>

      {/* 6. Chân dung nhân vật mới */}
      <Interactive.Div
        name="Chân dung nhân vật mới"
        from={218}
        durationInFrames={202}
        style={{position: 'absolute', left: viTriNhanVat, top: 250}}
      >
        <ChanDungNhanVat anh={anhNhanVat} cao={coNhanVat} />
      </Interactive.Div>

      {/* 7. Bằng cấp ngoài ngành */}
      <Interactive.Div
        name="Bằng cấp ngoài ngành"
        from={300}
        durationInFrames={120}
        style={{position: 'absolute', left: 100, top: 570}}
      >
        <BangCapNgoaiNganh anh={anhBangCap} rong={coBangCap} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
