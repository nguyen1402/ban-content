import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhMatCat: z.string().describe('Ảnh nền mặt cắt địa tầng (đồng cỏ + lòng đất)'),
  anhRe: z.string().describe('Ảnh tách nền lớp rễ cây đan xen'),
  anhNuocNham: z.string().describe('Ảnh tầng sỏi đá ngậm nước ngầm'),
  zoomNenTu: z.number().describe('Độ phóng ảnh mặt cắt lúc mở đầu'),
  zoomNenDen: z.number().describe('Độ phóng ảnh mặt cắt lúc kết thúc'),
  toiNen: z.number().describe('Độ tối của ảnh mặt cắt (0..0.5)'),
  reRong: z.number().describe('Chiều rộng lớp rễ cây (px)'),
  zoomNuocTu: z.number().describe('Độ phóng ảnh nước ngầm lúc bắt đầu'),
  zoomNuocDen: z.number().describe('Độ phóng ảnh nước ngầm lúc kết thúc'),
  sangOp: z.number().describe('Độ đậm dải sáng ngầm (0..1)'),
});

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const Canh = ({
  anhMatCat,
  anhRe,
  anhNuocNham,
  zoomNenTu,
  zoomNenDen,
  toiNen,
  reRong,
  zoomNuocTu,
  zoomNuocDen,
  sangOp,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const cuoi = durationInFrames - 1; // 170

  // --- Camera hạ xuống: ảnh mặt cắt trôi lên rất chậm suốt cả cảnh ---
  const panNen = interpolate(frame, [0, cuoi], [55, -55], CL);

  // --- Lớp rễ cây: parallax nhanh hơn, trôi lên và biến mất dần khi camera xuống sâu ---
  const rePan = interpolate(frame, [2, cuoi], [90, -380], CL);
  const reOp = interpolate(frame, [2, 20], [0, 1], CL);
  const reZoom = interpolate(frame, [2, cuoi], [1, 1.07], CL);

  // --- Tầng ngậm nước ngầm trượt lên từ dưới đáy khung (beat 2 = frame 83) ---
  const nuocY = interpolate(frame, [83, 109], [1080, 0], {...CL, easing: Easing.out(Easing.cubic)});
  const nuocMem = interpolate(frame, [83, 109], [170, 0], CL);

  // --- Dải sáng ngầm trôi ngang, làm bừng sáng độ ẩm trong sỏi đá ---
  const sangX = interpolate(frame, [100, cuoi], [-1100, 250], {...CL, easing: Easing.inOut(Easing.sin)});
  const sangA = interpolate(frame, [100, 124], [0, sangOp], CL);

  return (
    <AbsoluteFill style={{backgroundColor: '#151009', overflow: 'hidden'}}>
      {/* NỀN: mặt cắt địa tầng, luôn phủ kín khung */}
      <Interactive.Div
        name="Mặt cắt địa tầng"
        from={0}
        durationInFrames={171}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateY(${panNen}px)`,
          }}
        >
          <AnhNen anh={anhMatCat} tu={zoomNenTu} den={zoomNenDen} goc="50% 42%" toi={toiNen} />
        </div>
      </Interactive.Div>

      {/* LỚP RỄ CÂY ĐAN CÀI (tách nền) */}
      <Interactive.Div
        name="Lớp rễ cây đan xen"
        from={2}
        durationInFrames={169}
        style={{position: 'absolute', left: 260, top: 200}}
      >
        <div
          style={{
            opacity: reOp,
            transform: `translateY(${rePan}px) scale(${reZoom})`,
            transformOrigin: '50% 50%',
          }}
        >
          <Img
            src={src(anhRe)}
            style={{width: reRong, height: 'auto', display: 'block'}}
          />
        </div>
      </Interactive.Div>

      {/* TẦNG NGẬM NƯỚC NGẦM trượt lên phủ kín khung */}
      <Interactive.Div
        name="Tầng ngậm nước ngầm"
        from={83}
        durationInFrames={88}
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
            transform: `translateY(${nuocY}px)`,
            maskImage: `linear-gradient(to bottom, rgba(0,0,0,0) 0px, rgba(0,0,0,1) ${nuocMem}px)`,
            WebkitMaskImage: `linear-gradient(to bottom, rgba(0,0,0,0) 0px, rgba(0,0,0,1) ${nuocMem}px)`,
          }}
        >
          <AnhNen anh={anhNuocNham} tu={zoomNuocTu} den={zoomNuocDen} goc="50% 55%" toi={0.04} />
        </div>
      </Interactive.Div>

      {/* DẢI SÁNG NGẦM trong tầng sỏi ẩm */}
      <Interactive.Div
        name="Dải sáng ngầm"
        from={100}
        durationInFrames={71}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: sangX,
            top: 300,
            width: 2400,
            height: 620,
            transform: 'rotate(-14deg)',
            opacity: sangA,
            mixBlendMode: 'screen',
            background:
              'linear-gradient(90deg, rgba(255,241,205,0) 0%, rgba(255,241,205,0.42) 42%, rgba(255,247,222,0.62) 55%, rgba(255,241,205,0) 100%)',
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
