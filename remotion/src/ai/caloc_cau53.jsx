import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  nenNguDaiHo: z.string().describe('Hình nền Ngũ Đại Hồ dưới nước'),
  tachCaHoi: z.string().describe('Ảnh tách nền cá hồi hồ'),
  canMiengBamThit: z.string().describe('Ảnh cận cảnh miệng bám và phẫu diện giải phẫu'),
  nhanChatChongDong: z.string().describe('Nhãn chất chống đông máu'),
  nhanThoiGian: z.string().describe('Nhãn thời gian ký sinh'),
  kichThuocNhan: z.number().describe('Kích thước chữ nhãn (px)'),
  mauLamellipodin: z.string().describe('Màu huỳnh quang chất chống đông máu'),
  mauMauTuoi: z.string().describe('Màu dòng máu hút xoáy'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Pha 1: 0 -> 62 (Bám chặt)
  // Pha 2: 62 -> 146 (Cạo nát vảy và da)
  // Pha 3: 146 -> 201 (Tiết chất chống đông máu)
  // Pha 4: 201 -> 273 (Hút máu và dịch cơ thể)
  // Pha 5: 273 -> 327 (Suốt 1 - 1.5 năm kiệt quệ)

  // Cá hồi di chuyển chậm qua khung hình (giai đoạn 1)
  const caHoiX = interpolate(frame, [0, 62], [320, 480], kep);
  const caHoiY = interpolate(frame, [0, 62], [420, 400], kep);

  // Miệng giác hút cá mút đá lao tới dính chặt vào sườn cá hồi đúng frame 12 ('chặt')
  const mouthStrike = spring({
    frame: frame - 5,
    fps,
    config: {damping: 14, stiffness: 180, mass: 0.8},
  });
  const mouthX = interpolate(mouthStrike, [0, 1], [1300, 760]);
  const mouthY = interpolate(mouthStrike, [0, 1], [700, 460]);
  const mouthScale = interpolate(mouthStrike, [0, 1], [0.6, 1.15]);

  // Vết lõm áp lực chân không khi bám chặt (frame 12 -> 62)
  const dentOpacity = interpolate(frame, [12, 22], [0, 0.85], kep);

  // Giai đoạn cận cảnh giải phẫu (frame 62 -> 273): zoom & pan kịch tính
  const macroScale = interpolate(
    frame,
    [62, 75, 200, 273, 295],
    [1.0, 1.35, 1.45, 1.45, 1.1],
    {...kep, easing: Easing.out(Easing.cubic)}
  );
  const macroRot = interpolate(frame, [62, 146], [0, 6], kep);

  // Lực cào xoay của răng sừng (frame 62 -> 146)
  const scrapeCycle = Math.sin((frame - 62) * 0.7);
  const scrapeRot = interpolate(frame, [62, 146], [0, 180], kep);

  // Chất lỏng lamellipodin tiết ra (frame 146 -> 201)
  const fluidProg = interpolate(frame, [146, 180], [0, 1], kep);
  const fluidPulse = Math.sin(frame * 0.4) * 0.15 + 0.85;

  // Dòng máu và dịch cơ thể bị hút xoáy ngược vào vòm họng theo nhịp co bóp (frame 201 -> 273)
  const suctionPulse = (Math.sin((frame - 201) * 0.5) + 1) / 2;
  const suctionScale = interpolate(suctionPulse, [0, 1], [0.9, 1.15]);

  // Độ tóp teo và thâm đen của vết loét cơ thể cá (frame 201 -> 327)
  const atrophyDarkness = interpolate(frame, [201, 310], [0, 0.65], kep);

  // Kim đồng hồ quay tua nhanh (frame 273 -> 327)
  const clockRot = interpolate(frame, [273, 327], [0, 1080], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#03141f', overflow: 'hidden'}}>
      {/* Lớp nền toàn cảnh Ngũ Đại Hồ (Giai đoạn đầu và kết thúc) */}
      <Interactive.Div name="Nền Ngũ Đại Hồ" from={0} durationInFrames={327} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={props.nenNguDaiHo} tu={1.0} den={1.15} goc={0} toi={0.2} />
      </Interactive.Div>

      {/* LỚP 1: Toàn cảnh bám chặt (Frame 0 -> 65) */}
      {frame < 65 && (
        <>
          {/* Con cá hồi hồ bơi ngang */}
          <Interactive.Div
            name="Cá hồi hồ"
            from={0}
            durationInFrames={65}
            style={{
              position: 'absolute',
              left: caHoiX,
              top: caHoiY,
              width: 900,
              height: 351,
              transform: 'scale(1.25)',
              transformOrigin: 'center center',
            }}
          >
            <Img src={src(props.tachCaHoi)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />

            {/* Vết lõm chân không xuất hiện trên mạn sườn cá */}
            <div
              style={{
                position: 'absolute',
                left: 380,
                top: 130,
                width: 130,
                height: 130,
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(10,5,5,0.9) 20%, rgba(180,30,30,0.6) 60%, transparent 85%)',
                opacity: dentOpacity,
                transform: `scale(${interpolate(frame, [12, 20], [0.3, 1], kep)})`,
                border: '3px solid rgba(255,200,200,0.5)',
                boxShadow: 'inset 0 0 25px rgba(0,0,0,0.9)',
              }}
            />
          </Interactive.Div>

          {/* Miệng giác hút cá mút đá lao tới dính chặt vào mạn sườn */}
          {frame >= 5 && (
            <Interactive.Div
              name="Giác hút cá mút đá bám"
              from={5}
              durationInFrames={60}
              style={{
                position: 'absolute',
                left: mouthX,
                top: mouthY,
                width: 320,
                height: 320,
                transform: `scale(${mouthScale}) rotate(-25deg)`,
                transformOrigin: 'center center',
              }}
            >
              <svg width="320" height="320" viewBox="0 0 320 320">
                <defs>
                  <radialGradient id="lampreySuction" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#250505" />
                    <stop offset="45%" stopColor="#691f1d" />
                    <stop offset="80%" stopColor="#a37452" />
                    <stop offset="100%" stopColor="#402d1d" />
                  </radialGradient>
                  <filter id="shadowWrap">
                    <feDropShadow dx="-10" dy="10" stdDeviation="12" floodColor="#000" floodOpacity="0.8" />
                  </filter>
                </defs>
                {/* Cuống thân sau miệng giác hút */}
                <path d="M 160 160 Q 280 260 360 340 L 300 380 Q 200 280 130 190 Z" fill="#3d372d" opacity="0.9" />
                {/* Đĩa giác hút hình tròn đầy gai răng sừng */}
                <circle cx="160" cy="160" r="110" fill="url(#lampreySuction)" filter="url(#shadowWrap)" stroke="#1a0c02" strokeWidth="8" />
                {/* Các vòng răng sừng nhọn */}
                {[...Array(14)].map((_, i) => {
                  const angle = (i * 360) / 14;
                  return (
                    <polygon
                      key={`outer-tooth-${i}`}
                      points="155,62 165,62 160,82"
                      fill="#fff8db"
                      stroke="#876d33"
                      strokeWidth="1.5"
                      transform={`rotate(${angle} 160 160)`}
                    />
                  );
                })}
                {[...Array(10)].map((_, i) => {
                  const angle = (i * 360) / 10 + 12;
                  return (
                    <polygon
                      key={`inner-tooth-${i}`}
                      points="156,92 164,92 160,110"
                      fill="#fff1ba"
                      stroke="#876d33"
                      strokeWidth="1.5"
                      transform={`rotate(${angle} 160 160)`}
                    />
                  );
                })}
                {/* Lỗ họng trung tâm */}
                <circle cx="160" cy="160" r="38" fill="#0d0101" />
                <circle cx="160" cy="160" r="22" fill="#520505" />
              </svg>
            </Interactive.Div>
          )}
        </>
      )}

      {/* LỚP 2: Cận cảnh Macro Mặt Cắt Giải Phẫu (Frame 62 -> 327) */}
      {frame >= 62 && (
        <Interactive.Div
          name="Cận cảnh mặt cắt phẫu diện"
          from={62}
          durationInFrames={265}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `scale(${macroScale}) rotate(${macroRot}deg)`,
            transformOrigin: '880px 540px',
            filter: `brightness(${1 - atrophyDarkness * 0.4}) contrast(${1 + atrophyDarkness * 0.3})`,
          }}
        >
          <Img
            src={src(props.canMiengBamThit)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />

          {/* Hiệu ứng cơ học: Răng sừng xoay cạo nát vảy và mô thịt (Frame 62 -> 146) */}
          {frame < 146 && (
            <svg
              style={{
                position: 'absolute',
                left: 680,
                top: 340,
                width: 400,
                height: 400,
                transform: `rotate(${scrapeRot}deg)`,
                transformOrigin: '200px 200px',
                pointerEvents: 'none',
              }}
              viewBox="0 0 400 400"
            >
              {[...Array(8)].map((_, i) => {
                const angle = (i * 360) / 8;
                return (
                  <g key={`shred-${i}`} transform={`rotate(${angle} 200 200)`}>
                    <path
                      d="M 195 90 Q 205 130 200 170 Q 185 130 195 90 Z"
                      fill="#f5e8b5"
                      stroke="#800"
                      strokeWidth="2"
                    />
                    {/* Mảnh vảy văng ra */}
                    <circle
                      cx={190 + scrapeCycle * 30}
                      cy={70 - (i % 3) * 15}
                      r="7"
                      fill="#c9d9e6"
                      opacity={0.8}
                      stroke="#4f6e85"
                    />
                  </g>
                );
              })}
            </svg>
          )}

          {/* Hiệu ứng Vảy cá hồi văng ra và vết thương rách toạc (Frame 69 -> 140) */}
          {frame >= 69 && frame < 146 && (
            <div style={{position: 'absolute', left: 720, top: 380, width: 320, height: 320}}>
              {[...Array(12)].map((_, i) => {
                const flyDist = interpolate(frame, [69 + (i % 5) * 4, 130], [0, 180 + i * 20], kep);
                const angle = (i * Math.PI) / 6;
                const fx = Math.cos(angle) * flyDist + 160;
                const fy = Math.sin(angle) * flyDist + 160;
                return (
                  <div
                    key={`scale-frag-${i}`}
                    style={{
                      position: 'absolute',
                      left: fx,
                      top: fy,
                      width: 18,
                      height: 12,
                      borderRadius: '50% 50% 0 0',
                      background: 'linear-gradient(45deg, #a4b8c4, #dcecf7)',
                      transform: `rotate(${i * 45 + frame * 4}deg)`,
                      opacity: interpolate(frame, [100, 140], [1, 0], kep),
                      boxShadow: '0 0 6px rgba(0,0,0,0.5)',
                    }}
                  />
                );
              })}
            </div>
          )}

          {/* Lớp chất chống đông máu Lamellipodin thẩm thấu phát sáng (Frame 146 -> 205) */}
          {frame >= 146 && frame < 205 && (
            <div
              style={{
                position: 'absolute',
                left: 700,
                top: 360,
                width: 360,
                height: 360,
                borderRadius: '50%',
                background: `radial-gradient(circle, ${props.mauLamellipodin} 0%, rgba(186,85,211,0.5) 45%, transparent 75%)`,
                opacity: fluidProg * fluidPulse,
                mixBlendMode: 'screen',
                transform: `scale(${interpolate(frame, [146, 186], [0.4, 1.4], kep)})`,
                filter: 'blur(8px)',
              }}
            />
          )}

          {/* Nhịp co bóp nhu động hút xoáy máu và dịch cơ thể (Frame 201 -> 273) */}
          {frame >= 201 && frame < 273 && (
            <svg
              style={{
                position: 'absolute',
                left: 640,
                top: 300,
                width: 480,
                height: 480,
                transform: `scale(${suctionScale}) rotate(${frame * 2.5}deg)`,
                transformOrigin: '240px 240px',
                pointerEvents: 'none',
              }}
              viewBox="0 0 480 480"
            >
              <defs>
                <radialGradient id="bloodVortex" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#3d0000" stopOpacity="0.95" />
                  <stop offset="50%" stopColor={props.mauMauTuoi} stopOpacity="0.8" />
                  <stop offset="85%" stopColor="#ff9999" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                </radialGradient>
              </defs>
              <circle cx="240" cy="240" r="220" fill="url(#bloodVortex)" />
              {/* Vệt xoáy dòng dịch */}
              {[...Array(6)].map((_, i) => (
                <path
                  key={`swirl-${i}`}
                  d="M 240 240 Q 340 280 400 360"
                  stroke="rgba(255,220,150,0.7)"
                  strokeWidth="8"
                  fill="none"
                  strokeDasharray="20 15"
                  transform={`rotate(${i * 60} 240 240)`}
                />
              ))}
            </svg>
          )}

          {/* Vết thương thâm đen kiệt quệ lan rộng (Frame 260 -> 327) */}
          {frame >= 260 && (
            <div
              style={{
                position: 'absolute',
                left: 620,
                top: 280,
                width: 520,
                height: 520,
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(15,3,3,0.92) 20%, rgba(60,10,10,0.75) 60%, transparent 90%)',
                opacity: interpolate(frame, [260, 310], [0, 0.95], kep),
                boxShadow: 'inset 0 0 80px #000',
              }}
            />
          )}
        </Interactive.Div>
      )}

      {/* TEXT NHÃN 1: CHẤT CHỐNG ĐÔNG MÁU (Frame 158 -> 205) */}
      {frame >= 158 && frame < 206 && (
        <Interactive.Div
          name="Nhãn 1: Chất chống đông máu"
          from={158}
          durationInFrames={48}
          style={{
            position: 'absolute',
            left: 980,
            top: 260,
          }}
        >
          <Nhan chu={props.nhanChatChongDong} dx={180} dy={-90} co={props.kichThuocNhan} />
        </Interactive.Div>
      )}

      {/* ĐỒ HỌA TIMELINE VÀ NHÃN 2: 1 - 1,5 NĂM (Frame 273 -> 327) */}
      {frame >= 273 && (
        <Interactive.Div
          name="Timeline & Nhãn 2: 1 - 1.5 Năm"
          from={273}
          durationInFrames={54}
          style={{
            position: 'absolute',
            left: 1220,
            top: 140,
            display: 'flex',
            alignItems: 'center',
            gap: 28,
            padding: '24px 36px',
            backgroundColor: 'rgba(5, 12, 18, 0.88)',
            border: `3px solid ${VANG}`,
            borderRadius: 18,
            boxShadow: '0 16px 40px rgba(0,0,0,0.8)',
            opacity: interpolate(frame, [273, 285, 315, 327], [0, 1, 1, 0], kep),
          }}
        >
          {/* Biểu tượng đồng hồ kim quay tua nhanh */}
          <div
            style={{
              width: 90,
              height: 90,
              borderRadius: '50%',
              border: `4px solid ${VANG}`,
              position: 'relative',
              backgroundColor: '#0a1d29',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Tâm đồng hồ */}
            <div style={{width: 10, height: 10, borderRadius: '50%', backgroundColor: '#fff', zIndex: 3}} />
            {/* Kim giờ */}
            <div
              style={{
                position: 'absolute',
                top: 22,
                left: 42,
                width: 6,
                height: 25,
                backgroundColor: '#fff',
                transformOrigin: 'bottom center',
                transform: `rotate(${clockRot / 12}deg)`,
                borderRadius: 4,
              }}
            />
            {/* Kim phút quay nhanh */}
            <div
              style={{
                position: 'absolute',
                top: 10,
                left: 43,
                width: 4,
                height: 37,
                backgroundColor: VANG,
                transformOrigin: 'bottom center',
                transform: `rotate(${clockRot}deg)`,
                borderRadius: 3,
              }}
            />
          </div>

          <div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 68,
                fontWeight: 900,
                color: VANG,
                letterSpacing: 2,
                lineHeight: 1.1,
                textTransform: 'uppercase',
              }}
            >
              {props.nhanThoiGian}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 32,
                fontWeight: 600,
                color: '#e2efff',
                letterSpacing: 1,
              }}
            >
              KÝ SINH LIÊN TỤC
            </div>
          </div>
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};
