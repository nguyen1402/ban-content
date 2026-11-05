import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

export const schema = z.object({
  anhNen: z.string().describe('Ảnh nền đại công trường xử lý ô nhiễm nhìn từ trên cao'),
  anhHazmat: z.string().describe('Ảnh tư liệu cận cảnh công nhân hazmat vét dầu'),
  anhDau: z.string().describe('Ảnh con dấu niêm phong Superfund'),
  chuDau: z.string().describe('Tên hồ sơ in trên đầu tài liệu'),
  soNam: z.number().describe('Số năm kéo dài của dự án (đúng con số lời bình nói)'),
  nhanNam: z.string().describe('Nhãn đơn vị in cạnh con số'),
  coNam: z.number().describe('Cỡ chữ con số trên niên biểu'),
  mauNamDau: z.string().describe('Màu chữ con số'),
  mauNamCuoi: z.string().describe('Màu chữ nhãn đơn vị'),
  doDamNen: z.number().describe('Độ tối lớp phủ trên ảnh nền'),
  rongKhungAnh: z.number().describe('Bề ngang khung ảnh tư liệu'),
  caoKhungAnh: z.number().describe('Bề cao khung ảnh tư liệu'),
});

const MacDinh = {
  anhNen: 'nhan_y/64afb5bae0fd75.jpg',
  anhHazmat: 'nhan_y/6dbee14d24bb31.jpg',
  anhDau: 'nhan_y/3ff5e4dffc7495.png',
  chuDau: 'SUPERFUND',
  soNam: 20,
  nhanNam: 'NĂM',
  coNam: 96,
  mauNamDau: '#ffffff',
  mauNamCuoi: '#ffcf3f',
  doDamNen: 0.18,
  rongKhungAnh: 760,
  caoKhungAnh: 520,
};

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ---------- Khung ảnh công nhân hazmat (beat 4 → 114 → thu nhỏ sang trái) ----------
  const vaoSpring = spring({frame: frame - 4, fps, config: {damping: 200}, durationInFrames: 48});
  const truotVao = interpolate(frame, [4, 48], [330, 0], {...CL, easing: Easing.out(Easing.cubic)});
  const thuNho = interpolate(frame, [114, 148], [0, 1], {...CL, easing: Easing.inOut(Easing.cubic)});
  const tx = truotVao + thuNho * -430;
  const ty = thuNho * -32;
  const sc = 1 - thuNho * 0.34;
  const opaAnh = interpolate(frame, [4, 22], [0, 1], CL);
  const zoomTrong = 1.03 + 0.11 * (frame / 217);

  // ---------- Hồ sơ Superfund (beat 114) ----------
  const dxHoSo = interpolate(frame, [114, 148], [190, 0], {...CL, easing: Easing.out(Easing.cubic)});
  const opaHoSo = interpolate(frame, [114, 132], [0, 1], CL);

  // ---------- Con dấu đóng xuống ----------
  const dapSpring = spring({frame: frame - 128, fps, config: {damping: 14, mass: 0.7, stiffness: 130}});
  const coDau = 2.25 - 1.25 * dapSpring;
  const xoayDau = -22 + 14 * dapSpring;
  const opaDau = interpolate(frame, [128, 138], [0, 1], CL);

  // ---------- Niên biểu: con số năm kéo dài (beat 168) ----------
  const opaNiên = interpolate(frame, [168, 181], [0, 1], CL);
  const truotNiên = interpolate(frame, [168, 184], [34, 0], {...CL, easing: Easing.out(Easing.cubic)});
  const tienTrinh = interpolate(frame, [172, 214], [0, 1], {...CL, easing: Easing.linear});

  const rongKhung = props.rongKhungAnh;
  const caoKhung = props.caoKhungAnh;

  const vachDai = 800;
  const xDai = 300;
  const yDai = 92;

  return (
    <AbsoluteFill style={{backgroundColor: '#0b1410'}}>
      {/* NỀN: đại công trường, luôn hiện từ frame 0 tới cuối */}
      <Interactive.Div
        name="Nền đại công trường"
        from={0}
        durationInFrames={217}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen anh={props.anhNen} tu={1} den={1.1} goc="50% 45%" toi={props.doDamNen} />
      </Interactive.Div>

      {/* KHUNG ẢNH TƯ LIỆU: công nhân hazmat */}
      <Interactive.Div
        name="Khung ảnh công nhân hazmat"
        from={4}
        durationInFrames={213}
        style={{position: 'absolute', left: 580, top: 280, width: rongKhung, height: caoKhung}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: rongKhung,
            height: caoKhung,
            boxSizing: 'border-box',
            padding: 14,
            background: '#f4ecdc',
            borderRadius: 6,
            boxShadow: '0 34px 80px rgba(0,0,0,0.55)',
            opacity: opaAnh * (0.55 + 0.45 * vaoSpring),
            transform: `translate(${tx}px, ${ty}px) scale(${sc})`,
          }}
        >
          <div style={{width: '100%', height: '100%', overflow: 'hidden', borderRadius: 2, background: '#20211c'}}>
            <Img
              name="Công nhân hazmat vét dầu"
              src={src(props.anhHazmat)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: `scale(${zoomTrong})`,
              }}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* HỒ SƠ SUPERFUND + CON DẤU */}
      <Interactive.Div
        name="Hồ sơ Superfund"
        from={114}
        durationInFrames={103}
        style={{position: 'absolute', left: 1010, top: 200, width: 780, height: 640}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 780,
            height: 640,
            background: '#f7f1e3',
            border: '1px solid #ddd0b4',
            borderRadius: 8,
            boxShadow: '0 38px 90px rgba(0,0,0,0.6)',
            overflow: 'hidden',
            opacity: opaHoSo,
            transform: `translateX(${dxHoSo}px)`,
          }}
        >
          <div style={{position: 'absolute', left: 0, top: 0, width: 780, height: 96, background: '#1e3b2e'}} />
          <div
            style={{
              position: 'absolute',
              left: 40,
              top: 24,
              fontFamily: FONT,
              fontSize: 52,
              fontWeight: 800,
              letterSpacing: 6,
              color: '#f7f1e3',
            }}
          >
            {props.chuDau}
          </div>

          {[560, 640, 500, 620, 452].map((w, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: 44,
                top: 150 + i * 62,
                width: w,
                height: 14,
                borderRadius: 7,
                background: '#d6cab0',
              }}
            />
          ))}

          <div
            style={{
              position: 'absolute',
              left: 130,
              top: 112,
              width: 520,
              height: 520,
              transform: `scale(${coDau}) rotate(${xoayDau}deg)`,
              transformOrigin: '50% 50%',
              opacity: opaDau,
            }}
          >
            <Img
              name="Con dấu Superfund"
              src={src(props.anhDau)}
              style={{width: 520, height: 520, objectFit: 'contain'}}
            />
          </div>
        </div>
      </Interactive.Div>

      {/* NIÊN BIỂU: DỰ ÁN KÉO DÀI BAO NHIÊU NĂM */}
      <Interactive.Div
        name="Niên biểu số năm dự án"
        from={168}
        durationInFrames={49}
        style={{position: 'absolute', left: 240, top: 880, width: 1440, height: 180}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1440,
            height: 180,
            borderRadius: 14,
            background: 'rgba(10,20,16,0.42)',
            border: '1px solid rgba(255,255,255,0.12)',
            opacity: opaNiên,
            transform: `translateY(${truotNiên}px)`,
          }}
        />

        <div
          style={{
            position: 'absolute',
            left: 44,
            top: 30,
            display: 'flex',
            alignItems: 'baseline',
            gap: 16,
            opacity: opaNiên,
            transform: `translateY(${truotNiên}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: props.coNam,
              fontWeight: 800,
              color: props.mauNamDau,
              textShadow: '0 8px 24px rgba(0,0,0,0.65)',
              lineHeight: 1,
            }}
          >
            {props.soNam}
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: Math.round(props.coNam * 0.4),
              fontWeight: 700,
              letterSpacing: 4,
              color: props.mauNamCuoi,
              textShadow: '0 8px 24px rgba(0,0,0,0.65)',
              lineHeight: 1,
            }}
          >
            {props.nhanNam}
          </div>
        </div>

        <div
          style={{
            position: 'absolute',
            left: xDai,
            top: yDai,
            width: vachDai,
            height: 8,
            borderRadius: 4,
            background: 'rgba(255,255,255,0.28)',
            opacity: opaNiên,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: xDai,
            top: yDai,
            width: vachDai * tienTrinh,
            height: 8,
            borderRadius: 4,
            background: VANG,
            opacity: opaNiên,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: xDai + vachDai * tienTrinh - 17,
            top: yDai - 13,
            width: 34,
            height: 34,
            borderRadius: 17,
            background: VANG,
            border: '4px solid #ffffff',
            boxSizing: 'border-box',
            boxShadow: '0 6px 18px rgba(0,0,0,0.55)',
            opacity: opaNiên,
          }}
        />
      </Interactive.Div>
    </AbsoluteFill>
  );
};

Canh.defaultProps = MacDinh;
