import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhBao: z.string().describe('Ảnh trang báo cũ thập niên 1970 về vụ lốp xe Florida'),
  anhSaMac: z.string().describe('Ảnh nền sa mạc với chồng lốp xe phủ băng'),
  anhChongLop: z.string().describe('Ảnh cắt lớp chồng lốp xe cũ giữa sa mạc'),
  fBao: z.number().describe('Khung hình bắt đầu cảnh trang báo cũ'),
  fTruot: z.number().describe('Khung hình bắt đầu cú trượt ngang sang sa mạc'),
  fDongBang: z.number().describe('Khung hình punch-in đóng băng'),
  fCham: z.number().describe('Khung hình camera chậm lại gần như đứng hình'),
  thoiLuong: z.number().describe('Tổng số khung hình của cảnh'),
  quangBao: z.number().describe('Quãng lia ngang của trang báo (px)'),
  phongBao: z.number().describe('Độ phóng của trang báo'),
  toiBao: z.number().describe('Độ tối lớp phủ trang báo'),
  toiSaMac: z.number().describe('Độ tối lớp phủ nền sa mạc'),
  xLop: z.number().describe('Toạ độ X của chồng lốp'),
  yLop: z.number().describe('Toạ độ Y của chồng lốp'),
  wLop: z.number().describe('Chiều rộng chồng lốp'),
  hLop: z.number().describe('Chiều cao chồng lốp'),
  doTruot: z.number().describe('Quãng trượt vào của chồng lốp (px)'),
  doBang: z.number().describe('Độ mạnh cú punch-in khi đóng băng'),
  doTruotNen: z.number().describe('Độ phóng chậm của nền sa mạc'),
  doBangMo: z.number().describe('Độ đậm lớp băng phủ lốp'),
  doVang: z.number().describe('Độ đậm ánh nắng vàng cuối cảnh'),
});

export const Canh = (props) => {
  const {
    anhBao, anhSaMac, anhChongLop,
    fBao, fTruot, fDongBang, fCham, thoiLuong,
    quangBao, phongBao, toiBao, toiSaMac,
    xLop, yLop, wLop, hLop,
    doTruot, doBang, doTruotNen, doBangMo, doVang,
  } = props;

  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- Cú trượt ngang (slide transition) tại fTruot ---------- */
  const tien = interpolate(frame, [fTruot, fTruot + 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  const baoX = -1920 * tien;
  const saMacX = 1920 * (1 - tien);

  /* ---------- Trang báo: lia ngang + phóng chậm từ fBao ---------- */
  const baoScale = interpolate(frame, [fBao, fBao + 74], [1, 1.07], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  /* ---------- Nền sa mạc: vẫn tiếp tục phóng rất chậm ---------- */
  const saMacScale = interpolate(frame, [fTruot, thoiLuong], [1, 1 + doTruotNen], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.linear,
  });

  /* ---------- Chồng lốp: trượt vào, punch-in, rồi chậm dần ---------- */
  const lopX = interpolate(frame, [fTruot, fTruot + 14], [doTruot, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const lopVao = interpolate(frame, [fTruot, fTruot + 12], [1.14, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const lopTroi = interpolate(frame, [fTruot + 12, fDongBang, fCham, thoiLuong], [0, 0.035, 0.055, 0.075], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.linear,
  });

  const punch = interpolate(frame, [fDongBang, fDongBang + 7], [0, doBang], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const lopScale = lopVao + lopTroi + punch;

  /* ---------- Lớp băng mỏng phủ lốp ---------- */
  const bangMo = interpolate(frame, [fDongBang, fDongBang + 12], [0, doBangMo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  const quet = interpolate(frame, [fDongBang, fDongBang + 34], [130, -30], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });

  /* ---------- Ánh nắng vàng cuối cảnh ---------- */
  const vangMo = interpolate(frame, [fCham, thoiLuong], [0, doVang], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  const maskUrl = `url(${src(anhChongLop)})`;
  const maskStyle = {
    WebkitMaskImage: maskUrl,
    maskImage: maskUrl,
    WebkitMaskSize: '100% 100%',
    maskSize: '100% 100%',
    WebkitMaskRepeat: 'no-repeat',
    maskRepeat: 'no-repeat',
    WebkitMaskPosition: 'center',
    maskPosition: 'center',
  };

  return (
    <AbsoluteFill style={{backgroundColor: '#120f0c'}}>

      {/* ===== NỀN SA MẠC (nằm dưới, lộ ra khi trang báo trượt đi) ===== */}
      <Interactive.Div
        name="Nền sa mạc đóng băng"
        from={100}
        durationInFrames={174}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${saMacX}px) scale(${saMacScale})`,
            transformOrigin: '50% 55%',
          }}
        >
          <AnhNen anh={anhSaMac} tu={1.18} den={1.02} goc="50% 55%" toi={toiSaMac} />
        </div>
      </Interactive.Div>

      {/* ===== TRANG BÁO CŨ (lớp trên, trượt sang trái tại fTruot) ===== */}
      <Interactive.Div
        name="Trang báo cũ Florida"
        from={0}
        durationInFrames={116}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${baoX}px) scale(${baoScale})`,
            transformOrigin: '50% 50%',
          }}
        >
          <AnhLia anh={anhBao} huong="phai" quang={quangBao} phong={phongBao} toi={toiBao} />
        </div>
      </Interactive.Div>

      {/* ===== CHỒNG LỐP XE (chủ thể, trượt vào rồi đóng băng) ===== */}
      <Interactive.Div
        name="Chồng lốp xe giữa sa mạc"
        from={107}
        durationInFrames={167}
        style={{position: 'absolute', left: xLop, top: yLop, width: wLop, height: hLop}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: wLop,
            height: hLop,
            transform: `translateX(${lopX}px) scale(${lopScale})`,
            transformOrigin: '50% 58%',
          }}
        >
          <Img
            name="Ảnh cắt lớp chồng lốp"
            src={src(anhChongLop)}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: wLop,
              height: hLop,
              objectFit: 'contain',
            }}
          />

          {/* Lớp băng mỏng phủ kín các khung lốp */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: wLop,
              height: hLop,
              opacity: bangMo,
              background:
                'linear-gradient(135deg, rgba(216,244,255,0.95) 0%, rgba(255,255,255,0.35) 28%, rgba(190,228,255,0.85) 52%, rgba(255,255,255,0.4) 72%, rgba(176,216,255,0.9) 100%)',
              ...maskStyle,
            }}
          />

          {/* Vệt sáng quét trên mặt băng */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: wLop,
              height: hLop,
              opacity: bangMo * 0.85,
              background:
                'linear-gradient(100deg, rgba(255,255,255,0) 34%, rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 66%)',
              backgroundSize: '260% 100%',
              backgroundRepeat: 'no-repeat',
              backgroundPosition: `${quet}% 0`,
              mixBlendMode: 'screen',
              ...maskStyle,
            }}
          />
        </div>
      </Interactive.Div>

      {/* ===== ÁNH NẮNG VÀNG CUỐI CẢNH ===== */}
      <Interactive.Div
        name="Ánh nắng vàng cuối cảnh"
        from={194}
        durationInFrames={80}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: vangMo,
            mixBlendMode: 'screen',
            background:
              'linear-gradient(205deg, rgba(255,212,132,0.9) 0%, rgba(255,190,100,0.42) 42%, rgba(255,170,80,0) 78%)',
          }}
        />
      </Interactive.Div>

    </AbsoluteFill>
  );
};
