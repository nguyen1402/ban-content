import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, AnhNen, AnhLia, VongBut} from './thu_vien.jsx';

/* ---------- phần tử nhỏ ---------- */

const ChamTucson = ({mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 200, mass: 0.5}, durationInFrames: 18});
  const r = spring({frame: f - 5, fps, config: {damping: 200}, durationInFrames: 22});
  return (
    <>
      <div style={{position: 'absolute', left: -16, top: -16, width: 32, height: 32, borderRadius: '50%', background: mau, transform: `scale(${s})`}} />
      <div style={{position: 'absolute', left: -46, top: -46, width: 92, height: 92, borderRadius: '50%', border: `3px solid ${mau}`, opacity: 0.5 * r, transform: `scale(${0.5 + 0.5 * r})`}} />
    </>
  );
};

const SoNam = ({chu, co, mau}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f, fps, config: {damping: 200}, durationInFrames: 26});
  return (
    <div
      style={{
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontSize: co,
        fontWeight: 300,
        letterSpacing: co * 0.09,
        color: mau,
        lineHeight: 1,
        whiteSpace: 'nowrap',
        opacity: p,
        transform: `translateY(${(1 - p) * 26}px)`,
      }}
    >
      {chu}
    </div>
  );
};

const CoTienCanh = ({anh, rong, toc}) => {
  const f = useCurrentFrame();
  const cao = (rong * 606) / 700;
  const x = interpolate(f, [0, 90], [toc / 2, -toc / 2], kep);
  const vao = interpolate(f, [0, 6], [0, 1], kep);
  return (
    <div style={{position: 'absolute', left: -440 + x, top: 250, width: rong, height: cao, opacity: vao}}>
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

/* ---------- schema ---------- */

export const schema = z.object({
  anhBanDo: z.string().describe('Ảnh bản đồ cổ Arizona 1880'),
  anhThungLung: z.string().describe('Ảnh toàn cảnh thung lũng Altar có dòng suối'),
  anhCoTienCanh: z.string().describe('Ảnh PNG cỏ rậm tiền cảnh (trong suốt)'),
  anhDanBo: z.string().describe('Ảnh đàn bò giữa đồng cỏ cao quá đầu'),
  chuNam: z.string().describe('Chữ số năm in trên bản đồ'),
  coChuNam: z.number().describe('Cỡ chữ số năm (px)'),
  mauMuc: z.string().describe('Màu mực đỏ vẽ trên bản đồ'),
  doRongCo: z.number().describe('Chiều rộng lớp cỏ tiền cảnh (px)'),
  tocDoCo: z.number().describe('Quãng trượt ngang của lớp cỏ (px)'),
  quangPanBo: z.number().describe('Quãng pan ngang của ảnh đàn bò (px)'),
  phongBo: z.number().describe('Độ phóng của ảnh đàn bò'),
});

/* ---------- cảnh ---------- */

export const Canh = (props) => {
  const frame = useCurrentFrame();

  // Bản đồ: lặn sâu xuyên bản đồ rồi tan vào toàn cảnh
  const mapFade = interpolate(frame, [0, 168, 188], [1, 1, 0], kep);
  const diveCham = interpolate(frame, [0, 150], [1, 1.06], kep);
  const diveNhanh = interpolate(frame, [150, 196], [1, 2.7], {...kep, easing: Easing.in(Easing.cubic)});
  const dive = diveCham * diveNhanh;

  // Thung lũng hiện ra
  const valleyVao = interpolate(frame, [172, 189], [0, 1], kep);

  // Đàn bò hiện ra
  const boVao = interpolate(frame, [228, 242], [0, 1], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#1b140d'}}>
      {/* ===== BẢN ĐỒ CỔ 1880 ===== */}
      <Interactive.Div
        name="Bản đồ cổ 1880"
        from={0}
        durationInFrames={196}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: mapFade}}>
          <AbsoluteFill style={{transform: `scale(${dive})`, transformOrigin: '58% 62%'}}>
            <AnhNen anh={props.anhBanDo} tu={1} den={1.22} goc="58% 62%" toi={0.06} />

            <Interactive.Div
              name="Vòng mực đỏ khoanh thung lũng Altar"
              from={64}
              durationInFrames={132}
              style={{position: 'absolute', left: 470, top: 640}}
            >
              <VongBut w={460} h={300} />
            </Interactive.Div>

            <Interactive.Div
              name="Điểm đỏ định vị Tucson"
              from={36}
              durationInFrames={160}
              style={{position: 'absolute', left: 906, top: 700}}
            >
              <ChamTucson mau={props.mauMuc} />
            </Interactive.Div>
          </AbsoluteFill>

          <Interactive.Div
            name="Số năm 1880"
            from={3}
            durationInFrames={193}
            style={{position: 'absolute', left: 120, top: 96}}
          >
            <SoNam chu={props.chuNam} co={props.coChuNam} mau={props.mauMuc} />
          </Interactive.Div>
        </AbsoluteFill>
      </Interactive.Div>

      {/* ===== TOÀN CẢNH THUNG LŨNG ALTAR ===== */}
      <Interactive.Div
        name="Toàn cảnh thung lũng Altar"
        from={172}
        durationInFrames={74}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: valleyVao}}>
          <AnhNen anh={props.anhThungLung} tu={1.32} den={1.06} goc="50% 55%" />
        </AbsoluteFill>
      </Interactive.Div>

      {/* ===== ĐÀN BÒ GIỮA ĐỒNG CỎ CAO ===== */}
      <Interactive.Div
        name="Đàn bò giữa đồng cỏ cao"
        from={228}
        durationInFrames={94}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AbsoluteFill style={{opacity: boVao}}>
          <AnhLia anh={props.anhDanBo} huong="trai" quang={props.quangPanBo} phong={props.phongBo} />
        </AbsoluteFill>
      </Interactive.Div>

      {/* ===== LỚP CỎ TIỀN CẢNH (PARALLAX) ===== */}
      <Interactive.Div
        name="Lớp cỏ rậm tiền cảnh"
        from={232}
        durationInFrames={90}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <CoTienCanh anh={props.anhCoTienCanh} rong={props.doRongCo} toc={props.tocDoCo} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
