import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {kep, AnhNen, VongBut, MuiTen} from './thu_vien.jsx';

export const schema = z.object({
  anhDiaHinh: z.string().describe('Ảnh nền toàn cảnh địa hình khô cạn'),
  anhCanDat: z.string().describe('Ảnh cận cảnh lớp đất ẩm giữ nước'),
  anhGioCat: z.string().describe('Ảnh vùng gió cát xói mòn'),
  toiNen: z.number().describe('Độ tối lớp phủ ảnh nền (0 đến 0.5)'),
  zoomDiaHinhTu: z.number().describe('Tỉ lệ zoom đầu của ảnh địa hình'),
  zoomDiaHinhDen: z.number().describe('Tỉ lệ zoom cuối của ảnh địa hình'),
  zoomDatAmTu: z.number().describe('Tỉ lệ zoom đầu của ảnh đất ẩm'),
  zoomDatAmDen: z.number().describe('Tỉ lệ zoom cuối của ảnh đất ẩm'),
  zoomGioCatTu: z.number().describe('Tỉ lệ zoom đầu của ảnh gió cát'),
  zoomGioCatDen: z.number().describe('Tỉ lệ zoom cuối của ảnh gió cát'),
  nhip2: z.number().describe('Frame bắt đầu nhịp 2 (trượt sang cận cảnh đất ẩm)'),
  nhip3: z.number().describe('Frame bắt đầu nhịp 3 (vùng gió cát được bảo vệ)'),
  doTruot: z.number().describe('Số frame trượt của hiệu ứng chuyển cảnh'),
  coVongNhip1: z.number().describe('Bề rộng vòng khoanh vùng cấu trúc ngầm'),
  coVongNhip2: z.number().describe('Bề rộng vòng khoanh vùng nước ngầm thấm'),
  coVongNhip3: z.number().describe('Bề rộng vòng khoanh vùng đất được bảo vệ'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();

  /* ---------- NHỊP 1: toàn cảnh địa hình khô cạn (frame 2) ---------- */
  const sc1 = interpolate(frame, [0, 110], [1, 1.07], kep);
  const op1 = interpolate(frame, [96, 108], [1, 0], kep);

  /* ---------- NHỊP 2: trượt sang cận cảnh đất ẩm (frame 83) ---------- */
  const f2 = frame - 83;
  const slide2 = interpolate(f2, [0, 24], [1920, 0], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const sc2 = interpolate(f2, [0, 122], [1, 1.08], kep);
  const op2 = interpolate(frame, [163, 178], [1, 0], kep);

  /* ---------- NHỊP 3: vùng gió cát được bảo vệ (frame 173) ---------- */
  const f3 = frame - 173;
  const slide3 = interpolate(f3, [0, 26], [1080, 0], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const sc3 = interpolate(f3, [0, 115], [1, 1.06], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#20180c'}}>
      {/* ============ NHỊP 1 — ẢNH NỀN ĐỊA HÌNH ============ */}
      <Interactive.Div
        name="Toàn cảnh địa hình khô cạn"
        from={0}
        durationInFrames={110}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `scale(${sc1})`,
            transformOrigin: '50% 55%',
          }}
        >
          <AnhNen
            anh={props.anhDiaHinh}
            tu={props.zoomDiaHinhTu}
            den={props.zoomDiaHinhDen}
            goc="50% 55%"
            toi={props.toiNen}
          />
        </div>
      </Interactive.Div>

      {/* Vòng khoanh vùng cấu trúc giữ nước trong lòng đất */}
      <Interactive.Div
        name="Vòng khoanh cấu trúc ngầm"
        from={2}
        durationInFrames={108}
        style={{position: 'absolute', left: 660, top: 420, opacity: op1}}
      >
        <VongBut w={props.coVongNhip1} h={420} />
      </Interactive.Div>

      {/* Mũi tên chỉ xuống cấu trúc ngầm */}
      <Interactive.Div
        name="Mũi tên chỉ cấu trúc ngầm"
        from={2}
        durationInFrames={108}
        style={{position: 'absolute', left: 660, top: 250, opacity: op1}}
      >
        <MuiTen dx={120} dy={210} cong={0.35} />
      </Interactive.Div>

      {/* ============ NHỊP 2 — CẬN CẢNH ĐẤT ẨM ============ */}
      <Interactive.Div
        name="Cận cảnh đất ẩm giữ nước"
        from={83}
        durationInFrames={122}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateX(${slide2}px) scale(${sc2})`,
            transformOrigin: '50% 45%',
          }}
        >
          <AnhNen
            anh={props.anhCanDat}
            tu={props.zoomDatAmTu}
            den={props.zoomDatAmDen}
            goc="50% 45%"
            toi={props.toiNen}
          />
        </div>
      </Interactive.Div>

      {/* Vòng khoanh vùng nước ngầm thấm sâu */}
      <Interactive.Div
        name="Vòng khoanh nước ngầm thấm"
        from={83}
        durationInFrames={95}
        style={{position: 'absolute', left: 720, top: 430, opacity: op2}}
      >
        <VongBut w={props.coVongNhip2} h={400} />
      </Interactive.Div>

      {/* Ba mũi tên nước thấm xuống */}
      <Interactive.Div
        name="Mũi tên thấm xuống 1"
        from={83}
        durationInFrames={95}
        style={{position: 'absolute', left: 830, top: 300, opacity: op2}}
      >
        <MuiTen dx={-30} dy={200} cong={-0.22} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên thấm xuống 2"
        from={87}
        durationInFrames={91}
        style={{position: 'absolute', left: 960, top: 280, opacity: op2}}
      >
        <MuiTen dx={0} dy={230} cong={0.12} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên thấm xuống 3"
        from={91}
        durationInFrames={87}
        style={{position: 'absolute', left: 1090, top: 300, opacity: op2}}
      >
        <MuiTen dx={30} dy={200} cong={0.22} />
      </Interactive.Div>

      {/* ============ NHỊP 3 — VÙNG GIÓ CÁT ĐƯỢC BẢO VỆ ============ */}
      <Interactive.Div
        name="Vùng gió cát xói mòn"
        from={173}
        durationInFrames={115}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateY(${slide3}px) scale(${sc3})`,
            transformOrigin: '50% 50%',
          }}
        >
          <AnhNen
            anh={props.anhGioCat}
            tu={props.zoomGioCatTu}
            den={props.zoomGioCatDen}
            goc="50% 50%"
            toi={props.toiNen}
          />
        </div>
      </Interactive.Div>

      {/* Vòng khoanh lớp đất giữ ẩm được bảo vệ */}
      <Interactive.Div
        name="Vòng khoanh đất được bảo vệ"
        from={173}
        durationInFrames={115}
        style={{position: 'absolute', left: 640, top: 470}}
      >
        <VongBut w={props.coVongNhip3} h={430} />
      </Interactive.Div>

      {/* Ba mũi tên gió cát thổi tới */}
      <Interactive.Div
        name="Mũi tên gió cát 1"
        from={173}
        durationInFrames={115}
        style={{position: 'absolute', left: 140, top: 300}}
      >
        <MuiTen dx={420} dy={80} cong={0.35} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên gió cát 2"
        from={181}
        durationInFrames={107}
        style={{position: 'absolute', left: 120, top: 520}}
      >
        <MuiTen dx={460} dy={-40} cong={-0.3} />
      </Interactive.Div>

      <Interactive.Div
        name="Mũi tên gió cát 3"
        from={189}
        durationInFrames={99}
        style={{position: 'absolute', left: 160, top: 740}}
      >
        <MuiTen dx={400} dy={60} cong={0.25} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
