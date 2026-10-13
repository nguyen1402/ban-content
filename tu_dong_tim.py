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
STOCK_MOI_CANH = 3          # 12/10: video stock SẠCH (Pexels/Pixabay) — mỗi cảnh lấy tối đa bấy nhiêu clip khớp nhất
NGUONG_STOCK = 0.12         # điểm ảnh thu nhỏ tối thiểu để tải clip stock
STOCK_TOI_DA = 150           # trần số clip stock mỗi lần chạy (mỗi clip 10-30 s, 5-15 MB)
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
        tu_s += [(c.get("video") or [""])[0] for c in dai_g[:2]] + [(dai_g[0].get("anh") or [""])[0]]
    tu_s = list(dict.fromkeys(q.strip() for q in tu_s if q and q.strip()))
    kq_s = {}
    for k, q in enumerate(tu_s):
        _tt(du_an, buoc="tim_stock", xong=k, tong=len(tu_s))
        for x in kho_video_free.tim(q):
            kq_s.setdefault(x["id"], x)
    kho = dung_tay.doc_kho(du_an)
    ds_s = list(kq_s.values())                               # clip đã tải vẫn chấm (tai_file bỏ qua clip đã xong)
    _tt(du_an, buoc="cham_stock", xong=0, tong=len(ds_s))
    co, E = xep_hang.nhung_url([x["thumb"] for x in ds_s])
    chon_s = {}
    if co:
        S = E @ Q.T                                          # (clip, cảnh)
        for j in range(len(can)):
            for i in np.argsort(-S[:, j])[:STOCK_MOI_CANH]:
                if S[i, j] >= NGUONG_STOCK:
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
            xep = sorted((i for i in range(len(ds)) if chu_thumb[i] is False and min(ds[i].get("rong", 0), ds[i].get("cao", 0)) >= 500),
                         key=lambda i: -d[i])
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

    # 5. gợi ý đoạn (đoạn trỏ video gốc)
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
            thu += 1
            if d[i] < xep_hang.NGUONG_THAP or lay >= ANH_MOI_CANH or thu > 15:
                break
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
            lay += 1
    if yeu:
        _tt(du_an, buoc="goi_y", xong=0, tong=0)
        dung = dung_tay.doc_dung(du_an)
        ids = [c["id"] for c in yeu if not (dung.get(str(c["id"]), {}).get("doan") and not dung[str(c["id"])].get("goi_y"))]
        try:
            goi_y.goi_y(du_an, ids=ids)
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


def chay_nen(du_an, ngan_sach_phut=NGAN_SACH_PHUT, ten_nhap=None):
    with _KHOA:
        if TT.get(du_an, {}).get("dang"):
            raise ValueError("đang chạy tự động — chờ xong")
        TT[du_an] = {"dang": True, "buoc": "bat_dau", "luc": time.time()}

    def ch():
        try:
            kq = chay(du_an, ngan_sach_phut, ten_nhap)
            _tt(du_an, dang=False, ket_qua=kq, luc_xong=time.time())
        except Exception as e:                               # noqa: BLE001
            log(f"  ! tự động lỗi: {e}")
            _tt(du_an, dang=False, loi=str(e)[:300], luc_xong=time.time())
    threading.Thread(target=ch, daemon=True).start()
