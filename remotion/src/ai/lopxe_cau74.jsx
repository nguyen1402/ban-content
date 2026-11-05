import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anhTuongLop: z.string().describe('Ảnh bức tường lốp xe chặn dòng lũ'),
  anhMatCat: z.string().describe('Ảnh mặt cắt lòng suối'),
  anhThungLung: z.string().describe('Ảnh toàn cảnh thung lũng Bear Creek'),
  tenDiaDanh: z.string().describe('Tên địa danh hiển thị ở nhịp cuối'),
  coDiaDanh: z.number().describe('Cỡ chữ nhãn địa danh (px)'),
  nhanDx: z.number().describe('Độ lệch ngang của nhãn địa danh (px)'),
  nhanDy: z.number().describe('Độ lệch dọc của nhãn địa danh (px)'),
  doDamAnh1: z.number().describe('Độ tối ảnh nhịp 1 (0..0.5)'),
  doDamAnh2: z.number().describe('Độ tối ảnh nhịp 2 (0..0.5)'),
  doDamAnh3: z.number().describe('Độ tối ảnh nhịp 3 (0..0.5)'),
  phongNhip1: z.number().describe('Độ bật punch-in của nhịp 1 (tỉ lệ scale)'),
  zoomNhip1Tu: z.number().describe('Scale bắt đầu ảnh nhịp 1'),
  zoomNhip1Den: z.number().describe('Scale kết thúc ảnh nhịp 1'),
  zoomNhip2Tu: z.number().describe('Scale bắt đầu ảnh nhịp 2'),
  zoomNhip2Den: z.number().describe('Scale kết thúc ảnh nhịp 2'),
  zoomNhip3Tu: z.number().describe('Scale bắt đầu ảnh nhịp 3'),
  zoomNhip3Den: z.number().describe('Scale kết thúc ảnh nhịp 3'),
});

/* Lớp mờ: fade in / fade out theo frame cục bộ của Interactive.Div chứa nó */
const LopMo = ({vao, ra, dai, children}) => {
  const f = useCurrentFrame();
  let op = 1;
  if (vao > 0) {
    op = Math.min(op, interpolate(f, [0, vao], [0, 1], {...kep, easing: Easing.inOut(Easing.ease)}));
  }
  if (ra < dai - 1) {
    op = Math.min(op, interpolate(f, [ra, dai - 1], [1, 0], {...kep, easing: Easing.inOut(Easing.ease)}));
  }
  return <AbsoluteFill style={{opacity: op}}>{children}</AbsoluteFill>;
};

/* Nhịp 1: ảnh tường lốp + cú punch-in đúng frame 3 */
const Nhip1 = ({anh, toi, phong, tu, den}) => {
  const f = useCurrentFrame();
  const scale = interpolate(f, [3, 28], [1, 1 + phong], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <AbsoluteFill style={{transform: `scale(${scale})`}}>
      <AnhNen anh={anh} tu={tu} den={den} goc="50% 62%" toi={toi} />
    </AbsoluteFill>
  );
};

/* Đường cao độ kỹ thuật vẽ dần ra */
const DuongCaoDo = ({rong}) => {
  const f = useCurrentFrame();
  const p1 = interpolate(f, [0, 34], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p2 = interpolate(f, [18, 52], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const m = '#9FD3C7';
  return (
    <svg width={rong} height={120} style={{overflow: 'visible'}}>
      <line x1={0} y1={18} x2={rong * p1} y2={18} stroke={m} strokeWidth={4} strokeDasharray="22 16" strokeLinecap="round" opacity={0.9} />
      <line x1={0} y1={96} x2={rong * p2} y2={96} stroke={m} strokeWidth={4} strokeDasharray="22 16" strokeLinecap="round" opacity={0.7} />
      <line x1={0} y1={6} x2={0} y2={30} stroke={m} strokeWidth={4} opacity={p1} />
      <line x1={0} y1={84} x2={0} y2={108} stroke={m} strokeWidth={4} opacity={p2} />
    </svg>
  );
};

export const Canh = (props) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0a1512'}}>

      {/* ============ NHỊP 1 — frame 3 : xuyên qua tường lốp xe, dòng lũ cuộn xiết ============ */}
      <Interactive.Div
        name="Nhịp 1 — Tường lốp xe chặn dòng lũ"
        from={0}
        durationInFrames={99}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopMo vao={0} ra={84} dai={99}>
          <Nhip1
            anh={props.anhTuongLop}
            toi={props.doDamAnh1}
            phong={props.phongNhip1}
            tu={props.zoomNhip1Tu}
            den={props.zoomNhip1Den}
          />
        </LopMo>
      </Interactive.Div>

      {/* ============ NHỊP 2 — frame 83 : mặt cắt bùn phù sa lắng thành tầng đất mặt ============ */}
      <Interactive.Div
        name="Nhịp 2 — Mặt cắt lòng suối"
        from={83}
        durationInFrames={157}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopMo vao={16} ra={145} dai={157}>
          <AnhNen
            anh={props.anhMatCat}
            tu={props.zoomNhip2Tu}
            den={props.zoomNhip2Den}
            goc="50% 55%"
            toi={props.doDamAnh2}
          />
        </LopMo>
      </Interactive.Div>

      {/* Mũi tên động 1 — bùn lắng xuống */}
      <Interactive.Div
        name="Mũi tên lắng 1"
        from={89}
        durationInFrames={150}
        style={{position: 'absolute', left: 560, top: 300, width: 320, height: 420}}
      >
        <LopMo vao={0} ra={132} dai={150}>
          <MuiTen dx={0} dy={310} cong={26} />
        </LopMo>
      </Interactive.Div>

      {/* Mũi tên động 2 */}
      <Interactive.Div
        name="Mũi tên lắng 2"
        from={96}
        durationInFrames={143}
        style={{position: 'absolute', left: 930, top: 250, width: 320, height: 480}}
      >
        <LopMo vao={0} ra={125} dai={143}>
          <MuiTen dx={0} dy={380} cong={-26} />
        </LopMo>
      </Interactive.Div>

      {/* Mũi tên động 3 */}
      <Interactive.Div
        name="Mũi tên lắng 3"
        from={103}
        durationInFrames={136}
        style={{position: 'absolute', left: 1300, top: 300, width: 320, height: 420}}
      >
        <LopMo vao={0} ra={118} dai={136}>
          <MuiTen dx={0} dy={310} cong={26} />
        </LopMo>
      </Interactive.Div>

      {/* Đường cao độ kỹ thuật */}
      <Interactive.Div
        name="Đường cao độ bùn lắng"
        from={103}
        durationInFrames={136}
        style={{position: 'absolute', left: 380, top: 660, width: 1160, height: 120}}
      >
        <LopMo vao={0} ra={122} dai={136}>
          <DuongCaoDo rong={1160} />
        </LopMo>
      </Interactive.Div>

      {/* Vòng bút khoanh lớp đất mặt phì nhiêu */}
      <Interactive.Div
        name="Vòng khoanh lớp đất mặt"
        from={136}
        durationInFrames={103}
        style={{position: 'absolute', left: 460, top: 780, width: 1000, height: 210}}
      >
        <LopMo vao={0} ra={88} dai={103}>
          <VongBut w={1000} h={200} />
        </LopMo>
      </Interactive.Div>

      {/* ============ NHỊP 3 — frame 228 : toàn cảnh thung lũng Bear Creek ============ */}
      <Interactive.Div
        name="Nhịp 3 — Thung lũng Bear Creek"
        from={228}
        durationInFrames={64}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <LopMo vao={12} ra={999} dai={64}>
          <AnhNen
            anh={props.anhThungLung}
            tu={props.zoomNhip3Tu}
            den={props.zoomNhip3Den}
            goc="50% 50%"
            toi={props.doDamAnh3}
          />
        </LopMo>
      </Interactive.Div>

      {/* Dải tối nhẹ dưới chân khung cho nhãn địa danh dễ đọc */}
      <Interactive.Div
        name="Dải tối chân khung"
        from={228}
        durationInFrames={64}
        style={{position: 'absolute', left: 0, top: 740, width: 1920, height: 340}}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 340,
            background: 'linear-gradient(to bottom, rgba(6,20,14,0) 0%, rgba(6,20,14,0.42) 100%)',
          }}
        />
      </Interactive.Div>

      {/* Nhãn địa danh duy nhất của cảnh */}
      <Interactive.Div
        name="Nhãn địa danh Bear Creek"
        from={253}
        durationInFrames={39}
        style={{position: 'absolute', left: 1180, top: 600, width: 10, height: 10}}
      >
        <Nhan chu={props.tenDiaDanh} dx={props.nhanDx} dy={props.nhanDy} co={props.coDiaDanh} />
      </Interactive.Div>

    </AbsoluteFill>
  );
};
