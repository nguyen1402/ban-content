# -*- coding: utf-8 -*-
"""Giai đoạn 1 — Chia kịch bản theo chủ đề (chu_de.py).

Đầu vào: tu_khoa.json (hoặc danh sách cảnh có id, bat_dau, dai, text).
Gửi Gemini / ChatGPT: cả kịch bản đánh số theo cảnh, kèm số giây từng cảnh.
Trả về danh sách chủ đề:
  - ten: tên ngắn tiếng Việt
  - canh_tu, canh_den: ranh giới cảnh (liền mạch, không chồng lấn, phủ hết mọi cảnh)
  - mo_ta_en: mô tả hình ảnh bằng tiếng Anh
  - tu_khoa_en: 4-6 từ khoá tiếng Anh tìm video
  - tranh: những thứ không được hiện
Ràng buộc: mỗi chủ đề dài 30s - 2 phút, phủ hết mọi cảnh.
Tự kiểm tra:
  - Thiếu / chồng / sai thứ tự: hỏi lại một lần
  - Chủ đề < 30s: gộp vào chủ đề bên cạnh
  - Chủ đề > 120s: cắt đôi ở ranh giới cảnh
  - Kịch bản > 25.000 ký tự: chia 2-3 lượt, chồng nhau 2 cảnh ở chỗ nối
Lưu kết quả: ra/<dự án>/chu_de.json (kèm hash để dùng lại nếu kịch bản không đổi).
"""
import hashlib
import json
import os
import re

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

MAX_CHARS_LUOT = 25000       # kịch bản trên 25k ký tự thì chia lượt
THOI_LUONG_MIN = 30.0        # chủ đề tối thiểu 30 giây
THOI_LUONG_MAX = 120.0       # chủ đề tối đa 2 phút (120 giây)


def _hash_kich_ban(canh):
    """Hash ngắn gọn biểu diễn nội dung và thời lượng toàn bộ kịch bản."""
    raw = "|".join(f"{c['id']}:{c.get('bat_dau', 0):.2f}:{c.get('dai', 0):.2f}:{str(c.get('text', '')).strip()}"
                  for c in canh)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _danh_sach_canh_text(canh):
    """Biểu diễn danh sách cảnh dưới dạng văn bản có đánh số và số giây."""
    dong = []
    for c in canh:
        cid = c["id"]
        bd = float(c.get("bat_dau") or 0.0)
        dai = float(c.get("dai") or 0.0)
        kt = bd + dai
        txt = str(c.get("text") or "").strip()
        dong.append(f"Cảnh {cid} [{bd:.1f}s - {kt:.1f}s] ({dai:.1f}s): {txt}")
    return "\n".join(dong)


def _tao_prompt(canh_lot, canh_dau_id, canh_cuoi_id, tong_giay, loi_truoc=""):
    """Tạo prompt gửi LLM yêu cầu chia chủ đề."""
    ds_text = _danh_sach_canh_text(canh_lot)
    nhac_loi = ""
    if loi_truoc:
        nhac_loi = f"\nLƯU Ý LỖI Ở LƯỢT TRƯỚC: {loi_truoc}\nHãy sửa lại để đảm bảo không lặp lại lỗi trên!\n"

    return f"""Bạn là một chuyên gia biên kịch và đạo diễn hình ảnh cho video tư liệu đỉnh cao.
Nhiệm vụ của bạn là phân tích toàn bộ kịch bản được đánh số theo cảnh dưới đây thành các CHỦ ĐỀ (mỗi chủ đề là một phân đoạn nội dung liền mạch).
{nhac_loi}
KỊCH BẢN (gồm các cảnh từ {canh_dau_id} đến {canh_cuoi_id}, tổng thời lượng ~{tong_giay:.1f} giây):
{ds_text}

RÀNG BUỘC BẮT BUỘC:
1. PHỦ TOÀN BỘ CÁC CẢNH: Bắt đầu từ cảnh {canh_dau_id} đến cảnh {canh_cuoi_id}. Các chủ đề phải nối tiếp nhau LIỀN MẠCH, KHÔNG CHỒNG LẤN, KHÔNG BỎ SÓT CẢNH NÀO (ví dụ chủ đề 1 từ {canh_dau_id} đến 5, chủ đề 2 từ 6 đến 12...).
2. THỜI LƯỢNG MỖI CHỦ ĐỀ: khoảng 30 giây đến 2 phút (tính theo tổng số giây các cảnh thuộc chủ đề đó).
3. ĐẦU RA LÀ JSON ARRAY, mỗi phần tử có đúng các trường sau:
- "ten": Tên ngắn gọn bằng tiếng Việt mô tả nội dung chủ đề (để người dựng đọc).
- "canh_tu": Số nguyên, id cảnh bắt đầu của chủ đề.
- "canh_den": Số nguyên, id cảnh kết thúc của chủ đề (canh_tu <= canh_den).
- "phan_loai": Phân loại bản chất nội dung của chủ đề này (chọn đúng 1 trong các loại sau):
    * "mo_ta_ai_slow": Đoạn miêu tả diễn biến kịch tính, sự kiện, câu chuyện thực tế (CẦN TẠO CHUỖI ẢNH AI SLOW từng bước nối tiếp).
    * "tu_lieu_lich_su": Đoạn mốc thời gian, tài liệu lịch sử trong quá khứ (cần thẻ mốc thời gian tinh gọn / ảnh tư liệu).
    * "mo_phong_so_lieu": Đoạn số liệu quy mô, so sánh hai mặt, cơ chế (cần Biểu đồ cột Remotion).
    * "dia_danh_ban_do": Đoạn nhắc địa danh, vị trí địa lý, lan rộng (cần Bản đồ Remotion xuất hiện sớm).
    * "broll_tu_nhien": Đoạn phong cảnh, thiên nhiên, đời sống thông thường.
- "can_ai_slow": boolean (true nếu đoạn này có cảnh cần mô tả ảnh AI slow bám theo từng vế lời kể).
- "mo_ta_ai_slow": Ghi chú ngắn tiếng Việt về chuỗi hình ảnh AI slow nối tiếp cần thực hiện (ví dụ: "Cảnh xe bồn chở cá -> Cận cảnh bầy cá săn mồi -> Xe đổ cá xuống hồ"). Nếu không cần thì để "".
- "mo_ta_en": Đoạn mô tả hình ảnh bằng tiếng Anh (visual description) về những gì nên xuất hiện trong chủ đề này (dùng để chấm điểm hình ảnh).
- "tu_khoa_en": Danh sách 4-6 từ khoá tìm kiếm video trên YouTube bằng tiếng Anh, CHUYÊN DÙNG ĐỂ TÌM FOOTAGE B-ROLL / CINEMATIC / TÀI LIỆU SẠCH ĐẸP (ví dụ: ["flaco owl central park b-roll 4k", "eurasian eagle owl flying cinematic", "central park trees raw footage", "owl perched branch close up 4k"]). Tuyệt đối KHÔNG tạo từ khoá dính vlog, review, reaction, podcast hay người ngồi nói chuyện.
- "tranh": Những thứ KHÔNG ĐƯỢC xuất hiện trong hình ảnh của chủ đề này (ví dụ: "cá mập khi đang nói về cá chép; xe hơi hiện đại khi nói về thế kỷ 18").

Chỉ trả về JSON array hợp lệ, không có markdown phụ hay lời dẫn:
[
  {{
    "ten": "...",
    "canh_tu": {canh_dau_id},
    "canh_den": ...,
    "phan_loai": "mo_ta_ai_slow",
    "can_ai_slow": true,
    "mo_ta_ai_slow": "Xe bồn chở cá -> Cận cảnh cá trong bồn -> Xe đổ cá xuống hồ",
    "mo_ta_en": "...",
    "tu_khoa_en": ["...", "...", "...", "..."],
    "tranh": "..."
  }}
]"""


def _kiem_tra_ket_qua(raw_items, canh_dau_id, canh_cuoi_id):
    """Kiểm tra kết quả Gemini trả về có hợp lệ không.

    Trả về (hop_le, ds_sach, ly_do_loi).
    """
    if not isinstance(raw_items, list) or not raw_items:
        return False, [], "Kết quả không phải là danh sách JSON hoặc rỗng"

    sach = []
    for idx, it in enumerate(raw_items):
        if not isinstance(it, dict):
            return False, [], f"Mục thứ {idx + 1} không phải object"
        try:
            ctu = int(it.get("canh_tu"))
            cden = int(it.get("canh_den"))
        except (TypeError, ValueError):
            return False, [], f"Mục thứ {idx + 1} có canh_tu hoặc canh_den không phải số nguyên"

        if ctu > cden:
            return False, [], f"Mục '{it.get('ten')}' có canh_tu ({ctu}) > canh_den ({cden})"

        tk = it.get("tu_khoa_en") or []
        if isinstance(tk, str):
            tk = [s.strip() for s in tk.split(",") if s.strip()]
        elif isinstance(tk, list):
            tk = [str(s).strip() for s in tk if str(s).strip()]
        else:
            tk = []

        pl = str(it.get("phan_loai") or "broll_tu_nhien").strip()
        can_ai = bool(it.get("can_ai_slow") or pl == "mo_ta_ai_slow")
        mo_ta_ai = str(it.get("mo_ta_ai_slow") or "").strip()

        sach.append({
            "ten": str(it.get("ten") or f"Chủ đề {idx + 1}").strip(),
            "canh_tu": ctu,
            "canh_den": cden,
            "phan_loai": pl,
            "can_ai_slow": can_ai,
            "mo_ta_ai_slow": mo_ta_ai,
            "mo_ta_en": str(it.get("mo_ta_en") or "").strip(),
            "tu_khoa_en": tk[:6] if tk else [str(it.get("ten") or "")],
            "tranh": str(it.get("tranh") or "").strip()
        })

    # Kiểm tra tính phủ sóng liên tục
    if sach[0]["canh_tu"] != canh_dau_id:
        return False, sach, f"Chủ đề đầu bắt đầu từ cảnh {sach[0]['canh_tu']} thay vì {canh_dau_id}"
    if sach[-1]["canh_den"] != canh_cuoi_id:
        return False, sach, f"Chủ đề cuối kết thúc ở cảnh {sach[-1]['canh_den']} thay vì {canh_cuoi_id}"

    for i in range(1, len(sach)):
        truoc_den = sach[i - 1]["canh_den"]
        nay_tu = sach[i]["canh_tu"]
        if nay_tu != truoc_den + 1:
            return False, sach, f"Không liền mạch giữa chủ đề {i} (đến cảnh {truoc_den}) và chủ đề {i + 1} (từ cảnh {nay_tu})"

    return True, sach, ""


def _tu_chuan_hoa_ranh_gioi(ds, canh_dau_id, canh_cuoi_id):
    """Khi hỏi lại vẫn còn lệch nhẹ ranh giới, tự sắp xếp và gán lại liên tục."""
    if not ds:
        return [{
            "ten": "Toàn bộ kịch bản",
            "canh_tu": canh_dau_id,
            "canh_den": canh_cuoi_id,
            "phan_loai": "broll_tu_nhien",
            "can_ai_slow": False,
            "mo_ta_ai_slow": "",
            "mo_ta_en": "Documentary b-roll footage matching the narration",
            "tu_khoa_en": ["documentary footage"],
            "tranh": ""
        }]

    ds = sorted(ds, key=lambda x: (x["canh_tu"], x["canh_den"]))
    ket_qua = []
    cur_tu = canh_dau_id

    for i, it in enumerate(ds):
        it_den = max(cur_tu, it["canh_den"])
        if i == len(ds) - 1:
            it_den = canh_cuoi_id
        ket_qua.append({
            "ten": it["ten"],
            "canh_tu": cur_tu,
            "canh_den": it_den,
            "phan_loai": it.get("phan_loai", "broll_tu_nhien"),
            "can_ai_slow": it.get("can_ai_slow", False),
            "mo_ta_ai_slow": it.get("mo_ta_ai_slow", ""),
            "mo_ta_en": it["mo_ta_en"],
            "tu_khoa_en": it["tu_khoa_en"],
            "tranh": it["tranh"]
        })
        cur_tu = it_den + 1
        if cur_tu > canh_cuoi_id:
            break

    if ket_qua and ket_qua[-1]["canh_den"] < canh_cuoi_id:
        ket_qua[-1]["canh_den"] = canh_cuoi_id

    return ket_qua


def _tinh_thoi_luong_chu_de(cd, canh_dict):
    """Tính tổng thời lượng giây và danh sách cảnh của một chủ đề."""
    tong = 0.0
    for cid in range(cd["canh_tu"], cd["canh_den"] + 1):
        if cid in canh_dict:
            tong += float(canh_dict[cid].get("dai") or 0.0)
    return round(tong, 2)


def _gop_va_cat_chu_de(ds, canh_dict, canh_dau_id, canh_cuoi_id):
    """Xử lý quy tắc:

    1. Chủ đề quá ngắn (< 30s): gộp vào chủ đề bên cạnh.
    2. Chủ đề quá dài (> 120s): cắt đôi ở ranh giới cảnh.
    """
    if not ds:
        return ds

    if isinstance(canh_dict, list):
        canh_dict = {c["id"]: c for c in canh_dict}

    # BƯỚC 1: Gộp các chủ đề quá ngắn (< THOI_LUONG_MIN)
    # Lặp lại cho đến khi không còn chủ đề nào < 30s (nếu còn > 1 chủ đề)
    thay_doi = True
    vong = 0
    while thay_doi and len(ds) > 1 and vong < 20:
        vong += 1
        thay_doi = False
        for i in range(len(ds)):
            dur = _tinh_thoi_luong_chu_de(ds[i], canh_dict)
            if dur < THOI_LUONG_MIN:
                thay_doi = True
                # Chọn gộp vào bên trái hay bên phải
                if i == 0:
                    muc_tieu = 1
                elif i == len(ds) - 1:
                    muc_tieu = i - 1
                else:
                    dur_trai = _tinh_thoi_luong_chu_de(ds[i - 1], canh_dict)
                    dur_phai = _tinh_thoi_luong_chu_de(ds[i + 1], canh_dict)
                    muc_tieu = (i - 1) if dur_trai <= dur_phai else (i + 1)

                # Gộp ds[i] vào ds[muc_tieu]
                target = ds[muc_tieu]
                source = ds[i]
                target["canh_tu"] = min(target["canh_tu"], source["canh_tu"])
                target["canh_den"] = max(target["canh_den"], source["canh_den"])
                # Gộp từ khoá (loại trùng lặp, giữ thứ tự)
                merged_tk = list(dict.fromkeys(target.get("tu_khoa_en", []) + source.get("tu_khoa_en", [])))
                target["tu_khoa_en"] = merged_tk[:6]
                if not target["mo_ta_en"] and source["mo_ta_en"]:
                    target["mo_ta_en"] = source["mo_ta_en"]
                ds.pop(i)
                break

    # BƯỚC 2: Cắt các chủ đề quá dài (> THOI_LUONG_MAX)
    # Nếu một chủ đề > 120s và có từ 2 cảnh trở lên: cắt đôi ở ranh giới cảnh
    ket_qua = []
    for cd in ds:
        dur = _tinh_thoi_luong_chu_de(cd, canh_dict)
        so_canh = cd["canh_den"] - cd["canh_tu"] + 1

        if dur > THOI_LUONG_MAX and so_canh >= 2:
            # Tìm điểm cắt sao cho thời lượng 2 nửa cân bằng nhất
            tong_tich_luy = 0.0
            nua = dur / 2.0
            best_split = cd["canh_tu"]
            min_diff = 1e9

            for cid in range(cd["canh_tu"], cd["canh_den"]):
                tong_tich_luy += float(canh_dict.get(cid, {}).get("dai") or 0.0)
                diff = abs(tong_tich_luy - nua)
                if diff < min_diff:
                    min_diff = diff
                    best_split = cid

            # Nửa đầu
            cd1 = {
                "ten": cd["ten"],
                "canh_tu": cd["canh_tu"],
                "canh_den": best_split,
                "mo_ta_en": cd["mo_ta_en"],
                "tu_khoa_en": list(cd.get("tu_khoa_en", [])),
                "tranh": cd.get("tranh", "")
            }
            # Nửa sau
            cd2 = {
                "ten": f"{cd['ten']} (tiếp)",
                "canh_tu": best_split + 1,
                "canh_den": cd["canh_den"],
                "mo_ta_en": cd["mo_ta_en"],
                "tu_khoa_en": list(cd.get("tu_khoa_en", [])),
                "tranh": cd.get("tranh", "")
            }
            ket_qua.append(cd1)
            ket_qua.append(cd2)
        else:
            ket_qua.append(cd)

    # Đảm bảo số thứ tự và id chuẩn xác
    for idx, it in enumerate(ket_qua, 1):
        it["id"] = idx
        it["dai"] = _tinh_thoi_luong_chu_de(it, canh_dict)
        c_dau = canh_dict.get(it["canh_tu"], {})
        c_cuoi = canh_dict.get(it["canh_den"], {})
        it["bat_dau"] = round(float(c_dau.get("bat_dau") or 0.0), 2)
        it["ket_thuc"] = round(float(c_cuoi.get("bat_dau") or 0.0) + float(c_cuoi.get("dai") or 0.0), 2)
        it["so_canh"] = it["canh_den"] - it["canh_tu"] + 1

    return ket_qua


def _hoi_mot_luot(canh_lot, canh_dau_id, canh_cuoi_id):
    """Gửi một lượt kịch bản tới Gemini (fallback ChatGPT nếu lỗi).

    Kiểm tra và hỏi lại một lần nếu kết quả không hợp lệ.
    """
    tong_giay = sum(float(c.get("dai") or 0.0) for c in canh_lot)
    prompt = _tao_prompt(canh_lot, canh_dau_id, canh_cuoi_id, tong_giay)

    log(f"  [chu_de] Hỏi Gemini chia chủ đề cho cảnh {canh_dau_id} → {canh_cuoi_id} (~{tong_giay:.1f}s)...")
    raw_text = hoi_llm(prompt, timeout=240)
    parsed = rut_json(raw_text)

    hop_le, ds_sach, ly_do = _kiem_tra_ket_qua(parsed, canh_dau_id, canh_cuoi_id)
    if not hop_le:
        log(f"  [chu_de] ! Kết quả lượt 1 chưa hợp lệ ({ly_do}) -> hỏi lại 1 lần...")
        prompt_lai = _tao_prompt(canh_lot, canh_dau_id, canh_cuoi_id, tong_giay, loi_truoc=ly_do)
        raw_text_lai = hoi_llm(prompt_lai, timeout=240)
        parsed_lai = rut_json(raw_text_lai)
        hop_le_lai, ds_sach_lai, ly_do_lai = _kiem_tra_ket_qua(parsed_lai, canh_dau_id, canh_cuoi_id)
        if hop_le_lai:
            ds_sach = ds_sach_lai
        else:
            log(f"  [chu_de] ! Hỏi lại vẫn chưa chuẩn ({ly_do_lai}) -> tự căn chỉnh lại ranh giới cảnh")
            ds_sach = _tu_chuan_hoa_ranh_gioi(ds_sach_lai or ds_sach, canh_dau_id, canh_cuoi_id)

    return ds_sach


def chia_chu_de(du_an, buoc_lai=False):
    """Hàm chính: Đọc tu_khoa.json của dự án, chia kịch bản thành các chủ đề.

    Kết quả lưu vào ra/<dự án>/chu_de.json.
    Nếu kịch bản không đổi thì nạp lại từ cache.
    """
    _, out = thu_muc_du_an(du_an)
    duong_tu_khoa = os.path.join(out, "tu_khoa.json")
    canh = doc_json(duong_tu_khoa, []) or []
    if not canh:
        raise ValueError(f"Dự án '{du_an}' chưa có {duong_tu_khoa} — hãy chạy bước kịch bản trước")

    canh_dict = {c["id"]: c for c in canh}
    canh_dau_id = canh[0]["id"]
    canh_cuoi_id = canh[-1]["id"]
    h_hien_tai = _hash_kich_ban(canh)

    duong_chu_de = os.path.join(out, "chu_de.json")
    da_co = doc_json(duong_chu_de)
    if not buoc_lai and isinstance(da_co, dict) and da_co.get("_hash") == h_hien_tai and da_co.get("chu_de"):
        log(f"  [chu_de] Kịch bản không đổi -> dùng lại {len(da_co['chu_de'])} chủ đề từ chu_de.json")
        return da_co["chu_de"]

    tong_ky_tu = sum(len(c.get("text") or "") for c in canh)
    log(f"  [chu_de] Bắt đầu chia chủ đề cho {len(canh)} cảnh ({tong_ky_tu} ký tự, "
        f"{sum(float(c.get('dai') or 0) for c in canh):.1f}s)...")

    # Kịch bản dài trên khoảng 25 nghìn ký tự: chia 2–3 lượt, chồng nhau 2 cảnh ở chỗ nối
    if tong_ky_tu > MAX_CHARS_LUOT and len(canh) > 10:
        so_luot = max(2, int(-(-tong_ky_tu // MAX_CHARS_LUOT)))
        log(f"  [chu_de] Kịch bản dài ({tong_ky_tu} ký tự > {MAX_CHARS_LUOT}) -> chia làm {so_luot} lượt hỏi...")

        # Chia danh sách cảnh theo ký tự, chồng 2 cảnh ở chỗ nối
        chunks = []
        cur_chunk = []
        cur_chars = 0
        target_chars = tong_ky_tu / so_luot

        for i, c in enumerate(canh):
            cur_chunk.append(c)
            cur_chars += len(c.get("text") or "")
            if cur_chars >= target_chars and i < len(canh) - 4:
                # Chồng 2 cảnh sang chunk tiếp theo
                chunks.append(cur_chunk)
                cur_chunk = cur_chunk[-2:]
                cur_chars = sum(len(x.get("text") or "") for x in cur_chunk)
        if cur_chunk:
            if chunks:
                chunks[-1].extend([c for c in cur_chunk if c not in chunks[-1]])
            else:
                chunks.append(cur_chunk)

        # Hỏi từng chunk và ghép lại
        ds_gop = []
        cur_canh_tu = canh_dau_id
        for idx_c, chunk in enumerate(chunks):
            c_dau = chunk[0]["id"]
            c_cuoi = chunk[-1]["id"]
            res = _hoi_mot_luot(chunk, c_dau, c_cuoi)

            # Ghép với các lượt trước: cắt bớt phần chồng nhau
            if idx_c > 0 and ds_gop:
                ranh_gioi_cuoi = ds_gop[-1]["canh_den"]
                res_filtered = []
                for it in res:
                    if it["canh_den"] <= ranh_gioi_cuoi:
                        continue
                    if it["canh_tu"] <= ranh_gioi_cuoi:
                        it["canh_tu"] = ranh_gioi_cuoi + 1
                    res_filtered.append(it)
                res = res_filtered
            ds_gop.extend(res)

        ds_raw = _tu_chuan_hoa_ranh_gioi(ds_gop, canh_dau_id, canh_cuoi_id)
    else:
        ds_raw = _hoi_mot_luot(canh, canh_dau_id, canh_cuoi_id)

    # Gộp chủ đề ngắn (< 30s) và cắt đôi chủ đề dài (> 120s)
    ds_chu_de = _gop_va_cat_chu_de(ds_raw, canh_dict, canh_dau_id, canh_cuoi_id)

    # Lưu kết quả
    ghi_json(duong_chu_de, {
        "_hash": h_hien_tai,
        "so_chu_de": len(ds_chu_de),
        "chu_de": ds_chu_de
    })
    log(f"  [chu_de] Hoàn tất chia {len(ds_chu_de)} chủ đề -> lưu {duong_chu_de}")
    for it in ds_chu_de:
        log(f"    * Chủ đề {it['id']}: [{it['bat_dau']}s - {it['ket_thuc']}s] ({it['dai']}s, cảnh {it['canh_tu']}→{it['canh_den']}) - {it['ten']}")

    return ds_chu_de


def doc_chu_de(du_an):
    """Đọc chu_de.json của dự án nếu đã có, hoặc chia mới nếu chưa có."""
    _, out = thu_muc_du_an(du_an)
    duong = os.path.join(out, "chu_de.json")
    da = doc_json(duong)
    if isinstance(da, dict) and da.get("chu_de"):
        return da["chu_de"]
    return chia_chu_de(du_an)
