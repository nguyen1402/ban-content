import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_lich_su: z.string().describe('Ảnh tư liệu lịch sử thế kỷ trước (tông sepia)'),
  anh_may_moc: z.string().describe('Ảnh máy ủi hạng nặng trên nền đất nứt'),
  anh_vung_dat: z.string().describe('Ảnh toàn cảnh vùng đất khô cằn hiện tại'),
  moc_thoi_gian: z.string().describe('Mốc thời gian tối giản hiển thị trên ảnh tư liệu'),
  so_tien: z.number().describe('Con số tài chính đếm lên (triệu đô la)'),
  don_vi_tien: z.string().describe('Đơn vị tiền tệ của bộ đếm'),
  giay_dem: z.number().describe('Thời gian đếm (giây)'),
  co_moc: z.number().describe('Cỡ chữ mốc thời gian (px)'),
  co_dem: z.number().describe('Cỡ chữ bộ đếm tài chính (px)'),
  mau_chu: z.string().describe('Màu chữ chính'),
});

/* ---------- Lớp mờ dần để chuyển cảnh mượt (không bao giờ để nền trống) ---------- */
const LopHien = ({bat_dau, do_dai, children}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [bat_dau, bat_dau + do_dai], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.quad),
  });
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op}}>
      {children}
    </div>
  );
};

/* ---------- Gạch vàng vẽ ra ---------- */
const Gach = ({mau, rong, tre}) => {
  const f = useCurrentFrame();
  const w = interpolate(f, [tre, tre + 26], [0, rong], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  return <div style={{width: w, height: 7, background: mau, borderRadius: 4}} />;
};

/* ---------- Mốc thời gian tối giản ---------- */
const MocThoiGian = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const pop = spring({frame: f - 4, fps: 30, config: {damping: 200, mass: 0.9}});
  const op = interpolate(f, [2, 16], [0, 1], kep);
  const y = interpolate(pop, [0, 1], [34, 0]);
  return (
    <div style={{position: 'absolute', left: 0, top: 0}}>
      <Gach mau={VANG} rong={260} tre={0} />
      <div
        style={{
          marginTop: 28,
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 800,
          lineHeight: 1,
          letterSpacing: 10,
          color: mau,
          opacity: op,
          transform: `translateY(${y}px)`,
          textShadow: '0 8px 36px rgba(0,0,0,0.7)',
        }}
      >
        {chu}
      </div>
    </div>
  );
};

/* ---------- Bộ đếm tài chính ---------- */
const BoDem = ({so, don_vi, giay, co}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 14, 80, 92], [0, 1, 1, 0], kep);
  const y = interpolate(f, [0, 18], [30, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'absolute', left: 0, top: 0, opacity: op, transform: `translateY(${y}px)`}}>
      <Gach mau={VANG} rong={300} tre={0} />
      <div style={{marginTop: 30}}>
        <SoDem so={so} don_vi={don_vi} giay={giay} co={co} />
      </div>
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0c0a07'}}>
      {/* ============ 1. ẢNH TƯ LIỆU LỊCH SỬ — sepia trôi chậm (frame 0 → 100) ============ */}
      <Interactive.Div
        name="Ảnh tư liệu lịch sử"
        from={0}
        durationInFrames={100}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            filter: 'sepia(0.6) contrast(1.07) saturate(0.85)',
          }}
        >
          <AnhLia anh={props.anh_lich_su} huong="phai" quang={80} phong={1.14} toi={0.08} />
        </div>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 560,
            width: 1920,
            height: 520,
            background: 'linear-gradient(to top, rgba(18,12,5,0.66), rgba(18,12,5,0))',
          }}
        />
      </Interactive.Div>

      {/* ============ 2. MÁY MÓC HẠNG NẶNG + BỘ ĐẾM (frame 89 → 199) ============ */}
      <Interactive.Div
        name="Ảnh máy móc hạng nặng"
        from={89}
        durationInFrames={110}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <LopHien bat_dau={0} do_dai={11}>
          <AnhNen anh={props.anh_may_moc} tu={1} den={1.14} goc="52% 55%" toi={0.22} />
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 540,
              width: 1920,
              height: 540,
              background: 'linear-gradient(to top, rgba(10,8,5,0.7), rgba(10,8,5,0))',
            }}
          />
        </LopHien>
      </Interactive.Div>

      {/* ============ 3. TOÀN CẢNH VÙNG ĐẤT KHÔ CẰN — pull-back (frame 180 → 285) ============ */}
      <Interactive.Div
        name="Toàn cảnh vùng đất khô cằn"
        from={180}
        durationInFrames={105}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <LopHien bat_dau={0} do_dai={14}>
          <AnhNen anh={props.anh_vung_dat} tu={1.16} den={1} goc="50% 50%" toi={0.14} />
        </LopHien>
      </Interactive.Div>

      {/* ============ MỐC THỜI GIAN (frame 4 → 100) ============ */}
      <Interactive.Div
        name="Mốc thời gian"
        from={4}
        durationInFrames={96}
        style={{position: 'absolute', left: 150, top: 700}}
      >
        <MocThoiGian chu={props.moc_thoi_gian} co={props.co_moc} mau={props.mau_chu} />
      </Interactive.Div>

      {/* ============ BỘ ĐẾM TÀI CHÍNH (frame 89 → 190) ============ */}
      <Interactive.Div
        name="Bộ đếm tài chính"
        from={89}
        durationInFrames={101}
        style={{position: 'absolute', left: 150, top: 660}}
      >
        <BoDem
          so={props.so_tien}
          don_vi={props.don_vi_tien}
          giay={props.giay_dem}
          co={props.co_dem}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
