import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

/* ------------------------------------------------------------------ */
/* Lớp sơ đồ cắt ngang mờ: các lớp lốp (dải ngang) + mũi tên nước      */
/* chảy xuyên qua các khe hở. Chỉ dùng đường kẻ / mũi tên, không vẽ    */
/* lại vật thật.                                                       */
/* ------------------------------------------------------------------ */
const SoDoCat = ({mau}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 22], [0, 1], kep);
  const tr = interpolate(f, [0, 30], [46, 0], {...kep, easing: Easing.out(Easing.cubic)});

  const bands = [
    {y: 400, segs: [[360, 700], [780, 1120], [1200, 1560]]},
    {y: 540, segs: [[360, 620], [700, 1040], [1120, 1560]]},
    {y: 680, segs: [[360, 760], [840, 1180], [1260, 1560]]},
  ];

  const arrows = [
    {x: 740, y1: 298, y2: 470, d: 10},
    {x: 660, y1: 470, y2: 610, d: 24},
    {x: 800, y1: 610, y2: 752, d: 38},
  ];

  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <g opacity={op * 0.92} transform={`translate(0 ${tr})`}>
        {bands.map((b, i) =>
          b.segs.map((s, j) => (
            <line
              key={`b-${i}-${j}`}
              x1={s[0]}
              y1={b.y}
              x2={s[1]}
              y2={b.y}
              stroke={mau}
              strokeWidth={26}
              strokeLinecap="round"
              opacity={0.34}
            />
          ))
        )}
        {arrows.map((a, i) => {
          const len = a.y2 - a.y1;
          const pr = interpolate(f, [a.d, a.d + 18], [0, 1], kep);
          const tip = a.y1 + len * pr;
          return (
            <g key={`a-${i}`} opacity={pr}>
              <line x1={a.x} y1={a.y1} x2={a.x} y2={tip} stroke="#ffffff" strokeWidth={7} strokeLinecap="round" />
              <polyline
                points={`${a.x - 17},${tip - 24} ${a.x},${tip} ${a.x + 17},${tip - 24}`}
                fill="none"
                stroke="#ffffff"
                strokeWidth={7}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
};

/* ------------------------------------------------------------------ */
/* Ảnh công trường trượt vào bằng clip-path (chuyển cảnh mượt)         */
/* ------------------------------------------------------------------ */
const CanhCongTruong = ({anh, tu, den, toi, goc}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 22], [0, 100], {...kep, easing: Easing.out(Easing.cubic)});
  const clip = `inset(0% ${100 - p}% 0% 0%)`;
  return (
    <div style={{position: 'absolute', inset: 0, clipPath: clip, WebkitClipPath: clip}}>
      <AnhNen anh={anh} tu={tu} den={den} goc={goc} toi={toi} />
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Bộ đếm số hiện đại + nhãn mốc thời gian                             */
/* ------------------------------------------------------------------ */
const BoDem = ({so, donVi, giay, co, nhan, mau, coNhan}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200}, durationInFrames: 16});
  const op = interpolate(f, [0, 10], [0, 1], kep);
  const sc = interpolate(vao, [0, 1], [0.86, 1]);
  const opNhan = interpolate(f, [16, 30], [0, 1], kep);
  const tyNhan = interpolate(f, [16, 30], [18, 0], {...kep, easing: Easing.out(Easing.cubic)});

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        opacity: op,
        transform: `scale(${sc})`,
        transformOrigin: '100% 100%',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(8,12,18,0.58)',
          borderRadius: 34,
          border: `3px solid ${mau}`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 34,
          top: 30,
          width: 120,
          height: 10,
          borderRadius: 6,
          background: mau,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 44,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <SoDem so={so} don_vi={donVi} giay={giay} co={co} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 276,
          textAlign: 'center',
          color: mau,
          fontFamily: FONT,
          fontSize: coNhan,
          fontWeight: 800,
          letterSpacing: 6,
          opacity: opNhan,
          transform: `translateY(${tyNhan}px)`,
        }}
      >
        {nhan}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* CẢNH                                                               */
/* ------------------------------------------------------------------ */
export const Canh = (props) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f14', fontFamily: FONT, overflow: 'hidden'}}>
      {/* ẢNH 1 — bức tường lốp xe (phóng chậm suốt beat 1 & 2, giữ tới frame cuối) */}
      <Interactive.Div
        name="Ảnh tường lốp xe"
        from={0}
        durationInFrames={341}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anhTuong}
          tu={props.zoomTuongTu}
          den={props.zoomTuongDen}
          goc={props.gocTuong}
          toi={props.toiTuong}
        />
      </Interactive.Div>

      {/* BEAT 1 (frame 2) — mũi tên đồ họa chỉ hướng nước gặp khe hở */}
      <Interactive.Div
        name="Mũi tên hướng nước"
        from={2}
        durationInFrames={190}
        style={{position: 'absolute', left: 600, top: 292, width: 700, height: 700}}
      >
        <MuiTen dx={props.muiTenDx} dy={props.muiTenDy} cong={props.muiTenCong} />
      </Interactive.Div>

      {/* BEAT 2 (frame 99) — lớp cắt ngang sơ đồ mờ: nước thấm qua khe */}
      <Interactive.Div
        name="Sơ đồ cắt ngang thấm nước"
        from={99}
        durationInFrames={102}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <SoDoCat mau={props.mauSoDo} />
      </Interactive.Div>

      {/* BEAT 3 (frame 195) — chuyển cảnh sang toàn cảnh công trường, giữ tới frame cuối (341) */}
      <Interactive.Div
        name="Ảnh công trường lốp xe"
        from={195}
        durationInFrames={146}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <CanhCongTruong
          anh={props.anhCongTruong}
          tu={props.zoomCongTruongTu}
          den={props.zoomCongTruongDen}
          goc={props.gocCongTruong}
          toi={props.toiCongTruong}
        />
      </Interactive.Div>

      {/* BEAT 4 (frame 231) — bộ đếm 40% + nhãn tháng 6 */}
      <Interactive.Div
        name="Bộ đếm 40%"
        from={231}
        durationInFrames={110}
        style={{position: 'absolute', left: 1300, top: 590, width: 480, height: 390}}
      >
        <BoDem
          so={props.soPhanTram}
          donVi={props.donVi}
          giay={props.giayDem}
          co={props.coSoDem}
          nhan={props.nhanThang}
          coNhan={props.coNhanThang}
          mau={props.mauNhan}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* SCHEMA                                                             */
/* ------------------------------------------------------------------ */
export const schema = z.object({
  anhTuong: z.string().describe('Đường dẫn ảnh bức tường lốp xe'),
  anhCongTruong: z.string().describe('Đường dẫn ảnh toàn cảnh công trường'),
  gocTuong: z.string().describe('Tâm phóng ảnh tường lốp'),
  gocCongTruong: z.string().describe('Tâm phóng ảnh công trường'),
  zoomTuongTu: z.number().describe('Độ phóng đầu ảnh tường lốp'),
  zoomTuongDen: z.number().describe('Độ phóng cuối ảnh tường lốp'),
  zoomCongTruongTu: z.number().describe('Độ phóng đầu ảnh công trường'),
  zoomCongTruongDen: z.number().describe('Độ phóng cuối ảnh công trường'),
  toiTuong: z.number().describe('Độ tối ảnh tường lốp (0–0.5)'),
  toiCongTruong: z.number().describe('Độ tối ảnh công trường (0–0.5)'),
  muiTenDx: z.number().describe('Mũi tên: dịch ngang'),
  muiTenDy: z.number().describe('Mũi tên: dịch dọc'),
  muiTenCong: z.number().describe('Mũi tên: độ cong'),
  mauSoDo: z.string().describe('Màu các lớp trong sơ đồ cắt ngang'),
  soPhanTram: z.number().describe('Con số phần trăm hiển thị'),
  donVi: z.string().describe('Đơn vị sau con số'),
  giayDem: z.number().describe('Thời gian chạy bộ đếm (giây)'),
  coSoDem: z.number().describe('Cỡ chữ bộ đếm'),
  nhanThang: z.string().describe('Nhãn mốc thời gian'),
  coNhanThang: z.number().describe('Cỡ chữ nhãn thời gian'),
  mauNhan: z.string().describe('Màu nhấn của bộ đếm và nhãn'),
});

/* ------------------------------------------------------------------ */
/* DEFAULT PROPS                                                      */
/* ------------------------------------------------------------------ */
