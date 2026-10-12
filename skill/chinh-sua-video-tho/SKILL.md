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

- **Bản đồ vệ tinh cho cảnh nhắc địa điểm** (kiểu mới): cảnh có `loai = dia_diem` + `dia_danh_en` (do `mo_ta_canh.py`
  hỏi ChatGPT) — đoạn ĐẦU của cảnh thay bằng clip Remotion `BanDoNen` chế độ vệ tinh: camera phóng từ cả lục địa vào,
  đường viền THẬT của địa danh (Nominatim/OSM; chỉ nhận vùng hành chính/địa danh thật, bỏ từ chỉ hướng "Northern…"
  khi cần, khung theo mảnh đất liền lớn nhất) chạy nét vàng + tô mờ, tên địa danh góc trên. Nền: Sentinel-2 cloudless
  **2016** của EOX (CC BY 4.0, dòng ghi nguồn nhỏ góc dưới phải; các năm 2017+ là NC nên không dùng). Cache ô ảnh
  `cache/tiles_vt/`, clip `cache/ban_do_vt/`. Tắt: `--khong-ban-do`.
- **Lớp ảnh phủ minh hoạ** (`lop_phu.py`, 12/10 user): chia lời thành đoạn ~20 câu, hỏi ChatGPT câu nào CẦN thêm một
  ảnh (loài/vật/người/tài liệu cụ thể mà cảnh nền khó có, hoặc so sánh hai thứ; ~1 thẻ / 6-10 câu) + từ khoá ảnh ngắn.
  Ảnh lấy Google Images (cửa sổ Chrome hiện), SigLIP chấm theo từ khoá, BỎ ảnh có chữ / hoạt hình, KHÔNG lặp ảnh đã
  dùng (cả ảnh giống hệt ở link khác). Làm thẻ PNG bo góc viền trắng bóng đổ (`ra/<dự án>/lop_phu/`), đặt trên track
  `lop_phu` (trên track hình) ~40% khung, lệch phải/trái xen kẽ, nảy vào + mờ ra, cách nhau >= 8 s; video nền vẫn chạy.
  Tắt: `--khong-lop-phu`.
- **Hiệu ứng** (`hieu_ung.py`, track `hieu_ung` nằm giữa track hình và thẻ ảnh; tắt: `--khong-hieu-ung`):
  - *Bản đồ đường đi A→B*: ChatGPT tìm câu nói về di chuyển/lan rộng giữa HAI ĐỊA DANH THẬT; Remotion vệ tinh, camera
    ôm cả hai điểm, đường vàng cong vẽ dần + chấm sáng ở mũi (`nen_ban_do.chuan_bi_duong`). Bỏ tuyến có đầu không phải
    địa danh thật cấp thành phố trở lên ("trại ong → nhà"), nơi này nằm trong nơi kia ("Bordeaux → Pháp"), cách < 50 km;
    cùng tuyến trong 60 s chỉ vẽ một lần.
  - *Khung highlight viền vàng*: câu chỉ vào chi tiết nhỏ -> ffmpeg dựng từ chính đoạn hình đang chiếu: nền tối + mờ,
    giữa là khung bo góc viền vàng phóng 2× phần giữa cảnh (giữ cả phóng giấu logo).
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
