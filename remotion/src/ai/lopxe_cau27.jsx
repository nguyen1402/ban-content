import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền flycam toàn cảnh bãi rác lốp xe'),
  anhLop: z.string().describe('Ảnh cắt lớp lốp xe cũ phía trước (tạo chiều sâu)'),
  soLuong: z.number().describe('Con số lốp xe thải hiển thị'),
  phanTram: z.number().describe('Tỷ lệ tái chế (%) cho thanh chỉ số'),
  coSo: z.number().describe('Cỡ chữ con số lớn'),
  coNhan: z.number().describe('Cỡ chữ nhãn phần trăm'),
  mauSo: z.string().describe('Màu con số'),
  mauThanh: z.string().describe('Màu thanh tỷ lệ và nhãn'),
  rongLop: z.number().describe('Chiều rộng lớp lốp xe cận cảnh (px)'),
});

/* Nền flycam toàn cảnh: luôn phủ kín 100% khung hình, push-in rất chậm suốt cả cảnh */
const NenToanCanh: React.FC<{anh: string}> = ({anh}) => {
  const f = useCurrentFrame();
  const phong = interpolate(f, [0, 313], [1.04, 1.16], kep);
  const mo = interpolate(f, [0, 16], [0, 1], {...kep, easing: Easing.out(Easing.quad)});

  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#0e0e0e'}}>
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: '50% 45%',
          display: 'block',
          opacity: mo,
          transform: `scale(${phong})`,
          transformOrigin: '50% 45%',
          filter: 'brightness(0.92) contrast(1.06) saturate(1.03)',
        }}
      />
    </AbsoluteFill>
  );
};

/* Lớp lốp xe cận cảnh phía trước: phóng chậm tạo chiều sâu, cuối nhịp trượt xuống */
const LopTruoc: React.FC<{anh: string; rong: number}> = ({anh, rong}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 14], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const phong = interpolate(f, [0, 176], [0.96, 1.12], kep);
  const truot = interpolate(f, [0, 176], [48, -30], kep);
  const thoat = interpolate(f, [152, 175], [0, 1], {...kep, easing: Easing.in(Easing.cubic)});

  return (
    <div
      style={{
        opacity: vao * (1 - thoat),
        transform: `translate(${truot * 0.35}px, ${truot + thoat * 320}px) scale(${phong})`,
        transformOrigin: '28% 82%',
      }}
    >
      <Img
        src={src(anh)}
        style={{
          width: rong,
          height: 'auto',
          display: 'block',
          filter: 'brightness(0.94) contrast(1.06)',
        }}
      />
    </div>
  );
};

export const Canh: React.FC<z.infer<typeof schema>> = ({
  anhNen,
  anhLop,
  soLuong,
  phanTram,
  coSo,
  coNhan,
  mauSo,
  mauThanh,
  rongLop,
}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#121212'}}>
      {/* Nhịp 1 — flycam toàn cảnh bãi lốp, phủ kín khung hình suốt cả cảnh */}
      <Interactive.Div
        name="Nền flycam bãi lốp xe"
        from={0}
        durationInFrames={313}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NenToanCanh anh={anhNen} />
      </Interactive.Div>

      {/* Nhịp 1 — lớp lốp xe cắt phía trước, phóng chậm tạo chiều sâu */}
      <Interactive.Div
        name="Lớp lốp xe cận cảnh phía trước"
        from={4}
        durationInFrames={176}
        style={{position: 'absolute', left: -140, top: 430}}
      >
        <LopTruoc anh={anhLop} rong={rongLop} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
