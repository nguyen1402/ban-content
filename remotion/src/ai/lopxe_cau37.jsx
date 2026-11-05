import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  tireDamBg: z.string().describe('Ảnh nền đập lốp xe cũ'),
  tirePileImg: z.string().describe('Ảnh đống lốp thải'),
  concreteWallImg: z.string().describe('Ảnh tường bê tông'),
  blueprintDeskBg: z.string().describe('Ảnh bàn làm việc và bản vẽ'),
  titleText: z.string().describe('Tiêu đề Beat 1'),
  splitText: z.string().describe('Tiêu đề so sánh Beat 2'),
  finalText: z.string().describe('Tiêu đề cuối Beat 3'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();

  // Hiệu ứng mở màn so sánh cho Beat 2
  const wipe = interpolate(frame, [102, 120], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#111111', fontFamily: FONT}}>
      {/* Beat 1: 0 - 102 frames (0.0s - 3.4s) */}
      <Interactive.Div name="Nền đập lốp Beat 1" from={0} durationInFrames={102} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={src(props.tireDamBg)} tu={1} den={1.08} goc="50% 50%" toi={0.25} />
      </Interactive.Div>

      <Interactive.Div name="Tiêu đề câu hỏi" from={0} durationInFrames={102} style={{position: 'absolute', left: 100, top: 120, width: 1720, height: 140}}>
        <ChuNoi chu={props.titleText} co={76} />
      </Interactive.Div>

      <Interactive.Div name="Dấu hỏi 1" from={15} durationInFrames={87} style={{position: 'absolute', left: 1300, top: 300, width: 140, height: 160}}>
        <div style={{fontSize: 130, color: VANG, fontWeight: 'bold', textShadow: '0 4px 20px rgba(0,0,0,0.85)', opacity: interpolate(frame, [15, 30, 85, 102], [0, 0.95, 0.95, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), transform: `translateY(${Math.sin((frame - 15) * 0.1) * 12}px)`}}>?</div>
      </Interactive.Div>

      <Interactive.Div name="Dấu hỏi 2" from={35} durationInFrames={67} style={{position: 'absolute', left: 1540, top: 520, width: 180, height: 200}}>
        <div style={{fontSize: 160, color: '#ffffff', fontWeight: 'bold', textShadow: '0 4px 20px rgba(0,0,0,0.85)', opacity: interpolate(frame, [35, 50, 85, 102], [0, 0.9, 0.9, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), transform: `translateY(${Math.sin((frame - 35) * 0.08) * 15}px)`}}>?</div>
      </Interactive.Div>

      <Interactive.Div name="Dấu hỏi 3" from={50} durationInFrames={52} style={{position: 'absolute', left: 1140, top: 480, width: 120, height: 140}}>
        <div style={{fontSize: 110, color: VANG, fontWeight: 'bold', textShadow: '0 4px 20px rgba(0,0,0,0.85)', opacity: interpolate(frame, [50, 65, 85, 102], [0, 0.85, 0.85, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), transform: `translateY(${Math.sin((frame - 50) * 0.12) * 10}px)`}}>?</div>
      </Interactive.Div>

      {/* Beat 2: 102 - 273 frames (3.4s - 9.1s) */}
      <Interactive.Div name="Nền đập lốp Beat 2" from={102} durationInFrames={171} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={src(props.tireDamBg)} tu={1.08} den={1.16} goc="50% 50%" toi={0.65} />
      </Interactive.Div>

      <Interactive.Div name="Màn mờ bên trái" from={102} durationInFrames={171} style={{position: 'absolute', left: 0, top: 0, width: 960, height: 1080}}>
        <div style={{width: 960, height: 1080, backgroundColor: 'rgba(15, 23, 42, 0.45)', opacity: wipe, clipPath: `inset(0 ${(1 - wipe) * 100}% 0 0)`}} />
      </Interactive.Div>

      <Interactive.Div name="Màn mờ bên phải" from={102} durationInFrames={171} style={{position: 'absolute', left: 960, top: 0, width: 960, height: 1080}}>
        <div style={{width: 960, height: 1080, backgroundColor: 'rgba(30, 41, 59, 0.45)', opacity: wipe, clipPath: `inset(0 0 0 ${(1 - wipe) * 100}%)`}} />
      </Interactive.Div>

      <Interactive.Div name="Đường phân chia so sánh" from={102} durationInFrames={171} style={{position: 'absolute', left: 958, top: 0, width: 4, height: 1080}}>
        <div style={{width: 4, height: 1080, backgroundColor: VANG, opacity: wipe, transform: `scaleY(${wipe})`, boxShadow: '0 0 16px rgba(250, 204, 21, 0.7)'}} />
      </Interactive.Div>

      <Interactive.Div name="Ảnh đống lốp thải" from={102} durationInFrames={171} style={{position: 'absolute', left: 80, top: 250, width: 800, height: 460}}>
        <div style={{width: 800, height: 460, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: wipe, transform: `translateX(${(1 - wipe) * -60}px)`}}>
          <Img src={src(props.tirePileImg)} style={{maxWidth: 800, maxHeight: 460, objectFit: 'contain', filter: 'drop-shadow(0 20px 30px rgba(0,0,0,0.85))'}} />
        </div>
      </Interactive.Div>

      <Interactive.Div name="Nhãn rác thải lốp xe" from={102} durationInFrames={171} style={{position: 'absolute', left: 80, top: 750, width: 800, height: 80}}>
        <div style={{opacity: wipe, display: 'inline-flex', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.82)', borderLeft: '6px solid #ef4444', padding: '16px 32px', borderRadius: 8}}>
          <span style={{color: '#f87171', fontSize: 46, fontWeight: 800, letterSpacing: 1}}>RÁC THẢI LỐP XE</span>
        </div>
      </Interactive.Div>

      <Interactive.Div name="Ảnh tường bê tông" from={102} durationInFrames={171} style={{position: 'absolute', left: 1040, top: 250, width: 800, height: 460}}>
        <div style={{width: 800, height: 460, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: wipe, transform: `translateX(${(1 - wipe) * 60}px)`}}>
          <Img src={src(props.concreteWallImg)} style={{maxWidth: 800, maxHeight: 460, objectFit: 'contain', filter: 'drop-shadow(0 20px 30px rgba(0,0,0,0.85))'}} />
        </div>
      </Interactive.Div>

      <Interactive.Div name="Nhãn bê tông đắt tiền" from={102} durationInFrames={171} style={{position: 'absolute', left: 1040, top: 750, width: 800, height: 80}}>
        <div style={{opacity: wipe, display: 'inline-flex', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.82)', borderLeft: '6px solid #38bdf8', padding: '16px 32px', borderRadius: 8}}>
          <span style={{color: '#38bdf8', fontSize: 46, fontWeight: 800, letterSpacing: 1}}>BÊ TÔNG ĐẮT TIỀN</span>
        </div>
      </Interactive.Div>

      <Interactive.Div name="Thẻ so sánh Rác thải vs Bê tông" from={102} durationInFrames={171} style={{position: 'absolute', left: 600, top: 80, width: 720, height: 100}}>
        <div style={{width: 720, height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#000000', borderRadius: 50, border: `3px solid ${VANG}`, boxShadow: '0 8px 32px rgba(0,0,0,0.9)', opacity: interpolate(frame, [105, 120], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), transform: `scale(${interpolate(frame, [105, 122], [0.85, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.back(1.5))})})`}}>
          <span style={{color: VANG, fontSize: 52, fontWeight: 800, letterSpacing: 1}}>{props.splitText}</span>
        </div>
      </Interactive.Div>

      {/* Beat 3: 273 - 384 frames (9.1s - 12.8s) */}
      <Interactive.Div name="Nền bàn làm việc bản vẽ" from={273} durationInFrames={111} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={src(props.blueprintDeskBg)} tu={1} den={1.25} goc="60% 40%" toi={0.35} />
      </Interactive.Div>

      <Interactive.Div name="Nhãn vị thế người giải quyết" from={273} durationInFrames={111} style={{position: 'absolute', left: 150, top: 180, width: 1620, height: 160}}>
        <ChuNoi chu={props.finalText} co={84} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
