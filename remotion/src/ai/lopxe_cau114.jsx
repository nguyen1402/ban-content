import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhLopXe: z.string().describe('Ảnh sa mạc Arizona với đống lốp xe cũ'),
  anhDat: z.string().describe('Ảnh cận cảnh đất tự nhiên giữ nước'),
  anhBeTong: z.string().describe('Ảnh đập bê tông nứt nẻ dưới nắng'),
  soLuong: z.number().describe('Số lốp xe hiển thị trên màn hình'),
  donVi: z.string().describe('Đơn vị đi kèm số đếm'),
  demGiay: z.number().describe('Thời gian chạy số đếm (giây)'),
  coSo: z.number().describe('Cỡ chữ của số đếm'),
  wipeDat: z.number().describe('Số frame lướt chuyển sang ảnh đất'),
  wipeBeTong: z.number().describe('Số frame chuyển nhanh sang ảnh bê tông'),
});

// ---- Ảnh 1: sa mạc Arizona + lốp xe, đẩy máy chậm, thêm cú push-in ở nhịp 100 ----
const AnhLopXe = ({anh}) => {
  const f = useCurrentFrame();
  const push = interpolate(f, [100, 168], [1, 1.07], {...kep, easing: Easing.inOut(Easing.quad)});
  return (
    <div style={{position: 'absolute', inset: 0, transform: `scale(${push})`, transformOrigin: '50% 58%'}}>
      <AnhNen anh={anh} tu={1} den={1.06} goc="50% 50%" toi={0.14} />
    </div>
  );
};

// ---- Ảnh 2: đất tự nhiên giữ nước, lướt vào bằng wipe + lia máy ----
const AnhDat = ({anh, batDau, dai}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + dai], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const clip = `inset(0 ${(1 - p) * 100}% 0 0)`;
  return (
    <div style={{position: 'absolute', inset: 0, clipPath: clip, WebkitClipPath: clip}}>
      <AnhLia anh={anh} huong="phai" quang={90} toi={0.1} />
    </div>
  );
};

// ---- Ảnh 3: đập bê tông nứt nẻ, chuyển cảnh nhanh từ dưới lên, pull-back ----
const AnhBeTong = ({anh, batDau, dai}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + dai], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const clip = `inset(${(1 - p) * 100}% 0 0 0)`;
  return (
    <div style={{position: 'absolute', inset: 0, clipPath: clip, WebkitClipPath: clip}}>
      <AnhNen anh={anh} tu={1.16} den={1.02} goc="50% 60%" toi={0.1} />
    </div>
  );
};

// ---- Số đếm 1.500 ----
const Dem = ({so, donVi, giay, co}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [148, 166], [1, 0], kep);
  return (
    <div style={{opacity: op}}>
      <SoDem so={so} don_vi={donVi} giay={giay} co={co} />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0d0b08'}}>
      <Interactive.Div
        name="Ảnh lốp xe giữa sa mạc Arizona"
        from={0}
        durationInFrames={196}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLopXe anh={props.anhLopXe} />
      </Interactive.Div>

      <Interactive.Div
        name="Số đếm 1.500"
        from={4}
        durationInFrames={166}
        style={{position: 'absolute', left: 140, top: 700}}
      >
        <Dem so={props.soLuong} donVi={props.donVi} giay={props.demGiay} co={props.coSo} />
      </Interactive.Div>

      <Interactive.Div
        name="Ảnh đất tự nhiên giữ nước"
        from={170}
        durationInFrames={135}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhDat anh={props.anhDat} batDau={0} dai={props.wipeDat} />
      </Interactive.Div>

      <Interactive.Div
        name="Ảnh đập bê tông nứt nẻ"
        from={291}
        durationInFrames={79}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhBeTong anh={props.anhBeTong} batDau={2} dai={props.wipeBeTong} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
