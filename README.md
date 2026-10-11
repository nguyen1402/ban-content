# bán-content

Kịch bản (tiếng Việt) -> tìm hình/video minh họa -> ghép khớp lời -> bản nháp CapCut.

## Cài đặt
- Python 3.13, `pip install -r requirements.txt`
- Bước tách cảnh / đặt từ khóa dùng ChatGPT bằng COOKIE (không dùng key API): đọc kho cookie dùng chung
  của máy ở thư mục `CapCutTTS` trong `%LOCALAPPDATA%` (nằm ngoài repo; cần `pip install curl_cffi`).
- Giọng đọc: OmniVoice, env `D:\CapCutTTS\omnivoice-env`, clip mẫu `voices/Tự tin.wav`.
- `common.py` trỏ tới `C:\yt-dlp\yt-dlp.exe` và `ffmpeg.exe`; đổi nếu để chỗ khác.

## Chạy
    python chay.py kichbantest.txt --gioi-han 12 --ten "Test"

Kết quả: `ra/bao_cao.md`, `ra/kich_ban.srt`, bản nháp trong thư mục CapCut Drafts.

## Trạng thái
Tải video YouTube đang bị 403 (yt-dlp cũ); ô nào không có hình thì được lấp bằng ảnh
Wikimedia Commons hoặc thẻ "THIEU HINH".
