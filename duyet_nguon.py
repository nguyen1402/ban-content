# -*- coding: utf-8 -*-
"""DUYỆT & TỰ CHỌN NGUỒN THEO CHỦ ĐỀ:
1. Tìm video siêu tốc (5-10s) theo chủ đề: lấy thông tin tiêu đề, thumbnail, thời lượng, kênh (KHÔNG tải storyboard/AI).
2. Tự động phát hiện cảnh lịch sử/sự kiện và tìm ảnh tư liệu lịch sử thật (Archival Photos).
3. Người dùng xem trước (preview) và tick chọn video/ảnh ưng ý.
4. Tải đúng các video/ảnh đã chọn, cắt đa dạng góc máy (3-4 khoảng/video), áp dụng trần cứng chống lặp (tối đa 2 lần) và tạo bản nháp CapCut.
"""
import io
import json
import os
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import common
from common import doc_json, ghi_json, log, thu_muc_du_an
import dung_tay
import chu_de
import goi_y

TT = {}
_KHOA = threading.Lock()


def _tt(du_an, **kw):
    with _KHOA:
        TT.setdefault(du_an, {}).update(kw)


# --------------------------------------------------------------------------- 1. TÌM VIDEO THEO CHỦ ĐỀ (SIÊU TỐC)
def tim_video_theo_chu_de(du_an, nam_truoc=None, bo_kenh_lon=False, lam_moi=False):
    """Tìm video theo từng chủ đề trong 5-10s (chỉ lấy metadata + thumbnail, không tải storyboard).
    Hỗ trợ lọc video cổ (nam_truoc) và lọc bỏ kênh lớn có tích (bo_kenh_lon).
    Trả về danh sách chủ đề kèm các video ứng viên để người dùng tick chọn."""
    _tt(du_an, buoc="tim_video", xong=0, tong=0, dang=True)
    ds_chu_de = chu_de.chia_chu_de(du_an)
    if not ds_chu_de:
        raise ValueError("Không chia được chủ đề từ kịch bản")

    kenh_bo = doc_json(dung_tay.KENH_BO, {}) or {}
    kho = dung_tay.doc_kho(du_an)
    co_san = set()
    for k, m in kho.items():
        if m.get("loai") == "video" and m.get("trang_thai") == "xong":
            if m.get("video_goc"):
                co_san.add(m["video_goc"])
            elif k.startswith("v_"):
                co_san.add(k[2:])
            else:
                co_san.add(k)

    def format_time(sec):
        sec = int(sec or 0)
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    nam_str = str(nam_truoc).strip() if nam_truoc else ""
    if nam_str and not re.match(r"^\d{4}$", nam_str):
        nam_str = ""

    def tim_cho_chu_de(cd):
        tks = cd.get("tu_khoa_en") or [cd.get("ten", "")]
        kq_cd = {}
        for q in tks[:4]:
            q_str = str(q).strip()
            if not q_str:
                continue
            q_tim = f"{q_str} before:{nam_str}" if nam_str else q_str
            try:
                ds = dung_tay.tim_youtube(q_tim, n=10, lam_moi=lam_moi)
                for v in ds:
                    vid = v.get("id")
                    dai = float(v.get("dai") or 0)
                    kenh = v.get("kenh") or ""
                    xac_minh = bool(v.get("xac_minh"))
                    # Bỏ kênh lớn có tích xác minh nếu được yêu cầu
                    if bo_kenh_lon and xac_minh:
                        continue
                    # Lọc thời lượng 25s - 45 phút, bỏ video đã có trong kho
                    if vid and 25.0 <= dai <= 2700.0 and vid not in co_san:
                        v["thumb"] = f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"
                        v["url"] = f"https://www.youtube.com/watch?v={vid}"
                        v["dai_str"] = format_time(dai)
                        kq_cd.setdefault(vid, v)
            except Exception as e:
                log(f"    ! tìm '{q_str}': {e}")

        # Thu thập các clip đã có sẵn trong kho cho chủ đề này
        ds_kho = []
        for kid, m in kho.items():
            if m.get("loai") == "video" and m.get("trang_thai") == "xong" and os.path.isfile(m.get("file", "")):
                if m.get("chu_de") == cd["id"]:
                    vid_goc = m.get("video_goc") or (kid[2:].split("_")[0] if kid.startswith("v_") else "")
                    thumb = f"https://i.ytimg.com/vi/{vid_goc}/mqdefault.jpg" if vid_goc else ""
                    ds_kho.append({
                        "id": kid,
                        "tieu_de": m.get("tieu_de", kid),
                        "kenh": m.get("kenh", ""),
                        "dai": float(m.get("dai") or 0),
                        "dai_str": format_time(float(m.get("dai") or 0)),
                        "thumb": thumb,
                        "url": f"https://www.youtube.com/watch?v={vid_goc}" if vid_goc else "",
                        "video_goc": vid_goc,
                    })

        ds_kho.sort(key=lambda x: -x["dai"])
        dung_kho_mac_dinh = len(ds_kho) >= 2

        ds_vid = list(kq_cd.values())
        if bo_kenh_lon:
            ds_vid.sort(key=lambda x: (
                1 if x.get("xac_minh") else 0,
                abs(float(x.get("dai") or 0) - 360),
                -int(x.get("luot_xem") or 0) if int(x.get("luot_xem") or 0) < 500000 else 999999999
            ))
        else:
            # Sắp xếp ưu tiên video chất lượng: độ dài vừa phải (2 - 15 phút), lượt xem tốt
            ds_vid.sort(key=lambda x: (abs(float(x.get("dai") or 0) - 360), -int(x.get("luot_xem") or 0)))

        # Nếu đã có đủ clip trong kho, mặc định không cần tick video YouTube mới để tránh tải thừa
        for idx, v in enumerate(ds_vid):
            v["chon"] = False if dung_kho_mac_dinh else (idx < 2)

        return {
            "id": cd["id"],
            "ten": cd.get("ten", f"Chủ đề {cd['id']}"),
            "canh_tu": cd["canh_tu"],
            "canh_den": cd["canh_den"],
            "so_canh": cd.get("so_canh", cd["canh_den"] - cd["canh_tu"] + 1),
            "dai": cd.get("dai", 0),
            "mo_ta_en": cd.get("mo_ta_en", ""),
            "tu_khoa_en": cd.get("tu_khoa_en", []),
            "kho_co_san": ds_kho,
            "dung_kho": dung_kho_mac_dinh,
            "videos": ds_vid[:24]   # Lấy tối đa 24 video để người dùng có thể bấm 'Xem thêm'
        }

    ket_qua = []
    with ThreadPoolExecutor(4) as ex:
        ket_qua = list(ex.map(tim_cho_chu_de, ds_chu_de))

    _tt(du_an, buoc="tim_video", xong=len(ket_qua), tong=len(ket_qua), dang=False)
    return ket_qua


# --------------------------------------------------------------------------- 2. TÌM ẢNH TƯ LIỆU LỊCH SỬ THẬT
TU_KHOA_LICH_SU = (
    "thế kỷ", "thập niên", "năm 1", "năm 2", "lịch sử", "chiến tranh",
    "thời kỳ", "tư liệu", "hồ sơ", "di tích", "phát minh", "hiệp ước",
    "triều đại", "xưa", "cổ đại", "trung đại", "quá khứ", "tài liệu gốc"
)


def tim_anh_lich_su(du_an):
    """Quét các cảnh có yếu tố lịch sử/tư liệu và tìm ảnh chụp tư liệu lịch sử thật từ Google Images."""
    _, out = thu_muc_du_an(du_an)
    canh = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    ds_lich_su = []

    for c in canh:
        txt = (c.get("text") or "").lower()
        la_ls = any(k in txt for k in TU_KHOA_LICH_SU) or bool(re.search(r"\b(1[6-9]\d{2}|20[0-2]\d)\b", txt))
        if la_ls:
            tk_goc = (c.get("anh") or c.get("video") or [""])[0] or c.get("text", "")[:40]
            tk_tim = f"{tk_goc} archival photo historical"
            try:
                anhs = dung_tay.tim_anh(tk_tim, n=6)
                if anhs:
                    for i, a in enumerate(anhs):
                        a["chon"] = (i == 0)   # Mặc định tick chọn ảnh đẹp nhất đầu tiên
                    ds_lich_su.append({
                        "canh_id": c["id"],
                        "bat_dau": c.get("bat_dau", 0),
                        "dai": c.get("dai", 0),
                        "text": c.get("text", ""),
                        "tu_khoa": tk_tim,
                        "anhs": anhs[:6]
                    })
            except Exception as e:
                log(f"    ! tìm ảnh lịch sử cảnh {c['id']}: {e}")

    return ds_lich_su


# --------------------------------------------------------------------------- 3. TẢI ĐA DẠNG GÓC MÁY & KHỚP BẢN NHÁP
def tinh_khoang_da_dang(tong, min_dai=20.0, max_dai=30.0, so_khoang=3):
    """Cắt 3-4 khoảng ở các mốc khác nhau (đầu, giữa, cuối) của video để có đa dạng góc máy, tránh lặp."""
    tong = float(tong or 0)
    if tong <= min_dai:
        return [(0.0, tong)]
    if tong <= max_dai:
        return [(0.0, tong)]

    start_eff = max(5.0, tong * 0.06)
    end_eff = min(tong - 5.0, tong * 0.94)
    usable = end_eff - start_eff
    if usable < min_dai:
        return [(0.0, min(tong, max_dai))]

    so_khoang = min(so_khoang, max(1, int(usable // (min_dai + 10.0))))
    step = usable / (so_khoang + 1)
    khoang = []
    for i in range(1, so_khoang + 1):
        mid = start_eff + i * step
        bd = max(0.0, mid - min_dai / 2)
        kt = min(tong, bd + min_dai)
        khoang.append((round(bd, 1), round(kt, 1)))
    return khoang


def tai_va_ghep_da_chon(du_an, chon_video, chon_anh=None, ten_nhap=None):
    """Tải đúng các video và ảnh người dùng đã tick chọn:
    - Mỗi video cắt 3-4 khoảng ở các mốc khác nhau (kho footage phong phú).
    - Tải ảnh tư liệu lịch sử thật và gán cho các cảnh tương ứng.
    - Chạy gợi ý với TRẦN CỨNG CHỐNG LẶP (tối đa 2 lần/clip).
    - Tạo bản nháp CapCut hoàn chỉnh."""
    chon_video = chon_video or {}
    chon_anh = chon_anh or {}
    ten_nhap = (ten_nhap or f"{du_an}_tu_chon").strip()

    _tt(du_an, buoc="chuan_bi", dang=True, xong=0, tong=100)

    # 1. Thu thập danh sách khoảng cần cắt từ các video được chọn
    ds_khoang_tai = []
    for cd_id_str, vids in chon_video.items():
        cd_id = int(cd_id_str)
        for v in vids:
            vid = v.get("id")
            if not vid:
                continue
            dai = float(v.get("dai") or 180.0)
            khoangs = tinh_khoang_da_dang(dai, min_dai=22.0, max_dai=32.0, so_khoang=3)
            for bd, kt in khoangs:
                ds_khoang_tai.append({
                    "vid": vid,
                    "bd": bd,
                    "kt": kt,
                    "tieu_de": v.get("tieu_de", ""),
                    "kenh": v.get("kenh", ""),
                    "chu_de_id": cd_id
                })

    if ds_khoang_tai:
        log(f"  [duyệt nguồn] Tải {len(ds_khoang_tai)} khoảng đa dạng từ {sum(len(v) for v in chon_video.values())} video đã chọn...")
        _tt(du_an, buoc="tai_khoang", xong=0, tong=len(ds_khoang_tai))
        dung_tay.tai_khoang_cuon(du_an, ds_khoang_tai, ten_buoc="tai_khoang", max_cung_luc=3,
                                 on_tien_do=lambda x, n: _tt(du_an, buoc="tai_khoang", xong=x, tong=n,
                                                             pt=round(x * 100 / max(1, n), 1)))
    else:
        log("  [duyệt nguồn] Tận dụng kho video có sẵn trên máy (0s tải mạng)...")

    # 2. Tải các ảnh tư liệu lịch sử được chọn vào kho
    thu_anh = os.path.join(dung_tay._ra(du_an), "kho", "anh")
    os.makedirs(thu_anh, exist_ok=True)
    so_anh_tai = 0
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for cid_str, anh_list in chon_anh.items():
        cid = int(cid_str)
        for idx_a, a in enumerate(anh_list):
            u = a.get("url")
            if not u:
                continue
            kid = f"ls_{cid}_{idx_a}"
            f_dich = os.path.join(thu_anh, f"{kid}.jpg")
            try:
                req = urllib.request.Request(u, headers=UA)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                if len(data) > 8000:
                    with open(f_dich, "wb") as f_out:
                        f_out.write(data)
                    w, h = dung_tay._kich_thuoc(f_dich)
                    dung_tay._cap_nhat_kho(du_an, kid, loai="anh", lich_su=True, cho_canh=cid,
                                           tieu_de=f"Tư liệu lịch sử [Cảnh {cid}]", file=f_dich,
                                           rong=w, cao=h, trang_thai="xong", pt=100.0, luc=time.time())
                    so_anh_tai += 1
            except Exception as ex:
                log(f"    ! tải ảnh lịch sử {kid}: {ex}")

    if so_anh_tai:
        log(f"  [duyệt nguồn] Đã nạp {so_anh_tai} ảnh tư liệu lịch sử vào kho dự án")

    # 3. Video do người dùng duyệt & tự chọn được giữ nguyên trọn vẹn (không tự ý bỏ logo/phụ đề)
    _tt(du_an, buoc="goi_y", xong=0, tong=0)

    # 4. Gợi ý ghép cảnh theo chủ đề với TRẦN CỨNG CHỐNG LẶP (tối đa 2 lần/clip)
    _tt(du_an, buoc="goi_y", xong=0, tong=0)
    goi_y.goi_y(du_an, chi_canh_trong=False)

    # 5. Tạo bản nháp CapCut
    from common import thu_muc_nhap_capcut
    dd = thu_muc_nhap_capcut()
    if not dd:
        raise ValueError("không dò được thư mục CapCut Drafts")
    _tt(du_an, buoc="nhap", xong=0, tong=0)
    so_doan = dung_tay.tao_nhap(du_an, ten_nhap, dd)
    log(f"  [duyệt nguồn] Đã tạo bản nháp CapCut '{ten_nhap}' với {so_doan} đoạn hình")

    _tt(du_an, buoc="xong", dang=False, ten=ten_nhap, so=so_doan)
    return {"ok": True, "ten_nhap": ten_nhap, "so_doan": so_doan, "so_khoang": len(ds_khoang_tai), "so_anh": so_anh_tai}
