# -*- coding: utf-8 -*-
"""Kho tài nguyên CapCut trên máy: danh mục (chuyển cảnh, hiệu ứng chữ, nhãn dán nhấn mạnh, bộ lọc, hiệu ứng
video) đọc từ rp.db của CapCut, tải/cài gói tài nguyên, và phân loại kho âm thanh đã tải.

  python kho_capcut.py danh-muc            # quét rp.db -> cache/kho/danh_muc.json
  python kho_capcut.py am-thanh            # phân loại nhạc/SFX trong cache CapCut -> cache/kho/am_thanh.json
  python kho_capcut.py cai <effect_id>     # tải + cài một gói vào cache CapCut
"""
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import FFMPEG, ROOT, doc_json, ghi_json, log          # noqa: E402

CAP = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CapCut", "User Data", "Cache")
KHO = os.path.join(ROOT, "cache", "kho")
os.makedirs(KHO, exist_ok=True)

#: effect_type của CapCut -> tên loại dùng trong skill
LOAI = {"13": "chuyen_canh", "18": "chu_hoat_anh", "2": "nhan_dan", "8": "hieu_ung_video",
        "12": "bo_loc", "22": "bo_loc_2", "1": "mau_chu"}


# --------------------------------------------------------------------------- danh mục
def _la_vip(o):
    """Mục tính phí (cần gói VIP của CapCut)? Đọc cờ is_vip trong extra / business_info."""
    try:
        e = o.get("extra")
        e = json.loads(e) if isinstance(e, str) else (e or {})
        if e.get("is_vip"):
            return True
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        return bool(json.loads((o.get("business_info") or {}).get("json_str", "{}")).get("is_vip"))
    except (ValueError, TypeError, AttributeError):
        return False


def _mo_rp_db():
    base = os.path.join(CAP, "ressdk_db")
    dbs = sorted((os.path.join(base, d, "rp.db") for d in os.listdir(base)
                  if os.path.isfile(os.path.join(base, d, "rp.db"))), key=os.path.getmtime, reverse=True)
    if not dbs:
        raise FileNotFoundError("không thấy rp.db của CapCut")
    tmp = tempfile.mkdtemp(prefix="kho_capcut_")                   # chép cả .wal/.shm, không đụng file gốc
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(dbs[0] + ext):
            shutil.copy(dbs[0] + ext, os.path.join(tmp, "rp.db" + ext))
    return sqlite3.connect(os.path.join(tmp, "rp.db")), tmp


def quet_danh_muc():
    """Đọc mọi panel đã được CapCut lưu (chỉ những gì bạn đã mở xem trong app) -> danh mục có link tải."""
    con, tmp = _mo_rp_db()
    items = {}
    try:
        for (b,) in con.execute("select response_body from http_cache where url like '%get_panel_info%' "
                                "or url like '%get_resources_by_category%'"):
            raw = b if isinstance(b, (bytes, bytearray)) else str(b or "").encode("utf-8", "ignore")
            if raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except Exception:                                  # noqa: BLE001
                    continue
            try:
                d = json.loads(raw.decode("utf-8", "ignore"))
            except ValueError:
                continue

            def duyet(o):
                if isinstance(o, dict):
                    if "effect_type" in o and "title" in o and o.get("item_urls"):
                        loai = LOAI.get(str(o["effect_type"]))
                        if loai:
                            items.setdefault(loai, {})[str(o["id"])] = {
                                "id": str(o["id"]), "ten": o["title"], "md5": o.get("md5", ""),
                                "url": o["item_urls"][0], "sub_type": o.get("sub_type", ""),
                                "mo_ta": o.get("description", ""), "vip": _la_vip(o)}
                    for v in o.values():
                        duyet(v)
                elif isinstance(o, list):
                    for v in o:
                        duyet(v)
            duyet(d)
    finally:
        con.close()
        shutil.rmtree(tmp, ignore_errors=True)
    ra = {k: list(v.values()) for k, v in items.items()}
    ghi_json(os.path.join(KHO, "danh_muc.json"), ra)
    for k, v in ra.items():
        log(f"  {k}: {len(v)} mục")
    return ra


# --------------------------------------------------------------------------- cài gói
def thu_muc_cai(item):
    return os.path.join(CAP, "effect", item["id"], item["md5"])


def da_cai(item):
    return os.path.isdir(thu_muc_cai(item)) and bool(os.listdir(thu_muc_cai(item)))


def cai_goi(item):
    """Tải gói zip từ CDN của CapCut (link lấy từ chính kho CapCut), kiểm md5, giải nén vào cache/effect/<id>/<md5>/."""
    if da_cai(item):
        return thu_muc_cai(item)
    req = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        b = r.read()
    if item.get("md5") and hashlib.md5(b).hexdigest() != item["md5"]:
        raise ValueError(f"md5 không khớp cho {item['ten']}")
    dich = thu_muc_cai(item)
    os.makedirs(dich, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        z.extractall(dich)
    return dich


# --------------------------------------------------------------------------- âm thanh
def _giai_ma(path, sr=16000, toi_da=240):
    p = subprocess.run([FFMPEG, "-v", "error", "-t", str(toi_da), "-i", path, "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    return np.frombuffer(p.stdout, np.float32), sr


def phan_tich_file(path):
    x, sr = _giai_ma(path)
    if len(x) < sr * 0.05:
        return None
    dai = len(x) / sr
    hop = 512
    n = (len(x) - 1024) // hop
    if n < 4:
        return {"dai": round(dai, 2), "loai": "sfx", "kieu": "pop"}
    rms = np.array([np.sqrt(np.mean(x[i * hop:i * hop + 1024] ** 2)) for i in range(n)])
    fr = np.fft.rfftfreq(1024, 1 / sr)
    cen = np.array([np.sum(fr * np.abs(np.fft.rfft(x[i * hop:i * hop + 1024] * np.hanning(1024)))) /
                    (np.sum(np.abs(np.fft.rfft(x[i * hop:i * hop + 1024] * np.hanning(1024)))) + 1e-9)
                    for i in range(0, n, 2)])
    do_to = float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9))
    dinh = int(np.argmax(rms))
    vt_dinh = dinh / n
    ra = {"dai": round(dai, 2), "do_to_db": round(do_to, 1), "sang_hz": int(np.mean(cen)),
          "vt_dinh": round(vt_dinh, 2)}
    if dai < 6:
        ra["loai"] = "sfx"
        nua1, nua2 = rms[:n // 2].mean(), rms[n // 2:].mean()
        if dai < 0.7:
            ra["kieu"] = "pop"
        elif vt_dinh < 0.25:
            ra["kieu"] = "hit" if ra["sang_hz"] < 2500 else "ting"          # đập mạnh rồi tắt dần
        elif nua2 > nua1 * 1.8 and vt_dinh > 0.6:
            ra["kieu"] = "riser"                                           # tăng dần về cuối
        elif 0.15 < vt_dinh < 0.75 and ra["sang_hz"] > 1800:
            ra["kieu"] = "whoosh"                                          # vút qua, đỉnh giữa, nhiều nhiễu
        else:
            ra["kieu"] = "khac"
    elif dai < 30:
        ra["loai"] = "doan_ngan"
    else:
        ra["loai"] = "nhac"
        env = rms - rms.mean()
        ac = np.correlate(env, env, "full")[len(env) - 1:]
        lo, hi = int(60 / 180 * sr / hop), int(60 / 60 * sr / hop)           # 60-180 BPM
        k = lo + int(np.argmax(ac[lo:hi])) if hi < len(ac) else lo
        bpm = 60 * sr / hop / k
        while bpm < 70:
            bpm *= 2
        while bpm > 160:
            bpm /= 2
        ra["bpm"] = int(round(bpm))
        # nhãn thô (heuristic) — sửa tay ở am_thanh_nhan_tay.json nếu cần
        if bpm < 90 and ra["sang_hz"] < 2200:
            ra["tam_trang"] = "tram_huyen_bi"
        elif bpm < 110:
            ra["tam_trang"] = "dien_anh"
        elif ra["do_to_db"] > -18:
            ra["tam_trang"] = "soi_dong"
        else:
            ra["tam_trang"] = "nhe_nhang"
    return ra


def quet_am_thanh():
    thu_muc = os.path.join(CAP, "music")
    kq = {}
    fs = sorted(f for f in os.listdir(thu_muc) if f.endswith(".mp3"))
    for i, f in enumerate(fs, 1):
        try:
            r = phan_tich_file(os.path.join(thu_muc, f))
        except Exception as e:                                         # noqa: BLE001
            r = None
            log(f"  ! {f}: {e}")
        if r:
            r["file"] = os.path.join(thu_muc, f)
            kq[f] = r
        if i % 40 == 0:
            log(f"  {i}/{len(fs)}")
    tay = doc_json(os.path.join(ROOT, "chinh_sua", "am_thanh_nhan_tay.json"), {})
    for f, nhan in tay.items():
        if f in kq:
            kq[f].update(nhan)
    ghi_json(os.path.join(KHO, "am_thanh.json"), kq)
    dem = {}
    for v in kq.values():
        k = v.get("kieu") or v.get("tam_trang") or v["loai"]
        dem[(v["loai"], k)] = dem.get((v["loai"], k), 0) + 1
    for k, v in sorted(dem.items()):
        log(f"  {k[0]:10s} {k[1]:16s} {v}")
    return kq


if __name__ == "__main__":
    lenh = sys.argv[1] if len(sys.argv) > 1 else ""
    if lenh == "danh-muc":
        quet_danh_muc()
    elif lenh == "am-thanh":
        quet_am_thanh()
    elif lenh == "cai":
        dm = doc_json(os.path.join(KHO, "danh_muc.json"), {})
        tim = [it for v in dm.values() for it in v if it["id"] == sys.argv[2]]
        print(cai_goi(tim[0]) if tim else "không thấy id")
    else:
        print(__doc__)
