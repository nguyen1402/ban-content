import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const clE = (easing) => ({extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền đáy biển đống lốp'),
  anhThoLan: z.string().describe('Ảnh tư liệu thợ lặn'),
  nam: z.string().describe('Dòng năm hiển thị góc trên'),
  soLop: z.number().describe('Số chiếc lốp'),
  coNam: z.number().describe('Cỡ chữ năm (px)'),
  coSo: z.number().describe('Cỡ chữ bộ đếm (px)'),
  mauVang: z.string().describe('Màu vàng nhấn'),
  mauChu: z.string().describe('Màu chữ chính'),
  doToi: z.number().describe('Độ tối lớp phủ nền (0–0.5)'),
  heSoZoomNen: z.number().describe('Hệ số zoom cuối của nền'),
  thoiGianDem: z.number().describe('Số frame chạy bộ đếm'),
  doTreVong: z.number().describe('Frame bắt đầu vẽ vòng định vị'),
});

/* ---------- Năm 2007 - 2009 (góc trên) ---------- */
const KhoiNam = ({nam, co, mauVang, mauChu}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 12], [0, 1], cl);
  const tx = interpolate(f, [0, 18], [-90, 0], clE(Easing.out(Easing.cubic)));
  const vach = interpolate(f, [4, 22], [0, 1], clE(Easing.out(Easing.cubic)));
  const mo = interpolate(f, [196, 226], [1, 0.5], cl);
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 30,
        opacity: vao * mo,
        transform: `translateX(${tx}px)`,
        fontFamily: FONT,
        color: mauChu,
      }}
    >
      <div
        style={{
          width: 12,
          height: co * 0.95,
          background: mauVang,
          transform: `scaleY(${vach})`,
          transformOrigin: '50% 50%',
          borderRadius: 6,
        }}
      />
      <div
        style={{
          fontSize: co,
          fontWeight: 800,
          lineHeight: 1,
          letterSpacing: 2,
          textShadow: '0 8px 34px rgba(0,0,0,0.65)',
          whiteSpace: 'nowrap',
        }}
      >
        {nam}
      </div>
    </div>
  );
};

/* ---------- Khung ảnh thợ lặn (inset) ---------- */
const KhungThoLan = ({anh, mauVang}) => {
  const f = useCurrentFrame();
  const W = 720;
  const H = 640;

  // vào khung
  const vao = interpolate(f, [0, 16], [0, 1], cl);
  const txIn = interpolate(f, [0, 24], [150, 0], clE(Easing.out(Easing.cubic)));
  const sIn = interpolate(f, [0, 24], [1.08, 1], clE(Easing.out(Easing.cubic)));

  // nhường chỗ cho bộ đếm (local 144 = frame 233)
  const sOut = interpolate(f, [144, 174], [1, 0.5], clE(Easing.inOut(Easing.cubic)));
  const dxOut = interpolate(f, [144, 174], [0, 200], clE(Easing.inOut(Easing.cubic)));
  const dyOut = interpolate(f, [144, 174], [0, -300], clE(Easing.inOut(Easing.cubic)));

  // zoom chậm liên tục bên trong khung
  const zoom = 1.06 + f * 0.00075;

  // vòng sáng khoanh đôi tay
  const R = 138;
  const C = 2 * Math.PI * R;
  const draw = interpolate(f, [12, 40], [0, 1], clE(Easing.out(Easing.cubic)));
  const ringOp = interpolate(f, [8, 22], [0, 1], cl);

  return (
    <div
      style={{
        width: W,
        height: H,
        boxSizing: 'border-box',
        transform: `translate(${txIn + dxOut}px, ${dyOut}px) scale(${sIn * sOut})`,
        transformOrigin: '50% 50%',
        opacity: vao,
        border: '10px solid rgba(255,255,255,0.92)',
        borderRadius: 16,
        overflow: 'hidden',
        background: '#000',
        boxShadow: '0 34px 90px rgba(0,0,0,0.6)',
        position: 'relative',
      }}
    >
      <Img
        name="Ảnh thợ lặn"
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${zoom})`,
          display: 'block',
        }}
      />
      <svg
        width={360}
        height={360}
        style={{position: 'absolute', left: 180, top: 150, opacity: ringOp}}
      >
        <circle
          cx={180}
          cy={180}
          r={R}
          fill="none"
          stroke={mauVang}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C * (1 - draw)}
          transform="rotate(-90 180 180)"
        />
        <circle
          cx={180}
          cy={180}
          r={R + 20}
          fill="none"
          stroke={mauVang}
          strokeWidth={3}
          opacity={0.55 * draw}
          strokeDasharray="16 14"
        />
      </svg>
    </div>
  );
};

/* ---------- Vòng tròn định vị ---------- */
const VongDinhVi = ({mauVang, doTreVong}) => {
  const f = useCurrentFrame();
  const CX = 400;
  const CY = 400;
  const R = 370;
  const C = 2 * Math.PI * R;

  const draw = interpolate(f, [doTreVong, doTreVong + 28], [0, 1], clE(Easing.out(Easing.cubic)));
  const op = interpolate(f, [doTreVong - 2, doTreVong + 10], [0, 1], cl);
  const quay = f * 0.25;
  const phu = interpolate(f, [doTreVong + 12, doTreVong + 34], [0, 1], cl);
  const tickOp = interpolate(f, [doTreVong + 16, doTreVong + 34], [0, 1], cl);

  const tick = (x1, y1, x2, y2) => (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke={mauVang}
      strokeWidth={6}
      strokeLinecap="round"
      opacity={tickOp}
    />
  );

  return (
    <svg width={800} height={800} style={{opacity: op}}>
      <circle
        cx={CX}
        cy={CY}
        r={R}
        fill="none"
        stroke={mauVang}
        strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={C}
        strokeDashoffset={C * (1 - draw)}
        transform={`rotate(-90 ${CX} ${CY})`}
      />
      <g transform={`rotate(${quay} ${CX} ${CY})`} opacity={phu}>
        <circle
          cx={CX}
          cy={CY}
          r={R - 30}
          fill="none"
          stroke={mauVang}
          strokeWidth={3}
          strokeDasharray="18 16"
          opacity={0.8}
        />
      </g>
      {tick(CX - 3, CY - R - 52, CX - 3, CY - R - 16)}
      {tick(CX - 3, CY + R + 16, CX - 3, CY + R + 52)}
      {tick(CX - R - 52, CY - 3, CX - R - 16, CY - 3)}
      {tick(CX + R + 16, CY - 3, CX + R + 52, CY - 3)}
    </svg>
  );
};

/* ---------- Bộ đếm 72.000 ---------- */
const SoLon = ({so, co, mauChu, thoiGianDem}) => {
  const f = useCurrentFrame();
  const batDau = 6;
  const v = Math.round(
    interpolate(f, [batDau, batDau + thoiGianDem], [0, so], clE(Easing.out(Easing.cubic)))
  );
  const txt = String(v).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const op = interpolate(f, [2, 12], [0, 1], cl);
  const sc = interpolate(f, [2, 22], [1.25, 1], clE(Easing.out(Easing.cubic)));
  const tho = 1 + Math.sin(f * 0.07) * 0.007;
  return (
    <div
      style={{
        width: 1300,
        height: 400,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: op,
        transform: `scale(${sc * tho})`,
        fontFamily: FONT,
        fontSize: co,
        fontWeight: 900,
        lineHeight: 1,
        letterSpacing: 4,
        color: mauChu,
        textShadow: '0 14px 50px rgba(0,0,0,0.7)',
        whiteSpace: 'nowrap',
      }}
    >
      {txt}
    </div>
  );
};

export const Canh = ({
  anhNen,
  anhThoLan,
  nam,
  soLop,
  coNam,
  coSo,
  mauVang,
  mauChu,
  doToi,
  heSoZoomNen,
  thoiGianDem,
  doTreVong,
}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#04121c'}}>
      {/* Nền đáy biển u tối — chạy suốt shot */}
      <Interactive.Div
        name="Nền đáy biển"
        from={0}
        durationInFrames={328}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anhNen} tu={1} den={heSoZoomNen} goc="50% 45%" toi={doToi} />
      </Interactive.Div>

      {/* Năm 2007 - 2009 */}
      <Interactive.Div
        name="Năm 2007-2009"
        from={2}
        durationInFrames={326}
        style={{position: 'absolute', left: 96, top: 96}}
      >
        <KhoiNam nam={nam} co={coNam} mauVang={mauVang} mauChu={mauChu} />
      </Interactive.Div>

      {/* Khung ảnh thợ lặn */}
      <Interactive.Div
        name="Khung ảnh thợ lặn"
        from={89}
        durationInFrames={239}
        style={{position: 'absolute', left: 1060, top: 220}}
      >
        <KhungThoLan anh={anhThoLan} mauVang={mauVang} />
      </Interactive.Div>

      {/* Vòng tròn định vị */}
      <Interactive.Div
        name="Vòng định vị"
        from={233}
        durationInFrames={95}
        style={{position: 'absolute', left: 350, top: 100}}
      >
        <VongDinhVi mauVang={mauVang} doTreVong={doTreVong} />
      </Interactive.Div>

      {/* Bộ đếm 72.000 */}
      <Interactive.Div
        name="Bộ đếm 72.000"
        from={233}
        durationInFrames={95}
        style={{position: 'absolute', left: 100, top: 300}}
      >
        <SoLon so={soLop} co={coSo} mauChu={mauChu} thoiGianDem={thoiGianDem} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
