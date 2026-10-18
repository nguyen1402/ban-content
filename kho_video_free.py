# -*- coding: utf-8 -*-
"""Tìm VIDEO STOCK MIỄN PHÍ, KHÔNG WATERMARK/LOGO trên Pexels, Pixabay, Mixkit, Coverr, Wikimedia Commons (12/10 user:
bỏ tự tải YouTube vì dính logo kênh). Pexels/Pixabay/Mixkit/Coverr — mở trang tìm trong cửa sổ Chrome hiện
(cùng hạ tầng DevTools với anh_google: hồ sơ riêng, không cần API key), đọc JSON-LD VideoObject trong trang.

  * Pexels: link file mp4 trực tiếp (sd 960x540 / hd 1280x720 / hd 1920x1080 / uhd) -> lấy bản 1280x720 (15/10).
  * Pixabay: link xem trước _tiny.mp4; bản 1280x720 là _medium.mp4, 1920x1080 là _large.mp4 (cùng đường dẫn).
  * Giấy phép: cả hai cho dùng thương mại, không bắt ghi nguồn (Pexels License / Pixabay Content License).
  * Pixabay trả kết quả lỏng (tìm "sea urchin" ra cả "bàn chân trên cát") -> luôn chấm lại bằng SigLIP.
Kết quả: [{nguon, id, ten, trang, thumb, file, dai}] (chưa tải)."""
import json
import os
import queue
import re
import threading
import time
import urllib.parse
import urllib.request

from common import CACHE_CHUNG, doc_json, ghi_json, log

_CACHE = os.path.join(CACHE_CHUNG, "tim_video_free.json")

SO_TAB = int(os.environ.get("BC_SO_TAB", "10"))   # 15/10 user: tìm stock bằng 10 tab song song (trước: 1 tab, tuần tự)
_TOI_DA_TRANG = {"www.pexels.com": 3, "pixabay.com": 2, "mixkit.co": 3, "coverr.co": 3}   # mỗi trang tối đa bấy nhiêu tab
#                                                  cùng lúc — Pixabay từng trả 429 khi bị gọi dồn
_HO = queue.Queue()                                 # websocket URL các tab RIÊNG của bộ tìm stock (không đụng tab anh_google)
_KHOA_HO = threading.Lock()
_KHOA_CACHE = threading.Lock()
_SEM = {}
_DA_TAO = [0]


def _tab_rieng():
    """Một tab rảnh trong hồ (tạo dần tới SO_TAB tab trong cửa sổ Chrome tìm kiếm của anh_google)."""
    import anh_google as g
    try:
        return _HO.get_nowait()
    except queue.Empty:
        pass
    with _KHOA_HO:
        if _DA_TAO[0] < SO_TAB:
            with g._KHOA:                                    # noqa: SLF001  (mở Chrome một lần)
                if not g._ds_tab():                          # noqa: SLF001
                    g._mo_chrome("about:blank")              # noqa: SLF001
            req = urllib.request.Request(f"http://127.0.0.1:{g.CONG}/json/new?about:blank", method="PUT")
            t = json.load(urllib.request.urlopen(req, timeout=10))
            _DA_TAO[0] += 1
            return t["webSocketDebuggerUrl"]
    return _HO.get()                                         # đủ SO_TAB tab: chờ tab rảnh


def _mo_trang(url, cho=7.0, cuon=2):
    """HTML của trang sau khi tải xong + cuộn vài lần. 15/10 user: mỗi lượt một tab RIÊNG trong hồ SO_TAB tab (song
    song), mỗi trang web tối đa _TOI_DA_TRANG tab cùng lúc."""
    import anh_google as g
    trang = urllib.parse.urlparse(url).netloc
    with _KHOA_HO:
        sem = _SEM.setdefault(trang, threading.Semaphore(_TOI_DA_TRANG.get(trang, 2)))
    with sem:
        u = _tab_rieng()
        try:
            ws = g._WS(u)                                    # noqa: SLF001
        except Exception:                                    # noqa: BLE001  tab bị đóng tay -> bỏ, lần sau tạo tab mới
            with _KHOA_HO:
                _DA_TAO[0] -= 1
            raise
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
            _HO.put(u)


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
        tot = sorted(fs, key=lambda f: (f.get("width") != 1280, f.get("width") != 1920, -(f.get("width") or 0)))   # 15/10 user: 720p
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
                   "file": u.replace("_tiny.mp4", "_medium.mp4"), "file_nho": u.replace("_tiny.mp4", "_medium.mp4"),   # 15/10: 720p
                   "dai": _giay(o.get("duration"))})
    return ra


def _slug(q):
    return re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")


def tim_mixkit(q):
    """Mixkit (Mixkit License: thương mại, không cần ghi nguồn): thẻ kết quả có mã + ảnh thu nhỏ + tiêu đề; file 720p."""
    h = _mo_trang(f"https://mixkit.co/free-stock-video/{_slug(q)}/")
    ra, thay = [], set()
    for m in re.finditer(r'data-item-grid--video-player-item-id-value="(\d+)"', h):
        vid = m.group(1)
        if vid in thay:
            continue
        thay.add(vid)
        doan = h[m.end():m.end() + 2500]
        alt = re.search(r'class="item-grid-video-player__thumb" alt="([^"]*)"', doan)
        ra.append({"nguon": "mixkit", "id": "mk_" + vid, "ten": html_unescape(alt.group(1)) if alt else "",
                   "trang": f"https://mixkit.co/free-stock-video/{vid}/",
                   "thumb": f"https://assets.mixkit.co/videos/{vid}/{vid}-thumb-360-0.jpg",
                   "file": f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4", "dai": 0.0})
    return ra


def html_unescape(s):
    import html
    return html.unescape(s)


def tim_coverr(q):
    """Coverr (Coverr License: miễn phí thương mại): JSON trong trang có tiêu đề, ảnh thu nhỏ, độ dài, cờ dọc/premium,
    link mp4 1080p. Chỉ lấy video NGANG, không premium."""
    h = _mo_trang(f"https://coverr.co/s?q={urllib.parse.quote(q)}")
    ra, thay = [], set()
    for m in re.finditer(r'"baseFilename":"([^"]+)"', h):
        base = m.group(1)
        if base in thay:
            continue
        thay.add(base)
        dau = h.rfind('{"id":"', 0, m.start())               # chỉ đọc trong ĐÚNG đối tượng của video này
        het = h.find('"allSlugs"', m.end())
        if dau < 0 or het < 0 or het - m.end() > 4000:
            continue
        truoc, sau = h[dau:m.start()], h[m.end():het]
        if '"urls":{"mp4"' not in sau or '"isVertical":true' in sau or '"isPremium":true' in sau \
                or '"isAiGenerated":true' in sau:
            continue                                         # không phải video (banner, ảnh) / dọc / trả phí / AI
        td = re.findall(r'"title":"([^"]*)"', truoc)
        du = re.search(r'"duration":"([\d.]+)"', sau)
        ra.append({"nguon": "coverr", "id": "cv_" + re.sub(r"[^\w-]", "", base)[-40:], "ten": td[-1] if td else base,
                   "trang": "https://coverr.co", "thumb": f"https://cdn.coverr.co/videos/{base}/thumbnail?width=640",
                   "file": f"https://cdn.coverr.co/videos/{base}/720p.mp4", "dai": float(du.group(1)) if du else 0.0})
    return ra


GIAY_PHEP_NHAN = ("cc0", "public domain", "pd", "cc by 1.0", "cc by 2.0", "cc by 2.5", "cc by 3.0", "cc by 4.0", "cc by")


def tim_wikimedia(q):
    """Wikimedia Commons qua API công khai (không key): chỉ nhận PD / CC0 / CC BY (BỎ BY-SA, NC, ND — ràng buộc khi dùng
    thương mại). Kèm tác giả + giấy phép để ghi nguồn (ghi_nguon.txt)."""
    import urllib.request
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:video {q}",
        "gsrnamespace": 6, "gsrlimit": 25, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mediatype",
        "iiurlwidth": 640})
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={
            "User-Agent": "ban-content/0.4 (documentary editing tool; contact via github nguyen1402)"}), timeout=30)
        d = json.loads(r.read().decode("utf-8"))
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! Wikimedia '{q[:40]}': {str(e)[:80]}")
        return []
    ra = []
    for p in (d.get("query") or {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata") or {}
        lic = re.sub(r"<[^>]+>", "", (md.get("LicenseShortName") or {}).get("value", "")).strip()
        lk = lic.lower()
        if not lk or any(x in lk for x in ("sa", "nc", "nd")) and "public" not in lk:
            continue
        if not any(lk.startswith(x) or lk == x for x in GIAY_PHEP_NHAN):
            continue
        if (ii.get("width") or 0) < (ii.get("height") or 1) or (ii.get("width") or 0) < 640:
            continue                                         # chỉ video NGANG, >= 640 px
        tg = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()[:120]
        ra.append({"nguon": "wikimedia", "id": "wm_" + str(p.get("pageid")), "ten": p.get("title", "")[5:],
                   "trang": ii.get("descriptionurl", ""), "thumb": ii.get("thumburl", ""), "file": ii.get("url", ""),
                   "dai": float(ii.get("duration") or 0), "ghi_nguon": f"{p.get('title', '')[5:]} — {tg} — {lic} — {ii.get('descriptionurl', '')}"})
    return ra


NGUON_MAC_DINH = ("pexels", "pixabay", "mixkit", "coverr", "wikimedia")
_HAM = {"pexels": "tim_pexels", "pixabay": "tim_pixabay", "mixkit": "tim_mixkit", "coverr": "tim_coverr",
        "wikimedia": "tim_wikimedia"}


def _720(x):
    """15/10 user: hạ về 720p — kết quả cache cũ còn trỏ file 1080p (Pixabay/Coverr đổi được theo đường dẫn;
    Pexels cache cũ giữ nguyên, hết 7 ngày tìm lại sẽ lấy 1280x720)."""
    f = x.get("file") or ""
    if x.get("nguon") == "pixabay" and f.endswith("_large.mp4"):
        x = {**x, "file": f[:-len("_large.mp4")] + "_medium.mp4"}
    elif x.get("nguon") == "coverr" and f.endswith("/1080p.mp4"):
        x = {**x, "file": f[:-len("1080p.mp4")] + "720p.mp4"}
    return x


def _mot(n, q):
    """Kết quả MỘT nguồn cho từ khoá q (cache 7 ngày; ghi cache có khoá — gọi song song an toàn)."""
    k = f"{n}|{q.strip().lower()}"
    v = (doc_json(_CACHE, {}) or {}).get(k)
    if v and time.time() - v["luc"] < 7 * 86400:
        return [_720(x) for x in v["ds"]]
    try:
        ds = globals()[_HAM[n]](q)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! tìm {n} '{q[:40]}': {str(e)[:100]}")
        return []                                            # lỗi: không ghi cache (lần sau tìm lại)
    with _KHOA_CACHE:
        da = doc_json(_CACHE, {}) or {}
        da[k] = {"luc": time.time(), "ds": ds}
        ghi_json(_CACHE, da)
    return ds


def tim(q, nguon=NGUON_MAC_DINH):
    """Kết quả mọi nguồn cho từ khoá q (cache 7 ngày)."""
    ra = []
    for n in nguon:
        ra += _mot(n, q)
    return ra


def tim_nhieu(ds_tu, nguon=NGUON_MAC_DINH, bao=None):
    """15/10 user: tìm NHIỀU từ khoá SONG SONG (SO_TAB tab Chrome) -> {từ khoá: [kết quả]}. bao(xong, tong)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    viec = [(q, n) for q in ds_tu for n in nguon]
    ra = {q: [] for q in ds_tu}
    xong = 0
    with ThreadPoolExecutor(SO_TAB) as ex:
        tuong_lai = {ex.submit(_mot, n, q): q for q, n in viec}
        for f in as_completed(tuong_lai):
            ra[tuong_lai[f]] += f.result() or []
            xong += 1
            if bao:
                bao(xong, len(viec))
    return ra
