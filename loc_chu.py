# -*- coding: utf-8 -*-
"""(11/10 user: video có chữ thì ĐƯỢC; ẢNH bắt buộc không có chữ — goi_y/tu_dong_tim chỉ lọc ảnh. chu_video giữ lại.)
Dò CHỮ CHÈN ĐÈ (phụ đề, tiêu đề, banner, slide) trên khung video và ảnh — chỉ DÒ vị trí chữ (RapidOCR det,
không đọc chữ, GPU nếu có): ~60 ms/khung 480px.

  * Logo/watermark nhỏ ở GÓC (WBTV Official, Animal Planet, đồng hồ 07:24…) không tính.
  * Một khung "có chữ" khi tổng diện tích hộp chữ ngoài góc > NGUONG_DIEN_TICH khung hình.
  * Video: dò 1 khung / BUOC_GIAY giây (cùng nhịp chỉ mục SigLIP), lưu cache dùng chung (cache/chu_khung/<id>.npz).
  * Ảnh: dò ở 960px, tính cả chữ ở góc, có bất kỳ hộp chữ nào là loại; lưu cạnh file (<ảnh>.chu3.json).
Đo 11/10 trên kho th_nghi_m_2 (362 khung): bắt đủ phụ đề ngắn mà SigLIP bỏ sót; khung bị coi là sạch đúng là sạch."""
import json
import os
import subprocess
import threading

import numpy as np

from common import CACHE_CHUNG, FFMPEG, log

NGUONG_DIEN_TICH = 0.004
CANH_NGAN_TOI_DA = 0.15     # dòng chữ thật: cạnh ngắn hộp < ~10% chiều nhỏ của ảnh (đo 651 hộp, 11/10)
W, H = 480, 270
_TL = threading.local()


def _may():
    if not hasattr(_TL, "e"):
        import logging
        logging.disable(logging.WARNING)                     # RapidOCR báo "detection result is empty" mỗi khung sạch
        import sach_hinh
        from rapidocr import RapidOCR
        prm = {"Global.use_cls": False, "Global.use_rec": False}
        if sach_hinh._gpu_san_sang():                        # noqa: SLF001
            prm.update({"Det.engine_cfg.use_cuda": True, "EngineConfig.onnxruntime.use_cuda": True})
        _TL.e = RapidOCR(params=prm)
    return _TL.e


def dien_tich_chu(rgb, bo_goc=True):
    """Tỉ lệ diện tích hộp chữ trên khung (mảng HxWx3 RGB); bo_goc: không tính chữ nhỏ ở góc (logo kênh)."""
    h, w = rgb.shape[:2]
    r = _may()(np.ascontiguousarray(rgb[:, :, ::-1]))
    s = 0.0
    for b in (r.boxes if r.boxes is not None else []):
        b = np.asarray(b, float)
        if min(np.linalg.norm(b[1] - b[0]), np.linalg.norm(b[2] - b[1])) > CANH_NGAN_TOI_DA * min(w, h):
            continue                                         # hộp to bao cả ảnh / trùm vật: bộ dò bắt nhầm, không phải chữ
        x0, y0, x1, y1 = b[:, 0].min(), b[:, 1].min(), b[:, 0].max(), b[:, 1].max()
        cx, cy = (x0 + x1) / 2 / w, (y0 + y1) / 2 / h
        if bo_goc and (cx < 0.22 or cx > 0.78) and (cy < 0.18 or cy > 0.82) and (x1 - x0) / w < 0.25:
            continue                                         # logo / đồng hồ nhỏ ở góc
        s += (x1 - x0) * (y1 - y0) / (w * h)
    return s


def chu_video(kid, path, buoc=1.5):
    """Mảng tỉ lệ diện tích chữ, một giá trị cho mỗi khung i*buoc giây (cache)."""
    thu = os.path.join(CACHE_CHUNG, "chu_khung")
    os.makedirs(thu, exist_ok=True)
    npz = os.path.join(thu, f"{kid}_{buoc:g}.npz")
    if os.path.isfile(npz):
        return np.load(npz)["s"]
    vf = f"fps=1/{buoc},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2"
    p = subprocess.Popen([FFMPEG, "-v", "error", "-i", path, "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, creationflags=0x08000000 if os.name == "nt" else 0)
    n = W * H * 3
    ra = []
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        ra.append(dien_tich_chu(np.frombuffer(buf, np.uint8).reshape(H, W, 3)))
    p.wait()
    s = np.asarray(ra, np.float32)
    if len(s):
        np.savez(npz, s=s)
    else:
        log(f"    ! dò chữ: không trích được khung {kid}")
    return s


def co_chu_anh(path):
    """True nếu ảnh có chữ — TÍNH CẢ chữ nhỏ ở góc (watermark, 'Photo by…'): user bắt buộc ảnh không có chữ."""
    js = path + ".chu3.json"
    try:
        with open(js, encoding="utf-8") as f:
            return json.load(f)["s"] > 0
    except (OSError, ValueError, KeyError):
        pass
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((960, 960))                                 # dò ở 960px, có BẤT KỲ hộp chữ nào là loại: chữ cái
    s = dien_tich_chu(np.asarray(im), bo_goc=False)          # "a b c" của hình ghép bị mất ở 480px (đo 11/10)
    with open(js, "w", encoding="utf-8") as f:
        json.dump({"s": float(s)}, f)
    return s > 0
