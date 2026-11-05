import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {kep, FONT, AnhNen, SoDem} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh đáy biển u tối ngập lốp xe (quy mô)'),
  anhCan: z.string().describe('Ảnh cận cảnh đai nhựa và khóa thép'),
  soTrieu: z.string().describe('Dải số lượng lốp xe phế thải'),
  doSau: z.number().describe('Độ sâu đáy biển (m)'),
  giayDem: z.number().describe('Số giây chạy số đếm độ sâu'),
  coSoTrieu: z.number().describe('Cỡ chữ dải số lượng'),
  coDoSau: z.number().describe('Cỡ chữ số đếm độ sâu'),
  mauChu: z.string().describe('Màu chữ chính'),
  doToiNen: z.number().describe('Độ tối ảnh đáy biển (0..0.5)'),
  doToiCan: z.number().describe('Độ tối ảnh cận cảnh (0..0.5)'),
});

const D = {
  anhNen: 'nhan_y/ed31998679f14d.jpg',
  anhCan: 'nhan_y/c4581493a70f14.jpg',
  soTrieu: '1.000.000 – 2.000.000',
  doSau: 20,
  giayDem: 4.6,
  coSoTrieu: 104,
  coDoSau: 150,
  mauChu: '#F2EAD8',
  doToiNen: 0.3,
  doToiCan: 0.12,
};

export const Canh = ({
  anhNen,
  anhCan,
  soTrieu,
  doSau,
  giayDem,
  coSoTrieu,
  coDoSau,
  mauChu,
  doToiNen,
  doToiCan,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Nhịp 1 — dải số lượng bung ra rồi chìm dần xuống
  const bung = spring({frame: frame - 2, fps, config: {damping: 200, mass: 0.6}, durationInFrames: 24});
  const chim = interpolate(frame, [56, 134], [0, 1], {...kep, easing: Easing.in(Easing.quad)});
  const soMo = interpolate(chim, [0, 1], [1, 0], kep);

  // Nhịp 2 — chuyển mượt sang cận cảnh
  const hien = interpolate(frame, [162, 178], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});

  return (
    <AbsoluteFill style={{backgroundColor: '#04121a'}}>
      {/* NHỊP 1 — đáy biển u tối, camera hạ xuống */}
      <Interactive.Div
        name="Đáy biển lốp xe (quy mô)"
        from={0}
        durationInFrames={182}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anhNen} tu={1.0} den={1.12} goc="50% 42%" toi={doToiNen} />
      </Interactive.Div>

      {/* Dải số lượng 1 - 2 triệu, chìm dần xuống */}
      <Interactive.Div
        name="Dải số lượng lốp xe"
        from={2}
        durationInFrames={140}
        style={{position: 'absolute', left: 330, top: 360, width: 1260}}
      >
        <div
          style={{
            width: 1260,
            textAlign: 'center',
            fontFamily: FONT,
            fontWeight: 800,
            fontSize: coSoTrieu,
            letterSpacing: '2px',
            color: mauChu,
            textShadow: '0 8px 34px rgba(0,0,0,0.8)',
            opacity: soMo,
            transform: `translateY(${chim * 92}px) scale(${0.94 + 0.06 * bung})`,
            whiteSpace: 'nowrap',
          }}
        >
          {soTrieu}
        </div>
      </Interactive.Div>

      {/* Thước đo độ sâu hạ từ 0m chạm mốc 20m */}
      <Interactive.Div
        name="Số đếm độ sâu"
        from={2}
        durationInFrames={160}
        style={{position: 'absolute', left: 1370, top: 700}}
      >
        <div
          style={{
            fontFamily: FONT,
            color: mauChu,
            textShadow: '0 6px 26px rgba(0,0,0,0.8)',
            opacity: interpolate(frame, [2, 14], [0, 1], kep),
          }}
        >
          <SoDem so={doSau} don_vi="m" giay={giayDem} co={coDoSau} />
        </div>
      </Interactive.Div>

      {/* NHỊP 2 — cận cảnh đai nhựa và khóa thép */}
      <Interactive.Div
        name="Cận cảnh đai nhựa và khóa thép"
        from={162}
        durationInFrames={104}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: hien}}>
          <AnhNen anh={anhCan} tu={1.1} den={1.0} goc="50% 50%" toi={doToiCan} />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
