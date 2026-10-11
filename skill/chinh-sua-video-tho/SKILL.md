---
name: chinh-sua-video-tho
description: Chỉnh sửa dự án video THÔ (đã ghép hình khớp lời + giọng đọc) thành bản hoàn chỉnh trong CapCut — tự lập kế hoạch chuyển cảnh, chữ số liệu, nhạc nền (kho YouTube), chuyển động cho ảnh, rồi dựng dự án CapCut mới. Dùng khi người dùng muốn "edit/hoàn thiện/thêm hiệu ứng, nhạc, chuyển cảnh" cho dự án thô của repo bán-content, hoặc gõ /chinh-sua-video-tho.
---

# Chỉnh sửa dự án thô -> dự án CapCut hoàn chỉnh

Repo: `D:\CapCutTTS\bán-content` (mã ở `chinh_sua/`). Mọi lệnh chạy từ `chinh_sua/` với `python -X utf8`.

## Đầu vào
Dự án thô do `chay.py` sinh: `ra/ket_qua.json` (cảnh, nhịp, đoạn hình, giọng, mốc từng chữ) + clip trong `cache/clip/`.
Chưa có thì chạy ở gốc repo: `python chay.py <kịch_bản.txt> --ten "<tên>"`.

## Quy trình
1. **Kho** (một lần): `python kho_capcut.py danh-muc` (chuyển cảnh/hiệu ứng CapCut, chỉ dùng mục MIỄN PHÍ) và
   `python nhac_youtube.py` (tải ~3 bài nhạc nền/tâm trạng từ kênh "no copyright" trên YouTube; nguồn ghi ở `ra/nhac_nguon.txt`).
2. **Lập kế hoạch + dựng**: `python dung_hoan_chinh.py --ten "<tên dự án mới>"`
   - SRT từng câu (`ra/kich_ban_cau.srt`) với giờ theo MỐC TỪNG CHỮ THẬT của giọng đọc (Whisper).
   - ChatGPT (cookie) chia chương + tâm trạng nhạc.
   - Chuyển cảnh: cùng cảnh = cắt thẳng; đổi cảnh ≈45% chuyển nhẹ; đổi chương = chuyển mạnh. Chỉ dùng loại SẠCH
     (Mờ dần, Rõ dần, Trượt trái/phải, Phóng to) — Zoom gần nhẹ / Lật hiện ra / Hòa trộn rực rỡ làm nháy khung.
   - Chữ nhấn mạnh: CHỈ chỗ có CON SỐ / năm / thời lượng / số đo (+ thuật ngữ quan trọng); không chèn tên riêng hay khẩu hiệu.
   - Nhạc nền theo chương (fade, hạ âm lượng theo độ to). KHÔNG có hiệu ứng âm thanh (người dùng bỏ 09/10; `SFX_BAT=True` để bật lại).
   - Mọi ảnh tĩnh có keyframe chuyển động (phóng vào/thu ra/lia trái/lia phải).
3. **Sửa**: chỉnh `ra/ke_hoach.json` (giây) rồi `--giu-ke-hoach`; `--sua-nhanh` làm lại chữ + nhạc; `--tinh-lai-chuyen-canh`
   khi ô hình đã đổi (giữ chữ/nhạc, dựng lại chuyển cảnh và cập nhật giờ theo SRT).

## Ghi chú
- Bản đồ Remotion KHÔNG có dòng chú thích; phần Remotion đăng ký kênh/biểu đồ sẽ là lớp phông xanh (chưa làm).
- Chưa xuất MP4; chưa mở thử bản nháp trong CapCut khi viết skill này.
- Chuyển cảnh được ghi JSON trực tiếp theo mã danh mục CapCut thật (pycapcut sai mã) và tự cài gói vào cache CapCut.
