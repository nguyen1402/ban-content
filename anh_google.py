# -*- coding: utf-8 -*-
"""Tìm ẢNH trên Google Images bằng Chrome HIỆN CỬA SỔ (không chạy ngầm — Google chặn Chrome headless bằng captcha).

  * Chrome mở với hồ sơ RIÊNG %LOCALAPPDATA%\\CapCutTTS\\bc_chrome\\google (Chrome không cho điều khiển hồ sơ hằng
    ngày của người dùng qua DevTools) và cổng DevTools CONG. Mở một lần, các lần tìm sau dùng lại cửa sổ đó.
  * Mỗi lần tìm: chuyển tab sang trang google.com/search?udm=2, chờ trang hiện ảnh, đọc HTML, tách
    [ảnh thu nhỏ, ảnh gốc, trang nguồn, tiêu đề]. Tìm tuần tự (một tab), không dồn nhiều truy vấn cùng lúc.
  * Google hỏi captcha thì KHÔNG tự giải: đưa cửa sổ lên trước, chờ người dùng tự bấm giải (tối đa CHO_CAPTCHA giây).
  * Websocket DevTools viết bằng thư viện chuẩn (không cài thêm gói)."""
import base64
import json
import os
import re
import socket
import struct
import subprocess
import threading
import time
import urllib.parse
import urllib.request

from common import log

CONG = int(os.environ.get("BC_CHROME_CONG", "9333"))
CHO_CAPTCHA = 120
_KHOA = threading.Lock()


class _WS:
    """Websocket tối thiểu cho DevTools (chỉ khung chữ, đủ cho Runtime.evaluate/Page.navigate)."""

    def __init__(self, url):
        u = urllib.parse.urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        h = b""
        while b"\r\n\r\n" not in h:
            c = self.s.recv(1)
            if not c:
                raise ConnectionError("DevTools đóng kết nối")
            h += c
        if b" 101 " not in h.split(b"\r\n", 1)[0]:
            raise ConnectionError("DevTools từ chối websocket")
        self.n = 0

    def _doc(self, k):
        b = b""
        while len(b) < k:
            c = self.s.recv(k - len(b))
            if not c:
                raise ConnectionError("DevTools đóng kết nối")
            b += c
        return b

    def _nhan(self):
        buf = b""
        while True:
            b0, b1 = self._doc(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._doc(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._doc(8))[0]
            buf += self._doc(n)
            if b0 & 0x80:
                return buf.decode("utf-8", "ignore")

    def goi(self, method, **params):
        self.n += 1
        d = json.dumps({"id": self.n, "method": method, "params": params}).encode()
        m = os.urandom(4)
        n = len(d)
        hd = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else
                              bytes([0xFE]) + struct.pack(">H", n) if n < 65536 else bytes([0xFF]) + struct.pack(">Q", n))
        self.s.sendall(hd + m + bytes(x ^ m[i % 4] for i, x in enumerate(d)))
        while True:
            r = json.loads(self._nhan())
            if r.get("id") == self.n:
                if "error" in r:
                    raise RuntimeError(str(r["error"])[:200])
                return r.get("result", {})

    def js(self, bieu_thuc):
        r = self.goi("Runtime.evaluate", expression=bieu_thuc, returnByValue=True)
        return (r.get("result") or {}).get("value")

    def dong(self):
        try:
            self.s.close()
        except OSError:
            pass


def _ds_tab():
    try:
        return json.load(urllib.request.urlopen(f"http://127.0.0.1:{CONG}/json", timeout=2))
    except (OSError, ValueError):
        return None


def _mo_chrome(url):
    import anh_trinh_duyet
    exe = anh_trinh_duyet._chrome()                               # noqa: SLF001
    if not exe:
        raise ValueError("không tìm thấy Chrome/Edge trên máy")
    hs = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CapCutTTS", "bc_chrome", "google")
    os.makedirs(hs, exist_ok=True)
    subprocess.Popen([exe, f"--user-data-dir={hs}", f"--remote-debugging-port={CONG}", "--no-first-run",
                      "--no-default-browser-check", "--window-size=1150,850",
                      # 15/10: bộ tìm stock mở 10 tab cùng lúc — tab nền không bị Chrome hãm (trang tải đủ khi không hiện)
                      "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                      "--disable-backgrounding-occluded-windows", url])
    for _ in range(60):
        time.sleep(0.5)
        if _tab_trang(_ds_tab()):
            return
    raise ValueError("mở Chrome tìm ảnh không được (cổng DevTools không trả lời)")


def _tab_trang(ds):
    return next((t for t in ds or [] if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)


def _str(s):
    try:
        return json.loads('"' + s + '"')
    except ValueError:
        return s


_MAU = re.compile(r'\["(https://encrypted-tbn[^"]+)",(\d+),(\d+)\],\["(https?://[^"]+)",(\d+),(\d+)\]'
                  r'(?:(?!\["https://encrypted-tbn).){0,600}?"2003":\[null,"[^"]*","(https?://[^"]+)","((?:[^"\\]|\\.)*)"', re.S)


def doc_ket_qua(h, n):
    """[{url, thumb, tieu_de, kenh, trang, rong, cao}] từ HTML trang Google Images (udm=2)."""
    ra, seen = [], set()
    for m in _MAU.finditer(h):
        thumb, url, cao, rong, trang, td = _str(m.group(1)), _str(m.group(4)), int(m.group(5)), int(m.group(6)), _str(m.group(7)), _str(m.group(8))
        if url in seen:
            continue
        seen.add(url)
        ra.append({"url": url, "thumb": thumb, "tieu_de": td, "kenh": urllib.parse.urlparse(trang).netloc,
                   "trang": trang, "rong": rong, "cao": cao})
        if len(ra) >= n:
            break
    return ra


def google_anh(q, n=40, timeout=25):
    """Tìm ảnh cho từ khoá q trên Google Images. Ném ValueError (thông báo cho người dùng) khi không tìm được."""
    url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "udm": "2", "hl": "vi"})
    with _KHOA:
        tab = _tab_trang(_ds_tab())
        if not tab:
            _mo_chrome(url)
            tab = _tab_trang(_ds_tab())
            moi = True
        else:
            moi = False
        ws = _WS(tab["webSocketDebuggerUrl"])
        try:
            if not moi:
                ws.goi("Page.navigate", url=url)
                time.sleep(0.8)
            het = time.time() + timeout
            bao_captcha = False
            while True:
                tt = ws.js("[location.href, document.readyState, document.querySelectorAll('img').length]") or ["", "", 0]
                if "/sorry/" in tt[0]:
                    if not bao_captcha:
                        log("    ! Google hỏi captcha — giải trong cửa sổ Chrome tìm ảnh")
                        ws.goi("Page.bringToFront")
                        bao_captcha = True
                        het = time.time() + CHO_CAPTCHA
                elif tt[1] == "complete" and tt[2] >= 20:
                    time.sleep(0.6)
                    break
                if time.time() > het:
                    if bao_captcha:
                        raise ValueError("Google đang hỏi captcha — bấm giải trong cửa sổ Chrome tìm ảnh rồi Tìm lại")
                    break
                time.sleep(0.4)
            h = ws.js("document.documentElement.outerHTML") or ""
        finally:
            ws.dong()
    kq = doc_ket_qua(h, n)
    if not kq:
        log(f"    ! Google Images không ra ảnh cho '{q[:40]}'")
    return kq


_JS_VIDEO = r"""(() => [...document.querySelectorAll('[data-curl]')].map(e => {
    let c = e; for (let i = 0; i < 8 && c.parentElement; i++) { c = c.parentElement;
        if (c.innerText && c.innerText.length > 40 && c.querySelector('h3,[role=heading]')) break }
    return [e.getAttribute('data-curl') || '', c.innerText || ''] }))()"""


def _giay(s):
    p = [int(x) for x in s.split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def google_video(q, n=10, timeout=25):
    """15/10 user: tìm thêm ở Google Videos (udm=7) — nhiều cảnh sát nội dung hơn kho stock. Chỉ lấy kết quả YouTube
    (bước chấm storyboard + tải ≤720p dùng id YouTube): [{id, tieu_de, dai, kenh, luot_xem}] như dung_tay.tim_youtube."""
    url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": q, "udm": "7", "hl": "en"})
    with _KHOA:
        tab = _tab_trang(_ds_tab())
        moi = not tab
        if moi:
            _mo_chrome(url)
            tab = _tab_trang(_ds_tab())
        ws = _WS(tab["webSocketDebuggerUrl"])
        try:
            if not moi:
                ws.goi("Page.navigate", url=url)
                time.sleep(0.8)
            het = time.time() + timeout
            bao_captcha = False
            while True:
                tt = ws.js("[location.href, document.readyState, document.querySelectorAll('[data-curl]').length]") or ["", "", 0]
                if "/sorry/" in tt[0]:
                    if not bao_captcha:
                        log("    ! Google hỏi captcha — giải trong cửa sổ Chrome tìm ảnh")
                        ws.goi("Page.bringToFront")
                        bao_captcha = True
                        het = time.time() + CHO_CAPTCHA
                elif tt[1] == "complete" and tt[2] >= 1:
                    time.sleep(0.6)
                    break
                if time.time() > het:
                    break
                time.sleep(0.4)
            the = ws.js(_JS_VIDEO) or []
        finally:
            ws.dong()
    ra, seen = [], set()
    for u, txt in the:
        m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})", u)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        dong = [x.strip() for x in txt.splitlines() if x.strip()]
        dai = next((_giay(x) for x in dong if re.fullmatch(r"\d{1,2}(?::\d{2}){1,2}", x)), 0)
        kenh = next((x.split("·")[1].strip() for x in dong if x.startswith("YouTube ·") and x.count("·") >= 1), "")
        ra.append({"id": m.group(1), "tieu_de": dong[0] if dong else "", "dai": dai, "kenh": kenh, "luot_xem": 0,
                   "nguon_tim": "google_video"})
        if len(ra) >= n:
            break
    return ra
