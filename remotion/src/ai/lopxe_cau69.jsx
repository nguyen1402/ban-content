import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_office: z.string().describe('Ảnh nền phòng họp bang'),
  anh_officials: z.string().describe('Lớp cắt rời các quan chức'),
  anh_can_dam: z.string().describe('Ảnh cận cảnh đập rác chắn dòng nước'),
  anh_dam: z.string().describe('Ảnh macro cấu trúc đập rác tự chế'),
  anh_beaver: z.string().describe('Lớp cắt rời con hải ly hoang dã'),
  anh_nature: z.string().describe('Ảnh góc rộng thiên nhiên hoang dã'),
  tu_office: z.number().describe('Độ phóng đầu của nền phòng họp'),
  den_office: z.number().describe('Độ phóng cuối của nền phòng họp'),
  tu_dam: z.number().describe('Độ phóng đầu của đập rác macro'),
  den_dam: z.number().describe('Độ phóng cuối của đập rác macro'),
  do_punch: z.number().describe('Mức punch-in ở beat kỳ diệu (ví dụ 0.12)'),
  do_quang: z.number().describe('Độ rộng pan của ảnh thiên nhiên (px)'),
  do_sang: z.number().describe('Độ sáng của vệt light sweep'),
  do_nhoa: z.number().describe('Độ sáng của nháy trắng'),
  toi_nen: z.number().describe('Độ tối phủ lên ảnh nền (0..0.5)'),
  caoquan: z.number().describe('Chiều rộng lớp cắt quan chức (px)'),
  caohai: z.number().describe('Chiều rộng lớp cắt hải ly (px)'),
});

// ---------------------------------------------------------------------------
// Beat 1 (frame 2): lớp cắt quan chức trượt nhẹ vào khung hình
// ---------------------------------------------------------------------------
const QuanChuc = ({anh, rong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 22, mass: 0.9, stiffness: 90}});
  const x = interpolate(vao, [0, 1], [200, 0]);
  const mo = interpolate(vao, [0, 1], [0, 1]);
  const troi = interpolate(f, [0, 74], [0, -28]);
  const phong = interpolate(f, [0, 74], [1.03, 1.0]);
  return (
    <Img
      name="Quan chức đang quan sát"
      src={src(anh)}
      style={{
        width: rong,
        height: 'auto',
        opacity: mo,
        transform: `translateX(${x + troi}px) scale(${phong})`,
        transformOrigin: '50% 80%',
        filter: 'drop-shadow(0 26px 44px rgba(0,0,0,0.35))',
      }}
    />
  );
};

// ---------------------------------------------------------------------------
// Beat 2 (frame 74): light sweep lướt qua ảnh cận cảnh đập rác
// ---------------------------------------------------------------------------
const VetSang = ({do_sang}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 24], [-800, 2200], {...kep, easing: Easing.inOut(Easing.ease)});
  const op = interpolate(f, [0, 6, 16, 28], [0, 1, 0.8, 0], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 720,
        height: 1080,
        transform: `translateX(${x}px) skewX(-14deg)`,
        background: `linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,${do_sang}) 50%, rgba(255,255,255,0) 100%)`,
        opacity: op,
        pointerEvents: 'none',
      }}
    />
  );
};

// ---------------------------------------------------------------------------
// Beat 3 + 4 (frame 122 / 182): đập rác macro, punch-in + nháy sáng
// ---------------------------------------------------------------------------
const DapRac = ({anh, tu, den, toi, do_punch, do_nhoa}) => {
  const f = useCurrentFrame();
  // local 60 = global 182 (punch-in), local 90 = global 212 ('kỳ diệu')
  const punch = interpolate(f, [60, 66, 96], [1, 1 + do_punch, 1 + do_punch * 0.82], kep);
  const nhoa = interpolate(f, [88, 90, 96], [0, do_nhoa, 0], kep);
  const keo = interpolate(f, [0, 158], [0, -18], kep); // lớp trôi chậm tạo parallax
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${punch}) translateY(${keo}px)`}}>
        <AnhNen anh={anh} tu={tu} den={den} goc="50% 60%" toi={toi} />
      </div>
      <AbsoluteFill style={{backgroundColor: '#ffffff', opacity: nhoa, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Beat 4 (frame 182): hải ly hoang dã xuất hiện bên cạnh đập
// ---------------------------------------------------------------------------
const HaiLy = ({anh, rong}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const len = spring({frame: f, fps, config: {damping: 18, mass: 0.85, stiffness: 80}});
  const y = interpolate(len, [0, 1], [150, 0]);
  const mo = interpolate(len, [0, 1], [0, 1]);
  const phong = interpolate(f, [0, 98], [1.06, 1.0]);
  const lac = interpolate(f, [0, 98], [0, 14]);
  return (
    <Img
      name="Hải ly hoang dã đang làm việc"
      src={src(anh)}
      style={{
        width: rong,
        height: 'auto',
        opacity: mo,
        transform: `translate(${lac}px, ${y}px) scale(${phong})`,
        transformOrigin: '50% 100%',
        filter: 'drop-shadow(0 24px 46px rgba(0,0,0,0.4))',
      }}
    />
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#101418'}}>
      {/* Beat 1 — nền phòng họp bang, push-in nhẹ */}
      <Interactive.Div
        name="Nền phòng họp bang"
        from={0}
        durationInFrames={76}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anh_office} tu={props.tu_office} den={props.den_office} goc="50% 42%" toi={props.toi_nen} />
      </Interactive.Div>

      {/* Beat 1 (frame 2) — lớp cắt quan chức trượt vào */}
      <Interactive.Div
        name="Quan chức (lớp cắt) trượt vào"
        from={2}
        durationInFrames={74}
        style={{position: 'absolute', left: 1090, top: 190}}
      >
        <QuanChuc anh={props.anh_officials} rong={props.caoquan} />
      </Interactive.Div>

      {/* Beat 2 (frame 74) — cận cảnh đập rác chắn dòng nước + light sweep */}
      <Interactive.Div
        name="Cận cảnh đập rác chắn nước"
        from={74}
        durationInFrames={50}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anh_can_dam} tu={1.04} den={1.16} goc="50% 50%" toi={0.1} />
      </Interactive.Div>

      <Interactive.Div
        name="Vệt sáng chuyển cảnh"
        from={74}
        durationInFrames={50}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <VetSang do_sang={props.do_sang} />
      </Interactive.Div>

      {/* Beat 3 + 4 (frame 122) — macro đập rác, punch-in ở 182 */}
      <Interactive.Div
        name="Macro cấu trúc đập rác"
        from={122}
        durationInFrames={158}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DapRac
          anh={props.anh_dam}
          tu={props.tu_dam}
          den={props.den_dam}
          toi={props.toi_nen}
          do_punch={props.do_punch}
          do_nhoa={props.do_nhoa}
        />
      </Interactive.Div>

      {/* Beat 4 (frame 182) — hải ly hoang dã bên cạnh đập */}
      <Interactive.Div
        name="Hải ly hoang dã"
        from={182}
        durationInFrames={98}
        style={{position: 'absolute', left: 960, top: 400}}
      >
        <HaiLy anh={props.anh_beaver} rong={props.caohai} />
      </Interactive.Div>

      {/* Beat 5 (frame 280) — góc rộng thiên nhiên, pan chậm sang phải tới hết shot */}
      <Interactive.Div
        name="Thiên nhiên hoang dã (pan phải)"
        from={280}
        durationInFrames={137}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={props.anh_nature} huong="phai" quang={props.do_quang} phong={1.12} toi={0.08} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
