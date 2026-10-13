---
name: chinh-sua-video-tho
description: Chỉnh sửa dự án video THÔ (đã ghép hình khớp lời + giọng đọc) thành bản hoàn chỉnh trong CapCut — chuyển cảnh, chuyển động cho ảnh, BẢN ĐỒ VỆ TINH Remotion (khoanh vùng + đường đi A→B), KHUNG HIGHLIGHT viền vàng, PHỦ MÀU đổi chương, LỚP ẢNH PHỦ minh hoạ (thẻ ảnh bật lên trên video nền khi cần), rồi dựng dự án CapCut mới. KHÔNG tự thêm nhạc và chữ (user bỏ 12/10). Dùng khi người dùng muốn "edit/hoàn thiện/thêm hiệu ứng, chuyển cảnh, bản đồ, ảnh minh hoạ" cho dự án thô của repo bán-content, hoặc gõ /chinh-sua-video-tho.
---

# Chỉnh sửa dự án thô -> dự án CapCut hoàn chỉnh

Repo: `D:\CapCutTTS\bán-content` (mã ở `chinh_sua/`). Mọi lệnh chạy từ `chinh_sua/` với `python -X utf8`.

## Đầu vào (tự nhận một trong hai kiểu)
- **Kiểu mới** (trình dựng tay `/dung?du_an=` hoặc nút 🤖 Tự tìm + tải + khớp): `ra/<dự án>/tu_khoa.json` (cảnh, giờ,
  mô tả khung hình, loại cảnh, địa danh) + `dung.json` (đoạn hình từng cảnh) + kho (`ra/<dự án>/kho/`) + `giong_doc.wav`.
  Đọc bằng `du_an_moi.py`; đoạn video trỏ VIDEO GỐC (chọn lại đoạn trong CapCut được), tiếng gốc tắt; khoảng hở nhỏ
  (đoạn trước chạm cuối file) được lấp bằng cách cho đoạn sau bắt đầu sớm hơn — không để màn đen.
- **Kiểu cũ** (quy trình tự ghép `chay_ghep_tu_dong.py`): `ra/<dự án>/ket_qua.json` + clip trong cache.

## Lệnh
`python dung_hoan_chinh.py --du-an <dự án> --ten "<tên bản nháp mới>"`

Hoặc bấm nút **✨ Hoàn thiện bản nháp** trong trình dựng (`/dung?du_an=`): máy chủ chạy đúng lệnh trên ở nền
(tên = tên bản nháp thô bỏ `_dung`/`_tu_dong` + `_hoan_chinh`), nút hiện bước đang làm, log ở `ra/<dự án>/hoan_thien.log`.

- **Bản đồ vệ tinh cho cảnh nhắc địa điểm** (kiểu mới): cảnh có `loai = dia_diem` + `dia_danh_en` (do `mo_ta_canh.py`
  hỏi ChatGPT) — đoạn ĐẦU của cảnh thay bằng clip Remotion `BanDoNen` chế độ vệ tinh: camera phóng từ cả lục địa vào,
  đường viền THẬT của địa danh (Nominatim/OSM; chỉ nhận vùng hành chính/địa danh thật, bỏ từ chỉ hướng "Northern…"
  khi cần, khung theo mảnh đất liền lớn nhất) chạy nét vàng + tô mờ, tên địa danh góc trên. Nền: Sentinel-2 cloudless
  **2016** của EOX (CC BY 4.0, dòng ghi nguồn nhỏ góc dưới phải; các năm 2017+ là NC nên không dùng). Cache ô ảnh
  `cache/tiles_vt/`, clip `cache/ban_do_vt/`. Tắt: `--khong-ban-do`.
- **ĐIỀU PHỐI CHUNG** (`dieu_phoi.py` + `minh_hoa.py`, 13/10 user — mặc định bật, tắt `--khong-dieu-phoi`): MỘT lần hỏi
  ChatGPT mỗi đoạn ~20 câu, mỗi câu tối đa MỘT lớp (chỗ có thẻ highlight thì không có Remotion và ngược lại):
  `the` (thẻ highlight), `khoanh_vung` (vệ tinh khoanh vùng/ghim), `duong_di` (mũi tên + ICON PHƯƠNG TIỆN chạy dọc
  đường: ✈ máy bay xoay theo hướng, 🚢 tàu thủy nét đứt xanh, 🚆 tàu hoả, 🚚 xe, 🚶 đi bộ; lục địa bị bỏ), `lan_rong`
  (một nơi toả nhiều tuyến), và sơ đồ Remotion `MinhHoa.jsx` trên nền CHÍNH đoạn video đang chiếu phủ lớp TỐI + mờ:
  `dien_canh` (13/10 user — thay icon emoji và kiểu ô tròn nối mũi tên): 1-4 vai là ẢNH THẬT ĐÃ TÁCH NỀN
  (`anh_tach.py`: Google "<q> isolated on white background", bỏ trang ảnh kho watermark, soát chữ trên ảnh đã tách,
  hai vai không cùng ảnh) diễn hành động theo lời: xuat_hien, bien_thanh, bay_toi, tan_cong, bao_vay, lan_ra, sinh_soi,
  bo_chay, an, mang_di, lon_len, bien_mat + nhãn giai đoạn dưới khung — bật cho toàn bộ video (13/10 user duyệt).
  (Kiểu cũ cau_tao/quy_trinh/vong_doi/mo_phong còn mã nhưng ChatGPT không được chọn nữa.) Mỗi lớp + từng bộ phận/bước/hành động bật theo cụm "moc" của giọng
  đọc. Icon = emoji hệ thống (Segoe UI Emoji). Câu trả lời lưu `ra/<dự án>/dieu_phoi_hoi.json`; clip cache
  `cache/minh_hoa/`, `cache/ban_do_vt/`. Không đè lên cảnh bản đồ vệ tinh có sẵn trên track hình. Giới hạn: tàu thủy đi
  đường cong thẳng (chưa tìm đường biển thật).
- **DIỄN CẢNH — cách làm hiện tại (13/10 user, đã duyệt trên 2 kịch bản):**
  - ChatGPT nghĩ như motion designer: viết `y_tuong` (nhịp nguyên nhân→kết quả, trước→sau, chi tiết cụ thể) rồi chọn
    1-4 vai + 2-6 nhịp; TRẠNG THÁI BIẾN THỂ của cùng một vật là vai riêng ("SAME as actor N but plump / riddled with
    holes"), đổi bằng `bien_thanh`. Động từ: xuat_hien, bien_thanh, bay_toi, tan_cong, gam, an, keo_di, thay_the,
    bao_vay, lan_ra, sinh_soi, bo_chay, mang_di, lon_len, thu_nho, bien_mat, tach_ra, ket_hop. `vi_tri` trai/giua/phai.
  - Độ phủ mục tiêu 60-70% lời đọc; câu bình luận/chuyển ý để footage thật. Cảnh nối sát nhau: cắt đuôi cảnh trước.
  - Ảnh vai: AI (Gemini web/Nano Banana qua cookie, `anh_ve.py`) vẽ CẢ BỘ VAI một ảnh nền trắng kèm ảnh mẫu thật
    (`anh_tach.bo_canh`), cắt theo khoảng trắng dọc / khối liền; hỏng thì lùi về từng vai (ảnh thật tách nền, không
    được thì AI vẽ). Tài khoản Gemini xếp theo credit còn nhiều nhất (1 ảnh ≈ 17 credit; tài khoản lớn 12.096/đợt ~5 h).
  - Mỗi nhịp bật đúng cụm "moc" của giọng đọc; nhịp không khớp lời thì bỏ; cảnh chỉ còn "xuất hiện" thì bỏ;
    hai nhịp cách > 4 s thì tách thành hai lần bật.
  - Tiếng động diễn cảnh: ĐÃ TẮT (user nghe thử "không hợp") — `TIENG_DONG_BAT`.
  - Render Remotion: GPU (gl=angle) + 3 clip song song (đo 20 clip: 210 s -> 109 s); `RENDER_GL=cpu` để tắt GPU.
  - Bản đồ khoanh vùng: tên nằm GIỮA vùng khoanh sau khi viền chạy xong.
- **Thẻ ảnh highlight** (`lop_phu.py`, 12/10 user bản 2): ChatGPT chọn câu mang Ý QUAN TRỌNG (số liệu, bước ngoặt,
  so sánh nổi bật, lần đầu nhắc loài/người/vật/nơi). Bản "mọi dẫn chứng, không định mức" (200 thẻ) bị user chê rối mắt
  13/10 -> về ~1 thẻ / 3-5 câu, tối đa 1 thẻ/câu, thẻ hiện >= 3 s, cách nhau >= 1 s, bỏ thẻ trùng thông tin; mỗi thẻ một cụm moc + từ khoá ảnh + CHỮ NHẤN MẠNH 2-7 chữ (bắt buộc;
  số viết chữ -> chữ số qua `so_hien_thi.py`). Ảnh Google Images (bỏ ảnh có chữ / hoạt hình / trùng). Thẻ = 3 LỚP chỉnh tay được trong CapCut (13/10 user):
  ảnh thật `lop_phu` (bấm Thay thế để đổi ảnh), khung trắng bo góc + bóng + vạch cam `lop_phu_khung` (PNG dùng chung,
  ô ảnh trong suốt), chữ nhấn mạnh là lớp chữ CapCut `lop_phu_chu` (sửa chữ trực tiếp); cỡ **65% khung**, lệch nhẹ
  phải/trái xen kẽ, nảy vào + mờ ra; bật đúng lúc giọng đọc tới cụm "moc" (giờ từng chữ do `can_chu.py` căn bằng wav2vec2), tắt hết câu hoặc khi thẻ sau bật (bỏ thẻ bật sát < 1,5 s). Câu trả lời ChatGPT lưu ở `ra/<dự án>/lop_phu_hoi.json` (chạy lại giữ nguyên bộ thẻ; xoá file để hỏi lại). Tắt: `--khong-lop-phu`.
- **Lớp Remotion "BẢNG GIẤY" khớp lời** — MẶC ĐỊNH TẮT (12/10 user xem thử rồi bỏ; bật lại `--co-bang-giay`) (`bang_giay.py` + `remotion/src/BangGiay.jsx`, 12/10 user — kiểu kênh
  "Вся жизнь пчелы"): ChatGPT chọn dàn dựng TỪNG CÂU (đoạn ~20 câu, hỏi lại câu thiếu; cache
  `ra/<dự án>/bang_giay_kich_ban.json`): `toan_canh` (video tràn màn hình như cũ, ~30%), `the` (cảnh quay trong thẻ
  viền trắng bóng đổ trên nền giấy be + tiêu đề 1-4 chữ + nhãn chỉ chi tiết), `cau_hoi` (câu hỏi chữ to trên nền mờ),
  `so_sanh` (cột số đếm chạy), `moc` (năm đếm lên + thẻ ảnh), `ban_do` (bản đồ phẳng tô nước — chỉ tên nước có trong
  world-atlas, không thì về `the`). Cảnh quay trong thẻ = đúng các đoạn cắt ghép của câu đó (cắt sẵn vào
  `remotion/public/bg/`, giữ khung cuối 2 s). Câu không phải toan_canh liên tiếp gom thành KHỐI (<= 45 s): camera lướt
  thẻ này -> thẻ kia, mũi tên cam nét đứt vẽ dần. Khối đặt trên track `bang_giay` trên cùng; hiệu ứng/thẻ ảnh trùng
  khoảng khối bị bỏ. Render ~ thời gian thực (3 phút nội dung ≈ 3,5 phút). Tắt `--khong-bang-giay`; thử vài phút đầu:
  `--bang-giay-den 180`.
- **Hiệu ứng** (`hieu_ung.py`, track `hieu_ung` nằm giữa track hình và thẻ ảnh; tắt: `--khong-hieu-ung`):
  - *Bản đồ đường đi A→B*: ChatGPT tìm câu nói về di chuyển/lan rộng giữa HAI ĐỊA DANH THẬT; Remotion vệ tinh, camera
    ôm cả hai điểm, đường vàng cong vẽ dần + chấm sáng ở mũi (`nen_ban_do.chuan_bi_duong`). Bỏ tuyến có đầu không phải
    địa danh thật cấp thành phố trở lên ("trại ong → nhà"), nơi này nằm trong nơi kia ("Bordeaux → Pháp"), cách < 50 km;
    cùng tuyến trong 60 s chỉ vẽ một lần.
  - *Khung highlight viền vàng (kính lúp không có ảnh)*: ĐÃ TẮT (12/10 user) — `hieu_ung.PHONG_BAT`.
  - *Phủ màu* ấm lướt qua ~1 s ở mỗi lần đổi chương.
  - Không chồng nhau; thẻ ảnh phủ không đè lên bản đồ/highlight.
- **KHÔNG tự thêm nhạc nền và chữ nhấn mạnh** (12/10 user). Mã còn đó: bật lại bằng `--co-nhac` / `--co-chu`
  (chữ: ChatGPT chọn cụm NGUYÊN VĂN theo đoạn, `so_hien_thi.py` đổi số viết chữ -> chữ số). Không SFX (`SFX_BAT`).
- ChatGPT (cookie) chia chương — dùng cho chuyển cảnh: cùng cảnh = cắt thẳng; đổi cảnh ≈45% chuyển nhẹ; đổi chương =
  chuyển mạnh; hai đoạn không liền nhau thì không chuyển. Chỉ dùng loại SẠCH (Mờ dần, Rõ dần, Trượt trái/phải, Phóng to).
- Mọi ảnh tĩnh có keyframe chuyển động (phóng vào/thu ra/lia). Video YouTube có logo ở góc: phóng 1,25× giấu logo
  (cờ `phong` trong kho, do bước tự động dò).
- Kiểu mới: tắt "hút vào đoạn chính" và đưa video gốc vào khung Phương tiện của bản nháp.
- Nhịp hình do bước khớp (`goi_y.py`) quyết: đoạn chạy tới HẾT CẢNH QUAY của nguồn (1,2-5,5 s) và KHÔNG chạy qua
  chỗ ngắt nghỉ của giọng đọc (lặng >= 0,25 s trong giong_doc.wav, cache `ra/<dự án>/nghi.json`) -> mỗi chỗ nghỉ là một
  lần đổi cảnh; hai đoạn LIỀN NHAU không cùng một video và không gần như giống nhau (cosine SigLIP > 0,92); ảnh tĩnh
  chỉ khi không còn video dùng được.

## Sửa
Chỉnh `ra/<dự án>/ke_hoach.json` (giây) rồi `--giu-ke-hoach`; `--tinh-lai-chuyen-canh` khi ô hình đã đổi.

## Ghi chú
- Chưa xuất MP4 (dựng thành bản nháp CapCut).
- Chuyển cảnh ghi JSON trực tiếp theo mã danh mục CapCut thật (pycapcut sai mã) và tự cài gói vào cache CapCut.
- Số câu ChatGPT đề xuất (thẻ ảnh, hiệu ứng) dao động nhẹ giữa các lần chạy.
