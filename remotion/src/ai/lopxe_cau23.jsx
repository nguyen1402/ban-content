import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền đất nứt nẻ (toàn khung)'),
  anh_the: z.string().describe('Ảnh trong thẻ tư liệu / khung preview tập tiếp theo'),
  chu_nut: z.string().describe('Chữ trên phím đăng ký kênh'),
  mau_nut: z.string().describe('Màu mặt phím đăng ký'),
  mau_chu_nut: z.string().describe('Màu chữ trên phím đăng ký'),
  mau_vien_the: z.string().describe('Màu viền mỏng của thẻ tư liệu'),
  mau_nhan: z.string().describe('Màu thanh tiến trình trong khung preview'),
  mau_chuong: z.string().describe('Màu nét vẽ chuông báo'),
  mau_nen_chuong: z.string().describe('Màu nền badge chuông báo'),
  zoom_nen_tu: z.number().describe('Tỷ lệ zoom của nền lúc bắt đầu (zoom-out)'),
  zoom_nen_den: z.number().describe('Tỷ lệ zoom của nền lúc kết thúc'),
  toi_nen: z.number().describe('Độ tối lớp phủ trên ảnh nền'),
  do_toi_beat3: z.number().describe('Độ tối nền khi vào beat preview'),
  rong_the_dau: z.number().describe('Chiều rộng thẻ tư liệu ở beat 1 (px)'),
  rong_the_giua: z.number().describe('Chiều rộng thẻ khi vào giữa khung (px)'),
  rong_preview: z.number().describe('Chiều rộng khung preview cuối (px)')
});

/* ---------- lớp làm tối nền khi vào beat 3 ---------- */
const LopToi = ({doToi}) => {
  const p = useCurrentFrame();
  const o = interpolate(p, [0, 28], [0, doToi], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0.02) 0%, rgba(0,0,0,0.80) 100%)',
        opacity: o
      }}
    />
  );
};

/* ---------- thẻ tư liệu: trái -> giữa -> khung preview ---------- */
const TheTuLieu = ({anh, vien, mauNhan, rongDau, rongGiua, rongPreview}) => {
  const p = useCurrentFrame();
  const {fps} = useVideoConfig();

  const mv = spring({frame: p - 75, fps, config: {damping: 200, mass: 0.9}, durationInFrames: 34});
  const ex = spring({frame: p - 120, fps, config: {damping: 200, mass: 1.0}, durationInFrames: 40});

  const cx = interpolate(mv, [0, 1], [470, 960]);

  const cyBase = interpolate(mv, [0, 1], [470, 480]);
  const wBase = interpolate(mv, [0, 1], [rongDau, rongGiua]);
  const hBase = wBase * 0.632;
  const rot = interpolate(mv, [0, 1], [-2.2, 0]);

  const cy = interpolate(ex, [0, 1], [cyBase, 490]);
  const w = interpolate(ex, [0, 1], [wBase, rongPreview]);
  const h = interpolate(ex, [0, 1], [hBase, rongPreview * 0.562]);
  const radius = interpolate(ex, [0, 1], [12, 18]);

  const float = Math.sin(p / 30) * 6;
  const innerScale = interpolate(p, [0, 262], [1.16, 1.0], kep);
  const prog = interpolate(p, [122, 262], [0.02, 0.92], kep);
  const progOp = interpolate(ex, [0, 0.25], [0, 1], kep);

  const sweepX = interpolate(p, [72, 106], [-0.5, 1.5], kep);
  const sweepOp = interpolate(p, [72, 80, 100, 108], [0, 0.5, 0.5, 0], kep);

  return (
    <div
      style={{
        position: 'absolute',
        left: cx - w / 2,
        top: cy + float - h / 2,
        width: w,
        height: h,
        borderRadius: radius,
        overflow: 'hidden',
        border: `2px solid ${vien}`,
        background: '#0b0b0e',
        boxShadow: '0 40px 90px rgba(0,0,0,0.6)',
        transform: `rotate(${rot}deg)`
      }}
    >
      <Img
        name="Ảnh thẻ tư liệu"
        src={src(anh)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${innerScale})`}}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0.02) 45%, rgba(0,0,0,0.55) 100%)'
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: -h * 0.5,
          left: 0,
          width: w * 0.45,
          height: h * 2,
          background:
            'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.34) 50%, rgba(255,255,255,0) 100%)',
          transform: `translateX(${sweepX * w}px) rotate(10deg)`,
          opacity: sweepOp
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          bottom: 0,
          width: '100%',
          height: 8,
          background: 'rgba(255,255,255,0.18)',
          opacity: progOp
        }}
      >
        <div style={{width: `${prog * 100}%`, height: '100%', background: mauNhan}} />
      </div>
    </div>
  );
};

/* ---------- phím đăng ký kênh dạng vật lý ---------- */
const NutDangKy = ({chu, mau, mauChu}) => {
  const p = useCurrentFrame();
  const {fps} = useVideoConfig();

  const vao = spring({frame: p, fps, config: {damping: 13, mass: 0.7}, durationInFrames: 22});
  const nhan = interpolate(p, [12, 16, 23], [0, 1, 0], kep);
  const bat = interpolate(p, [16, 30], [0, 1], kep);
  const hien = interpolate(p, [0, 6], [0, 1], kep);
  const mo = interpolate(p, [58, 70], [1, 0], kep);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 470,
        height: 180,
        transform: `scale(${vao})`,
        transformOrigin: '50% 62%',
        opacity: hien * mo
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 12,
          top: 36,
          width: 446,
          height: 124,
          borderRadius: 20,
          background: '#141419',
          boxShadow: '0 22px 45px rgba(0,0,0,0.55)'
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 12,
          top: 18 + 16 * nhan,
          width: 446,
          height: 124,
          borderRadius: 20,
          background: mau,
          border: '2px solid rgba(255,255,255,0.28)',
          boxShadow: `0 0 ${bat * 34}px rgba(255,200,60,${0.55 * bat}), inset 0 2px 0 rgba(255,255,255,0.42)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 46,
            fontWeight: 800,
            letterSpacing: 6,
            color: mauChu
          }}
        >
          {chu}
        </div>
      </div>
    </div>
  );
};

/* ---------- con trỏ thanh lịch ---------- */
const ConTro = () => {
  const p = useCurrentFrame();
  const {fps} = useVideoConfig();

  const toi = spring({frame: p, fps, config: {damping: 200, mass: 1}, durationInFrames: 20});
  const x = interpolate(toi, [0, 1], [1520, 968]);
  const y = interpolate(toi, [0, 1], [940, 760]);
  const bam = interpolate(p, [18, 21, 27], [1, 0.85, 1], kep);
  const mo = interpolate(p, [0, 5, 66, 76], [0, 1, 1, 0], kep);

  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          transform: `translate(${x}px, ${y}px) scale(${bam})`,
          transformOrigin: '0 0',
          opacity: mo
        }}
      >
        <svg width={56} height={74} viewBox="0 0 28 37" style={{filter: 'drop-shadow(0 8px 12px rgba(0,0,0,0.5))'}}>
          <path
            d="M2 1 L2 27.5 L9.2 20.8 L14.4 32.4 L20 29.8 L14.9 18.2 L23.4 18.2 Z"
            fill="#FFFFFF"
            stroke="#141418"
            strokeWidth={1.8}
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
};

/* ---------- chuông báo bật lên sau khi nhấn ---------- */
const ChuongBao = ({mau, mauNen}) => {
  const p = useCurrentFrame();
  const {fps} = useVideoConfig();

  const vao = spring({frame: p, fps, config: {damping: 11, mass: 0.6}, durationInFrames: 22});
  const lac = Math.sin(p * 0.95) * 14 * Math.exp(-p / 18);
  const mo = interpolate(p, [0, 5, 40, 52], [0, 1, 1, 0], kep);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 152,
        height: 152,
        transform: `scale(${vao}) rotate(${lac}deg)`,
        transformOrigin: '50% 50%',
        opacity: mo
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: mauNen,
          border: `2px solid ${mau}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 18px 40px rgba(0,0,0,0.5)'
        }}
      >
        <svg
          width={82}
          height={82}
          viewBox="0 0 24 24"
          fill="none"
          stroke={mau}
          strokeWidth={1.6}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6.2 16.4V11a5.8 5.8 0 0 1 11.6 0v5.4l1.4 2.2H4.8l1.4-2.2Z" />
          <path d="M10 20.2a2.2 2.2 0 0 0 4 0" />
        </svg>
      </div>
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0c'}}>
      {/* NỀN: đất nứt nẻ trôi chậm về chiều sâu suốt shot */}
      <Interactive.Div
        name="Nền đất nứt nẻ"
        from={0}
        durationInFrames={266}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anh_nen}
          tu={props.zoom_nen_tu}
          den={props.zoom_nen_den}
          goc="50% 45%"
          toi={props.toi_nen}
        />
      </Interactive.Div>

      {/* Lớp làm tối nền khi bước sang beat preview */}
      <Interactive.Div
        name="Làm tối nền"
        from={123}
        durationInFrames={143}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopToi doToi={props.do_toi_beat3} />
      </Interactive.Div>

      {/* THẺ TƯ LIỆU -> KHUNG PREVIEW */}
      <Interactive.Div
        name="Thẻ tư liệu và khung preview"
        from={3}
        durationInFrames={263}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <TheTuLieu
          anh={props.anh_the}
          vien={props.mau_vien_the}
          mauNhan={props.mau_nhan}
          rongDau={props.rong_the_dau}
          rongGiua={props.rong_the_giua}
          rongPreview={props.rong_preview}
        />
      </Interactive.Div>

      {/* PHÍM ĐĂNG KÝ */}
      <Interactive.Div
        name="Phím đăng ký kênh"
        from={84}
        durationInFrames={70}
        style={{position: 'absolute', left: 725, top: 680}}
      >
        <NutDangKy chu={props.chu_nut} mau={props.mau_nut} mauChu={props.mau_chu_nut} />
      </Interactive.Div>

      {/* CHUÔNG BÁO */}
      <Interactive.Div
        name="Chuông báo kích hoạt"
        from={102}
        durationInFrames={52}
        style={{position: 'absolute', left: 1122, top: 588}}
      >
        <ChuongBao mau={props.mau_chuong} mauNen={props.mau_nen_chuong} />
      </Interactive.Div>

      {/* CON TRỎ */}
      <Interactive.Div
        name="Con trỏ nhấn phím"
        from={78}
        durationInFrames={80}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <ConTro />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
