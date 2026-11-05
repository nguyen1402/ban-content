import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhMatCat: z.string().describe('Ảnh mặt cắt kỹ thuật của lốp nhồi sỏi'),
  anhCumLop: z.string().describe('Ảnh cụm lốp liên kết xung quanh'),
  anhDaiKhoa: z.string().describe('Ảnh dây đai nhựa và khóa kim loại (tách nền)'),
  anhCotThep: z.string().describe('Ảnh thanh cốt thép xuyên tâm (tách nền)'),
  coSo: z.string().describe('Cỡ sỏi ghi trên thước đo'),
  mau: z.string().describe('Màu nét vẽ kỹ thuật'),
  doPhong: z.number().describe('Độ phóng ban đầu của ảnh mặt cắt'),
  doPhongRa: z.number().describe('Độ phóng cuối của ảnh mặt cắt'),
  doPhongCum: z.number().describe('Độ phóng ban đầu của ảnh cụm lốp (kéo lùi)'),
  doPhongCumRa: z.number().describe('Độ phóng cuối của ảnh cụm lốp'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  /* ---------- BEAT 1 : mặt cắt lốp + thước đo ---------- */
  const fCat = frame;
  const matCatOut = interpolate(frame, [142, 164], [1, 0], kep);

  /* thước đo 2,5 cm */
  const fDo = frame - 92;
  const doP = interpolate(fDo, [0, 26], [0, 1], {...kep, easing: Easing.inOut(Easing.cubic)});
  const doTxt = interpolate(fDo, [16, 32], [0, 1], kep);
  const doTxtScale = interpolate(fDo, [16, 34], [0.82, 1], {...kep, easing: Easing.out(Easing.back(1.6))});
  const doOut = interpolate(frame, [166, 184], [1, 0], kep);

  /* ---------- BEAT 2 : mạng lưới liên kết ---------- */
  const fNet = frame - 142;
  const netDim = interpolate(frame, [205, 234], [1, 0.55], kep);

  /* ---------- BEAT 3 : dây đai + khóa kim loại ---------- */
  const fDai = frame - 205;
  const daiSpring = spring({frame: fDai, fps, config: {damping: 16, mass: 0.85, stiffness: 90}});
  const daiX = interpolate(daiSpring, [0, 1], [540, 0]);
  const daiOp = interpolate(fDai, [0, 12], [0, 1], kep);
  const daiDrift = interpolate(fDai, [0, 191], [0, -24], kep);

  /* ---------- BEAT 4 : thanh cốt thép xuyên tâm ---------- */
  const fThep = frame - 292;
  const thepEase = interpolate(fThep, [0, 46], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const thepX = interpolate(thepEase, [0, 1], [-1520, 0]);
  const thepOp = interpolate(fThep, [0, 10], [0, 1], kep);
  const thepDrift = interpolate(fThep, [0, 104], [0, -16], kep);

  const netPts = [
    [280, 320],
    [900, 200],
    [1580, 350],
    [320, 830],
    [980, 900],
    [1620, 780],
  ];
  const netLinks = [
    [0, 1],
    [1, 2],
    [0, 3],
    [1, 4],
    [2, 5],
    [3, 4],
    [4, 5],
    [0, 4],
    [1, 5],
  ];

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0d10'}}>
      {/* ===== ẢNH NỀN 2 : cụm lốp liên kết (kéo lùi mở rộng) ===== */}
      <Interactive.Div
        name="Cụm lốp liên kết xung quanh"
        from={142}
        durationInFrames={254}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anhCumLop}
          tu={props.doPhongCum}
          den={props.doPhongCumRa}
          goc="50% 52%"
          toi={0.08}
        />
      </Interactive.Div>

      {/* ===== ẢNH NỀN 1 : mặt cắt kỹ thuật của lốp nhồi sỏi ===== */}
      <Interactive.Div
        name="Mặt cắt lốp nhồi sỏi"
        from={0}
        durationInFrames={168}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, opacity: matCatOut}}>
          <AnhNen
            anh={props.anhMatCat}
            tu={props.doPhong}
            den={props.doPhongRa}
            goc="50% 48%"
            toi={0.1}
          />
        </div>
      </Interactive.Div>

      {/* ===== MẠNG LƯỚI LIÊN KẾT (vẽ dần từ frame 142) ===== */}
      <Interactive.Div
        name="Mạng lưới đường liên kết"
        from={142}
        durationInFrames={254}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: netDim}}>
          <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
            {netLinks.map(([a, b], i) => {
              const p = interpolate(fNet, [i * 1.6, i * 1.6 + 24], [0, 1], {
                ...kep,
                easing: Easing.out(Easing.cubic),
              });
              const A = netPts[a];
              const B = netPts[b];
              return (
                <line
                  key={`l-${i}`}
                  x1={A[0]}
                  y1={A[1]}
                  x2={B[0]}
                  y2={B[1]}
                  stroke={props.mau}
                  strokeWidth={6}
                  strokeLinecap="round"
                  pathLength={1}
                  strokeDasharray={1}
                  strokeDashoffset={1 - p}
                  opacity={0.9}
                />
              );
            })}
            {netPts.map((P, i) => {
              const p = interpolate(fNet, [i * 2, i * 2 + 16], [0, 1], {
                ...kep,
                easing: Easing.out(Easing.cubic),
              });
              return (
                <circle key={`n-${i}`} cx={P[0]} cy={P[1]} r={15 * p} fill={props.mau} opacity={0.95} />
              );
            })}
          </svg>
        </div>
      </Interactive.Div>

      {/* ===== THƯỚC ĐO CỠ SỎI 2,5 cm ===== */}
      <Interactive.Div
        name="Thước đo cỡ sỏi"
        from={92}
        durationInFrames={92}
        style={{position: 'absolute', left: 1170, top: 290}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 700,
            height: 520,
            opacity: doOut,
          }}
        >
          <svg width={700} height={520} style={{position: 'absolute', left: 0, top: 0}}>
            <line
              x1={90}
              y1={40}
              x2={90}
              y2={460}
              stroke={props.mau}
              strokeWidth={7}
              strokeLinecap="round"
              strokeDasharray={420}
              strokeDashoffset={420 * (1 - doP)}
            />
            <line
              x1={48}
              y1={40}
              x2={132}
              y2={40}
              stroke={props.mau}
              strokeWidth={7}
              strokeLinecap="round"
              strokeDasharray={84}
              strokeDashoffset={84 * (1 - Math.min(1, doP * 1.5))}
            />
            <line
              x1={48}
              y1={460}
              x2={132}
              y2={460}
              stroke={props.mau}
              strokeWidth={7}
              strokeLinecap="round"
              strokeDasharray={84}
              strokeDashoffset={84 * (1 - Math.max(0, (doP - 0.55) / 0.45))}
            />
          </svg>
          <div
            style={{
              position: 'absolute',
              left: 152,
              top: 200,
              fontFamily: FONT,
              fontSize: 96,
              lineHeight: 1,
              fontWeight: 800,
              letterSpacing: 1,
              color: props.mau,
              opacity: doTxt,
              transform: `scale(${doTxtScale})`,
              transformOrigin: '0% 50%',
              textShadow: '0 6px 22px rgba(0,0,0,0.85)',
              whiteSpace: 'nowrap',
            }}
          >
            {props.coSo}
          </div>
        </div>
      </Interactive.Div>

      {/* ===== DÂY ĐAI NHỰA + KHÓA KIM LOẠI ===== */}
      <Interactive.Div
        name="Dây đai nhựa và khóa kim loại"
        from={205}
        durationInFrames={191}
        style={{position: 'absolute', left: 640, top: 392}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1050,
            height: 620,
            opacity: daiOp,
            transform: `translateX(${daiX + daiDrift}px) rotate(-3deg)`,
          }}
        >
          <Img
            name="Dây đai và khóa kim loại"
            src={src(props.anhDaiKhoa)}
            style={{width: 1050, height: 620, objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>

      {/* ===== THANH CỐT THÉP XUYÊN TÂM ===== */}
      <Interactive.Div
        name="Thanh cốt thép xuyên tâm"
        from={292}
        durationInFrames={104}
        style={{position: 'absolute', left: 380, top: 282}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1190,
            height: 532,
            opacity: thepOp,
            transform: `translateX(${thepX + thepDrift}px)`,
          }}
        >
          <Img
            name="Thanh cốt thép xuyên tâm"
            src={src(props.anhCotThep)}
            style={{width: 1190, height: 532, objectFit: 'contain'}}
          />
        </div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export default Canh;
