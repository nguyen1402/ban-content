// 20/10 user: "Cảnh Remotion theo mô tả" — AI đổi mô tả tiếng Việt thành KỊCH BẢN CẢNH (JSON) theo khuôn dưới; component
// này chỉ việc dựng theo (không để AI viết code tự do -> không lỗi biên dịch, phong cách đồng bộ).
//
// props: { giay, nen: "#rrggbb" | {anh, phong:[đầu,cuối], toi: 0-1}, lop: [ ... ] }
// Mỗi lớp: { loai, vao (giây), ra (giây), hieu_ung: "mo"|"truot_len"|"truot_trai"|"phong"|"nay"|"go", ... }
//   chu     : text, x, y (0-1, tâm), co (px), mau, dam, nghieng, nen_chu (màu hộp nền, tuỳ chọn), rong (0-1)
//   so      : tu, den, x, y, co, mau, truoc ("" chữ trước số), sau (chữ sau số), dem (giây đếm, mặc định 1.5)
//   hinh    : dang "tron"|"chu_nhat"|"vien_tron"|"vien_chu_nhat", x, y, w, h (0-1), mau, day (độ dày viền px)
//   mui_ten : tu [x,y], den [x,y], mau, day — vẽ dần từ đầu tới cuối
//   anh     : src (đường dẫn trong public/), x, y, w, h (0-1), phong [đầu,cuối], bo (bo góc px)
import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {BanDoVeTinh} from './BanDoVeTinh.jsx';

const W = 1920, H = 1080;
const FONT = '"Segoe UI", "Be Vietnam Pro", Arial, sans-serif';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

function hienRa(f, fps, l, tong) {
  const vao = Math.round((l.vao ?? 0) * fps), ra = Math.round((l.ra ?? tong) * fps);
  const vao_d = Math.round(0.35 * fps), ra_d = Math.round(0.3 * fps);
  if (f < vao || f > ra) return null;
  const a = Math.min(interpolate(f, [vao, vao + vao_d], [0, 1], clamp), interpolate(f, [ra - ra_d, ra], [1, 0], clamp));
  const p = interpolate(f, [vao, vao + vao_d], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const sp = spring({frame: f - vao, fps, config: {damping: 12, stiffness: 140}});
  const hu = l.hieu_ung || 'mo';
  let tf = '';
  if (hu === 'truot_len') tf = `translateY(${(1 - p) * 60}px)`;
  else if (hu === 'truot_trai') tf = `translateX(${(1 - p) * 120}px)`;
  else if (hu === 'phong') tf = `scale(${0.6 + 0.4 * p})`;
  else if (hu === 'nay') tf = `scale(${sp})`;
  return {a, tf, f0: f - vao, dai: ra - vao};
}

function hop(l, w, h) {
  const x = (l.x ?? 0.5) * W, y = (l.y ?? 0.5) * H;
  return {position: 'absolute', left: x - w / 2, top: y - h / 2, width: w, height: h};
}

function Chu({l, f, fps, tong}) {
  const r = hienRa(f, fps, l, tong);
  if (!r) return null;
  let text = String(l.text ?? '');
  if ((l.hieu_ung || '') === 'go') text = text.slice(0, Math.max(0, Math.round(r.f0 / fps * 18)));
  const rong = (l.rong ?? 0.85) * W, co = l.co ?? 72;
  return (
    <div style={{...hop(l, rong, co * 3), display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: r.a,
      transform: r.tf}}>
      <span style={{fontFamily: FONT, fontSize: co, fontWeight: l.dam === false ? 400 : 800, fontStyle: l.nghieng ? 'italic' : 'normal',
        color: l.mau || '#fff', textAlign: 'center', lineHeight: 1.15, textShadow: l.nen_chu ? 'none' : '0 4px 18px rgba(0,0,0,.55)',
        background: l.nen_chu || 'transparent', padding: l.nen_chu ? '8px 22px' : 0, borderRadius: 10}}>{text}</span>
    </div>);
}

function So({l, f, fps, tong}) {
  const r = hienRa(f, fps, l, tong);
  if (!r) return null;
  const tu = Number(l.tu ?? 0), den = Number(l.den ?? 0), dem = Math.max(0.2, l.dem ?? 1.5) * fps;
  const v = interpolate(r.f0, [0, dem], [tu, den], {...clamp, easing: Easing.out(Easing.cubic)});
  const so = Math.round(v).toLocaleString('vi-VN');
  return <Chu l={{...l, text: `${l.truoc || ''}${so}${l.sau || ''}`, hieu_ung: l.hieu_ung || 'phong', co: l.co ?? 160}} f={f} fps={fps} tong={tong} />;
}

function Hinh({l, f, fps, tong}) {
  const r = hienRa(f, fps, l, tong);
  if (!r) return null;
  const w = (l.w ?? 0.2) * W, h = (l.h ?? 0.2) * H, d = l.dang || 'tron', day = l.day ?? 6, mau = l.mau || '#e53935';
  const vien = d.startsWith('vien');
  return <div style={{...hop(l, w, h), opacity: r.a, transform: r.tf, borderRadius: d.includes('tron') ? '50%' : 12,
    background: vien ? 'transparent' : mau, border: vien ? `${day}px solid ${mau}` : 'none'}} />;
}

function MuiTen({l, f, fps, tong}) {
  const r = hienRa(f, fps, l, tong);
  if (!r) return null;
  const [x1, y1] = (l.tu || [0.3, 0.5]).map((v, k) => v * (k ? H : W));
  const [x2, y2] = (l.den || [0.7, 0.5]).map((v, k) => v * (k ? H : W));
  const p = interpolate(r.f0, [0, 0.8 * fps], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  const xe = x1 + (x2 - x1) * p, ye = y1 + (y2 - y1) * p, goc = Math.atan2(y2 - y1, x2 - x1), mau = l.mau || '#ffd54f', day = l.day ?? 10;
  const dau = 34;
  return (
    <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, opacity: r.a}}>
      <line x1={x1} y1={y1} x2={xe} y2={ye} stroke={mau} strokeWidth={day} strokeLinecap="round" />
      {p > 0.95 && <polygon fill={mau} points={`${x2},${y2} ${x2 - dau * Math.cos(goc - 0.45)},${y2 - dau * Math.sin(goc - 0.45)} ${x2 - dau * Math.cos(goc + 0.45)},${y2 - dau * Math.sin(goc + 0.45)}`} />}
    </svg>);
}

function Anh({l, f, fps, tong}) {
  const r = hienRa(f, fps, l, tong);
  if (!r || !l.src) return null;
  const w = (l.w ?? 0.5) * W, h = (l.h ?? 0.5) * H, [a, b] = l.phong || [1, 1.08];
  const s = interpolate(r.f0, [0, Math.max(1, r.dai)], [a, b], clamp);
  return (
    <div style={{...hop(l, w, h), overflow: 'hidden', borderRadius: l.bo ?? 14, opacity: r.a, transform: r.tf,
      boxShadow: '0 12px 40px rgba(0,0,0,.5)'}}>
      <Img src={staticFile(l.src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${s})`}} />
    </div>);
}

const LOP = {chu: Chu, so: So, hinh: Hinh, mui_ten: MuiTen, anh: Anh};

export const CanhMoTa = (props) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const tong = durationInFrames / fps;
  const nen = props.nen;
  let lopNen = <AbsoluteFill style={{background: typeof nen === 'string' && nen ? nen : '#0b0d12'}} />;
  if (nen && typeof nen === 'object' && nen.anh) {
    const [a, b] = nen.phong || [1, 1.1];
    const s = interpolate(f, [0, durationInFrames], [a, b], clamp);
    lopNen = (
      <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
        <Img src={staticFile(nen.anh)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${s})`}} />
        <AbsoluteFill style={{background: `rgba(0,0,0,${nen.toi ?? 0.35})`}} />
      </AbsoluteFill>);
  }
  if (props.ban_do && props.ban_do.cam) lopNen = <BanDoVeTinh bd={props.ban_do} />;   // 20/10: nền bản đồ vệ tinh
  return (
    <AbsoluteFill>
      {lopNen}
      {(props.lop || []).map((l, k) => {
        const C = LOP[l.loai];
        return C ? <C key={k} l={l} f={f} fps={fps} tong={tong} /> : null;
      })}
    </AbsoluteFill>);
};
