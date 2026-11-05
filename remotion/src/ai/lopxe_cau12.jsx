import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền đồng cỏ khô cằn'),
  anh_mong: z.string().describe('Ảnh móng bò tách nền'),
  anh_bua: z.string().describe('Ảnh búa tạ tách nền'),
  anh_dat: z.string().describe('Ảnh cận cảnh lớp đất mặt nứt nẻ'),
  anh_thuc_vat: z.string().describe('Ảnh thảm thực vật khô tách nền'),
  luc_punch: z.number().describe('Độ phóng punch-in khi búa tạ giáng xuống'),
  nhip_mong: z.number().describe('Số frame cho một nhịp giẫm của móng bò'),
  do_nhay_mong: z.number().describe('Độ nhấc lên của móng bò (px)'),
  toc_do_truot: z.number().describe('Tốc độ trôi xuống của lớp móng bò (px/frame)'),
  rong_mong: z.number().describe('Chiều rộng hiển thị của một móng bò (px)'),
  rong_bua: z.number().describe('Chiều rộng hiển thị của búa tạ (px)'),
  rong_thuc_vat: z.number().describe('Chiều rộng hiển thị của thảm thực vật (px)'),
});

/* ---------- lớp móng bò giẫm đạp (dùng local frame của Interactive.Div) ---------- */
const MongBo = ({anh, ds, nhip, nhay, truot, tiLe}) => {
  const f = useCurrentFrame();
  return (
    <>
      {ds.map((m, i) => {
        const p = ((((f + m.d) % nhip) + nhip) % nhip) / nhip;
        const nang = interpolate(p, [0, 0.5, 0.72, 1], [1, 0, 0.28, 1], kep);
        const dy = -nhay * nang + truot * f;
        const bop = 1 - 0.12 * (1 - nang);
        const w = m.w * tiLe;
        const h = (w * 682) / 585;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: m.x,
              top: m.y + dy,
              width: w,
              height: h,
              transform: `rotate(${m.r}deg) scaleY(${bop})`,
              transformOrigin: '50% 100%',
            }}
          >
            <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
          </div>
        );
      })}
    </>
  );
};

/* ---------- búa tạ giáng xuống ---------- */
const BuaTa = ({anh, rong, x, y}) => {
  const f = useCurrentFrame();
  const dy = interpolate(f, [0, 3, 9, 18, 22, 27, 33, 40, 51], [-540, 70, -180, -480, -520, 70, -220, -600, -900], kep);
  const op = interpolate(f, [0, 2, 42, 51], [0, 1, 1, 0], kep);
  const h = (rong * 417) / 700;
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y + dy,
        width: rong,
        height: h,
        opacity: op,
        transform: 'rotate(-7deg)',
        transformOrigin: '50% 100%',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

/* ---------- thảm thực vật khô héo ---------- */
const ThucVat = ({anh, rong}) => {
  const f = useCurrentFrame();
  const len = interpolate(f, [0, 18], [320, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const op = interpolate(f, [0, 12], [0, 1], kep);
  const heo = interpolate(f, [20, 145], [1, 0.86], kep);
  const nghieng = interpolate(f, [20, 145], [0, -2.4], kep);
  const h = (rong * 345) / 700;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: rong,
        height: h,
        opacity: op,
        transform: `translateY(${len}px) rotate(${nghieng}deg) scaleY(${heo})`,
        transformOrigin: '50% 100%',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

const MONG = [
  {x: -10, y: -170, w: 480, d: 0.0, r: -5},
  {x: 450, y: -200, w: 480, d: 2.5, r: 3},
  {x: 910, y: -170, w: 480, d: 5.0, r: -2},
  {x: 1370, y: -200, w: 480, d: 7.5, r: 6},
  {x: -60, y: 170, w: 540, d: 4.0, r: 4},
  {x: 420, y: 140, w: 540, d: 1.2, r: -6},
  {x: 900, y: 170, w: 540, d: 6.4, r: 2},
  {x: 1380, y: 140, w: 540, d: 3.6, r: -4},
  {x: 160, y: 540, w: 580, d: 5.5, r: -3},
  {x: 760, y: 520, w: 580, d: 0.8, r: 5},
  {x: 1360, y: 540, w: 580, d: 3.0, r: -5},
];

export const Canh = (props) => {
  const frame = useCurrentFrame();

  // punch-in quanh từ «búa tạ» (87) và «tạ» (111)
  const p1 = interpolate(frame, [85, 87, 93, 106], [1, 1 + props.luc_punch, 1 + props.luc_punch * 0.85, 1], kep);
  const p2 = interpolate(frame, [109, 111, 117, 131], [1, 1 + props.luc_punch * 0.75, 1 + props.luc_punch * 0.6, 1], kep);
  const scale = p1 * p2;

  // swipe lớp đất nứt vào từ phải ở frame 122
  const sx = interpolate(frame, [122, 142], [1920, 0], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#1a1207', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${scale})`, transformOrigin: '50% 55%'}}>
        {/* NỀN: đồng cỏ khô cằn */}
        <Interactive.Div name="Nền đồng cỏ khô" from={0} durationInFrames={319} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
          <AnhNen anh={props.anh_nen} tu={1.0} den={1.14} goc="50% 45%" toi={0.06} />
        </Interactive.Div>

        {/* MÓNG BÒ GIẪM ĐẠP */}
        <Interactive.Div name="Lớp móng bò giẫm đạp" from={4} durationInFrames={136} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
          <MongBo
            anh={props.anh_mong}
            ds={MONG}
            nhip={props.nhip_mong}
            nhay={props.do_nhay_mong}
            truot={props.toc_do_truot}
            tiLe={props.rong_mong / 480}
          />
        </Interactive.Div>

        {/* BÚA TẠ GIÁNG XUỐNG */}
        <Interactive.Div name="Búa tạ giáng xuống" from={84} durationInFrames={52} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
          <BuaTa anh={props.anh_bua} rong={props.rong_bua} x={400} y={40} />
        </Interactive.Div>

        {/* CẬN CẢNH ĐẤT MẶT NỨT NẺ (swipe từ phải) */}
        <Interactive.Div
          name="Cận cảnh đất mặt nứt nẻ"
          from={122}
          durationInFrames={197}
          style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: `translateX(${sx}px)`}}
        >
          <AnhNen anh={props.anh_dat} tu={1.15} den={1.02} goc="50% 50%" toi={0.1} />
        </Interactive.Div>

        {/* THẢM THỰC VẬT KHÔ HÉO ĐÈ LÊN MẶT ĐẤT */}
        <Interactive.Div
          name="Thảm thực vật khô héo"
          from={174}
          durationInFrames={145}
          style={{position: 'absolute', left: 210, top: 545, width: 1500, height: 740}}
        >
          <ThucVat anh={props.anh_thuc_vat} rong={props.rong_thuc_vat} />
        </Interactive.Div>
      </div>
    </AbsoluteFill>
  );
};
