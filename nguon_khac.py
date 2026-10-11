# -*- coding: utf-8 -*-
"""Các nguồn VIDEO/ẢNH bổ sung (ngoài YouTube thường): Internet Archive, Wikimedia Commons video, Dailymotion,
YouTube lọc Creative Commons, và (khi có key miễn phí) Pexels, Pixabay.

Mỗi hàm trả danh sách mục cùng khuôn với tim_nguon.tim_youtube:
  {id, tieu_de, dai, kenh, nguon, url?}      (url = link tải TRỰC TIẾP; thiếu url thì tải bằng yt-dlp từ `trang`)
Key (nếu có) đọc từ pexels_key.txt / pixabay_key.txt cạnh file này (đã nằm trong .gitignore)."""
import json
import os
import re
import urllib.parse
import urllib.request

from common import ROOT, YTDLP, YT_JS, chay

UA = {"User-Agent": "ban-content/0.4 (stock footage research tool)"}
DAI_MIN_KHO, DAI_MAX_KHO = 5, 1500


_BO = {"a", "an", "the", "of", "in", "on", "at", "to", "and", "with", "from", "by", "for", "as", "footage",
       "shot", "video", "clip", "wide", "aerial", "close", "up"}


def _tu_chinh(q, toi_da=3):
    tu = [w for w in re.findall(r"[A-Za-z]+", q.lower()) if w not in _BO and len(w) > 2]
    return tu[:toi_da] or [q]


def _json(url, headers=None, timeout=30):
    h = dict(UA)
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:                                    # noqa: BLE001
        return {}


def lay_key(ten):
    p = os.path.join(ROOT, ten + "_key.txt")
    try:
        for ln in open(p, encoding="utf-8-sig"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                return ln
    except OSError:
        pass
    return ""


# --------------------------------------------------------------------------- không cần key
LICH_SU = ("archiv", "histor", "vintage", "1800", "1890", "1900", "19th", "old film", "reenact", "black and white", "newsreel")


def archive(q, n=4):
    """Internet Archive (phim tư liệu, nhiều thứ thuộc phạm vi công cộng). Chỉ chạy cho truy vấn LỊCH SỬ —
    với cụm động vật nó trả toàn phim lạc đề. Lấy bản mp4 nhỏ nhất đủ dùng."""
    if not any(w in q.lower() for w in LICH_SU):
        return []
    tu = _tu_chinh(q)
    cum = " AND ".join(tu)
    d = _json("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        {"q": f"(title:({cum}) OR subject:({cum}) OR description:({cum})) AND mediatype:(movies)",
         "fl[]": ["identifier", "title"], "rows": n + 3, "sort[]": "downloads desc", "output": "json"}, doseq=True))
    ra = []
    for doc in (d.get("response", {}).get("docs") or [])[:n + 3]:
        ident = doc.get("identifier")
        meta = _json(f"https://archive.org/metadata/{ident}")
        mp4 = []
        for f in meta.get("files") or []:
            nm = f.get("name", "")
            try:
                kich, dai = int(f.get("size", 0)), float(f.get("length", 0) or 0)
            except ValueError:
                continue
            if nm.lower().endswith(".mp4") and 1_000_000 < kich < 150_000_000 and DAI_MIN_KHO <= dai <= DAI_MAX_KHO:
                mp4.append((kich, nm, dai))
        if not mp4:
            continue
        kich, nm, dai = sorted(mp4)[0]
        ra.append({"id": "ia_" + re.sub(r"\W+", "_", ident)[:40], "tieu_de": doc.get("title", ident)[:80],
                   "dai": dai, "kenh": "archive.org", "nguon": "archive",
                   "url": f"https://archive.org/download/{ident}/{urllib.parse.quote(nm)}"})
        if len(ra) >= n:
            break
    return ra


def commons_video(q, n=4):
    """Clip thiên nhiên ngắn trên Wikimedia Commons (webm/ogv); cụm dài không ra thì thử 1-2 từ chính."""
    for cum in dict.fromkeys([q, " ".join(_tu_chinh(q, 2)), _tu_chinh(q, 1)[0]]):
        ra = _commons_video(cum, n)
        if ra:
            return ra
    return []


def _commons_video(q, n=4):
    d = _json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"filetype:video {q}", "gsrlimit": n + 4, "prop": "imageinfo",
        "iiprop": "url|size|mime|metadata"}))
    ra = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("url") or int(ii.get("size", 0)) > 150_000_000:
            continue
        dai = 0.0
        for m in ii.get("metadata") or []:
            if m.get("name") == "length":
                try:
                    dai = float(m.get("value"))
                except (TypeError, ValueError):
                    pass
        if dai and not (DAI_MIN_KHO <= dai <= DAI_MAX_KHO):
            continue
        ra.append({"id": "cv_" + re.sub(r"\W+", "_", p.get("title", ""))[:50], "tieu_de": p.get("title", "")[:80],
                   "dai": dai or 20.0, "kenh": "commons", "nguon": "commons_video", "url": ii["url"]})
        if len(ra) >= n:
            break
    return ra


def dailymotion(q, n=4):
    """Dailymotion qua API công khai (không key); tải bằng yt-dlp."""
    d = _json("https://api.dailymotion.com/videos?" + urllib.parse.urlencode(
        {"search": q, "fields": "id,title,duration,owner.screenname", "limit": n + 4, "sort": "relevance"}))
    ra = []
    for v in d.get("list") or []:
        dai = v.get("duration") or 0
        if not (20 <= dai <= DAI_MAX_KHO):
            continue
        ra.append({"id": "dm_" + v["id"], "tieu_de": v.get("title", "")[:80], "dai": dai,
                   "kenh": v.get("owner.screenname", ""), "nguon": "dailymotion",
                   "trang": f"https://www.dailymotion.com/video/{v['id']}"})
        if len(ra) >= n:
            break
    return ra


def youtube_cc(q, n=4):
    """YouTube chỉ gồm video cấp phép Creative Commons (ít bị Content ID hơn)."""
    from tim_nguon import _kenh_bi_chan, DAI_MIN, DAI_MAX
    rc, out, _ = chay([YTDLP, *YT_JS, "--no-warnings", "--flat-playlist", "-J",
                       "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&sp=EgIwAQ%253D%253D"],
                      timeout=90)
    try:
        ds = json.loads(out).get("entries") or []
    except ValueError:
        return []
    ra = []
    for e in ds:
        dai = e.get("duration") or 0
        if not (DAI_MIN <= dai <= DAI_MAX) or _kenh_bi_chan(e.get("channel")):
            continue
        ra.append({"id": e["id"], "tieu_de": e.get("title", ""), "dai": dai, "kenh": e.get("channel", ""),
                   "nguon": "youtube_cc"})
        if len(ra) >= n:
            break
    return ra


# --------------------------------------------------------------------------- cần key miễn phí
def pexels_video(q, n=6):
    k = lay_key("pexels")
    if not k:
        return []
    d = _json("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": q, "per_page": n + 2, "orientation": "landscape"}), headers={"Authorization": k})
    ra = []
    for v in d.get("videos") or []:
        fs = sorted((f for f in v.get("video_files") or [] if f.get("link") and (f.get("width") or 0) >= 640
                     and f.get("file_type") == "video/mp4"), key=lambda f: f["width"])
        if not fs or not (DAI_MIN_KHO <= (v.get("duration") or 0) <= 120):
            continue
        ra.append({"id": f"px_{v['id']}", "tieu_de": (v.get("url", "").rstrip("/").split("/")[-1])[:80],
                   "dai": v["duration"], "kenh": "pexels", "nguon": "pexels", "url": fs[0]["link"]})
        if len(ra) >= n:
            break
    return ra


def pixabay_video(q, n=6):
    k = lay_key("pixabay")
    if not k:
        return []
    d = _json("https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": k, "q": q, "per_page": max(n + 2, 3)}))
    ra = []
    for h in d.get("hits") or []:
        v = (h.get("videos") or {})
        f = v.get("small") or v.get("medium") or v.get("tiny")
        if not f or not f.get("url") or not (DAI_MIN_KHO <= (h.get("duration") or 0) <= 120):
            continue
        ra.append({"id": f"pb_{h['id']}", "tieu_de": (h.get("tags") or "")[:80], "dai": h["duration"],
                   "kenh": "pixabay", "nguon": "pixabay", "url": f["url"]})
        if len(ra) >= n:
            break
    return ra


def pexels_anh(q, n=4):
    k = lay_key("pexels")
    if not k:
        return []
    d = _json("https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": q, "per_page": n + 2, "orientation": "landscape"}), headers={"Authorization": k})
    return [{"id": f"pxa_{p['id']}", "tieu_de": (p.get("alt") or q)[:80], "url": (p.get("src") or {}).get("large2x")
             or p["src"]["large"], "nguon": "pexels", "giay_phep": "Pexels", "tac_gia": p.get("photographer", "")}
            for p in (d.get("photos") or [])[:n] if p.get("src")]


def pixabay_anh(q, n=4):
    k = lay_key("pixabay")
    if not k:
        return []
    d = _json("https://pixabay.com/api/?" + urllib.parse.urlencode(
        {"key": k, "q": q, "image_type": "photo", "orientation": "horizontal", "per_page": max(n + 2, 3)}))
    return [{"id": f"pba_{h['id']}", "tieu_de": (h.get("tags") or q)[:80], "url": h.get("largeImageURL"),
             "nguon": "pixabay", "giay_phep": "Pixabay", "tac_gia": h.get("user", "")}
            for h in (d.get("hits") or [])[:n] if h.get("largeImageURL")]


def _bat_dau():
    v = {"ia": archive, "cv": commons_video, "dm": dailymotion}
    if os.environ.get("BAT_YT_CC") == "1":
        v["ytcc"] = youtube_cc
    if lay_key("pexels"):
        v["px"] = pexels_video
    if lay_key("pixabay"):
        v["pb"] = pixabay_video
    return v


VIDEO_ADAPTER = _bat_dau()
ANH_ADAPTER = {k: f for k, f in (("pxa", pexels_anh), ("pba", pixabay_anh)) if lay_key(k[:2] == "px" and "pexels" or "pixabay")}
