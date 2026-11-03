import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen: z.string().describe('Hình nền bùn cát đáy sông'),
  anh_au_trung: z.string().describe('Hình cắt lớp ấu trùng mút đá'),
  tieu_de_an_minh: z.string().describe('Nhãn trạng thái mù lòa ẩn mình'),
  tieu_de_thoi_gian: z.string().describe('Chữ số thời gian tồn tại'),
  don_vi_thoi_gian: z.string().describe('Đơn vị thời gian'),
});

// Component nhãn đồng bộ hoàn toàn điểm neo, đường dẫn và hộp chữ không bị cô lập
const NhanDongBo = ({chu, dx = 170, dy = -150, co = 60}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, 8], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const o = interpolate(f, [0, 6], [0, 1], kep);
  const phai = dx >= 0;

  return (
    <div style={{position: 'relative', width: 0, height: 0, opacity: o}}>
      <svg width={1} height={1} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <g style={{filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.85))'}}>
          <line
            x1={0}
            y1={0}
            x2={dx * p}
            y2={dy * p}
            stroke="#ffffff"
            strokeWidth={4}
          />
          <circle
            cx={0}
            cy={0}
            r={8 * p}
            fill="#ffffff"
            stroke={VANG}
            strokeWidth={2}
          />
        </g>
      </svg>
      <div
        style={{
          position: 'absolute',
          left: phai ? dx + 12 : undefined,
          right: phai ? undefined : -dx + 12,
          top: dy - co * 0.8,
          whiteSpace: 'nowrap',
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: co,
          color: '#ffffff',
          padding: '8px 24px',
          background: 'rgba(10, 12, 14, 0.82)',
          [phai ? 'borderLeft' : 'borderRight']: `7px solid ${VANG}`,
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
          transform: `scale(${interpolate(f, [0, 8], [0.88, 1], {...kep, easing: Easing.out(Easing.cubic)})})`,
          transformOrigin: phai ? 'left center' : 'right center',
        }}
      >
        {chu}
      </div>
    </div>
  );
};

export const Canh = (props) => {
  const frame = useCurrentFrame();

  // 1. Chuyển động đào hang chui sâu vào lớp bùn cát (frame 17 -> 78)
  // Ấu trùng lặn sâu dần xuống lớp trầm tích đáy sông (frame 17: bắt đầu chui vào bùn, frame 78: chìm sâu cố định)
  const chuiSauX = interpolate(frame, [17, 78], [110, 0], {
    easing: Easing.bezier(0.25, 0.1, 0.25, 1),
    ...kep,
  });
  const chuiSauY = interpolate(frame, [17, 78], [-95, 20], {
    easing: Easing.bezier(0.2, 0.8, 0.35, 1),
    ...kep,
  });
  const gocNghieng = interpolate(frame, [17, 45, 78], [-15, -7, 0], kep);
  const auTrungOpacity = interpolate(frame, [17, 21], [0.82, 1], kep);

  // Dao động uốn lượn khi đào hang (giảm dần về 0 khi nằm yên tĩnh lặng trong bùn)
  const lucDao = interpolate(frame, [17, 68, 82], [1, 0.7, 0], kep);
  const uonMinhY = Math.sin((frame - 17) * 0.45) * 6 * lucDao;

  // Hiệu ứng rãnh đào mở ra rõ nét theo bước chui của ấu trùng
  const ranDatWidth = interpolate(frame, [20, 82], [0, 620], kep);
  const ranDatOpacity = interpolate(frame, [20, 35, 130, 160], [0, 0.85, 0.85, 0.4], kep);

  // Ánh sáng lân tinh leo lét rọi quanh thân ấu trùng trường tồn (frame 143+)
  const lanTinhPulse = Math.sin((frame - 143) * 0.12) * 0.2 + 0.8;
  const lanTinhOpacity = interpolate(frame, [143, 175], [0, 0.85], kep) * lanTinhPulse;

  // Độ sâu lắng đọng của đáy sông
  const doSauBaoPhu = interpolate(frame, [20, 90], [0.1, 0.4], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0907', overflow: 'hidden'}}>
      {/* 1. Nền bùn cát đáy sông phủ kín 1920x1080 suốt toàn bộ cảnh */}
      <Interactive.Div
        name="Nền bùn cát"
        from={0}
        durationInFrames={218}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, zIndex: 1}}
      >
        <AnhNen anh={props.anh_nen} tu={1.0} den={1.08} goc="50% 60%" toi={0.16} />
      </Interactive.Div>

      {/* 2. Lớp phủ bóng tối đáy sông */}
      <Interactive.Div
        name="Lớp phủ bóng tối đáy sông"
        from={0}
        durationInFrames={218}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none', zIndex: 2}}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            background: 'radial-gradient(ellipse at 50% 65%, rgba(0, 0, 0, 0) 35%, rgba(8, 5, 2, 0.55) 100%)',
            opacity: doSauBaoPhu,
          }}
        />
      </Interactive.Div>

      {/* 3. Đường rãnh đào trong bùn cát mở ra theo chuyển động chui sâu */}
      <Interactive.Div
        name="Đường rãnh bùn cát"
        from={17}
        durationInFrames={201}
        style={{
          position: 'absolute',
          left: 420,
          top: 260,
          width: 660,
          height: 380,
          pointerEvents: 'none',
          zIndex: 3,
          opacity: ranDatOpacity,
        }}
      >
        <svg width="660" height="380" viewBox="0 0 660 380" style={{overflow: 'visible'}}>
          <defs>
            <linearGradient id="ranhVien" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#7a5d3f" stopOpacity="0.65" />
              <stop offset="60%" stopColor="#4a3622" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#251a0e" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="ranhSau" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#080503" stopOpacity="0.95" />
              <stop offset="60%" stopColor="#170f07" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#050302" stopOpacity="0.5" />
            </linearGradient>
            <filter id="ranhBlur">
              <feGaussianBlur stdDeviation="7" />
            </filter>
          </defs>
          <path
            d="M 580 30 Q 360 140 40 310"
            stroke="url(#ranhVien)"
            strokeWidth="96"
            strokeLinecap="round"
            fill="none"
            filter="url(#ranhBlur)"
            strokeDasharray="660"
            strokeDashoffset={660 - ranDatWidth}
          />
          <path
            d="M 580 30 Q 360 140 40 310"
            stroke="url(#ranhSau)"
            strokeWidth="56"
            strokeLinecap="round"
            fill="none"
            filter="url(#ranhBlur)"
            strokeDasharray="660"
            strokeDashoffset={660 - ranDatWidth}
          />
        </svg>
      </Interactive.Div>

      {/* 4. Hốc hang bùn tối bao quanh thân ấu trùng khi ẩn nấp sâu dưới cát */}
      <Interactive.Div
        name="Hốc hang bùn của ấu trùng"
        from={17}
        durationInFrames={201}
        style={{
          position: 'absolute',
          left: 210,
          top: 360,
          width: 1500,
          height: 600,
          pointerEvents: 'none',
          zIndex: 4,
          transform: `translate(${chuiSauX}px, ${chuiSauY + uonMinhY}px) rotate(${gocNghieng}deg)`,
          transformOrigin: '40% 50%',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 80,
            top: 40,
            width: 1320,
            height: 480,
            borderRadius: '50%',
            background: 'radial-gradient(ellipse at 45% 55%, rgba(6, 4, 2, 0.72) 0%, rgba(12, 8, 4, 0.45) 55%, transparent 75%)',
            filter: 'blur(32px)',
          }}
        />
      </Interactive.Div>

      {/* 5. Ấu trùng mút đá chui sâu vào bùn cát và cuộn mình tĩnh lặng */}
      <Interactive.Div
        name="Ấu trùng mút đá"
        from={17}
        durationInFrames={201}
        style={{
          position: 'absolute',
          left: 260,
          top: 340,
          width: 1400,
          height: 590,
          zIndex: 6,
          opacity: auTrungOpacity,
          transform: `translate(${chuiSauX}px, ${chuiSauY + uonMinhY}px) rotate(${gocNghieng}deg)`,
          transformOrigin: '40% 50%',
        }}
      >
        {/* Ánh lân tinh bao bọc thân ấu trùng trường tồn suốt nhiều năm */}
        <div
          style={{
            position: 'absolute',
            left: -50,
            top: -40,
            width: 1500,
            height: 670,
            borderRadius: '50%',
            background: 'radial-gradient(ellipse at 45% 50%, rgba(94, 234, 212, 0.28) 0%, rgba(56, 189, 248, 0.1) 45%, transparent 75%)',
            opacity: lanTinhOpacity,
            filter: 'blur(28px)',
            pointerEvents: 'none',
          }}
        />

        <Img
          src={src(props.anh_au_trung)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            filter: 'drop-shadow(0 22px 38px rgba(0, 0, 0, 0.95)) brightness(0.92) contrast(1.12)',
          }}
        />
      </Interactive.Div>

      {/* 6. Lớp trầm tích phù sa phủ chìm ấu trùng dưới lòng bùn (Tạo hiệu ứng cắt lớp địa chất chân thực) */}
      <Interactive.Div
        name="Lớp trầm tích phủ ấu trùng"
        from={17}
        durationInFrames={201}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          pointerEvents: 'none',
          mixBlendMode: 'multiply',
          opacity: 0.38,
          zIndex: 8,
        }}
      >
        <AnhNen anh={props.anh_nen} tu={1.0} den={1.08} goc="50% 60%" toi={0.16} />
      </Interactive.Div>

      {/* 7. Lớp bề mặt bùn cát phía trên (Layer cắt lớp mờ tự nhiên): Ấu trùng chui ngập tự nhiên dưới mặt bùn */}
      <Interactive.Div
        name="Lớp bề mặt bùn cát"
        from={0}
        durationInFrames={218}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          pointerEvents: 'none',
          zIndex: 10,
          maskImage: 'linear-gradient(to bottom, black 0px, black 150px, rgba(0,0,0,0.5) 190px, transparent 240px)',
          WebkitMaskImage: 'linear-gradient(to bottom, black 0px, black 150px, rgba(0,0,0,0.5) 190px, transparent 240px)',
        }}
      >
        <AnhNen anh={props.anh_nen} tu={1.0} den={1.08} goc="50% 60%" toi={0.16} />
      </Interactive.Div>

      {/* 8. Bụi phù sa xới lở khi ấu trùng đào sâu vào bùn cát */}
      <Interactive.Div
        name="Bụi phù sa xới lở"
        from={17}
        durationInFrames={65}
        style={{
          position: 'absolute',
          left: 580,
          top: 240,
          width: 380,
          height: 220,
          pointerEvents: 'none',
          zIndex: 9,
          opacity: interpolate(frame, [17, 26, 52, 78], [0, 0.65, 0.5, 0], kep),
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            background: 'radial-gradient(ellipse at 40% 60%, rgba(138, 102, 68, 0.5) 0%, rgba(70, 48, 28, 0.3) 50%, transparent 75%)',
            filter: 'blur(22px)',
          }}
        />
      </Interactive.Div>

      {/* 9. Nhãn khoa học: Sống ẩn mình & Mù lòa (đồng bộ điểm neo, đặt an toàn trong safe zone) */}
      <Interactive.Div
        name="Nhãn ẩn mình mù lòa"
        from={88}
        durationInFrames={55}
        style={{
          position: 'absolute',
          left: 420,
          top: 610,
          width: 600,
          height: 200,
          zIndex: 15,
        }}
      >
        <NhanDongBo chu={props.tieu_de_an_minh} dx={170} dy={-150} co={60} />
      </Interactive.Div>

      {/* 10. Cao trào thị giác: Lớp phủ số đếm thời gian trường tồn '3 – 10+ NĂM' (frame 143 - 218) */}
      <Interactive.Div
        name="Khối thời gian trường tồn"
        from={143}
        durationInFrames={75}
        style={{
          position: 'absolute',
          left: 160,
          top: 120,
          width: 800,
          height: 240,
          zIndex: 16,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
        }}
      >
        <HienDan vao={14} het={10}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 108,
              fontWeight: 900,
              letterSpacing: '4px',
              color: '#f8fafc',
              textShadow: '0 0 28px rgba(94, 234, 212, 0.75), 0 8px 32px rgba(0,0,0,0.95)',
              lineHeight: 1.1,
              display: 'flex',
              alignItems: 'baseline',
              gap: 24,
            }}
          >
            <span>{props.tieu_de_thoi_gian}</span>
            <span
              style={{
                fontSize: 72,
                fontWeight: 800,
                color: VANG,
                letterSpacing: '6px',
                textShadow: '0 0 22px rgba(251, 191, 36, 0.65)',
              }}
            >
              {props.don_vi_thoi_gian}
            </span>
          </div>

          <div
            style={{
              marginTop: 16,
              height: 5,
              width: 420,
              background: `linear-gradient(90deg, ${VANG} 0%, rgba(94, 234, 212, 0.85) 70%, transparent 100%)`,
              boxShadow: '0 0 14px rgba(251, 191, 36, 0.85)',
            }}
          />
        </HienDan>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
