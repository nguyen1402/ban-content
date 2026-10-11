# -*- coding: utf-8 -*-
"""Bước 4 — tải ĐÚNG đoạn đã chọn (độ phân giải cao), vá ô thiếu bằng ảnh Commons / thẻ
báo thiếu, dựng clip 1920x1080 rồi sinh bản nháp CapCut + SRT + báo cáo."""
import os
import re
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from common import (FFMPEG, OUT, YTDLP, YT_JS, chay, doc_json, duong_cache, ghi_json, log)

W, H, FPS = 1920, 1080, 30
FONT = "C\\:/Windows/Fonts/arial.ttf"


_KHOA_FULL = {}


def chat_luong():
    """Chiều cao tối đa (px) của đoạn dựng: 360 = cắt thẳng từ bản xem trước 360p (rất nhanh nhưng MỜ khi phóng lên
    1080p); 720/1080 = tải riêng ĐÚNG đoạn đã chọn ở độ phân giải đó. Đặt bằng chay.py --chat-luong (mặc định 1080)."""
    try:
        return int(os.environ.get("BC_CHAT_LUONG", "720"))
    except ValueError:
        return 720


def _file_xem_truoc(vid):
    d = duong_cache("xem_truoc")
    for f in os.listdir(d):
        if f.startswith(vid + ".") and not f.endswith((".part", ".ytdl")):
            return os.path.join(d, f)
    return None


def _tai_doan(o):
    """Trả (nguồn, lệch) để ffmpeg cắt [bd, bd+dai]: nguồn là file/URL, lệch là giây bắt đầu TRONG nguồn đó.
    Độ phân giải cao: link trực tiếp (Archive/Commons) -> ffmpeg cắt thẳng qua HTTP; còn lại tải ĐÚNG đoạn bằng yt-dlp.
    Không được thì lùi về bản xem trước 360p."""
    cao = chat_luong()
    if cao > 360:
        if o.get("url"):
            return o["url"], o["bd"]
        # Tải CẢ video MỘT LẦN ở <=cao (video không tiếng) rồi cắt nhiều đoạn từ file đó. Cách "chỉ tải đúng đoạn"
        # (--download-sections) bị YouTube bóp còn ~5 KB/s: đoạn 5 giây mất 6 phút.
        ten = f"full_{o['id']}_{cao}"
        d_ = os.path.dirname(duong_cache("doan_tho", "x"))
        tim = lambda: next((os.path.join(d_, f) for f in os.listdir(d_)
                            if f.startswith(ten + ".") and not f.endswith((".part", ".ytdl"))), None)
        with _KHOA_FULL.setdefault(o["id"], threading.Lock()):       # nhiều đoạn cùng một video: chỉ một luồng tải, luồng kia chờ
            p = tim()
            if not (p and os.path.getsize(p) > 10000):
                mau = duong_cache("doan_tho", ten + ".%(ext)s")
                chay([YTDLP, *YT_JS, "--no-warnings", "-q", "--no-playlist", "--max-filesize", "700M",
                      "-f", f"bv*[height<={cao}][ext=mp4]/bv*[height<={cao}]/bv*",
                      "--ffmpeg-location", os.path.dirname(FFMPEG),
                      "-o", mau, o.get("trang") or f"https://www.youtube.com/watch?v={o['id']}"], timeout=1800)
                p = tim()
        if p and os.path.getsize(p) > 10000:
            return p, o["bd"]
        log(f"    ! không tải được đoạn {cao}p của {o['id']} — dùng bản xem trước 360p")
    p = _file_xem_truoc(o["id"])
    return (p, o["bd"]) if p else None


def _render_video(src, dai, dich, lech):
    import sach_hinh
    cat = None
    try:
        cat = sach_hinh.vung_cat(src, lech, dai)            # viền đen / khung nhỏ lọt trong khung
    except Exception:                                       # noqa: BLE001
        pass
    vf = ((f"crop={cat}," if cat else "") +
          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"fps={FPS},format=yuv420p")
    rc, _, err = chay([FFMPEG, "-y", "-v", "error", "-ss", f"{lech:.2f}", "-i", src,
                       "-t", f"{dai:.2f}", "-an", "-vf", vf, "-c:v", "libx264",
                       "-preset", "veryfast", "-crf", "18", dich], timeout=600)
    return rc == 0 and os.path.isfile(dich)


def _render_anh(img, dai, dich):
    """Ảnh TĨNH phủ khung 16:9 (không zoom/lia — hiệu ứng để bước dựng sau làm)."""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p")
    rc, _, _ = chay([FFMPEG, "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS),
                     "-i", img, "-t", f"{dai:.2f}", "-vf", vf, "-c:v", "libx264",
                     "-preset", "veryfast", "-crf", "18", dich], timeout=600)
    return rc == 0 and os.path.isfile(dich)


def _render_the_thieu(canh, o, dich):
    txt = duong_cache("the", f"{canh['id']}.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write(f"THIEU HINH - canh {canh['id']}\n{canh.get('mo_ta', '')[:110]}")
    tf = txt.replace("\\", "/").replace(":", "\\:")
    vf = (f"drawtext=fontfile='{FONT}':textfile='{tf}':fontcolor=white:fontsize=44:"
          f"x=(w-text_w)/2:y=(h-text_h)/2,format=yuv420p")
    rc, _, _ = chay([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
                     f"color=c=0x303030:s={W}x{H}:r={FPS}", "-t", f"{o['dai']:.2f}",
                     "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", dich], timeout=120)
    return rc == 0 and os.path.isfile(dich)


def va_bang_anh(canh_ds, tim):
    """Ô còn THIẾU -> thử ảnh Commons (chấm CLIP, ngưỡng nới hơn vì ảnh tĩnh)."""
    from PIL import Image
    import chon_doan as cdn
    for c in canh_ds:
        if not any(o.get("thieu") for o in c["o"]):
            continue
        ung = []
        for q in c.get("q", []):
            ung += (tim.get(q.strip().lower(), {}).get("wc") or [])
        seen, ds = set(), []
        for it in ung:
            if it["id"] not in seen:
                seen.add(it["id"])
                ds.append(it)
        imgs, giu = [], []
        for it in ds[:8]:
            p = duong_cache("anh", it["id"] + ".jpg")
            try:
                if not os.path.isfile(p):
                    req = urllib.request.Request(it["url"], headers={"User-Agent": "ban-content/0.1"})
                    with urllib.request.urlopen(req, timeout=40) as r, open(p, "wb") as f:
                        f.write(r.read())
                imgs.append(Image.open(p).convert("RGB"))
                giu.append((it, p))
            except Exception:                                  # noqa: BLE001
                continue
        if not imgs:
            continue
        qv = cdn.nhung_chu([c.get("mo_ta") or c["q"][0]])[0]
        s = cdn.nhung_anh(imgs) @ qv
        dung = set()
        for o in c["o"]:
            if not o.get("thieu"):
                continue
            for i in np.argsort(-s):
                if int(i) in dung:
                    continue
                if float(s[i]) >= cdn.NGUONG + 0.01:
                    it, p = giu[int(i)]
                    dai_o = o.get("dai") or round(c["dai"] / len(c["o"]), 2)
                    o.clear()
                    o.update({"anh": p, "dai": dai_o, "diem": round(float(s[i]), 4),
                              "tieu_de": it["tieu_de"], "nguon": "commons",
                              "giay_phep": it.get("giay_phep", "")})
                    dung.add(int(i))
                break
    return canh_ds


def _dai_nguon(vid):
    """Độ dài (giây) của video theo chỉ mục CLIP (khung cuối + bước); None nếu không biết."""
    try:
        t = np.load(duong_cache("chi_muc_l14", vid + ".npz"))["t"]
        return float(t[-1]) + 1.5
    except Exception:                                    # noqa: BLE001
        return None


def _noi_tiep_thieu(canh_ds):
    """Ô còn THIẾU (không đoạn/ảnh đạt) -> cho video của ô liền trước CHẠY TIẾP phủ lên, thay vì thẻ THIẾU:
    lấy đoạn kế ngay sau đoạn trước trong CÙNG video (nếu hết video thì lấy đoạn ngay trước nó)."""
    truoc = None
    n = 0
    for c in canh_ds:
        for o in c.get("o", []):
            if o.get("thieu"):
                if truoc is None:
                    continue
                dai = o.get("dai") or round(c["dai"] / max(len(c["o"]), 1), 2)
                tong = _dai_nguon(truoc["id"])
                bd = truoc["bd"] + truoc["dai"]
                if tong is not None and bd + dai > tong:
                    bd = max(0.0, truoc["bd"] - dai)
                    if bd + dai > truoc["bd"] + 0.01:     # không còn chỗ trước đó đủ dài
                        continue
                giu = {k: o[k] for k in ("nhip", "text") if k in o}
                o.clear()
                o.update(giu)
                o.update({k: truoc[k] for k in ("id", "tieu_de", "kenh", "nguon", "url", "trang") if k in truoc})
                o.update({"bd": round(bd, 2), "dai": dai, "diem": 0.0, "noi_tiep": True})
                n += 1
                truoc = o                                  # nhiều ô THIẾU liền nhau: ô sau chạy tiếp từ ô vừa phủ
                continue
            if o.get("id") and not o.get("anh") and not o.get("do_hoa"):
                truoc = o
    if n:
        log(f"    ô THIẾU được video liền trước chạy tiếp phủ lên: {n}")


def dung_clip(canh_ds, song_song=8):
    """Tải đoạn + render mỗi ô thành một clip. Trả danh sách clip theo thứ tự thời gian."""
    viec = []
    for c in canh_ds:
        for k, o in enumerate(c["o"]):
            viec.append((c, k, o))
    # dai của ô sau khi vá ảnh có thể mất; khôi phục từ cảnh
    for c, k, o in viec:
        o.setdefault("dai", round(c["dai"] / len(c["o"]), 2))
    _noi_tiep_thieu(canh_ds)

    def _lam(v):
        c, k, o = v
        dich = duong_cache("clip", f"{c['id']:04d}_{k}.mp4")
        ok = False
        if o.get("do_hoa") and o.get("clip") and os.path.isfile(o["clip"]):
            return v                                    # đồ họa Remotion đã dựng sẵn
        if o.get("anh"):
            ok = _render_anh(o["anh"], o["dai"], dich)
        elif not o.get("thieu"):
            for cand in [o] + list(o.get("alt") or []):
                tl = _tai_doan(cand)
                if tl and _render_video(tl[0], o["dai"], dich, tl[1]):
                    if cand is not o:
                        o.update({k: cand[k] for k in ("id", "bd", "diem", "tieu_de", "kenh", "url", "trang") if k in cand})
                    ok = True
                    break
        if not ok:
            o["thieu"] = True
            ok = _render_the_thieu(c, o, dich)
        o["clip"] = dich if ok else None
        return v

    log(f"[4] dựng {len(viec)} clip…")
    with ThreadPoolExecutor(song_song) as ex:
        for i, _ in enumerate(ex.map(_lam, viec), 1):
            if i % 10 == 0 or i == len(viec):
                from common import tien_do
                log(f"    dựng {i}/{len(viec)}")
                tien_do("dung", "dang", f"{i}/{len(viec)} clip")
    return canh_ds


def _srt_time(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def xuat_srt(canh_ds, path):
    with open(path, "w", encoding="utf-8") as f:
        for c in canh_ds:
            f.write(f"{c['id']}\n{_srt_time(c['bat_dau'])} --> "
                    f"{_srt_time(c['bat_dau'] + c['dai'])}\n{c['text']}\n\n")


def _dai_that(path):
    """Độ dài THẬT của clip (µs) — render làm tròn theo khung hình nên ngắn hơn dự định chút ít."""
    import cv2
    cap = cv2.VideoCapture(path)
    n, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS) or FPS
    cap.release()
    return int(n / fps * 1_000_000)


def xuat_nhap_capcut(canh_ds, ten, drafts_dir):
    import pycapcut as draft
    from pycapcut import trange
    folder = draft.DraftFolder(drafts_dir)
    script = folder.create_draft(ten, W, H, allow_replace=True)
    script.add_track(draft.TrackType.video, track_name="hinh")
    co_giong = any(c.get("giong") for c in canh_ds)
    if co_giong:
        script.add_track(draft.TrackType.audio, track_name="giong")
    t = 0
    for c in canh_ds:
        t0 = t
        for o in c["o"]:
            if not o.get("clip"):
                continue
            d = min(int(round(o["dai"] * 1_000_000)), _dai_that(o["clip"]) - 1000)
            script.add_segment(draft.VideoSegment(draft.VideoMaterial(o["clip"]),
                                                  trange(t, d)), track_name="hinh")
            t += d
        if co_giong and c.get("giong"):
            # không để giọng vượt phần hình của cảnh (hình bị làm tròn theo khung nên ngắn hơn
            # chút ít) — vượt là chồng lên cảnh sau và pycapcut từ chối ghi.
            ad = min(int(c["giong_dai"] * 1_000_000), max(t - t0, 0))
            if ad <= 0:
                continue
            script.add_segment(draft.AudioSegment(draft.AudioMaterial(c["giong"]),
                                                  trange(t0, ad)), track_name="giong")
    script.save()
    return t / 1e6


def noi_giong(canh_ds, path):
    """Nối giọng đọc của mọi cảnh thành MỘT file wav đúng mốc thời gian (khoảng lặng giữa các cảnh giữ nguyên)."""
    import wave
    co = [c for c in canh_ds if c.get("giong") and os.path.isfile(c["giong"])]
    if not co:
        return None
    with wave.open(co[0]["giong"], "rb") as w:
        kenh, rong, tan = w.getnchannels(), w.getsampwidth(), w.getframerate()
    khung = kenh * rong
    tong = int(round(max(c["bat_dau"] + c["dai"] for c in canh_ds) * tan)) + tan
    buf = bytearray(tong * khung)
    for c in co:
        with wave.open(c["giong"], "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (kenh, rong, tan):
                log(f"    ! cảnh {c['id']}: định dạng giọng khác, bỏ qua khi nối")
                continue
            data = w.readframes(w.getnframes())
        bd = int(round(c["bat_dau"] * tan)) * khung
        buf[bd:bd + len(data)] = data[:max(0, len(buf) - bd)]
    with wave.open(path, "wb") as w:
        w.setnchannels(kenh)
        w.setsampwidth(rong)
        w.setframerate(tan)
        w.writeframes(bytes(buf))
    return path


def xuat_nhap_giong(canh_ds, ten, drafts_dir):
    """Bản nháp CapCut CHỈ có giọng đọc (đúng mốc từng cảnh) + clip đồ hoạ Remotion (bản đồ, biểu đồ) đặt đúng chỗ;
    phần hình còn lại để trống cho người dùng tự kéo video/ảnh vào."""
    import pycapcut as draft
    from pycapcut import trange
    folder = draft.DraftFolder(drafts_dir)
    script = folder.create_draft(ten, W, H, allow_replace=True)
    if any(c.get("do_hoa_clip") for c in canh_ds):
        script.add_track(draft.TrackType.video, track_name="do_hoa")
    script.add_track(draft.TrackType.audio, track_name="giong")
    het = 0
    for c in canh_ds:
        t0 = int(round(c["bat_dau"] * 1_000_000))
        dai_canh = int(round(c["dai"] * 1_000_000))
        if c.get("giong") and os.path.isfile(c["giong"]):
            ad = min(int(c["giong_dai"] * 1_000_000), dai_canh)
            if ad > 0:
                script.add_segment(draft.AudioSegment(draft.AudioMaterial(c["giong"]), trange(t0, ad)),
                                   track_name="giong")
        for dh in c.get("do_hoa_clip") or []:
            if not os.path.isfile(dh["file"]):
                continue
            bd = t0 + int(round(dh["bd"] * 1_000_000))
            d = min(int(round(dh["dai"] * 1_000_000)), _dai_that(dh["file"]) - 1000, t0 + dai_canh - bd)
            if d > 0:
                script.add_segment(draft.VideoSegment(draft.VideoMaterial(dh["file"]), trange(bd, d)),
                                   track_name="do_hoa")
        het = max(het, t0 + dai_canh)
    script.save()
    return het / 1e6


def bao_cao(canh_ds, path):
    dong = ["# Báo cáo ghép hình\n",
            "| Cảnh | Giây | Nguồn | Điểm | Ghi chú |", "|---|---|---|---|---|"]
    thieu = 0
    for c in canh_ds:
        for k, o in enumerate(c["o"]):
            if o.get("thieu"):
                thieu += 1
                ng, gc = "**THIẾU**", c.get("mo_ta", "")[:70]
            elif o.get("anh"):
                ng, gc = f"ảnh {o.get('nguon', 'web')} ({o.get('giay_phep', '')})", o.get("tieu_de", "")[:70]
            elif o.get("do_hoa"):
                ng, gc = f"đồ họa Remotion ({o['do_hoa']})", ""
            else:
                ng = f"yt {o['id']} @{o['bd']:.0f}s"
                gc = (("⚠ CÒN CHỮ — " if o.get("co_chu") else "") +
                      f"{o.get('kenh', '')} — {o.get('tieu_de', '')[:60]}")
            dong.append(f"| {c['id']}.{k} | {o['dai']:.1f} | {ng} | {o.get('diem', 0):.3f} | {gc} |")
    n = sum(len(c["o"]) for c in canh_ds)
    dong.insert(1, f"\nTổng {n} ô hình, thiếu {thieu} ({thieu / max(n, 1):.0%}).\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(dong))
    return thieu, n
