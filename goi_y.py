# -*- coding: utf-8 -*-
"""GỢI Ý TỰ ĐỘNG cho trình dựng tay: điền sẵn các đoạn hình lên thanh thời gian của cảnh, lấy từ KHO DỰ ÁN
(video/ảnh người dùng đã chọn tải) — người dùng xem, kéo sửa rồi mới xác nhận cắt.

Cách chấm: SigLIP (mặc định; CLIP cũ) so câu "nên chiếu" + từ khoá của cảnh với khung hình (1 khung/1,5 giây) của từng
video trong kho; cửa sổ đúng độ dài đoạn có điểm trung bình cao nhất thắng. Đoạn không chứa điểm đổi cảnh
của video gốc (căn theo ranh cảnh), bỏ đoạn có khung đen ở hai đầu, tránh lặp lại cùng một đoạn hình đã gợi ý."""
import os
import threading
import time

import numpy as np

from common import log

DOAN_TOI_DA = 4.0           # 12/10: video mẫu user đưa cắt trung vị 2,5 s (10%: 1,4 s; 90%: 5,2 s) -> chia 1,5-4 s
DOAN_TOI_THIEU = 1.0
DOAN_MUC_TIEU = 2.6         # cửa sổ dò chỗ khớp; độ dài đoạn thật theo cảnh quay của nguồn:
SHOT_MIN, SHOT_MAX = 0.8, 5.5   # video mẫu: linh hoạt 0.8s - 5.5s theo đúng nhịp thở giọng đọc
VIDEO_DU_TOT = 0.05          # đoạn video khớp từ mức này (điểm gốc SigLIP) thì không thay bằng ảnh (0,12 khi chấm câu tiếng Việt; câu mô tả tiếng Anh thang thấp hơn — đo 12/10)
GIONG_TOI_DA = 0.92         # 12/10 user: đoạn kế tiếp không được "gần như giống" đoạn trước (cosine khung SigLIP)
THUONG_SACH = 0.02          # 12/10: video stock sạch (Pexels/Pixabay, không logo) gần bằng điểm thì thắng YouTube
THUONG_GAN = 0.015          # video đang dùng ở 2 cảnh liền trước được cộng điểm: hình liền mạch, không nhảy chủ đề
THUONG_ANH = 0.03           # ảnh phải hơn video bấy nhiêu điểm mới được chọn (video động thường dễ xem hơn)
MO_HINH_MAC_DINH = "siglip"   # 11/10: user so 2 bản nháp, SigLIP 2 chọn đúng hơn CLIP -> mặc định
TT = {}                      # dự án -> trạng thái chạy nền {dang, xong, tong, loi}
_KHOA = threading.Lock()


# 14/10 user: "video dùng lại nhiều lần mà cách sát nhau" (đo chuot_newyor: 87 video cho 287 đoạn, 121 lần cùng video
# trong vòng 30 s, có chỗ cách 3 s) -> giãn cách + giới hạn lượt; hết video mới thì ẢNH (Gemini vẽ riêng chỗ đó) lấp.
CACH_LAP = 60.0             # cùng một video / ảnh cách nhau ít nhất bấy nhiêu giây trên timeline
CACH_LAP_LUI = 25.0         # hết video mới VÀ không có ảnh lấp: nới còn bấy nhiêu (vẫn không sát nhau)
LUOT_TOI_DA = 3             # mỗi video dùng tối đa 3 lần cả bài...
GIAY_MOI_LUOT = 10.0        # ...và 1 lần cho mỗi 10 s độ dài của nó (clip 26 s -> 2 lần)
LUOT_ANH = 2                # ảnh thường dùng tối đa 2 lần; ảnh Gemini vẽ riêng cho một cảnh (cho_canh) chỉ 1 lần
KHOP_KEM = 0.05             # 15/10 user chọn 0,05 (Flow 0 điểm); 14/10 user (tàu Anh cập cảng 1770 -> clip "đường phố, xe hơi"): video tốt nhất dưới mức này
#                             (điểm gốc SigLIP theo mô tả khung hình; đo chuot_newyor: 37/269 đoạn) -> chỗ THIẾU, Gemini vẽ
DIA_DANH_DAU = False        # 14/10 user: KHÔNG ép ảnh địa danh lên đầu cảnh địa điểm (Google trả hồ Lake George cho
#                             "New York City") — ảnh địa danh chấm như mọi ảnh khác

BO_YOUTUBE_TU_DONG = False  # 12/10 user bỏ video YouTube máy tự tải (logo kênh); 15/10 user dùng lại (Google Videos)


def _chi_muc(kho, mo_hinh=None):
    """[(id, t, e, file, bien, tong, xau)] cho mọi video đã tải xong trong kho (chỉ mục CLIP + điểm đổi cảnh, có cache)."""
    mo_hinh = mo_hinh or MO_HINH_MAC_DINH
    import chon_doan
    import sach_hinh
    ra = []
    for kid, m in kho.items():
        if m.get("loai") != "video" or m.get("trang_thai") != "xong" or not os.path.isfile(m.get("file", "")):
            continue
        if BO_YOUTUBE_TU_DONG and not m.get("sach") and not m.get("tay"):
            continue
        if m.get("bo_yt") and not m.get("tay"):              # 16/10: YouTube có logo kênh / phụ đề to -> bỏ (trừ khi người dùng tự chọn)
            continue
        try:
            if mo_hinh == "siglip":
                import nhung_siglip
                t, e = nhung_siglip.chi_muc_video("tay_" + kid, m["file"])
            else:
                t, e = chon_doan.chi_muc_video({"id": "tay_" + kid, "file": m["file"], "dai": m.get("dai", 0)})
        except Exception as ex:                             # noqa: BLE001
            log(f"    ! chỉ mục hỏng {kid}: {ex}")
            continue
        if len(t) < 2:
            continue
        import loc_minh_hoa                                  # 12/10: bỏ hoạt hình/slide + khúc đứng hình (trừ khi người dùng tự chọn)
        xau, ti_hh = loc_minh_hoa.khung_xau("tay_" + kid, m["file"], np.asarray(e), chon_doan.BUOC_GIAY)
        if not m.get("tay") and ti_hh > loc_minh_hoa.TI_LE_BO_VIDEO:
            log(f"    bỏ video thuyết trình/hoạt hình {kid} ({ti_hh * 100:.0f}% khung là hình vẽ)")
            continue
        if not m.get("sach") and not m.get("tay") and m.get("chu_yt") is not None:
            try:                                             # 16/10: khung có chữ (phụ đề, tiêu đề) của video YouTube: không lấy
                import loc_chu
                s_chu = loc_chu.chu_video("tay_" + kid, m["file"], chon_doan.BUOC_GIAY)
                n_ = min(len(xau), len(s_chu))
                xau = np.asarray(xau).copy()
                xau[:n_] |= s_chu[:n_] > loc_chu.NGUONG_DIEN_TICH
            except Exception:                                # noqa: BLE001
                pass
        bien = sach_hinh.canh_cat(m["file"], "tay_" + kid)
        tong = float(t[-1]) + chon_doan.BUOC_GIAY
        if float(m.get("dai") or 0) > 0:                     # độ dài THẬT của file: chỉ mục ước dư -> đoạn chạm cuối bị cắt,
            tong = min(tong, float(m["dai"]) - 0.15)         # hở vài phần mười giây đen trên timeline (lỗi đo 12/10)
        ra.append((kid, np.asarray(t), np.asarray(e), m["file"], bien, tong, xau))
    return ra


def _ngang(m):
    """14/10 user: chỉ dùng hình NGANG (rộng >= 1,2 x cao). Đọc cỡ từ kho; thiếu thì đo file."""
    w, h = m.get("rong") or 0, m.get("cao") or 0
    f = m.get("file", "")
    if not (w and h) and os.path.isfile(f):
        try:
            if m.get("loai") == "anh":
                from PIL import Image
                w, h = Image.open(f).size
            else:
                import dung_tay
                w, h = dung_tay._kich_thuoc(f)               # noqa: SLF001
        except Exception:                                   # noqa: BLE001
            return True
    return not (w and h) or w >= 1.2 * h


def _anh(kho, mo_hinh=None):
    """[(id, vector, dia_danh)] cho mọi ảnh trong kho (nhúng, lưu cạnh file). dia_danh: ảnh tìm theo tên địa danh."""
    mo_hinh = mo_hinh or MO_HINH_MAC_DINH
    import chon_doan
    from PIL import Image
    ra = []
    for kid, m in kho.items():
        f = m.get("file", "")
        if m.get("loai") != "anh" or m.get("trang_thai") != "xong" or not os.path.isfile(f):
            continue
        try:
            import loc_chu
            if loc_chu.co_chu_anh(f):                        # 11/10 user: ẢNH bắt buộc không có chữ (video thì được)
                continue
            import loc_minh_hoa
            if loc_minh_hoa.la_hoat_hinh_anh(f):             # 12/10 user: ảnh phải là ảnh thật (bản đồ được)
                continue
        except Exception:                                   # noqa: BLE001
            pass
        npy = f + ".l14.npy"
        try:
            if mo_hinh == "siglip":
                import nhung_siglip
                ra.append((kid, nhung_siglip.vec_anh_file(f), (m.get("dia_danh") or "").lower()))
                continue
            if os.path.isfile(npy):
                v = np.load(npy)
            else:
                v = chon_doan.nhung_anh([Image.open(f).convert("RGB")])[0]
                np.save(npy, v)
            ra.append((kid, v, (m.get("dia_danh") or "").lower()))
        except Exception:                                   # noqa: BLE001
            continue
    return ra


NGHI_TOI_THIEU = 0.25       # 12/10 user: mỗi chỗ NGẮT NGHỈ của giọng đọc (lặng >= 0,25 s) là một lần đổi cảnh


def cho_nghi(du_an):
    """Giây (tuyệt đối) giữa các khoảng lặng >= NGHI_TOI_THIEU trong giong_doc.wav — chỗ ngắt nghỉ câu/vế câu.
    Đo 12/10: th_nghi_m_2 có 355 chỗ (200 câu, 262 dấu phẩy). Cache ra/<dự án>/nghi.json theo mtime file giọng."""
    import re
    import subprocess
    from common import FFMPEG, doc_json, ghi_json, thu_muc_du_an
    out = thu_muc_du_an(du_an)[1]
    wav = os.path.join(out, "giong_doc.wav")
    if not os.path.isfile(wav):
        return []
    cache = os.path.join(out, "nghi.json")
    da = doc_json(cache, {}) or {}
    if da.get("mtime") == os.path.getmtime(wav) and da.get("nguong") == NGHI_TOI_THIEU:
        return da["ds"]
    p = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", wav, "-af",
                        f"silencedetect=noise=-38dB:d={NGHI_TOI_THIEU}", "-f", "null", "-"],
                       capture_output=True, timeout=600, creationflags=0x08000000 if os.name == "nt" else 0)
    err = p.stderr.decode("utf-8", "ignore")
    ds = [round(float(e) - float(d) / 2, 2) for e, d in
          re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", err)]
    ghi_json(cache, {"mtime": os.path.getmtime(wav), "nguong": NGHI_TOI_THIEU, "ds": ds})
    return ds


NGHI_GIONG_DOC = True        # 16/10 user: chuyển hẳn sang băm theo ngắt nghỉ thật của giọng đọc (Acoustic Silence)
LANG_GIONG = 0.15            # chỗ lặng ngắt nghỉ câu/vế câu trong giọng đọc (>= 0.15s)
DOAN_MIN_NGHI = 0.8          # tối thiểu 0.8s cho nhịp mở đầu/ngắt câu (bắt trọn mọi chỗ lấy hơi thực tế)
DOAN_MAX_NGHI = 5.5          # tối đa 5.5s đổi cảnh (tránh đứng hình quá lâu)

CAT_DAU_CAU = False         # Tắt băm dấu phẩy/chấm văn bản; chuyển hoàn toàn sang ngắt nghỉ giọng đọc thật
CUM_TOI_THIEU = 1.0         # vế ngắn hơn bấy nhiêu giây gộp với vế kế bên (hình không nháy liên tục)
CUM_TOI_DA = 7.0            # vế dài hơn: cắt thêm ở chỗ lặng gần giữa vế nhất (không có thì chia đôi)
LANG_NGAN = 0.12            # chỗ lặng ngắn nhất tính là ngắt ở dấu câu
CUA_BAT = 1.2               # mốc dấu câu ước theo tỉ lệ ký tự -> bắt vào chỗ lặng thật trong ±bấy nhiêu giây


def _lang(du_an, d):
    """[(giây giữa chỗ lặng, độ dài lặng)] trong giong_doc.wav với ngưỡng lặng d (cache theo mtime)."""
    import re
    import subprocess
    from common import FFMPEG, doc_json, ghi_json, thu_muc_du_an
    out = thu_muc_du_an(du_an)[1]
    wav = os.path.join(out, "giong_doc.wav")
    if not os.path.isfile(wav):
        return []
    cache = os.path.join(out, "lang.json")
    da = doc_json(cache, {}) or {}
    if da.get("mtime") == os.path.getmtime(wav) and str(d) in da.get("ds", {}):
        return [tuple(x) for x in da["ds"][str(d)]]
    pr = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", wav, "-af", f"silencedetect=noise=-35dB:d={d}",
                         "-f", "null", "-"], capture_output=True, timeout=600, creationflags=0x08000000 if os.name == "nt" else 0)
    ds = [(round(float(e) - float(x) / 2, 3), round(float(x), 3)) for e, x in
          re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", pr.stderr.decode("utf-8", "ignore"))]
    if da.get("mtime") != os.path.getmtime(wav):
        da = {"mtime": os.path.getmtime(wav), "ds": {}}
    da["ds"][str(d)] = ds
    ghi_json(cache, da)
    return ds


def cho_dau_cau(du_an, c, lang=None):
    """16/10 user: điểm chuyển hình TRONG cảnh c (giây tính từ đầu cảnh) = chỗ DẤU CÂU (, ; : . ! ? …) của lời đọc.
    Mốc mỗi dấu câu ước theo tỉ lệ ký tự trong cảnh rồi bắt vào chỗ lặng thật gần nhất (theo thứ tự, mỗi chỗ lặng
    một lần; lặng dài được ưu tiên). Đo 16/10: chuot_newyor 226/242 dấu câu bắt được chỗ lặng, fish 106/108; mọi
    mốc dấu chấm trùng ranh câu thật (32/32). Vế < CUM_TOI_THIEU gộp vế kế bên; vế > CUM_TOI_DA cắt thêm ở chỗ lặng
    gần giữa nhất."""
    import re
    lang = _lang(du_an, LANG_NGAN) if lang is None else lang
    t, a, L = c.get("text") or "", float(c.get("bat_dau") or 0), float(c["dai"]) - float(c.get("nghi_sau") or 0)
    trong = [(x - a, d) for x, d in lang if a + 0.3 < x < a + L - 0.3]
    moc, j = [], 0
    for m in re.finditer(r"[,;:.!?…]+(?=\s)", t):
        u = L * (m.start() + 1) / max(len(t), 1)
        tot = None
        for i in range(j, len(trong)):
            x, d = trong[i]
            if x > u + CUA_BAT:
                break
            if abs(x - u) <= CUA_BAT and (tot is None or abs(x - u) - 0.3 * d < abs(trong[tot][0] - u) - 0.3 * trong[tot][1]):
                tot = i
        if tot is not None:
            moc.append(trong[tot][0])
            j = tot + 1
    # gộp vế quá ngắn: bỏ mốc làm vế trước (hoặc vế cuối) ngắn hơn CUM_TOI_THIEU
    gon = []
    for x in moc:
        if x - (gon[-1] if gon else 0.0) >= CUM_TOI_THIEU:
            gon.append(x)
    while gon and L - gon[-1] < CUM_TOI_THIEU:
        gon.pop()
    # vế quá dài: cắt thêm ở chỗ lặng gần giữa vế (đủ xa hai đầu), không có thì chia đều
    ra, truoc = [], 0.0
    for x in gon + [L]:
        while x - truoc > CUM_TOI_DA:
            n = int(-(-(x - truoc) // CUM_TOI_DA))
            muc = truoc + (x - truoc) / n
            hop = [y for y, _ in trong if truoc + CUM_TOI_THIEU <= y <= x - CUM_TOI_THIEU and y - truoc <= CUM_TOI_DA]
            y = min(hop, key=lambda v: abs(v - muc)) if hop else muc
            ra.append(round(y, 2))
            truoc = y
        if x < L:
            ra.append(round(x, 2))
        truoc = x
    return ra


def cho_nghi_giong_doc(du_an, c, lang=None):
    """Điểm chuyển hình TRONG cảnh c (giây tính từ đầu cảnh) = CHỖ NGẮT NGHỈ THẬT CỦA GIỌNG ĐỌC trong giong_doc.wav.
    Bỏ qua hoàn toàn dấu chấm, dấu phẩy ngữ pháp của văn bản.
    Bắt trọn mọi chỗ lấy hơi / ngắt nghỉ tự nhiên:
    - Lặng rõ (>= 0.20s): chỉ cần cách điểm trước >= 0.8s và cách đuôi >= 0.7s (bắt trọn các cụm mở đầu ngắn như 'Từ sông Murray,', 'Ba trăm triệu con,').
    - Lặng nhẹ (0.15s - 0.20s): cần cách điểm trước >= 1.4s và cách đuôi >= 1.0s.
    - Chống đứng hình: câu quá dài (> 5.5s không nghỉ) tự chèn góc máy mới."""
    lang = _lang(du_an, LANG_GIONG) if lang is None else lang
    a, L = float(c.get("bat_dau") or 0), float(c["dai"]) - float(c.get("nghi_sau") or 0)
    if L < 1.2:
        return []

    # Các khoảng lặng thật sự nằm bên trong cảnh
    trong = [(round(x - a, 2), round(d, 2)) for x, d in lang if a + 0.4 < x < a + L - 0.4]

    mocs = []
    truoc = 0.0
    for x, d in trong:
        min_cach = 0.8 if d >= 0.20 else 1.4
        min_duoi = 0.7 if d >= 0.20 else 1.0
        if x - truoc >= min_cach and L - x >= min_duoi:
            mocs.append(x)
            truoc = x

    # Nếu có khoảng nào quá dài (> DOAN_MAX_NGHI), chèn thêm điểm cắt ở chỗ lặng nhỏ hoặc chia đều
    ra = []
    truoc = 0.0
    for m in mocs + [L]:
        while m - truoc > DOAN_MAX_NGHI:
            hop = [x for x, _ in trong if truoc + 1.2 <= x <= m - 1.2 and x - truoc <= DOAN_MAX_NGHI]
            if hop:
                mid = truoc + (m - truoc) / 2
                chon_x = min(hop, key=lambda v: abs(v - mid))
            else:
                chon_x = round(truoc + (m - truoc) / 2, 2)
            ra.append(chon_x)
            truoc = chon_x
        if m < L:
            ra.append(m)
            truoc = m
    return sorted(list(set(ra)))


def _chia(dai):
    """Chia cảnh thành n đoạn đều nhau, mỗi đoạn trong [DOAN_TOI_THIEU, DOAN_TOI_DA] khi có thể."""
    n = max(1, int(round(dai / DOAN_MUC_TIEU)), int(np.ceil(dai / DOAN_TOI_DA)))
    while n > 1 and dai / n < DOAN_TOI_THIEU:
        n -= 1
    d = dai / n
    return [(round(i * d, 2), round(d if i < n - 1 else dai - i * d, 2)) for i in range(n)]


def goi_y_canh(canh, vids, anhs, da_dung, mo_hinh=None, gan=(), sach=(), truoc=None, nghi=(), lan=None, t0=0.0,
               thieu=None, rieng=None, cd_id=None, kid_to_cd=None):
    """Giai đoạn 5: Danh sách đoạn gợi ý cho một cảnh.
    - Nguồn được dùng: ưu tiên video thuộc chủ đề của cảnh đó (cd_id).
    - Chuyển hình: ở dấu phẩy, dấu chấm (cho_dau_cau).
    - Chọn clip: trong kho của chủ đề, chấm theo từng vế câu và lấy clip hợp nhất.
    - Bỏ ngưỡng 'khớp kém': miễn là clip thuộc chủ đề thì được dùng (luôn lấp đầy).
    - Luật không lặp: cùng một clip cách nhau ít nhất 60s, mỗi video dùng tối đa 3 lần.
    - Fallback khi kho chủ đề hết:
        1. Clip của chủ đề liền trước hoặc liền sau (cách >= 60s).
        2. Dùng lại clip của chính chủ đề, nới khoảng cách còn 25s.
        3. Ảnh thật tìm trên Google.
        4. Không dùng ảnh AI vẽ."""
    truoc = truoc if truoc is not None else {}
    lan = lan if lan is not None else {}                    # kho_id -> [giây TUYỆT ĐỐI trên timeline đã dùng]
    rieng = rieng or {}                                     # ảnh riêng cho cảnh
    kid_to_cd = kid_to_cd or {}

    def con_cho(kid, tong, cach, cap):
        """Video còn được dùng ở giờ hiện tại? (giãn cách `cach` s; trần cứng tối đa 2 lần/clip)"""
        ts = lan.get(kid, [])
        if cach and any(abs(t0 + pos - x) < cach for x in ts):
            return False
        # TRẦN CỨNG CHỐNG LẶP: Chế độ chuẩn (Step 1, Step 2) tối đa 2 lần/clip
        if cap and len(ts) >= 2:
            return False
        return True


    def con_cho_anh(kid):
        if rieng.get(kid) not in (None, canh["id"]):
            return False
        ts = lan.get(kid, [])
        return len(ts) < (1 if rieng.get(kid) is not None else LUOT_ANH) and not any(abs(t0 + pos - x) < CACH_LAP for x in ts)

    nghi = sorted(x for x in nghi if 0.35 < x < float(canh["dai"]) - float(canh.get("nghi_sau") or 0) - 0.35)
    mo_hinh = mo_hinh or MO_HINH_MAC_DINH
    import chon_doan
    import sach_hinh
    q = [s for s in (canh.get("video") or [])[:2]]
    if mo_hinh == "siglip" and canh.get("canh_en"):
        import nhung_siglip
        qv = nhung_siglip.vec_mo_ta(canh["canh_en"][0], canh["canh_en"][1:])
    elif mo_hinh == "siglip":
        import nhung_siglip
        qv = nhung_siglip.vec_mo_ta(canh.get("noi_dung") or canh.get("text", ""), q)
    else:
        qv = chon_doan._vec(canh.get("noi_dung") or (q[0] if q else canh.get("text", "")), q)   # noqa: SLF001

    doan = []
    BG = chon_doan.BUOC_GIAY
    cs_n = max(1, int(round(DOAN_MUC_TIEU / BG)))
    S = [(kid, t, e @ qv, f, bien, tong, xau) for kid, t, e, f, bien, tong, xau in vids]
    E_ = {kid: e for kid, t, e, f, bien, tong, xau in vids}

    # Phân nhóm video theo chủ đề
    if cd_id is not None:
        S_chinh = [it for it in S if kid_to_cd.get(it[0]) == cd_id]
        S_ke = [it for it in S if kid_to_cd.get(it[0]) in (cd_id - 1, cd_id + 1)]
    else:
        S_chinh = S
        S_ke = []

    L = float(canh["dai"])
    pos = 0.0
    while L - pos > 0.05:
        rem = round(L - pos, 2)
        bd = round(pos, 2)
        toi_nghi = next((x for x in nghi if x > pos + 0.3), None)
        if toi_nghi is not None:
            rem = round(toi_nghi - pos, 2)

        def do_dai(vao, bien, tong, rem=rem, chat=False):
            if chat:
                return round(rem, 2) if tong - vao >= rem + 0.05 else None
            con = next((b for b in bien if b > vao + 0.05), tong) - vao - 0.05
            d = min(con, SHOT_MAX, rem)
            if 0 < rem - d < SHOT_MIN:
                if con >= rem and rem <= SHOT_MAX + 1.0:
                    d = rem
                elif rem - SHOT_MIN >= SHOT_MIN:
                    d = rem - SHOT_MIN
            return round(d, 2) if d >= min(SHOT_MIN, rem) - 0.01 else None

        def tim_pool(pool, tranh_lap, cach=CACH_LAP, cap=True, chat=False):
            cand = []
            for kid, t, s, f, bien, tong, xau in pool:
                if len(s) < cs_n:
                    continue
                if kid == truoc.get("kid"):
                    continue
                if not con_cho(kid, tong, cach, cap):
                    continue
                cs = np.convolve(s, np.ones(cs_n) / cs_n, mode="valid")
                for i in np.argsort(-cs)[:20]:
                    vao = float(t[i])
                    cat_truoc = [b for b in bien if b <= vao]
                    if cat_truoc and vao - cat_truoc[-1] < 0.8:
                        vao = cat_truoc[-1] + 0.1
                    dai = do_dai(vao, bien, tong, chat=chat)
                    if not dai or vao + dai > tong + 0.01:
                        continue
                    qua_cat = chat and any(vao + 0.3 < b < vao + dai - 0.3 for b in bien)
                    trung_doan = any(vao < b and vao + dai > a for a, b in da_dung.get(kid, []))
                    if tranh_lap and trung_doan:
                        continue
                    k0, k1 = int(vao // BG), int(np.ceil((vao + dai) / BG))
                    if xau[k0:k1 + 1].any():
                        continue
                    goc = float(s[k0:max(k0 + 1, k1)].mean())
                    vw = E_[kid][k0:max(k0 + 1, k1)].mean(0)
                    if truoc.get("v") is not None and float(vw @ truoc["v"]) / (np.linalg.norm(vw) + 1e-8) > GIONG_TOI_DA:
                        continue
                    so_lan_dung = len(lan.get(kid, []))
                    cand.append((goc - 0.12 * so_lan_dung - (0.35 if trung_doan else 0.0) + (THUONG_GAN if kid in gan else 0.0)
                                 + (THUONG_SACH if kid in sach else 0.0) - (0.01 if qua_cat else 0.0),
                                 kid, round(vao, 2), f, goc, dai))
                    break
            return sorted(cand, key=lambda x: -x[0])

        def chon_tu(cand):
            for diem, kid, vao, f, goc, dai in cand[:6]:
                if not sach_hinh.dau_cuoi_toi(f, vao, dai):
                    return (diem, kid, vao, goc, dai)
            return None

        cd = (CAT_DAU_CAU or NGHI_GIONG_DOC) and bool(nghi)
        chon = None

        # 1. Clip của chính chủ đề: tìm ĐOẠN MỚI chưa từng dùng trên timeline (cách >= 60s, tối đa 2 lần)
        if S_chinh:
            cand = (tim_pool(S_chinh, True, cach=CACH_LAP, cap=True, chat=cd) if cd else None) or tim_pool(S_chinh, True, cach=CACH_LAP, cap=True)
            chon = chon_tu(cand)

        # 2. Lùi sang clip của chủ đề liền trước/sau: ĐOẠN MỚI chưa từng dùng
        if chon is None and S_ke:
            cand = ((tim_pool(S_ke, True, cach=CACH_LAP, cap=True, chat=cd) if cd else None)
                    or tim_pool(S_ke, True, cach=CACH_LAP, cap=True))
            chon = chon_tu(cand)

        # 3. Tìm trong toàn bộ kho: ĐOẠN MỚI chưa từng dùng
        if chon is None and S:
            cand = ((tim_pool(S, True, cach=CACH_LAP, cap=True, chat=cd) if cd else None)
                    or tim_pool(S, True, cach=CACH_LAP, cap=True))
            chon = chon_tu(cand)

        # 4. Nới trần lượt dùng nhưng VẪN BẮT BUỘC ĐOẠN MỚI CHƯA TỪNG DÙNG (tranh_lap=True) trong toàn bộ kho
        if chon is None and S:
            cand = ((tim_pool(S, True, cach=CACH_LAP_LUI, cap=False, chat=cd) if cd else None)
                    or tim_pool(S, True, cach=CACH_LAP_LUI, cap=False))
            chon = chon_tu(cand)

        # 5. Nếu toàn bộ kho đều không còn một giây mới nào: mới đành nới lỏng (vẫn phạt nặng trùng đoạn)
        if chon is None and S_chinh:
            cand = ((tim_pool(S_chinh, False, cach=CACH_LAP_LUI, cap=False, chat=cd) if cd else None)
                    or tim_pool(S_chinh, False, cach=CACH_LAP_LUI, cap=False))
            chon = chon_tu(cand)

        # 4. Ảnh thật tìm trên Google
        dai_anh = rem if rem <= (DOAN_MAX_NGHI if NGHI_GIONG_DOC else (CUM_TOI_DA if cd else SHOT_MAX)) else min(3.5, rem - SHOT_MIN)
        tot_anh = None
        for kid, v, _dd in anhs:
            if not con_cho_anh(kid):
                continue
            goc = float(v @ qv)
            d_ = goc - 0.03 * len(da_dung.get(kid, []))
            if not any(x["kho_id"] == kid for x in doan) and (tot_anh is None or d_ > tot_anh[0]):
                tot_anh = (d_, kid, goc)

        # Quyết định chọn hình
        if chon:
            doan.append({"loai": "video", "kho_id": chon[1], "vao": chon[2], "bd": bd, "dai": chon[4], "diem": round(chon[3], 3)})
            da_dung.setdefault(chon[1], []).append((chon[2], chon[2] + chon[4]))
            lan.setdefault(chon[1], []).append(t0 + bd)
            pos += chon[4]
            k0, k1 = int(chon[2] // BG), int(np.ceil((chon[2] + chon[4]) / BG))
            v = E_[chon[1]][k0:max(k0 + 1, k1)].mean(0)
            truoc.update(kid=chon[1], v=v / (np.linalg.norm(v) + 1e-8))
        elif tot_anh:
            doan.append({"loai": "anh", "kho_id": tot_anh[1], "vao": 0.0, "bd": bd, "dai": round(dai_anh, 2),
                         "diem": round(tot_anh[2], 3)})
            da_dung.setdefault(tot_anh[1], []).append((0.0, 0.0))
            lan.setdefault(tot_anh[1], []).append(t0 + bd)
            pos += dai_anh
            truoc.update(kid=tot_anh[1], v=None)
        else:
            # Cuối cùng nếu cả video và ảnh đều chưa lấp được: nới khoảng cách về 0s trong toàn bộ video
            cand_cuoi = tim_pool(S, False, cach=0, cap=False)
            chon_cuoi = chon_tu(cand_cuoi)
            if chon_cuoi:
                doan.append({"loai": "video", "kho_id": chon_cuoi[1], "vao": chon_cuoi[2], "bd": bd, "dai": chon_cuoi[4], "diem": round(chon_cuoi[3], 3)})
                da_dung.setdefault(chon_cuoi[1], []).append((chon_cuoi[2], chon_cuoi[2] + chon_cuoi[4]))
                lan.setdefault(chon_cuoi[1], []).append(t0 + bd)
                pos += chon_cuoi[4]
                k0, k1 = int(chon_cuoi[2] // BG), int(np.ceil((chon_cuoi[2] + chon_cuoi[4]) / BG))
                v = E_[chon_cuoi[1]][k0:max(k0 + 1, k1)].mean(0)
                truoc.update(kid=chon_cuoi[1], v=v / (np.linalg.norm(v) + 1e-8))
            else:
                break

    # đoạn liền nhau cùng một video, nối tiếp nhau trong video gốc -> gộp làm một (đỡ cắt vụn)
    gon = []
    for d in doan:
        p = gon[-1] if gon else None
        if p and p["loai"] == d["loai"] == "video" and p["kho_id"] == d["kho_id"] and abs(p["vao"] + p["dai"] - d["vao"]) < 0.2 \
                and p["dai"] + d["dai"] <= SHOT_MAX + 0.01 and not ((CAT_DAU_CAU or NGHI_GIONG_DOC) and nghi):
            p["dai"] = round(p["dai"] + d["dai"], 2)
        else:
            gon.append(d)
    return gon


def goi_y(du_an, ids=None, chi_canh_trong=True, mo_hinh=None, luu=True):
    """Gợi ý cho các cảnh (ids=None: mọi cảnh). chi_canh_trong: bỏ qua cảnh đã có kế hoạch người dùng tự dựng.
    Ghi thẳng kế hoạch (trạng thái 'chưa cắt', đánh dấu goi_y) — người dùng sửa rồi mới cắt."""
    import dung_tay
    from common import doc_json, ghi_json, thu_muc_du_an
    out = thu_muc_du_an(du_an)[1]
    canh = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    kho = {k: m for k, m in dung_tay.doc_kho(du_an).items()
           if _ngang(m) and (m.get("tay") or not m.get("sai_chu_de"))         # người dùng tự chọn hoặc không sai chủ đề
           and (m.get("tay") or not m.get("phong_xanh"))}                     # người dùng tự chọn hoặc không phông xanh
    mo_hinh = mo_hinh or MO_HINH_MAC_DINH
    vids, anhs = _chi_muc(kho, mo_hinh), _anh(kho, mo_hinh)
    if not vids and not anhs:
        raise ValueError("Kho dự án chưa có video/ảnh nào tải xong — tìm và tải vài video trước")
    dung = dung_tay.doc_dung(du_an)
    da_dung = {}
    lan = {}                                                # kho_id -> giây tuyệt đối đã dùng (giãn cách 14/10)
    bd_canh = {str(c["id"]): float(c.get("bat_dau") or 0) for c in canh}
    for cid, kh in (dung.items() if luu else []):             # đoạn người dùng đã dùng: tránh gợi ý trùng
        if (not chi_canh_trong or kh.get("goi_y")) and (ids is None or int(cid) in ids):
            continue                                        # gợi ý cũ sắp bị tính lại: không coi là "đã dùng" (lỗi 12/10)
        for d in kh.get("doan", []):
            lan.setdefault(d["kho_id"], []).append(bd_canh.get(str(cid), 0.0) + float(d.get("bd") or 0))
            if d["loai"] == "video":
                da_dung.setdefault(d["kho_id"], []).append((d["vao"], d["vao"] + d["dai"]))
    rieng = {k: m["cho_canh"] for k, m in kho.items() if m.get("cho_canh") is not None}
    chu_de_ds = doc_json(os.path.join(out, "chu_de.json"), {}).get("chu_de") or []
    canh_sang_cd = {}
    for cd in chu_de_ds:
        for cid in range(cd.get("canh_tu", 0), cd.get("canh_den", 0) + 1):
            canh_sang_cd[cid] = cd.get("id")
    kid_to_cd = {k: m.get("chu_de") for k, m in kho.items()}

    chon = [c for c in canh if ids is None or c["id"] in ids]
    n = 0
    ke_hoach = {}
    thieu_ds = {}
    gan, gan_truoc = set(), []
    truoc = {}                                              # đoạn đứng ngay trước (nối qua ranh giới cảnh)
    if NGHI_GIONG_DOC:
        lang = _lang(du_an, LANG_GIONG)
    elif CAT_DAU_CAU:
        lang = _lang(du_an, LANG_NGAN)
    else:
        lang = []
        nghi = cho_nghi(du_an)
    sach = {k for k, m in kho.items() if m.get("sach")}
    for k, c in enumerate(chon):
        kh = dung.get(str(c["id"]), {})
        if luu and chi_canh_trong and kh.get("doan") and not kh.get("goi_y"):
            continue
        th = []
        if NGHI_GIONG_DOC:
            moc = cho_nghi_giong_doc(du_an, c, lang)
        elif CAT_DAU_CAU and lang:
            moc = cho_dau_cau(du_an, c, lang)
        else:
            moc = [x - float(c.get("bat_dau") or 0) for x in nghi]
        doan = goi_y_canh(c, vids, anhs, da_dung, mo_hinh, gan, sach, truoc,
                          moc, lan=lan, t0=float(c.get("bat_dau") or 0),
                          thieu=th, rieng=rieng, cd_id=canh_sang_cd.get(c["id"]),
                          kid_to_cd=kid_to_cd)
        thieu_ds[str(c["id"])] = len(th)
        gan_truoc.append({d["kho_id"] for d in doan if d["loai"] == "video"})
        gan = set().union(*gan_truoc[-2:])
        if not doan:
            continue
        if not luu:                                          # chỉ trả kế hoạch (vd so sánh mô hình), không ghi dung.json
            ke_hoach[str(c["id"])] = {"doan": doan, "goi_y": True}
            n += 1
            continue
        dung_tay.luu_canh(du_an, c["id"], doan)
        with dung_tay._KHOA:                                  # noqa: SLF001
            d = dung_tay.doc_dung(du_an)
            d[str(c["id"])]["goi_y"] = True
            d[str(c["id"])]["diem"] = [x.get("diem") for x in doan]
            ghi_json(dung_tay._dung_path(du_an), d)            # noqa: SLF001
        n += 1
        with _KHOA:
            TT[du_an] = dict(TT.get(du_an, {}), xong=k + 1, tong=len(chon), so_canh=n)
    if luu:                                                 # chỗ hết video mới -> tu_dong_tim nhờ Gemini vẽ bù
        p_th = os.path.join(out, "thieu_hinh.json")
        cu = doc_json(p_th, {}) or {}
        cu.update(thieu_ds)
        ghi_json(p_th, {k: v for k, v in cu.items() if v})
        if any(thieu_ds.values()):
            log(f"  gợi ý: {sum(thieu_ds.values())} chỗ hết video mới (đã tạm dùng lại video cách >= {CACH_LAP_LUI:.0f} s)")
    return ke_hoach if not luu else n


def goi_y_nen(du_an, ids=None, chi_canh_trong=True, ten_nhap=None):
    """Chạy goi_y trong luồng nền (giao diện hỏi trạng thái qua TT). ten_nhap: xong thì tạo luôn bản nháp CapCut."""
    with _KHOA:
        if TT.get(du_an, {}).get("dang"):
            raise ValueError("đang gợi ý — chờ xong")
        TT[du_an] = {"dang": True, "xong": 0, "tong": 0, "so_canh": 0, "luc": time.time()}

    def chay():
        try:
            n = goi_y(du_an, ids, chi_canh_trong)
            nhap = None
            if ten_nhap:
                import dung_tay
                from common import thu_muc_nhap_capcut
                dd = thu_muc_nhap_capcut()
                if not dd:
                    raise ValueError("không dò được thư mục CapCut Drafts")
                with _KHOA:
                    TT[du_an].update(buoc="nhap")
                nhap = {"ten": ten_nhap, "so": dung_tay.tao_nhap(du_an, ten_nhap, dd)}
            with _KHOA:
                TT[du_an].update(dang=False, so_canh=n, nhap=nhap)
        except Exception as e:                              # noqa: BLE001
            with _KHOA:
                TT[du_an].update(dang=False, loi=str(e)[:300])
    threading.Thread(target=chay, daemon=True).start()
