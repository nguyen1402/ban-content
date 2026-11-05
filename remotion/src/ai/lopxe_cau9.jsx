import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhDongCo: z.string().describe('Ảnh đồng cỏ khô cằn Arizona'),
  anhTrangTrai: z.string().describe('Ảnh trang trại lịch sử 1870'),
  anhDanBo: z.string().describe('Ảnh đàn bò thưa thớt'),
  chuQuyetDinh: z.string().describe('Dòng chữ quyết định ngắn (tối đa 4 từ)'),
  coChuQuyetDinh: z.number().describe('Cỡ chữ dòng quyết định'),
  chuNam: z.string().describe('Số năm hiển thị trong hộp'),
  coChuNam: z.number().describe('Cỡ chữ số năm'),
  soBo: z.number().describe('Số lượng bò'),
  donViBo: z.string().describe('Đơn vị số lượng bò'),
  giayDem: z.number().describe('Số giây đếm số bò'),
  coSoDem: z.number().describe('Cỡ chữ bộ đếm'),
  mauChu: z.string().describe('Màu chữ chính'),
});

export const Canh = (props) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---- crossfade giữa ba lớp ảnh (không có khoảng trống) ----
  const op1 = interpolate(f, [0, 14, 152, 168], [0, 1, 1, 0], {...kep, easing: Easing.inOut(Easing.ease)});
  const op2 = interpolate(f, [158, 174, 266, 280], [0, 1, 1, 0], {...kep, easing: Easing.inOut(Easing.ease)});
  const op3 = interpolate(f, [272, 290], [0, 1], {...kep, easing: Easing.out(Easing.ease)});

  // ---- lớp chữ quyết định (mờ ảo) ----
  const chuOp = interpolate(f, [6, 48, 118, 146], [0, 0.94, 0.94, 0], {...kep, easing: Easing.inOut(Easing.ease)});
  const chuY = interpolate(f, [6, 52], [46, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const gachW = interpolate(f, [26, 82], [0, 540], {...kep, easing: Easing.out(Easing.cubic)});

  // ---- hộp số năm 1870 ----
  const namSpring = spring({frame: f - 162, fps, config: {damping: 200, mass: 0.9, stiffness: 90}});
  const namOp = interpolate(f, [162, 184], [0, 1], {...kep, easing: Easing.out(Easing.ease)});
  const namX = (1 - namSpring) * 110;

  // ---- bộ đếm số bò ----
  const demOp = interpolate(f, [276, 294], [0, 1], {...kep, easing: Easing.out(Easing.ease)});
  const demY = interpolate(f, [276, 296], [46, 0], {...kep, easing: Easing.out(Easing.cubic)});

  return (
    <AbsoluteFill style={{backgroundColor: '#0d0b09'}}>
      {/* ===== LỚP ẢNH 1 : đồng cỏ Arizona ===== */}
      <Interactive.Div
        name="Ảnh đồng cỏ Arizona"
        from={0}
        durationInFrames={168}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op1}}>
          <AnhNen anh={props.anhDongCo} tu={1.02} den={1.13} goc="50% 45%" toi={0.38} />
        </div>
      </Interactive.Div>

      {/* ===== LỚP ẢNH 2 : trang trại lịch sử ===== */}
      <Interactive.Div
        name="Ảnh trang trại 1870"
        from={160}
        durationInFrames={120}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op2}}>
          <AnhNen anh={props.anhTrangTrai} tu={1.14} den={1.02} goc="50% 52%" toi={0.3} />
        </div>
      </Interactive.Div>

      {/* ===== LỚP ẢNH 3 : đàn bò thưa thớt (giữ tới cuối) ===== */}
      <Interactive.Div
        name="Ảnh đàn bò thưa thớt"
        from={274}
        durationInFrames={58}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op3}}>
          <AnhNen anh={props.anhDanBo} tu={1.02} den={1.1} goc="50% 55%" toi={0.26} />
        </div>
      </Interactive.Div>

      {/* ===== CHỮ : quyết định ngắn ===== */}
      <Interactive.Div
        name="Chữ quyết định"
        from={6}
        durationInFrames={140}
        style={{position: 'absolute', left: 230, top: 392}}
      >
        <div style={{opacity: chuOp, transform: `translateY(${chuY}px)`}}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: props.coChuQuyetDinh,
              lineHeight: 1.18,
              letterSpacing: 3,
              fontWeight: 600,
              color: props.mauChu,
              whiteSpace: 'pre-line',
              maxWidth: 1100,
              textShadow: '0 6px 30px rgba(0,0,0,0.55)',
            }}
          >
            {props.chuQuyetDinh}
          </div>
          <div
            style={{
              marginTop: 28,
              width: gachW,
              height: 4,
              background: VANG,
              opacity: 0.85,
              borderRadius: 2,
            }}
          />
        </div>
      </Interactive.Div>

      {/* ===== HỘP SỐ NĂM 1870 ===== */}
      <Interactive.Div
        name="Hộp số năm 1870"
        from={162}
        durationInFrames={118}
        style={{position: 'absolute', left: 1362, top: 148}}
      >
        <div
          style={{
            width: 420,
            height: 236,
            border: `3px solid ${VANG}`,
            borderRadius: 10,
            background: 'rgba(12,10,8,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: namOp,
            transform: `translateX(${namX}px)`,
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: props.coChuNam,
              fontWeight: 700,
              letterSpacing: 8,
              color: VANG,
              lineHeight: 1,
            }}
          >
            {props.chuNam}
          </div>
        </div>
      </Interactive.Div>

      {/* ===== BỘ ĐẾM SỐ BÒ ===== */}
      <Interactive.Div
        name="Bộ đếm số bò"
        from={276}
        durationInFrames={56}
        style={{position: 'absolute', left: 160, top: 700}}
      >
        <div
          style={{
            opacity: demOp,
            transform: `translateY(${demY}px)`,
            background: 'rgba(10,8,6,0.42)',
            padding: '20px 48px 24px 48px',
            borderRadius: 16,
            display: 'inline-block',
          }}
        >
          <SoDem so={props.soBo} don_vi={props.donViBo} giay={props.giayDem} co={props.coSoDem} />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
