import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_giao_su: z.string().describe('Ảnh giáo sư kỹ thuật bên bảng đen'),
  anh_dam: z.string().describe('Ảnh cắt lớp đập bê tông (PNG trong suốt)'),
  anh_tuong: z.string().describe('Ảnh cận cảnh kết cấu tường rỗng'),
  ten_giao_su: z.string().describe('Tên hiển thị của giáo sư'),
  so_tien: z.number().describe('Số tiền đích của bộ đếm'),
  don_vi_tien: z.string().describe('Đơn vị tiền tệ'),
  giay_dem: z.number().describe('Thời gian chạy bộ đếm (giây)'),
  co_so: z.number().describe('Cỡ chữ bộ đếm'),
  co_ten: z.number().describe('Cỡ chữ tên giáo sư'),
  rong_dam: z.number().describe('Chiều rộng ảnh đập bê tông (px)'),
  lech_whip: z.number().describe('Độ lệch cú lia máy ngang (px)'),
  zoom_nen_tu: z.number().describe('Tỉ lệ zoom đầu của ảnh nền giáo sư'),
  zoom_nen_den: z.number().describe('Tỉ lệ zoom cuối của ảnh nền giáo sư'),
  toi_nen: z.number().describe('Độ tối lớp phủ ảnh nền giáo sư'),
  toi_tuong: z.number().describe('Độ tối lớp phủ ảnh tường rỗng'),
});

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

/* ---------- Tên Giáo sư Honig (góc phải trên) ---------- */
const TenGiaoSu = ({chu, co}) => {
  const f = useCurrentFrame();
  const hien = interpolate(f, [0, 18, 166, 196], [0, 1, 1, 0], CL);
  const truot = interpolate(f, [0, 20], [26, 0], {...CL, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 18, opacity: hien, transform: `translateY(${truot}px)`}}>
      <div style={{width: 9, height: co * 1.0, backgroundColor: VANG, borderRadius: 5}} />
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 600,
          letterSpacing: 2,
          color: '#ffffff',
          whiteSpace: 'nowrap',
          textShadow: '0 6px 22px rgba(0,0,0,0.85)',
        }}
      >
        {chu}
      </div>
    </div>
  );
};

/* ---------- Đập bê tông: lia máy ngang + punch-in ---------- */
const DamBeTong = ({anh, rong, lech}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 12], [lech, 0], {...CL, easing: Easing.out(Easing.cubic)});
  const s = interpolate(f, [0, 10, 60, 207], [1.18, 1.0, 1.03, 1.09], {...CL, easing: Easing.out(Easing.cubic)});
  const cao = rong / 1.8135;
  return (
    <div
      style={{
        position: 'absolute',
        left: 100 + x,
        top: 66,
        width: rong,
        height: cao,
        transform: `scale(${s})`,
        transformOrigin: '50% 50%',
      }}
    >
      <Img
        name="Ảnh đập bê tông"
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'contain', display: 'block'}}
      />
    </div>
  );
};

/* ---------- Vệt sáng quét qua kết cấu tường ---------- */
const VetSang = () => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, 48], [-140, 240], {...CL, easing: Easing.inOut(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: 0,
        width: '75%',
        height: '100%',
        background:
          'linear-gradient(102deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.10) 30%, rgba(255,255,255,0.46) 50%, rgba(255,255,255,0.10) 70%, rgba(255,255,255,0) 100%)',
        mixBlendMode: 'screen',
        pointerEvents: 'none',
      }}
    />
  );
};

/* ---------- Bộ đếm tiền với punch-in ---------- */
const BoDem = ({so, don_vi, giay, co}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sp = spring({frame: f, fps, config: {damping: 14, stiffness: 170, mass: 0.7}});
  const sc = interpolate(sp, [0, 1], [1.35, 1]);
  const op = interpolate(f, [0, 5], [0, 1], CL);
  return (
    <div style={{opacity: op, transform: `scale(${sc})`, transformOrigin: '0% 50%'}}>
      <SoDem so={so} don_vi={don_vi} giay={giay} co={co} />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', overflow: 'hidden'}}>
      {/* 1 — Nền: Giáo sư Honig tính toán trên bảng đen (0 → hết shot) */}
      <Interactive.Div
        name="Ảnh Giáo sư Honig bên bảng đen"
        from={0}
        durationInFrames={411}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anh_giao_su}
          tu={props.zoom_nen_tu}
          den={props.zoom_nen_den}
          goc="50% 42%"
          toi={props.toi_nen}
        />
      </Interactive.Div>

      {/* 1b — Tên giáo sư hiện ở góc */}
      <Interactive.Div
        name="Tên Giáo sư Honig"
        from={4}
        durationInFrames={196}
        style={{position: 'absolute', left: 1225, top: 128}}
      >
        <TenGiaoSu chu={props.ten_giao_su} co={props.co_ten} />
      </Interactive.Div>

      {/* 2 — Lia máy sang đập bê tông (204 → 320) */}
      <Interactive.Div
        name="Đập bê tông quy mô tương đương"
        from={204}
        durationInFrames={207}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <DamBeTong anh={props.anh_dam} rong={props.rong_dam} lech={props.lech_whip} />
      </Interactive.Div>

      {/* 2b — Bộ đếm chi phí */}
      <Interactive.Div
        name="Bộ đếm chi phí 35.000 đô la"
        from={204}
        durationInFrames={116}
        style={{position: 'absolute', left: 120, top: 796}}
      >
        <BoDem so={props.so_tien} don_vi={props.don_vi_tien} giay={props.giay_dem} co={props.co_so} />
      </Interactive.Div>

      {/* 3 — Kết cấu rỗng của bức tường (320 → hết shot) */}
      <Interactive.Div
        name="Cận cảnh kết cấu tường rỗng"
        from={320}
        durationInFrames={91}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anh_tuong} tu={1.2} den={1.0} goc="50% 50%" toi={props.toi_tuong} />
        <VetSang />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
