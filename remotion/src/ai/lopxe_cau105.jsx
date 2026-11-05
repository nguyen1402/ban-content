import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhDayBien: z.string().describe('Ảnh đáy biển sâu ngập lốp xe cũ'),
  anhSanHo: z.string().describe('Ảnh cận cảnh rạn san hô bị lốp xe đè nát'),
  anhBaiBien: z.string().describe('Ảnh bãi biển ven bờ ngập lốp xe, sóng vỗ trắng xóa'),
  panNgang: z.number().describe('Quãng pan ngang của ảnh đáy biển (px)'),
  daiWipe: z.number().describe('Số frame của hiệu ứng wipe mở ảnh san hô'),
  daiTruot: z.number().describe('Số frame của hiệu ứng trượt ảnh bãi biển'),
  toiDayBien: z.number().describe('Độ tối của ảnh đáy biển (0-0.5)'),
  toiSanHo: z.number().describe('Độ tối của ảnh san hô (0-0.5)'),
  toiBaiBien: z.number().describe('Độ tối của ảnh bãi biển (0-0.5)'),
});

const WipeNgang = ({batDau, dai, children}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + dai], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });
  const phai = interpolate(p, [0, 1], [100, 0], kep);
  return (
    <AbsoluteFill style={{clipPath: `inset(0% ${phai}% 0% 0%)`}}>{children}</AbsoluteFill>
  );
};

const TruotSangTrai = ({batDau, dai, children}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [batDau, batDau + dai], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const x = interpolate(p, [0, 1], [100, 0], kep);
  return (
    <AbsoluteFill style={{transform: `translateX(${x}%)`}}>{children}</AbsoluteFill>
  );
};

const Hien = ({tre, dai, children}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [tre, tre + dai], [0, 1], kep);
  return <div style={{opacity: o}}>{children}</div>;
};

export const Canh = (props) => {
  const {
    anhDayBien,
    anhSanHo,
    anhBaiBien,
    panNgang,
    daiWipe,
    daiTruot,
    toiDayBien,
    toiSanHo,
    toiBaiBien,
  } = props;

  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#000000', fontFamily: FONT, overflow: 'hidden'}}>
      {/* 1. Đáy biển sâu ngập lốp xe — pan phải, từ frame 0 */}
      <Interactive.Div
        name="Đáy biển ngập lốp xe"
        from={0}
        durationInFrames={96}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhLia anh={anhDayBien} huong="phai" quang={panNgang} phong={1.06} toi={toiDayBien} />
      </Interactive.Div>

      {/* 2. Cận cảnh san hô bị đè nát — wipe ngang từ frame 87 */}
      <Interactive.Div
        name="San hô bị lốp xe đè nát"
        from={87}
        durationInFrames={117}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <WipeNgang batDau={0} dai={daiWipe}>
          <AnhNen anh={anhSanHo} tu={1.02} den={1.14} goc="50% 55%" toi={toiSanHo} />
        </WipeNgang>
      </Interactive.Div>

      {/* 3. Bãi biển ven bờ ngập lốp xe — trượt sang trái từ frame 198 */}
      <Interactive.Div
        name="Bãi biển ngập lốp xe"
        from={198}
        durationInFrames={84}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <TruotSangTrai batDau={0} dai={daiTruot}>
          <AnhNen anh={anhBaiBien} tu={1.12} den={1.02} goc="50% 60%" toi={toiBaiBien} />
        </TruotSangTrai>
      </Interactive.Div>

      {/* Nhãn ngắn "HÀNG TRIỆU LỐP" — không có con số, thay cho bộ đếm */}
      <Interactive.Div
        name="Nhãn HÀNG TRIỆU LỐP"
        from={3}
        durationInFrames={279}
        style={{position: 'absolute', left: 96, top: 112, width: 1000, height: 300}}
      >
        <Hien tre={0} dai={14}>
          <div
            style={{
              fontFamily: FONT,
              color: VANG,
              fontSize: 92,
              fontWeight: 800,
              letterSpacing: 6,
              lineHeight: 1.05,
              textShadow: '0 6px 24px rgba(0,0,0,0.65)',
            }}
          >
            HÀNG TRIỆU LỐP
          </div>
        </Hien>
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
