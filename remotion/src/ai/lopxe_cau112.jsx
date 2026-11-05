import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, FONT, AnhNen} from './thu_vien.jsx';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anhFlorida: z.string().describe('Ảnh tư liệu bãi lốp xe dưới biển Florida'),
  anhArizona: z.string().describe('Ảnh toàn cảnh đập khô Arizona'),
  anhThep: z.string().describe('Ảnh cận cảnh thanh thép chằng néo'),
  chuFlorida: z.string().describe('Chữ hiển thị ở cảnh Florida'),
  chuArizona: z.string().describe('Chữ hiển thị ở cảnh Arizona'),
  coChu: z.number().describe('Cỡ chữ nhãn địa danh (px)'),
  mauChu: z.string().describe('Màu chữ nhãn địa danh'),
  mauGach: z.string().describe('Màu gạch chân dưới nhãn'),
  toiFlorida: z.number().describe('Độ tối lớp phủ ảnh Florida (0–0.5)'),
  toiArizona: z.number().describe('Độ tối lớp phủ ảnh Arizona (0–0.5)'),
  zoomFloridaTu: z.number().describe('Tỉ lệ zoom đầu của ảnh Florida'),
  zoomFloridaDen: z.number().describe('Tỉ lệ zoom cuối của ảnh Florida'),
  zoomArizonaTu: z.number().describe('Tỉ lệ zoom đầu của ảnh Arizona'),
  zoomArizonaDen: z.number().describe('Tỉ lệ zoom cuối của ảnh Arizona'),
  zoomThepTu: z.number().describe('Tỉ lệ zoom đầu của ảnh thép'),
  zoomThepDen: z.number().describe('Tỉ lệ zoom cuối của ảnh thép'),
  rongKhungThep: z.number().describe('Chiều rộng khung cận cảnh thép (px)'),
  caoKhungThep: z.number().describe('Chiều cao khung cận cảnh thép (px)'),
});

/* ---------- lớp ảnh Florida: kéo lùi chậm + cú nhấn ở nhịp 5 + trượt ngang ra ---------- */
const LopFlorida = ({anh, zoomTu, zoomDen, toi}) => {
  const f = useCurrentFrame();
  const tx = interpolate(f, [67, 84], [0, -1920], {...CLAMP, easing: Easing.inOut(Easing.cubic)});
  const sc = interpolate(f, [5, 18], [1.06, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});
  return (
    <AbsoluteFill style={{transform: `translateX(${tx}px) scale(${sc})`, transformOrigin: '50% 45%'}}>
      <AnhNen anh={src(anh)} tu={zoomTu} den={zoomDen} goc="50% 45%" toi={toi} />
    </AbsoluteFill>
  );
};

/* ---------- lớp ảnh Arizona: trượt ngang vào + cú nhấn ở nhịp 113 ---------- */
const LopArizona = ({anh, zoomTu, zoomDen, toi}) => {
  const f = useCurrentFrame();
  const tx = interpolate(f, [0, 17], [1920, 0], {...CLAMP, easing: Easing.inOut(Easing.cubic)});
  const sc = interpolate(f, [46, 64], [1, 1.035], {...CLAMP, easing: Easing.out(Easing.cubic)});
  return (
    <AbsoluteFill style={{transform: `translateX(${tx}px) scale(${sc})`, transformOrigin: '50% 55%'}}>
      <AnhNen anh={src(anh)} tu={zoomTu} den={zoomDen} goc="50% 55%" toi={toi} />
    </AbsoluteFill>
  );
};

/* ---------- khung cận cảnh thanh thép chằng néo ---------- */
const LopThep = ({anh, zoomTu, zoomDen, rong, cao}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 16], [720, 0], {...CLAMP, easing: Easing.out(Easing.cubic)});
  const ra = interpolate(f, [46, 56], [0, 1], {...CLAMP, easing: Easing.in(Easing.cubic)});
  const ty = vao - ra * 760;
  const opacity = interpolate(f, [46, 56], [1, 0], CLAMP);
  return (
    <div
      style={{
        position: 'relative',
        width: rong,
        height: cao,
        overflow: 'hidden',
        borderRadius: 6,
        border: '2px solid rgba(255,255,255,0.5)',
        transform: `translateY(${ty}px)`,
        opacity,
      }}
    >
      <AnhNen anh={src(anh)} tu={zoomTu} den={zoomDen} goc="50% 50%" toi={0.05} />
    </div>
  );
};

/* ---------- chữ Florida ---------- */
const ChuFloridaLop = ({chu, coChu, mauChu, mauGach}) => {
  const f = useCurrentFrame();
  const opacity = interpolate(f, [0, 12, 56, 72], [0, 1, 1, 0], CLAMP);
  const tx = interpolate(f, [0, 16, 56, 72], [-80, 0, 0, -300], {...CLAMP, easing: Easing.out(Easing.cubic)});
  const gach = interpolate(f, [10, 34], [0, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{opacity, transform: `translateX(${tx}px)`}}>
      <div style={{position: 'relative', display: 'inline-block'}}>
        <span
          style={{
            fontFamily: FONT,
            fontSize: coChu,
            fontWeight: 800,
            lineHeight: 1,
            letterSpacing: '-0.02em',
            color: mauChu,
            whiteSpace: 'nowrap',
            textShadow: '0 8px 34px rgba(0,0,0,0.6)',
          }}
        >
          {chu}
        </span>
        <div
          style={{
            position: 'absolute',
            left: 0,
            bottom: -24,
            width: '100%',
            height: 10,
            borderRadius: 5,
            background: mauGach,
            transform: `scaleX(${gach})`,
            transformOrigin: 'left center',
          }}
        />
      </div>
    </div>
  );
};

/* ---------- chữ Arizona ---------- */
const ChuArizonaLop = ({chu, coChu, mauChu, mauGach}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 200}, durationInFrames: 26});
  const opacity = interpolate(f, [0, 10], [0, 1], CLAMP);
  const tx = interpolate(s, [0, 1], [-120, 0]);
  const gach = interpolate(f, [12, 38], [0, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{opacity, transform: `translateX(${tx}px)`}}>
      <div style={{position: 'relative', display: 'inline-block'}}>
        <span
          style={{
            fontFamily: FONT,
            fontSize: coChu,
            fontWeight: 800,
            lineHeight: 1,
            letterSpacing: '-0.02em',
            color: mauChu,
            whiteSpace: 'nowrap',
            textShadow: '0 8px 34px rgba(0,0,0,0.6)',
          }}
        >
          {chu}
        </span>
        <div
          style={{
            position: 'absolute',
            left: 0,
            bottom: -24,
            width: '100%',
            height: 10,
            borderRadius: 5,
            background: mauGach,
            transform: `scaleX(${gach})`,
            transformOrigin: 'left center',
          }}
        />
      </div>
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0e11'}}>
      {/* Nền Arizona: giữ tới khung cuối */}
      <Interactive.Div
        name="Ảnh toàn cảnh đập khô Arizona"
        from={67}
        durationInFrames={188}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopArizona
          anh={props.anhArizona}
          zoomTu={props.zoomArizonaTu}
          zoomDen={props.zoomArizonaDen}
          toi={props.toiArizona}
        />
      </Interactive.Div>

      {/* Nền Florida: trượt ra ở nhịp 67 */}
      <Interactive.Div
        name="Ảnh tư liệu bãi lốp dưới biển Florida"
        from={0}
        durationInFrames={85}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopFlorida
          anh={props.anhFlorida}
          zoomTu={props.zoomFloridaTu}
          zoomDen={props.zoomFloridaDen}
          toi={props.toiFlorida}
        />
      </Interactive.Div>

      {/* Khung cận cảnh thanh thép chằng néo */}
      <Interactive.Div
        name="Khung cận cảnh thanh thép chằng néo"
        from={67}
        durationInFrames={56}
        style={{position: 'absolute', left: 950, top: 240}}
      >
        <LopThep
          anh={props.anhThep}
          zoomTu={props.zoomThepTu}
          zoomDen={props.zoomThepDen}
          rong={props.rongKhungThep}
          cao={props.caoKhungThep}
        />
      </Interactive.Div>

      {/* Chữ Florida */}
      <Interactive.Div
        name="Chữ Florida"
        from={5}
        durationInFrames={76}
        style={{position: 'absolute', left: 110, top: 96}}
      >
        <ChuFloridaLop
          chu={props.chuFlorida}
          coChu={props.coChu}
          mauChu={props.mauChu}
          mauGach={props.mauGach}
        />
      </Interactive.Div>

      {/* Chữ Arizona */}
      <Interactive.Div
        name="Chữ Arizona"
        from={113}
        durationInFrames={142}
        style={{position: 'absolute', left: 110, top: 96}}
      >
        <ChuArizonaLop
          chu={props.chuArizona}
          coChu={props.coChu}
          mauChu={props.mauChu}
          mauGach={props.mauGach}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
