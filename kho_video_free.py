# -*- coding: utf-8 -*-
"""Tìm VIDEO STOCK MIỄN PHÍ, KHÔNG WATERMARK/LOGO trên Pexels và Pixabay — mở trang tìm trong cửa sổ Chrome hiện
(cùng hạ tầng DevTools với anh_google: hồ sơ riêng, không cần API key), đọc JSON-LD VideoObject trong trang.

  * Pexels: link file mp4 trực tiếp (sd 960x540 / hd 1280x720 / hd 1920x1080 / uhd) -> lấy bản hd <= 1080p.
  * Pixabay: link xem trước _tiny.mp4; bản 1280x720 là _medium.mp4, 1920x1080 là _large.mp4 (cùng đường dẫn).
  * Giấy phép: cả hai cho dùng thương mại, không bắt ghi nguồn (Pexels License / Pixabay Content License).
  * Pixabay trả kết quả lỏng (tìm "sea urchin" ra cả "bàn chân trên cát") -> luôn chấm lại bằng SigLIP.
Kết quả: [{nguon, id, ten, trang, thumb, file, dai}] (chưa tải)."""
import json
import os
import re
import time
import urllib.parse

from common import CACHE_CHUNG, doc_json, ghi_json, log

_CACHE = os.path.join(CACHE_CHUNG, "tim_video_free.json")


def _mo_trang(url, cho=7.0, cuon=2):
    """HTML của trang sau khi tải xong + cuộn vài lần (dùng chung tab Chrome với anh_google, tuần tự)."""
    import anh_google as g
    with g._KHOA:                                            # noqa: SLF001
        tab = g._tab_trang(g._ds_tab())                      # noqa: SLF001
        if not tab:
            g._mo_chrome(url)                                # noqa: SLF001
            tab = g._tab_trang(g._ds_tab())                  # noqa: SLF001
        ws = g._WS(tab["webSocketDebuggerUrl"])              # noqa: SLF001
        try:
            ws.goi("Page.navigate", url=url)
            het = time.time() + cho
            while time.time() < het:
                time.sleep(0.8)
                if ws.js("document.readyState") == "complete" and ws.js("document.querySelectorAll('script[type=\"application/ld+json\"]').length"):
                    break
            for _ in range(cuon):
                ws.js("window.scrollBy(0, 2500)")
                time.sleep(1.2)
            return ws.js("document.documentElement.outerHTML") or ""
        finally:
            ws.dong()


def _ld(h):
    ra = []
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S):
        try:
            ra.append(json.loads(m.group(1)))
        except ValueError:
            continue
    return ra


def _video_objects(x):
    if isinstance(x, dict):
        if x.get("@type") == "VideoObject":
            yield x
        for v in x.values():
            yield from _video_objects(v)
    elif isinstance(x, list):
        for v in x:
            yield from _video_objects(v)


def _giay(d):
    m = re.match(r"P?T(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", str(d or ""))
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0)) if m else 0.0


def tim_pexels(q):
    """Đọc __NEXT_DATA__ của trang (JSON-LD chỉ có ở một số từ khoá): mỗi video có tiêu đề, kích thước, ảnh thu nhỏ,
    danh sách file theo độ phân giải. Chỉ lấy video NGANG, file 1920x1080 (không có thì 1280x720)."""
    h = _mo_trang(f"https://www.pexels.com/search/videos/{urllib.parse.quote(q)}/")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    try:
        data = json.loads(m.group(1))["props"]["pageProps"]["initialData"]["data"] if m else []
    except (ValueError, KeyError, TypeError):
        data = []
    ra = []
    for it in data:
        a = it.get("attributes") or {}
        v = a.get("video") or {}
        if not v or (a.get("width") or 0) <= (a.get("height") or 0):
            continue
        fs = [f for f in v.get("video_files") or [] if (f.get("width") or 0) > (f.get("height") or 0)]
        tot = sorted(fs, key=lambda f: (f.get("width") != 1920, f.get("width") != 1280, -(f.get("width") or 0)))
        if not tot:
            continue
        th = v.get("thumbnail") or {}
        ra.append({"nguon": "pexels", "id": f"px_{a.get('id')}", "ten": a.get("title") or a.get("description") or "",
                   "trang": f"https://www.pexels.com/video/{a.get('slug', '')}-{a.get('id')}/",
                   "thumb": th.get("medium") or th.get("large") or th.get("small") or "",
                   "file": tot[0]["link"], "dai": float(a.get("duration") or v.get("duration") or 0)})
    return ra


def tim_pixabay(q):
    h = _mo_trang(f"https://pixabay.com/videos/search/{urllib.parse.quote(q)}/")
    ra, thay = [], set()
    for o in (v for x in _ld(h) for v in _video_objects(x)):
        u = o.get("contentUrl", "")
        m = re.search(r"/(\d+)(?:-\d+)?_tiny\.mp4$", u)
        if not m or m.group(1) in thay:
            continue
        thay.add(m.group(1))
        trang = o.get("acquireLicensePage", "")
        ra.append({"nguon": "pixabay", "id": "pb_" + m.group(1), "ten": o.get("name", ""),
                   "trang": urllib.parse.urljoin("https://pixabay.com", trang), "thumb": o.get("thumbnailUrl", ""),
                   "file": u.replace("_tiny.mp4", "_large.mp4"), "file_nho": u.replace("_tiny.mp4", "_medium.mp4"),
                   "dai": _giay(o.get("duration"))})
    return ra


def tim(q, nguon=("pexels", "pixabay")):
    """Kết quả cả hai kho cho từ khoá q (cache 7 ngày)."""
    da = doc_json(_CACHE, {}) or {}
    ra = []
    for n in nguon:
        k = f"{n}|{q.strip().lower()}"
        if k in da and time.time() - da[k]["luc"] < 7 * 86400:
            ra += da[k]["ds"]
            continue
        try:
            ds = tim_pexels(q) if n == "pexels" else tim_pixabay(q)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! tìm {n} '{q[:40]}': {str(e)[:100]}")
            ds = []
        da = doc_json(_CACHE, {}) or {}
        da[k] = {"luc": time.time(), "ds": ds}
        ghi_json(_CACHE, da)
        ra += ds
    return ra
