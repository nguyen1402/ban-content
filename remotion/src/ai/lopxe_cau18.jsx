import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNenTrangTrai: z.string().describe('Ảnh nền trang trại xanh ngát'),
  anhNenLuBun: z.string().describe('Ảnh nền dòng lũ bùn đất cuộn trôi'),
  anhCanDuongCat: z.string().describe('Ảnh cận đường đất nông trang bị cát bùn vùi lấp'),
  anhDanBo: z.string().describe('Cut-out đàn bò đang chăn thả'),
  anhTheHe: z.string().describe('Cut-out gia đình nhà King nhìn từ sau lưng'),
  chuKhoa: z.string().describe('Chữ khoá ngắn hiện trên màn hình'),
  coChu: z.number().describe('Cỡ chữ khoá (px)'),
  mauChu: z.string().describe('Màu chữ khoá'),
  doDamNen: z.number().describe('Độ tối lớp phủ nền trang trại (0..0.5)'),
  doDamLu: z.number().describe('Độ tối lớp phủ nền lũ bùn (0..0.5)'),
  punchNen: z.number().describe('Tỉ lệ punch-in vào bãi cỏ ở nhịp chăn thả'),
  punchDuong: z.number().describe('Tỉ lệ punch-in nhanh vào con đường cát'),
});

const LopNenTrangTrai = ({anh, punch, toi}) => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, 82, 120], [1, 1, punch], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        transform: `scale(${zoom})`,
        transformOrigin: '52% 62%',
      }}
    >
      <AnhNen anh={anh} tu={1.14} den={1.0} goc="50% 55%" toi={toi} />
    </div>
  );
};

const LopNenLuBun = ({anh, toi}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 22], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        opacity: op,
      }}
    >
      <AnhNen anh={anh} tu={1.03} den={1.13} goc="50% 60%" toi={toi} />
    </div>
  );
};

const LopCanDuong = ({anh, punch}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 12], [0, 1], kep);
  const zoom = interpolate(f, [0, 24, 88], [punch, 1.04, 1.10], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        opacity: op,
        transform: `scale(${zoom})`,
        transformOrigin: '50% 72%',
      }}
    >
      <AnhNen anh={anh} tu={1.02} den={1.07} goc="50% 72%" toi={0.03} />
    </div>
  );
};

const LopTheHe = ({anh}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 18], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const ra = interpolate(f, [196, 215], [1, 0], kep);
  const dx = interpolate(f, [0, 215], [12, -24], kep);
  const dy = interpolate(f, [0, 215], [0, -16], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 600,
        height: 596,
        opacity: Math.min(vao, ra),
        transform: `translate(${dx}px, ${dy}px)`,
      }}
    >
      <Img
        name="Gia đình nhà King nhìn từ sau lưng"
        src={src(anh)}
        style={{
          width: 600,
          height: 596,
          objectFit: 'contain',
          filter: 'sepia(0.45) contrast(0.95) drop-shadow(0 18px 26px rgba(0,0,0,0.35))',
        }}
      />
    </div>
  );
};

const LopDanBo = ({anh}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 22], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const ra = interpolate(f, [113, 137], [1, 0], kep);
  const dx = interpolate(f, [0, 28, 137], [120, 0, -46], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 900,
        height: 238,
        opacity: Math.min(vao, ra),
        transform: `translateX(${dx}px)`,
      }}
    >
      <Img
        name="Đàn bò ăn cỏ trên đồng"
        src={src(anh)}
        style={{
          width: 900,
          height: 238,
          objectFit: 'contain',
          filter: 'drop-shadow(0 16px 22px rgba(0,0,0,0.30))',
        }}
      />
    </div>
  );
};

const ChuKhoa = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 14], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const ra = interpolate(f, [192, 207], [1, 0], kep);
  const day = interpolate(f, [0, 22], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const dich = interpolate(f, [0, 42], [46, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{opacity: Math.min(vao, ra), transform: `translateX(${dich}px)`}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 900,
          color: mau,
          letterSpacing: 4,
          lineHeight: 1,
          whiteSpace: 'nowrap',
          textShadow: '0 10px 34px rgba(0,0,0,0.55)',
        }}
      >
        {chu}
      </div>
      <div
        style={{
          marginTop: 20,
          width: 660 * day,
          height: 14,
          background: VANG,
          borderRadius: 8,
        }}
      />
    </div>
  );
};

export const Canh = (props) => {
  const {
    anhNenTrangTrai,
    anhNenLuBun,
    anhCanDuongCat,
    anhDanBo,
    anhTheHe,
    chuKhoa,
    coChu,
    mauChu,
    doDamNen,
    doDamLu,
    punchNen,
    punchDuong,
  } = props;

  return (
    <AbsoluteFill style={{backgroundColor: '#101010'}}>
      <Interactive.Div
        name="Nền trang trại xanh"
        from={0}
        durationInFrames={222}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopNenTrangTrai anh={anhNenTrangTrai} punch={punchNen} toi={doDamNen} />
      </Interactive.Div>

      <Interactive.Div
        name="Nền dòng lũ bùn"
        from={200}
        durationInFrames={179}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopNenLuBun anh={anhNenLuBun} toi={doDamLu} />
      </Interactive.Div>

      <Interactive.Div
        name="Cận đường đất bị cát vùi lấp"
        from={291}
        durationInFrames={88}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopCanDuong anh={anhCanDuongCat} punch={punchDuong} />
      </Interactive.Div>

      <Interactive.Div
        name="Gia đình nhà King"
        from={4}
        durationInFrames={216}
        style={{position: 'absolute', left: 240, top: 320, width: 600, height: 596}}
      >
        <LopTheHe anh={anhTheHe} />
      </Interactive.Div>

      <Interactive.Div
        name="Đàn bò chăn thả"
        from={82}
        durationInFrames={138}
        style={{position: 'absolute', left: 820, top: 718, width: 900, height: 238}}
      >
        <LopDanBo anh={anhDanBo} />
      </Interactive.Div>

      <Interactive.Div
        name="Chữ khoá"
        from={4}
        durationInFrames={208}
        style={{position: 'absolute', left: 120, top: 110, width: 900, height: 230}}
      >
        <ChuKhoa chu={chuKhoa} co={coChu} mau={mauChu} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
