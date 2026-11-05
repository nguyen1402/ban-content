import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Đường dẫn ảnh nền đô thị hối hả'),
  zoomTu: z.number().describe('Tỉ lệ zoom bắt đầu của ảnh nền'),
  zoomDen: z.number().describe('Tỉ lệ zoom kết thúc của ảnh nền'),
  gocZoom: z.string().describe('Gốc zoom của ảnh nền'),
  toiNen: z.number().describe('Độ tối phủ lên ảnh nền (0 - 0.5)'),
  chuKhoa: z.string().describe('Chữ khóa hiện lên khi thoại nhắc sống chậm lại'),
  coChuKhoa: z.number().describe('Cỡ chữ khóa (px)'),
  mauChuKhoa: z.string().describe('Màu chữ khóa'),
  mauGachChan: z.string().describe('Màu gạch chân dưới chữ khóa'),
  chuX: z.number().describe('Toạ độ X của khối chữ khóa'),
  chuY: z.number().describe('Toạ độ Y của khối chữ khóa'),
  mauNhip: z.string().describe('Màu đường nhịp tim ở góc màn hình'),
  rongNhip: z.number().describe('Chiều rộng khung nhịp tim (px)'),
  caoNhip: z.number().describe('Chiều cao khung nhịp tim (px)'),
  nhipX: z.number().describe('Toạ độ X khung nhịp tim'),
  nhipY: z.number().describe('Toạ độ Y khung nhịp tim'),
  tocDoTruot: z.number().describe('Quãng trượt của đường nhịp tim (px)'),
  doDamNhip: z.number().describe('Độ dày nét vẽ nhịp tim (px)'),
});

/* ---------- Đường nhịp tim (đồ hoạ lớp phủ, không phải hình thật) ---------- */
const duongNhip = (rong, cao, soNhip) => {
  const bw = rong / soNhip;
  const giua = cao / 2;
  let d = `M 0 ${giua}`;
  for (let i = 0; i < soNhip; i++) {
    const x = i * bw;
    d += ` L ${x + bw * 0.26} ${giua}`;
    d += ` L ${x + bw * 0.34} ${giua}`;
    d += ` L ${x + bw * 0.40} ${giua - cao * 0.42}`;
    d += ` L ${x + bw * 0.46} ${giua + cao * 0.42}`;
    d += ` L ${x + bw * 0.52} ${giua}`;
    d += ` L ${x + bw * 0.62} ${giua}`;
    d += ` L ${x + bw * 0.68} ${giua - cao * 0.16}`;
    d += ` L ${x + bw * 0.74} ${giua}`;
    d += ` L ${x + bw * 1.0} ${giua}`;
  }
  return d;
};

/* ---------- Lớp 3: HUD nhịp tim / áp lực ---------- */
const NhipTim = ({mau, rong, cao, tocDo, doDam}) => {
  const f = useCurrentFrame();
  const ve = interpolate(f, [0, 34], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const truot = interpolate(f, [0, 108, 150], [0, -tocDo, -tocDo * 1.22], {...kep, easing: Easing.out(Easing.quad)});
  const bienDo = interpolate(f, [0, 96, 134, 158], [1, 1, 0.2, 0.02], kep);
  const mo = interpolate(f, [0, 8, 132, 158], [0, 1, 0.72, 0], kep);
  const rongVe = rong * 2.6;
  return (
    <div style={{width: rong, height: cao, overflow: 'hidden', opacity: mo}}>
      <svg
        width={rongVe}
        height={cao}
        viewBox={`0 0 ${rongVe} ${cao}`}
        style={{transform: `translateX(${truot}px) scaleY(${bienDo})`, transformOrigin: '50% 50%'}}
      >
        <path
          d={duongNhip(rongVe, cao, 6)}
          fill="none"
          stroke={mau}
          strokeWidth={doDam}
          strokeLinejoin="round"
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray="1"
          strokeDashoffset={1 - ve}
        />
      </svg>
    </div>
  );
};

/* ---------- Lớp 2: vệt sáng quét lúc mở cảnh ---------- */
const VetSangQuet = () => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 44], [0, 2700], {...kep, easing: Easing.inOut(Easing.quad)});
  const op = interpolate(f, [0, 12, 32, 44], [0, 0.8, 0.8, 0], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: -800,
        top: -220,
        width: 760,
        height: 1520,
        opacity: op,
        transform: `translateX(${x}px) rotate(10deg)`,
        background:
          'linear-gradient(90deg, rgba(255,240,214,0) 0%, rgba(255,240,214,0.5) 50%, rgba(255,240,214,0) 100%)',
        mixBlendMode: 'screen',
      }}
    />
  );
};

/* ---------- Lớp 2b: nắng ấm trượt chậm qua tiền cảnh ---------- */
const NangAm = () => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 180], [-900, 900], {...kep, easing: Easing.inOut(Easing.sin)});
  const op = interpolate(f, [0, 46], [0, 0.55], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: -960,
        top: -200,
        width: 3840,
        height: 1480,
        opacity: op,
        transform: `translateX(${x}px)`,
        background:
          'linear-gradient(102deg, rgba(255,178,86,0) 30%, rgba(255,196,120,0.5) 45%, rgba(255,216,158,0.38) 55%, rgba(255,178,86,0) 70%)',
        mixBlendMode: 'screen',
      }}
    />
  );
};

/* ---------- Lớp 4: chữ khóa ---------- */
const ChuKhoa = ({chu, co, mau, mauGach}) => {
  const f = useCurrentFrame();
  const tu = chu.split(' ');
  const gach = interpolate(f, [12, 38], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const troi = interpolate(f, [0, 127], [10, -8], kep);
  return (
    <div style={{transform: `translateY(${troi}px)`, position: 'relative', display: 'inline-block'}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 800,
          lineHeight: 1.02,
          letterSpacing: '-0.02em',
          color: mau,
          whiteSpace: 'nowrap',
          textShadow: '0 10px 34px rgba(0,0,0,0.42)',
        }}
      >
        {tu.map((t, i) => {
          const t0 = i * 6;
          const p = interpolate(f, [t0, t0 + 16], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                marginRight: co * 0.2,
                opacity: p,
                transform: `translateY(${(1 - p) * 48}px)`,
              }}
            >
              {t}
            </span>
          );
        })}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          bottom: -26,
          height: Math.max(8, co * 0.055),
          width: `${gach * 100}%`,
          background: mauGach,
          borderRadius: 8,
        }}
      />
    </div>
  );
};

export const Canh = (props) => {
  const {durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0e12', overflow: 'hidden'}}>
      {/* Lớp 1: hậu cảnh đô thị, camera tiến nhẹ suốt 9.9 giây */}
      <AnhNen anh={props.anhNen} tu={props.zoomTu} den={props.zoomDen} goc={props.gocZoom} toi={props.toiNen} />

      {/* Dải tối chân khung để chữ đọc được, không che mất ảnh */}
      <Interactive.Div
        name="Dải tối chân khung"
        from={0}
        durationInFrames={durationInFrames}
        style={{position: 'absolute', left: 0, top: 520}}
      >
        <div
          style={{
            width: 1920,
            height: 560,
            background:
              'linear-gradient(to top, rgba(6,9,14,0.48) 0%, rgba(6,9,14,0.26) 46%, rgba(6,9,14,0) 100%)',
          }}
        />
      </Interactive.Div>

      {/* Lớp 2: vệt sáng quét mở cảnh (beat frame 2) */}
      <Interactive.Div
        name="Vệt sáng quét"
        from={2}
        durationInFrames={48}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <VetSangQuet />
      </Interactive.Div>

      {/* Lớp 3: HUD nhịp tim / áp lực (beat frame 2 -> dịu dần từ 118) */}
      <Interactive.Div
        name="Nhịp tim áp lực"
        from={2}
        durationInFrames={166}
        style={{position: 'absolute', left: props.nhipX, top: props.nhipY}}
      >
        <NhipTim
          mau={props.mauNhip}
          rong={props.rongNhip}
          cao={props.caoNhip}
          tocDo={props.tocDoTruot}
          doDam={props.doDamNhip}
        />
      </Interactive.Div>

      {/* Lớp 2b: nắng ấm trượt chậm qua tiền cảnh (beat frame 118) */}
      <Interactive.Div
        name="Nắng ấm trượt"
        from={118}
        durationInFrames={180}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <NangAm />
      </Interactive.Div>

      {/* Lớp 4: chữ khóa "chậm lại" (beat frame 171) */}
      <Interactive.Div
        name="Chữ khóa sống chậm lại"
        from={171}
        durationInFrames={127}
        style={{position: 'absolute', left: props.chuX, top: props.chuY}}
      >
        <ChuKhoa chu={props.chuKhoa} co={props.coChuKhoa} mau={props.mauChuKhoa} mauGach={props.mauGachChan} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
