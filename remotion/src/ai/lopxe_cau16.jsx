import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_trang_trai: z.string().describe('Ảnh góc cao toàn cảnh trang trại King Anvil'),
  anh_bien_hieu: z.string().describe('Ảnh biển hiệu gỗ King Anvil Ranch (tách nền)'),
  anh_can_ranh_xoi: z.string().describe('Ảnh cận cảnh lòng rãnh xói sâu'),
  anh_nha_trang_trai: z.string().describe('Ảnh ngôi nhà trang trại bên mép vực (tách nền)'),
  mau_net_do: z.string().describe('Màu nét vẽ đồ hoạ rãnh xói'),
  day_net_do: z.number().describe('Độ dày nét vẽ rãnh xói (px)'),
  rong_bien_hieu: z.number().describe('Chiều rộng biển hiệu (px)'),
  rong_nha: z.number().describe('Chiều rộng ngôi nhà trang trại (px)'),
  do_toi_nen: z.number().describe('Độ tối lớp phủ trên ảnh nền (0 - 0.5)'),
  quang_pan: z.number().describe('Quãng pan ảnh toàn cảnh (px)'),
  zoom_dau: z.number().describe('Tỉ lệ zoom đầu của ảnh cận cảnh'),
  zoom_cuoi: z.number().describe('Tỉ lệ zoom cuối của ảnh cận cảnh'),
});

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

/* ---------- Nét vẽ đồ hoạ đỏ cắt ngang khu đất (vẽ dần) ---------- */
const NetRanhXoi = ({mau, day}) => {
  const f = useCurrentFrame();
  const ve = interpolate(f, [2, 36], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    ...CLAMP,
  });
  const mo = interpolate(f, [0, 5, 46, 56], [0, 1, 1, 0], CLAMP);

  return (
    <svg
      width={1920}
      height={1080}
      viewBox="0 0 1920 1080"
      style={{position: 'absolute', left: 0, top: 0, opacity: mo}}
    >
      <path
        d="M -40 726 C 270 646 520 792 830 706 C 1140 620 1432 764 1960 662"
        fill="none"
        stroke={mau}
        strokeWidth={day}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray="1"
        strokeDashoffset={1 - ve}
      />
      <path
        d="M -40 726 C 270 646 520 792 830 706 C 1140 620 1432 764 1960 662"
        fill="none"
        stroke={mau}
        strokeWidth={Math.max(2, day * 0.28)}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.55}
        pathLength={1}
        strokeDasharray="1"
        strokeDashoffset={1 - ve}
        transform="translate(0 -16)"
      />
    </svg>
  );
};

/* ---------- Biển hiệu gỗ tách lớp trồi lên ---------- */
const BienHieu = ({anh, rong}) => {
  const f = useCurrentFrame();
  const vao = spring({frame: f, fps: 30, config: {damping: 14, mass: 0.7, stiffness: 90}});
  const y = interpolate(vao, [0, 1], [130, 0]);
  const mo = interpolate(f, [0, 7, 46, 58], [0, 1, 1, 0], CLAMP);
  const lac = Math.sin(f / 30) * 1.3;

  return (
    <div
      style={{
        width: rong,
        opacity: mo,
        transform: `translateY(${y}px) rotate(${lac}deg)`,
        transformOrigin: '50% 50%',
        filter: 'drop-shadow(0 26px 34px rgba(0,0,0,0.45))',
      }}
    >
      <Img src={src(anh)} style={{width: rong, display: 'block'}} />
    </div>
  );
};

/* ---------- Ngôi nhà trang trại chênh vênh bên mép vực ---------- */
const NhaTrangTrai = ({anh, rong}) => {
  const f = useCurrentFrame();
  const vao = spring({frame: f, fps: 30, config: {damping: 17, mass: 0.9, stiffness: 70}});
  const x = interpolate(vao, [0, 1], [-190, 0]);
  const rotVao = interpolate(vao, [0, 1], [-10, -3]);
  const rung = Math.sin(f / 33) * 0.9;
  const mo = interpolate(f, [0, 5], [0.4, 1], CLAMP);

  return (
    <div
      style={{
        width: rong,
        opacity: mo,
        transform: `translateX(${x}px) rotate(${rotVao + rung}deg)`,
        transformOrigin: '50% 100%',
        filter: 'drop-shadow(0 30px 40px rgba(0,0,0,0.5))',
      }}
    >
      <Img src={src(anh)} style={{width: rong, display: 'block'}} />
    </div>
  );
};

export const Canh = (props) => {
  const f = useCurrentFrame();
  const moNen2 = interpolate(f, [55, 62], [0, 1], {
    easing: Easing.inOut(Easing.ease),
    ...CLAMP,
  });

  return (
    <AbsoluteFill>
      {/* Nhịp 1 — toàn cảnh trang trại từ trên cao, pan chậm sang phải */}
      <Interactive.Div
        name="Toàn cảnh trang trại King Anvil"
        from={0}
        durationInFrames={64}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia
          anh={props.anh_trang_trai}
          huong="phai"
          quang={props.quang_pan}
          phong={1.14}
          toi={props.do_toi_nen}
        />
      </Interactive.Div>

      {/* Nhịp 2 — cận cảnh lòng rãnh xói, đẩy máy vào sâu */}
      <Interactive.Div
        name="Cận cảnh lòng rãnh xói"
        from={55}
        durationInFrames={92}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: moNen2}}
      >
        <AnhNen
          anh={props.anh_can_ranh_xoi}
          tu={props.zoom_dau}
          den={props.zoom_cuoi}
          goc="50% 55%"
          toi={props.do_toi_nen}
        />
      </Interactive.Div>

      {/* Nét vẽ đồ hoạ đỏ xuất hiện cắt ngang khu đất */}
      <Interactive.Div
        name="Nét vẽ đỏ rãnh xói"
        from={4}
        durationInFrames={58}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <NetRanhXoi mau={props.mau_net_do} day={props.day_net_do} />
      </Interactive.Div>

      {/* Biển hiệu gỗ tách lớp phía trước */}
      <Interactive.Div
        name="Biển hiệu King Anvil Ranch"
        from={4}
        durationInFrames={58}
        style={{position: 'absolute', left: 510, top: 470}}
      >
        <BienHieu anh={props.anh_bien_hieu} rong={props.rong_bien_hieu} />
      </Interactive.Div>

      {/* Ngôi nhà trang trại chênh vênh bên bờ vực */}
      <Interactive.Div
        name="Nhà trang trại bên mép vực"
        from={55}
        durationInFrames={92}
        style={{position: 'absolute', left: 180, top: 490}}
      >
        <NhaTrangTrai anh={props.anh_nha_trang_trai} rong={props.rong_nha} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
