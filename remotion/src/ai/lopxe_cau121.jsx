import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src} from './thu_vien.jsx';

export const schema = z.object({
  anhBinhLuan: z.string().describe('Ảnh thẻ bình luận'),
  anhNutDangKy: z.string().describe('Ảnh nút đăng ký kênh'),
  anhHaoQuang: z.string().describe('Ảnh hào quang tỏa sáng'),
  anhTheVideo: z.string().describe('Ảnh thẻ gợi ý video'),
  mauNenTren: z.string().describe('Màu nền studio phía trên'),
  mauNenDuoi: z.string().describe('Màu nền studio phía dưới'),
  rongTheBinhLuan: z.number().describe('Chiều rộng thẻ bình luận (px)'),
  rongNutDangKy: z.number().describe('Chiều rộng nút đăng ký (px)'),
  rongHaoQuang: z.number().describe('Chiều rộng hào quang (px)'),
  rongTheVideo: z.number().describe('Chiều rộng thẻ gợi ý video (px)'),
  doToi: z.number().describe('Độ đậm lớp tối viền nền (0..0.5)'),
});

const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

/* ---------------- biểu tượng tương tác (glyph UI vẽ bằng SVG) ---------------- */
const BieuTuong = ({loai}) => {
  const paths = {
    tim: 'M12 21.2C9.1 19 3 14.4 3 9.6 3 6.5 5.3 4.3 8.1 4.3c1.6 0 3 .8 3.9 2 .9-1.2 2.3-2 3.9-2 2.8 0 5.1 2.2 5.1 5.3 0 4.8-6.1 9.4-9 11.6z',
    thich: 'M8.5 21.5V9.8l4.2-7.1c.2-.3.5-.5.9-.5h.5c1 0 1.8.9 1.6 1.9l-.8 4.4h4.6c1.3 0 2.3 1.2 2 2.5l-1.5 8.2c-.2 1.1-1.2 1.8-2.3 1.8H8.5zM3 9.8h3.5v11.7H3z',
    chat: 'M4 3.5h16c1.1 0 2 .9 2 2v9.5c0 1.1-.9 2-2 2H9.8L4 21.5v-4.5c-1.1 0-2-.9-2-2V5.5c0-1.1.9-2 2-2z',
    sao: 'M12 2.2l3 6.3 6.9 1-5 4.9 1.2 6.9L12 18l-6.1 3.3L7.1 14.4l-5-4.9 6.9-1z',
    chia: 'M14 2.5l7.5 7.5-7.5 7.5v-4.7c-6.2.2-9.7 2.3-11.5 6.2-.6-6.9 3.6-11.6 11.5-12V2.5z',
  };
  return (
    <svg width={74} height={74} viewBox="0 0 24 24">
      <path d={paths[loai]} fill="#ffffff" />
    </svg>
  );
};

/* ---------------- thẻ bình luận nổi ---------------- */
const TheBinhLuan = ({f, anh, rong}) => {
  const {fps} = useVideoConfig();
  const cao = (rong * 265) / 700;
  const vao = spring({frame: f, fps, config: {damping: 14, mass: 0.85, stiffness: 110}});
  const tx = interpolate(vao, [0, 1], [-1150, 0]);
  const sc = interpolate(vao, [0, 1], [0.82, 1]);
  const op = interpolate(f, [0, 9], [0, 1], cl);
  const ra = interpolate(f, [118, 140], [0, 1], {...cl, easing: Easing.in(Easing.cubic)});
  const floatY = Math.sin(f / 24) * 9;
  const rot = Math.sin(f / 34) * 1.0;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translate(${tx - ra * 520}px, ${floatY}px) scale(${sc * (1 - ra * 0.25)}) rotate(${rot}deg)`,
        opacity: op * (1 - ra),
      }}
    >
      <Img
        src={src(anh)}
        style={{width: rong, height: cao, display: 'block', filter: 'drop-shadow(0 26px 44px rgba(0,0,0,0.55))'}}
      />
    </div>
  );
};

/* ---------------- một biểu tượng tương tác bay ra ---------------- */
const BieuTuongNoi = ({f, i, loai, mau, cx, cy}) => {
  const {fps} = useVideoConfig();
  const fr = f - i * 3;
  const s = spring({frame: fr, fps, config: {damping: 11, mass: 0.7, stiffness: 130}});
  const dx = (960 - cx) * (1 - s);
  const dy = (570 - cy) * (1 - s);
  const sc = 0.25 + 0.75 * s;
  const bob = Math.sin((f + i * 13) / 17) * 10;
  const rot = Math.sin((f + i * 9) / 21) * 9;
  const op = interpolate(fr, [0, 6], [0, 1], cl);
  return (
    <div
      style={{
        width: 140,
        height: 140,
        borderRadius: '50%',
        background: `linear-gradient(150deg, ${mau} 0%, ${mau}aa 100%)`,
        border: '5px solid rgba(255,255,255,0.92)',
        boxShadow: '0 18px 38px rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: `translate(${dx}px, ${dy + bob}px) scale(${sc}) rotate(${rot}deg)`,
        opacity: op,
      }}
    >
      <BieuTuong loai={loai} />
    </div>
  );
};

/* ---------------- hào quang lan tỏa ---------------- */
const HaoQuang = ({f, anh, rong}) => {
  const cao = (rong * 437) / 700;
  const op = interpolate(f, [0, 14], [0, 0.95], cl);
  const sc = interpolate(f, [0, 40], [0.6, 1.06], {...cl, easing: Easing.out(Easing.cubic)});
  const rot = f * 0.35;
  const shift = interpolate(f, [76, 104], [0, -320], {...cl, easing: Easing.inOut(Easing.cubic)});
  const fadeIn = interpolate(f, [0, 20], [0, 1], cl);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translateX(${shift}px) scale(${sc})`,
        opacity: op,
      }}
    >
      <svg width={rong} height={cao} viewBox={`0 0 ${rong} ${cao}`} style={{position: 'absolute', left: 0, top: 0}}>
        {[0, 1, 2].map((i) => {
          const ph = ((f * 0.9 + i * 33) % 100) / 100;
          const r = 240 + ph * 380;
          return (
            <circle
              key={i}
              cx={rong / 2}
              cy={cao / 2}
              r={r}
              fill="none"
              stroke="#ff5555"
              strokeWidth={7}
              opacity={(1 - ph) * 0.55 * fadeIn}
            />
          );
        })}
      </svg>
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: rong,
          height: cao,
          display: 'block',
          transform: `rotate(${rot}deg)`,
          transformOrigin: '50% 50%',
        }}
      />
    </div>
  );
};

/* ---------------- nút đăng ký ---------------- */
const NutDangKy = ({f, anh, rong}) => {
  const {fps} = useVideoConfig();
  const cao = (rong * 214) / 700;
  const vao = spring({frame: f, fps, config: {damping: 12, mass: 0.75, stiffness: 120}});
  const sIn = interpolate(vao, [0, 1], [0.35, 1]);
  const op = interpolate(f, [0, 7], [0, 1], cl);
  const pulse = interpolate(f, [44, 56, 74, 92], [1, 1.13, 1.0, 1.04], {...cl, easing: Easing.inOut(Easing.quad)});
  const breathe = 1 + Math.sin(f / 26) * 0.012;
  const shift = interpolate(f, [124, 152], [0, -320], {...cl, easing: Easing.inOut(Easing.cubic)});
  const rot = Math.sin(f / 30) * 1.2;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translateX(${shift}px) scale(${sIn * pulse * breathe}) rotate(${rot}deg)`,
        transformOrigin: '50% 50%',
        opacity: op,
      }}
    >
      <Img
        src={src(anh)}
        style={{width: rong, height: cao, display: 'block', filter: 'drop-shadow(0 26px 44px rgba(0,0,0,0.55))'}}
      />
    </div>
  );
};

/* ---------------- thẻ gợi ý video ---------------- */
const TheVideo = ({f, anh, rong}) => {
  const {fps} = useVideoConfig();
  const cao = (rong * 393) / 438;
  const vao = spring({frame: f, fps, config: {damping: 13, mass: 0.8, stiffness: 110}});
  const tx = interpolate(vao, [0, 1], [540, 0]);
  const sc = interpolate(vao, [0, 1], [0.75, 1]);
  const op = interpolate(f, [0, 8], [0, 1], cl);
  const floatY = Math.sin(f / 20) * 10;
  const rot = Math.sin(f / 26) * 2;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translate(${tx}px, ${floatY}px) scale(${sc}) rotate(${rot}deg)`,
        opacity: op,
      }}
    >
      <Img
        src={src(anh)}
        style={{width: rong, height: cao, display: 'block', filter: 'drop-shadow(0 26px 44px rgba(0,0,0,0.55))'}}
      />
    </div>
  );
};

/* ---------------- cảnh ---------------- */
const BLOB = [
  {x: 180, y: 120, w: 820, h: 820, c: 'rgba(122,92,255,0.38)'},
  {x: 1280, y: 40, w: 660, h: 660, c: 'rgba(78,196,255,0.26)'},
  {x: 1460, y: 620, w: 760, h: 760, c: 'rgba(255,118,178,0.22)'},
  {x: 60, y: 640, w: 700, h: 700, c: 'rgba(255,190,96,0.17)'},
  {x: 760, y: 420, w: 560, h: 560, c: 'rgba(120,255,220,0.12)'},
];

const DS_BIEU_TUONG = [
  {ten: 'Biểu tượng tim', loai: 'tim', mau: '#ff4d6d', left: 230, top: 170},
  {ten: 'Biểu tượng thích', loai: 'thich', mau: '#3b82f6', left: 1550, top: 170},
  {ten: 'Biểu tượng bình luận', loai: 'chat', mau: '#22c55e', left: 200, top: 700},
  {ten: 'Biểu tượng sao', loai: 'sao', mau: '#f59e0b', left: 1570, top: 710},
  {ten: 'Biểu tượng chia sẻ', loai: 'chia', mau: '#a855f7', left: 890, top: 130},
];

export const Canh = ({
  anhBinhLuan,
  anhNutDangKy,
  anhHaoQuang,
  anhTheVideo,
  mauNenTren,
  mauNenDuoi,
  rongTheBinhLuan,
  rongNutDangKy,
  rongHaoQuang,
  rongTheVideo,
  doToi,
}) => {
  const frame = useCurrentFrame();

  const caoBinhLuan = (rongTheBinhLuan * 265) / 700;
  const caoNut = (rongNutDangKy * 214) / 700;
  const caoHaoQuang = (rongHaoQuang * 437) / 700;
  const caoVideo = (rongTheVideo * 393) / 438;

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0918'}}>
      {/* ---------- nền studio mờ ảo ---------- */}
      <Interactive.Div
        name="Nền studio mờ ảo"
        from={0}
        durationInFrames={334}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            overflow: 'hidden',
            background: `linear-gradient(155deg, ${mauNenTren} 0%, ${mauNenDuoi} 62%, #07060f 100%)`,
          }}
        >
          <div style={{position: 'absolute', inset: -140, transform: `scale(${1.03 + frame * 0.00025})`}}>
            {BLOB.map((b, i) => (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  left: b.x + Math.sin(frame / 70 + i) * 42,
                  top: b.y + Math.cos(frame / 90 + i) * 34,
                  width: b.w,
                  height: b.h,
                  borderRadius: '50%',
                  background: `radial-gradient(circle, ${b.c} 0%, rgba(0,0,0,0) 68%)`,
                }}
              />
            ))}
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 720,
                width: 1920,
                height: 360,
                background: 'linear-gradient(180deg, rgba(120,150,235,0.16) 0%, rgba(0,0,0,0) 100%)',
              }}
            />
          </div>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 32%, rgba(0,0,0,${doToi}) 100%)`,
            }}
          />
        </div>
      </Interactive.Div>

      {/* ---------- thẻ bình luận nổi (beat 2) ---------- */}
      <Interactive.Div
        name="Thẻ bình luận nổi"
        from={2}
        durationInFrames={140}
        style={{position: 'absolute', left: 460, top: 380, width: rongTheBinhLuan, height: caoBinhLuan}}
      >
        <TheBinhLuan f={frame - 2} anh={anhBinhLuan} rong={rongTheBinhLuan} />
      </Interactive.Div>

      {/* ---------- các biểu tượng tương tác (beat 86) ---------- */}
      {DS_BIEU_TUONG.map((b, i) => (
        <Interactive.Div
          key={b.ten}
          name={b.ten}
          from={86}
          durationInFrames={248}
          style={{position: 'absolute', left: b.left, top: b.top, width: 140, height: 140}}
        >
          <BieuTuongNoi f={frame - 86} i={i} loai={b.loai} mau={b.mau} cx={b.left + 70} cy={b.top + 70} />
        </Interactive.Div>
      ))}

      {/* ---------- hào quang (beat 180) ---------- */}
      <Interactive.Div
        name="Hào quang lan tỏa"
        from={180}
        durationInFrames={154}
        style={{position: 'absolute', left: 340, top: 150, width: rongHaoQuang, height: caoHaoQuang}}
      >
        <HaoQuang f={frame - 180} anh={anhHaoQuang} rong={rongHaoQuang} />
      </Interactive.Div>

      {/* ---------- nút đăng ký (beat 132) ---------- */}
      <Interactive.Div
        name="Nút đăng ký kênh"
        from={132}
        durationInFrames={202}
        style={{position: 'absolute', left: 510, top: 400, width: rongNutDangKy, height: caoNut}}
      >
        <NutDangKy f={frame - 132} anh={anhNutDangKy} rong={rongNutDangKy} />
      </Interactive.Div>

      {/* ---------- thẻ gợi ý video (beat 256) ---------- */}
      <Interactive.Div
        name="Thẻ gợi ý video"
        from={256}
        durationInFrames={78}
        style={{position: 'absolute', left: 1180, top: 300, width: rongTheVideo, height: caoVideo}}
      >
        <TheVideo f={frame - 256} anh={anhTheVideo} rong={rongTheVideo} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
