# -*- coding: utf-8 -*-
"""LOẠI CLIP SAI CHỦ ĐỀ (14/10/2026 user): bài chuột New York mà kéo vào clip hải ly (nutria) ở Rome, chuột nhảy ở sa
mạc Ấn Độ — stock miễn phí thiếu clip đúng nên clip "gần giống" lọt qua điểm SigLIP. Trừ điểm không đủ: clip đúng hết
lượt là clip gần giống được chọn ngay -> LOẠI HẲN.

Cách làm (tổng quát, không bảng từ gõ tay): đưa ChatGPT (cookie) đoạn kịch bản + danh sách TÊN clip (Pexels/Pixabay đặt
tên mô tả: "Urban Nutria by Riverside in Rome"), hỏi clip nào có VẬT CHÍNH khác loài/khác loại với mọi thứ lời kể nhắc
tới (hoặc rõ ràng là một địa danh khác khi lời kể nói về một nơi cụ thể). Clip chung chung (phố, người, đô thị) không
loại. Cache theo dự án: ra/<dự án>/loc_chu_de.json {md5(tên): true/false}."""
import hashlib
import os

from common import doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

LO = 40                      # số tên clip mỗi lượt hỏi (14/10: 120 tên/lượt trả số lệch, loại nhầm clip chuột)


def _k(ten):
    return hashlib.md5(str(ten or "").strip().lower().encode("utf-8")).hexdigest()[:16]


def _kich_ban(du_an):
    canh = doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []
    t = " ".join(str(c.get("text") or "") for c in canh)
    return t[:24000]                                         # cả kịch bản (đo 14/10: 17k ký tự; cắt 5k thì loại nhầm Alberta, Chicago)


def sai_chu_de(du_an, ten_theo_id):
    """ten_theo_id: {id: tên clip} -> set id có vật chính SAI so với kịch bản. Lỗi mạng: không loại gì."""
    path = os.path.join(thu_muc_du_an(du_an)[1], "loc_chu_de.json")
    da = doc_json(path, {}) or {}
    can = sorted({_k(t): t for t in ten_theo_id.values() if t and _k(t) not in da}.items())
    if can:
        kb = _kich_ban(du_an)
        lo = [can[i:i + LO] for i in range(0, len(can), LO)]
        ps = [("Below is a video narration script, then a numbered list of stock clip TITLES that may be used as "
               "B-roll for it.\n\nSCRIPT:\n" + kb + "\n\nCLIPS:\n" + "\n".join(f"{i}. {t}" for i, (_, t) in enumerate(l, 1))
               + "\n\nFor EVERY clip decide if it fits. A clip is WRONG only when its MAIN SUBJECT is clearly a "
               "different species or kind of thing than ANYTHING the script mentions (e.g. script about rats -> a nutria, "
               "gerbil, hamster, beaver clip is wrong), or it shows a specific named place that the script NEVER "
               "mentions. Anything the script mentions anywhere (any animal, person, object, city, country) is NOT wrong. "
               "Generic clips (streets, buildings, people, food, machines, landscapes) are NOT wrong. If unsure -> fits.\n"
               'Return ONLY a JSON array, one object per clip in order: {"so": <number>, "dau": "<first 3 words of the '
               'title, copied exactly>", "vat": "<main subject in 1-3 words>", "dung": true|false}') for l in lo]
        ra = hoi_nhieu(ps, timeout=240)
        moi = 0
        for l, txt in zip(lo, ra):
            j = rut_json(txt) if txt else None
            if not isinstance(j, list):
                continue                                     # lượt hỏng: lần sau hỏi lại (không ghi cache)
            for x in j:
                try:
                    k, ten = l[int(x.get("so")) - 1]
                except (TypeError, ValueError, IndexError, AttributeError):
                    continue
                dau = " ".join(str(x.get("dau") or "").lower().split())
                if not dau or dau[:12] not in " ".join(ten.lower().split()):
                    continue                                 # trả lệch số (dau không khớp tên) -> bỏ, lần sau hỏi lại
                da[k] = x.get("dung") is False
                moi += da[k]
        ghi_json(path, da)
        log(f"  lọc sai chủ đề: hỏi {len(can)} tên clip, loại {moi}")
    return {i for i, t in ten_theo_id.items() if t and da.get(_k(t))}


def dung_noi(du_an, ten, tieu_de):
    """14/10 user: ảnh địa danh "New York City" lại là hồ Lake George (bài "nơi nên đến ở BANG New York"). tieu_de: [tên
    trang ảnh] -> set chỉ số ảnh mà tiêu đề cho thấy chụp CHÍNH nơi `ten` (không phải nơi khác / vùng rộng hơn / nơi gần
    đó). Lỗi mạng: trả tất cả (giữ hành vi cũ)."""
    path = os.path.join(thu_muc_du_an(du_an)[1], "loc_dia_danh.json")
    da = doc_json(path, {}) or {}
    k = lambda t: _k(ten + "|" + str(t))                     # noqa: E731
    can = [t for t in tieu_de if k(t) not in da]
    if can:
        txt = hoi_nhieu([f"Place: {ten}\nBelow are titles of web pages where candidate photos of that place were found. "
                         "For each, decide if the photo most likely shows THAT EXACT place (not a different place, not a "
                         "wider region/state/country, not somewhere nearby). If the title gives no hint, answer true.\n"
                         + "\n".join(f"{i}. {t}" for i, t in enumerate(can, 1))
                         + '\nReturn ONLY JSON: [{"so": <number>, "dung": true|false}]'], timeout=120)[0]
        j = rut_json(txt or "")
        if isinstance(j, list):
            for x in j:
                try:
                    da[k(can[int(x.get("so")) - 1])] = x.get("dung") is not False
                except (TypeError, ValueError, IndexError, AttributeError):
                    continue
            ghi_json(path, da)
    return {i for i, t in enumerate(tieu_de) if da.get(k(t), True)}


def phong_xanh(f):
    """14/10 user: clip PHÔNG XANH (con cú trên nền xanh lá trơn) lọt vào B-roll. Lấy 6 khung (1 khung/3 s): nền phông là
    một màu xanh lá / xanh dương ĐỀU (độ lệch màu < 6) chiếm >= 25% khung. Đo chuot_newyor: 4 clip phông 95-99%, độ lệch
    1-2; cỏ xanh mờ tự nhiên 43% nhưng lệch 8-19 -> giữ; trời xanh tự nhiên không phải phông
    (xanh dương phông chroma gắt hơn hẳn: B hơn G >= 80)."""
    import subprocess
    import numpy as np
    from common import FFMPEG
    try:
        r = subprocess.run([FFMPEG, "-v", "error", "-i", f, "-vf", "fps=1/3,scale=96:54", "-frames:v", "6", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=120,
                           creationflags=0x08000000 if os.name == "nt" else 0).stdout
        a = np.frombuffer(r, np.uint8).reshape(-1, 54, 96, 3).astype(int)
    except Exception:                                        # noqa: BLE001
        return False
    if not len(a):
        return False
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    for m in ((G > 120) & (G > R + 40) & (G > B + 40), (B > 150) & (B > R + 100) & (B > G + 80)):
        ti, lech = float(m.mean()), (float(a[m].std(axis=0).max()) if m.any() else 99.0)
        if (ti >= 0.6 and lech < 10.0) or (ti >= 0.25 and lech < 6.0):   # phông sáng chói: nhiễu nén đẩy lệch tới ~6,8
            return True
    return False


def danh_dau_phong_xanh(du_an):
    """Đánh dấu kho.phong_xanh cho mọi video (đo một lần, lưu trong kho)."""
    import dung_tay
    n = 0
    for k, m in dung_tay.doc_kho(du_an).items():
        if m.get("loai") == "video" and m.get("trang_thai") == "xong" and "phong_xanh" not in m and os.path.isfile(m.get("file", "")):
            px = phong_xanh(m["file"])
            dung_tay._cap_nhat_kho(du_an, k, phong_xanh=px)   # noqa: SLF001
            n += px
    if n:
        log(f"  phông xanh: bỏ {n} clip")
    return n


def danh_dau_kho(du_an):
    """Đánh dấu kho.sai_chu_de cho mọi video/ảnh tải từ nguồn ngoài (ảnh Gemini vẽ theo cảnh thì bỏ qua)."""
    import dung_tay
    kho = dung_tay.doc_kho(du_an)
    ten = {k: m.get("tieu_de") or "" for k, m in kho.items()
           if m.get("trang_thai") == "xong" and m.get("nguon") != "gemini" and m.get("loai") in ("video", "anh")}
    sai = sai_chu_de(du_an, ten)
    for k in ten:
        if bool(kho[k].get("sai_chu_de")) != (k in sai):
            dung_tay._cap_nhat_kho(du_an, k, sai_chu_de=k in sai)   # noqa: SLF001
    return sai
