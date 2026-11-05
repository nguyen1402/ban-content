import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, interpolateColors, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const lerp = (a, b, t) => a + (b - a) * t;

const dinhDang = (n) => {
  const s = Math.round(n).toString();
  return s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
};

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền phong cảnh / bản vẽ kỹ thuật'),
  anhDap: z.string().describe('Ảnh cắt đập bê tông kiên cố'),
  tongTien: z.number().describe('Số tiền cuối cùng (đô la)'),
  nguongDo: z.number().describe('Ngưỡng ngân sách cảnh báo (đô la)'),
  coSo: z.number().describe('Cỡ chữ bộ đếm số tiền'),
  rongThanh: z.number().describe('Chiều rộng thanh ngân sách'),
  mauSo: z.string().describe('Màu số tiền bình thường'),
  mauDo: z.string().describe('Màu đỏ cảnh báo'),
  mauDay: z.string().describe('Màu thanh tiến độ trước ngưỡng'),
  damTrai: z.number().describe('Vị trí trái của đập bê tông'),
  damTren: z.number().describe('Vị trí trên của đập bê tông'),
  damRong: z.number().describe('Chiều rộng đập bê tông'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  /* ---------- LỚP NỀN PHONG CẢNH ---------- */
  const opNen = interpolate(frame, [0, 22], [0.4, 1], {...kep});

  /* ---------- ĐẬP BÊ TÔNG ---------- */
  const fD = frame - 4;
  const truot = interpolate(fD, [0, 52], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const yTruot = lerp(-560, 0, truot);
  const opDap = interpolate(fD, [0, 24], [0, 1], {...kep});
  const net = interpolate(fD, [66, 84], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const nhay = interpolate(fD, [71, 81, 110], [1, 1.075, 1.0], {...kep, easing: Easing.inOut(Easing.quad)});
  const thuNho = interpolate(fD, [129, 172], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});

  const tiLe = nhay * lerp(1, 0.745, thuNho);
  const tx = lerp(0, -340, thuNho);
  const troi = Math.sin(frame / 44) * 5;
  const ty = yTruot + lerp(0, 30, thuNho) + troi;

  /* ---------- BỘ ĐẾM CHI PHÍ ---------- */
  const c = frame - 133;
  const tienDo = interpolate(c, [0, 49], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const giaTri = Math.min(props.tongTien, props.tongTien * tienDo);
  const daDo = interpolate(c, [49, 66], [0, 1], {...kep});
  const pop = interpolate(c, [49, 58, 74], [1, 1.12, 1.05], {...kep, easing: Easing.out(Easing.quad)});
  const veThe = interpolate(c, [0, 16], [0, 1], {...kep});
  const veThanh = interpolate(c, [4, 22], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const veVach = interpolate(c, [8, 28], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  const mauChu = interpolateColors(daDo, [0, 1], [props.mauSo, props.mauDo]);
  const rongDay = props.rongThanh * Math.min(1, giaTri / props.tongTien);
  const viTriVach = props.rongThanh * (props.nguongDo / props.tongTien);
  const daVuot = giaTri >= props.nguongDo;
  const mauDay = daVuot ? props.mauDo : props.mauDay;

  return (
    <AbsoluteFill style={{backgroundColor: '#08111c'}}>

      {/* NỀN PHONG CẢNH TRANG TRẠI */}
      <Interactive.Div
        name="Nền phong cảnh trang trại"
        from={0}
        durationInFrames={384}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: opNen}}
      >
        <AnhNen anh={props.anhNen} tu={1.03} den={1.16} goc="50% 45%" toi={0.26} />
      </Interactive.Div>

      {/* ĐẬP BÊ TÔNG KIÊN CỐ */}
      <Interactive.Div
        name="Đập bê tông kiên cố"
        from={4}
        durationInFrames={380}
        style={{
          position: 'absolute',
          left: props.damTrai,
          top: props.damTren,
          width: props.damRong,
          transform: `translate(${tx}px, ${ty}px) scale(${tiLe})`,
          transformOrigin: '0% 0%',
          opacity: opDap,
          filter: `saturate(${lerp(0.5, 1.12, net)}) brightness(${lerp(0.92, 1.04, net)}) contrast(${lerp(0.95, 1.1, net)})`,
        }}
      >
        <Img
          src={src(props.anhDap)}
          name="Ảnh đập bê tông"
          from={4}
          durationInFrames={380}
          style={{width: '100%', display: 'block', filter: 'drop-shadow(0 26px 44px rgba(0,0,0,0.5))'}}
        />
      </Interactive.Div>

      {/* BỘ ĐẾM CHI PHÍ */}
      <Interactive.Div
        name="Bộ đếm chi phí"
        from={133}
        durationInFrames={251}
        style={{position: 'absolute', left: 940, top: 250, width: 900, height: 560}}
      >
        {/* thẻ nền mờ cho số tiền */}
        <div
          style={{
            position: 'absolute',
            left: -20,
            top: -50,
            width: 940,
            height: 520,
            borderRadius: 28,
            background: 'rgba(6,16,28,0.32)',
            border: '2px solid rgba(255,255,255,0.14)',
            opacity: veThe,
          }}
        />

        {/* số tiền */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 20,
            width: 900,
            textAlign: 'center',
            fontFamily: FONT,
            fontWeight: 900,
            fontSize: props.coSo,
            lineHeight: 1,
            letterSpacing: -6,
            whiteSpace: 'nowrap',
            color: mauChu,
            textShadow: '0 10px 34px rgba(0,0,0,0.6)',
            transform: `scale(${pop})`,
            transformOrigin: '50% 50%',
          }}
        >
          {`$${dinhDang(giaTri)}`}
        </div>

        {/* thanh ngân sách + vạch đỏ */}
        <div
          style={{
            position: 'absolute',
            left: 50,
            top: 320,
            width: props.rongThanh,
            height: 30,
            opacity: veThanh,
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              height: 30,
              background: 'rgba(8,20,34,0.55)',
              border: '2px solid rgba(255,255,255,0.45)',
              borderRadius: 15,
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: rongDay,
              height: 30,
              background: mauDay,
              borderRadius: 15,
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: viTriVach - 4,
              top: -60,
              width: 8,
              height: 110,
              background: props.mauDo,
              borderRadius: 4,
              transformOrigin: '50% 100%',
              transform: `scaleY(${veVach})`,
            }}
          />
        </div>
      </Interactive.Div>

    </AbsoluteFill>
  );
};
