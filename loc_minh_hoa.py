# -*- coding: utf-8 -*-
"""Lọc hình KHÔNG MINH HOẠ ĐƯỢC (12/10 user: mọi hình phải là hình thật, người xem nhìn là hiểu):

  * HOẠT HÌNH / slide / infographic / tranh vẽ: SigLIP so khung với hai nhóm câu mô tả (ảnh chụp thật + bản đồ vs
    hoạt hình, clip art, sơ đồ...). Điểm > NGUONG_HOAT_HINH = hình vẽ. Dùng lại vector đã nhúng nên gần như miễn phí.
    Đo trên kho th_nghi_m_2: ngưỡng 0 tách rõ — trên 0 gần như toàn slide/hoạt hình thuyết trình/màn Subscribe.
  * ĐỨNG HÌNH (kéo dài một khung để thuyết trình, ảnh tĩnh có banner): chênh điểm ảnh trung bình (64x36 xám, thang
    0-255) giữa hai khung cách 1,5 s < NGUONG_DUNG trong >= 2 cặp liền nhau (>= 3 s). Cảnh quay thật có chuyển động
    nhẹ (chim đứng, ong bò) vẫn > 1. (Vector SigLIP KHÔNG dùng được cho việc này: cùng cảnh quay cũng giống nhau.)
  * Video có > TI_LE_BO_VIDEO khung hoạt hình (kênh thuyết trình) bị bỏ cả video."""
import os
import subprocess

import numpy as np

from common import CACHE_CHUNG, FFMPEG

NGUONG_HOAT_HINH = 0.0
NGUONG_DUNG = 1.0
TI_LE_BO_VIDEO = 0.30
# 19/10 user ("dò nhầm những khu vực video có cảnh bị slow từ 1 ảnh đứng im"): khúc ẢNH TĨNH được phóng / lia chậm —
# cả khung khớp gần hoàn hảo bằng MỘT phép dời + phóng chung (footage thật luôn có chuyển động riêng lẻ / thị sai).
# Đo kho cho_digo (328 mảnh): ngưỡng dưới bắt đúng dingo hoàng hôn phóng dần, ảnh dựng chuồng + bản đồ, chuỗi ảnh chim.
KEO_DOI_PX = 0.4            # có dời / phóng (khung 320x180, 2 khung/giây) — dưới mức này là đứng hình (đã có lọc riêng)
KEO_KHOP = 0.9              # >= 90% điểm theo dõi khớp một phép biến đổi chung
KEO_SAI_SO = 2.5            # sai khác điểm ảnh còn lại sau khi bù phép biến đổi (thang 0-255)
KEO_TOI_THIEU = 1.0         # khúc dài từ bấy nhiêu giây mới loại (19/10: 1,5 -> 1,0 — khúc đứng 2-4 s vẫn lọt vào bản thô)
KEO_SAI_TINH = 2.0          # 19/10 user ("ảnh zoom to không chuyển động" vẫn lọt): khung KHÔNG dời (đứng hình) cũng tính —
#                             khớp gần hoàn hảo, sai số < ngưỡng này là ĐỨNG YÊN / phóng cực chậm (đo bản thô cho_digo: 5
#                             đoạn dời 0,00 sai < 0,6 = video dừng hình). Khung phẳng (trời, nước) không có điểm theo dõi:
KEO_CHENH_PHANG = 0.8       #   chênh điểm ảnh trung bình < ngưỡng này cũng là đứng yên
KEO_TRUNG_VI = 0.9          # 20/10 user (ảnh tĩnh nutria phóng chậm vẫn lọt: có phụ đề đổi + hạt bụi + lông lấp lánh -> sai số
#                             TRUNG BÌNH 3-7): làm mờ nhẹ rồi lấy TRUNG VỊ sai lệch sau khi bù biến đổi — ảnh tĩnh 0,43-0,84,
#                             footage chuyển động thật cao hơn; kèm khớp >= KEO_KHOP_TV (phụ đề đổi làm tụt tỉ lệ khớp)
KEO_KHOP_TV = 0.8
# 25/10 user ("tự chọn video thì băm kiểu gì cũng được nhưng phải khớp cơ bản những cảnh rõ ràng"): cảnh RÁC của video
# YouTube — không phải footage minh hoạ. Nhóm "người" chỉ dùng khi chủ thể không phải người.
RAC = ["a title card with large text", "a black screen with white text", "a subscribe button end screen",
       "a youtube end screen with video thumbnails", "a channel logo intro animation", "a blank black screen",
       "a split screen collage of several videos", "a map graphic", "a computer screen recording"]
RAC_NGUOI = ["a person talking to the camera", "a presenter speaking in a studio", "an interview with a person sitting",
             "a vlogger talking selfie video"]
_RAC = {}


def diem_rac(e, co_nguoi=True):
    """(n,) điểm SigLIP cao nhất với các mô tả cảnh rác (co_nguoi: tính cả người nói trước ống kính / phỏng vấn)."""
    import nhung_siglip
    k = bool(co_nguoi)
    if k not in _RAC:
        _RAC[k] = nhung_siglip.nhung_chu(RAC + (RAC_NGUOI if k else []))
    return (np.atleast_2d(e) @ _RAC[k].T).max(1)


THAT = ["a real photograph of an animal", "a real photograph of an insect", "a real photograph of a bird",
        "a real photograph of people", "a real photograph of an object", "a real photograph of a landscape",
        "an aerial photograph", "a geographic map", "a news photograph"]
GIA = ["a cartoon illustration", "a vector clip art drawing", "an infographic", "a diagram", "a digital painting",
       "an anime drawing", "a 3D render", "a children's book illustration", "a sketch drawing"]
_V = {}


def diem_hoat_hinh(e):
    """Điểm 'hình vẽ' cho từng vector SigLIP (mảng (n,)); > NGUONG_HOAT_HINH là hoạt hình/slide."""
    import nhung_siglip
    if not _V:
        _V["t"], _V["g"] = nhung_siglip.nhung_chu(THAT), nhung_siglip.nhung_chu(GIA)
    e = np.atleast_2d(e)
    return (e @ _V["g"].T).max(1) - (e @ _V["t"].T).max(1)


# 25/10 user ("nói tàu hoả chìm dưới đáy đại dương lại băm lấy đoạn ô tô dưới đáy đại dương"): khớp mô tả cả câu thì BỐI CẢNH
# (đáy biển) đủ điểm -> thêm CHỐT VẬT THỂ: khung phải giống vật thể chính hơn các vật dễ nhầm
# nhóm vật + CẶP HAY NHẦM thật (đo 25/10 trên dự án America_DUMPED: tàu thuyền / cá / thợ lặn điểm cao ở MỌI cảnh dưới nước
# nên không dùng làm vật so — chỉ so những cặp dễ lẫn hình dạng: toa tàu <-> ô tô / xe tải, người <-> thú…)
NHOM_NHAM = {"ray": ["a train", "a subway car"], "duong_bo": ["a car", "a truck", "a bus"], "thuyen": ["a ship", "a boat"],
             "bay": ["an airplane"], "nguoi": ["a person", "a scuba diver"], "thu": ["an animal", "a dog", "a bird"],
             "nha": ["a building"]}
CAP_NHAM = {"ray": ["duong_bo", "bay"], "duong_bo": ["ray"], "thuyen": ["bay"], "bay": ["thuyen", "duong_bo"],
            "nguoi": ["thu"], "thu": ["nguoi"], "nha": []}
VAT_NHAM = [x for n in NHOM_NHAM.values() for x in n]
NGUONG_VAT_NHAM = 0.04     # vật dễ nhầm phải HIỆN RÕ (điểm SigLIP >= mức này; ô tô chìm đo 0,05-0,08)
LE_VAT = 0.025             # ... và hơn vật thể chính ít nhất bấy nhiêu (toa tàu bị cần cẩu thả: thua xe 0,024 -> vẫn giữ)
GIONG_VAT = 0.70           # vật thể chính giống nhóm nào nhất (>= mức này) thì thuộc nhóm đó
_LUONG = {"thousands", "hundreds", "dozens", "many", "various", "several", "lots", "group", "groups", "pair", "set", "pile"}
_VAT = {}


def vat_chinh(mo_ta_en):
    """Cụm danh từ ĐẦU của mô tả chủ thể (vật thể lõi): "An old subway car being lifted into the ocean" -> "An old subway car"."""
    import re
    tu = str(mo_ta_en or "").replace(",", " ").split()
    ra = []
    for w in tu:
        wl = w.lower().strip(".;:")
        if wl == "of" and ra and ra[-1].lower() in _LUONG:   # "Thousands of old tires" -> đi tiếp qua "of"
            ra.append(w)
            continue
        if ra and (re.search(r"(ing|ed)$", wl) or wl in ("in", "on", "at", "with", "under", "from", "into", "of", "near",
                                                        "and", "that", "which", "who", "as", "to", "for", "by", "while")):
            break
        ra.append(w.strip(".;:"))
    return " ".join(ra[:7])


def sai_vat(e, mo_ta_en):
    """(n,) bool — 25/10 user ("nói tàu hoả chìm dưới đáy đại dương lại băm đoạn ô tô dưới đáy đại dương"): khung có vật
    DỄ NHẦM hiện rõ và khớp hơn hẳn vật thể chính (khớp cả câu thì bối cảnh đáy biển đủ điểm nên ô tô chìm lọt vào chủ thể
    toa tàu). Vật thể chính không thuộc nhóm nào / không có cặp nhầm -> mọi khung qua chốt."""
    import nhung_siglip
    vat = vat_chinh(mo_ta_en)
    e = np.atleast_2d(e)
    if not vat:
        return np.zeros(len(e), bool)
    if vat not in _VAT:
        v = nhung_siglip.nhung_chu([f"a photo of {vat.lower()}"])[0]   # chữ thường: SigLIP phân biệt hoa / thường
        c = nhung_siglip.nhung_chu(VAT_NHAM)
        giong = c @ v
        nhom = {k: max(float(giong[VAT_NHAM.index(x)]) for x in ds) for k, ds in NHOM_NHAM.items()}
        import re
        vl = " " + re.sub(r"[^a-z ]", " ", vat.lower()) + " "
        # nhóm của vật thể chính: CỤM TÊN khớp dài nhất trước ("subway cars" -> nhóm ray, dù vector gần "a car" hơn),
        # không khớp tên nào mới theo độ giống vector
        khop = [(len(x), k) for k, ds in NHOM_NHAM.items() for x in ds
                if re.search(r"\b" + re.escape(x.split(" ", 1)[-1]) + r"s?\b", vl)]
        cua = max(khop)[1] if khop else (max(nhom, key=nhom.get) if max(nhom.values()) >= GIONG_VAT else None)
        for x in NHOM_NHAM.get(cua, []):                     # gạch cụm của chính nhóm ("subway car" chứa chữ "car")
            vl = re.sub(r"\b" + re.escape(x.split(" ", 1)[-1]) + r"s?\b", " ", vl)
        ten_co = {k for k, ds in NHOM_NHAM.items() if k != cua                # "subway cars, ships" -> thuyền cũng đúng
                  and any(re.search(r"\b" + re.escape(x.split()[-1]) + r"s?\b", vl) for x in ds)}
        so = [x for k in CAP_NHAM.get(cua, []) if k not in ten_co for x in NHOM_NHAM[k]]
        _VAT[vat] = (v, nhung_siglip.nhung_chu(so) if so else None)
    v, c = _VAT[vat]
    if c is None:
        return np.zeros(len(e), bool)
    nham = (e @ c.T).max(1)
    return (nham >= NGUONG_VAT_NHAM) & (nham - e @ v >= LE_VAT)


GAME = ["a video game screenshot", "computer game graphics", "a flight simulator game"]
LE_GAME = 0.03              # 18/10 đo cho_digo: lề 0,03 bắt 6/6 clip game, 7/398 clip khác (cũng là game / màn hình máy tính)


def la_game(e, ti_le=0.5):
    """True nếu > ti_le khung là cảnh TRÒ CHƠI ĐIỆN TỬ (18/10 user thấy 'hoạt hình' = gameplay trực thăng)."""
    import nhung_siglip
    if "game" not in _V:
        _V["game"] = nhung_siglip.nhung_chu(GAME)
        if "t" not in _V:
            _V["t"], _V["g"] = nhung_siglip.nhung_chu(THAT), nhung_siglip.nhung_chu(GIA)
    e = np.atleast_2d(e)
    if not len(e):
        return False
    return float((((e @ _V["game"].T).max(1) - (e @ _V["t"].T).max(1)) > LE_GAME).mean()) > ti_le


def la_hoat_hinh_anh(path):
    import nhung_siglip
    return bool(diem_hoat_hinh(nhung_siglip.vec_anh_file(path))[0] > NGUONG_HOAT_HINH)


def chuyen_dong(kid, path, buoc=1.5):
    """Chênh điểm ảnh giữa các cặp khung liền nhau (n-1,) theo nhịp chỉ mục (cache dùng chung)."""
    thu = os.path.join(CACHE_CHUNG, "chuyen_dong")
    os.makedirs(thu, exist_ok=True)
    npy = os.path.join(thu, f"{kid}_{buoc:g}.npy")
    if os.path.isfile(npy):
        return np.load(npy)
    W, H = 64, 36
    p = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-an", "-vf", f"fps=1/{buoc},scale={W}:{H},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    a = np.frombuffer(p.stdout, np.uint8)
    n = len(a) // (W * H)
    a = a[:n * W * H].reshape(n, H, W).astype(np.float32)
    d = np.abs(a[1:] - a[:-1]).mean((1, 2)) if n > 1 else np.zeros(0, np.float32)
    np.save(npy, d)
    return d


def keo_tinh(kid, path):
    """[(giây đầu, giây cuối)] các khúc ảnh tĩnh bị phóng / lia chậm (cache dùng chung theo kid)."""
    import json
    thu = os.path.join(CACHE_CHUNG, "keo_tinh")
    os.makedirs(thu, exist_ok=True)
    p_ = os.path.join(thu, f"{kid}_v3.json")
    if os.path.isfile(p_):
        try:
            return [tuple(x) for x in json.load(open(p_, encoding="utf-8"))]
        except (OSError, ValueError):
            pass
    import cv2
    W, H = 320, 180
    r = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-an", "-vf", f"fps=2,scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    n = len(r.stdout) // (W * H)
    ks = [np.frombuffer(r.stdout, np.uint8, W * H, k * W * H).reshape(H, W) for k in range(n)]
    y0, y1, x0, x1 = H // 8, H - H // 8, W // 8, W - W // 8
    ok = []
    for a, b in zip(ks, ks[1:]):
        dat = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean()) < KEO_CHENH_PHANG
        p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 4)
        if p0 is not None and len(p0) >= 25:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None)
            m = st.ravel() == 1
            if m.sum() >= 25:
                q0, q1 = p0[m].reshape(-1, 2), p1[m].reshape(-1, 2)
                M, inl = cv2.estimateAffinePartial2D(q0, q1, method=cv2.RANSAC, ransacReprojThreshold=0.6)
                if M is not None:
                    doi = float(np.median(np.linalg.norm((q0 @ M[:, :2].T + M[:, 2]) - q0, axis=1)))
                    w = cv2.warpAffine(a, M, (W, H))
                    sai = float(np.abs(w[y0:y1, x0:x1].astype(np.int16) - b[y0:y1, x0:x1].astype(np.int16)).mean())
                    khop = float(inl.mean()) > KEO_KHOP
                    dat = dat or (khop and (sai < KEO_SAI_TINH or (doi > KEO_DOI_PX and sai < KEO_SAI_SO)))
                    if not dat and float(inl.mean()) >= KEO_KHOP_TV:
                        g1 = cv2.GaussianBlur(w.astype(np.float32), (7, 7), 0)
                        g2 = cv2.GaussianBlur(b.astype(np.float32), (7, 7), 0)
                        dat = float(np.median(np.abs(g1[y0:y1, x0:x1] - g2[y0:y1, x0:x1]))) <= KEO_TRUNG_VI
        ok.append(dat)
    ra, i = [], 0
    while i < len(ok):                                       # cặp khung i = khoảng [i/2, i/2 + 0,5] giây
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]:
                j += 1
            if (j - i) * 0.5 >= KEO_TOI_THIEU:
                ra.append((round(i * 0.5, 2), round(j * 0.5, 2)))
            i = j
        else:
            i += 1
    json.dump(ra, open(p_, "w", encoding="utf-8"))
    return ra


def khung_xau(kid, path, e, buoc=1.5):
    """(mask, ti_le_hoat_hinh): mask[i] = khung i là hoạt hình/slide hoặc nằm trong khúc đứng hình >= 3 s."""
    hh = diem_hoat_hinh(e) > NGUONG_HOAT_HINH
    xau = hh.copy()
    d = chuyen_dong(kid, path, buoc)
    tinh = d < NGUONG_DUNG
    i = 0
    while i < len(tinh):
        if tinh[i]:
            j = i
            while j < len(tinh) and tinh[j]:
                j += 1
            if j - i >= 2:
                xau[i:min(j + 1, len(xau))] = True
            i = j
        else:
            i += 1
    try:                                                     # 19/10: khúc ảnh tĩnh phóng / lia chậm
        for a_, b_ in keo_tinh(kid, path):
            for k in range(len(xau)):
                if a_ - buoc / 2 <= k * buoc <= b_:
                    xau[k] = True
    except Exception:                                        # noqa: BLE001
        pass
    return xau, float(hh.mean()) if len(hh) else 0.0
