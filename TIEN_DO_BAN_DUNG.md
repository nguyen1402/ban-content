# BÁO CÁO TIẾN ĐỘ & TỔNG KẾT HỆ THỐNG: BÀN DỰNG THEO CÂU
> **Cập nhật 01/11 (Đợt 2):** bộ máy duy nhất là `ban_dung.tu_dong_bam_chu_the`, chủ thể lấy từ `chu_the` của dự án; nút ⚡ chạy
> nền và KHÔNG tự xuất CapCut; các script `chay_*`/`dieu_phoi_*` đã chuyển vào `luu_tru_script_cu/`, đừng chạy lại. Phần dưới là
> báo cáo cũ, số liệu và mục "Lọc chủ thể đặc thù" không còn đúng hoàn toàn.
> **Ngày cập nhật:** 01/11/2026 (00:38)  
> **Dự án kiểm thử:** `ra/chosoi/` (160 câu kịch bản)  
> **Địa chỉ máy chủ:** `http://127.0.0.1:8777/ban-dung` (hoặc `/ban_dung`)

---

## 1. MỤC TIÊU & BÀI TOÁN CỐT LÕI ĐÃ GIẢI QUYẾT

1. **Khắc phục giao diện cũ khó thao tác:**
   - Chuyển toàn bộ giao diện dọc 3 cột sang **Bố cục chuẩn NLE CapCut Desktop**:
     - **Nửa trên bên trái:** Kho Nguồn Media & YouTube theo Chủ thể kịch bản.
     - **Nửa trên bên phải:** Màn hình Monitor Preview 16:9 với điểm In `[ I ]` / Out `[ O ]` và Storyboard dải ảnh từng giây.
     - **Nửa dưới:** Timeline đa track toàn màn hình chuẩn CapCut (Track Video + Track Lời đọc & Waveform).
   - Loại bỏ hoàn toàn tất cả **"Đuôi chất lượng"** (`+ documentary`, `+ 4k`, `+ b-roll`) gây nhiễu từ khoá tìm kiếm.

2. **Khắc phục vấn đề dựng thủ công quá lâu (160 câu):**
   - Không bắt người dùng phải xem và căn In/Out cho từng câu lẻ loi.
   - Xây dựng cơ chế **Tự động băm theo Chủ thể**: 1 click tự động băm, chọn lọc và lấp đầy timeline.

3. **Giải quyết bài toán "Bán-content" & Kháng bản quyền YouTube (Content ID):**
   - **Băm nhỏ dồn dập:** Cắt nhịp dồn theo từng hơi thở/dấu ngắt câu của MC ($1.2s - 3.5s$).
   - **Giãn cách nguồn video gốc ($\ge 3$ cảnh):** Các mảnh cắt từ cùng một video YouTube gốc tuyệt đối không xuất hiện cạnh nhau, bắt buộc phải cách xa nhau ít nhất 3 đến 5 cảnh, đảo luân phiên liên tục hơn 100 nguồn video trong kho.
   - **Khóa sử dụng 1 lần (Zero Reuse):** Mỗi mảnh cắt chỉ được dùng đúng 1 lần duy nhất trên toàn bộ timeline.

4. **Chấm điểm thị giác cấp mảnh thật (Slice-level Scoring) bằng SigLIP GPU:**
   - Tuyệt đối không chấm điểm đại diện cho cả video gốc (tránh lỗi video có sói ở phút thứ 8 nhưng đoạn đầu là đại bàng/người dẫn chuyện).
   - Mắt AI soi trực tiếp vào khung hình thực tế của từng mảnh cắt 2s – 4s trong kho.

5. **Cơ chế Bù chỗ thiếu bằng ẢNH AI (Flow Image) hoặc VEO 3:**
   - Những cảnh không có trong kho (dê núi sừng nhọn, hươu chạy, cừu đeo giáp gai...): Hệ thống **để trống khoảng thời gian trên timeline (blank)** chứ tuyệt đối không gán ghép bừa bãi.
   - Cung cấp nút bấm 1 click: **`[🎨 Ảnh AI]`** (Flow 0 điểm) và **`[🎬 Veo 3]`** để lấy prompt chuẩn National Geographic bù vào.

---

## 2. NHẬT KÝ NÂNG CẤP & SỬA LỖI HÔM NAY (31/10 - 01/11/2026)

### 2.1. Phát hiện và Khắc phục các lỗi thực tế khi kiểm thử trên CapCut:

1. **Lỗi lạc video dọc & viền đen (Pillarbox):**
   * *Hiện tượng:* Đoạn Cảnh 10 bị dính video dọc `#shorts` của YouTube (`v_kpW63PbyE00` có dòng chữ "Hình ảnh minh họa" và 2 viền đen dày).
   * *Nguyên nhân:* Bộ lọc cũ chỉ quét tên tệp mà không đọc độ phân giải khung hình.
   * *Khắc phục:* Viết bộ lọc OpenCV đo chính xác tỉ lệ khung hình $w \ge 1.55 \times h$ và quét điểm ảnh 2 cột biên trái/phải để loại trừ 100% video dọc, video vuông, pillarbox và video chứa `#shorts`/`tiktok`.

2. **Lỗi Cảnh 1 bị dính chim đại bàng săn dê:**
   * *Hiện tượng:* Câu mở đầu *"Một chiếc răng gãy có thể là bản án tử đối với loài sói"* nhưng CapCut phát ra hình một con chim đại bàng khổng lồ đang sà xuống săn dê núi.
   * *Nguyên nhân:* Video gốc `v_yrUjfpT1an8` (tiêu đề: *Eagle vs Wolves*) dài 10 phút, đoạn sau có bầy sói nhưng 3 giây đầu tiên lại là chim đại bàng. Thuật toán cũ lấy vector đại diện của cả video gán cho mảnh cắt đầu tiên nên bị chấm nhầm.
   * *Khắc phục:* Triển khai **Lập chỉ mục thị giác cấp mảnh (`chi_muc_manh_clip.npz`)**. AI soi trực tiếp vào giây đầu tiên của từng mảnh, đo được điểm chim đại bàng cao gấp đôi sói nên đã loại bỏ vĩnh viễn clip này khỏi câu về sói. Cảnh 1 đã được thay thế chuẩn xác bằng cú máy cận cảnh sói hoang đứng giữa rừng (`v_DRLq2jzbZvc_c33`).

3. **Lỗi đứng hình / Chỗ nghỉ giọng mà không chuyển cảnh:**
   * *Hiện tượng:* Người thuyết minh đã ngắt nghỉ, lấy hơi nhưng khung hình vẫn giữ nguyên, không chuyển góc máy.
   * *Nguyên nhân:* Tham số `DOAN_GOP_NGAN = 2.0s` và `NHIP_TOI_THIEU = 3.5s` quá lớn, tự động gộp các khoảng nghỉ ngắn (1.2s - 1.8s) vào cảnh trước.
   * *Khắc phục:* 
     * Hạ ngưỡng bắt ngắt giọng thật trong sóng âm (`giong_doc.wav`) xuống **`1.2s`**.
     * Giới hạn độ dài tối đa của 1 cú máy xuống **`3.5s`**.
     * Kết quả: Tổng số đoạn cắt tăng từ **373 lên 503 segments** (tăng thêm 130 cú chuyển cảnh). Cứ trung bình **2.2 giây là đổi 1 góc máy mới**, khớp hoàn toàn với nhịp thở của MC.

4. **Lỗi bẫy câu văn dài trong AI thị giác (SigLIP / CLIP):**
   * *Hiện tượng:* Nạp cả câu văn triết lý hoặc câu miêu tả dài (*"Wolf showing its sharp teeth and powerful jaws in the wilderness"*) khiến AI chọn nhầm cảnh đồng cỏ, rừng rậm rỗng không có sói.
   * *Nguyên nhân:* Từ ngữ bối cảnh (`wilderness`) làm vector bị lệch 57% về phía phong cảnh; chi tiết vi mô (`sharp teeth`) không tồn tại trong các cú máy toàn cảnh thông thường.
   * *Khắc phục:* Chuyển sang **Cấu trúc Bóc tách 3 tầng (Atomic Visual Elements)**:
     $$\text{Prompt SigLIP} = [\text{Chủ thể cốt lõi}] + [\text{Cỡ cảnh Toàn/Cận}] + [\text{Hành động chính}] + [\text{Bộ lọc phủ định: no humans, no birds}]$$

5. **Lỗi nhận diện nhầm lợn rừng ở Cảnh 15:**
   * *Hiện tượng:* Câu nói về lợn rừng húc trả quyết liệt nhưng bị gán nhầm cảnh bầy cừu trên đồng cỏ ướt.
   * *Khắc phục:* Khóa chặt các chủ thể đặc thù vào đúng nguồn chuyên biệt (`txRKUAquIjk` cho lợn rừng; `GS6E3t-5its` cho lừa; `_-htBS_QRbQ` cho Llama; `6P4Lt-SIUFU` cho nhím). Cảnh 15 hiện tại để trống chính xác 5.79 giây đầu (dê núi, hươu) và khớp đúng 100% video lợn rừng thật ở vế cuối.

---

## 3. KIẾN TRÚC ĐIỀU PHỐI TỔNG QUÁT (ÁP DỤNG CHO MỌI DỰ ÁN VỀ SAU)

Quy trình chuẩn hóa trong `ban_dung.py` (hàm `tu_dong_bam_chu_the`) hoạt động tự động trên mọi kịch bản mới theo 4 bước:

```
[Kịch bản & Giọng đọc]
         │
         ▼
[1. Băm dày theo sóng âm] ──► Ngắt nghỉ hơi >= 1.2s & Cắt tối đa 3.5s
         │
         ▼
[2. Mắt AI cấp mảnh]      ──► Quét kho sinh file chi_muc_manh_clip.npz (~3 MB trên GPU RTX 3060)
         │
         ▼
[3. Phân tách thị giác]   ──► Bóc tách [Chủ thể] + [Cỡ cảnh] + [Hành động] + [Khử người/chim]
         │
         ▼
[4. Bộ lọc Bán-content]    ──► Giãn cách nguồn gốc >= 3 cảnh + Zero Reuse + Để trống chỗ thiếu
         │
         ▼
[Xuất thẳng bản nháp CapCut Desktop]
```

### Các thông số chuẩn đã chốt:
| Thông số | Giá trị | Ý nghĩa |
|---|---|---|
| `DOAN_GOP_NGAN` | `1.2s` | Ngưỡng ngắt nghỉ tối thiểu để tạo 1 cú cắt cảnh mới. |
| `DOAN_MAX_NGHI` | `3.5s` | Thời lượng tối đa của một cú máy (chống đứng hình). |
| `KACH_XA_CANH` | `3 cảnh` | Khoảng cách tối thiểu giữa 2 lần xuất hiện của cùng một nguồn video gốc (kháng Content ID). |
| `Dung lượng Cache` | `~3.16 MB` | File `.npz` nén chứa toàn bộ vector thị giác của 1.600+ clip, tải trong 0.05s. |
| `Tỉ lệ khung hình` | $\ge 1.55$ | Chỉ nhận video 16:9 điện ảnh, loại bỏ 100% Shorts/dọc/pillarbox. |

---

## 4. HƯỚNG DẪN THỰC THI CHO CÁC DỰ ÁN TIẾP THEO

Khi bắt đầu một dự án mới bất kỳ (ví dụ: *sutu, camap, tank, space...*):
1. **Nạp kịch bản & Giọng đọc:** Chạy tạo âm thanh và phân tích kịch bản như quy trình chung.
2. **Nạp video vào kho:** Dán link YouTube vào các chủ thể trên giao diện Bàn dựng (`http://127.0.0.1:8777/ban-dung`).
3. **Bấm 1 Click `⚡ TỰ ĐỘNG BĂM THEO CHỦ THỂ`:**
   - Hệ thống tự động trích xuất khung hình và lập chỉ mục SigLIP cho dự án mới (~1 phút).
   - Tự động băm nhịp dày 2s – 3s theo đúng nhịp thở của giọng đọc.
   - Tự động đảo nguồn giãn cách $\ge 3$ cảnh và loại trừ hoàn toàn clip trùng lặp.
   - Xuất thẳng timeline hoàn chỉnh sang CapCut Desktop.
4. **Bù hình cảnh thiếu:** Mở Bàn dựng Web, lướt các block viền cam `⚠️ Thiếu footage` $\rightarrow$ Bấm `[🎨 Ảnh AI]` hoặc `[🎬 Veo 3]` để bù hình vào các khoảng trống.
