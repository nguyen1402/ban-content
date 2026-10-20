# -*- coding: utf-8 -*-
"""MÔ TẢ HÌNH THEO TỪNG VẾ (18/10 user: cảnh nói "sói được đưa trở lại… nai… liễu… hải ly… rồi đến các loài chim" mà
hiện toàn chim — cả cảnh 9 s chỉ có MỘT mô tả).

Mỗi cảnh chia thành các VẾ theo chỗ nghỉ thật của giọng (goi_y.cho_nghi_giong_doc — đúng chỗ đổi hình của bản thô); chữ
mỗi vế ước theo tỉ lệ ký tự trong cảnh. AI viết cho từng vế:
  * mo_ta_en: khung hình nên thấy trong lúc đọc vế đó (đúng đối tượng của vế; vế bình luận -> cảnh chung của cảnh)
  * tim_en  : 2-5 từ tìm video YouTube cho vế đó (hình ảnh chung: vật + hành động / bối cảnh, không tên riêng)
goi_y chấm clip theo mô tả của VẾ đang lấp; 🤖 tìm bổ sung bằng tim_en cho vế chưa có clip khớp.
Lưu ra/<dự án>/mo_ta_ve.json, khoá theo (chữ cảnh + mốc vế) -> chạy lại chỉ hỏi cảnh đã đổi."""
import hashlib
import os

from common import doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

CANH_MOI_LO = 12
_VEC = {}

_P = """Bạn dựng hình cho video tư liệu: footage thật (video quay ngoài đời) chạy theo lời đọc, ĐỔI HÌNH ở mỗi VẾ dưới đây.
Với MỖI VẾ của mỗi cảnh, viết:
  - "mo_ta_en": một câu TIẾNG ANH tả khung hình nên thấy TRONG LÚC ĐỌC VẾ ĐÓ — đúng đối tượng / hành động mà VẾ ĐÓ nhắc
    (vế nhắc sói thì sói, vế nhắc chim thì chim). Vế chỉ là bình luận, câu hỏi, số liệu, chuyển ý -> tả ĐỐI TƯỢNG CHÍNH
    CỦA ĐOẠN (ghi trong ngoặc sau id cảnh) — không bịa đối tượng mới, không tả người ngồi bàn / văn phòng / màn hình.
  - "tim_en": 2-5 từ TIẾNG ANH để tìm video YouTube cho khung hình đó: vật / con vật / người + hành động hoặc bối cảnh
    (ví dụ "gray wolf walking river", "beaver building dam"). Không tên riêng người, không tên sự kiện, không chữ
    cinematic / b-roll / 4k / footage.
  - "rieng": true CHỈ KHI vế NHẮC RÕ một con vật / người / vật / nơi chốn nhìn thấy được KHÁC đối tượng chính của đoạn
    (ví dụ đoạn về dê mà vế nói "nước cuốn bùn phủ kín rạn san hô" -> true). Vế không nhắc đối tượng nào mới, hoặc chỉ nhắc
    lại đối tượng chính -> false (hình vẫn là đối tượng chính của đoạn).
  - "nhac_lai": true nếu vế NHẮC LẠI một sự việc / cảnh đã kể ở phần TRƯỚC của video ("nếu bạn còn nhớ", "như đã nói",
    "đàn dê trước đó cũng…") — chỗ đó được dùng lại hình cũ.
Trả ĐÚNG số vế của mỗi cảnh, theo đúng thứ tự.

{ds}

Chỉ trả JSON: {{"<id cảnh>": [{{"mo_ta_en": "...", "tim_en": "...", "rieng": false, "nhac_lai": false}}, ...], ...}}"""


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "mo_ta_ve.json")


def _cat_ve(text, L, moc):
    """Chữ của từng vế: cắt câu theo tỉ lệ thời gian (moc: điểm chia trong cảnh, giây), bắt vào khoảng trắng gần nhất."""
    t = str(text or "").strip()
    cat, tr = [], 0
    for x in moc:
        k = int(round(len(t) * x / max(L, 0.01)))
        trai, phai = t.rfind(" ", tr, max(k, tr) + 1), t.find(" ", k)
        k = min((v for v in (trai, phai) if v > tr), key=lambda v: abs(v - k), default=k)
        cat.append(k)
        tr = k
    bien = [0] + cat + [len(t)]
    return [t[a:b].strip(" ,.;:") for a, b in zip(bien, bien[1:])]


def ve_canh(du_an, c, lang):
    """[(bd, kt, chữ vế)] (giây tính từ đầu cảnh) của một cảnh theo chỗ nghỉ giọng."""
    import goi_y
    L = float(c["dai"]) - float(c.get("nghi_sau") or 0)
    moc = goi_y.cho_nghi_giong_doc(du_an, c, lang) if lang else []
    loi = _cat_ve(c.get("text"), L, moc)
    bien = [0.0] + list(moc) + [L]
    return [(round(a, 2), round(b, 2), s) for (a, b), s in zip(zip(bien, bien[1:]), loi)]


def _khoa(c, ve, dt=""):
    return hashlib.md5(("v2|" + str(c.get("text")) + "|" + dt + "|" + ",".join(f"{a:.1f}" for a, _, _ in ve)).encode("utf-8")).hexdigest()[:12]


def lam(du_an, _lan=0):
    """Điền mô tả theo vế cho mọi cảnh còn thiếu / đã đổi. Trả {id cảnh (str): [{bd, kt, loi, mo_ta_en, tim_en}]}."""
    import goi_y
    canh = doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []
    try:
        lang = goi_y._lang(du_an, goi_y.LANG_GIONG)          # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        lang = []
    da = doc_json(_p(du_an), {}) or {}
    dt_cua = {}                                              # 18/10: đối tượng chính của đoạn nội dung chứa cảnh (chu_de.py)
    for cd in (doc_json(os.path.join(thu_muc_du_an(du_an)[1], "chu_de.json"), {}) or {}).get("chu_de") or []:
        for i in range(cd.get("canh_tu", 0), cd.get("canh_den", 0) + 1):
            dt_cua[str(i)] = cd.get("doi_tuong") or ""
    can, ve_cua = [], {}
    for c in canh:
        ve = ve_canh(du_an, c, lang)
        ve_cua[str(c["id"])] = ve
        if (da.get(str(c["id"])) or {}).get("_k") != _khoa(c, ve, dt_cua.get(str(c["id"]), "")):
            can.append(c)
    if can:
        lots = [can[i:i + CANH_MOI_LO] for i in range(0, len(can), CANH_MOI_LO)]
        log(f"  mô tả hình theo vế: {len(can)} cảnh, {len(lots)} lô…")
        prompts = []
        for lot in lots:
            ds = "\n\n".join(f"CẢNH {c['id']} (đối tượng chính của đoạn: {dt_cua.get(str(c['id'])) or 'theo lời'}): "
                             f"{str(c.get('text', '')).strip()}\n" + "\n".join(
                f"  vế {k + 1}: {s}" for k, (_, _, s) in enumerate(ve_cua[str(c["id"])])) for c in lot)
            prompts.append(_P.format(ds=ds))
        for lot, tra in zip(lots, hoi_nhieu(prompts, timeout=300)):
            j = rut_json(tra or "")
            if not isinstance(j, dict):
                log(f"    ! mô tả theo vế: lô cảnh {lot[0]['id']}-{lot[-1]['id']} không ra JSON "
                    f"({len(tra or '')} ký tự: {(tra or '')[:120]!r})")
                continue
            import re
            j = {(re.findall(r"\d+", str(k)) or [k])[-1]: v for k, v in j.items()}   # AI hay ghi khoá "CẢNH 13"
            for c in lot:
                ve = ve_cua[str(c["id"])]
                xs = j.get(str(c["id"])) or []
                if not isinstance(xs, list) or not xs:
                    continue
                xs = (xs + [xs[-1]] * len(ve))[:len(ve)]          # thiếu vế: lấy mô tả vế trước
                da[str(c["id"])] = {"_k": _khoa(c, ve, dt_cua.get(str(c["id"]), "")), "ve": [
                    {"bd": a, "kt": b, "loi": s, "mo_ta_en": str((x or {}).get("mo_ta_en") or "").strip(),
                     "tim_en": str((x or {}).get("tim_en") or "").strip(),
                     "rieng": bool((x or {}).get("rieng")), "nhac_lai": bool((x or {}).get("nhac_lai"))}
                    for (a, b, s), x in zip(ve, xs)]}
        ghi_json(_p(du_an), da)
        xong = sum(1 for c in can if (da.get(str(c['id'])) or {}).get('_k') == _khoa(c, ve_cua[str(c['id'])], dt_cua.get(str(c['id']), '')))
        log(f"    mô tả theo vế: {xong}/{len(can)} cảnh")
        if xong < len(can) and _lan == 0:                    # lô hỏng JSON / AI lỗi: hỏi lại một lượt cho cảnh còn thiếu
            return lam(du_an, 1)
    return {k: v["ve"] for k, v in da.items() if isinstance(v, dict) and v.get("ve")}


def doc(du_an):
    return {k: v["ve"] for k, v in (doc_json(_p(du_an), {}) or {}).items() if isinstance(v, dict) and v.get("ve")}


def nhac_lai(ve):
    """[(bd, kt)] các vế NHẮC LẠI sự việc cũ (được dùng lại hình cũ, vẫn cách >= 15 s)."""
    return [(float(v["bd"]), float(v["kt"])) for v in ve or [] if v.get("nhac_lai")]


def vec_ve(du_an, cid, ve, chi_rieng=True):
    """[(bd, kt, vector)] của các vế một cảnh (mô tả rỗng bị bỏ). Cache trong bộ nhớ theo (dự án, cảnh, mô tả)."""
    import nhung_siglip
    ra = []
    for v in ve:
        if not v.get("mo_ta_en") or (chi_rieng and not v.get("rieng")):   # 19/10: vế trung tính -> đối tượng chính của đoạn
            continue
        k = (du_an, cid, v["mo_ta_en"])
        if k not in _VEC:
            _VEC[k] = nhung_siglip.nhung_chu([v["mo_ta_en"]])[0]
        ra.append((float(v["bd"]), float(v["kt"]), _VEC[k]))
    return ra
