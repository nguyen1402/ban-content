import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

/* ------------------------------------------------------------------ */
/* NHỊP 1 — lớp không ảnh nền (trôi chậm, thu nhẹ để lộ chiều sâu)     */
/* ------------------------------------------------------------------ */

const LopKhongAnh = ({anh, tu, den, goc, toi}) => {
  return <AnhNen anh={anh} tu={tu} den={den} goc={goc} toi={toi} />;
};

/* Cụm 3 ô phân tích thực địa: hiện dần rất êm rồi mờ dần trước nhịp 2 */
const LopOPhanTich = ({anh, tu, den, moc_hien, moc_tan}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, moc_hien], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const ra = interpolate(f, [moc_tan, moc_tan + 16], [1, 0], {...kep, easing: Easing.inOut(Easing.quad)});
  const sc = interpolate(f, [0, 146], [tu, den], kep);
  return (
    <AbsoluteFill style={{opacity: vao * ra, transform: `scale(${sc})`, transformOrigin: '50% 46%'}}>
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};

/* Đường đo đạc mảnh ghim vào 3 vị trí chịu tác động (vẽ dần theo từng từ) */
const DuongDoDac = ({diem, moc, mau}) => {
  const f = useCurrentFrame();
  const ra = interpolate(f, [128, 146], [1, 0], kep);
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, opacity: ra}}>
      {diem.map((d, i) => {
        const t = interpolate(f, [moc[i], moc[i] + 22], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
        const cx = d[0];
        const cy = d[1];
        const r = 66;
        const C = 2 * Math.PI * r;
        const tx = cx + (960 - cx) * 0.33;
        const ty = cy + (540 - cy) * 0.33;
        return (
          <g key={i}>
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={mau}
              strokeWidth={2.5}
              strokeDasharray={`${C}`}
              strokeDashoffset={C * (1 - t)}
              opacity={0.55}
            />
            <line
              x1={cx}
              y1={cy}
              x2={tx}
              y2={ty}
              stroke={mau}
              strokeWidth={2}
              strokeDasharray="10 9"
              opacity={0.42 * t}
            />
            <circle cx={tx} cy={ty} r={4.5} fill={mau} opacity={0.65 * t} />
          </g>
        );
      })}
    </svg>
  );
};

/* ------------------------------------------------------------------ */
/* NHỊP 2 — đầm lầy màu mỡ ngả vàng, co rút dưới biểu đồ suy thoái      */
/* ------------------------------------------------------------------ */

const BieuDoSuyThoai = ({x, y, w, h, mau, moc}) => {
  const f = useCurrentFrame();
  const t = interpolate(f, [moc, moc + 36], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const duLieu = [0.13, 0.2, 0.28, 0.43, 0.59, 0.75, 0.9];
  const pts = duLieu.map((v, i) => [x + (w * i) / (duLieu.length - 1), y + h * v]);
  const poly = pts.map((p) => p.join(',')).join(' ');
  return (
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, opacity: 0.92}}>
      <defs>
        <clipPath id="cat_bieu_do_suy_thoai">
          <rect x={x - 12} y={y - 14} width={w * t + 12} height={h + 46} />
        </clipPath>
      </defs>
      <line x1={x} y1={y + h} x2={x + w} y2={y + h} stroke="#ffffff" strokeWidth={2.5} opacity={0.3} />
      <line x1={x} y1={y} x2={x} y2={y + h} stroke="#ffffff" strokeWidth={2.5} opacity={0.3} />
      <g clipPath="url(#cat_bieu_do_suy_thoai)">
        <polyline
          points={poly}
          fill="none"
          stroke={mau}
          strokeWidth={6}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {pts.map((p, i) => (
          <circle key={i} cx={p[0]} cy={p[1]} r={8} fill={mau} />
        ))}
      </g>
    </svg>
  );
};

const LopDampMauMo = ({anh, tu, den, toi, mau_vang, xBieuDo, yBieuDo, wBieuDo, hBieuDo, mocBieuDo}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 16], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  const sc = interpolate(f, [0, 100], [1.07, 1.0], kep);
  const kho = interpolate(f, [0, 82], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  return (
    <AbsoluteFill style={{opacity: vao, transform: `scale(${sc})`, transformOrigin: '50% 52%'}}>
      <AnhNen anh={anh} tu={tu} den={den} goc="50% 52%" toi={toi} />
      <AbsoluteFill
        style={{
          backgroundColor: mau_vang,
          opacity: 0.42 * kho,
          mixBlendMode: 'multiply',
        }}
      />
      <BieuDoSuyThoai
        x={xBieuDo}
        y={yBieuDo}
        w={wBieuDo}
        h={hBieuDo}
        mau={VANG}
        moc={mocBieuDo}
      />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* NHỊP 3 — lòng suối khô cạn, push-in chậm, giữ tĩnh lặng tới hết câu  */
/* ------------------------------------------------------------------ */

const LopLongSuoi = ({anh, tu, den, toi}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 19], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  return (
    <AbsoluteFill style={{opacity: vao}}>
      <AnhNen anh={anh} tu={tu} den={den} goc="50% 58%" toi={toi} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* SCHEMA                                                              */
/* ------------------------------------------------------------------ */

export const schema = z.object({
  anh_map: z.string().describe('Ảnh không ảnh thung lũng sông'),
  anh_o_phan_tich: z.string().describe('Ảnh cụm 3 ô phân tích thực địa'),
  anh_ngap_nuoc: z.string().describe('Ảnh toàn cảnh đất ngập nước màu mỡ xưa'),
  anh_long_suoi: z.string().describe('Ảnh toàn cảnh lòng suối trơ sỏi đá'),

  map_zoom_tu: z.number().describe('Tỉ lệ bắt đầu của không ảnh nền'),
  map_zoom_den: z.number().describe('Tỉ lệ kết thúc của không ảnh nền'),
  map_goc: z.string().describe('Tâm zoom không ảnh nền'),
  map_toi: z.number().describe('Độ tối không ảnh nền'),

  o_zoom_tu: z.number().describe('Tỉ lệ bắt đầu cụm ô phân tích'),
  o_zoom_den: z.number().describe('Tỉ lệ kết thúc cụm ô phân tích'),
  o_moc_hien: z.number().describe('Số frame cụm ô phân tích hiện rõ'),
  o_moc_tan: z.number().describe('Frame cụm ô phân tích bắt đầu mờ dần'),

  diem1_x: z.number().describe('Hoành độ điểm đo 1'),
  diem1_y: z.number().describe('Tung độ điểm đo 1'),
  diem2_x: z.number().describe('Hoành độ điểm đo 2'),
  diem2_y: z.number().describe('Tung độ điểm đo 2'),
  diem3_x: z.number().describe('Hoành độ điểm đo 3'),
  diem3_y: z.number().describe('Tung độ điểm đo 3'),
  moc_do_1: z.number().describe('Frame vẽ đường đo 1'),
  moc_do_2: z.number().describe('Frame vẽ đường đo 2'),
  moc_do_3: z.number().describe('Frame vẽ đường đo 3'),

  nuoc_zoom_tu: z.number().describe('Tỉ lệ bắt đầu ảnh đầm lầy'),
  nuoc_zoom_den: z.number().describe('Tỉ lệ kết thúc ảnh đầm lầy'),
  nuoc_toi: z.number().describe('Độ tối ảnh đầm lầy'),
  mau_vang: z.string().describe('Màu úa vàng phủ lên đầm lầy'),

  bieu_do_x: z.number().describe('Hoành độ biểu đồ suy thoái'),
  bieu_do_y: z.number().describe('Tung độ biểu đồ suy thoái'),
  bieu_do_w: z.number().describe('Chiều rộng biểu đồ suy thoái'),
  bieu_do_h: z.number().describe('Chiều cao biểu đồ suy thoái'),
  bieu_do_moc: z.number().describe('Frame bắt đầu vẽ biểu đồ'),

  suoi_zoom_tu: z.number().describe('Tỉ lệ bắt đầu ảnh lòng suối'),
  suoi_zoom_den: z.number().describe('Tỉ lệ push-in kết thúc ảnh lòng suối'),
  suoi_toi: z.number().describe('Độ tối ảnh lòng suối'),
});

/* ------------------------------------------------------------------ */
/* CẢNH                                                               */
/* ------------------------------------------------------------------ */

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#101010', fontFamily: FONT, overflow: 'hidden'}}>
      {/* NHỊP 1 — nền không ảnh thung lũng, trôi chậm suốt 0 → ~5.4s */}
      <Interactive.Div
        name="Không ảnh thung lũng trôi chậm"
        from={0}
        durationInFrames={166}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopKhongAnh
          anh={props.anh_map}
          tu={props.map_zoom_tu}
          den={props.map_zoom_den}
          goc={props.map_goc}
          toi={props.map_toi}
        />
      </Interactive.Div>

      {/* NHỊP 1 — cụm 3 ô phân tích thực địa nổi lên trên không ảnh */}
      <Interactive.Div
        name="Cụm 3 ô phân tích thực địa"
        from={2}
        durationInFrames={146}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopOPhanTich
          anh={props.anh_o_phan_tich}
          tu={props.o_zoom_tu}
          den={props.o_zoom_den}
          moc_hien={props.o_moc_hien}
          moc_tan={props.o_moc_tan}
        />
      </Interactive.Div>

      {/* NHỊP 1 — đường đo đạc mảnh ghim 3 vị trí, vẽ dần theo lời */}
      <Interactive.Div
        name="Đường đo đạc 3 điểm"
        from={2}
        durationInFrames={146}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DuongDoDac
          diem={[
            [props.diem1_x, props.diem1_y],
            [props.diem2_x, props.diem2_y],
            [props.diem3_x, props.diem3_y],
          ]}
          moc={[props.moc_do_1, props.moc_do_2, props.moc_do_3]}
          mau={VANG}
        />
      </Interactive.Div>

      {/* NHỊP 2 — đầm lầy màu mỡ ngả vàng, co rút dưới biểu đồ suy thoái */}
      <Interactive.Div
        name="Đầm lầy màu mỡ ngả vàng"
        from={146}
        durationInFrames={100}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopDampMauMo
          anh={props.anh_ngap_nuoc}
          tu={props.nuoc_zoom_tu}
          den={props.nuoc_zoom_den}
          toi={props.nuoc_toi}
          mau_vang={props.mau_vang}
          xBieuDo={props.bieu_do_x}
          yBieuDo={props.bieu_do_y}
          wBieuDo={props.bieu_do_w}
          hBieuDo={props.bieu_do_h}
          mocBieuDo={props.bieu_do_moc}
        />
      </Interactive.Div>

      {/* NHỊP 3 — lòng suối khô cạn, push-in chậm tới frame cuối */}
      <Interactive.Div
        name="Lòng suối khô cạn trơ sỏi đá"
        from={223}
        durationInFrames={86}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopLongSuoi
          anh={props.anh_long_suoi}
          tu={props.suoi_zoom_tu}
          den={props.suoi_zoom_den}
          toi={props.suoi_toi}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
