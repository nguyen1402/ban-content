# -*- coding: utf-8 -*-
"""Kho NHẠC NỀN lấy từ YouTube (kênh nhạc 'no copyright') theo tâm trạng của chủ đề.

  python nhac_youtube.py            # tìm + tải ~3 bài mỗi tâm trạng -> cache/nhac_yt/<tam_trang>/<id>.mp3
Kết quả: cache/kho/nhac_youtube.json (đã phân tích độ to/nhịp) và ra/nhac_nguon.txt (tiêu đề, kênh, link để ghi vào mô tả).

Lưu ý: 'no copyright' là lời của kênh đăng, không phải bảo đảm pháp lý — kiểm tra mô tả từng bài nếu cần ghi công."""
import json
import os
import subprocess
import sys

AQ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQ)
for p in (ROOT, AQ):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import FFMPEG, OUT, YTDLP, YT_JS, duong_cache, ghi_json, log        # noqa: E402
import kho_capcut                                                               # noqa: E402

TRUY_VAN = {
    "dien_anh": ["documentary cinematic background music no copyright",
                 "cinematic nature documentary music no copyright"],
    "huyen_bi": ["mysterious dark ambient documentary music no copyright",
                 "mystery documentary cinematic music no copyright"],
    "soi_dong": ["tense cinematic suspense background music no copyright",
                 "tension cinematic documentary music no copyright"],
    "nhe_nhang": ["gentle hopeful emotional nature piano music no copyright",
                  "peaceful hopeful piano background music no copyright"],
}
LOAI_TRU = ("horror", "scary", "halloween", "trailer", "fantasy", "metal", "rock", "edm", "phonk", "lofi", "lo-fi",
            "christmas", "sad violin", "boxing")
MOI_TAM_TRANG = 3


def _tim(q):
    p = subprocess.run([YTDLP, *YT_JS, "--no-warnings", "--flat-playlist", "-J", f"ytsearch14:{q}"],
                       capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        return json.loads(p.stdout.decode("utf-8", "ignore")).get("entries") or []
    except ValueError:
        return []


def _tai(vid, dich):
    if os.path.isfile(dich) and os.path.getsize(dich) > 100_000:
        return True
    subprocess.run([YTDLP, *YT_JS, "--no-warnings", "-q", "--no-playlist", "-f", "bestaudio", "-x",
                    "--audio-format", "mp3", "--audio-quality", "5", "--ffmpeg-location", os.path.dirname(FFMPEG),
                    "-o", dich[:-4] + ".%(ext)s", f"https://www.youtube.com/watch?v={vid}"],
                   capture_output=True, timeout=900, creationflags=0x08000000 if os.name == "nt" else 0)
    return os.path.isfile(dich) and os.path.getsize(dich) > 100_000


def lay_nhac():
    kq, nguon = {}, []
    for mood, qs in TRUY_VAN.items():
        da, thu_muc = 0, duong_cache("nhac_yt", mood, "x")
        thu_muc = os.path.dirname(thu_muc)
        seen = set()
        for q in qs:
            for e in _tim(q):
                d = e.get("duration") or 0
                t = (e.get("title") or "").lower()
                if e["id"] in seen or not (120 <= d <= 420) or any(w in t for w in LOAI_TRU):
                    continue
                seen.add(e["id"])
                dich = os.path.join(thu_muc, e["id"] + ".mp3")
                if not _tai(e["id"], dich):
                    log(f"  ! không tải được {e['id']}")
                    continue
                r = kho_capcut.phan_tich_file(dich)
                if not r:
                    continue
                r.update({"file": dich, "loai": "nhac", "tam_trang": mood, "nguon": "youtube", "id": e["id"],
                          "tieu_de": e.get("title", ""), "kenh": e.get("channel", "")})
                kq[e["id"]] = r
                nguon.append(f"{mood}\t{e.get('title', '')}\t{e.get('channel', '')}\thttps://www.youtube.com/watch?v={e['id']}")
                da += 1
                log(f"  {mood}: {e.get('channel', '')[:22]} — {e.get('title', '')[:50]} ({d:.0f}s, {r['do_to_db']} dB)")
                if da >= MOI_TAM_TRANG:
                    break
            if da >= MOI_TAM_TRANG:
                break
    ghi_json(os.path.join(kho_capcut.KHO, "nhac_youtube.json"), kq)
    with open(os.path.join(OUT, "nhac_nguon.txt"), "w", encoding="utf-8") as f:
        f.write("tam_trang\ttieu_de\tkenh\tlink\n" + "\n".join(nguon) + "\n")
    return kq


if __name__ == "__main__":
    lay_nhac()
