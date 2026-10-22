# -*- coding: utf-8 -*-
"""LỚP ẢNH PHỦ minh hoạ — "ảnh highlight" (12/10 user: thẻ ảnh bật lên trên video nền đang chạy; bản 2: thẻ TO 65%
khung, MỌI câu có ý quan trọng đều có một thẻ, mỗi thẻ BẮT BUỘC kèm chữ nhấn mạnh in ngay dưới ảnh).

  1. Chia lời thành đoạn ~20 câu, hỏi ChatGPT câu nào CẦN thêm một ảnh minh hoạ (vật/người/loài/tài liệu cụ thể mà
     cảnh nền khó có, hoặc so sánh hai thứ) + từ khoá tìm ảnh tiếng Anh ngắn. Chỉ khi thật cần (~1 / 6-10 câu).
  2. Tìm Google Images (cửa sổ Chrome hiện, anh_google), chấm SigLIP theo từ khoá, BỎ ảnh có chữ / hoạt hình
     (loc_chu, loc_minh_hoa — cùng luật ảnh của bước khớp), tải ảnh tốt nhất.
  3. Làm THẺ: ảnh bo góc, viền trắng, bóng đổ, nền trong suốt (PNG) — ra/<dự án>/lop_phu/.
  4. dung_hoan_chinh đặt thẻ lên track video "lop_phu" (trên track hình), nảy vào + mờ ra, xen kẽ phải/trái."""
import io
import os
import urllib.request

from common import doc_json, ghi_json, hoi_nhieu, log, rut_json

CAU_MOI_DOAN = 20
CO = 0.65                  # 12/10 user: thẻ highlight chiếm 65% khung
_P = """You are the editor of a Vietnamese documentary video. While B-roll footage keeps playing, you pop up a large HIGHLIGHT CARD: a real photograph with a short bold caption under it, to stress the KEY IDEAS of the narration. Below is ONE PASSAGE (sentence index. text).
Choose the sentences that carry an IMPORTANT idea of the story: a key fact or number, a turning point, a striking comparison, the first mention of a key species/person/object/place, a cause or consequence the viewer must remember. Skip filler, transitions and pure emotion. Typically 1 card every 3-5 sentences, AT MOST ONE card per sentence, and never two cards about the same fact.
For each chosen sentence give:
- "anh": a SHORT English Google Images query (2-6 words) for a real photograph that illustrates that idea (no diagrams, no labeled maps, no text in the picture);
- "chu": the Vietnamese EMPHASIS CAPTION for the card, 2-7 words, punchy, stating the key idea (prefer the sentence's own key words; numbers as digits, e.g. "3 triệu tấn mỗi năm", "Nhanh gấp đôi xe đua");
- "moc": 2-8 words COPIED EXACTLY from the sentence (same spelling, numbers as written in the sentence) where the key idea is said — the card pops up when the narrator says these words.
Return ONLY JSON: [{{"cau": <sentence index>, "anh": "<image search query>", "chu": "<Vietnamese caption>", "moc": "<exact words from the sentence>"}}]

PASSAGE:
{ds}"""
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def _the(anh, out_png, chu="", W=1100, H=700, vien=12, bo=30, bong=26, CH=170):
    """Thẻ highlight: ảnh cắt vừa W×H bo góc + dải CHỮ NHẤN MẠNH (CH px) ngay dưới ảnh, viền trắng, bóng đổ; PNG trong suốt."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
    im = ImageOps.fit(anh.convert("RGB"), (W, H), Image.LANCZOS)
    ch = CH if chu else 0
    pad = bong * 2
    can = Image.new("RGBA", (W + 2 * vien + 2 * pad, H + ch + 2 * vien + 2 * pad), (0, 0, 0, 0))
    bo_trong = Image.new("L", (W + 2 * vien, H + ch + 2 * vien), 0)
    ImageDraw.Draw(bo_trong).rounded_rectangle([0, 0, W + 2 * vien - 1, H + ch + 2 * vien - 1], bo + vien, fill=255)
    sh = Image.new("RGBA", can.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), (pad + 8, pad + 14), bo_trong)
    can = Image.alpha_composite(can, sh.filter(ImageFilter.GaussianBlur(bong / 2)))
    trang = Image.new("RGBA", bo_trong.size, (255, 255, 255, 255))
    can.paste(trang, (pad, pad), bo_trong)
    mat = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mat).rounded_rectangle([0, 0, W - 1, H - 1], bo, fill=255)
    can.paste(im, (pad + vien, pad + vien), mat)
    if chu:                                                   # dải chữ nhấn mạnh: vạch cam bên trái + chữ đậm, tự co cỡ
        d = ImageDraw.Draw(can)
        x0, y0 = pad + vien, pad + vien + H + 8
        d.rounded_rectangle([x0 + 18, y0 + 26, x0 + 32, y0 + ch - 34], 6, fill=(224, 120, 47, 255))
        for co in (72, 64, 56, 50, 44, 38):
            f = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", co)
            dong, cur = [], ""
            for w_ in chu.split():
                th = (cur + " " + w_).strip()
                if d.textlength(th, font=f) <= W - 90:
                    cur = th
                else:
                    dong.append(cur)
                    cur = w_
            dong.append(cur)
            if len(dong) <= 2 and len(dong) * co * 1.15 <= ch - 30:
                break
        tong_cao = len(dong) * co * 1.15
        for k, dg in enumerate(dong):
            d.text((x0 + 56, y0 + (ch - 8 - tong_cao) / 2 + k * co * 1.15), dg, font=f, fill=(34, 30, 26, 255))
    can.save(out_png)
    return out_png


# 13/10 user: "thẻ mà chỉnh tay trên CapCut được thì tốt" -> thẻ = 3 LỚP riêng trong CapCut:
#   ảnh thật (lop_phu, bấm Thay thế để đổi ảnh) + khung trắng bo góc có dải chữ (lop_phu_khung, PNG dùng chung,
#   ô ảnh trong suốt) + chữ nhấn mạnh là LỚP CHỮ CapCut (lop_phu_chu, sửa chữ trực tiếp).
TW, TH, TV, TBO, TBONG, TCH = 1100, 700, 12, 30, 26, 170     # ô ảnh, viền, bo góc, bóng, cao dải chữ (px trên PNG khung)
TPAD = TBONG * 2
PW, PH = TW + 2 * TV + 2 * TPAD, TH + TCH + 2 * TV + 2 * TPAD   # cỡ PNG khung


def _khung(thu):
    """PNG khung dùng chung: thẻ trắng bo góc + bóng đổ + vạch cam trên dải chữ; Ô ẢNH TRONG SUỐT (góc bo vẫn trắng
    để che góc vuông của ảnh nằm dưới)."""
    from PIL import Image, ImageDraw, ImageFilter
    out = os.path.join(thu, "_khung_v1.png")
    if os.path.isfile(out):
        return out
    can = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    the = Image.new("L", (TW + 2 * TV, TH + TCH + 2 * TV), 0)
    ImageDraw.Draw(the).rounded_rectangle([0, 0, TW + 2 * TV - 1, TH + TCH + 2 * TV - 1], TBO + TV, fill=255)
    sh = Image.new("RGBA", can.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), (TPAD + 8, TPAD + 14), the)
    can = Image.alpha_composite(can, sh.filter(ImageFilter.GaussianBlur(TBONG / 2)))
    can.paste((255, 255, 255, 255), (TPAD, TPAD), the)
    d = ImageDraw.Draw(can)
    x0, y0 = TPAD + TV, TPAD + TV + TH
    d.rounded_rectangle([x0 + TW // 2 - 90, y0 + 14, x0 + TW // 2 + 90, y0 + 22], 4, fill=(224, 120, 47, 255))
    o = Image.new("L", (TW, TH), 0)                          # khoét ô ảnh (bo góc) -> trong suốt
    ImageDraw.Draw(o).rounded_rectangle([0, 0, TW - 1, TH - 1], TBO, fill=255)
    a = can.getchannel("A")
    a.paste(0, (TPAD + TV, TPAD + TV), o)
    can.putalpha(a)
    can.save(out)
    return out


def _anh_the(anh, out_jpg):
    """Ảnh thật cắt đúng tỉ lệ ô ảnh (TW:TH) -> JPG đặt dưới khung."""
    from PIL import Image, ImageOps
    ImageOps.fit(anh.convert("RGB"), (TW, TH), Image.LANCZOS).save(out_jpg, quality=92)
    return out_jpg


GIONG_ANH = 0.93           # vector ảnh giống ảnh đã dùng hơn mức này = cùng một ảnh (tải từ trang khác) -> bỏ


def _chon_anh(q, thu, ten, da_dung, chu=""):
    """Tải ảnh thật khớp nhất cho từ khoá q (không chữ, không hoạt hình, CHƯA dùng ở thẻ khác) -> (PNG thẻ, vector).
    da_dung: {"url": set, "v": [vector]} — 12/10: không lặp cùng một ảnh ở nhiều thẻ."""
    import anh_google
    import loc_chu
    import loc_minh_hoa
    import nhung_siglip
    import xep_hang
    from PIL import Image
    try:
        ds = anh_google.google_anh(q, n=30)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! lớp phủ: tìm ảnh '{q}' lỗi: {str(e)[:80]}")
        return None
    if not ds:
        return None
    qv = nhung_siglip.nhung_chu([f"a photograph of {q}"])[0]
    d, co_chu = xep_hang.diem_anh([a["thumb"] or a["url"] for a in ds], qv, luong=4, chu=True)
    xep = sorted((i for i in range(len(ds)) if co_chu[i] is False and min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 500),
                 key=lambda i: -d[i])
    for i in xep[:12]:
        if ds[i]["url"] in da_dung["url"]:
            continue
        try:
            raw = urllib.request.urlopen(urllib.request.Request(ds[i]["url"], headers=UA), timeout=25).read(20 << 20)
            anh = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:                                    # noqa: BLE001
            continue
        goc = os.path.join(thu, ten + "_goc.jpg")
        anh.save(goc, quality=92)
        try:
            if loc_chu.co_chu_anh(goc) or loc_minh_hoa.la_hoat_hinh_anh(goc):
                continue
        except Exception:                                    # noqa: BLE001
            pass
        v = nhung_siglip.nhung_anh([anh])[0]
        if any(float(v @ u) > GIONG_ANH for u in da_dung["v"]):
            continue                                         # cùng ảnh đã dùng (khác link)
        da_dung["url"].add(ds[i]["url"])
        da_dung["v"].append(v)
        return _anh_the(anh, os.path.join(thu, ten + "_anh.jpg"))
    return None


def _chuan(s):
    import re
    import unicodedata
    return [w for w in re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFC", s.lower())).split() if w]


def _luc_hien(c, moc):
    """(bật, tắt) theo GIỌNG THẬT: bật lúc đọc tới chữ đầu của cụm `moc` trong câu (giờ từng chữ c["tu"] do can_chu căn),
    tắt khi đọc hết câu (+0,3 s). Không tìm thấy cụm / không có giờ từng chữ -> bật đầu câu."""
    tu = c.get("tu") or []
    bat, tat = c["t0"], c["t1"] + 0.3
    if tu and moc:
        w = [_chuan(t[0]) for t in tu]
        phang = [(k, x) for k, ws in enumerate(w) for x in ws]
        m = _chuan(moc)
        tot, vt = 0, None
        for s in range(len(phang)):                          # vị trí khớp nhiều chữ liên tiếp nhất
            n = 0
            while n < len(m) and s + n < len(phang) and phang[s + n][1] == m[n]:
                n += 1
            if n > tot:
                tot, vt = n, phang[s][0]
        if vt is not None and tot >= min(2, len(m)):
            bat = tu[vt][1]
    return round(max(c["t0"], bat - 0.1), 2), round(tat, 2)


THE_TOI_THIEU = 3.0        # 13/10: thẻ hiện ít nhất 3 s mới cho thẻ sau bật
CACH_THE = 1.0             # khoảng trống giữa hai thẻ


def _giong_chu(a, b):
    """Hai chữ nhấn mạnh nói cùng một thông tin (>= 50% từ của chữ ngắn hơn trùng nhau, hoặc cùng một con số)."""
    import re
    wa, wb = set(_chuan(a)), set(_chuan(b))
    if not wa or not wb:
        return False
    so_a, so_b = set(re.findall(r"\d[\d.,]*", a)), set(re.findall(r"\d[\d.,]*", b))
    if so_a & so_b and any(len(x) >= 3 for x in so_a & so_b):
        return True
    return len(wa & wb) >= 0.5 * min(len(wa), len(wb))


def lap(cau, out, de_xuat=None, cam=()):
    """Kế hoạch lớp phủ: [{cau, anh, file(ảnh thẻ), bd, dai, ben}] (cache theo câu + từ khoá trong out/lop_phu.json).
    de_xuat: danh sách lớp của dieu_phoi.hoi (lấy kieu == "the") — có thì KHÔNG hỏi ChatGPT riêng.
    cam: [(a, b)] khoảng giờ đã có lớp minh hoạ khác (bản đồ / sơ đồ) — thẻ không bật trong đó."""
    thu = os.path.join(out, "lop_phu")
    os.makedirs(thu, exist_ok=True)
    if de_xuat is not None:
        return _lap_tu(cau, out, thu, [x for x in de_xuat if x.get("kieu") == "the"], cam)
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    # 13/10: LƯU câu trả lời ChatGPT theo (câu lệnh + đoạn lời) -> chạy lại giữ nguyên bộ thẻ, chỉ hỏi đoạn đổi lời
    import hashlib
    hoi = [_P.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot)) for lot in lots]
    khoa = [hashlib.md5(p.encode("utf-8")).hexdigest()[:16] for p in hoi]
    p_hoi = os.path.join(out, "lop_phu_hoi.json")
    da_hoi = doc_json(p_hoi, {}) or {}
    can = [k for k, kk in enumerate(khoa) if not rut_json(da_hoi.get(kk) or "")]
    log(f"[LP] lớp ảnh phủ: hỏi ChatGPT {len(can)}/{len(lots)} đoạn nội dung (còn lại dùng câu trả lời đã lưu)…")
    if can:
        moi = hoi_nhieu([hoi[k] for k in can], timeout=240)
        for k, r in zip(can, moi):
            if rut_json(r or ""):
                da_hoi[khoa[k]] = r
        ghi_json(p_hoi, da_hoi)
    tra = [da_hoi.get(kk, "") for kk in khoa]
    return _lap_tu(cau, out, thu, [x for r in tra for x in (rut_json(r) or [])], cam)


def _lap_tu(cau, out, thu, ds_x, cam=()):
    theo_i = {c["i"]: c for c in cau}
    muon = []
    if True:
        for x in ds_x:
            try:
                c = theo_i.get(int(x.get("cau", 0)))
            except (TypeError, ValueError, AttributeError):
                continue
            q = str((x or {}).get("anh", "")).strip()
            chu = str((x or {}).get("chu", "")).strip().strip(".")
            if c and q and chu:                              # bắt buộc có chữ nhấn mạnh
                import so_hien_thi
                muon.append((c, q, so_hien_thi.doi(chu), str((x or {}).get("moc", "")).strip()))
    cache = os.path.join(out, "lop_phu.json")
    cu = {}
    for x in (doc_json(cache, []) or []):
        f = x.get("file") or ""
        if x.get("v4") and os.path.isfile(f):
            cu[(x["cau"], x["anh"], x.get("chu"))] = x
        elif x.get("v3") and os.path.isfile(f[:-4] + "_goc.jpg"):   # bản PNG in chữ cũ: cắt lại từ ảnh gốc
            from PIL import Image
            x = dict(x, file=_anh_the(Image.open(f[:-4] + "_goc.jpg"), f[:-4] + "_anh.jpg"), v4=True)
            cu[(x["cau"], x["anh"], x.get("chu"))] = x
    ra, ben = [], 1
    da_dung = {"url": {x.get("url") for x in cu.values()}, "v": []}
    da_cau = set()
    for c, q, chu, moc in sorted(muon, key=lambda z: _luc_hien(z[0], z[3])[0]):
        bd, kt = _luc_hien(c, moc)
        if any(bd < b_ + 0.3 and bd + THE_TOI_THIEU > a_ - 0.3 for a_, b_ in cam):
            continue                                         # trùng giờ bản đồ / sơ đồ Remotion: không thẻ
        # 13/10 user: thẻ nhảy liên tục rối mắt + "1 thông tin nháy 2 lần" -> mỗi câu tối đa 1 thẻ; thẻ sau KHÔNG cắt
        # ngắn thẻ trước — bật khi thẻ trước đã hiện đủ (>= THE_TOI_THIEU) và cách quãng >= CACH_THE, không thì bỏ
        if c["i"] in da_cau:
            continue
        if ra:
            tr = ra[-1]
            if bd < tr["bd"] + THE_TOI_THIEU + CACH_THE or _giong_chu(chu, tr["chu"]):
                continue
            if tr["bd"] + tr["dai"] > bd - CACH_THE:
                tr["dai"] = round(bd - CACH_THE - tr["bd"], 2)
        x = cu.get((c["i"], q, chu))
        if not x:
            f = _chon_anh(q, thu, f"lp_{c['i']:04d}", da_dung, chu)
            if not f:
                continue
            x = {"cau": c["i"], "anh": q, "chu": chu, "file": f, "v4": True}
        x = dict(x)                                          # cùng ảnh/chữ ở hai câu khác nhau: không ghi đè lẫn nhau
        x.update(bd=round(bd, 2), dai=round(max(2.5, min(8.0, kt - bd)), 2), ben=ben, moc=moc)
        ra.append(x)
        da_cau.add(c["i"])
        ben = -ben
    ghi_json(cache, ra)
    log(f"    {len(ra)} thẻ ảnh phủ (từ {len(muon)} câu ChatGPT đề xuất)")
    return ra


EM_MOI_CO = 21.0           # 13/10 đo trên CapCut: cỡ chữ 1 ~ 21 px (em) trên PNG khung khi thẻ ở 65% (ước 6,2 là sai)


def _co_chu(chu):
    """(cỡ chữ CapCut, chữ đã ngắt dòng) cho dải chữ: một dòng nếu vừa bề ngang ô ảnh, không thì tự ngắt 2 dòng
    (không để CapCut tự xuống dòng — max_line_width của nó không theo khung thẻ)."""
    from PIL import ImageFont
    rong = TW * 0.88

    def do(co):
        return ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", int(co * EM_MOI_CO))
    for co in (4.6, 4.2, 3.8, 3.4, 3.1):
        if do(co).getlength(chu) <= rong:
            return co, chu
    w = chu.split()
    for co in (3.0, 2.8, 2.6):          # 2 dòng: cao 2 x 1,2 em phải lọt dải chữ (170 px)
        f = do(co)
        tot = min(range(1, len(w)), key=lambda k: max(f.getlength(" ".join(w[:k])), f.getlength(" ".join(w[k:]))),
                  default=None)
        if tot and max(f.getlength(" ".join(w[:tot])), f.getlength(" ".join(w[tot:]))) <= rong:
            return co, " ".join(w[:tot]) + "\n" + " ".join(w[tot:])
    return 2.6, chu


def dat(script, ds, SEC=1_000_000, W=1920, H=1080):
    """Đặt thẻ lên 3 track (lop_phu = ảnh, lop_phu_khung, lop_phu_chu — đã tạo): cỡ 65% khung (12/10 user), lệch nhẹ
    phải/trái xen kẽ, nảy vào, mờ ra. Ba lớp nảy CÙNG nhau quanh tâm thẻ: mỗi keyframe cỡ s của khung đi kèm cỡ + vị
    trí tính sẵn cho ảnh và chữ (vị trí tuyến tính theo s nên nội suy giữa keyframe vẫn khớp)."""
    import pycapcut as draft
    from pycapcut import trange
    KP = draft.KeyframeProperty
    if not ds:
        return 0
    khung = _khung(os.path.dirname(ds[0]["file"]))
    fk = min(W / PW, H / PH)                                 # CapCut đặt vật liệu vừa khung hình trước khi phóng
    fa = min(W / TW, H / TH)
    dy_anh = (PH / 2 - (TPAD + TV + TH / 2))                 # tâm ô ảnh / dải chữ so với tâm khung (px PNG, lên = +)
    dy_chu = (PH / 2 - (TPAD + TV + TH + 10 + TCH / 2))
    vk = draft.VideoMaterial(khung)
    for x in ds:
        d = int(x["dai"] * SEC)
        tx = 0.2 * x["ben"]
        mocs = [(0, CO * 0.72), (int(0.22 * SEC), CO * 1.04), (int(0.36 * SEC), CO)]

        def lop(s_):                                         # (cỡ ảnh, y ảnh, cỡ chữ, y chữ) khi khung cỡ s_
            return (s_ * fk / fa, dy_anh * fk * s_ / (H / 2), s_ / CO, dy_chu * fk * s_ / (H / 2))
        a0 = lop(CO)
        seg_a = draft.VideoSegment(draft.VideoMaterial(x["file"]), trange(int(x["bd"] * SEC), d),
                                   clip_settings=draft.ClipSettings(scale_x=a0[0], scale_y=a0[0],
                                                                    transform_x=tx, transform_y=a0[1]))
        seg_k = draft.VideoSegment(vk, trange(int(x["bd"] * SEC), d),
                                   clip_settings=draft.ClipSettings(scale_x=CO, scale_y=CO, transform_x=tx))
        co, chu = _co_chu(x["chu"])
        seg_c = draft.TextSegment(chu, trange(int(x["bd"] * SEC), d),
                                  style=draft.TextStyle(size=co, bold=True, color=(0.13, 0.12, 0.1), align=1),
                                  clip_settings=draft.ClipSettings(transform_x=tx, transform_y=a0[3]))
        for t, s_ in mocs:
            la = lop(s_)
            seg_k.add_keyframe(KP.uniform_scale, t, s_)
            seg_a.add_keyframe(KP.uniform_scale, t, la[0])
            seg_a.add_keyframe(KP.position_y, t, la[1])
            seg_c.add_keyframe(KP.uniform_scale, t, la[2])
            seg_c.add_keyframe(KP.position_y, t, la[3])
        for seg in (seg_a, seg_k):
            seg.add_keyframe(KP.alpha, 0, 0.0)
            seg.add_keyframe(KP.alpha, int(0.18 * SEC), 1.0)
            seg.add_keyframe(KP.alpha, max(d - int(0.3 * SEC), int(0.4 * SEC)), 1.0)
            seg.add_keyframe(KP.alpha, d - 1000, 0.0)
        seg_c.add_animation(draft.TextIntro.渐显, int(0.18 * SEC))     # chữ: keyframe độ mờ không ăn -> hiệu ứng vào/ra
        seg_c.add_animation(draft.TextOutro.渐隐, int(0.3 * SEC))
        script.add_segment(seg_a, track_name="lop_phu")
        script.add_segment(seg_k, track_name="lop_phu_khung")
        script.add_segment(seg_c, track_name="lop_phu_chu")
    return len(ds)


NV_CO = 0.5                # 22/10 user: thẻ ảnh NHÂN VẬT THẬT chiếm ~50% khung, lệch trái / phải xen kẽ
NV_DAI = (3.0, 6.0)        # thẻ hiện 3-6 s


def lap_nhan_vat(cau, out, ds_nv, cam=()):
    """22/10 user ("nhân vật thật sự tồn tại thì không dùng ảnh AI vẽ mà tìm ảnh google tải về rồi phủ lên nền video
    đang chạy"): mỗi nhân vật THẬT (dieu_phoi kieu "nhan_vat": ten, anh = từ khoá Google, moc) -> ẢNH THẬT tìm trên
    Google Images (cùng bộ lọc ảnh có chữ / hoạt hình / trùng của thẻ highlight) làm thẻ bo góc KHÔNG CHỮ (21/10 user tắt
    chữ trên màn hình) -> [{cau, ten, anh, file(PNG thẻ), bd, dai, ben}]. Cache out/nhan_vat.json."""
    from PIL import Image
    thu = os.path.join(out, "lop_phu")
    os.makedirs(thu, exist_ok=True)
    theo_i = {c["i"]: c for c in cau}
    p_cache = os.path.join(out, "nhan_vat.json")
    cu = {(x["cau"], x["anh"]): x for x in doc_json(p_cache, []) or [] if os.path.isfile(x.get("file") or "")}
    da_dung = {"url": set(), "v": []}
    ra, ben = [], 1
    for x in sorted(ds_nv, key=lambda z: int(z.get("cau") or 0)):
        try:
            c = theo_i.get(int(x.get("cau")))
        except (TypeError, ValueError):
            continue
        q = str(x.get("anh") or "").strip()
        if not c or not q:
            continue
        moc = str(x.get("moc") or "").strip()
        bd, kt = _luc_hien(c, moc)
        if any(bd < b_ + 0.3 and bd + NV_DAI[0] > a_ - 0.3 for a_, b_ in cam):
            continue                                         # trùng giờ bản đồ / sơ đồ: không thẻ
        if ra and bd < ra[-1]["bd"] + ra[-1]["dai"] + 0.5:
            continue
        y = cu.get((c["i"], q))
        if not y:
            jpg = _chon_anh(q, thu, f"nv_{c['i']:04d}", da_dung)
            if not jpg:
                log(f"    ! nhân vật «{x.get('ten')}»: không tìm được ảnh thật ('{q}')")
                continue
            png = jpg[:-4] + "_the.png"
            _the(Image.open(jpg), png, chu="")
            y = {"cau": c["i"], "ten": str(x.get("ten") or ""), "anh": q, "file": png}
        y = dict(y, bd=round(bd, 2), dai=round(max(NV_DAI[0], min(NV_DAI[1], kt - bd)), 2), ben=ben)
        ra.append(y)
        ben = -ben
    ghi_json(p_cache, ra)
    log(f"    {len(ra)} thẻ ảnh NHÂN VẬT THẬT (ảnh Google) / {len(ds_nv)} nhân vật điều phối nêu")
    return ra


def dat_nhan_vat(script, ds, SEC=1_000_000):
    """Đặt thẻ nhân vật lên track "nhan_vat" (đã tạo): nảy vào, mờ ra, lệch trái / phải xen kẽ."""
    import pycapcut as draft
    from pycapcut import trange
    KP = draft.KeyframeProperty
    for x in ds:
        d = int(x["dai"] * SEC)
        seg = draft.VideoSegment(draft.VideoMaterial(x["file"]), trange(int(x["bd"] * SEC), d),
                                 clip_settings=draft.ClipSettings(scale_x=NV_CO, scale_y=NV_CO, transform_x=0.42 * x["ben"]))
        for t, s_ in ((0, NV_CO * 0.72), (int(0.22 * SEC), NV_CO * 1.04), (int(0.36 * SEC), NV_CO)):
            seg.add_keyframe(KP.uniform_scale, t, s_)
        seg.add_keyframe(KP.alpha, 0, 0.0)
        seg.add_keyframe(KP.alpha, int(0.18 * SEC), 1.0)
        seg.add_keyframe(KP.alpha, max(d - int(0.3 * SEC), int(0.4 * SEC)), 1.0)
        seg.add_keyframe(KP.alpha, d - 1000, 0.0)
        script.add_segment(seg, track_name="nhan_vat")
    return len(ds)
