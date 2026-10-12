# -*- coding: utf-8 -*-
"""LỚP ẢNH PHỦ minh hoạ (12/10 user: "cho hình ảnh đè lên để minh hoạ nếu cần" — như video mẫu kênh user đưa: vài
lớp hình xếp lên trên trong khi video nền vẫn chạy).

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
_P = """You are the editor of a Vietnamese documentary video. While B-roll footage keeps playing full screen, you may pop up a small PICTURE CARD on one side of the screen to illustrate what the narrator says. Below is ONE PASSAGE (sentence index. text).
Choose ONLY the sentences where an extra still picture really helps the viewer understand: a specific animal/species, person, object, tool, document, building or place that the background footage probably does not show, or a comparison of two things. Do NOT choose abstract or emotional sentences. About 1 card per 6-10 sentences at most; skip the passage if nothing needs a card.
For each chosen sentence give "anh": a SHORT English Google Images query (2-6 words) for a real photograph (no diagrams, no maps with labels, no text).
Return ONLY JSON: [{{"cau": <sentence index>, "anh": "<image search query>"}}]

PASSAGE:
{ds}"""
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def _the(anh, out_png, W=1100, H=760, vien=12, bo=30, bong=26):
    """Thẻ ảnh: cắt vừa khung W×H, bo góc, viền trắng, bóng đổ mờ; PNG nền trong suốt."""
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
    im = ImageOps.fit(anh.convert("RGB"), (W, H), Image.LANCZOS)
    pad = bong * 2
    can = Image.new("RGBA", (W + 2 * vien + 2 * pad, H + 2 * vien + 2 * pad), (0, 0, 0, 0))
    bo_trong = Image.new("L", (W + 2 * vien, H + 2 * vien), 0)
    ImageDraw.Draw(bo_trong).rounded_rectangle([0, 0, W + 2 * vien - 1, H + 2 * vien - 1], bo + vien, fill=255)
    sh = Image.new("RGBA", can.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), (pad + 8, pad + 14), bo_trong)
    can = Image.alpha_composite(can, sh.filter(ImageFilter.GaussianBlur(bong / 2)))
    trang = Image.new("RGBA", bo_trong.size, (255, 255, 255, 255))
    can.paste(trang, (pad, pad), bo_trong)
    mat = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mat).rounded_rectangle([0, 0, W - 1, H - 1], bo, fill=255)
    can.paste(im, (pad + vien, pad + vien), mat)
    can.save(out_png)
    return out_png


GIONG_ANH = 0.93           # vector ảnh giống ảnh đã dùng hơn mức này = cùng một ảnh (tải từ trang khác) -> bỏ


def _chon_anh(q, thu, ten, da_dung):
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
    d, chu = xep_hang.diem_anh([a["thumb"] or a["url"] for a in ds], qv, luong=4, chu=True)
    xep = sorted((i for i in range(len(ds)) if chu[i] is False and min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 500),
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
        return _the(anh, os.path.join(thu, ten + ".png"))
    return None


def lap(cau, out):
    """Kế hoạch lớp phủ: [{cau, anh, file(PNG thẻ), bd, dai, ben}] (cache theo câu + từ khoá trong out/lop_phu.json)."""
    thu = os.path.join(out, "lop_phu")
    os.makedirs(thu, exist_ok=True)
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    log(f"[LP] lớp ảnh phủ: hỏi ChatGPT {len(lots)} đoạn nội dung…")
    tra = hoi_nhieu([_P.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot)) for lot in lots], timeout=240)
    theo_i = {c["i"]: c for c in cau}
    muon = []
    for r in tra:
        for x in (rut_json(r) or []):
            try:
                c = theo_i.get(int(x.get("cau", 0)))
            except (TypeError, ValueError, AttributeError):
                continue
            q = str((x or {}).get("anh", "")).strip()
            if c and q:
                muon.append((c, q))
    cache = os.path.join(out, "lop_phu.json")
    cu = {(x["cau"], x["anh"]): x for x in (doc_json(cache, []) or []) if x.get("file") and os.path.isfile(x["file"])
          and x.get("v2")}
    ra, cuoi, ben = [], -1e9, 1
    da_dung = {"url": {x.get("url") for x in cu.values()}, "v": []}
    for c, q in sorted(muon, key=lambda z: z[0]["t0"]):
        if c["t0"] - cuoi < 8.0:                             # không dồn thẻ: cách nhau >= 8 s
            continue
        x = cu.get((c["i"], q))
        if not x:
            f = _chon_anh(q, thu, f"lp_{c['i']:04d}", da_dung)
            if not f:
                continue
            x = {"cau": c["i"], "anh": q, "file": f, "v2": True}
        bd = c["t0"] + 0.2
        x.update(bd=round(bd, 2), dai=round(max(2.5, min(5.0, c["t1"] - bd)), 2), ben=ben)
        ra.append(x)
        cuoi, ben = bd, -ben
    ghi_json(cache, ra)
    log(f"    {len(ra)} thẻ ảnh phủ (từ {len(muon)} câu ChatGPT đề xuất)")
    return ra


def dat(script, ds, SEC=1_000_000):
    """Đặt thẻ lên track 'lop_phu' (đã tạo, nằm trên track hình): cỡ ~40% khung, lệch phải/trái, nảy vào, mờ ra."""
    import pycapcut as draft
    from pycapcut import trange
    KP = draft.KeyframeProperty
    for x in ds:
        d = int(x["dai"] * SEC)
        seg = draft.VideoSegment(draft.VideoMaterial(x["file"]), trange(int(x["bd"] * SEC), d),
                                 clip_settings=draft.ClipSettings(scale_x=0.42, scale_y=0.42,
                                                                  transform_x=0.48 * x["ben"], transform_y=-0.04))
        seg.add_keyframe(KP.uniform_scale, 0, 0.30)          # nảy vào: nhỏ -> hơi quá -> vừa
        seg.add_keyframe(KP.uniform_scale, int(0.22 * SEC), 0.45)
        seg.add_keyframe(KP.uniform_scale, int(0.36 * SEC), 0.42)
        seg.add_keyframe(KP.alpha, 0, 0.0)
        seg.add_keyframe(KP.alpha, int(0.18 * SEC), 1.0)
        seg.add_keyframe(KP.alpha, max(d - int(0.3 * SEC), int(0.4 * SEC)), 1.0)
        seg.add_keyframe(KP.alpha, d - 1000, 0.0)
        script.add_segment(seg, track_name="lop_phu")
    return len(ds)
