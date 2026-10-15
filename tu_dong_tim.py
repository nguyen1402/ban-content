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
DUNG_YOUTUBE = False        # 12/10 user: KHÔNG tự tải YouTube nữa (logo kênh) — chỉ kho miễn phí sạch
STOCK_MOI_CANH = 4          # 12/10: video stock SẠCH (Pexels/Pixabay) — mỗi cảnh lấy tối đa bấy nhiêu clip MỚI khớp nhất
#                             (14/10: clip đã chọn cho cảnh khác không tính -> kho đa dạng, đỡ lặp hình)
NGUONG_STOCK = 0.12         # điểm ảnh thu nhỏ tối thiểu để tải clip stock
STOCK_TOI_DA = 300           # trần số clip stock mỗi lần chạy (mỗi clip 10-30 s, 5-15 MB); 14/10: 150 -> 300 (đỡ lặp)
TU_STOCK_MOI_NHOM = 3       # 14/10: mỗi nhóm ~1 phút tìm từ khoá video của 3 cảnh dài nhất (trước: 2) + biến thể + ảnh
GEMINI_BU_TOI_DA = 200      # 14/10 user: chỗ hết video mới -> Gemini vẽ ảnh ngang (trần mỗi lần chạy; ~17 credit/ảnh)
ANH_MOI_DIA_DANH = 4        # mỗi địa danh: 2 ảnh phong cảnh + 2 ảnh từ trên cao
GIAY_MOI_NHOM = 60.0        # gom cảnh liền nhau thành nhóm ~1 phút voice; mỗi nhóm tìm TU_MOI_NHOM từ khoá
TU_MOI_NHOM = 2
KQ_MOI_TU = 6               # 11/10: user thấy quét ~1.500 video cho 166 cảnh là quá nhiều
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


def chay(du_an, ngan_sach_phut=NGAN_SACH_PHUT, ten_nhap=None, chi_chon=False):
    """chi_chon=True: chỉ tìm + chấm + chọn (không tải, không đổi kế hoạch) — để đo/xem trước."""
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
        try:
            r = dung_tay.tim_youtube(q, KQ_MOI_TU)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! tìm '{q[:40]}': {str(e)[:80]}")
            r = []
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
    ung = [v for v in kq.values() if VIDEO_MIN <= (v.get("dai") or 0) <= VIDEO_MAX and v["id"] not in co_san]
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
    tu_s = list(dict.fromkeys(q.strip() for q in tu_s if q and q.strip()))
    kq_s = {}
    _tt(du_an, buoc="tim_stock", xong=0, tong=len(tu_s))
    t_tim = time.time()                                      # 15/10 user: 10 tab song song (trước: tuần tự 1 tab)
    theo_tu = kho_video_free.tim_nhieu(tu_s, bao=lambda x, n: _tt(du_an, buoc="tim_stock", xong=x, tong=n))
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
        sai = loc_chu_de.sai_chu_de(du_an, {x["id"]: x.get("ten") or "" for x in ds_s})
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! lọc sai chủ đề lỗi: {str(e)[:120]}")
        sai = set()
    ds_s = [x for x in ds_s if x["id"] not in sai]
    _tt(du_an, buoc="cham_stock", xong=0, tong=len(ds_s))
    co, E = xep_hang.nhung_url([x["thumb"] for x in ds_s], bao=lambda x, n: _tt(du_an, xong=x, tong=n))
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
    if chon_s and not chi_chon:
        kids_s = []
        for b in range(0, len(chon_s), 3):                   # 3 file một lúc (Pixabay chặn 429 khi tải dồn)
            kids_s += [dung_tay.tai_file(du_an, ds_s[i]["id"], ds_s[i]["file"], ds_s[i]["ten"], ds_s[i]["nguon"],
                                     ds_s[i].get("ghi_nguon", "")) for i in chon_s[b:b + 3]]
            _cho_tai(du_an, kids_s, "tai_stock")
    kho = dung_tay.doc_kho(du_an)

    # 3. chọn theo ngân sách (video sẵn trong kho: tính vào ngân sách và điểm nền)
    _tt(du_an, buoc="chon", xong=0, tong=0)
    da_dung, cur = 0.0, np.full(len(can), -1.0)
    import loc_minh_hoa
    for k, m in kho.items():
        if m.get("loai") == "video" and m.get("trang_thai") == "xong" and os.path.isfile(m.get("file", "")):
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
        q = ((c.get("anh") or []) + (c.get("video") or []))[:1]
        if not q:
            continue
        try:
            ds = dung_tay.tim_anh(q[0], 30)
        except ValueError as e:                              # captcha không giải / Google lỗi: dừng phần ảnh
            loi_anh = str(e)
            log(f"    ! ảnh bù dừng: {loi_anh[:120]}")
            break
        if not ds:
            continue
        d, chu_thumb = xep_hang.diem_anh([a["thumb"] or a["url"] for a in ds], xep_hang.vec_canh(c), chu=True)
        xep = sorted((i for i in range(len(ds)) if chu_thumb[i] is False),    # ảnh thu nhỏ đã thấy chữ: khỏi tải
                     key=lambda i: -(d[i] + (0.02 if min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 700 else 0)))
        lay = thu = 0
        for i in xep:
            if d[i] < xep_hang.NGUONG_THAP or lay >= ANH_MOI_CANH or thu >= 15:
                break
            if ds[i].get("rong") and ds[i].get("cao") and ds[i]["rong"] < 1.2 * ds[i]["cao"]:
                continue                                     # 14/10 user: ảnh dọc / vuông -> khỏi tải
            thu += 1
            try:
                kid = dung_tay.tai_anh(du_an, ds[i]["url"], ds[i].get("tieu_de", ""))
            except Exception:                                # noqa: BLE001  (trang chặn tải ảnh gốc: lấy ảnh kế)
                continue
            try:
                import loc_chu
                import loc_minh_hoa
                f_anh = dung_tay.doc_kho(du_an)[kid]["file"]
                if loc_chu.co_chu_anh(f_anh) or loc_minh_hoa.la_hoat_hinh_anh(f_anh):
                    continue                                 # ảnh có chữ / hoạt hình: không tính, lấy ảnh kế
            except Exception:                                # noqa: BLE001
                pass
            import goi_y as _gy
            if not _gy._ngang(dung_tay.doc_kho(du_an)[kid]):  # noqa: SLF001  ảnh tải về là ảnh dọc: không tính
                continue
            lay += 1
        lay_cua[c["id"]] = lay
    # 6c. 14/10 user: cảnh cần ảnh bù mà không tìm được ảnh NGANG hợp -> Gemini vẽ một ảnh chụp ngang 16:9
    ve_bu = [c for c in yeu if not lay_cua.get(c["id"])]
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
    if viec:
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
        try:
            import loc_chu
            if loc_chu.co_chu_anh(dich):
                ly_do = "có chữ"
                log(f"    ! cảnh {c['id']}: ảnh vẽ bù lần {lan + 1}: {ly_do}")
                continue
        except Exception:                                    # noqa: BLE001
            pass
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


def chay_nen(du_an, ngan_sach_phut=NGAN_SACH_PHUT, ten_nhap=None, sau=None):
    """sau: hàm gọi khi chạy XONG không lỗi (13/10 user: tự chạy tiếp ✨ Hoàn thiện — một mạch tới bản cuối)."""
    with _KHOA:
        if TT.get(du_an, {}).get("dang"):
            raise ValueError("đang chạy tự động — chờ xong")
        TT[du_an] = {"dang": True, "buoc": "bat_dau", "luc": time.time()}

    def ch():
        try:
            kq = chay(du_an, ngan_sach_phut, ten_nhap)
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
