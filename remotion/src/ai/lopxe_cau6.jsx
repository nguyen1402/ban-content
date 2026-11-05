import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

/* ---------- Nền rễ cây: pan nhẹ sang phải + push chậm ---------- */
const NenRe = ({anh, zoomTu, zoomDen, pan}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 258], [zoomTu, zoomDen], kep);
  const tx = interpolate(f, [0, 258], [pan, -pan], kep);
  const ty = interpolate(f, [0, 258], [pan * 0.22, -pan * 0.22], kep);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}>
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `translate(${tx}px, ${ty}px) scale(${s})`,
        }}
      />
    </div>
  );
};

/* ---------- Lớp bọt biển đất ẩm trượt vào từ góc trái (parallax) ---------- */
const BotBien = ({anh, rong, cao, treo, tocDo}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 28], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const tx = -treo * (1 - vao) + interpolate(f, [28, 234], [0, tocDo], kep);
  const ty = interpolate(f, [0, 234], [26, -34], kep);
  const s = interpolate(f, [0, 234], [0.93, 1.05], kep);
  return (
    <Img
      src={src(anh)}
      style={{
        width: rong,
        height: cao,
        transform: `translate(${tx}px, ${ty}px) scale(${s})`,
        transformOrigin: '50% 60%',
        filter: 'drop-shadow(0 26px 44px rgba(0,0,0,0.45))',
      }}
    />
  );
};

/* ---------- Quét sáng lướt qua giọt nước ---------- */
const QuetSang = ({rong, doSang, nghieng}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 38], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
  const x = interpolate(p, [0, 1], [-840, 2020]);
  const op = interpolate(f, [0, 7, 30, 45], [0, doSang, doSang, 0], kep);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        overflow: 'hidden',
        opacity: op,
        mixBlendMode: 'screen',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: x,
          top: -320,
          width: rong,
          height: 1720,
          transform: `rotate(${nghieng}deg)`,
          background:
            'linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.32) 40%, rgba(255,255,255,0.92) 50%, rgba(255,255,255,0.32) 60%, rgba(255,255,255,0) 100%)',
          filter: 'blur(6px)',
        }}
      />
    </div>
  );
};

/* ---------- Đất khô nứt nẻ: wipe ngang + punch-in vào vết nứt ---------- */
const DatKho = ({anh, treo, punch}) => {
  const f = useCurrentFrame();
  const wipe = interpolate(f, [0, 20], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const clip = `inset(0% ${(1 - wipe) * 100}% 0% 0%)`;
  const slideX = interpolate(f, [0, 20], [treo, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const cham = interpolate(f, [0, 41], [1, 1.04], kep);
  const bung = interpolate(f, [41, 55], [0, punch], {...kep, easing: Easing.out(Easing.cubic)});
  const sau = interpolate(f, [55, 93], [0, 0.05], kep);
  const s = cham + bung + sau;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        overflow: 'hidden',
        clipPath: clip,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `scale(${s})`,
          transformOrigin: '50% 58%',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: -150,
            top: -90,
            width: 2220,
            height: 1260,
            transform: `translateX(${slideX}px)`,
          }}
        >
          <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
      </div>
    </div>
  );
};

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền rễ cây đan xen trong lòng đất'),
  anhBotBien: z.string().describe('Ảnh cắt rời lớp bọt biển đất ẩm'),
  anhDatKho: z.string().describe('Ảnh nền đất khô nứt nẻ'),
  zoomNenTu: z.number().describe('Tỉ lệ phóng nền rễ lúc bắt đầu'),
  zoomNenDen: z.number().describe('Tỉ lệ phóng nền rễ lúc kết thúc'),
  panNen: z.number().describe('Quãng pan ngang của nền rễ (px)'),
  botBienRong: z.number().describe('Chiều rộng lớp bọt biển (px)'),
  botBienCao: z.number().describe('Chiều cao lớp bọt biển (px)'),
  botBienX: z.number().describe('Vị trí ngang của lớp bọt biển (px)'),
  botBienY: z.number().describe('Vị trí dọc của lớp bọt biển (px)'),
  botBienTreo: z.number().describe('Quãng trượt vào từ góc trái (px)'),
  botBienTocDo: z.number().describe('Tốc độ trôi parallax của bọt biển (px)'),
  quetSangRong: z.number().describe('Bề rộng vệt sáng (px)'),
  quetSangDo: z.number().describe('Độ sáng của vệt quét (0-1)'),
  quetSangNghieng: z.number().describe('Độ nghiêng vệt sáng (độ)'),
  wipeTreo: z.number().describe('Quãng trượt ngang của đất khô khi wipe (px)'),
  punchDo: z.number().describe('Mức phóng nhanh vào vết nứt (tỉ lệ)'),
});

export const Canh = (props) => {
  const {
    anhNen,
    anhBotBien,
    anhDatKho,
    zoomNenTu,
    zoomNenDen,
    panNen,
    botBienRong,
    botBienCao,
    botBienX,
    botBienY,
    botBienTreo,
    botBienTocDo,
    quetSangRong,
    quetSangDo,
    quetSangNghieng,
    wipeTreo,
    punchDo,
  } = props;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0a08', overflow: 'hidden'}}>
      {/* 1. Nền rễ cây — frame 2 «Toàn bộ hệ rễ cây» */}
      <Interactive.Div
        name="Nền rễ cây"
        from={0}
        durationInFrames={258}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <NenRe anh={anhNen} zoomTu={zoomNenTu} zoomDen={zoomNenDen} pan={panNen} />
      </Interactive.Div>

      {/* 2. Bọt biển đất ẩm trượt vào — frame 95 «hoạt động hệt như một tấm bọt biển» */}
      <Interactive.Div
        name="Lớp bọt biển"
        from={95}
        durationInFrames={234}
        style={{position: 'absolute', left: 175, top: 245}}
      >
        <BotBien
          anh={anhBotBien}
          rong={botBienRong}
          cao={botBienCao}
          treo={botBienTreo}
          tocDo={botBienTocDo}
        />
      </Interactive.Div>

      {/* 3. Quét sáng — frame 176 «giữ trọn từng giọt nước» */}
      <Interactive.Div
        name="Quét sáng"
        from={176}
        durationInFrames={48}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <QuetSang rong={quetSangRong} doSang={quetSangDo} nghieng={quetSangNghieng} />
      </Interactive.Div>

      {/* 4. Đất khô nứt nẻ — frame 236 «Nhưng cảnh tượng đó» / frame 277 «hoàn toàn biến mất» */}
      <Interactive.Div
        name="Đất khô nứt nẻ"
        from={236}
        durationInFrames={93}
        style={{position: 'absolute', left: 0, top: 0}}
      >
        <DatKho anh={anhDatKho} treo={wipeTreo} punch={punchDo} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
