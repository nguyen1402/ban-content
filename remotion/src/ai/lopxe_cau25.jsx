import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhSuoi: z.string().describe('Ảnh dòng suối tự nhiên'),
  anhBieuDo: z.string().describe('Ảnh biểu đồ kỹ thuật thủy văn'),
  anhTrangTrai: z.string().describe('Ảnh toàn cảnh trang trại khô cằn'),
  anhLopXe: z.string().describe('Ảnh cận cảnh chồng lốp xe cũ'),
  zoomSuoiTu: z.number().describe('Độ phóng dòng suối lúc mở cảnh'),
  zoomSuoiDen: z.number().describe('Độ phóng dòng suối lúc kết thúc'),
  zoomBieuDoTu: z.number().describe('Độ phóng biểu đồ lúc trượt vào'),
  zoomBieuDoDen: z.number().describe('Độ phóng biểu đồ lúc kết thúc'),
  zoomTrangTraiTu: z.number().describe('Độ phóng trang trại lúc trượt vào'),
  zoomTrangTraiDen: z.number().describe('Độ phóng trang trại lúc kết thúc'),
  zoomLopXeTu: z.number().describe('Độ phóng lốp xe lúc bắt đầu punch-in'),
  zoomLopXeDen: z.number().describe('Độ phóng lốp xe lúc kết thúc'),
  quangTruotNgang: z.number().describe('Quãng trượt ngang của biểu đồ (px)'),
  soFrameTruotNgang: z.number().describe('Số frame trượt ngang của biểu đồ'),
  quangTruotDoc: z.number().describe('Quãng trượt dọc của trang trại (px)'),
  soFrameTruotDoc: z.number().describe('Số frame trượt dọc của trang trại'),
  soFrameHienLopXe: z.number().describe('Số frame hoà trộn lớp lốp xe'),
  toiSuoi: z.number().describe('Độ tối phủ lên dòng suối (0-0.5)'),
  toiBieuDo: z.number().describe('Độ tối phủ lên biểu đồ (0-0.5)'),
  toiTrangTrai: z.number().describe('Độ tối phủ lên trang trại (0-0.5)'),
  toiLopXe: z.number().describe('Độ tối phủ lên lốp xe (0-0.5)'),
});

/* ---------- Ảnh phủ toàn khung ---------- */
const AnhPhu = ({anh, ten}) => (
  <Img
    src={src(anh)}
    name={ten}
    style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}}
  />
);

/* ---------- Beat 1: dòng suối, đẩy máy rất chậm ---------- */
const KhoiSuoi = ({anh, tu, den, toi, dai}) => {
  const f = useCurrentFrame();
  const scale = interpolate(f, [0, dai], [tu, den], kep);
  const y = interpolate(f, [0, dai], [0, -26], kep);
  return (
    <div style={{position: 'absolute', inset: 0, transform: `scale(${scale}) translateY(${y}px)`}}>
      <AnhPhu anh={anh} ten="Ảnh dòng suối" />
      <div style={{position: 'absolute', inset: 0, background: `rgba(6,18,24,${toi})`}} />
    </div>
  );
};

/* ---------- Beat 2: biểu đồ trượt ngang vào từ bên phải ---------- */
const KhoiBieuDo = ({anh, tu, den, toi, dai, quang, soFrame}) => {
  const f = useCurrentFrame();
  const x = interpolate(f, [0, soFrame], [quang, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const scale = interpolate(f, [soFrame, dai], [tu, den], kep);
  return (
    <div style={{position: 'absolute', inset: 0, transform: `translateX(${x}px)`}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${scale})`}}>
        <AnhPhu anh={anh} ten="Ảnh biểu đồ thủy văn" />
        <div style={{position: 'absolute', inset: 0, background: `rgba(8,14,22,${toi})`}} />
      </div>
    </div>
  );
};

/* ---------- Beat 3: trang trại trượt lên từ dưới ---------- */
const KhoiTrangTrai = ({anh, tu, den, toi, dai, quang, soFrame}) => {
  const f = useCurrentFrame();
  const y = interpolate(f, [0, soFrame], [quang, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const scale = interpolate(f, [0, dai], [tu, den], kep);
  const x = interpolate(f, [0, dai], [0, -44], kep);
  return (
    <div style={{position: 'absolute', inset: 0, transform: `translateY(${y}px)`}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${scale}) translateX(${x}px)`}}>
        <AnhPhu anh={anh} ten="Ảnh trang trại khô cằn" />
        <div style={{position: 'absolute', inset: 0, background: `rgba(24,16,6,${toi})`}} />
      </div>
    </div>
  );
};

/* ---------- Beat 4: punch-in chậm vào chồng lốp xe ---------- */
const KhoiLopXe = ({anh, tu, den, toi, dai, soFrameHien}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, soFrameHien], [0, 1], {...kep, easing: Easing.out(Easing.quad)});
  const scale = interpolate(f, [0, dai], [tu, den], {...kep, easing: Easing.out(Easing.quad)});
  const x = interpolate(f, [0, dai], [0, -30], kep);
  const y = interpolate(f, [0, dai], [0, -18], kep);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        opacity: op,
        transform: `scale(${scale}) translateX(${x}px) translateY(${y}px)`,
      }}
    >
      <AnhPhu anh={anh} ten="Ảnh chồng lốp xe cũ" />
      <div style={{position: 'absolute', inset: 0, background: `rgba(10,10,12,${toi})`}} />
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#000000'}}>
      {/* 1 — frame 2: dòng suối tự nhiên */}
      <Interactive.Div
        name="Dòng suối tự nhiên"
        from={0}
        durationInFrames={378}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <KhoiSuoi
          anh={props.anhSuoi}
          tu={props.zoomSuoiTu}
          den={props.zoomSuoiDen}
          toi={props.toiSuoi}
          dai={378}
        />
      </Interactive.Div>

      {/* 2 — frame 116: biểu đồ kỹ thuật thủy văn trượt ngang vào */}
      <Interactive.Div
        name="Biểu đồ kỹ thuật thủy văn"
        from={116}
        durationInFrames={262}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <KhoiBieuDo
          anh={props.anhBieuDo}
          tu={props.zoomBieuDoTu}
          den={props.zoomBieuDoDen}
          toi={props.toiBieuDo}
          dai={262}
          quang={props.quangTruotNgang}
          soFrame={props.soFrameTruotNgang}
        />
      </Interactive.Div>

      {/* 3 — frame 158: toàn cảnh trang trại khô cằn trượt lên */}
      <Interactive.Div
        name="Toàn cảnh trang trại khô cằn"
        from={158}
        durationInFrames={220}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <KhoiTrangTrai
          anh={props.anhTrangTrai}
          tu={props.zoomTrangTraiTu}
          den={props.zoomTrangTraiDen}
          toi={props.toiTrangTrai}
          dai={220}
          quang={props.quangTruotDoc}
          soFrame={props.soFrameTruotDoc}
        />
      </Interactive.Div>

      {/* 4 — frame 242: punch-in chậm vào chồng lốp xe cũ (giữ tới frame cuối) */}
      <Interactive.Div
        name="Cận cảnh chồng lốp xe cũ"
        from={242}
        durationInFrames={136}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <KhoiLopXe
          anh={props.anhLopXe}
          tu={props.zoomLopXeTu}
          den={props.zoomLopXeDen}
          toi={props.toiLopXe}
          dai={136}
          soFrameHien={props.soFrameHienLopXe}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
