# -*- coding: utf-8 -*-
"""Ý CỐT LÕI -> ẢNH AI TOÀN MÀN HÌNH (18/10 user).

User: ảnh AI không theo tỉ lệ cố định mà đặt ĐÚNG những chỗ cốt lõi — quá trình, hành động, cơ chế mà người xem cần THẤY
mới hiểu "đoạn này đang nói vấn đề gì" (cốt lõi của cả video). Ở các đoạn đó ảnh AI THAY HẲN video (toàn màn hình);
phần còn lại footage thật lấp.

  1. lap(du_an): gửi CẢ kịch bản cho AI -> 5-10 ý cốt lõi, mỗi ý = các cảnh liền nhau tả quá trình / hành động + CHUỖI 1-4
     ảnh nối tiếp (+ mô tả nhân vật lặp lại để ảnh trông liền mạch). Tổng thời lượng <= TRAN_TI_LE (trần mềm: bỏ ý ưu
     tiên thấp). Mốc từng ảnh chia đều rồi BẮT vào chỗ nghỉ thật của giọng (hình băm theo nhịp nghỉ giọng đọc).
     Lưu ra/<dự án>/cot_loi.json — người dùng xem / sửa / xoá trước khi vẽ (bảng 🎯 trên giao diện).
  2. ve(du_an): vẽ ảnh còn thiếu (Gemini cookie, hết lượt -> Flow) — ảnh chụp ngang 16:9 siêu thực, ghi vào kho dự án
     (loai "anh", cot_loi=True). Chạy song song lúc 🤖 tải video.
  3. khoang(du_an): [(bd, kt, kho_id)] tuyệt đối — goi_y đặt ảnh thay video; 🤖 bỏ qua footage; ✨ không chồng lớp AI khác.
"""
import hashlib
import os
import threading
import time

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

DUNG_BAN_THO = False        # 18/10 user: "không dùng ảnh AI cho bản thô" -> 🤖 không lập/vẽ, goi_y không đặt, ✨ không lọc theo
#                             (bản thô chỉ footage; ảnh AI chỉ ở bước ✨ đè lên hành động / quá trình / con vật)
TRAN_TI_LE = 0.40            # tổng ảnh cốt lõi tối đa ~40% thời lượng (trần mềm, không phải định mức)
GIAY_MOI_ANH = 3.5           # gợi ý cho AI: ~1 ảnh mỗi 3-5 s lời kể
ANH_NGAN_NHAT = 2.0          # một ảnh hiện ít nhất bấy nhiêu giây
_KHOA = threading.Lock()
TT = {}


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "cot_loi.json")


def doc(du_an):
    return doc_json(_p(du_an), {}) or {}


def _canh(du_an):
    return doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []


def _hash(canh):
    return hashlib.md5("|".join(f"{c['id']}:{str(c.get('text', '')).strip()}" for c in canh).encode("utf-8")).hexdigest()[:16]


_P = """Bạn là đạo diễn hình ảnh cho video tư liệu kể chuyện. Footage thật (video quay ngoài đời) sẽ lấp phần lớn video.
Nhiệm vụ: tìm những chỗ CỐT LÕI cần ẢNH MINH HOẠ (AI vẽ, thay hẳn video, toàn màn hình) để người xem NHÌN là hiểu
"đoạn này đang nói vấn đề gì" — các vấn đề cốt lõi của CẢ video.

KỊCH BẢN (mỗi dòng: id cảnh [số giây] lời kể):
{ds}

YÊU CẦU:
1. Rút ra 5-10 Ý CỐT LÕI của câu chuyện (vấn đề, nguyên nhân, cơ chế, giải pháp, diễn biến then chốt, kết quả).
2. Với mỗi ý, chọn ĐÚNG các cảnh LIỀN NHAU đang TẢ một QUÁ TRÌNH / HÀNH ĐỘNG / CƠ CHẾ cụ thể nhìn thấy được (ví dụ:
   "con vật được thả lên bờ rồi lần theo dấu con mồi", "đất trôi theo mưa xuống rạn san hô", "viên thuốc dưới da tự kích
   hoạt"). KHÔNG chọn: phong cảnh chung chung, lời chào / kêu gọi đăng ký, câu bình luận trừu tượng, số liệu khô.
3. Mỗi ý vẽ CHUỖI 1-4 ảnh nối tiếp theo diễn biến (khoảng 1 ảnh cho mỗi {giay} giây lời kể của các cảnh đó). Mỗi ảnh
   là MỘT khoảnh khắc cụ thể, viết bằng TIẾNG ANH như mô tả một bức ẢNH CHỤP tư liệu thật (ai/cái gì, đang làm gì, ở
   đâu, góc máy) — không chữ, không sơ đồ.
4. "nhan_vat": nhân vật / con vật / vật xuất hiện LẶP LẠI ở nhiều ảnh (kèm mô tả ngoại hình tiếng Anh cố định) để các ảnh
   trông cùng một nhân vật.
5. "uu_tien": 1 = cốt lõi nhất, 3 = phụ.

Chỉ trả về JSON hợp lệ, không lời dẫn:
{{"nhan_vat": [{{"ten": "...", "mo_ta_en": "..."}}],
 "y": [{{"ten": "tên ý ngắn tiếng Việt", "uu_tien": 1, "canh_tu": 0, "canh_den": 0, "vi_sao": "...",
        "chuoi": ["English photo description step 1", "..."]}}]}}"""


def lap(du_an, buoc_lai=False):
    """Lập (hoặc đọc lại) danh sách ý cốt lõi + chuỗi ảnh + mốc thời gian. Trả dict cot_loi.json."""
    canh = sorted(_canh(du_an), key=lambda c: int(c["id"]))
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — chạy bước 1 trước")
    h = _hash(canh)
    da = doc(du_an)
    if not buoc_lai and da.get("_hash") == h and da.get("y"):
        return da
    theo_id = {int(c["id"]): c for c in canh}
    tong = max(float(c["bat_dau"]) + float(c["dai"]) for c in canh)
    # kịch bản dài: chia lượt ~20k ký tự (Gemini web hỏng JSON khi prompt quá dài)
    lots, cur, n = [], [], 0
    for c in canh:
        dong = f"{c['id']} [{float(c['dai']):.0f}s] {str(c.get('text', '')).strip()}"
        if cur and n + len(dong) > 20000:
            lots.append(cur)
            cur, n = [], 0
        cur.append(dong)
        n += len(dong)
    if cur:
        lots.append(cur)
    nhan_vat, ys = [], []
    for lot in lots:
        j = None
        for _ in range(2):
            j = rut_json(hoi_llm(_P.format(ds="\n".join(lot), giay=GIAY_MOI_ANH), timeout=300))
            if isinstance(j, dict) and isinstance(j.get("y"), list):
                break
        if not isinstance(j, dict):
            log("    ! ý cốt lõi: AI không trả JSON hợp lệ cho một lượt")
            continue
        nhan_vat += [x for x in (j.get("nhan_vat") or []) if isinstance(x, dict) and x.get("mo_ta_en")]
        ys += [x for x in j.get("y") or [] if isinstance(x, dict)]
    # chuẩn hoá: cảnh có thật, liền nhau, không chồng ý trước; ảnh >= ANH_NGAN_NHAT s
    sach, da_dung = [], set()
    for x in ys:
        try:
            a, b = int(x.get("canh_tu")), int(x.get("canh_den"))
        except (TypeError, ValueError):
            continue
        a, b = min(a, b), max(a, b)
        ids = [i for i in range(a, b + 1) if i in theo_id and i not in da_dung]
        chuoi = [str(s).strip() for s in (x.get("chuoi") or []) if str(s).strip()][:4]
        if not ids or not chuoi or ids != list(range(ids[0], ids[-1] + 1)):
            continue
        bd = float(theo_id[ids[0]]["bat_dau"])
        kt = float(theo_id[ids[-1]]["bat_dau"]) + float(theo_id[ids[-1]]["dai"]) - float(theo_id[ids[-1]].get("nghi_sau") or 0)
        chuoi = chuoi[:max(1, int((kt - bd) // ANH_NGAN_NHAT))]
        da_dung.update(ids)
        sach.append({"ten": str(x.get("ten") or "").strip(), "uu_tien": int(x.get("uu_tien") or 2) if str(x.get("uu_tien") or "2").isdigit() else 2,
                     "vi_sao": str(x.get("vi_sao") or "").strip(), "canh": ids, "bd": round(bd, 2), "kt": round(kt, 2),
                     "anh": [{"mo_ta_en": s} for s in chuoi]})
    # trần mềm: bỏ ý ưu tiên thấp (rồi dài) cho tới khi tổng <= TRAN_TI_LE
    sach.sort(key=lambda y: (y["uu_tien"], -(y["kt"] - y["bd"])))
    giu, cong = [], 0.0
    for y in sach:
        if cong + (y["kt"] - y["bd"]) > TRAN_TI_LE * tong and giu:
            log(f"    ý cốt lõi bỏ (vượt trần {TRAN_TI_LE:.0%}): {y['ten']}")
            continue
        giu.append(y)
        cong += y["kt"] - y["bd"]
    giu.sort(key=lambda y: y["bd"])
    _bo_sung_anh(giu, theo_id)
    _dat_moc(du_an, giu)
    ra = {"_hash": h, "luc": time.time(), "nhan_vat": nhan_vat, "y": giu}
    with _KHOA:
        ghi_json(_p(du_an), ra)
    log(f"  ý cốt lõi: {len(giu)} ý, {sum(len(y['anh']) for y in giu)} ảnh, {cong:.0f}s / {tong:.0f}s "
        f"({cong / max(tong, 1):.0%} thời lượng)")
    return ra


ANH_TOI_DA_GIAY = 5.0        # một ảnh đứng quá bấy nhiêu giây -> xin thêm bước (hình băm theo nhịp nghỉ giọng ~2 s)

_P_THEM = """Mỗi ý dưới đây là một QUÁ TRÌNH trong video tư liệu, đang có chuỗi ảnh quá ít so với thời lượng lời kể.
Viết lại chuỗi cho ĐÚNG số ảnh yêu cầu: các khoảnh khắc nối tiếp theo diễn biến lời kể, mỗi ảnh một khoảnh khắc / góc máy
khác nhau, mô tả bằng TIẾNG ANH như một bức ẢNH CHỤP tư liệu thật (không chữ, không sơ đồ). Giữ nhân vật như chuỗi cũ.

{ds}

Chỉ trả JSON: {{"<số thứ tự ý>": ["English photo description", ...], ...}}"""


def _bo_sung_anh(ys, theo_id):
    """18/10 đo cho_digo: AI hay cho 2 ảnh cho đoạn 15-30 s (một ảnh đứng 15 s) -> hỏi thêm một lượt cho đủ
    ~1 ảnh / GIAY_MOI_ANH s (tối đa 8 ảnh / ý)."""
    import math
    can = []
    for k, y in enumerate(ys):
        n = min(8, max(1, math.ceil((y["kt"] - y["bd"]) / GIAY_MOI_ANH)))
        if (y["kt"] - y["bd"]) / len(y["anh"]) > ANH_TOI_DA_GIAY and n > len(y["anh"]):
            can.append((k, n))
    if not can:
        return
    ds = "\n\n".join(
        f"{k + 1}. Ý: {ys[k]['ten']} — CẦN ĐÚNG {n} ẢNH\n   Lời kể: "
        + " ".join(str(theo_id[i].get("text", "")) for i in ys[k]["canh"])
        + "\n   Chuỗi cũ: " + " | ".join(a["mo_ta_en"] for a in ys[k]["anh"]) for k, n in can)
    j = rut_json(hoi_llm(_P_THEM.format(ds=ds), timeout=240))
    if not isinstance(j, dict):
        log("    ! ý cốt lõi: không xin thêm được ảnh (giữ chuỗi cũ)")
        return
    for k, n in can:
        moi = [str(s).strip() for s in (j.get(str(k + 1)) or []) if str(s).strip()]
        if len(moi) > len(ys[k]["anh"]):
            ys[k]["anh"] = [{"mo_ta_en": s} for s in moi[:n]]


def _dat_moc(du_an, ys):
    """Mốc từng ảnh: chia đều đoạn của ý rồi bắt vào CHỖ NGHỈ THẬT của giọng gần nhất (±1 s) — đổi hình đúng nhịp."""
    try:
        import goi_y
        lang = [x for x, d in goi_y._lang(du_an, goi_y.LANG_GIONG)]   # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        lang = []
    for y in ys:
        n = len(y["anh"])
        moc = [y["bd"]]
        for k in range(1, n):
            muc = y["bd"] + (y["kt"] - y["bd"]) * k / n
            gan = [x for x in lang if abs(x - muc) <= 1.0 and x - moc[-1] >= ANH_NGAN_NHAT and y["kt"] - x >= ANH_NGAN_NHAT]
            moc.append(round(min(gan, key=lambda x: abs(x - muc)) if gan else muc, 2))
        moc.append(y["kt"])
        for k, a in enumerate(y["anh"]):
            a["bd"], a["kt"] = round(moc[k], 2), round(moc[k + 1], 2)


def luu(du_an, ys):
    """Người dùng sửa / xoá ý hoặc câu mô tả ảnh trên giao diện. Ảnh đổi câu mô tả -> vẽ lại; mốc tính lại."""
    da = doc(du_an)
    cu = {a.get("mo_ta_en"): a for y in da.get("y") or [] for a in y.get("anh") or []}
    for y in ys:
        y["anh"] = [dict(cu.get(a.get("mo_ta_en")) or {}, mo_ta_en=a.get("mo_ta_en", "").strip())
                    for a in y.get("anh") or [] if a.get("mo_ta_en", "").strip()]
    ys = [y for y in ys if y.get("anh")]
    _dat_moc(du_an, ys)
    da["y"] = ys
    with _KHOA:
        ghi_json(_p(du_an), da)
    return da


def _prompt(mo_ta, nhan_vat):
    nv = " ".join(f"{x.get('ten', '')}: {x['mo_ta_en']}." for x in nhan_vat if x.get("mo_ta_en"))
    return ("Create an ultra-realistic high-resolution documentary PHOTOGRAPH in WIDE 16:9 LANDSCAPE (horizontal) format "
            f"that fills the whole frame. Scene: {mo_ta}. "
            + (f"Recurring subjects must look exactly like this: {nv} " if nv else "")
            + _phong_cach() + " No text, no letters, no captions, "
              "no logos, no watermark, no borders, no collage, no illustration style.")


def _phong_cach():
    """19/10 user: phong cách ảnh cố định (chinh_sua/anh_ve.PHONG_CACH)."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    return anh_ve.phong_cach()


def ve(du_an, luong=3):
    """Vẽ mọi ảnh cốt lõi còn thiếu -> kho dự án (kid "ai_<hash>"). Trả số ảnh vẽ được trong lượt này."""
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from PIL import Image
    import dung_tay
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    da = doc(du_an)
    nv = da.get("nhan_vat") or []
    thu = os.path.join(thu_muc_du_an(du_an)[1], "kho", "anh")
    kho = dung_tay.doc_kho(du_an)
    viec = []
    for y in da.get("y") or []:
        for a in y.get("anh") or []:
            p = _prompt(a["mo_ta_en"], nv)
            kid = "ai_" + hashlib.md5(p.encode("utf-8")).hexdigest()[:12]
            a["kho_id"], a["canh"] = kid, y["canh"][0]
            m = kho.get(kid) or {}
            if not (m.get("trang_thai") == "xong" and os.path.isfile(m.get("file", ""))):
                viec.append((kid, p, a, y))
    with _KHOA:
        moi = doc(du_an)
        if moi.get("_hash") == da.get("_hash"):
            moi["y"] = da["y"]
            ghi_json(_p(du_an), moi)
    TT[du_an] = {"dang": True, "xong": 0, "tong": len(viec)}
    if not viec:
        TT[du_an]["dang"] = False
        return 0
    log(f"  vẽ ảnh cốt lõi: {len(viec)} ảnh (Gemini cookie, hết lượt -> Flow)…")

    def mot(job):
        kid, p, a, y = job
        for lan in range(3):
            f = anh_ve.ve_prompt(p if lan == 0 else p + " Absolutely NO writing anywhere.", thu, f"_{kid}_{lan}.png")
            if not f:
                continue
            try:
                im = Image.open(f).convert("RGB")
                w, h = im.size
                if w < 1.2 * h:                              # AI trả ảnh vuông / dọc -> cắt giữa về 16:9
                    hh = int(w * 9 / 16)
                    im = im.crop((0, (h - hh) // 2, w, (h - hh) // 2 + hh))
                dich = os.path.join(thu, kid + ".jpg")
                im.save(dich, quality=95)
                os.remove(f)
            except Exception as e:                           # noqa: BLE001
                log(f"    ! ảnh cốt lõi {kid}: {str(e)[:80]}")
                continue
            dung_tay._cap_nhat_kho(du_an, kid, loai="anh", tieu_de=f"Cốt lõi: {y['ten'][:50]}", file=dich,   # noqa: SLF001
                                   nguon="ai_cot_loi", trang_thai="xong", pt=100.0, rong=im.size[0], cao=im.size[1],
                                   luc=time.time(), cot_loi=True, cho_canh=y["canh"][0])
            with _KHOA:
                TT[du_an]["xong"] += 1
            return True
        log(f"    ! không vẽ được ảnh cốt lõi: {a['mo_ta_en'][:70]}")
        return False
    with ThreadPoolExecutor(luong) as ex:
        n = sum(1 for r in ex.map(mot, viec) if r)
    TT[du_an]["dang"] = False
    log(f"  vẽ ảnh cốt lõi xong: {n}/{len(viec)}")
    return n


def ve_nen(du_an):
    """Vẽ chạy nền (giao diện / 🤖 gọi, không chờ). Trả Thread."""
    th = threading.Thread(target=lambda: _an_toan(ve, du_an), daemon=True)
    th.start()
    return th


def _an_toan(f, *a):
    try:
        return f(*a)
    except Exception as e:                                   # noqa: BLE001
        log(f"  ! ảnh cốt lõi lỗi: {str(e)[:160]}")
        TT.setdefault(a[0], {})["dang"] = False


def khoang(du_an, chi_da_ve=True):
    """[(bd, kt, kho_id)] tuyệt đối của các ảnh cốt lõi (chi_da_ve: chỉ ảnh đã vẽ xong trong kho)."""
    if not DUNG_BAN_THO:
        return []
    da = doc(du_an)
    if not da.get("y"):
        return []
    kho = None
    if chi_da_ve:
        import dung_tay
        kho = dung_tay.doc_kho(du_an)
    ra = []
    for y in da["y"]:
        for a in y.get("anh") or []:
            kid = a.get("kho_id")
            if chi_da_ve and not (kid and (kho.get(kid) or {}).get("trang_thai") == "xong"):
                continue
            ra.append((float(a["bd"]), float(a["kt"]), kid))
    return sorted(ra)


def khoang_y(du_an):
    """[(bd, kt)] của mọi ý cốt lõi (dù ảnh đã vẽ hay chưa) — 🤖 bỏ qua footage ở các đoạn này."""
    if not DUNG_BAN_THO:
        return []
    return sorted((float(y["bd"]), float(y["kt"])) for y in doc(du_an).get("y") or [])
