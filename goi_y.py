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
CACH_LAP = 15.0             # 19/10 user: dùng lại một hình thì hai lần phải cách nhau >= 15 s trên timeline
CACH_LAP_LUI = 15.0         # (không nới thấp hơn nữa — hết hình thì vẽ ảnh AI, không lặp sát)
GOC_GAN = 3                 # 22/10 user: tránh vài đoạn liền nhau cùng MỘT video gốc — đoạn mới không lấy video gốc của
#                             GOC_GAN đoạn trước (thiếu hình thì nới về chỉ tránh đoạn ngay trước)
LAP_MO_RONG = True          # 22/10 user: kho chủ thể cạn -> (a) cảnh khác CÙNG video gốc (ngưỡng hạ), (b) kho chủ thể đi
#                             cùng (nhắc trong câu, rồi chủ thể câu trước / sau) — hết cả hai mới để trống
DE_TRONG_KHI_HET = True     # 20/10 user: hết đoạn khớp thì để TRỐNG (không lấp tạm bằng mảnh đã dùng, không ảnh AI)
KHONG_DUNG_LAI = True       # 19/10 user (tối): "không sử dụng lại cảnh đã có ở toàn bài" — mỗi mảnh / ảnh dùng MỘT lần
LUOT_MANH = 1 if KHONG_DUNG_LAI else 2   # (cũ: tối đa 2 lần, trừ vế NHẮC LẠI sự việc cũ)
POOL_NGUONG = 0.11          # 19/10: clip thuộc kho đoạn nếu khớp đối tượng đoạn >= ngưỡng và không kém đoạn khớp nhất
POOL_LECH = 0.02            #   quá bấy nhiêu (đo cho_digo: kho đoạn dê 0 clip dưới biển; trước đây gán theo id đoạn cũ)
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

    def _doan(m):                                            # khúc lõi của mảnh (bỏ phần cắt dư hai đầu)
        bd = float(m.get("loi_bd") or 0)
        return m["file"], bd, max(float(m.get("loi_kt") or m.get("dai") or 0) - bd, 1.0)
    co = [m for m in kho.values() if m.get("loai") == "video" and m.get("trang_thai") == "xong" and os.path.isfile(m.get("file", ""))]
    hep = dict(zip([id(m) for m in co], sach_hinh.song_song(lambda m: sach_hinh.khung_hep(*_doan(m)), co)))
    sach_hinh.luu_khung_hep()
    for kid, m in kho.items():
        if m.get("loai") != "video" or m.get("trang_thai") != "xong" or not os.path.isfile(m.get("file", "")):
            continue
        if hep.get(id(m)):                                   # 23/10 user: video dọc / 4:3 viền đen trong khung ngang -> bỏ
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
        tu_chon = m.get("tay") and not m.get("manh_cua")      # 18/10: mảnh máy tự cắt không miễn lọc
        if not tu_chon and (ti_hh > loc_minh_hoa.TI_LE_BO_VIDEO or loc_minh_hoa.la_game(np.asarray(e))):
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
DOAN_GOP_NGAN = 2.0          # 19/10 user: đoạn ngắn hơn bấy nhiêu giây gộp vào đoạn sau (không băm)
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
    # 19/10 user: đoạn < DOAN_GOP_NGAN giây thì GỘP vào đoạn sau (không băm hình ở đó); đoạn cuối cảnh ngắn -> gộp đoạn trước
    moc = sorted(set(ra))
    gon, truoc = [], 0.0
    for m in moc:
        if m - truoc >= DOAN_GOP_NGAN:
            gon.append(m)
            truoc = m
    while gon and L - gon[-1] < DOAN_GOP_NGAN:
        gon.pop()
    return gon


def pool_noi_dung(vids, anhs, vec_cd, loi=None):
    """19/10 user (đoạn nói dê mà nhảy sang cảnh dưới biển): kho của mỗi đoạn tính theo NỘI DUNG HÌNH — điểm trung bình
    nửa khung tốt nhất của clip so với đối tượng đoạn (mo_ta_en). Không độc quyền: clip dê vào kho mọi đoạn về dê.
    Trả {kho_id: {id đoạn}}."""
    ids = list(vec_cd)
    if not ids:
        return {}
    # 22/10: mỗi đoạn có thể nhiều vector (mô tả chủ thể + từng TRẠNG THÁI) -> điểm đoạn = điểm vector khớp nhất
    hang = [np.atleast_2d(np.asarray(vec_cd[i])) for i in ids]
    V = np.concatenate(hang)
    thuoc = np.concatenate([np.full(len(h), j) for j, h in enumerate(hang)])
    ra = {}
    loi = loi or {}

    def tot(v):                                              # khung dùng được (lõi mảnh, không xấu); không còn khung nào -> tất cả
        e = np.asarray(v[2])
        x = np.zeros(len(e), bool)
        xv = np.asarray(v[6], bool) if len(v) > 6 else np.zeros(0, bool)
        x[:min(len(e), len(xv))] = xv[:len(e)]
        if v[0] in loi and v[1] is not None:                 # 22/10: mảnh cắt dư -> chỉ chấm khung trong LÕI
            t_ = np.asarray(v[1], float)[:len(e)]
            x[:len(t_)] |= (t_ < loi[v[0]][0] - 0.8) | (t_ > loi[v[0]][1])
        return e[~x] if (~x).any() else e
    for kid, e in [(v[0], tot(v)) for v in vids] + [(a[0], np.asarray(a[1])[None]) for a in anhs]:
        s_all = np.asarray(e) @ V.T
        s = np.stack([s_all[:, thuoc == j].max(1) for j in range(len(ids))], 1)
        k = max(1, len(s) // 2)
        d = np.sort(s, 0)[-k:].mean(0)
        tot = float(d.max())
        ra[kid] = {ids[j] for j in range(len(ids)) if d[j] >= POOL_NGUONG and d[j] >= tot - POOL_LECH} | {ids[int(d.argmax())]}
    return ra


def _chia(dai):
    """Chia cảnh thành n đoạn đều nhau, mỗi đoạn trong [DOAN_TOI_THIEU, DOAN_TOI_DA] khi có thể."""
    n = max(1, int(round(dai / DOAN_MUC_TIEU)), int(np.ceil(dai / DOAN_TOI_DA)))
    while n > 1 and dai / n < DOAN_TOI_THIEU:
        n -= 1
    d = dai / n
    return [(round(i * d, 2), round(d if i < n - 1 else dai - i * d, 2)) for i in range(n)]


def goi_y_canh(canh, vids, anhs, da_dung, mo_hinh=None, gan=(), sach=(), truoc=None, nghi=(), lan=None, t0=0.0,
               thieu=None, rieng=None, cd_id=None, kid_to_cd=None, ep=(), ve_vec=(), nhom=None, nhac=(), cd_phu=(),
               loi=None):
    """Giai đoạn 5: Danh sách đoạn gợi ý cho một cảnh.
    - Nguồn được dùng: ưu tiên video thuộc chủ đề của cảnh đó (cd_id).
    - Chuyển hình: ở dấu phẩy, dấu chấm (cho_dau_cau).
    - Chọn clip: trong kho của chủ đề, chấm theo từng vế câu và lấy clip hợp nhất.
    - Bỏ ngưỡng 'khớp kém': miễn là clip thuộc chủ đề thì được dùng (luôn lấp đầy).
    - 19/10 user: kho đoạn = clip có NỘI DUNG khớp đối tượng đoạn (pool_noi_dung); vế không nhắc đối tượng khác chấm
      theo đối tượng chính của đoạn; vế nhắc rõ đối tượng khác (ve_vec, cờ "rieng") tìm cả kho.
    - Luật lặp: một mảnh dùng tối đa LUOT_MANH = 2 lần, hai lần cách nhau >= 15 s (tính theo video gốc).
      Vế NHẮC LẠI sự việc cũ (nhac) được dùng lại hình cũ quá 2 lần (vẫn cách >= 15 s).
    - Hết hình đúng đối tượng: ảnh (ảnh AI vẽ riêng cho cảnh / ảnh thật cùng kho) -> không có thì ghi `thieu`
      (tu_dong_tim vẽ ảnh AI rồi gợi ý lại) và tạm lấp bằng clip của kho đoạn. KHÔNG lấy hình kho đoạn khác."""
    truoc = truoc if truoc is not None else {}
    lan = lan if lan is not None else {}                    # kho_id -> [giây TUYỆT ĐỐI trên timeline đã dùng]
    rieng = rieng or {}                                     # ảnh riêng cho cảnh
    nhom = nhom or {}                                       # kho_id -> video gốc (các mảnh cùng nguồn)
    cung_goc = {}
    for k_, g_ in nhom.items():
        cung_goc.setdefault(g_, []).append(k_)
    kid_to_cd = kid_to_cd or {}

    def con_cho(kid, tong, cach, cap):
        """Video còn được dùng ở giờ hiện tại? (giãn cách `cach` s; trần cứng tối đa 2 lần/clip)
        18/10 user ("lặp lại sát nhau"): giãn cách tính theo VIDEO GỐC — mọi mảnh cắt từ cùng một video (đo cho_digo:
        176/404 đoạn cùng video gốc cách nhau < 30 s)."""
        ts = lan.get(kid, [])
        ts_goc = [x for k2 in cung_goc.get(nhom.get(kid, kid), (kid,)) for x in lan.get(k2, [])]
        if cach and any(abs(t0 + pos - x) < cach for x in ts_goc):
            return False
        # TRẦN CỨNG CHỐNG LẶP: Chế độ chuẩn (Step 1, Step 2) tối đa 2 lần/clip
        if cap and len(ts) >= LUOT_MANH:
            return False
        return True


    def con_cho_anh(kid):
        if rieng.get(kid) not in (None, canh["id"]):
            return False
        ts = lan.get(kid, [])
        return len(ts) < (1 if rieng.get(kid) is not None or KHONG_DUNG_LAI else LUOT_ANH) and not any(abs(t0 + pos - x) < CACH_LAP for x in ts)

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
    E_ = {kid: e for kid, t, e, f, bien, tong, xau in vids}

    def cham(v_):                                            # điểm từng khung với vector truy vấn v_ + chia nhóm chủ đề
        S_ = [(kid, t, e @ v_, f, bien, tong, xau) for kid, t, e, f, bien, tong, xau in vids]
        if cd_id is not None:
            return S_, [it for it in S_ if cd_id in kid_to_cd.get(it[0], ())]
        return S_, S_
    S, S_chinh = cham(qv)
    qv_cur = qv

    L = float(canh["dai"])
    pos = 0.0
    while L - pos > 0.05:
        # 18/10 user: ẢNH CỐT LÕI (cot_loi.py) THAY HẲN video toàn màn hình ở đúng mốc đã định (mốc khớp nhịp nghỉ giọng)
        f_ = next((x for x in ep if x[0] - 0.3 <= pos < x[1] - 0.05), None)
        if f_ is not None:
            d_ = round(min(f_[1], L) - pos, 2)
            doan.append({"loai": "anh", "kho_id": f_[2], "vao": 0.0, "bd": round(pos, 2), "dai": d_, "diem": 1.0, "cot_loi": True})
            lan.setdefault(f_[2], []).append(t0 + pos)
            pos += d_
            truoc.update(kid=f_[2], v=None)
            continue
        rem = round(L - pos, 2)
        bd = round(pos, 2)
        toi_nghi = next((x for x in nghi if x > pos + 0.3), None)
        if toi_nghi is not None:
            rem = round(toi_nghi - pos, 2)
        toi_ep = next((x[0] for x in ep if x[0] > pos + 0.05), None)
        if toi_ep is not None and toi_ep - pos < rem:            # không lấn sang ảnh cốt lõi kế tiếp
            rem = round(toi_ep - pos, 2)
        # 18/10 user (nói "sói" mà hiện chim): chấm theo mô tả của VẾ đang đọc (mo_ta_ve.py), không một mô tả cả cảnh
        # 19/10 user: chỉ vế NHẮC RÕ đối tượng khác mới có vector riêng; hết vế đó quay về đối tượng chính của đoạn
        v_ve = next((vv for a_, b_, vv in ve_vec if a_ - 0.05 <= pos < b_ - 0.05), None)
        v_dich = qv if v_ve is None else v_ve
        if v_dich is not qv_cur:
            qv_cur = v_dich
            S, S_chinh = cham(qv_cur)
        dang_nhac = any(a_ - 0.05 <= pos < b_ - 0.05 for a_, b_ in nhac)

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

        def tim_pool(pool, tranh_lap, cach=CACH_LAP, cap=True, chat=False, goc_min=None, da_dang=True):
            cand = []
            for kid, t, s, f, bien, tong, xau in pool:
                if len(s) < cs_n:
                    continue
                if kid == truoc.get("kid") or nhom.get(kid, kid) == nhom.get(truoc.get("kid"), truoc.get("kid")):
                    continue
                if da_dang and nhom.get(kid, kid) in truoc.get("goc_gan", ()):   # 22/10: không vài đoạn liền 1 video gốc
                    continue
                if not con_cho(kid, tong, cach, cap):
                    continue
                cs = np.convolve(s, np.ones(cs_n) / cs_n, mode="valid")
                for i in np.argsort(-cs)[:20]:
                    vao = float(t[i])
                    cat_truoc = [b for b in bien if b <= vao]
                    if cat_truoc and vao - cat_truoc[-1] < 0.8:
                        vao = cat_truoc[-1] + 0.1
                    tong_k = tong
                    if kid in (loi or {}):                   # 22/10 user: mảnh CẮT DƯ -> vào / ra kẹp trong phần LÕI
                        vao = max(vao, loi[kid][0])
                        tong_k = min(tong, loi[kid][1])
                    dai = do_dai(vao, bien, tong_k, chat=chat)
                    if not dai or vao + dai > tong_k + 0.01:
                        continue
                    qua_cat = chat and any(vao + 0.3 < b < vao + dai - 0.3 for b in bien)
                    trung_doan = any(vao < b and vao + dai > a for a, b in da_dung.get(kid, []))
                    if tranh_lap and trung_doan:
                        continue
                    k0, k1 = int(vao // BG), int(np.ceil((vao + dai) / BG))
                    if xau[k0:k1 + 1].any():
                        continue
                    goc = float(s[k0:max(k0 + 1, k1)].mean())
                    if goc_min is not None and goc < goc_min:
                        continue
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

        def thu(pool, tranh_lap, cach=CACH_LAP, cap=True, goc_min=None):
            if not pool:
                return None
            for dd_ in (True, False):                        # 22/10: đa dạng nguồn trước; thiếu hình mới nới
                cand = ((tim_pool(pool, tranh_lap, cach=cach, cap=cap, chat=cd, goc_min=goc_min, da_dang=dd_) if cd else None)
                        or tim_pool(pool, tranh_lap, cach=cach, cap=cap, goc_min=goc_min, da_dang=dd_))
                r_ = chon_tu(cand)
                if r_ is not None:
                    return r_
            return None

        P_ = S_chinh if cd_id is not None else S              # kho ĐÚNG đối tượng của đoạn (không có đoạn: cả kho)
        # 1. vế nhắc rõ đối tượng khác: tìm cả kho theo vế đó (phải khớp hẳn), không có thì về kho đoạn
        if v_ve is not None:
            chon = thu(S, True, goc_min=POOL_NGUONG - 0.03)
        # 2. kho của đoạn: ĐOẠN MỚI chưa từng dùng (mảnh <= 2 lần, cách >= 15 s)
        if chon is None:
            chon = thu(P_, True)
        # 2b. 22/10 user: kho chủ thể cạn -> cảnh quay KHÁC của chính các video gốc thuộc kho đó (cùng nguồn, quay cùng
        #     chủ thể) với ngưỡng hạ một chút
        if chon is None and LAP_MO_RONG and cd_id is not None:
            goc_cd = {nhom.get(it[0], it[0]) for it in P_}
            chon = thu([it for it in S if nhom.get(it[0], it[0]) in goc_cd and cd_id not in kid_to_cd.get(it[0], ())],
                       True, goc_min=POOL_NGUONG - 0.03)
        # 2c. kho các chủ thể ĐI CÙNG: nhắc trong câu, rồi chủ thể của câu trước / câu sau (theo thứ tự cd_phu)
        if chon is None and LAP_MO_RONG:
            for cd_k in cd_phu:
                chon = thu([it for it in S if cd_k in kid_to_cd.get(it[0], ())], True)
                if chon is not None:
                    break
        # 3. kho của đoạn: dùng lại đoạn cũ (vẫn <= 2 lần, cách >= 15 s) — TẮT khi KHONG_DUNG_LAI
        if chon is None and not KHONG_DUNG_LAI:
            chon = thu(P_, False)
        # 4. vế NHẮC LẠI sự việc cũ: được dùng lại hình cũ quá 2 lần (cả kho, vẫn cách >= 15 s) — TẮT khi KHONG_DUNG_LAI
        if chon is None and dang_nhac and not KHONG_DUNG_LAI:
            chon = thu(S, False, cap=False)

        # 5. Ảnh: ảnh AI vẽ riêng cho cảnh này / ảnh thật CÙNG kho đoạn
        dai_anh = rem if rem <= (DOAN_MAX_NGHI if NGHI_GIONG_DOC else (CUM_TOI_DA if cd else SHOT_MAX)) else min(3.5, rem - SHOT_MIN)
        tot_anh = None
        if chon is None:
            for kid, v, _dd in anhs:
                if not con_cho_anh(kid):
                    continue
                if cd_id is not None and rieng.get(kid) != canh["id"] and cd_id not in kid_to_cd.get(kid, ()):
                    continue                                 # ảnh lạc đối tượng: không lấy
                goc = float(v @ qv_cur) + (1.0 if rieng.get(kid) == canh["id"] else 0.0)
                d_ = goc - 0.03 * len(da_dung.get(kid, []))
                if not any(x["kho_id"] == kid for x in doan) and (tot_anh is None or d_ > tot_anh[0]):
                    tot_anh = (d_, kid, goc)
        # 6. Hết hình: ghi chỗ thiếu (tu_dong_tim vẽ ảnh AI cho chỗ này rồi gợi ý lại); tạm lấp bằng clip kho đoạn
        tam = False
        if chon is None and tot_anh is None:
            if thieu is not None:
                thieu.append({"bd": round(t0 + bd, 2), "dai": round(rem, 2)})
            if DE_TRONG_KHI_HET:                             # 20/10 user: không có đoạn khớp -> ĐỂ TRỐNG khúc này
                pos += rem
                truoc.update(kid=None, v=None)
                continue
            chon = thu(P_, False, cap=False) or thu(P_, False, cach=0, cap=False)
            tam = True

        # Quyết định chọn hình
        if chon:
            doan.append({"loai": "video", "kho_id": chon[1], "vao": chon[2], "bd": bd, "dai": chon[4], "diem": round(chon[3], 3)}
                        | ({"tam": True} if tam else {}))
            da_dung.setdefault(chon[1], []).append((chon[2], chon[2] + chon[4]))
            lan.setdefault(chon[1], []).append(t0 + bd)
            pos += chon[4]
            k0, k1 = int(chon[2] // BG), int(np.ceil((chon[2] + chon[4]) / BG))
            v = E_[chon[1]][k0:max(k0 + 1, k1)].mean(0)
            truoc.update(kid=chon[1], v=v / (np.linalg.norm(v) + 1e-8),
                         goc_gan=(list(truoc.get("goc_gan") or []) + [nhom.get(chon[1], chon[1])])[-GOC_GAN:])
        elif tot_anh:
            doan.append({"loai": "anh", "kho_id": tot_anh[1], "vao": 0.0, "bd": bd, "dai": round(dai_anh, 2),
                         "diem": round(tot_anh[2] - (1.0 if rieng.get(tot_anh[1]) == canh["id"] else 0.0), 3)})
            da_dung.setdefault(tot_anh[1], []).append((0.0, 0.0))
            lan.setdefault(tot_anh[1], []).append(t0 + bd)
            pos += dai_anh
            truoc.update(kid=tot_anh[1], v=None)
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
           and (m.get("tay") or not m.get("phong_xanh"))                      # người dùng tự chọn hoặc không phông xanh
           and not m.get("cot_loi")                          # ảnh cốt lõi chỉ đặt đúng mốc của nó (ep), không làm ảnh lấp chỗ
           and not (m.get("loai") == "video" and dung_tay.la_kenh_loai(m))}   # 23/10 user: tin tức / trẻ em / hoạt hình / 3D / nhạc
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
    canh_sang_cd, canh_binh_luan = {}, {}
    mo_ta_cd = {cd.get("id"): cd.get("mo_ta_en") for cd in chu_de_ds if cd.get("loai", "ke") == "ke"}
    for cd in chu_de_ds:
        ds_k = cd.get("kho_ds") or [cd.get("kho_cd") or cd.get("id")]
        for n_, cid in enumerate(range(cd.get("canh_tu", 0), cd.get("canh_den", 0) + 1)):
            k_ = ds_k[n_ % len(ds_k)]                         # 18/10: bình luận dài thừa kế nhiều đoạn kể -> luân phiên kho
            canh_sang_cd[cid] = k_                            # đoạn bình luận dùng kho của đoạn kể nó thừa kế
            if cd.get("loai") == "binh_luan" and (mo_ta_cd.get(k_) or cd.get("mo_ta_en")):
                canh_binh_luan[cid] = mo_ta_cd.get(k_) or cd["mo_ta_en"]
    kid_to_cd = {}
    loi_map = {k: (float(m["loi_bd"]), float(m["loi_kt"])) for k, m in kho.items() if m.get("loi_bd") is not None}
    tt_cd = {cd.get("id"): [x["en"] for x in cd.get("trang_thai") or [] if x.get("en")]
             for cd in chu_de_ds if cd.get("loai", "ke") == "ke"}
    if mo_hinh == "siglip" and mo_ta_cd:                      # 19/10: kho đoạn theo NỘI DUNG HÌNH (không theo id đoạn cũ)
        import nhung_siglip                                   # 22/10: + mô tả các TRẠNG THÁI của chủ thể
        kid_to_cd = pool_noi_dung(vids, anhs, {i: np.stack([nhung_siglip.vec_mo_ta(mt, [])]
                                                           + [nhung_siglip.vec_mo_ta(x, []) for x in tt_cd.get(i, [])])
                                               for i, mt in mo_ta_cd.items() if mt}, loi=loi_map)
    if not kid_to_cd:
        kid_to_cd = {k: {m.get("chu_de")} for k, m in kho.items()}
    nhom_goc = {k: m.get("video_goc") or m.get("manh_cua") or k for k, m in kho.items() if m.get("loai") == "video"}

    chon = [c for c in canh if ids is None or c["id"] in ids]
    n = 0
    ke_hoach = {}
    thieu_ds, thieu_ct = {}, {}
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
    try:                                                     # 18/10: mô tả hình theo VẾ (đã lập ở 🤖)
        import mo_ta_ve
        ve_tat_ca = mo_ta_ve.doc(du_an) if mo_hinh == "siglip" else {}
        theo_chu_the = (doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("nguon") == "chu_the"
        if theo_chu_the and mo_hinh == "siglip":             # 19/10 user: vế nhắc tên chủ thể khác -> chiếu chủ thể đó
            import chu_the                                   # (dò tên cục bộ, không hỏi AI)
            ve_tat_ca = chu_the.ve_rieng(du_an, lang)
    except Exception:                                        # noqa: BLE001
        ve_tat_ca, theo_chu_the = {}, False
    tt_cau = {}
    if theo_chu_the:
        try:
            import chu_the
            tt_cau = chu_the.trang_thai_cau(du_an)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! trạng thái chủ thể theo câu: {str(e)[:100]}")
    phu_canh = {}                                            # 22/10: id cảnh -> [kho chủ thể đi cùng] cho bước lấp mở rộng
    if theo_chu_the and LAP_MO_RONG:
        try:
            import chu_the
            ct_cd = {}
            for cd in chu_de_ds:
                if cd.get("chu_the") is not None:
                    ct_cd.setdefault(cd["chu_the"], cd.get("kho_cd") or cd.get("id"))
            ks_c = chu_the.ds_k_cau(du_an)
            ids_s = sorted(ks_c)
            for n_, cid in enumerate(ids_s):
                ke = [ks_c[x][0] for x in (ids_s[n_ - 1] if n_ else None, ids_s[n_ + 1] if n_ + 1 < len(ids_s) else None)
                      if x is not None and ks_c.get(x)]
                rieng_cd = canh_sang_cd.get(cid)
                phu_canh[cid] = list(dict.fromkeys(ct_cd[k] for k in ks_c[cid][1:] + ke
                                                   if k in ct_cd and ct_cd[k] != rieng_cd))
        except Exception as e:                               # noqa: BLE001
            log(f"    ! chủ thể đi cùng (lấp mở rộng): {str(e)[:100]}")
    try:                                                     # 18/10: ảnh cốt lõi đã vẽ -> mốc tuyệt đối
        import cot_loi
        ep_tuyet_doi = cot_loi.khoang(du_an)
    except Exception:                                        # noqa: BLE001
        ep_tuyet_doi = []
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
        bl = canh_binh_luan.get(c["id"])                     # câu bình luận / hỏi: chấm theo ĐỐI TƯỢNG của đoạn kể thừa kế
        dt_ = (tt_cau.get(c["id"])                           # 22/10 user: câu có TRẠNG THÁI chủ thể -> chấm theo trạng thái
               or bl or mo_ta_cd.get(canh_sang_cd.get(c["id"])))   # 19/10 user: vế trung tính -> ĐỐI TƯỢNG CHÍNH của đoạn
        c_cham = dict(c, canh_en=[dt_]) if dt_ else c
        ve_c = (ve_tat_ca.get(str(c["id"])) or []) if ve_tat_ca and (theo_chu_the or not bl) else []
        doan = goi_y_canh(c_cham, vids, anhs, da_dung, mo_hinh, gan, sach, truoc,
                          moc, lan=lan, t0=float(c.get("bat_dau") or 0),
                          thieu=th, rieng=rieng, cd_id=canh_sang_cd.get(c["id"]),
                          kid_to_cd=kid_to_cd, nhom=nhom_goc, cd_phu=phu_canh.get(c["id"], ()), loi=loi_map,
                          ve_vec=mo_ta_ve.vec_ve(du_an, str(c["id"]), ve_c) if ve_c else (),
                          nhac=mo_ta_ve.nhac_lai(ve_c) if ve_c else (),
                          ep=[(max(a_, c0_) - c0_, min(b_, c0_ + float(c["dai"])) - c0_, k_)
                              for c0_ in [float(c.get("bat_dau") or 0)] for a_, b_, k_ in ep_tuyet_doi
                              if a_ < c0_ + float(c["dai"]) - 0.3 and b_ > c0_ + 0.3])
        thieu_ds[str(c["id"])] = len(th)
        thieu_ct[str(c["id"])] = th
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
        p_ct = os.path.join(out, "thieu_chi_tiet.json")      # 19/10: từng chỗ hết hình (giây tuyệt đối) cho bước vẽ ảnh AI
        ct = doc_json(p_ct, {}) or {}
        ct.update(thieu_ct)
        ghi_json(p_ct, {k: v for k, v in ct.items() if v})
        if any(thieu_ds.values()):
            log(f"  gợi ý: {sum(thieu_ds.values())} chỗ hết hình đúng đối tượng (tạm lấp bằng clip cùng đoạn, chờ ảnh AI)")
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
