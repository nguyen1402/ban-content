# -*- coding: utf-8 -*-
"""Lọc hình SẠCH: không chữ cứng (phụ đề, biển chữ chèn), không logo kênh ở góc, không viền đen.

  * co_chu(file, bd, dai)   OCR vài khung của đoạn — có chữ rõ là loại.
  * logo_video(file, id)    logo TĨNH ở góc, đo trên cả video (nội dung đổi, logo thì không).
  * vung_cat(file, ...)     cropdetect để cắt viền đen / khung hình nhỏ lọt trong khung.
"""
import os
import re
import threading

import numpy as np

from common import FFMPEG, chay, doc_json, duong_cache, ghi_json

NGUONG_CHU = 0.80          # độ tin cậy OCR tối thiểu để coi là có chữ
SO_KHUNG_OCR = 4
_OCR = {}


def _ffmpeg_khung(path, vf, bd=None, dai=None, fmt="rgb24"):
    lenh = [FFMPEG, "-v", "error"]
    if bd is not None:
        lenh += ["-ss", f"{bd:.2f}", "-t", f"{dai:.2f}"]
    lenh += ["-i", path, "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", fmt, "-"]
    p = __import__("subprocess").run(lenh, capture_output=True, timeout=300,
                                     creationflags=0x08000000 if os.name == "nt" else 0)
    return p.stdout


# --------------------------------------------------------------------------- chữ cứng
_TL = threading.local()
_KHOA_OCR = threading.Lock()
LUONG_OCR = 3              # số luồng ONNX cho MỖI bộ OCR (mặc định -1 = mọi lõi → nhiều bộ chạy chung tranh nhau, chậm gấp chục lần)
_DA_OCR = {}
_KHOA_JSON = threading.Lock()


def tat_ocr():
    """Công tắc tắt lọc chữ (giao diện / --khong-ocr đặt BC_TAT_OCR=1): bỏ OCR, giữ các bộ lọc còn lại."""
    return os.environ.get("BC_TAT_OCR") == "1"


def _gpu_san_sang():
    """True nếu onnxruntime thấy CUDA. Nạp trước DLL CUDA/cuDNN đi kèm torch (đã có trong môi trường) cho chắc."""
    if "g" not in _OCR:
        ok = False
        try:
            import onnxruntime as ort
            try:
                import torch
                ort.preload_dlls(cuda=True, cudnn=True, directory=os.path.join(os.path.dirname(torch.__file__), "lib"))
            except Exception:                           # noqa: BLE001  (bản ort cũ không có preload_dlls / không có torch)
                pass
            ok = "CUDAExecutionProvider" in ort.get_available_providers()
        except Exception:                               # noqa: BLE001
            ok = False
        _OCR["g"] = ok
    return _OCR["g"]


def _ocr():
    """Mỗi luồng một bộ RapidOCR riêng. Có CUDA thì chạy trên GPU (nhanh hơn nhiều, không ăn CPU); không thì CPU,
    mỗi bộ chỉ LUONG_OCR luồng để nhiều bộ chạy chung không tranh lõi."""
    if not hasattr(_TL, "e"):
        import logging
        logging.disable(logging.INFO)                   # RapidOCR rất ồn ở mức INFO
        from rapidocr import RapidOCR
        gpu = _gpu_san_sang()
        prm = {"EngineConfig.onnxruntime.intra_op_num_threads": LUONG_OCR,
               "EngineConfig.onnxruntime.inter_op_num_threads": 1}
        if gpu:
            prm.update({"Det.engine_cfg.use_cuda": True, "Cls.engine_cfg.use_cuda": True, "Rec.engine_cfg.use_cuda": True,
                        "EngineConfig.onnxruntime.use_cuda": True})
        _TL.e = RapidOCR(params=prm)
    return _TL.e


def chu_van(path, bd, dai, w=480, h=270):
    """Văn bản OCR (độ tin cậy >= NGUONG_CHU, >=3 ký tự chữ/số) thấy trong [bd, bd+dai]; '' nếu không có chữ.
    Dùng làm TÍN HIỆU: chữ khớp tên thực thể của nhịp (logo RSPCA, bảng 1080 Poison) là điểm cộng, chữ lạ mới bị loại."""
    if tat_ocr():
        return ""
    khoa = f"{os.path.basename(path)}|{bd:.1f}|{dai:.1f}"
    cu, moi = duong_cache("ocr.json"), duong_cache("ocr_van.json")
    with _KHOA_OCR:
        if cu not in _DA_OCR:
            _DA_OCR[cu] = doc_json(cu, {})
        if _DA_OCR[cu].get(khoa) is False:               # bản cache cũ: đã biết không có chữ
            return ""
        if moi not in _DA_OCR:
            _DA_OCR[moi] = doc_json(moi, {})
        if khoa in _DA_OCR[moi]:
            return _DA_OCR[moi][khoa]
    buf = _ffmpeg_khung(path, f"fps={SO_KHUNG_OCR}/{max(dai, 1.0):.2f},scale={w}:{h}", bd, dai)
    n = len(buf) // (w * h * 3)
    ds = []
    for i in range(min(n, SO_KHUNG_OCR)):
        im = np.frombuffer(buf, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3)
        r = _ocr()(im)
        for t, sc in zip(r.txts or [], r.scores or []):
            if float(sc) >= NGUONG_CHU and len(re.sub(r"\W", "", t)) >= 3:
                ds.append(t.strip())
    kq = " | ".join(dict.fromkeys(ds))
    with _KHOA_OCR:
        _DA_OCR[moi][khoa] = kq
        ghi_json(moi, _DA_OCR[moi])
    return kq


def co_chu(path, bd, dai, w=480, h=270):
    """True nếu đoạn có chữ OCR được (>=3 ký tự chữ/số, tin cậy cao)."""
    return bool(chu_van(path, bd, dai, w, h))


_TINH = {}


def anh_tinh(path, bd, dai, w=160, h=90):
    """True nếu đoạn là MỘT TẤM ẢNH/khung chữ ĐỨNG YÊN làm thành video: các khung (6/giây) gần như giống hệt nhau
    (sai khác trung bình <0,35/255). Quay thật luôn có nhiễu cảm biến nên không bao giờ giống hệt.
    KHÔNG bắt được ảnh bị phóng/lia (Ken Burns): đã thử bù chuyển động toàn cục nhưng cảnh quay thật ít động
    (flycam trên đồng, bẫy ảnh) cho số đo y hệt nên bị loại nhầm ~1/3 — bỏ."""
    k = (path, round(bd, 1), round(dai, 1))
    if k in _TINH:
        return _TINH[k]
    buf = _ffmpeg_khung(path, f"fps=6,scale={w}:{h},format=gray", bd, dai, fmt="gray")
    n = len(buf) // (w * h)
    kq = False
    if n >= 5:
        F = np.frombuffer(buf, np.uint8, n * w * h).reshape(n, w * h).astype(np.float32)
        kq = bool(np.abs(np.diff(F, axis=0)).mean() < 0.35)
    _TINH[k] = kq
    return kq


def kiem_truoc(ds, luong=6):
    """Chạy SONG SONG bộ lọc 'khung đen đầu/cuối' + 'ảnh đứng yên' + OCR cho nhiều đoạn (path, bd, dai) và ghi vào
    cache; sau đó gọi lại từng hàm tuần tự sẽ trả ngay từ cache."""
    from concurrent.futures import ThreadPoolExecutor

    def mot_doan(x):
        if not dau_cuoi_toi(*x) and not anh_tinh(*x):
            chu_van(*x)
    with ThreadPoolExecutor(luong) as ex:
        list(ex.map(mot_doan, ds))


# --------------------------------------------------------------------------- logo tĩnh
def _cau_truc(m):
    gx = np.abs(np.diff(m, axis=1))[:-1, :]
    gy = np.abs(np.diff(m, axis=0))[:, :-1]
    return float((gx + gy).mean())


def logo_video(path, vid, w=320, h=180):
    """Danh sách góc có logo tĩnh ('TL','TR','BL','BR'). Cần >=40 khung (video đủ dài) mới tin."""
    cache = duong_cache("logo.json")
    da = doc_json(cache, {})
    if vid in da:
        return da[vid]
    buf = _ffmpeg_khung(path, f"fps=1/1.5,scale={w}:{h}", fmt="gray")
    n = len(buf) // (w * h)
    ra = []
    if n >= 40:
        F = np.frombuffer(buf, np.uint8, n * w * h).reshape(n, h, w).astype(np.float32)
        mean = F.mean(axis=0)
        ph, pw = int(h * 0.2), int(w * 0.2)
        vung = {"TL": mean[:ph, :pw], "TR": mean[:ph, w - pw:],
                "BL": mean[h - ph:, :pw], "BR": mean[h - ph:, w - pw:]}
        ct = {k: _cau_truc(v) for k, v in vung.items()}
        for k, v in ct.items():
            khac = sorted(x for kk, x in ct.items() if kk != k)
            if v >= 6.0 and v >= 2.5 * max(khac[len(khac) // 2], 0.3):
                ra.append(k)
    with _KHOA_JSON:                                    # nhiều luồng cùng ghi: đọc lại rồi ghi để không mất mục của luồng khác
        da = doc_json(cache, {})
        da[vid] = ra
        ghi_json(cache, da)
    return ra


LOGO_TOI_THIEU = 1.2        # % điểm ở góc là NÉT ĐỨNG YÊN (qua mọi cảnh quay) thì coi là logo / chữ kênh


def _ben_vung(F, nguong=25.0):
    """Tỉ lệ khung mà mỗi điểm là NÉT (cạnh) — logo/chữ kênh: gần 1 ở mọi khung, nội dung đổi: thấp."""
    gx = np.abs(np.diff(F, axis=2))[:, :-1, :]
    gy = np.abs(np.diff(F, axis=1))[:, :, :-1]
    return ((gx + gy) > nguong).mean(axis=0)


def logo_kenh(path, vid, dai=0.0):
    """16/10 user ("nhiều kênh có logo kênh"): góc có logo / chữ kênh (ACM, ABC TV, @tên instagram…) -> ['TL',...].
    Lấy MỘT khung giữa mỗi cảnh quay (canh_cat): logo đứng yên qua mọi cảnh quay, phông nền thì không. Video ít cảnh
    quay (< 8, cắt mềm): lấy khung theo chuyển động, chỉ tin khi phần giữa khung không có nét đứng yên (máy quay cố
    định -> phông nền đứng yên, không phải logo). Đo 16/10: fish 28 video YouTube bắt ACM, ABC TV, @instagram, logo
    màu (đã xem khung); 120 clip stock (không logo) báo nhầm 0."""
    cache = duong_cache("logo_kenh.json")
    da = doc_json(cache, {})
    if vid in da:
        return da[vid]
    W, H = 320, 180
    buf = _ffmpeg_khung(path, f"fps=2,scale={W}:{H}", fmt="gray")
    n = len(buf) // (W * H)
    ra = []
    if n >= 24:
        A = np.frombuffer(buf, np.uint8, n * W * H).reshape(n, H, W)
        dai = float(dai or n / 2.0)
        moc = [0.0] + list(canh_cat(path, vid)) + [dai]
        giua = [(a + b) / 2 for a, b in zip(moc, moc[1:]) if b - a >= 1.0]
        theo_canh = len(giua) >= 8
        if theo_canh:
            if len(giua) > 40:
                giua = [giua[int(i * len(giua) / 40)] for i in range(40)]
            F = np.stack([A[min(n - 1, int(t * 2))] for t in giua]).astype(np.float32)
        else:                                               # cắt mềm: khung đổi rõ so với khung chọn trước
            idx = np.linspace(0, n - 1, min(n, 120)).astype(int)
            G = A[idx, H // 5:-H // 5, W // 5:-W // 5].astype(np.float32)
            rep = [0]
            for i in range(1, len(idx)):
                if np.abs(G[i] - G[rep[-1]]).mean() > 18:
                    rep.append(i)
            F = A[idx[rep]].astype(np.float32) if len(rep) >= 12 else None
        if F is not None:
            P = _ben_vung(F)
            h, w = P.shape
            ph, pw = int(h * 0.22), int(w * 0.25)
            vung = {"TL": P[:ph, :pw], "TR": P[:ph, -pw:], "BL": P[-ph:, :pw], "BR": P[-ph:, -pw:]}
            nen = float((P[ph:-ph, pw:-pw] > 0.6).mean()) * 100
            for k, v in vung.items():
                p = float((v > 0.6).mean()) * 100
                if p >= LOGO_TOI_THIEU and p > 3 * nen and (theo_canh or nen <= 0.1):
                    ra.append(k)
    with _KHOA_JSON:
        da = doc_json(cache, {})
        da[vid] = ra
        ghi_json(cache, da)
    return ra


def logo_kenh_gop(paths, vid_goc):
    """16/10 user: gộp khung hình của MỌI khoảng cùng một video gốc rồi mới dò logo kênh.
    Một khoảng 30s ít cảnh quay -> gộp khung của nhiều khoảng (mỗi khoảng ở một đoạn thời gian khác nhau)
    giúp đủ cảnh quay để bộ dò _ben_vung nhận diện chính xác logo đứng yên ở góc."""
    cache = duong_cache("logo_kenh.json")
    da = doc_json(cache, {})
    if vid_goc in da:
        return da[vid_goc]
    W, H = 320, 180
    frames_all = []
    for p in paths:
        if not os.path.isfile(p):
            continue
        try:
            buf = _ffmpeg_khung(p, f"fps=2,scale={W}:{H}", fmt="gray")
            n = len(buf) // (W * H)
            if n > 0:
                A = np.frombuffer(buf, np.uint8, n * W * H).reshape(n, H, W)
                frames_all.append(A)
        except Exception:
            continue
    if not frames_all:
        return []
    A_gop = np.concatenate(frames_all, axis=0) if len(frames_all) > 1 else frames_all[0]
    n_all = len(A_gop)
    ra = []
    if n_all >= 16:
        idx = np.linspace(0, n_all - 1, min(n_all, 150)).astype(int)
        G = A_gop[idx, H // 5:-H // 5, W // 5:-W // 5].astype(np.float32)
        rep = [0]
        for i in range(1, len(idx)):
            if np.abs(G[i] - G[rep[-1]]).mean() > 16:
                rep.append(i)
        F = A_gop[idx[rep]].astype(np.float32) if len(rep) >= 8 else None
        if F is not None:
            P = _ben_vung(F)
            h, w = P.shape
            ph, pw = int(h * 0.22), int(w * 0.25)
            vung = {"TL": P[:ph, :pw], "TR": P[:ph, -pw:], "BL": P[-ph:, :pw], "BR": P[-ph:, -pw:]}
            nen = float((P[ph:-ph, pw:-pw] > 0.6).mean()) * 100
            for k, v in vung.items():
                p = float((v > 0.6).mean()) * 100
                if p >= LOGO_TOI_THIEU and p > 3 * nen and nen <= 0.25:
                    ra.append(k)
    with _KHOA_JSON:
        da = doc_json(cache, {})
        da[vid_goc] = ra
        ghi_json(cache, da)
    return ra



# --------------------------------------------------------------------------- viền đen
def vung_cat(path, bd, dai):
    """Chuỗi 'w:h:x:y' để cắt viền đen quanh hình thật; None nếu không đáng cắt."""
    p = __import__("subprocess").run(
        [FFMPEG, "-ss", f"{max(bd, 0):.2f}", "-t", f"{min(dai, 3):.2f}", "-i", path, "-vf",
         "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"],
        capture_output=True, timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
    m = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", p.stderr.decode("utf-8", "ignore"))
    if not m:
        return None
    cw, ch, cx, cy = map(int, m[-1])
    # kích thước gốc
    d = re.findall(r"Stream.*Video.* (\d{2,5})x(\d{2,5})", p.stderr.decode("utf-8", "ignore"))
    if not d:
        return None
    W, H = int(d[0][0]), int(d[0][1])
    if cw * ch >= 0.97 * W * H or cw * ch < 0.35 * W * H or cw < 64 or ch < 64:
        return None
    return f"{cw}:{ch}:{cx}:{cy}"


# --------------------------------------------------------------------------- điểm cắt của video gốc
def canh_cat(path, vid, nguong=0.32):
    """Danh sách thời điểm (giây) video gốc đổi cảnh — để căn đoạn không lọt mẩu cảnh khác dài <1s."""
    cache = duong_cache("shots.json")
    da = doc_json(cache, {})
    if vid in da:
        return da[vid]
    p = __import__("subprocess").run(
        [FFMPEG, "-i", path, "-an", "-vf", f"select='gt(scene,{nguong})',showinfo", "-f", "null", "-"],
        capture_output=True, timeout=900, creationflags=0x08000000 if os.name == "nt" else 0)
    ts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", p.stderr.decode("utf-8", "ignore"))]
    kq = sorted(set(round(t, 2) for t in ts))
    with _KHOA_JSON:
        da = doc_json(cache, {})
        da[vid] = kq
        ghi_json(cache, da)
    return kq


MIN_MAU = 1.2        # mẩu cảnh ngắn hơn mức này ở đầu/cuối đoạn là "cắt thừa"


def can_cua_so(bd, dai, bien, tong, chat=False):
    """Dịch cửa sổ [bd, bd+dai] sao cho không có mẩu cảnh khác <MIN_MAU ở hai đầu.
    Trả bd mới, hoặc None nếu quanh đó toàn cảnh quá ngắn mà không thể cắt đẹp."""
    bd = max(0.0, min(bd, max(0.0, tong - dai)))
    for _ in range(4):
        trong = [b for b in bien if bd + 0.05 < b < bd + dai - 0.05]
        xau = list(trong) if chat else [b for b in trong if (b - bd) < MIN_MAU or (bd + dai - b) < MIN_MAU]
        if not xau:
            return bd
        b = xau[0]
        sau = [x for x in bien if x > b]
        if (sau[0] if sau else tong) - b >= dai:               # cảnh sau lằn cắt đủ dài -> bắt đầu từ đó
            bd = b + 0.10
            continue
        truoc = [x for x in bien if x < b]
        if b - (truoc[-1] if truoc else 0.0) >= dai:           # cảnh trước lằn cắt đủ dài -> kết thúc ở đó
            bd = max(0.0, b - dai - 0.10)
            continue
        return None
    return None


# --------------------------------------------------------------------------- khung đen ở hai đầu đoạn
_TOI = {}


def dau_cuoi_toi(path, bd, dai, w=64, h=36):
    k = (path, round(bd, 2), round(dai, 2))
    if k not in _TOI:
        _TOI[k] = _dau_cuoi_toi(path, bd, dai, w, h)
    return _TOI[k]


def _dau_cuoi_toi(path, bd, dai, w=64, h=36):
    """True nếu 2-3 khung đầu hoặc cuối của đoạn gần như ĐEN trong khi phần giữa sáng: đó là cảnh mờ
    dần vào/ra đen của video gốc (bộ dò điểm cắt không thấy), nhìn như khung nháy khi ghép."""
    buf = _ffmpeg_khung(path, f"fps=15,scale={w}:{h},format=gray", bd, dai, fmt="gray")
    n = len(buf) // (w * h)
    if n < 6:
        return False
    F = np.frombuffer(buf, np.uint8, n * w * h).reshape(n, w * h).astype(np.float32).mean(1)
    giua = float(np.median(F[2:-2]))
    return giua > 45 and (F[:2].min() < 0.45 * giua or F[-2:].min() < 0.45 * giua)


# --------------------------------------------------------------------------- khái niệm KHÔNG muốn (CLIP)
def vien_phang(path, bd, dai):
    """Viền đen/xám đặc quanh khung nhỏ lọt trong khung: dò bằng độ lệch chuẩn của dải mép; trả 'w:h:x:y' hoặc None."""
    buf = _ffmpeg_khung(path, "scale=320:180,format=gray", bd + min(dai, 2.0) / 2, 0.2, fmt="gray")
    if len(buf) < 320 * 180:
        return None
    g = np.frombuffer(buf, np.uint8, 320 * 180).reshape(180, 320).astype(np.float32)
    mep = lambda a: (float(a.std()) < 7.0)                              # dải mép gần như phẳng
    t = 0
    while t < 80 and mep(g[t:t + 2, :]):
        t += 2
    b = 180
    while b > 100 and mep(g[b - 2:b, :]):
        b -= 2
    l = 0
    while l < 120 and mep(g[:, l:l + 2]):
        l += 2
    r = 320
    while r > 200 and mep(g[:, r - 2:r]):
        r -= 2
    cw, ch = r - l, b - t
    if cw * ch >= 0.95 * 320 * 180 or cw * ch < 0.35 * 320 * 180 or cw < 100 or ch < 60:
        return None
    return f"{cw / 320:.4f}*iw:{ch / 180:.4f}*ih:{l / 320:.4f}*iw:{t / 180:.4f}*ih"


# --------------------------------------------------------------------------- mức chuyển động của đoạn
def chuyen_dong(path, bd, dai, w=64, h=36):
    """Sai khác trung bình giữa các khung liên tiếp (8 khung/giây, thang 0-255): ~1-2 = gần như đứng yên,
    >=5 = có đối tượng/máy quay chuyển động rõ."""
    buf = _ffmpeg_khung(path, f"fps=8,scale={w}:{h},format=gray", bd, dai, fmt="gray")
    n = len(buf) // (w * h)
    if n < 4:
        return 0.0
    F = np.frombuffer(buf, np.uint8, n * w * h).reshape(n, w * h).astype(np.float32)
    return float(np.abs(np.diff(F, axis=0)).mean())



# --------------------------------------------------------------------------- khung hẹp (video dọc / 4:3 trong khung ngang)
HEP_TI_LE = 1.6            # phần hình thật hẹp hơn tỉ lệ rộng/cao này -> loại (16:9 = 1,78; 4:3 = 1,33; dọc = 0,56)
HEP_VIEN_TOI = 28          # cột tối ở MỌI khung (độ sáng < ngưỡng) = viền đen
HEP_DUONG_NOI = 0.7        # đường nối thẳng đứng cắt >= 70% số hàng ở CẢ hai bên đối xứng = video dọc đặt giữa nền mờ
_HEP = {}
_KHOA_HEP = threading.Lock()


def hep_khung(F):
    """F: các khung xám (n, H, W) float32 CÙNG MỘT CẢNH (W ~256) -> True nếu khung hẹp (xem khung_hep)."""
    H, W = F.shape[1], F.shape[2]
    toi = F.max(axis=(0, 1)) < HEP_VIEN_TOI
    if not toi.all():
        aL, aR = int(np.argmin(toi)), int(np.argmin(toi[::-1]))
        if aL >= 0.06 * W and aR >= 0.06 * W and abs(aL - aR) <= 10 * W / 256 and (W - aL - aR) / H < HEP_TI_LE:
            return True
    dx = np.abs(np.diff(F, axis=2))
    frac = (dx > 7).mean(axis=1).mean(axis=0)
    e = dx.mean(axis=(0, 1))
    sc, c = 0.0, 0
    for c_ in range(int(W * .05), int(W * .42)):
        c2 = W - 2 - c_
        s_ = min(float(frac[c_]), float(frac[max(c2 - 3, 0):c2 + 4].max()))
        if s_ > sc:
            sc, c = s_, c_
    if sc >= HEP_DUONG_NOI and (W - 2 * c) / H < HEP_TI_LE and W - 5 - c > c + 3:
        trong = float(e[c + 3:W - 5 - c].mean())
        ngoai = float(np.r_[e[:max(c - 2, 1)], e[W - c:]].mean())
        return ngoai < 0.7 * trong
    return False


def khung_hep(path, bd, dai, W=256, H=144):
    """23/10 user: True nếu đoạn thực chất KHÔNG phải hình ngang đầy khung — (A) viền đen hai bên đối xứng (4:3, dọc)
    hoặc (B) video dọc đặt giữa nền mờ / nền trang trí (hai đường nối thẳng đứng đối xứng, ngoài ít chi tiết hơn trong).
    Đo 23/10 trên 600 mảnh America_DUMPED: A bắt 17/17 đúng, B (ngưỡng 0,7) 10/10 đúng; cảnh tối / hoàng hôn không nhầm."""
    from common import CACHE_CHUNG
    k = f"{os.path.basename(path)}|{os.path.getsize(path) if os.path.isfile(path) else 0}|{bd:.1f}|{dai:.1f}"
    cache = os.path.join(CACHE_CHUNG, "khung_hep.json")
    with _KHOA_HEP:
        if not _HEP:
            _HEP.update(doc_json(cache, {}) or {})
            _HEP.setdefault("", 0)
        if k in _HEP:
            return bool(_HEP[k])
    buf = _ffmpeg_khung(path, f"fps={6 / max(dai, 1):.3f},scale={W}:{H},format=gray", bd, dai, fmt="gray")
    n = len(buf) // (W * H)
    kq = n >= 2 and hep_khung(np.frombuffer(buf, np.uint8, n * W * H).reshape(n, H, W).astype(np.float32))
    with _KHOA_HEP:
        _HEP[k] = int(kq)
        if len(_HEP) % 50 == 0:
            ghi_json(cache, dict(_HEP))
    return kq


def luu_khung_hep():
    from common import CACHE_CHUNG
    with _KHOA_HEP:
        if _HEP:
            ghi_json(os.path.join(CACHE_CHUNG, "khung_hep.json"), dict(_HEP))

def song_song(ham, ds, luong=8):
    """Chạy ham(x) cho mọi x trong ds CÙNG LÚC (việc nặng là ffmpeg/IO nên luồng đủ dùng); trả list theo thứ tự."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(luong) as ex:
        return list(ex.map(ham, ds))
