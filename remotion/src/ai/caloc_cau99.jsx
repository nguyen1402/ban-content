import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, AnhNen} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen_song: z.string().describe('Hình nền dòng nước sông Manistee'),
  anh_au_trung: z.string().describe('Hình cắt ấu trùng cá mút đá'),
  anh_ca_hoi_van: z.string().describe('Hình cắt cá hồi vân'),
  anh_ca_tue: z.string().describe('Hình cắt cá tuế đầu to'),
  tieu_de_ca_hoi: z.string().describe('Nhãn tác động cá hồi vân'),
  tieu_de_ca_tue: z.string().describe('Nhãn tác động cá tuế đầu to'),
  mau_hoa_chat: z.string().describe('Màu dải hóa chất diệt khuẩn'),
  mau_nguy_hiem: z.string().describe('Màu chữ cảnh báo thiệt hại'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // 1. Quét hóa chất cam vàng lampricide (Frame 0 -> 64)
  const hoaChatX = interpolate(frame, [0, 58], [-900, 2300], {
    ...kep,
    easing: Easing.bezier(0.25, 0.1, 0.25, 1),
  });
  const hoaChatOpacity = interpolate(frame, [0, 10, 44, 62], [0.3, 0.95, 0.9, 0], kep);

  // 2. Giai đoạn 1: Ấu trùng cá mút đá (Frame 0 -> 60)
  // Quét qua, ngả sắc cam độc và tan biến sạch hoàn toàn
  const tanBienLarva1 = interpolate(frame, [22, 50], [1, 0], kep);
  const tanBienLarva2 = interpolate(frame, [15, 38], [1, 0], kep);
  const tanBienLarva3 = interpolate(frame, [28, 56], [1, 0], kep);

  // 3. Giai đoạn 2: Cá hồi vân (bắt đầu vào từ frame 52 để nối tiếp trơn tru, khung 63 đạt 100% hiển thị)
  const troutAppear = spring({
    frame: frame - 52,
    fps,
    config: {damping: 14, mass: 0.85},
  });

  // Con cá hồi 1 bị trúng độc: lật ngửa bụng tự nhiên (lật theo trục thân scaleY và nghiêng nhẹ) và chìm xuống đáy
  const troutRoll = interpolate(frame, [82, 122], [1, -1], {
    ...kep,
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const troutTilt = interpolate(frame, [82, 122], [0, -10], {
    ...kep,
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const troutDyingY = interpolate(frame, [82, 140], [0, 120], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const troutPoisonStain = interpolate(frame, [78, 112], [0, 0.9], kep);

  // Con cá hồi 2 sống sót: bơi lội uốn lượn tự nhiên
  const troutSwimX = Math.sin((frame - 52) * 0.07) * 18;
  const troutSwimY = Math.cos((frame - 52) * 0.05) * 12;

  // Tách chữ cho nhãn Cá hồi vân: "50%" màu đỏ rực, "CÁ HỒI VÂN" màu trắng tinh khôi
  const wordsHoi = (props.tieu_de_ca_hoi || '50% Cá hồi vân').split(' ');
  const phanTramHoi = wordsHoi[0];
  const tenHoi = wordsHoi.slice(1).join(' ');

  // 4. Giai đoạn 3: Cá tuế đầu to (Frame 146 -> 253)
  // Tỉ lệ chính xác 40%: 2 con chết ngửa bụng chìm đáy, 3 con sống bơi khỏe mạnh
  const minnowAppear = spring({
    frame: frame - 146,
    fps,
    config: {damping: 15, mass: 0.8},
  });

  // 2 con cá tuế trúng độc lật ngửa bụng (lật scaleY tự nhiên) và chìm xuống đáy
  const minnowRoll = interpolate(frame, [166, 196], [1, -1], {
    ...kep,
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const minnowTilt = interpolate(frame, [166, 196], [0, -8], {
    ...kep,
    easing: Easing.bezier(0.4, 0, 0.2, 1),
  });
  const minnowDeadY = interpolate(frame, [166, 215], [0, 95], kep);
  const minnowPoisonStain = interpolate(frame, [160, 186], [0, 0.9], kep);

  // Tách chữ cho nhãn Cá tuế: "40%" màu vàng cam rực, "CÁ TUẾ ĐẦU TO" màu trắng tinh khôi
  const wordsTue = (props.tieu_de_ca_tue || '40% Cá tuế đầu to').split(' ');
  const phanTramTue = wordsTue[0];
  const tenTue = wordsTue.slice(1).join(' ');

  return (
    <AbsoluteFill style={{backgroundColor: '#0a1a22', overflow: 'hidden'}}>
      {/* Nền nước sông Manistee rõ nét, không bị tối mờ flat đen */}
      <AnhNen anh={src(props.anh_nen_song)} tu={1.04} den={1.12} goc="center" toi={0.06} />

      {/* Ánh sáng tự nhiên từ mặt nước chiếu rọi nhẹ nhàng */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at 50% 15%, rgba(56, 189, 248, 0.16) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Dải gradient nhẹ trên đỉnh và đáy tăng độ tương phản cho nhãn chữ */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(180deg, rgba(5, 16, 22, 0.52) 0%, transparent 22%, transparent 75%, rgba(5, 16, 22, 0.55) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* ================= LUỒNG HÓA CHẤT CAM VÀNG QUÉT QUA SÔNG (Frame 0 -> 64) ================= */}
      {frame <= 64 && (
        <Interactive.Div
          name="Luồng hóa chất quét qua"
          from={0}
          durationInFrames={64}
          style={{
            position: 'absolute',
            top: 0,
            left: hoaChatX,
            width: 1050,
            height: 1080,
            opacity: hoaChatOpacity,
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              width: '100%',
              height: '100%',
              background: 'linear-gradient(90deg, rgba(234, 88, 12, 0) 0%, rgba(245, 158, 11, 0.85) 45%, rgba(249, 115, 22, 0.95) 55%, rgba(234, 88, 12, 0) 100%)',
              filter: 'blur(28px)',
              transform: 'skewX(-16deg)',
              mixBlendMode: 'screen',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 180,
              width: 550,
              height: 1080,
              background: 'linear-gradient(90deg, transparent 0%, rgba(254, 215, 170, 0.8) 50%, transparent 100%)',
              filter: 'blur(18px)',
              transform: 'skewX(-16deg)',
              mixBlendMode: 'overlay',
            }}
          />
        </Interactive.Div>
      )}

      {/* ================= GIAI ĐOẠN 1: ẤU TRÙNG CÁ MÚT ĐÁ (0.0s - 2.0s -> Frame 0 - 60) ================= */}
      {frame < 61 && (
        <>
          {/* Ấu trùng chính diện to lớn vượt chuẩn >= 40% chiều cao (cao 450px / 1080px = 41.7%) */}
          <Interactive.Div
            name="Ấu trùng cá mút đá 1 (chính)"
            from={0}
            durationInFrames={61}
            style={{
              position: 'absolute',
              left: 380,
              top: 300,
              width: 1180,
              height: 450,
              opacity: tanBienLarva1,
              transform: `scale(${1 + (1 - tanBienLarva1) * 0.12}) translateY(${(1 - tanBienLarva1) * 15}px)`,
              filter: `drop-shadow(0 20px 40px rgba(0,0,0,0.65)) ${tanBienLarva1 < 0.9 ? 'sepia(0.85) hue-rotate(-20deg) saturate(3) brightness(1.25)' : ''}`,
            }}
          >
            <Img
              src={src(props.anh_au_trung)}
              name="Hình ấu trùng cá mút đá 1"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>

          {/* Ấu trùng 2 phía trên trái */}
          <Interactive.Div
            name="Ấu trùng cá mút đá 2 (trên)"
            from={0}
            durationInFrames={61}
            style={{
              position: 'absolute',
              left: 100,
              top: 100,
              width: 680,
              height: 260,
              opacity: tanBienLarva2 * 0.9,
              transform: `scale(${0.92 + (1 - tanBienLarva2) * 0.12}) rotate(-6deg)`,
              filter: `drop-shadow(0 15px 30px rgba(0,0,0,0.55)) ${tanBienLarva2 < 0.9 ? 'sepia(0.85) hue-rotate(-20deg) saturate(3) brightness(1.25)' : ''}`,
            }}
          >
            <Img
              src={src(props.anh_au_trung)}
              name="Hình ấu trùng cá mút đá 2"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>

          {/* Ấu trùng 3 phía dưới phải */}
          <Interactive.Div
            name="Ấu trùng cá mút đá 3 (dưới)"
            from={0}
            durationInFrames={61}
            style={{
              position: 'absolute',
              left: 1140,
              top: 610,
              width: 720,
              height: 275,
              opacity: tanBienLarva3 * 0.9,
              transform: `scale(${0.9 + (1 - tanBienLarva3) * 0.12}) rotate(10deg)`,
              filter: `drop-shadow(0 15px 30px rgba(0,0,0,0.55)) ${tanBienLarva3 < 0.9 ? 'sepia(0.85) hue-rotate(-20deg) saturate(3) brightness(1.25)' : ''}`,
            }}
          >
            <Img
              src={src(props.anh_au_trung)}
              name="Hình ấu trùng cá mút đá 3"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>
        </>
      )}

      {/* ================= GIAI ĐOẠN 2: CÁ HỒI VÂN (Từ frame 52 trở đi) ================= */}
      {frame >= 52 && (
        <>
          {/* Con 1: 50% trúng độc hóa chất cam, lật ngửa bụng tự nhiên (scaleY(-1)) và chìm xuống đáy (Kích thước to: rộng 980, cao 435px >= 40%) */}
          <Interactive.Div
            name="Cá hồi vân 1 (Trúng độc lật ngửa)"
            from={52}
            durationInFrames={201}
            style={{
              position: 'absolute',
              left: 30,
              top: 270 + troutDyingY,
              width: 980,
              height: 435,
              opacity: troutAppear,
              transform: `scale(${troutAppear}) scaleY(${troutRoll}) rotate(${troutTilt}deg)`,
              filter: troutPoisonStain > 0.1
                ? `drop-shadow(0 0 35px rgba(249, 115, 22, ${troutPoisonStain})) saturate(${1 + troutPoisonStain * 0.9})`
                : 'drop-shadow(0 20px 40px rgba(0,0,0,0.6))',
            }}
          >
            <Img
              src={src(props.anh_ca_hoi_van)}
              name="Hình cá hồi trúng độc 1"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
            {/* Vệt hóa chất cam bám trên thân cá */}
            <div
              style={{
                position: 'absolute',
                inset: '18% 22%',
                background: 'radial-gradient(circle, rgba(249, 115, 22, 0.9) 0%, rgba(234, 88, 12, 0.5) 60%, transparent 80%)',
                opacity: troutPoisonStain,
                mixBlendMode: 'color-burn',
                pointerEvents: 'none',
                filter: 'blur(10px)',
              }}
            />
          </Interactive.Div>

          {/* Con 2: 50% còn lại sống sót bơi lội khỏe mạnh (Kích thước to: rộng 960, cao 430px >= 40%) */}
          <Interactive.Div
            name="Cá hồi vân 2 (Sống sót bơi lội)"
            from={52}
            durationInFrames={201}
            style={{
              position: 'absolute',
              left: 950 + troutSwimX,
              top: 180 + troutSwimY,
              width: 960,
              height: 430,
              opacity: troutAppear,
              transform: `scale(${troutAppear})`,
              filter: 'drop-shadow(0 20px 40px rgba(0,0,0,0.6))',
            }}
          >
            <Img
              src={src(props.anh_ca_hoi_van)}
              name="Hình cá hồi sống sót 2"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>

          {/* Hộp nhãn: 50% CÁ HỒI VÂN - Xuất hiện từ frame 54, đến frame 60 đã sáng rõ 100% */}
          <Interactive.Div
            name="Nhãn 50% Cá hồi vân"
            from={54}
            durationInFrames={199}
            style={{
              position: 'absolute',
              left: 70,
              top: 60,
              opacity: interpolate(frame, [54, 61], [0, 1], kep),
              transform: `translateY(${interpolate(frame, [54, 61], [20, 0], kep)}px)`,
              zIndex: 10,
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 16,
                background: 'rgba(6, 18, 25, 0.94)',
                border: '1.5px solid rgba(255, 255, 255, 0.2)',
                borderLeft: '12px solid #ef4444',
                padding: '16px 36px',
                borderRadius: '18px',
                boxShadow: '0 18px 45px rgba(0, 0, 0, 0.8)',
              }}
            >
              <span
                style={{
                  fontFamily: FONT,
                  fontSize: 84,
                  fontWeight: 900,
                  color: '#ff4d4d',
                  lineHeight: 1,
                  textShadow: '0 0 25px rgba(239, 68, 68, 0.6), 0 3px 6px rgba(0,0,0,0.9)',
                }}
              >
                {phanTramHoi}
              </span>
              <span
                style={{
                  fontFamily: FONT,
                  fontSize: 66,
                  fontWeight: 900,
                  color: '#ffffff',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  lineHeight: 1,
                  textShadow: '0 4px 14px rgba(0, 0, 0, 0.95)',
                }}
              >
                {tenHoi}
              </span>
            </div>
          </Interactive.Div>
        </>
      )}

      {/* ================= GIAI ĐOẠN 3: CÁ TUẾ ĐẦU TO (Từ frame 146 trở đi) ================= */}
      {frame >= 146 && (
        <>
          {/* 40% chết ngửa bụng chìm đáy (2 con) - Bố trí rộng thoáng không bị cá hồi đè */}
          <Interactive.Div
            name="Cá tuế 1 (Chết ngửa bụng)"
            from={146}
            durationInFrames={107}
            style={{
              position: 'absolute',
              left: 280,
              top: 680 + minnowDeadY,
              width: 540,
              height: 205,
              opacity: minnowAppear,
              transform: `scale(${minnowAppear}) scaleY(${minnowRoll}) rotate(${minnowTilt}deg)`,
              filter: minnowPoisonStain > 0.1
                ? `drop-shadow(0 0 25px rgba(249, 115, 22, ${minnowPoisonStain})) saturate(${1 + minnowPoisonStain * 0.8})`
                : 'drop-shadow(0 15px 30px rgba(0,0,0,0.55))',
            }}
          >
            <Img
              src={src(props.anh_ca_tue)}
              name="Hình cá tuế chết 1"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
            <div
              style={{
                position: 'absolute',
                inset: '12% 20%',
                background: 'radial-gradient(circle, rgba(249, 115, 22, 0.85) 0%, transparent 75%)',
                opacity: minnowPoisonStain,
                mixBlendMode: 'color-burn',
                pointerEvents: 'none',
                filter: 'blur(8px)',
              }}
            />
          </Interactive.Div>

          <Interactive.Div
            name="Cá tuế 2 (Chết ngửa bụng)"
            from={146}
            durationInFrames={107}
            style={{
              position: 'absolute',
              left: 680,
              top: 730 + minnowDeadY * 0.92,
              width: 500,
              height: 190,
              opacity: minnowAppear,
              transform: `scale(${minnowAppear}) scaleY(${minnowRoll}) rotate(${minnowTilt * 0.9}deg)`,
              filter: minnowPoisonStain > 0.1
                ? `drop-shadow(0 0 25px rgba(249, 115, 22, ${minnowPoisonStain})) saturate(${1 + minnowPoisonStain * 0.8})`
                : 'drop-shadow(0 15px 30px rgba(0,0,0,0.55))',
            }}
          >
            <Img
              src={src(props.anh_ca_tue)}
              name="Hình cá tuế chết 2"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
            <div
              style={{
                position: 'absolute',
                inset: '12% 20%',
                background: 'radial-gradient(circle, rgba(249, 115, 22, 0.85) 0%, transparent 75%)',
                opacity: minnowPoisonStain,
                mixBlendMode: 'color-burn',
                pointerEvents: 'none',
                filter: 'blur(8px)',
              }}
            />
          </Interactive.Div>

          {/* 60% sống sót bơi lội khỏe mạnh (3 con) */}
          <Interactive.Div
            name="Cá tuế 3 (Sống sót 1)"
            from={146}
            durationInFrames={107}
            style={{
              position: 'absolute',
              left: 1120,
              top: 570 + Math.sin((frame - 146) * 0.1) * 10,
              width: 540,
              height: 205,
              opacity: minnowAppear,
              transform: `scale(${minnowAppear})`,
              filter: 'drop-shadow(0 15px 30px rgba(0,0,0,0.55))',
            }}
          >
            <Img
              src={src(props.anh_ca_tue)}
              name="Hình cá tuế sống 3"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>

          <Interactive.Div
            name="Cá tuế 4 (Sống sót 2)"
            from={146}
            durationInFrames={107}
            style={{
              position: 'absolute',
              left: 1440,
              top: 680 + Math.cos((frame - 146) * 0.12) * 11,
              width: 480,
              height: 185,
              opacity: minnowAppear,
              transform: `scale(${minnowAppear})`,
              filter: 'drop-shadow(0 15px 30px rgba(0,0,0,0.55))',
            }}
          >
            <Img
              src={src(props.anh_ca_tue)}
              name="Hình cá tuế sống 4"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>

          <Interactive.Div
            name="Cá tuế 5 (Sống sót 3)"
            from={146}
            durationInFrames={107}
            style={{
              position: 'absolute',
              left: 1220,
              top: 820 + Math.sin((frame - 146) * 0.09) * 9,
              width: 460,
              height: 175,
              opacity: minnowAppear,
              transform: `scale(${minnowAppear})`,
              filter: 'drop-shadow(0 15px 30px rgba(0,0,0,0.55))',
            }}
          >
            <Img
              src={src(props.anh_ca_tue)}
              name="Hình cá tuế sống 5"
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </Interactive.Div>

          {/* Hộp nhãn: 40% CÁ TUẾ ĐẦU TO - Đặt góc dưới trái gọn gàng, chữ cực to rõ ràng */}
          <Interactive.Div
            name="Nhãn 40% Cá tuế đầu to"
            from={150}
            durationInFrames={103}
            style={{
              position: 'absolute',
              left: 70,
              top: 880,
              opacity: interpolate(frame, [150, 162], [0, 1], kep),
              transform: `translateY(${interpolate(frame, [150, 162], [20, 0], kep)}px)`,
              zIndex: 10,
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 16,
                background: 'rgba(6, 18, 25, 0.94)',
                border: '1.5px solid rgba(255, 255, 255, 0.2)',
                borderLeft: '12px solid #f59e0b',
                padding: '16px 36px',
                borderRadius: '18px',
                boxShadow: '0 18px 45px rgba(0, 0, 0, 0.8)',
              }}
            >
              <span
                style={{
                  fontFamily: FONT,
                  fontSize: 84,
                  fontWeight: 900,
                  color: '#fbbf24',
                  lineHeight: 1,
                  textShadow: '0 0 25px rgba(245, 158, 11, 0.6), 0 3px 6px rgba(0,0,0,0.9)',
                }}
              >
                {phanTramTue}
              </span>
              <span
                style={{
                  fontFamily: FONT,
                  fontSize: 66,
                  fontWeight: 900,
                  color: '#ffffff',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  lineHeight: 1,
                  textShadow: '0 4px 14px rgba(0, 0, 0, 0.95)',
                }}
              >
                {tenTue}
              </span>
            </div>
          </Interactive.Div>
        </>
      )}
    </AbsoluteFill>
  );
};
