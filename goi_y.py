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
DOAN_TOI_THIEU = 1.5
DOAN_MUC_TIEU = 2.6         # cửa sổ dò chỗ khớp; độ dài đoạn thật theo cảnh quay của nguồn:
SHOT_MIN, SHOT_MAX = 1.2, 5.5   # video mẫu: 10% shot 1,4 s, 90% 5,2 s
VIDEO_DU_TOT = 0.05          # đoạn video khớp từ mức này (điểm gốc SigLIP) thì không thay bằng ảnh (0,12 khi chấm câu tiếng Việt; câu mô tả tiếng Anh thang thấp hơn — đo 12/10)
GIONG_TOI_DA = 0.92         # 12/10 user: đoạn kế tiếp không được "gần như giống" đoạn trước (cosine khung SigLIP)
THUONG_SACH = 0.02          # 12/10: video stock sạch (Pexels/Pixabay, không logo) gần bằng điểm thì thắng YouTube
THUONG_GAN = 0.015          # video đang dùng ở 2 cảnh liền trước được cộng điểm: hình liền mạch, không nhảy chủ đề
THUONG_ANH = 0.03           # ảnh phải hơn video bấy nhiêu điểm mới được chọn (video động thường dễ xem hơn)
MO_HINH_MAC_DINH = "siglip"   # 11/10: user so 2 bản nháp, SigLIP 2 chọn đúng hơn CLIP -> mặc định
TT = {}                      # dự án -> trạng thái chạy nền {dang, xong, tong, loi}
_KHOA = threading.Lock()


BO_YOUTUBE_TU_DONG = True   # 12/10 user: không dùng video YouTube do máy tự tải (dính logo kênh); video tự tải tay vẫn dùng


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
        import loc_minh_hoa                                  # 12/10 user: bỏ hoạt hình/slide + khúc đứng hình
        xau, ti_hh = loc_minh_hoa.khung_xau("tay_" + kid, m["file"], np.asarray(e), chon_doan.BUOC_GIAY)
        if ti_hh > loc_minh_hoa.TI_LE_BO_VIDEO:
            log(f"    bỏ video thuyết trình/hoạt hình {kid} ({ti_hh * 100:.0f}% khung là hình vẽ)")
            continue
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


def _chia(dai):
    """Chia cảnh thành n đoạn đều nhau, mỗi đoạn trong [DOAN_TOI_THIEU, DOAN_TOI_DA] khi có thể."""
    n = max(1, int(round(dai / DOAN_MUC_TIEU)), int(np.ceil(dai / DOAN_TOI_DA)))
    while n > 1 and dai / n < DOAN_TOI_THIEU:
        n -= 1
    d = dai / n
    return [(round(i * d, 2), round(d if i < n - 1 else dai - i * d, 2)) for i in range(n)]


def goi_y_canh(canh, vids, anhs, da_dung, mo_hinh=None, gan=(), sach=(), truoc=None, nghi=()):
    """Danh sách đoạn gợi ý cho một cảnh. da_dung: {kho_id: [(bd, kt)]} — đoạn gốc đã gợi ý (tránh lặp).
    gan: video đang dùng ở các cảnh liền trước — được cộng THUONG_GAN (lấy đoạn KHÁC của chính video đó).
    truoc: {"kid", "v"} đoạn ĐỨNG NGAY TRƯỚC (cảnh trước) — 12/10 user: hai đoạn liền nhau không cùng một video và
    không gần như giống nhau (cosine > GIONG_TOI_DA). Hàm cập nhật truoc theo đoạn cuối của cảnh."""
    truoc = truoc if truoc is not None else {}
    # chỗ nghỉ TRONG cảnh (giây tính từ đầu cảnh); quãng (nghỉ X) chèn ở cuối cảnh KHÔNG phải chỗ đổi hình — hình cảnh
    # trước kéo dài qua đó (14/10 user)
    nghi = sorted(x for x in nghi if 0.5 < x < float(canh["dai"]) - float(canh.get("nghi_sau") or 0) - 0.5)
    mo_hinh = mo_hinh or MO_HINH_MAC_DINH
    import chon_doan
    import sach_hinh
    q = [s for s in (canh.get("video") or [])[:2]]
    if mo_hinh == "siglip" and canh.get("canh_en"):          # 12/10: chấm theo Ý NGHĨA (hành động + bối cảnh)
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
    L = float(canh["dai"])
    pos = 0.0
    while L - pos > 0.05:
        rem = round(L - pos, 2)
        bd = round(pos, 2)
        toi_nghi = next((x for x in nghi if x > pos + 0.5), None)
        if toi_nghi is not None:                            # không đoạn nào chạy qua chỗ nghỉ: tới chỗ nghỉ là đổi cảnh
            rem = round(toi_nghi - pos, 2)

        def do_dai(vao, bien, tong, rem=rem):
            """12/10: đoạn chạy tới HẾT CẢNH QUAY của nguồn (điểm cắt kế tiếp) như video mẫu, trong [SHOT_MIN, SHOT_MAX],
            không để lại mẩu cuối cảnh ngắn hơn SHOT_MIN."""
            con = next((b for b in bien if b > vao + 0.05), tong) - vao - 0.05
            d = min(con, SHOT_MAX, rem)
            if 0 < rem - d < SHOT_MIN:
                if con >= rem and rem <= SHOT_MAX + 1.0:
                    d = rem
                elif rem - SHOT_MIN >= SHOT_MIN:
                    d = rem - SHOT_MIN
            return round(d, 2) if d >= min(SHOT_MIN, rem) - 0.01 else None

        def tim(tranh_lap):
            cand = []
            for kid, t, s, f, bien, tong, xau in S:
                if len(s) < cs_n:
                    continue
                cs = np.convolve(s, np.ones(cs_n) / cs_n, mode="valid")
                if kid == truoc.get("kid"):
                    continue                                # 12/10 user: hai đoạn liền nhau không cùng một video
                for i in np.argsort(-cs)[:20]:
                    vao = float(t[i])
                    cat_truoc = [b for b in bien if b <= vao]
                    if cat_truoc and vao - cat_truoc[-1] < 0.8:     # vừa qua điểm cắt: bắt đầu từ đầu cảnh quay cho trọn
                        vao = cat_truoc[-1] + 0.1
                    dai = do_dai(vao, bien, tong)
                    if not dai or vao + dai > tong + 0.01:
                        continue
                    if tranh_lap and any(vao < b and vao + dai > a for a, b in da_dung.get(kid, [])):
                        continue                            # đoạn này đã gợi ý cho chỗ khác
                    k0, k1 = int(vao // BG), int(np.ceil((vao + dai) / BG))
                    if xau[k0:k1 + 1].any():
                        continue                            # hoạt hình/slide hoặc đứng hình
                    goc = float(s[k0:max(k0 + 1, k1)].mean())
                    vw = E_[kid][k0:max(k0 + 1, k1)].mean(0)
                    if truoc.get("v") is not None and float(vw @ truoc["v"]) / (np.linalg.norm(vw) + 1e-8) > GIONG_TOI_DA:
                        continue                            # gần như giống hệt đoạn trước (cùng cảnh quay ở video khác)
                    cand.append((goc - 0.01 * len(da_dung.get(kid, [])) + (THUONG_GAN if kid in gan else 0.0)
                                 + (THUONG_SACH if kid in sach else 0.0),
                                 kid, round(vao, 2), f, goc, dai))
                    break
            return sorted(cand, key=lambda x: -x[0])

        def chon_tu(cand):
            for diem, kid, vao, f, goc, dai in cand[:6]:
                if not sach_hinh.dau_cuoi_toi(f, vao, dai):
                    return (diem, kid, vao, goc, dai)
            return None
        chon = chon_tu(tim(True))
        dai_anh = rem if rem <= SHOT_MAX else min(3.5, rem - SHOT_MIN)
        tot_anh = None
        ten_dd = (canh.get("dia_danh_en") or "").lower() if canh.get("loai") == "dia_diem" else ""
        if ten_dd and not doan:                             # cảnh địa điểm: đoạn ĐẦU là ảnh thật của chính nơi đó
            for kid, v, dd in anhs:                         # (skill thay bằng bản đồ vệ tinh -> cho dài hơn)
                if dd == ten_dd:
                    goc = float(v @ qv)
                    d_ = goc - 0.03 * len(da_dung.get(kid, []))
                    if tot_anh is None or d_ > tot_anh[0]:
                        tot_anh = (d_, kid, goc)
            if tot_anh:
                con_canh = round(L - pos, 2)                # bản đồ cần thời gian phóng vào: cho chạy qua chỗ nghỉ
                d_dd = con_canh if con_canh <= 7.0 else min(6.0, con_canh - SHOT_MIN)
                if nghi:                                    # kết thúc ở chỗ nghỉ gần mốc 4-6 s nhất (vẫn đổi cảnh ở chỗ nghỉ)
                    hop = [x for x in nghi if 3.5 <= x <= 7.0]
                    if hop:
                        d_dd = min(hop, key=lambda x: abs(x - 5.0))
                doan.append({"loai": "anh", "kho_id": tot_anh[1], "vao": 0.0, "bd": bd, "dai": round(d_dd, 2),
                             "diem": round(tot_anh[2], 3)})
                da_dung.setdefault(tot_anh[1], []).append((0.0, 0.0))
                pos += d_dd
                truoc.update(kid=tot_anh[1], v=None)
                continue
        for kid, v, _dd in anhs:
            goc = float(v @ qv)
            d_ = goc - 0.03 * len(da_dung.get(kid, []))   # ảnh đã gợi ý ở cảnh khác: kém ưu tiên
            if not any(x["kho_id"] == kid for x in doan) and (tot_anh is None or d_ > tot_anh[0]):
                tot_anh = (d_, kid, goc)
        if chon is None:                                    # không còn đoạn chưa dùng: cho lặp lại đoạn đã chiếu (trước khi dùng ảnh)
            chon = chon_tu(tim(False))
        # 11/10 user: ảnh CHỈ bù chỗ thiếu; 12/10: video mẫu gần như không có ảnh tĩnh -> ảnh khi hết video dùng được
        if tot_anh and (chon is None or (chon[3] < VIDEO_DU_TOT and tot_anh[2] >= chon[3] + THUONG_ANH)):
            doan.append({"loai": "anh", "kho_id": tot_anh[1], "vao": 0.0, "bd": bd, "dai": round(dai_anh, 2),
                         "diem": round(tot_anh[2], 3)})
            da_dung.setdefault(tot_anh[1], []).append((0.0, 0.0))
            pos += dai_anh
            truoc.update(kid=tot_anh[1], v=None)
        elif chon:
            doan.append({"loai": "video", "kho_id": chon[1], "vao": chon[2], "bd": bd, "dai": chon[4], "diem": round(chon[3], 3)})
            da_dung.setdefault(chon[1], []).append((chon[2], chon[2] + chon[4]))
            pos += chon[4]
            k0, k1 = int(chon[2] // BG), int(np.ceil((chon[2] + chon[4]) / BG))
            v = E_[chon[1]][k0:max(k0 + 1, k1)].mean(0)
            truoc.update(kid=chon[1], v=v / (np.linalg.norm(v) + 1e-8))
        else:
            break
    # đoạn liền nhau cùng một video, nối tiếp nhau trong video gốc -> gộp làm một (đỡ cắt vụn)
    gon = []
    for d in doan:
        p = gon[-1] if gon else None
        if p and p["loai"] == d["loai"] == "video" and p["kho_id"] == d["kho_id"] and abs(p["vao"] + p["dai"] - d["vao"]) < 0.2                 and p["dai"] + d["dai"] <= SHOT_MAX + 0.01:
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
    kho = {k: m for k, m in dung_tay.doc_kho(du_an).items() if _ngang(m)}   # 14/10 user: bỏ hình dọc / vuông
    mo_hinh = mo_hinh or MO_HINH_MAC_DINH
    vids, anhs = _chi_muc(kho, mo_hinh), _anh(kho, mo_hinh)
    if not vids and not anhs:
        raise ValueError("Kho dự án chưa có video/ảnh nào tải xong — tìm và tải vài video trước")
    dung = dung_tay.doc_dung(du_an)
    da_dung = {}
    for cid, kh in (dung.items() if luu else []):             # đoạn người dùng đã dùng: tránh gợi ý trùng
        if kh.get("goi_y") and (ids is None or int(cid) in ids):
            continue                                        # gợi ý cũ sắp bị tính lại: không coi là "đã dùng" (lỗi 12/10)
        for d in kh.get("doan", []):
            if d["loai"] == "video":
                da_dung.setdefault(d["kho_id"], []).append((d["vao"], d["vao"] + d["dai"]))
    chon = [c for c in canh if ids is None or c["id"] in ids]
    n = 0
    ke_hoach = {}
    gan, gan_truoc = set(), []
    truoc = {}                                              # đoạn đứng ngay trước (nối qua ranh giới cảnh)
    nghi = cho_nghi(du_an)
    sach = {k for k, m in kho.items() if m.get("sach")}
    for k, c in enumerate(chon):
        kh = dung.get(str(c["id"]), {})
        if luu and chi_canh_trong and kh.get("doan") and not kh.get("goi_y"):
            continue
        doan = goi_y_canh(c, vids, anhs, da_dung, mo_hinh, gan, sach, truoc,
                          [x - float(c.get("bat_dau") or 0) for x in nghi])
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
