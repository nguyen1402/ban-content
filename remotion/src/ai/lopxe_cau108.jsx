import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền bản đồ Florida mờ tối'),
  anhLop: z.string().describe('Ảnh lốp xe phế thải dưới đáy biển'),
  namDau: z.string().describe('Mốc năm mở đầu (2023)'),
  soLop: z.string().describe('Con số lốp xe đã thu gom (640.000)'),
  namCuoi: z.string().describe('Mốc năm kết thúc (2030)'),
  mauChinh: z.string().describe('Màu chữ chính (trắng ngà)'),
  mauNhan: z.string().describe('Màu nhấn (vàng)'),
  coSoLon: z.number().describe('Cỡ chữ con số lớn ở giữa'),
  coNam: z.number().describe('Cỡ chữ các mốc năm'),
  doToi: z.number().describe('Độ tối của ảnh nền (0 - 0.5)'),
  rongKhung: z.number().describe('Chiều rộng khung ảnh lốp xe'),
  caoKhung: z.number().describe('Chiều cao khung ảnh lốp xe'),
});

/* ---------- Mốc năm 2023 (góc trên, hiện từ từ) ---------- */
const ChuNam = ({chu, co, mau, doDam = 1}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 18], [0, 1], kep);
  const dy = interpolate(f, [0, 24], [36, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const phong = interpolate(f, [0, 382], [1, 1.06], kep);
  return (
    <div
      style={{
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: co,
        lineHeight: 1,
        letterSpacing: '-0.03em',
        color: mau,
        opacity: op * doDam,
        transform: `translateY(${dy}px) scale(${phong})`,
        transformOrigin: 'left top',
        textShadow: '0 10px 34px rgba(0,0,0,0.72)',
      }}
    >
      {chu}
    </div>
  );
};

/* ---------- Con số lớn 640.000 (trung tâm, lớn dần) ---------- */
const SoLop = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 16], [0, 1], kep);
  const sc = interpolate(f, [0, 30, 235], [0.8, 1, 1.075], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const dy = interpolate(f, [0, 30], [26, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: co,
        lineHeight: 1,
        letterSpacing: '-0.035em',
        color: mau,
        opacity: op,
        transform: `translateY(${dy}px) scale(${sc})`,
        transformOrigin: '50% 50%',
        textShadow: '0 14px 44px rgba(0,0,0,0.75)',
      }}
    >
      {chu}
    </div>
  );
};

/* ---------- Khung ảnh lốp xe dưới đáy biển ---------- */
const KhungLop = ({anh}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 32], [0, 1], kep);
  const dy = interpolate(f, [0, 38], [54, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const sc = interpolate(f, [0, 323], [1.16, 1.02], kep);
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        borderRadius: 20,
        overflow: 'hidden',
        border: '6px solid rgba(247,242,228,0.85)',
        boxShadow: '0 34px 70px rgba(0,0,0,0.6)',
        opacity: op,
        transform: `translateY(${dy}px)`,
        backgroundColor: '#0a1a24',
      }}
    >
      <Img
        name="Ảnh lốp xe dưới biển"
        from={0}
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${sc})`}}
      />
    </div>
  );
};

/* ---------- Mũi tên tiến trình 2023 -> 2030 ---------- */
const MuiTenTienTrinh = ({mau, mauNhan}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 60], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const headOp = interpolate(f, [44, 62], [0, 1], kep);
  const L = 954;
  const x0 = 12;
  const y = 80;
  const cx = x0 + L * p;
  const dotOp = interpolate(p, [0, 0.03, 1], [0, 1, 1], kep);
  return (
    <svg width={1010} height={160} style={{overflow: 'visible'}}>
      <line
        x1={x0}
        y1={y}
        x2={x0 + L}
        y2={y}
        stroke={mau}
        strokeWidth={5}
        strokeLinecap="round"
        opacity={0.22}
      />
      <line
        x1={x0}
        y1={y}
        x2={x0 + L}
        y2={y}
        stroke={mau}
        strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={L}
        strokeDashoffset={L * (1 - p)}
      />
      <path
        d={`M ${x0 + L - 46} ${y - 40} L ${x0 + L + 4} ${y} L ${x0 + L - 46} ${y + 40}`}
        fill="none"
        stroke={mau}
        strokeWidth={6}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={headOp}
      />
      <circle cx={x0} cy={y} r={11} fill={mauNhan} />
      <circle cx={cx} cy={y} r={13} fill={mauNhan} opacity={dotOp} />
    </svg>
  );
};

/* ---------- Mốc 2030 (bật lên ở đầu mũi tên) ---------- */
const NamCuoi = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 200, mass: 0.7, stiffness: 110}});
  const sc = interpolate(s, [0, 1], [0.7, 1]);
  const op = interpolate(f, [0, 12], [0, 1], kep);
  const drift = interpolate(f, [0, 93], [1, 1.045], kep);
  return (
    <div
      style={{
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: co,
        lineHeight: 1,
        letterSpacing: '-0.03em',
        color: mau,
        opacity: op,
        transform: `scale(${sc * drift})`,
        transformOrigin: 'left top',
        textShadow: '0 10px 36px rgba(0,0,0,0.78)',
      }}
    >
      {chu}
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#08111a'}}>
      {/* Nền bản đồ Florida mờ tối, đẩy chậm suốt 12.8 giây */}
      <Interactive.Div
        name="Nền bản đồ Florida"
        from={0}
        durationInFrames={384}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhNen} tu={1} den={1.09} goc="50% 45%" toi={props.doToi} />
      </Interactive.Div>

      {/* Mốc năm 2023 - góc trên trái */}
      <Interactive.Div
        name="Năm 2023"
        from={2}
        durationInFrames={382}
        style={{position: 'absolute', left: 120, top: 96}}
      >
        <ChuNam chu={props.namDau} co={props.coNam} mau={props.mauChinh} />
      </Interactive.Div>

      {/* Khung ảnh lốp xe dưới đáy biển - góc dưới trái */}
      <Interactive.Div
        name="Khung ảnh lốp xe dưới biển"
        from={61}
        durationInFrames={323}
        style={{
          position: 'absolute',
          left: 90,
          top: 636,
          width: props.rongKhung,
          height: props.caoKhung,
        }}
      >
        <KhungLop anh={props.anhLop} />
      </Interactive.Div>

      {/* Con số 640.000 - trung tâm */}
      <Interactive.Div
        name="Con số 640.000"
        from={149}
        durationInFrames={235}
        style={{position: 'absolute', left: 540, top: 372}}
      >
        <SoLop chu={props.soLop} co={props.coSoLon} mau={props.mauNhan} />
      </Interactive.Div>

      {/* Mũi tên tiến trình 2023 -> 2030 */}
      <Interactive.Div
        name="Mũi tên tiến trình"
        from={197}
        durationInFrames={187}
        style={{position: 'absolute', left: 700, top: 850}}
      >
        <MuiTenTienTrinh mau={props.mauChinh} mauNhan={props.mauNhan} />
      </Interactive.Div>

      {/* Mốc năm 2030 ở đầu mũi tên */}
      <Interactive.Div
        name="Năm 2030"
        from={291}
        durationInFrames={93}
        style={{position: 'absolute', left: 1518, top: 724}}
      >
        <NamCuoi chu={props.namCuoi} co={props.coNam} mau={props.mauNhan} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
