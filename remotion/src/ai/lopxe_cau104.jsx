import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền: cụm lốp cũ dưới đáy biển'),
  anhKhoa: z.string().describe('Ảnh cận cảnh: khóa kim loại rỉ sét'),
  anhDay: z.string().describe('Ảnh cận cảnh: dây buộc mục đứt'),
  anhNuoc: z.string().describe('Ảnh nền: dòng chảy bão biển hỗn loạn'),
  anhNhomTach: z.string().describe('Ảnh tách: các nhóm lốp bung tách'),
  anhLopTroi: z.string().describe('Ảnh tách: lốp trôi dạt khắp nơi'),
  doPhongNen: z.number().describe('Độ phóng cuối của ảnh nền cụm lốp'),
  doPhongDay: z.number().describe('Độ phóng của ảnh dây buộc'),
  doPhongNuoc: z.number().describe('Độ phóng đầu của lớp nước biển (kéo lùi dần)'),
  doMoNuoc: z.number().describe('Độ đậm lớp nước biển tràn qua (0-1)'),
  bienDoRung: z.number().describe('Biên độ rung của khối lốp trước khi bị xé (px)'),
  doTachNhom: z.number().describe('Quãng đường nhóm lốp bị cuốn đi (px)'),
  doTroiLop: z.number().describe('Quãng đường lốp trôi về phía camera (px)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- LỚP DÂY BUỘC (xuất hiện mềm từ frame 128) ---------- */
  const fDay = frame - 128;
  const opDay = interpolate(fDay, [0, 16], [0, 1], kep);

  /* ---------- LỚP NƯỚC BIỂN (tràn qua từ 157) ---------- */
  const opNuoc = interpolate(frame, [157, 178], [0, props.doMoNuoc], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  /* ---------- CỬA SỔ PHÓNG ĐẠI KHÓA KIM LOẠI ---------- */
  const fWin = frame - 2;
  const popWin = spring({frame: fWin, fps, config: {damping: 15, stiffness: 95, mass: 0.9}});
  const shrinkWin = interpolate(frame, [98, 128], [1, 0.08], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const scaleWin = popWin * shrinkWin;
  const opWin = interpolate(frame, [2, 10, 118, 128], [0, 1, 1, 0], kep);
  const zoomWin = interpolate(frame, [2, 128], [1.35, 2.2], kep);
  const opLine = interpolate(frame, [10, 24], [0, 1], kep);

  /* ---------- NHÓM LỐP BUNG TÁCH (từ 190) ---------- */
  const fe = frame - 190;
  const opE = interpolate(fe, [0, 14], [0, 1], kep);
  const rungE =
    Math.sin(fe * 0.6) * props.bienDoRung * interpolate(fe, [0, 8, 34], [0, 1, 0], kep);
  const ex = interpolate(frame, [190, 202, 316], [0, 8, props.doTachNhom], {
    ...kep,
    easing: Easing.inOut(Easing.sin),
  });
  const ey = interpolate(frame, [190, 202, 316], [0, -6, -175], {
    ...kep,
    easing: Easing.inOut(Easing.sin),
  });
  const erot = interpolate(frame, [190, 202, 316], [0, 1.2, 13], {
    ...kep,
    easing: Easing.inOut(Easing.sin),
  });
  const esc = interpolate(frame, [190, 202, 250, 316], [0.94, 1, 0.96, 0.84], kep);

  /* ---------- LỐP TRÔI DẠT (từ 250) ---------- */
  const opF = interpolate(frame, [250, 264], [0, 1], kep);
  const fx = interpolate(frame, [250, 316], [0, props.doTroiLop], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const fy = interpolate(frame, [250, 316], [0, -120], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const fsc = interpolate(frame, [250, 316], [0.9, 1.18], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const frot = interpolate(frame, [250, 316], [-5, 4], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#04121c', overflow: 'hidden'}}>
      {/* ===== 1. NỀN: CỤM LỐP CŨ DƯỚI ĐÁY BIỂN ===== */}
      <Interactive.Div
        name="Cụm lốp cũ dưới đáy biển"
        from={0}
        durationInFrames={316}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhNen} tu={1} den={props.doPhongNen} goc="50% 58%" toi={0.08} />
      </Interactive.Div>

      {/* ===== 2. CỬA SỔ PHÓNG ĐẠI GẮN VÀO KHÓA KIM LOẠI ===== */}
      <Interactive.Div
        name="Cửa sổ phóng đại khóa kim loại"
        from={2}
        durationInFrames={130}
        style={{position: 'absolute', left: 740, top: 200, width: 440, height: 440}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            overflow: 'hidden',
            opacity: opWin,
            transform: `scale(${scaleWin})`,
            transformOrigin: '50% 50%',
            border: '6px solid rgba(222,240,255,0.9)',
            boxSizing: 'border-box',
          }}
        >
          <Img
            src={src(props.anhKhoa)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${zoomWin})`,
              transformOrigin: '46% 52%',
            }}
          />
        </div>
        <svg
          width={440}
          height={440}
          style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: opLine}}
        >
          <line x1={357} y1={393} x2={410} y2={460} stroke="rgba(222,240,255,0.85)" strokeWidth={3} />
          <circle cx={410} cy={460} r={16} fill="none" stroke="rgba(222,240,255,0.9)" strokeWidth={3} />
          <circle cx={410} cy={460} r={4} fill="rgba(222,240,255,0.95)" />
        </svg>
      </Interactive.Div>

      {/* ===== 3. CẬN CẢNH DÂY BUỘC MỤC ĐỨT ===== */}
      <Interactive.Div
        name="Dây buộc mục đứt"
        from={128}
        durationInFrames={188}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: opDay}}>
          <AnhLia anh={props.anhDay} huong="phai" quang={70} phong={props.doPhongDay} toi={0.06} />
        </AbsoluteFill>
      </Interactive.Div>

      {/* ===== 4. DÒNG NƯỚC BÃO BIỂN TRÀN QUA ===== */}
      <Interactive.Div
        name="Dòng chảy bão biển"
        from={157}
        durationInFrames={159}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: opNuoc}}>
          <AnhNen anh={props.anhNuoc} tu={props.doPhongNuoc} den={1} goc="50% 45%" toi={0.05} />
        </AbsoluteFill>
      </Interactive.Div>

      {/* ===== 5. CÁC NHÓM LỐP BUNG TÁCH ===== */}
      <Interactive.Div
        name="Các nhóm lốp bung tách"
        from={190}
        durationInFrames={126}
        style={{position: 'absolute', left: 520, top: 300, width: 980, height: 519}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: opE,
            transform: `translate(${ex + rungE}px, ${ey}px) rotate(${erot}deg) scale(${esc})`,
            transformOrigin: '50% 50%',
          }}
        >
          <Img
            src={src(props.anhNhomTach)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      {/* ===== 6. LỐP TRÔI DẠT KHẮP NƠI ===== */}
      <Interactive.Div
        name="Lốp trôi dạt khắp nơi"
        from={250}
        durationInFrames={66}
        style={{position: 'absolute', left: 1210, top: 190, width: 660, height: 760}}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: opF,
            transform: `translate(${fx}px, ${fy}px) rotate(${frot}deg) scale(${fsc})`,
            transformOrigin: '50% 50%',
          }}
        >
          <Img
            src={src(props.anhLopTroi)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
