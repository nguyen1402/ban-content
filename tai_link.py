# -*- coding: utf-8 -*-
"""Tải các video YouTube (hoặc trang yt-dlp hỗ trợ) do người dùng dán link về ra/<dự án>/video_tai/.

    python tai_link.py <dự án>            # đọc kich_ban/<dự án>.link.txt (mỗi dòng một link)

Bản <=1080p, có tiếng, gộp thành mp4 để kéo thẳng vào CapCut. Tiến độ từng link ghi vào
ra/<dự án>/tai_link.json cho giao diện đọc. Link đã tải xong (có file) thì bỏ qua."""
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from common import FFMPEG, YTDLP, YT_JS, thu_muc_du_an  # noqa: E402


def doc_link(du_an):
    p = os.path.join(ROOT, "kich_ban", f"{du_an}.link.txt")
    try:
        with open(p, encoding="utf-8") as f:
            return list(dict.fromkeys(l.strip() for l in f if l.strip().startswith("http")))
    except OSError:
        return []


def main():
    du_an = sys.argv[1]
    _cache, out = thu_muc_du_an(du_an)
    thu = os.path.join(out, "video_tai")
    os.makedirs(thu, exist_ok=True)
    tt_path = os.path.join(out, "tai_link.json")
    links = doc_link(du_an)
    tt = {u: {"tt": "cho", "pt": 0.0, "file": "", "loi": ""} for u in links}

    def ghi():
        tmp = tt_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"cap_nhat": time.time(), "links": [dict(url=u, **v) for u, v in tt.items()]}, f, ensure_ascii=False)
        os.replace(tmp, tt_path)

    ghi()
    for u in links:
        tt[u]["tt"] = "dang"
        ghi()
        lenh = [YTDLP, *YT_JS, "--no-playlist", "--newline", "--no-warnings", "--no-overwrites", "--no-part",
                "-f", "bv*+ba/b", "-S", "res:1080,vcodec:h264,acodec:m4a",
                "--merge-output-format", "mp4", "--ffmpeg-location", os.path.dirname(FFMPEG),
                "--progress-template", "download:PT %(progress._percent_str)s",
                "--print", "after_move:FILE %(filepath)s",
                "-o", os.path.join(thu, "%(title).80B [%(id)s].%(ext)s"), u]
        p = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             creationflags=0x08000000 if os.name == "nt" else 0)
        cuoi = []
        lan_ghi = 0.0
        for dong in iter(p.stdout.readline, b""):
            s = dong.decode("utf-8", "ignore").strip()
            if not s:
                continue
            cuoi = (cuoi + [s])[-6:]
            m = re.match(r"PT\s+([\d.]+)%", s)
            if m:
                tt[u]["pt"] = float(m.group(1))
                if time.time() - lan_ghi > 1.0:
                    ghi()
                    lan_ghi = time.time()
            elif s.startswith("FILE "):
                tt[u]["file"] = s[5:].strip()
            elif "has already been downloaded" in s:
                m2 = re.search(r"\[download\]\s+(.+?) has already been downloaded", s)
                if m2:
                    tt[u]["file"] = m2.group(1).strip()
        p.wait()
        if p.returncode == 0 and tt[u]["file"]:
            tt[u].update(tt="xong", pt=100.0)
        else:
            tt[u].update(tt="loi", loi=" | ".join(x for x in cuoi if "ERROR" in x)[-300:] or f"mã {p.returncode}")
        ghi()


if __name__ == "__main__":
    main()
