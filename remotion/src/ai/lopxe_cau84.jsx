import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, FONT, VANG, AnhNen, AnhLia} from './thu_vien.jsx';

export const schema = z.object({
  anhDap: z.string().describe('Ảnh cận cảnh đập làm từ cành cây khô, thân gỗ và bùn đất'),
  anhNuoc: z.string().describe('Ảnh dòng suối nhỏ bị giữ lại, nước chảy chậm, đất màu lắng đọng'),
  anhNgap: z.string().describe('Ảnh toàn cảnh dải đất ngập nước xanh tốt, tràn đầy sinh khí'),
  beat1: z.number().describe('Frame bắt đầu beat 1 - đắp đập cành cây và bùn'),
  beat2: z.number().describe('Frame bắt đầu beat 2 - nước chậm lại, giữ đất màu'),
  beat3: z.number().describe('Frame bắt đầu beat 3 - vùng đất ngập nước tốt tươi'),
  zoomDau: z.number().describe('Độ phóng to bắt đầu của ảnh đập'),
  zoomCuoi: z.number().describe('Độ phóng to kết thúc của ảnh đập'),
  quangLia: z.number().describe('Quãng lia ngang của ảnh dòng nước (px)'),
  doToi: z.number().describe('Độ tối lớp phủ trên ảnh nền (0..0.5)'),
  doWipe: z.number().describe('Số frame thực hiện hiệu ứng wipe mở rộng'),
  doTruot: z.number().describe('Số frame trượt ngang của ảnh dòng nước'),
  doAmAnh: z.number().describe('Độ đậm mảng màu vàng khô tan dần ở beat 3'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const {
    anhDap,
    anhNuoc,
    anhNgap,
    beat1,
    beat2,
    beat3,
    zoomDau,
    zoomCuoi,
    quangLia,
    doToi,
    doWipe,
    doTruot,
    doAmAnh,
  } = props;

  // ---- beat 2 : ảnh dòng nước trượt mượt vào từ bên phải ----
  const f2 = frame - beat2;
  const truotX = interpolate(f2, [0, doTruot], [1920, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const doNet2 = interpolate(f2, [0, doTruot * 0.8], [0.35, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // ---- beat 3 : wipe mở rộng sang dải đất ngập nước ----
  const f3 = frame - beat3;
  const wipe = interpolate(f3, [0, doWipe], [100, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  const amAnhVang = interpolate(f3, [0, 52], [doAmAnh, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  // ---- chuyển động nền liên tục cho khung hình không bao giờ đứng yên ----
  const drift = interpolate(frame, [0, durationInFrames], [0, -26], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // ================= LỚP TRƯỚC : BEAT 1 =================
  const f1 = frame - beat1;
  const pop1 = spring({frame: Math.max(0, f1 - 14), fps, config: {damping: 200, mass: 0.7}, durationInFrames: 30});
  const opa1 = interpolate(f1, [14, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const vach1 = interpolate(f1, [26, 70], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // ================= LỚP TRƯỚC : BEAT 2 =================
  const pop2 = spring({frame: Math.max(0, f2 - 8), fps, config: {damping: 200, mass: 0.7}, durationInFrames: 28});
  const opa2 = interpolate(f2, [8, 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const vach2 = interpolate(f2, [22, 62], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const lat2 = interpolate(f2, [40, 96], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // ================= LỚP TRƯỚC : BEAT 3 =================
  const pop3 = spring({frame: Math.max(0, f3 - 8), fps, config: {damping: 200, mass: 0.7}, durationInFrames: 28});
  const opa3 = interpolate(f3, [10, 32], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const vach3 = interpolate(f3, [20, 64], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const nhip = 1 + 0.04 * Math.sin(frame / 7);

  return (
    <AbsoluteFill style={{backgroundColor: '#1a1408'}}>
      {/* ================= BEAT 1 : đập cành cây khô và bùn ================= */}
      <Interactive.Div
        name="Đập cành cây khô và bùn đất"
        from={0}
        durationInFrames={146}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={anhDap} tu={zoomDau} den={zoomCuoi} goc="50% 52%" toi={doToi} />

        {/* --- lớp trước : ảnh cắt tròn cận cảnh đập --- */}
        <div
          style={{
            position: 'absolute',
            left: 1180,
            top: 120,
            width: 420,
            height: 420,
            opacity: opa1,
            transform: `scale(${0.72 + 0.28 * pop1})`,
            transformOrigin: '50% 50%',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 420,
              height: 420,
              borderRadius: '50%',
              overflow: 'hidden',
              border: `10px solid ${VANG}`,
              boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
            }}
          >
            <Img
              src={src(anhDap)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                objectPosition: '44% 48%',
                transform: 'scale(2.05)',
              }}
            />
          </div>
          {/* vòng khoanh vẽ dần */}
          <svg
            width={470}
            height={470}
            viewBox="0 0 470 470"
            style={{position: 'absolute', left: -25, top: -25, pointerEvents: 'none'}}
          >
            <circle
              cx={235}
              cy={235}
              r={220}
              fill="none"
              stroke={VANG}
              strokeWidth={5}
              strokeLinecap="round"
              strokeDasharray={1382}
              strokeDashoffset={1382 * (1 - vach1)}
              opacity={0.95}
            />
          </svg>
        </div>

        {/* --- mũi tên chỉ đúng chỗ đắp đập --- */}
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}>
          <path
            d="M 1160 380 C 1070 350 1010 376 966 428"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            strokeDasharray={320}
            strokeDashoffset={320 * (1 - vach1)}
          />
          <path
            d="M 966 428 L 996 392"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            opacity={vach1}
          />
          <path
            d="M 966 428 L 1002 440"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            opacity={vach1}
          />
        </svg>
      </Interactive.Div>

      {/* ================= BEAT 2 : nước chậm lại, đất màu lắng đọng ================= */}
      <Interactive.Div
        name="Dòng nước chảy chậm giữ lại đất màu"
        from={143}
        durationInFrames={106}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${truotX}px)`,
            opacity: doNet2,
          }}
        >
          <AnhLia anh={anhNuoc} huong="phai" quang={quangLia} toi={doToi} />
        </div>

        {/* --- lớp trước : thẻ ảnh cận cảnh nước chảy chậm --- */}
        <div
          style={{
            position: 'absolute',
            left: 1230,
            top: 160,
            width: 450,
            height: 340,
            borderRadius: 26,
            overflow: 'hidden',
            border: '8px solid #ffffff',
            boxShadow: '0 30px 70px rgba(0,0,0,0.6)',
            opacity: opa2,
            transform: `translateY(${(1 - pop2) * 70}px) scale(${0.88 + 0.12 * pop2})`,
          }}
        >
          <Img
            src={src(anhNuoc)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: '58% 62%',
              transform: 'scale(1.75)',
            }}
          />
        </div>

        {/* --- mũi tên + hạt đất màu lắng xuống --- */}
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}>
          <path
            d="M 1180 470 C 1000 480 880 520 800 596"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            strokeDasharray={480}
            strokeDashoffset={480 * (1 - vach2)}
          />
          <path
            d="M 800 596 L 838 580"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            opacity={vach2}
          />
          <path
            d="M 800 596 L 826 628"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            opacity={vach2}
          />
        </svg>

        {/* --- hạt đất màu lắng đọng --- */}
        <div
          style={{
            position: 'absolute',
            left: 690,
            top: 650,
            width: 320,
            height: 120,
            opacity: opa2,
          }}
        >
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: 24 + i * 58,
                top: 60 - 44 * Math.sin((lat2 + i * 0.18) * Math.PI),
                width: 20,
                height: 20,
                borderRadius: '50%',
                background: '#c69a52',
                boxShadow: '0 6px 16px rgba(0,0,0,0.5)',
              }}
            />
          ))}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 6,
              height: 14,
              borderRadius: 8,
              background: 'rgba(198,154,82,0.85)',
              transform: `scaleX(${lat2})`,
              transformOrigin: '50% 50%',
            }}
          />
        </div>
      </Interactive.Div>

      {/* ================= BEAT 3 : dải đất ngập nước xanh tốt ================= */}
      <Interactive.Div
        name="Dải đất ngập nước xanh tốt"
        from={247}
        durationInFrames={117}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            clipPath: `inset(0% ${wipe}% 0% 0%)`,
            transform: `translateY(${drift}px)`,
          }}
        >
          <AnhNen anh={anhNgap} tu={1.16} den={1.02} goc="50% 55%" toi={doToi} />
          {/* mảng vàng khô tan dần nhường chỗ cho sắc xanh */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              background:
                'linear-gradient(180deg, rgba(168,124,32,1) 0%, rgba(120,96,40,1) 55%, rgba(60,52,20,1) 100%)',
              opacity: amAnhVang,
              mixBlendMode: 'soft-light',
            }}
          />
        </div>

        {/* --- lớp trước : thẻ ảnh cận cảnh vùng ngập nước --- */}
        <div
          style={{
            position: 'absolute',
            left: 140,
            top: 640,
            width: 470,
            height: 300,
            borderRadius: 26,
            overflow: 'hidden',
            border: '8px solid #ffffff',
            boxShadow: '0 30px 70px rgba(0,0,0,0.6)',
            opacity: opa3,
            transform: `translateY(${(1 - pop3) * 70}px) scale(${0.9 + 0.1 * pop3})`,
          }}
        >
          <Img
            src={src(anhNgap)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: '48% 62%',
              transform: 'scale(1.9)',
            }}
          />
          {/* chú thích duy nhất trên màn hình */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 0,
              padding: '16px 18px 18px',
              background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.82) 100%)',
              fontFamily: FONT,
              fontSize: 34,
              fontWeight: 700,
              letterSpacing: 3,
              color: '#ffffff',
              textAlign: 'center',
            }}
          >
            ĐẤT NGẬP NƯỚC
          </div>
        </div>

        {/* --- vòng khoanh nhấp nháy trên mảng xanh --- */}
        <div
          style={{
            position: 'absolute',
            left: 1330,
            top: 330,
            width: 300,
            height: 300,
            opacity: opa3,
            transform: `scale(${nhip})`,
            transformOrigin: '50% 50%',
          }}
        >
          <svg width={300} height={300} viewBox="0 0 300 300">
            <circle
              cx={150}
              cy={150}
              r={128}
              fill="none"
              stroke={VANG}
              strokeWidth={7}
              strokeLinecap="round"
              strokeDasharray={804}
              strokeDashoffset={804 * (1 - vach3)}
            />
          </svg>
        </div>

        {/* --- mũi tên nối thẻ ảnh với mảng xanh --- */}
        <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}>
          <path
            d="M 630 640 C 830 600 1050 520 1240 470"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            strokeDasharray={700}
            strokeDashoffset={700 * (1 - vach3)}
            opacity={0.95}
          />
          <path
            d="M 1240 470 L 1200 442"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            opacity={vach3}
          />
          <path
            d="M 1240 470 L 1206 504"
            fill="none"
            stroke={VANG}
            strokeWidth={7}
            strokeLinecap="round"
            opacity={vach3}
          />
        </svg>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
