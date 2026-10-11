# -*- coding: utf-8 -*-
"""Tìm ẢNH bằng Chrome THẬT (không cần key): mở Bing Images trong Chrome với hồ sơ RIÊNG của công cụ rồi đọc kết quả.

  * Hồ sơ nằm ở %LOCALAPPDATA%\\CapCutTTS\\bc_chrome\\p<N> — KHÔNG đụng vào hồ sơ Chrome hằng ngày của người dùng
    (không đăng nhập, không cookie cá nhân).
  * Chrome thật (chế độ headless mới) có dấu vân tay bình thường nên ít bị chặn hơn bản headless-shell.
  * Chạy song song tối đa LUONG_TOI_DA tiến trình, mỗi tiến trình một hồ sơ riêng (Chrome khoá hồ sơ).
  * Kết quả lưu cache theo từ khoá ở tim_nguon (khoá "anh:<từ khoá>"), nên mỗi từ khoá chỉ tìm một lần."""
import glob
import hashlib
import html
import json
import os
import queue
import random
import re
import subprocess
import threading
import time
import urllib.parse

from common import log

LUONG_TOI_DA = 4
_HOSO = None
_KHOA = threading.Lock()


def _chrome():
    cho = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
           os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
           r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    for p in cho:
        if os.path.isfile(p):
            return p
    g = glob.glob(r"D:\CapCutTTS\hoat_hinh_remotion\node_modules\.remotion\**\chrome-headless-shell.exe", recursive=True)
    return g[0] if g else None


def _hang_hoso():
    """Hàng đợi thư mục hồ sơ: mỗi lần tìm lấy một hồ sơ rảnh (Chrome không cho hai tiến trình dùng chung một hồ sơ)."""
    global _HOSO
    with _KHOA:
        if _HOSO is None:
            goc = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CapCutTTS", "bc_chrome")
            _HOSO = queue.Queue()
            for i in range(LUONG_TOI_DA):
                d = os.path.join(goc, f"p{i}")
                os.makedirs(d, exist_ok=True)
                _HOSO.put(d)
    return _HOSO


def _doc_ket_qua(h, n):
    """Danh sách {url, thumb, tieu_de, w, h} từ HTML trang Bing Images."""
    ra, seen = [], set()
    for m in re.finditer(r'class="iusc"[^>]*?\sm="([^"]+)"', h):
        try:
            j = json.loads(html.unescape(m.group(1)))
        except ValueError:
            continue
        u = j.get("murl")
        if not u or u in seen or not u.lower().startswith("http"):
            continue
        seen.add(u)
        ra.append({"url": u, "thumb": j.get("turl", ""), "tieu_de": j.get("t", "") or j.get("desc", ""),
                   "kenh": urllib.parse.urlparse(u).netloc})
        if len(ra) >= n:
            break
    return ra


def bing_anh(q, n=8, timeout=60):
    """Tìm ảnh cho từ khoá q. Trả [] nếu bị chặn/không có (kèm log) — không bao giờ ném lỗi."""
    exe = _chrome()
    if not exe:
        return []
    url = "https://www.bing.com/images/search?" + urllib.parse.urlencode({"q": q, "form": "HDRSC2", "first": "1"})
    hang = _hang_hoso()
    hs = hang.get()
    try:
        time.sleep(random.uniform(0.2, 0.9))              # giãn cách nhẹ cho giống người dùng thật
        lenh = [exe, "--headless=new", f"--user-data-dir={hs}", "--no-first-run", "--no-default-browser-check",
                "--disable-gpu", "--mute-audio", "--lang=en-US", "--dump-dom", "--virtual-time-budget=6000", url]
        p = subprocess.run(lenh, capture_output=True, timeout=timeout,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        h = p.stdout.decode("utf-8", "ignore")
        kq = _doc_ket_qua(h, n)
        if not kq and ("captcha" in h.lower() or "unusual traffic" in h.lower()):
            log(f"    ! Bing chặn (captcha) ở từ khoá '{q[:40]}'")
        return kq
    except (subprocess.SubprocessError, OSError) as e:
        log(f"    ! trình duyệt lỗi ở '{q[:40]}': {str(e)[:80]}")
        return []
    finally:
        hang.put(hs)


def ung_vien(q, n=8):
    """Mục kho ảnh (cùng khuôn kho_web): id, tieu_de, url, nguon, giay_phep."""
    ra = []
    for r in bing_anh(q, n):
        ra.append({"id": "bg_" + hashlib.md5(r["url"].encode()).hexdigest()[:14], "tieu_de": r["tieu_de"][:100],
                   "url": r["url"], "nguon": "bing", "giay_phep": "", "kenh": r["kenh"], "thumb": r["thumb"]})
    return ra
