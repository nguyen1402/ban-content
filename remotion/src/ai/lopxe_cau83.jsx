import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

// Đường lộ trình đỏ vẽ dọc theo dòng sông San Pedro trên bản đồ cổ
const DUONG_SONG =
	'M 1300 350 C 1258 460 1178 512 1148 606 C 1118 700 1152 776 1102 858 C 1062 926 1012 948 958 992';

const HAI_LY_BOI = [
	{left: 60, top: 848, w: 660, tre: 0, huong: 1},
	{left: 1130, top: 772, w: 720, tre: 8, huong: -1},
	{left: 560, top: 918, w: 600, tre: 16, huong: 1},
];

const HAI_LY_BAY = [
	{left: 120, top: 596, w: 620, tre: 0, huong: -1},
	{left: 1180, top: 536, w: 680, tre: 6, huong: 1},
	{left: 760, top: 392, w: 540, tre: 12, huong: -1},
];

export const schema = z.object({
	anhBanDo: z.string().describe('Ảnh nền bản đồ cổ nước Mỹ thập niên 1820'),
	anhThamHiem: z.string().describe('Ảnh tách nền bóng lưng nhà thám hiểm thế kỷ 19'),
	anhSong: z.string().describe('Ảnh sông San Pedro hoang sơ thời xưa'),
	anhHaiLyCanCanh: z.string().describe('Ảnh cận cảnh hải ly đang gặm gỗ'),
	anhHaiLyBoi: z.string().describe('Ảnh tách nền hải ly đang bơi'),
	anhHaiLyBay: z.string().describe('Ảnh tách nền hải ly đang đắp đập'),
	nam: z.number().describe('Năm in lớn trên bản đồ'),
	tenNhaThamHiem: z.string().describe('Tên nhà thám hiểm'),
	mauDuong: z.string().describe('Màu đường lộ trình trên bản đồ'),
	mauChu: z.string().describe('Màu chữ năm trên bản đồ'),
	coNam: z.number().describe('Cỡ chữ năm'),
	coTen: z.number().describe('Cỡ chữ tên nhà thám hiểm'),
	doDayNet: z.number().describe('Độ dày nét đường lộ trình'),
});

export const Canh = (props) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	// ===== PHA BẢN ĐỒ =====
	const whip = interpolate(frame, [183, 191], [0, -1700], {
		...kep,
		easing: Easing.in(Easing.cubic),
	});
	const zoom = interpolate(frame, [134, 184], [1, 1.2], kep);
	const camX = interpolate(frame, [134, 184], [0, -70], kep);
	const camY = interpolate(frame, [134, 184], [0, -160], kep);
	const ve = interpolate(frame, [134, 180], [0, 1], kep);
	const luot = interpolate(frame, [4, 44], [-700, 2200], kep);

	const namScale = spring({
		frame: Math.max(0, frame - 4),
		fps,
		config: {damping: 13, mass: 0.6, stiffness: 90},
	});
	const namOp = interpolate(frame, [4, 14], [0, 1], kep);

	const thamOp = interpolate(frame, [56, 74], [0, 1], kep);
	const thamX = interpolate(frame, [56, 74], [-90, 0], {...kep, easing: Easing.out(Easing.cubic)});
	const tenOp = interpolate(frame, [56, 70], [0, 1], kep);
	const tenY = interpolate(frame, [56, 74], [34, 0], {...kep, easing: Easing.out(Easing.cubic)});

	// ===== CHUYỂN CẢNH =====
	const flash = interpolate(frame, [183, 187, 193], [0, 0.62, 0], kep);
	const slideIn = interpolate(frame, [184, 196], [1250, 0], {
		...kep,
		easing: Easing.out(Easing.cubic),
	});

	return (
		<AbsoluteFill style={{backgroundColor: '#1a1208'}}>
			{/* ---------- BẢN ĐỒ CỔ 1820 ---------- */}
			<Interactive.Div
				name="Bản đồ cổ nước Mỹ 1820"
				from={0}
				durationInFrames={192}
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: 1920,
					height: 1080,
					transform: `translateX(${whip}px)`,
				}}
			>
				<div
					style={{
						position: 'absolute',
						left: 0,
						top: 0,
						width: 1920,
						height: 1080,
						transform: `scale(${zoom}) translate(${camX}px, ${camY}px)`,
						transformOrigin: '50% 50%',
					}}
				>
					<AnhNen anh={props.anhBanDo} tu={1.04} den={1.12} goc="50% 50%" toi={0.05} />

					{/* Đường lộ trình đỏ nét đứt */}
					<Interactive.Div
						name="Đường lộ trình sông San Pedro"
						from={134}
						durationInFrames={58}
						style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
					>
						<svg
							width={1920}
							height={1080}
							viewBox="0 0 1920 1080"
							style={{position: 'absolute', left: 0, top: 0}}
						>
							<defs>
								<mask id="loTrinhMask" maskUnits="userSpaceOnUse" x={0} y={0} width={1920} height={1080}>
									<path
										d={DUONG_SONG}
										fill="none"
										stroke="#ffffff"
										strokeWidth={18}
										strokeLinecap="round"
										pathLength={1000}
										strokeDasharray="1000"
										strokeDashoffset={1000 - 1000 * ve}
									/>
								</mask>
							</defs>
							<path
								d={DUONG_SONG}
								fill="none"
								stroke={props.mauDuong}
								strokeWidth={props.doDayNet}
								strokeDasharray="26 18"
								strokeLinecap="round"
								mask="url(#loTrinhMask)"
							/>
						</svg>
					</Interactive.Div>

					{/* Năm 1825 */}
					<Interactive.Div
						name="Năm 1825"
						from={4}
						durationInFrames={186}
						style={{position: 'absolute', left: 0, top: 110, width: 1920, textAlign: 'center'}}
					>
						<div
							style={{
								fontFamily: FONT,
								fontSize: props.coNam,
								fontWeight: 900,
								color: props.mauChu,
								letterSpacing: 8,
								lineHeight: 1,
								opacity: namOp,
								transform: `scale(${namScale})`,
								textShadow: '0 8px 0 rgba(255,255,255,0.30)',
							}}
						>
							{props.nam}
						</div>
					</Interactive.Div>

					{/* Bóng lưng nhà thám hiểm */}
					<Interactive.Div
						name="Bóng lưng nhà thám hiểm"
						from={56}
						durationInFrames={134}
						style={{position: 'absolute', left: 90, top: 250, width: 470, height: 700}}
					>
						<Img
							src={src(props.anhThamHiem)}
							style={{
								width: '100%',
								height: '100%',
								objectFit: 'contain',
								opacity: thamOp,
								transform: `translateX(${thamX}px)`,
								filter: 'drop-shadow(0 18px 28px rgba(58,36,16,0.38))',
							}}
						/>
					</Interactive.Div>

					{/* Thẻ tên James Ohio Pattie */}
					<Interactive.Div
						name="Thẻ tên James Ohio Pattie"
						from={56}
						durationInFrames={134}
						style={{position: 'absolute', left: 620, top: 430, width: 680, textAlign: 'center'}}
					>
						<div
							style={{
								display: 'inline-block',
								padding: '18px 44px',
								background: 'rgba(38,23,10,0.82)',
								border: '3px solid rgba(214,178,110,0.9)',
								borderRadius: 14,
								fontFamily: FONT,
								fontSize: props.coTen,
								fontWeight: 700,
								color: '#f6e6c4',
								letterSpacing: 2,
								whiteSpace: 'nowrap',
								opacity: tenOp,
								transform: `translateY(${tenY}px)`,
							}}
						>
							{props.tenNhaThamHiem}
						</div>
					</Interactive.Div>
				</div>

				{/* Lướt sáng nhẹ trên bản đồ */}
				<Interactive.Div
					name="Lướt sáng bản đồ"
					from={4}
					durationInFrames={44}
					style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, overflow: 'hidden'}}
				>
					<div
						style={{
							position: 'absolute',
							left: luot,
							top: -260,
							width: 380,
							height: 1600,
							transform: 'rotate(14deg)',
							background:
								'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.55) 50%, rgba(255,255,255,0) 100%)',
						}}
					/>
				</Interactive.Div>
			</Interactive.Div>

			{/* ---------- WHIP-PAN: VỆT SÁNG ---------- */}
			<Interactive.Div
				name="Vệt sáng chuyển cảnh"
				from={183}
				durationInFrames={12}
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: 1920,
					height: 1080,
					opacity: flash,
					background:
						'linear-gradient(100deg, rgba(255,255,255,0) 18%, rgba(255,255,255,0.92) 50%, rgba(255,255,255,0) 82%)',
				}}
			/>

			{/* ---------- SÔNG SAN PEDRO THỰC TẾ ---------- */}
			<Interactive.Div
				name="Sông San Pedro hoang sơ"
				from={184}
				durationInFrames={26}
				style={{
					position: 'absolute',
					left: 0,
					top: 0,
					width: 1920,
					height: 1080,
					transform: `translateX(${slideIn}px)`,
				}}
			>
				<AnhNen anh={props.anhSong} tu={1.14} den={1.02} goc="50% 45%" toi={0.04} />
			</Interactive.Div>

			{/* ---------- PUNCH-IN: CẬN CẢNH HẢI LY ---------- */}
			<Interactive.Div
				name="Cận cảnh hải ly gặm gỗ"
				from={205}
				durationInFrames={115}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={props.anhHaiLyCanCanh} tu={1.24} den={1.06} goc="50% 50%" toi={0.04} />
			</Interactive.Div>

			{/* ---------- HẢI LY BƠI LỘI ---------- */}
			<Interactive.Div
				name="Đàn hải ly bơi lội"
				from={205}
				durationInFrames={115}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				{HAI_LY_BOI.map((h, i) => {
					const lf = Math.max(0, frame - 205 - h.tre);
					const sp = spring({frame: lf, fps, config: {damping: 13, mass: 0.7, stiffness: 110}});
					const op = interpolate(lf, [0, 8], [0, 1], kep);
					const dx = interpolate(lf, [0, 115], [0, 70 * h.huong], kep);
					const dy = Math.sin((frame + i * 55) / 20) * 6;
					return (
						<Img
							key={`boi-${i}`}
							src={src(props.anhHaiLyBoi)}
							style={{
								position: 'absolute',
								left: h.left,
								top: h.top,
								width: h.w,
								opacity: op,
								transform: `translate(${dx}px, ${dy}px) scale(${0.86 + 0.14 * sp})`,
								transformOrigin: '50% 50%',
								filter: 'drop-shadow(0 10px 18px rgba(0,40,30,0.35))',
							}}
						/>
					);
				})}
			</Interactive.Div>

			{/* ---------- HẢI LY ĐÔNG ĐÚC KHẮP DÒNG SÔNG ---------- */}
			<Interactive.Div
				name="Hải ly đông đúc khắp sông"
				from={228}
				durationInFrames={92}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				{HAI_LY_BAY.map((h, i) => {
					const lf = Math.max(0, frame - 228 - h.tre);
					const sp = spring({frame: lf, fps, config: {damping: 12, mass: 0.6, stiffness: 120}});
					const op = interpolate(lf, [0, 8], [0, 1], kep);
					const dx = interpolate(lf, [0, 92], [0, 55 * h.huong], kep);
					const dy = Math.sin((frame + i * 47) / 24) * 5;
					return (
						<Img
							key={`bay-${i}`}
							src={src(props.anhHaiLyBay)}
							style={{
								position: 'absolute',
								left: h.left,
								top: h.top,
								width: h.w,
								opacity: op,
								transform: `translate(${dx}px, ${dy}px) scale(${0.8 + 0.2 * sp})`,
								transformOrigin: '50% 50%',
								filter: 'drop-shadow(0 12px 20px rgba(0,40,30,0.35))',
							}}
						/>
					);
				})}
			</Interactive.Div>
		</AbsoluteFill>
	);
};
