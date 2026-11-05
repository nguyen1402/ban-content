import React from 'react';
import {AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan} from './thu_vien.jsx';

export const schema = z.object({
	phongKyThuatPath: z.string().describe('Đường dẫn ảnh nền phòng kỹ thuật'),
	dongSongThuyVanPath: z.string().describe('Đường dẫn ảnh nền dòng sông thủy văn'),
	tu_Scale: z.number().describe('Tỷ lệ zoom ban đầu ảnh nền 1'),
	den_Scale: z.number().describe('Tỷ lệ zoom kết thúc ảnh nền 1'),
	tu_Scale_ThuyVan: z.number().describe('Tỷ lệ zoom ban đầu ảnh nền 2'),
	den_Scale_ThuyVan: z.number().describe('Tỷ lệ zoom kết thúc ảnh nền 2'),
	pan_X_Max: z.number().describe('Dịch chuyển X tối đa (parallax)'),
	punchInPercentage: z.number().describe('Tỷ lệ punch-in (%)'),
	punchInStartFrame: z.number().describe('Khung hình bắt đầu punch-in (toàn)'),
	lightSweepStartFrame: z.number().describe('Khung hình bắt đầu light sweep (toàn)'),
	sweepWidth: z.number().describe('Độ rộng dải sáng'),
	sweepColor: z.string().describe('Màu sắc dải sáng'),
	stiffness_Slide: z.number().describe('Độ cứng lò xo trượt'),
	damping_Slide: z.number().describe('Độ giảm chấn lò xo trượt'),
	stiffness_Punch: z.number().describe('Độ cứng lò xo punch-in'),
	damping_Punch: z.number().describe('Độ giảm chấn lò xo punch-in'),
});

export const Canh = (props) => {
	const frame = useCurrentFrame();
	const {width, height} = useVideoConfig();

	const localFrame_Lab = frame;
	const localFrame_River = Math.max(0, frame - 17);

	// Animation cho ảnh nền phòng kỹ thuật
	const scale_Lab = interpolate(localFrame_Lab, [0, 112], [props.tu_Scale, props.den_Scale]);
	const pan_X_Lab = interpolate(localFrame_Lab, [0, 112], [-props.pan_X_Max / 2, props.pan_X_Max / 2]);

	// Animation cho ảnh nền thủy văn
	// Trượt vào (slide-in)
	const slideInX = spring({
		frame: localFrame_River,
		fps: 30,
		config: {stiffness: props.stiffness_Slide, damping: props.damping_Slide},
		from: 1920,
		to: 0,
	});

	// Phấn nảy (punch-in) - scale thêm props.punchInPercentage/100
	const punchInSpring = spring({
		frame: frame - 76,
		fps: 30,
		config: {stiffness: props.stiffness_Punch, damping: props.damping_Punch},
		from: 0,
		to: props.punchInPercentage / 100,
	});

	// Zoom nền và pan (parallax) sau khi trượt vào
	const baseScale_ThuyVan = interpolate(localFrame_River, [20, 95], [props.tu_Scale_ThuyVan, props.den_Scale_ThuyVan], kep.clamp);
	const totalScale_ThuyVan = baseScale_ThuyVan * (1 + punchInSpring);
	const pan_X_ThuyVan = interpolate(localFrame_River, [20, 95], [props.pan_X_Max / 2, -props.pan_X_Max / 2], kep.clamp);

	// Ánh sáng lướt qua (light sweep)
	const sweepFrameLocal = Math.max(0, frame - 76);
	const sweepX = interpolate(sweepFrameLocal, [0, 20], [-props.sweepWidth, 1920 + props.sweepWidth], kep.clamp);
	const sweepOpacity = interpolate(sweepFrameLocal, [0, 10, 20], [0, 0.5, 0], kep.clamp);

	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			{/* Ảnh nền 1: Phòng kỹ thuật (ở dưới) */}
			<Interactive.Div name="Phòng kỹ thuật" from={0} durationInFrames={112}>
				<AnhNen anh={props.phongKyThuatPath} tu={props.tu_Scale} den={props.den_Scale} goc="50% 50%" />
			</Interactive.Div>

			{/* Ảnh nền 2: Dòng sông thủy văn (trượt lên và che dần) */}
			<Interactive.Div
				name="Dòng sông thủy văn"
				from={17}
				durationInFrames={95}
				style={{
					position: 'absolute',
					top: 0,
					left: slideInX,
					width: 1920,
					height: 1080,
					overflow: 'hidden',
				}}
			>
				{/* Bên trong Div này, ảnh thủy văn được pan và scale */}
				<AbsoluteFill style={{overflow: 'hidden'}}>
					<Img
						src={src(props.dongSongThuyVanPath)}
						style={{
							position: 'absolute',
							width: 1920,
							height: 1080,
							top: 0,
							left: pan_X_ThuyVan,
							transform: `scale(${totalScale_ThuyVan})`,
							transformOrigin: '50% 50%',
							objectFit: 'cover',
						}}
					/>
				</AbsoluteFill>

				{/* Ánh sáng lướt qua (light sweep) */}
				<Interactive.Div
					name="LightSweep"
					from={0}
					durationInFrames={20}
					style={{
						position: 'absolute',
						top: 0,
						left: sweepX,
						width: props.sweepWidth,
						height: 1080,
						opacity: sweepOpacity,
						background: `linear-gradient(90deg, transparent, ${props.sweepColor}, transparent)`,
						transform: 'skewX(-20deg)',
					}}
				/>
			</Interactive.Div>
		</AbsoluteFill>
	);
};
