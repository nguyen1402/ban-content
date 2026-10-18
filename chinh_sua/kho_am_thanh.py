# -*- coding: utf-8 -*-
"""KHO ÂM THANH SẠCH & KHÔNG BẢN QUYỀN (100% YouTube Audio Library, CC0, Pixabay).
Quét thư mục kho_am_thanh/ (nhạc theo tâm trạng + SFX chuyên dụng),
đo độ dài và độ to (loudness) qua FFmpeg, xuất cache/kho/kho_am_thanh_chuan.json.
"""
import json
import os
import re
import subprocess
import sys

AQ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQ)
for p in (ROOT, AQ):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import FFMPEG, doc_json, ghi_json, log
import kho_capcut

KHO_GOC = os.path.join(ROOT, "kho_am_thanh")
FILE_CACHE = os.path.join(kho_capcut.KHO, "kho_am_thanh_chuan.json")


def _do_to_va_dai(path):
    """Dùng FFmpeg volumedetect để đo max_volume / mean_volume và độ dài."""
    cmd = [FFMPEG, "-i", path, "-af", "volumedetect", "-vn", "-sn", "-dn", "-f", "null", "NUL" if os.name == "nt" else "/dev/null"]
    p = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000 if os.name == "nt" else 0)
    out = p.stderr or ""
    
    # Độ dài
    m_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out)
    dai = 0.0
    if m_dur:
        h, m, s = m_dur.groups()
        dai = int(h) * 3600 + int(m) * 60 + float(s)
        
    # Độ to trung bình
    m_vol = re.search(r"mean_volume:\s*(-?[\d\.]+)\s*dB", out)
    do_to = float(m_vol.group(1)) if m_vol else -18.0
    
    return round(dai, 2), round(do_to, 1)


def quet_kho_chuan(force=False):
    """Quét toàn bộ nhạc và SFX trong kho_am_thanh/."""
    da = doc_json(FILE_CACHE, {}) if not force else {}
    os.makedirs(KHO_GOC, exist_ok=True)
    kq = {}
    
    # 1. Nhạc nền theo tâm trạng
    nhac_dir = os.path.join(KHO_GOC, "nhac")
    if os.path.isdir(nhac_dir):
        for mood in os.listdir(nhac_dir):
            m_path = os.path.join(nhac_dir, mood)
            if not os.path.isdir(m_path):
                continue
            for fn in os.listdir(m_path):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
                    continue
                fp = os.path.join(m_path, fn)
                fid = f"nhac_{mood}_{fn}"
                if fid in da and os.path.getmtime(fp) <= da[fid].get("mtime", 0):
                    kq[fid] = da[fid]
                    continue
                dai, do_to = _do_to_va_dai(fp)
                if dai <= 0:
                    continue
                item = {
                    "id": fid,
                    "ten": os.path.splitext(fn)[0],
                    "file": fp,
                    "loai": "nhac",
                    "tam_trang": mood,
                    "dai": dai,
                    "do_to_db": do_to,
                    "mtime": os.path.getmtime(fp),
                    "nguon": "kho_chuan"
                }
                kq[fid] = item
                log(f"  [Nhạc - {mood}] {item['ten']} ({dai:.1f}s, {do_to} dB)")

    # 2. SFX theo mục đích sử dụng
    sfx_dir = os.path.join(KHO_GOC, "sfx")
    kieu_map = {
        "chuyen_canh": "whoosh",
        "nhan_manh": "hit",
        "moi_truong": "moi_truong"
    }
    if os.path.isdir(sfx_dir):
        for sub, kieu in kieu_map.items():
            s_path = os.path.join(sfx_dir, sub)
            if not os.path.isdir(s_path):
                continue
            for fn in os.listdir(s_path):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
                    continue
                fp = os.path.join(s_path, fn)
                fid = f"sfx_{sub}_{fn}"
                if fid in da and os.path.getmtime(fp) <= da[fid].get("mtime", 0):
                    kq[fid] = da[fid]
                    continue
                dai, do_to = _do_to_va_dai(fp)
                if dai <= 0:
                    continue
                item = {
                    "id": fid,
                    "ten": os.path.splitext(fn)[0],
                    "file": fp,
                    "loai": "sfx",
                    "kieu": kieu,
                    "muc_dich": sub,
                    "dai": dai,
                    "do_to_db": do_to,
                    "mtime": os.path.getmtime(fp),
                    "nguon": "kho_chuan"
                }
                kq[fid] = item
                log(f"  [SFX - {sub}] {item['ten']} ({dai:.2f}s, {do_to} dB)")

    ghi_json(FILE_CACHE, kq)
    return kq


if __name__ == "__main__":
    print(f"Quét kho âm thanh chuẩn: {KHO_GOC}")
    res = quet_kho_chuan(force=True)
    nhac_n = sum(1 for v in res.values() if v["loai"] == "nhac")
    sfx_n = sum(1 for v in res.values() if v["loai"] == "sfx")
    print(f"Tổng kết: {nhac_n} bài nhạc, {sfx_n} hiệu ứng âm thanh -> {FILE_CACHE}")
