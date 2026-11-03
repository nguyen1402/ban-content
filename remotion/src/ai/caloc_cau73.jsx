import React from 'react';
import { AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan } from './thu_vien.jsx';

export const schema = z.object({
  bgNen: z.string().describe('Ảnh nền bến cảng hoang tàn'),
  bgCanThung: z.string().describe('Ảnh cận cảnh thùng xe đầy cá'),
  imgXeTai: z.string().describe('Ảnh xe tải 20 tấn cutout'),
  text1: z.string().describe('Văn bản onscreen 1 (340 xe)'),
  text2: z.string().describe('Văn bản onscreen 2 (7 xe)'),
  text1Color: z.string().describe('Màu chữ onscreen 1'),
  text2Color: z.string().describe('Màu chữ onscreen 2'),
  textSize: z.number().describe('Kích thước chữ onscreen'),
  xeWidth: z.number().describe('Chiều rộng 1 xe tải'),
  xeHeight: z.number().describe('Chiều cao 1 xe tải'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Timing constants (frames)
  // 0.0s - 1.7s: Scene 1 Harbor background (frame 0 - 51)
  // 1.9s - 3.66s: Scene 2 Top-down truck fleet + Text 1 (frame 57 - 110)
  // 3.86s - 5.14s: Scene 3 Close-up fish truck (frame 116 - 154)
  // 5.73s - 6.13s: Scene 4 Cold gray wipe effect, 333 trucks turn to ash (frame 172 - 184)
  // 6.37s - 8.77s: Scene 5 Camera zoom back to remaining trucks (frame 191 - 263)
  // 8.99s - 9.79s: Scene 6 Only 7 trucks remain + Pop-up Text 2 (frame 270 - 314)

  // Wipe progress around frame 172..184
  const wipeProgress = interpolate(frame, [170, 184], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.25, 1, 0.5, 1),
  });

  // Fleet scale/zoom animation from top-down to wide overview
  const fleetZoom = interpolate(frame, [57, 110, 170, 270], [1.3, 1.0, 1.0, 0.85], kep);

  // Remaining 7 trucks opacity/highlight vs vanished trucks
  const vanishedOpacity = interpolate(frame, [172, 182], [1, 0], kep);

  // Pop-up scale for Text 2
  const text2Spring = spring({
    frame: frame - 270,
    fps,
    config: { damping: 12, stiffness: 120 },
  });

  // Generate 20 rows of trucks to represent 340 trucks visually
  const totalTrucks = 340;
  const columns = 17;
  const rows = 20;

  const trucksGrid = Array.from({ length: totalTrucks }).map((_, i) => {
    const r = Math.floor(i / columns);
    const c = i % columns;
    const isRemainingSeven = i >= totalTrucks - 7; // Last 7 trucks stay

    // Isometric / top-down staggered positioning
    const posX = 160 + c * 95 + (r % 2) * 20;
    const posY = 180 + r * 42;

    // Disintegration ash offset during wipe
    const seed = random(`truck_${i}`);
    const ashDriftX = (seed - 0.5) * 80;
    const ashDriftY = -seed * 120;

    return {
      id: i,
      x: posX,
      y: posY,
      isRemainingSeven,
      ashDriftX,
      ashDriftY,
    };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#11161d', overflow: 'hidden' }}>
      {/* BACKGROUND 1: Bến cảng hoang tàn (Background base) */}
      <Interactive.Div
        name="Ảnh Nền Bến Cảng"
        from={0}
        durationInFrames={314}
        style={{ position: 'absolute', width: 1920, height: 1080 }}
      >
        <AnhNen anh={props.bgNen} tu={1.0} den={1.12} goc="center" toi={0.25} />
      </Interactive.Div>

      {/* SCENE 2 & 4 & 5 & 6: TRUCK FLEET GRID */}
      {frame >= 50 && (
        <AbsoluteFill
          style={{
            transform: `scale(${fleetZoom})`,
            transformOrigin: '50% 60%',
            opacity: frame >= 116 && frame < 165 ? 0 : 1, // Hidden during close-up fish tank scene
          }}
        >
          {trucksGrid.map((truck) => {
            const isVanished = !truck.isRemainingSeven;
            const currentOpacity = isVanished ? vanishedOpacity : 1;
            const ashX = isVanished ? (1 - vanishedOpacity) * truck.ashDriftX : 0;
            const ashY = isVanished ? (1 - vanishedOpacity) * truck.ashDriftY : 0;

            return (
              <Interactive.Div
                key={truck.id}
                name={truck.isRemainingSeven ? `Xe Còn Sót ${truck.id}` : `Xe Tải ${truck.id}`}
                from={50}
                durationInFrames={264}
                style={{
                  position: 'absolute',
                  left: truck.x + ashX,
                  top: truck.y + ashY,
                  width: props.xeWidth,
                  height: props.xeHeight,
                  opacity: currentOpacity,
                  filter: isVanished && vanishedOpacity < 0.8 ? `grayscale(${100 - vanishedOpacity * 100}%) blur(${(1 - vanishedOpacity) * 8}px)` : 'none',
                  transform: truck.isRemainingSeven && frame >= 270 ? 'scale(1.15)' : 'scale(1)',
                  transition: 'transform 0.3s ease-out',
                }}
              >
                <Img
                  src={src(props.imgXeTai)}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    filter: truck.isRemainingSeven && frame >= 270 ? 'drop-shadow(0px 0px 15px rgba(239, 68, 68, 0.8))' : 'none',
                  }}
                />
              </Interactive.Div>
            );
          })}
        </AbsoluteFill>
      )}

      {/* SCENE 3: CLOSE-UP FISH TRUCK TANK (3.86s - 5.14s => Frame 116 - 154) */}
      {frame >= 116 && frame <= 165 && (
        <Interactive.Div
          name="Cận Cảnh Thùng Xe Cá Hồi"
          from={116}
          durationInFrames={50}
          style={{ position: 'absolute', width: 1920, height: 1080 }}
        >
          <AnhNen anh={props.bgCanThung} tu={1.05} den={1.2} goc="center" toi={0.15} />
          {/* Subtle text dynamic highlight for rich detail */}
          <div
            style={{
              position: 'absolute',
              bottom: 100,
              left: 100,
              backgroundColor: 'rgba(0,0,0,0.7)',
              padding: '16px 36px',
              borderRadius: 12,
              borderLeft: '6px solid #eab308',
            }}
          >
            <span style={{ fontFamily: FONT, fontSize: 48, color: '#FFFFFF', fontWeight: 'bold' }}>
              Thùng xe đầy ắp cá hồi hồ
            </span>
          </div>
        </Interactive.Div>
      )}

      {/* WIPE EFFECT (5.73s - 6.13s => Frame 172 - 184) */}
      {frame >= 170 && frame <= 190 && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '1920px',
            height: '1080px',
            background: `linear-gradient(105deg, transparent ${wipeProgress - 15}%, rgba(200, 210, 220, 0.8) ${wipeProgress}%, transparent ${wipeProgress + 15}%)`,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* TEXT ONSCREEN 1: "340 xe (gần 7.000 tấn)" (1.9s - 3.66s => Frame 57 - 110) */}
      {frame >= 57 && frame < 116 && (
        <Interactive.Div
          name="Onscreen Text 1"
          from={57}
          durationInFrames={55}
          style={{
            position: 'absolute',
            top: 90,
            left: 100,
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            padding: '24px 48px',
            borderRadius: 16,
            border: '2px solid rgba(250, 204, 21, 0.6)',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: props.textSize, fontWeight: 900, color: props.text1Color }}>
            {props.text1}
          </div>
        </Interactive.Div>
      )}

      {/* TEXT ONSCREEN 2 POP-UP: "7 xe (135 tấn - 2%)" (8.99s - 9.79s+ => Frame 270 - 314) */}
      {frame >= 270 && (
        <Interactive.Div
          name="Onscreen Text 2 Pop-up"
          from={270}
          durationInFrames={44}
          style={{
            position: 'absolute',
            top: 420,
            left: 540,
            transform: `scale(${text2Spring})`,
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            padding: '32px 64px',
            borderRadius: 24,
            border: '4px solid #ef4444',
            boxShadow: '0 25px 50px rgba(239, 68, 68, 0.4)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: props.textSize + 10, fontWeight: 900, color: props.text2Color }}>
            {props.text2}
          </div>
          <div style={{ fontFamily: FONT, fontSize: 36, color: '#94a3b8', marginTop: 8 }}>
            Sụp đổ 98% sản lượng đánh bắt
          </div>
        </Interactive.Div>
      )}
    </AbsoluteFill>
  );
};

export const defaultProps = {
  bgNen: 'nhan_y/e97c2ea126ad38.jpg',
  bgCanThung: 'nhan_y/e29c7cdd7efeb8.jpg',
  imgXeTai: 'nhan_y/bfccd7fb86b0d3.png',
  text1: '340 xe (gần 7.000 tấn)',
  text2: '7 xe (135 tấn - 2%)',
  text1Color: '#facc15',
  text2Color: '#ef4444',
  textSize: 90,
  xeWidth: 140,
  xeHeight: 67,
};
