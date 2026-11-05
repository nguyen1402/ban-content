import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhNen: z.string().describe('Ảnh thung lũng hoang vu có tàn tích đập gỗ của hải ly'),
  anhNuoc: z.string().describe('Ảnh dòng nước mưa lũ cuồn cuộn'),
  anhDat: z.string().describe('Ảnh lớp đất màu bị dòng nước cuốn phăng'),
  anhRanh: z.string().describe('Ảnh cận cảnh rãnh vực xói lở sâu hoắm'),
  f1: z.number().describe('Frame bắt đầu nhịp 1 - thung lũng tàn tích đập'),
  f2: z.number().describe('Frame bắt đầu nhịp 2 - nước lũ cuồn cuộn'),
  f3: z.number().describe('Frame bắt đầu nhịp 3 - đất màu bị cuốn trôi'),
  f4: z.number().describe('Frame bắt đầu nhịp 4 - rãnh vực xói lở'),
  dai1: z.number().describe('Số frame tồn tại của ảnh thung lũng (đè dưới ảnh nước lũ)'),
  dai2: z.number().describe('Số frame tồn tại của ảnh nước lũ (đè dưới ảnh đất màu)'),
  dai3: z.number().describe('Số frame tồn tại của ảnh đất màu (đè dưới ảnh rãnh vực)'),
  dai4: z.number().describe('Số frame tồn tại của ảnh rãnh vực (đến hết shot)'),
  zoomNenTu: z.number().describe('Tỉ lệ zoom đầu của ảnh thung lũng'),
  zoomNenDen: z.number().describe('Tỉ lệ zoom cuối của ảnh thung lũng'),
  zoomNuocTu: z.number().describe('Tỉ lệ zoom đầu của ảnh nước lũ (pull-back)'),
  zoomNuocDen: z.number().describe('Tỉ lệ zoom cuối của ảnh nước lũ'),
  zoomDatTu: z.number().describe('Tỉ lệ zoom đầu của ảnh đất màu'),
  zoomDatDen: z.number().describe('Tỉ lệ zoom cuối của ảnh đất màu'),
  zoomRanhTu: z.number().describe('Tỉ lệ zoom đầu của ảnh rãnh vực'),
  zoomRanhDen: z.number().describe('Tỉ lệ zoom cuối của ảnh rãnh vực'),
  daiTruot: z.number().describe('Số frame trượt của hiệu ứng chuyển ảnh'),
  punchDau: z.number().describe('Tỉ lệ punch-in tức thời của ảnh rãnh vực'),
  punchCuoi: z.number().describe('Tỉ lệ punch-in chậm dần của ảnh rãnh vực'),
  toiNen: z.number().describe('Độ tối lớp phủ của ảnh thung lũng'),
  toiNuoc: z.number().describe('Độ tối lớp phủ của ảnh nước lũ'),
  toiDat: z.number().describe('Độ tối lớp phủ của ảnh đất màu'),
  toiRanh: z.number().describe('Độ tối lớp phủ của ảnh rãnh vực'),
  toiVien: z.number().describe('Độ tối vignette bốn góc khung hình'),
});

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

// ---- Bảng màu / font an toàn (dùng đồ của thư viện nếu là chuỗi) ----
const FF = typeof FONT === 'string' ? FONT : 'system-ui, "Segoe UI", Roboto, sans-serif';
const VANG_S = typeof VANG === 'string' ? VANG : '#e9c46a';
const EM_S = typeof EM === 'string' ? EM : '#7fd1c1';
const TRANG = '#f6f0e3';

const hien = (f, bd, dai = 16) => interpolate(f, [bd, bd + dai], [0, 1], CLAMP);
const nhichLen = (f, bd, dai = 22, tu = 40) =>
  interpolate(f, [bd, bd + dai], [tu, 0], {...CLAMP, easing: Easing.out(Easing.cubic)});

// ---- Lớp trước: thẻ ảnh cận cảnh (photo card, KHÔNG còn nhãn chữ) ----
const TheAnh = ({anh, left, top, width, height, gocAnh = '50% 50%', phong = 1, doMo = 1, xoay = 0, dichY = 0}) => (
  <div
    style={{
      position: 'absolute',
      left,
      top,
      width,
      height,
      opacity: doMo,
      transform: `translateY(${dichY}px) rotate(${xoay}deg)`,
      borderRadius: 12,
      overflow: 'hidden',
      border: `6px solid ${TRANG}`,
      boxShadow: '0 30px 70px rgba(0,0,0,0.68)',
      backgroundColor: '#0e0d0b',
    }}
  >
    <Img
      src={src(anh)}
      style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: gocAnh, transform: `scale(${phong})`}}
    />
  </div>
);

// ---- Lớp trước: vòng khoanh vẽ dần quanh đúng chi tiết ----
const Vong = ({cx, cy, rx, ry, tien, mau = VANG_S, day = 5}) => (
  <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, pointerEvents: 'none'}}>
    <ellipse
      cx={cx}
      cy={cy}
      rx={rx}
      ry={ry}
      fill="none"
      stroke={mau}
      strokeWidth={day}
      pathLength={1}
      strokeDasharray="1 1"
      strokeDashoffset={1 - Math.min(1, Math.max(0, tien))}
      strokeLinecap="round"
    />
    <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={mau} strokeWidth={day * 4} opacity={0.16 * tien} />
  </svg>
);

// ---- Lớp trước: chương mục góc trên trái — chỉ là dấu nhịp, KHÔNG số ----
const DauNhip = ({doMo}) => (
  <div style={{position: 'absolute', left: 80, top: 72, opacity: doMo, display: 'flex', alignItems: 'center', gap: 16}}>
    <div
      style={{
        width: 10,
        height: 64,
        borderRadius: 5,
        background: VANG_S,
        boxShadow: '0 4px 18px rgba(0,0,0,0.9)',
      }}
    />
    <div
      style={{
        width: 26,
        height: 26,
        borderRadius: '50%',
        border: `6px solid ${VANG_S}`,
        boxShadow: '0 4px 18px rgba(0,0,0,0.9)',
      }}
    />
  </div>
);

// ---- Lớp trước: mũi tên chỉ hướng dòng chảy ----
const MuiChevron = ({x, y, doMo, mau = EM_S, co = 52}) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: co,
      height: co,
      opacity: doMo,
      borderTop: `7px solid ${mau}`,
      borderRight: `7px solid ${mau}`,
      transform: 'rotate(45deg)',
      filter: 'drop-shadow(0 0 10px rgba(0,0,0,0.65))',
    }}
  />
);

// ---- Lớp trước: thước đo chiều sâu (chỉ vạch đo, KHÔNG con số) ----
const DoCao = ({x, y1, y2, tien}) => {
  const h = Math.max(0, (y2 - y1) * tien);
  const moDau = Math.min(1, tien * 3);
  const moCuoi = Math.max(0, (tien - 0.65) / 0.35);
  return (
    <>
      <div style={{position: 'absolute', left: x - 1, top: y1, width: 3, height: h, background: EM_S, opacity: 0.95}} />
      <div style={{position: 'absolute', left: x - 18, top: y1 - 2, width: 36, height: 3, background: EM_S, opacity: moDau}} />
      <div style={{position: 'absolute', left: x - 18, top: y1 + h - 1, width: 36, height: 3, background: EM_S, opacity: moCuoi}} />
      <div
        style={{
          position: 'absolute',
          left: x - 22,
          top: y1 + h - 1,
          width: 0,
          height: 0,
          opacity: moCuoi,
          borderLeft: '16px solid transparent',
          borderRight: '16px solid transparent',
          borderTop: `22px solid ${EM_S}`,
          filter: 'drop-shadow(0 6px 14px rgba(0,0,0,0.6))',
        }}
      />
    </>
  );
};

// ---- Lớp trước: lát cắt đất mặt vẽ bằng CSS (không tái sử dụng ảnh nền) ----
const LatCatDat = ({doMo}) => (
  <div
    style={{
      position: 'absolute',
      left: 1400,
      top: 592,
      width: 300,
      height: 300,
      borderRadius: '50%',
      overflow: 'hidden',
      border: `8px solid ${TRANG}`,
      boxShadow: '0 30px 70px rgba(0,0,0,0.7)',
      opacity: doMo,
      transform: `scale(${0.86 + 0.14 * doMo})`,
      backgroundColor: '#3a2a1a',
    }}
  >
    <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: '18%', background: '#5f7d3a'}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: '18%', height: '24%', background: '#7a4d24'}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: '42%', height: '26%', background: '#5e3a1c'}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: '68%', height: '18%', background: '#a9865a'}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: '86%', height: '14%', background: '#cbb78e'}} />
    <div
      style={{
        position: 'absolute',
        left: '30%',
        top: '18%',
        width: '9%',
        height: '60%',
        background: 'rgba(0,0,0,0.38)',
        transform: 'rotate(8deg)',
        transformOrigin: 'top center',
      }}
    />
    <div style={{position: 'absolute', left: 0, right: 0, top: '42%', height: 2, background: 'rgba(246,240,227,0.6)'}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: '68%', height: 2, background: 'rgba(246,240,227,0.6)'}} />
  </div>
);

export const Canh = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Nhịp 2: ảnh nước lũ lướt vào từ bên phải
  const truot2 = interpolate(
    frame,
    [props.f2, props.f2 + props.daiTruot],
    [100, 0],
    {...CLAMP, easing: Easing.out(Easing.cubic)}
  );

  // Nhịp 3: ảnh đất màu trượt sang từ bên trái
  const truot3 = interpolate(
    frame,
    [props.f3, props.f3 + props.daiTruot],
    [-100, 0],
    {...CLAMP, easing: Easing.out(Easing.cubic)}
  );

  // Nhịp 4: punch-in nhanh rồi trôi chậm
  const punch4 = interpolate(
    frame,
    [props.f4, props.f4 + 12, props.f4 + 60],
    [1, props.punchDau, props.punchCuoi],
    {...CLAMP, easing: Easing.out(Easing.cubic)}
  );

  // ----- Lớp trước nhịp 1: vòng khoanh đập gỗ + thẻ ảnh cận cảnh -----
  const vong1 = interpolate(frame, [22, 58], [0, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});
  const the1 = hien(frame, 38, 18);
  const the1Len = nhichLen(frame, 38, 22, 40);

  // ----- Lớp trước nhịp 2: dòng chảy cuồn cuộn (không con số) -----
  const tf2 = Math.max(0, frame - props.f2);
  const chay = (tf2 * 6) % 150;
  const mo2 = hien(frame, props.f2 + 8, 18);
  const the2 = hien(frame, props.f2 + 18, 20);
  const the2Len = nhichLen(frame, props.f2 + 18, 24, 36);

  // ----- Lớp trước nhịp 3: thanh đất bị rửa trôi + lát cắt tròn -----
  const tf3 = Math.max(0, frame - props.f3);
  const datFill = interpolate(tf3, [6, 46], [0, 0.78], {...CLAMP, easing: Easing.out(Easing.cubic)});
  const mo3 = hien(frame, props.f3 + 6, 16);
  const mo3b = hien(frame, props.f3 + 14, 18);

  // ----- Lớp trước nhịp 4: vòng khoanh + thước đo + thẻ cận cảnh -----
  const tf4 = Math.max(0, frame - props.f4);
  const vong4 = interpolate(tf4, [8, 44], [0, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});
  const do4 = interpolate(tf4, [26, 62], [0, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});
  const the4 = hien(frame, props.f4 + 16, 20);
  const the4Len = nhichLen(frame, props.f4 + 16, 24, 44);

  // =====================================================================
  // MỖI ẢNH NỀN CHỈ ĐƯỢC MOUNT TRONG ĐÚNG MỘT KHỐI DUY NHẤT.
  // Khối trước kéo dài tới khi khối kế tiếp phủ kín (kể cả lúc trượt),
  // không bao giờ quay lại ảnh cũ; khối cuối kéo tới frame cuối của shot.
  // Không có con số nào trên màn hình: lời thoại không đọc số nào cả.
  // Interactive.Div dùng số literal để editor tương tác nhận diện được.
  // =====================================================================

  return (
    <AbsoluteFill style={{backgroundColor: '#0b0a08', overflow: 'hidden'}}>

      {/* NHỊP 1 — thung lũng tàn tích đập hải ly, push-in chậm */}
      <Interactive.Div
        name="Nhịp 1 - Thung lũng tàn tích đập hải ly"
        from={0}
        durationInFrames={160}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <AnhNen
          anh={props.anhNen}
          tu={props.zoomNenTu}
          den={props.zoomNenDen}
          goc="50% 45%"
          toi={props.toiNen}
        />
      </Interactive.Div>

      {/* NHỊP 2 — nước lũ cuồn cuộn lướt vào, pull-back nhẹ */}
      <Interactive.Div
        name="Nhịp 2 - Dòng nước lũ cuồn cuộn"
        from={130}
        durationInFrames={180}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${truot2}%)`,
          }}
        >
          <AnhNen
            anh={props.anhNuoc}
            tu={props.zoomNuocTu}
            den={props.zoomNuocDen}
            goc="50% 55%"
            toi={props.toiNuoc}
          />
        </div>
      </Interactive.Div>

      {/* NHỊP 3 — đất màu bị cuốn phăng, trượt sang từ trái (mount DUY NHẤT) */}
      <Interactive.Div
        name="Nhịp 3 - Lớp đất màu bị cuốn trôi"
        from={280}
        durationInFrames={180}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${truot3}%)`,
          }}
        >
          <AnhNen
            anh={props.anhDat}
            tu={props.zoomDatTu}
            den={props.zoomDatDen}
            goc="50% 60%"
            toi={props.toiDat}
          />
        </div>
      </Interactive.Div>

      {/* NHỊP 4 — punch-in cận cảnh rãnh vực, giữ tới hết shot */}
      <Interactive.Div
        name="Nhịp 4 - Rãnh vực xói lở sâu hoắm"
        from={430}
        durationInFrames={170}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `scale(${punch4})`,
            transformOrigin: '50% 50%',
          }}
        >
          <AnhNen
            anh={props.anhRanh}
            tu={props.zoomRanhTu}
            den={props.zoomRanhDen}
            goc="50% 50%"
            toi={props.toiRanh}
          />
        </div>
      </Interactive.Div>

      {/* Vignette nhẹ giữ khung hình luôn đầy và tập trung */}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 52%, rgba(0,0,0,${props.toiVien}) 100%)`,
        }}
      />

      {/* ================= LỚP TRƯỚC 1 — khoanh đập gỗ + thẻ ảnh cận cảnh (không nhãn) ================= */}
      <Interactive.Div
        name="Lớp trước 1 - Khoanh tàn tích đập gỗ + thẻ ảnh cận cảnh"
        from={0}
        durationInFrames={130}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}
      >
        <DauNhip doMo={hien(frame, 6, 16)} />
        <Vong cx={1150} cy={470} rx={215} ry={142} tien={vong1} />
        <TheAnh
          anh={props.anhNen}
          left={1352}
          top={676}
          width={392}
          height={258}
          gocAnh="62% 40%"
          phong={1.85}
          xoay={-3.5}
          doMo={the1}
          dichY={the1Len}
        />
      </Interactive.Div>

      {/* ================= LỚP TRƯỚC 2 — mũi tên dòng chảy cuồn cuộn (không con số) ================= */}
      <Interactive.Div
        name="Lớp trước 2 - Mũi tên dòng nước lũ cuồn cuộn"
        from={130}
        durationInFrames={150}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}
      >
        <DauNhip doMo={hien(frame, props.f2 + 6, 16)} />
        {Array.from({length: 10}).map((_, i) => {
          const x = 520 + ((i * 110 + chay) % 1000);
          const y = 330 + (i % 3) * 92;
          return <MuiChevron key={i} x={x} y={y} doMo={0.9 * mo2} co={i % 3 === 1 ? 44 : 56} />;
        })}
        <TheAnh
          anh={props.anhNuoc}
          left={1418}
          top={128}
          width={366}
          height={242}
          gocAnh="50% 50%"
          phong={1.7}
          xoay={3}
          doMo={the2}
          dichY={the2Len}
        />
      </Interactive.Div>

      {/* ================= LỚP TRƯỚC 3 — thanh đất bị rửa trôi + lát cắt CSS (không con số) ================= */}
      <Interactive.Div
        name="Lớp trước 3 - Thanh đất bị rửa trôi + lát cắt đất mặt"
        from={280}
        durationInFrames={150}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}
      >
        <DauNhip doMo={mo3} />
        <div
          style={{
            position: 'absolute',
            left: 120,
            top: 792,
            width: 720,
            opacity: mo3,
            transform: `translateY(${(1 - mo3) * 26}px)`,
          }}
        >
          <div
            style={{
              width: '100%',
              height: 30,
              background: 'rgba(246,240,227,0.18)',
              border: '2px solid rgba(246,240,227,0.4)',
              borderRadius: 15,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${datFill * 100}%`,
                height: '100%',
                background: `linear-gradient(90deg, ${VANG_S}, ${EM_S})`,
              }}
            />
          </div>
          <div
            style={{
              marginTop: 14,
              marginLeft: `${datFill * 100}%`,
              width: 0,
              height: 0,
              borderLeft: '14px solid transparent',
              borderRight: '14px solid transparent',
              borderTop: `20px solid ${EM_S}`,
              filter: 'drop-shadow(0 6px 14px rgba(0,0,0,0.6))',
            }}
          />
        </div>
        {/* Lát cắt đất mặt vẽ CSS: không mount lại props.anhDat */}
        <LatCatDat doMo={mo3b} />
      </Interactive.Div>

      {/* ================= LỚP TRƯỚC 4 — khoanh rãnh vực + thước đo chiều sâu + thẻ ảnh ================= */}
      <Interactive.Div
        name="Lớp trước 4 - Khoanh rãnh vực + thước đo chiều sâu"
        from={430}
        durationInFrames={170}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, pointerEvents: 'none'}}
      >
        <DauNhip doMo={hien(frame, props.f4 + 6, 16)} />
        <Vong cx={960} cy={540} rx={330} ry={250} tien={vong4} />
        <DoCao x={600} y1={480} y2={820} tien={do4} />
        <TheAnh
          anh={props.anhRanh}
          left={1352}
          top={676}
          width={392}
          height={258}
          gocAnh="50% 50%"
          phong={1.9}
          xoay={3}
          doMo={the4}
          dichY={the4Len}
        />
      </Interactive.Div>

    </AbsoluteFill>
  );
};
