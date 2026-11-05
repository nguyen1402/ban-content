import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, AnhNen, AnhLia} from './thu_vien.jsx';

export const schema = z.object({
  anhNuoc: z.string().describe('Ảnh nền dòng nước chảy qua đá'),
  anhRe: z.string().describe('Ảnh nền rễ cây bám chặt vách đá'),
  anhNhanh: z.string().describe('Ảnh cut-out nhánh cây non'),
  panNuoc: z.number().describe('Quãng pan ngang của ảnh nước (px)'),
  phongNuoc: z.number().describe('Tỉ lệ phóng của ảnh nước'),
  toiNuoc: z.number().describe('Độ tối lớp phủ ảnh nước (0-0.5)'),
  driftNgang: z.number().describe('Camera drift ngang khi tới nhịp điệu tự nhiên (px)'),
  driftDoc: z.number().describe('Camera drift dọc khi tới nhịp điệu tự nhiên (px)'),
  zoomReTu: z.number().describe('Tỉ lệ phóng ban đầu của ảnh rễ cây'),
  zoomReDen: z.number().describe('Tỉ lệ phóng cuối của ảnh rễ cây'),
  toiRe: z.number().describe('Độ tối lớp phủ ảnh rễ cây (0-0.5)'),
  punch: z.number().describe('Mức punch-in khi tới từ khóa vững bền bỉ'),
  sweepMau: z.string().describe('Màu vệt sáng lướt qua'),
  sweepRong: z.number().describe('Bề rộng vệt sáng (% khung hình)'),
  sweepDay: z.number().describe('Số khung hình vệt sáng lướt qua'),
  nhanhLech: z.number().describe('Quãng trượt vào của nhánh cây non (px)'),
  nhanhNghieng: z.number().describe('Biên độ nghiêng qua lại của nhánh cây (độ)'),
  nhanhNhup: z.number().describe('Biên độ nhấp nhô của nhánh cây (px)'),
  nhanhMo: z.number().describe('Độ mờ của nhánh cây non'),
});

/* ---------------- vệt sáng lướt ---------------- */
const LuotSang = ({batDau, day, mau, rong}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + day], [0, 1], {...kep, easing: Easing.inOut(Easing.ease)});
  const x = interpolate(p, [0, 1], [-70, 170], kep);
  const op = interpolate(p, [0, 0.18, 0.82, 1], [0, 0.6, 0.6, 0], kep);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          top: '-30%',
          bottom: '-30%',
          left: `${x}%`,
          width: `${rong}%`,
          background: `linear-gradient(100deg, rgba(255,255,255,0) 0%, ${mau} 50%, rgba(255,255,255,0) 100%)`,
          transform: 'rotate(10deg)',
          opacity: op,
          mixBlendMode: 'screen',
        }}
      />
    </div>
  );
};

/* ---------------- ảnh nền dòng nước (0 - 140) ---------------- */
const KhoiNuoc = ({p}) => {
  const f = useCurrentFrame();
  // beat 91 «nhịp điệu tự nhiên»: camera drift nhẹ theo chiều uốn lượn
  const dx = interpolate(f, [91, 140], [0, p.driftNgang], {...kep, easing: Easing.inOut(Easing.ease)});
  const dy = interpolate(f, [91, 140], [0, p.driftDoc], {...kep, easing: Easing.inOut(Easing.ease)});
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `translate(${dx}px, ${dy}px) scale(1.04)`}}>
        <AnhLia anh={p.anhNuoc} huong="phai" quang={p.panNuoc} phong={p.phongNuoc} toi={p.toiNuoc} />
      </div>
      {/* beat 65 «và việc biết nương theo»: ánh sáng lan tỏa trên mặt nước */}
      <LuotSang batDau={65} day={p.sweepDay} mau={p.sweepMau} rong={p.sweepRong} />
    </AbsoluteFill>
  );
};

/* ---------------- ảnh nền rễ cây (122 - 204) ---------------- */
const KhoiRe = ({p}) => {
  const f = useCurrentFrame();
  // beat 125 «lại giúp chúng ta»: slide chuyển cảnh nhẹ nhàng (local 1 -> 13)
  const tx = interpolate(f, [1, 13], [1920, 0], {...kep, easing: Easing.out(Easing.cubic)});
  // beat 147 «đứng vững bền bỉ hơn»: punch-in 10% (local 25 -> 33)
  const punch = interpolate(f, [25, 33], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const scale = 1 + p.punch * punch;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translateX(${tx}px) scale(${scale})`,
          transformOrigin: '50% 50%',
        }}
      >
        <AnhNen anh={p.anhRe} tu={p.zoomReTu} den={p.zoomReDen} goc="50% 55%" toi={p.toiRe} />
      </div>
      {/* beat 147: light sweep trên rễ cây */}
      <LuotSang batDau={25} day={p.sweepDay} mau={p.sweepMau} rong={p.sweepRong} />
    </AbsoluteFill>
  );
};

/* ---------------- nhánh cây non tiền cảnh (30 - 204) ---------------- */
const KhoiNhanh = ({p}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  // beat 34 «chính sự mềm dẻo»: trượt từ bên trái vào (local 4 -> ~28)
  const vao = spring({frame: Math.max(0, f - 4), fps, config: {damping: 17, stiffness: 72, mass: 1}});
  const tx = interpolate(vao, [0, 1], [-p.nhanhLech, 0]);
  const op = interpolate(f, [4, 20], [0, p.nhanhMo], kep);
  // uốn theo dòng nước
  const nghieng = Math.sin(f / 26) * p.nhanhNghieng;
  const nhup = Math.sin(f / 21 + 1) * p.nhanhNhup;
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
      <Img
        name="Nhánh cây non uốn theo dòng nước"
        from={0}
        durationInFrames={174}
        src={src(p.anhNhanh)}
        style={{
          position: 'absolute',
          left: 100,
          top: 560,
          width: 1250,
          height: 473,
          objectFit: 'contain',
          transform: `translate(${tx}px, ${nhup}px) rotate(${nghieng}deg)`,
          transformOrigin: '12% 88%',
          opacity: op,
          filter: 'drop-shadow(0 16px 26px rgba(0,0,0,0.35))',
        }}
      />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f12'}}>
      <Interactive.Div
        name="Ảnh nền dòng nước chảy qua đá"
        from={0}
        durationInFrames={140}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiNuoc p={props} />
      </Interactive.Div>

      <Interactive.Div
        name="Ảnh nền rễ cây bám vách đá"
        from={122}
        durationInFrames={82}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiRe p={props} />
      </Interactive.Div>

      <Interactive.Div
        name="Nhánh cây non tiền cảnh"
        from={30}
        durationInFrames={174}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiNhanh p={props} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
