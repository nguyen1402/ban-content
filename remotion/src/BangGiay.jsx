import React, {useMemo} from 'react';
import {
  AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {geoMercator, geoPath, geoBounds} from 'd3-geo';
import {feature} from 'topojson-client';
import countries from 'world-atlas/countries-110m.json';

// "BẢNG GIẤY" — kiểu dựng kênh mẫu user đưa (12/10): nền giấy be, cảnh quay nằm trong THẺ viền trắng bóng đổ,
// tiêu đề đậm trên thẻ, nhãn chỉ chi tiết, mũi tên cam nét đứt nối thẻ trước -> thẻ sau, camera lướt giữa các thẻ.
// Một composition = một KHỐI các nhịp liên tiếp. Mỗi nhịp (beat): {kieu, bd, dai (giây, tính từ đầu khối), clips[], ...}
//   kieu: 'the' | 'cau_hoi' | 'so_sanh' | 'moc' | 'ban_do'
//   clips: [{src (file trong public/), tu (giây trong nhịp), dai}] — video chạy trong thẻ, đổi clip đúng giờ đã cắt.

const W = 1920;
const H = 1080;
const FPS = 30;
const GIAY = '#ece3d6';
const MUC = '#33281f';
const CAM = '#e0782f';
const FONT = '"Segoe UI", "Segoe UI Variable", Arial, sans-serif';
const TW = 1180;            // thẻ video
const TH = 664;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const em = Easing.inOut(Easing.cubic);
const geoNuoc = feature(countries, countries.objects.countries).features;

// vị trí các nhịp trên tấm bảng: đi sang phải, lên xuống so le (để mũi tên cong và camera lướt chéo)
const viTri = (i) => ({x: i * 1650, y: (i % 2 === 0 ? 0 : 1) * 380 - 190 * (i % 3 === 2 ? 1 : 0)});

const NenGiay = () => (
  <AbsoluteFill style={{background: GIAY}}>
    <svg width={W} height={H} style={{position: 'absolute', opacity: 0.35}}>
      <filter id="nhieu"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
        <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.3  0 0 0 0.18 0" /></filter>
      <rect width="100%" height="100%" filter="url(#nhieu)" />
    </svg>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 60%, rgba(70,50,30,0.18) 100%)'}} />
  </AbsoluteFill>
);

const Clips = ({clips, w, h, mo = 0, goc = 0}) => (
  <div style={{position: 'absolute', inset: 0, overflow: 'hidden', filter: mo ? `blur(${mo}px) brightness(0.9)` : 'none'}}>
    {clips.map((c, i) => (
      <Sequence key={i} from={Math.round((goc + c.tu) * FPS)}
        durationInFrames={Math.max(1, Math.round((c.dai + (i === clips.length - 1 ? 1.9 : 0)) * FPS))} layout="none">
        {c.anh
          ? <Img src={staticFile(c.src)} style={{width: w, height: h, objectFit: 'cover', position: 'absolute'}} />
          : <OffthreadVideo src={staticFile(c.src)} muted style={{width: w, height: h, objectFit: 'cover', position: 'absolute'}} />}
      </Sequence>
    ))}
  </div>
);

const The = ({children, w = TW, h = TH, xoay = 0, hien = 1}) => (
  <div style={{position: 'absolute', left: -w / 2 - 12, top: -h / 2 - 12, width: w + 24, height: h + 24, background: '#fff',
    borderRadius: 6, boxShadow: '0 18px 40px rgba(60,40,20,0.28), 0 4px 10px rgba(60,40,20,0.18)',
    transform: `rotate(${xoay}deg) scale(${0.92 + 0.08 * hien})`, opacity: hien}}>
    <div style={{position: 'absolute', left: 12, top: 12, width: w, height: h, overflow: 'hidden', borderRadius: 2}}>{children}</div>
  </div>
);

const TieuDe = ({chu, y, hien}) => (chu ? (
  <div style={{position: 'absolute', left: -900, width: 1800, top: y, textAlign: 'center', fontFamily: FONT, fontWeight: 800,
    fontSize: 74, color: MUC, letterSpacing: 0.5, opacity: hien, transform: `translateY(${(1 - hien) * 24}px)`}}>{chu}</div>
) : null);

const Nhan = ({chu, hien}) => (chu ? (
  <div style={{position: 'absolute', left: TW / 2 - 330, top: TH / 2 - 150, opacity: hien}}>
    <svg width="260" height="120" style={{position: 'absolute', left: -200, top: 40, overflow: 'visible'}}>
      <path d="M250,20 C170,20 120,80 30,90" stroke={MUC} strokeWidth="4" fill="none" pathLength="1" strokeDasharray="1"
        strokeDashoffset={1 - hien} />
      <circle cx="30" cy="90" r="9" fill={CAM} stroke="#fff" strokeWidth="3" opacity={hien} />
    </svg>
    <div style={{background: '#fff', color: MUC, fontFamily: FONT, fontWeight: 700, fontSize: 40, padding: '10px 22px',
      borderRadius: 8, boxShadow: '0 6px 16px rgba(0,0,0,0.25)', whiteSpace: 'nowrap', borderLeft: `8px solid ${CAM}`}}>{chu}</div>
  </div>
) : null);

const CauHoi = ({b, hien}) => (
  <>
    <div style={{position: 'absolute', left: -560, top: -300, width: 1120, height: 600, opacity: 0.55 * hien}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: 6, overflow: 'hidden'}}><Clips clips={b.clips} w={1120} h={600} mo={10} goc={b.bd} /></div>
    </div>
    <div style={{position: 'absolute', left: -800, width: 1600, top: -120, textAlign: 'center', fontFamily: FONT, fontWeight: 800,
      fontSize: 78, lineHeight: 1.18, color: MUC, opacity: hien, transform: `scale(${0.94 + 0.06 * hien})`}}>{b.chu}</div>
  </>
);

const SoSanh = ({b, t}) => {
  const so = (b.so || []).slice(0, 3);
  const max = Math.max(...so.map((s) => Math.abs(s.gia_tri) || 0), 1);
  return (
    <div style={{position: 'absolute', left: -so.length * 210, top: -300, width: so.length * 420, height: 760}}>
      {so.map((s, i) => {
        const k = em(clamp((t - 0.5 - i * 0.35) / 1.1, 0, 1));
        const cao = 330 * (Math.abs(s.gia_tri) / max) * k;
        const gt = s.gia_tri * k;
        const hienSo = Number.isInteger(s.gia_tri) ? Math.round(gt).toLocaleString('vi-VN') : gt.toFixed(1).replace('.', ',');
        return (
          <div key={i} style={{position: 'absolute', left: i * 420 + 90, width: 240, bottom: 120, height: 640}}>
            <div style={{position: 'absolute', bottom: cao + 120, width: '100%', textAlign: 'center', fontFamily: FONT,
              fontWeight: 800, fontSize: 70, color: i === 0 ? CAM : MUC, opacity: k}}>{hienSo}
              <span style={{fontSize: 34, marginLeft: 6}}>{s.don_vi || ''}</span></div>
            <div style={{position: 'absolute', bottom: 0, width: '100%', height: cao, background: i === 0 ? CAM : '#cdbba6',
              borderRadius: '8px 8px 0 0'}} />
            <div style={{position: 'absolute', bottom: -78, width: 360, left: -60, textAlign: 'center', fontFamily: FONT,
              fontWeight: 700, fontSize: 34, color: MUC, opacity: k}}>{s.nhan}</div>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: 40, right: 40, bottom: 120, height: 4, background: MUC, opacity: 0.6}} />
    </div>
  );
};

const Moc = ({b, t, hien}) => {
  const k = em(clamp((t - 0.4) / 1.2, 0, 1));
  const nam = Math.round((b.nam_tu ?? (b.nam - 30)) + (b.nam - (b.nam_tu ?? (b.nam - 30))) * k);
  return (
    <>
      <div style={{position: 'absolute', left: -420, top: 0}}>
        <The w={736} h={414} xoay={-2} hien={hien}><Clips clips={b.clips || []} w={736} h={414} goc={b.bd} /></The>
      </div>
      <div style={{position: 'absolute', left: 30, top: -170, fontFamily: FONT, fontWeight: 900, fontSize: 210, color: CAM,
        opacity: hien, letterSpacing: 4}}>{nam}</div>
      <div style={{position: 'absolute', left: 40, top: 80, width: 640, fontFamily: FONT, fontWeight: 700, fontSize: 44,
        lineHeight: 1.2, color: MUC, opacity: k}}>{b.nhan || ''}</div>
    </>
  );
};

const BanDoPhang = ({b, hien}) => {
  const ten = (b.dia_danh_en || '').toLowerCase();
  const chon = geoNuoc.filter((f) => (f.properties.name || '').toLowerCase() === ten);
  const proj = useMemo(() => {
    const p = geoMercator();
    if (chon.length) {
      const [[w, s], [e, n]] = geoBounds({type: 'FeatureCollection', features: chon});
      const rong = Math.max(e - w, (n - s) * 1.6, 12);
      p.center([(w + e) / 2, (s + n) / 2]).scale((1300 / (rong * Math.PI / 180)) * 0.62);
    } else {
      p.center([10, 30]).scale(260);
    }
    return p.translate([0, 0]);
  }, [ten]);
  const path = geoPath(proj);
  return (
    <svg width="1800" height="1000" viewBox="-900 -500 1800 1000" style={{position: 'absolute', left: -900, top: -500, opacity: hien}}>
      {geoNuoc.map((f, i) => {
        const la = chon.includes(f);
        return <path key={i} d={path(f) || ''} fill={la ? CAM : '#d9ccbb'} stroke="#f3ece2" strokeWidth={la ? 2 : 1} />;
      })}
      {b.nhan && chon.length ? (() => {
        const c = path.centroid(chon[0]);
        return (
          <g>
            <rect x={c[0] - b.nhan.length * 13 - 20} y={c[1] - 34} width={b.nhan.length * 26 + 40} height={64} rx={10} fill="#fff"
              stroke={MUC} strokeWidth={2} />
            <text x={c[0]} y={c[1] + 12} textAnchor="middle" fontFamily={FONT} fontWeight={800} fontSize={40} fill={MUC}>{b.nhan}</text>
          </g>
        );
      })() : null}
    </svg>
  );
};

export const BangGiay = ({nhip = []}) => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const {durationInFrames: N} = useVideoConfig();
  // nhịp hiện tại + camera: lướt từ nhịp trước sang nhịp này trong 0,7 s đầu nhịp
  let i = 0;
  for (let k = 0; k < nhip.length; k++) if (t >= nhip[k].bd) i = k;
  const b = nhip[i] || {bd: 0, dai: N / FPS};
  const tl = t - b.bd;
  const chuyen = em(clamp(tl / 0.7, 0, 1));
  const p0 = viTri(Math.max(0, i - 1));
  const p1 = viTri(i);
  const cx = i === 0 ? p1.x : p0.x + (p1.x - p0.x) * chuyen;
  const cy = i === 0 ? p1.y : p0.y + (p1.y - p0.y) * chuyen;
  const zoom = 1 - 0.12 * Math.sin(Math.PI * chuyen) * (i === 0 ? 0 : 1);     // lùi nhẹ giữa lúc lướt
  const troi = 1 + 0.03 * clamp(tl / Math.max(b.dai, 1), 0, 1);               // phóng chậm khi đứng yên ở một thẻ
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <NenGiay />
      <div style={{position: 'absolute', left: W / 2, top: H / 2, transform: `scale(${zoom * troi}) translate(${-cx}px, ${-cy}px)`}}>
        {nhip.map((n, k) => {
          if (k < i - 1 || k > i + 1) return null;
          const p = viTri(k);
          const tk = t - n.bd;
          const hien = k === i ? em(clamp((tk - 0.15) / 0.5, 0, 1)) : (k === i - 1 ? 1 : 0);
          const xoay = (k % 2 ? 1 : -1) * 0.8;
          // mũi tên từ thẻ trước sang thẻ này
          const mui = k > 0 && k <= i ? (() => {
            const a = viTri(k - 1);
            const ve = k === i ? em(clamp((tk + 0.1) / 0.8, 0, 1)) : 1;
            const x0 = a.x + TW / 2 + 40, y0 = a.y + 40, x1 = p.x - TW / 2 - 60, y1 = p.y - 40;
            const mx = (x0 + x1) / 2, my = Math.min(y0, y1) - 160;
            return (
              <svg key={'m' + k} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}} width="1" height="1">
                <path d={`M${x0},${y0} Q${mx},${my} ${x1},${y1}`} stroke={CAM} strokeWidth="7" fill="none" strokeLinecap="round"
                  strokeDasharray="20 18" pathLength="1000" strokeDashoffset={0}
                  style={{clipPath: 'none'}} opacity={0.9} mask={`url(#mm${k})`} />
                <defs><mask id={`mm${k}`}><path d={`M${x0},${y0} Q${mx},${my} ${x1},${y1}`} stroke="#fff" strokeWidth="14" fill="none"
                  pathLength="1" strokeDasharray="1" strokeDashoffset={1 - ve} /></mask></defs>
                <circle cx={x1} cy={y1} r="10" fill={CAM} opacity={ve > 0.98 ? 1 : 0} />
              </svg>
            );
          })() : null;
          return (
            <React.Fragment key={k}>
              {mui}
              <div style={{position: 'absolute', left: p.x, top: p.y}}>
                {n.kieu === 'the' && <>
                  <TieuDe chu={n.tieu_de} y={-TH / 2 - 130} hien={hien} />
                  <The xoay={xoay} hien={hien}><Clips clips={n.clips} w={TW} h={TH} goc={n.bd} /></The>
                  {k === i && <Nhan chu={n.nhan} hien={em(clamp((tk - 0.9) / 0.5, 0, 1))} />}
                </>}
                {n.kieu === 'cau_hoi' && <CauHoi b={n} hien={hien} />}
                {n.kieu === 'so_sanh' && <>
                  <TieuDe chu={n.tieu_de} y={-470} hien={hien} />
                  <SoSanh b={n} t={k === i ? tk : 99} />
                </>}
                {n.kieu === 'moc' && <Moc b={n} t={k === i ? tk : 99} hien={hien} />}
                {n.kieu === 'ban_do' && <>
                  <BanDoPhang b={n} hien={hien} />
                </>}
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
