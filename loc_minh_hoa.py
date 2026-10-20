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
    p_ = os.path.join(thu, f"{kid}_v2.json")
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
