import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, random, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {kep, FONT, AnhNen, AnhLia, SoDem, Nhan, VongBut, MuiTen} from './thu_vien.jsx';

export const schema = z.object({
	anh_bai_lop: z.string().describe('Ảnh tư liệu bãi lốp xe đang cháy (nhịp 1)'),
	anh_khoi: z.string().describe('Ảnh nền khói cho bản đồ 3 tiểu bang (nhịp 2)'),
	anh_long_dat: z.string().describe('Ảnh nền cho mặt cắt địa tầng (nhịp 3)'),
	so_lop: z.number().describe('Con số lốp xe hiện trên counter'),
	counter_co: z.number().describe('Cỡ chữ của counter'),
	counter_giay: z.number().describe('Thời gian counter chạy (giây)'),
	mau_chu: z.string().describe('Màu chữ counter'),
	co_nhan_bang: z.number().describe('Cỡ chữ tên 3 tiểu bang'),
	mau_bien_gioi: z.string().describe('Màu đường ranh giới tiểu bang'),
	mau_tang_nuoc: z.string().describe('Màu tầng ngậm nước ngầm'),
	mau_dau: z.string().describe('Màu dầu cao su nóng chảy'),
});

const PLUME_A =
	'M 0 0 C 70 -40 160 -20 190 40 C 250 70 260 160 190 210 C 210 290 110 330 40 290 C -30 340 -120 310 -140 240 C -210 210 -210 120 -150 80 C -170 20 -90 -30 0 0 Z';
const PLUME_B =
	'M 0 0 C 55 -30 120 -10 145 35 C 195 55 200 125 145 160 C 160 225 85 255 30 225 C -25 265 -95 240 -110 185 C -165 165 -165 95 -115 65 C -130 15 -70 -25 0 0 Z';

export const Canh = (props: z.infer<typeof schema>) => {
	const f = useCurrentFrame();

	/* ---------------- NHỊP 1 : 0 - 4.5s ---------------- */
	const counterIn = interpolate(f, [12, 30], [0, 1], kep);
	const counterY = interpolate(f, [12, 34], [46, 0], {...kep, easing: Easing.out(Easing.cubic)});
	const smokeH = interpolate(f, [80, 142], [0, 660], {...kep, easing: Easing.inOut(Easing.quad)});
	const smokeO = interpolate(f, [80, 118], [0, 0.88], kep);

	/* ---------------- NHỊP 2 : 4.5 - 7.3s ---------------- */
	const mapO = interpolate(f, [143, 162], [0, 1], kep);
	const plumeK = interpolate(f, [143, 217], [0.3, 1.9], {...kep, easing: Easing.out(Easing.quad)});
	const plumeO = interpolate(f, [143, 164], [0, 0.9], kep);
	const plume2K = interpolate(f, [152, 217], [0.2, 1.35], {...kep, easing: Easing.out(Easing.quad)});

	/* ---------------- NHỊP 3 : 7.3 - 11.3s ---------------- */
	const csY = interpolate(f, [218, 258], [330, 0], {...kep, easing: Easing.out(Easing.cubic)});
	const csO = interpolate(f, [218, 234], [0, 1], kep);
	const oilP = interpolate(f, [234, 302], [0, 1], {...kep, easing: Easing.inOut(Easing.quad)});
	const spread = interpolate(f, [280, 334], [0, 450], {...kep, easing: Easing.out(Easing.cubic)});
	const waterDim = interpolate(f, [280, 334], [0, 0.45], kep);

	return (
		<AbsoluteFill style={{backgroundColor: '#141210'}}>
			{/* ================= NHỊP 1 ================= */}
			<Interactive.Div
				name="Ảnh bãi lốp xe cháy"
				from={0}
				durationInFrames={143}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhLia anh={props.anh_bai_lop} huong="phai" quang={130} phong={1.06} toi={0.22} />
			</Interactive.Div>

			<Interactive.Div
				name="Khói đen phủ góc trên"
				from={80}
				durationInFrames={63}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<div
					style={{
						position: 'absolute',
						left: 0,
						top: 0,
						width: 1920,
						height: smokeH,
						opacity: smokeO,
						background:
							'linear-gradient(to bottom, rgba(20,18,17,0.94) 0%, rgba(26,24,22,0.7) 48%, rgba(26,24,22,0) 100%)',
					}}
				/>
			</Interactive.Div>

			<Interactive.Div
				name="Counter 7.000.000"
				from={10}
				durationInFrames={133}
				style={{position: 'absolute', left: 120, top: 790}}
			>
				<div
					style={{
						opacity: counterIn,
						transform: `translateY(${counterY}px)`,
						fontFamily: FONT,
						fontWeight: 800,
						fontSize: props.counter_co,
						letterSpacing: '-3px',
						color: props.mau_chu,
						textShadow: '0 10px 34px rgba(0,0,0,0.6)',
						whiteSpace: 'nowrap',
					}}
				>
					<SoDem so={props.so_lop} don_vi="" giay={props.counter_giay} co={props.counter_co} />
				</div>
			</Interactive.Div>

			{/* ================= NHỊP 2 ================= */}
			<Interactive.Div
				name="Ảnh nền khói bản đồ"
				from={143}
				durationInFrames={75}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={props.anh_khoi} tu={1.14} den={1} goc="50% 50%" toi={0.34} />
			</Interactive.Div>

			<Interactive.Div
				name="Bản đồ 3 tiểu bang"
				from={143}
				durationInFrames={75}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{opacity: mapO}}>
					<defs>
						<radialGradient id="khoiMap" cx="50%" cy="50%" r="50%">
							<stop offset="0%" stopColor="#33302d" stopOpacity="0.95" />
							<stop offset="55%" stopColor="#3b3835" stopOpacity="0.62" />
							<stop offset="100%" stopColor="#3b3835" stopOpacity="0" />
						</radialGradient>
						<filter id="memKhoi">
							<feGaussianBlur stdDeviation="24" />
						</filter>
					</defs>

					{/* vệt khói loang rộng */}
					<g transform={`translate(830 620) scale(${plume2K})`} opacity={plumeO * 0.8}>
						<path d={PLUME_B} fill="url(#khoiMap)" filter="url(#memKhoi)" transform="translate(-140 -90)" />
					</g>
					<g transform={`translate(830 620) scale(${plumeK})`} opacity={plumeO}>
						<path d={PLUME_A} fill="url(#khoiMap)" filter="url(#memKhoi)" />
					</g>

					{/* ranh giới 3 tiểu bang */}
					<g
						fill="rgba(255,255,255,0.05)"
						stroke={props.mau_bien_gioi}
						strokeWidth={3}
						strokeLinejoin="round"
					>
						<polygon points="420,380 620,330 700,420 660,520 560,600 430,560 380,470" />
						<polygon points="860,430 1180,400 1260,450 1150,482 980,472 900,460" />
						<polygon points="700,520 900,470 1120,500 1250,560 1300,700 1150,800 900,820 760,720 700,620" />
					</g>
				</svg>
			</Interactive.Div>

			<Interactive.Div
				name="Vòng đánh dấu điểm cháy"
				from={150}
				durationInFrames={68}
				style={{position: 'absolute', left: 830, top: 620}}
			>
				<VongBut w={280} h={200} />
			</Interactive.Div>

			<Interactive.Div
				name="Nhãn West Virginia"
				from={162}
				durationInFrames={56}
				style={{position: 'absolute', left: 560, top: 470}}
			>
				<Nhan chu="West Virginia" dx={-150} dy={-120} co={props.co_nhan_bang} />
			</Interactive.Div>

			<Interactive.Div
				name="Nhãn Maryland"
				from={172}
				durationInFrames={46}
				style={{position: 'absolute', left: 1080, top: 440}}
			>
				<Nhan chu="Maryland" dx={160} dy={-120} co={props.co_nhan_bang} />
			</Interactive.Div>

			<Interactive.Div
				name="Nhãn Virginia"
				from={182}
				durationInFrames={36}
				style={{position: 'absolute', left: 1010, top: 700}}
			>
				<Nhan chu="Virginia" dx={140} dy={130} co={props.co_nhan_bang} />
			</Interactive.Div>

			{/* ================= NHỊP 3 ================= */}
			<Interactive.Div
				name="Ảnh nền mặt cắt địa tầng"
				from={218}
				durationInFrames={122}
				style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}}
			>
				<AnhNen anh={props.anh_long_dat} tu={1.02} den={1.13} goc="50% 25%" toi={0.3} />
			</Interactive.Div>

			<Interactive.Div
				name="Mặt cắt địa tầng"
				from={218}
				durationInFrames={122}
				style={{position: 'absolute', left: 0, top: 500}}
			>
				<div style={{transform: `translateY(${csY}px)`, opacity: csO}}>
					<svg width={1920} height={580} viewBox="0 0 1920 580">
						<defs>
							<radialGradient id="dauLoang" cx="50%" cy="50%" r="50%">
								<stop offset="0%" stopColor="#0a0908" stopOpacity="0.96" />
								<stop offset="60%" stopColor="#0d0b0a" stopOpacity="0.78" />
								<stop offset="100%" stopColor="#0d0b0a" stopOpacity="0" />
							</radialGradient>
							<clipPath id="catTangNuoc">
								<rect x="0" y="380" width="1920" height="120" />
							</clipPath>
						</defs>

						{/* các tầng địa chất */}
						<rect x="0" y="0" width="1920" height="72" fill="#332a22" />
						<rect x="0" y="72" width="1920" height="158" fill="#4c4239" />
						<rect x="0" y="230" width="1920" height="150" fill="#39352f" />
						<rect x="0" y="380" width="1920" height="120" fill={props.mau_tang_nuoc} />
						<rect x="0" y="500" width="1920" height="80" fill="#161413" />

						{/* sỏi đá trong tầng cuội */}
						{Array.from({length: 18}).map((_, i) => (
							<circle
								key={`peb-${i}`}
								cx={60 + i * 104 + random(`pebx${i}`) * 58}
								cy={100 + random(`peby${i}`) * 118}
								r={4 + random(`pebr${i}`) * 6}
								fill="rgba(255,255,255,0.10)"
							/>
						))}

						{/* đường phân tầng */}
						<g stroke="rgba(255,255,255,0.14)" strokeWidth={2}>
							<line x1="0" y1="72" x2="1920" y2="72" />
							<line x1="0" y1="230" x2="1920" y2="230" />
							<line x1="0" y1="380" x2="1920" y2="380" />
							<line x1="0" y1="500" x2="1920" y2="500" />
						</g>
						<rect x="0" y="380" width="1920" height="7" fill="rgba(190,235,255,0.45)" />

						{/* nước ngầm bị vẩn đục */}
						<g clipPath="url(#catTangNuoc)">
							<ellipse
								cx={950}
								cy={442}
								rx={Math.max(spread, 0.5)}
								ry={66}
								fill="url(#dauLoang)"
							/>
							<rect x="0" y="380" width={1920} height={120} fill="#050505" opacity={waterDim * 0.35} />
						</g>

						{/* dầu cao su rỉ xuống */}
						<path
							d="M 940 -20 C 975 70, 900 130, 935 200 C 965 265, 915 320, 950 400"
							fill="none"
							stroke={props.mau_dau}
							strokeWidth={34}
							strokeLinecap="round"
							strokeDasharray={470}
							strokeDashoffset={470 * (1 - oilP)}
						/>
					</svg>
				</div>
			</Interactive.Div>

			<Interactive.Div
				name="Mũi tên dầu ngấm (trái)"
				from={248}
				durationInFrames={92}
				style={{position: 'absolute', left: 700, top: 620}}
			>
				<MuiTen dx={0} dy={230} cong={34} />
			</Interactive.Div>

			<Interactive.Div
				name="Mũi tên dầu ngấm (phải)"
				from={258}
				durationInFrames={82}
				style={{position: 'absolute', left: 1220, top: 620}}
			>
				<MuiTen dx={0} dy={230} cong={-34} />
			</Interactive.Div>
		</AbsoluteFill>
	);
};
