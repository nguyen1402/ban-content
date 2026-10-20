# -*- coding: utf-8 -*-
"""Giai đoạn 1 — Chia kịch bản theo chủ đề (chu_de.py).

Đầu vào: tu_khoa.json (hoặc danh sách cảnh có id, bat_dau, dai, text).
Gửi Gemini / ChatGPT: cả kịch bản đánh số theo cảnh, kèm số giây từng cảnh.
Trả về danh sách chủ đề:
  - ten: tên ngắn tiếng Việt
  - canh_tu, canh_den: ranh giới cảnh (liền mạch, không chồng lấn, phủ hết mọi cảnh)
  - mo_ta_en: mô tả hình ảnh bằng tiếng Anh
  - tu_khoa_en: 5-6 từ khoá tiếng Anh tìm video trên YouTube — hình ảnh CHUNG (vật + hành động / bối cảnh), không tên riêng
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
    return hashlib.md5(("nd3|" + raw).encode("utf-8")).hexdigest()[:16]   # nd2: chia theo NỘI DUNG (18/10)


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

    return f"""Bạn dựng hình cho video tư liệu: footage thật (video quay ngoài đời) chạy suốt theo lời đọc.
Hãy chia kịch bản dưới đây thành các ĐOẠN NỘI DUNG liền nhau. Mỗi đoạn là một khối lời kể xoay quanh MỘT ĐỐI TƯỢNG NHÌN
THẤY ĐƯỢC; đổi đối tượng chính thì sang đoạn mới. KHÔNG có giới hạn thời lượng: đoạn dài hay ngắn tuỳ nội dung.
{nhac_loi}
KỊCH BẢN (cảnh {canh_dau_id} đến {canh_cuoi_id}, ~{tong_giay:.0f} giây):
{ds_text}

MỖI ĐOẠN có các trường:
- "ten": tên ngắn tiếng Việt; GIỮ NGUYÊN tên riêng (người, con vật có tên như "Curry", "Rice", địa danh) — không dịch.
- "canh_tu", "canh_den": số nguyên — đoạn chạy từ cảnh nào tới cảnh nào. Các đoạn nối tiếp LIỀN MẠCH, không chồng, không
  sót cảnh ({canh_dau_id} -> {canh_cuoi_id}).
- "loai": "ke" nếu PHẦN LỚN câu của đoạn KỂ / TẢ sự vật, sự việc, diễn biến, con vật, nơi chốn cụ thể — kể cả khi đoạn
  mở bằng / xen MỘT câu hỏi, câu "thử tưởng tượng", câu bình luận. "binh_luan" CHỈ khi gần như TOÀN BỘ đoạn là ý kiến,
  câu hỏi, chuyển ý, tóm tắt, kêu gọi đăng ký / bình luận, bài học (không tả sự vật cụ thể nào mới). Đoạn kể về báo chí
  đưa tin, dư luận, quan chức ra quyết định, họp hành, công bố nghiên cứu cũng là "binh_luan" (hình phải lấy từ đối tượng
  của câu chuyện mà các tin / quyết định đó nói tới — không quay báo, giấy tờ, phòng họp).
- "doi_tuong": (bắt buộc với "ke") THỨ NGƯỜI XEM PHẢI THẤY TRÊN HÌNH — con vật / người / nơi chốn / vật thể cụ thể + bối
  cảnh (ví dụ "đàn dê hoang trên sườn đồi đá của đảo nhiệt đới", "hai con dingo trên bãi biển"). CẤM dùng khái niệm
  trừu tượng hay thể loại: tin tức, dư luận, bài học, kết luận, ý kiến, tranh cãi, câu hỏi, chính sách, kế hoạch, sự kiện.
- "bang_chung": (bắt buộc với "ke") 3-12 chữ COPY NGUYÊN VĂN từ lời kể của đoạn cho thấy đối tượng đó.
- "ke_thua_canh": (bắt buộc với "binh_luan") số id MỘT CẢNH thuộc đoạn "ke" mà đoạn bình luận này đang bàn tới (thường là
  đoạn kể ngay trước; câu kêu gọi đăng ký / chuyển ý thì lấy đoạn kể ngay trước). Đoạn bình luận KHÔNG tự đặt đối tượng:
  nó dùng hình của đoạn kể đó.
- "mo_ta_en": (với "ke") một câu TIẾNG ANH tả khung hình của đối tượng (dùng để chấm hình).
- "tu_khoa_en": (với "ke") ĐỦ 5-6 từ khoá (không ít hơn 5) TIẾNG ANH tìm video YouTube về đúng đối tượng, ngắn 2-5 từ: vật / con vật / người +
  hành động hoặc bối cảnh (ví dụ "feral goats on rocky hillside", "dingo walking on beach"). Không tên riêng người, không
  tên sự kiện, không chữ cinematic / b-roll / 4k / footage / animation.
- "tranh": những thứ KHÔNG được hiện (ví dụ "cá mập khi đang nói về cá chép").

Chỉ trả về JSON array hợp lệ, không markdown, không lời dẫn:
[
  {{"ten": "...", "canh_tu": {canh_dau_id}, "canh_den": 0, "loai": "ke", "doi_tuong": "...", "bang_chung": "...",
    "mo_ta_en": "...", "tu_khoa_en": ["...", "..."], "tranh": "..."}},
  {{"ten": "...", "canh_tu": 0, "canh_den": 0, "loai": "binh_luan", "ke_thua_canh": 0}}
]"""


# 18/10: chữ làm YouTube trả video flycam du lịch / quảng cáo thay vì đúng đối tượng — AI có lỡ viết thì gỡ ra
_CHU_CAM = re.compile(r"\b(cinematic|b-?roll|4k|uhd|8k|hdr|footage|stock|mockup|animation|visualization|archive|raw)\b", re.I)


def _bo_chu_cam(q):
    return re.sub(r"\s+", " ", _CHU_CAM.sub(" ", str(q))).strip()


_TRUU_TUONG = re.compile(r"tin tức|dư luận|bài học|kết luận|ý kiến|tranh cãi|câu hỏi|chính sách|kế hoạch|sự kiện|"
                         r"thông tin|vấn đề|nghịch lý|phân tích|bình luận|quan điểm|tổng kết|lời kêu gọi|"
                         # 18/10 đo cho_digo: "quan chức họp bàn và báo chí đưa tin", "tài liệu nghiên cứu trên bàn" lọt lưới
                         r"báo chí|bài báo|tờ báo|quan chức|chính quyền|họp|hội nghị|tài liệu|giấy tờ|văn bản|hồ sơ|"
                         r"bàn làm việc|văn phòng|máy tính|màn hình|biểu đồ|số liệu|dữ liệu|nghiên cứu khoa học", re.I)
_TRUU_TUONG_EN = re.compile(r"\b(newspaper|news|headline|article|document|paper|desk|office|meeting|press conference|"
                            r"official|politician|government|computer|screen|chart|graph|data|report|study)s?\b", re.I)


BINH_LUAN_DAI = 60.0        # đoạn bình luận dài hơn bấy nhiêu giây thừa kế nhiều đoạn kể (luân phiên hình)
_HU = set(("những trong không người được nhưng chúng cũng chính trước thành nhiều khoảng trên dưới quanh giữa cùng "
            "hai ba một các của với và đã đang sẽ là có này đó hình như khi rồi lại vào ra lên xuống bên cạnh nơi "
            "hòn con cái chiếc").split())   # chữ hư / chữ quá chung


def _chuan(t):
    return re.sub(r"[^\w]+", " ", str(t or "").lower()).strip()


def _kiem_noi_dung(sach, canh_dict):
    """18/10 user: 'đoạn bình luận mà AI nói nội dung chính là tin tức thì sai bét' -> lý do lỗi ('' = đạt)."""
    loi = []
    for it in sach:
        if it["loai"] == "binh_luan":
            if it.get("ke_thua_canh") is None:
                loi.append(f"đoạn bình luận '{it['ten']}' thiếu ke_thua_canh")
            continue
        dt = it.get("doi_tuong") or ""
        if not dt:
            loi.append(f"đoạn kể '{it['ten']}' thiếu doi_tuong")
        elif _TRUU_TUONG.search(dt):
            loi.append(f"doi_tuong '{dt}' là khái niệm trừu tượng / giấy tờ / họp hành, phải là thứ của CÂU CHUYỆN nhìn "
                       f"thấy được (con vật, nơi chốn, sự vật) — đoạn chỉ có tin tức / quyết định / nghiên cứu thì là binh_luan")
        elif _TRUU_TUONG_EN.search(it.get("mo_ta_en") or "") or any(_TRUU_TUONG_EN.search(k) for k in it.get("tu_khoa_en") or []):
            loi.append(f"đoạn '{it['ten']}': mo_ta_en / tu_khoa_en tả báo chí, giấy tờ, họp, màn hình — phải là đối tượng của câu chuyện")
        if len(it.get("tu_khoa_en") or []) < 4:
            loi.append(f"đoạn '{it['ten']}' chỉ có {len(it.get('tu_khoa_en') or [])} từ khoá, cần 5-6")
        loi_doan = _chuan(" ".join(str(canh_dict.get(c, {}).get("text") or "") for c in range(it["canh_tu"], it["canh_den"] + 1)))
        bc = _chuan(it.get("bang_chung"))
        chu_bc = bc.split()
        if not bc or (bc not in loi_doan and sum(w in loi_doan.split() for w in chu_bc) < 0.7 * len(chu_bc)):
            loi.append(f"bang_chung '{it.get('bang_chung')}' không có nguyên văn trong lời kể của đoạn '{it['ten']}'")
    return "; ".join(loi[:6])


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
        tk = [x for x in (_bo_chu_cam(x) for x in tk) if x]

        pl = str(it.get("phan_loai") or "broll_tu_nhien").strip()
        can_ai = bool(it.get("can_ai_slow") or pl == "mo_ta_ai_slow")
        mo_ta_ai = str(it.get("mo_ta_ai_slow") or "").strip()

        try:
            ktc = int(it.get("ke_thua_canh")) if it.get("ke_thua_canh") is not None else None
        except (TypeError, ValueError):
            ktc = None
        sach.append({
            "ten": str(it.get("ten") or f"Chủ đề {idx + 1}").strip(),
            "canh_tu": ctu,
            "canh_den": cden,
            "loai": "binh_luan" if str(it.get("loai") or "").strip() == "binh_luan" else "ke",
            "doi_tuong": str(it.get("doi_tuong") or "").strip(),
            "bang_chung": str(it.get("bang_chung") or "").strip(),
            "ke_thua_canh": ktc,
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
            **it,                                            # 18/10: giữ loai / doi_tuong / bang_chung / ke_thua_canh
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
    return _hoi_mot_luot_nd(canh_lot, canh_dau_id, canh_cuoi_id)


def _hoi_mot_luot_cu(canh_lot, canh_dau_id, canh_cuoi_id):
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


def _hoi_mot_luot_nd(canh_lot, canh_dau_id, canh_cuoi_id):
    """Như _hoi_mot_luot_cu nhưng kiểm thêm NỘI DUNG (đối tượng nhìn thấy, bằng chứng nguyên văn, thừa kế) — sai thì hỏi
    lại tối đa 2 lượt kèm lý do; vẫn sai ở vài đoạn thì đoạn đó đổi thành "binh_luan" thừa kế đoạn kể gần nhất."""
    canh_dict = {c["id"]: c for c in canh_lot}
    tong_giay = sum(float(c.get("dai") or 0.0) for c in canh_lot)
    loi_truoc, ds_sach = "", []
    for lan in range(3):
        log(f"  [chu_de] Hỏi AI chia đoạn nội dung cảnh {canh_dau_id} → {canh_cuoi_id}" + (f" (lượt {lan + 1})" if lan else "") + "...")
        parsed = rut_json(hoi_llm(_tao_prompt(canh_lot, canh_dau_id, canh_cuoi_id, tong_giay, loi_truoc=loi_truoc), timeout=300))
        hop_le, ds, ly_do = _kiem_tra_ket_qua(parsed, canh_dau_id, canh_cuoi_id)
        if not hop_le:
            ds = _tu_chuan_hoa_ranh_gioi(ds, canh_dau_id, canh_cuoi_id) if ds else ds
        ly_do = ly_do or _kiem_noi_dung(ds, canh_dict) if ds else (ly_do or "không ra JSON")
        if ds:
            ds_sach = ds
        if not ly_do:
            return ds_sach
        log(f"  [chu_de] ! đoạn nội dung chưa đạt: {ly_do[:200]}")
        loi_truoc = ly_do
    # hết lượt: CHỈ đoạn kể không có đối tượng nhìn thấy được (thiếu / trừu tượng) mới chuyển sang thừa kế; câu trích lệch
    # thì vẫn giữ là đoạn kể (18/10 đo: đổi kiểu cũ làm "dingo thả trên Townshend" mượn hình hai nhà sinh thái học)
    for it in ds_sach:
        dt = it.get("doi_tuong") or ""
        if it["loai"] == "ke" and (not dt or _TRUU_TUONG.search(dt) or _TRUU_TUONG_EN.search(it.get("mo_ta_en") or "")):
            it["loai"], it["ke_thua_canh"] = "binh_luan", None
    return ds_sach


_P_THUA_KE = """Video tư liệu có các ĐOẠN KỂ, mỗi đoạn có một đối tượng hiện trên hình:
{ke}

Các ĐOẠN BÌNH LUẬN dưới đây không có hình riêng: hình của chúng phải lấy từ đoạn kể có ĐỐI TƯỢNG mà lời bình luận ĐANG
BÀN TỚI (con vật / người / sự vật được nhắc hoặc được ám chỉ trong lời — không phải cứ đoạn ngay trước). Ví dụ lời bàn về
viên thuốc độc trong người hai con chó thì chọn đoạn có dingo; lời kêu gọi đăng ký / chuyển ý thì chọn đoạn kể ngay trước.
Đoạn bình luận dài / tổng kết nhắc nhiều đối tượng thì chọn 2-4 đoạn kể, đối tượng nhắc nhiều nhất trước.
{bl}

Chỉ trả JSON: {{"<id đoạn bình luận>": [<id đoạn kể>, ...], ...}}"""


def _hoi_thua_ke(ds, ke, canh_dict):
    """18/10 user (đoạn bình luận mượn sai hình: bàn về dingo mà ra san hô / chim): hỏi AI RIÊNG một câu cho mọi đoạn bình
    luận — đoạn đó đang bàn về đối tượng của đoạn kể nào. Trả {id bình luận: [id đoạn kể]}; lỗi -> {}."""
    bl = [it for it in ds if it["loai"] == "binh_luan"]
    if not bl or not ke:
        return {}
    ds_ke = "\n".join(f"#{k['id']}: {k.get('doi_tuong') or k.get('ten')}" for k in ke)
    ds_bl = "\n\n".join(f"BÌNH LUẬN #{it['id']}: " + " ".join(
        str(canh_dict.get(c, {}).get("text") or "") for c in range(it["canh_tu"], it["canh_den"] + 1))[:1500] for it in bl)
    try:
        j = rut_json(hoi_llm(_P_THUA_KE.format(ke=ds_ke, bl=ds_bl), timeout=240))
    except Exception:                                        # noqa: BLE001
        j = None
    if not isinstance(j, dict):
        log("  [chu_de] ! không hỏi được đoạn bình luận thừa kế đoạn nào -> so chữ")
        return {}
    ra = {}
    for k, v in j.items():
        so = re.findall(r"\d+", str(k))
        if so and isinstance(v, list):
            ra[int(so[-1])] = [int(x) for x in v if str(x).strip().lstrip("#").isdigit() or isinstance(x, int)]
    return ra


def _hoan_tat(ds, canh_dict):
    """Gán id / mốc giờ; đoạn bình luận thừa kế (kho_cd + đối tượng + mô tả + từ khoá) của đoạn kể nó bàn tới."""
    for idx, it in enumerate(ds, 1):
        it["id"] = idx
        it["dai"] = _tinh_thoi_luong_chu_de(it, canh_dict)
        c_dau, c_cuoi = canh_dict.get(it["canh_tu"], {}), canh_dict.get(it["canh_den"], {})
        it["bat_dau"] = round(float(c_dau.get("bat_dau") or 0.0), 2)
        it["ket_thuc"] = round(float(c_cuoi.get("bat_dau") or 0.0) + float(c_cuoi.get("dai") or 0.0), 2)
        it["so_canh"] = it["canh_den"] - it["canh_tu"] + 1
    ke = [it for it in ds if it["loai"] == "ke"]
    if not ke:                                               # không đoạn kể nào (hiếm): đoạn đầu làm đoạn kể
        ds[0]["loai"] = "ke"
        ke = [ds[0]]
    def cap_chu(t):                                          # cặp âm tiết liền nhau (bãi biển, choi choi, con dingo…)
        w = _chuan(t).split()                                # bỏ chữ hư ("trên", "hai con"…) — đo 18/10: làm nhiễu
        return ({a + " " + b for a, b in zip(w, w[1:]) if not (a in _HU or b in _HU)}
                | {x for x in w if len(x) >= 4 and x not in _HU})

    for it in ds:
        if it["loai"] == "ke":
            it["kho_cd"] = it["id"]
            it["kho_ds"] = [it["id"]]
    tra_loi = _hoi_thua_ke(ds, ke, canh_dict)
    for it in ds:
        if it["loai"] == "ke":
            continue
        loi = " ".join(str(canh_dict.get(c, {}).get("text") or "") for c in range(it["canh_tu"], it["canh_den"] + 1))
        cl = cap_chu(loi)
        diem = sorted(((len(cl & cap_chu(k.get("doi_tuong", ""))), -abs(k["id"] - it["id"]), k)   # chỉ ĐỐI TƯỢNG (tên đoạn
                                                                                                 # như "Nghịch lý…" gây nhiễu)
                       for k in ke), key=lambda x: (-x[0], -x[1]))
        nhac = [k for d, _, k in diem if d > 0]                # đoạn kể có đối tượng được NHẮC trong lời bình luận
        ai_chon = next((k for k in ke if it.get("ke_thua_canh") is not None
                        and k["canh_tu"] <= it["ke_thua_canh"] <= k["canh_den"]), None)
        theo_id_ke = {k["id"]: k for k in ke}
        hoi_rieng = [theo_id_ke[i] for i in (tra_loi.get(it["id"]) or []) if i in theo_id_ke]   # GIỮ thứ tự AI xếp
        if hoi_rieng:                                        # câu hỏi RIÊNG cho đoạn bình luận (chính xác nhất)
            # 18/10 user (A): kiểm lại AI bằng SỐ LẦN lời bình luận nhắc tới đối tượng của từng đoạn kể — đoạn KHÔNG được
            # nhắc (vd khu nghỉ dưỡng trong "bài học" chỉ nói dingo, rừng, san hô) bị loại; nhắc nhiều nhất lên đầu
            loi_c = " " + _chuan(loi) + " "
            nhac_so = {k["id"]: sum(loi_c.count(" " + w + " ") for w in cap_chu(k.get("doi_tuong", ""))) for k in ke}
            # GIỮ thứ tự AI; chỉ loại đoạn AI chọn mà lời KHÔNG nhắc tới (khi có đoạn được nhắc), rồi bù đoạn được nhắc nhiều
            # nhất (đo: xếp hoàn toàn theo số lần nhắc bị nhiễu — "sinh thái" kéo về "khu nghỉ dưỡng sinh thái")
            ai_nhac = [k for k in hoi_rieng if nhac_so[k["id"]] > 0]
            khac = sorted((k for k in ke if k not in hoi_rieng and nhac_so[k["id"]] > 0),
                          key=lambda k: (-nhac_so[k["id"]], abs(k["id"] - it["id"])))
            ung = ai_nhac + khac if (ai_nhac or khac) else hoi_rieng
            if it.get("dai", 0) > BINH_LUAN_DAI:              # dài: mỗi ĐỐI TƯỢNG một kho (không 4 kho cùng là dingo)
                gon, da_co = [], []
                for k in ung:
                    w_ = cap_chu(k.get("doi_tuong", ""))
                    if not any(len(w_ & x) >= max(1, min(len(w_), len(x)) // 2) for x in da_co):
                        gon.append(k)
                        da_co.append(w_)
                ung = gon or ung
            cha = ung[0]
            kho_ds = [k["id"] for k in ung][:4 if it.get("dai", 0) > BINH_LUAN_DAI else 1]
            it.update(kho_cd=cha["id"], kho_ds=kho_ds, thua_ke=cha["id"], doi_tuong=cha.get("doi_tuong", ""),
                      mo_ta_en=cha.get("mo_ta_en", ""), tu_khoa_en=list(cha.get("tu_khoa_en") or []), tranh=cha.get("tranh", ""))
            continue
        if nhac:
            cha = ai_chon if ai_chon in nhac else nhac[0]     # AI chọn mà lời có nhắc -> tin AI (trùng chữ dễ nhiễu:
            #                                                   "sinh thái" khớp nhầm "khu nghỉ dưỡng sinh thái")
        else:
            cha = ai_chon or next((k for k in reversed(ke) if k["id"] < it["id"]), None) or next(k for k in ke if k["id"] > it["id"])
        kho_ds = [cha["id"]]
        if it.get("dai", 0) > BINH_LUAN_DAI:                   # dài / tổng kết: thêm các đoạn kể khác được nhắc (tối đa 4)
            kho_ds += [k["id"] for k in nhac if k["id"] != cha["id"]][:3]
        it.update(kho_cd=cha["id"], kho_ds=kho_ds, thua_ke=cha["id"], doi_tuong=cha.get("doi_tuong", ""),
                  mo_ta_en=cha.get("mo_ta_en", ""), tu_khoa_en=list(cha.get("tu_khoa_en") or []), tranh=cha.get("tranh", ""))
    return ds


CHIA_THEO_CHU_THE = True    # 19/10 user: chia đoạn theo CHỦ THỂ của cả video (chu_the.py: một lần hỏi AI + dò tên cục bộ)
#                             thay cho hỏi AI chia đoạn theo nội dung; False = cách cũ


def chia_chu_de(du_an, buoc_lai=False):
    """Hàm chính: Đọc tu_khoa.json của dự án, chia kịch bản thành các chủ đề.

    Kết quả lưu vào ra/<dự án>/chu_de.json.
    Nếu kịch bản không đổi thì nạp lại từ cache.
    """
    if CHIA_THEO_CHU_THE:
        import chu_the
        return chu_the.chia_doan(du_an, hoi_lai=buoc_lai)
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

    # 18/10 user: chia theo NỘI DUNG — không gộp / cắt theo thời lượng; đoạn bình luận thừa kế đoạn kể
    ds_chu_de = _hoan_tat(ds_raw, canh_dict)

    # Lưu kết quả
    ghi_json(duong_chu_de, {
        "_hash": h_hien_tai,
        "so_chu_de": len(ds_chu_de),
        "chu_de": ds_chu_de
    })
    log(f"  [chu_de] Hoàn tất chia {len(ds_chu_de)} chủ đề -> lưu {duong_chu_de}")
    for it in ds_chu_de:
        log(f"    * Đoạn {it['id']} [{it['bat_dau']}s - {it['ket_thuc']}s] cảnh {it['canh_tu']}→{it['canh_den']} "
            f"{'KỂ' if it['loai'] == 'ke' else 'bình luận -> đoạn ' + str(it.get('thua_ke'))}: {it['ten']} | thấy: {it.get('doi_tuong', '')[:60]}")

    return ds_chu_de


def doc_chu_de(du_an):
    """Đọc chu_de.json của dự án nếu đã có, hoặc chia mới nếu chưa có."""
    _, out = thu_muc_du_an(du_an)
    duong = os.path.join(out, "chu_de.json")
    da = doc_json(duong)
    if isinstance(da, dict) and da.get("chu_de") and (da.get("nguon") == "chu_the") == CHIA_THEO_CHU_THE:
        return da["chu_de"]
    return chia_chu_de(du_an)
