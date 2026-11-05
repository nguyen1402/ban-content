import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
	anhNen: z.string().describe('Ảnh nền công trình thủy lợi'),
	anhTuong: z.string().describe('Ảnh cắt lớp tường bê tông cốt thép'),
	anhCotThep: z.string().describe('Ảnh cận cảnh cốt thép trong tường'),
	zoomNenDau: z.number().describe('Độ zoom đầu của ảnh nền'),
	zoomNenCuoi: z.number().describe('Độ zoom cuối của ảnh nền'),
	toiNen: z.number().describe('Độ tối lớp phủ ảnh nền'),
	fTuong: z.number().describe('Frame tường bê tông trượt lên'),
	fCotThep: z.number().describe('Frame thẻ cốt thép trượt vào'),
	fMuiTen: z.number().describe('Frame mũi tên lực vẽ ra'),
	xTuong: z.number().describe('Toạ độ X của tường bê tông'),
	yTuong: z.number().describe('Toạ độ Y của tường bê tông'),
	wTuong: z.number().describe('Chiều rộng tường bê tông'),
	hTuong: z.number().describe('Chiều cao tường bê tông'),
	xThe: z.number().describe('Toạ độ X thẻ cốt thép'),
	yThe: z.number().describe('Toạ độ Y thẻ cốt thép'),
	wThe: z.number().describe('Chiều rộng thẻ cốt thép'),
	hThe: z.number().describe('Chiều cao thẻ cốt thép'),
	mauMuiTen: z.string().describe('Màu mũi tên lực'),
	dayMuiTen: z.number().describe('Độ dày nét mũi tên'),
});

const ARROW_YS = [350, 480, 610];

const RING_CX = 1430;
const RING_CY = 570;
const RING_R = 120;
const RING_LEN = 2 * Math.PI * RING_R;

export const Canh = (props) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	/* ---------- Nhịp 2: tường bê tông cốt thép (frame 80) ---------- */
	const lw = frame - 80;
	const wallSpring = spring({
		frame: Math.max(0, lw),
		fps,
		config: {damping: 15, mass: 1.1, stiffness: 80},
	});
	const wallY = interpolate(wallSpring, [0, 1], [560, 0]);
	const wallOp = interpolate(lw, [0, 8], [0, 1], kep);
	const wallDrift = interpolate(lw, [0, 236], [1.06, 1.0], kep);

	/* ---------- Nhịp 1: thẻ cận cảnh cốt thép (frame 12) ---------- */
	const lc = frame - 12;
	const cardSpring = spring({
		frame: Math.max(0, lc),
		fps,
		config: {damping: 18, mass: 1, stiffness: 90},
	});
	const cardX = interpolate(cardSpring, [0, 1], [-720, 0]);
	const cardOp = interpolate(lc, [0, 10], [0, 1], kep);
	const cardDrift = interpolate(lc, [0, 300], [0, -20], kep);

	/* ---------- Nhịp 2b: vòng khoanh đúng vị trí cốt thép (frame 150) ---------- */
	const lr = frame - 150;
	const ringDraw = interpolate(lr, [0, 26], [0, 1], {
		...kep,
		easing: Easing.out(Easing.cubic),
	});
	const ringOp = interpolate(lr, [0, 6], [0, 1], kep);
	const ringPulse = 1 + 0.035 * Math.sin(Math.max(0, lr) / 6);

	/* ---------- Nhịp 3: mũi tên lực dòng chảy (frame 242) ---------- */
	const la = frame - 242;
	const arrowPush = interpolate(la, [0, 74], [0, 26], kep);

	return (
		<AbsoluteFill style={{backgroundColor: '#0d1117'}}>
			{/* Ảnh nền công trình thủy lợi — chạy suốt shot */}
			<Interactive.Div
				name="Ảnh nền công trình thủy lợi"
				from={0}
				durationInFrames={316}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen
					anh={props.anhNen}
					tu={props.zoomNenDau}
					den={props.zoomNenCuoi}
					goc="50% 45%"
					toi={props.toiNen}
				/>
			</Interactive.Div>

			{/* LỚP TRƯỚC 1: thẻ ảnh cận cảnh cốt thép trượt vào từ trái, giữ gần hết shot */}
			<Interactive.Div
				name="Thẻ cận cảnh cốt thép"
				from={12}
				durationInFrames={300}
				style={{position: 'absolute', left: 80, top: 660, width: 640, height: 360}}
			>
				<div
					style={{
						position: 'relative',
						width: 640,
						height: 360,
						transform: `translateX(${cardX + cardDrift}px)`,
						opacity: cardOp,
						borderRadius: 14,
						overflow: 'hidden',
						border: '8px solid #ffffff',
						boxShadow: '0 26px 60px rgba(0,0,0,0.45)',
						boxSizing: 'border-box',
					}}
				>
					<Img
						name="Cận cảnh cốt thép"
						src={src(props.anhCotThep)}
						style={{width: 640, height: 360, objectFit: 'cover'}}
					/>
					<div
						style={{
							position: 'absolute',
							left: 0,
							bottom: 0,
							width: 640,
							height: 54,
							background: 'rgba(13,17,23,0.78)',
							display: 'flex',
							alignItems: 'center',
							paddingLeft: 20,
							boxSizing: 'border-box',
							fontFamily: FONT,
							fontSize: 26,
							fontWeight: 700,
							letterSpacing: 1.5,
							color: VANG,
						}}
					>
						CỐT THÉP CHỊU LỰC
					</div>
				</div>
			</Interactive.Div>

			{/* LỚP TRƯỚC 2: tường bê tông cắt lớp trượt lên ở foreground */}
			<Interactive.Div
				name="Tường bê tông cốt thép"
				from={80}
				durationInFrames={236}
				style={{position: 'absolute', left: 1040, top: 300, width: 780, height: 541}}
			>
				<div
					style={{
						width: 780,
						height: 541,
						transform: `translateY(${wallY}px) scale(${wallDrift})`,
						transformOrigin: '50% 100%',
						opacity: wallOp,
					}}
				>
					<Img
						name="Tường bê tông"
						src={src(props.anhTuong)}
						style={{width: 780, height: 541, objectFit: 'contain'}}
					/>
				</div>
			</Interactive.Div>

			{/* LỚP TRƯỚC 3: vòng khoanh đúng chỗ thanh cốt thép trên tường */}
			<Interactive.Div
				name="Vòng khoanh cốt thép"
				from={150}
				durationInFrames={166}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<svg
					width={1920}
					height={1080}
					viewBox="0 0 1920 1080"
					style={{position: 'absolute', left: 0, top: 0}}
				>
					<g
						style={{opacity: ringOp}}
						transform={`translate(${RING_CX} ${RING_CY}) scale(${ringPulse}) translate(${-RING_CX} ${-RING_CY})`}
					>
						<circle
							cx={RING_CX}
							cy={RING_CY}
							r={RING_R}
							fill="none"
							stroke={props.mauMuiTen}
							strokeWidth={7}
							strokeLinecap="round"
							strokeDasharray={RING_LEN}
							strokeDashoffset={(1 - ringDraw) * RING_LEN}
							transform={`rotate(-90 ${RING_CX} ${RING_CY})`}
						/>
						<circle
							cx={RING_CX}
							cy={RING_CY}
							r={RING_R + 14}
							fill="none"
							stroke={props.mauMuiTen}
							strokeWidth={2}
							opacity={0.4 * ringDraw}
						/>
					</g>
				</svg>
			</Interactive.Div>

			{/* LỚP TRƯỚC 4: mũi tên lực dòng chảy đè lên toàn màn hình */}
			<Interactive.Div
				name="Mũi tên lực dòng chảy"
				from={242}
				durationInFrames={74}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<svg
					width={1920}
					height={1080}
					viewBox="0 0 1920 1080"
					style={{position: 'absolute', left: 0, top: 0}}
				>
					{ARROW_YS.map((y, i) => {
						const l = la - i * 4;
						const draw = interpolate(l, [0, 16], [0, 1], {
							...kep,
							easing: Easing.out(Easing.cubic),
						});
						const headScale = interpolate(l, [10, 22], [0, 1], {
							...kep,
							easing: Easing.out(Easing.back(1.6)),
						});
						const dash = 900;
						return (
							<g
								key={i}
								transform={`translate(${arrowPush} 0)`}
								style={{opacity: interpolate(l, [0, 4], [0, 1], kep)}}
							>
								<line
									x1={70}
									y1={y}
									x2={970}
									y2={y}
									stroke={props.mauMuiTen}
									strokeWidth={props.dayMuiTen}
									strokeLinecap="round"
									strokeDasharray={dash}
									strokeDashoffset={(1 - draw) * dash}
								/>
								<polygon
									points={`970,${y - 34} 970,${y + 34} 1030,${y}`}
									fill={props.mauMuiTen}
									transform={`translate(970 ${y}) scale(${headScale}) translate(-970 ${-y})`}
								/>
							</g>
						);
					})}
				</svg>
			</Interactive.Div>
		</AbsoluteFill>
	);
};

export default Canh;
