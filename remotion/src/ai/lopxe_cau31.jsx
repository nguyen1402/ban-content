import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
	anhToanCanh: z.string().describe('Ảnh toàn cảnh bãi lốp'),
	anhBaoCu: z.string().describe('Ảnh trang báo cũ'),
	anhKhoiDen: z.string().describe('Ảnh cột khói đen khổng lồ'),
	chuHalloween: z.string().describe('Dòng chữ lớn trên trang báo'),
	coChuLon: z.number().describe('Cỡ chữ dòng đầu (px)'),
	coSoNam: z.number().describe('Cỡ chữ năm 1983 (px)'),
	toiNen: z.number().describe('Độ tối lớp phủ ảnh nền (0..0.5)'),
	nhanBanDo: z.string().describe('Nhãn trên bản đồ định vị'),
	coNhanBanDo: z.number().describe('Cỡ chữ nhãn bản đồ (px)'),
});

const BanDo = ({nhan, co}) => {
	const f = useCurrentFrame();
	const vao = interpolate(f, [0, 10], [0, 1], kep);
	const p = (f % 45) / 45;
	const r = 12 + p * 48;
	const op = 0.85 * (1 - p);
	const dd = 7 + 3 * Math.sin(f / 6);

	return (
		<div
			style={{
				width: 390,
				height: 310,
				borderRadius: 22,
				overflow: 'hidden',
				position: 'relative',
				background: 'rgba(14,30,26,0.88)',
				border: '3px solid rgba(255,255,255,0.6)',
				boxShadow: '0 16px 44px rgba(0,0,0,0.55)',
				opacity: vao,
				transform: `translateY(${interpolate(vao, [0, 1], [26, 0])}px)`,
			}}
		>
			<svg width={390} height={310} viewBox="0 0 390 310" style={{position: 'absolute', left: 0, top: 0}}>
				<rect x={0} y={0} width={390} height={310} fill="rgba(22,44,36,0.9)" />
				<polyline points="0,64 120,84 212,62 330,98 390,84" fill="none" stroke="rgba(140,215,175,0.6)" strokeWidth={5} />
				<polyline points="0,204 140,220 252,192 390,212" fill="none" stroke="rgba(140,215,175,0.42)" strokeWidth={4} />
				<polyline points="62,0 82,120 58,222 92,310" fill="none" stroke="rgba(140,215,175,0.5)" strokeWidth={4} />
				<polyline points="262,0 250,112 282,202 252,310" fill="none" stroke="rgba(140,215,175,0.34)" strokeWidth={3} />
				<circle cx={195} cy={112} r={r} fill="none" stroke={VANG} strokeWidth={4} opacity={op} />
				<circle cx={195} cy={112} r={dd} fill={VANG} />
				<circle cx={195} cy={112} r={3} fill="#fff" />
			</svg>
			<div
				style={{
					position: 'absolute',
					left: 0,
					bottom: 8,
					width: '100%',
					textAlign: 'center',
					fontFamily: FONT,
					fontSize: co,
					fontWeight: 900,
					color: '#fff',
					letterSpacing: 1,
					textShadow: '0 4px 14px rgba(0,0,0,0.8)',
				}}
			>
				{nhan}
			</div>
		</div>
	);
};

const ChuBaoLon = ({chu, co1, co2}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const parts = chu.trim().split(' ');
	const dong2 = parts.length > 1 ? parts[parts.length - 1] : '';
	const dong1 = parts.length > 1 ? parts.slice(0, -1).join(' ') : chu;
	const s = spring({frame: f, fps, config: {damping: 200, mass: 0.6}});
	const scale = interpolate(s, [0, 1], [1.34, 1]);
	const op = interpolate(f, [0, 10], [0, 1], kep);
	const w = interpolate(f, [16, 42], [0, 1], {...kep, easing: Easing.out(Easing.cubic)});

	return (
		<div
			style={{
				width: 1620,
				opacity: op,
				transform: `scale(${scale})`,
				transformOrigin: 'left center',
				fontFamily: FONT,
				color: '#fff',
				textShadow: '0 8px 30px rgba(0,0,0,0.8), 0 2px 6px rgba(0,0,0,0.95)',
			}}
		>
			<div style={{fontSize: co1, fontWeight: 900, letterSpacing: 2, lineHeight: 1}}>{dong1}</div>
			<div style={{fontSize: co2, fontWeight: 900, letterSpacing: 4, lineHeight: 1.05, marginTop: 10, color: VANG}}>{dong2}</div>
			<div style={{height: 16, width: `${w * 100}%`, background: VANG, marginTop: 22, borderRadius: 10}} />
		</div>
	);
};

export const Canh = ({anhToanCanh, anhBaoCu, anhKhoiDen, chuHalloween, coChuLon, coSoNam, toiNen, nhanBanDo, coNhanBanDo}) => {
	return (
		<AbsoluteFill style={{backgroundColor: '#0b0b0b'}}>
			{/* BEAT 1 — frame 4: toàn cảnh bãi lốp */}
			<Interactive.Div
				name="Ảnh toàn cảnh bãi lốp"
				from={0}
				durationInFrames={80}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={src(anhToanCanh)} tu={1} den={1.14} goc="50% 50%" toi={toiNen} />
			</Interactive.Div>

			<Interactive.Div
				name="Bản đồ định vị Winchester"
				from={8}
				durationInFrames={66}
				style={{position: 'absolute', left: 1450, top: 720, width: 390, height: 310}}
			>
				<BanDo nhan={nhanBanDo} co={coNhanBanDo} />
			</Interactive.Div>

			{/* BEAT 2 — frame 71: trang báo cũ */}
			<Interactive.Div
				name="Ảnh trang báo cũ"
				from={71}
				durationInFrames={100}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={src(anhBaoCu)} tu={1.13} den={1} goc="50% 45%" toi={0.1} />
			</Interactive.Div>

			<Interactive.Div
				name="Lớp tối làm nổi chữ"
				from={71}
				durationInFrames={100}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<div
					style={{
						width: 1920,
						height: 1080,
						background: 'linear-gradient(100deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.18) 52%, rgba(0,0,0,0) 100%)',
					}}
				/>
			</Interactive.Div>

			<Interactive.Div
				name="Chữ lớn ĐÊM HALLOWEEN 1983"
				from={71}
				durationInFrames={100}
				style={{position: 'absolute', left: 140, top: 350, width: 1620, height: 420}}
			>
				<ChuBaoLon chu={chuHalloween} co1={coChuLon} co2={coSoNam} />
			</Interactive.Div>

			{/* BEAT 3 — frame 165: cột khói đen khổng lồ */}
			<Interactive.Div
				name="Ảnh cột khói đen khổng lồ"
				from={165}
				durationInFrames={61}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={src(anhKhoiDen)} tu={1.05} den={1.2} goc="50% 38%" toi={0.12} />
			</Interactive.Div>
		</AbsoluteFill>
	);
};
