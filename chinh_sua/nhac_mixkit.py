# -*- coding: utf-8 -*-
"""NHẠC NỀN từ Mixkit (13/10 user: "tìm cả nhạc ghép vào, ưu tiên nhạc không vi phạm chính sách YouTube mà phù hợp
nội dung"). Kho cũ (nhạc kênh YouTube "No Copyright") không chắc an toàn -> dùng Mixkit: giấy phép Mixkit (Stock Music
Free License) cho phép dùng trong video, KHÔNG cần ghi tên; vẫn ghi nguồn vào ra/<dự án>/nhac_nguon.txt để đối chiếu.

  1. Gộp chương thành ĐOẠN NHẠC: chương liền nhau cùng tâm trạng gộp lại; đoạn < DOAN_TOI_THIEU giây gộp vào đoạn bên.
  2. ChatGPT đọc nội dung từng đoạn -> 2-3 từ khoá nhạc tiếng Anh (thể loại + tâm trạng) — rút từ CHÍNH kịch bản.
  3. Tìm Mixkit (trang tìm kiếm, JSON-LD MusicRecording) qua cửa sổ Chrome chung -> tải mp3 (cache/nhac_mixkit/),
     đo độ to (ffmpeg volumedetect) -> âm lượng nhỏ hơn giọng đọc; bài ngắn hơn đoạn thì nối bài kế (không lặp bài)."""
import html
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

from common import CACHE_CHUNG, FFMPEG, doc_json, ghi_json, hoi_nhieu, log, rut_json

DOAN_TOI_THIEU = 60.0
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
THU = os.path.join(CACHE_CHUNG, "nhac_mixkit")
_P = """You choose BACKGROUND MUSIC for sections of a Vietnamese documentary narration (music stays quiet under the voice).
For each SECTION below, give 2-3 short English search keywords for a stock-music site (Mixkit), each 1-3 words, combining
mood and genre that fit the CONTENT and emotion (e.g. "mysterious ambient", "hopeful piano", "tense cinematic",
"curious science", "epic orchestral", "calm nature"). No vocals. Avoid comedy / upbeat pop unless the section is light-hearted.
Return ONLY JSON: [{{"doan": <section index>, "tu_khoa": ["...", "..."]}}]

SECTIONS:
{ds}"""


def _doan(chuong):
    """Chương -> đoạn nhạc [{tu, den, tam_trang, cau: (tu_cau, den_cau), ten}]."""
    ds = []
    for c in chuong:
        if ds and ds[-1]["tam_trang"] == c.get("tam_trang"):
            ds[-1].update(den=c["den"], cau=(ds[-1]["cau"][0], c["den_cau"]), ten=ds[-1]["ten"] + " / " + c.get("ten", ""))
        else:
            ds.append({"tu": c["tu"], "den": c["den"], "tam_trang": c.get("tam_trang", ""), "cau": (c["tu_cau"], c["den_cau"]),
                       "ten": c.get("ten", "")})
    doi = True
    while doi and len(ds) > 1:                               # đoạn quá ngắn: gộp vào đoạn bên ngắn hơn
        doi = False
        for k, d in enumerate(ds):
            if d["den"] - d["tu"] < DOAN_TOI_THIEU:
                j = k - 1 if k > 0 and (k == len(ds) - 1 or ds[k - 1]["den"] - ds[k - 1]["tu"] <= ds[k + 1]["den"] - ds[k + 1]["tu"]) else k + 1
                a, b = sorted((k, j))
                ds[a].update(den=ds[b]["den"], cau=(ds[a]["cau"][0], ds[b]["cau"][1]), ten=ds[a]["ten"] + " / " + ds[b]["ten"])
                del ds[b]
                doi = True
                break
    ds[0]["tu"] = 0.0
    return ds


def _giay(s):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def tim(q):
    """Mixkit: [{id, ten, the_loai, tac_gia, dai, url, trang}] (cache 7 ngày)."""
    import time
    import kho_video_free as K
    os.makedirs(THU, exist_ok=True)
    so = os.path.join(THU, "_tim.json")
    da = doc_json(so, {}) or {}
    v = da.get(q)
    if v and time.time() - v.get("luc", 0) < 7 * 86400:
        return v["kq"]
    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")
    h = K._mo_trang(f"https://mixkit.co/free-stock-music/discover/{urllib.parse.quote(slug)}/", cho=8, cuon=1)   # noqa: SLF001
    kq, thay = [], set()
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        for g in (d.get("@graph") or [d]):
            for x in (g.get("itemListElement") or []):
                if isinstance(x, dict) and x.get("@type") == "MusicRecording" and str(x.get("url", "")).endswith(".mp3"):
                    tid = x["url"].rstrip("/").split("/")[-2]
                    if tid in thay:
                        continue
                    thay.add(tid)
                    kq.append({"id": tid, "ten": x.get("name", ""), "the_loai": x.get("genre", ""), "tac_gia": x.get("byArtist", ""),
                               "dai": _giay(x.get("duration")), "url": x["url"],
                               "trang": f"https://mixkit.co/free-stock-music/discover/{slug}/"})
    if not kq:                                               # trang TÌM KIẾM không có JSON-LD: đọc thẻ bài
        phan = re.split(r'data-audio-player-item-id-value="', h)[1:]
        for p in phan:
            tid = p.split('"', 1)[0]
            if not tid.isdigit() or tid in thay or 'data-audio-player-item-type-value="music"' not in p[:200]:
                continue
            thay.add(tid)
            ten = re.search(r'item-grid-card__title">\s*(.*?)\s*</h2>', p, re.S)
            tg = re.search(r'item-grid-music-preview__author">\s*by\s*(.*?)\s*</p>', p, re.S)
            nhan = re.findall(r'class="meta-links__link"[^>]*href="/free-stock-music/[^"]*">([^<]+)</a>', p[:6000])
            kq.append({"id": tid, "ten": html.unescape(ten.group(1)) if ten else f"Mixkit {tid}",
                       "the_loai": ", ".join(dict.fromkeys(nhan))[:80], "tac_gia": html.unescape(tg.group(1)) if tg else "",
                       "dai": 0, "url": f"https://assets.mixkit.co/music/{tid}/{tid}.mp3",
                       "trang": f"https://mixkit.co/free-stock-music/discover/{slug}/"})
    da[q] = {"luc": time.time(), "kq": kq}
    ghi_json(so, da)
    return kq


def _tai(b):
    """Tải mp3 + đo độ to trung bình (dB) -> b có thêm file, do_to_db."""
    os.makedirs(THU, exist_ok=True)
    f = os.path.join(THU, f"{b['id']}.mp3")
    if not (os.path.isfile(f) and os.path.getsize(f) > 10000):
        raw = urllib.request.urlopen(urllib.request.Request(b["url"], headers=UA), timeout=60).read(40 << 20)
        open(f, "wb").write(raw)
    js = f + ".json"
    db = (doc_json(js, {}) or {}).get("db")
    if db is None:
        p = subprocess.run([FFMPEG, "-hide_banner", "-i", f, "-af", "volumedetect", "-f", "null", "-"], capture_output=True,
                           timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
        loi = p.stderr.decode("utf-8", "ignore")
        m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", loi)
        db = float(m.group(1)) if m else -20.0
        d = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", loi)
        ghi_json(js, {"db": db, "dai": int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else 0})
    dai = (doc_json(js, {}) or {}).get("dai") or b.get("dai") or 0
    return dict(b, file=f, do_to_db=db, dai=dai)


def chon(chuong, cau, out):
    """Kế hoạch nhạc [{tu, den, file, vol, tam_trang, ten, tac_gia, url}] phủ cả video; ghi ra/<dự án>/nhac_nguon.txt."""
    if not chuong:
        return []
    ds = _doan(chuong)
    theo_i = {c["i"]: c for c in cau}
    mo_ta = []
    for k, d in enumerate(ds):
        loi = " ".join(theo_i[i]["text"] for i in range(d["cau"][0], d["cau"][1] + 1) if i in theo_i)
        mo_ta.append(f"{k}. [{d['ten']}] {loi[:700]}")
    p = _P.format(ds="\n".join(mo_ta))
    so = os.path.join(out, "nhac_hoi.json")
    da = doc_json(so, {}) or {}
    import hashlib
    kh = hashlib.md5(p.encode("utf-8")).hexdigest()[:16]
    if not rut_json(da.get(kh) or ""):
        log(f"[NH] nhạc nền: hỏi ChatGPT từ khoá cho {len(ds)} đoạn…")
        r = hoi_nhieu([p], timeout=180)[0]
        if rut_json(r or ""):
            da[kh] = r
            ghi_json(so, da)
    tk = {}
    for x in (rut_json(da.get(kh) or "") or []):
        try:
            tk[int(x["doan"])] = [str(t) for t in x.get("tu_khoa") or [] if str(t).strip()][:3]
        except (KeyError, TypeError, ValueError):
            continue
    ra, da_dung = [], set()
    for k, d in enumerate(ds):
        ung = []
        for q in tk.get(k) or [d["tam_trang"].replace("_", " ") + " documentary"]:
            try:
                ung += [b for b in tim(q) if b["id"] not in {u["id"] for u in ung}]
            except Exception as e:                           # noqa: BLE001
                log(f"    ! nhạc: tìm '{q}' lỗi {str(e)[:80]}")
        san = []                                             # tải trước tối đa 6 bài đầu bảng (có thời lượng thật)
        for b in [b for b in ung if b["id"] not in da_dung][:6]:
            try:
                b = _tai(b)
            except Exception as e:                           # noqa: BLE001
                log(f"    ! nhạc: tải '{b['ten']}' lỗi {str(e)[:80]}")
                continue
            if b["dai"] >= 40:
                san.append(b)
        t = d["tu"]
        while t < d["den"] - 4.0:
            con = [b for b in san if b["id"] not in da_dung]
            if not con:
                break
            can = d["den"] - t                               # ưu tiên bài đủ dài cho phần còn lại; giữ thứ tự hợp từ khoá
            b = sorted(con, key=lambda z: (z["dai"] < can, -z["dai"] if z["dai"] < can else 0))[0]
            da_dung.add(b["id"])
            dai = min(b["dai"] - 0.3, d["den"] - t)
            vol = round(max(0.05, min(0.2, 0.11 * 10 ** ((-20 - b["do_to_db"]) / 20))), 3)
            ra.append({"tu": round(t, 2), "den": round(t + dai, 2), "file": b["file"], "vol": vol, "tam_trang": d["tam_trang"],
                       "ten": b["ten"], "tac_gia": b["tac_gia"], "url": b["url"], "doan": d["ten"]})
            t += dai
    if ra:
        with open(os.path.join(out, "nhac_nguon.txt"), "w", encoding="utf-8") as f:
            f.write("Nhạc nền — Mixkit (Mixkit Stock Music Free License: dùng trong video, không bắt buộc ghi tên)\n")
            for m in ra:
                f.write(f"{m['tu']:7.1f}s-{m['den']:7.1f}s  {m['ten']} — {m['tac_gia']}  {m['url']}\n")
    log(f"    nhạc nền: {len(ra)} bài cho {len(ds)} đoạn ({', '.join(sorted({m['ten'] for m in ra}))})")
    return ra
