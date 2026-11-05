import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, VANG, AnhNen, Nhan} from './thu_vien.jsx';

export const schema = z.object({
  anhBanDo: z.string().describe('Ảnh bản đồ vệ tinh làm nền xuyên suốt'),
  anhKenh: z.string().describe('Ảnh cận cảnh lòng sông cạn (khung inset)'),
  anhVuc: z.string().describe('Ảnh tách nền vách vực xói mòn'),
  anhNha: z.string().describe('Ảnh ngôi nhà đơn sơ bên mép vực'),
  tenSong1: z.string().describe('Nhãn sông Santa Cruz (nhãn duy nhất trên màn hình)'),
  mauDuong: z.string().describe('Màu nét vẽ đường sông'),
  mauNhan: z.string().describe('Màu chữ nhãn sông'),
  coNhan: z.number().describe('Cỡ chữ nhãn sông (px)'),
  dayNet: z.number().describe('Độ dày nét sông (px)'),
  zoomNenTu: z.number().describe('Tỉ lệ zoom bản đồ lúc bắt đầu'),
  zoomNenDen: z.number().describe('Tỉ lệ zoom bản đồ lúc kết thúc'),
  zoomNhaTu: z.number().describe('Tỉ lệ zoom ngôi nhà lúc bắt đầu'),
  zoomNhaDen: z.number().describe('Tỉ lệ zoom ngôi nhà lúc kết thúc'),
  doMoNen: z.number().describe('Độ tối phủ lên nền khi đưa vách vực vào'),
});

const C = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- BEAT 1: các đường sông vẽ dần trên bản đồ ---------- */
  const pSC = interpolate(frame, [6, 42], [0, 1], {...C, easing: Easing.inOut(Easing.cubic)});
  const pRI = interpolate(frame, [49, 85], [0, 1], {...C, easing: Easing.inOut(Easing.cubic)});
  const pAW = interpolate(frame, [138, 168], [0, 1], {...C, easing: Easing.inOut(Easing.cubic)});

  const opSC = interpolate(frame, [30, 44], [0, 1], C);

  /* ---------- BEAT 2 (frame 163): khung inset lòng sông cạn trượt vào ---------- */
  const kF = frame - 163;
  const slide = spring({frame: kF, fps, config: {damping: 200, stiffness: 90, mass: 0.9}, durationInFrames: 22});
  const txIn = interpolate(slide, [0, 1], [1150, 0]);
  const opInset = interpolate(kF, [0, 9], [0, 1], C);
  const toCorner = interpolate(kF, [45, 60], [0, 1], {...C, easing: Easing.inOut(Easing.cubic)});
  const tx = txIn + toCorner * 490;
  const ty = toCorner * -220;
  const scInset = 1 - toCorner * 0.53;
  const zoomInset = 1.05 + 0.07 * interpolate(kF, [0, 112], [0, 1], C);

  /* ---------- BEAT 3 (frame 208): vách vực xói mòn bật lên giữa khung ---------- */
  const vF = frame - 208;
  const pop = spring({frame: vF, fps, config: {damping: 15, stiffness: 110, mass: 0.8}, durationInFrames: 26});
  const vScale = interpolate(pop, [0, 1], [1.24, 1]);
  const vOp = interpolate(vF, [0, 8], [0, 1], C);
  const vDrift = interpolate(vF, [0, 58], [0, -20], C);

  /* ---------- lớp làm dịu nền khi đưa vách vực vào ---------- */
  const dimOp = interpolate(frame, [206, 222], [0, props.doMoNen], C);

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0f14'}}>
      {/* ===== NỀN: bản đồ vệ tinh toàn khu vực ===== */}
      <Interactive.Div
        name="Bản đồ vệ tinh nền"
        from={0}
        durationInFrames={382}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhBanDo} tu={props.zoomNenTu} den={props.zoomNenDen} goc="50% 50%" toi={0.16} />
      </Interactive.Div>

      {/* ===== Đường vector sông Santa Cruz ===== */}
      <Interactive.Div
        name="Đường sông Santa Cruz"
        from={6}
        durationInFrames={376}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
          <path
            d="M 120 190 C 480 300 780 470 1420 730"
            fill="none"
            stroke={props.mauDuong}
            strokeWidth={props.dayNet}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1"
            strokeDashoffset={1 - pSC}
          />
        </svg>
      </Interactive.Div>

      {/* ===== Đường vector sông Rillito ===== */}
      <Interactive.Div
        name="Đường sông Rillito"
        from={49}
        durationInFrames={333}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
          <path
            d="M 140 640 C 480 580 820 620 1240 470"
            fill="none"
            stroke={props.mauDuong}
            strokeWidth={props.dayNet}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1"
            strokeDashoffset={1 - pRI}
          />
        </svg>
      </Interactive.Div>

      {/* ===== Đường vector lòng suối Altar Wash ===== */}
      <Interactive.Div
        name="Đường suối Altar Wash"
        from={138}
        durationInFrames={244}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
          <path
            d="M 1800 240 C 1600 460 1360 600 1080 800"
            fill="none"
            stroke={props.mauDuong}
            strokeWidth={props.dayNet}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray="1"
            strokeDashoffset={1 - pAW}
          />
        </svg>
      </Interactive.Div>

      {/* ===== Nhãn sông Santa Cruz (chỉ giữ MỘT text ngắn) ===== */}
      <Interactive.Div
        name="Nhãn sông Santa Cruz"
        from={30}
        durationInFrames={352}
        style={{position: 'absolute', left: 740, top: 430}}
      >
        <div style={{opacity: opSC, color: props.mauNhan}}>
          <Nhan chu={props.tenSong1} dx={70} dy={-100} co={props.coNhan} />
        </div>
      </Interactive.Div>

      {/* ===== Lớp làm dịu nền trước khi đưa vách vực vào giữa ===== */}
      <Interactive.Div
        name="Lớp làm dịu nền"
        from={206}
        durationInFrames={60}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div style={{width: '100%', height: '100%', backgroundColor: '#0a1018', opacity: dimOp}} />
      </Interactive.Div>

      {/* ===== BEAT 2: khung inset lòng sông cạn (trượt vào góc phải rồi thu nhỏ) ===== */}
      <Interactive.Div
        name="Khung cận cảnh lòng sông cạn"
        from={163}
        durationInFrames={112}
        style={{position: 'absolute', left: 940, top: 320}}
      >
        <div
          style={{
            width: 900,
            height: 506,
            transformOrigin: '0 0',
            transform: `translate(${tx}px, ${ty}px) scale(${scInset})`,
            opacity: opInset,
          }}
        >
          <div
            style={{
              width: '100%',
              height: '100%',
              boxSizing: 'border-box',
              overflow: 'hidden',
              border: `4px solid ${VANG}`,
              boxShadow: '0 26px 60px rgba(0,0,0,0.45)',
            }}
          >
            <Img
              name="Lòng sông cạn"
              src={src(props.anhKenh)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: `scale(${zoomInset})`,
                transformOrigin: '50% 50%',
              }}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* ===== BEAT 3: mặt cắt vách vực xói mòn dựng đứng giữa khung ===== */}
      <Interactive.Div
        name="Vách vực xói mòn"
        from={208}
        durationInFrames={58}
        style={{position: 'absolute', left: 528, top: 230}}
      >
        <div
          style={{
            width: 865,
            height: 620,
            opacity: vOp,
            transform: `translateY(${vDrift}px) scale(${vScale})`,
            transformOrigin: '50% 60%',
          }}
        >
          <Img
            name="Mặt cắt vách vực"
            src={src(props.anhVuc)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      {/* ===== BEAT 4: toàn cảnh ngôi nhà bên mép vực, zoom chậm đến hết câu ===== */}
      <Interactive.Div
        name="Ngôi nhà bên mép vực"
        from={262}
        durationInFrames={120}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhNha} tu={props.zoomNhaTu} den={props.zoomNhaDen} goc="50% 58%" toi={0.08} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
