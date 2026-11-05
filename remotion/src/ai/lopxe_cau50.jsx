import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhBoKe: z.string().describe('Ảnh bờ kè bê tông cứng bị nước lũ xói mòn hai bên'),
  anhBanVe: z.string().describe('Ảnh bản vẽ kỹ thuật phương án gia cố bờ đất'),
  anhSoDo: z.string().describe('Ảnh sơ đồ cắt lớp mỏ neo thép cắm vào bờ'),
  anhThuocDo: z.string().describe('Ảnh thước đo chiều sâu mỏ neo'),
  doSau: z.number().describe('Độ sâu mỏ neo tính bằng mét'),
  donVi: z.string().describe('Đơn vị của độ sâu'),
  coSo: z.number().describe('Cỡ chữ số độ sâu (px)'),
  coThuoc: z.number().describe('Chiều cao ảnh thước đo (px)'),
  xThuoc: z.number().describe('Toạ độ X của thước đo'),
  yThuoc: z.number().describe('Toạ độ Y của thước đo'),
  xSo: z.number().describe('Toạ độ X của số độ sâu'),
  ySo: z.number().describe('Toạ độ Y của số độ sâu'),
  xVong: z.number().describe('Toạ độ X vòng khoanh bờ kè bị xói'),
  yVong: z.number().describe('Toạ độ Y vòng khoanh bờ kè bị xói'),
  wVong: z.number().describe('Chiều rộng vòng khoanh'),
  hVong: z.number().describe('Chiều cao vòng khoanh'),
});

const LopVongXoi = ({w, h}) => {
  const f = useCurrentFrame();
  const sc = interpolate(f, [0, 186], [1, 1.07], kep);
  return (
    <div style={{transform: `scale(${sc})`, transformOrigin: '50% 50%'}}>
      <VongBut w={w} h={h} />
    </div>
  );
};

const LopThuocDo = ({anh, cao}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const tien = spring({frame: f, fps, config: {damping: 18, mass: 0.8}});
  const x = interpolate(tien, [0, 1], [520, 0]);
  const op = interpolate(f, [0, 9], [0, 1], kep);
  return (
    <div style={{opacity: op, transform: `translateX(${x}px)`}}>
      <Img src={src(anh)} style={{height: cao, width: 'auto', display: 'block'}} />
    </div>
  );
};

const SoDoSau = ({so, donVi, co}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 14, mass: 0.7}});
  const sc = interpolate(s, [0, 1], [0.62, 1]);
  const op = interpolate(f, [0, 8], [0, 1], kep);
  return (
    <div style={{transform: `scale(${sc})`, opacity: op, transformOrigin: 'left center'}}>
      <SoDem so={so} don_vi={donVi} giay={1.2} co={co} />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0e12'}}>
      <Interactive.Div
        name="Ảnh bờ kè bê tông bị nước lũ khoét sâu"
        from={4}
        durationInFrames={186}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhBoKe} tu={1.02} den={1.16} goc="50% 55%" toi={0.1} />
      </Interactive.Div>

      <Interactive.Div
        name="Vòng khoanh vùng bờ kè bị xói"
        from={12}
        durationInFrames={178}
        style={{position: 'absolute', left: props.xVong, top: props.yVong}}
      >
        <LopVongXoi w={props.wVong} h={props.hVong} />
      </Interactive.Div>

      <Interactive.Div
        name="Ảnh bản vẽ kỹ thuật phương án gia cố"
        from={184}
        durationInFrames={40}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhBanVe} tu={1.0} den={1.12} goc="55% 45%" toi={0.08} />
      </Interactive.Div>

      <Interactive.Div
        name="Sơ đồ cắt lớp mỏ neo thép"
        from={217}
        durationInFrames={108}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhSoDo} tu={1.14} den={1.0} goc="50% 50%" toi={0.06} />
      </Interactive.Div>

      <Interactive.Div
        name="Thước đo chiều sâu mỏ neo"
        from={283}
        durationInFrames={42}
        style={{position: 'absolute', left: props.xThuoc, top: props.yThuoc}}
      >
        <LopThuocDo anh={props.anhThuocDo} cao={props.coThuoc} />
      </Interactive.Div>

      <Interactive.Div
        name="Số độ sâu 3 mét"
        from={283}
        durationInFrames={42}
        style={{position: 'absolute', left: props.xSo, top: props.ySo}}
      >
        <SoDoSau so={props.doSau} donVi={props.donVi} co={props.coSo} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
