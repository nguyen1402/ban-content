# -*- coding: utf-8 -*-
"""Chấm ĐỘ KHỚP kết quả tìm với một cảnh bằng SigLIP — KHÔNG tải video:

  * Video YouTube: lấy STORYBOARD (dải khung hình nhỏ YouTube tạo sẵn cho thanh tua, vài trăm KB/video), nhúng từng
    khung, điểm video = trung bình trượt 3 khung cao nhất; kèm giây khớp nhất. Lưu cache theo id video
    (cache/storyboard/<id>.npz) — tìm lại hay chạy tự động sau đều không tải lại.
  * Ảnh: nhúng ảnh thu nhỏ của kết quả tìm.

Điểm SigLIP so400m: khớp rõ thường >= 0,15; dưới NGUONG_THAP coi như lạc đề (giao diện làm mờ)."""
import io
import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from common import CACHE_CHUNG, YT_JS, YTDLP, log

NGUONG_THAP = 0.10
TOI_DA_KHUNG = 240          # video dài: lấy đều tối đa bấy nhiêu khung storyboard
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}


def _lay(url, t=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t).read()


def _khung_storyboard(vid):
    """([giây], [PIL]) và độ dài video, từ storyboard nét nhất."""
    from PIL import Image
    p = subprocess.run([YTDLP, *YT_JS, "-J", "--no-warnings", "https://www.youtube.com/watch?v=" + vid],
                       capture_output=True, timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        j = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
    except ValueError:
        j = {}
    tong = float(j.get("duration") or 0)
    sb = [f for f in j.get("formats") or [] if str(f.get("format_id", "")).startswith("sb") and f.get("fragments")]
    if not sb:
        return [], [], tong
    f = max(sb, key=lambda x: x.get("width") or 0)
    W, H, rr, cc = f["width"], f["height"], f["rows"], f["columns"]
    tam, t0 = [], 0.0
    for fr in f["fragments"]:
        tam.append((t0, fr))
        t0 += fr.get("duration") or 0
    n_to = rr * cc
    buoc = max(1, int(np.ceil(len(tam) * n_to / TOI_DA_KHUNG)))   # lấy 1 khung mỗi `buoc` khung

    def mot(a):
        t0, fr = a
        try:
            im = Image.open(io.BytesIO(_lay(fr["url"]))).convert("RGB")
        except Exception:                                    # noqa: BLE001
            return []
        dt = (fr.get("duration") or 0) / n_to
        o = []
        for k in range(n_to):
            t = t0 + k * dt
            if (tong and t >= tong) or ((k // cc) + 1) * H > im.height:
                break
            o.append((t, im.crop(((k % cc) * W, (k // cc) * H, (k % cc + 1) * W, (k // cc + 1) * H))))
        return o

    ra = []
    with ThreadPoolExecutor(6) as ex:
        for o in ex.map(mot, tam):
            ra += o
    ra = ra[::buoc] if buoc > 1 else ra
    return [t for t, _ in ra], [im for _, im in ra], tong


def storyboard(vid):
    """(t, e, tong): mốc giây + vector SigLIP các khung storyboard của video YouTube (có cache)."""
    import nhung_siglip
    thu = os.path.join(CACHE_CHUNG, "storyboard_" + nhung_siglip._NGAN)    # noqa: SLF001  (dùng chung mọi dự án)
    os.makedirs(thu, exist_ok=True)
    npz = os.path.join(thu, vid + ".npz")
    if os.path.isfile(npz):
        d = np.load(npz)
        return d["t"], d["e"], float(d["tong"])
    t, ims, tong = _khung_storyboard(vid)
    try:                                                     # 23/10: soát sạch luôn trên khung vừa tải (khỏi tải lại)
        soat_sach(vid, ims)
    except Exception as ex:                                  # noqa: BLE001
        log(f"    ! soát sạch {vid}: {str(ex)[:80]}")
    e = nhung_siglip.nhung_anh(ims) if ims else np.zeros((0, 1), np.float32)
    t = np.asarray(t, np.float32)
    if len(t) or tong:
        np.savez(npz, t=t, e=e, tong=tong)
    return t, e, tong


def diem_khung(e, t, qv):
    """(điểm, giây khớp nhất) — trung bình trượt 3 khung cao nhất."""
    if len(t) < 1:
        return -1.0, 0.0
    s = e @ qv
    k = min(3, len(s))
    cs = np.convolve(s, np.ones(k) / k, mode="valid")
    i = int(np.argmax(cs))
    j = i + int(np.argmax(s[i:i + k]))
    return float(cs[i]), float(t[j])


def diem_video(ids, qv, luong=6):
    """{id: {diem, t}} cho danh sách id YouTube."""
    def mot(v):
        try:
            t, e, _ = storyboard(v)
            d, giay = diem_khung(e, t, qv)
            return v, {"diem": round(d, 4), "t": round(giay, 1)}
        except Exception as ex:                              # noqa: BLE001
            log(f"    ! storyboard {v}: {str(ex)[:80]}")
            return v, {"diem": -1, "t": 0}
    with ThreadPoolExecutor(luong) as ex:
        return dict(ex.map(mot, ids))


def diem_anh(urls, qv, luong=8, chu=False):
    """[điểm] cho danh sách URL ảnh (thường là ảnh thu nhỏ); ảnh không tải được = -1.
    chu=True: trả thêm [có chữ] (dò chữ trên ảnh thu nhỏ, tính cả góc — user: ảnh bắt buộc không có chữ)."""
    from PIL import Image
    import nhung_siglip

    def mot(u):
        try:
            return Image.open(io.BytesIO(_lay(u, 15))).convert("RGB")
        except Exception:                                    # noqa: BLE001
            return None
    with ThreadPoolExecutor(luong) as ex:
        ims = list(ex.map(mot, urls))
    co = [i for i, im in enumerate(ims) if im is not None]
    ra = [-1.0] * len(urls)
    if co:
        e = nhung_siglip.nhung_anh([ims[i] for i in co])
        for i, d in zip(co, e @ qv):
            ra[i] = round(float(d), 4)
    if not chu:
        return ra
    import loc_chu
    co_chu = [None] * len(urls)
    for i in co:
        try:
            im = ims[i]
            im.thumbnail((loc_chu.W, loc_chu.W))
            co_chu[i] = bool(loc_chu.dien_tich_chu(np.asarray(im), bo_goc=False) > loc_chu.NGUONG_DIEN_TICH)
        except Exception:                                    # noqa: BLE001
            pass
    return ra, co_chu


def nhung_url(urls, luong=16, bao=None, cho=8):
    """(chỉ số tải được, ma trận vector SigLIP) cho danh sách URL ảnh (ảnh thu nhỏ của kết quả tìm).
    13/10 (đo: 3.022 ảnh, 4 luồng, chờ 15 s, không cache -> kẹt hàng chục phút khi mạng chập chờn): 16 luồng, chờ tối
    đa `cho` s mỗi ảnh, CACHE vector theo URL ở cache/vec_url_<model>/ (chạy lại không tải lại), báo tiến độ qua
    bao(xong, tong) mỗi lô."""
    import hashlib
    import nhung_siglip
    from PIL import Image
    thu = os.path.join(CACHE_CHUNG, "vec_url_" + nhung_siglip.MO_HINH.split("/")[-1])
    os.makedirs(thu, exist_ok=True)

    def tep(u):
        return os.path.join(thu, hashlib.md5(u.encode("utf-8")).hexdigest() + ".npy")
    vec = [None] * len(urls)
    for k, u in enumerate(urls):
        f = tep(u)
        if os.path.isfile(f):
            try:
                vec[k] = np.load(f)
            except Exception:                                # noqa: BLE001
                pass
    can = [k for k in range(len(urls)) if vec[k] is None]

    def mot(u):
        try:
            return Image.open(io.BytesIO(_lay(u, cho))).convert("RGB")
        except Exception:                                    # noqa: BLE001
            return None
    xong = len(urls) - len(can)
    if bao:
        bao(xong, len(urls))
    LO = 256
    with ThreadPoolExecutor(luong) as ex:
        for a in range(0, len(can), LO):
            lo = can[a:a + LO]
            ims = list(ex.map(mot, [urls[k] for k in lo]))
            co_lo = [(k, im) for k, im in zip(lo, ims) if im is not None]
            if co_lo:
                E = nhung_siglip.nhung_anh([im for _, im in co_lo])
                for (k, _), v in zip(co_lo, E):
                    vec[k] = v
                    np.save(tep(urls[k]), v)
            xong += len(lo)
            if bao:
                bao(xong, len(urls))
    co = [k for k in range(len(urls)) if vec[k] is not None]
    return co, (np.stack([vec[k] for k in co]) if co else np.zeros((0, 1), np.float32))


def vec_canh(canh=None, q=""):
    """Vector truy vấn: theo cảnh (câu 'nên chiếu' + từ khoá video) nếu có, không thì theo chính từ khoá tìm."""
    import nhung_siglip
    if canh and canh.get("canh_en"):                         # 12/10: mô tả khung hình tiếng Anh (mo_ta_canh.py)
        return nhung_siglip.vec_mo_ta(canh["canh_en"][0], canh["canh_en"][1:])
    if canh:
        return nhung_siglip.vec_mo_ta(canh.get("noi_dung") or canh.get("text", ""), (canh.get("video") or [])[:2])
    return nhung_siglip.nhung_chu([q])[0]


# --------------------------------------------------------------------------- soát SẠCH trước khi tải (23/10 user)
# "lọc ngay trước khi tải về, tối ưu tránh dư thừa; logo và chữ bé chấp nhận được": soát trên chính các khung storyboard
# (không tải video), kết quả cache theo id video dùng chung mọi dự án.
SOAT_KHUNG = 24             # số khung storyboard đem soát chữ / mặt (rải đều)
CHU_TO_CAO = 0.11           # hộp chữ OCR cao >= 11% chiều cao khung (đo trên storyboard phóng 640x360) = chữ TO; đo 23/10:
#                             "Courtesy of MTA", phụ đề nhỏ ~0,07-0,09 -> chữ bé, kệ (user: "logo và chữ bé chấp nhận được")
CHU_TO_TI_LE = 0.25         # chữ to nằm CÙNG MỘT DẢI NGANG ở >= 25% khung -> chữ CHÈN (phụ đề to, chữ chìm to, tiêu đề)
#                             -> bỏ; chữ to trong cảnh (container, biển số) đổi chỗ liên tục nên không gom được một dải
MAT_TO_RONG = 0.15          # mặt người rộng >= 15% bề ngang khung = người nói trước camera
MAT_TO_TI_LE = 0.40         # >= 40% khung có mặt to -> bỏ (vlog, podcast, phỏng vấn, người dẫn)
HEP_TI_LE_BO = 0.50         # >= 50% nhóm khung là khung hẹp (dọc / 4:3 viền đen / nền mờ) -> bỏ
_SOAT = {}
_KHOA_SOAT = __import__("threading").Lock()
_YN = __import__("threading").local()


def _mat(im):
    import cv2
    if not hasattr(_YN, "d"):
        buf = np.fromfile(os.path.join(CACHE_CHUNG, "model_mat", "face_detection_yunet_2023mar.onnx"), np.uint8)
        _YN.d = cv2.FaceDetectorYN.create("onnx", buf, np.zeros(0, np.uint8), (320, 180), 0.8)   # đường dẫn có dấu: nạp bộ nhớ
    a = cv2.cvtColor(np.asarray(im.convert("RGB").resize((320, 180))), cv2.COLOR_RGB2BGR)
    _YN.d.setInputSize((320, 180))
    _, f = _YN.d.detect(a)
    return 0.0 if f is None else float(max(x[2] for x in f)) / 320


def _dai_chu_to(im):
    """Các dải ngang (0..9 theo chiều cao) có chữ TO trong khung."""
    import sach_hinh
    r = sach_hinh._ocr()(np.asarray(im.convert("RGB").resize((640, 360))))   # noqa: SLF001
    ra = set()
    for b, t, sc in zip(r.boxes if r.boxes is not None else [], r.txts or [], r.scores or []):
        if float(sc) >= 0.8 and len("".join(ch for ch in t if ch.isalnum())) >= 3:
            b = np.asarray(b)
            if float(np.ptp(b[:, 1])) / 360 >= CHU_TO_CAO:
                ra.add(min(9, int(float(b[:, 1].mean()) / 36)))
    return ra


def _soat_anh(ims):
    """Các khung PIL storyboard -> {hep, chu, mat, bo}."""
    import sach_hinh
    ra = {"hep": 0.0, "chu": 0.0, "mat": 0.0}
    if not ims:
        return ra
    F = np.stack([np.asarray(im.convert("L").resize((256, 144)), np.float32) for im in ims])
    nhom = [F[i:i + 8] for i in range(0, len(F) - 1, 8) if len(F[i:i + 8]) >= 2]
    ra["hep"] = round(float(np.mean([sach_hinh.hep_khung(g) for g in nhom])) if nhom else 0.0, 3)
    chon = [ims[int(i)] for i in np.linspace(0, len(ims) - 1, min(SOAT_KHUNG, len(ims)))]
    ra["mat"] = round(float(np.mean([_mat(im) >= MAT_TO_RONG for im in chon])), 3)
    if not sach_hinh.tat_ocr():
        from collections import Counter
        dem = Counter(y for im in chon for y in _dai_chu_to(im))
        ra["chu"] = round(max(dem.values()) / len(chon), 3) if dem else 0.0
    return ra


def _ly_do(kq):
    """Lý do bỏ theo NGƯỠNG HIỆN TẠI (cache chỉ giữ tỉ lệ đo được -> đổi ngưỡng không phải đo lại)."""
    if kq.get("hep", 0) >= HEP_TI_LE_BO:
        return "khung hẹp (dọc / viền đen)"
    if kq.get("chu", 0) >= CHU_TO_TI_LE:
        return "chữ to / phụ đề to"
    if kq.get("mat", 0) >= MAT_TO_TI_LE:
        return "người nói trước camera"
    return ""


def soat_sach(vid, ims=None):
    """{hep, chu, mat, bo} của video YouTube — bo != '' là nên BỎ trước khi tải. Cache cache/soat_sb.json."""
    p = os.path.join(CACHE_CHUNG, "soat_sb.json")
    with _KHOA_SOAT:
        if not _SOAT:
            try:
                _SOAT.update(json.load(open(p, encoding="utf-8")))
            except (OSError, ValueError):
                _SOAT[""] = {}
        if vid in _SOAT:
            return dict(_SOAT[vid], bo=_ly_do(_SOAT[vid]))
    if ims is None:
        _, ims, _ = _khung_storyboard(vid)
    kq = _soat_anh(ims)
    with _KHOA_SOAT:
        _SOAT[vid] = kq
        tam = p + ".tmp"
        json.dump(_SOAT, open(tam, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tam, p)
    return dict(kq, bo=_ly_do(kq))
