import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhLaoDong: z.string().describe('Ảnh nền công nhân Mỹ làm việc thủ công'),
  anhMuiTen: z.string().describe('Ảnh mũi tên đỏ chỉ chi phí lao động tăng vọt'),
  anhXuong: z.string().describe('Ảnh nền xưởng tái chế công nghiệp'),
  anhMayEp: z.string().describe('Ảnh cận cảnh máy ép thủy lực nén lốp phế thải'),
  anhCongTruong: z.string().describe('Ảnh nền công trường'),
  anhKhoiCaoSu: z.string().describe('Ảnh tách khối cao su nén 1 tấn'),
  anhLapDat: z.string().describe('Ảnh nền công trường lắp đặt'),
  anhCanCau: z.string().describe('Ảnh tách cần cẩu cơ giới'),
  chuTan: z.string().describe('Nhãn trọng lượng khối nén'),
  mauNhan: z.string().describe('Màu nền nhãn trọng lượng'),
  coNhan: z.number().describe('Cỡ chữ nhãn trọng lượng (px)'),
  rongKhoi: z.number().describe('Chiều rộng khối cao su nén (px)'),
  caoKhoi: z.number().describe('Chiều cao khối cao su nén (px)'),
  xKhoi: z.number().describe('Toạ độ X khối nén'),
  yKhoi: z.number().describe('Toạ độ Y khối nén'),
  xNhan: z.number().describe('Toạ độ X nhãn 1 TẤN'),
  yNhan: z.number().describe('Toạ độ Y nhãn 1 TẤN'),
  nangLen: z.number().describe('Độ cao cần cẩu nhấc khối (px)'),
  xCanCau: z.number().describe('Toạ độ X cần cẩu'),
  yCanCau: z.number().describe('Toạ độ Y cần cẩu'),
  rongCanCau: z.number().describe('Chiều rộng cần cẩu (px)'),
  caoCanCau: z.number().describe('Chiều cao cần cẩu (px)'),
  xMuiTen: z.number().describe('Toạ độ X mũi tên đỏ'),
  yMuiTen: z.number().describe('Toạ độ Y mũi tên đỏ'),
  rongMuiTen: z.number().describe('Chiều rộng mũi tên đỏ (px)'),
  caoMuiTen: z.number().describe('Chiều cao mũi tên đỏ (px)'),
});

/* ---------- NHỊP 1 : nền lao động thủ công ---------- */
const NenLaoDong = ({anh}) => {
  return <AnhNen anh={anh} tu={1.02} den={1.15} goc="48% 42%" toi={0.28} />;
};

const MuiTenChiPhi = ({anh, x, y, w, h}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f - 2, fps, config: {damping: 15, mass: 0.9}});
  const yVao = interpolate(vao, [0, 1], [190, 0]);
  const sc = interpolate(f, [0, 130], [0.86, 1.06], kep);
  const op = interpolate(f, [0, 10], [0, 1], kep);
  const xoay = interpolate(f, [0, 130], [-16, -7], kep);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op}}>
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: w,
          height: h,
          objectFit: 'contain',
          transform: `translateY(${yVao}px) scale(${sc}) rotate(${xoay}deg)`,
          transformOrigin: '50% 85%',
          filter: 'drop-shadow(0 18px 34px rgba(0,0,0,0.45))',
        }}
      />
    </div>
  );
};

/* ---------- NHỊP 2 : quét mở xưởng tái chế ---------- */
const XuongTaiChe = ({anh}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 14], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        clipPath: `inset(0% ${(1 - p) * 100}% 0% 0%)`,
      }}
    >
      <AnhNen anh={anh} tu={1.0} den={1.12} goc="50% 50%" toi={0.22} />
      <div
        style={{
          position: 'absolute',
          left: p * 1920 - 7,
          top: 0,
          width: 14,
          height: 1080,
          background: VANG,
          opacity: p > 0.02 && p < 0.98 ? 0.85 : 0,
        }}
      />
    </div>
  );
};

/* ---------- NHỊP 3 : cận cảnh máy ép ---------- */
const MayEpLop = ({anh}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const dam = spring({frame: f, fps, config: {damping: 18, mass: 1.2}});
  const sc = interpolate(dam, [0, 1], [1.22, 1.02]) + f * 0.0009;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${sc})`, transformOrigin: '50% 55%'}}>
        <AnhNen anh={anh} tu={1.0} den={1.06} goc="50% 55%" toi={0.16} />
      </div>
    </div>
  );
};

/* ---------- NHỊP 4 : khối nén 1 tấn ---------- */
const KhoiCaoSu = ({anh, x, y, w, h, nang}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f - 4, fps, config: {damping: 16, mass: 1.3}});
  const yVao = interpolate(vao, [0, 1], [440, 0]);
  const nhac = interpolate(f, [105, 145], [0, -nang], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const op = interpolate(f, [0, 8], [0, 1], kep);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op}}>
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: w,
          height: h,
          objectFit: 'contain',
          transform: `translateY(${yVao + nhac}px)`,
          filter: 'drop-shadow(0 26px 40px rgba(0,0,0,0.5))',
        }}
      />
    </div>
  );
};

const NhanTan = ({chu, mau, co, x, y, nang}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f - 15, fps, config: {damping: 14, mass: 0.8}});
  const op = interpolate(vao, [0, 1], [0, 1]);
  const sc = interpolate(vao, [0, 1], [0.68, 1]);
  const nhac = interpolate(f, [105, 145], [0, -nang], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translateY(${nhac}px)`, opacity: op}}>
      <div
        style={{
          transform: `scale(${sc})`,
          transformOrigin: '0% 50%',
          background: mau,
          color: '#111111',
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: co,
          lineHeight: 1,
          letterSpacing: 3,
          padding: '20px 38px',
          borderRadius: 12,
          boxShadow: '0 14px 30px rgba(0,0,0,0.45)',
          whiteSpace: 'nowrap',
        }}
      >
        {chu}
      </div>
    </div>
  );
};

/* ---------- NHỊP 5 : cần cẩu nhấc khối ---------- */
const CanCau = ({anh, x, y, w, h, nang}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const xuong = spring({frame: f, fps, config: {damping: 17, mass: 1.1}});
  const yXuong = interpolate(xuong, [0, 1], [-430, 0]);
  const nhac = interpolate(f, [17, 57], [0, -nang], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const op = interpolate(f, [0, 4], [0, 1], kep);
  const nghieng = interpolate(f, [0, 14], [4, 0], kep);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op}}>
      <Img
        src={src(anh)}
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: w,
          height: h,
          objectFit: 'contain',
          transform: `translateY(${yXuong + nhac}px) rotate(${nghieng}deg)`,
          transformOrigin: '80% 20%',
          filter: 'drop-shadow(0 22px 36px rgba(0,0,0,0.45))',
        }}
      />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{background: '#101010'}}>
      {/* NHỊP 1 — frame 4 */}
      <Interactive.Div
        name="Nền công nhân Mỹ làm việc thủ công"
        from={0}
        durationInFrames={162}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NenLaoDong anh={props.anhLaoDong} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên đỏ chi phí lao động tăng"
        from={4}
        durationInFrames={141}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <MuiTenChiPhi
          anh={props.anhMuiTen}
          x={props.xMuiTen}
          y={props.yMuiTen}
          w={props.rongMuiTen}
          h={props.caoMuiTen}
        />
      </Interactive.Div>

      {/* NHỊP 2 — frame 145 */}
      <Interactive.Div
        name="Quét mở xưởng tái chế"
        from={145}
        durationInFrames={30}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <XuongTaiChe anh={props.anhXuong} />
      </Interactive.Div>

      {/* NHỊP 3 — frame 170 */}
      <Interactive.Div
        name="Cận cảnh máy ép lốp phế thải"
        from={170}
        durationInFrames={72}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <MayEpLop anh={props.anhMayEp} />
      </Interactive.Div>

      {/* NHỊP 4 — frame 239 */}
      <Interactive.Div
        name="Nền công trường"
        from={239}
        durationInFrames={150}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhCongTruong} tu={1.14} den={1.0} goc="50% 52%" toi={0.18} />
      </Interactive.Div>

      {/* NHỊP 5 — frame 327 */}
      <Interactive.Div
        name="Nền công trường lắp đặt"
        from={327}
        durationInFrames={62}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhLapDat} tu={1.16} den={1.03} goc="50% 45%" toi={0.2} />
      </Interactive.Div>

      <Interactive.Div
        name="Khối cao su nén 1 tấn"
        from={239}
        durationInFrames={150}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiCaoSu
          anh={props.anhKhoiCaoSu}
          x={props.xKhoi}
          y={props.yKhoi}
          w={props.rongKhoi}
          h={props.caoKhoi}
          nang={props.nangLen}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Nhãn trọng lượng 1 TẤN"
        from={239}
        durationInFrames={150}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NhanTan
          chu={props.chuTan}
          mau={props.mauNhan}
          co={props.coNhan}
          x={props.xNhan}
          y={props.yNhan}
          nang={props.nangLen}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Cần cẩu cơ giới nhấc khối"
        from={327}
        durationInFrames={62}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <CanCau
          anh={props.anhCanCau}
          x={props.xCanCau}
          y={props.yCanCau}
          w={props.rongCanCau}
          h={props.caoCanCau}
          nang={props.nangLen}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
