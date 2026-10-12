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
    return xau, float(hh.mean()) if len(hh) else 0.0
