import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền bãi lốp xe sa mạc Arizona 1996'),
  anhLich: z.string().describe('Ảnh cắt bìa kẹp lịch công tác dã chiến'),
  anhChiHuy: z.string().describe('Ảnh cắt thợ Minyard và Giáo sư Honig'),
  anhTinhNguyen: z.string().describe('Ảnh cắt nhóm tình nguyện viên'),
  anhCongIch: z.string().describe('Ảnh cắt nhóm lao động công ích'),
  anhLenhToa: z.string().describe('Ảnh cắt lệnh tòa án quận có mộc đỏ'),
  phongNen: z.number().describe('Độ phóng của ảnh nền ở cuối cảnh'),
  toiNen: z.number().describe('Độ tối phủ lên ảnh nền (0-0.5)'),
  gocNen: z.string().describe('Gốc phóng của ảnh nền'),
  rongLich: z.number().describe('Chiều rộng thẻ lịch công tác (px)'),
  caoLich: z.number().describe('Chiều cao thẻ lịch công tác (px)'),
  rongChiHuy: z.number().describe('Chiều rộng cụm Minyard - Honig (px)'),
  caoChiHuy: z.number().describe('Chiều cao cụm Minyard - Honig (px)'),
  rongTinhNguyen: z.number().describe('Chiều rộng thẻ tình nguyện viên (px)'),
  caoTinhNguyen: z.number().describe('Chiều cao thẻ tình nguyện viên (px)'),
  rongCongIch: z.number().describe('Chiều rộng thẻ lao động công ích (px)'),
  caoLenhToa: z.number().describe('Chiều cao lệnh tòa án (px)'),
  rongLenhToa: z.number().describe('Chiều rộng lệnh tòa án (px)'),
  pushCuoi: z.number().describe('Hệ số siết tiêu cự ở beat cuối'),
  bienDoTroi: z.number().describe('Biên độ trôi chậm của các thẻ (px)'),
});

/* ---------- thẻ ảnh cắt lớp trượt vào ---------- */
const TheAnh = ({anh, rong, cao, tuX, tuY, xoayVao, xoayRa, tre, bienDo, dai}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 19, mass: 0.95, stiffness: 85}});
  const x = interpolate(vao, [0, 1], [tuX, 0]);
  const y = interpolate(vao, [0, 1], [tuY, 0]);
  const rot = interpolate(vao, [0, 1], [xoayVao, xoayRa]);
  const troi = Math.sin((f + tre) / 58) * bienDo;
  const phong = interpolate(f, [0, dai], [1, 1.035], kep);
  return (
    <div
      style={{
        width: rong,
        height: cao,
        transform: `translate(${x + troi}px, ${y}px) rotate(${rot}deg) scale(${phong})`,
        opacity: interpolate(vao, [0, 1], [0, 1], kep),
        filter: 'drop-shadow(0 20px 34px rgba(0,0,0,0.45))',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

/* ---------- lệnh tòa án ghim vào bố cục ---------- */
const LenhToa = ({anh, rong, cao, tre, bienDo, dai}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vao = spring({frame: f, fps, config: {damping: 14, mass: 0.7, stiffness: 120}});
  const sc = interpolate(vao, [0, 1], [0.55, 1]);
  const rot = interpolate(vao, [0, 1], [-14, -4.5]);
  const troi = Math.sin((f + tre) / 50) * bienDo * 0.75;
  const phong = interpolate(f, [0, dai], [1, 1.045], kep);
  return (
    <div
      style={{
        width: rong,
        height: cao,
        transform: `translate(${troi}px, 0px) rotate(${rot}deg) scale(${sc * phong})`,
        opacity: interpolate(vao, [0, 1], [0, 1], kep),
        filter: 'drop-shadow(0 24px 40px rgba(0,0,0,0.5))',
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // camera siết nhẹ tiêu cự từ beat cuối (frame 242) tới hết cảnh
  const push = interpolate(frame, [242, durationInFrames], [1, props.pushCuoi], {
    easing: Easing.inOut(Easing.quad),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#20180c', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${push})`, transformOrigin: '48% 56%'}}>

        {/* NỀN: bãi công trường lốp xe Arizona 1996 — trôi chậm suốt cảnh */}
        <Interactive.Div
          name="Nền bãi lốp Arizona 1996"
          from={0}
          durationInFrames={326}
          style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
        >
          <AnhNen
            anh={props.anhNen}
            tu={1}
            den={props.phongNen}
            goc={props.gocNen}
            toi={props.toiNen}
          />
        </Interactive.Div>

        {/* BEAT 1 — frame 4: bìa kẹp lịch công tác dã chiến (thứ Bảy / Chủ Nhật) */}
        <Interactive.Div
          name="Bìa kẹp lịch công tác dã chiến"
          from={4}
          durationInFrames={322}
          style={{position: 'absolute', left: 1430, top: 180}}
        >
          <TheAnh
            anh={props.anhLich}
            rong={props.rongLich}
            cao={props.caoLich}
            tuX={520}
            tuY={-40}
            xoayVao={9}
            xoayRa={-2.5}
            tre={0}
            bienDo={props.bienDoTroi}
            dai={322}
          />
        </Interactive.Div>

        {/* BEAT 2 — frame 76: Minyard & Giáo sư Honig trượt vào giữa bên trái bìa lịch */}
        <Interactive.Div
          name="Cụm Minyard và Giáo sư Honig"
          from={76}
          durationInFrames={250}
          style={{position: 'absolute', left: 140, top: 250}}
        >
          <TheAnh
            anh={props.anhChiHuy}
            rong={props.rongChiHuy}
            cao={props.caoChiHuy}
            tuX={-540}
            tuY={20}
            xoayVao={-7}
            xoayRa={1.5}
            tre={17}
            bienDo={props.bienDoTroi}
            dai={250}
          />
        </Interactive.Div>

        {/* BEAT 3 — frame 155: nhóm tình nguyện viên, mở rộng đội hình phía sau */}
        <Interactive.Div
          name="Nhóm tình nguyện viên"
          from={155}
          durationInFrames={171}
          style={{position: 'absolute', left: 880, top: 90}}
        >
          <TheAnh
            anh={props.anhTinhNguyen}
            rong={props.rongTinhNguyen}
            cao={props.caoTinhNguyen}
            tuX={150}
            tuY={70}
            xoayVao={7}
            xoayRa={-1.5}
            tre={31}
            bienDo={props.bienDoTroi}
            dai={171}
          />
        </Interactive.Div>

        {/* BEAT 4 — frame 242: nhóm lao động công ích ở góc tiền cảnh đối trọng */}
        <Interactive.Div
          name="Nhóm lao động công ích"
          from={242}
          durationInFrames={84}
          style={{position: 'absolute', left: 50, top: 600}}
        >
          <TheAnh
            anh={props.anhCongIch}
            rong={props.rongCongIch}
            cao={props.caoCongIch}
            tuX={-200}
            tuY={150}
            xoayVao={-8}
            xoayRa={1}
            tre={47}
            bienDo={props.bienDoTroi}
            dai={84}
          />
        </Interactive.Div>

        {/* BEAT 4b — frame 274: lệnh tòa án quận có mộc đỏ ghim cạnh nhóm */}
        <Interactive.Div
          name="Lệnh tòa án quận có mộc đỏ"
          from={274}
          durationInFrames={52}
          style={{position: 'absolute', left: 780, top: 470}}
        >
          <LenhToa
            anh={props.anhLenhToa}
            rong={props.rongLenhToa}
            cao={props.caoLenhToa}
            tre={61}
            bienDo={props.bienDoTroi}
            dai={52}
          />
        </Interactive.Div>

      </AbsoluteFill>
    </AbsoluteFill>
  );
};
