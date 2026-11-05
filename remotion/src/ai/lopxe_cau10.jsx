import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  bgImage: z.string().describe('Ảnh nền Arizona 1870'),
  cowImage: z.string().describe('Ảnh bò lẻ'),
  title1: z.string().describe('Tiêu đề đầu'),
  title2: z.string().describe('Tiêu đề sau'),
});

// Component con thể hiện từng cá thể bò kèm bóng tiếp đất và blend ánh nắng sa mạc
const ConBo = ({
  anh,
  chieuRong,
  chieuCao,
  lat = false,
  doSang = 1,
  doAm = 0.25,
  doMo = 1,
  style = {},
}) => {
  return (
    <div
      style={{
        position: 'relative',
        width: chieuRong,
        height: chieuCao,
        opacity: doMo,
        ...style,
      }}
    >
      {/* Bóng đổ tiếp đất tự nhiên */}
      <div
        style={{
          position: 'absolute',
          bottom: -chieuCao * 0.08,
          left: '12%',
          width: '76%',
          height: chieuCao * 0.22,
          background: 'radial-gradient(ellipse at center, rgba(35, 20, 10, 0.75) 0%, rgba(35, 20, 10, 0) 70%)',
          borderRadius: '50%',
          filter: 'blur(6px)',
          zIndex: 1,
        }}
      />
      {/* Hình ảnh con bò với hiệu ứng blend màu sa mạc */}
      <Img
        src={src(anh)}
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          transform: lat ? 'scaleX(-1)' : 'none',
          filter: `sepia(${doAm}) brightness(${doSang}) drop-shadow(0 4px 6px rgba(0,0,0,0.35))`,
          zIndex: 2,
        }}
      />
    </div>
  );
};

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Nhịp đếm số mượt mà từ 40.000 lên 1.500.000
  const soBoHienTai = Math.round(
    interpolate(frame, [0, 120, 150, 230], [40000, 40000, 150000, 1500000], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
    })
  );

  // Hiệu ứng zoom nhẹ nền và rung lắc nhẹ khi đàn bò đạt 1.5 triệu con (quá tải)
  const doRung = interpolate(frame, [170, 210, 283], [0, 3, 2], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const lacX = Math.sin(frame * 0.8) * doRung;
  const lacY = Math.cos(frame * 0.9) * doRung;

  // Lớp bò bùng nổ (Phase 2): Tầng xa, tầng trung, tầng cận cảnh tạo mật độ nghẹt thở
  const danhSachBoBungNo = [
    // Tầng xa (background layer, nhỏ & mờ)
    {x: 100, y: 430, w: 220, h: 137, lat: false, sang: 0.9, delay: 145, z: 10},
    {x: 320, y: 440, w: 240, h: 149, lat: true, sang: 0.92, delay: 147, z: 11},
    {x: 580, y: 420, w: 230, h: 143, lat: false, sang: 0.88, delay: 148, z: 10},
    {x: 820, y: 435, w: 250, h: 155, lat: true, sang: 0.9, delay: 150, z: 12},
    {x: 1100, y: 425, w: 240, h: 149, lat: false, sang: 0.91, delay: 151, z: 11},
    {x: 1350, y: 430, w: 260, h: 161, lat: true, sang: 0.89, delay: 153, z: 10},
    {x: 1620, y: 440, w: 230, h: 143, lat: false, sang: 0.9, delay: 154, z: 11},

    // Tầng trung (midground layer)
    {x: -40, y: 520, w: 380, h: 236, lat: false, sang: 0.95, delay: 152, z: 20},
    {x: 240, y: 540, w: 410, h: 255, lat: true, sang: 0.97, delay: 155, z: 22},
    {x: 540, y: 510, w: 400, h: 248, lat: false, sang: 0.96, delay: 158, z: 21},
    {x: 860, y: 535, w: 420, h: 261, lat: true, sang: 0.98, delay: 160, z: 23},
    {x: 1200, y: 515, w: 390, h: 242, lat: false, sang: 0.95, delay: 163, z: 22},
    {x: 1500, y: 545, w: 430, h: 267, lat: true, sang: 0.97, delay: 165, z: 24},

    // Tầng tiền cảnh (foreground layer, to lớn & choán khung hình)
    {x: -80, y: 660, w: 560, h: 348, lat: false, sang: 1.05, delay: 168, z: 30},
    {x: 340, y: 680, w: 600, h: 373, lat: true, sang: 1.08, delay: 171, z: 32},
    {x: 780, y: 650, w: 620, h: 385, lat: false, sang: 1.05, delay: 175, z: 31},
    {x: 1220, y: 690, w: 590, h: 367, lat: true, sang: 1.06, delay: 178, z: 33},
    {x: 1580, y: 670, w: 540, h: 336, lat: false, sang: 1.03, delay: 182, z: 30},
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#111',
        fontFamily: FONT,
        overflow: 'hidden',
        transform: `translate(${lacX}px, ${lacY}px)`,
      }}
    >
      {/* Background Arizona với tone bụi nắng sa mạc */}
      <Interactive.Div
        name="Nền Arizona"
        from={0}
        durationInFrames={283}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={src(props.bgImage)} tu={1} den={1.12} goc="50% 60%" toi={0.15} />
      </Interactive.Div>

      {/* Lớp filter ánh sáng vàng phủ nắng sa mạc */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at 60% 20%, rgba(255, 200, 120, 0.18) 0%, rgba(180, 100, 30, 0.12) 80%)',
          mixBlendMode: 'color-burn',
          pointerEvents: 'none',
          zIndex: 5,
        }}
      />

      {/* Giai đoạn đầu: 40.000 con (thưa thớt) */}
      <Interactive.Div
        name="Giai đoạn đầu đàn bò thưa thớt"
        from={0}
        durationInFrames={155}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          opacity: interpolate(frame, [140, 155], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <Interactive.Div name="Bò 1" from={0} durationInFrames={155} style={{position: 'absolute', left: 280, top: 620}}>
          <ConBo anh={props.cowImage} chieuRong={360} chieuCao={224} doAm={0.3} doSang={0.95} />
        </Interactive.Div>
        <Interactive.Div name="Bò 2" from={10} durationInFrames={145} style={{position: 'absolute', left: 820, top: 660}}>
          <ConBo anh={props.cowImage} chieuRong={300} chieuCao={186} lat={true} doAm={0.35} doSang={1.0} />
        </Interactive.Div>
        <Interactive.Div name="Bò 3" from={20} durationInFrames={135} style={{position: 'absolute', left: 1320, top: 590}}>
          <ConBo anh={props.cowImage} chieuRong={330} chieuCao={205} doAm={0.25} doSang={0.92} />
        </Interactive.Div>
      </Interactive.Div>

      {/* Giai đoạn bùng nổ: Tăng vọt lên 1.500.000 con lấp kín khung hình */}
      <Interactive.Div
        name="Giai đoạn bùng nổ đàn bò"
        from={140}
        durationInFrames={143}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        {danhSachBoBungNo.map((bo, idx) => {
          const frameBatDau = bo.delay;
          if (frame < frameBatDau) return null;

          const doNay = spring({
            frame: frame - frameBatDau,
            fps,
            config: {damping: 14, stiffness: 120},
          });

          return (
            <Interactive.Div
              key={idx}
              name={`Đàn bò tràn ngập ${idx + 1}`}
              from={frameBatDau}
              durationInFrames={283 - frameBatDau}
              style={{
                position: 'absolute',
                left: bo.x,
                top: bo.y,
                zIndex: bo.z,
                transform: `scale(${interpolate(doNay, [0, 1], [0.5, 1])})`,
                opacity: interpolate(doNay, [0, 1], [0, 1]),
              }}
            >
              <ConBo
                anh={props.cowImage}
                chieuRong={bo.w}
                chieuCao={bo.h}
                lat={bo.lat}
                doSang={bo.sang}
                doAm={0.32}
              />
            </Interactive.Div>
          );
        })}
      </Interactive.Div>

      {/* Hiển thị số lượng trực quan tăng liên tục giữ nhịp thị giác suốt clip */}
      <Interactive.Div
        name="Bảng thống kê số lượng bò"
        from={20}
        durationInFrames={263}
        style={{
          position: 'absolute',
          left: 120,
          top: 100,
          zIndex: 50,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div style={{textShadow: '0 4px 18px rgba(0,0,0,0.85)'}}>
          <ChuNoi chu={frame < 150 ? props.title1 : props.title2} co={86} mau={frame >= 170 ? '#ffdd55' : '#ffffff'} />
        </div>

        {/* Đồng hồ số đếm trực quan thể hiện sự quá tải */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'baseline',
            gap: 12,
            background: 'rgba(20, 14, 8, 0.75)',
            border: `2px solid ${frame >= 170 ? '#e67e22' : 'rgba(255, 255, 255, 0.2)'}`,
            borderRadius: 14,
            padding: '10px 24px',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            width: 'fit-content',
          }}
        >
          <span style={{color: '#ffc83b', fontSize: 52, fontWeight: 900, letterSpacing: 2}}>
            {soBoHienTai.toLocaleString('vi-VN')}
          </span>
          <span style={{color: '#f0f0f0', fontSize: 32, fontWeight: 700}}>CON</span>
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
