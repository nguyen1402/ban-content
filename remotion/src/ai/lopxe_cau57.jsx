import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, FONT, VANG} from './thu_vien.jsx';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anh_nen_site: z.string().describe('Ảnh nền công trường đập lốp xe thập niên 1990'),
  anh_tach_minyard: z.string().describe('Ảnh cắt nhân vật thợ Minyard'),
  anh_can_tires: z.string().describe('Ảnh cận cảnh đống lốp xe xếp gọn'),
  anh_nen_storm: z.string().describe('Ảnh bầu trời giông bão kéo đến trên trang trại'),
  chu_ten: z.string().describe('Tên nhân vật hiển thị trên màn hình'),
  so_tuan: z.number().describe('Số tuần đếm trên đồng hồ tiến độ'),
  co_dong_ho: z.number().describe('Cỡ chữ số của đồng hồ tiến độ'),
  mau_nhan: z.string().describe('Màu nhấn cho đồng hồ tiến độ'),
});

/* ---------- lớp ảnh nền có push-in chậm ---------- */
const AnhNenDay = ({anh, tu, den, goc, toi, dur}) => {
  const f = useCurrentFrame();
  const scale = interpolate(f, [0, dur], [tu, den], clamp);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale})`,
          transformOrigin: goc,
        }}
      />
      <AbsoluteFill style={{backgroundColor: '#000', opacity: toi}} />
    </AbsoluteFill>
  );
};

/* ---------- khối 1: công trường 1990 ---------- */
const KhoiNenSite = ({anh}) => (
  <AbsoluteFill>
    <AnhNenDay anh={anh} tu={1.03} den={1.16} goc="50% 55%" toi={0.2} dur={30} />
  </AbsoluteFill>
);

/* ---------- khối 2: lớp cắt thợ Minyard (parallax) ---------- */
const KhoiMinyard = ({anh}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200, stiffness: 90}, durationInFrames: 20});
  const bottom = interpolate(vao, [0, 1], [-200, 55]);
  const left = interpolate(f, [0, 26], [185, 95], clamp);
  return (
    <div style={{position: 'absolute', left, bottom, width: 820}}>
      <Img
        src={src(anh)}
        style={{width: 820, height: 'auto', display: 'block', filter: 'drop-shadow(0 18px 40px rgba(0,0,0,0.55))'}}
      />
    </div>
  );
};

/* ---------- khối 3: tên nhân vật ---------- */
const KhoiTen = ({chu}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200}, durationInFrames: 14});
  const x = interpolate(vao, [0, 1], [-70, 0]);
  const op = interpolate(f, [0, 4, 17, 22], [0, 1, 1, 0], clamp);
  const w = interpolate(f, [2, 15], [0, 430], {...clamp, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'absolute', left: 130, top: 108, opacity: op, transform: `translateX(${x}px)`}}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 150,
          fontWeight: 900,
          color: '#ffffff',
          letterSpacing: 8,
          lineHeight: 1,
          textShadow: '0 8px 26px rgba(0,0,0,0.6)',
        }}
      >
        {chu}
      </div>
      <div style={{width: w, height: 12, backgroundColor: VANG, marginTop: 20, borderRadius: 6}} />
    </div>
  );
};

/* ---------- khối 4: cận cảnh đống lốp (whoosh + pull-back) ---------- */
const KhoiLopXe = ({anh}) => {
  const f = useCurrentFrame();
  const s =
    f < 14
      ? interpolate(f, [0, 14], [1.36, 1.16], {...clamp, easing: Easing.out(Easing.cubic)})
      : interpolate(f, [14, 254], [1.16, 1.02], clamp);
  const sweepX = interpolate(f, [0, 13], [-620, 2150], clamp);
  const sweepOp = interpolate(f, [0, 2, 10, 14], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${s})`,
          transformOrigin: '50% 45%',
        }}
      />
      <AbsoluteFill style={{backgroundColor: '#000', opacity: 0.12}} />
      <div
        style={{
          position: 'absolute',
          left: sweepX,
          top: -220,
          width: 420,
          height: 1560,
          transform: 'rotate(12deg)',
          opacity: sweepOp,
          background:
            'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.42) 50%, rgba(255,255,255,0) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};

/* ---------- khối 5: đồng hồ tiến độ +1 tuần ---------- */
const KhoiDongHo = ({so, co, mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 200}, durationInFrames: 14});
  const len = interpolate(vao, [0, 1], [70, 0]);
  const op = interpolate(f, [0, 7, 120, 132], [0, 1, 1, 0], clamp);
  const p = interpolate(f, [6, 50], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const val = so * p;
  const hien = val >= so - 0.0001 ? `${so}` : val.toFixed(1);
  return (
    <div
      style={{
        position: 'absolute',
        left: 1040,
        top: 540,
        width: 740,
        opacity: op,
        transform: `translateY(${len}px)`,
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(10,14,18,0.45)',
          borderRadius: 26,
          padding: '34px 46px 38px 46px',
          border: `3px solid ${mau}`,
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', gap: 22}}>
          <div style={{fontFamily: FONT, fontSize: 112, fontWeight: 900, color: mau, lineHeight: 1}}>+</div>
          <div style={{fontFamily: FONT, fontSize: co, fontWeight: 900, color: '#ffffff', lineHeight: 1}}>{hien}</div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 78,
              fontWeight: 800,
              color: mau,
              letterSpacing: 6,
              lineHeight: 1,
            }}
          >
            TUẦN
          </div>
        </div>
        <div
          style={{
            marginTop: 28,
            width: '100%',
            height: 18,
            backgroundColor: 'rgba(255,255,255,0.22)',
            borderRadius: 9,
            overflow: 'hidden',
          }}
        >
          <div style={{width: `${p * 100}%`, height: '100%', backgroundColor: mau, borderRadius: 9}} />
        </div>
      </div>
    </div>
  );
};

/* ---------- khối 6: bão kéo đến (whip-pan + punch-in) ---------- */
const KhoiBao = ({anh}) => {
  const f = useCurrentFrame();
  const whip = interpolate(f, [0, 10], [1920, 0], {...clamp, easing: Easing.out(Easing.cubic)});
  const drift = 1.05 + 0.055 * (f / 140);
  const punch = interpolate(f, [66, 71], [0, 0.13], clamp);
  const punch2 = interpolate(f, [100, 105], [0, 0.06], clamp);
  const s = drift + punch + punch2;
  return (
    <AbsoluteFill style={{transform: `translateX(${whip}px)`}}>
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Img
          src={src(anh)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${s})`,
            transformOrigin: '50% 40%',
          }}
        />
        <AbsoluteFill style={{backgroundColor: '#0a0d12', opacity: 0.18}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- nháy sáng trắng ---------- */
const NhaySang = () => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 1, 2], [0.9, 0.5, 0], clamp);
  return <AbsoluteFill style={{backgroundColor: '#ffffff', opacity: op}} />;
};

/* ---------- shot ---------- */
export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0e12'}}>
      <Interactive.Div
        name="Nền công trường lốp xe 1990"
        from={0}
        durationInFrames={30}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiNenSite anh={props.anh_nen_site} />
      </Interactive.Div>

      <Interactive.Div
        name="Lớp cắt thợ Minyard"
        from={4}
        durationInFrames={26}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiMinyard anh={props.anh_tach_minyard} />
      </Interactive.Div>

      <Interactive.Div
        name="Tên nhân vật"
        from={4}
        durationInFrames={22}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiTen chu={props.chu_ten} />
      </Interactive.Div>

      <Interactive.Div
        name="Cận cảnh đống lốp xe"
        from={26}
        durationInFrames={254}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiLopXe anh={props.anh_can_tires} />
      </Interactive.Div>

      <Interactive.Div
        name="Đồng hồ tiến độ một tuần"
        from={58}
        durationInFrames={132}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiDongHo so={props.so_tuan} co={props.co_dong_ho} mau={props.mau_nhan} />
      </Interactive.Div>

      <Interactive.Div
        name="Bầu trời giông bão ập đến"
        from={264}
        durationInFrames={140}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <KhoiBao anh={props.anh_nen_storm} />
      </Interactive.Div>

      <Interactive.Div
        name="Nháy sáng trắng"
        from={365}
        durationInFrames={3}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NhaySang />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
