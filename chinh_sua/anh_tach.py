# -*- coding: utf-8 -*-
"""ẢNH THẬT ĐÃ TÁCH NỀN cho cảnh "diễn cảnh" Remotion (13/10 user: thay icon bằng ảnh thật xoá nền).

Tìm Google Images "<từ khoá> isolated on white background" (ảnh nền trắng tách sạch nhất) -> xếp theo SigLIP, bỏ ảnh có
chữ / hoạt hình -> tách nền ISNet (cat_nen.py) -> chỉ nhận ảnh tách SẠCH: đối tượng chiếm 6-80% ảnh, phần lớn nhất liền một
khối (>= 85% diện tích), không dính mép quá nhiều. Ghi PNG vào remotion/public/cat/ (cache theo từ khoá)."""
import hashlib
import io
import os
import urllib.request

import numpy as np

from common import CACHE_CHUNG, doc_json, ghi_json, log

REMOTION = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
PUB = os.path.join(REMOTION, "public", "cat")
KHO_WATERMARK = ("dreamstime", "shutterstock", "istockphoto", "alamy", "123rf", "depositphotos", "photocase",
                 "stock.adobe", "gettyimages", "canstockphoto", "bigstock", "pond5", "fotolia", "agefotostock", "vecteezy",
                 "colourbox", "featurepics", "megapixl", "panthermedia", "masterfile", "superstock", "pixta")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def _sach(png, nhieu_manh=False):
    """Ảnh tách có sạch không: (ok, lý do). nhieu_manh=True (ảnh AI vẽ): cho phép vật gồm nhiều mảnh rời."""
    import cv2
    from PIL import Image
    a = np.asarray(Image.open(png).getchannel("A"), np.uint8)
    m = (a > 128).astype(np.uint8)
    ti_le = float(m.mean())
    if ti_le < 0.06:
        return False, f"đối tượng quá nhỏ {ti_le:.2f}"
    n, nhan, tk, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return False, "không có đối tượng"
    lon = tk[1:, cv2.CC_STAT_AREA].max()
    if not nhieu_manh and lon / max(1, m.sum()) < 0.85:
        return False, "nhiều mảnh rời"
    vien = np.concatenate([m[0], m[-1], m[:, 0], m[:, -1]]).mean()
    if vien > 0.6:
        return False, "dính kín mép (chưa tách khỏi nền)"
    return True, ""


def _tu_anh_ve(mo_ta, khoa):
    """Vẽ bằng Gemini (anh_ve.py) rồi tách nền + kiểm sạch/chữ (KHÔNG lọc 'hoạt hình': ảnh vẽ là chủ ý)."""
    import anh_ve
    import cat_nen
    import loc_chu
    from PIL import Image
    k = hashlib.md5(("ve|" + khoa).encode("utf-8")).hexdigest()[:14]
    for lan in range(2):
        f = anh_ve.ve(mo_ta, PUB, f"_{k}_ve{lan}_{__import__('threading').get_ident()}.png")
        if not f:
            return None
        out = os.path.join(PUB, f"{k}.png")
        thu = f[:-4] + "_tach.jpg"
        try:
            cat_nen.tach_nen(f, out)
            ok, ly_do = _sach(out, nhieu_manh=True)
            if ok:
                im = Image.open(out)
                nen = Image.new("RGB", im.size, (128, 128, 128))
                nen.paste(im, (0, 0), im)
                nen.save(thu, quality=92)
                if not loc_chu.co_chu_anh(thu):
                    if max(im.size) > 900:
                        im.thumbnail((900, 900), Image.LANCZOS)
                        im.save(out)
                    return {"src": f"cat/{k}.png", "url": "ve:" + mo_ta, "ve": True}
                ly_do = "chữ đè lên đối tượng"
            log(f"    ! ảnh vẽ '{mo_ta[:50]}' lần {lan + 1}: {ly_do}")
        finally:
            _xoa(f, thu, thu + ".chu3.json")
    return None


_KHOA_SO = __import__("threading").Lock()


def _ghi_so(khoa, gia_tri):
    so = os.path.join(CACHE_CHUNG, "anh_tach.json")
    with _KHOA_SO:
        da = doc_json(so, {}) or {}
        da[khoa] = gia_tri
        ghi_json(so, da)


_KHOA_VAI = {}


def _xoa(*fs):
    for f in fs:
        try:
            if f and os.path.isfile(f):
                os.remove(f)
        except OSError:
            pass


def lay(q, tranh=(), ve=None, truu_tuong=False):
    """Bọc _lay: một khoá cho mỗi (từ khoá, mô tả vẽ) -> chạy song song không làm trùng việc / đè file tạm."""
    k = (q or "", ve or "", tuple(sorted(tranh)))
    with _KHOA_SO:
        kh = _KHOA_VAI.setdefault(k, __import__("threading").Lock())
    with kh:
        return _lay(q, tranh, ve, truu_tuong)


def _lay(q, tranh=(), ve=None, truu_tuong=False):
    """Từ khoá tiếng Anh -> tên file tương đối trong remotion/public ("cat/<băm>.png") hoặc None.
    tranh: các URL ảnh gốc đã dùng cho vai khác trong cùng cảnh -> không lấy lại (hai vai không cùng một ảnh).
    ve: mô tả tiếng Anh để AI VẼ (13/10 user) — dùng khi truu_tuong (thứ không có ảnh thật cụ thể: vi khuẩn, enzyme,
    phân tử, dòng tiền…) hoặc khi không tìm được ảnh thật tách sạch."""
    import anh_google
    import cat_nen
    import loc_chu
    import loc_minh_hoa
    import nhung_siglip
    import xep_hang
    from PIL import Image
    os.makedirs(PUB, exist_ok=True)
    so = os.path.join(CACHE_CHUNG, "anh_tach.json")
    da = doc_json(so, {}) or {}
    q = (q or "").strip()
    if not q and not ve:
        return None
    tranh = set(tranh)
    khoa = q if not tranh else q + "|" + hashlib.md5("|".join(sorted(tranh)).encode()).hexdigest()[:8]
    v0 = da.get(khoa, "chua")
    if ve and (not q or v0 is None):                        # không có từ khoá / ảnh thật đã thử mà không đạt -> vẽ
        truu_tuong = True
    if truu_tuong and ve:                                   # trừu tượng: VẼ luôn, không tìm ảnh thật
        khoa = "ve|" + ve + ("|" + khoa if tranh else "")
        v = da.get(khoa)
        if isinstance(v, dict) and os.path.isfile(os.path.join(REMOTION, "public", v.get("src", ""))):
            return v
        r = _tu_anh_ve(ve, khoa)
        if r:                                               # vẽ hỏng (mạng / hết lượt) KHÔNG ghi sổ -> lần sau vẽ lại
            _ghi_so(khoa, r)
        return r
    if khoa in da:
        v = da[khoa]
        f = v.get("src") if isinstance(v, dict) else v
        if f and os.path.isfile(os.path.join(REMOTION, "public", f)):
            u = v.get("url", "") if isinstance(v, dict) else ""
            if not u or u not in tranh:
                return {"src": f, "url": u}
        elif not f:
            return None
    try:
        ds = anh_google.google_anh(f"{q} isolated on white background", n=30)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! ảnh tách nền '{q}': tìm lỗi {str(e)[:80]}")
        return None
    ra, ly = None, []
    if ds:
        qv = nhung_siglip.nhung_chu([f"a photograph of {q}"])[0]
        d = xep_hang.diem_anh([a["thumb"] or a["url"] for a in ds], qv, luong=4)
        # KHÔNG loại theo chữ trên ảnh gốc: ảnh nền trắng hầu hết là ảnh kho có watermark ở NỀN — tách nền là mất.
        # Soát chữ trên ảnh ĐÃ TÁCH (đặt lên nền xám): còn chữ = chữ đè lên chính đối tượng -> loại.
        # trang ảnh kho đóng watermark MỜ đè lên đối tượng (OCR không bắt được) -> bỏ theo nguồn
        xep = sorted((i for i in range(len(ds)) if min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 350
                      and ds[i].get("url") not in tranh
                      and not any(w in (ds[i].get("url", "") + " " + ds[i].get("trang", "")).lower() for w in KHO_WATERMARK)),
                     key=lambda i: -d[i])
        k = hashlib.md5(khoa.encode("utf-8")).hexdigest()[:14]
        ly = [f"{len(ds)} ảnh, {len(xep)} đủ cỡ"]
        for n, i in enumerate(xep[:6]):
            tam = os.path.join(PUB, f"_{k}_{n}_{__import__('threading').get_ident()}.jpg")            # tên RIÊNG từng ảnh thử (cache soát chữ theo tên file)
            thu = tam[:-4] + "_tach.jpg"
            out = os.path.join(PUB, f"{k}.png")
            try:
                raw = urllib.request.urlopen(urllib.request.Request(ds[i]["url"], headers=UA), timeout=25).read(20 << 20)
                Image.open(io.BytesIO(raw)).convert("RGB").save(tam, quality=94)
                if loc_minh_hoa.la_hoat_hinh_anh(tam):
                    ly.append("hoạt hình")
                    continue
                cat_nen.tach_nen(tam, out)
                ok, ly_do = _sach(out)
                if not ok:
                    ly.append(ly_do)
                    continue
                im = Image.open(out)
                nen = Image.new("RGB", im.size, (128, 128, 128))
                nen.paste(im, (0, 0), im)
                nen.save(thu, quality=92)
                if loc_chu.co_chu_anh(thu):
                    ly.append("chữ đè lên đối tượng")
                    continue
                if max(im.size) > 900:                       # đủ nét cho cỡ hiện ~450 px, file nhẹ
                    im.thumbnail((900, 900), Image.LANCZOS)
                    im.save(out)
                ra = {"src": f"cat/{k}.png", "url": ds[i]["url"]}
                break
            except Exception as e:                           # noqa: BLE001
                ly.append(f"lỗi {type(e).__name__}")
                continue
            finally:
                _xoa(tam, thu, tam + ".chu3.json", thu + ".chu3.json")
        if not ra and os.path.isfile(os.path.join(PUB, f"{k}.png")):
            os.remove(os.path.join(PUB, f"{k}.png"))
    if not ra and ve:                                       # không có ảnh thật tách sạch -> nhờ AI vẽ
        log(f"    ảnh thật '{q}' không đạt — vẽ bằng AI")
        ra = _tu_anh_ve(ve, "ve|" + ve + "|" + khoa)
    _ghi_so(khoa, ra)
    if not ra:
        log(f"    ! ảnh tách nền '{q}': không có ảnh tách sạch ({'; '.join(ly) if ds else 'không tìm thấy'})")
    return ra


# ================================================================ BỘ VAI MỘT LƯỢT (13/10 user)
# "mọi vật thể cần remotion gửi ảnh mẫu cho AI để tạo đối tượng … AI tạo theo kiểu story ảnh, mang về cắt ra": mỗi diễn
# cảnh nhờ Gemini vẽ TẤT CẢ vai trên MỘT ảnh nền trắng (hàng ngang, cách xa, cùng phong cách; đính kèm ảnh mẫu thật của
# vai cụ thể) -> tách nền cả ảnh -> cắt theo khoảng trắng dọc giữa các vai. Không thiếu vai, không lệch phong cách.

def _anh_mau(y, thu, k):
    """Ảnh mẫu thật cho một vai (để AI vẽ đúng hình dạng): ảnh đã tách trong sổ, không có thì ảnh Google đầu bảng."""
    if y.get("truu_tuong") or not (y.get("anh") or "").strip():
        return None
    v = (doc_json(os.path.join(CACHE_CHUNG, "anh_tach.json"), {}) or {}).get(y["anh"].strip())
    f = os.path.join(REMOTION, "public", v["src"]) if isinstance(v, dict) and v.get("src") else None
    if f and os.path.isfile(f) and not v.get("ve"):
        from PIL import Image
        im = Image.open(f)
        nen = Image.new("RGB", im.size, (255, 255, 255))
        nen.paste(im, (0, 0), im)
        out = os.path.join(thu, f"_mau_{k}.jpg")
        nen.save(out, quality=92)
        return out
    try:
        import anh_google
        ds = anh_google.google_anh(f"{y['anh']} isolated on white background", n=12)
    except Exception:                                        # noqa: BLE001
        return None
    from PIL import Image
    for a in ds[:4]:
        if any(w in (a.get("url", "") + " " + a.get("trang", "")).lower() for w in KHO_WATERMARK):
            continue
        try:
            raw = urllib.request.urlopen(urllib.request.Request(a["url"], headers=UA), timeout=20).read(15 << 20)
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            if min(im.size) < 300:
                continue
            im.thumbnail((1024, 1024))
            out = os.path.join(thu, f"_mau_{k}.jpg")
            im.save(out, quality=90)
            return out
        except Exception:                                    # noqa: BLE001
            continue
    return None


def _nhom_cot(m, n):
    """Chia theo dải cột có vật (khoảng trắng dọc) -> [mặt nạ bool từng vai] hoặc None."""
    cot = m.sum(axis=0) >= 3
    W = len(cot)
    chay, i = [], 0
    while i < W:
        if cot[i]:
            j = i
            while j < W and cot[j]:
                j += 1
            chay.append([i, j])
            i = j
        else:
            i += 1
    chay = [c for c in chay if c[1] - c[0] >= W * 0.02]
    while len(chay) > n:
        khe = [chay[t + 1][0] - chay[t][1] for t in range(len(chay) - 1)]
        t = khe.index(min(khe))
        chay[t:t + 2] = [[chay[t][0], chay[t + 1][1]]]
    if len(chay) != n:
        return None
    ra = []
    for a, b in chay:
        mm = np.zeros_like(m)
        mm[:, a:b] = m[:, a:b]
        ra.append(mm)
    return ra


def _nhom_khoi(m, n):
    """Dự phòng: theo KHỐI LIỀN — bỏ vụn, gộp khối chồng nhau theo chiều ngang, rồi gộp cặp gần nhất tới đủ n."""
    import cv2
    so, nhan, tk, tam = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    tong = m.size
    k = [t for t in range(1, so) if tk[t, cv2.CC_STAT_AREA] >= tong * 0.002]
    if len(k) < n:
        return None
    nhom = [{"id": [t], "x0": tk[t, 0], "x1": tk[t, 0] + tk[t, 2], "dt": tk[t, cv2.CC_STAT_AREA]} for t in k]
    doi = True
    while doi:                                               # khối chồng nhau theo chiều ngang = cùng một vai
        doi = False
        for a in range(len(nhom)):
            for b in range(a + 1, len(nhom)):
                A, B = nhom[a], nhom[b]
                if min(A["x1"], B["x1"]) - max(A["x0"], B["x0"]) > 0.3 * min(A["x1"] - A["x0"], B["x1"] - B["x0"]):
                    A["id"] += B["id"]
                    A["x0"], A["x1"], A["dt"] = min(A["x0"], B["x0"]), max(A["x1"], B["x1"]), A["dt"] + B["dt"]
                    del nhom[b]
                    doi = True
                    break
            if doi:
                break
    nhom.sort(key=lambda g: g["x0"])
    while len(nhom) > n:                                     # gộp cặp kề nhau có khe hẹp nhất
        khe = [nhom[t + 1]["x0"] - nhom[t]["x1"] for t in range(len(nhom) - 1)]
        t = khe.index(min(khe))
        A, B = nhom[t], nhom[t + 1]
        A["id"] += B["id"]
        A["x1"], A["dt"] = max(A["x1"], B["x1"]), A["dt"] + B["dt"]
        del nhom[t + 1]
    if len(nhom) != n:
        return None
    return [np.isin(nhan, g["id"]) & m for g in nhom]


def _bo_vun_duoi(mm):
    """Bỏ khối nhỏ (< 3% vật chính) nằm HẲN DƯỚI đáy vật chính — chỗ AI hay tự viết số/chữ dưới vật."""
    import cv2
    so, nhan, tk, _ = cv2.connectedComponentsWithStats(mm.astype(np.uint8), 8)
    if so <= 2:
        return mm
    lon = 1 + int(np.argmax(tk[1:, cv2.CC_STAT_AREA]))
    day = tk[lon, 1] + tk[lon, 3]
    for t in range(1, so):
        if t != lon and tk[t, cv2.CC_STAT_AREA] < 0.03 * tk[lon, cv2.CC_STAT_AREA] and tk[t, 1] > day - 2:
            mm = mm & (nhan != t)
    return mm


def _cat_hang(sheet_png, n, k):
    """Tách nền ảnh bộ vai rồi cắt ra đúng n vai (trái -> phải) -> [đường dẫn PNG] hoặc None."""
    import cat_nen
    import loc_chu
    from PIL import Image
    img = Image.open(sheet_png).convert("RGB")
    a = cat_nen.mat_na(img)
    a = np.clip((a - 0.12) / 0.76, 0, 1)
    m = a > 0.5
    nhom = _nhom_cot(m, n) or _nhom_khoi(m, n)
    if not nhom:
        return None
    ra = []
    for t, mm in enumerate(nhom):
        mm = _bo_vun_duoi(mm)
        ys, xs = np.nonzero(mm)
        if len(xs) == 0:
            return None
        y0, y1, x0, x1 = max(0, ys.min() - 4), ys.max() + 5, max(0, xs.min() - 4), xs.max() + 5
        alpha = (a * 255).astype(np.uint8)
        alpha[~__import__("scipy.ndimage", fromlist=["binary_dilation"]).binary_dilation(mm, iterations=3)] = 0
        rgba = np.dstack([np.asarray(img), alpha])[y0:y1, x0:x1]
        o = Image.fromarray(rgba, "RGBA")
        out = os.path.join(PUB, f"{k}_{t}.png")
        o.save(out)
        ok, ly_do = _sach(out, nhieu_manh=True)
        thu = out[:-4] + "_tach.jpg"
        nen = Image.new("RGB", o.size, (128, 128, 128))
        nen.paste(o, (0, 0), o)
        nen.save(thu, quality=92)
        co_chu = loc_chu.co_chu_anh(thu)
        _xoa(thu, thu + ".chu3.json")
        if not ok or co_chu:
            log(f"    ! bộ vai: mảnh {t + 1} {'có chữ' if co_chu else ly_do}")
            return None
        ra.append(f"cat/{k}_{t}.png")
    return ra


def bo_canh(vai):
    """vai: [{ten, anh, ve, truu_tuong}] (<= 3) -> [{src, url}] đủ từng vai (cùng thứ tự) hoặc None (để lùi về cách cũ)."""
    import json as _json
    import threading
    import anh_ve
    vai = [y for y in vai if isinstance(y, dict)][:4]
    if not vai:
        return None
    k = hashlib.md5(_json.dumps([(y.get("ten"), y.get("anh"), y.get("ve")) for y in vai], ensure_ascii=False)
                    .encode("utf-8")).hexdigest()[:14]
    khoa = "bo|" + k
    v = (doc_json(os.path.join(CACHE_CHUNG, "anh_tach.json"), {}) or {}).get(khoa)
    if isinstance(v, list) and all(os.path.isfile(os.path.join(REMOTION, "public", x)) for x in v):
        return [{"src": x, "url": f"bo:{k}:{t}"} for t, x in enumerate(v)]
    os.makedirs(PUB, exist_ok=True)
    tam = os.path.join(PUB, f"_bo_{k}_{threading.get_ident()}")
    os.makedirs(tam, exist_ok=True)
    mau = []
    for t, y in enumerate(vai):
        f = _anh_mau(y, tam, t)
        if f:
            mau.append((t, f))
    import re
    THU = ["the first", "the second", "the third", "the fourth"]

    def _doi(t):                                             # "SAME as actor 2 but…" -> "exactly the same as the second subject but…"
        return re.sub(r"same as (?:actor |subject )?(\d)", lambda mt: "exactly the same as " + THU[min(3, int(mt.group(1)))] + " subject",
                      t, flags=re.I)
    phan = [_doi((y.get("ve") or y.get("anh") or y.get("ten") or "").strip().rstrip(".")) for y in vai]
    mo_ta = "From left to right: " + "; then ".join(phan) + "."
    if any("same as" in x.lower() for x in phan):
        mo_ta += (" A subject described as 'exactly the same as …' must look identical to that subject (same species, "
                  "colours, angle, size) except for the stated change.")
    n = len(vai)
    prompt = (f"Create ONE wide image on a plain pure white background showing exactly {n} separate subject"
              f"{'s' if n > 1 else ''} in a single horizontal row, left to right in this order, with WIDE empty white space "
              f"between them (they must not touch or overlap), all in the same realistic, highly detailed style and "
              f"lighting (photorealistic, or a realistic 3D render for microscopic things), each fully visible and "
              f"roughly the same size. {mo_ta}\n"
              + (("The attached reference photo" + ("s show" if len(mau) > 1 else " shows") + " the real appearance of "
                  + ", ".join(THU[t] for t, _ in mau) + " subject" + ("s" if len(mau) > 1 else "") + " (in that order) — "
                  "keep it faithful.\n") if mau else "")
              + "Absolutely NO text anywhere: no numbers, no letters, no captions or labels under the subjects, no arrows, "
                "no ground shadow, no frame; any screen must be blank.")
    ra = None
    try:
        for lan in range(2):
            f = anh_ve.ve_prompt(prompt, tam, f"bo_{lan}.png", tep=[x for _, x in mau])
            if not f:
                break
            ra = _cat_hang(f, n, f"{k}")
            if ra:
                break
            log(f"    ! bộ vai '{', '.join(y.get('ten') or '' for y in vai)}' lần {lan + 1}: cắt không ra đúng {n} vai")
    finally:
        import shutil
        shutil.rmtree(tam, ignore_errors=True)
    if ra:
        _ghi_so(khoa, ra)
        return [{"src": x, "url": f"bo:{k}:{t}"} for t, x in enumerate(ra)]
    return None
