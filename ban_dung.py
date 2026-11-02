# -*- coding: utf-8 -*-
# 30/10 user ("Bàn dựng theo câu: chọn hình từng câu trước khi tải, không tải cả video, không băm cả video"):
# Module nghiệp vụ cho Bàn dựng theo câu: quản lý trạng thái ban_dung.json, tính nhịp câu, tìm video YouTube / kho,
# chấm storyboard, tải video theo khoảng chỉ định (yt-dlp --download-sections), đặt vào nhịp và đồng bộ sang dung.json.
import copy
import glob
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request

import common
from common import CACHE_CHUNG, FFMPEG, YT_JS, YTDLP, doc_json, ghi_json, log, thu_muc_du_an
import dung_tay
import goi_y

_KHOA = threading.Lock()
LE_TAI_GIAY = 2.0                 # lề giây ±2s trước/sau khoảng chọn để người dùng dễ trượt mép trong CapCut
TOI_DA_UNG_VIEN = 8               # số video ứng viên hiển thị cho một câu
NHIP_TOI_THIEU = 1.2             # giây tối thiểu cho 1 nhịp hình (băm dày theo ngắt giọng thực tế)
LOI_NHAN_AI = "NHAN_AI"          # đầu thông báo lỗi để giao diện hỏi xác nhận "vẫn dùng"


def _tep_ban_dung(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "ban_dung.json")


def doc(du_an):
    """Đọc dữ liệu trạng thái bàn dựng ban_dung.json của dự án."""
    with _KHOA:
        p = _tep_ban_dung(du_an)
        d = doc_json(p, {}) or {}
        if not d:
            d = {"_phien_ban": 1, "cau": {}, "ung_vien": {}}
        if "_phien_ban" not in d:
            d["_phien_ban"] = 1
        d.setdefault("cau", {})
        d.setdefault("ung_vien", {})
        return d


def ghi(du_an, d):
    """Ghi trạng thái bàn dựng ra file ban_dung.json an toàn đa luồng."""
    with _KHOA:
        p = _tep_ban_dung(du_an)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        ghi_json(p, d)


def lap_danh_sach_canh(du_an, lam_moi=False):
    """02/11: dự án mới chưa có ban_dung.json -> trang Bàn dựng gọi hàm này (trước chưa có hàm, trang lỗi 500).
    Tạo mục cho mọi câu trong tu_khoa.json, nhịp theo chỗ ngắt giọng, chưa gắn hình. lam_moi: chia lại nhịp mọi câu."""
    canhs = doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []
    d = doc(du_an)
    for c in canhs:
        k = str(c.get("id"))
        cu = d["cau"].get(k)
        if cu and cu.get("nhip") and not lam_moi:
            continue
        d["cau"][k] = dict(cu or {"cach": "footage", "loai_goi_y": "quay_duoc", "tin_cay": "xanh", "tu_khoa": [],
                                  "bat_buoc": [], "cam": [], "ghim_nguon": []},
                           nhip=nhip_cua_cau(du_an, c.get("id")), sua_luc=time.time())
    ghi(du_an, d)
    return d["cau"]


# --------------------------------------------------------------------------- nhịp của câu
def nhip_cua_cau(du_an, canh_id):
    """Chia câu thành 1 hoặc nhiều nhịp hình theo chỗ ngắt giọng đọc (goi_y.cho_nghi_giong_doc), gộp nhịp < 2 s."""
    out = thu_muc_du_an(du_an)[1]
    canhs = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    c = next((x for x in canhs if str(x.get("id")) == str(canh_id)), None)
    if not c:
        return [{"bd": 0.0, "dai": 3.0, "nguon": None, "kho_id": None, "da_tai": False}]

    dai_tong = float(c.get("dai") or 3.0)
    if dai_tong <= NHIP_TOI_THIEU:
        return [{"bd": 0.0, "dai": round(dai_tong, 2), "nguon": None, "kho_id": None, "da_tai": False}]

    try:
        lang = goi_y._lang(du_an, goi_y.LANG_GIONG)          # noqa: SLF001
        nghi = goi_y.cho_nghi_giong_doc(du_an, c, lang) or []
    except Exception as e:                                    # noqa: BLE001
        log(f"    ! [ban_dung] loi cho_nghi_giong_doc canh {canh_id}: {e}")
        nghi = []

    # Cắt theo các mốc giây ngắt giọng
    mocs = sorted(list(dict.fromkeys([0.0] + [float(t) for t in nghi if 0.0 < float(t) < dai_tong] + [dai_tong])))
    nhip_tam = []
    for i in range(len(mocs) - 1):
        t0, t1 = mocs[i], mocs[i + 1]
        nhip_tam.append({"bd": round(t0, 2), "dai": round(t1 - t0, 2), "nguon": None, "kho_id": None, "da_tai": False})

    # Gộp nhịp < NHIP_TOI_THIEU vào nhịp liền kề
    if len(nhip_tam) > 1:
        ra = []
        for n in nhip_tam:
            if not ra:
                ra.append(n)
            elif n["dai"] < NHIP_TOI_THIEU:
                ra[-1]["dai"] = round(ra[-1]["dai"] + n["dai"], 2)
            elif ra[-1]["dai"] < NHIP_TOI_THIEU:
                cuoi = ra.pop()
                n["bd"] = cuoi["bd"]
                n["dai"] = round(cuoi["dai"] + n["dai"], 2)
                ra.append(n)
            else:
                ra.append(n)
        return ra

    return nhip_tam


# --------------------------------------------------------------------------- độ tin cậy của câu
def tinh_tin_cay(du_an, canh_id, cau_info, dung_info=None):
    """Tính màu tin cậy cho câu:
    - xanh: đã được người dùng tự chọn/dựng, hoặc footage khớp tốt.
    - do: khong_quay_duoc chưa có ảnh/veo, hoặc chưa có hình.
    - vang: có cảnh báo nhãn nghi vấn, hoặc mượn kho khác, điểm thấp."""
    if not cau_info:
        return "do"
    cach = cau_info.get("cach", "chua")
    if cach in ("anh_ai", "veo"):
        return "xanh"
    if cau_info.get("loai_goi_y") == "khong_quay_duoc" and cach != "footage":
        return "do"

    # Kiểm tra nhịp footage
    nhips = cau_info.get("nhip") or []
    if not nhips or not any(x.get("da_tai") or x.get("kho_id") for x in nhips):
        if dung_info and dung_info.get("doan"):
            return "xanh" if dung_info.get("ban_dung") else "vang"
        return "do"

    for n in nhips:
        if not n.get("da_tai") and not n.get("kho_id"):
            return "vang"

    return "xanh"


# --------------------------------------------------------------------------- tải theo khoảng
def tai_khoang(du_an, vid, vao, ra, cho_phep_ai=False):
    """Tải đúng khoảng giây [vao, ra] của video YouTube bằng yt-dlp --download-sections.
    Trả về kid (mã mảnh trong kho) khi thành công.
    01/11 user: video có nhãn AI bị chặn, trừ khi người dùng đã xác nhận (cho_phep_ai=True)."""
    vid = str(vid).strip()
    vao = float(vao)
    ra = float(ra)
    if ra <= vao:
        raise ValueError(f"Khoảng không hợp lệ: vao={vao}, ra={ra}")

    if dung_tay.la_video_ai(vid) and not cho_phep_ai:
        raise ValueError(f"{LOI_NHAN_AI}: video {vid} có nhãn AI của YouTube, không tải")

    out = thu_muc_du_an(du_an)[1]
    thu_vid = os.path.join(out, "kho", "video")
    os.makedirs(thu_vid, exist_ok=True)

    kid = f"v_{vid}_t{int(vao)}"
    file_mp4 = os.path.join(thu_vid, f"{kid}.mp4")

    # Nếu đã tồn tại file hợp lệ -> tái sử dụng
    if os.path.isfile(file_mp4) and os.path.getsize(file_mp4) > 20000:
        log(f"    [ban_dung] file {kid}.mp4 đã có sẵn, dùng lại.")
        return kid

    vao_le = max(0.0, vao - LE_TAI_GIAY)
    ra_le = ra + LE_TAI_GIAY
    ffmpeg_dir = os.path.dirname(FFMPEG) or "."

    lenh = [
        YTDLP, *YT_JS, "--no-playlist", "--no-warnings",
        "-f", "bv*[height<=720]/b", "-S", "res:720,vcodec:h264",
        "--download-sections", f"*{vao_le:.1f}-{ra_le:.1f}",
        "--force-keyframes-at-cuts",
        "--ffmpeg-location", ffmpeg_dir,
        "-o", file_mp4,
        f"https://www.youtube.com/watch?v={vid}"
    ]

    log(f"    [ban_dung] tải khoảng {vao_le:.1f}s -> {ra_le:.1f}s của video {vid}...")
    err_cuoi = ""
    for lan in range(2):
        try:
            p = subprocess.run(
                lenh, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=300, creationflags=0x08000000 if os.name == "nt" else 0
            )
        except subprocess.TimeoutExpired:
            err_cuoi = "Quá thời gian tải (300 s)"
            continue

        if p.returncode == 0 and os.path.isfile(file_mp4) and os.path.getsize(file_mp4) > 20000:
            break
        if p.stderr:
            err_cuoi = p.stderr.decode("utf-8", "ignore").strip()
        time.sleep(1.5)

    if not os.path.isfile(file_mp4) or os.path.getsize(file_mp4) <= 20000:
        msg = err_cuoi or "Lỗi không tải được đoạn video"
        log(f"    ! [ban_dung] tải khoảng thất bại {vid}: {msg[:200]}")
        raise RuntimeError(f"Lỗi tải video: {msg[:150]}")

    # Đo độ dài và kích thước
    dai = dung_tay._do_dai(file_mp4)                          # noqa: SLF001
    rong, cao = dung_tay._kich_thuoc(file_mp4)                # noqa: SLF001

    # Đăng ký vào kho Media
    dung_tay._cap_nhat_kho(                                   # noqa: SLF001
        du_an, kid, loai="video", file=file_mp4, video_goc=vid,
        giay_bat_dau=vao, giay_ket_thuc=ra, dai=dai, rong=rong, cao=cao,
        trang_thai="xong", tay=True, ban_dung=True
    )

    # Đánh chỉ mục SigLIP nếu có thể
    try:
        import nhung_siglip
        nhung_siglip.chi_muc_video("tay_" + kid, file_mp4)
    except Exception as e:                                    # noqa: BLE001
        log(f"    ! [ban_dung] chi_muc_video {kid}: {e}")

    return kid


# --------------------------------------------------------------------------- đặt nhịp và đồng bộ
def uom_nhip(du_an, canh_id, i_nhip, nguon_info):
    """Ướm trước một đoạn video (kèm In/Out) vào nhịp i_nhip mà chưa cần tải ngay.
    Lưu trực tiếp vào ban_dung.json để giữ nguyên trạng thái khi đổi câu hoặc tải lại trang."""
    bd_data = doc(du_an)
    cau_id_str = str(canh_id)
    c_info = bd_data["cau"].setdefault(cau_id_str, {
        "cach": "footage", "loai_goi_y": "quay_duoc", "tin_cay": "xanh",
        "tu_khoa": [], "bat_buoc": [], "cam": [], "nhip": [],
        "ghim_nguon": [], "sua_luc": time.time()
    })

    if not c_info.get("nhip"):
        c_info["nhip"] = nhip_cua_cau(du_an, canh_id)

    i_nhip = int(i_nhip)
    if 0 <= i_nhip < len(c_info["nhip"]):
        c_info["nhip"][i_nhip]["nguon"] = nguon_info
        if nguon_info and nguon_info.get("vid"):
            vid = nguon_info["vid"]
            if vid not in c_info.setdefault("ghim_nguon", []):
                c_info["ghim_nguon"].insert(0, vid)

    c_info["cach"] = "footage"
    c_info["tin_cay"] = "xanh"
    c_info["sua_luc"] = time.time()
    ghi(du_an, bd_data)
    return True


def cap_nhat_nhip(du_an, canh_id, nhip_moi):
    """Cập nhật toàn bộ danh sách nhịp (chia thêm, gộp, kéo chỉnh độ dài) cho một câu."""
    bd_data = doc(du_an)
    cau_id_str = str(canh_id)
    c_info = bd_data["cau"].setdefault(cau_id_str, {
        "cach": "footage", "loai_goi_y": "quay_duoc", "tin_cay": "xanh",
        "tu_khoa": [], "bat_buoc": [], "cam": [], "nhip": [],
        "ghim_nguon": [], "sua_luc": time.time()
    })

    ds_nhip = []
    t_chay = 0.0
    for n in nhip_moi or []:
        dai = max(0.2, round(float(n.get("dai") or 1.0), 2))
        ds_nhip.append({
            "bd": round(t_chay, 2),
            "dai": dai,
            "nguon": n.get("nguon"),
            "kho_id": n.get("kho_id"),
            "da_tai": bool(n.get("da_tai"))
        })
        t_chay += dai

    c_info["nhip"] = ds_nhip
    c_info["sua_luc"] = time.time()
    ghi(du_an, bd_data)
    return ds_nhip


def dat_nhip(du_an, canh_id, i_nhip, kid, vao_trong_manh=0.0, nguon_info=None):
    """Đặt mảnh kid vào nhịp i_nhip của câu canh_id, lưu ban_dung.json và đồng bộ sang dung.json."""
    bd_data = doc(du_an)
    cau_id_str = str(canh_id)
    c_info = bd_data["cau"].setdefault(cau_id_str, {
        "cach": "footage", "loai_goi_y": "quay_duoc", "tin_cay": "xanh",
        "tu_khoa": [], "bat_buoc": [], "cam": [], "nhip": [],
        "ghim_nguon": [], "sua_luc": time.time()
    })

    if not c_info.get("nhip"):
        c_info["nhip"] = nhip_cua_cau(du_an, canh_id)

    i_nhip = int(i_nhip)
    if i_nhip < len(c_info["nhip"]):
        c_info["nhip"][i_nhip]["kho_id"] = kid
        c_info["nhip"][i_nhip]["da_tai"] = True
        if nguon_info:
            c_info["nhip"][i_nhip]["nguon"] = nguon_info
        if nguon_info and nguon_info.get("vid"):
            vid = nguon_info["vid"]
            if vid not in c_info.setdefault("ghim_nguon", []):
                c_info["ghim_nguon"].insert(0, vid)

    c_info["cach"] = "footage"
    c_info["tin_cay"] = "xanh"
    c_info["sua_luc"] = time.time()
    ghi(du_an, bd_data)

    # Đồng bộ sang dung.json
    kho = dung_tay.doc_kho(du_an, quet=False)
    doan_list = []
    for n in c_info["nhip"]:
        k_id = n.get("kho_id")
        if k_id and k_id in kho:
            f = kho[k_id].get("file", "")
            vao_f = float(vao_trong_manh)
            if n.get("nguon") and "vao" in n["nguon"]:
                v_goc = float(n["nguon"]["vao"])
                v_le = max(0.0, v_goc - LE_TAI_GIAY)
                vao_f = round(v_goc - v_le, 2)
            doan_list.append({
                "loai": "video", "kho_id": k_id, "file": f,
                "vao": vao_f,
                "bd": float(n["bd"]), "dai": float(n["dai"])
            })

    if doan_list:
        dung_tay.luu_canh(du_an, canh_id, doan_list)
        # Đánh dấu ban_dung = True và goi_y = False
        with dung_tay._KHOA:
            dung_data = dung_tay.doc_dung(du_an)
            if cau_id_str in dung_data:
                dung_data[cau_id_str]["ban_dung"] = True
                dung_data[cau_id_str]["goi_y"] = False
                common.ghi_json(dung_tay._dung_path(du_an), dung_data)

    return True


# --------------------------------------------------------------------------- trích xuất Video ID từ link YouTube
def trich_xuat_vid(chuoi):
    """Lấy video ID và số giây (nếu có) từ chuỗi URL hoặc ID YouTube."""
    if not chuoi:
        return None, 0.0
    chuoi = str(chuoi).strip()
    m_url = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})", chuoi)
    vid = m_url.group(1) if m_url else (chuoi if re.match(r"^[a-zA-Z0-9_-]{11}$", chuoi) else None)
    t_sec = 0.0
    m_t = re.search(r"[?&]t=(\d+h)?(\d+m)?(\d+s)?(\d+)?", chuoi)
    if m_t:
        h = int(m_t.group(1)[:-1]) if m_t.group(1) else 0
        m = int(m_t.group(2)[:-1]) if m_t.group(2) else 0
        s = int(m_t.group(3)[:-1]) if m_t.group(3) else (int(m_t.group(4)) if m_t.group(4) else 0)
        t_sec = float(h * 3600 + m * 60 + s)
    return vid, t_sec


# --------------------------------------------------------------------------- tìm cho câu
def tim_cho_cau(du_an, canh_id=None, q=None, nguon="youtube", trang=1,
                sap="lien_quan", dai="", ngay="", hd=False, cc=False, loai_tru=True, duoi="", so_luong=20):
    """Tìm ứng viên video cho câu hoặc tìm theo chủ thể / từ khoá tự nhập:
    - Nếu q là link YouTube -> nạp thẳng video đó.
    - Ghép đuôi duoi (documentary, 4k, b-roll) nếu được chỉ định và chưa có trong q.
    - Tìm YouTube với đầy đủ bộ lọc kiểu YouTube: sap, dai, ngay, hd, cc, loai_tru.
    - Lọc kênh xấu, video AI, thời lượng > 60p."""
    q_str = str(q or "").strip()
    vid_direct, t_direct = trich_xuat_vid(q_str)
    if vid_direct:
        # Link dán trực tiếp: trả về ngay ứng viên này
        tieu_de = f"Video YouTube ({vid_direct})"
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_direct}&format=json"
            req = urllib.request.Request(oembed_url, headers=dung_tay.UA)
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tieu_de = data.get("title") or tieu_de
        except Exception:                                     # noqa: BLE001
            pass
        co_ai = bool(dung_tay.la_video_ai(vid_direct))        # 01/11 user: link dán tay cũng phải kiểm tra nhãn AI thật
        return {
            "ds": [{
                "vid": vid_direct, "tieu_de": tieu_de, "kenh": "",
                "dai": 0, "dai_str": "0:00", "luot_xem_str": "",
                "thumb": f"https://i.ytimg.com/vi/{vid_direct}/hqdefault.jpg",
                "direct_t": t_direct, "khoang": [[t_direct, t_direct + 5.0, 1.0]],
                "nhan": {"ai": co_ai, "cc": True, "chu_the": 1.0, "nham": False, "con_la": None, "nhung": True}
            }],
            "het": True
        }

    q_tim = q_str

    het = False
    raw_items = []
    try:
        import chon_tay
        res = chon_tay.tim(du_an, q_tim, trang=int(trang), sap=sap, ngay=ngay, dai=dai, hd=bool(hd), cc=bool(cc), loai_tru=bool(loai_tru), so_luong=int(so_luong))
        raw_items = res.get("ds") or []
        het = res.get("het", False)
    except Exception as e:                                    # noqa: BLE001
        log(f"    ! [ban_dung] chon_tay.tim loi: {e}, thu dung_tay.tim_youtube")
        raw_items = dung_tay.tim_youtube(q_tim, n=TOI_DA_UNG_VIEN)

    bd_data = doc(du_an)
    ghim = bd_data.get("cau", {}).get(str(canh_id or ""), {}).get("ghim_nguon") or []

    ra_ds = []
    for it in raw_items:
        vid = it.get("id") or it.get("vid")
        if not vid:
            continue
        # Bỏ video AI
        if dung_tay.la_video_ai(vid):
            continue
        # Bỏ video dài > 60 phút
        dai_vid = float(it.get("dai") or 0)
        if dai_vid > 3600:
            continue

        item = {
            "vid": vid,
            "tieu_de": it.get("tieu_de") or it.get("title") or "",
            "kenh": it.get("kenh") or it.get("channel") or "",
            "dai": dai_vid,
            "dai_str": it.get("dai_str") or "",
            "luot_xem_str": it.get("luot_xem_str") or "",
            "thumb": it.get("thumb") or f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            "da_co": it.get("da_co", 0),
            "khoang": [],
            "nhan": {
                "ai": False,
                "cc": dung_tay.nguon_an_toan(vid, it.get("kenh") or ""),
                "chu_the": 0.0, "nham": False, "con_la": None, "nhung": True
            }
        }
        if vid in ghim:
            ra_ds.insert(0, item)
        else:
            ra_ds.append(item)

    return {"ds": ra_ds, "het": het}


# --------------------------------------------------------------------------- lấy chủ thể dự án
def lay_chu_the(du_an):
    """Lấy danh sách các chủ thể của dự án kèm từ khoá gợi ý cho Bàn dựng."""
    try:
        import chon_tay
        ds = chon_tay.chu_the_ds(du_an)
        return chon_tay.tu_khoa_nhanh(du_an, ds)
    except Exception as e:                                    # noqa: BLE001
        log(f"    ! [ban_dung] lay_chu_the loi: {e}")
        return []


def tai_tat_ca_nhip_cau(du_an, canh_id, bao_fn=None):
    """Tải toàn bộ các nhịp đã ướm nhưng chưa tải về của câu."""
    bd_data = doc(du_an)
    cau_id_str = str(canh_id)
    c_info = bd_data.get("cau", {}).get(cau_id_str)
    if not c_info or not c_info.get("nhip"):
        return False

    nhips = c_info["nhip"]
    for idx, n in enumerate(nhips):
        if n.get("da_tai") and n.get("kho_id"):
            continue
        nguon = n.get("nguon")
        if not nguon or not nguon.get("vid"):
            continue
        vid = nguon["vid"]
        vao = float(nguon.get("vao") or 0.0)
        ra = float(nguon.get("ra") or (vao + n["dai"]))
        if bao_fn:
            bao_fn(f"Đang tải mảnh {idx + 1}/{len(nhips)} ({vao:.1f}s - {ra:.1f}s) video {vid}...")
        kid = tai_khoang(du_an, vid, vao, ra)
        dat_nhip(du_an, canh_id, idx, kid, vao_trong_manh=0.0, nguon_info=nguon)

    return True


# --------------------------------------------------------------------------- chấm video (storyboard)
def cham_video(du_an, canh_id, vid):
    """Chấm điểm video qua storyboard và vector mô tả cảnh."""
    try:
        import xep_hang
        t, e, tong = xep_hang.storyboard(vid)
        if not t:
            return {"vid": vid, "khoang": [], "nhan": {"ai": False, "cc": True}}

        khoang = []
        if len(t) >= 2:
            step = max(1, len(t) // 3)
            for idx in range(0, min(len(t) - 1, 3 * step), step):
                khoang.append([round(t[idx], 1), round(t[min(idx + step, len(t) - 1)], 1), 0.85])

        nhan = {
            "ai": dung_tay.la_video_ai(vid),
            "cc": dung_tay.nguon_an_toan(vid),
            "chu_the": 0.8,
            "nham": False,
            "con_la": None,
            "nhung": True
        }
        res = {"vid": vid, "khoang": khoang, "nhan": nhan, "tong": tong}
        # Lưu cache vào ung_vien
        bd_data = doc(du_an)
        bd_data.setdefault("ung_vien", {}).setdefault(str(canh_id), {})[vid] = res
        ghi(du_an, bd_data)
        return res
    except Exception as err:                                  # noqa: BLE001
        log(f"    ! [ban_dung] cham_video loi {vid}: {err}")
        return {"vid": vid, "khoang": [], "nhan": {"ai": False, "cc": True}}


# --------------------------------------------------------------------------- lấy ảnh dải Storyboard
def lay_storyboard_anh(vid):
    """Lấy danh sách ảnh khung storyboard từ YouTube và lưu ra cache để giao diện hiển thị cuộn ngang."""
    vid = str(vid).strip()
    cache_dir = os.path.join(common.CACHE_CHUNG, "sb_anh", vid)
    os.makedirs(cache_dir, exist_ok=True)

    # Đã có ảnh trong cache
    files_co = sorted(glob.glob(os.path.join(cache_dir, "*.jpg")))
    meta_p = os.path.join(cache_dir, "meta.json")
    if files_co and os.path.isfile(meta_p):
        meta = doc_json(meta_p, {}) or {}
        return {
            "vid": vid,
            "anh": [f.replace("\\", "/") for f in files_co],
            "giay": meta.get("giay") or [],
            "tong": meta.get("tong") or 0.0
        }

    import xep_hang
    t_list, pil_imgs, tong = xep_hang._khung_storyboard(vid)  # noqa: SLF001
    anh_ra = []
    giay_ra = []
    for idx, (sec, im) in enumerate(zip(t_list, pil_imgs)):
        fn = os.path.join(cache_dir, f"khung_{idx:03d}.jpg")
        try:
            im.save(fn, quality=80)
            anh_ra.append(fn.replace("\\", "/"))
            giay_ra.append(round(sec, 1))
        except Exception:                                     # noqa: BLE001
            pass

    ghi_json(meta_p, {"giay": giay_ra, "tong": tong})
    return {"vid": vid, "anh": anh_ra, "giay": giay_ra, "tong": tong}


# --------------------------------------------------------------------------- chuẩn bị trước
def chuan_bi_truoc(du_an, tu_canh, so=5):
    """Luồng nền chuẩn bị trước ứng viên cho các câu tiếp theo."""
    def _chay():
        try:
            out = thu_muc_du_an(du_an)[1]
            canhs = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
            tu_idx = next((i for i, c in enumerate(canhs) if str(c.get("id")) == str(tu_canh)), 0)
            for c in canhs[tu_idx + 1:tu_idx + 1 + int(so)]:
                cid = c.get("id")
                q = (c.get("tu_khoa") or [c.get("text") or ""])[0]
                tim_cho_cau(du_an, cid, q=q)
        except Exception as e:                                # noqa: BLE001
            log(f"    ! [ban_dung] chuan_bi_truoc loi: {e}")

    threading.Thread(target=_chay, daemon=True).start()


# --------------------------------------------------------------------------- tự động băm theo chủ thể (mọi dự án)
# 01/11 user (Đợt 2): gom các script chay_*/dieu_phoi_* thành MỘT bộ máy: chấm từng khung thật (không chấm đại diện cả mảnh/video),
# chủ thể lấy từ chu_the của dự án (không viết cứng sói/cừu), không dùng lại mảnh, giãn cách nguồn, thiếu thì ĐỂ TRỐNG.
KACH_NGUON = 3                    # hai mảnh cùng video gốc phải cách nhau ít nhất 3 nhịp
SAN_MANH = 0.095                  # điểm chủ thể tối thiểu của một khung (dưới mức này thường là cảnh rỗng, không thấy con vật)
VAT_LA_CANH_NGUOI = 0.07          # cảnh của chủ thể con người: con vật ngoài kịch bản đạt mức này thì loại
MANH_TOI_DA = 30.0                # mảnh dài hơn là video gốc chưa băm -> không tự đặt
TU_XUNG_HO = {"chúng", "chúng ta", "nó", "họ", "ta"}   # tên gọi trong chu_the không dùng để dò chủ thể của nhịp
RAC_TIEU_DE = re.compile(r"gameplay|minecraft|\blego\b|\btoy\b|creepypasta|\bhorror\b|\breaction\b|#shorts\b|\bshorts\b|\btiktok\b"
                         r"|\bseminar\b|\bwebinar\b|\binterview\b|\bpodcast\b|\banimation\b|\bcartoon\b|\b3d render\b", re.I)
# hình gây nhiễu chung: mảnh giống các mô tả này hơn giống chủ thể thì bị loại (trừ khi chính chủ thể gần nghĩa mô tả đó)
# 02/11 user: bỏ "chim bay / đại bàng" (thêm riêng cho chosoi) — bài có chim (mòng biển trên hồ…) bị loại oan
HINH_NHIEU = ["a photo of a person, human face, presenter talking to camera, interview in studio",
              "a 3D render, video game graphics, computer generated image",
              "a cartoon animation, drawn illustration",
              "a movie scene with actors in costume, film set",
              "a title card with large text on plain background"]
NGUONG_GAN_NGHIA = 0.6            # chủ thể gần nghĩa hình nhiễu (cosine >= ngưỡng) thì không loại theo hình nhiễu đó
NGUONG_CUNG_CHU_THE = 0.85        # chỉ hai chủ thể gần như trùng mô tả mới không loại trừ nhau (sói đồng cỏ vẫn khác cừu)
NGUONG_NGUOI = 0.58               # mô tả chủ thể gần "person" tới mức này -> chủ thể là con người
SAN_NGUOI = 0.09                  # điểm sàn của chủ thể con người
SAN_TU_DIEN = 0.07                # con vật từ từ điển mô tả ngắn, điểm thường thấp hơn chủ thể mô tả đầy đủ
LE_KHUNG = 0.5                    # giây lùi vào trong so với khung kề khung bị loại (khung cách nhau 1,5 giây)
DO_SANG_TOI_THIEU = 35            # khung tối đen (cảnh đêm, màn đen) không dùng làm hình
TU_DAU_TEN = ("loài ", "bầy ", "đàn ", "người ", "con ")   # 'Bầy sói', 'Loài sói' và 'Sói' là một chủ thể
# 01/11 user ("kho có lợn rừng, hươu mà đoạn nói đấy không băm; nông trại lẫn bò"): từ điển con vật dùng chung mọi dự án.
# Lời có nhắc mà chưa là chủ thể -> tự thành chủ thể của nhịp đó; kịch bản không nhắc -> mảnh giống con đó bị loại.
CON_VAT = [(("lợn rừng", "heo rừng"), "a wild boar, black wild pig in the forest"), (("hươu", "nai"), "a deer in the wild"),
           (("dê núi",), "a mountain goat with horns on rocks"), (("dê",), "a goat"), (("bò",), "a cow, cattle"),
           (("trâu",), "a water buffalo"), (("lợn", "heo"), "a domestic pig"), (("ngựa",), "a horse"), (("chó",), "a dog"),
           (("gà",), "a chicken"), (("vịt",), "a duck"), (("mèo",), "a cat"), (("gấu",), "a bear"), (("khỉ",), "a monkey"),
           (("voi",), "an elephant"), (("sư tử",), "a lion"), (("con hổ", "hổ vằn"), "a tiger"), (("con cáo",), "a fox"),
           (("con rắn", "rắn độc"), "a snake"), (("con chuột", "chuột đồng"), "a rat"), (("thỏ",), "a rabbit"),
           (("đại bàng", "chim ưng"), "an eagle"), (("báo đốm", "báo hoa mai"), "a leopard, jaguar with spots")]


def _goc_manh(m):
    """Mã video YouTube của mảnh: trường video_goc, hoặc đọc từ tên file (mục v_kho_video_* không có trường này)."""
    if m.get("video_goc"):
        return m["video_goc"]
    t = re.match(r"v_([\w-]{11})(?:_|\.)", os.path.basename(m.get("file") or ""))
    return t.group(1) if t else ""


def _ds_manh(du_an):
    """Mảnh video đủ điều kiện: [{kids, file, goc, dai, tieu_de, rong, cao}], mỗi file một mục (kho có mục trùng file)."""
    theo_file = {}
    for kid, m in dung_tay.doc_kho(du_an, quet=False).items():
        f = m.get("file") or ""
        if m.get("loai") != "video" or m.get("trang_thai") != "xong" or kid.startswith("g_") or not os.path.isfile(f):
            continue
        x = theo_file.setdefault(f, {"kids": [], "file": f, "goc": "", "dai": 0.0, "tieu_de": "", "rong": 0, "cao": 0, "tay": False})
        x["kids"].append(kid)
        x["tay"] = x["tay"] or bool(m.get("tay"))
        x["goc"] = x["goc"] or _goc_manh(m)
        x["dai"] = x["dai"] or float(m.get("dai") or 0)
        x["rong"], x["cao"] = x["rong"] or int(m.get("rong") or 0), x["cao"] or int(m.get("cao") or 0)
        if not re.fullmatch(r"v_.*\.mp4", m.get("tieu_de") or ""):
            x["tieu_de"] = x["tieu_de"] or (m.get("tieu_de") or "")
    return [x for x in theo_file.values() if x["goc"] and not RAC_TIEU_DE.search(x["tieu_de"])]


def _chi_muc_khung(du_an, ds, bao):
    """01/11 user (dê núi ra gấu: một mảnh có nhiều cảnh, chấm chung cả mảnh thì sai): {file: (t, sáng, viền, e)} — mốc giây,
    độ sáng, cờ viền đen 2 bên và vector SigLIP của từng khung (1 khung/1,5 giây), lưu chi_muc_khung.npz, chỉ tính mảnh mới."""
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor
    import chon_doan
    import nhung_siglip
    p = os.path.join(thu_muc_du_an(du_an)[0], "chi_muc_khung.npz")
    co = {}
    if os.path.isfile(p):
        with np.load(p) as d:                                 # phải đóng file, Windows mới cho thay tệp ở cuối hàm
            files, dau, t, sang, vien, e = d["files"], d["dau"], d["t"], d["sang"], d["vien"], d["e"]
        for i, f in enumerate(files):
            a, b = dau[i], dau[i + 1]
            co[str(f)] = (t[a:b], sang[a:b], vien[a:b], e[a:b].astype(np.float32))
    thieu = [x for x in ds if x["file"] not in co]

    def _khung(x):
        try:
            return chon_doan._khung_ffmpeg(x["file"])             # noqa: SLF001
        except Exception as loi:                                  # noqa: BLE001
            log(f"    ! [ban_dung] khung {x['file']}: {loi}")
            return [], []

    for i in range(0, len(thieu), 64):
        if bao:
            bao(f"Đọc từng khung hình {i}/{len(thieu)} mảnh...")
        lo = thieu[i:i + 64]
        with ThreadPoolExecutor(6) as ex:
            khung = list(ex.map(_khung, lo))
        phang = [im for k in khung for im in k[0]]
        e = nhung_siglip.nhung_anh(phang) if phang else None
        j = 0
        for x, (imgs, ts) in zip(lo, khung):
            n = len(imgs)
            if not n:
                co[x["file"]] = (np.zeros(0, np.float32), np.zeros(0, np.float32), np.zeros(0, bool), np.zeros((0, 1152), np.float32))
                continue
            a = np.stack([np.asarray(im.convert("L"), np.float32) for im in imgs])
            w = a.shape[2]
            vien_ = (a[:, :, :int(w * 0.12)].mean((1, 2)) < 20) & (a[:, :, int(w * 0.88):].mean((1, 2)) < 20) \
                & (a[:, :, int(w * 0.35):int(w * 0.65)].mean((1, 2)) > 28)
            co[x["file"]] = (np.array(ts, np.float32), a.mean((1, 2)), vien_, e[j:j + n].astype(np.float32))
            j += n
    if thieu:
        ks = list(co)
        dau = np.cumsum([0] + [len(co[f][0]) for f in ks])
        tam = p + ".tam.npz"
        np.savez(tam, files=np.array(ks), dau=dau, t=np.concatenate([co[f][0] for f in ks]),
                 sang=np.concatenate([co[f][1] for f in ks]), vien=np.concatenate([co[f][2] for f in ks]),
                 e=np.concatenate([co[f][3] for f in ks]).astype(np.float16))
        os.replace(tam, p)
    return co


def _chu_the_gop(du_an):
    """Gộp các lô ('Sói · lô 1', 'Sói · lô 2') -> [{ten, goi: [regex], loai, cau_en: [mô tả + từ khoá hình]}]."""
    import chu_the
    def _than(ten):
        t = ten.lower()
        while t.startswith(TU_DAU_TEN):
            t = t.split(" ", 1)[1]
        return t

    gop = {}
    ds_goc = sorted(chu_the.doc(du_an) or [], key=lambda c: len((c.get("ten") or "").split(" · ")[0]))
    for c in ds_goc:
        ten = (c.get("ten") or "").split(" · ")[0].strip()
        khoa = next((k for k in gop if _than(ten).startswith(_than(k))), ten)
        x = gop.setdefault(khoa, {"ten": khoa, "ten_khac": set(), "goi": {khoa}, "loai": c.get("loai"), "cau_en": []})
        x["ten_khac"].add(ten)
        x["goi"].add(ten)
        x["goi"].update(g.split(" · ")[0].strip() for g in c.get("goi") or [])
        for t in [c.get("mo_ta_en")] + [s.get("tu_khoa") for s in c.get("trang_thai") or []]:
            if t and t not in x["cau_en"]:
                x["cau_en"].append(t)
    for x in gop.values():
        ds = sorted((g.lower() for g in x["goi"] if len(g) >= 3 and g.lower() not in TU_XUNG_HO), key=len, reverse=True)
        x["goi"] = [re.compile(r"\b" + re.escape(g) + r"\b") for g in ds]
    return list(gop.values())


def _them_vat_nhac(ds_ct, text):
    """Thêm vào ds_ct các con vật lời đọc có nhắc mà chưa là chủ thể; trả [mô tả en] các con vật kịch bản KHÔNG nhắc."""
    text = text.lower()
    ngoai = []
    for ten_vn, en in CON_VAT:
        goi = [re.compile(r"\b" + re.escape(t) + r"\b") for t in ten_vn]
        if not any(g.search(text) for g in goi):
            ngoai.append(en)
        elif not any(p.pattern == g.pattern for c in ds_ct for p in c["goi"] for g in goi):
            ten = ten_vn[0].capitalize()
            ds_ct.append({"ten": ten, "ten_khac": {ten}, "goi": goi, "loai": "song", "cau_en": [en]})
    return ngoai


def _manh_sach(x, vao, dai, loc_chu, nho):
    """Mảnh ngang 16:9 và ĐOẠN định dùng không dính chữ cứng. Kết quả lưu ở `nho` để chạy lại không phải đo."""
    import sach_hinh
    f = x["file"]
    k_tl = f + "#ti_le"
    if k_tl not in nho:
        r, c = x["rong"], x["cao"]
        if not r or not c:
            r, c = dung_tay._kich_thuoc(f)                    # noqa: SLF001
        nho[k_tl] = bool(r and c and r >= 1.55 * c)
    if not nho[k_tl] or not loc_chu or x["tay"]:
        return nho[k_tl]
    k_chu = f"{f}#chu{vao:.1f}+{dai:.1f}"
    if k_chu not in nho:
        try:
            nho[k_chu] = len(re.sub(r"[^a-zA-Z0-9\u00C0-\u1EF9]", "", sach_hinh.chu_van(f, vao, dai))) < 6
        except Exception as e:                                # noqa: BLE001
            log(f"    ! [ban_dung] OCR {f}: {e}")
            nho[k_chu] = True
    return nho[k_chu]


def tu_dong_bam_chu_the(du_an, giu_da_dung=True, loc_sub=True, bao=None, luu=True):
    """Băm cả bài vào timeline. giu_da_dung: nhịp đã có mảnh giữ nguyên, chỉ lấp nhịp trống. luu=False: chỉ tính, không ghi.
    Không đụng câu đã chọn Ảnh AI/Veo và câu dựng tay ngoài bàn dựng."""
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor
    import chu_the
    import nhung_siglip

    def _bao(s):
        log(f"[ban_dung] {s}")
        if bao:
            bao(s)

    out, cache = thu_muc_du_an(du_an)[1], thu_muc_du_an(du_an)[0]
    canh_list = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    if not canh_list:
        raise ValueError("Chưa có danh sách câu tu_khoa.json")
    ds_ct = _chu_the_gop(du_an)
    if not ds_ct:
        raise ValueError("Chưa có chủ thể — bấm Lập chủ thể trước")
    vat_ngoai = _them_vat_nhac(ds_ct, " ".join(c.get("text") or "" for c in canh_list))
    ten_tu_dien = {c["ten"] for c in ds_ct if len(c["cau_en"]) == 1}
    ten_ct = {t: c for c in ds_ct for t in c["ten_khac"]}

    # 1. mảnh sạch: bỏ video có nhãn AI, rồi lấy vector từng mảnh
    ds = _ds_manh(du_an)
    goc_ds = sorted({x["goc"] for x in ds})
    _bao(f"Kiểm tra nhãn AI {len(goc_ds)} video gốc...")
    with ThreadPoolExecutor(6) as ex:
        goc_ai = {g for g, a in zip(goc_ds, ex.map(dung_tay.la_video_ai, goc_ds)) if a}
    # 01/11 user: video người dùng đã tự chọn thì giữ dù có nhãn AI hay chữ cứng (xem _manh_sach)
    ds = [x for x in ds if x["tay"] or x["goc"] not in goc_ai]
    for x in ds:
        x["dai"] = x["dai"] or dung_tay._do_dai(x["file"])    # noqa: SLF001
    ds = [x for x in ds if 0 < x["dai"] <= MANH_TOI_DA]
    co = _chi_muc_khung(du_an, ds, _bao)
    ds = [x for x in ds if len(co.get(x["file"], ((),))[0])]
    if not ds:
        raise ValueError("Kho chưa có mảnh video nào dùng được")
    G = np.concatenate([co[x["file"]][3] for x in ds])
    dau = np.cumsum([0] + [len(co[x["file"]][0]) for x in ds])
    T = np.concatenate([co[x["file"]][0] for x in ds])
    tot = np.concatenate([(co[x["file"]][1] >= DO_SANG_TOI_THIEU) & ~co[x["file"]][2] for x in ds])

    # 2. vector chủ thể + bộ lọc TỪNG KHUNG: khung phải giống chủ thể hơn chủ thể khác loại và hơn hình nhiễu
    v_ct = {c["ten"]: nhung_siglip.nhung_chu(c["cau_en"]).mean(0) for c in ds_ct}
    v_ct = {k: v / (np.linalg.norm(v) + 1e-9) for k, v in v_ct.items()}
    v_nhieu = nhung_siglip.nhung_chu(HINH_NHIEU)
    S_nhieu = G @ v_nhieu.T
    S_vat = (G @ nhung_siglip.nhung_chu(vat_ngoai).T).max(1) if vat_ngoai else np.zeros(len(G), np.float32)
    so_ct = {k: G @ v for k, v in v_ct.items()}

    def _qua_loc(ten):
        v = v_ct[ten]
        doi = [so_ct[c["ten"]] for c in ds_ct if c["loai"] != "noi" and float(v @ v_ct[c["ten"]]) < NGUONG_CUNG_CHU_THE]
        cot = [i for i, t in enumerate(v_nhieu @ v) if t < NGUONG_GAN_NGHIA]
        s = so_ct[ten]
        # chủ thể là con người: cảnh có vật nuôi cạnh người vẫn đúng -> không so với chủ thể khác, siết điểm sàn thay vào đó
        la_nguoi = float(v_nhieu[0] @ v) >= NGUONG_NGUOI
        # cảnh người + bò: điểm người cao hơn điểm bò nên so tương đối không bắt được -> chủ thể con người dùng ngưỡng tuyệt đối
        san = SAN_NGUOI if la_nguoi else (SAN_TU_DIEN if ten in ten_tu_dien else SAN_MANH)
        ok = tot & (s >= san) & ((S_vat < VAT_LA_CANH_NGUOI) if la_nguoi else (s > S_vat))
        if doi and not la_nguoi:
            ok &= s > np.max(doi, axis=0)
        if cot:
            ok &= s > S_nhieu[:, cot].max(1)
        return ok

    def _doan_dung(ten):
        """Các đoạn liền nhau của mọi mảnh mà MỌI khung đều qua lọc: (J, A, B, R) = mảnh, giây đầu/cuối, vector trung bình."""
        ok = _qua_loc(ten)
        J, A, B, R, D = [], [], [], [], []
        for j, x in enumerate(ds):
            a, b = dau[j], dau[j + 1]
            i = a
            while i < b:
                if not ok[i]:
                    i += 1
                    continue
                k = i
                while k + 1 < b and ok[k + 1]:
                    k += 1
                J.append(j)
                A.append(0.0 if i == a else float(T[i]) - LE_KHUNG)   # khung kề trượt lọc -> cảnh đổi đâu đó giữa hai khung
                B.append(x["dai"] if k == b - 1 else float(T[k]) + LE_KHUNG)
                v = G[i:k + 1].mean(0)
                R.append(v / (np.linalg.norm(v) + 1e-9))
                D.append(float(so_ct[ten][i:k + 1].mean()))
                i = k + 1
        return {"J": np.array(J, int), "A": np.array(A, np.float32), "B": np.array(B, np.float32), "D": np.array(D, np.float32),
                "R": np.stack(R).astype(np.float32) if R else np.zeros((0, G.shape[1]), np.float32)}
    doan_ct = {c["ten"]: _doan_dung(c["ten"]) for c in ds_ct}

    # 3. dàn nhịp theo thời gian, ghi nhận nhịp giữ lại để giãn cách hai phía
    bd_data = doc(du_an)
    cau_map = bd_data["cau"]
    dung_cu = dung_tay.doc_dung(du_an)
    kho = dung_tay.doc_kho(du_an, quet=False)
    tt_cau = chu_the.trang_thai_cau(du_an)
    ct_cau = {c["id"]: [t.split(" · ")[0].strip() for t in c.get("ds") or []] for c in chu_the.ds_canh(du_an)}
    khe, vi_tri, da_dung, ket_qua = [], {}, set(), {}
    tep_sach = os.path.join(cache, "manh_sach.json")
    nho = doc_json(tep_sach, {}) or {}
    chi_so = {x["file"]: j for j, x in enumerate(ds)}
    ngu_canh = None

    def _chu_the_nhip(c, n):
        """Chủ thể của nhịp: thứ được nhắc SỚM NHẤT trong đoạn lời ứng với nhịp, rồi chủ thể của câu, rồi nhịp trước."""
        L = float(c.get("dai") or 1.0)
        text = c.get("text") or ""
        ve = text[int(len(text) * n["bd"] / L):int(len(text) * min(1.0, (n["bd"] + n["dai"]) / L)) + 1].lower()
        nhac = [(m.start(), -len(m.group()), x["ten"]) for x in ds_ct for g in x["goi"] for m in g.finditer(ve)]
        if nhac:
            return min(nhac)[2]
        return next((ten_ct[t]["ten"] for t in ct_cau.get(c["id"], []) if t in ten_ct), None) or ngu_canh

    for c in canh_list:
        scid = str(c["id"])
        cu = cau_map.get(scid) or {}
        kh = dung_cu.get(scid) or {}
        if cu.get("cach") in ("anh_ai", "veo") or (kh.get("doan") and not kh.get("ban_dung") and not kh.get("goi_y")):
            continue                                          # người dùng đã quyết câu này
        nhips = copy.deepcopy(cu.get("nhip")) if giu_da_dung and cu.get("nhip") else nhip_cua_cau(du_an, c["id"])
        ket_qua[scid] = {"canh": c, "cu": cu, "nhip": nhips}
        for n in nhips:
            ten = _chu_the_nhip(c, n)
            ngu_canh = ten or ngu_canh
            n["chu_the"] = ten or "Chung"
            m = kho.get(n.get("kho_id") or "") or {}
            g = _goc_manh(m)
            f = m.get("file")
            j = chi_so.get(f)
            # nhịp cũ chỉ được giữ nếu người dùng tự chọn, hoặc mảnh vẫn đúng chủ thể của nhịp theo bộ lọc hiện tại
            vao_cu = next((float(d.get("vao") or 0) for d in kh.get("doan") or [] if d.get("kho_id") == n.get("kho_id")), 0.0)
            dat = False
            if j is not None and ten:
                dd = doan_ct[ten]
                trong_doan = (dd["J"] == j) & (dd["A"] <= vao_cu + 0.1) & (dd["B"] >= vao_cu + n["dai"] - 0.2)
                dat = bool(trong_doan.any()) and _manh_sach(ds[j], vao_cu, n["dai"], loc_sub, nho)
            if f and f not in da_dung and giu_da_dung and (m.get("ban_dung") or dat):
                da_dung.add(m["file"])
                vi_tri.setdefault(g, []).append(len(khe))
                n["vao_manh"] = vao_cu
            else:
                n.update(kho_id=None, da_tai=False, nguon=None, thieu=True)
            khe.append((scid, n))

    # 4. lấp từng nhịp trống
    xong, trong, ds_thieu = 0, 0, []
    # chủ thể ít đoạn hình chọn trước, kẻo mảnh lợn rừng hiếm bị nhịp sói giành mất
    for i in sorted(range(len(khe)), key=lambda k: len(doan_ct[khe[k][1]["chu_the"]]["J"]) if khe[k][1]["chu_the"] in doan_ct else 0):
        scid, n = khe[i]
        c = ket_qua[scid]["canh"]
        ten = n["chu_the"] if n["chu_the"] in ten_ct else None
        chinh = next((ten_ct[t]["ten"] for t in ct_cau.get(c["id"], []) if t in ten_ct), None)
        en = (tt_cau.get(c["id"]) if ten == chinh else "") or (ten_ct[ten]["cau_en"][0] if ten else "")
        n["prompt_anh"] = f"Ultra-realistic National Geographic documentary photo of {en}, highly detailed, 8k"
        n["prompt_veo"] = f"Cinematic documentary footage of {en}, professional color grading, 4k"
        if n.get("kho_id"):
            continue
        if not ten:
            trong += 1
            continue
        if i % 20 == 0:
            _bao(f"Chọn mảnh nhịp {i}/{len(khe)}...")
        dem = v_ct[ten]
        if en and en != ten_ct[ten]["cau_en"][0]:
            dem = dem + nhung_siglip.nhung_chu([en])[0]
        dem = dem / (np.linalg.norm(dem) + 1e-9)
        dd = doan_ct[ten]
        diem = dd["R"] @ dem - 0.002 * np.array([len(vi_tri.get(ds[j]["goc"], [])) for j in dd["J"]], np.float32)
        chon = None
        for h in np.argsort(-diem):
            x = ds[int(dd["J"][h])]
            a, b = float(dd["A"][h]), float(dd["B"][h])
            if x["file"] in da_dung or b - a < n["dai"] - 0.2:
                continue
            if any(abs(p - i) < KACH_NGUON for p in vi_tri.get(x["goc"], [])):
                continue
            vao = round(min(max(0.0, a + (b - a - n["dai"]) / 2), max(0.0, x["dai"] - n["dai"])), 2)   # lấy giữa đoạn, tránh mép cảnh
            if _manh_sach(x, vao, min(n["dai"], b - a), loc_sub, nho):
                chon = x
                break
        if not chon:
            trong += 1
            continue
        kid = chon["kids"][0]
        m = kho.get(kid) or {}
        da_dung.add(chon["file"])
        vi_tri.setdefault(chon["goc"], []).append(i)
        xong += 1
        n.update(kho_id=kid, da_tai=True, thieu=False, vao_manh=vao, diem=round(float(dd["D"][h]), 3), nguon={
            "vid": chon["goc"], "tieu_de": chon["tieu_de"] or kid, "vao": float(m.get("giay_bat_dau") or 0.0) + vao,
            "ra": float(m.get("giay_bat_dau") or 0.0) + vao + n["dai"], "file": chon["file"]})
    ghi_json(tep_sach, nho)

    # 5. kết quả từng câu
    cau_moi = {}
    for scid, r in ket_qua.items():
        nhips, cu, c = r["nhip"], r["cu"], r["canh"]
        co = sum(1 for n in nhips if n.get("kho_id"))
        thieu = co < len(nhips)
        p = next((n for n in nhips if n.get("prompt_anh")), {})
        cau_moi[scid] = dict(cu, cach="footage" if co else "thieu", thieu=thieu, chu_the=nhips[0].get("chu_the") if nhips else "",
                             tin_cay="xanh" if not thieu else ("vang" if co else "do"), nhip=nhips,
                             cau_lenh_anh=p.get("prompt_anh", ""), cau_lenh_veo=p.get("prompt_veo", ""), sua_luc=time.time())
        if thieu:
            ds_thieu.append({"cau": c["id"], "text": c.get("text", ""), "chu_the": cau_moi[scid]["chu_the"],
                             "prompt_anh": p.get("prompt_anh", ""), "prompt_veo": p.get("prompt_veo", "")})

    tong_cau, da_phu = len(canh_list), len(cau_moi) - len(ds_thieu)
    if luu:
        bd_moi = doc(du_an)                                   # đọc lại: trong lúc băm người dùng có thể đã sửa câu khác
        bd_moi["cau"].update(cau_moi)
        ghi(du_an, bd_moi)
        with dung_tay._KHOA:                                  # noqa: SLF001
            dung_data = dung_tay.doc_dung(du_an)
            for scid, x in cau_moi.items():
                cu_doan = {d.get("kho_id"): d for d in (dung_data.get(scid) or {}).get("doan") or []}
                doan = [{"loai": "video", "kho_id": n["kho_id"], "vao": float(n.get("vao_manh", (cu_doan.get(n["kho_id"]) or {}).get("vao") or 0.0)),
                         "bd": float(n["bd"]), "dai": float(n["dai"])} for n in x["nhip"] if n.get("kho_id")]
                dung_data[scid] = {"doan": doan, "ban_dung": True, "goi_y": False, "luc": time.time()}
            ghi_json(dung_tay._dung_path(du_an), dung_data)   # noqa: SLF001
    _bao(f"Băm xong: thêm {xong} mảnh, {trong} nhịp để trống, {da_phu}/{tong_cau} câu đủ hình.")
    return {"ok": True, "da_phu": da_phu, "tong_cau": tong_cau, "thieu": len(ds_thieu), "them": xong, "nhip_trong": trong,
            "ds_thieu": ds_thieu, "cau": cau_moi, "goc_ai": sorted(goc_ai)} if not luu else {
            "ok": True, "da_phu": da_phu, "tong_cau": tong_cau, "thieu": len(ds_thieu), "them": xong, "nhip_trong": trong,
            "ds_thieu": ds_thieu}
