# Bản Content

Kịch bản tiếng Việt → tách cảnh → giọng đọc OmniVoice + từ khoá tìm nguồn (ChatGPT) → bản nháp CapCut chỉ có giọng.
Video, ảnh, bản đồ bạn tự tìm theo từ khoá rồi ghép trong CapCut.

Kết quả mỗi dự án nằm ở `ra/<dự án>/`:

| File | Nội dung |
|---|---|
| `tu_khoa.md`, `tu_khoa.json` | Từng cảnh: nên chiếu gì, từ khoá tìm video/ảnh/bản đồ (kèm link Google Maps) |
| `giong_doc.wav` | Giọng đọc cả kịch bản, đúng mốc thời gian |
| `kich_ban.srt` | Phụ đề theo cảnh |
| `video_tai/` | Video tải từ link YouTube bạn dán |
| Bản nháp CapCut | Ghi thẳng vào thư mục CapCut Drafts, chỉ có track giọng |

---

## Dựng lại sau khi clone

Máy cần: Windows, card NVIDIA (OmniVoice chạy GPU), Python 3.13 (Miniconda), Node.js, CapCut bản PC.

### 1. Lấy code

```bash
git clone https://github.com/nguyen1402/ban-content.git D:\CapCutTTS\bán-content
cd D:\CapCutTTS\bán-content
```

Thư mục `voices/` có sẵn trong repo (các file giọng mẫu `.wav`; file `.omni.pt` đi kèm là bộ nhớ đệm giọng, hỏng thì tự tạo lại).

### 2. Python chính (giao diện + quy trình)

```bash
pip install -r requirements.txt
```

### 3. Env riêng cho OmniVoice (đọc giọng)

```bash
python -m venv D:\CapCutTTS\omnivoice-env
D:\CapCutTTS\omnivoice-env\Scripts\pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
D:\CapCutTTS\omnivoice-env\Scripts\pip install -r requirements-omnivoice.txt
```

Lần đọc đầu tiên OmniVoice tự tải model `k2-fsa/OmniVoice` từ Hugging Face (vài GB).
Đặt env ở chỗ khác thì khai báo đường dẫn: `set BC_OMNI_PY=E:\duong\dan\python.exe`.

### 4. ffmpeg và yt-dlp

- **ffmpeg**: chép `ffmpeg.exe` vào `C:\yt-dlp\` (mặc định), hoặc để trong PATH, hoặc `set BC_FFMPEG=<đường dẫn>`.
- **yt-dlp** (cho mục "Tải video từ link"): tải `yt-dlp.exe` bản mới nhất từ
  https://github.com/yt-dlp/yt-dlp/releases vào `tools\yt-dlp.exe`. Cần Node.js trong PATH (yt-dlp dùng để giải
  mã YouTube, thiếu thì bị lỗi 403).

### 5. Cookie ChatGPT (để hỏi từ khoá)

Công cụ hỏi ChatGPT bằng **cookie đăng nhập**, không dùng key API. Kho cookie dùng chung với CapCut TTS Studio,
nằm NGOÀI repo ở `%LOCALAPPDATA%\CapCutTTS\chatgpt_cookies.json`. Thêm/làm mới cookie bằng CapCut TTS Studio.
Nhiều tài khoản thì mỗi tài khoản một luồng, chạy song song.

### 6. Chạy

Bấm đúp `mo_giao_dien.bat` rồi mở http://127.0.0.1:8777 (cổng bận thì tự sang cổng kế tiếp, xem cửa sổ đen).

Hoặc chạy dòng lệnh:

```bash
python chay.py kich_ban\ten_du_an.txt --du-an ten_du_an --ten "Tên bản nháp" --giong-clip "voices\Tự tin.wav" --num-step 32
```

---

## 🎨 Tạo hàng loạt ảnh bằng Google Flow (Nano Banana, 0 điểm)

Hỗ trợ nhập nhiều câu lệnh tạo ảnh và chạy script tự động vẽ hàng loạt ảnh, xoay vòng các hồ sơ Chrome Flow (0 credit).

- **Trên giao diện Web**: Bấm nút **🖼️ Tạo hàng loạt ảnh Flow** ở thanh điều hướng trên cùng (hoặc mở thẻ `🎨 Hồ sơ Flow`):
  - Dán danh sách câu prompt (mỗi dòng một câu, hoặc cú pháp `tên_file: câu lệnh`).
  - Hoặc bấm **📄 Nạp từ file (.txt)**, hoặc **💡 Lấy từ kịch bản dự án** để tự động lấy toàn bộ mô tả cảnh của kịch bản đang chọn.
  - Chọn tỉ lệ ảnh (`16:9`, `9:16`, `1:1`, `4:3`, `3:4`), phong cách gợi ý (Điện ảnh, Hoạt hình, Tách nền trắng...), thư mục lưu ảnh.
  - Bấm **▶ Bắt đầu tạo hàng loạt**: hiển thị thanh tiến độ %, thẻ ảnh xem trước tức thì (bấm xem full HD / tải về), nút dừng và nút chạy lại câu lỗi.
- **Bằng dòng lệnh (script CLI)**:
  ```bash
  # Vẽ từ file text danh sách prompt
  python flow_hang_loat.py danh_sach.txt --ti-le 16:9 --thu ra/anh_flow

  # Hoặc truyền trực tiếp câu prompt
  python flow_hang_loat.py --prompts "chú mèo ngồi ngắm mưa\nphi thuyền không gian" --ti-le 16:9
  ```

---

## Trình dựng + tự động tìm hình (nút 🤖) + skill hoàn thiện

Sau khi `chay.py` xong, nút "🎬 Mở trình dựng tay" (http://127.0.0.1:8777/dung?du_an=<dự án>):

- **Tìm video** (YouTube, xếp theo độ khớp SigLIP chấm trên storyboard, có "khớp nhất ở phút…") và **tìm ảnh**
  (Google Images qua cửa sổ Chrome hiện — Google hỏi captcha thì tự giải; ảnh có chữ bị đánh dấu). Bấm mới tải.
- **🤖 Tự tìm + tải + khớp + bản nháp** (`tu_dong_tim.py`): hỏi ChatGPT mô tả khung hình từng cảnh → tìm video
  stock SẠCH Pexels/Pixabay + YouTube theo nhóm cảnh → chọn theo NGÂN SÁCH phút tải → khớp đoạn (cắt theo cảnh quay
  nguồn và theo chỗ ngắt nghỉ của giọng đọc) → ảnh Google bù chỗ trống → bản nháp CapCut, đoạn trỏ VIDEO GỐC.
- **Skill hoàn thiện** (`chinh_sua/dung_hoan_chinh.py`, tài liệu `skill/chinh-sua-video-tho/SKILL.md`): bản đồ vệ
  tinh khoanh vùng / đường đi A→B (Remotion, `remotion/`), khung highlight viền vàng, phủ màu đổi chương, thẻ ảnh phủ,
  chuyển cảnh (khung highlight viền vàng đã tắt; thẻ ảnh highlight 65% kèm chữ nhấn mạnh). Chạy bằng lệnh hoặc nút
  **✨ Hoàn thiện bản nháp** trong trình dựng (log `ra/<dự án>/hoan_thien.log`). Remotion: `cd remotion && npm install` một lần.
- Cần thêm: torch (CUDA) + `transformers` + `rapidocr` (đã ghi trong `requirements.txt`); onnxruntime-gpu 1.22.0
  (bản CUDA 12) cài riêng: `pip install onnxruntime-gpu==1.22.0 --target ort_gpu`. Model SigLIP
  `google/siglip2-so400m-patch16-256` (~4,3 GB) tự tải lần đầu.

## Ghi chú

- **Số dài**: OmniVoice tự nuốt "trăm/mươi/nghìn" khi đọc số dài. Trước khi đọc, `tts/tach_so.py` đổi chữ số ra chữ
  và nối gạch cụm số ("hai-mươi-tám-nghìn-ba-trăm-bảy-mươi-sáu") — chỉ ở bản đưa vào máy đọc, kịch bản giữ nguyên.
- **Không** sửa chính tả, **không** "nói giảm nói tránh" khi đọc giọng.
- Giọng đã đọc lưu theo cảnh trong `cache/`; cảnh nào đổi chữ thì tự đọc lại khi chạy.
- Thêm giọng mới: nút "+ Thêm giọng" (file 5–10 giây, một người nói, không nhạc nền).
- Bản cũ tự tìm + chấm + ghép video vẫn ở `chay_ghep_tu_dong.py` (cần thêm `requirements-ghep-cu.txt`).
- Không đưa lên git: `cache/`, `ra/`, `kich_ban/`, `tools/`, `ort_gpu/`, `remotion/node_modules/`, log.
