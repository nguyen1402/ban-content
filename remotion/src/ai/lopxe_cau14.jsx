import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen1: z.string().describe('Ảnh nền top-down dòng lũ bùn đỏ cuộn xiết trong rãnh đất'),
  anhDatSut: z.string().describe('Ảnh cắt vách đất sụt lở trượt xuống lòng rãnh'),
  anhNen2: z.string().describe('Ảnh nền flycam toàn cảnh rãnh xói kéo dài về chân núi'),
  mauDuong: z.string().describe('Màu nét đồ họa vàng cam vẽ ngược dòng'),
  dayNet: z.number().describe('Độ dày nét đồ họa (px)'),
  quangTruotNgang: z.number().describe('Quãng trượt ngang của vách đất vào lòng rãnh (px)'),
  quangTruotDoc: z.number().describe('Quãng trượt xuống của vách đất (px)'),
  rongDat: z.number().describe('Chiều rộng khối vách đất (px)'),
  caoDat: z.number().describe('Chiều cao khối vách đất (px)'),
  toiNen1: z.number().describe('Độ tối nền beat 1 (0..0.5)'),
  toiNen2: z.number().describe('Độ tối nền beat 2 (0..0.5)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- BEAT 1 : khối đất trượt vào lòng rãnh (bắt đầu frame 66) ---------- */
  const fDat = frame - 50; // local frame của khối vách đất
  const tien = interpolate(fDat, [16, 40], [0, 1], {
    ...kep,
    easing: Easing.bezier(0.45, 0, 0.25, 1),
  });
  const datX = interpolate(tien, [0, 1], [0, -props.quangTruotNgang]);
  const datY = interpolate(tien, [0, 1], [-34, props.quangTruotDoc]);
  const datRot = interpolate(tien, [0, 1], [0, -6]);
  const datScale = interpolate(tien, [0, 1], [1, 0.93]);

  /* ---------- BEAT 2 : hòa tan sang toàn cảnh đầu nguồn (frame 94) ---------- */
  const f2 = frame - 92; // local frame của beat 2
  const doDam2 = interpolate(f2, [0, 12], [0, 1], kep);

  /* ---------- Nét đồ họa vẽ ngược về đầu nguồn ---------- */
  const fLine = frame - 94;
  const ve = interpolate(fLine, [0, 46], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const hCat = ve * 1080;
  const netMo = interpolate(fLine, [0, 6], [0, 1], kep);

  const duongDan =
    'M 1210 1010 C 1160 880 1080 860 990 800 C 880 730 850 640 930 565 C 1000 495 900 430 845 355 C 800 295 830 245 862 190';

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {/* ================= NỀN BEAT 1 ================= */}
      <Interactive.Div
        name="Nền top-down rãnh lũ bùn đỏ"
        from={0}
        durationInFrames={104}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia
          anh={props.anhNen1}
          huong="xuong"
          quang={130}
          phong={1.08}
          toi={props.toiNen1}
        />
      </Interactive.Div>

      {/* ================= KHỐI VÁCH ĐẤT SỤT LỞ ================= */}
      <Interactive.Div
        name="Vách đất sụt trượt vào lòng dòng chảy"
        from={50}
        durationInFrames={54}
        style={{position: 'absolute', left: 1130, top: 150, width: props.rongDat, height: props.caoDat}}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            transform: `translate(${datX}px, ${datY}px) rotate(${datRot}deg) scale(${datScale})`,
            transformOrigin: '50% 50%',
          }}
        >
          <Img
            src={src(props.anhDatSut)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      {/* ================= NỀN BEAT 2 : TOÀN CẢNH ĐẦU NGUỒN ================= */}
      <Interactive.Div
        name="Toàn cảnh rãnh xói về chân núi"
        from={92}
        durationInFrames={73}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div style={{width: '100%', height: '100%', opacity: doDam2}}>
          <AnhNen
            anh={props.anhNen2}
            tu={1}
            den={1.1}
            goc="50% 22%"
            toi={props.toiNen2}
          />
        </div>
      </Interactive.Div>

      {/* ================= NÉT ĐỒ HỌA VẼ NGƯỢC DÒNG ================= */}
      <Interactive.Div
        name="Nét đồ họa gặm ngược về đầu nguồn"
        from={94}
        durationInFrames={71}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg
          width={1920}
          height={1080}
          viewBox="0 0 1920 1080"
          style={{position: 'absolute', left: 0, top: 0}}
        >
          <defs>
            <clipPath id="lo-xoi-nguoc">
              <rect x={0} y={1080 - hCat} width={1920} height={hCat} />
            </clipPath>
          </defs>
          <g clipPath="url(#lo-xoi-nguoc)" opacity={netMo}>
            <path
              d={duongDan}
              fill="none"
              stroke={props.mauDuong}
              strokeWidth={props.dayNet}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="28 18"
            />
          </g>
        </svg>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
