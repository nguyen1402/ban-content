import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhHonig: z.string().describe('Ảnh Giáo sư Stewart Honig trong phòng làm việc'),
  anhSoDo: z.string().describe('Ảnh sơ đồ đập lốp xe (cut-out)'),
  anhBanGiay: z.string().describe('Ảnh bàn làm việc ngập tài liệu cũ'),
  zoomHonigTu: z.number().describe('Độ phóng to đầu của ảnh Honig'),
  zoomHonigDen: z.number().describe('Độ phóng to cuối của ảnh Honig'),
  panPhai: z.number().describe('Số pixel ảnh Honig trượt sang phải'),
  zoomBanTu: z.number().describe('Độ phóng to đầu của bàn tài liệu'),
  zoomBanDen: z.number().describe('Độ phóng to cuối của bàn tài liệu'),
  zoomThemTu: z.number().describe('Hệ số zoom-out cộng thêm lúc bắt đầu beat cuối'),
  zoomThemDen: z.number().describe('Hệ số zoom-out cộng thêm ở cuối cảnh'),
  toiHonig: z.number().describe('Độ tối ảnh Honig (0..0.5)'),
  toiBan: z.number().describe('Độ tối ảnh bàn tài liệu (0..0.5)'),
  doSangDau: z.number().describe('Độ sáng lúc ảnh Honig vừa hiện lên'),
  rongSoDo: z.number().describe('Chiều rộng ảnh sơ đồ'),
  caoSoDo: z.number().describe('Chiều cao ảnh sơ đồ'),
  demSoDo: z.number().describe('Lề trắng trong khung sơ đồ'),
  mauKhung: z.string().describe('Màu nền khung sơ đồ'),
  mauVien: z.string().describe('Màu viền khung sơ đồ'),
  mauGach: z.string().describe('Màu đường gạch chéo đỏ'),
  dayGach: z.number().describe('Độ dày đường gạch chéo đỏ'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---- beat 1 (frame 4): ảnh Honig, zoom chậm + sáng dần lên ----
  const panX = interpolate(frame, [28, 58], [0, props.panPhai], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const doSang = interpolate(frame, [4, 28], [props.doSangDau, 1], {
    ...kep,
    easing: Easing.out(Easing.quad),
  });

  // ---- beat 2 (frame 30): khung sơ đồ bật lên ----
  const pop = spring({
    frame: Math.max(0, frame - 30),
    fps,
    config: {damping: 13, mass: 0.7, stiffness: 110},
  });

  // ---- beat 3 (frame 61): vệt sáng quét qua khung sơ đồ ----
  const sweepX = interpolate(frame, [61, 93], [-340, 820], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const moSoDo = interpolate(frame, [108, 128], [1, 0], kep);

  // ---- beat 4 (frame 111): wipe sang bàn tài liệu cũ ----
  const wipe = interpolate(frame, [111, 138], [0, 100], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });

  // ---- beat 5 (frame 141): zoom-out chậm + gạch chéo đỏ vẽ ra ----
  const zoomThem = interpolate(frame, [141, 195], [props.zoomThemTu, props.zoomThemDen], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });
  const lineP = interpolate(frame, [141, 173], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });

  const rongKhung = props.rongSoDo + props.demSoDo * 2;
  const caoKhung = props.caoSoDo + props.demSoDo * 2;

  return (
    <AbsoluteFill style={{backgroundColor: '#101010'}}>
      {/* ============ ẢNH GIÁO SƯ HONIG (nền, frame 0 → 145) ============ */}
      <Interactive.Div
        name="Ảnh Giáo sư Stewart Honig"
        from={0}
        durationInFrames={145}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            transform: `translateX(${panX}px)`,
            filter: `brightness(${doSang})`,
          }}
        >
          <AnhNen
            anh={props.anhHonig}
            tu={props.zoomHonigTu}
            den={props.zoomHonigDen}
            goc="42% 38%"
            toi={props.toiHonig}
          />
        </div>
      </Interactive.Div>

      {/* ============ KHUNG SƠ ĐỒ ĐẬP LỐP XE (frame 30 → 130) ============ */}
      <Interactive.Div
        name="Khung sơ đồ đập lốp xe"
        from={30}
        durationInFrames={100}
        style={{position: 'absolute', left: 1100, top: 320, width: rongKhung, height: caoKhung}}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            borderRadius: 18,
            overflow: 'hidden',
            backgroundColor: props.mauKhung,
            border: `3px solid ${props.mauVien}`,
            boxShadow: '0 26px 70px rgba(0,0,0,0.5)',
            transform: `translateY(${(1 - pop) * 70}px) scale(${0.72 + 0.28 * pop}) rotate(${(1 - pop) * 4}deg)`,
            opacity: pop * moSoDo,
          }}
        >
          <Img
            name="Ảnh sơ đồ đập lốp xe"
            src={src(props.anhSoDo)}
            from={30}
            durationInFrames={100}
            style={{
              position: 'absolute',
              left: props.demSoDo,
              top: props.demSoDo,
              width: props.rongSoDo,
              height: props.caoSoDo,
              objectFit: 'cover',
            }}
          />
          {/* vệt sáng quét */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: -140,
              width: 260,
              height: 780,
              pointerEvents: 'none',
              background:
                'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.92) 50%, rgba(255,255,255,0) 100%)',
              transform: `translateX(${sweepX}px) rotate(16deg)`,
              opacity: interpolate(frame, [61, 70, 88, 96], [0, 1, 1, 0], kep),
            }}
          />
        </div>
      </Interactive.Div>

      {/* ============ BÀN TÀI LIỆU CŨ (frame 111 → 195, wipe vào) ============ */}
      <Interactive.Div
        name="Bàn tài liệu cũ bị bỏ quên"
        from={111}
        durationInFrames={84}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            clipPath: `inset(0 ${100 - wipe}% 0 0)`,
          }}
        >
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              transform: `scale(${zoomThem})`,
            }}
          >
            <AnhNen
              anh={props.anhBanGiay}
              tu={props.zoomBanTu}
              den={props.zoomBanDen}
              goc="55% 52%"
              toi={props.toiBan}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* ============ GẠCH CHÉO ĐỎ (frame 141 → 195) ============ */}
      <Interactive.Div
        name="Đường gạch chéo đỏ"
        from={141}
        durationInFrames={54}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
          <line
            x1={690}
            y1={815}
            x2={1300}
            y2={352}
            stroke={props.mauGach}
            strokeWidth={props.dayGach}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - lineP}
          />
        </svg>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
