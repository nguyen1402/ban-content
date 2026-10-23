import re
# -*- coding: utf-8 -*-
"""Dựng các lớp minh hoạ do dieu_phoi.py chọn (13/10 user) -> clip đặt trên track 'hieu_ung' (toàn khung):

  * bản đồ: khoanh_vung (vệ tinh khoanh vùng / ghim điểm), duong_di (mũi tên + icon phương tiện), lan_rong (nhiều tuyến);
  * sơ đồ Remotion MinhHoa.jsx trên nền CHÍNH đoạn video đang chiếu được làm TỐI: cau_tao, quy_trinh, vong_doi, mo_phong
    (mo_phong bản thử: chỉ tới MO_PHONG_DEN giây).

Mọi lớp bật đúng lúc giọng đọc tới cụm "moc" (giờ từng chữ của can_chu.py); từng bộ phận / bước / hành động cũng bật theo
cụm moc riêng. Các lớp không chồng nhau; không chồng lên đoạn bản đồ vệ tinh đã có trên track hình (cảnh địa điểm)."""
import hashlib
import json
import os

from common import ROOT, log

AQ = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "remotion", "public")

MO_PHONG_DEN = 1e9          # 13/10 user duyệt sau 2 kịch bản thử: bật diễn cảnh cho TOÀN BỘ video (trước: 180 s)
SO_DO = ("dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong", "so_sanh", "su_kien", "giai_thich", "tai_hien")
BO_VAI_AI = True           # 13/10 user: mọi vai do AI vẽ CẢ BỘ một lượt (kèm ảnh mẫu thật); hỏng thì lùi về từng vai
#: 13/10 user: diễn cảnh có TIẾNG ĐỘNG đi kèm — loại SFX (kho CapCut: pop / whoosh / hit / ting) theo hành động
AM_HANH_DONG = {"xuat_hien": "pop", "an": "pop", "sinh_soi": "pop", "bay_toi": "whoosh", "bo_chay": "whoosh",
                "mang_di": "whoosh", "lan_ra": "whoosh", "bien_mat": "whoosh", "bao_vay": "whoosh", "tan_cong": "hit",
                "tach_ra": "hit", "bien_thanh": "ting", "ket_hop": "ting", "lon_len": "ting"}
#: 13/10 user: "hình xuất hiện nhanh quá xong kết thúc luôn, người xem chưa hiểu" -> sau khi vật / nhịp CUỐI hiện xong
#: (hoạt cảnh ~HOAT_CANH s) phải đứng yên thêm GIU_CUOI s rồi mới tắt; cảnh sau không được cắt đuôi ngắn hơn mức đó.
HOAT_CANH = 1.0
GIU_CUOI = 2.0
KHOANG_NGAT = 4.0
DI_TRUOC = 0.1             # 18/10 user: hình hiện TRƯỚC lời 0,1 s (hằng bị xoá ở e47e14b mà code còn dùng -> thêm lại)
def lenh_ve(ve, thoi_dai="", co_mau=False):
    """Câu lệnh vẽ đầy đủ của một ảnh AI tái hiện (✨ và nút 🎨 Vẽ lại trên giao diện dùng chung)."""
    import anh_ve
    p = (f"{str(ve).strip().rstrip('.')}. Wide 16:9 landscape photograph. {anh_ve.phong_cach(thoi_dai)} "
         f"Absolutely NO text, NO letters, NO words.")      # 19/10 user: phong cách cố định + đúng thời đại
    if co_mau:
        p = ("The attached image is an EARLIER shot of the same story. Any subject that also appears in this "
             "shot must look exactly the same (same species, body shape, colours, markings, clothing, vehicle), "
             "same place, weather and light. Do NOT copy its framing and do NOT add subjects that this shot "
             "does not describe — follow the new camera position, subjects and counts below: " + p)
    return p


CHU_PHU = False             # 21/10 user: bản hoàn thiện TẮT thêm chữ lên màn hình (lớp phủ đen + chữ trắng số liệu / mốc năm)
SOAT_VE_LAI = 0             # 19/10: soát ảnh bằng Gemini chấm sai cả hai chiều (đo 4 ảnh cho_digo) -> TẮT
ANH_DUNG_TOI_DA = 5.0      # 23/10 user: một ảnh AI đứng tối đa 5 s — dài hơn thì vẽ ẢNH NỐI TIẾP (cùng cảnh, khoảnh khắc sau)
ANH_NGAN_NHAT = 1.5        #   chỗ đổi ảnh AI chọn mà làm ảnh ngắn hơn bấy nhiêu giây thì bỏ chỗ đổi đó
_KHUNG_NOI = ("a closer shot", "a wide shot", "a detail close-up", "a shot from another side")


def _loi_trong(ds_c, t0, t1):
    """Các chữ giọng đọc nói trong [t0, t1)."""
    return " ".join(str(w[0]) for c in ds_c for w in (c.get("tu") or []) if t0 <= float(w[1]) < t1).strip()


def _lich_anh(x, bd, dai, ds_c):
    """23/10 user: lịch ảnh của một chuỗi ảnh AI -> [(giây bắt đầu, câu lệnh, hướng)]. Chỗ đổi ảnh do AI chốt (moc_n);
    đoạn nào vẫn dài quá ANH_DUNG_TOI_DA thì chia đều và vẽ thêm ẢNH NỐI TIẾP (cùng cảnh, khoảnh khắc sau, khung máy khác)."""
    ve, i = [], 1
    while str(x.get(f"ve_{i}") or "").strip():
        ve.append((str(x[f"ve_{i}"]).strip(), x.get(f"moc_{i}"), x.get(f"huong_{i}") or None))
        i += 1
    if not ve and str(x.get("ve") or "").strip():
        ve = [(str(x["ve"]).strip(), None, None)]
    if not ve:
        return []
    kt = bd + dai
    ts = [bd] + [(_tim(ds_c, m) if m else None) for _, m, _ in ve[1:]]
    for k in range(1, len(ts)):                              # AI có ảnh mà không tìm thấy mốc: chia đều giữa hai mốc biết
        if ts[k] is None:
            j = next((q for q in range(k + 1, len(ts)) if ts[q] is not None), None)
            sau = ts[j] if j is not None else kt
            ts[k] = ts[k - 1] + (sau - ts[k - 1]) / ((j if j is not None else len(ts)) - k + 1)
    lich = []
    for (p_, _, h_), t in zip(ve, ts):
        if not lich or (t >= lich[-1][0] + ANH_NGAN_NHAT and t <= kt - ANH_NGAN_NHAT):
            lich.append((round(t, 2), p_, h_, False))
    ra = []
    for k, (t, p_, h_, _) in enumerate(lich):
        t_kt = lich[k + 1][0] if k + 1 < len(lich) else kt
        n = max(1, int(-(-(t_kt - t - 0.05) // ANH_DUNG_TOI_DA)))
        d = (t_kt - t) / n
        ra.append((round(t, 2), p_, h_))
        for q in range(1, n):
            t0 = t + q * d
            loi = _loi_trong(ds_c, t0, t0 + d)
            ra.append((round(t0, 2), f"{p_.rstrip('.')} — the NEXT moment of this same scene, {_KHUNG_NOI[(q - 1) % 4]}"
                       + (f", showing what the narration now says: \"{loi}\"" if loi else ""), h_))
    return ra


KHOANG_GIUA = 0.5          # 17/10: khoảng đệm 0.5s đạt chuẩn 19-20 cảnh AI Storytelling (25-30% thời lượng)


def _ve_day_du(y, ds):
    """Mô tả vẽ đứng riêng được: "SAME as actor N but X" -> "<mô tả vai N>, but X" (vẽ một mình thì không có actor N)."""
    import re
    ve = str(y.get("ve") or "").strip()
    m = re.match(r"\s*same as (?:actor |subject )?(\d)\s*,?\s*(.*)$", ve, re.I | re.S)
    if m and int(m.group(1)) < len(ds):
        goc = str(ds[int(m.group(1))].get("ve") or "").strip().rstrip(".")
        ve = f"{goc}, {m.group(2).strip()}" if goc else m.group(2).strip()
    return ve


TOAN_Y = ("tong_quat", "liet_ke", "con_so")   # 14/10 user: hiện MỘT lần đến hết ý (không nhịp từng bước)


def _chuan_hoa(x):
    """Kế hoạch kiểu MỚI (14/10: một ảnh cho cả ý) -> cấu trúc vai/hanh_dong cũ để phần giờ / dựng dùng chung."""
    kh = str(x.get("khuon") or "")
    if str(x.get("bo_cuc") or "").lower() == "liet_ke" and kh not in TOAN_Y:
        return x                                             # kế hoạch cũ (trước->sau liệt kê) giữ nguyên
    if kh == "liet_ke":
        return dict(x, bo_cuc="liet_ke", hanh_dong=[],
                    vai=[dict(y, vi_tri="", dan=False) for y in (x.get("vai") or []) if isinstance(y, dict)][:5])
    if kh in ("tong_quat", "con_so") and x.get("ve"):
        return dict(x, bo_cuc="", hanh_dong=[], vai=[{"ten": "", "ve": str(x["ve"])}])
    return x


_CHU_SO = {"không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5, "nhăm": 5, "sáu": 6,
           "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9}
_DON_VI = {"nghìn": 1000, "ngàn": 1000, "triệu": 10 ** 6, "tỷ": 10 ** 9, "tỉ": 10 ** 9}


def so_chu_so(s):
    """14/10 user ("Gần chín mươi phần trăm" -> "Gần 90%"): số đọc bằng chữ -> chữ số; giữ chữ trước/sau. Không đổi
    được -> '' (khi đó chỉ hiện ảnh, không hiện số)."""
    import re
    s = str(s or "").strip()
    if not s or re.search(r"\d", s):
        return s
    tu = s.split()
    so_tu = set(_CHU_SO) | set(_DON_VI) | {"mười", "mươi", "trăm", "linh", "lẻ"}
    i = next((k for k, w in enumerate(tu) if w.lower() in so_tu), None)
    if i is None:
        return ""
    j = i
    while j < len(tu) and tu[j].lower() in so_tu:
        j += 1
    tong, nhom, cho, dv_cuoi = 0, 0, 0, None
    for w in (x.lower() for x in tu[i:j]):
        if w == "mươi":
            nhom += (cho or 1) * 10
            cho = 0
        elif w == "mười":
            nhom += 10
        elif w == "trăm":
            nhom += (cho or 1) * 100
            cho = 0
        elif w in ("linh", "lẻ"):
            continue
        elif w in _DON_VI:
            nhom += cho
            tong += (nhom or 1) * _DON_VI[w]
            nhom, cho, dv_cuoi = 0, 0, w
        else:
            cho = _CHU_SO[w]
    tong += nhom + cho
    if not tong and "không" not in (x.lower() for x in tu[i:j]):
        return ""
    if dv_cuoi in ("triệu", "tỷ", "tỉ") and tong % _DON_VI[dv_cuoi] == 0:
        so = f"{tong // _DON_VI[dv_cuoi]} {dv_cuoi}"          # "ba triệu" -> "3 triệu" (đúng kiểu đọc)
    else:
        so = f"{tong:,}".replace(",", ".")
    sau = tu[j:]
    if len(sau) >= 2 and sau[0].lower() == "phần" and sau[1].lower() == "trăm":
        so, sau = so + "%", sau[2:]
    return " ".join(tu[:i] + [so] + sau)


def _toi_da_vai(x):
    """Số vai tối đa: cảnh LIỆT KÊ tới 6 (mỗi mục một vai), cảnh thường 4."""
    if str(x.get("bo_cuc") or "").lower() == "liet_ke":
        return 6
    return 3 if str(x.get("khuon") or "") == "hanh_dong" else 4


def _vt(v):
    """Chỗ đứng ChatGPT ghi (có thể có dấu: "giữa", "trái", "phải") -> trai/giua/phai hoặc ""."""
    import unicodedata
    t = unicodedata.normalize("NFD", str(v or "")).encode("ascii", "ignore").decode().lower().strip()
    return t if t in ("trai", "giua", "phai") else ""          # 13/10: hai hành động cách hơn 4 s -> tắt cảnh ở giữa, bật lại đúng lúc hành động sau
LAM = {"xuat_hien", "bien_thanh", "bay_toi", "tan_cong", "bao_vay", "lan_ra", "sinh_soi", "bo_chay", "an", "mang_di",
       "lon_len", "bien_mat", "tach_ra", "ket_hop", "gam", "keo_di", "thay_the", "thu_nho"}
BAN_DO = ("khoanh_vung", "duong_di", "lan_rong")
VE_BAN_DO = ("ban_do_ve",)   # 14/10 user: địa điểm nhắc NHANH -> bản đồ AI vẽ (đa phong cách) thay vì vệ tinh phóng từ trên cao


def _ve_ban_do(x):
    """Bản đồ AI vẽ cho một địa điểm -> "bando/<băm>.png" (trong remotion/public) hoặc None (chấp nhận có chữ)."""
    import hashlib
    import anh_ve
    from common import CACHE_CHUNG, doc_json, ghi_json
    from PIL import Image
    pub = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion", "public", "bando")
    os.makedirs(pub, exist_ok=True)
    # 14/10 user: phong cách CỐ ĐỊNH "siêu thực ảnh chụp vệ tinh" (đa dạng nằm ở chuyển động máy quay, 4 kiểu)
    noi = str(x.get("ve") or x.get("dia_danh") or "")
    prompt = (f"Create a hyper-realistic satellite photograph (like a real high-resolution orbital image, natural colours, "
              f"real terrain, coastlines, rivers, cities and clouds) of {noi}. The place {x.get('dia_danh', '')} is exactly at the "
              f"CENTRE of the image and subtly highlighted (slightly brighter, a soft glowing border) while the surroundings "
              f"stay natural and slightly darker. Wide 16:9 landscape, top-down view. Absolutely NO text anywhere: no place "
              f"names, no labels, no letters, no numbers, no legend, no compass, no frame, no map graphics.")
    k = hashlib.md5((prompt + "|cat83").encode("utf-8")).hexdigest()[:14]
    so = os.path.join(CACHE_CHUNG, "ban_do_ve.json")
    v = (doc_json(so, {}) or {}).get(k)
    if v and os.path.isfile(os.path.join(pub, os.path.basename(v))):
        return v
    for lan in range(2):
        f = anh_ve.ve_prompt(prompt if lan == 0 else prompt + " Remove ALL writing.", pub, f"_{k}_{lan}.png")
        if not f:
            return None
        out = os.path.join(pub, f"{k}.png")
        im = Image.open(f).convert("RGB")
        # dấu ✦ Gemini tự đóng ở ~(91% ngang, 84% dọc): cắt 17% mép PHẢI + DƯỚI (giữ 16:9); tâm vùng (giữa ảnh gốc) nay ở
        # 0,5/0,83 ≈ 60% khung -> MinhHoa.jsx BanDoVe đặt ghim tại TAM_BDV
        w, h = im.size
        im = im.crop((0, 0, int(w * 0.83), int(h * 0.83))).resize((w, h), Image.LANCZOS)
        im.save(out)
        os.remove(f)
        d = doc_json(so, {}) or {}                           # 15/10 user: ảnh AI vẽ CHẤP NHẬN có chữ — không soát chữ
        d[k] = f"bando/{k}.png"
        ghi_json(so, d)
        return f"bando/{k}.png"
    return None


def _tim(cau_ds, moc):
    """Giờ (giây) giọng đọc nói chữ đầu của cụm moc trong các câu cau_ds; None nếu không thấy."""
    from lop_phu import _chuan
    m = _chuan(moc or "")
    if not m:
        return None
    for c in cau_ds:
        tu = c.get("tu") or []
        phang = [(k, x) for k, t in enumerate(tu) for x in _chuan(t[0])]
        tot, vt = 0, None
        for s in range(len(phang)):
            n = 0
            while n < len(m) and s + n < len(phang) and phang[s + n][1] == m[n]:
                n += 1
            if n > tot:
                tot, vt = n, phang[s][0]
        if vt is not None and tot >= min(2, len(m)):
            return float(tu[vt][1])
    return None


def _tim_doan(cau_ds, moc):
    """(t_dau, t_cuoi) của cụm moc trong cau_ds; (None, None) nếu không thấy."""
    from lop_phu import _chuan
    m = _chuan(moc or "")
    if not m:
        return None, None
    for c in cau_ds:
        tu = c.get("tu") or []
        phang = [(k, x) for k, t in enumerate(tu) for x in _chuan(t[0])]
        tot, vt_dau, vt_cuoi = 0, None, None
        for s in range(len(phang)):
            n = 0
            while n < len(m) and s + n < len(phang) and phang[s + n][1] == m[n]:
                n += 1
            if n > tot:
                tot = n
                vt_dau = phang[s][0]
                vt_cuoi = phang[s + n - 1][0]
        if vt_dau is not None and tot >= min(2, len(m)):
            return float(tu[vt_dau][1]), float(tu[vt_cuoi][2])
    return None, None


def _trich_su_kien(c):
    """Trích xuất các mốc thời gian / năm (kèm t_bd, t_kt) có trong câu c."""
    import re
    tu = c.get("tu") or []
    if not tu:
        return []
    SO_TU = {"một", "hai", "ba", "bốn", "năm", "lăm", "sáu", "bảy", "bẩy", "tám", "chín", "mười", "mươi",
             "trăm", "nghìn", "ngàn", "tư", "lẻ", "linh"}
    groups, cur = [], []
    for i, w in enumerate(tu):
        raw = w[0].strip()
        clean = re.sub(r"[^\w\s]", "", raw.lower()).strip()
        has_punct = bool(re.search(r"[,;.\-]", raw))
        if clean in SO_TU:
            cur.append((i, raw, clean, float(w[1]), float(w[2])))
            if has_punct:
                groups.append(cur)
                cur = []
        else:
            if cur:
                groups.append(cur)
                cur = []
    if cur:
        groups.append(cur)

    ds_nam = []
    # (a) Thế kỷ
    for i, w in enumerate(tu):
        raw = re.sub(r"[^\w\s]", "", w[0].lower()).strip()
        if raw == "thế" and i + 1 < len(tu) and re.sub(r"[^\w\s]", "", tu[i + 1][0].lower()).strip() == "kỷ":
            j = i + 2
            tk_words = []
            while j < len(tu) and re.sub(r"[^\w\s]", "", tu[j][0].lower()).strip() in SO_TU:
                tk_words.append(tu[j])
                j += 1
            if tk_words:
                tk_so = so_chu_so(" ".join(re.sub(r"[^\w\s]", "", x[0].lower()) for x in tk_words)).replace(".", "")
                ds_nam.append({
                    "nam": f"THẾ KỶ {tk_so}",
                    "t_bd": float(tu[i][1]),
                    "t_kt": float(tk_words[-1][2]),
                })

    # (b) Thập niên
    for i, w in enumerate(tu):
        raw = re.sub(r"[^\w\s]", "", w[0].lower()).strip()
        if raw == "thập" and i + 1 < len(tu) and re.sub(r"[^\w\s]", "", tu[i + 1][0].lower()).strip() == "niên":
            j = i + 2
            tn_words = []
            while j < len(tu) and re.sub(r"[^\w\s]", "", tu[j][0].lower()).strip() in SO_TU:
                tn_words.append(tu[j])
                j += 1
            if tn_words:
                tn_so = so_chu_so(" ".join(re.sub(r"[^\w\s]", "", x[0].lower()) for x in tn_words)).replace(".", "")
                t_bd = float(tu[i - 1][1]) if i > 0 and re.sub(r"[^\w\s]", "", tu[i - 1][0].lower()).strip() == "đầu" else float(tu[i][1])
                prefix = "ĐẦU " if (i > 0 and re.sub(r"[^\w\s]", "", tu[i - 1][0].lower()).strip() == "đầu") else ""
                ds_nam.append({
                    "nam": f"{prefix}THẬP NIÊN {tn_so}",
                    "t_bd": t_bd,
                    "t_kt": float(tn_words[-1][2]),
                })

    # (c) Tháng ... năm ...
    for i, w in enumerate(tu):
        raw = re.sub(r"[^\w\s]", "", w[0].lower()).strip()
        if raw == "tháng" and i + 1 < len(tu) and re.sub(r"[^\w\s]", "", tu[i + 1][0].lower()).strip() in SO_TU:
            thang_so = so_chu_so(re.sub(r"[^\w\s]", "", tu[i + 1][0].lower())).replace(".", "")
            j = i + 2
            if j < len(tu) and re.sub(r"[^\w\s]", "", tu[j][0].lower()).strip() == "năm":
                k = j + 1
                nam_words = []
                while k < len(tu) and re.sub(r"[^\w\s]", "", tu[k][0].lower()).strip() in SO_TU:
                    nam_words.append(tu[k])
                    k += 1
                if nam_words:
                    nam_so = so_chu_so(" ".join(re.sub(r"[^\w\s]", "", x[0].lower()) for x in nam_words)).replace(".", "")
                    if len(nam_so) > 4 and nam_so.startswith("2000"):
                        nam_so = "20" + nam_so[-2:]
                    ds_nam.append({
                        "nam": f"THÁNG {thang_so}/{nam_so}",
                        "t_bd": float(tu[i][1]),
                        "t_kt": float(nam_words[-1][2]),
                    })

    # (d) Nhóm số năm thông thường (18xx, 19xx, 20xx)
    for g in groups:
        clean_phrase = " ".join(x[2] for x in g)
        if clean_phrase.startswith("năm "):
            clean_phrase = clean_phrase[4:]
        val = so_chu_so(clean_phrase).replace(".", "")
        if val.startswith("2000") and len(val) >= 5:
            val = "20" + val[-2:]
        if re.match(r"^(1[89]\d\d|20\d\d)$", val):
            ds_nam.append({
                "nam": val,
                "t_bd": g[0][3],
                "t_kt": g[-1][4],
            })

    ds_nam.sort(key=lambda z: (z["t_bd"], -z["t_kt"]))
    ket_qua = []
    for it in ds_nam:
        if not any(it["t_bd"] >= k["t_bd"] and it["t_kt"] <= k["t_kt"] for k in ket_qua):
            ket_qua.append(it)
    return ket_qua



def _moc_con(ds, cau_ds, bd, dai, tang=False):
    """Giờ (tính từ đầu clip) cho từng bộ phận / bước theo moc riêng; thiếu thì rải đều; tang=True: bắt tăng dần."""
    n = len(ds)
    ra = []
    for k, m in enumerate(ds):
        t = _tim(cau_ds, m.get("moc"))
        deu = 0.5 + (dai * 0.72 - 0.5) * (k / max(1, n - 1))
        ra.append(round(t - bd, 2) if t is not None and 0.2 <= t - bd <= dai - 0.8 else round(deu, 2))
    if tang:
        for k in range(1, n):
            ra[k] = max(ra[k], ra[k - 1] + 0.5)
        ra = [min(t, dai - 0.6) for t in ra]
    return ra


def _gio_dien_canh(x, ds_c, ke):
    """13/10 user: "voice nói đến đâu thì hành động đến đó". Giờ TUYỆT ĐỐI theo giọng:
    - mỗi hành động bật đúng lúc đọc tới cụm moc của nó (tìm trong các câu của cảnh + câu kế tiếp); KHÔNG thấy -> BỎ
      hành động đó (không rải đều đoán mò);
    - cảnh bật ngay trước hành động đầu (0,35 s); mỗi vai hiện khi được NHẮC TÊN hoặc khi bắt đầu tham gia hành động
      (sớm hơn trong hai mốc, không trước lúc cảnh bật); vai là kết quả bien_thanh / chủ thể xuat_hien thì hiện ở hành động đó;
    - cảnh tắt sau hành động cuối 2-3,5 s (kéo tới hết câu nếu lời còn nói tiếp).
    -> {bd, dai, hd: [{ai, lam, toi, nhan, t(tuyệt đối)}], vao: [giờ tuyệt đối | None]} hoặc None."""
    tim_o = ds_c                                             # 14/10 user: không lấn sang câu mới -> không tìm mốc ở câu kế
    chan = (ke["t0"] - 0.05) if ke else max(c["t1"] for c in ds_c) + 0.4   # cảnh phải tắt trước khi câu kế bắt đầu
    vai = x.get("vai") or []
    hd = []
    for y in (x.get("hanh_dong") or [])[:8 if str(x.get("bo_cuc") or "").lower() == "liet_ke" else 5]:   # liệt kê: mỗi mục trước+sau
        try:
            ai = int(y.get("ai"))
            toi = None if y.get("toi") in (None, "", "null") else int(y.get("toi"))
        except (TypeError, ValueError, AttributeError):
            continue
        if y.get("lam") not in LAM or not (0 <= ai < len(vai)) or (toi is not None and not (0 <= toi < len(vai)) or toi == ai):
            continue
        if y["lam"] == "bien_thanh" and toi is None:
            continue
        if y["lam"] == "bien_thanh" and "same as" not in str((vai[toi] or {}).get("ve") or "").lower():
            y = dict(y, lam="xuat_hien")                     # 14/10: không biến thứ này thành THỨ KHÁC — thứ kia hiện thêm
            ai, toi = toi, None
        t = _tim(tim_o, y.get("moc"))
        if t is None:
            continue
        hd.append({"ai": ai, "lam": y["lam"], "toi": toi, "nhan": str(y.get("nhan") or ""), "t": t})
    hd.sort(key=lambda h: h["t"])
    khuon = str(x.get("khuon") or "")
    if not hd and khuon in ("con_so", "so_sanh") + TOAN_Y:     # khuôn con số / cả ý: không cần nhịp chuyển động
        t = _tim(ds_c, x.get("moc") if khuon in ("tong_quat", "liet_ke") else (x.get("moc_so") or x.get("moc")))
        if t is None and khuon in ("tong_quat", "liet_ke"):
            t = ds_c[0]["t0"]                                # 14/10: cả ý -> mốc không khớp thì từ đầu câu
        if t is not None:
            hd = [{"ai": 0, "lam": "xuat_hien", "toi": None, "nhan": "", "t": t}]
    # 14/10 user: nhịp quá sát (săn rồi chết ngay) -> nhịp sau chờ nhịp trước diễn xong (>= 1,2 s); không vượt cuối câu
    goc_t = [h["t"] for h in hd]
    for cach in (1.2, 1.0, 0.85, 0.7):                       # 14/10: câu dồn nhiều nhịp -> nhịp sát lại chứ không bỏ nhịp cuối
        gon = []
        for h, t in zip(hd, goc_t):
            h["t"] = t
            if gon:
                h["t"] = max(h["t"], gon[-1]["t"] + cach)
                if h["t"] > chan - 0.8:
                    continue                                 # hết chỗ trong câu: bỏ nhịp này thay vì lấn câu sau
            gon.append(h)
        if len(gon) == len(hd):
            break
    hd = gon
    for h in hd:                                             # 14/10 user: hình đi trước lời
        h["t"] = round(h["t"] - DI_TRUOC, 2)
    if not hd:
        return []
    def _cau_cua(t):                                         # câu chứa giờ t (trong các câu của cảnh + câu kế)
        return next((c["i"] for c in tim_o if c["t0"] - 0.3 <= t <= c["t1"] + 0.3), None)
    nhom = [[hd[0]]]
    for h in hd[1:]:
        # 13/10 user: diễn TRỌN câu tới kết quả -> KHÔNG tách giữa một câu; chỉ tách khi hai nhịp cách > KHOANG_NGAT
        # VÀ nằm ở hai câu khác nhau (lời giữa chúng nói chuyện khác)
        if h["t"] - nhom[-1][-1]["t"] > KHOANG_NGAT and _cau_cua(h["t"]) != _cau_cua(nhom[-1][-1]["t"]):
            nhom.append([h])
        else:
            nhom[-1].append(h)
    het_cau = max(c["t1"] for c in ds_c) + 0.3
    ra = []
    dau_cau = ds_c[0]["t0"] - 0.2
    ten_som = [t for t in (_tim(tim_o, (v or {}).get("ten")) if isinstance(v, dict) else None for v in vai)
               if t is not None and t >= dau_cau]
    for k, g in enumerate(nhom):
        bd = g[0]["t"] - 0.35
        if k == 0 and ten_som:                               # 14/10: mở cảnh ở lần nhắc SỚM NHẤT (nhịp đầu hoặc tên vai
            bd = min(bd, min(ten_som) - DI_TRUOC - 0.35)     # được đọc) — vai chỉ được nhắc tên vẫn hiện đúng lúc
        bd = max(0.0, bd)                                    # đi trước lời nhưng không trước đầu video
        cuoi = g[-1]["t"]
        tran = nhom[k + 1][0]["t"] - 0.9 if k + 1 < len(nhom) else 1e9
        ket = next((c["t1"] for c in tim_o if c["t0"] - 0.3 <= cuoi <= c["t1"] + 0.3), cuoi)   # hết câu chứa nhịp cuối
        it_nhat = cuoi + HOAT_CANH + GIU_CUOI                # nhịp cuối hiện xong + đứng yên 2 s cho người xem kịp hiểu
        kt = max(min(tran, max(it_nhat, min(max(het_cau, ket + 0.3), cuoi + 5.0))), min(it_nhat, tran + 0.9))
        kt = min(kt, chan)                                   # 14/10 user: tuyệt đối không lấn sang câu mới
        if khuon in TOAN_Y:                                  # 14/10 user: hiện một lần, đứng tới HẾT Ý (hết các câu của cảnh)
            kt = max(kt, min(het_cau, chan))
        vao = []
        for i, v in enumerate(vai):
            dung = [h["t"] for h in g if h["ai"] == i or h["toi"] == i]
            sau = any(h["lam"] in ("xuat_hien", "thay_the") and h["ai"] == i or h["lam"] == "bien_thanh" and h["toi"] == i
                      for h in g)
            ten = _tim(tim_o, (v or {}).get("ten")) if isinstance(v, dict) else None
            if ten is not None and not (bd - 0.5 <= ten <= kt):
                ten = None                                   # tên được nhắc ở nhóm khác
            if sau:
                vao.append(None)
            elif dung or ten is not None:                    # 14/10: vi_tri CHỈ là chỗ đứng — vai hiện khi được nhắc / tham gia
                vao.append(max(bd, min([t - 0.35 for t in dung] + ([ten - DI_TRUOC] if ten is not None else []))))
            else:
                vao.append(None)                             # vai không dính tới nhóm này: không hiện
        if khuon == "co_che" and vao:                        # cơ chế: vật NGOÀI hiện trước, kính lúp mở sau
            co = [v for v in vao if v is not None]
            vao[0] = min(co) if co else bd
        if kt - bd < 1.6:
            continue
        t_so = _tim(ds_c, x.get("moc_so")) if khuon == "con_so" else None
        if t_so is not None:
            t_so -= DI_TRUOC
        ra.append({"bd": round(bd, 2), "dai": round(kt - bd, 2), "hd": g, "vao": vao, "t_so": t_so})
    gop = []                                                 # hai phần cách nhau < 1 s: nối liền (không nháy tắt-bật)
    for r in ra:
        if gop and r["bd"] - (gop[-1]["bd"] + gop[-1]["dai"]) < 1.0:
            p0 = gop[-1]
            p0["hd"] = p0["hd"] + r["hd"]
            p0["vao"] = [a if a is not None and (b is None or a <= b) else b for a, b in zip(p0["vao"], r["vao"])]
            p0["dai"] = round(r["bd"] + r["dai"] - p0["bd"], 2)
        else:
            gop.append(r)
    return gop


def _render_so_do(jobs):
    """jobs: [(khoa, giay, props)] -> {khoa: mp4|None}. Cache theo props ở cache/minh_hoa/."""
    import nen_ban_do
    from common import CACHE_CHUNG
    thu = os.path.join(CACHE_CHUNG, "minh_hoa")
    os.makedirs(thu, exist_ok=True)
    ra, viec = {}, []
    for khoa, giay, pr in jobs:
        out = os.path.join(thu, hashlib.md5((json.dumps(pr, ensure_ascii=False, sort_keys=True) + f"|{giay}|v46")
                                            .encode()).hexdigest()[:16] + ".mp4")
        ra[khoa] = out
        if not (os.path.isfile(out) and os.path.getsize(out) > 5000):
            viec.append({"comp": "MinhHoa", "giay": giay, "out": out, "props": pr})
    if viec:
        log(f"    Remotion dựng {len(viec)} sơ đồ minh hoạ (biểu đồ số liệu / mốc thời gian / HUD)…")
        nen_ban_do._render(viec, thu, ten="sơ đồ minh hoạ")                # noqa: SLF001
    return {k: (v if os.path.isfile(v) and os.path.getsize(v) > 5000 else None) for k, v in ra.items()}


def lap(cau, canh, de_xuat, SEC=1_000_000):
    """[{kieu, cau, bd, dai, file, mo_ta}] không chồng nhau, sắp theo giờ."""
    import bang_giay
    import nen_ban_do as B
    theo_i = {c["i"]: c for c in cau}
    vt = [(t / SEC, (t + d) / SEC) for c in canh for (t, d, o) in c["_os"] if o.get("ban_do")]   # bản đồ có sẵn trên track hình
    ung_hud, ung_ai = [], []
    for x in de_xuat:
        k = x.get("kieu")
        if k not in SO_DO + BAN_DO + VE_BAN_DO:
            continue
        c = theo_i.get(x["cau"])
        if not c:
            continue
        ds_c = [theo_i[j] for j in range(x["cau"], x.get("den_cau", x["cau"]) + 1) if j in theo_i]
        bd = round(c["t0"], 2)
        kt = ds_c[-1]["t1"]
        dai = round(max(1.8, kt - bd), 2)

        if k in ("tai_hien", "dien_canh"):
            # 18/10 user: Ảnh AI chuyển thẳng sang CapCut timeline (không render Remotion)
            # 18/10 user ("tích tắc là hết câu ảnh đã mất, nháy 1 cái footage"): phủ cả quãng nghỉ cuối câu tới khi câu sau
            # bắt đầu (mốc câu là ước tính, giọng thật thường kéo quá t1 một chút)
            ke_ = theo_i.get(ds_c[-1]["i"] + 1)
            if ke_ and 0 <= ke_["t0"] - kt < 1.5:
                kt = ke_["t0"]
                dai = round(max(1.8, kt - bd), 2)
            t_m = _tim(ds_c, x.get("moc_1") or x.get("moc"))     # 19/10: ảnh 1 hiện đúng lúc giọng tới cụm của nó
            if t_m is not None and bd + 0.8 < t_m - DI_TRUOC < kt - 2.0:
                bd = round(t_m - DI_TRUOC, 2)
                dai = round(kt - bd, 2)
            ung_ai.append((bd, dai, "tai_hien", x, ds_c))
            continue

        t = _tim(ds_c, x.get("moc_so") or x.get("moc"))
        if k in BAN_DO or k in VE_BAN_DO or k == "ban_do_ve":
            kt_hud = ds_c[-1]["t1"] + 0.5
            dai = round(max(3.8, min(8.0, kt_hud - bd)), 2)
        elif k == "su_kien":
            ds_nam_c = _trich_su_kien(c)
            if ds_nam_c:
                bd = round(ds_nam_c[0]["t_bd"], 2)
                t_cuoi = ds_nam_c[-1]["t_kt"]
                kt_hud = round(t_cuoi + 1.0, 2)
                dai = round(max(1.8, kt_hud - bd), 2)
                if len(ds_nam_c) > 1:
                    x["cac_nam"] = [{"nam": r["nam"], "t": round(r["t_bd"] - bd, 2)} for r in ds_nam_c]
                    x["nam"] = ", ".join(r["nam"] for r in ds_nam_c)
                else:
                    x["cac_nam"] = None
                    x["nam"] = x.get("nam") or ds_nam_c[0]["nam"]
            else:
                t_dau, t_cuoi = _tim_doan(ds_c, x.get("moc"))
                if t_dau is not None:
                    bd = round(t_dau, 2)
                    kt_hud = round((t_cuoi if t_cuoi else t_dau + 1.0) + 1.0, 2)
                    dai = round(max(1.8, kt_hud - bd), 2)
                else:
                    bd = round(c["t0"], 2)
                    dai = 2.0
        elif k in ("so_sanh", "song", "con_so"):
            bd = round(t if t is not None else c["t0"], 2)
            kt_hud = ds_c[-1]["t1"] + 0.1
            dai = round(max(2.2, min(3.5, kt_hud - bd)), 2)
        else:
            kt_hud = ds_c[-1]["t1"] + 0.3
            dai = round(max(2.5, min(5.5, kt_hud - bd)), 2)

        ke = theo_i.get(x.get("den_cau", x["cau"]) + 1)
        if ke:
            dai = round(min(dai, ke["t0"] - 0.05 - bd), 2)
        if dai < 1.4:
            continue
        if any(bd < b_ + 0.3 and bd + dai > a_ - 0.3 for a_, b_ in vt):
            continue
        ung_hud.append((bd, dai, k, x, ds_c))

    # Xử lý ung_ai: sắp theo giờ, xén mép và snap cảnh liền kề
    nhan_ai = []
    for u in sorted(ung_ai, key=lambda z: z[0]):
        u = list(u)
        if nhan_ai:
            prev = nhan_ai[-1]
            prev_end = round(prev[0] + prev[1], 2)
            if u[0] < prev_end:
                prev[1] = round(max(1.8, u[0] - prev[0]), 2)
            elif u[0] - prev_end < 1.5:                      # 18/10: hở ngắn giữa hai chuỗi -> kéo chuỗi trước nối liền
                prev[1] = round(u[0] - prev[0], 2)           # (không lộ footage một nhịp, chuỗi sau vẫn đúng mốc câu)
        nhan_ai.append(u)

    def _uu(u):
        k_ = u[2]
        if k_ in ("su_kien", "con_so", "so_sanh", "giai_thich"):
            return 0
        if k_ in VE_BAN_DO or k_ in BAN_DO:
            return 1
        return 2

    nhan_hud = []
    for u in sorted(ung_hud, key=lambda z: (_uu(z), z[0])):
        u = list(u)
        if any(u[0] < v[0] + v[1] + 0.1 and v[0] < u[0] + u[1] + 0.1 for v in nhan_hud):
            continue
        nhan_hud.append(u)
    nhan_hud.sort(key=lambda z: z[0])
    gon_hud = []                                             # 19/10 user (C): câu có cả mốc thời gian + ảnh AI giữ cả hai
    for u in nhan_hud:
        dau_ai = [a[0] for a in nhan_ai if u[0] - 0.05 <= a[0] < u[0] + u[1] and a[0] - u[0] >= 1.2]
        if dau_ai:
            u[1] = round(min(dau_ai) - u[0], 2)
        if any(a[0] < u[0] + u[1] - 0.05 and u[0] < a[0] + a[1] for a in nhan_ai):
            continue                                         # vẫn chồng ảnh AI (HUD có nền video, sẽ che ảnh) -> bỏ HUD
        gon_hud.append(u)
    nhan_hud = gon_hud

    diem_cat = sorted(list(set(
        [round(t / SEC, 3) for cc in canh for (t, d, o) in cc.get("_os", [])] +
        [round((t + d) / SEC, 3) for cc in canh for (t, d, o) in cc.get("_os", [])]
    )))

    for i in range(len(nhan_hud)):
        if nhan_hud[i][2] == "su_kien":
            continue
        bd_i, dai_i = nhan_hud[i][0], nhan_hud[i][1]
        kt_i = round(bd_i + dai_i, 2)
        truoc_kt = round(nhan_hud[i - 1][0] + nhan_hud[i - 1][1] + 0.05, 2) if i > 0 else 0.0
        sau_bd = round(nhan_hud[i + 1][0] - 0.05, 2) if i < len(nhan_hud) - 1 else 1e9

        gant_kt = [c for c in diem_cat if abs(kt_i - c) <= 1.3 and bd_i + 1.2 <= c <= sau_bd]
        if gant_kt:
            c_tot = min(gant_kt, key=lambda c: abs(kt_i - c))
            dai_i = round(c_tot - bd_i, 2)
            kt_i = c_tot
        gant_bd = [c for c in diem_cat if abs(bd_i - c) <= 0.5 and truoc_kt <= c <= kt_i - 1.2]
        if gant_bd:
            c_tot = min(gant_bd, key=lambda c: abs(bd_i - c))
            bd_i = c_tot
            dai_i = round(kt_i - bd_i, 2)
        nhan_hud[i][0] = round(bd_i, 2)
        nhan_hud[i][1] = round(dai_i, 2)

    # ---- bản đồ cho HUD
    viec, ma, vt_canh = [], {}, []
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan_hud):
        pt = x.get("phuong_tien") if x.get("phuong_tien") in ("may_bay", "tau_thuy", "tau_hoa", "xe", "di_bo") else ""
        if k == "khoanh_vung" and x.get("dia_danh"):
            # 22/10 user ("từ ngoài trái đất, đánh dấu lãnh thổ"): bản đồ VỆ TINH THẬT (ban_do.clip_dia_danh — từ vũ
            # trụ bay xuống, viền lãnh thổ OpenStreetMap, ghim + tên) thay khung BanDoNen cũ
            vt_canh.append((n, dai, x))
            ma[n] = x.get("ten_vi") or x["dia_danh"]
        elif k == "duong_di" and x.get("tu") and x.get("den"):
            viec.append((n, dai, B.chuan_bi_duong, [x["tu"], x["den"], x.get("tu_vi") or None, x.get("den_vi") or None, pt]))
            ma[n] = f"{x.get('tu_vi') or x['tu']} → {x.get('den_vi') or x['den']}"
        elif k == "lan_rong" and x.get("goc") and isinstance(x.get("noi"), list):
            noi = [[str(y.get("en") or ""), str(y.get("vi") or "")] for y in x["noi"] if isinstance(y, dict) and y.get("en")]
            viec.append((n, dai, B.chuan_bi_lan_rong, [x["goc"], noi[:6], x.get("goc_vi") or None, pt]))
            ma[n] = f"{x.get('goc_vi') or x['goc']} → {len(noi)} nơi"
    clip = B.dung_clip(viec) if viec else {}
    if vt_canh:
        import ban_do
        for n, dai, x in vt_canh:                            # tuần tự: mỗi lần dựng dùng chung public/ban_do
            clip[n] = ban_do.clip_dia_danh(x["dia_danh"], x.get("ten_vi") or "", dai, khoanh=True)

    from concurrent.futures import ThreadPoolExecutor

    for u in nhan_ai:
        u[3]["_dai"] = u[1]
        u[3]["_lich"] = _lich_anh(u[3], u[0], u[1], u[4])   # 23/10: lịch ảnh nối tiếp (mỗi ảnh <= 5 s)
        u[3]["_text"] = " ".join(str(c.get("text") or "") for c in u[4])   # cho bước soát ảnh
    for u in nhan_hud:
        u[3]["_dai"] = u[1]

    bdv = [u[3] for u in nhan_hud if u[2] == "ban_do_ve"]
    th = [u[3] for u in nhan_ai]

    def _ve_tai_hien(x):
        lich = x.get("_lich") or []
        prompts = [l[1] for l in lich]
        if not prompts:
            return []

        import hashlib, anh_ve
        PUB = os.path.join(ROOT, "remotion", "public")
        os.makedirs(PUB, exist_ok=True)
        ds_ten, ve_ds, huong_ds, t_ds = [], [], [], []
        mau = None                                           # 19/10 user: ảnh 1 là NGUYÊN LIỆU cho ảnh 2-3 (cùng vật chính)
        for i, p in enumerate(prompts):
            kid = hashlib.md5(((mau or "") + "|" + p).encode("utf-8")).hexdigest()[:14]
            ten_f = f"tai_hien_{kid}_{i}.png"
            f_anh = os.path.join(PUB, ten_f)
            if not (os.path.isfile(f_anh) and os.path.getsize(f_anh) > 5000):
                p_full = lenh_ve(p, x.get("thoi_dai"), co_mau=bool(mau))
                try:
                    f_anh = anh_ve.ve_prompt(p_full, PUB, ten_f, tep=[mau] if mau else None, timeout=120)
                except Exception as e:
                    log(f"    ! vẽ tái hiện [{i+1}] lỗi: {e}")
                    f_anh = None
                # 19/10 user ("ảnh trông ngu"): Gemini xem lại ảnh vừa vẽ; trượt -> vẽ lại kèm đúng lỗi (tối đa SOAT_VE_LAI)
                for _l in range(SOAT_VE_LAI if f_anh and os.path.isfile(f_anh) else 0):
                    dat, loi = anh_ve.soat(f_anh, x.get("_text"), p)
                    if dat:
                        break
                    log(f"    ảnh tái hiện câu {x.get('cau')} [{i+1}] trượt soát: {loi[:140]} -> vẽ lại")
                    try:
                        f2 = anh_ve.ve_prompt(p_full + " FIX these problems of the previous attempt: " + loi, PUB,
                                              f"_soat_{kid}_{_l}.png", tep=[mau] if mau else None, timeout=120)
                    except Exception:                         # noqa: BLE001
                        f2 = None
                    if not (f2 and os.path.isfile(f2)):
                        break
                    os.replace(f2, f_anh)
            if f_anh and os.path.isfile(f_anh):
                ds_ten.append(f_anh)
                ve_ds.append(p)
                huong_ds.append(lich[i][2])                  # 22/10: hướng chuyển động theo hành động của ảnh
                t_ds.append(lich[i][0])                      # 23/10: giờ ảnh này bắt đầu (ảnh vẽ hỏng -> ảnh trước đứng thay)
                mau = mau or f_anh                           # mọi ảnh sau lấy ẢNH ĐẦU làm mẫu (không trôi dần)
        x["_ve_ds"] = ve_ds                                  # 19/10 user: lưu câu mô tả từng ảnh (sửa tay trên giao diện)
        x["_huong_ds"] = huong_ds
        x["_t_ds"] = t_ds
        return ds_ten

    log(f"    vẽ {len(bdv)} bản đồ, kiểm tra/vẽ {len(th)} chuỗi ảnh AI…")
    import anh_ve
    with ThreadPoolExecutor(anh_ve.so_luong_ve()) as ex:        # 22/10 user: số luồng = số tài khoản cookie (chia đều)
        for x, a in zip(bdv, ex.map(_ve_ban_do, bdv)):
            x["_anh"] = a
        for x, a in zip(th, ex.map(_ve_tai_hien, th)):
            x["_ds_anh"] = a
            x["_anh"] = a[0] if a else None

    # Phân chia ảnh AI thành các lát cắt phan_doan đưa trực tiếp lên CapCut
    ra_anh_ai = []
    for bd, dai, k, x, ds_c in nhan_ai:
        ds_anh = x.get("_ds_anh") or []
        if not ds_anh:
            continue
        n_anh = len(ds_anh)
        phan_doan = []
        _hd = list(x.get("_huong_ds") or [])

        def _hg(k_, _hd=_hd, _n=len(ds_anh)):
            k_ = min(k_, _n - 1)
            return _hd[k_] if k_ < len(_hd) else None
        sfx_th = [{"t": round(bd + 0.2, 2), "kieu": "whoosh", "ly_do": "tái hiện AI"}]

        t_ds = list(x.get("_t_ds") or [bd])                 # 23/10: chỗ đổi ảnh theo lịch (AI chốt + ảnh nối tiếp)
        t_ds[0] = bd
        for k_ in range(n_anh):
            t0 = t_ds[k_] if k_ < len(t_ds) else bd
            t1 = t_ds[k_ + 1] if k_ + 1 < len(t_ds) else bd + dai
            phan_doan.append({"bd": round(t0, 2), "dai": round(t1 - t0, 2), "file": ds_anh[k_], "huong": _hg(k_)})
            if k_:
                sfx_th.append({"t": round(t0, 2), "kieu": "whoosh", "ly_do": f"chuyển cảnh AI {k_ + 1}"})

        ra_anh_ai.append({
            "cau": x["cau"],
            "bd": bd,
            "dai": dai,
            "ds_anh": ds_anh,
            "ve": list(x.get("_ve_ds") or []),               # câu mô tả từng ảnh, cùng thứ tự ds_anh
            "thoi_dai": x.get("thoi_dai") or "",
            "text": x.get("_text") or "",
            "phan_doan": phan_doan,
            "mo_ta": f"ảnh AI: {x.get('tieu_de') or 'chuỗi phân cảnh'}",
            "am": sfx_th
        })

    # ---- sơ đồ HUD trên nền video tối (chỉ render Remotion cho HUD/bản đồ)
    jobs, ma_am, chu_phu = [], {}, []
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan_hud):
        if k == "ban_do_ve":
            if x.get("_anh"):
                import hashlib
                bt = int(hashlib.md5(str(x.get("dia_danh")).encode("utf-8")).hexdigest(), 16) % 4
                jobs.append((n, dai, {"kieu": "ban_do_ve", "nen": [], "anh": x["_anh"], "ten": x.get("ten_vi") or "",
                                      "bien_the": bt}))
                ma[n] = f"bản đồ vẽ (vệ tinh siêu thực): {x.get('ten_vi')}"
                ma_am[n] = [{"t": round(bd + 0.2, 2), "kieu": "whoosh", "ly_do": "bản đồ"}]
            continue
        if k not in SO_DO:
            continue
        pr = {"kieu": k, "nen": bang_giay._clips(canh, bd, bd + dai)}                      # noqa: SLF001
        # 19/10 user: KHÔNG dựng Remotion viết chữ lên video (biểu đồ cột / sóng, số, mốc năm) — thay bằng LỚP PHỦ ĐEN + CHỮ
        # TRẮNG CapCut đặt chồng lên footage thật (dung_hoan_chinh.dat_chu_phu; chữ sửa tay được trong CapCut)
        if k in ("so_sanh", "song", "con_so", "cot"):
            ben = [b for b in (x.get("ben_a"), x.get("ben_b")) if isinstance(b, dict) and str(b.get("gia_tri") or "").strip()]
            if ben and CHU_PHU:
                chu_phu.append({"kieu": "chu_phu", "cau": x["cau"], "bd": bd, "dai": dai, "mo_ta": f"số liệu: {x.get('tieu_de')}",
                                "tieu_de": str(x.get("tieu_de") or ""),
                                "cot": [{"so": str(b["gia_tri"]), "nhan": str(b.get("ten") or "")} for b in ben],
                                "am": [{"t": round(bd + 0.2, 2), "kieu": "hit", "ly_do": "số liệu"}]})
            continue
        elif k == "su_kien":
            if str(x.get("nam") or "").strip() and CHU_PHU:
                chu_phu.append({"kieu": "chu_phu", "cau": x["cau"], "bd": bd, "dai": dai, "mo_ta": f"mốc: {x.get('nam')}",
                                "tieu_de": "", "cot": [{"so": str(x["nam"]).upper(), "nhan": ""}],
                                "am": [{"t": round(bd + 0.15, 2), "kieu": "whoosh", "ly_do": "mốc sự kiện"}]})
            continue
        elif k in ("giai_thich", "quy_trinh"):
            jobs.append((n, dai, {"kieu": "giai_thich", "nen": pr["nen"], "tieu_de": x.get("tieu_de") or "", "cac_buoc": x.get("cac_buoc") or x.get("buoc") or x.get("muc") or []}))
            ma[n] = f"giải thích cơ chế: {x.get('tieu_de')}"
            ma_am[n] = [{"t": round(bd + 0.25, 2), "kieu": "whoosh", "ly_do": "giải thích"}]
            continue
        elif k == "cau_tao":
            ds = [y for y in (x.get("phan") or []) if isinstance(y, dict) and y.get("chu")][:6]
            ts = _moc_con(ds, ds_c, bd, dai)
            pr.update(chu_the=x.get("chu_the") or "", bieu_tuong=x.get("bieu_tuong") or "",
                      muc=[{"chu": y["chu"], "t": t} for y, t in zip(ds, ts)])
            ma[n] = f"cấu tạo: {x.get('chu_the')}"
        elif k in ("quy_trinh", "vong_doi"):
            ds = [y for y in (x.get("buoc") or []) if isinstance(y, dict) and y.get("chu")][:5]
            ts = _moc_con(ds, ds_c, bd, dai, tang=True)
            pr.update(tieu_de=x.get("tieu_de") or "",
                      muc=[{"chu": y["chu"], "bieu_tuong": y.get("bieu_tuong") or "", "t": t} for y, t in zip(ds, ts)])
            ma[n] = f"{'quy trình' if k == 'quy_trinh' else 'vòng đời'}: {x.get('tieu_de')}"
        if not pr["nen"] or not (pr.get("muc") or pr.get("vai")) or len(pr.get("muc") or []) < 2:
            continue
        jobs.append((n, dai, pr))

    clip.update(_render_so_do(jobs) if jobs else {})
    ra = list(chu_phu)
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan_hud):
        if clip.get(n):
            ra.append({"kieu": k, "cau": x["cau"], "bd": bd, "dai": dai, "file": clip[n], "mo_ta": ma.get(n, ""),
                       "am": ma_am.get(n, [])})
    dem = {}
    for y in ra:
        dem[y["kieu"]] = dem.get(y["kieu"], 0) + 1
    log(f"    minh hoạ Remotion: {', '.join(f'{k} {v}' for k, v in sorted(dem.items())) or 'không có'} "
        f"(đề xuất {len(ung_hud)}, sau khi lọc {len(nhan_hud)})")
    log(f"    ảnh AI CapCut: {len(ra_anh_ai)} cảnh ({sum(len(y['phan_doan']) for y in ra_anh_ai)} ảnh)")
    return ra, ra_anh_ai
