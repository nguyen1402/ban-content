# -*- coding: utf-8 -*-
"""SigLIP 2 (mặc định google/siglip2-so400m-patch16-256; đổi bằng biến môi trường BC_SIGLIP): nhúng ảnh và câu chữ vào cùng không gian — thay thế CLIP để
chấm "khung hình nào khớp câu mô tả". Nhận câu TIẾNG VIỆT trực tiếp (huấn luyện đa ngôn ngữ).
Chỉ mục khung hình video lưu riêng ở cache/chi_muc_siglip/ (không lẫn với chỉ mục CLIP)."""
import os
import threading

import numpy as np

from common import duong_cache

MO_HINH = os.environ.get("BC_SIGLIP", "google/siglip2-so400m-patch16-256")   # 11/10: user so, chọn so400m
_NGAN = MO_HINH.split("/")[-1].replace("siglip2-", "")       # vd large-patch16-256, so400m-patch16-256
# bản large giữ thư mục cũ (đã lập chỉ mục); bản khác có thư mục riêng — vector khác mô hình không trộn được
THU_MUC = "chi_muc_siglip" if _NGAN == "large-patch16-256" else "chi_muc_siglip_" + _NGAN
DUOI_ANH = ".siglip.npy" if _NGAN == "large-patch16-256" else f".siglip_{_NGAN}.npy"
_M = {}
_KHOA = threading.RLock()        # máy chủ gọi từ nhiều luồng: một lượt GPU một lúc


def _nap():
    with _KHOA:
        return _nap_()


def _nap_():
    if not _M:
        import os
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        import torch
        import transformers
        transformers.logging.set_verbosity_error()
        from transformers import AutoModel, AutoProcessor
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        dt = torch.float16 if dev == "cuda" else torch.float32
        try:
            p = AutoProcessor.from_pretrained(MO_HINH, local_files_only=True)
            m = AutoModel.from_pretrained(MO_HINH, local_files_only=True, dtype=dt).to(dev).eval()
        except Exception:
            p = AutoProcessor.from_pretrained(MO_HINH)
            m = AutoModel.from_pretrained(MO_HINH, dtype=dt).to(dev).eval()
        _M.update(m=m, p=p, dev=dev, t=torch)
    return _M



def _chuan(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-8)


def nhung_anh(imgs, lo=32):
    M = _nap()
    ra = []
    for i in range(0, len(imgs), lo):
        with _KHOA:
            inp = M["p"](images=imgs[i:i + lo], return_tensors="pt").to(M["dev"])
            with M["t"].no_grad():
                f = M["m"].get_image_features(pixel_values=inp["pixel_values"].to(M["m"].dtype))
        f = getattr(f, "pooler_output", f)
        ra.append(f.float().cpu().numpy())
    return _chuan(np.concatenate(ra)) if ra else np.zeros((0, 1024), np.float32)


def nhung_chu(texts):
    M = _nap()
    with _KHOA:
        inp = M["p"](text=list(texts), padding="max_length", max_length=64, truncation=True, return_tensors="pt").to(M["dev"])
        with M["t"].no_grad():
            f = M["m"].get_text_features(input_ids=inp["input_ids"])
    f = getattr(f, "pooler_output", f)
    return _chuan(f.float().cpu().numpy())


def vec_mo_ta(noi_dung, q):
    """Vector truy vấn của một cảnh/nhịp: câu 'nên chiếu' (tiếng Việt, trọng số cao) + 2 từ khoá đầu."""
    cau = [noi_dung] + list(q[:2]) if noi_dung else list(q[:3])
    v = nhung_chu(cau)
    w = np.array([0.6, 0.25, 0.15][:len(v)], np.float32)
    return _chuan((v * w[:, None]).sum(0, keepdims=True))[0]


def chi_muc_video(kid, path):
    """(t, e): mốc giây và vector SigLIP của 1 khung/1,5 giây (lưu .npz, chạy lại không tính lại)."""
    import chon_doan
    npz = duong_cache(THU_MUC, kid + ".npz")
    if os.path.isfile(npz):
        d = np.load(npz)
        return d["t"], d["e"]
    imgs, ts = chon_doan._khung_ffmpeg(path)                   # noqa: SLF001  (cùng cách trích khung với CLIP)
    e = nhung_anh(imgs)
    t = np.array(ts, np.float32)
    np.savez(npz, t=t, e=e)
    return t, e


def vec_anh_file(path):
    from PIL import Image
    npy = path + DUOI_ANH
    if os.path.isfile(npy):
        return np.load(npy)
    v = nhung_anh([Image.open(path).convert("RGB")])[0]
    np.save(npy, v)
    return v
