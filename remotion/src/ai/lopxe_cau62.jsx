import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  anh_nen_suoi: z.string().describe('Ảnh nền thung lũng suối khô nhìn từ trên cao'),
  anh_song_bun: z.string().describe('Ảnh lớp sóng bùn đỏ (PNG tách nền)'),
  anh_canh_cay: z.string().describe('Ảnh cành cây khô trôi (PNG tách nền)'),
  anh_cat_phu_sa: z.string().describe('Ảnh mây cát phù sa (PNG tách nền)'),
  anh_dap_lop: z.string().describe('Ảnh đập lốp xe đang thi công'),
  anh_john_king: z.string().describe('Ảnh tư liệu ông John King bên bờ vực'),
  anh_ranh_xoi: z.string().describe('Ảnh cận cảnh rãnh xói sâu nước xiết'),
  ten_nhan_vat: z.string().describe('Tên nhân vật hiển thị ở góc dưới'),
  co_ten: z.number().describe('Cỡ chữ tên nhân vật (px)'),
  phong_nen1_tu: z.number().describe('Độ phóng nền suối lúc bắt đầu'),
  phong_nen1_den: z.number().describe('Độ phóng nền suối lúc kết thúc'),
  phong_dap_tu: z.number().describe('Độ phóng nền đập lốp xe lúc bắt đầu'),
  phong_dap_den: z.number().describe('Độ phóng nền đập lốp xe lúc kết thúc'),
  phong_king_tu: z.number().describe('Độ phóng ảnh John King lúc bắt đầu'),
  phong_king_den: z.number().describe('Độ phóng ảnh John King lúc kết thúc'),
  quang_lia: z.number().describe('Quãng lia ngang của cảnh rãnh xói (px)'),
  phong_xoi: z.number().describe('Độ phóng cảnh rãnh xói'),
  do_mo_cat: z.number().describe('Độ đục của lớp mây cát phù sa'),
  do_toi: z.number().describe('Độ tối phủ lên ảnh nền'),
});

const LopTruot = ({anh, rong, cao, tu, den, dai, do_mo}) => {
  const f = useCurrentFrame();
  const hien = interpolate(f, [0, 24], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const p = interpolate(f, [0, dai], [0, 1], kep);
  const x = tu.x + (den.x - tu.x) * p;
  const y = tu.y + (den.y - tu.y) * p;
  const r = tu.r + (den.r - tu.r) * p;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: rong,
        height: cao,
        opacity: hien * do_mo,
        transform: `translate(${x}px, ${y}px) rotate(${r}deg)`,
      }}
    >
      <Img src={src(anh)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
    </div>
  );
};

const TenNhan = ({ten, co}) => {
  const f = useCurrentFrame();
  const vao = interpolate(f, [0, 18], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  const y = interpolate(f, [0, 18], [34, 0], {...kep, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 24, opacity: vao, transform: `translateY(${y}px)`}}>
      <div style={{width: 10, height: co * 1.05, backgroundColor: VANG, borderRadius: 2}} />
      <div
        style={{
          fontFamily: FONT,
          fontSize: co,
          fontWeight: 800,
          color: '#ffffff',
          letterSpacing: 5,
          whiteSpace: 'nowrap',
          textShadow: '0 6px 22px rgba(0,0,0,0.72)',
        }}
      >
        {ten}
      </div>
    </div>
  );
};

export const Canh = (props) => {
  const frame = useCurrentFrame();

  const opa_king = interpolate(frame, [212, 226], [0, 1], kep);
  const opa_xoi = interpolate(frame, [272, 286], [0, 1], kep);

  return (
    <AbsoluteFill style={{backgroundColor: '#20110a'}}>
      {/* NHỊP 1 — thung lũng suối khô nhìn từ trên cao */}
      <Interactive.Div
        name="Nền thung lũng suối khô"
        from={0}
        durationInFrames={125}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anh_nen_suoi}
          tu={props.phong_nen1_tu}
          den={props.phong_nen1_den}
          goc="42% 30%"
          toi={props.do_toi}
        />
      </Interactive.Div>

      {/* NHỊP 1 — lớp sóng bùn đỏ trượt vào từ phía trên trái */}
      <Interactive.Div
        name="Lớp sóng bùn đỏ"
        from={3}
        durationInFrames={122}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <LopTruot
          anh={props.anh_song_bun}
          rong={1500}
          cao={754}
          tu={{x: -430, y: -300, r: -8}}
          den={{x: 70, y: 130, r: 2}}
          dai={122}
          do_mo={0.97}
        />
      </Interactive.Div>

      {/* NHỊP 2 — mây cát phù sa nổi lên tạo lớp */}
      <Interactive.Div
        name="Mây cát phù sa"
        from={92}
        durationInFrames={33}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <LopTruot
          anh={props.anh_cat_phu_sa}
          rong={1300}
          cao={906}
          tu={{x: -260, y: 640, r: 0}}
          den={{x: 120, y: 250, r: -2}}
          dai={33}
          do_mo={props.do_mo_cat}
        />
      </Interactive.Div>

      {/* NHỊP 2 — cành cây khô trôi nổi */}
      <Interactive.Div
        name="Cành cây khô trôi"
        from={92}
        durationInFrames={33}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
      >
        <LopTruot
          anh={props.anh_canh_cay}
          rong={1100}
          cao={633}
          tu={{x: 980, y: 60, r: 9}}
          den={{x: 660, y: 190, r: -2}}
          dai={33}
          do_mo={0.95}
        />
      </Interactive.Div>

      {/* NHỊP 3 — cận cảnh đập lốp xe đang thi công */}
      <Interactive.Div
        name="Đập lốp xe đang thi công"
        from={125}
        durationInFrames={101}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
      >
        <AnhNen
          anh={props.anh_dap_lop}
          tu={props.phong_dap_tu}
          den={props.phong_dap_den}
          goc="50% 55%"
          toi={props.do_toi}
        />
      </Interactive.Div>

      {/* NHỊP 4 — ảnh tư liệu ông John King */}
      <Interactive.Div
        name="Ảnh tư liệu ông John King"
        from={212}
        durationInFrames={74}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          opacity: opa_king,
          filter: 'sepia(0.18) saturate(0.92)',
        }}
      >
        <AnhNen
          anh={props.anh_john_king}
          tu={props.phong_king_tu}
          den={props.phong_king_den}
          goc="50% 40%"
          toi={0.12}
        />
      </Interactive.Div>

      <Interactive.Div
        name="Tên John King"
        from={214}
        durationInFrames={58}
        style={{position: 'absolute', left: 90, top: 868}}
      >
        <TenNhan ten={props.ten_nhan_vat} co={props.co_ten} />
      </Interactive.Div>

      {/* NHỊP 5 — cận cảnh rãnh xói sâu, nước xiết */}
      <Interactive.Div
        name="Rãnh xói sâu nước xiết"
        from={272}
        durationInFrames={104}
        style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: opa_xoi}}
      >
        <AnhLia anh={props.anh_ranh_xoi} huong="phai" quang={props.quang_lia} phong={props.phong_xoi} toi={0.1} />
      </Interactive.Div>
    </AbsoluteFill>
  );
};
