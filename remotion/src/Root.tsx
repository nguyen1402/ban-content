import React from 'react';
import {Composition} from 'remotion';
import {BanDo} from './BanDo.jsx';
import {BanDoNen} from './BanDoNen.jsx';
import {BieuDo} from './BieuDo.jsx';
import {BangGiay} from './BangGiay.jsx';
import {NhanVat} from './NhanVat.jsx';
import {MinhHoa} from './MinhHoa.jsx';
import {CanhMoTa} from './CanhMoTa.jsx';
import {NhanY} from './NhanY.jsx';
import {NuocDang, nuocDangSchema, NUOC_DANG_MAC_DINH} from './Canh3D.jsx';
import {Folder} from 'remotion';
import {GiaiPhau, giaiPhauSchema, GIAI_PHAU_MAC_DINH} from './GiaiPhau.jsx';
// NHAN_Y_AI_IMPORT_BAT_DAU
import {coGiong} from './ai/thu_vien.jsx';
import {Canh as AiCalocCau106, schema as AiCalocCau106Schema} from './ai/caloc_cau106.jsx';
const AiCalocCau106G = coGiong(AiCalocCau106, "nhan_y/giong_caloc_cau106.wav");
import {Canh as AiCalocCau20, schema as AiCalocCau20Schema} from './ai/caloc_cau20.jsx';
const AiCalocCau20G = coGiong(AiCalocCau20, "nhan_y/giong_caloc_cau20.wav");
import {Canh as AiCalocCau33, schema as AiCalocCau33Schema} from './ai/caloc_cau33.jsx';
const AiCalocCau33G = coGiong(AiCalocCau33, "nhan_y/giong_caloc_cau33.wav");
import {Canh as AiCalocCau53, schema as AiCalocCau53Schema} from './ai/caloc_cau53.jsx';
const AiCalocCau53G = coGiong(AiCalocCau53, "nhan_y/giong_caloc_cau53.wav");
import {Canh as AiCalocCau57, schema as AiCalocCau57Schema} from './ai/caloc_cau57.jsx';
const AiCalocCau57G = coGiong(AiCalocCau57, "nhan_y/giong_caloc_cau57.wav");
import {Canh as AiCalocCau64, schema as AiCalocCau64Schema} from './ai/caloc_cau64.jsx';
const AiCalocCau64G = coGiong(AiCalocCau64, "nhan_y/giong_caloc_cau64.wav");
import {Canh as AiCalocCau73, schema as AiCalocCau73Schema} from './ai/caloc_cau73.jsx';
const AiCalocCau73G = coGiong(AiCalocCau73, "nhan_y/giong_caloc_cau73.wav");
import {Canh as AiCalocCau87, schema as AiCalocCau87Schema} from './ai/caloc_cau87.jsx';
const AiCalocCau87G = coGiong(AiCalocCau87, "nhan_y/giong_caloc_cau87.wav");
import {Canh as AiCalocCau99, schema as AiCalocCau99Schema} from './ai/caloc_cau99.jsx';
const AiCalocCau99G = coGiong(AiCalocCau99, "nhan_y/giong_caloc_cau99.wav");
// NHAN_Y_AI_IMPORT_KET_THUC

const FPS = 30;
// Thời lượng lấy từ props.giay (Python truyền theo độ dài giọng đọc của cảnh).
const meta = async ({props}: {props: any}) => ({
  durationInFrames: Math.max(30, Math.round((props.giay || 5) * FPS)),
});

export const Root = () => (
  <>
    <Composition id="BanDo" component={BanDo} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5}} calculateMetadata={meta} />
    <Composition id="BanDoNen" component={BanDoNen} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, lop: [{z: 10, ox: 0, oy: 0, w: 256, h: 256, src: ''}]}} calculateMetadata={meta} />
    <Composition id="BangGiay" component={BangGiay} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, nhip: []}} calculateMetadata={meta} />
    <Composition id="BieuDo" component={BieuDo} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5}} calculateMetadata={meta} />
    <Composition id="MinhHoa" component={MinhHoa} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, kieu: 'quy_trinh', muc: []}} calculateMetadata={meta} />
    <Composition id="CanhMoTa" component={CanhMoTa} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, nen: '#0b0d12', lop: []}} calculateMetadata={meta} />
    <Composition id="NhanVat" component={NhanVat} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, anh: '', nen: '', kieu: 'giua'}} calculateMetadata={meta} />
    <Composition id="NhanY" component={NhanY} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, nen: '', anh: '', nhip: []}} calculateMetadata={meta} />
    <Composition id="NuocDang" component={NuocDang} width={1920} height={1080} fps={FPS}
      durationInFrames={240} schema={nuocDangSchema} defaultProps={NUOC_DANG_MAC_DINH} calculateMetadata={meta} />
    <Composition id="GiaiPhau" component={GiaiPhau} width={1920} height={1080} fps={FPS}
      durationInFrames={300} schema={giaiPhauSchema} defaultProps={GIAI_PHAU_MAC_DINH} calculateMetadata={meta} />
    <Folder name="sua-tay">
      {/* NHAN_Y_SUA_BAT_DAU — khối này do chinh_sua/nhan_y.py sinh ra: mỗi chỗ nhấn ý dựng bằng cảnh mẫu 3D là một mục.
          Sửa thông số ở bảng bên phải Studio rồi bấm lưu (Studio ghi vào đây); chạy lại nhan_y.py thì dựng đúng chỗ đã sửa. */}
      <Composition id="ai-caloc-cau106" component={AiCalocCau106G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau106Schema} calculateMetadata={meta}
        defaultProps={{"bgImage": "nhan_y/c971e66784d097.jpg", "salmonImage": "nhan_y/fd9acf07152889.png", "eelImage": "nhan_y/3d2e9d40089aa0.png", "larvaeImage": "nhan_y/268ba2971bedaf.png", "title1": "Bơi lội ở tầng nước giữa", "title2": "Đào bới sâu vào bùn cát", "giay": 10.47}} />
      <Composition id="ai-caloc-cau20" component={AiCalocCau20G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau20Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_dia_hinh": "nhan_y/765df697ab6b6e.jpg", "anh_toa_nha": "nhan_y/de0cd8f6f058b1.png", "nhan_do_cao": "~99 m", "nhan_tang_nha": "30 tầng", "nhan_ho_erie": "HỒ ERIE", "nhan_ho_ontario": "HỒ ONTARIO", "mau_thuoc_do": "#00f0ff", "giay": 8.29}} />
      <Composition id="ai-caloc-cau33" component={AiCalocCau33G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau33Schema} calculateMetadata={meta}
        defaultProps={{"bgImage": "nhan_y/5fc4953aed5817.jpg", "boatImage": "nhan_y/3c7adf348cdc8a.png", "gateImage": "nhan_y/f278721193a171.png", "text1": "1. Khóa cổng", "text2": "2. Cân bằng mực nước", "text1From": 116, "text2From": 263, "waterRiseFrom": 174, "waterRiseTo": 263, "boatEnterFrom": 77, "boatEnterTo": 101, "lowWaterLevel": 680, "highWaterLevel": 440, "giay": 10.85}} />
      <Composition id="ai-caloc-cau53" component={AiCalocCau53G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau53Schema} calculateMetadata={meta}
        defaultProps={{"nenNguDaiHo": "nhan_y/2ae05ac64e2f9c.jpg", "tachCaHoi": "nhan_y/cd2e783a4e3d55.png", "canMiengBamThit": "nhan_y/0bc3cf831df4fd.jpg", "nhanChatChongDong": "CHẤT CHỐNG ĐÔNG MÁU", "nhanThoiGian": "1 - 1,5 NĂM", "kichThuocNhan": 58, "mauLamellipodin": "rgba(200, 100, 255, 0.85)", "mauMauTuoi": "#e01616", "giay": 10.91}} />
      <Composition id="ai-caloc-cau57" component={AiCalocCau57G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau57Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/3f0493e82d2ae2.jpg", "anh_au_trung": "nhan_y/653af02f9937df.png", "tieu_de_an_minh": "Ẩn mình • Mù lòa", "tieu_de_thoi_gian": "3 – 10+", "don_vi_thoi_gian": "NĂM", "giay": 7.27}} />
      <Composition id="ai-caloc-cau64" component={AiCalocCau64G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau64Schema} calculateMetadata={meta}
        defaultProps={{"mapBgPath": "nhan_y/1229a8e2d2d1b8.jpg", "redArrowPath": "nhan_y/afd8fed24df4d0.png", "tieudeBeat1": "1937: Hồ Huron", "tieudeBeat2": "1938: Hồ Superior", "tieudeBeat3": "Hoàn tất xâm chiếm Ngũ Hồ", "mauDoMuc": "#9a1818", "mauGiayDa": "#f5ebd5", "mauChuDam": "#24180e", "giay": 10.23}} />
      <Composition id="ai-caloc-cau73" component={AiCalocCau73G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau73Schema} calculateMetadata={meta}
        defaultProps={{"bgNen": "nhan_y/e97c2ea126ad38.jpg", "bgCanThung": "nhan_y/e29c7cdd7efeb8.jpg", "imgXeTai": "nhan_y/bfccd7fb86b0d3.png", "text1": "340 xe (gần 7.000 tấn)", "text2": "7 xe (135 tấn - 2%)", "text1Color": "#facc15", "text2Color": "#ef4444", "textSize": 90, "xeWidth": 140, "xeHeight": 67, "giay": 10.45}} />
      <Composition id="ai-caloc-cau87" component={AiCalocCau87G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau87Schema} calculateMetadata={meta}
        defaultProps={{"nenSuoi": "nhan_y/3cecf0562930bc.jpg", "anhDapTran": "nhan_y/75ec4266c02b36.png", "anhCaMutDa": "nhan_y/595f958eb600fc.png", "anhCaBanDia": "nhan_y/8f3a37d386c022.png", "tieuDePhacThao": "THIẾT KẾ ĐẬP TRÀN BẢO VỆ", "nhanDoCao": "Chênh lệch độ cao vừa phải", "nhanChanCaMutDa": "BỊ CHẶN LẠI & TRÔI XUỐNG", "nhanCaBanDiaNhay": "CÁ BẢN ĐỊA NHẢY QUA DỄ DÀNG", "nhanCuaDan": "CỬA DẪN RIÊNG BIỆT (FISHWAY)", "giay": 13.21}} />
      <Composition id="ai-caloc-cau99" component={AiCalocCau99G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau99Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_song": "nhan_y/c2b5ed2c53e063.jpg", "anh_au_trung": "nhan_y/ca785beaee76c2.png", "anh_ca_hoi_van": "nhan_y/5d8346e097582c.png", "anh_ca_tue": "nhan_y/ad060c4317b359.png", "tieu_de_ca_hoi": "50% Cá hồi vân", "tieu_de_ca_tue": "40% Cá tuế đầu to", "mau_hoa_chat": "#f59e0b", "mau_nguy_hiem": "#ef4444", "giay": 8.43}} />
      {/* NHAN_Y_SUA_KET_THUC */}
    </Folder>
  </>
);
