// 05/11 user (sửa tay "giống cách xếp lớp trong CapCut" — xem lớp trước / sau / trên / dưới, phóng to thu nhỏ, xoá, phát lại
// mượt): trong trình sửa lớp, mọi `import … from 'remotion'` (cảnh AI + thu_vien) trỏ vào tệp này. Giữ nguyên Remotion, chỉ
// BỌC Interactive.* và Img: lớp nào user đang chỉnh (theo `name`) thì đè from / durationInFrames / ẩn / vị trí / cỡ / độ mờ /
// thứ tự lớp ngay lúc phát — không đóng gói lại, kéo tới đâu thấy tới đó.
import React from 'react';
import * as R from 'remotion-goc';
import {tinhHieuUng, kieuBoc, kieuLop} from './src/ai/hieu_ung_tinh.js';

export * from 'remotion-goc';

const nghe = new Set();
let banSo = 0;
export const kho = {
  ov: {},                                  // tên lớp -> {from, dai, an, trai, tren, z, co, mo}
  dat(ten, vaa) {
    this.ov = {...this.ov, [ten]: {...(this.ov[ten] || {}), ...vaa}};
    banSo++;
    nghe.forEach((f) => f());
  },
  datHet(ov) {
    this.ov = ov || {};
    banSo++;
    nghe.forEach((f) => f());
  },
  nghe: (f) => { nghe.add(f); return () => nghe.delete(f); },
  ban: () => banSo,
};

// 05/11 user ("không thể sửa chữ … hoặc sửa mấy cái hiệu ứng"): nội dung lớp bọc trong Trong — đổi chữ (chu: {cũ: mới})
// ngay trên DOM, và hiệu ứng vào / ra / liên tục (hieu) theo khung CỤC BỘ của lớp, cùng công thức với HieuUng khi dựng.
const Trong = ({hieu, chu, kieu, children}) => {
  const r = React.useRef(null);
  const f = R.useCurrentFrame();
  const {durationInFrames} = R.useVideoConfig();
  React.useLayoutEffect(() => {
    const el = r.current;
    if (!el || !chu) return;
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const t = n.nodeValue, g = t.trim();
      if (g && Object.prototype.hasOwnProperty.call(chu, g) && chu[g] !== g) n.nodeValue = t.replace(g, chu[g]);
    }
  });
  const co = hieu && (hieu.vao || hieu.ra || hieu.lien);
  const st = co ? {...kieuBoc(kieu), ...tinhHieuUng(f, durationInFrames, hieu)} : {display: 'contents'};
  return <div ref={r} style={st}>{children}</div>;
};

const boc = (C, loai) => {
  const W = React.forwardRef((p, ref) => {
    React.useSyncExternalStore(kho.nghe, kho.ban);
    const o = (p.name && kho.ov[p.name]) || null;
    if (!o) return <C ref={ref} {...p} data-ten={p.name} data-loai={loai} />;
    const con = loai !== 'Img' && (o.hieu || o.chu)
      ? <Trong hieu={o.hieu} chu={o.chu} kieu={kieuLop({...(p.style || {}), ...(o.trai != null ? {left: o.trai} : {}), ...(o.tren != null ? {top: o.tren} : {})})}>{p.children}</Trong> : p.children;
    const st = {...(p.style || {})};
    if (o.trai != null) st.left = o.trai;
    if (o.tren != null) st.top = o.tren;
    if (o.z != null) st.zIndex = o.z;
    if (o.mo != null) st.opacity = o.mo;
    if (o.co != null && o.co !== 1) st.scale = String(o.co);
    return <C ref={ref} {...p} from={o.from ?? p.from} durationInFrames={o.dai ?? p.durationInFrames}
      hidden={o.an || o.xoa || p.hidden} style={st} data-ten={p.name} data-loai={loai}>{con}</C>;
  });
  W.displayName = `SuaLop(${loai})`;
  return W;
};

export const Interactive = Object.fromEntries(Object.entries(R.Interactive).map(([k, v]) =>
  [k, /^[A-Z]/.test(k) && (typeof v === 'function' || (v && v.$$typeof)) ? boc(v, k) : v]));
export const Img = boc(R.Img, 'Img');
