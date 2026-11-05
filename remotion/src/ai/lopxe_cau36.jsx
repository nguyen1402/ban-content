import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhDam: z.string().describe('Ảnh công trình đập lốp xe cũ lúc hoàng hôn'),
  anhTuong: z.string().describe('Ảnh bức tường bê tông đắt tiền'),
  anhSoDo: z.string().describe('Ảnh sơ đồ cắt lớp kết cấu bê tông (nền trong suốt)'),
  anhXuong: z.string().describe('Ảnh xưởng làm việc đơn sơ'),
  anhHonig: z.string().describe('Ảnh chân dung nhân vật Honig (nền trong suốt)'),
  tenNhanVat: z.string().describe('Tên nhân vật hiển thị trên màn hình'),
  coTen: z.number().describe('Cỡ chữ tên nhân vật (px)'),
  mauTen: z.string().describe('Màu chữ tên nhân vật'),
  quangPanDam: z.number().describe('Biên độ pan ngang của ảnh đập lốp xe (px)'),
  phongDam: z.number().describe('Độ phóng của ảnh đập lốp xe'),
  toiDam: z.number().describe('Độ tối phủ lên ảnh đập lốp xe (0 - 0.5)'),
  tuTuong: z.number().describe('Tỉ lệ zoom bắt đầu của ảnh tường bê tông'),
  denTuong: z.number().describe('Tỉ lệ zoom kết thúc của ảnh tường bê tông'),
  toiTuong: z.number().describe('Độ tối phủ lên ảnh tường bê tông (0 - 0.5)'),
  xSoDo: z.number().describe('Toạ độ X của sơ đồ cắt lớp bê tông'),
  ySoDo: z.number().describe('Toạ độ Y của sơ đồ cắt lớp bê tông'),
  rongSoDo: z.number().describe('Chiều rộng sơ đồ cắt lớp bê tông (px)'),
  tuXuong: z.number().describe('Tỉ lệ zoom bắt đầu của ảnh xưởng làm việc'),
  denXuong: z.number().describe('Tỉ lệ zoom kết thúc của ảnh xưởng làm việc'),
  toiXuong: z.number().describe('Độ tối phủ lên ảnh xưởng làm việc (0 - 0.5)'),
  xHonig: z.number().describe('Toạ độ X của chân dung Honig'),
  yHonig: z.number().describe('Toạ độ Y của chân dung Honig'),
  rongHonig: z.number().describe('Chiều rộng chân dung Honig (px)'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // === Beat 2 @106: trượt màn hình sang trái ===
  const truot = interpolate(frame, [106, 136], [0, -1920], {
    ...kep,
    easing: Easing.inOut(Easing.cubic),
  });

  const opSoDo = interpolate(frame, [106, 126], [0, 1], {...kep});
  const scSoDo = interpolate(frame, [106, 142], [0.88, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  // === Beat 3 @277: chuyển cảnh êm sang xưởng ===
  const opXuong = interpolate(frame, [277, 308], [0, 1], {
    ...kep,
    easing: Easing.inOut(Easing.quad),
  });

  // === Beat 4 @344: ghép chân dung Honig ===
  const popHonig = spring({
    frame: Math.max(0, frame - 344),
    fps,
    config: {damping: 15, mass: 0.8, stiffness: 95},
  });
  const opHonig = interpolate(frame, [344, 364], [0, 1], {...kep});
  const yHonig = interpolate(popHonig, [0, 1], [70, 0], {...kep});
  const scHonig =
    interpolate(popHonig, [0, 1], [0.93, 1], {...kep}) *
    interpolate(frame, [344, 401], [1, 1.05], {...kep});

  // chữ tên
  const opTen = interpolate(frame, [352, 376], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.quad),
  });
  const yTen = interpolate(frame, [352, 382], [40, 0], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });
  const gachTen = interpolate(frame, [356, 388], [0, 1], {
    ...kep,
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a', overflow: 'hidden'}}>
      {/* ---------- 1. Công trình đập lốp xe (pan phải) ---------- */}
      <Interactive.Div
        name="Công trình đập lốp xe"
        from={0}
        durationInFrames={401}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${truot}px)`,
          }}
        >
          <AnhLia
            anh={props.anhDam}
            huong="phai"
            quang={props.quangPanDam}
            phong={props.phongDam}
            toi={props.toiDam}
          />
        </div>
      </Interactive.Div>

      {/* ---------- 2. Tường bê tông (trượt vào từ phải) ---------- */}
      <Interactive.Div
        name="Tường bê tông"
        from={106}
        durationInFrames={295}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${truot + 1920}px)`,
          }}
        >
          <AnhNen
            anh={props.anhTuong}
            tu={props.tuTuong}
            den={props.denTuong}
            goc="50% 45%"
            toi={props.toiTuong}
          />
        </div>
      </Interactive.Div>

      {/* ---------- 2b. Sơ đồ cắt lớp bê tông ---------- */}
      <Interactive.Div
        name="Sơ đồ cắt lớp bê tông"
        from={106}
        durationInFrames={194}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${truot + 1920}px)`,
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: props.xSoDo,
              top: props.ySoDo,
              width: props.rongSoDo,
              opacity: opSoDo,
              transform: `scale(${scSoDo})`,
              transformOrigin: '50% 50%',
            }}
          >
            <Img
              name="Sơ đồ cắt lớp"
              src={src(props.anhSoDo)}
              style={{
                width: '100%',
                display: 'block',
                filter: 'drop-shadow(0 22px 46px rgba(0,0,0,0.6))',
              }}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* ---------- 3. Xưởng làm việc (hiện êm) ---------- */}
      <Interactive.Div
        name="Xưởng làm việc"
        from={277}
        durationInFrames={124}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            opacity: opXuong,
          }}
        >
          <AnhNen
            anh={props.anhXuong}
            tu={props.tuXuong}
            den={props.denXuong}
            goc="50% 50%"
            toi={props.toiXuong}
          />
        </div>
      </Interactive.Div>

      {/* ---------- 4. Chân dung Honig ---------- */}
      <Interactive.Div
        name="Chân dung Honig"
        from={344}
        durationInFrames={57}
        style={{position: 'absolute', left: props.xHonig, top: props.yHonig, width: props.rongHonig, height: 950}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: '100%',
            opacity: opHonig,
            transform: `translateY(${yHonig}px) scale(${scHonig})`,
            transformOrigin: '50% 100%',
          }}
        >
          <Img
            name="Chân dung Honig"
            src={src(props.anhHonig)}
            style={{
              width: '100%',
              display: 'block',
              filter: 'drop-shadow(0 26px 54px rgba(0,0,0,0.55))',
            }}
          />
        </div>
      </Interactive.Div>

      {/* ---------- 4b. Tên nhân vật ---------- */}
      <Interactive.Div
        name="Tên nhân vật"
        from={352}
        durationInFrames={49}
        style={{position: 'absolute', left: 130, top: 700}}
      >
        <div style={{opacity: opTen, transform: `translateY(${yTen}px)`}}>
          <div
            style={{
              fontFamily: FONT,
              fontWeight: 800,
              fontSize: props.coTen,
              lineHeight: 1,
              letterSpacing: 8,
              color: props.mauTen,
              textShadow: '0 10px 30px rgba(0,0,0,0.6)',
            }}
          >
            {props.tenNhanVat}
          </div>
          <div
            style={{
              width: 400,
              height: 12,
              marginTop: 20,
              backgroundColor: VANG,
              transform: `scaleX(${gachTen})`,
              transformOrigin: 'left center',
            }}
          />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
