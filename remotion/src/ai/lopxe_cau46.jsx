import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {AnhNen, ChuNoi, MuiTen} from './thu_vien.jsx';

export const schema = z.object({
	anhSaMac: z.string().describe('Ảnh toàn cảnh sa mạc dưới nắng'),
	anhXeng: z.string().describe('Ảnh cận cảnh xẻng đào cát'),
	anhDat: z.string().describe('Ảnh cắt lớp đất sa mạc'),
	chuDoSau: z.string().describe('Dòng chữ độ sâu hiển thị'),
	coChuDoSau: z.number().describe('Cỡ chữ độ sâu (px)'),
	zoomSaMac: z.number().describe('Mức zoom cuối của ảnh sa mạc'),
	zoomXeng: z.number().describe('Mức zoom đầu (kéo về) của ảnh xẻng đào'),
	zoomDat: z.number().describe('Mức zoom cuối của ảnh cắt lớp đất'),
	doRongQuet: z.number().describe('Bề rộng vệt nắng quét (px)'),
	gocQuet: z.number().describe('Góc nghiêng vệt nắng (độ)'),
	doMoQuet: z.number().describe('Độ đậm vệt nắng (0-1)'),
	chuKyQuet: z.number().describe('Số frame cho một lượt quét nắng'),
});

// Vệt nắng chói quét ngang khung hình (hiệu ứng ánh sáng, không phải ảnh)
const VetQuet: React.FC<{doRong: number; goc: number; doMo: number; chuKy: number}> = ({
	doRong,
	goc,
	doMo,
	chuKy,
}) => {
	const f = useCurrentFrame();
	const p = (f % chuKy) / chuKy;
	const x = interpolate(p, [0, 1], [-doRong * 1.5, 1920 + doRong * 0.5], {
		easing: Easing.inOut(Easing.ease),
	});
	const op = interpolate(p, [0, 0.18, 0.82, 1], [0, 1, 1, 0]);
	return (
		<div
			style={{
				position: 'absolute',
				left: x,
				top: -260,
				width: doRong,
				height: 1600,
				transform: `rotate(${goc}deg)`,
				background: `linear-gradient(90deg, rgba(255,248,214,0) 0%, rgba(255,248,214,${doMo}) 50%, rgba(255,248,214,0) 100%)`,
				opacity: op,
				mixBlendMode: 'screen',
			}}
		/>
	);
};

export const Canh = ({
	anhSaMac,
	anhXeng,
	anhDat,
	chuDoSau,
	coChuDoSau,
	zoomSaMac,
	zoomXeng,
	zoomDat,
	doRongQuet,
	gocQuet,
	doMoQuet,
	chuKyQuet,
}: z.infer<typeof schema>) => {
	return (
		<AbsoluteFill style={{backgroundColor: '#2a1d10'}}>
			{/* NHỊP 1 — toàn cảnh sa mạc dưới nắng gay gắt */}
			<Interactive.Div
				name="Toàn cảnh sa mạc"
				from={0}
				durationInFrames={112}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={anhSaMac} tu={1} den={zoomSaMac} goc="50% 45%" toi={0.1} />
			</Interactive.Div>

			<Interactive.Div
				name="Vệt nắng quét"
				from={0}
				durationInFrames={112}
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: 1920,
					height: 1080,
					overflow: 'hidden',
				}}
			>
				<VetQuet doRong={doRongQuet} goc={gocQuet} doMo={doMoQuet} chuKy={chuKyQuet} />
			</Interactive.Div>

			{/* NHỊP 2 — cận cảnh xẻng cào lớp cát khô */}
			<Interactive.Div
				name="Cận cảnh xẻng đào cát"
				from={103}
				durationInFrames={90}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={anhXeng} tu={zoomXeng} den={1} goc="50% 50%" toi={0.06} />
			</Interactive.Div>

			{/* NHỊP 3 — cắt lớp đất sa mạc + số đo chiều sâu */}
			<Interactive.Div
				name="Cắt lớp đất sa mạc"
				from={184}
				durationInFrames={170}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={anhDat} tu={1} den={zoomDat} goc="50% 60%" toi={0.04} />
			</Interactive.Div>

			<Interactive.Div
				name="Mũi tên chỉ chiều sâu"
				from={186}
				durationInFrames={168}
				style={{position: 'absolute', left: 940, top: 280}}
			>
				<MuiTen dx={0} dy={340} cong={0.18} />
			</Interactive.Div>

			<Interactive.Div
				name="Dòng chữ độ sâu"
				from={186}
				durationInFrames={168}
				style={{position: 'absolute', left: 1120, top: 370}}
			>
				<ChuNoi chu={chuDoSau} co={coChuDoSau} />
			</Interactive.Div>
		</AbsoluteFill>
	);
};
