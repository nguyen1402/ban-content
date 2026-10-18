# -*- coding: utf-8 -*-
"""HIỆU ỨNG kiểu video mẫu kênh user (12/10) — đặt trên track 'hieu_ung' (trên track hình, dưới thẻ ảnh phủ):

  * BẢN ĐỒ ĐƯỜNG ĐI A -> B: ChatGPT tìm câu nói về di chuyển / lan rộng từ nơi này tới nơi kia -> Remotion bản đồ
    vệ tinh, đường vàng cong vẽ dần (nen_ban_do.dung_clip_duong), phủ toàn khung trong lúc đọc câu đó.
  * KHUNG HIGHLIGHT VIỀN VÀNG: câu chỉ vào một CHI TIẾT nhỏ (bộ phận, cấu trúc) -> dựng sẵn bằng ffmpeg từ chính đoạn
    hình đang chiếu: giữa khung là "kính lúp" bo góc viền vàng phóng to phần giữa cảnh, nền vẫn là cảnh đó.
  * PHỦ MÀU khi đổi chương: một lớp màu ấm lướt qua ~1 s (PNG một màu, keyframe độ mờ 0 -> 0,45 -> 0).
Các hiệu ứng không chồng nhau trên cùng track (ưu tiên đường đi > highlight > phủ màu)."""
import os
import subprocess

from common import FFMPEG, hoi_nhieu, log, rut_json

CAU_MOI_DOAN = 20
PHONG_BAT = False          # 12/10 user: bỏ "khoanh highlight không có ảnh" (kính lúp viền vàng) — thay bằng thẻ ảnh 65% + chữ
_P = """You are the editor of a Vietnamese documentary video. Below is ONE PASSAGE of the narration (sentence index. text).
Find ONLY these two kinds of sentences:
(a) "duong": the sentence describes MOVEMENT, TRAVEL, SPREAD or SHIPPING from one NAMED real place to ANOTHER named real place (country, region, city, port) — both must be proper geographic names on a world map, far apart, and neither inside the other. NOT generic places like "the apiary", "home", "nearby forests", "an area". Give "tu" and "den" as English place names WITH country (e.g. "Bordeaux, France"), and "tu_vi" / "den_vi" as the short Vietnamese names used in the narration.
(b) "phong": the sentence points at a small DETAIL of an animal, plant or object (a body part, a structure, a mark) that a zoom-in highlight would help the viewer notice. At most 1 per ~15 sentences.
Skip everything else. Return [] if nothing qualifies.
Return ONLY JSON: [{{"cau": <sentence index>, "kieu": "duong", "tu": "...", "den": "...", "tu_vi": "...", "den_vi": "..."}} or {{"cau": <sentence index>, "kieu": "phong"}}]

PASSAGE:
{ds}"""


def _png_mau(path, mau=(255, 176, 140)):
    from PIL import Image
    if not os.path.isfile(path):
        Image.new("RGBA", (1920, 1080), mau + (255,)).save(path)
    return path


def _mat_na(path, W, H, bo, vien=0, mau=(255, 212, 0)):
    """PNG: vien=0 -> mặt nạ trắng bo góc (alphamerge); vien>0 -> khung viền vàng bo góc nền trong suốt."""
    from PIL import Image, ImageDraw
    if os.path.isfile(path):
        return path
    if vien:
        im = Image.new("RGBA", (W + 2 * vien, H + 2 * vien), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, W + 2 * vien - 1, H + 2 * vien - 1], bo + vien, outline=mau + (255,),
                                             width=vien)
    else:
        im = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, W - 1, H - 1], bo, fill=255)
    im.save(path)
    return path


def _clip_phong(o, src0, dai, out, phong=2.0, LW=900, LH=506, vien=10):
    """Clip 1920x1080 dài `dai` s: cảnh gốc (đúng như track hình, kể cả phóng giấu logo) + kính lúp bo góc viền vàng
    ở giữa phóng `phong` lần phần giữa cảnh."""
    if os.path.isfile(out) and os.path.getsize(out) > 5000:
        return out
    thu = os.path.dirname(out)
    mn = _mat_na(os.path.join(thu, f"_mat_{LW}x{LH}.png"), LW, LH, 26)
    kv = _mat_na(os.path.join(thu, f"_vien_{LW}x{LH}.png"), LW, LH, 26, vien)
    ph = float(o.get("phong") or 1.0)
    cw, ch = 1920 / phong, 1080 / phong
    fc = (f"[0:v]crop=iw/{ph}:ih/{ph},scale=1920:1080,setsar=1,split[a][b];"
          f"[b]crop={cw:.0f}:{ch:.0f}:{(1920 - cw) / 2:.0f}:{(1080 - ch) / 2:.0f},scale={LW}:{LH}[z];"
          f"[1:v]format=gray[m];[z][m]alphamerge[zm];"
          f"[a]gblur=sigma=7,eq=brightness=-0.13[ad];"                 # nền quanh khung tối + mờ để khung nổi lên
          f"[ad][zm]overlay={(1920 - LW) // 2}:{(1080 - LH) // 2}[o1];"
          f"[o1][2:v]overlay={(1920 - LW) // 2 - vien}:{(1080 - LH) // 2 - vien},format=yuv420p[v]")
    p = subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", f"{src0:.3f}", "-t", f"{dai:.3f}", "-i", o["clip"],
                        "-loop", "1", "-i", mn, "-loop", "1", "-i", kv, "-filter_complex", fc, "-map", "[v]", "-an",
                        "-t", f"{dai:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", out],
                       capture_output=True, timeout=300, creationflags=0x08000000 if os.name == "nt" else 0)
    if p.returncode != 0:
        log(f"    ! highlight lỗi: {p.stderr.decode('utf-8', 'ignore')[-200:]}")
        return None
    return out


def lap(cau, canh, chuong, out, SEC=1_000_000, san=None):
    """Kế hoạch hiệu ứng: [{kieu, bd, dai, file, ...}] không chồng nhau, theo giờ câu (cau: t0/t1 giây).
    san: các lớp minh hoạ đã dựng (minh_hoa.lap, 13/10) -> KHÔNG hỏi ChatGPT đường đi/highlight riêng, chỉ thêm phủ màu."""
    import nen_ban_do
    thu = os.path.join(out, "hieu_ung")
    os.makedirs(thu, exist_ok=True)
    if san is not None:
        ra = list(san)
        png = _png_mau(os.path.join(thu, "_phu_mau.png"))
        for ch in chuong[1:]:
            a = float(ch.get("tu") or 0) - 0.5
            if a > 0 and all(a + 1.0 <= y["bd"] - 0.05 or a >= y["bd"] + y["dai"] + 0.05 for y in ra):
                ra.append({"kieu": "phu_mau", "bd": round(a, 2), "dai": 1.0, "file": png})
        return sorted(ra, key=lambda y: y["bd"])
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    log(f"[HU] hiệu ứng (đường đi / highlight): hỏi ChatGPT {len(lots)} đoạn…")
    tra = hoi_nhieu([_P.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot)) for lot in lots], timeout=240)
    theo_i = {c["i"]: c for c in cau}
    duong, phong = [], []
    for r in tra:
        for x in (rut_json(r) or []):
            try:
                c = theo_i.get(int(x.get("cau", 0)))
            except (TypeError, ValueError, AttributeError):
                continue
            if not c:
                continue
            if x.get("kieu") == "duong" and x.get("tu") and x.get("den"):
                duong.append((c, x))
            elif x.get("kieu") == "phong" and PHONG_BAT:
                phong.append(c)
    ra = []

    def trong(a, b):
        return all(b <= y["bd"] - 0.05 or a >= y["bd"] + y["dai"] + 0.05 for y in ra)

    # (a) bản đồ đường đi
    viec, thay = [], {}
    for c, x in duong:
        k = (x["tu"].lower(), x["den"].lower())
        if c["t0"] - thay.get(k, -1e9) < 60:               # cùng một tuyến trong 60 s: chỉ vẽ lần đầu
            continue
        thay[k] = c["t0"]
        bd = c["t0"]
        dai = round(max(4.5, min(7.0, c["t1"] - bd)), 2)
        viec.append((c, x, bd, dai))
    if viec:
        clip = nen_ban_do.dung_clip_duong([(x["tu"], x["den"], d, x.get("tu_vi") or None, x.get("den_vi") or None)
                                           for c, x, bd, d in viec])
        for c, x, bd, d in viec:
            f = clip.get((x["tu"], x["den"], round(d, 2)))
            if f and trong(bd, bd + d):
                ra.append({"kieu": "duong", "cau": c["i"], "bd": round(bd, 2), "dai": d, "file": f,
                           "mo_ta": f"{x.get('tu_vi') or x['tu']} → {x.get('den_vi') or x['den']}"})
    # (b) khung highlight viền vàng: dựng từ chính đoạn hình đang chiếu lúc đọc câu
    doan = sorted((t / SEC, d / SEC, o) for cc in canh for (t, d, o) in cc["_os"])
    for c in phong:
        giua = (c["t0"] + c["t1"]) / 2
        hit = next(((t, d, o) for t, d, o in doan if t <= giua < t + d), None)
        if not hit or hit[2].get("anh") or hit[2].get("ban_do"):
            continue
        t, d, o = hit
        a, b = max(t, c["t0"]), min(t + d, c["t1"] + 0.3)
        if b - a < 1.5 or not trong(a, b):
            continue
        f = _clip_phong(o, o.get("vao", 0.0) + (a - t), b - a, os.path.join(thu, f"phong_{c['i']:04d}.mp4"))
        if f:
            ra.append({"kieu": "phong", "cau": c["i"], "bd": round(a, 2), "dai": round(b - a, 2), "file": f})
    # (c) phủ màu khi đổi chương
    png = _png_mau(os.path.join(thu, "_phu_mau.png"))
    for ch in chuong[1:]:
        a = float(ch.get("tu") or 0) - 0.5
        if a > 0 and trong(a, a + 1.0):
            ra.append({"kieu": "phu_mau", "bd": round(a, 2), "dai": 1.0, "file": png})
    ra.sort(key=lambda y: y["bd"])
    log(f"    hiệu ứng: {sum(y['kieu'] == 'duong' for y in ra)} bản đồ đường đi, "
        f"{sum(y['kieu'] == 'phong' for y in ra)} khung highlight, {sum(y['kieu'] == 'phu_mau' for y in ra)} phủ màu "
        f"(ChatGPT đề xuất {len(duong)} đường đi, {len(phong)} highlight)")
    return ra


def dat(script, ds, SEC=1_000_000):
    """Đặt hiệu ứng lên track 'hieu_ung' (đã tạo)."""
    import pycapcut as draft
    from pycapcut import trange
    KP = draft.KeyframeProperty
    for x in ds:
        d = int(x["dai"] * SEC)
        mat = draft.VideoMaterial(x["file"])
        if x["kieu"] != "phu_mau":
            d = min(d, int(mat.duration) - 1000)
        seg = draft.VideoSegment(mat, trange(int(x["bd"] * SEC), d))
        if x["kieu"] == "phu_mau":                           # lớp màu lướt qua
            seg.add_keyframe(KP.alpha, 0, 0.0)
            seg.add_keyframe(KP.alpha, d // 2, 0.45)
            seg.add_keyframe(KP.alpha, d - 1000, 0.0)
        else:                                                # 18/10 user: không cho hiệu ứng mờ dần lúc xuất hiện và kết thúc
            pass
        script.add_segment(seg, track_name="hieu_ung")
    return len(ds)
