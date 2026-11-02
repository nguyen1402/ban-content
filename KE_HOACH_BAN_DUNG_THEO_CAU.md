# Kế hoạch: Bàn dựng theo câu (chọn hình từng câu trước khi tải)

> Tài liệu giao việc cho người/agent lập trình (Antigravity IDE). Viết ngày 30/10/2026 dựa trên code hiện tại của repo
> `bán-content`. Đọc hết mục 0–3 trước khi code.

---

## 0. Mục tiêu

Hiện nay quy trình là: tìm video **theo chủ thể** → tải **cả video** → băm toàn bộ → máy tự khớp → người dùng sửa tay
trong CapCut. Kho đầy footage sai (chó thay sói, người tiền sử, chuồng gà…), sửa sau rất chậm.

Làm mới một **"Bàn dựng theo câu"**: người dùng đi lần lượt từng câu lời đọc, với mỗi câu chọn một trong ba cách:

| Cách | Ý nghĩa |
|---|---|
| 🎥 **Footage** | Tìm video (máy gợi ý từ khoá *hoặc người dùng tự gõ / tự dán link*), **xem trực tiếp**, đặt **điểm vào / ra**, máy **chỉ tải đúng khoảng đó** rồi đặt vào câu |
| 🖼 **Ảnh AI** | Vẽ ảnh trên Flow (0 điểm), câu lệnh điền sẵn, sửa được |
| 🎬 **Veo** | Tạo clip Flow Veo (tốn điểm), câu lệnh điền sẵn, sửa được |

Yêu cầu bắt buộc của người dùng:

1. **Chủ động**: người dùng tự tìm bằng tay, tự chỉ định đoạn cắt cho bất kỳ câu nào — kể cả câu **không có chủ thể**
   (câu chung chung, câu bình luận). Máy chỉ gợi ý, không ép.
2. **Nhanh hơn** băm-rồi-sửa: không tải cả video, không băm cả video; máy chuẩn bị trước câu kế tiếp.
3. **Không bao giờ ghi đè bản nháp CapCut người dùng đã sửa tay** — luôn xuất ra bản nháp tên mới.
4. **Không dùng video YouTube có nhãn "do AI tạo"**.

Không thuộc phạm vi lần này: nhạc, SFX, chữ, chuyển cảnh (đã có ở bước ✨ Hoàn thiện).

---

## 1. Kiến trúc hiện có cần dùng lại (KHÔNG viết lại)

Máy chủ: **Bottle** (`giao_dien/may_chu.py`), cổng mặc định 8777. Mẫu endpoint:
`@app.post("/api/...")`, đọc `request.json`, tên dự án qua `slug(d["du_an"])`, trả `json_ok({...})`, lỗi
`raise HTTPError(400, "...")`. Việc lâu chạy nền bằng `_job_doi_thu(ham)` → trả `job`; giao diện hỏi trạng thái
(xem các endpoint đang dùng `TT_DOI_THU`). File phục vụ cho trình duyệt qua `url_tep(path)`.

Giao diện dựng: `giao_dien/dung.html` (JS thuần, hàm tắt `$()`, `api()`, `post()`, `tb()` thông báo).

| Việc | Hàm có sẵn | Ghi chú |
|---|---|---|
| Thư mục dự án | `common.thu_muc_du_an(du_an)[1]` → `ra/<du_an>/` | |
| Câu lời đọc + mốc giây | `ra/<du_an>/tu_khoa.json` (mỗi "cảnh" = 1 câu: `id, bat_dau, dai, text`) | `cho_phu.doc_cau(out)` cho câu chi tiết `t0, t1, text` |
| Chỗ ngắt giọng trong câu | `goi_y.cho_nghi_giong_doc(du_an, canh, goi_y._lang(du_an, goi_y.LANG_GIONG))` | dùng để chia câu dài thành 2–3 nhịp hình |
| Kế hoạch hình từng câu | `dung_tay.doc_dung(du_an)` / `dung_tay.luu_canh(du_an, canh_id, doan)`; file `ra/<du_an>/dung.json` | mỗi `doan`: `{loai: "video"|"anh", kho_id, vao, bd, dai}` |
| Kho mảnh | `dung_tay.doc_kho(du_an)`, `dung_tay._cap_nhat_kho(du_an, kid, **truong)` | mục video: `loai, file, video_goc, giay_bat_dau, giay_ket_thuc, dai, rong, cao, trang_thai, tay, ghi_nguon…` |
| Tìm YouTube (không tải) | `dung_tay.tim_youtube(q, n)` → `[{id, tieu_de, dai, kenh, luot_xem}]`; `chon_tay.tim(du_an, q, trang, …)` (có bộ lọc như YouTube) | ưu tiên `chon_tay.tim` |
| Tìm Google Videos | `anh_google.google_video(q, n)` | cửa sổ Chrome, có thể hỏi captcha |
| Storyboard (không tải) | `xep_hang.storyboard(vid)` → `(t, e, tong)`: giây + vector SigLIP từng khung; `xep_hang._khung_storyboard(vid)` → ảnh PIL | có cache `cache/storyboard_*` |
| Vector chữ / ảnh | `nhung_siglip.nhung_chu([...])`, `nhung_siglip.vec_mo_ta(text, [])`, `nhung_siglip.nhung_anh(imgs)` | |
| Lọc nhãn AI YouTube | `dung_tay.la_video_ai(vid)` (cache `cache/video_ai_yt.json`) | đọc mục "How this was made" |
| Giấy phép | `dung_tay.nguon_an_toan(vid, kenh)` | CC / kênh chính phủ Mỹ |
| Lọc kênh xấu | `dung_tay.la_kenh_loai(v)`, `dung_tay.bi_chan(v)` | |
| Kiểm tra nội dung hình | `nham_lan.py`: `kho_nham` (con dễ nhầm), `con_la` (con vật lạ), `vec_chu` + `CO_CHU_THE` (chủ thể có trong hình), `vec_tinh` + `HANH_DONG_MANH` (đúng hành động), `tu_cam` / `ten_bi_cam` (lọc tên video) | dùng lại nguyên, áp lên khung storyboard |
| Tải video gốc | `dung_tay._tai_video_goc(vid, file, chi_hinh=True)` (yt-dlp) | bàn dựng cần thêm bản **tải theo khoảng** (mục 4.3) |
| Điểm đổi cảnh | `sach_hinh.canh_cat(file, key)` | |
| Logo / khung hẹp | `sach_hinh.khung_hep(...)`, `loc_minh_hoa.khung_xau(...)` | |
| Ảnh AI một chỗ | endpoint `/api/anh_ai/ve_thu`, `/api/anh_ai/luu`; hàm `anh_ve.ve_prompt(prompt, thu, ten)` | `common.giu_dac_diem` tự gắn đặc điểm bắt buộc (cừu gai nhím…) |
| Veo một chỗ | `flow_video.tao(prompt, thu, ten_goc, model=…, phan_giai="720p", do_dai="8s")`; `veo_canh.py` | tốn ~12 điểm/clip; `flow_video.uoc_diem(...)` |
| Đánh dấu 📝 ảnh AI / Veo | `cho_phu.py` (`hinh_ai.json`), `cho_phu.canh_phu(du_an)` | bàn dựng phải ghi vào cùng chỗ này để ✨ hiểu |
| Hồ sơ câu chuyện | `ra/<du_an>/ho_so_truyen.json` (`nhan_vat[].mo_ta_en, khoa_en, kem_en, bat_buoc_en`) | |
| Xuất bản nháp | `dung_tay.tao_nhap(...)` (thô), `chinh_sua/dung_hoan_chinh.py --du-an X --ten Y` (hoàn chỉnh) | |
| Ghép không ghi đè | `ghep_sau_moc.py --goc A --moi B --ten C --moc <giây>` | mục 6 cần mở rộng thành ghép **theo danh sách khoảng** |

Quy ước code của repo: tên biến/hàm tiếng Việt không dấu, chú thích tiếng Việt có ghi ngày + lý do
(`# 30/10 user (...): ...`), hằng số cấu hình ở đầu file viết HOA, xử lý lỗi kiểu `except Exception as e:  # noqa: BLE001`
rồi `log(...)`. Windows: mọi `subprocess` thêm `creationflags=0x08000000`; đọc/ghi file `encoding="utf-8"`.

---

## 2. Mô hình dữ liệu mới

### 2.1 `ra/<du_an>/ban_dung.json` — trạng thái bàn dựng theo câu

```json
{
  "_phien_ban": 1,
  "cau": {
    "37": {
      "cach": "footage",            // "footage" | "anh_ai" | "veo" | "chua"
      "loai_goi_y": "quay_duoc",    // máy phân loại: "quay_duoc" | "khong_quay_duoc"
      "tin_cay": "vang",            // "xanh" | "vang" | "do" (mục 5)
      "tu_khoa": ["grey wolf running through snow", "wolf pack winter"],
      "bat_buoc": ["wolf"], "cam": ["dog", "person", "cartoon"],
      "nhip": [                      // các nhịp hình trong câu (theo chỗ ngắt giọng)
        {"bd": 0.0, "dai": 2.6, "nguon": {"kieu": "youtube", "vid": "abc123xyz00", "vao": 812.4, "ra": 815.0},
         "kho_id": "v_abc123xyz00_t812", "da_tai": true}
      ],
      "cau_lenh_anh": "...", "cau_lenh_veo": "...",
      "ghim_nguon": ["abc123xyz00"],  // video người dùng ưu tiên cho các câu sau cùng chủ thể
      "sua_luc": 1793300000.0
    }
  },
  "ung_vien": {                      // cache kết quả tìm + chấm theo câu (để mở lại không tìm lại)
    "37": {"q": "...", "luc": 0, "ds": [{"vid": "...", "tieu_de": "...", "kenh": "...", "dai": 0,
            "khoang": [[810.0, 818.0, 0.142]], "nhan": {"ai": false, "cc": true, "chu_the": 0.11, "nham": false,
            "con_la": null, "nhung": true}}]}
  }
}
```

### 2.2 Đồng bộ sang `dung.json` (để ✨ và xuất bản nháp dùng như cũ)

Mỗi khi người dùng bấm **Dùng** ở một câu: ghi `dung_tay.luu_canh(du_an, canh_id, doan)` với `doan` dựng từ `nhip`
(`loai:"video"`, `kho_id`, `vao` = giây trong **tệp mảnh đã tải** (thường 0 + lề), `bd`, `dai`). Đánh dấu
`dung[canh_id]["ban_dung"] = true` và **không** đặt `goi_y=true` (để các lần gợi ý tự động sau không ghi đè).

Câu chọn 🖼 / 🎬: ghi vào `hinh_ai.json` qua các hàm của `cho_phu` (cùng định dạng chỗ 📝 hiện có) để bước 🎨 / ✨ vẽ
đúng chỗ; đồng thời xoá `doan` footage của câu đó trong `dung.json`.

### 2.3 Mục kho cho mảnh tải theo khoảng

`kid = f"v_{vid}_t{int(vao)}"`, các trường: `loai:"video"`, `file`, `video_goc: vid`, `giay_bat_dau: vao`,
`giay_ket_thuc: ra`, `dai`, `rong`, `cao`, `trang_thai:"xong"`, `tay: true`, `ban_dung: true`, `ghi_nguon`, `giay_phep`.
Mảnh tự chọn (`tay: true`) được các bước lọc tự động tôn trọng — giữ nguyên quy ước này.

---

## 3. Luồng người dùng (UX)

### 3.1 Vào bàn dựng
Nút mới **"🎞 Bàn dựng theo câu"** trên `dung.html` → trang mới `giao_dien/ban_dung.html?du_an=<x>`.

Bố cục 3 cột:
- **Trái — danh sách câu** theo thời gian: số câu, mốc giây, 1 dòng lời, biểu tượng cách (🎥/🖼/🎬/—) và chấm màu tin cậy
  (🟢🟡🔴). Bộ lọc: "chỉ câu vàng/đỏ", "chỉ câu chưa chọn", "từ phút … đến …".
- **Giữa — câu đang chọn**: lời đọc, ▶ nghe đúng đoạn giọng (`giong_doc.wav` cắt theo `bat_dau/dai`, dùng `<audio>` +
  `currentTime`), 3 nút cách làm hình, rồi khu làm việc theo cách đã chọn (3.2–3.4).
- **Phải — xem trước**: trình phát (YouTube nhúng hoặc `<video>` mảnh đã tải), nút đặt **vào / ra**, khung tóm tắt các
  nhịp của câu (thanh thời gian câu, mỗi nhịp một ô màu).

### 3.2 Cách 🎥 Footage
1. **Ô từ khoá** điền sẵn (`tu_khoa[0]`), người dùng sửa tự do. Cạnh đó:
   - **"Dán link"**: dán URL YouTube bất kỳ (hoặc `youtu.be/…?t=812`) → bỏ qua tìm, mở thẳng video đó.
   - **"Tệp trên máy"**: chọn video có sẵn trong kho dự án hoặc một tệp trên máy (cho câu không có chủ thể / footage riêng).
   - Nguồn: YouTube (mặc định) | Google Videos | Kho dự án.
2. **Danh sách ứng viên** (tối đa 8/trang): mỗi video một hàng — tiêu đề, kênh, độ dài, **dải ảnh storyboard** (cuộn ngang),
   khoảng khớp tô màu, nhãn: `✓ có sói` / `⚠ giống chó` / `✗ nhãn AI` / `✗ không CC` / `⚠ con vật lạ: gà`.
   Video có nhãn AI **ẩn mặc định** (có công tắc hiện để biết). Bấm một ảnh trên dải → trình phát bên phải mở tại giây đó.
3. **Xem trực tiếp**: YouTube IFrame Player API (`https://www.youtube.com/iframe_api`), `player.seekTo(giay, true)`,
   `player.getCurrentTime()`. Nút **[ Vào ]** / **[ Ra ]** lấy giây đang xem; phím `I` / `O`. Có thể kéo trực tiếp trên dải
   storyboard để chọn khoảng. Hiện "khoảng 2,6 s / nhịp cần 2,6 s" và cảnh báo nếu ngắn hơn nhịp.
   Video chặn nhúng (lỗi player 101/150) → hiện dải storyboard + nút "Mở trên YouTube" (tab mới, `&t=<giây>`), người dùng
   gõ tay giây vào / ra.
4. **Dùng**: gửi `{vid, vao, ra, nhip}` → máy tải đúng khoảng (4.3), cắt theo cảnh quay nếu có điểm đổi cảnh trong khoảng,
   đặt vào nhịp đang chọn, chuyển sang nhịp kế tiếp của câu (hoặc câu kế tiếp khi hết nhịp).
   Một câu dài: chọn nhiều khoảng cho các nhịp; nút **"Lấp cả câu từ khoảng này"** tự kéo dài khoảng ra phủ hết các nhịp
   (cắt theo cảnh quay liền nhau trong cùng video).
5. **Câu không có chủ thể** (câu chung chung, bình luận): vẫn làm y hệt — máy không ép kiểm tra chủ thể, nhãn kiểm tra
   chỉ để tham khảo.

### 3.3 Cách 🖼 Ảnh AI
Ô câu lệnh tiếng Anh điền sẵn (AI viết theo câu + hồ sơ câu chuyện; `common.giu_dac_diem` tự gắn đặc điểm bắt buộc). Nút
**Vẽ thử** (2 ảnh, dùng `/api/anh_ai/ve_thu`), chọn 1 → **Dùng** (`/api/anh_ai/luu` + ghi chỗ vào `hinh_ai.json`).

### 3.4 Cách 🎬 Veo
Ô câu lệnh điền sẵn + ước điểm (`flow_video.uoc_diem`) + điểm còn hôm nay (`/api/veo_con`). **Tạo** chạy nền; xong hiện
video xem trước; **Dùng** → ghi vào chỗ Veo của `hinh_ai.json`. Lỗi kiểm duyệt Flow ("violate our policies") hiện rõ lý
do + gợi ý viết nhẹ lại.

### 3.5 Phím tắt
`↑/↓` câu trước/sau · `Enter` dùng ứng viên đang chọn · `1–8` chọn ứng viên · `F`/`A`/`V` đổi cách 🎥/🖼/🎬 ·
`I`/`O` vào/ra · `Space` phát/dừng · `N` nghe lời đọc câu · `J` nhảy tới câu vàng/đỏ kế tiếp · `/` vào ô từ khoá.

---

## 4. Backend chi tiết

### 4.1 Module mới `ban_dung.py` (gốc repo)

```text
doc(du_an) / ghi(du_an, d)                 # ban_dung.json, có khoá luồng
lap_danh_sach_canh(du_an, lam_moi=False)   # 4.2 — AI phân loại câu + từ khoá + bắt buộc / cấm (chạy nền, cache theo băm kịch bản)
nhip_cua_cau(du_an, canh_id)               # chia câu theo chỗ ngắt giọng (goi_y.cho_nghi_giong_doc), gộp nhịp < 2 s
tim_cho_cau(du_an, canh_id, q=None, nguon="youtube", trang=1)   # 4.4
cham_video(du_an, canh_id, vid)            # 4.5 — storyboard + kiểm tra -> {khoang, nhan}
tai_khoang(du_an, vid, vao, ra)            # 4.3 -> kid
dat_nhip(du_an, canh_id, i_nhip, kid, vao_trong_manh=0.0)   # cập nhật ban_dung.json + dung.json
chuan_bi_truoc(du_an, tu_canh, so=5)       # 4.6 — luồng nền
```

### 4.2 Danh sách cảnh (một lần hỏi AI cho cả bài, người dùng duyệt)
Dùng `common.hoi_nhieu([...])` (đã có xoay tài khoản Gemini/ChatGPT) với prompt yêu cầu JSON cho TỪNG câu:
`{"id", "loai": "quay_duoc|khong_quay_duoc", "hinh": "<mô tả tiếng Việt>", "tu_khoa_en": [2-3 cụm], "bat_buoc_en": [...],
"cam_en": [...]}`. Gửi theo lô 40 câu, kèm khối STORY BIBLE (`tu_dong_tim._ho_so_chu(out)`).
Quy tắc trong prompt: câu giả định / vật tưởng tượng / số liệu / ngoại hình đặc biệt chưa có thật (cừu mặc giáp gai) →
`khong_quay_duoc`. Lưu vào `ban_dung.json`. Giao diện có bảng duyệt dạng bảng chữ (sửa ô, đổi loại) trước khi tìm.

### 4.3 Tải theo khoảng (thay cho tải cả video)
```text
yt-dlp --js-runtimes node --cookies cookies.txt --no-playlist --no-warnings
       -f "bv*[height<=720]/b" -S "res:720,vcodec:h264"
       --download-sections "*{vao-2}-{ra+2}" --force-keyframes-at-cuts
       --ffmpeg-location <thư mục ffmpeg> -o ra/<du_an>/kho/video/v_{vid}_t{int(vao)}.mp4  https://youtu.be/{vid}
```
- Lấy cờ chung (`YTDLP`, `YT_JS`, cookies, `FFMPEG`) từ `common` / `dung_tay` giống `_tai_video_goc`.
- Lề ±2 s để người dùng còn trượt trong CapCut; ghi `loi_bd`, `loi_kt` (khúc lõi) vào mục kho — `goi_y` đã hiểu 2 trường này.
- Sau tải: `sach_hinh.khung_hep` (bỏ nếu khung dọc/viền đen), đo `dai/rong/cao` (`dung_tay._do_dai`, `_kich_thuoc`),
  `nhung_siglip.chi_muc_video("tay_"+kid, file)` để có chỉ mục cho các bước sau.
- Trước khi tải: bắt buộc `dung_tay.la_video_ai(vid)` = False (trừ khi người dùng bấm "vẫn dùng" — hỏi xác nhận).
- Timeout 300 s, thử lại 1 lần; lỗi thì báo rõ trên giao diện (không treo).
- Kiểm thử thực tế: so thời gian tải khoảng 6 s của video 20 phút với `_tai_video_goc` cả video (mục tiêu < 20 s).

### 4.4 Tìm cho một câu
1. `q` = từ khoá người dùng gõ, hoặc `tu_khoa_en[0]`.
2. Nguồn YouTube: `chon_tay.tim(du_an, q, trang)`; Google Videos: `anh_google.google_video(q, 10)`; Kho: lọc mục kho
   theo điểm SigLIP với `vec_mo_ta(hinh_en)`.
3. Bỏ ngay (không chấm): `la_kenh_loai`, `bi_chan`, `nham_lan.ten_bi_cam(tieu_de, nham_lan.tu_cam(mo_ta_chu_the))`,
   độ dài > 60 phút.
4. **Ghim nguồn** của câu trước cùng chủ thể đứng đầu danh sách.
5. Trả ngay danh sách thô (để giao diện hiện), rồi chấm từng video ở nền (4.5) và đẩy kết quả dần (giao diện hỏi lại 1 s/lần).

### 4.5 Chấm một video cho một câu (chỉ storyboard, không tải)
- `t, e, tong = xep_hang.storyboard(vid)`.
- Điểm khung với `vec_mo_ta(hinh_en)`; khoảng khớp = cửa sổ trượt ≥ độ dài nhịp, top 3 khoảng không chồng nhau
  (có thể dùng `dung_tay.khoang_khop(t, s, tong)`).
- Nhãn (mỗi khoảng): `chu_the` = điểm `nham_lan.vec_chu(mo_ta_chu_the)` trung bình (đạt `CO_CHU_THE` → ✓);
  `nham` = con dễ nhầm thắng (dùng cùng công thức `kho_nham` trên các khung trong khoảng); `con_la` (công thức `con_la`);
  `hanh_dong` nếu câu khớp `HANH_DONG_MANH` (so với `vec_tinh`); `ai` = `la_video_ai`; `cc` = `nguon_an_toan`.
- Thêm nhãn **"cảnh dựng / CGI"**: so điểm "a real documentary photograph" với "a movie scene with actors in costume" /
  "a 3D render" / "an AI generated image"; thua → ⚠ (đây là chỗ bắt cảnh người tiền sử dựng phim).
- Cache theo `(vid, canh_id, băm hinh_en)` trong `ban_dung.json["ung_vien"]`.
- **(Tuỳ chọn, mạnh)** Dò phụ đề: `yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format vtt` → tìm câu
  thuyết minh chứa từ khoá (wolf attack…) → cộng điểm khoảng giây đó. Cache theo `vid`.

### 4.6 Chuẩn bị trước
Khi người dùng mở câu N: luồng nền chạy `tim_cho_cau` + `cham_video` (5 video đầu) cho câu N+1…N+5 chưa có ứng viên.
Giới hạn: 1 luồng tìm, 3 luồng storyboard; huỷ khi người dùng nhảy xa (> 10 câu).

### 4.7 Endpoint mới (`may_chu.py`)
| Endpoint | Vào | Ra |
|---|---|---|
| `GET /ban_dung` | — | trang `ban_dung.html` |
| `GET /api/ban_dung/trang_thai?du_an=` | | toàn bộ `ban_dung.json` + danh sách câu (`tu_khoa.json`) + `dung.json` rút gọn |
| `POST /api/ban_dung/lap_canh` | `{du_an, lam_moi}` | `{job}` |
| `POST /api/ban_dung/luu_canh` | `{du_an, cau: {id: {...}}}` | `{ok}` — người dùng sửa bảng danh sách cảnh |
| `POST /api/ban_dung/tim` | `{du_an, canh_id, q, nguon, trang}` | `{ds: [...]}` (thô) |
| `GET /api/ban_dung/ung_vien?du_an=&canh_id=` | | `{ds: [... có khoang, nhan]}` (đã chấm tới đâu trả tới đó) |
| `GET /api/ban_dung/storyboard?vid=` | | `{anh: [url…], giay: [...], tong}` — lưu ảnh khung storyboard ra `cache/sb_anh/<vid>/` rồi `url_tep` |
| `POST /api/ban_dung/dung_khoang` | `{du_an, canh_id, nhip, vid, vao, ra}` | `{job}` → xong `{kid, url}` |
| `POST /api/ban_dung/dung_kho` | `{du_an, canh_id, nhip, kid, vao, ra}` | `{ok}` — dùng mảnh / tệp đã có |
| `POST /api/ban_dung/cach` | `{du_an, canh_id, cach}` | `{ok}` |
| `POST /api/ban_dung/xuat` | `{du_an, goc, ten, khoang: [[a,b]…]}` | `{job}` (mục 6) |

---

## 5. Độ tin cậy từng câu (để người dùng chỉ xem câu cần xem)

Tính khi mở bàn dựng (và sau mỗi lần gợi ý tự động), lưu `tin_cay`:
- 🔴 **đỏ**: câu `khong_quay_duoc` chưa có ảnh/Veo; câu chưa có hình; nhịp có footage dưới `goi_y.SAN_DIEM`.
- 🟡 **vàng**: footage có nhãn ⚠ (chủ thể < `CO_CHU_THE`, giống con dễ nhầm, con vật lạ, cảnh dựng), câu hành động mạnh,
  footage mượn kho chủ thể khác, điểm < 0,10.
- 🟢 **xanh**: còn lại, và mọi câu người dùng đã tự chọn trong bàn dựng.

Nút `J` / "câu cần xem tiếp theo" nhảy tới câu đỏ → vàng kế tiếp.

---

## 6. Xuất bản nháp — KHÔNG ghi đè

1. Người dùng chọn **bản nháp gốc** (bản đang sửa tay trong CapCut, ví dụ `chosoi_hoan_chinh`) và **tên mới**
   (mặc định `<gốc>_ban_dung_<HHMM>`). Nếu tên đã tồn tại → báo lỗi, không ghi.
2. Dựng bản tạm từ kế hoạch: `chinh_sua/dung_hoan_chinh.py --du-an <x> --ten <x>_tam_ban_dung` (không `--co-hook-veo`).
3. **Mở rộng `ghep_sau_moc.py`** thành ghép theo **danh sách khoảng** `[[a1,b1],[a2,b2]…]` = các câu người dùng đã chọn
   trong bàn dựng (mốc lấy từ `bat_dau`, `bat_dau+dai` của câu): trong bản sao của bản gốc, track `hinh` bỏ đoạn nằm trong
   các khoảng (đoạn vắt qua mép thì cắt ngắn tới mép), chép đoạn của bản tạm nằm trong các khoảng (vắt qua mép thì cắt
   `source_timerange` cho khớp). Các track khác giữ nguyên của bản gốc.
   Câu chọn 🖼/🎬: clip Veo / ảnh nằm ở track `hook` hoặc `hinh` tuỳ cách ✨ dựng — kiểm tra trong bản tạm và chép đúng track.
4. Kiểm tra sau ghép (tự động, in ra): đoạn ngoài các khoảng giống hệt bản gốc; không chồng lấn trên `hinh`; mọi
   `material_id` / `extra_material_refs` có trong `materials`; ghi cả `draft_content.json` gốc và
   `Timelines/*/draft_content.json`; `draft_meta_info.json` có `draft_id` mới.
5. Cảnh báo nếu bản gốc đang mở trong CapCut (thời gian sửa `draft_content.json` < 2 phút trước) — đề nghị lưu/đóng trước.

---

## 7. Giai đoạn làm & tiêu chí nghiệm thu

### Giai đoạn 1 — Bàn dựng cơ bản + footage tự tìm / tự dán (ưu tiên cao nhất)
- Trang `ban_dung.html` với danh sách câu, nghe lời đọc, 3 cách.
- Footage: ô từ khoá tự gõ, **dán link YouTube**, chọn mảnh trong kho, danh sách ứng viên có dải storyboard,
  trình phát YouTube nhúng, đặt vào/ra, **tải đúng khoảng**, đặt vào nhịp, ghi `dung.json`.
- Ẩn video nhãn AI.
- ✅ Nghiệm thu: với dự án `chosoi`, chọn tay footage cho 5 câu (có 1 câu không chủ thể) bằng link tự dán, mỗi lần
  "Dùng" xong < 30 s; `dung.json` có đúng 5 câu `ban_dung: true`; ✨ dựng ra bản nháp có đúng các khoảng đó.

### Giai đoạn 2 — Gợi ý thông minh trước khi tải
- Danh sách cảnh AI (quay được / không quay được, từ khoá, bắt buộc / cấm) + bảng duyệt chữ.
- Chấm storyboard + nhãn kiểm tra (chủ thể, dễ nhầm, con lạ, hành động, cảnh dựng, AI, CC); khoảng khớp tô màu.
- Ảnh AI / Veo trong cùng bảng.
- ✅ Nghiệm thu: câu "sói lao vào tấn công" — 8 ứng viên đầu không có video nhãn AI, mỗi ứng viên có nhãn; video husky /
  phim người tiền sử bị gắn ⚠ hoặc bị lọc trước.

### Giai đoạn 3 — Tốc độ
- Chuẩn bị trước 5 câu, phím tắt đầy đủ, ghim nguồn, "Lấp cả câu từ khoảng này".
- Độ tin cậy 🟢🟡🔴 + nút câu cần xem tiếp theo.
- ✅ Nghiệm thu: chuyển sang câu kế tiếp đã có ứng viên chấm sẵn (không phải chờ) trong ≥ 4/5 lần.

### Giai đoạn 4 — Xuất không ghi đè
- `ghep_sau_moc.py` ghép theo danh sách khoảng + endpoint `xuat`.
- ✅ Nghiệm thu: xuất từ `chosoi_hoan_chinh` → bản mới; so sánh tự động cho thấy ngoài các câu đã chọn mọi đoạn giống hệt;
  bản gốc không đổi thời gian sửa.

### Giai đoạn 5 (tuỳ chọn)
- Dò phụ đề YouTube để định vị khoảng giây.
- "Tìm bằng hình": chọn một khung ưng ý → xếp ứng viên theo độ giống ảnh (SigLIP ảnh–ảnh).
- Học từ ✓/✗: khung bị ✗ thành mẫu xấu (loại khung giống), kênh bị ✗ ≥ 3 lần vào danh sách chặn.

---

## 8. Bẫy đã biết (đọc kỹ)

- **Storyboard YouTube thưa** (1 ảnh / vài giây) → khoảng khớp chỉ gần đúng; điểm vào/ra chính xác do người dùng chỉnh
  khi xem trực tiếp.
- **Video chặn nhúng** (lỗi IFrame 101/150) → luôn có đường dự phòng: dải storyboard + mở tab YouTube + gõ tay giây.
- **`--download-sections` cần ffmpeg** và `--force-keyframes-at-cuts` để không đen đầu; kiểm tra khoảng tải ra đúng giây
  (lệch keyframe) bằng `ffprobe`.
- **Cookies YouTube** (`cookies.txt`) đã được dùng ở các lệnh yt-dlp hiện có — dùng lại đúng cách, không in cookies ra log.
- **Không ghi đè** bất kỳ thư mục bản nháp CapCut nào đã tồn tại; không sửa `dung.json` của câu người dùng đã dựng tay
  ngoài bàn dựng (`goi_y` false và không `ban_dung`) trừ khi người dùng bấm vào câu đó.
- **Hai bản nội dung CapCut**: bản nháp có 2 bản `draft_content.json` (gốc + `Timelines/<id>/`) — phải ghi cả hai.
- **Kiểm duyệt Flow**: ảnh/video có thể bị gỡ SAU khi tạo ("violate our policies") — không có link tải; báo rõ, gợi ý
  viết nhẹ (không xác, máu, con vật bất động).
- **Đặc điểm bắt buộc**: đừng tự chế lại logic — mọi câu lệnh ảnh/video đi qua `anh_ve.ve_prompt` / `flow_video.tao` đã
  được `common.giu_dac_diem` gắn đặc điểm theo `ho_so_truyen.json`.
- **Chrome Flow / Gemini tự đóng khi rảnh** (`flow_ve._dong_khi_ranh`, `gemini_chrome.don_chrome_ranh`) — không mở
  Chrome riêng ngoài các hàm này.
- Máy chủ chạy đa luồng (`ThreadingMixIn`): mọi ghi `ban_dung.json` / `dung.json` / `kho` phải qua khoá
  (`dung_tay._KHOA` cho kho/dung).
- Sau khi sửa code Python của máy chủ phải khởi động lại máy chủ.

---

## 9. Kiểm thử gợi ý

- `python -X utf8 -c "import ban_dung; ..."`: gọi `tim_cho_cau('chosoi', 48, 'wolf attack sheep')`, `cham_video(...)` với
  một video sói thật và một video husky → nhãn đúng.
- Tải khoảng: `tai_khoang('chosoi', '<vid>', 812.0, 818.0)` → tệp ~10 s, `ffprobe` độ dài 9–11 s, < 20 s thời gian.
- Ghép: chạy `ghep_sau_moc.py` mở rộng trên bản sao của `chosoi_hoan_chinh` với 2 khoảng → script kiểm tra mục 6.4 in OK.
- Giao diện: mở `/ban_dung?du_an=chosoi`, đi 10 câu bằng phím tắt, không lỗi console.
