import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen_dat: z.string().describe('Ảnh nền bãi đất trống ngoại ô'),
  anh_lop_co: z.string().describe('Ảnh cắt nền chiếc lốp xe đơn lẻ'),
  anh_thap_lop: z.string().describe('Ảnh cắt nền tháp lốp phế liệu'),
  anh_bai_phe_lieu: z.string().describe('Ảnh nền bãi phế liệu lốp xe'),
  anh_can_muoi: z.string().describe('Ảnh macro lăng quăng và muỗi trong nước đọng'),
  anh_can_hoa_hoan: z.string().describe('Ảnh cận cảnh lửa và khói từ đống lốp'),
  phong_lop: z.number().describe('Độ phóng to nhấn của chiếc lốp đơn (1.2 = 120%)'),
  phong_thap: z.number().describe('Độ phóng to nhấn của tháp lốp (1.15 = 115%)'),
  phong_lua: z.number().describe('Độ phóng to nhấn của ảnh hỏa hoạn (1.15 = 115%)'),
});

/* ---------- Đường dẫn ảnh mặc định (dùng khi prop bị thiếu) ---------- */
const ANH_MAC_DINH = {
  anh_nen_dat: 'nhan_y/453e710fb6a079.jpg',
  anh_lop_co: 'nhan_y/05e4efc8a0f56b.png',
  anh_thap_lop: 'nhan_y/2437ed989229f5.png',
  anh_bai_phe_lieu: 'nhan_y/cb123d100504b4.jpg',
  anh_can_muoi: 'nhan_y/3455e04f2ac255.jpg',
  anh_can_hoa_hoan: 'nhan_y/0883692a4967b3.jpg',
};

/* ---------- Nền bãi đất trống: trượt sang trái khi hết beat ---------- */
const NenDat = ({anh}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [103, 111], [0, -1920], {
    ...kep,
    easing: Easing.in(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        transform: `translateX(${x}px)`,
      }}
    >
      <AnhNen anh={anh} tu={1.0} den={1.12} goc="50% 58%" toi={0.08} />
    </div>
  );
};

/* ---------- Chiếc lốp đơn: pop 120% rồi thu lại ---------- */
const LopCo = ({anh, phong}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 12, 26, 45], [1, phong, 1, 1.05], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const y = interpolate(f, [0, 45], [26, 0], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: '100%',
        height: '100%',
        transform: `translateY(${y}px) scale(${s})`,
        transformOrigin: '50% 62%',
      }}
    >
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          filter: 'drop-shadow(0 24px 34px rgba(0,0,0,0.45))',
        }}
      />
    </div>
  );
};

/* ---------- Tháp lốp: whip-pan vào, phóng to, rồi trượt sang trái ---------- */
const ThapLop = ({anh, phong}) => {
  const f = useCurrentFrame();
  const panX = interpolate(f, [0, 7], [280, 0], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const s = interpolate(f, [0, 18, 27, 53, 61], [1.0, 1.04, phong, 1.22, 1.26], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const outX = interpolate(f, [54, 61], [0, -1950], {
    ...kep,
    easing: Easing.in(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: '100%',
        height: '100%',
        transform: `translateX(${panX + outX}px) scale(${s})`,
        transformOrigin: '50% 65%',
      }}
    >
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          filter: 'drop-shadow(0 26px 38px rgba(0,0,0,0.45))',
        }}
      />
    </div>
  );
};

/* ---------- Lớp phủ macro muỗi: pop vào, zoom chậm, whip-pan ra phải ---------- */
const CanMuoi = ({anh}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: f, fps, config: {damping: 14, stiffness: 110, mass: 0.7}});
  const popS = interpolate(pop, [0, 1], [0.68, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'extend',
  });
  const zoom = interpolate(f, [0, 71], [1.0, 1.08], kep);
  const outX = interpolate(f, [66, 71], [0, 2600], {
    ...kep,
    easing: Easing.in(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: '100%',
        height: '100%',
        transform: `translateX(${outX}px) scale(${popS})`,
        transformOrigin: '50% 50%',
        borderRadius: 26,
        overflow: 'hidden',
        boxShadow: '0 30px 70px rgba(0,0,0,0.5)',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '100%',
          height: '100%',
          transform: `scale(${zoom})`,
        }}
      >
        <AnhNen anh={anh} tu={1.0} den={1.06} goc="50% 50%" toi={0.05} />
      </div>
    </div>
  );
};

/* ---------- Hỏa hoạn: cháy âm ỉ, phóng to mạnh ở beat cuối ---------- */
const HoaHoan = ({anh, phong}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 25, 36, 75], [1.0, 1.03, phong, 1.24], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: '100%',
        height: '100%',
        transform: `scale(${s})`,
        transformOrigin: '50% 58%',
      }}
    >
      <AnhNen anh={anh} tu={1.0} den={1.09} goc="50% 58%" toi={0.05} />
    </div>
  );
};

export const Canh = (props) => {
  const anh_nen_dat = props.anh_nen_dat ?? ANH_MAC_DINH.anh_nen_dat;
  const anh_lop_co = props.anh_lop_co ?? ANH_MAC_DINH.anh_lop_co;
  const anh_thap_lop = props.anh_thap_lop ?? ANH_MAC_DINH.anh_thap_lop;
  const anh_bai_phe_lieu = props.anh_bai_phe_lieu ?? ANH_MAC_DINH.anh_bai_phe_lieu;
  const anh_can_muoi = props.anh_can_muoi ?? ANH_MAC_DINH.anh_can_muoi;
  const anh_can_hoa_hoan = props.anh_can_hoa_hoan ?? ANH_MAC_DINH.anh_can_hoa_hoan;

  const phong_lop = props.phong_lop ?? 1.2;
  const phong_thap = props.phong_thap ?? 1.15;
  const phong_lua = props.phong_lua ?? 1.15;

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a'}}>
      {/* NỀN RỘNG: bãi phế liệu lốp xe (nằm dưới, giữ tới cuối cảnh) */}
      <Interactive.Div
        name="Nền bãi phế liệu lốp xe"
        from={103}
        durationInFrames={221}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anh_bai_phe_lieu} tu={1.0} den={1.12} goc="50% 50%" toi={0.06} />
      </Interactive.Div>

      {/* NỀN: bãi đất trống (trượt sang trái ở frame 103) */}
      <Interactive.Div
        name="Nền bãi đất trống"
        from={0}
        durationInFrames={111}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NenDat anh={anh_nen_dat} />
      </Interactive.Div>

      {/* CHIẾC LỐP ĐƠN */}
      <Interactive.Div
        name="Chiếc lốp đơn lẻ"
        from={3}
        durationInFrames={46}
        style={{position: 'absolute', left: 550, top: 430, width: 820, height: 520}}
      >
        <LopCo anh={anh_lop_co} phong={phong_lop} />
      </Interactive.Div>

      {/* THÁP LỐP PHẾ LIỆU */}
      <Interactive.Div
        name="Tháp lốp phế liệu"
        from={49}
        durationInFrames={62}
        style={{position: 'absolute', left: 340, top: 330, width: 1240, height: 650}}
      >
        <ThapLop anh={anh_thap_lop} phong={phong_thap} />
      </Interactive.Div>

      {/* ẢNH HỎA HOẠN (nằm dưới lớp muỗi, hiện ra khi muỗi whip-pan đi) */}
      <Interactive.Div
        name="Cận cảnh lửa và khói"
        from={248}
        durationInFrames={76}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <HoaHoan anh={anh_can_hoa_hoan} phong={phong_lua} />
      </Interactive.Div>

      {/* LỚP PHỦ MACRO: lăng quăng và muỗi */}
      <Interactive.Div
        name="Lớp phủ macro muỗi"
        from={182}
        durationInFrames={72}
        style={{position: 'absolute', left: 170, top: 100, width: 1580, height: 880}}
      >
        <CanMuoi anh={anh_can_muoi} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
