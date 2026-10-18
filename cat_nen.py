# -*- coding: utf-8 -*-
"""Tách con vật/đối tượng khỏi nền ảnh -> PNG trong suốt (cho cảnh đồ họa Remotion).

Model: ISNet general-use (ONNX, ~170MB, tools/mo_hinh/). Chạy trên GPU nếu onnxruntime thấy CUDA."""
import os

import numpy as np

import common                                              # noqa: F401  (ưu tiên onnxruntime-gpu ở ort_gpu/)
from common import ROOT

MODEL = os.path.join(ROOT, "tools", "mo_hinh", "isnet-general-use.onnx")
_S = {}


def _phien():
    if "s" not in _S:
        import onnxruntime as ort
        try:
            import torch
            ort.preload_dlls(cuda=True, cudnn=True, directory=os.path.join(os.path.dirname(torch.__file__), "lib"))
        except Exception:                                  # noqa: BLE001
            pass
        ds = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "CUDAExecutionProvider" in ort.get_available_providers() \
            else ["CPUExecutionProvider"]
        _S["s"] = ort.InferenceSession(MODEL, providers=ds)
    return _S["s"]


def mat_na(img):
    """img: PIL RGB -> mặt nạ float 0..1 cùng kích thước."""
    from PIL import Image
    s = _phien()
    x = np.asarray(img.convert("RGB").resize((1024, 1024), Image.BILINEAR), np.float32) / 255.0
    x = (x - 0.5)                                          # ISNet: mean 0.5, std 1
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    p = s.run(None, {s.get_inputs()[0].name: x})[0][0][0]
    p = (p - p.min()) / max(float(p.max() - p.min()), 1e-6)
    return np.asarray(Image.fromarray((p * 255).astype(np.uint8)).resize(img.size, Image.LANCZOS), np.float32) / 255.0


def nen_la_trang(img, ti_le=0.85):
    """Ảnh có nằm trên NỀN TRẮNG không: >= ti_le điểm ở dải viền (3% mỗi cạnh) gần trắng (kênh tối nhất >= 225)."""
    x = np.asarray(img.convert("RGB"), np.uint8)
    h, w = x.shape[:2]
    b = max(2, int(0.03 * min(h, w)))
    vien = np.concatenate([x[:b].reshape(-1, 3), x[-b:].reshape(-1, 3), x[:, :b].reshape(-1, 3), x[:, -b:].reshape(-1, 3)])
    return float((vien.min(axis=1) >= 225).mean()) >= ti_le


def hop_nen_trang(img, a):
    """14/10 user ("cây cao xoá bay sạch màu"): ISNet hay xoá phần MẢNH / THƯA / SÁNG (tán lá, lông, khói, lưới).
    Ảnh AI vẽ luôn trên NỀN TRẮNG trơn -> gộp thêm mặt nạ theo màu (điểm khác trắng rõ = vật): tán lá được giữ nhờ màu,
    phần vật màu trắng vẫn còn nhờ ISNet. Bỏ đốm lẻ nhỏ.
    15/10: ảnh KHÔNG nằm trên nền trắng (AI vẽ cả cảnh chụp có phông) -> chỉ dùng ISNet (tách vật chính khỏi phông);
    gộp mặt nạ màu với ảnh có phông thì cả khung thành "vật" -> bị loại "dính kín mép", vẽ lại hoài."""
    from scipy import ndimage
    if not nen_la_trang(img):
        return a
    x = np.asarray(img.convert("RGB"), np.float32)
    d = (255.0 - x).max(axis=2)                              # độ "khác trắng" (bóng xám nhạt < 45 không tính)
    wk = np.clip((d - 45.0) / 30.0, 0, 1)
    nhan, n = ndimage.label(wk > 0.5)
    if n:
        co = ndimage.sum(np.ones_like(nhan), nhan, range(1, n + 1))
        wk[np.isin(nhan, np.nonzero(co < 0.0004 * nhan.size)[0] + 1)] = 0
    return np.maximum(a, wk)


def tach_nen(duong_vao, duong_ra, cat_vien=True, nen_trang=False):
    """Ghi PNG RGBA: con vật rõ, nền trong suốt; cắt khít khung quanh đối tượng. Trả (rộng, cao, tỉ lệ diện tích đối tượng).
    nen_trang=True: ảnh vẽ trên nền trắng trơn -> gộp thêm mặt nạ theo màu (hop_nen_trang)."""
    from PIL import Image
    img = Image.open(duong_vao).convert("RGB")
    m = mat_na(img)
    m = np.clip((m - 0.12) / 0.76, 0, 1)                   # làm gắt mép một chút, bỏ quầng mờ
    if nen_trang:
        m = hop_nen_trang(img, m)
    rgba = np.dstack([np.asarray(img), (m * 255).astype(np.uint8)])
    out = Image.fromarray(rgba, "RGBA")
    if cat_vien:
        bb = out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        if bb:
            out = out.crop(bb)
    out.save(duong_ra)
    return out.size[0], out.size[1], float((m > 0.5).mean())
