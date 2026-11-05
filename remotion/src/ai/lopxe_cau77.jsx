import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhDatKho: z.string().describe('Ảnh nền đất khô nứt nẻ hoang tàn'),
  anhThaoNguyen: z.string().describe('Ảnh nền thảo nguyên xanh tràn đầy sinh khí'),
  anhTho: z.string().describe('Cut-out thỏ đồng sa mạc đang ăn cỏ'),
  anhLinhMieu: z.string().describe('Cut-out linh miêu trên mỏm đá trung cảnh'),
  phongDatCuoi: z.number().describe('Độ phóng của nền đất khô ở cuối khối'),
  phongThaoDau: z.number().describe('Độ phóng đầu của nền thảo nguyên'),
  phongThaoCuoi: z.number().describe('Độ phóng cuối của nền thảo nguyên'),
  daiSangRong: z.number().describe('Bề rộng dải sáng chuyển cảnh (px)'),
  daiSangCao: z.number().describe('Chiều cao dải sáng chuyển cảnh (px)'),
  daiSangOpacity: z.number().describe('Độ đậm dải sáng chuyển cảnh'),
  heSoTruotPhai: z.number().describe('Số px cảnh dịch sang trái khi máy quay trượt phải'),
  lechParallaxTho: z.number().describe('Số px thỏ tiền cảnh trôi thêm (parallax)'),
  lechParallaxMieu: z.number().describe('Số px linh miêu trôi thêm (parallax)'),
  moTho: z.number().describe('Độ mờ tiêu cự của thỏ tiền cảnh ở nhịp 3 (px)'),
  thoTrai: z.number().describe('Toạ độ X của thỏ tiền cảnh'),
  thoTop: z.number().describe('Toạ độ Y của thỏ tiền cảnh'),
  thoRong: z.number().describe('Bề rộng cut-out thỏ'),
  mieuTrai: z.number().describe('Toạ độ X của linh miêu'),
  mieuTop: z.number().describe('Toạ độ Y của linh miêu'),
  mieuRong: z.number().describe('Bề rộng cut-out linh miêu'),
});

const NHIP1 = 2;
const NHIP2 = 56;
const NHIP3 = 194;

// chống props thiếu / NaN: luôn có số hợp lệ để lớp tiền cảnh không bị "tàng hình"
const so = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v : d);

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const cuoi = Math.max(2, durationInFrames - 1);

  const phongDatCuoi = so(props.phongDatCuoi, 1.14);
  const phongThaoDau = so(props.phongThaoDau, 1.06);
  const phongThaoCuoi = so(props.phongThaoCuoi, 1.18);
  const daiSangRong = so(props.daiSangRong, 520);
  const daiSangCao = so(props.daiSangCao, 1700);
  const daiSangOpacity = so(props.daiSangOpacity, 0.85);
  const heSoTruotPhai = so(props.heSoTruotPhai, 130);
  const lechParallaxTho = so(props.lechParallaxTho, 120);
  const lechParallaxMieu = so(props.lechParallaxMieu, 70);
  const moTho = so(props.moTho, 5);
  const thoTrai = so(props.thoTrai, 1040);
  const thoTop = so(props.thoTop, 520);
  const thoRong = so(props.thoRong, 660);
  const mieuTrai = so(props.mieuTrai, 300);
  const mieuTop = so(props.mieuTop, 300);
  const mieuRong = so(props.mieuRong, 540);

  // ---- Nhịp 1: đất khô -> thảo nguyên xanh (frame 2) ----
  const xanhHien = interpolate(frame, [NHIP1, NHIP1 + 56], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.ease),
  });

  // ---- Nhịp 3: máy quay trượt sang phải (frame 194) ----
  const truot = interpolate(frame, [NHIP3, cuoi], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.ease),
  });

  const nenDich = -heSoTruotPhai * truot;

  // ---- Ô kính cận cảnh vết nứt (nằm TRONG cùng khối với nền đất khô) ----
  const the1Vao = interpolate(frame, [0, 14], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const the1Ra = interpolate(frame, [72, 92], [0, 1], {...kep, easing: Easing.in(Easing.cubic)});
  const the1Op = the1Vao * (1 - the1Ra);
  const the1Dich =
    interpolate(frame, [0, 14], [70, 0], {...kep, easing: Easing.out(Easing.cubic)}) +
    interpolate(frame, [72, 92], [0, -50], {...kep, easing: Easing.in(Easing.cubic)});

  // ---- Thỏ tiền cảnh: vào sớm (frame 56) và ở lại tới hết cảnh ----
  const thoOp = interpolate(frame, [NHIP2, NHIP2 + 16], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  const thoDich =
    interpolate(frame, [NHIP2, NHIP2 + 24], [120, 0], {...kep, easing: Easing.out(Easing.cubic)}) +
    interpolate(frame, [NHIP3, cuoi], [0, -lechParallaxTho], {
      ...kep,
      easing: Easing.inOut(Easing.ease),
    });

  const thoNhip = interpolate(
    frame,
    [70, 97, 125, 153, 181, cuoi],
    [0, -12, 0, -12, 0, -7],
    {...kep, easing: Easing.inOut(Easing.ease)}
  );

  const thoMo = interpolate(frame, [NHIP3, NHIP3 + 26], [0, moTho], {
    ...kep,
    easing: Easing.inOut(Easing.ease),
  });

  const thoPhong = interpolate(frame, [NHIP2, cuoi], [1, 1.06], kep);

  // ---- Vòng khoanh đúng chỗ chú thỏ (frame 150) ----
  const vongOp = interpolate(frame, [150, 166, 212, 232], [0, 1, 1, 0], kep);
  const vongScale = interpolate(frame, [150, 174], [0.55, 1], {
    ...kep,
    easing: Easing.out(Easing.back(1.6)),
  });
  const vongXoay = interpolate(frame, [150, cuoi], [0, 42], kep);

  // ---- Linh miêu trung cảnh (frame 194) ----
  const mieuDich = interpolate(frame, [NHIP3, NHIP3 + 26, cuoi], [80, 0, -lechParallaxMieu], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  const mieuMo = interpolate(frame, [NHIP3, NHIP3 + 22], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.ease),
  });

  const mieuPhong = interpolate(frame, [NHIP3, cuoi], [0.96, 1.04], kep);

  // ---- Ô tròn cận cảnh linh miêu (frame 206) — nằm TRONG cùng khối với linh miêu ----
  const the2Op = interpolate(frame, [206, 222, cuoi - 14, cuoi], [0, 1, 1, 0], kep);
  const the2Scale = interpolate(frame, [206, 234], [0.6, 1], {
    ...kep,
    easing: Easing.out(Easing.back(1.5)),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#2b2a20'}}>
      {/* KHỐI 1 — NỀN ĐẤT KHÔ NỨT NẺ + Ô KÍNH CẬN CẢNH VẾT NỨT
          Ảnh props.anhDatKho chỉ được mount DUY NHẤT ở đây, một khối trải hết nhịp 1-2.
          zIndex đưa khối lên trên nền xanh để ô kính vẫn nổi, còn nền đất tự mờ dần. */}
      <Interactive.Div
        name="Nền đất khô nứt nẻ + ô kính cận cảnh"
        from={0}
        durationInFrames={274}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, zIndex: 1}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: 1 - xanhHien,
            transform: `translateX(${nenDich * 0.6}px)`,
          }}
        >
          <AnhNen anh={props.anhDatKho} tu={1} den={phongDatCuoi} goc="50% 50%" toi={0.12} />
        </div>
        <div style={{position: 'absolute', left: 1290, top: 108, width: 460, height: 300}}>
          <div
            style={{
              width: '100%',
              height: '100%',
              opacity: the1Op,
              transform: `translateY(${the1Dich}px) rotate(-3deg)`,
              borderRadius: 20,
              overflow: 'hidden',
              border: '10px solid rgba(255,255,255,0.94)',
              boxShadow: '0 34px 70px rgba(0,0,0,0.55)',
              boxSizing: 'border-box',
              background: '#0d0c08',
            }}
          >
            <Img
              src={src(props.anhDatKho)}
              style={{width: '100%', height: '100%', objectFit: 'cover', transform: 'scale(2.9)'}}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* KHỐI 2 — NỀN THẢO NGUYÊN XANH (hiện dần từ frame 2, ở lại tới hết cảnh) */}
      <Interactive.Div
        name="Nền thảo nguyên xanh"
        from={2}
        durationInFrames={272}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: xanhHien,
            transform: `translateX(${nenDich}px)`,
          }}
        >
          <AnhNen
            anh={props.anhThaoNguyen}
            tu={phongThaoDau}
            den={phongThaoCuoi}
            goc="50% 55%"
            toi={0.05}
          />
        </div>
      </Interactive.Div>

      {/* DẢI SÁNG QUÉT CHUYỂN CẢNH (frame 2) */}
      <Interactive.Div
        name="Dải sáng chuyển cảnh"
        from={2}
        durationInFrames={62}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: -220,
            width: daiSangRong,
            height: daiSangCao,
            background:
              'linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,251,224,0.9) 48%, rgba(255,255,255,0) 92%)',
            transform: `translateX(${interpolate(frame, [NHIP1, NHIP1 + 60], [-1400, 2400], {
              ...kep,
              easing: Easing.inOut(Easing.ease),
            })}px) skewX(-14deg)`,
            opacity:
              interpolate(frame, [NHIP1, NHIP1 + 18, NHIP1 + 46, NHIP1 + 60], [0, 1, 1, 0], kep) *
              daiSangOpacity,
            mixBlendMode: 'screen',
            pointerEvents: 'none',
          }}
        />
      </Interactive.Div>

      {/* LỚP TIỀN CẢNH MỜ — tạo độ sâu, có mặt suốt cả cảnh */}
      <Interactive.Div
        name="Lớp tiền cảnh mờ tạo độ sâu"
        from={0}
        durationInFrames={274}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            bottom: 0,
            width: 1920,
            height: 360,
            background: 'linear-gradient(to top, rgba(14,20,10,0.62) 0%, rgba(14,20,10,0) 100%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 0,
            bottom: 0,
            width: 1920,
            height: 170,
            background: 'linear-gradient(to top, rgba(8,12,6,0.55) 0%, rgba(8,12,6,0) 100%)',
            filter: 'blur(6px)',
          }}
        />
      </Interactive.Div>

      {/* THỎ ĐỒNG ĂN CỎ — TIỀN CẢNH (vào từ frame 56, ở lại tới hết) */}
      <Interactive.Div
        name="Thỏ đồng ăn cỏ tiền cảnh"
        from={56}
        durationInFrames={218}
        style={{position: 'absolute', left: thoTrai, top: thoTop, width: thoRong, height: 488}}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            opacity: thoOp,
            transform: `translateX(${thoDich}px) translateY(${thoNhip}px) scale(${thoPhong})`,
            transformOrigin: '50% 95%',
            filter: `blur(${thoMo}px) drop-shadow(0 26px 34px rgba(0,0,0,0.5))`,
          }}
        >
          <Img
            src={src(props.anhTho)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      {/* VÒNG KHOANH ĐÚNG CHỖ CHÚ THỎ (frame 150) */}
      <Interactive.Div
        name="Vòng khoanh chú thỏ"
        from={150}
        durationInFrames={124}
        style={{position: 'absolute', left: thoTrai + 118, top: thoTop + 96, width: 268, height: 268}}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            opacity: vongOp,
            transform: `translateX(${thoDich}px) translateY(${thoNhip}px) scale(${vongScale})`,
            transformOrigin: '50% 50%',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 268,
              height: 268,
              borderRadius: '50%',
              border: '6px solid rgba(255,214,102,0.95)',
              boxShadow: '0 0 26px rgba(255,200,80,0.65), inset 0 0 22px rgba(255,200,80,0.35)',
              boxSizing: 'border-box',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: -18,
              top: -18,
              width: 304,
              height: 304,
              borderRadius: '50%',
              border: '3px dashed rgba(255,255,255,0.8)',
              transform: `rotate(${vongXoay}deg)`,
              boxSizing: 'border-box',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: -6,
              top: 280,
              padding: '10px 20px',
              borderRadius: 999,
              background: 'rgba(0,0,0,0.6)',
              color: '#fff',
              fontSize: 28,
              letterSpacing: 3,
              whiteSpace: 'nowrap',
              boxShadow: '0 10px 24px rgba(0,0,0,0.45)',
            }}
          >
            THỎ ĐỒNG ĂN CỎ
          </div>
        </div>
      </Interactive.Div>

      {/* KHỐI CUỐI — LINH MIÊU TRÊN MỎM ĐÁ + Ô TRÒN CẬN CẢNH
          Ảnh props.anhLinhMieu chỉ mount DUY NHẤT ở đây, một khối trải tới frame cuối. */}
      <Interactive.Div
        name="Linh miêu trên mỏm đá + ô tròn cận cảnh"
        from={194}
        durationInFrames={80}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: mieuTrai,
            top: mieuTop,
            width: mieuRong,
            height: 454,
            opacity: mieuMo,
            transform: `translateX(${mieuDich}px) scale(${mieuPhong})`,
            transformOrigin: '50% 90%',
            filter: 'drop-shadow(0 22px 30px rgba(0,0,0,0.45))',
          }}
        >
          <Img
            src={src(props.anhLinhMieu)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>
        <div style={{position: 'absolute', left: 118, top: 690, width: 300, height: 300}}>
          <div
            style={{
              width: '100%',
              height: '100%',
              opacity: the2Op,
              transform: `scale(${the2Scale})`,
              borderRadius: '50%',
              overflow: 'hidden',
              border: '8px solid rgba(255,214,120,0.92)',
              boxShadow: '0 26px 60px rgba(0,0,0,0.6)',
              boxSizing: 'border-box',
              background: '#141a10',
            }}
          >
            <Img
              src={src(props.anhLinhMieu)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: 'scale(1.7) translateY(6%)',
              }}
            />
          </div>
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
