import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';

// 03/11 user (câu 52 caloc: "miệng tròn như giác hút, bên trong nhiều vòng răng sừng, chính giữa là lưỡi ráp như giũa" mà
// clip chỉ khoanh nguyên con cá): cảnh mẫu GIẢI PHẪU dùng chung cho câu tả cấu tạo — toàn thân -> kính lúp mở ra cận cảnh
// nhìn thẳng bộ phận -> lần lượt chỉ từng phần (viền / vòng trong / tâm / điểm) đúng lúc lời đọc nhắc, kèm nhãn có đường
// dẫn; tuỳ chọn thẻ VÍ VON (vật được so sánh) trượt vào. Chỉnh tay mọi thông số trong Remotion Studio.
const src = (s) => (!s ? '' : /^(https?:|data:|file:)/.test(s) ? s : staticFile(s));
const kep = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const FONT = '"Segoe UI", "Be Vietnam Pro", Arial, sans-serif';
const VANG = '#ffd23f';
const W = 1920, H = 1080;

const chuThich = z.object({
  t: z.number().min(0).max(30).describe('Giây hiện'),
  kieu: z.enum(['vien', 'vong', 'tam', 'diem']).describe('viền ngoài / vòng bên trong / tâm / một điểm'),
  r: z.number().min(0).max(1.3).describe('Bán kính (0 = tâm, 1 = viền bộ phận)'),
  goc: z.number().min(-180).max(180).describe('Hướng đặt nhãn (độ, 0 = sang phải, 90 = xuống dưới)'),
  chu: z.string().describe('Nhãn'),
  x: z.number().min(-1).max(1).describe('Điểm trên ảnh cận cảnh — ngang (0–1; -1 = tính theo bán kính và hướng)'),
  y: z.number().min(-1).max(1).describe('Điểm trên ảnh cận cảnh — dọc (0–1; -1 = tính theo bán kính và hướng)'),
});

export const giaiPhauSchema = z.object({
  giay: z.number().min(1).max(30).describe('Độ dài clip (giây)'),
  toan: z.string().describe('Ảnh toàn thân (để trống = vào thẳng cận cảnh)'),
  can: z.string().describe('Ảnh cận cảnh nhìn thẳng bộ phận'),
  tam: z.tuple([z.number(), z.number()]).describe('Tâm bộ phận trên ảnh cận cảnh [ngang, dọc] (0–1)'),
  ban_kinh: z.number().min(0.05).max(0.7).describe('Bán kính bộ phận (phần chiều rộng ảnh)'),
  vao_can: z.number().min(0).max(30).describe('Giây kính lúp mở ra cận cảnh'),
  chu_thich: z.array(chuThich).describe('Các chú thích theo thứ tự lời đọc'),
  phong_tam: z.number().min(1).max(3).describe('Phóng vào tâm ở chú thích cuối (1 = không phóng)'),
  vi_von_anh: z.string().describe('Ảnh vật được ví von (PNG tách nền, để trống = không có)'),
  vi_von_chu: z.string().describe('Chữ của thẻ ví von'),
  vi_von_t: z.number().min(0).max(30).describe('Giây thẻ ví von hiện'),
  vi_von_ben: z.enum(['duoi_phai', 'duoi_trai', 'tren_phai', 'tren_trai']).describe('Góc đặt thẻ ví von'),
});

export const GIAI_PHAU_MAC_DINH = {
  giay: 10, toan: '', can: '', tam: [0.5, 0.5], ban_kinh: 0.3, vao_can: 1.2, phong_tam: 1.5,
  chu_thich: [], vi_von_anh: '', vi_von_chu: '', vi_von_t: 7, vi_von_ben: 'duoi_phai',
};

// một chú thích: hình (vòng / chấm) vẽ dần + đường dẫn + nhãn
const MotChuThich = ({c, cx, cy, R, kinhR, fps, anh}) => {
  const f = useCurrentFrame();
  const t0 = c.t * fps;
  const p = interpolate(f, [t0, t0 + 16], [0, 1], {...kep, easing: Easing.bezier(0.3, 0, 0.2, 1)});
  const pn = interpolate(f, [t0 + 10, t0 + 20], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});
  if (p <= 0) return null;
  const r = Math.max(0.0001, c.r) * R;
  const g = (c.goc * Math.PI) / 180;
  // điểm đường dẫn bắt đầu: toạ độ dò trên ảnh (x, y) nếu có, không thì theo bán kính + hướng
  const coDiem = c.x !== undefined && c.x >= 0 && c.y >= 0;
  const rTam = c.kieu === 'tam' ? Math.max(0.12, c.r || 0.3) * R : 0;   // đường dẫn của "tâm" bắt đầu ở mép vòng
  const neo = coDiem ? anh(c.x, c.y) : c.kieu === 'tam' ? [cx + Math.cos(g) * rTam, cy + Math.sin(g) * rTam]
    : [cx + Math.cos(g) * r, cy + Math.sin(g) * r];
  const xa = Math.max(kinhR + 70, r + 150);
  const phai = Math.cos(g) >= 0;
  const rongNhan = c.chu.length * 27 + 60;                              // ước bề ngang nhãn (px)
  const nhan = [Math.min(W - 40 - (phai ? rongNhan + 14 : 0), Math.max(40 + (phai ? 0 : rongNhan + 14), cx + Math.cos(g) * xa)),
    Math.min(H - 80, Math.max(80, cy + Math.sin(g) * xa))];
  const L = 2 * Math.PI * r;
  return (
    <>
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <g style={{filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.8))'}}>
          {c.kieu === 'vien' || c.kieu === 'vong'
            ? <circle cx={cx} cy={cy} r={Math.min(r, kinhR - 6)} fill="none" stroke={VANG} strokeWidth={c.kieu === 'vien' ? 7 : 5}
                strokeDasharray={c.kieu === 'vong' ? `${18} ${12}` : L} strokeDashoffset={c.kieu === 'vong' ? 0 : L * (1 - p)}
                opacity={c.kieu === 'vong' ? p : 1} transform={`rotate(${c.goc - 90} ${cx} ${cy})`} />
            : <circle cx={c.kieu === 'tam' && !coDiem ? cx : neo[0]} cy={c.kieu === 'tam' && !coDiem ? cy : neo[1]} r={(c.kieu === 'tam' ? Math.max(0.12, c.r || 0.3) * R : Math.max(22, 0.09 * R)) * (0.6 + 0.4 * p)} fill="none" stroke={VANG}
                strokeWidth={6} opacity={p} />}
          <line x1={neo[0]} y1={neo[1]} x2={neo[0] + (nhan[0] - neo[0]) * pn} y2={neo[1] + (nhan[1] - neo[1]) * pn}
            stroke="#fff" strokeWidth={4} />
          <circle cx={neo[0]} cy={neo[1]} r={7} fill="#fff" opacity={pn} />
        </g>
      </svg>
      <div style={{position: 'absolute', top: nhan[1] - 40, left: phai ? nhan[0] + 14 : undefined,
        right: phai ? undefined : W - nhan[0] + 14, opacity: pn, transform: `translateX(${(1 - pn) * (phai ? -30 : 30)}px)`,
        fontFamily: FONT, fontWeight: 800, fontSize: 52, color: '#fff', whiteSpace: 'nowrap', padding: '8px 22px',
        background: 'rgba(10,12,14,0.72)', borderLeft: phai ? `7px solid ${VANG}` : undefined,
        borderRight: phai ? undefined : `7px solid ${VANG}`, boxShadow: '0 8px 24px rgba(0,0,0,0.45)'}}>{c.chu}</div>
    </>
  );
};

export const GiaiPhau = (p) => {
  const q = {...GIAI_PHAU_MAC_DINH, ...p};
  const f = useCurrentFrame();
  const {fps, durationInFrames: D} = useVideoConfig();
  const t = f / fps;
  const mo = q.toan ? interpolate(t, [q.vao_can, q.vao_can + 0.8], [0, 1], {...kep, easing: Easing.bezier(0.5, 0, 0.2, 1)}) : 1;
  // cận cảnh: đẩy nhẹ suốt cảnh + phóng vào tâm khi tới chú thích cuối
  const cuoi = q.chu_thich.length ? q.chu_thich[q.chu_thich.length - 1].t : 1e9;
  const Rthay = Math.min(q.ban_kinh * W, 0.48 * H);                  // phần bộ phận có trong ảnh (px, ảnh gốc)
  const vua = Math.min(1, (0.42 * H) / Rthay);                         // co ảnh cận cảnh cho bộ phận vừa trong kính
  const phong = vua * interpolate(t, [q.vao_can, q.giay], [1.0, 1.08], kep) *
    interpolate(t, [cuoi - 0.2, cuoi + 0.8], [1, q.phong_tam], {...kep, easing: Easing.bezier(0.45, 0, 0.2, 1)});
  const [tx, ty] = q.tam;
  const cx0 = tx * W, cy0 = ty * H;
  // phóng quanh tâm bộ phận và kéo tâm dần về giữa khung
  const keo = interpolate(t, [q.vao_can, q.vao_can + 1.2], [0, 1], {...kep, easing: Easing.bezier(0.45, 0, 0.2, 1)});
  const ox = (W / 2 - cx0) * keo, oy = (H / 2 - cy0) * keo;
  const cx = cx0 + ox, cy = cy0 + oy;
  const R = Rthay * phong;
  const kinhR = Math.min(0.47 * H, Rthay * vua * 1.08, 0.5 * H * vua - 4);   // bán kính kính lúp khi đã mở hẳn
  const kinh = interpolate(mo, [0, 1], [0, kinhR]);                    // bán kính kính lúp đang mở
  const vv = q.vi_von_anh ? interpolate(t, [q.vi_von_t, q.vi_von_t + 0.6], [0, 1], {...kep, easing: Easing.out(Easing.back(1.4))}) : 0;
  return (
    <AbsoluteFill style={{background: '#05080a', overflow: 'hidden', opacity: interpolate(f, [0, 6, D - 8, D], [0, 1, 1, 0], kep)}}>
      {q.toan ? <Img src={src(q.toan)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover',
        transform: `scale(${interpolate(t, [0, q.vao_can + 0.8], [1.02, 1.25], kep)})`,
        filter: `brightness(${1 - 0.55 * mo}) blur(${6 * mo}px)`}} /> : null}
      <AbsoluteFill style={{clipPath: `circle(${kinh}px at ${W / 2}px ${H / 2}px)`}}>
        <Img src={src(q.can)} style={{position: 'absolute', width: W, height: H, objectFit: 'cover', transformOrigin: `${cx0}px ${cy0}px`,
          transform: `translate(${ox}px, ${oy}px) scale(${phong})`}} />
        <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 50%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.55) 100%)'}} />
      </AbsoluteFill>
      {mo > 0 ? <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        <circle cx={W / 2} cy={H / 2} r={kinh} fill="none" stroke="#f4f1ea" strokeWidth={12}
          style={{filter: 'drop-shadow(0 10px 30px rgba(0,0,0,0.7))'}} /></svg> : null}
      {q.chu_thich.map((c, i) => <MotChuThich key={i} c={c} cx={cx} cy={cy} R={R} kinhR={kinhR} fps={fps}
        anh={(u, v) => [cx + (u * W - cx0) * phong, cy + (v * H - cy0) * phong]} />)}
      {q.vi_von_anh ? <div style={{position: 'absolute', [String(q.vi_von_ben).endsWith('trai') ? 'left' : 'right']: 70,
        [String(q.vi_von_ben).startsWith('tren') ? 'top' : 'bottom']: 70, width: 440, padding: 20, background: 'rgba(250,248,242,0.96)',
        boxShadow: '0 14px 40px rgba(0,0,0,0.55)', opacity: Math.min(1, vv * 1.5),
        transform: `translateY(${(1 - vv) * 120}px) rotate(${(1 - vv) * 6 - 2}deg)`}}>
        <Img src={src(q.vi_von_anh)} style={{width: '100%', height: 220, objectFit: 'contain'}} />
        <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 40, color: '#1c1c1c', textAlign: 'center', marginTop: 8}}>{q.vi_von_chu}</div>
      </div> : null}
    </AbsoluteFill>
  );
};
