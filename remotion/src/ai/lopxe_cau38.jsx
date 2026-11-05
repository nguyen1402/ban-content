import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhDap: z.string().describe('Ảnh bản vẽ mặt cắt đập bê tông (nền)'),
  anhMach: z.string().describe('Ảnh giấy can sơ đồ mạch điện'),
  anhSuoi: z.string().describe('Ảnh dòng suối tự nhiên uốn lượn (nền)'),
  zoomDapTu: z.number().describe('Độ phóng bắt đầu của bản vẽ đập'),
  zoomDapDen: z.number().describe('Độ phóng kết thúc của bản vẽ đập'),
  zoomSuoiTu: z.number().describe('Độ phóng bắt đầu của dòng suối'),
  zoomSuoiDen: z.number().describe('Độ phóng kết thúc của dòng suối'),
  giayMo: z.number().describe('Độ đậm tối đa của tờ giấy can'),
  doToiDap: z.number().describe('Độ tối phủ lên bản vẽ đập'),
});

export const Canh = (props) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---- BEAT 1 (frame 3): bản vẽ đập bê tông, cú đẩy nhẹ vào ----
  const dapPunch = interpolate(f, [3, 38], [1.05, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  // ---- BEAT 2 (frame 79): tờ giấy can mạch điện trượt đè lên ----
  const vao = spring({frame: f - 79, fps, config: {damping: 200, mass: 1}, durationInFrames: 45});
  const giayDX = interpolate(vao, [0, 1], [300, 0]);
  const giayDY = interpolate(vao, [0, 1], [-130, 0]);
  const giayRot = interpolate(vao, [0, 1], [-3.4, 0]);
  const giayHien = interpolate(f, [79, 108], [0, 1], kep);
  const giayTruot = interpolate(f, [79, 135], [0, -22], kep);
  const giayTan = interpolate(f, [135, 166], [1, 0], {
    ...kep,
    easing: Easing.in(Easing.cubic),
  });
  const giayPhong = interpolate(f, [135, 170], [1, 1.12], kep);
  const giayOp = Math.min(giayHien, giayTan) * props.giayMo;

  // ---- BEAT 3 (frame 135): dòng suối tự nhiên quét vào, xoá bỏ khuôn hình học ----
  const wipe = interpolate(f, [135, 180], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const catSuoi = `inset(0% ${(1 - wipe) * 100}% 0% 0%)`;

  return (
    <AbsoluteFill style={{backgroundColor: '#0a1622', overflow: 'hidden'}}>
      {/* NỀN 1 — bản thiết kế đập bê tông */}
      <Interactive.Div
        name="Bản vẽ mặt cắt đập bê tông"
        from={0}
        durationInFrames={250}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            overflow: 'hidden',
            transform: `scale(${dapPunch})`,
          }}
        >
          <AnhNen
            anh={props.anhDap}
            tu={props.zoomDapTu}
            den={props.zoomDapDen}
            goc="50% 46%"
            toi={props.doToiDap}
          />
        </div>
      </Interactive.Div>

      {/* NỀN 2 — dòng suối tự nhiên quét vào từ trái */}
      <Interactive.Div
        name="Dòng suối tự nhiên"
        from={135}
        durationInFrames={115}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          clipPath: catSuoi,
        }}
      >
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}>
          <AnhNen
            anh={props.anhSuoi}
            tu={props.zoomSuoiTu}
            den={props.zoomSuoiDen}
            goc="46% 52%"
            toi={0}
          />
        </div>
      </Interactive.Div>

      {/* LỚP 3 — tờ giấy can sơ đồ mạch điện */}
      <Interactive.Div
        name="Giấy can sơ đồ mạch điện"
        from={79}
        durationInFrames={171}
        style={{position: 'absolute', left: 100, top: 56, width: 1720, height: 968}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1720,
            height: 968,
            opacity: giayOp,
            transform: `translate(${giayDX}px, ${giayDY + giayTruot}px) rotate(${giayRot}deg) scale(${giayPhong})`,
            boxShadow: '0 34px 90px rgba(0, 0, 0, 0.45)',
          }}
        >
          <Img
            src={src(props.anhMach)}
            style={{width: 1720, height: 968, objectFit: 'cover', display: 'block'}}
          />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
