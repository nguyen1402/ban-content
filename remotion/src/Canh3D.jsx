import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, Easing, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

// 03/11 user: cảnh mẫu 3D cho nhấn ý — "ảnh 3D chiều sâu xong mực nước vào kiểu ngập sâu 8m", và "tôi phải được phép
// động tay vào chỉnh sửa": mọi thông số nằm trong schema dưới đây (tên tiếng Việt) -> sửa trong Remotion Studio, bấm
// lưu, rồi chinh_sua/nhan_y.py --dung-lai dựng lại đúng chỗ đó. Đơn vị cảnh: MÉT. Mọi chuyển động theo useCurrentFrame.
const src = (s) => (!s ? '' : /^(https?:|data:|file:)/.test(s) ? s : staticFile(s));
const kep = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const FONT = '"Segoe UI", "Be Vietnam Pro", Arial, sans-serif';
const diem = z.tuple([z.number(), z.number(), z.number()]);

export const nuocDangSchema = z.object({
  giay: z.number().min(1).max(30).describe('Độ dài clip (giây)'),
  muc_nuoc: z.number().min(0.5).max(60).describe('Mực nước cuối (mét)'),
  bat_dau_dang: z.number().min(0).max(30).describe('Giây nước bắt đầu dâng'),
  thoi_gian_dang: z.number().min(0.3).max(30).describe('Nước dâng trong bao nhiêu giây'),
  cao_thanh: z.number().min(1).max(80).describe('Thành âu cao (mét)'),
  rong: z.number().min(4).max(200).describe('Lòng âu rộng (mét)'),
  dai: z.number().min(8).max(400).describe('Lòng âu dài (mét)'),
  mau_nuoc: zColor().describe('Màu nước'),
  do_trong: z.number().min(0).max(1).describe('Độ trong của nước (0 đục – 1 trong)'),
  song: z.number().min(0).max(1).describe('Độ gợn sóng'),
  thac: z.boolean().describe('Nước tràn vào từ cửa âu'),
  thuoc_do: z.boolean().describe('Hiện thước đo mét trên thành'),
  nguoi: z.string().describe('Ảnh người đứng dưới đáy làm thước so (PNG tách nền, để trống = không có)'),
  nguoi_cao: z.number().min(0.5).max(5).describe('Người cao (mét)'),
  tuong: z.string().describe('Ảnh bề mặt bê tông của thành / đáy (để trống = màu xám)'),
  troi: z.string().describe('Ảnh bầu trời phía sau (để trống = màu)'),
  cam_dau: diem.describe('Camera lúc đầu [ngang, cao, xa] (mét)'),
  cam_giua: diem.describe('Camera lúc nước dâng [ngang, cao, xa]'),
  cam_cuoi: diem.describe('Camera lúc cuối [ngang, cao, xa]'),
  nhin: diem.describe('Camera nhìn vào điểm [ngang, cao, xa]'),
  chu: z.string().describe('Chữ hiện khi nước dâng xong (để trống = không có)'),
  chu_luc: z.number().min(0).max(30).describe('Giây chữ hiện'),
  so_dem: z.boolean().describe('Hiện số mét đếm theo mực nước'),
});

export const NUOC_DANG_MAC_DINH = {
  giay: 8, muc_nuoc: 8, bat_dau_dang: 1.2, thoi_gian_dang: 4.5, cao_thanh: 10.5, rong: 16, dai: 60,
  mau_nuoc: '#1f5f6e', do_trong: 0.35, song: 0.5, thac: true, thuoc_do: true, nguoi: '', nguoi_cao: 1.75,
  tuong: '', troi: '', cam_dau: [6, 30, 10], cam_giua: [4, 20, 2], cam_cuoi: [4, 16, 1], nhin: [-3, 3, -18],
  chu: '', chu_luc: 6, so_dem: true,
};

// nạp ảnh thành texture (Remotion chờ ảnh xong mới chụp khung)
const useAnh = (duong, lap = false) => {
  const [tex, setTex] = useState(null);
  const [h] = useState(() => (duong ? delayRender(`ảnh ${duong}`) : null));
  useEffect(() => {
    if (!duong) return;
    new THREE.TextureLoader().load(src(duong), (t) => {
      t.colorSpace = THREE.SRGBColorSpace;
      if (lap) t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.anisotropy = 8;
      setTex(t);
    }, undefined, () => continueRender(h));
  }, [duong]);                                                          // eslint-disable-line react-hooks/exhaustive-deps
  // 03/11 (xem thử: vài khung trắng tường): chỉ cho chụp khung SAU khi cảnh đã vẽ lại với ảnh
  useEffect(() => {
    if (tex && h !== null) requestAnimationFrame(() => requestAnimationFrame(() => continueRender(h)));
  }, [tex]);                                                            // eslint-disable-line react-hooks/exhaustive-deps
  return tex;
};

// khối hộp có toạ độ ảnh theo MÉT (ảnh bề mặt lặp mỗi `o` mét, không bị kéo dãn theo chiều dài khối)
const Hop = ({kich: [w, h, d], o = 14, children, ...p}) => {
  const geo = useMemo(() => {
    const g = new THREE.BoxGeometry(w, h, d);
    const uv = g.attributes.uv;
    const mat = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];      // +x -x +y -y +z -z
    for (let i = 0; i < uv.count; i++) {
      const [a, b] = mat[Math.floor(i / 4)];
      uv.setXY(i, (uv.getX(i) * a) / o, (uv.getY(i) * b) / o);
    }
    uv.needsUpdate = true;
    return g;
  }, [w, h, d, o]);
  return <mesh geometry={geo} {...p}>{children}</mesh>;
};

// thước đo vạch mét vẽ bằng canvas
const useThuoc = (cao) => useMemo(() => {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 2048;
  const g = c.getContext('2d');
  g.fillStyle = 'rgba(250,250,245,0.92)';
  g.fillRect(96, 0, 40, 2048);
  g.fillStyle = '#111';
  g.font = 'bold 64px Segoe UI, Arial';
  const n = Math.floor(cao);
  for (let m = 0; m <= n; m++) {
    const y = 2048 - (m / cao) * 2048;
    g.fillRect(96, y - 6, 120, 12);
    if (m > 0) g.fillText(`${m}`, 150, y + 22);
    for (let q = 1; q < 4 && m < n; q++) g.fillRect(96, y - (q / 4 / cao) * 2048 - 3, 60, 6);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}, [cao]);

// mặt nước lưới gợn sóng (đỉnh lưới tính theo khung hình — không tự chạy)
const MatNuoc = ({rong, dai, y, mau, do_trong, song, f}) => {
  const geo = useMemo(() => new THREE.PlaneGeometry(rong, dai, 48, 96), [rong, dai]);
  useMemo(() => {
    const p = geo.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), v = p.getY(i);
      p.setZ(i, song * (0.08 * Math.sin(x * 0.9 + f * 0.11) + 0.06 * Math.sin(v * 0.6 - f * 0.08) + 0.03 * Math.sin((x + v) * 2.1 + f * 0.2)));
    }
    p.needsUpdate = true;
    geo.computeVertexNormals();
  }, [geo, f, song]);
  return (
    <mesh geometry={geo} rotation={[-Math.PI / 2, 0, 0]} position={[0, y, -dai / 2]} receiveShadow>
      <meshPhysicalMaterial color={mau} roughness={0.06} metalness={0.15} envMapIntensity={1.4} transparent opacity={1 - do_trong * 0.6}
        clearcoat={1} clearcoatRoughness={0.05} side={THREE.DoubleSide} />
    </mesh>
  );
};

export const NuocDang = (p) => {
  const q = {...NUOC_DANG_MAC_DINH, ...p};
  const f = useCurrentFrame();
  const {fps, width, height, durationInFrames: D} = useVideoConfig();
  const t = f / fps;
  const tuong = useAnh(q.tuong, true);
  const nguoi = useAnh(q.nguoi);
  const troi = useAnh(q.troi);
  const thuoc = useThuoc(q.cao_thanh);
  // trời làm môi trường phản chiếu cho mặt nước (nước không còn một mảng màu phẳng)
  const moiTruong = useMemo(() => {
    if (!troi) return null;
    const t = troi.clone();
    t.mapping = THREE.EquirectangularReflectionMapping;
    t.needsUpdate = true;
    return t;
  }, [troi]);
  const dang = interpolate(t, [q.bat_dau_dang, q.bat_dau_dang + q.thoi_gian_dang], [0, 1],
    {...kep, easing: Easing.bezier(0.3, 0.05, 0.25, 1)});
  const muc = 0.02 + dang * q.muc_nuoc;
  // camera: đầu -> giữa (khi nước dâng) -> cuối, êm
  const lerp = (a, b, k) => a.map((v, i) => v + (b[i] - v) * k);
  const k1 = interpolate(t, [0, q.bat_dau_dang + q.thoi_gian_dang * 0.5], [0, 1], {...kep, easing: Easing.bezier(0.45, 0, 0.3, 1)});
  const k2 = interpolate(t, [q.bat_dau_dang + q.thoi_gian_dang * 0.5, D / fps], [0, 1], {...kep, easing: Easing.bezier(0.45, 0, 0.3, 1)});
  const cam = k2 > 0 ? lerp(q.cam_giua, q.cam_cuoi, k2) : lerp(q.cam_dau, q.cam_giua, k1);
  const {rong: R, dai: L, cao_thanh: C} = q;
  // key theo ảnh: three không tự dựng lại shader khi map đổi từ null -> ảnh (xem thử: vài khung tường trắng)
  const be = <meshStandardMaterial key={tuong ? 'anh' : 'tron'} color={tuong ? '#ffffff' : '#8d8b86'} map={tuong || null}
    roughness={0.95} />;
  const thac = q.thac && dang > 0 && dang < 1;
  const nguoiH = q.nguoi_cao, nguoiW = nguoi ? nguoiH * (nguoi.image.width / nguoi.image.height) : 0;
  const chuP = q.chu ? interpolate(t, [q.chu_luc, q.chu_luc + 0.5], [0, 1], {...kep, easing: Easing.out(Easing.cubic)}) : 0;
  return (
    <AbsoluteFill style={{background: '#9fb4c2', opacity: interpolate(f, [0, 6, D - 8, D], [0, 1, 1, 0], kep)}}>
      <ThreeCanvas width={width} height={height} shadows camera={{fov: 50, near: 0.1, far: 900, position: cam}}>
        <CameraNhin cam={cam} nhin={q.nhin} />
        <fog attach="fog" args={['#a9bcc8', 40, 260]} />
        <hemisphereLight args={['#dfe9f2', '#5a5348', 0.9]} />
        <directionalLight position={[18, 40, 12]} intensity={2.2} castShadow shadow-mapSize={[2048, 2048]}
          shadow-camera-left={-60} shadow-camera-right={60} shadow-camera-top={60} shadow-camera-bottom={-60} />
        {troi ? <mesh position={[0, 40, -L - 120]}><planeGeometry args={[520, 290]} /><meshBasicMaterial map={troi} fog={false} /></mesh> : null}
        {moiTruong ? <primitive object={moiTruong} attach="environment" /> : null}
        {/* mặt đất quanh âu: 4 dải chừa miệng âu */}
        {[[-(R / 2 + 4 + 60), -L / 2, 120, L + 260], [R / 2 + 4 + 60, -L / 2, 120, L + 260], [0, 3 + 60, R + 8, 120],
          [0, -L - 3 - 60, R + 8, 120]].map(([x, z, w, d], i) => (
          <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[x, C, z]} receiveShadow>
            <planeGeometry args={[w, d]} /><meshStandardMaterial color="#77736b" roughness={1} />
          </mesh>))}
        {/* đáy + hai thành + cửa xa (khối bê tông, chừa lòng âu) */}
        <Hop kich={[R, 0.5, L]} position={[0, -0.25, -L / 2]} receiveShadow>{be}</Hop>
        <Hop kich={[4, C, L]} position={[-R / 2 - 2, C / 2, -L / 2]} castShadow receiveShadow>{be}</Hop>
        <Hop kich={[4, C, L]} position={[R / 2 + 2, C / 2, -L / 2]} castShadow receiveShadow>{be}</Hop>
        {[-L - 1.5, 1.5].map((z) => <Hop key={z} kich={[R + 8, C, 3]} position={[0, C / 2, z]} castShadow receiveShadow>
          <meshStandardMaterial key={tuong ? 'anh' : 'tron'} color="#77736c" map={tuong || null} roughness={0.9} /></Hop>)}
        {/* thước đo trên thành trái, gần camera */}
        {q.thuoc_do ? <mesh position={[-R / 2 + 0.06, C / 2, -9]} rotation={[0, Math.PI / 2, 0]}>
          <planeGeometry args={[C / 4, C]} /><meshBasicMaterial map={thuoc} transparent toneMapped={false} /></mesh> : null}
        {/* người dưới đáy (ảnh tách nền đứng thẳng, luôn quay về camera theo chiều ngang) */}
        {nguoi ? <NguoiQuay vt={[-R / 2 + 3.2, nguoiH / 2, -10]} cam={cam} w={nguoiW} h={nguoiH} tex={nguoi} /> : null}
        {/* khối nước: thân mờ + mặt nước gợn (chưa dâng thì ẩn — mặt nước sát đáy tạo vệt loang) */}
        {dang > 0.003 ? <>
          <mesh position={[0, muc / 2, -L / 2]}><boxGeometry args={[R - 0.02, muc, L - 0.02]} />
            <meshStandardMaterial color={q.mau_nuoc} transparent opacity={0.55 - q.do_trong * 0.35} depthWrite={false} /></mesh>
          <MatNuoc rong={R} dai={L} y={muc} mau={q.mau_nuoc} do_trong={q.do_trong} song={q.song * Math.min(1, muc)} f={f} />
          {/* vạch mực nước trên thước */}
          {q.thuoc_do ? <mesh position={[-R / 2 + 0.1, muc + 0.02, -9]} rotation={[0, Math.PI / 2, 0]}>
            <planeGeometry args={[C / 4 + 1.2, 0.18]} /><meshBasicMaterial color="#ffd23f" toneMapped={false} /></mesh> : null}
        </> : null}
        {/* thác tràn vào từ cửa xa */}
        {thac ? <mesh position={[0, (C + muc) / 2, -L + 0.2]}><planeGeometry args={[R * 0.7, C - muc]} />
          <meshStandardMaterial color="#e8f2f4" transparent opacity={0.55 + 0.15 * Math.sin(f * 0.7)} roughness={0.3} /></mesh> : null}
      </ThreeCanvas>
      {q.so_dem ? <div style={{position: 'absolute', left: 90, top: 70, fontFamily: FONT, fontWeight: 900, fontSize: 120, color: '#fff',
        textShadow: '0 6px 24px rgba(0,0,0,0.7)', opacity: interpolate(t, [q.bat_dau_dang, q.bat_dau_dang + 0.3], [0, 1], kep)}}>
        {(dang * q.muc_nuoc).toFixed(q.muc_nuoc < 10 ? 1 : 0).replace('.', ',')} m</div> : null}
      {q.chu ? <div style={{position: 'absolute', left: 0, right: 0, bottom: 110, textAlign: 'center', fontFamily: FONT, fontWeight: 900,
        fontSize: 104, color: '#fff', textShadow: '0 4px 18px rgba(0,0,0,0.85)', opacity: chuP,
        transform: `translateY(${(1 - chuP) * 40}px)`}}>{q.chu}</div> : null}
    </AbsoluteFill>
  );
};

// ảnh người đứng: tấm phẳng luôn quay mặt về camera (nhìn từ trên xuống không bị bẹp thành vệt)
const NguoiQuay = ({vt, cam, w, h, tex}) => {
  const ref = React.useRef();
  React.useLayoutEffect(() => {
    if (ref.current) ref.current.lookAt(...cam);
  });
  return <mesh ref={ref} position={vt} castShadow><planeGeometry args={[w, h]} />
    <meshStandardMaterial map={tex} transparent alphaTest={0.4} roughness={1} side={THREE.DoubleSide} /></mesh>;
};

// camera đặt lại vị trí + hướng nhìn mỗi khung (theo useCurrentFrame qua props)
const CameraNhin = ({cam, nhin}) => {
  const camera = useThree((s) => s.camera);
  camera.position.set(...cam);
  camera.lookAt(...nhin);
  camera.updateProjectionMatrix();
  return null;
};
