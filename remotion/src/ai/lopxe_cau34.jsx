import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhTrangTrai: z.string().describe('Ảnh trang trại Arizona 1995 (hai người đàn ông nhìn từ phía sau)'),
  anhVucXoiMon: z.string().describe('Ảnh vực rãnh xói mòn khổng lồ'),
  anhNhaHoang: z.string().describe('Ảnh ngôi nhà trang trại bên bờ vực xói mòn'),
  anhDatNut: z.string().describe('Ảnh cận cảnh lớp đất nứt nẻ khô cằn'),
  chuNam: z.string().describe('Chữ đồ họa hiển thị ở góc trái'),
  coNam: z.number().describe('Cỡ chữ của chữ năm (px)'),
  mauNam: z.string().describe('Màu chữ năm'),
  viTriX: z.number().describe('Toạ độ X của chữ năm (px)'),
  viTriY: z.number().describe('Toạ độ Y của chữ năm (px)'),
  mucPhongTo: z.number().describe('Mức punch-in của ảnh đất nứt ở beat cuối'),
  doToiCuoi: z.number().describe('Độ tối phủ lên ảnh cuối (0..0.5)'),
  doDamNen: z.number().describe('Độ tối nhẹ phủ lên ảnh nền'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  /* ---------------- BEAT 1 (frame 4): chữ "1995" + push-in trang trại ---------------- */
  const p1 = interpolate(frame, [4, 28], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const out1 = interpolate(frame, [126, 142], [1, 0], kep);
  const lineW = interpolate(frame, [16, 46], [0, 268], {...kep, easing: Easing.out(Easing.cubic)});
  const textY = (1 - p1) * 46;

  /* ---------------- BEAT 2 (frame 143): whip-pan sang vực xói mòn ---------------- */
  const whipX = interpolate(frame, [143, 152], [1920, 0], {...kep, easing: Easing.out(Easing.cubic)});

  /* ---------------- BEAT 3 (frame 244): fade sang nhà bên bờ vực ---------------- */
  const op3 = interpolate(frame, [244, 262], [0, 1], kep);

  /* ---------------- BEAT 4 (frame 316): punch-in + tối dần trên đất nứt ---------------- */
  const p4 = interpolate(frame, [316, 372], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  const scale4 = 1 + p4 * props.mucPhongTo;
  const op4 = interpolate(frame, [316, 328], [0, 1], kep);
  const toi4 = p4 * props.doToiCuoi;

  return (
    <AbsoluteFill>
      {/* ---------- ẢNH 1 : TRANG TRẠI 1995 (0 → 152) ---------- */}
      <Interactive.Div
        name="Ảnh trang trại 1995"
        from={0}
        durationInFrames={152}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhTrangTrai} tu={1.03} den={1.17} goc="50% 45%" toi={props.doDamNen} />
      </Interactive.Div>

      {/* ---------- ẢNH 2 : VỰC XÓI MÒN (143 → 263) ---------- */}
      <Interactive.Div
        name="Ảnh vực xói mòn"
        from={143}
        durationInFrames={120}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${whipX}px)`,
          }}
        >
          <AnhNen anh={props.anhVucXoiMon} tu={1.16} den={1.03} goc="50% 50%" toi={props.doDamNen} />
        </div>
      </Interactive.Div>

      {/* ---------- ẢNH 3 : NHÀ TRANG TRẠI BÊN BỜ VỰC (244 → 330) ---------- */}
      <Interactive.Div
        name="Ảnh nhà bên bờ vực"
        from={244}
        durationInFrames={86}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: op3,
          }}
        >
          <AnhNen anh={props.anhNhaHoang} tu={1.14} den={1.02} goc="50% 50%" toi={props.doDamNen} />
        </div>
      </Interactive.Div>

      {/* ---------- ẢNH 4 : ĐẤT NỨT NẺ (316 → 372) ---------- */}
      <Interactive.Div
        name="Ảnh đất nứt nẻ"
        from={316}
        durationInFrames={56}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: op4,
            transform: `scale(${scale4})`,
            transformOrigin: '50% 50%',
          }}
        >
          <AnhNen anh={props.anhDatNut} tu={1.0} den={1.05} goc="50% 50%" toi={props.doDamNen} />
        </div>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            backgroundColor: '#0A0806',
            opacity: toi4,
          }}
        />
      </Interactive.Div>

      {/* ---------- CHỮ NĂM 1995 (beat 1) ---------- */}
      <Interactive.Div
        name="Chữ năm 1995"
        from={4}
        durationInFrames={140}
        style={{position: 'absolute', left: props.viTriX, top: props.viTriY}}
      >
        <div style={{opacity: p1 * out1, transform: `translateY(${textY}px)`}}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: props.coNam,
              fontWeight: 800,
              letterSpacing: 8,
              lineHeight: 1,
              color: props.mauNam,
              textShadow: '0 6px 28px rgba(0,0,0,0.55)',
            }}
          >
            {props.chuNam}
          </div>
          <div
            style={{
              marginTop: 20,
              height: 6,
              width: lineW,
              backgroundColor: VANG,
              borderRadius: 3,
              boxShadow: '0 2px 14px rgba(0,0,0,0.45)',
            }}
          />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
