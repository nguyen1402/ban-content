# -*- coding: utf-8 -*-
"""Kho ảnh trên web (không cần key): Wikimedia Commons + iNaturalist.

Mỗi adapter trả danh sách {id, tieu_de, url, nguon, giay_phep, tac_gia}. Việc chọn ảnh nào
khớp cảnh làm ở chon_anh.py (CLIP), ở đây chỉ tìm."""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "ban-content/0.2 (video illustration research tool)"}


def _get_json(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:                                   # noqa: BLE001
        return {}


def commons(q, n=6):
    """Ảnh Wikimedia Commons, rộng >=1200px, đã thu về ~1920px."""
    d = _get_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"filetype:bitmap {q}", "gsrlimit": n + 4, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1920}))
    ra = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl") or (ii.get("width") or 0) < 1200:
            continue
        meta = ii.get("extmetadata", {})
        lic = (meta.get("LicenseShortName", {}) or {}).get("value", "")
        tg = re.sub(r"<[^>]+>", "", (meta.get("Artist", {}) or {}).get("value", ""))[:60]
        ra.append({"id": "wc_" + re.sub(r"\W+", "_", p.get("title", ""))[:70],
                   "tieu_de": p.get("title", ""), "url": ii["thumburl"], "nguon": "commons",
                   "giay_phep": lic, "tac_gia": tg})
        if len(ra) >= n:
            break
    return ra


def inaturalist(q, n=6):
    """Ảnh quan sát loài của iNaturalist (cấp phép mở, đã được cộng đồng xác minh loài)."""
    d = _get_json("https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode({
        "q": q, "photos": "true", "quality_grade": "research", "per_page": n + 4,
        "license": "cc0,cc-by,cc-by-sa", "order_by": "votes", "order": "desc"}))
    ra = []
    for o in d.get("results") or []:
        for ph in (o.get("photos") or [])[:1]:
            u = (ph.get("url") or "").replace("/square.", "/original.")
            if not u:
                continue
            ra.append({"id": f"inat_{ph.get('id')}",
                       "tieu_de": (o.get("taxon") or {}).get("name", "") or q,
                       "url": u, "nguon": "inaturalist",
                       "giay_phep": ph.get("license_code", "") or "",
                       "tac_gia": (ph.get("attribution") or "")[:60]})
        if len(ra) >= n:
            break
    return ra


def wikipedia(q, n=1):
    """Ảnh chính của trang Wikipedia khớp tên (loài, địa danh, sự vật) — thường là ảnh đại diện tốt nhất."""
    d = _get_json("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrlimit": 2,
        "prop": "pageimages", "piprop": "original", "redirects": 1}))
    ra = []
    trang = sorted((d.get("query", {}).get("pages") or {}).values(), key=lambda p: p.get("index", 9))
    for p in trang:
        o = (p.get("original") or {})
        u = o.get("source", "")
        if urllib.parse.urlparse(u).path.lower().endswith((".jpg", ".jpeg", ".png"))                 and (o.get("width") or 0) >= 1200:
            ra.append({"id": "wp_" + re.sub(r"\W+", "_", p.get("title", ""))[:60],
                       "tieu_de": p.get("title", ""), "url": u.split("?")[0], "nguon": "wikipedia",
                       "giay_phep": "Wikimedia", "tac_gia": ""})
    return ra[:n]


ADAPTER = {"wc": commons, "inat": inaturalist, "wp": wikipedia}


try:                                                       # Pexels/Pixabay ảnh: chỉ khi đã có file key
    import nguon_khac as _nk
    ADAPTER.update(_nk.ANH_ADAPTER)
except Exception:                                          # noqa: BLE001
    pass
