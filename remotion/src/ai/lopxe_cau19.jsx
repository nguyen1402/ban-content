import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  tieuDe: z.string().describe('Tiêu đề chính trên góc'),
  namKhoiDau: z.string().describe('Năm bắt đầu mốc thời gian'),
  namKetThuc: z.string().describe('Năm kết thúc mốc thời gian'),
  dienTichSo: z.number().describe('Số liệu diện tích héc ta'),
  dienTichDonVi: z.string().describe('Đơn vị diện tích'),
  anhNen1: z.string().describe('Ảnh nền đồng cỏ Arizona'),
  anhDanBo: z.string().describe('Ảnh cắt lớp đàn bò Longhorn'),
  anhDatToTien: z.string().describe('Ảnh đất tổ tiên'),
});

// 1. Nền đồng cỏ Arizona với chuyển động camera push-in và pan liên tục
const NenDongCoArizona = ({anh}) => {
  const f = useCurrentFrame();

  let scale = 1.05;
  let panX = 0;
  let panY = 0;

  if (f < 76) {
    scale = interpolate(f, [0, 76], [1.05, 1.18], kep);
    panX = interpolate(f, [0, 76], [0, -45], kep);
    panY = interpolate(f, [0, 76], [0, -15], kep);
  } else if (f < 105) {
    const f2 = f - 76;
    scale = interpolate(f2, [0, 8], [1.22, 1.28], {...kep, easing: Easing.out(Easing.cubic)});
    panX = interpolate(f2, [0, 29], [-45, -95], kep);
    panY = -15;
  } else {
    const f3 = f - 105;
    scale = interpolate(f3, [0, 55], [1.10, 1.18], kep);
    panX = interpolate(f3, [0, 55], [20, -15], kep);
    panY = interpolate(f3, [0, 55], [-10, 0], kep);
  }

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transformOrigin: '50% 50%',
          transform: `scale(${scale}) translate(${panX}px, ${panY}px)`,
          filter: 'brightness(0.92) contrast(1.04)'
        }}
      />
    </AbsoluteFill>
  );
};

// 2. Bóng đen silhouette các thế hệ gia đình đứng nhìn ra thảo nguyên (0 - 76 frames)
const BongDenTheHe = () => {
  const f = useCurrentFrame();
  const opacity = interpolate(f, [0, 10], [0, 1], kep) * interpolate(f, [68, 76], [1, 0], kep);
  const translateY = interpolate(f, [0, 14], [25, 0], {...kep, easing: Easing.out(Easing.cubic)});
  const scale = interpolate(f, [14, 76], [1, 1.04], kep);

  return (
    <div style={{
      position: 'absolute',
      right: '50px',
      bottom: '0px',
      width: '860px',
      height: '540px',
      opacity,
      transform: `translateY(${translateY}px) scale(${scale})`,
      transformOrigin: 'bottom right',
      pointerEvents: 'none'
    }}>
      <svg viewBox="0 0 860 540" style={{width: '100%', height: '100%', overflow: 'visible'}}>
        <defs>
          <filter id="goldBacklight" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="-4" stdDeviation="6" floodColor="#ffd23f" floodOpacity="0.4" />
            <feDropShadow dx="0" dy="6" stdDeviation="16" floodColor="#000000" floodOpacity="0.85" />
          </filter>
        </defs>
        <g filter="url(#goldBacklight)" fill="#120f0c">
          {/* Gò đồi tiền cảnh uốn lượn tự nhiên */}
          <path d="M 0,514 Q 140,500 280,508 T 560,512 T 860,518 L 860,540 L 0,540 Z" />
          {/* Cụm cỏ thảo nguyên mọc trên gò đất */}
          <path d="M 105,512 Q 112,492 118,512 Q 124,495 130,512 Z M 275,508 Q 282,488 288,508 Q 295,492 302,508 Z M 420,510 Q 426,490 432,510 Q 438,494 445,510 Z M 720,516 Q 726,494 732,516 Q 738,498 745,516 Z" />

          {/* 1. Ông nội (Elder Grandfather) - Mũ cao bồi rộng vành, áo khoác duster dài */}
          {/* Mũ */}
          <path d="M 172,78 C 168,52 174,38 186,34 C 192,38 196,38 202,34 C 214,38 220,52 216,78 Z" />
          <path d="M 132,84 C 150,92 186,94 194,94 C 202,94 238,92 256,84 C 262,81 262,86 254,90 C 236,99 202,100 194,100 C 186,100 152,99 134,90 C 126,86 126,81 132,84 Z" />
          {/* Cổ áo */}
          <path d="M 184,98 C 184,108 186,120 186,126 L 202,126 C 202,120 204,108 204,98 Z" />
          {/* Thân áo duster & cánh tay buông tự nhiên */}
          <path d="M 186,126 C 172,132 158,140 148,150 C 138,168 134,220 136,280 C 138,320 144,340 148,340 C 152,340 154,320 154,280 C 154,230 160,180 168,164 L 166,270 C 160,340 148,420 134,478 C 134,482 176,482 194,482 L 194,390 L 198,390 L 198,482 C 216,482 258,482 258,478 C 244,420 232,340 226,270 L 224,164 C 232,180 238,230 238,280 C 238,320 240,340 244,340 C 248,340 254,320 256,280 C 258,220 254,168 244,150 C 234,140 220,132 206,126 Z" />
          {/* Đôi bốt cao bồi */}
          <path d="M 148,478 L 144,522 C 144,526 162,527 168,525 L 170,478 Z" />
          <path d="M 220,478 L 222,525 C 228,527 246,526 246,522 L 242,478 Z" />

          {/* 2. Người cha (Father Rancher) - Vóc dáng cường tráng, tay chống hông, mũ Stetson */}
          {/* Mũ */}
          <path d="M 346,76 C 342,50 348,36 360,32 C 366,36 370,36 376,32 C 388,36 394,50 390,76 Z" />
          <path d="M 308,82 C 326,90 358,92 368,92 C 378,92 410,90 428,82 C 434,79 434,84 426,88 C 408,97 376,98 368,98 C 360,98 328,97 310,88 C 302,84 302,79 308,82 Z" />
          {/* Cổ & Vai gáy */}
          <path d="M 358,96 L 356,124 L 380,124 L 378,96 Z" />
          {/* Thân trên: Áo gi-lê, tay trái chống hông, tay phải đặt cạnh con */}
          <path d="M 356,124 C 340,130 326,140 316,155 C 302,176 290,215 304,242 C 310,250 320,248 322,238 C 314,218 320,185 330,168 L 328,255 L 348,258 L 344,310 C 338,350 330,420 324,522 C 324,527 344,527 350,524 L 358,345 L 372,345 L 380,524 C 386,527 406,527 406,522 C 400,420 392,350 388,310 L 386,258 L 404,255 L 402,168 C 412,185 418,220 412,250 C 412,260 422,262 426,254 C 438,230 432,176 418,155 C 408,140 394,130 380,124 Z" />

          {/* 3. Người mẹ (Mother Matriarch) - Váy dài thảo nguyên, nón rộng vành thanh lịch */}
          {/* Nón */}
          <path d="M 496,106 C 496,86 506,78 518,78 C 530,78 540,86 540,106 Z" />
          <path d="M 466,114 C 484,120 508,122 518,122 C 528,122 552,120 570,114 C 576,112 576,116 568,119 C 550,126 526,127 518,127 C 510,127 486,126 468,119 C 460,116 460,112 466,114 Z" />
          {/* Cổ & Vai */}
          <path d="M 510,126 L 508,146 L 528,146 L 526,126 Z" />
          {/* Khăn choàng & Thân váy xoè nhẹ */}
          <path d="M 508,146 C 494,152 482,162 476,176 C 468,194 470,230 475,242 C 478,248 484,245 485,238 C 482,222 488,188 496,178 L 498,252 C 488,295 470,395 448,502 C 448,508 584,508 584,502 C 562,395 544,295 536,252 L 538,178 C 546,188 552,222 549,238 C 550,245 556,248 559,242 C 564,230 566,194 558,176 C 552,162 540,152 528,146 Z" />
          {/* Giày thấp thoáng gấu váy */}
          <path d="M 486,502 L 484,522 C 484,525 500,525 504,522 L 502,502 Z" />
          <path d="M 530,502 L 532,522 C 536,525 552,525 552,522 L 550,502 Z" />

          {/* 4. Đứa con (Child) - Mũ cao bồi nhỏ, háo hức nhìn về phía thảo nguyên */}
          {/* Mũ */}
          <path d="M 640,210 C 636,192 642,180 652,176 C 656,180 660,180 664,176 C 674,180 680,192 676,210 Z" />
          <path d="M 612,216 C 626,222 648,224 656,224 C 664,224 686,222 700,216 C 704,214 704,218 698,221 C 684,227 662,228 656,228 C 650,228 628,227 614,221 C 608,218 608,214 612,216 Z" />
          {/* Cổ & Thân bé */}
          <path d="M 650,228 L 648,248 L 664,248 L 662,228 Z" />
          <path d="M 648,248 C 636,252 624,260 618,272 C 612,286 614,320 618,330 C 620,335 624,333 624,328 C 622,315 626,290 632,282 L 630,340 C 626,370 618,430 612,524 C 612,527 628,527 632,525 L 638,380 L 646,380 L 652,525 C 656,527 672,527 672,524 C 666,430 660,370 656,340 L 654,282 C 662,290 675,302 688,298 C 694,296 695,288 686,284 C 676,278 668,266 664,258 C 660,252 654,248 648,248 Z" />
        </g>
      </svg>
    </div>
  );
};

// 3. Nhãn chữ 'THẾ HỆ NHÀ KING' (frame 36 - 76)
const NhanTieuDeTheHe = ({tieuDe}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 10], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{
      opacity: p,
      transform: `translateY(${interpolate(p, [0, 1], [-20, 0])}px)`,
      display: 'flex',
      alignItems: 'center',
      gap: '20px',
      background: 'rgba(10, 12, 16, 0.78)',
      padding: '16px 36px',
      borderRadius: '16px',
      borderLeft: `8px solid ${VANG}`,
      backdropFilter: 'blur(12px)',
      boxShadow: '0 12px 32px rgba(0,0,0,0.6)'
    }}>
      <span style={{
        color: VANG,
        fontSize: '58px',
        fontWeight: 900,
        letterSpacing: '3px',
        textTransform: 'uppercase',
        textShadow: '0 4px 18px rgba(0,0,0,0.95)'
      }}>
        {tieuDe}
      </span>
    </div>
  );
};

// 4. Mốc thời gian dọc (1895 - 1980s) xuất hiện từ frame 50 đến 76
const MocThoiGianDoc = ({namKhoiDau, namKetThuc}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 14], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const lineHeight = p * 140;
  const p2 = interpolate(f, [12, 20], [0, 1], kep);

  return (
    <div style={{
      background: 'rgba(10, 12, 16, 0.78)',
      padding: '24px 32px',
      borderRadius: '20px',
      border: '2px solid rgba(255, 210, 63, 0.4)',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 16px 40px rgba(0,0,0,0.6)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        opacity: interpolate(f, [0, 8], [0, 1], kep)
      }}>
        <div style={{
          width: '18px',
          height: '18px',
          borderRadius: '50%',
          backgroundColor: '#ffffff',
          boxShadow: '0 0 16px #ffffff'
        }} />
        <span style={{
          color: '#ffffff',
          fontSize: '56px',
          fontWeight: 900,
          textShadow: '0 4px 16px rgba(0,0,0,0.9)'
        }}>
          {namKhoiDau}
        </span>
      </div>

      <div style={{
        position: 'relative',
        width: '6px',
        height: `${lineHeight}px`,
        backgroundColor: VANG,
        marginLeft: '6px',
        boxShadow: `0 0 14px ${VANG}`,
        borderRadius: '3px',
        margin: '6px 0 6px 6px'
      }}>
        <div style={{
          position: 'absolute',
          top: `${Math.max(0, lineHeight - 12)}px`,
          left: '-5px',
          width: '16px',
          height: '16px',
          borderRadius: '50%',
          backgroundColor: VANG,
          boxShadow: `0 0 18px ${VANG}`
        }} />
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        opacity: p2,
        transform: `translateY(${interpolate(p2, [0, 1], [10, 0])}px)`
      }}>
        <div style={{
          width: '18px',
          height: '18px',
          borderRadius: '50%',
          backgroundColor: VANG,
          boxShadow: `0 0 16px ${VANG}`
        }} />
        <span style={{
          color: VANG,
          fontSize: '56px',
          fontWeight: 900,
          textShadow: '0 4px 16px rgba(0,0,0,0.9)'
        }}>
          {namKetThuc}
        </span>
      </div>
    </div>
  );
};

// 5. Đàn bò Texas Longhorn di chuyển trực tiếp trên thảo nguyên (frame 76 - 105)
const DanBoTexasLonghorn = ({anh}) => {
  const f = useCurrentFrame();
  const panX = interpolate(f, [0, 29], [-380, -90], kep);

  return (
    <div style={{
      position: 'absolute',
      bottom: '180px',
      left: `${panX}px`,
      width: '2800px',
      height: '440px',
      overflow: 'visible',
      pointerEvents: 'none'
    }}>
      <Img
        src={src(anh)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          filter: 'drop-shadow(0 15px 24px rgba(0,0,0,0.65)) contrast(1.08)'
        }}
      />
    </div>
  );
};

// Tiêu đề phân đoạn 'CHĂN THẢ GIA SÚC'
const TieuDeChanThaGiaSuc = () => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 10], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{
      opacity: p,
      transform: `translateX(${interpolate(p, [0, 1], [-30, 0])}px)`,
      display: 'flex',
      alignItems: 'center',
      gap: '20px',
      background: 'rgba(10, 12, 16, 0.78)',
      padding: '16px 36px',
      borderRadius: '16px',
      borderLeft: `8px solid ${VANG}`,
      backdropFilter: 'blur(12px)',
      boxShadow: '0 12px 32px rgba(0,0,0,0.6)'
    }}>
      <span style={{
        color: '#ffffff',
        fontSize: '56px',
        fontWeight: 900,
        letterSpacing: '2px',
        textTransform: 'uppercase',
        textShadow: '0 4px 18px rgba(0,0,0,0.95)'
      }}>
        CHĂN THẢ GIA SÚC
      </span>
    </div>
  );
};

// 6. Hiệu ứng quét sáng (Light Sweep) trên mảnh đất tổ tiên (frame 105 - 160)
const QuetSangDatToTien = () => {
  const f = useCurrentFrame();
  const sweepPos = interpolate(f, [0, 32], [-500, 2400], kep);

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      bottom: 0,
      left: `${sweepPos}px`,
      width: '450px',
      background: 'linear-gradient(90deg, transparent 0%, rgba(255, 230, 160, 0.15) 30%, rgba(255, 255, 255, 0.5) 50%, rgba(255, 230, 160, 0.15) 70%, transparent 100%)',
      transform: 'skewX(-25deg)',
      mixBlendMode: 'screen',
      pointerEvents: 'none'
    }} />
  );
};

// 7. Bảng thông tin diện tích đất tổ tiên '17,700 HÉC TA'
const BangThongTinDienTich = ({dienTichSo, dienTichDonVi}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 12], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

  return (
    <div style={{
      position: 'absolute',
      bottom: '80px',
      left: '100px',
      width: '960px',
      height: '440px',
      backgroundColor: 'rgba(12, 14, 18, 0.85)',
      borderRadius: '24px',
      border: `3px solid rgba(255, 210, 63, 0.8)`,
      boxShadow: '0 24px 60px rgba(0,0,0,0.85), 0 0 40px rgba(255,210,63,0.2)',
      backdropFilter: 'blur(16px)',
      padding: '36px 48px',
      boxSizing: 'border-box',
      opacity: p,
      transform: `translateY(${interpolate(p, [0, 1], [30, 0])}px)`,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between'
    }}>
      <div>
        <div style={{
          color: VANG,
          fontSize: '28px',
          fontWeight: 800,
          letterSpacing: '3px',
          textTransform: 'uppercase',
          marginBottom: '8px'
        }}>
          THẾ HỆ NHÀ KING • 1895 - 1980s
        </div>
        <div style={{
          color: '#ffffff',
          fontSize: '54px',
          fontWeight: 900,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
          textShadow: '0 4px 16px rgba(0,0,0,0.9)'
        }}>
          MẢNH ĐẤT TỔ TIÊN ĐỂ LẠI
        </div>
        <div style={{
          width: '100%',
          height: '3px',
          background: 'linear-gradient(90deg, #ffd23f, transparent)',
          marginTop: '16px'
        }} />
      </div>

      <div style={{display: 'flex', alignItems: 'baseline', gap: '24px'}}>
        <SoDem so={dienTichSo} don_vi="" giay={1.1} co={140} />
        <span style={{
          color: VANG,
          fontSize: '64px',
          fontWeight: 900,
          letterSpacing: '2px',
          textShadow: '0 4px 18px rgba(0,0,0,0.9)'
        }}>
          {dienTichDonVi}
        </span>
      </div>

      <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
        <div style={{
          width: '10px',
          height: '10px',
          borderRadius: '50%',
          backgroundColor: VANG,
          boxShadow: `0 0 10px ${VANG}`
        }} />
        <span style={{
          color: 'rgba(255,255,255,0.8)',
          fontSize: '26px',
          fontWeight: 600,
          letterSpacing: '1px'
        }}>
          ĐỒNG CỎ CHĂN THẢ GIA SÚC LỊCH SỬ
        </span>
      </div>
    </div>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', fontFamily: FONT, overflow: 'hidden'}}>
      {/* 1. Nền đồng cỏ Arizona chạy xuyên suốt toàn bộ cảnh */}
      <Interactive.Div
        name="NenDongCoArizona"
        from={0}
        durationInFrames={160}
        style={{position: 'absolute', inset: 0}}
      >
        <NenDongCoArizona anh={props.anhNen1} />
      </Interactive.Div>

      {/* 2. Bóng đen silhouette các thế hệ đứng nhìn ra thảo nguyên */}
      <Interactive.Div
        name="BongDenTheHe"
        from={0}
        durationInFrames={76}
        style={{position: 'absolute', inset: 0}}
      >
        <BongDenTheHe />
      </Interactive.Div>

      {/* 3. Nhãn chữ 'THẾ HỆ NHÀ KING' ở góc trên */}
      <Interactive.Div
        name="NhanTieuDeTheHe"
        from={36}
        durationInFrames={40}
        style={{position: 'absolute', left: 100, top: 80}}
      >
        <NhanTieuDeTheHe tieuDe={props.tieuDe} />
      </Interactive.Div>

      {/* 4. Mốc thời gian dọc (1895 - 1980s) */}
      <Interactive.Div
        name="MocThoiGianDoc"
        from={50}
        durationInFrames={26}
        style={{position: 'absolute', left: 100, top: 200}}
      >
        <MocThoiGianDoc namKhoiDau={props.namKhoiDau} namKetThuc={props.namKetThuc} />
      </Interactive.Div>

      {/* 5. Đàn bò Texas Longhorn di chuyển trên thảo nguyên */}
      <Interactive.Div
        name="DanBoTexasLonghorn"
        from={76}
        durationInFrames={29}
        style={{position: 'absolute', inset: 0}}
      >
        <DanBoTexasLonghorn anh={props.anhDanBo} />
      </Interactive.Div>

      {/* 6. Tiêu đề phân đoạn 'CHĂN THẢ GIA SÚC' */}
      <Interactive.Div
        name="TieuDeChanThaGiaSuc"
        from={76}
        durationInFrames={29}
        style={{position: 'absolute', left: 100, top: 80}}
      >
        <TieuDeChanThaGiaSuc />
      </Interactive.Div>

      {/* 7. Hiệu ứng quét sáng (Light Sweep) */}
      <Interactive.Div
        name="QuetSangDatToTien"
        from={105}
        durationInFrames={55}
        style={{position: 'absolute', inset: 0}}
      >
        <QuetSangDatToTien />
      </Interactive.Div>

      {/* 8. Bảng thông tin diện tích đất tổ tiên */}
      <Interactive.Div
        name="BangThongTinDienTich"
        from={105}
        durationInFrames={55}
        style={{position: 'absolute', inset: 0}}
      >
        <BangThongTinDienTich dienTichSo={props.dienTichSo} dienTichDonVi={props.dienTichDonVi} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
