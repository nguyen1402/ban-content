import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

/* ---------- helpers ---------- */
const arcPath = (r, a0, a1) => {
  const x0 = r * Math.cos(a0);
  const y0 = r * Math.sin(a0);
  const x1 = r * Math.cos(a1);
  const y1 = r * Math.sin(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
};

/* ---------- lớp sơ đồ kỹ thuật mối nối neo (góc phải) ---------- */
const SoDoNoi = ({mauNet, mauNhan, gayLocal, doGay}) => {
  const f = useCurrentFrame();

  const panelOp = interpolate(f, [0, 22], [0, 1], kep);
  const ve = (s, d) =>
    interpolate(f, [s, s + d], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  const pBlkL = ve(12, 28);
  const pBlkR = ve(20, 28);
  const pCable = ve(6, 52);
  const pJoint = ve(48, 32);
  const pRing = ve(64, 26);

  /* đứt gãy bắt đầu đúng frame 175 toàn cục */
  const fg = f - gayLocal;
  const gayP = interpolate(fg, [0, 18], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const gap = gayP * doGay;

  /* chuyển động chậm liên tục */
  const wob = Math.sin(f / 27) * 3;
  const wob2 = Math.sin(f / 20 + 1.3) * 2.6;

  const cableL = `M 135 362 C 172 ${300 + wob}, 262 ${254 + wob2}, ${332 - gap} ${250 + wob2 * 0.6}`;
  const cableR = `M 625 362 C 588 ${300 - wob}, 498 ${254 - wob2}, ${428 + gap} ${250 - wob2 * 0.6}`;

  const gAngle = 0.05 + gayP * 0.55;
  const spin = (f * 0.35) % 360;

  /* sóng phủ qua sơ đồ, xuất hiện sau khi mối nối đứt */
  const waveOp = interpolate(fg, [12, 64], [0, 1], kep) * 0.42;
  const waves = [];
  for (let i = 0; i < 5; i++) {
    const yBase = 118 + i * 104;
    const ph = f * 0.055 + i * 1.7;
    let d = '';
    for (let x = 8; x <= 752; x += 14) {
      const y =
        yBase +
        Math.sin(x * 0.017 + ph) * 13 +
        Math.sin(x * 0.0071 - ph * 0.7) * 7;
      d += (x === 8 ? 'M' : 'L') + ` ${x} ${y.toFixed(1)}`;
    }
    waves.push(d);
  }

  return (
    <svg width={760} height={640} viewBox="0 0 760 640" style={{overflow: 'visible'}}>
      {/* khung sơ đồ */}
      <rect
        x={4}
        y={4}
        width={752}
        height={632}
        rx={22}
        fill="rgba(4,22,30,0.40)"
        stroke="rgba(140,230,245,0.45)"
        strokeWidth={2.5}
        opacity={panelOp}
      />

      {/* góc kỹ thuật */}
      <g
        opacity={panelOp * 0.9}
        stroke={mauNhan}
        strokeWidth={4}
        fill="none"
        strokeLinecap="round"
      >
        <path d="M 26 46 L 26 26 L 46 26" />
        <path d="M 734 46 L 734 26 L 714 26" />
        <path d="M 26 594 L 26 614 L 46 614" />
        <path d="M 734 594 L 734 614 L 714 614" />
      </g>

      {/* dây cáp neo trái + phải */}
      <path
        d={cableL}
        fill="none"
        stroke={mauNet}
        strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={360}
        strokeDashoffset={360 * (1 - pCable)}
      />
      <path
        d={cableR}
        fill="none"
        stroke={mauNet}
        strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={360}
        strokeDashoffset={360 * (1 - pCable)}
      />

      {/* khối neo trái */}
      <g
        opacity={pBlkL}
        transform={`translate(135 401) scale(${0.86 + 0.14 * pBlkL}) translate(-135 -401)`}
      >
        <rect
          x={72}
          y={362}
          width={126}
          height={78}
          rx={12}
          fill="rgba(10,44,58,0.68)"
          stroke={mauNet}
          strokeWidth={3.5}
        />
        <circle cx={102} cy={401} r={9} fill="none" stroke={mauNhan} strokeWidth={3.5} />
        <circle cx={135} cy={401} r={9} fill="none" stroke={mauNhan} strokeWidth={3.5} />
        <circle cx={168} cy={401} r={9} fill="none" stroke={mauNhan} strokeWidth={3.5} />
      </g>

      {/* khối neo phải */}
      <g
        opacity={pBlkR}
        transform={`translate(625 401) scale(${0.86 + 0.14 * pBlkR}) translate(-625 -401)`}
      >
        <rect
          x={562}
          y={362}
          width={126}
          height={78}
          rx={12}
          fill="rgba(10,44,58,0.68)"
          stroke={mauNet}
          strokeWidth={3.5}
        />
        <circle cx={592} cy={401} r={9} fill="none" stroke={mauNhan} strokeWidth={3.5} />
        <circle cx={625} cy={401} r={9} fill="none" stroke={mauNhan} strokeWidth={3.5} />
        <circle cx={658} cy={401} r={9} fill="none" stroke={mauNhan} strokeWidth={3.5} />
      </g>

      {/* vòng định vị nét đứt xoay chậm */}
      <g transform={`translate(${380 + wob * 0.5} ${250 + wob2 * 0.5})`} opacity={pRing}>
        <circle
          r={88}
          fill="none"
          stroke={mauNhan}
          strokeWidth={2}
          strokeDasharray="8 12"
          opacity={0.75}
          transform={`rotate(${-f * 0.28})`}
        />
      </g>

      {/* mối nối neo (vòng khuyên) */}
      <g
        transform={`translate(${380 + wob * 0.5} ${250 + wob2 * 0.5}) rotate(${spin})`}
        opacity={pJoint}
      >
        <path
          d={arcPath(46, gAngle, Math.PI - gAngle)}
          fill="none"
          stroke={mauNet}
          strokeWidth={6}
          strokeLinecap="round"
        />
        <path
          d={arcPath(46, Math.PI + gAngle, 2 * Math.PI - gAngle)}
          fill="none"
          stroke={mauNet}
          strokeWidth={6}
          strokeLinecap="round"
        />
        <circle r={17} fill="rgba(10,44,58,0.92)" stroke={mauNhan} strokeWidth={4} />
        {[0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2].map((a, i) => (
          <circle key={i} cx={32 * Math.cos(a)} cy={32 * Math.sin(a)} r={5} fill={mauNhan} />
        ))}
      </g>

      {/* vết đứt gãy tại mối nối */}
      <g
        transform={`translate(${380 + wob * 0.5} ${250 + wob2 * 0.5})`}
        opacity={gayP}
      >
        <path
          d="M -8 -38 L 4 -17 L -5 0 L 6 17 L -4 38"
          fill="none"
          stroke="#ffffff"
          strokeWidth={4}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={130}
          strokeDashoffset={130 * (1 - gayP)}
        />
      </g>

      {/* mũi giằng xé hai đầu cáp */}
      <g
        opacity={interpolate(fg, [4, 18], [0, 1], kep)}
        stroke={VANG}
        strokeWidth={5}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={`M ${300 - gap} 234 L ${274 - gap} 250 L ${300 - gap} 266`} />
        <path d={`M ${460 + gap} 234 L ${486 + gap} 250 L ${460 + gap} 266`} />
      </g>

      {/* sóng phủ qua sơ đồ */}
      <g opacity={waveOp} stroke="#9fe9ff" strokeWidth={2.4} fill="none" strokeLinecap="round">
        {waves.map((d, i) => (
          <path key={i} d={d} />
        ))}
      </g>
    </svg>
  );
};

/* ---------- vệt sáng sóng quét toàn khung ---------- */
const QuetSong = () => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 231], [-900, 1500], {
    ...kep,
    easing: Easing.inOut(Easing.sin),
  });
  const op = interpolate(f, [0, 45, 200, 231], [0, 0.55, 0.55, 0.22], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: -700,
        top: 0,
        width: 3200,
        height: 1080,
        transform: `translateX(${x}px)`,
        opacity: op,
        background:
          'linear-gradient(100deg, rgba(120,225,255,0) 42%, rgba(150,240,255,0.30) 50%, rgba(120,225,255,0) 58%)',
        mixBlendMode: 'screen',
      }}
    />
  );
};

/* ---------- schema ---------- */
export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền đống lốp xe dưới biển Florida'),
  zoomTu: z.number().describe('Tỉ lệ zoom nền lúc bắt đầu'),
  zoomDen: z.number().describe('Tỉ lệ zoom nền lúc kết thúc'),
  doToi: z.number().describe('Độ tối lớp phủ nền (0..0.5)'),
  mauNet: z.string().describe('Màu nét chính của sơ đồ'),
  mauNhan: z.string().describe('Màu điểm neo / nét phụ'),
  frameGay: z.number().describe('Frame mối nối neo bị đứt gãy'),
  doGay: z.number().describe('Độ hở của mối nối khi đứt (px)'),
});

/* ---------- cảnh ---------- */
export const Canh = (props) => {
  const frame = useCurrentFrame();
  const gayLocal = props.frameGay - 2;

  return (
    <AbsoluteFill style={{backgroundColor: '#04141c'}}>
      <Interactive.Div
        name="Ảnh nền đống lốp Florida dưới biển"
        from={0}
        durationInFrames={406}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anhNen}
          tu={props.zoomTu}
          den={props.zoomDen}
          goc="52% 58%"
          toi={props.doToi}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Sơ đồ kỹ thuật mối nối neo"
        from={2}
        durationInFrames={404}
        style={{position: 'absolute', left: 1100, top: 170}}
      >
        <SoDoNoi
          mauNet={props.mauNet}
          mauNhan={props.mauNhan}
          gayLocal={gayLocal}
          doGay={props.doGay}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Vệt sáng sóng quét"
        from={175}
        durationInFrames={231}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <QuetSong />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
