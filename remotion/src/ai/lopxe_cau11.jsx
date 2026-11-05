import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

/* ---------- helpers ---------- */
const dinhDang = (n) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');

/* ---------- schema ---------- */
export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền thảo nguyên khô cằn Arizona'),
  anhBo: z.string().describe('Ảnh cắt trong suốt đàn bò'),
  soDau: z.number().describe('Số con ban đầu'),
  soCuoi: z.number().describe('Số con sau khi tăng vọt'),
  donVi: z.string().describe('Đơn vị của con số'),
  khungBatDau: z.number().describe('Frame bắt đầu hiện counter và đồ thị cột'),
  khungNhay: z.number().describe('Frame (cục bộ) counter bắt đầu nhảy số'),
  soFrameNhay: z.number().describe('Số frame counter nhảy số'),
  khungBo: z.number().describe('Frame lớp cắt đàn bò xuất hiện'),
  xDem: z.number().describe('Toạ độ X của counter'),
  yDem: z.number().describe('Toạ độ Y của counter'),
  coDem: z.number().describe('Cỡ chữ con số'),
  mauDem: z.string().describe('Màu con số'),
  mauDonVi: z.string().describe('Màu chữ đơn vị'),
  xCot: z.number().describe('Toạ độ X của đồ thị cột'),
  yCot: z.number().describe('Toạ độ Y của đồ thị cột'),
  rongCot: z.number().describe('Chiều rộng mỗi cột'),
  khoangCot: z.number().describe('Khoảng cách giữa hai cột'),
  caoCot1: z.number().describe('Chiều cao cột nhỏ (mốc ban đầu)'),
  caoCot2: z.number().describe('Chiều cao cột lớn (mốc tăng vọt)'),
  mauCot1: z.string().describe('Màu cột nhỏ'),
  mauCot2: z.string().describe('Màu cột lớn'),
  xBo: z.number().describe('Toạ độ X của lớp đàn bò'),
  yBo: z.number().describe('Toạ độ Y của lớp đàn bò'),
  rongBo: z.number().describe('Chiều rộng lớp đàn bò'),
});

/* ---------- counter ---------- */
// Chỉ hiển thị đúng con số lời thoại đọc: "một triệu rưỡi con" (1.500.000).
const BoDem = ({soCuoi, donVi, co, mauDem, mauDonVi, khungNhay}) => {
  const frame = useCurrentFrame();

  const hien = interpolate(frame, [khungNhay, khungNhay + 10], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const nhun = interpolate(frame, [khungNhay, khungNhay + 8, khungNhay + 30], [0.72, 1.13, 1], kep);
  const truot = interpolate(frame, [khungNhay, khungNhay + 12], [26, 0], {...kep, easing: Easing.out(Easing.cubic)});

  return (
    <div
      style={{
        fontFamily: FONT,
        fontWeight: 900,
        whiteSpace: 'nowrap',
        display: 'flex',
        alignItems: 'baseline',
        gap: 20,
        opacity: hien,
        transform: `translateY(${truot}px) scale(${nhun})`,
        transformOrigin: 'left bottom',
        textShadow: '0 10px 30px rgba(0,0,0,0.65), 0 2px 6px rgba(0,0,0,0.5)',
      }}
    >
      <span style={{fontSize: co, color: mauDem, letterSpacing: -3, lineHeight: 1}}>{dinhDang(soCuoi)}</span>
      <span style={{fontSize: co * 0.4, color: mauDonVi, fontWeight: 700, lineHeight: 1}}>{donVi}</span>
    </div>
  );
};

/* ---------- bar chart ---------- */
const DoThiCot = ({rong, khoang, cao1, cao2, mau1, mau2, khungNhay, soFrameNhay}) => {
  const frame = useCurrentFrame();

  const g1 = interpolate(frame, [0, 18], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const g2 = interpolate(frame, [khungNhay, khungNhay + soFrameNhay], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  const h1 = Math.max(2, cao1 * g1);
  const h2 = Math.max(2, cao1 + (cao2 - cao1) * g2);
  const co = {position: 'absolute', bottom: 0, width: rong, borderRadius: '8px 8px 0 0'};

  return (
    <div style={{position: 'relative', width: rong * 2 + khoang, height: cao2}}>
      <div style={{...co, left: 0, height: h1, background: mau1}} />
      <div style={{...co, left: rong + khoang, height: h2, background: mau2, boxShadow: '0 10px 30px rgba(0,0,0,0.35)'}} />
    </div>
  );
};

/* ---------- photo card cut-out (in front) ---------- */
const TheAnh = ({anh, rong, nhan}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const vao = spring({frame, fps, config: {damping: 20, mass: 1, stiffness: 90}});
  const y = interpolate(vao, [0, 1], [90, 0]);
  const op = interpolate(frame, [0, 14], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const xoay = interpolate(vao, [0, 1], [4, -2]);

  return (
    <div style={{opacity: op, transform: `translateY(${y}px) rotate(${xoay}deg)`}}>
      <div style={{background: '#ffffff', padding: 16, borderRadius: 14, boxShadow: '0 30px 60px rgba(0,0,0,0.5)'}}>
        <Img src={src(anh)} style={{width: rong, height: 'auto', display: 'block', borderRadius: 6}} />
        <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 30, color: '#1a1a1a', textAlign: 'center', paddingTop: 12, letterSpacing: 1}}>{nhan}</div>
      </div>
    </div>
  );
};

/* ---------- circular inset close-up (in front) ---------- */
const CanhGan = ({anh, size}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const vao = spring({frame, fps, config: {damping: 22, mass: 1, stiffness: 80}});
  const s = interpolate(vao, [0, 1], [0.55, 1]);

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        overflow: 'hidden',
        border: '10px solid #ffffff',
        boxShadow: '0 22px 44px rgba(0,0,0,0.5)',
        transform: `scale(${s})`,
        background: '#222',
      }}
    >
      <Img
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: '45% 55%', transform: 'scale(1.7)', transformOrigin: '45% 55%'}}
      />
    </div>
  );
};

/* ---------- pulsing ring ---------- */
const VongNhip = ({size}) => {
  const frame = useCurrentFrame();
  const p = (frame % 40) / 40;
  const s = interpolate(p, [0, 1], [1, 1.28]);
  const o = interpolate(p, [0, 1], [0.75, 0]);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: size,
        height: size,
        borderRadius: '50%',
        border: '6px solid #FFD166',
        transform: `scale(${s})`,
        opacity: o,
        pointerEvents: 'none',
      }}
    />
  );
};

/* ---------- downward arrow ---------- */
const MuiTenXuong = ({size, mau}) => (
  <div
    style={{
      width: 0,
      height: 0,
      borderLeft: `${size}px solid transparent`,
      borderRight: `${size}px solid transparent`,
      borderTop: `${size * 1.4}px solid ${mau}`,
      filter: 'drop-shadow(0 8px 12px rgba(0,0,0,0.55))',
    }}
  />
);

/* ---------- main shot ---------- */
export const Canh = (props) => {
  const {
    anhNen, anhBo, soCuoi, donVi, khungBatDau, khungNhay, soFrameNhay, khungBo,
    xDem, yDem, coDem, mauDem, mauDonVi,
    xCot, yCot, rongCot, khoangCot, caoCot1, caoCot2, mauCot1, mauCot2,
    xBo, yBo, rongBo,
  } = props;

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {/* Nền thảo nguyên: trôi chậm suốt 144 frame */}
      <Interactive.Div
        name="Nền thảo nguyên"
        from={0}
        durationInFrames={144}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anhNen} tu={1.02} den={1.13} goc={'50% 55%'} toi={0.16} />
      </Interactive.Div>

      {/* Đồ thị cột: hiện ngay từ đầu, cột lớn vọt cao từ khungNhay */}
      <Interactive.Div
        name="Đồ thị cột"
        from={0}
        durationInFrames={144}
        style={{position: 'absolute', left: xCot, top: yCot}}
      >
        <DoThiCot
          rong={rongCot}
          khoang={khoangCot}
          cao1={caoCot1}
          cao2={caoCot2}
          mau1={mauCot1}
          mau2={mauCot2}
          khungNhay={khungNhay}
          soFrameNhay={soFrameNhay}
        />
      </Interactive.Div>

      {/* Thẻ ảnh cắt đàn bò phía trước, tạo chiều sâu */}
      <Interactive.Div
        name="Thẻ ảnh đàn bò"
        from={0}
        durationInFrames={144}
        style={{position: 'absolute', left: xBo, top: yBo}}
      >
        <TheAnh anh={anhBo} rong={rongBo} nhan="ĐÀN BÒ" />
      </Interactive.Div>

      {/* Mũi tên chỉ xuống thẻ ảnh */}
      <Interactive.Div
        name="Mũi tên chỉ thẻ ảnh"
        from={0}
        durationInFrames={144}
        style={{position: 'absolute', left: xBo + rongBo / 2 - 34, top: yBo - 80}}
      >
        <MuiTenXuong size={34} mau="#FFD166" />
      </Interactive.Div>

      {/* Ảnh cận cảnh tròn phía trước + vòng nhấp nháy */}
      <Interactive.Div
        name="Cận cảnh đàn bò"
        from={0}
        durationInFrames={144}
        style={{position: 'absolute', left: 120, top: 640}}
      >
        <div style={{position: 'relative', width: 280, height: 280}}>
          <VongNhip size={280} />
          <CanhGan anh={anhBo} size={280} />
        </div>
      </Interactive.Div>

      {/* Counter HUD ở góc trên */}
      <Interactive.Div
        name="Con số đàn bò"
        from={0}
        durationInFrames={144}
        style={{position: 'absolute', left: xDem, top: yDem}}
      >
        <BoDem
          soCuoi={soCuoi}
          donVi={donVi}
          co={coDem}
          mauDem={mauDem}
          mauDonVi={mauDonVi}
          khungNhay={khungNhay}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
