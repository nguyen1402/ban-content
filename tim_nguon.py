# -*- coding: utf-8 -*-
"""Bước 2 — dựng THƯ VIỆN ứng viên: tìm YouTube (yt-dlp) + ảnh Wikimedia Commons, tải bản
nhẹ (360p, không tiếng) để chấm điểm. Một video trả lời được nhiều cảnh nên gom thành một
kho chung thay vì tìm-rồi-tải riêng từng cảnh."""
import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import (KENH_CHAN, YTDLP, YT_JS, chay, doc_json, duong_cache, ghi_json, log)

TOI_DA_MOI_TRUY_VAN = 6
DAI_MIN, DAI_MAX = 20, 1500           # giây — bỏ clip quá ngắn / phim quá dài


def _kenh_bi_chan(ten):
    t = (ten or "").lower() + " "
    return any(k in t for k in KENH_CHAN)


def tim_youtube(q, n=TOI_DA_MOI_TRUY_VAN):
    rc, out, _ = chay([YTDLP, *YT_JS, "--no-warnings", "--flat-playlist", "-J",
                       f"ytsearch{n + 4}:{q}"], timeout=90)
    try:
        ds = json.loads(out).get("entries") or []
    except ValueError:
        return []
    ra = []
    for e in ds:
        dai = e.get("duration") or 0
        if not (DAI_MIN <= dai <= DAI_MAX) or _kenh_bi_chan(e.get("channel")):
            continue
        ra.append({"id": e["id"], "tieu_de": e.get("title", ""), "dai": dai,
                   "kenh": e.get("channel", ""), "nguon": "youtube"})
        if len(ra) >= n:
            break
    return ra


def tim_commons_anh(q, n=4):
    """Ảnh Wikimedia Commons (API công khai, không cần key). Trả link ảnh đã thu ~1920px."""
    url = ("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"filetype:bitmap {q}", "gsrlimit": n + 4, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1920}))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ban-content/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception:                                   # noqa: BLE001
        return []
    ra = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl") or (ii.get("width") or 0) < 1200:
            continue
        lic = (ii.get("extmetadata", {}).get("LicenseShortName", {}) or {}).get("value", "")
        ra.append({"id": "wc_" + re.sub(r"\W+", "_", p.get("title", ""))[:60],
                   "tieu_de": p.get("title", ""), "url": ii["thumburl"], "nguon": "commons",
                   "giay_phep": lic, "kenh": ""})
        if len(ra) >= n:
            break
    return ra


def gom_truy_van(canh):
    """{truy vấn: [id cảnh]} — mỗi truy vấn tìm đúng một lần dù nhiều cảnh dùng chung."""
    d = {}
    for c in canh:
        for q in list(c.get("q", [])) + [q for nh in c.get("nhip_tho") or [] for q in nh.get("q", [])]:
            d.setdefault(q.strip().lower(), []).append(c["id"])
    return d


def tim_tat_ca(canh, song_song=6):
    """Tìm YouTube + các kho ảnh web cho mọi truy vấn; truy vấn đã có cache chỉ bổ sung nguồn thiếu."""
    import kho_web
    import nguon_khac
    cache = duong_cache("tim.json")
    so = doc_json(cache, {})
    viec = [q for q in gom_truy_van(canh)
            if q not in so or not all(k in so[q] for k in ("yt", *kho_web.ADAPTER, *nguon_khac.VIDEO_ADAPTER))]
    log(f"[2] {len(viec)} truy vấn cần tìm/bổ sung (đã có cache {len(so)})")

    def _lam(q):
        e = dict(so.get(q) or {})
        ham_cua = {"yt": tim_youtube, **kho_web.ADAPTER, **nguon_khac.VIDEO_ADAPTER}   # YouTube, kho ảnh, Dailymotion/Commons/Archive…
        can = {k: h for k, h in ham_cua.items() if k not in e}
        if can:
            with ThreadPoolExecutor(len(can)) as ex2:                # MỌI nguồn của một truy vấn tìm CÙNG LÚC
                for k, kq in zip(can, ex2.map(lambda h: h(q), can.values())):
                    e[k] = kq
        return q, e

    with ThreadPoolExecutor(song_song) as ex:
        for i, (q, kq) in enumerate(ex.map(_lam, viec), 1):
            so[q] = kq
            if i % 20 == 0 or i == len(viec):
                ghi_json(cache, so)
                from common import tien_do
                log(f"    tìm {i}/{len(viec)}")
                tien_do("tim", "dang", f"tìm {i}/{len(viec)}")
    # ảnh: từ khóa NGẮN (anh_q) -> mọi kho ảnh; lưu dưới khóa 'anh:<q>'
    anh_q = sorted({s.strip().lower() for c in canh
                    for s in list(c.get("anh_q", [])) + [x for nh in c.get("nhip_tho") or []
                                                         for x in nh.get("anh_q", [])] if s.strip()})
    can_anh = [q for q in anh_q if "anh:" + q not in so]
    log(f"    từ khóa ảnh ngắn cần tìm: {len(can_anh)}/{len(anh_q)}")

    def _anh(q):
        return q, {k: ham(q) for k, ham in kho_web.ADAPTER.items()}

    with ThreadPoolExecutor(song_song) as ex:
        for i, (q, kq) in enumerate(ex.map(_anh, can_anh), 1):
            so["anh:" + q] = kq
            if i % 25 == 0 or i == len(can_anh):
                ghi_json(cache, so)
    # ảnh theo TÊN THỰC THỂ cụ thể của từng nhịp (tổ chức, vật, người, địa danh): tìm bằng Chrome thật (Bing Images)
    ten_ent = {}
    for c in canh:
        for nh in c.get("nhip_tho") or []:
            for e in nh.get("ents") or []:
                nm = (e.get("name") or "").strip().lower()
                if nm:
                    ten_ent.setdefault(nm, e.get("kind", "footage"))
    # nhịp KHÔNG có thực thể (lời trừu tượng/chung) cũng phải có ảnh Bing: dùng chính cụm tìm kiếm của nhịp (q[0], q[1])
    for c in canh:
        for nh in c.get("nhip_tho") or []:
            for q in (nh.get("q") or [])[:(1 if nh.get("ents") else 2)]:     # có thực thể: q[0]; trừu tượng: q[0] và q[1]
                q = str(q).strip().lower()
                if q:
                    ten_ent.setdefault(q, "footage")
    can_bg = [nm for nm in ten_ent if "bg" not in so.get("anh:" + nm, {})]
    if can_bg:
        import anh_trinh_duyet
        log(f"    ảnh theo tên thực thể (Chrome thật): {len(can_bg)}/{len(ten_ent)} từ khoá cần tìm")
        with ThreadPoolExecutor(anh_trinh_duyet.LUONG_TOI_DA) as ex:
            for i, (nm, kq) in enumerate(zip(can_bg, ex.map(anh_trinh_duyet.ung_vien, can_bg)), 1):
                so.setdefault("anh:" + nm, {})["bg"] = kq
                if i % 20 == 0 or i == len(can_bg):
                    ghi_json(cache, so)
                    log(f"    ảnh thực thể {i}/{len(can_bg)}")
    ghi_json(cache, so)
    return so


HAN_MUC = {"yt": 1.0, "dm": 0.12, "cv": 0.10, "ia": 0.06, "px": 0.30, "pb": 0.20, "ytcc": 0.15}


def kho_ung_vien(canh, tim, toi_da=80):
    """Gom ứng viên video từ MỌI nguồn (khử trùng id). Mỗi nguồn có hạn mức riêng để YouTube không lấn hết;
    trong từng nguồn, video xuất hiện ở nhiều truy vấn xếp trước."""
    qs = set()
    for c in canh:
        qs.update(q.strip().lower() for q in list(c.get("q", [])) + [q for nh in c.get("nhip_tho") or [] for q in nh.get("q", [])])
    theo_nguon = {}
    for q in qs:
        e = tim.get(q, {})
        for k in HAN_MUC:
            for it in (e.get("yt") if k == "yt" else e.get(k)) or []:
                d = theo_nguon.setdefault(k, {})
                d.setdefault(it["id"], [0, it])[0] += 1
    ra = []
    tong_hm = sum(HAN_MUC[k] for k in theo_nguon) or 1.0         # chia hạn mức cho TỔNG đúng bằng toi_da (trước đây cộng dồn vượt ~25%)
    for k, d in theo_nguon.items():
        co = sorted(d.values(), key=lambda z: -z[0])
        ra += [it for _n, it in co[:max(3, int(toi_da * HAN_MUC[k] / tong_hm))]]
    return ra


def them_link(urls):
    """Link video do NGƯỜI DÙNG chỉ định -> mục kho (id/tiêu đề/độ dài/kênh) lấy bằng yt-dlp; link hỏng bị bỏ qua."""
    ra = []
    for u in urls:
        u = (u or "").strip()
        if not u.startswith("http"):
            continue
        rc, out, err = chay([YTDLP, *YT_JS, "--no-warnings", "-q", "--no-playlist", "--skip-download",
                             "--print", "%(id)s	%(title)s	%(duration)s	%(channel)s	%(webpage_url)s", u], timeout=120)
        row = (out or "").strip().splitlines()
        if rc != 0 or not row:
            log(f"    ! link không đọc được: {u[:80]}")
            continue
        f = row[-1].split("	")
        if len(f) < 5:
            continue
        try:
            dai = float(f[2])
        except ValueError:
            dai = 0.0
        ra.append({"id": f[0], "tieu_de": f[1], "dai": dai, "kenh": f[3], "nguon": "youtube", "trang": f[4],
                   "uu_tien": True})
    return ra


TAI_TOI_DA_GIAY = 100           # một video tải trực tiếp quá thời gian/dung lượng này thì bỏ
TAI_TOI_DA_BYTE = 250 << 20


def _tai_truc_tiep(it, dich):
    """Nguồn có link mp4/webm trực tiếp (Pexels, Pixabay, Archive, Commons): tải rồi hạ về 360p không tiếng."""
    tho = dich + ".tho"
    try:
        req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0"})
        import time
        t0, n = time.time(), 0
        with urllib.request.urlopen(req, timeout=60) as r, open(tho, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                n += len(b)
                if time.time() - t0 > TAI_TOI_DA_GIAY or n > TAI_TOI_DA_BYTE:
                    log(f"    ! bỏ {it['id']}: tải quá chậm/quá nặng ({n >> 20} MB sau {time.time() - t0:.0f}s)")
                    return None                          # Archive/Commons hay trả file gốc rất nặng, tải chậm -> bỏ, đừng chặn cả bước
        from common import FFMPEG
        rc, _, _ = chay([FFMPEG, "-y", "-v", "error", "-i", tho, "-an", "-vf", "scale=-2:360", "-c:v", "libx264",
                         "-preset", "veryfast", "-crf", "26", dich], timeout=600)
        return dich if rc == 0 and os.path.isfile(dich) else None
    except Exception:                                    # noqa: BLE001
        return None
    finally:
        if os.path.isfile(tho):
            os.remove(tho)


def tai_xem_truoc(it, chieu_cao=360):
    """Tải bản nhẹ không tiếng để chấm. Trả đường dẫn hoặc None."""
    dich = duong_cache("xem_truoc", it["id"] + ".mp4")
    if os.path.isfile(dich) and os.path.getsize(dich) > 10000:
        return dich
    if it.get("url"):
        return _tai_truc_tiep(it, dich)
    mau = duong_cache("xem_truoc", it["id"] + ".%(ext)s")
    rc, _, err = chay([YTDLP, *YT_JS, "--no-warnings", "-q", "--no-playlist", "--max-filesize", "400M",
                       "-f", f"bv*[height<={chieu_cao}][ext=mp4]/bv*[height<={chieu_cao}]/wv*",
                       "--merge-output-format", "mp4", "-o", mau,
                       it.get("trang") or f"https://www.youtube.com/watch?v={it['id']}"], timeout=600)
    if os.path.isfile(dich):
        return dich
    for f in os.listdir(os.path.dirname(dich)):           # có thể ra .webm/.mkv
        if f.startswith(it["id"] + ".") and not f.endswith((".part", ".ytdl")):
            return os.path.join(os.path.dirname(dich), f)
    log(f"    ! tải hỏng {it['id']}: {err.strip()[-120:]}")
    return None


def tai_kho(kho, toi_da, song_song=8):
    kho = kho[:toi_da]
    log(f"    tải bản xem trước {len(kho)} video…")
    import time
    from common import eta_chu, tien_do
    t0 = time.time()
    with ThreadPoolExecutor(song_song) as ex:
        ds = []
        for i, p in enumerate(ex.map(tai_xem_truoc, kho), 1):
            ds.append(p)
            if i % 5 == 0 or i == len(kho):
                e = eta_chu(t0, i, len(kho))
                log(f"    tải {i}/{len(kho)}{e}")
                tien_do("tai", "dang", f"tải {i}/{len(kho)}")
    ra = []
    for it, p in zip(kho, ds):
        if p:
            it = dict(it)
            it["file"] = p
            ra.append(it)
    log(f"    tải được {len(ra)}/{len(kho)}")
    return ra
