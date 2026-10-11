import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {geoMercator, geoPath, geoGraticule10, geoBounds} from 'd3-geo';
import {feature} from 'topojson-client';
import land from 'world-atlas/land-10m.json';

const W = 1920;
const H = 1080;
const FONT = '"Segoe UI", Arial, sans-serif';
const geoTatCa = feature(land, land.objects.land);
// Mercator + zoom lớn làm đa giác Nam Cực (kéo tới cực) thành tọa độ khổng lồ, hỏng cả lớp tô.
// Chỉ giữ các mảng đất nằm gần địa điểm và không chạm vĩ độ cực.
const mangDat = [];
for (const g of geoTatCa.features ? geoTatCa.features : [geoTatCa]) {
  const polys = g.geometry.type === 'MultiPolygon' ? g.geometry.coordinates : [g.geometry.coordinates];
  for (const c of polys) {
    const [[w, s], [e, n]] = geoBounds({type: 'Polygon', coordinates: c});
    if (s > -80 && n < 85) mangDat.push({type: 'Feature', properties: {}, geometry: {type: 'Polygon', coordinates: c}, w, s, e, n});
  }
}

// props: {giay, dia_diem, lat, lon, rong_km, nam_tu, nam_den, dau[{ten,lat,lon}], chu_thich[]}
export const BanDo = ({
  dia_diem = '', lat = 0, lon = 0, rong_km = 40,
  nam_tu = null, nam_den = null, dau = [], chu_thich = [],
}) => {
  const f = useCurrentFrame();
  const {durationInFrames: N} = useVideoConfig();
  const k = Easing.inOut(Easing.cubic)(Math.min(1, f / (N * 0.8)));

  // Phóng từ tầm khu vực (~6000km) vào tầm địa điểm (rong_km), nội suy theo logarit.
  const km = Math.exp(interpolate(k, [0, 1], [Math.log(6000), Math.log(Math.max(2, rong_km))]));
  // Mercator: ở vĩ độ lat, 1 độ kinh = 111km*cos(lat). scale d3 = px cho 1 radian kinh độ.
  const kmMoiRadian = 6371 * Math.cos((lat * Math.PI) / 180);
  const scale = (W / km) * kmMoiRadian;

  const proj = useMemo(
    () => geoMercator().center([lon, lat]).translate([W / 2, H / 2]).clipExtent([[-50, -50], [W + 50, H + 50]]),
    [lon, lat],
  );
  proj.scale(scale);
  const path = geoPath(proj);
  const gan = mangDat.filter((m) => m.n > lat - 25 && m.s < lat + 25 && m.e > lon - 35 && m.w < lon + 35);

  const nam = nam_tu != null && nam_den != null
    ? Math.round(interpolate(f, [N * 0.12, N * 0.88], [nam_tu, nam_den],
        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}))
    : null;
  const pulse = 1 + 0.25 * Math.sin(f / 5);
  const [px, py] = proj([lon, lat]) || [W / 2, H / 2];
  const hien = (i) => interpolate(f, [N * (0.3 + 0.1 * i), N * (0.4 + 0.1 * i)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg,#0b2a4a,#154a7a)', fontFamily: FONT}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <rect x="0" y="0" width={W} height={H} fill="#1c5d8f" />
        <path d={path(geoGraticule10())} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="1" />
        <path d={path({type: 'FeatureCollection', features: gan})} fill="#e8dcb8" stroke="#8a7a4a" strokeWidth={Math.max(0.8, 2.4 - k * 1.2)} />
        {dau.map((m, i) => {
          const p = proj([m.lon, m.lat]);
          if (!p) return null;
          return (
            <g key={i} opacity={hien(i)}>
              <circle cx={p[0]} cy={p[1]} r={14} fill="#ffd400" stroke="#222" strokeWidth="3" />
              <text x={p[0] + 26} y={p[1] + 8} fontSize="38" fontWeight="700" fill="#fff"
                stroke="#0b2a4a" strokeWidth="7" paintOrder="stroke">{m.ten}</text>
            </g>
          );
        })}
        <circle cx={px} cy={py} r={34 * pulse} fill="rgba(230,40,40,0.25)" />
        <circle cx={px} cy={py} r={14} fill="#e62828" stroke="#fff" strokeWidth="4" />
      </svg>
      <div style={{position: 'absolute', left: 70, top: 56, color: '#fff', fontSize: 64, fontWeight: 800,
        textShadow: '0 4px 14px rgba(0,0,0,0.6)', opacity: interpolate(f, [0, 20], [0, 1])}}>{dia_diem}</div>
      {nam !== null && (
        <div style={{position: 'absolute', right: 80, bottom: 70, color: '#ffd400', fontSize: 190,
          fontWeight: 900, textShadow: '0 6px 18px rgba(0,0,0,0.7)', letterSpacing: 4}}>{nam}</div>
      )}
      <div style={{position: 'absolute', left: 70, bottom: 70, display: 'flex', flexDirection: 'column', gap: 14}}>
        {chu_thich.map((c, i) => (
          <div key={i} style={{opacity: hien(i), transform: `translateX(${(1 - hien(i)) * -40}px)`,
            color: '#fff', fontSize: 44, fontWeight: 600, background: 'rgba(0,0,0,0.55)',
            padding: '10px 22px', borderRadius: 10, maxWidth: 1100}}>{c}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
