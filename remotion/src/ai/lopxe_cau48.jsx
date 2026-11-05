import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Ảnh nền hàng lốp xe xếp chặt dưới đáy hố móng'),
  anh_coc: z.string().describe('Ảnh cọc thép ghim xuống (PNG nền trong)'),
  bg_tu: z.number().describe('Độ phóng to đầu của ảnh nền'),
  bg_den: z.number().describe('Độ phóng to cuối của ảnh nền'),
  bg_goc: z.string().describe('Gốc phóng to của ảnh nền'),
  coc_w: z.number().describe('Chiều rộng cụm cọc thép'),
  coc_h: z.number().describe('Chiều cao cụm cọc thép'),
  coc_roi_tu: z.number().describe('Độ cao cọc thép rơi xuống (px)'),
  beat_coc: z.number().describe('Frame bắt đầu beat cọc thép ghim xuống'),
  beat_do: z.number().describe('Frame bắt đầu vẽ thước đo 0.5m'),
  thu_x: z.number().describe('Toạ độ ngang của thước đo'),
  thu_tren: z.number().describe('Toạ độ đỉnh thước đo'),
  thu_duoi: z.number().describe('Toạ độ đáy thước đo'),
  so_do: z.string().describe('Số liệu chiều dài hiển thị'),
  co_so: z.number().describe('Cỡ chữ số liệu'),
  mau: z.string().describe('Màu nhấn của thước và số liệu'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // ---- Beat 1 (frame 3): hàng lốp dưới đáy móng (nền chạy suốt cảnh) ----
  // ---- Beat 2 (frame 79): cọc thép ghim xuống + số liệu 0.5m ----

  // cọc thép rơi/ghim xuống
  const cocRoi = spring({
    frame: Math.max(0, frame - props.beat_coc),
    fps,
    config: {damping: 18, mass: 1, stiffness: 80},
  });
  const cocY = interpolate(cocRoi, [0, 1], [-props.coc_roi_tu, 0]);
  const cocMo = interpolate(frame, [props.beat_coc, props.beat_coc + 5], [0, 1], kep);
  // trôi chậm sau khi cắm xuống để khung hình luôn động
  const cocTruot = interpolate(frame, [props.beat_coc, durationInFrames], [0, -16], kep);
  const cocPhong = interpolate(frame, [props.beat_coc, durationInFrames], [1, 1.045], kep);

  // thước đo vẽ dần
  const ve = interpolate(frame, [props.beat_do, props.beat_do + 22], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const muiTenHien = interpolate(frame, [props.beat_do + 16, props.beat_do + 26], [0, 1], kep);
  const soNo = spring({
    frame: Math.max(0, frame - (props.beat_do + 14)),
    fps,
    config: {damping: 14, stiffness: 150, mass: 0.7},
  });
  const soPhong = interpolate(soNo, [0, 1], [0.55, 1]);
  const soMo = interpolate(frame, [props.beat_do + 14, props.beat_do + 20], [0, 1], kep);

  const yGiua = (props.thu_tren + props.thu_duoi) / 2;
  const nua = (props.thu_duoi - props.thu_tren) / 2;
  const x = props.thu_x;

  return (
    <AbsoluteFill style={{backgroundColor: '#0d0f10'}}>
      {/* Nền: hàng lốp xe dưới đáy hố móng */}
      <Interactive.Div
        name="Nền hàng lốp dưới đáy hố móng"
        from={0}
        durationInFrames={166}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anh_nen} tu={props.bg_tu} den={props.bg_den} goc={props.bg_goc} toi={0.16} />
      </Interactive.Div>

      {/* Cọc thép ghim xuyên qua lốp */}
      <Interactive.Div
        name="Cọc thép ghim xuống đáy"
        from={79}
        durationInFrames={87}
        style={{position: 'absolute', left: 480, top: 380}}
      >
        <div
          style={{
            width: props.coc_w,
            height: props.coc_h,
            transform: `translateY(${cocY + cocTruot}px) scale(${cocPhong})`,
            transformOrigin: '50% 70%',
            opacity: cocMo,
          }}
        >
          <Img
            src={src(props.anh_coc)}
            name="Cọc thép"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              filter: 'drop-shadow(0 26px 34px rgba(0,0,0,0.5))',
            }}
          />
        </div>
      </Interactive.Div>

      {/* Thước đo chiều dài + số liệu 0.5m */}
      <Interactive.Div
        name="Thước đo 0.5m"
        from={79}
        durationInFrames={87}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
          <line
            x1={x}
            y1={yGiua}
            x2={x}
            y2={props.thu_tren}
            stroke={props.mau}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={nua}
            strokeDashoffset={nua * (1 - ve)}
          />
          <line
            x1={x}
            y1={yGiua}
            x2={x}
            y2={props.thu_duoi}
            stroke={props.mau}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={nua}
            strokeDashoffset={nua * (1 - ve)}
          />
          <g opacity={muiTenHien}>
            <polygon
              points={`${x},${props.thu_tren - 24} ${x - 17},${props.thu_tren + 8} ${x + 17},${props.thu_tren + 8}`}
              fill={props.mau}
            />
            <polygon
              points={`${x},${props.thu_duoi + 24} ${x - 17},${props.thu_duoi - 8} ${x + 17},${props.thu_duoi - 8}`}
              fill={props.mau}
            />
          </g>
          <g
            transform={`translate(${x + 48}, ${yGiua}) scale(${soPhong})`}
            opacity={soMo}
            style={{transformOrigin: `${x + 48}px ${yGiua}px`}}
          >
            <text
              x={0}
              y={0}
              dominantBaseline="central"
              fontFamily={FONT}
              fontSize={props.co_so}
              fontWeight={900}
              fill={props.mau}
              stroke="rgba(8,10,12,0.85)"
              strokeWidth={13}
              paintOrder="stroke"
            >
              {props.so_do}
            </text>
          </g>
        </svg>
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
