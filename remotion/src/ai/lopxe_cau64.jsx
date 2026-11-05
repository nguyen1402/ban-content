import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhSuoi: z.string().describe('Ảnh toàn cảnh lòng suối sỏi đá sau lũ'),
  anhNhom: z.string().describe('Ảnh cắt rời nhóm người kiểm tra hiện trường'),
  anhDap: z.string().describe('Ảnh cận cảnh đoạn đập đá bị hư hại'),
  anhCongTruong: z.string().describe('Ảnh công trường đập dưới nắng mùa hè'),
  mauVong: z.string().describe('Màu vòng tròn đánh dấu điểm hư hại'),
  rongNhom: z.number().describe('Chiều rộng nhóm người ở tiền cảnh (px)'),
  mauQuetSang: z.string().describe('Màu vệt quét sáng trên công trường'),
  doMoQuetSang: z.number().describe('Độ mờ vệt quét sáng (0..1)'),
  gocXoayQuet: z.number().describe('Góc nghiêng vệt quét sáng (độ)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---------- NHỊP 1 : toàn cảnh suối đá + nhóm người (bắt đầu frame 3) ----------
  const f1 = frame - 3;
  const xNhom =
    interpolate(f1, [0, 46], [-1000, 140], {...kep, easing: Easing.out(Easing.cubic)}) +
    interpolate(f1, [46, 120], [0, 80], kep);
  const scaleNhom = interpolate(f1, [0, 46], [0.94, 1], {...kep, easing: Easing.out(Easing.cubic)});

  // ---------- NHỊP 3 : vệt quét sáng (bắt đầu frame 220) ----------
  const f3 = frame - 220;
  const quet1 = interpolate(f3, [0, 38], [-1300, 2500], kep);
  const quet2 = interpolate(f3, [42, 82], [-1300, 2500], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#1b1f22'}}>
      {/* ===== ẢNH NỀN NHỊP 1 : lòng suối sau lũ ===== */}
      <Interactive.Div
        name="Nền toàn cảnh suối đá sau lũ"
        from={0}
        durationInFrames={125}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={src(props.anhSuoi)} tu={1.02} den={1.14} goc="50% 55%" toi={0.08} />
      </Interactive.Div>

      {/* ===== NHÓM NGƯỜI KIỂM TRA (cắt rời) bước vào lòng suối ===== */}
      <Interactive.Div
        name="Nhóm người kiểm tra ở tiền cảnh"
        from={3}
        durationInFrames={120}
        style={{position: 'absolute', left: 0, top: 500, width: 1920, height: 580, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            transform: `translateX(${xNhom}px) scale(${scaleNhom})`,
            transformOrigin: '0% 100%',
          }}
        >
          <Img
            name="Nhóm người kiểm tra"
            src={src(props.anhNhom)}
            style={{width: props.rongNhom, height: 'auto', display: 'block'}}
          />
        </div>
      </Interactive.Div>

      {/* ===== ẢNH NỀN NHỊP 2 : cận cảnh đập hư hại ===== */}
      <Interactive.Div
        name="Cận cảnh đoạn đập bị hư hại"
        from={123}
        durationInFrames={97}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={src(props.anhDap)} tu={1.16} den={1.01} goc="52% 48%" toi={0.06} />
      </Interactive.Div>

      {/* ===== VÒNG TRÒN ĐỎ VẼ TAY ĐÁNH DẤU ĐIỂM HƯ HẠI ===== */}
      <Interactive.Div
        name="Vòng tròn đỏ đánh dấu điểm hư hại"
        from={123}
        durationInFrames={97}
        style={{position: 'absolute', left: 840, top: 300, width: 560, height: 420, color: props.mauVong}}
      >
        <VongBut w={560} h={420} />
      </Interactive.Div>

      {/* ===== ẢNH NỀN NHỊP 3 : công trường đập dưới nắng hè ===== */}
      <Interactive.Div
        name="Công trường đập dưới nắng mùa hè"
        from={220}
        durationInFrames={95}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={src(props.anhCongTruong)} tu={1.0} den={1.12} goc="50% 46%" toi={0.04} />
      </Interactive.Div>

      {/* ===== HIỆU ỨNG QUÉT SÁNG ===== */}
      <Interactive.Div
        name="Hiệu ứng quét sáng công trường"
        from={220}
        durationInFrames={95}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: -300,
            width: 600,
            height: 1700,
            opacity: props.doMoQuetSang,
            mixBlendMode: 'screen',
            background: `linear-gradient(100deg, rgba(255,255,255,0) 0%, ${props.mauQuetSang} 50%, rgba(255,255,255,0) 100%)`,
            transform: `translateX(${quet1}px) rotate(${props.gocXoayQuet}deg)`,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: -300,
            width: 600,
            height: 1700,
            opacity: props.doMoQuetSang * 0.75,
            mixBlendMode: 'screen',
            background: `linear-gradient(100deg, rgba(255,255,255,0) 0%, ${props.mauQuetSang} 50%, rgba(255,255,255,0) 100%)`,
            transform: `translateX(${quet2}px) rotate(${props.gocXoayQuet}deg)`,
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
