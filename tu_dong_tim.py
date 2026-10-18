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
GEMINI_BU_TOI_DA = 200      # 14/10 user: chỗ hết video mới -> Gemini vẽ ảnh ngang (trần mỗi lần chạy; ~17 credit/ảnh)
ANH_MOI_DIA_DANH = 4        # mỗi địa danh: 2 ảnh phong cảnh + 2 ảnh từ trên cao
GIAY_MOI_NHOM = 60.0        # gom cảnh liền nhau thành nhóm ~1 phút voice; mỗi nhóm tìm TU_MOI_NHOM từ khoá
TU_MOI_NHOM = 2
KQ_MOI_TU = 6               # 11/10: user thấy quét ~1.500 video cho 166 cảnh là quá nhiều
MODIFIERS_BROLL = ("b-roll", "footage")


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


TAI_CUNG_LUC = 5             # 15/10 user: 5 clip tải cùng lúc (trước: lô 3, chờ cả lô xong)
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

    # 2. Lấy từ khoá từ mỗi chủ đề (tự động gắn modifier B-roll / Cinematic / Loại trừ vlog)
    tu_khoa_ds = tao_tu_khoa_broll(ds_chu_de)

    # 3. Tìm nguồn theo chủ đề (Google Videos + YouTube): ~50-100 lượt tìm
    _tt(du_an, buoc="tim_chu_de", xong=0, tong=len(tu_khoa_ds))
    kq = {}
    dem = [0]

    def tim_mot_tu(q):
        r = []
        try:
            import anh_google
            r += anh_google.google_video(q, KQ_MOI_TU)
        except Exception as e:
            log(f"    ! Google Videos '{q[:40]}': {str(e)[:80]}")
        try:
            r += dung_tay.tim_youtube(q, KQ_MOI_TU)
        except Exception as e:
            log(f"    ! tìm '{q[:40]}': {str(e)[:80]}")
        with _KHOA:
            dem[0] += 1
        _tt(du_an, buoc="tim_chu_de", xong=dem[0], tong=len(tu_khoa_ds))
        return r

    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(tim_mot_tu, tu_khoa_ds):
            for v in r:
                kq.setdefault(v["id"], v)

    # Lọc ngay từ khi tìm:
    # bỏ video quá ngắn hoặc dài hơn 45 phút; bỏ video kênh trong kenh_bo.json; bỏ video đã có trong kho
    kho = dung_tay.doc_kho(du_an)
    co_san = set()
    for k, m in kho.items():
        if m.get("loai") == "video" and m.get("trang_thai") == "xong":
            if m.get("video_goc"):
                co_san.add(m["video_goc"])
            elif k.startswith("v_"):
                co_san.add(k[2:])
            else:
                co_san.add(k)

    kenh_bo = doc_json(dung_tay.KENH_BO, {}) or {}
    ung = [v for v in kq.values() if VIDEO_MIN <= (v.get("dai") or 0) <= VIDEO_MAX
           and v["id"] not in co_san and (v.get("kenh") or "") not in kenh_bo]
    # Giới hạn tối đa 120 ứng viên để bước chấm storyboard nhanh gọn (khoảng 30-45 giây), không bị chờ 5-7 phút
    if len(ung) > 120:
        log(f"  tìm được {len(ung)} ứng viên -> chọn top 120 ứng viên tiềm năng nhất để chấm storyboard")
        ung = ung[:120]
    else:
        log(f"  tìm theo chủ đề: {len(tu_khoa_ds)} từ khoá → {len(kq)} video, {len(ung)} ứng viên")

    # 4. Chấm sơ bộ bằng storyboard so với mo_ta_en của chủ đề
    _tt(du_an, buoc="storyboard", xong=0, tong=len(ung))
    log(f"  bắt đầu chấm storyboard cho {len(ung)} video ứng viên (6 luồng GPU)...")
    vec_cd = nhung_siglip.nhung_chu([cd["mo_ta_en"] for cd in ds_chu_de])
    dem = [0]
    diem_theo_cd = {cd["id"]: [] for cd in ds_chu_de}

    def sb(v):
        try:
            t, e, tong = xep_hang.storyboard(v["id"])
            import loc_minh_hoa
            if len(t) and (loc_minh_hoa.diem_hoat_hinh(e) > loc_minh_hoa.NGUONG_HOAT_HINH).mean() > loc_minh_hoa.TI_LE_BO_VIDEO:
                res = None
            else:
                scores = [float((e @ vec_cd[k]).max()) if len(e) else -1.0 for k in range(len(ds_chu_de))]
                k_best = int(np.argmax(scores))
                best_sc = scores[k_best]
                res = (best_sc, k_best, t, e, tong) if best_sc >= NGUONG_DUNG else None
        except Exception as ex:
            log(f"    ! storyboard {v['id']}: {str(ex)[:80]}")
            res = None
        with _KHOA:
            dem[0] += 1
            if dem[0] % 20 == 0 or dem[0] == len(ung):
                log(f"  chấm storyboard: {dem[0]}/{len(ung)} video ({int(dem[0] * 100 / max(1, len(ung)))}%)")
        _tt(du_an, buoc="storyboard", xong=dem[0], tong=len(ung))
        return v, res


    with ThreadPoolExecutor(6) as ex:
        for v, res in ex.map(sb, ung):
            if res is not None:
                best_sc, k_best, t, e, tong = res
                cd_id = ds_chu_de[k_best]["id"]
                v["chu_de_id"] = cd_id
                v["diem_cd"] = best_sc
                diem_theo_cd[cd_id].append((v, best_sc, k_best, t, e, tong))

    # 5. Lượng video cần cho mỗi chủ đề: ~3 lần độ dài của chủ đề
    video_duoc_chon = []
    tong_giay_chon = 0.0

    for cd in ds_chu_de:
        cd_id = cd["id"]
        cd_dai = float(cd.get("dai") or 60.0)
        muc_tieu_giay = 3.0 * cd_dai
        ung_cd = sorted(diem_theo_cd[cd_id], key=lambda x: -x[1])
        tich_luy = 0.0
        for v, sc, k_best, t, e, tong in ung_cd:
            video_duoc_chon.append((v, k_best, t, e, tong))
            tich_luy += float(v.get("dai") or 0.0)
            tong_giay_chon += float(v.get("dai") or 0.0)
            if tich_luy >= muc_tieu_giay:
                break

    log(f"  chọn theo chủ đề: {len(video_duoc_chon)} video nguồn cho {len(ds_chu_de)} chủ đề")
    _tt(du_an, chon=len(video_duoc_chon), phut=round(tong_giay_chon / 60, 1), so_canh=len(can))
    if chi_chon:
        return {"chon": [(v["id"], v.get("tieu_de", ""), v.get("dai")) for v, _, _, _, _ in video_duoc_chon],
                "phut": round(tong_giay_chon / 60, 1), "so_canh": len(can)}

    # 6. Giai đoạn 3: Chỉ tải đúng khoảng cần (1-4 khoảng 20-40s mỗi video)
    _tt(du_an, buoc="tai_khoang", xong=0, tong=0)
    ds_khoang_tai = []
    for v, k_best, t, e, tong in video_duoc_chon:
        qv = vec_cd[k_best]
        khoang_tot = dung_tay.chon_khoang_video(t, e, qv, tong, min_dai=20.0, max_dai=40.0, toi_da_khoang=4)
        for bd, kt, sc in khoang_tot:
            ds_khoang_tai.append({
                "vid": v["id"],
                "bd": bd,
                "kt": kt,
                "tieu_de": v.get("tieu_de", ""),
                "kenh": v.get("kenh", ""),
                "chu_de_id": ds_chu_de[k_best]["id"]
            })

    log(f"  tải từng khoảng: {len(ds_khoang_tai)} khoảng từ {len(video_duoc_chon)} video được chọn (3-5 lượt cùng lúc)...")
    _tt(du_an, buoc="tai_khoang", xong=0, tong=len(ds_khoang_tai))
    dung_tay.tai_khoang_cuon(du_an, ds_khoang_tai, ten_buoc="tai_khoang", max_cung_luc=TAI_CUNG_LUC,
                             on_tien_do=lambda x, n: _tt(du_an, buoc="tai_khoang", xong=x, tong=n,
                                                         pt=round(x * 100 / max(1, n), 1)))

    # 6b. Tự động tải bù ứng viên dự phòng nếu video chính bị lỗi tải (bot chặn, lỗi mạng)
    kho_hien = dung_tay.doc_kho(du_an)
    da_tai_vids = {v["id"] for v, _, _, _, _ in video_duoc_chon}
    ds_du_phong = []
    for k_cd, cd in enumerate(ds_chu_de):
        cd_id = cd["id"]
        cd_dai = float(cd.get("dai") or 60.0)
        tong_xong = sum(
            float(m.get("dai") or 0.0) for m in kho_hien.values()
            if m.get("loai") == "video" and m.get("chu_de") == cd_id and m.get("trang_thai") == "xong"
        )
        if tong_xong < cd_dai:
            ung_con = [x for x in diem_theo_cd.get(cd_id, []) if x[0]["id"] not in da_tai_vids]
            for v_dp, sc, k_best, t, e, tong in ung_con[:2]:
                da_tai_vids.add(v_dp["id"])
                qv = vec_cd[k_best]
                khoang_tot = dung_tay.chon_khoang_video(t, e, qv, tong, min_dai=20.0, max_dai=40.0, toi_da_khoang=3)
                for bd, kt, sc in khoang_tot:
                    ds_du_phong.append({
                        "vid": v_dp["id"], "bd": bd, "kt": kt,
                        "tieu_de": v_dp.get("tieu_de", ""), "kenh": v_dp.get("kenh", ""),
                        "chu_de_id": cd_id
                    })
    if ds_du_phong:
        log(f"  tải dự phòng: {len(ds_du_phong)} khoảng bù cho các chủ đề thiếu footage...")
        dung_tay.tai_khoang_cuon(du_an, ds_du_phong, ten_buoc="tai_du_phong", max_cung_luc=TAI_CUNG_LUC,
                                 on_tien_do=lambda x, n: _tt(du_an, buoc="tai_khoang", xong=x, tong=n,
                                                             pt=round(x * 100 / max(1, n), 1)))

    # 7. Giai đoạn 4: Lọc logo và phụ đề sau khi tải
    dung_tay.danh_dau_logo(du_an)
    _tt(du_an, buoc="loc_yt", xong=0, tong=0)
    try:
        bo, soat = dung_tay.loc_youtube(du_an, {v["id"]: v.get("kenh") or "" for v in kq.values()})
        if soat:
            log(f"  soát video YouTube: bỏ {bo}/{soat} khoảng (logo kênh / phụ đề to)")
    except Exception as e:
        log(f"    ! soát logo/phụ đề YouTube lỗi: {str(e)[:120]}")

    # 8. Giai đoạn 5: Lấp hình theo chủ đề
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

    # 10. Tạo bản nháp CapCut
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
        with ThreadPoolExecutor(3) as ex:
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


def _anh_google_canh(du_an, c, toi_da, rieng=False):
    """Ảnh THẬT Google Images cho cảnh c: tải tối đa `toi_da` ảnh NGANG, không chữ, không hoạt hình -> [id kho].
    rieng=True (chỗ hết video mới): chỉ lấy ảnh CHƯA có trong kho và gắn cho_canh (goi_y dùng ảnh đó ở đúng cảnh này).
    Ném ValueError khi Google hỏi captcha mà không giải / lỗi."""
    import dung_tay
    import goi_y as _gy
    import xep_hang
    q = ((c.get("anh") or []) + (c.get("video") or []))[:1]
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
              f"fills the whole frame. Scene: {noi_dung} (keywords: {goi}). Natural light, real-world look, like stock "
              f"footage. No text, no letters, no captions, no logos, no watermark, no borders, no collage."
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
        w, h = im.size
        im = im.crop((0, 0, int(w * 0.86), int(h * 0.86)))   # (dấu ✦ đã xoá ở anh_ve; cắt mép giữ khung cũ)
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

