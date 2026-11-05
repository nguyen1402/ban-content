import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
  nenBanLamViec: z.string().describe('Ảnh nền bàn làm việc 1970'),
  tachTayTinhToan: z.string().describe('Ảnh tách tay kỹ sư'),
  nenDapBeTong: z.string().describe('Ảnh nền đập bê tông'),
  nenHemNui: z.string().describe('Ảnh nền hẻm núi Arizona'),
  canDapLopXe: z.string().describe('Ảnh cảnh đập lốp xe'),
});

export const Canh = (props) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{backgroundColor: '#000', fontFamily: FONT, overflow: 'hidden'}}>
      {/* 0.0s - 1.8s: Giáo sư Honig tính toán */}
      <Interactive.Div name="CanhBanLamViec" from={0} durationInFrames={60} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={props.nenBanLamViec} tu={1} den={1.05} goc="50% 50%" toi={0.2} />
        <Interactive.Div name="TayTinhToan" from={0} durationInFrames={60} style={{position: 'absolute', right: 0, top: 200}}>
          <Img src={src(props.tachTayTinhToan)} style={{width: 800, transform: `translateX(${interpolate(frame, [0, 30], [200, 0], {extrapolateRight: 'clamp'})}px)`}} />
        </Interactive.Div>
        <Interactive.Div name="TieuDeHonig" from={10} durationInFrames={50} style={{position: 'absolute', left: 100, bottom: 100}}>
          <div style={{fontSize: 72, color: '#fff', fontWeight: 'bold', textShadow: '2px 2px 8px rgba(0,0,0,0.8)'}}>
            GIÁO SƯ HONIG TÍNH TOÁN
          </div>
        </Interactive.Div>
      </Interactive.Div>

      {/* 1.8s - 4.5s: Đập bê tông quy mô tương đương */}
      <Interactive.Div name="CanhDapBeTong" from={50} durationInFrames={95} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={props.nenDapBeTong} tu={1.02} den={1.1} goc="50% 40%" toi={0.15} />
        <Interactive.Div name="NhanDapBeTong" from={55} durationInFrames={90} style={{position: 'absolute', left: 120, top: 120}}>
          <div style={{fontSize: 90, color: VANG, fontWeight: 'bold', textShadow: '3px 3px 10px rgba(0,0,0,0.9)'}}>
            ĐẬP BÊ TÔNG
          </div>
          <div style={{fontSize: 40, color: '#fff', marginTop: 10, textShadow: '2px 2px 6px rgba(0,0,0,0.8)'}}>
            Quy mô tương đương đập lốp xe
          </div>
        </Interactive.Div>
      </Interactive.Div>

      {/* 4.8s - 8.0s: 35 nghìn đô la */}
      <Interactive.Div name="CanhGiaTien" from={140} durationInFrames={100} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={props.nenDapBeTong} tu={1.1} den={1.2} goc="50% 50%" toi={0.3} />
        <Interactive.Div name="HienSoTien" from={145} durationInFrames={95} style={{position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center'}}>
          <div style={{fontSize: 50, color: '#fff', marginBottom: 20, textShadow: '2px 2px 8px rgba(0,0,0,0.8)'}}>
            Kinh phí dự kiến
          </div>
          <div style={{fontSize: 140, color: '#ff4d4d', fontWeight: 'bold', textShadow: '4px 4px 15px rgba(0,0,0,0.9)'}}>
            {frame > 215 ? '$35,000' : `$${Math.floor(interpolate(frame, [145, 215], [5000, 35000], {extrapolateRight: 'clamp'}))}`}
          </div>
          <div style={{fontSize: 45, color: VANG, marginTop: 10, textShadow: '2px 2px 6px rgba(0,0,0,0.8)'}}>
            Gấp 7 lần kinh phí đập lốp xe
          </div>
        </Interactive.Div>
      </Interactive.Div>

      {/* 8.2s - 10.8s: Khó hiểu tại thực địa */}
      <Interactive.Div name="CanhThucDia" from={240} durationInFrames={80} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={props.nenHemNui} tu={1.0} den={1.05} goc="40% 50%" toi={0.2} />
        <Interactive.Div name="ThacMac" from={245} durationInFrames={75} style={{position: 'absolute', right: 200, top: 200}}>
          <div style={{fontSize: 120, color: VANG, fontWeight: 'bold', textShadow: '3px 3px 12px rgba(0,0,0,0.9)'}}>
            ?
          </div>
        </Interactive.Div>
        <Interactive.Div name="TieuDeKhoHieu" from={245} durationInFrames={75} style={{position: 'absolute', left: 100, bottom: 120}}>
          <div style={{fontSize: 64, color: '#fff', fontWeight: 'bold', textShadow: '2px 2px 8px rgba(0,0,0,0.8)'}}>
            ĐIỀU KHÓ HIỂU...
          </div>
        </Interactive.Div>
      </Interactive.Div>

      {/* 10.9s - 13.1s: Công năng của đập lốp xe */}
      <Interactive.Div name="CanhCongNang" from={320} durationInFrames={72} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}>
        <AnhNen anh={props.canDapLopXe} tu={1.05} den={1.15} goc="50% 50%" toi={0.1} />
        <Interactive.Div name="LightSweep" from={320} durationInFrames={72} style={{
          position: 'absolute',
          left: `${interpolate(frame, [320, 392], [-50, 150], {extrapolateRight: 'clamp'})}%`,
          top: 0,
          width: '30%',
          height: '100%',
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
          transform: 'skewX(-20deg)',
          pointerEvents: 'none'
        }} />
        <Interactive.Div name="TieuDeCongNang" from={325} durationInFrames={67} style={{position: 'absolute', left: 100, bottom: 120}}>
          <div style={{fontSize: 72, color: VANG, fontWeight: 'bold', textShadow: '3px 3px 10px rgba(0,0,0,0.9)'}}>
            CÔNG NĂNG NGHỊCH LÝ
          </div>
        </Interactive.Div>
      </Interactive.Div>
    </AbsoluteFill>
  );
};
