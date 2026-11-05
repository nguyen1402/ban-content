import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, AnhNen, AnhLia} from './thu_vien.jsx';

export const schema = z.object({
  anh_ban_lam_viec: z.string().describe('Ảnh nền bàn làm việc bộn bề, đèn vàng ấm'),
  anh_tai_lieu: z.string().describe('Ảnh thẻ chồng hồ sơ rối ren'),
  anh_cua_so: z.string().describe('Ảnh nền khung cửa sổ ngập ánh sáng, chậu cây'),
  quang_truot_ban: z.number().describe('Quãng trượt ngang ảnh bàn làm việc (px)'),
  toi_ban_lam_viec: z.number().describe('Độ tối ảnh bàn làm việc (0–0.5)'),
  phong_cua_so_tu: z.number().describe('Tỉ lệ phóng ảnh cửa sổ lúc bắt đầu'),
  phong_cua_so_den: z.number().describe('Tỉ lệ phóng ảnh cửa sổ lúc kết thúc'),
  the_toc_do: z.number().describe('Độ cứng lò xo khi thẻ trượt vào'),
  the_nghieng: z.number().describe('Độ nghiêng của thẻ hồ sơ (độ)'),
  the_le_tren: z.number().describe('Khoảng cách từ đáy thẻ tới đường nét nhấn (px)'),
  mau_nhan: z.string().describe('Màu đường nét nhấn dưới thẻ'),
});

/* ---------- LỚP 1: nền bàn làm việc, trượt ngang sang phải ---------- */
const NenBanLamViec = ({anh, quang, toi}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [182, 200], [1, 0], kep);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op}}>
      <AnhLia anh={anh} huong="phai" quang={quang} toi={toi} />
    </div>
  );
};

/* ---------- LỚP 3: nền cửa sổ, lùi máy nhẹ ---------- */
const NenCuaSo = ({anh, tu, den}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 16], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op}}>
      <AnhNen anh={anh} tu={tu} den={den} goc="50% 55%" toi={0.05} />
    </div>
  );
};

/* ---------- LỚP 2: thẻ hồ sơ trượt vào từ trái ---------- */
const TheHoSo = ({anh, nghieng, leTren, mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  const vao = spring({frame: f, fps, config: {damping: 20, mass: 1, stiffness: 95}});
  const ra = interpolate(f, [100, 122], [0, 1], {...kep, easing: Easing.in(Easing.cubic)});

  const tx = (1 - vao) * -1150 - ra * 1250;
  const rot = nghieng + (1 - vao) * -5;
  const op = interpolate(f, [0, 5, 104, 122], [0, 1, 1, 0], kep);

  const net1 = interpolate(f, [14, 38], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const net2 = interpolate(f, [22, 48], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: '100%',
        height: '100%',
        opacity: op,
        transform: `translateX(${tx}px)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '100%',
          height: '100%',
          borderRadius: 18,
          overflow: 'hidden',
          transform: `rotate(${rot}deg)`,
          boxShadow: '0 34px 90px rgba(0,0,0,0.55)',
          border: '2px solid rgba(255,255,255,0.30)',
          backgroundColor: '#141210',
        }}
      >
        <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </div>

      <div
        style={{
          position: 'absolute',
          left: 0,
          top: leTren,
          width: '100%',
          height: 5,
          backgroundColor: mau,
          transform: `scaleX(${net1})`,
          transformOrigin: 'left center',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: leTren + 26,
          width: '58%',
          height: 3,
          backgroundColor: mau,
          opacity: 0.65,
          transform: `scaleX(${net2})`,
          transformOrigin: 'left center',
        }}
      />
    </div>
  );
};

/* ---------- CẢNH ---------- */
export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0d0b09', overflow: 'hidden'}}>
      <Interactive.Div
        name="Nền bàn làm việc"
        from={0}
        durationInFrames={200}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NenBanLamViec
          anh={props.anh_ban_lam_viec}
          quang={props.quang_truot_ban}
          toi={props.toi_ban_lam_viec}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Nền cửa sổ"
        from={184}
        durationInFrames={140}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NenCuaSo anh={props.anh_cua_so} tu={props.phong_cua_so_tu} den={props.phong_cua_so_den} />
      </Interactive.Div>

      <Interactive.Div
        name="Thẻ hồ sơ rối ren"
        from={88}
        durationInFrames={130}
        style={{position: 'absolute', left: 150, top: 230, width: 940, height: 640}}
      >
        <TheHoSo
          anh={props.anh_tai_lieu}
          nghieng={props.the_nghieng}
          leTren={props.the_le_tren}
          mau={props.mau_nhan}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
