import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
	anh1: z.string().describe('Ảnh đầm lầy hải ly hoang dã Bắc Mỹ'),
	anh2: z.string().describe('Ảnh bàn kiểm định da lông thế kỷ 19'),
	anh3: z.string().describe('Ảnh áo choàng viền lông và mũ phớt hải ly thời Victoria'),
	chuNhan: z.string().describe('Chữ ngắn trên nhãn giá vintage (tối đa 4 từ, không chứa số/năm)'),
	coNhan: z.number().describe('Cỡ chữ nhãn giá (px)'),
	mauKinh: z.string().describe('Màu đồng thau của gọng kính lúp'),
	toi1: z.number().describe('Độ tối ảnh đầm lầy'),
	toi2: z.number().describe('Độ tối ảnh bàn da lông'),
	toi3: z.number().describe('Độ tối ảnh tiệm may'),
});

export const Canh = (props) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();

	// ---- chuyển cảnh mượt giữa 3 nhịp ----
	const op2 = interpolate(f, [61, 73], [0, 1], kep);
	const op3 = interpolate(f, [164, 176], [0, 1], kep);

	// ---- nhịp 2: kính lúp quang học ----
	const f2 = f - 61;
	const kinhLen = spring({frame: f2, fps, config: {damping: 200}, durationInFrames: 24});
	const kinhOp = interpolate(f2, [0, 12], [0, 1], kep);
	const kinhScale = 0.84 + 0.16 * kinhLen;

	// ---- nhịp 3: nhãn giá vintage ----
	const fTag = f - 176;
	const tagLen = spring({frame: fTag, fps, config: {damping: 200}, durationInFrames: 20});
	const tagOp = interpolate(fTag, [0, 10], [0, 1], kep);

	// Chỉ giữ tối đa 4 từ để chữ trên nhãn luôn ngắn gọn
	const nhanNgan = String(props.chuNhan || '')
		.trim()
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 4)
		.join(' ');

	return (
		<AbsoluteFill style={{backgroundColor: '#0b0a08'}}>
			{/* ================= NHỊP 1 — ĐẦM LẦY ================= */}
			<Interactive.Div
				name="Đầm lầy hải ly"
				from={0}
				durationInFrames={74}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={props.anh1} tu={1.18} den={1.0} goc="50% 58%" toi={props.toi1} />
			</Interactive.Div>

			{/* ================= NHỊP 2 — BÀN DA LÔNG ================= */}
			<Interactive.Div
				name="Bàn kiểm định da lông"
				from={61}
				durationInFrames={117}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op2}}>
					<AnhNen anh={props.anh2} tu={1.0} den={1.12} goc="45% 50%" toi={props.toi2} />
				</div>
			</Interactive.Div>

			{/* Kính lúp quang học soi lớp lông nỉ tơ */}
			<Interactive.Div
				name="Kính lúp quang học"
				from={61}
				durationInFrames={117}
				style={{position: 'absolute', left: 1160, top: 200, width: 560, height: 560}}
			>
				<div
					style={{
						position: 'absolute',
						left: 0,
						top: 0,
						width: 560,
						height: 560,
						transform: `scale(${kinhScale})`,
						opacity: kinhOp,
					}}
				>
					{/* cán kính */}
					<div
						style={{
							position: 'absolute',
							left: 437,
							top: 450,
							width: 66,
							height: 310,
							borderRadius: 33,
							background: `linear-gradient(90deg,#4a3110,${props.mauKinh} 45%,#f0d79a 56%,#7a5a22)`,
							transform: 'rotate(-40deg)',
							transformOrigin: 'top center',
						}}
					/>
					{/* thấu kính */}
					<div
						style={{
							position: 'absolute',
							left: 0,
							top: 0,
							width: 560,
							height: 560,
							borderRadius: '50%',
							overflow: 'hidden',
							boxSizing: 'border-box',
							border: `16px solid ${props.mauKinh}`,
							backgroundColor: '#191309',
						}}
					>
						<div
							style={{
								position: 'absolute',
								inset: 0,
								backgroundImage: `url(${src(props.anh2)})`,
								backgroundSize: '290% auto',
								backgroundPosition: `${44 + 6 * kinhLen}% ${46 - 5 * kinhLen}%`,
								transform: `scale(${1.02 + 0.06 * kinhLen})`,
							}}
						/>
						<div
							style={{
								position: 'absolute',
								inset: 0,
								borderRadius: '50%',
								border: '6px solid rgba(255,240,200,0.30)',
							}}
						/>
					</div>
				</div>
			</Interactive.Div>

			{/* ================= NHỊP 3 — TIỆM MAY VICTORIA ================= */}
			<Interactive.Div
				name="Tiệm may quý tộc Victoria"
				from={164}
				durationInFrames={74}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, opacity: op3}}>
					<AnhLia anh={props.anh3} huong="phai" quang={70} phong={1.12} toi={props.toi3} />
				</div>
			</Interactive.Div>

			{/* Nhãn giá vintage */}
			<Interactive.Div
				name="Nhãn giá vintage"
				from={176}
				durationInFrames={62}
				style={{position: 'absolute', left: 1210, top: 760, width: 540, height: 190}}
			>
				<div
					style={{
						position: 'absolute',
						left: 0,
						top: 0,
						width: 540,
						height: 190,
						boxSizing: 'border-box',
						background: '#f2e6c9',
						borderRadius: 14,
						border: '5px dashed #8a6a3a',
						boxShadow: '0 16px 34px rgba(0,0,0,0.45)',
						transform: `rotate(-7deg) scale(${0.88 + 0.12 * tagLen})`,
						opacity: tagOp,
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
					}}
				>
					<div
						style={{
							position: 'absolute',
							left: 34,
							top: 80,
							width: 30,
							height: 30,
							borderRadius: '50%',
							background: '#c8b795',
							boxShadow: 'inset 0 3px 6px rgba(0,0,0,0.45)',
						}}
					/>
					<div
						style={{
							fontFamily: FONT,
							fontSize: props.coNhan,
							lineHeight: 1,
							letterSpacing: 3,
							color: '#3a2a16',
							paddingLeft: 50,
							paddingRight: 20,
							textAlign: 'center',
							whiteSpace: 'nowrap',
						}}
					>
						{nhanNgan}
					</div>
				</div>
			</Interactive.Div>
		</AbsoluteFill>
	);
};
