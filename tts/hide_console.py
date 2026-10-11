# -*- coding: utf-8 -*-
"""hide_console.py — ẩn cửa sổ console đen của MỌI tiến trình con trên Windows.

App/worker chạy bằng pythonw (hoặc được GUI khởi động với CREATE_NO_WINDOW nên KHÔNG
có console). Khi đó mỗi tiến trình con kiểu console (ffmpeg / ffprobe / yt-dlp / python…)
sẽ TỰ bung một cửa sổ đen mới nếu không đặt CREATE_NO_WINDOW — chạy vòng lặp gọi ffmpeg
hàng nghìn lần (vd lồng tiếng từng clip) thì loạn hết màn hình.

Import module này MỘT LẦN ở đầu mỗi tiến trình -> mọi subprocess.Popen/run sau đó tự thêm
cờ ẩn. Idempotent (đánh dấu subprocess._no_window_patched) nên import/patch nhiều lần cũng
chỉ vá đúng một lần; cờ creationflags cũ (nếu caller tự truyền) vẫn được giữ, chỉ OR thêm.
"""
import os
import subprocess

if os.name == "nt" and not getattr(subprocess, "_no_window_patched", False):
    _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    _orig_popen, _orig_run = subprocess.Popen, subprocess.run

    def _with_no_window(k):
        k["creationflags"] = k.get("creationflags", 0) | _NO_WINDOW
        return k

    class _PopenNoWindow(_orig_popen):      # giữ isinstance(x, subprocess.Popen)
        def __init__(self, *a, **k):
            super().__init__(*a, **_with_no_window(k))

    def _run_no_window(*a, **k):
        return _orig_run(*a, **_with_no_window(k))

    subprocess.Popen = _PopenNoWindow
    subprocess.run = _run_no_window
    subprocess._no_window_patched = True
