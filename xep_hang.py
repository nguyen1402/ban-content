# -*- coding: utf-8 -*-
"""Chấm ĐỘ KHỚP kết quả tìm với một cảnh bằng SigLIP — KHÔNG tải video:

  * Video YouTube: lấy STORYBOARD (dải khung hình nhỏ YouTube tạo sẵn cho thanh tua, vài trăm KB/video), nhúng từng
    khung, điểm video = trung bình trượt 3 khung cao nhất; kèm giây khớp nhất. Lưu cache theo id video
    (cache/storyboard/<id>.npz) — tìm lại hay chạy tự động sau đều không tải lại.
  * Ảnh: nhúng ảnh thu nhỏ của kết quả tìm.

Điểm SigLIP so400m: khớp rõ thường >= 0,15; dưới NGUONG_THAP coi như lạc đề (giao diện làm mờ)."""
import io
import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from common import CACHE_CHUNG, YT_JS, YTDLP, log

NGUONG_THAP = 0.10
TOI_DA_KHUNG = 240          # video dài: lấy đều tối đa bấy nhiêu khung storyboard
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def _lay(url, t=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t).read()


def _khung_storyboard(vid):
    """([giây], [PIL]) và độ dài video, từ storyboard nét nhất."""
    from PIL import Image
    p = subprocess.run([YTDLP, *YT_JS, "-J", "--no-warnings", "https://www.youtube.com/watch?v=" + vid],
                       capture_output=True, timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        j = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
    except ValueError:
        j = {}
    tong = float(j.get("duration") or 0)
    sb = [f for f in j.get("formats") or [] if str(f.get("format_id", "")).startswith("sb") and f.get("fragments")]
    if not sb:
        return [], [], tong
    f = max(sb, key=lambda x: x.get("width") or 0)
    W, H, rr, cc = f["width"], f["height"], f["rows"], f["columns"]
    tam, t0 = [], 0.0
    for fr in f["fragments"]:
        tam.append((t0, fr))
        t0 += fr.get("duration") or 0
    n_to = rr * cc
    buoc = max(1, int(np.ceil(len(tam) * n_to / TOI_DA_KHUNG)))   # lấy 1 khung mỗi `buoc` khung

    def mot(a):
        t0, fr = a
        try:
            im = Image.open(io.BytesIO(_lay(fr["url"]))).convert("RGB")
        except Exception:                                    # noqa: BLE001
            return []
        dt = (fr.get("duration") or 0) / n_to
        o = []
        for k in range(n_to):
            t = t0 + k * dt
            if (tong and t >= tong) or ((k // cc) + 1) * H > im.height:
                break
            o.append((t, im.crop(((k % cc) * W, (k // cc) * H, (k % cc + 1) * W, (k // cc + 1) * H))))
        return o

    ra = []
    with ThreadPoolExecutor(6) as ex:
        for o in ex.map(mot, tam):
            ra += o
    ra = ra[::buoc] if buoc > 1 else ra
    return [t for t, _ in ra], [im for _, im in ra], tong


def storyboard(vid):
    """(t, e, tong): mốc giây + vector SigLIP các khung storyboard của video YouTube (có cache)."""
    import nhung_siglip
    thu = os.path.join(CACHE_CHUNG, "storyboard_" + nhung_siglip._NGAN)    # noqa: SLF001  (dùng chung mọi dự án)
    os.makedirs(thu, exist_ok=True)
    npz = os.path.join(thu, vid + ".npz")
    if os.path.isfile(npz):
        d = np.load(npz)
        return d["t"], d["e"], float(d["tong"])
    t, ims, tong = _khung_storyboard(vid)
    e = nhung_siglip.nhung_anh(ims) if ims else np.zeros((0, 1), np.float32)
    t = np.asarray(t, np.float32)
    if len(t) or tong:
        np.savez(npz, t=t, e=e, tong=tong)
    return t, e, tong


def diem_khung(e, t, qv):
    """(điểm, giây khớp nhất) — trung bình trượt 3 khung cao nhất."""
    if len(t) < 1:
        return -1.0, 0.0
    s = e @ qv
    k = min(3, len(s))
    cs = np.convolve(s, np.ones(k) / k, mode="valid")
    i = int(np.argmax(cs))
    j = i + int(np.argmax(s[i:i + k]))
    return float(cs[i]), float(t[j])


def diem_video(ids, qv, luong=6):
    """{id: {diem, t}} cho danh sách id YouTube."""
    def mot(v):
        try:
            t, e, _ = storyboard(v)
            d, giay = diem_khung(e, t, qv)
            return v, {"diem": round(d, 4), "t": round(giay, 1)}
        except Exception as ex:                              # noqa: BLE001
            log(f"    ! storyboard {v}: {str(ex)[:80]}")
            return v, {"diem": -1, "t": 0}
    with ThreadPoolExecutor(luong) as ex:
        return dict(ex.map(mot, ids))


def diem_anh(urls, qv, luong=8, chu=False):
    """[điểm] cho danh sách URL ảnh (thường là ảnh thu nhỏ); ảnh không tải được = -1.
    chu=True: trả thêm [có chữ] (dò chữ trên ảnh thu nhỏ, tính cả góc — user: ảnh bắt buộc không có chữ)."""
    from PIL import Image
    import nhung_siglip

    def mot(u):
        try:
            return Image.open(io.BytesIO(_lay(u, 15))).convert("RGB")
        except Exception:                                    # noqa: BLE001
            return None
    with ThreadPoolExecutor(luong) as ex:
        ims = list(ex.map(mot, urls))
    co = [i for i, im in enumerate(ims) if im is not None]
    ra = [-1.0] * len(urls)
    if co:
        e = nhung_siglip.nhung_anh([ims[i] for i in co])
        for i, d in zip(co, e @ qv):
            ra[i] = round(float(d), 4)
    if not chu:
        return ra
    import loc_chu
    co_chu = [None] * len(urls)
    for i in co:
        try:
            im = ims[i]
            im.thumbnail((loc_chu.W, loc_chu.W))
            co_chu[i] = bool(loc_chu.dien_tich_chu(np.asarray(im), bo_goc=False) > loc_chu.NGUONG_DIEN_TICH)
        except Exception:                                    # noqa: BLE001
            pass
    return ra, co_chu


def nhung_url(urls, luong=16, bao=None, cho=8):
    """(chỉ số tải được, ma trận vector SigLIP) cho danh sách URL ảnh (ảnh thu nhỏ của kết quả tìm).
    13/10 (đo: 3.022 ảnh, 4 luồng, chờ 15 s, không cache -> kẹt hàng chục phút khi mạng chập chờn): 16 luồng, chờ tối
    đa `cho` s mỗi ảnh, CACHE vector theo URL ở cache/vec_url_<model>/ (chạy lại không tải lại), báo tiến độ qua
    bao(xong, tong) mỗi lô."""
    import hashlib
    import nhung_siglip
    from PIL import Image
    thu = os.path.join(CACHE_CHUNG, "vec_url_" + nhung_siglip.MO_HINH.split("/")[-1])
    os.makedirs(thu, exist_ok=True)

    def tep(u):
        return os.path.join(thu, hashlib.md5(u.encode("utf-8")).hexdigest() + ".npy")
    vec = [None] * len(urls)
    for k, u in enumerate(urls):
        f = tep(u)
        if os.path.isfile(f):
            try:
                vec[k] = np.load(f)
            except Exception:                                # noqa: BLE001
                pass
    can = [k for k in range(len(urls)) if vec[k] is None]

    def mot(u):
        try:
            return Image.open(io.BytesIO(_lay(u, cho))).convert("RGB")
        except Exception:                                    # noqa: BLE001
            return None
    xong = len(urls) - len(can)
    if bao:
        bao(xong, len(urls))
    LO = 256
    with ThreadPoolExecutor(luong) as ex:
        for a in range(0, len(can), LO):
            lo = can[a:a + LO]
            ims = list(ex.map(mot, [urls[k] for k in lo]))
            co_lo = [(k, im) for k, im in zip(lo, ims) if im is not None]
            if co_lo:
                E = nhung_siglip.nhung_anh([im for _, im in co_lo])
                for (k, _), v in zip(co_lo, E):
                    vec[k] = v
                    np.save(tep(urls[k]), v)
            xong += len(lo)
            if bao:
                bao(xong, len(urls))
    co = [k for k in range(len(urls)) if vec[k] is not None]
    return co, (np.stack([vec[k] for k in co]) if co else np.zeros((0, 1), np.float32))


def vec_canh(canh=None, q=""):
    """Vector truy vấn: theo cảnh (câu 'nên chiếu' + từ khoá video) nếu có, không thì theo chính từ khoá tìm."""
    import nhung_siglip
    if canh and canh.get("canh_en"):                         # 12/10: mô tả khung hình tiếng Anh (mo_ta_canh.py)
        return nhung_siglip.vec_mo_ta(canh["canh_en"][0], canh["canh_en"][1:])
    if canh:
        return nhung_siglip.vec_mo_ta(canh.get("noi_dung") or canh.get("text", ""), (canh.get("video") or [])[:2])
    return nhung_siglip.nhung_chu([q])[0]
