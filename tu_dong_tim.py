# -*- coding: utf-8 -*-
"""TỰ ĐỘNG từ đầu tới bản nháp, có NGÂN SÁCH tải video:

  1. tìm YouTube theo từ khoá video của mọi cảnh chưa dựng (từ khoá trùng chỉ tìm một lần);
  2. chấm storyboard của MỌI video tìm được với MỌI cảnh (SigLIP, không tải video) — một video tìm cho cảnh này
     vẫn được tính nếu nó có hình cho cảnh khác;
  3. chọn video THAM LAM theo "độ phủ thêm được / phút tải": mỗi lượt lấy video nâng điểm khớp của nhiều cảnh nhất
     (tính theo độ dài cảnh) trên mỗi phút thời lượng, tới khi chạm ngân sách (mặc định 120 phút, lố tối đa 10%);
     video đã có trong kho tính vào ngân sách;
  4. tải 720p (3 video một lúc) → gợi ý đoạn (goi_y, đoạn trỏ video gốc);
  5. cảnh còn trống/khớp kém: tìm ẢNH Google Images (cửa sổ Chrome hiện; captcha người dùng tự giải), chấm thumbnail,
     tải 2 ảnh tốt nhất rồi gợi ý lại cho riêng các cảnh đó — ảnh không giới hạn số lượng;
  6. tạo bản nháp CapCut (đoạn video trỏ video gốc: kéo mép / chọn lại đoạn ngay trong CapCut).

Cảnh người dùng đã tự dựng giữ nguyên."""
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from common import doc_json, log, thu_muc_du_an

NGAN_SACH_PHUT = 120
LO_TOI_DA = 1.10            # được lố ngân sách 10%
VIDEO_MIN, VIDEO_MAX = 20, 45 * 60     # bỏ video quá ngắn / dài hơn 45 phút (ăn hết ngân sách)
NGUONG_DUNG = 0.12          # điểm storyboard dưới mức này: video không giúp gì cho cảnh
NGUONG_ANH = 0.10           # sau gợi ý: đoạn điểm dưới mức này (hoặc trống) -> tìm ảnh bù
ANH_MOI_CANH = 2
DUNG_YOUTUBE = True         # 12/10 user tắt (logo kênh); 15/10 user BẬT LẠI: tìm thêm trên Google Videos (nhiều cảnh sát
#                             nội dung hơn kho stock), chấp nhận video có bản quyền; tải ≤720p, logo góc -> phóng to giấu
STOCK_MOI_CANH = 4          # 12/10: video stock SẠCH (Pexels/Pixabay) — mỗi cảnh lấy tối đa bấy nhiêu clip MỚI khớp nhất
#                             (14/10: clip đã chọn cho cảnh khác không tính -> kho đa dạng, đỡ lặp hình)
NGUONG_STOCK = 0.12         # điểm ảnh thu nhỏ tối thiểu để tải clip stock
STOCK_TOI_DA = 300           # trần số clip stock mỗi lần chạy (mỗi clip 10-30 s, 5-15 MB); 14/10: 150 -> 300 (đỡ lặp)
TU_STOCK_MOI_NHOM = 3       # 14/10: mỗi nhóm ~1 phút tìm từ khoá video của 3 cảnh dài nhất (trước: 2) + biến thể + ảnh
VE_AI_BU = False            # 16/10 user: bản thô KHÔNG tạo ảnh AI bù (chỗ thiếu: ảnh thật Google, không có thì dùng lại video)
VE_AI_KHI_HET = False       # 20/10 user: KHÔNG vẽ ảnh AI cho chỗ hết đoạn khớp nữa — để trống, người dùng tự chỉnh
ANH_GOOGLE_BU = False       # 20/10 user: cảnh trống cũng KHÔNG lấp ảnh Google (để trống)
_VE_AI_KHI_HET_CU = True        # 19/10 user: chế độ chủ đề — chỗ HẾT footage đúng đối tượng (goi_y ghi thieu_chi_tiet.json)
#                             -> Gemini vẽ ảnh ngang cho đúng chỗ đó (không lặp hình quá luật, không lấy hình lạc đề)
GEMINI_BU_TOI_DA = 200      # 14/10 user: chỗ hết video mới -> Gemini vẽ ảnh ngang (trần mỗi lần chạy; ~17 credit/ảnh)
ANH_MOI_DIA_DANH = 4        # mỗi địa danh: 2 ảnh phong cảnh + 2 ảnh từ trên cao
GIAY_MOI_NHOM = 60.0        # gom cảnh liền nhau thành nhóm ~1 phút voice; mỗi nhóm tìm TU_MOI_NHOM từ khoá
TU_MOI_NHOM = 2
VE_TIM_TOI_DA = 120         # 18/10: tối đa bấy nhiêu từ khoá tìm bổ sung cho các VẾ chưa có clip khớp (thiếu nặng trước)
VE_KQ_MOI_TU = 5            # mỗi từ khoá theo vế lấy bấy nhiêu kết quả (đủ cho đối tượng cụ thể, đỡ chấm storyboard)
VE_THEM_TOI_DA = 60         # tối đa bấy nhiêu video thêm riêng cho vế chưa phủ
KQ_MOI_TU = 6               # 11/10: user thấy quét ~1.500 video cho 166 cảnh là quá nhiều
MODIFIERS_BROLL = ("b-roll", "footage")
THEM_DUOI_BROLL = False     # 19/10 user: "tìm đúng y nguyên từ khoá tôi nhập" — không thêm biến thể "… b-roll / … footage"


def tao_tu_khoa_broll(ds_chu_de):
    """Tạo danh sách từ khoá tìm kiếm video tự nhiên, chính xác cho từng chủ đề:
    - Nếu từ khoá gốc đã dài (>= 4 từ, ví dụ 'fish spawning flooded plains'): GIỮ NGUYÊN để không làm loãng kết quả.
    - Nếu từ khoá ngắn (1-3 từ, ví dụ 'carp fish', 'new york rats'): bổ sung biến thể gắn 'footage' hoặc 'b-roll'.
    - Tuyệt đối không nhồi cờ loại trừ (-vlog...) vì làm YouTube xếp hạng sai lệch sang game/phim truyền hình."""
    kq = []
    da_co = set()

    for idx_cd, cd in enumerate(ds_chu_de):
        cac_tk = cd.get("tu_khoa_en") or []
        for i, q in enumerate(cac_tk):
            q_clean = str(q).strip()
            if not q_clean:
                continue
            q_low = q_clean.lower()
            if q_low in da_co:
                continue
            da_co.add(q_low)

            # Luôn giữ từ khoá gốc
            kq.append(q_clean)

            if not THEM_DUOI_BROLL:                            # 19/10 user: tìm ĐÚNG Y NGUYÊN từ khoá người dùng nhập
                continue
            # Nếu từ ngắn (1-3 từ) và chưa có modifier thì thêm 1 biến thể footage/b-roll
            words = q_clean.split()
            co_mod = any(m in q_low for m in ("b-roll", "b roll", "footage", "cinematic", "documentary"))
            if len(words) <= 3 and not co_mod:
                mod = MODIFIERS_BROLL[i % len(MODIFIERS_BROLL)]
                q_mod = f"{q_clean} {mod}"
                if q_mod.lower() not in da_co:
                    da_co.add(q_mod.lower())
                    kq.append(q_mod)

    return kq



TT = {}
_KHOA = threading.Lock()



def _tt(du_an, **kw):
    with _KHOA:
        TT.setdefault(du_an, {}).update(kw)


def _diem_canh(e, t, Q):
    """Điểm khớp (trung bình trượt 3 khung, lấy max theo thời gian) của một video với mọi cảnh: (số cảnh,)."""
    if len(t) < 1:
        return np.full(Q.shape[0], -1.0)
    s = e @ Q.T                                              # (khung, cảnh)
    k = min(3, len(s))
    if k > 1:
        c = np.cumsum(np.vstack([np.zeros((1, s.shape[1])), s]), axis=0)
        s = (c[k:] - c[:-k]) / k
    return s.max(axis=0)


def chon_video(ung_vien, Q, w, ngan_sach_giay, da_dung_giay=0.0, cur=None):
    """Tham lam. ung_vien: [(id, dai, diem_canh)]. w: trọng số cảnh (giây). Trả [id] theo thứ tự chọn."""
    cur = np.maximum(np.full(Q.shape[0], NGUONG_DUNG), cur if cur is not None else -1)
    con = list(ung_vien)
    chon, dung = [], da_dung_giay
    while con:
        tot, tot_i = 0.0, -1
        for i, (vid, dai, d) in enumerate(con):
            if dung + dai > ngan_sach_giay * LO_TOI_DA:
                continue
            g = float((np.maximum(0, d - cur) * w).sum()) / (dai / 60 + 1.0)
            if g > tot:
                tot, tot_i = g, i
        if tot_i < 0 or tot < 1e-3:
            break
        vid, dai, d = con.pop(tot_i)
        chon.append(vid)
        dung += dai
        cur = np.maximum(cur, d)
        if dung >= ngan_sach_giay:
            break
    return chon, dung, cur


def nhom_canh(can, giay=GIAY_MOI_NHOM):
    """Gom cảnh LIỀN NHAU thành nhóm ~giay giây voice (cảnh kề nhau thường cùng chủ đề)."""
    nhom, cur, dai = [], [], 0.0
    for c in can:
        cur.append(c)
        dai += float(c.get("dai") or 0)
        if dai >= giay:
            nhom.append(cur)
            cur, dai = [], 0.0
    if cur:
        if nhom and dai < giay / 3:
            nhom[-1] += cur
        else:
            nhom.append(cur)
    return nhom


def tu_khoa_nhom(can):
    """Mỗi nhóm: từ khoá video ĐẦU của các cảnh dài nhất (khác nhau), tối đa TU_MOI_NHOM."""
    ra = []
    for g in nhom_canh(can):
        lay = []
        for c in sorted(g, key=lambda x: -float(x.get("dai") or 0)):
            q = ((c.get("video") or [""])[0] or "").strip()
            if q and q.lower() not in {x.lower() for x in lay}:
                lay.append(q)
            if len(lay) >= TU_MOI_NHOM:
                break
        # 12/10: thêm câu HÀNH ĐỘNG (mô tả khung hình) của cảnh dài nhất có mô tả — tìm ra sẵn cảnh tấn công/săn mồi
        for c in sorted(g, key=lambda x: -float(x.get("dai") or 0)):
            q = ((c.get("canh_en") or [""])[0] or "").strip()
            if q:
                lay.append(q)
                break
        ra += lay
    return ra


AN_TOAN_BAN_QUYEN = False   # 22/10 user: TẮT (thử America_an_toan: toa tàu chỉ 50/172 mảnh) -> quay về MỌI NGUỒN.
#                             Bật True = chế độ chủ thể chỉ lấy nguồn ĐƯỢC PHÉP DÙNG — stock miễn phí
#                             (Pexels / Pixabay / Mixkit / Coverr / Wikimedia PD-CC0-CC BY) + YouTube Creative Commons (kiểm
#                             lại từng video) + kênh cơ quan chính phủ Mỹ; bỏ Google Videos; ghi nguồn ra ghi_nguon.txt
STOCK_MOI_CD = 6            # mỗi chủ thể tải tối đa bấy nhiêu clip stock khớp nhất (ảnh thu nhỏ) trước khi tìm YouTube
BAM_GOP = 6                # 22/10 user: chế độ băm cả video — một video nguồn tính góp tối đa bấy nhiêu mảnh khi chọn video
TAI_CUNG_LUC = 10            # 22/10 đo 20-30 video thật: 5 cùng lúc 78 Mbit/s, 10 -> 99, 15 -> 121, 0 lỗi (trước: 5)
TAI_TOI_DA_NGUON = {"pixabay": 2}   # Pixabay trả 429 khi tải dồn -> tối đa 2 clip Pixabay cùng lúc


def _tai_cuon(du_an, viec, ten_buoc):
    """viec: [(nguồn, hàm bắt đầu tải -> id kho)]. Tải CUỐN: luôn giữ TAI_CUNG_LUC clip đang tải, clip nào xong (hoặc
    lỗi) thì clip kế vào thế chỗ ngay; in tiến độ ra console mỗi ~10 clip."""
    import dung_tay
    cho, dang, kids, bao, t0 = list(viec), [], [], 0, time.time()
    tong = len(cho)
    while cho or dang:
        kho = dung_tay.doc_kho(du_an)
        dang = [(n, k) for n, k in dang if kho.get(k, {}).get("trang_thai") not in ("xong", "loi")]
        i = 0
        while i < len(cho) and len(dang) < TAI_CUNG_LUC:
            n, ham = cho[i]
            if sum(1 for n2, _ in dang if n2 == n) >= TAI_TOI_DA_NGUON.get(n, TAI_CUNG_LUC):
                i += 1                                       # nguồn này đủ suất -> lấy clip nguồn khác trước
                continue
            cho.pop(i)
            k = ham()
            kids.append(k)
            dang.append((n, k))
        xong = sum(1 for k in kids if kho.get(k, {}).get("trang_thai") in ("xong", "loi"))
        _tt(du_an, buoc=ten_buoc, xong=xong, tong=tong,
            pt=round((xong + sum(kho.get(k, {}).get("pt", 0) / 100 for _, k in dang)) * 100 / max(1, tong), 1))
        if xong - bao >= 10 or (xong == tong and bao < tong):
            log(f"  tải stock {xong}/{tong} ({(time.time() - t0) / 60:.1f} phút)")
            bao = xong
        time.sleep(1)


def _so_luong_ve():
    """22/10 user: số luồng vẽ ảnh = số tài khoản Gemini cookie dùng được (anh_ve.so_luong_ve)."""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
        import anh_ve
        return anh_ve.so_luong_ve()
    except Exception:                                        # noqa: BLE001
        return 3


def _cho_tai(du_an, kids, ten_buoc):
    import dung_tay
    while True:
        kho = dung_tay.doc_kho(du_an)
        m = [kho.get(k, {}) for k in kids]
        xong = sum(1 for x in m if x.get("trang_thai") in ("xong", "loi"))
        _tt(du_an, buoc=ten_buoc, xong=xong, tong=len(kids),
            pt=round(sum(100 if x.get("trang_thai") in ("xong", "loi") else x.get("pt", 0) for x in m) / max(1, len(kids)), 1))
        if xong == len(kids):
            return
        time.sleep(2)


def chay_theo_chu_de(du_an, ngan_sach_phut=NGAN_SACH_PHUT, ten_nhap=None, chi_chon=False, dung_stock=True):
    """Giai đoạn 2 & 3: Tự động tìm nguồn theo chủ đề, chấm storyboard với mô tả chủ đề,
    tải 1-4 khoảng tốt nhất mỗi video trong ngân sách ~3x độ dài chủ đề, lọc logo/phụ đề gộp,
    và khớp đoạn theo chủ đề."""
    import chu_de
    import dung_tay
    import goi_y
    import nhung_siglip
    import xep_hang
    out = thu_muc_du_an(du_an)[1]
    canh = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — chạy bước Từ khoá trước")

    dung = dung_tay.doc_dung(du_an)
    can = [c for c in canh if not (dung.get(str(c["id"]), {}).get("doan") and not dung[str(c["id"])].get("goi_y"))]
    if not can:
        raise ValueError("mọi cảnh đều đã tự dựng — không còn cảnh nào để tự động")

    t_bd = time.time()

    # 1. Chia kịch bản theo chủ đề (Giai đoạn 1)
    _tt(du_an, buoc="chia_chu_de", xong=0, tong=len(canh))
    ds_chu_de = chu_de.chia_chu_de(du_an)
    _tt(du_an, buoc="chia_chu_de", xong=len(ds_chu_de), tong=len(ds_chu_de))
    if not ds_chu_de:
        raise ValueError("Không chia được chủ đề từ kịch bản")
    # 18/10 user: chia theo NỘI DUNG — chỉ ĐOẠN KỂ tìm tư liệu; đoạn bình luận dùng kho của đoạn kể nó thừa kế (kho_cd)
    ds_tat_ca = ds_chu_de
    ds_chu_de = [cd for cd in ds_tat_ca if cd.get("loai", "ke") != "binh_luan"] or ds_tat_ca

    # 2. Lấy từ khoá từ mỗi chủ đề (tự động gắn modifier B-roll / Cinematic / Loại trừ vlog)
    tu_khoa_ds = tao_tu_khoa_broll(ds_chu_de)

    # 3. Tìm nguồn theo chủ đề (Google Videos + YouTube): ~50-100 lượt tìm
    # 18/10 user: "bỏ giới hạn (120 ứng viên), mục tiêu là tìm ĐỦ khoảng minh hoạ". ĐỦ = mỗi chủ đề có đủ MẢNH ~6 s cho
    # số NHỊP NGHỈ GIỌNG của nó (goi_y băm hình theo chỗ lặng của giọng; mỗi mảnh dùng tối đa 2 lần). Chấm storyboard
    # theo LÔ, dừng khi mọi chủ đề đủ; hết ứng viên mà còn chủ đề thiếu -> tìm thêm (nhiều kết quả hơn) cho chủ đề đó.
    vec_cd = nhung_siglip.nhung_chu([cd["mo_ta_en"] for cd in ds_chu_de])
    # 19/10 user ("tránh dư thừa"): bỏ hỏi AI tả khung hình TỪNG CẢNH (mo_ta_canh) — mô tả theo VẾ (mo_ta_ve) thay nó,
    # cảnh thiếu mô tả vế thì dùng mô tả đoạn
    theo_id = {c["id"]: c for c in canh}
    # 18/10 user (nói "sói" mà hiện chim): chấm theo mô tả TỪNG VẾ (mo_ta_ve.py — vế = đoạn giữa hai chỗ nghỉ giọng);
    # cảnh chưa có mô tả vế thì dùng mô tả cảnh (canh_en), rồi mô tả chủ đề
    try:
        import mo_ta_ve
        if chu_de.CHIA_THEO_CHU_THE:                         # 19/10 user: chế độ chủ thể không hỏi AI từng vế
            ve_tat_ca = {}
        else:
            _tt(du_an, buoc="mo_ta_ve", xong=0, tong=0)
            ve_tat_ca = mo_ta_ve.lam(du_an)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! mô tả theo vế lỗi (dùng mô tả cảnh): {str(e)[:120]}")
        ve_tat_ca = {}
    P, QV_ds = [], []                                        # P[j] = {cd (chỉ số chủ đề), canh, tim}; QV_ds[j] = vector
    for k, cd in enumerate(ds_chu_de):
        for i in range(cd["canh_tu"], cd["canh_den"] + 1):
            ve = [x for x in ve_tat_ca.get(str(i)) or [] if x.get("mo_ta_en")]
            if ve:
                for x, vv in zip(ve, nhung_siglip.nhung_chu([x["mo_ta_en"] for x in ve])):
                    P.append({"cd": k, "canh": i, "tim": x.get("tim_en") or ""})
                    QV_ds.append(vv)
            elif (theo_id.get(i) or {}).get("canh_en"):
                P.append({"cd": k, "canh": i, "tim": ""})
                QV_ds.append(nhung_siglip.vec_mo_ta(theo_id[i]["canh_en"][0], theo_id[i]["canh_en"][1:]))
        if not any(x["cd"] == k for x in P):
            P.append({"cd": k, "canh": cd["canh_tu"], "tim": ""})
            QV_ds.append(np.asarray(vec_cd[k]))
        # 22/10 user: chế độ chủ thể — thêm mô tả hình TỪNG TRẠNG THÁI của chủ thể (storyboard / băm cảnh chấm cả các
        # trạng thái: "toa tàu bị cần cẩu thả xuống biển" khác "toa tàu chạy ở New York")
        tt_ = [x for x in cd.get("trang_thai") or [] if x.get("en")]
        if tt_:
            for x, vv in zip(tt_, nhung_siglip.nhung_chu([x["en"] for x in tt_])):
                P.append({"cd": k, "canh": (x.get("cau") or [cd["canh_tu"]])[0], "tim": x.get("tu_khoa") or ""})
                QV_ds.append(vv)
    QV = np.stack(QV_ds)
    idx_cd = [np.array([j for j, x in enumerate(P) if x["cd"] == k]) for k in range(len(ds_chu_de))]
    Q_cd = [QV[ix] for ix in idx_cd]                         # cắt sát mảnh: chấm khung thật với các vế của chủ đề
    try:
        lang = goi_y._lang(du_an, goi_y.LANG_GIONG) if getattr(goi_y, "NGHI_GIONG_DOC", False) else []   # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        lang = []
    # 18/10 user: Ý CỐT LÕI (quá trình / hành động then chốt) dùng ẢNH AI THAY HẲN video -> lập danh sách (đã lập / sửa
    # trên bảng 🎯 thì dùng lại), VẼ CHẠY NỀN song song lúc tìm + tải footage, và KHÔNG tìm footage cho các đoạn đó
    ve_cl, ai_span = None, []
    try:
        import cot_loi
        if cot_loi.DUNG_BAN_THO:                             # 18/10 user: bản thô KHÔNG dùng ảnh AI (cờ tắt)
            _tt(du_an, buoc="cot_loi", xong=0, tong=0)
            cot_loi.lap(du_an)
            ai_span = cot_loi.khoang_y(du_an)
            ve_cl = None if chi_chon else cot_loi.ve_nen(du_an)   # chỉ chọn (xem trước): không vẽ
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! ý cốt lõi lỗi (bỏ qua, footage lấp hết): {str(e)[:120]}")
    can_manh = {}
    for cd in ds_tat_ca:                                     # đoạn bình luận: nhịp cộng vào đoạn kể nó thừa kế
        so_nhip = 0
        for i in range(cd["canh_tu"], cd["canh_den"] + 1):
            c = theo_id.get(i)
            if not c:
                continue
            c0, c1 = float(c["bat_dau"]), float(c["bat_dau"]) + float(c["dai"])
            moc = [c0] + [c0 + x for x in goi_y.cho_nghi_giong_doc(du_an, c, lang)] + [c1] if lang else                 [c0 + k * (c1 - c0) / max(1, round((c1 - c0) / 2.5)) for k in range(max(1, round((c1 - c0) / 2.5)) + 1)]
            so_nhip += sum(1 for a, b in zip(moc, moc[1:]) if not any(x <= (a + b) / 2 <= y for x, y in ai_span))
        ds_k = cd.get("kho_ds") or [cd.get("kho_cd") or cd["id"]]   # bình luận dài: chia đều cho các đoạn kể thừa kế
        for k_ in ds_k:
            can_manh[k_] = can_manh.get(k_, 0) + so_nhip / len(ds_k)
    can_manh = {k: int(np.ceil(v / goi_y.LUOT_MANH * 1.3)) for k, v in can_manh.items()}   # +30% dự trù mảnh bị bỏ;
    #                                                       19/10: không dùng lại cảnh -> mỗi mảnh 1 lần (cũ: 2)
    for cd in ds_chu_de:
        can_manh.setdefault(cd["id"], 1)
        if cd.get("chi_tim"):                                # 19/10: chủ thể / từ khoá thêm chỉ làm chủ thể phụ của câu
            can_manh[cd["id"]] = max(2, int(cd.get("so_dung") or 1))
    if ai_span:
        log(f"  ý cốt lõi: {len(ai_span)} đoạn ảnh AI ({sum(y - x for x, y in ai_span):.0f}s) — không tìm footage cho các đoạn này")
    log(f"  cần mảnh ~{dung_tay.MANH_GIAY:.0f}s theo nhịp nghỉ giọng: " + ", ".join(f"CĐ{k} {v}" for k, v in can_manh.items()))

    kho = dung_tay.doc_kho(du_an)
    co_san = {m.get("video_goc") or (k[2:] if k.startswith("v_") else k) for k, m in kho.items()
              if m.get("loai") == "video" and m.get("trang_thai") in ("xong", "tach")}
    kenh_bo = doc_json(dung_tay.KENH_BO, {}) or {}
    kq, da_xet = {}, set()
    diem_theo_cd = {cd["id"]: [] for cd in ds_chu_de}

    def tim_yt_an_toan(q, n):
        """22/10 user (an toàn bản quyền): YouTube CHỈ video Creative Commons + video kênh cơ quan chính phủ Mỹ; bỏ
        nguồn rủi ro cao (tin tức, truyền hình, stock bán bản quyền, hãng phim). Giấy phép kiểm lại trước khi tải."""
        r = []
        try:
            r += dung_tay.tim_youtube(q, n, chi_cc=True)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! tìm CC '{q[:40]}': {str(e)[:80]}")
        try:
            r += [v for v in dung_tay.tim_youtube(q, n) if dung_tay.la_kenh_cong(v.get("kenh"))]
        except Exception as e:                               # noqa: BLE001
            log(f"    ! tìm '{q[:40]}': {str(e)[:80]}")
        return [v for v in r if not dung_tay.bi_chan(v)]

    def tim_mot_tu(q, n):
        if AN_TOAN_BAN_QUYEN:
            return tim_yt_an_toan(q, n)
        r = []
        try:
            import anh_google
            r += anh_google.google_video(q, n)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! Google Videos '{q[:40]}': {str(e)[:80]}")
        try:
            r += dung_tay.tim_youtube(q, n)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! tìm '{q[:40]}': {str(e)[:80]}")
        return r

    def uoc_manh(khoang):                                    # ước số mảnh 6 s giữ được (đo 18/10: ~60% khoảng thô khớp)
        return sum(max(1, int((kt - bd) * 0.6 // dung_tay.MANH_GIAY)) for bd, kt, _ in khoang)

    def thieu():
        return [cd for cd in ds_chu_de if sum(uoc_manh(x[6]) for x in diem_theo_cd[cd["id"]]) < can_manh[cd["id"]]]

    def sb(v):
        try:
            t, e, tong = xep_hang.storyboard(v["id"])
            import loc_minh_hoa
            if len(t) and (loc_minh_hoa.diem_hoat_hinh(e) > loc_minh_hoa.NGUONG_HOAT_HINH).mean() > loc_minh_hoa.TI_LE_BO_VIDEO:
                return v, None
            if len(e) and loc_minh_hoa.la_game(np.asarray(e)):   # 18/10: cảnh trò chơi điện tử -> bỏ cả video
                return v, None
            if not len(e):
                return v, None
            S_all = np.asarray(e) @ QV.T                     # (khung, vế)
            s_cd = [S_all[:, ix].max(1) for ix in idx_cd]
            scores = [float(x.max()) for x in s_cd]
            k_best = int(np.argmax(scores))
            khoang = dung_tay.khoang_khop(t, s_cd[k_best], tong) if scores[k_best] >= NGUONG_DUNG else []
            if float(tong or 0) > 900 and len(khoang) < 2:   # video > 15 phút chỉ 1 chỗ khớp: tải cả trăm MB cho
                khoang = []                                  # vài giây -> bỏ
            return v, ((scores[k_best], k_best, t, e, tong, khoang, S_all.max(0)) if khoang else None)
        except Exception as ex:                              # noqa: BLE001
            log(f"    ! storyboard {v['id']}: {str(ex)[:80]}")
            return v, None

    def tim_va_cham(ds_tu, n, vong):
        _tt(du_an, buoc="tim_chu_de", xong=0, tong=len(ds_tu))
        theo_tu = []
        with ThreadPoolExecutor(4) as ex:
            for k, r in enumerate(ex.map(lambda q: tim_mot_tu(q, n), ds_tu)):
                theo_tu.append(r)
                _tt(du_an, buoc="tim_chu_de", xong=k + 1, tong=len(ds_tu))
        ung = []                                             # xen kẽ theo thứ hạng: mọi từ khoá đều sớm có ứng viên
        for hang in range(max((len(r) for r in theo_tu), default=0)):
            for r in theo_tu:
                if hang < len(r):
                    v = r[hang]
                    if (v["id"] not in da_xet and v["id"] not in co_san and VIDEO_MIN <= (v.get("dai") or 0) <= VIDEO_MAX
                            and (v.get("kenh") or "") not in kenh_bo):
                        da_xet.add(v["id"])
                        kq.setdefault(v["id"], v)
                        ung.append(v)
        log(f"  vòng {vong}: {len(ds_tu)} từ khoá -> {len(ung)} ứng viên mới; chấm storyboard theo lô, dừng khi đủ")
        # 18/10 đo cho_digo: chủ đề trừu tượng (kết luận, dư luận…) không bao giờ đủ -> chấm hết 745 video mất 22 phút.
        # 3 lô liền (90 video) không thêm mảnh nào cho các chủ đề còn thiếu -> dừng
        truoc, khong_tien = -1, 0
        for i0 in range(0, len(ung), 30):
            with ThreadPoolExecutor(6) as ex:
                for v, res in ex.map(sb, ung[i0:i0 + 30]):
                    if res is not None:
                        cd_id = ds_chu_de[res[1]]["id"]
                        v["chu_de_id"], v["diem_cd"] = cd_id, res[0]
                        diem_theo_cd[cd_id].append((v, *res))
            xong = min(len(ung), i0 + 30)
            _tt(du_an, buoc="storyboard", xong=xong, tong=len(ung))
            con = thieu()
            log(f"  chấm storyboard {xong}/{len(ung)}: còn {len(con)} chủ đề chưa đủ mảnh")
            if not con:
                break
            co = sum(min(can_manh[c["id"]], sum(uoc_manh(x[6]) for x in diem_theo_cd[c["id"]])) for c in ds_chu_de)
            khong_tien = khong_tien + 1 if co <= truoc else 0
            truoc = max(truoc, co)
            if khong_tien >= 3:
                log(f"  90 video liền không thêm mảnh cho {len(con)} chủ đề còn thiếu -> dừng chấm")
                break

    # 3a. 22/10 user (an toàn bản quyền): STOCK MIỄN PHÍ TRƯỚC (Pexels / Pixabay / Mixkit / Coverr / Wikimedia PD-CC0-CC BY)
    #     theo từ khoá các trạng thái chủ thể -> chấm ảnh thu nhỏ với từng chủ thể, tải mỗi chủ thể <= STOCK_MOI_CD clip
    #     khớp nhất, BĂM theo cảnh như video YouTube; số mảnh stock được trừ vào số mảnh còn phải tìm trên YouTube
    if AN_TOAN_BAN_QUYEN and getattr(dung_tay, "BAM_CA_VIDEO", False) and not chi_chon:
        try:
            import kho_video_free
            tu_s = list(dict.fromkeys(q for cd in ds_chu_de for q in (cd.get("tu_khoa_en") or [])[:5] if q))
            _tt(du_an, buoc="tim_stock", xong=0, tong=len(tu_s))
            theo_tu = kho_video_free.tim_nhieu(tu_s, bao=lambda x, n: _tt(du_an, buoc="tim_stock", xong=x, tong=n)) \
                if tu_s else {}
            ds_s = list({x["id"]: x for v in theo_tu.values() for x in v if x.get("file") and x.get("thumb")}.values())
            co_s, E_s = xep_hang.nhung_url([x["thumb"] for x in ds_s]) if ds_s else ([], None)
            chon_s = {}                                      # id clip -> (clip, id chủ thể)
            for k_, cd in enumerate(ds_chu_de):
                if not len(co_s) or not len(idx_cd[k_]):
                    continue
                S_ = (E_s @ QV[idx_cd[k_]].T).max(1)
                for i in np.argsort(-S_)[:STOCK_MOI_CD]:
                    x = ds_s[co_s[int(i)]]
                    if S_[i] >= NGUONG_DUNG and x["id"] not in chon_s:
                        chon_s[x["id"]] = (x, cd["id"])
            log(f"  stock miễn phí: {len(tu_s)} từ khoá -> {len(ds_s)} clip, chọn tải {len(chon_s)}")

            def gn(x):
                return x.get("ghi_nguon") or (f"{x.get('ten', '')} — {x.get('nguon', '')} (giấy phép {x.get('nguon', '')}: "
                                              f"dùng miễn phí) — {x.get('trang') or x.get('file', '')}")
            if chon_s:
                _tai_cuon(du_an, [(x["nguon"], (lambda x=x: dung_tay.tai_file(du_an, x["id"], x["file"], x.get("ten", ""),
                                                                             x["nguon"], gn(x))))
                                  for x, _ in chon_s.values()], "tai_stock")
                kho_s = dung_tay.doc_kho(du_an)
                viec_s = [(kid_, cd_id, x) for kid_, (x, cd_id) in chon_s.items()
                          if kho_s.get(kid_, {}).get("trang_thai") == "xong"]

                def bam_stock(v_):
                    kid_, cd_id, x = v_
                    f_ = kho_s[kid_]["file"]
                    g_, n_ = dung_tay.bam_theo_canh(du_an, kid_, f_, QV, cd_id, {
                        "tieu_de": x.get("ten", ""), "kenh": x.get("nguon", ""), "ghi_nguon": gn(x),
                        "giay_phep": f"stock miễn phí ({x.get('nguon', '')})", "nguon_kho": x.get("nguon", "")})
                    dung_tay._cap_nhat_kho(du_an, kid_, trang_thai="tach", so_manh=n_)   # noqa: SLF001  clip gốc -> mảnh
                    return cd_id, n_
                with ThreadPoolExecutor(4) as ex:
                    da_bam = list(ex.map(bam_stock, viec_s))
                for cd_id, n_ in da_bam:                     # mảnh stock trừ vào số mảnh còn phải tìm trên YouTube
                    can_manh[cd_id] = max(1, can_manh.get(cd_id, 1) - n_)
                log(f"  stock miễn phí: {len(viec_s)} clip -> {sum(n for _, n in da_bam)} mảnh; còn cần trên YouTube: "
                    + ", ".join(f"CĐ{k} {v}" for k, v in can_manh.items()))
        except Exception as e:                               # noqa: BLE001
            log(f"    ! stock miễn phí lỗi (bỏ qua, chỉ dùng YouTube an toàn): {str(e)[:150]}")

    tim_va_cham(tu_khoa_ds, KQ_MOI_TU, 1)
    if thieu():                                              # vòng 2: chủ đề còn thiếu -> nhiều kết quả hơn mỗi từ khoá
        tim_va_cham(tao_tu_khoa_broll(thieu()), 30, 2)
    for cd in thieu():
        co = sum(uoc_manh(x[6]) for x in diem_theo_cd[cd["id"]])
        log(f"  ! CĐ {cd['id']} '{cd.get('ten', '')[:40]}' chỉ tìm được ~{co}/{can_manh[cd['id']]} mảnh — khớp đoạn sẽ dùng lại / lấy chủ đề bên cạnh")

    # 4b. 18/10 user: VẾ chưa có clip nào khớp (ví dụ con vật chỉ được nhắc một lần — "sói", "hải ly": từ khoá chủ đề
    #     không có) -> tìm bổ sung bằng từ khoá RIÊNG của vế (mo_ta_ve.tim_en), chỉ YouTube
    def tot_nhat(lst):
        b = np.full(len(P), -1.0)
        for x in lst:
            b = np.maximum(b, x[7])
        return b
    tat_ca = [x for lst in diem_theo_cd.values() for x in lst]
    b_ = tot_nhat(tat_ca)
    # thiếu nặng nhất trước (18/10 đo cho_digo: 99 vế thiếu, cắt 80 từ khoá đầu theo thứ tự kịch bản -> mất vế "sói",
    # "hải ly" ở cuối video)
    ve_thieu = sorted((j for j in range(len(P)) if b_[j] < NGUONG_DUNG and P[j]["tim"]), key=lambda j: b_[j])
    tu_ve = list(dict.fromkeys(P[j]["tim"] for j in ve_thieu))[:VE_TIM_TOI_DA]
    if tu_ve:
        log(f"  {len(ve_thieu)}/{len(P)} vế chưa có clip khớp -> tìm bổ sung {len(tu_ve)} từ khoá theo vế")
        _tt(du_an, buoc="tim_ve", xong=0, tong=len(tu_ve))
        with ThreadPoolExecutor(4) as ex:
            kq_ve = list(ex.map(lambda q: (tim_yt_an_toan(q, VE_KQ_MOI_TU) if AN_TOAN_BAN_QUYEN
                                           else dung_tay.tim_youtube(q, VE_KQ_MOI_TU)), tu_ve))
        ung_ve = []
        for r in kq_ve:
            for v in r or []:
                if (v["id"] not in da_xet and v["id"] not in co_san and VIDEO_MIN <= (v.get("dai") or 0) <= VIDEO_MAX
                        and (v.get("kenh") or "") not in kenh_bo):
                    da_xet.add(v["id"])
                    kq.setdefault(v["id"], v)
                    ung_ve.append(v)
        with ThreadPoolExecutor(6) as ex:
            for k_, (v, res) in enumerate(ex.map(sb, ung_ve)):
                _tt(du_an, buoc="storyboard", xong=k_ + 1, tong=len(ung_ve))
                if res is not None:
                    cd_id = ds_chu_de[res[1]]["id"]
                    v["chu_de_id"], v["diem_cd"] = cd_id, res[0]
                    diem_theo_cd[cd_id].append((v, *res))
        b2 = tot_nhat([x for lst in diem_theo_cd.values() for x in lst])
        log(f"  tìm theo vế: {len(ung_ve)} video mới -> còn {sum(1 for j in ve_thieu if b2[j] < NGUONG_DUNG)}/{len(ve_thieu)} vế chưa có clip khớp")

    # 5. Chọn video mỗi chủ đề (điểm cao trước) tới khi ĐỦ số mảnh ước tính
    video_duoc_chon = []
    tong_giay_chon = 0.0
    for cd in ds_chu_de:
        cd_id = cd["id"]
        tich_luy = 0
        # 18/10: ưu tiên video <= 10 phút; video dài chỉ lên trước khi có >= 3 chỗ khớp (tải cả trăm MB cho vài giây)
        for v, sc, k_best, t, e, tong, khoang, _mp in sorted(
                diem_theo_cd[cd_id], key=lambda x: (1 if float(x[5] or 0) > 600 and len(x[6]) < 3 else 0, -x[1])):
            if tich_luy >= can_manh[cd_id]:
                break
            video_duoc_chon.append((v, k_best, t, e, tong, khoang))
            # 22/10 user: băm cả video -> mỗi video tính góp tối đa BAM_GOP mảnh -> chọn NHIỀU video nguồn hơn (đa dạng)
            tich_luy += min(uoc_manh(khoang), BAM_GOP) if getattr(dung_tay, "BAM_CA_VIDEO", False) else uoc_manh(khoang)
            tong_giay_chon += sum(kt - bd for bd, kt, _ in khoang)

    # 5b. Vế mà các video đã chọn chưa phủ (điểm < NGUONG_DUNG) nhưng có video khác khớp -> thêm video khớp nhất của
    #     vế đó, cắt đúng khoảng khớp VẾ, gán chủ đề của vế (goi_y lấy trong kho chủ đề của cảnh)
    da_chon = {v["id"] for v, *_ in video_duoc_chon}
    phu = np.full(len(P), -1.0)
    for x in (x for lst in diem_theo_cd.values() for x in lst if x[0]["id"] in da_chon):
        phu = np.maximum(phu, x[7])
    them = 0
    tat_ca = [x for lst in diem_theo_cd.values() for x in lst]
    for j in sorted(range(len(P)), key=lambda j: phu[j]):     # vế chưa phủ nặng nhất trước
        if phu[j] >= NGUONG_DUNG or them >= VE_THEM_TOI_DA:
            continue
        ung_j = sorted((x for x in tat_ca if x[0]["id"] not in da_chon and x[7][j] >= NGUONG_DUNG), key=lambda x: -x[7][j])
        if not ung_j:
            continue
        v, sc, k_best, t, e, tong, khoang, mp = ung_j[0]
        kh_j = dung_tay.khoang_khop(t, np.asarray(e) @ QV[j], tong, toi_da=2)
        if not kh_j:
            continue
        video_duoc_chon.append((v, P[j]["cd"], t, e, tong, kh_j))
        da_chon.add(v["id"])
        phu = np.maximum(phu, mp)
        tong_giay_chon += sum(kt - bd for bd, kt, _ in kh_j)
        them += 1
    if them:
        log(f"  thêm {them} video cho các vế chưa có hình (sói, hải ly… — đối tượng chỉ nhắc một lần)")

    log(f"  chọn theo chủ đề: {len(video_duoc_chon)} video nguồn cho {len(ds_chu_de)} chủ đề")
    _tt(du_an, chon=len(video_duoc_chon), phut=round(tong_giay_chon / 60, 1), so_canh=len(can))
    if chi_chon:
        return {"chon": [(v["id"], v.get("tieu_de", ""), v.get("dai")) for v, _, _, _, _, _ in video_duoc_chon],
                "phut": round(tong_giay_chon / 60, 1), "so_canh": len(can)}

    giay_phep = {}                                           # id YouTube -> giấy phép đã kiểm (ghi nguồn)

    def loc_giay_phep(chon):
        """22/10 user (an toàn bản quyền): đọc GIẤY PHÉP THẬT từng video đã chọn (song song, cache) — giữ Creative Commons
        thật / kênh chính phủ Mỹ, bỏ phần còn lại (bộ lọc CC lúc tìm có thể sót; người đăng lại hay gắn CC bừa)."""
        if not AN_TOAN_BAN_QUYEN or not chon:
            return chon
        with ThreadPoolExecutor(8) as ex:
            kq_gp = list(ex.map(lambda x: dung_tay.nguon_an_toan(x[0]["id"], x[0].get("kenh")), chon))
        giu = []
        for x, (ok, gp) in zip(chon, kq_gp):
            if ok:
                giay_phep[x[0]["id"]] = gp
                giu.append(x)
        log(f"  kiểm giấy phép: giữ {len(giu)}/{len(chon)} video (Creative Commons thật / kênh chính phủ Mỹ)")
        return giu

    def ds_tai(chon):
        return [{"vid": v["id"], "bd": bd, "kt": kt, "tieu_de": v.get("tieu_de", ""), "kenh": v.get("kenh", ""),
                 "chu_de_id": ds_chu_de[k_best]["id"],
                 "giay_phep": giay_phep.get(v["id"], ""),
                 "ghi_nguon": (f"{v.get('tieu_de', '')} — {v.get('kenh', '')} — {giay_phep[v['id']]} — "
                               f"https://youtu.be/{v['id']}" if v["id"] in giay_phep else "")}
                for v, k_best, t, e, tong, khoang in chon for bd, kt, _ in khoang]

    id_cd = [c["id"] for c in ds_chu_de]
    tk_cat = {"giu": 0.0, "manh": 0, "khoang": 0}
    khoa_cat = threading.Lock()

    def cat_ngay(vid, kids):
        """18/10: cắt sát NGAY khi một video tải xong (chạy chồng lên lúc video khác còn tải)."""
        kho_ = dung_tay.doc_kho(du_an)
        for k in kids:
            m = kho_.get(k) or {}
            if m.get("trang_thai") != "xong" or m.get("cat_sat") or m.get("chu_de") not in id_cd:
                continue
            g_, m_ = dung_tay.cat_sat_khop(du_an, k, Q_cd[id_cd.index(m["chu_de"])])
            with khoa_cat:
                tk_cat["giu"] += g_
                tk_cat["manh"] += m_
                tk_cat["khoang"] += 1

    bam_ca = None
    if getattr(dung_tay, "BAM_CA_VIDEO", False):            # 22/10 user: băm CẢ video theo cảnh quay, chấm với mọi chủ thể
        def bam_ca(vid, f, ds_it):
            return dung_tay.bam_theo_canh(du_an, vid, f, QV, ds_it[0].get("chu_de_id"), ds_it[0])

    def cat_sat(chon):
        """18/10: chấm KHUNG THẬT từng khoảng vừa tải với mô tả các cảnh của chủ đề -> cắt sát đoạn khớp."""
        kho_ = dung_tay.doc_kho(du_an)
        viec = [(k, Q_cd[[c["id"] for c in ds_chu_de].index(m["chu_de"])]) for k, m in kho_.items()
                if m.get("video_goc") in {v["id"] for v, *_ in chon} and m.get("trang_thai") == "xong"
                and not m.get("cat_sat") and m.get("chu_de") in [c["id"] for c in ds_chu_de]]
        giu, so_manh = 0.0, 0
        for n_, (k, Q) in enumerate(viec):
            _tt(du_an, buoc="cat_sat", xong=n_, tong=len(viec))
            try:
                g_, m_ = dung_tay.cat_sat_khop(du_an, k, Q)
                giu, so_manh = giu + g_, so_manh + m_
            except Exception as e:                           # noqa: BLE001
                log(f"    ! cắt sát {k}: {str(e)[:100]}")
        bo = sum(1 for k, _ in viec if dung_tay.doc_kho(du_an).get(k, {}).get("trang_thai") == "loi")
        log(f"  cắt sát chỗ khớp: {len(viec)} khoảng -> {so_manh} mảnh ~{dung_tay.MANH_GIAY:.0f}s, {giu / 60:.1f} phút "
            f"(bỏ {bo} khoảng: không khớp / có phụ đề)")

    # 6. Tải các KHOẢNG KHỚP (tải cả video 720p rồi cắt — 18/10 đo: --download-sections 20 s mất 128 s, cả video
    #    230 s chỉ 6 s), rồi cắt sát theo khung thật
    video_duoc_chon = loc_giay_phep(video_duoc_chon)
    ds_khoang_tai = ds_tai(video_duoc_chon)
    log(f"  tải từng khoảng: {len(ds_khoang_tai)} khoảng khớp từ {len(video_duoc_chon)} video được chọn ({TAI_CUNG_LUC} video cùng lúc, "
        f"{'băm cả video theo cảnh quay' if bam_ca else 'cắt sát ngay'})...")
    _tt(du_an, buoc="tai_khoang", xong=0, tong=len(ds_khoang_tai))
    dung_tay.tai_khoang_cuon(du_an, ds_khoang_tai, ten_buoc="tai_khoang", max_cung_luc=TAI_CUNG_LUC,
                             sau_moi_video=cat_ngay, chi_hinh=True, bam_ca=bam_ca,
                             on_tien_do=lambda x, n: _tt(du_an, buoc="tai_khoang", xong=x, tong=n,
                                                         pt=round(x * 100 / max(1, n), 1)))
    log(f"  cắt sát ngay sau tải: {tk_cat['khoang']} khoảng -> {tk_cat['manh']} mảnh ~{dung_tay.MANH_GIAY:.0f}s, "
        f"{tk_cat['giu'] / 60:.1f} phút")
    cat_sat(video_duoc_chon)                                 # khoảng nào còn sót (lỗi giữa chừng) thì cắt nốt

    # 6b. Chủ đề còn ít hình (tải lỗi / cắt sát bỏ nhiều) -> tải thêm ứng viên kế tiếp
    kho_hien = dung_tay.doc_kho(du_an)
    da_tai_vids = {v["id"] for v, *_ in video_duoc_chon}
    du_phong = []
    for k_cd, cd in enumerate(ds_chu_de):
        cd_id = cd["id"]
        so_manh = sum(1 for m in kho_hien.values()
                      if m.get("loai") == "video" and m.get("chu_de") == cd_id and m.get("trang_thai") == "xong")
        if so_manh < can_manh[cd_id] / 1.3:
            ung_con = [x for x in sorted(diem_theo_cd.get(cd_id, []), key=lambda x: -x[1]) if x[0]["id"] not in da_tai_vids]
            for v_dp, sc, k_best, t, e, tong, khoang, _mp in ung_con[:3]:
                da_tai_vids.add(v_dp["id"])
                du_phong.append((v_dp, k_best, t, e, tong, khoang))
    du_phong = loc_giay_phep(du_phong)
    if du_phong:
        ds_du_phong = ds_tai(du_phong)
        log(f"  tải dự phòng: {len(ds_du_phong)} khoảng bù cho các chủ đề thiếu footage...")
        dung_tay.tai_khoang_cuon(du_an, ds_du_phong, ten_buoc="tai_du_phong", max_cung_luc=TAI_CUNG_LUC,
                                 sau_moi_video=cat_ngay, chi_hinh=True, bam_ca=bam_ca,
                                 on_tien_do=lambda x, n: _tt(du_an, buoc="tai_khoang", xong=x, tong=n,
                                                             pt=round(x * 100 / max(1, n), 1)))
        cat_sat(du_phong)

    # 7. Giai đoạn 4: Lọc logo và phụ đề sau khi tải
    # 18/10 user: chế độ chủ đề KHÔNG dò logo / phụ đề nữa (tự zoom bỏ trong CapCut) — đo: dò logo 0,4 s/clip

    # 8. Giai đoạn 5: Lấp hình theo chủ đề
    if ve_cl is not None and ve_cl.is_alive():                # ảnh cốt lõi phải xong trước khi khớp đoạn
        log("  chờ vẽ xong ảnh cốt lõi…")
        while ve_cl.is_alive():
            t_ = cot_loi.TT.get(du_an, {})
            _tt(du_an, buoc="ve_cot_loi", xong=t_.get("xong", 0), tong=t_.get("tong", 0))
            ve_cl.join(2)

    _tt(du_an, buoc="goi_y", xong=0, tong=0)
    if any(m.get("trang_thai") == "xong" for m in dung_tay.doc_kho(du_an).values()):
        goi_y.goi_y(du_an)

    # 9. Cảnh trống -> ảnh Google bù (Ảnh thật, không dùng ảnh AI vẽ)
    dung = dung_tay.doc_dung(du_an)
    yeu = []
    for c in can:
        kh = dung.get(str(c["id"]), {})
        doan = kh.get("doan") or []
        phu_giay = sum(d["dai"] for d in doan)
        if not doan or phu_giay < float(c["dai"]) - 0.5:
            yeu.append(c)
    loi_anh = None
    if yeu and not ANH_GOOGLE_BU:
        log(f"  {len(yeu)} cảnh còn chỗ trống (không có đoạn khớp) — để trống cho người dùng tự chỉnh")
        yeu = []
    if yeu:
        for k, c in enumerate(yeu):
            _tt(du_an, buoc="anh", xong=k, tong=len(yeu))
            try:
                _anh_google_canh(du_an, c, ANH_MOI_CANH)
            except ValueError as e:
                loi_anh = str(e)
                log(f"    ! ảnh bù dừng: {loi_anh[:120]}")
                break
        _tt(du_an, buoc="goi_y", xong=0, tong=0)
        dung = dung_tay.doc_dung(du_an)
        ids = [c["id"] for c in yeu if not (dung.get(str(c["id"]), {}).get("doan") and not dung[str(c["id"])].get("goi_y"))]
        try:
            goi_y.goi_y(du_an, ids=ids)
        except ValueError:
            pass

    # 9b. 19/10 user: "hết hình thì tạo ảnh AI" — mỗi chỗ goi_y không còn footage đúng đối tượng (mảnh đã dùng 2 lần /
    #     không cách được 15 s) -> Gemini vẽ một ảnh ngang (đối tượng chính của đoạn + mô tả vế đó), gắn riêng cho cảnh,
    #     rồi gợi ý lại các cảnh ấy (ảnh vẽ riêng được ưu tiên đúng ở chỗ hết hình)
    if VE_AI_KHI_HET:
        _ve_cho_het_hinh(du_an, can)

    # 10. Tạo bản nháp CapCut
    nhap = None
    if ten_nhap:
        from common import thu_muc_nhap_capcut
        dd = thu_muc_nhap_capcut()
        if not dd:
            raise ValueError("không dò được thư mục CapCut Drafts")
        _tt(du_an, buoc="nhap", xong=0, tong=0)
        nhap = {"ten": ten_nhap, "so": dung_tay.tao_nhap(du_an, ten_nhap, dd)}

    # 10b. 22/10 user (an toàn bản quyền): GHI NGUỒN mọi nguồn đang có hình trong kế hoạch (CC BY bắt buộc ghi tác giả)
    #      -> ra/<dự án>/ghi_nguon.txt, gộp theo video gốc — dán vào mô tả video YouTube
    try:
        dung_ = dung_tay.doc_dung(du_an)
        kho_ = dung_tay.doc_kho(du_an)
        nguon_ = {}
        for kh in dung_.values():
            for x in kh.get("doan", []):
                m = kho_.get(x["kho_id"]) or {}
                goc_ = m.get("video_goc") or x["kho_id"]
                if goc_ in nguon_:
                    continue
                if m.get("ghi_nguon"):
                    nguon_[goc_] = m["ghi_nguon"]
                elif len(str(goc_)) == 11:                   # id YouTube (chế độ cũ / chưa kiểm giấy phép)
                    td = re.sub(r"\s*\[cảnh [^\]]*\]$", "", str(m.get("tieu_de") or ""))
                    nguon_[goc_] = f"{td} — {m.get('kenh', '')} — https://youtu.be/{goc_}"
        with open(os.path.join(out, "ghi_nguon.txt"), "w", encoding="utf-8") as f:
            f.write("Nguồn tư liệu hình ảnh (giấy phép Creative Commons / public domain / stock miễn phí):\n")
            f.write("\n".join(f"- {v}" for v in sorted(nguon_.values())) + "\n")
        log(f"  ghi nguồn: {len(nguon_)} nguồn -> ghi_nguon.txt")
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! ghi nguồn lỗi: {str(e)[:120]}")

    dung = dung_tay.doc_dung(du_an)
    co_hinh = sum(1 for c in canh if dung.get(str(c["id"]), {}).get("doan"))
    log(f"  tự động theo chủ đề xong sau {(time.time() - t_bd) / 60:.1f} phút: {co_hinh}/{len(canh)} cảnh có hình")
    return {"co_hinh": co_hinh, "so_canh": len(canh), "anh_bu": len(yeu), "loi_anh": loi_anh, "nhap": nhap,
            "video": len(video_duoc_chon), "phut": round(tong_giay_chon / 60, 1)}


def chay(du_an, ngan_sach_phut=NGAN_SACH_PHUT, ten_nhap=None, chi_chon=False, dung_stock=True, che_do="chu_de"):
    """chi_chon=True: chỉ tìm + chấm + chọn (không tải, không đổi kế hoạch) — để đo/xem trước.
    dung_stock=False: bỏ tìm/tải Pexels/Pixabay/Mixkit/Coverr — chỉ video YouTube.
    che_do='chu_de': tìm nguồn và tải từng khoảng theo chủ đề (Giai đoạn 2); 'canh': tìm theo cảnh cũ."""
    if che_do == "chu_de":
        return chay_theo_chu_de(du_an, ngan_sach_phut, ten_nhap, chi_chon, dung_stock)

    import dung_tay
    import goi_y
    import nhung_siglip
    import xep_hang
    out = thu_muc_du_an(du_an)[1]
    canh = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — chạy bước Từ khoá trước")
    import tu_khoa                                           # 19/10: từ khoá từng cảnh chỉ hỏi khi dùng chế độ theo cảnh
    canh = tu_khoa.bu_tu_khoa(du_an) or canh
    _tt(du_an, buoc="mo_ta", xong=0, tong=len(canh))
    import mo_ta_canh                                        # 12/10: chấm theo ý nghĩa (hành động + bối cảnh)
    canh = mo_ta_canh.lam_mo_ta(du_an)
    dung = dung_tay.doc_dung(du_an)
    can = [c for c in canh if not (dung.get(str(c["id"]), {}).get("doan") and not dung[str(c["id"])].get("goi_y"))]
    if not can:
        raise ValueError("mọi cảnh đều đã tự dựng — không còn cảnh nào để tự động")
    t_bd = time.time()
    _tt(du_an, buoc="vec", xong=0, tong=len(can))
    Q = np.stack([xep_hang.vec_canh(c) for c in can])
    w = np.array([float(c.get("dai") or 3.0) for c in can])

    # 1. tìm YouTube (tắt mặc định — DUNG_YOUTUBE)
    tu = list(dict.fromkeys(tu_khoa_nhom(can))) if DUNG_YOUTUBE else []
    kq = {}
    dem = [0]

    def tim(q):
        r = []
        try:                                                 # 15/10 user: Google Videos trước (kết quả sát nội dung hơn)
            import anh_google
            r += anh_google.google_video(q, KQ_MOI_TU)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! Google Videos '{q[:40]}': {str(e)[:80]}")
        try:
            r += dung_tay.tim_youtube(q, KQ_MOI_TU)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! tìm '{q[:40]}': {str(e)[:80]}")
        with _KHOA:
            dem[0] += 1
        _tt(du_an, buoc="tim", xong=dem[0], tong=len(tu))
        return r
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(tim, tu):
            for v in r:
                kq.setdefault(v["id"], v)
    kho = dung_tay.doc_kho(du_an)
    co_san = {k[2:] for k, m in kho.items() if m.get("loai") == "video" and m.get("trang_thai") == "xong"}
    kenh_bo = doc_json(dung_tay.KENH_BO, {}) or {}            # 16/10: kênh từng bị bỏ vì logo / phụ đề to
    ung = [v for v in kq.values() if VIDEO_MIN <= (v.get("dai") or 0) <= VIDEO_MAX and v["id"] not in co_san
           and (v.get("kenh") or "") not in kenh_bo]
    log(f"  tự động: {len(tu)} từ khoá → {len(kq)} video, {len(ung)} ứng viên")

    # 2. storyboard + chấm với mọi cảnh
    dem[0] = 0
    diem = {}

    def sb(v):
        try:
            t, e, tong = xep_hang.storyboard(v["id"])
            import loc_minh_hoa                              # 12/10: kênh thuyết trình/hoạt hình -> không tải
            if len(t) and (loc_minh_hoa.diem_hoat_hinh(e) > loc_minh_hoa.NGUONG_HOAT_HINH).mean() > loc_minh_hoa.TI_LE_BO_VIDEO:
                d = None
            else:
                d = _diem_canh(e, t, Q)
        except Exception as ex:                              # noqa: BLE001
            log(f"    ! storyboard {v['id']}: {str(ex)[:80]}")
            d = None
        with _KHOA:
            dem[0] += 1
        _tt(du_an, buoc="storyboard", xong=dem[0], tong=len(ung))
        return v, d
    with ThreadPoolExecutor(6) as ex:
        for v, d in ex.map(sb, ung):
            if d is not None:
                diem[v["id"]] = (v, d)

    # 2b. VIDEO STOCK SẠCH (Pexels/Pixabay, không logo — 12/10 user: video mẫu không lẫn logo/chữ) theo từ khoá NGẮN
    #     của từng nhóm cảnh; chấm ảnh thu nhỏ với MỌI cảnh; tải vài clip khớp nhất mỗi cảnh TRƯỚC YouTube (rẻ) để
    #     bước chọn YouTube dồn ngân sách vào cảnh stock không phủ được (hành động đặc thù).
    import kho_video_free
    tu_s = []
    for g in nhom_canh(can):
        dai_g = sorted(g, key=lambda x: -float(x.get("dai") or 0))
        tu_s += [(c.get("video") or [""])[0] for c in dai_g[:TU_STOCK_MOI_NHOM]]
        tu_s += [((dai_g[0].get("video") or ["", ""]) + [""])[1], (dai_g[0].get("anh") or [""])[0]]
    tu_s = list(dict.fromkeys(q.strip() for q in tu_s if q and q.strip())) if dung_stock else []
    if not dung_stock:
        log("  kho video free: TẮT (chỉ dùng video YouTube)")
    kq_s = {}
    _tt(du_an, buoc="tim_stock", xong=0, tong=len(tu_s))
    t_tim = time.time()                                      # 15/10 user: 10 tab song song (trước: tuần tự 1 tab)
    theo_tu = kho_video_free.tim_nhieu(tu_s, bao=lambda x, n: _tt(du_an, buoc="tim_stock", xong=x, tong=n)) if tu_s else {}
    for q in tu_s:                                           # giữ thứ tự từ khoá như cũ
        for x in theo_tu.get(q) or []:
            kq_s.setdefault(x["id"], x)
    log(f"  tìm stock: {len(tu_s)} từ khoá x {len(kho_video_free.NGUON_MAC_DINH)} nguồn trong "
        f"{(time.time() - t_tim) / 60:.1f} phút ({kho_video_free.SO_TAB} tab)")
    kho = dung_tay.doc_kho(du_an)
    ds_s = list(kq_s.values())                               # clip đã tải vẫn chấm (tai_file bỏ qua clip đã xong)
    import loc_chu_de                                        # 14/10 user: clip sai con vật / vật chính -> không tải
    _tt(du_an, buoc="loc_chu_de", xong=0, tong=len(ds_s))
    try:
        sai = loc_chu_de.sai_chu_de(du_an, {x["id"]: x.get("ten") or "" for x in ds_s}) if ds_s else set()
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! lọc sai chủ đề lỗi: {str(e)[:120]}")
        sai = set()
    ds_s = [x for x in ds_s if x["id"] not in sai]
    _tt(du_an, buoc="cham_stock", xong=0, tong=len(ds_s))
    co, E = xep_hang.nhung_url([x["thumb"] for x in ds_s], bao=lambda x, n: _tt(du_an, xong=x, tong=n)) if ds_s else ([], None)
    chon_s = {}
    if co:
        S = E @ Q.T                                          # (clip, cảnh)
        for j in range(len(can)):
            moi = 0
            for i in np.argsort(-S[:, j])[:STOCK_MOI_CANH * 6]:
                if S[i, j] < NGUONG_STOCK or moi >= STOCK_MOI_CANH:
                    break
                if co[i] not in chon_s:                      # 14/10: cảnh kề nhau hay chung top clip -> lấy clip MỚI
                    moi += 1
                chon_s[co[i]] = max(chon_s.get(co[i], -1), float(S[i, j]))
    chon_s = sorted(chon_s, key=lambda i: -chon_s[i])[:STOCK_TOI_DA]
    log(f"  stock sạch: {len(tu_s)} từ khoá → {len(ds_s)} clip, chọn tải {len(chon_s)}")
    if chon_s and not chi_chon:                              # 15/10 user: tải CUỐN 5 clip, xong cái nào vào cái kế ngay
        _tai_cuon(du_an, [(ds_s[i]["nguon"], (lambda x=ds_s[i]: dung_tay.tai_file(
            du_an, x["id"], x["file"], x["ten"], x["nguon"], x.get("ghi_nguon", "")))) for i in chon_s], "tai_stock")
    kho = dung_tay.doc_kho(du_an)

    # 3. chọn theo ngân sách (video sẵn trong kho: tính vào ngân sách và điểm nền)
    _tt(du_an, buoc="chon", xong=0, tong=0)
    da_dung, cur = 0.0, np.full(len(can), -1.0)
    import loc_minh_hoa
    for k, m in kho.items():
        if m.get("loai") == "video" and m.get("trang_thai") == "xong" and os.path.isfile(m.get("file", "")) \
                and not m.get("bo_yt"):                      # 16/10: video YouTube đã bỏ (logo/phụ đề) không tính
            try:
                t, e = nhung_siglip.chi_muc_video("tay_" + k, m["file"])
            except Exception:                                # noqa: BLE001
                continue
            if len(t) and (loc_minh_hoa.diem_hoat_hinh(e) > loc_minh_hoa.NGUONG_HOAT_HINH).mean() > loc_minh_hoa.TI_LE_BO_VIDEO:
                continue                                     # video thuyết trình đã tải nhầm: không dùng nên không tính
            da_dung += float(m.get("dai") or 0)
            cur = np.maximum(cur, _diem_canh(e, t, Q))
    chon, tong_giay, cur = chon_video([(i, float(v["dai"]), d) for i, (v, d) in diem.items()], Q, w,
                                      ngan_sach_phut * 60, da_dung, cur)
    phu = int((cur >= NGUONG_DUNG).sum())
    log(f"  tự động: chọn {len(chon)} video, kho {tong_giay / 60:.0f}/{ngan_sach_phut} phút; ước {phu}/{len(can)} cảnh có video khớp")
    _tt(du_an, chon=len(chon), phut=round(tong_giay / 60, 1), uoc_phu=phu, so_canh=len(can))
    if chi_chon:
        return {"chon": [(v, diem[v][0].get("tieu_de", ""), diem[v][0].get("dai")) for v in chon], "phut": round(tong_giay / 60, 1),
                "uoc_phu": phu, "so_canh": len(can), "ung_vien": len(ung), "cur": cur, "can": can}

    # 4. tải (3 một lúc)
    kids = []
    for i in range(0, len(chon), 3):
        lo = []
        for vid in chon[i:i + 3]:
            v = diem[vid][0]
            lo.append(dung_tay.tai_video(du_an, vid, v.get("tieu_de", ""), v.get("dai", 0)))
        kids += lo
        _cho_tai(du_an, kids, "tai")

    dung_tay.danh_dau_logo(du_an)                            # YouTube có logo góc -> phóng to giấu logo khi dựng
    _tt(du_an, buoc="loc_yt", xong=0, tong=0)                # 16/10 user: bỏ hẳn video có logo kênh / phụ đề to
    try:
        bo, soat = dung_tay.loc_youtube(du_an, {k: v.get("kenh") or "" for k, v in kq.items()})
        if soat:
            log(f"  soát video YouTube: bỏ {bo}/{soat} (logo kênh / phụ đề to)")
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! soát logo/phụ đề YouTube lỗi: {str(e)[:120]}")

    # 4b. ảnh THẬT của từng địa danh (cảnh loai=dia_diem): Google Images "<nơi> landscape" / "aerial view"
    dds = list(dict.fromkeys(c["dia_danh_en"] for c in can if c.get("loai") == "dia_diem" and c.get("dia_danh_en")))
    kho = dung_tay.doc_kho(du_an)
    for k, ten in enumerate(dds):
        _tt(du_an, buoc="dia_danh", xong=k, tong=len(dds))
        if sum(1 for m in kho.values() if (m.get("dia_danh") or "").lower() == ten.lower() and m.get("trang_thai") == "xong") >= ANH_MOI_DIA_DANH:
            continue
        qv = nhung_siglip.nhung_chu([f"a landscape photograph of {ten}"])[0]
        lay = 0
        for q in (f"{ten} landscape", f"{ten} aerial view"):
            try:
                ds = dung_tay.tim_anh(q, 30)
            except ValueError as e:
                log(f"    ! ảnh địa danh dừng: {str(e)[:120]}")
                ds = []
            if not ds:
                continue
            d, chu_thumb = xep_hang.diem_anh([a["thumb"] or a["url"] for a in ds], qv, chu=True)
            try:                                             # 14/10 user: tiêu đề trang cho thấy là NƠI KHÁC -> bỏ
                import loc_chu_de
                dung_cho = loc_chu_de.dung_noi(du_an, ten, [a.get("tieu_de") or "" for a in ds])
            except Exception as e:                           # noqa: BLE001
                log(f"    ! kiểm ảnh địa danh lỗi: {str(e)[:100]}")
                dung_cho = set(range(len(ds)))
            xep = sorted((i for i in range(len(ds)) if chu_thumb[i] is False and i in dung_cho
                          and min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 500), key=lambda i: -d[i])
            lay_q = 0
            for i in xep[:10]:
                if lay_q >= ANH_MOI_DIA_DANH // 2:
                    break
                try:
                    kid = dung_tay.tai_anh(du_an, ds[i]["url"], ds[i].get("tieu_de", ""))
                except Exception:                            # noqa: BLE001
                    continue
                f_anh = dung_tay.doc_kho(du_an)[kid]["file"]
                try:
                    import loc_chu
                    if loc_chu.co_chu_anh(f_anh) or loc_minh_hoa.la_hoat_hinh_anh(f_anh):
                        continue
                except Exception:                            # noqa: BLE001
                    pass
                dung_tay._cap_nhat_kho(du_an, kid, dia_danh=ten)   # noqa: SLF001
                lay_q += 1
            lay += lay_q
        log(f"    ảnh địa danh '{ten}': {lay}")

    # 5. gợi ý đoạn (đoạn trỏ video gốc); 14/10: trước đó đánh dấu clip SAI chủ đề trong kho (goi_y bỏ qua)
    _tt(du_an, buoc="loc_chu_de", xong=0, tong=0)
    try:
        import loc_chu_de
        loc_chu_de.danh_dau_kho(du_an)
        loc_chu_de.danh_dau_phong_xanh(du_an)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! lọc sai chủ đề (kho) lỗi: {str(e)[:120]}")
    _tt(du_an, buoc="goi_y", xong=0, tong=0)
    if any(m.get("trang_thai") == "xong" for m in dung_tay.doc_kho(du_an).values()):
        goi_y.goi_y(du_an)

    # 6. cảnh trống / khớp kém -> ảnh Google bù
    dung = dung_tay.doc_dung(du_an)
    yeu = []
    for c in can:
        kh = dung.get(str(c["id"]), {})
        doan = kh.get("doan") or []
        phu_giay = sum(d["dai"] for d in doan)
        diem_doan = [x for x in (kh.get("diem") or []) if x is not None]   # luu_canh ghi điểm ở kh["diem"], không trong đoạn
        if not doan or phu_giay < float(c["dai"]) - 0.5:       # 12/10: ảnh chỉ bù chỗ TRỐNG (video mẫu ~1% ảnh)
            yeu.append(c)
    loi_anh = None
    lay_cua = {}
    for k, c in enumerate(yeu):
        _tt(du_an, buoc="anh", xong=k, tong=len(yeu))
        try:
            lay = len(_anh_google_canh(du_an, c, ANH_MOI_CANH))
        except ValueError as e:                              # captcha không giải / Google lỗi: dừng phần ảnh
            loi_anh = str(e)
            log(f"    ! ảnh bù dừng: {loi_anh[:120]}")
            break
        lay_cua[c["id"]] = lay
    # 6c. 14/10 user: cảnh cần ảnh bù mà không tìm được ảnh NGANG hợp -> Gemini vẽ một ảnh chụp ngang 16:9
    ve_bu = [c for c in yeu if not lay_cua.get(c["id"])] if VE_AI_BU else []
    for k, c in enumerate(ve_bu):
        _tt(du_an, buoc="anh_ve", xong=k, tong=len(ve_bu))
        if not _ve_anh_ngang(du_an, c):
            log(f"    ! cảnh {c['id']}: Gemini không vẽ được ảnh bù")
    if yeu:
        _tt(du_an, buoc="goi_y", xong=0, tong=0)
        dung = dung_tay.doc_dung(du_an)
        ids = [c["id"] for c in yeu if not (dung.get(str(c["id"]), {}).get("doan") and not dung[str(c["id"])].get("goi_y"))]
        try:
            goi_y.goi_y(du_an, ids=ids)
        except ValueError:
            pass

    # 6d. 14/10 user: chỗ HẾT VIDEO MỚI (goi_y ghi thieu_hinh.json, tạm dùng lại video cách >= 25 s) -> Gemini vẽ mỗi
    #     chỗ một ảnh chụp ngang (góc máy khác nhau trong cùng cảnh), gắn cho đúng cảnh đó, rồi gợi ý lại các cảnh ấy
    thieu = {int(k): int(v) for k, v in (doc_json(os.path.join(out, "thieu_hinh.json"), {}) or {}).items() if v}
    theo_id = {c["id"]: c for c in can}
    viec = [(theo_id[i], k) for i, n in sorted(thieu.items()) if i in theo_id for k in range(n)][:GEMINI_BU_TOI_DA]
    if viec and not loi_anh:                                 # 15/10 user: ưu tiên ẢNH THẬT Google, Gemini chỉ vẽ phần còn thiếu
        can_anh = {}
        for c, _ in viec:
            can_anh[c["id"]] = can_anh.get(c["id"], 0) + 1
        con = {}
        for k, (i, n) in enumerate(can_anh.items()):
            _tt(du_an, buoc="anh", xong=k, tong=len(can_anh))
            try:
                lay = len(_anh_google_canh(du_an, theo_id[i], n, rieng=True))
            except ValueError as e:                          # captcha không giải / Google lỗi: phần còn lại để Gemini vẽ
                log(f"    ! ảnh Google bù dừng: {str(e)[:120]}")
                break
            con[i] = n - lay
        da_lay = sum(n - con.get(i, n) for i, n in can_anh.items())
        if da_lay:
            log(f"  ảnh thật Google lấp {da_lay}/{len(viec)} chỗ hết video mới")
        dem_c = {}
        viec2 = []
        for c, k in viec:
            dem_c[c["id"]] = dem_c.get(c["id"], 0) + 1
            if dem_c[c["id"]] <= con.get(c["id"], can_anh[c["id"]]):
                viec2.append((c, k))
        if da_lay and len(viec2) < len(viec):
            _tt(du_an, buoc="goi_y", xong=0, tong=0)
            try:
                goi_y.goi_y(du_an, ids=sorted({c["id"] for c, _ in viec if con.get(c["id"], 1) < can_anh[c["id"]]}))
            except ValueError:
                pass
        viec = viec2
    if viec and VE_AI_BU:
        log(f"  {len(viec)} chỗ hết video mới -> Gemini vẽ ảnh ngang bù ({len({c['id'] for c, _ in viec})} cảnh)")
        dem_v = [0]

        def ve1(ck):
            r = _ve_anh_ngang(du_an, ck[0], bien_the=ck[1])
            with _KHOA:
                dem_v[0] += 1
            _tt(du_an, buoc="anh_ve", xong=dem_v[0], tong=len(viec))
            return r
        with ThreadPoolExecutor(_so_luong_ve()) as ex:
            duoc = sum(1 for r in ex.map(ve1, viec) if r)
        log(f"  Gemini vẽ bù được {duoc}/{len(viec)} ảnh")
        if duoc:
            _tt(du_an, buoc="goi_y", xong=0, tong=0)
            try:
                goi_y.goi_y(du_an, ids=sorted({c["id"] for c, _ in viec}))
            except ValueError:
                pass

    # 6b. ghi nguồn (Wikimedia CC BY bắt buộc ghi tác giả) cho các clip ĐANG DÙNG trong kế hoạch
    dung = dung_tay.doc_dung(du_an)
    kho = dung_tay.doc_kho(du_an)
    dung_id = {x["kho_id"] for kh in dung.values() for x in kh.get("doan", [])}
    dong = sorted({kho[k]["ghi_nguon"] for k in dung_id if kho.get(k, {}).get("ghi_nguon")})
    with open(os.path.join(out, "ghi_nguon.txt"), "w", encoding="utf-8") as f:
        f.write("Nguồn video (chép vào mô tả video):\n" + "\n".join(dong) + "\n" +
                "Video thêm từ Pexels, Pixabay, Mixkit, Coverr (giấy phép miễn phí, không bắt buộc ghi nguồn).\n")

    # 7. bản nháp
    nhap = None
    if ten_nhap:
        from common import thu_muc_nhap_capcut
        dd = thu_muc_nhap_capcut()
        if not dd:
            raise ValueError("không dò được thư mục CapCut Drafts")
        _tt(du_an, buoc="nhap", xong=0, tong=0)
        nhap = {"ten": ten_nhap, "so": dung_tay.tao_nhap(du_an, ten_nhap, dd)}
    dung = dung_tay.doc_dung(du_an)
    co_hinh = sum(1 for c in canh if dung.get(str(c["id"]), {}).get("doan"))
    log(f"  tự động xong sau {(time.time() - t_bd) / 60:.1f} phút: {co_hinh}/{len(canh)} cảnh có hình")
    return {"co_hinh": co_hinh, "so_canh": len(canh), "anh_bu": len(yeu), "loi_anh": loi_anh, "nhap": nhap,
            "video": len(chon), "phut": round(tong_giay / 60, 1)}


def _tu_khoa_doan(du_an, cid):
    """Từ khoá tìm (tiếng Anh) của ĐOẠN nội dung chứa cảnh cid (chu_de.json; đoạn bình luận dùng đoạn kể nó mượn hình)."""
    cds = (doc_json(os.path.join(thu_muc_du_an(du_an)[1], "chu_de.json"), {}) or {}).get("chu_de") or []
    cd = next((x for x in cds if x.get("canh_tu", 0) <= cid <= x.get("canh_den", -1)), None)
    if not cd:
        return []
    cd = next((x for x in cds if x.get("id") == (cd.get("kho_cd") or cd.get("id"))), cd)
    return [t for t in (cd.get("tu_khoa_en") or []) if t] or ([cd["doi_tuong"]] if cd.get("doi_tuong") else [])


def _anh_google_canh(du_an, c, toi_da, rieng=False):
    """Ảnh THẬT Google Images cho cảnh c: tải tối đa `toi_da` ảnh NGANG, không chữ, không hoạt hình -> [id kho].
    rieng=True (chỗ hết video mới): chỉ lấy ảnh CHƯA có trong kho và gắn cho_canh (goi_y dùng ảnh đó ở đúng cảnh này).
    Ném ValueError khi Google hỏi captcha mà không giải / lỗi."""
    import dung_tay
    import goi_y as _gy
    import xep_hang
    q = ((c.get("anh") or []) + (c.get("video") or []))[:1]
    if not q:                                                # 19/10: chế độ chủ đề không có từ khoá từng cảnh
        q = _tu_khoa_doan(du_an, c["id"])[:1]
    if not q:
        return []
    ds = dung_tay.tim_anh(q[0], 30)
    if not ds:
        return []
    d, chu_thumb = xep_hang.diem_anh([a["thumb"] or a["url"] for a in ds], xep_hang.vec_canh(c), chu=True)
    xep = sorted((i for i in range(len(ds)) if chu_thumb[i] is False),    # ảnh thu nhỏ đã thấy chữ: khỏi tải
                 key=lambda i: -(d[i] + (0.02 if min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 700 else 0)))
    ra, thu = [], 0
    for i in xep:
        if d[i] < xep_hang.NGUONG_THAP or len(ra) >= toi_da or thu >= 15:
            break
        if ds[i].get("rong") and ds[i].get("cao") and ds[i]["rong"] < 1.2 * ds[i]["cao"]:
            continue                                         # 14/10 user: ảnh dọc / vuông -> khỏi tải
        thu += 1
        truoc = set(dung_tay.doc_kho(du_an)) if rieng else set()
        try:
            kid = dung_tay.tai_anh(du_an, ds[i]["url"], ds[i].get("tieu_de", ""))
        except Exception:                                    # noqa: BLE001  (trang chặn tải ảnh gốc: lấy ảnh kế)
            continue
        if rieng and kid in truoc:                           # ảnh đã có trong kho (đang dùng chỗ khác): lấy ảnh kế
            continue
        try:
            import loc_chu
            import loc_minh_hoa
            f_anh = dung_tay.doc_kho(du_an)[kid]["file"]
            if loc_chu.co_chu_anh(f_anh) or loc_minh_hoa.la_hoat_hinh_anh(f_anh):
                continue                                     # ảnh có chữ / hoạt hình: không tính, lấy ảnh kế
        except Exception:                                    # noqa: BLE001
            pass
        if not _gy._ngang(dung_tay.doc_kho(du_an)[kid]):     # noqa: SLF001  ảnh tải về là ảnh dọc: không tính
            continue
        if rieng:
            dung_tay._cap_nhat_kho(du_an, kid, cho_canh=c["id"])   # noqa: SLF001
        ra.append(kid)
    return ra


def _ve_cho_het_hinh(du_an, can):
    """Đọc thieu_chi_tiet.json (goi_y) -> vẽ ảnh AI cho từng chỗ hết hình -> gợi ý lại các cảnh đó."""
    import dung_tay
    import goi_y
    import mo_ta_ve
    out = thu_muc_du_an(du_an)[1]
    ct = {int(k): v for k, v in (doc_json(os.path.join(out, "thieu_chi_tiet.json"), {}) or {}).items() if v}
    theo_id = {c["id"]: c for c in can}
    cds = (doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("chu_de") or []
    theo_cd = {cd.get("id"): cd for cd in cds}
    ve_all = mo_ta_ve.doc(du_an)
    viec = []
    for cid, ds in sorted(ct.items()):
        c = theo_id.get(cid)
        if not c:
            continue
        cd = next((x for x in cds if x.get("canh_tu", 0) <= cid <= x.get("canh_den", -1)), {})
        cd = theo_cd.get(cd.get("kho_cd") or cd.get("id"), cd)            # đoạn bình luận: đối tượng của đoạn kể thừa kế
        c0 = float(c.get("bat_dau") or 0)
        for k, o in enumerate(ds):
            t = float(o.get("bd", c0)) - c0
            ve = next((v for v in ve_all.get(str(cid)) or [] if float(v["bd"]) - 0.05 <= t < float(v["kt"]) - 0.05), {})
            mo_ta = (ve.get("mo_ta_en") if ve.get("rieng") or not cd.get("mo_ta_en") else
                     f"{cd['mo_ta_en']}. {ve.get('mo_ta_en') or ''}".strip(". "))
            if not mo_ta:
                mo_ta = c.get("noi_dung") or c.get("text") or ""
            viec.append((dict(c, noi_dung=mo_ta, anh=[cd.get("doi_tuong") or ""], video=[]), k))
    viec = viec[:GEMINI_BU_TOI_DA]
    if not viec:
        return 0
    log(f"  {len(viec)} chỗ hết footage đúng đối tượng -> Gemini vẽ ảnh ngang ({len({c['id'] for c, _ in viec})} cảnh)")
    dem = [0]

    def ve1(ck):
        try:
            r = _ve_anh_ngang(du_an, ck[0], bien_the=ck[1])
        except Exception as e:                               # noqa: BLE001
            log(f"    ! cảnh {ck[0]['id']}: vẽ ảnh hết hình lỗi: {str(e)[:120]}")
            r = None
        with _KHOA:
            dem[0] += 1
        _tt(du_an, buoc="anh_ve", xong=dem[0], tong=len(viec))
        return r
    with ThreadPoolExecutor(_so_luong_ve()) as ex:
        duoc = sum(1 for r in ex.map(ve1, viec) if r)
    log(f"  Gemini vẽ được {duoc}/{len(viec)} ảnh cho chỗ hết hình")
    if duoc:
        _tt(du_an, buoc="goi_y", xong=0, tong=0)
        dung = dung_tay.doc_dung(du_an)
        ids = sorted({c["id"] for c, _ in viec if not (dung.get(str(c["id"]), {}).get("doan")
                                                        and not dung[str(c["id"])].get("goi_y"))})
        try:
            goi_y.goi_y(du_an, ids=ids)
        except ValueError:
            pass
    return duoc


def _ve_anh_ngang(du_an, c, bien_the=0):
    """Gemini (cookie) vẽ một ẢNH CHỤP NGANG 16:9 cho cảnh -> id kho | None. Cache theo câu lệnh (vẽ lại không tốn)."""
    import hashlib
    import sys
    from PIL import Image
    from common import thu_muc_du_an
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    import dung_tay
    noi_dung = (c.get("noi_dung") or c.get("text") or "").strip()
    goi = ", ".join(((c.get("anh") or []) + (c.get("video") or []))[:2])
    prompt = (f"Create a realistic high-resolution documentary PHOTOGRAPH in WIDE 16:9 LANDSCAPE (horizontal) format that "
              f"fills the whole frame. Scene: {noi_dung} (keywords: {goi}). {anh_ve.phong_cach(c.get('thoi_dai'))} "
              f"No text, no letters, no captions, no logos, no watermark, no borders, no collage."
              + (f" Shot variation {bien_the + 1}: use a clearly different camera angle, distance and moment than a "
                 f"standard shot of this scene." if bien_the else ""))
    kid = "g_" + hashlib.md5(prompt.encode("utf-8")).hexdigest()[:12]
    m = dung_tay.doc_kho(du_an).get(kid)
    if m and m.get("trang_thai") == "xong" and os.path.isfile(m.get("file", "")):
        if m.get("cho_canh") is None:
            dung_tay._cap_nhat_kho(du_an, kid, cho_canh=c["id"])   # noqa: SLF001
        return kid
    thu = os.path.join(thu_muc_du_an(du_an)[1], "kho", "anh")
    # 14/10 user: hỏng thì vẽ lại bằng được; từ lượt 3 nhờ ChatGPT viết lại cảnh theo LÝ DO hỏng (tối đa 6 lượt)
    canh_ve, ly_do = noi_dung, ""
    for lan in range(6):
        if lan >= 2 and lan % 2 == 0 and ly_do:
            moi_ = _viet_lai_canh(canh_ve, ly_do)
            if moi_:
                canh_ve = moi_
                log(f"    cảnh {c['id']}: ChatGPT viết lại cảnh (lỗi trước: {ly_do}) -> '{canh_ve[:70]}'")
        p_ = prompt if canh_ve == noi_dung else prompt.replace(f"Scene: {noi_dung}", f"Scene: {canh_ve}")
        f = anh_ve.ve_prompt(p_ if lan % 2 == 0 else p_ + " Absolutely NO writing anywhere.", thu, f"_{kid}_{lan}.png")
        if not f:
            ly_do = "từ chối / không trả ảnh"
            log(f"    ! cảnh {c['id']}: ảnh vẽ bù lần {lan + 1}: {ly_do}")
            continue
        im = Image.open(f).convert("RGB")
        # 19/10 user: không cắt / làm mờ dấu ✦ — bản nháp phóng to ảnh Gemini 120% (dung_tay.tao_nhap)
        if im.size[0] < 1.2 * im.size[1]:                  # AI trả ảnh vuông/dọc: cắt giữa về 16:9
            w2, h2 = im.size
            hh = int(w2 * 9 / 16)
            im = im.crop((0, (h2 - hh) // 2, w2, (h2 - hh) // 2 + hh))
        dich = os.path.join(thu, kid + ".jpg")
        im.save(dich, quality=95)
        try:
            os.remove(f)
        except OSError:
            pass
        # 15/10 user: ảnh AI vẽ CHẤP NHẬN có chữ (biển báo, nhãn…) — không soát chữ, không vẽ lại vì chữ
        dung_tay._cap_nhat_kho(du_an, kid, loai="anh", tieu_de=f"Gemini vẽ: {noi_dung[:60]}", file=dich,   # noqa: SLF001
                               nguon="gemini", trang_thai="xong", pt=100.0, rong=im.size[0], cao=im.size[1],
                               luc=time.time(), cho_canh=c["id"])   # 14/10: ảnh vẽ riêng cho cảnh này (goi_y chỉ dùng ở đây)
        log(f"    cảnh {c['id']}: Gemini vẽ ảnh ngang {im.size[0]}x{im.size[1]}")
        return kid
    return None


def _viet_lai_canh(canh, ly_do):
    """ChatGPT viết lại mô tả CẢNH (ảnh chụp ngang phủ kín khung) cho cùng ý, tránh đúng lỗi vừa gặp. '' nếu không được."""
    from common import hoi_llm
    ly = {"có chữ": "text / letters / signs appeared in the picture",
          "từ chối / không trả ảnh": "the image generator refused or returned no image"}.get(ly_do, ly_do)
    t = hoi_llm("An AI image generator must make an ULTRA-PHOTOREALISTIC wide documentary photograph (16:9, filling the "
                "frame) for the scene below, with NO text at all. The previous attempt failed: " + ly + ".\nRewrite the "
                "scene description (English) for the SAME meaning so the next attempt succeeds: remove anything that tends "
                "to carry writing (signs, newspapers, labels, screens, packaging, posters, street names, logos); avoid "
                "anything violent or graphic a generator may refuse. Under 70 words. Return ONLY the new description."
                "\n\nSCENE:\n" + str(canh), timeout=120)
    t = (t or "").strip().strip('"').strip()
    return t if 15 <= len(t) <= 800 else ""


def chay_nen(du_an, ngan_sach_phut=NGAN_SACH_PHUT, ten_nhap=None, sau=None, dung_stock=True, che_do="chu_de"):
    """sau: hàm gọi khi chạy XONG không lỗi (13/10 user: tự chạy tiếp ✨ Hoàn thiện — một mạch tới bản cuối).
    che_do='chu_de': tìm theo chủ đề (Giai đoạn 2); 'canh': tìm theo cảnh cũ."""
    with _KHOA:
        if TT.get(du_an, {}).get("dang"):
            raise ValueError("đang chạy tự động — chờ xong")
        TT[du_an] = {"dang": True, "buoc": "bat_dau", "luc": time.time(), "che_do": che_do}

    def ch():
        try:
            kq = chay(du_an, ngan_sach_phut, ten_nhap, dung_stock=dung_stock, che_do=che_do)
            ht = ""
            if sau:
                try:
                    ht = sau() or ""
                except Exception as e:                       # noqa: BLE001
                    log(f"  ! không chạy tiếp được Hoàn thiện: {e}")
                    ht = "lỗi: " + str(e)[:200]
            _tt(du_an, dang=False, ket_qua=kq, luc_xong=time.time(), hoan_thien=ht)
        except Exception as e:                               # noqa: BLE001
            log(f"  ! tự động lỗi: {e}")
            _tt(du_an, dang=False, loi=str(e)[:300], luc_xong=time.time())
    threading.Thread(target=ch, daemon=True).start()

