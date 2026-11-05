import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {kep, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anh_dat: z.string().describe('Ảnh mặt đất nứt nẻ dưới nắng hè gay gắt'),
  anh_long_dat: z.string().describe('Ảnh lớp cắt ngang lòng đất ẩm với mạch nước ngầm'),
  anh_nuoi_duong: z.string().describe('Ảnh macro rễ cây hút nước và côn trùng'),
  zoom_dat_tu: z.number().describe('Độ phóng to bắt đầu của mặt đất nứt nẻ'),
  zoom_dat_den: z.number().describe('Độ phóng to kết thúc của mặt đất nứt nẻ'),
  zoom_long_dat_tu: z.number().describe('Độ phóng to bắt đầu của lòng đất ẩm'),
  zoom_long_dat_den: z.number().describe('Độ phóng to kết thúc của lòng đất ẩm'),
  zoom_macro_tu: z.number().describe('Độ phóng to bắt đầu của khung macro rễ cây'),
  zoom_macro_den: z.number().describe('Độ phóng to kết thúc của khung macro rễ cây'),
  dai_wipe_dat: z.number().describe('Số frame hiệu ứng wipe lộ lớp đất ẩm'),
  dai_wipe_macro: z.number().describe('Số frame hiệu ứng wipe lộ khung macro'),
  mau_vach: z.string().describe('Màu vạch sáng ở mép wipe'),
  do_toi_dat: z.number().describe('Độ tối của ảnh mặt đất nứt nẻ'),
  do_toi_long_dat: z.number().describe('Độ tối của ảnh lòng đất ẩm'),
});

const WipeXuong = ({batDau, dai, mau, children}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + dai], [0, 100], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const vach = interpolate(f, [batDau, batDau + dai, batDau + dai + 14], [0, 1, 0], kep);
  return (
    <>
      <AbsoluteFill style={{clipPath: `inset(0% 0% ${100 - p}% 0%)`}}>{children}</AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: `${p}%`,
          width: 1920,
          height: 6,
          marginTop: -3,
          background: mau,
          opacity: vach,
        }}
      />
    </>
  );
};

const WipeNgang = ({batDau, dai, mau, children}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + dai], [0, 100], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const vach = interpolate(f, [batDau, batDau + dai, batDau + dai + 14], [0, 1, 0], kep);
  return (
    <>
      <AbsoluteFill style={{clipPath: `inset(0% ${100 - p}% 0% 0%)`}}>{children}</AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: `${p}%`,
          height: 1080,
          width: 6,
          marginLeft: -3,
          background: mau,
          opacity: vach,
        }}
      />
    </>
  );
};

/* ---------- Lớp trước (foreground) ---------- */

const BadgeNangNong = () => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [6, 26], [0, 1], kep);
  const ra = interpolate(f, [106, 128], [1, 0], kep);
  const op = Math.min(vao, ra);
  const xoay = f * 0.6;
  const pulse = 0.9 + 0.1 * Math.sin(f / 7);
  return (
    <div
      style={{
        position: 'absolute',
        left: 80,
        top: 70,
        opacity: op,
        transform: `translateY(${(1 - vao) * -24}px)`,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        background: 'rgba(30,17,8,0.78)',
        border: '2px solid rgba(255,170,70,0.85)',
        borderRadius: 20,
        padding: '16px 26px 16px 18px',
        boxShadow: '0 16px 50px rgba(0,0,0,0.5)',
      }}
    >
      <div style={{position: 'relative', width: 58, height: 58}}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            background: 'conic-gradient(from 0deg, #ffb347, #ff7a1a, #ffb347, #ff7a1a, #ffb347)',
            transform: `rotate(${xoay}deg)`,
            filter: 'blur(1px)',
            opacity: 0.6,
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 11,
            borderRadius: '50%',
            background: 'radial-gradient(circle at 40% 35%, #ffe6a8, #ff8c2b)',
            boxShadow: `0 0 ${22 + pulse * 8}px #ff8c2b`,
          }}
        />
      </div>
      <div>
        <div style={{fontFamily: 'sans-serif', fontSize: 14, letterSpacing: 4, color: '#ffcf8f'}}>
          MẶT ĐẤT
        </div>
        <div style={{fontFamily: 'sans-serif', fontSize: 40, fontWeight: 800, color: '#fff', lineHeight: 1}}>
          NẮNG GẮT
        </div>
      </div>
    </div>
  );
};

const DoAmDat = () => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [20, 40], [0, 1], kep);
  const ra = interpolate(f, [106, 128], [1, 0], kep);
  const op = Math.min(vao, ra);
  const doAm = interpolate(f, [20, 126], [16, 5], kep);
  return (
    <div
      style={{
        position: 'absolute',
        right: 90,
        bottom: 90,
        width: 380,
        opacity: op,
        transform: `translateY(${(1 - vao) * 30}px)`,
        background: 'rgba(30,17,8,0.8)',
        border: '2px solid rgba(255,200,120,0.65)',
        borderRadius: 18,
        padding: '20px 26px',
        boxShadow: '0 16px 50px rgba(0,0,0,0.5)',
      }}
    >
      <div style={{fontFamily: 'sans-serif', fontSize: 14, letterSpacing: 4, color: '#ffd7a0'}}>
        MẶT ĐẤT
      </div>
      <div style={{fontFamily: 'sans-serif', fontSize: 32, fontWeight: 800, color: '#fff', lineHeight: 1.1}}>
        KHÔ KHỐC
      </div>
      <div
        style={{
          height: 12,
          borderRadius: 6,
          background: 'rgba(255,255,255,0.15)',
          marginTop: 12,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${doAm}%`,
            background: 'linear-gradient(90deg,#ffb347,#ff5a2b)',
            borderRadius: 6,
          }}
        />
      </div>
    </div>
  );
};

const VongKhoanh = ({x, y, r, mau, vao, ra, nhan}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [vao, vao + 16, ra - 16, ra], [0, 1, 1, 0], kep);
  const pulse = 1 + 0.05 * Math.sin(f / 7);
  return (
    <div style={{position: 'absolute', left: x, top: y, opacity: op}}>
      <div
        style={{
          position: 'absolute',
          left: -r,
          top: -r,
          width: 2 * r,
          height: 2 * r,
          borderRadius: '50%',
          border: `4px dashed ${mau}`,
          transform: `scale(${pulse})`,
          boxShadow: `0 0 30px ${mau}`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: -8,
          top: -8,
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: mau,
          boxShadow: `0 0 18px ${mau}`,
        }}
      />
      {nhan ? (
        <div
          style={{
            position: 'absolute',
            left: r + 22,
            top: -20,
            fontFamily: 'sans-serif',
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: 2,
            color: '#22130a',
            background: mau,
            padding: '10px 18px',
            borderRadius: 10,
            whiteSpace: 'nowrap',
            boxShadow: '0 10px 30px rgba(0,0,0,0.45)',
          }}
        >
          {nhan}
        </div>
      ) : null}
    </div>
  );
};

const ThuocDoSau = () => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [172, 194], [0, 1], kep);
  const marks = [0, 1, 2, 3, 4, 5, 6, 7, 8];
  const H = 460;
  return (
    <div
      style={{
        position: 'absolute',
        right: 80,
        top: 120,
        width: 260,
        opacity: vao,
        transform: `translateX(${(1 - vao) * 40}px)`,
      }}
    >
      <div style={{fontFamily: 'sans-serif', fontSize: 16, letterSpacing: 4, color: '#9fe4ff', marginBottom: 14}}>
        ĐỘ SÂU
      </div>
      <div style={{position: 'relative', height: H, borderLeft: '3px solid rgba(140,220,255,0.75)'}}>
        {marks.map((m, i) => {
          const top = (i / (marks.length - 1)) * H;
          const lon = i % 2 === 0;
          return (
            <div
              key={m}
              style={{position: 'absolute', left: -2, top, display: 'flex', alignItems: 'center', gap: 12}}
            >
              <div style={{width: lon ? 22 : 12, height: 3, background: '#9fe4ff', opacity: lon ? 1 : 0.6}} />
            </div>
          );
        })}
      </div>
    </div>
  );
};

const ChuThichNuocNgam = () => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [182, 204], [0, 1], kep);
  const pulse = 0.5 + 0.5 * Math.sin(f / 8);
  return (
    <div style={{position: 'absolute', left: 700, top: 800, opacity: vao}}>
      <div
        style={{
          position: 'absolute',
          left: -20,
          top: -20,
          width: 40,
          height: 40,
          borderRadius: '50%',
          background: '#4fc3ff',
          boxShadow: `0 0 ${18 + pulse * 22}px #4fc3ff`,
        }}
      />
      <div style={{position: 'absolute', left: 26, top: -1, width: 220, height: 3, background: '#4fc3ff'}} />
      <div
        style={{
          position: 'absolute',
          left: 244,
          top: -56,
          background: 'rgba(8,40,60,0.88)',
          border: '2px solid #4fc3ff',
          borderRadius: 14,
          padding: '14px 22px',
          boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
          whiteSpace: 'nowrap',
        }}
      >
        <div style={{fontFamily: 'sans-serif', fontSize: 14, letterSpacing: 3, color: '#7fd8ff'}}>
          MẠCH NƯỚC NGẦM
        </div>
        <div style={{fontFamily: 'sans-serif', fontSize: 28, fontWeight: 800, color: '#dff5ff', marginTop: 4}}>
          VẪN LUÔN DUY TRÌ
        </div>
      </div>
    </div>
  );
};

const TheMacro = ({anh}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [218, 244], [0, 1], kep);
  return (
    <div
      style={{
        position: 'absolute',
        right: 80,
        bottom: 70,
        width: 470,
        height: 300,
        opacity: vao,
        transform: `translateY(${(1 - vao) * 40}px) rotate(${(1 - vao) * -3}deg)`,
        borderRadius: 18,
        overflow: 'hidden',
        border: '4px solid rgba(255,230,180,0.95)',
        boxShadow: '0 24px 60px rgba(0,0,0,0.65)',
      }}
    >
      <AnhNen anh={anh} tu={1.1} den={1.5} goc="50% 50%" toi={0} />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          padding: '12px 18px',
          background: 'linear-gradient(0deg, rgba(0,0,0,0.85), rgba(0,0,0,0))',
          fontFamily: 'sans-serif',
          color: '#ffe6b0',
          fontSize: 18,
          letterSpacing: 2,
          fontWeight: 700,
        }}
      >
        CẬN CẢNH: RỄ HÚT NƯỚC
      </div>
    </div>
  );
};

const DemNuoc = () => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [236, 260], [0, 1], kep);
  const song = 0.55 + 0.45 * Math.sin(f / 7);
  return (
    <div
      style={{
        position: 'absolute',
        left: 80,
        bottom: 80,
        opacity: vao,
        transform: `translateY(${(1 - vao) * 30}px)`,
        background: 'rgba(14,44,24,0.85)',
        border: '2px solid rgba(150,230,150,0.85)',
        borderRadius: 18,
        padding: '16px 28px',
        boxShadow: '0 16px 50px rgba(0,0,0,0.5)',
        width: 360,
      }}
    >
      <div style={{fontFamily: 'sans-serif', fontSize: 14, letterSpacing: 4, color: '#a8f0b0'}}>
        NƯỚC RỄ ĐÃ HÚT
      </div>
      <div style={{fontFamily: 'sans-serif', fontSize: 30, fontWeight: 800, color: '#fff', lineHeight: 1.1}}>
        LIÊN TỤC
      </div>
      <div
        style={{
          height: 12,
          borderRadius: 6,
          background: 'rgba(255,255,255,0.15)',
          marginTop: 12,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${40 + song * 55}%`,
            background: 'linear-gradient(90deg,#6ce8a1,#a8f0b0)',
            borderRadius: 6,
          }}
        />
      </div>
    </div>
  );
};

/* ---------- Cảnh ---------- */

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#2a1c11'}}>
      {/* 1. Nền: mặt đất nứt nẻ */}
      <Interactive.Div
        name="Mặt đất nứt nẻ dưới nắng hè"
        from={0}
        durationInFrames={328}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anh_dat}
          tu={props.zoom_dat_tu}
          den={props.zoom_dat_den}
          goc="50% 45%"
          toi={props.do_toi_dat}
        />
      </Interactive.Div>

      {/* Lớp trước 1: nhãn nhiệt độ + vòng khoanh vết nứt + đồng hồ độ ẩm */}
      <Interactive.Div
        name="Chú thích mặt đất nứt nẻ"
        from={0}
        durationInFrames={140}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <BadgeNangNong />
        <VongKhoanh x={1220} y={640} r={150} mau="#ffd27a" vao={36} ra={124} nhan="ĐẤT NỨT NẺ" />
        <DoAmDat />
      </Interactive.Div>

      {/* 2. Wipe lộ lòng đất ẩm + mạch nước ngầm */}
      <Interactive.Div
        name="Lớp cắt ngang lòng đất ẩm và mạch nước ngầm"
        from={130}
        durationInFrames={198}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <WipeXuong batDau={0} dai={props.dai_wipe_dat} mau={props.mau_vach}>
          <AnhNen
            anh={props.anh_long_dat}
            tu={props.zoom_long_dat_tu}
            den={props.zoom_long_dat_den}
            goc="50% 60%"
            toi={props.do_toi_long_dat}
          />
        </WipeXuong>
      </Interactive.Div>

      {/* Lớp trước 2: thước độ sâu + callout mạch nước ngầm có chấm nhấp nháy */}
      <Interactive.Div
        name="Chú thích lòng đất"
        from={130}
        durationInFrames={198}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <ThuocDoSau />
        <ChuThichNuocNgam />
      </Interactive.Div>

      {/* 3. Wipe lộ macro rễ cây + côn trùng */}
      <Interactive.Div
        name="Macro rễ cây hút nước và côn trùng"
        from={193}
        durationInFrames={135}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <WipeNgang batDau={0} dai={props.dai_wipe_macro} mau={props.mau_vach}>
          <AnhNen
            anh={props.anh_nuoi_duong}
            tu={props.zoom_macro_tu}
            den={props.zoom_macro_den}
            goc="50% 55%"
            toi={0}
          />
        </WipeNgang>
      </Interactive.Div>

      {/* Lớp trước 3: thẻ ảnh cận cảnh (inset) + vòng khoanh lông rễ + đếm nước */}
      <Interactive.Div
        name="Chú thích macro rễ cây"
        from={193}
        durationInFrames={135}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <VongKhoanh x={720} y={520} r={140} mau="#a8f0b0" vao={232} ra={320} nhan="LÔNG RỄ HÚT NƯỚC" />
        <TheMacro anh={props.anh_nuoi_duong} />
        <DemNuoc />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
