import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, AnhNen, AnhLia} from './thu_vien.jsx';

export const schema = z.object({
  anhSuoi: z.string().describe('Ảnh nền toàn cảnh dòng suối'),
  anhNguoi: z.string().describe('Ảnh cắt người dân đang hoài nghi'),
  anhLopXe: z.string().describe('Ảnh hàng lốp xe xếp dọc lòng suối'),
  anhCat: z.string().describe('Ảnh cận lớp cát bồi tụ sau lốp xe'),
  quangPan: z.number().describe('Quãng trượt ngang của cảnh suối (px)'),
  phongSuoi: z.number().describe('Độ phóng ảnh dòng suối'),
  toiSuoi: z.number().describe('Độ tối ảnh dòng suối (0..0.5)'),
  lechCat: z.number().describe('Độ lệch ngang khi người dân trượt vào (px)'),
  xNguoi: z.number().describe('Toạ độ X của ảnh người dân'),
  yNguoi: z.number().describe('Toạ độ Y của ảnh người dân'),
  rongNguoi: z.number().describe('Chiều rộng ảnh người dân (px)'),
  caoNguoi: z.number().describe('Chiều cao ảnh người dân (px)'),
  zoomDau: z.number().describe('Tỉ lệ ảnh người dân lúc trượt vào'),
  zoomGiua: z.number().describe('Tỉ lệ ảnh người dân ngay trước khi thu nhỏ'),
  zoomCuoi: z.number().describe('Tỉ lệ ảnh người dân sau khi thu nhỏ'),
  punchDau: z.number().describe('Tỉ lệ punch-in lúc bắt đầu'),
  punchCuoi: z.number().describe('Tỉ lệ punch-in mạnh nhất'),
  banKinhCat: z.number().describe('Bán kính mặt nạ mở ra (px)'),
  quetRong: z.number().describe('Chiều rộng vệt sáng quét (px)'),
});

export const Canh = (props) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- Nhịp 2: người dân trượt vào (frame 41) ---------- */
  const vaoNguoi = spring({frame: f - 41, fps, config: {damping: 200, mass: 0.9}});
  const lechX = interpolate(vaoNguoi, [0, 1], [props.lechCat, 0]);

  /* ---------- Nhịp 3: thu nhỏ khung ảnh (frame 145) ---------- */
  const zoomNguoi = interpolate(
    f,
    [41, 145, 215],
    [props.zoomDau, props.zoomGiua, props.zoomCuoi],
    {...kep, easing: Easing.inOut(Easing.quad)}
  );

  /* ---------- Nhịp 4: quét sáng chuyển cảnh (frame 217) ---------- */
  const sweepX = interpolate(f, [217, 247], [-1000, 2200], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const sweepOp = interpolate(f, [217, 233, 247], [0.85, 0.85, 0], kep);

  /* ---------- Nhịp 5: punch-in + mở mặt nạ lớp cát (frame 299) ---------- */
  const punch = interpolate(
    f,
    [217, 299, 328, 389],
    [props.punchDau, props.punchDau, props.punchCuoi, props.punchCuoi + 0.09],
    {...kep, easing: Easing.inOut(Easing.cubic)}
  );
  const banKinh = interpolate(f, [299, 340], [0, props.banKinhCat], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const zoomCat = interpolate(f, [299, 389], [1.05, 0.98], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0e1216'}}>
      {/* Nhịp 1 – toàn cảnh dòng suối, camera dịch chậm sang phải */}
      <Interactive.Div
        name="Toàn cảnh dòng suối"
        from={0}
        durationInFrames={220}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <AnhLia
          anh={props.anhSuoi}
          huong="phai"
          quang={props.quangPan}
          phong={props.phongSuoi}
          toi={props.toiSuoi}
        />
      </Interactive.Div>

      {/* Nhịp 2 + 3 – nhóm người hoài nghi trượt vào rồi thu nhỏ */}
      <Interactive.Div
        name="Người dân hoài nghi"
        from={41}
        durationInFrames={176}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <Img
          src={src(props.anhNguoi)}
          style={{
            position: 'absolute',
            left: props.xNguoi,
            top: props.yNguoi,
            width: props.rongNguoi,
            height: props.caoNguoi,
            objectFit: 'contain',
            transform: `translateX(${lechX}px) scale(${zoomNguoi})`,
            transformOrigin: '50% 50%',
            filter: 'drop-shadow(0 22px 46px rgba(0,0,0,0.5))',
          }}
        />
      </Interactive.Div>

      {/* Nhịp 4 + 5 – hàng lốp xe, punch-in và mở mặt nạ lớp cát */}
      <Interactive.Div
        name="Hàng lốp xe chắn bùn"
        from={217}
        durationInFrames={172}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `scale(${punch})`,
            transformOrigin: '58% 56%',
          }}
        >
          <AnhNen anh={props.anhLopXe} tu={1.02} den={1.14} goc="50% 55%" toi={0.08} />
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              clipPath: `circle(${banKinh}px at 58% 56%)`,
              WebkitClipPath: `circle(${banKinh}px at 58% 56%)`,
            }}
          >
            <Img
              src={src(props.anhCat)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: `scale(${zoomCat})`,
                transformOrigin: '58% 56%',
              }}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* Nhịp 4 – vệt sáng quét chuyển cảnh */}
      <Interactive.Div
        name="Quét sáng chuyển cảnh"
        from={217}
        durationInFrames={30}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: -180,
            width: props.quetRong,
            height: 1440,
            background:
              'linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.45) 50%, rgba(255,255,255,0) 100%)',
            transform: `translateX(${sweepX}px) skewX(-14deg)`,
            opacity: sweepOp,
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
