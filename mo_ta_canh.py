# -*- coding: utf-8 -*-
"""MÔ TẢ KHUNG HÌNH tiếng Anh cho từng cảnh (hỏi ChatGPT) — để SigLIP chấm theo Ý NGHĨA câu (hành động + bối cảnh),
không chỉ theo danh từ. 12/10 đo trên 12 cảnh hành động th_nghi_m_2: chấm theo câu này ra đúng hành động ~10/12
(chim xé tổ, ong vây cửa tổ, ong dính lưới điện...), cách cũ (câu 'nên chiếu' tiếng Việt + từ khoá) lặp một cảnh
chim đứng cạnh tổ. Mỗi cảnh có:
  canh_en      2 câu mô tả khung hình tiếng Anh (6-14 từ, cụ thể, nhìn thấy được)
  loai         hanh_dong | dia_diem | vat | nguoi | khai_niem
  dia_danh_en  tên địa danh tiếng Anh (kèm nước) khi loai = dia_diem — để tìm ẢNH THẬT của nơi đó
Ghi thẳng vào ra/<dự án>/tu_khoa.json (thêm trường), cache ở cache/du_an/<dự án>/mo_ta_canh.json."""
import hashlib
import json
import os

from common import doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

PHIEN_BAN = 1
LOAI = ("hanh_dong", "dia_diem", "vat", "nguoi", "khai_niem")
_P = """You are a documentary video editor choosing STOCK FOOTAGE (B-roll) for each narration line of a Vietnamese documentary.
Story summary: {tom_tat}

For each line, describe what the viewer should SEE so the picture conveys the MEANING of the line (not necessarily the exact subject): the ACTION happening and the SETTING. If the line is abstract (numbers, ideas), describe a concrete scene that carries the same meaning.
Return ONLY a JSON array, one object per line:
{{"id": <id>, "loai": one of "hanh_dong" (an action/event), "dia_diem" (ONLY when the line DESCRIBES a place itself — its landscape, geography, look; a line that merely MENTIONS a place while telling an event, e.g. "ships brought rats to New York in 1770", is "hanh_dong", NOT "dia_diem"), "vat" (an animal/object is the focus), "nguoi" (people/human activity), "khai_niem" (abstract idea/numbers),
 "canh_en": [2 short English shot descriptions, 6-14 words each, concrete and visual, e.g. "a fishing boat sailing out of a harbor at dawn"],
 "dia_danh_en": English place name with its country if loai is "dia_diem" (e.g. "Kyoto, Japan"), else ""}}

Lines (with the previous line for context):
{muc}"""


def _khoa(c):
    # 13/10: khoá gồm cả CÂU LỆNH — sửa câu lệnh thì mô tả cảnh tự hỏi lại (trước chỉ theo lời câu -> dùng mãi bản cũ)
    return hashlib.md5((c["text"] + "|" + hashlib.md5(_P.encode("utf-8")).hexdigest()[:8]).encode("utf-8")).hexdigest()[:10]


def lam_mo_ta(du_an, lo=10):
    """Điền canh_en/loai/dia_danh_en cho mọi cảnh trong tu_khoa.json còn thiếu. Trả danh sách cảnh đã cập nhật."""
    cache_dir, out = thu_muc_du_an(du_an)
    p_tk = os.path.join(out, "tu_khoa.json")
    canh = doc_json(p_tk, []) or []
    cache = os.path.join(cache_dir, "mo_ta_canh.json")
    da = doc_json(cache, {}) or {}
    ctx = doc_json(os.path.join(cache_dir, "ten.json"), {}) or {}
    truoc = {c["id"]: (canh[i - 1]["text"] if i else "") for i, c in enumerate(canh)}

    def thieu():
        return [c for c in canh if (da.get(str(c["id"])) or {}).get("_k") != _khoa(c)
                or (da.get(str(c["id"])) or {}).get("_v") != PHIEN_BAN]
    can = thieu()
    for vong in range(3):
        if not can:
            break
        co = lo if vong == 0 else max(2, lo // (2 * vong))
        lots = [can[i:i + co] for i in range(0, len(can), co)]
        ps = [_P.format(tom_tat=str(ctx.get("tom_tat", ""))[:1500],
                        muc=json.dumps([{"id": c["id"], "cau_truoc": truoc[c["id"]][:200], "cau": c["text"]} for c in lot],
                                       ensure_ascii=False, indent=0)) for lot in lots]
        log(f"  mô tả khung hình{' (hỏi lại lần ' + str(vong) + ')' if vong else ''}: {len(can)} cảnh, {len(lots)} lô…")

        def xu_ly(i, tra, lots=lots):
            kq = rut_json(tra)
            if not isinstance(kq, list):
                log(f"    ! lô mô tả {lots[i][0]['id']}-{lots[i][-1]['id']}: trả lời không đọc được")
                return
            mp = {}
            for x in kq:
                if isinstance(x, dict):
                    try:
                        mp[int(x.get("id", -1))] = x
                    except (TypeError, ValueError):
                        pass
            for c in lots[i]:
                x = mp.get(c["id"])
                ds = [str(s).strip() for s in ((x or {}).get("canh_en") or []) if str(s).strip()]
                if not ds:
                    continue
                loai = str(x.get("loai", "")).strip()
                da[str(c["id"])] = {"_k": _khoa(c), "_v": PHIEN_BAN, "canh_en": ds[:3],
                                    "loai": loai if loai in LOAI else "vat",
                                    "dia_danh_en": str(x.get("dia_danh_en") or "").strip() if loai == "dia_diem" else ""}
            ghi_json(cache, da)
        hoi_nhieu(ps, timeout=200, on_xong=xu_ly)
        can = thieu()
    for c in can:
        log(f"    ! cảnh {c['id']}: ChatGPT không trả mô tả khung hình")
    for c in canh:
        x = da.get(str(c["id"])) or {}
        c["canh_en"], c["loai"], c["dia_danh_en"] = x.get("canh_en", []), x.get("loai", ""), x.get("dia_danh_en", "")
    ghi_json(p_tk, canh)
    log(f"    mô tả khung hình: {sum(1 for c in canh if c['canh_en'])}/{len(canh)} cảnh; "
        f"địa điểm: {sum(1 for c in canh if c['dia_danh_en'])}")
    return canh
