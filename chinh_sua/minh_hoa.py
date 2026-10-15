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

from common import log

MO_PHONG_DEN = 1e9          # 13/10 user duyệt sau 2 kịch bản thử: bật diễn cảnh cho TOÀN BỘ video (trước: 180 s)
SO_DO = ("dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong")
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
DI_TRUOC = 0.5             # 14/10 user: hình hiện TRƯỚC lời ~0,5 s (người xem nghe tới thì hình đã rõ)
KHOANG_GIUA = 2.0          # 14/10 user: ít nhất 2 s footage thật giữa hai lớp minh hoạ (video có nhịp, không ngợp)


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
    """Bản đồ AI vẽ cho một địa điểm -> "bando/<băm>.png" (trong remotion/public) hoặc None. Soát chữ: có chữ thì vẽ lại."""
    import hashlib
    import anh_ve
    import loc_chu
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
        thu = out[:-4] + "_thu.jpg"
        im.save(thu, quality=90)
        co_chu = loc_chu.co_chu_anh(thu)
        for z in (thu, thu + ".chu3.json"):
            if os.path.isfile(z):
                os.remove(z)
        if not co_chu:
            d = doc_json(so, {}) or {}
            d[k] = f"bando/{k}.png"
            ghi_json(so, d)
            return f"bando/{k}.png"
        log(f"    ! bản đồ vẽ '{x.get('ten_vi')}' lần {lan + 1}: có chữ — vẽ lại")
        os.remove(out)
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
        out = os.path.join(thu, hashlib.md5((json.dumps(pr, ensure_ascii=False, sort_keys=True) + f"|{giay}|v35")
                                            .encode()).hexdigest()[:16] + ".mp4")
        ra[khoa] = out
        if not (os.path.isfile(out) and os.path.getsize(out) > 5000):
            viec.append({"comp": "MinhHoa", "giay": giay, "out": out, "props": pr})
    if viec:
        log(f"    Remotion dựng {len(viec)} sơ đồ minh hoạ…")
        nen_ban_do._render(viec, thu)                                    # noqa: SLF001
    return {k: (v if os.path.isfile(v) and os.path.getsize(v) > 5000 else None) for k, v in ra.items()}


def lap(cau, canh, de_xuat, SEC=1_000_000):
    """[{kieu, cau, bd, dai, file, mo_ta}] không chồng nhau, sắp theo giờ."""
    import bang_giay
    import nen_ban_do as B
    theo_i = {c["i"]: c for c in cau}
    vt = [(t / SEC, (t + d) / SEC) for c in canh for (t, d, o) in c["_os"] if o.get("ban_do")]   # bản đồ có sẵn trên track hình
    ung = []
    for x in de_xuat:
        k = x.get("kieu")
        if k not in SO_DO + BAN_DO + VE_BAN_DO:
            continue
        c = theo_i.get(x["cau"])
        if not c:
            continue
        ds_c = [theo_i[j] for j in range(x["cau"], x.get("den_cau", x["cau"]) + 1) if j in theo_i]
        if k == "dien_canh":
            x = _chuan_hoa(x)
            for g in _gio_dien_canh(x, ds_c, theo_i.get(x.get("den_cau", x["cau"]) + 1)):
                if g["bd"] > MO_PHONG_DEN:
                    continue
                if any(g["bd"] < b_ + 0.3 and g["bd"] + g["dai"] > a_ - 0.3 for a_, b_ in vt):
                    continue
                ung.append((g["bd"], g["dai"], k, dict(x, _gio=g), ds_c))
            continue
        t = _tim([c], x.get("moc"))
        bd = round(max(c["t0"], (t if t is not None else c["t0"]) - 0.1), 2)
        kt = ds_c[-1]["t1"] + 0.4
        if k in ("mo_phong", "dien_canh") and bd > MO_PHONG_DEN:
            continue
        dai = round(max(4.5, min(8.0, kt - bd)) if k in BAN_DO else max(3.8, min(6.5, kt - bd)) if k in VE_BAN_DO
                    else max(5.5, min(14.0, kt - bd)), 2)
        ke = theo_i.get(x.get("den_cau", x["cau"]) + 1)
        if ke:                                               # 14/10 user: không lấn sang câu mới
            dai = round(min(dai, ke["t0"] - 0.05 - bd), 2)
        if dai < 2.0:
            continue
        if any(bd < b_ + 0.3 and bd + dai > a_ - 0.3 for a_, b_ in vt):
            continue                                         # trùng cảnh bản đồ vệ tinh đã có trên track hình
        ung.append((bd, dai, k, x, ds_c))
    ung.sort(key=lambda z: z[0])
    # không chồng nhau. 13/10: cảnh nối sát nhau -> CẮT ĐUÔI cảnh trước tới lúc cảnh sau bật (đuôi chỉ là phần giữ hình
    # sau hành động cuối); chỉ bỏ cảnh sau khi cắt xong cảnh trước còn < 1,2 s sau hành động cuối của nó.
    def _xong(u):                                            # sớm nhất được tắt: nhịp cuối hiện xong + giữ GIU_CUOI s
        g = (u[3] or {}).get("_gio")
        return (g["hd"][-1]["t"] if g and g.get("hd") else u[0] + 1.0) + HOAT_CANH + GIU_CUOI
    # 14/10 user: chừa >= KHOANG_GIUA s footage giữa hai lớp; khi tranh chỗ giữ lớp CÓ GIÁ TRỊ hơn (không phải lớp đến trước)
    def _uu(u):
        x_ = u[3] or {}
        kh_ = str(x_.get("khuon") or "")
        if u[2] == "dien_canh":
            return 0 if kh_ in ("tong_quat", "liet_ke", "truoc_sau", "hanh_dong", "co_che", "so_sanh", "") else 1
        return 2 if u[2] in VE_BAN_DO else 3
    nhan = []
    for u in sorted(ung, key=lambda z: (_uu(z), z[0])):
        u = list(u)
        if any(u[0] < v[0] + v[1] + KHOANG_GIUA and v[0] < u[0] + u[1] + KHOANG_GIUA for v in nhan):
            continue
        nhan.append(u)
    nhan.sort(key=lambda z: z[0])
    # ---- bản đồ
    viec, ma = [], {}
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan):
        pt = x.get("phuong_tien") if x.get("phuong_tien") in ("may_bay", "tau_thuy", "tau_hoa", "xe", "di_bo") else ""
        if k == "khoanh_vung" and x.get("dia_danh"):
            viec.append((n, dai, B.chuan_bi_vetinh, [x["dia_danh"], x.get("ten_vi") or None]))
            ma[n] = x.get("ten_vi") or x["dia_danh"]
        elif k == "duong_di" and x.get("tu") and x.get("den"):
            viec.append((n, dai, B.chuan_bi_duong, [x["tu"], x["den"], x.get("tu_vi") or None, x.get("den_vi") or None, pt]))
            ma[n] = f"{x.get('tu_vi') or x['tu']} → {x.get('den_vi') or x['den']}"
        elif k == "lan_rong" and x.get("goc") and isinstance(x.get("noi"), list):
            noi = [[str(y.get("en") or ""), str(y.get("vi") or "")] for y in x["noi"] if isinstance(y, dict) and y.get("en")]
            viec.append((n, dai, B.chuan_bi_lan_rong, [x["goc"], noi[:6], x.get("goc_vi") or None, pt]))
            ma[n] = f"{x.get('goc_vi') or x['goc']} → {len(noi)} nơi"
    clip = B.dung_clip(viec) if viec else {}
    # ---- lấy sẵn ảnh vai của mọi diễn cảnh, SONG SONG 3 cảnh (Google vẫn tuần tự do khoá trình duyệt; vẽ AI chạy song song)
    import anh_tach
    from concurrent.futures import ThreadPoolExecutor

    def _vai_canh(x):
        if str(x.get("khuon") or "") in ("tong_quat", "con_so") and x.get("ve"):
            r = anh_tach.anh_tong_quat(str(x["ve"])) if BO_VAI_AI else None   # 14/10 user: MỘT ảnh cho cả ý
            return [{"ten": "", "src": r["src"], "vi_tri": "giua", "dan": False}] if r else [None]
        ds = [y for y in (x.get("vai") or []) if isinstance(y, dict)][:_toi_da_vai(x)]
        bo = anh_tach.bo_canh_nhom(ds) if BO_VAI_AI else [None] * len(ds)
        vai, da_url = [], []
        for y, b in zip(ds, bo):
            if b:                                            # 13/10 user: AI vẽ cả bộ vai (theo nhóm nhỏ)
                vai.append({"ten": str(y.get("ten") or ""), "src": b["src"], "vi_tri": _vt(y.get("vi_tri")),
                            "dan": bool(y.get("dan"))})
                continue
            r = None
            ve = _ve_day_du(y, ds)
            if BO_VAI_AI and ve:                             # 14/10: bộ hỏng -> AI vẽ RIÊNG vai này (ảnh web cắt nền hay ra rác)
                r = anh_tach.lay("", ve=ve)
            bien_the = re.match(r"\s*same as (?:actor |subject )?(\d)", str(y.get("ve") or ""), re.I)
            if not r and bien_the:                           # trạng thái "sau" mà AI vẽ hỏng: ảnh web không cùng vật -> dùng
                goc = int(bien_the.group(1))                 # lại ảnh vai gốc (đỡ hơn một mảnh rác lạ)
                if goc < len(vai) and vai[goc]:
                    vai.append(dict(vai[goc], ten=str(y.get("ten") or ""), vi_tri=_vt(y.get("vi_tri"))))
                    continue
            if not r:
                r = anh_tach.lay(str(y.get("anh") or ""), tranh=da_url, ve=str(y.get("ve") or "") or None,
                                 truu_tuong=bool(y.get("truu_tuong")))
            if r and r.get("url"):
                da_url.append(r["url"])
            vai.append({"ten": str(y.get("ten") or ""), "src": r["src"], "vi_tri": _vt(y.get("vi_tri")),
                        "dan": bool(y.get("dan"))} if r else None)
        return vai
    dc = [u[3] for u in nhan if u[2] == "dien_canh"]
    bdv = [u[3] for u in nhan if u[2] == "ban_do_ve"]
    log(f"    lấy ảnh vai cho {len(dc)} diễn cảnh (ảnh thật tách nền / AI vẽ), vẽ {len(bdv)} bản đồ…")
    with ThreadPoolExecutor(3) as ex:
        san = list(ex.map(_vai_canh, dc))
        for x, a in zip(bdv, ex.map(_ve_ban_do, bdv)):
            x["_anh"] = a
    for x, v in zip(dc, san):
        x["_vai"] = v
    import unicodedata
    dau_tien = {}
    for x in sorted(dc, key=lambda z: z["_gio"]["bd"]):     # 14/10: một vật một ảnh xuyên suốt video
        for y, v in zip([y for y in (x.get("vai") or []) if isinstance(y, dict)], x["_vai"]):
            if not v or "same as" in str(y.get("ve") or "").lower():
                continue
            kt_ = unicodedata.normalize("NFC", str(y.get("ten") or "")).lower().strip()
            if not kt_:
                continue                                     # ảnh tổng quát không tên: không dùng chung
            if kt_ in dau_tien:
                v["src"] = dau_tien[kt_]
            else:
                dau_tien[kt_] = v["src"]
    # ---- sơ đồ trên nền video tối
    jobs, ma_am = [], {}
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan):
        if k == "ban_do_ve":
            if x.get("_anh"):
                import hashlib
                bt = int(hashlib.md5(str(x.get("dia_danh")).encode("utf-8")).hexdigest(), 16) % 4   # kiểu máy quay đổi theo nơi
                jobs.append((n, dai, {"kieu": "ban_do_ve", "nen": [], "anh": x["_anh"], "ten": x.get("ten_vi") or "",
                                      "bien_the": bt}))
                ma[n] = f"bản đồ vẽ (vệ tinh siêu thực): {x.get('ten_vi')}"
            continue
        if k not in SO_DO:
            continue
        pr = {"kieu": k, "nen": bang_giay._clips(canh, bd, bd + dai)}                      # noqa: SLF001
        if k == "dien_canh":                                 # 13/10 user: ảnh thật tách nền thay icon
            vai = [dict(v) if v else None for v in x["_vai"]]
            g = x["_gio"]
            hd = [dict(h, t=round(h["t"] - bd, 2)) for h in g["hd"]
                  if h["ai"] < len(vai) and vai[h["ai"]] and (h["toi"] is None or (h["toi"] < len(vai) and vai[h["toi"]]))]
            khuon = str(x.get("khuon") or "")
            lk = str(x.get("bo_cuc") or "").lower() == "liet_ke"
            if not any(vai):
                log(f"    ! diễn cảnh câu {x['cau']}: không có ảnh — bỏ")
                continue
            if not lk and khuon not in ("con_so", "so_sanh") + TOAN_Y and not any(h["lam"] != "xuat_hien" for h in hd) and not any(
                    h["lam"] != "xuat_hien" for h in (x.get("hanh_dong") or []) if isinstance(h, dict)):
                log(f"    ! diễn cảnh câu {x['cau']}: không còn hành động chuyển động (chỉ xuất hiện / thiếu ảnh / mốc không khớp lời) — bỏ")
                continue
            for k2, v in enumerate(vai):
                if v:
                    v["vao"] = None if k2 >= len(g["vao"]) or g["vao"][k2] is None else round(max(0.0, g["vao"][k2] - bd), 2)
            if lk:                                           # 14/10 user: LIỆT KÊ = mọi mục CÙNG hiện, chia cột, chỉ trạng thái "sau"
                den = {h["ai"]: h["toi"] for h in hd if h["lam"] == "bien_thanh" and h["toi"] is not None}
                dich = set(den.values())
                moc_i = {}
                for i in range(len(vai)):
                    ts = [h["t"] for h in hd if h["ai"] == i or h["toi"] == i]
                    if vai[i] and vai[i].get("vao") is not None:
                        ts.append(vai[i]["vao"])
                    if ts:
                        moc_i[i] = min(ts)
                muc = []
                for i in sorted(moc_i, key=moc_i.get) + [i for i in range(len(vai)) if i not in moc_i]:
                    if i in dich:
                        continue
                    j, da = i, {i}
                    while j in den and den[j] not in da:     # theo chuỗi biến thành tới trạng thái cuối
                        j = den[j]
                        da.add(j)
                    if vai[j] or vai[i]:
                        muc.append(dict(vai[j] or vai[i]))
                if len(muc) < 2:
                    log(f"    ! diễn cảnh câu {x['cau']}: liệt kê còn < 2 mục có ảnh — bỏ")
                    continue
                t0 = max(0.1, min(moc_i.values()) if moc_i else 0.3)
                for k2, v in enumerate(muc):
                    v["vao"] = round(t0, 2)                  # 14/10 user: liệt kê hiện HẾT cùng lúc
                vai, hd = muc, []
            pr.update(vai=[v or {"ten": "", "src": ""} for v in vai], hanh_dong=hd,
                      bo_cuc="liet_ke" if lk else "", khuon=khuon)
            if khuon == "tong_quat":                         # 14/10 user: dòng tiêu đề tiếng Việt dưới ảnh tổng quát
                pr.update(chu_tq=str(x.get("tieu_de") or "").strip())
            if khuon == "con_so":
                ts = g.get("t_so")
                pr.update(so=so_chu_so(x.get("so")), hoi=False,   # 14/10 user: không gắn "?" vào con số
                          t_so=round(max(0.3, (ts - bd) if ts is not None else 0.6), 2))
            elif khuon == "so_sanh":
                try:
                    gt = [float(str(z).replace(",", ".")) for z in (x.get("gia_tri") or [])][:2]
                except ValueError:
                    gt = []
                pr.update(gia_tri=gt if len(gt) == 2 else [], nhan_gt=[str(z) for z in (x.get("nhan_gt") or [])][:2])
            am, cuoi_am = [], -9.0
            for h in hd:                                     # tiếng động đúng lúc hành động (cách nhau >= 0,5 s)
                t_am = round(bd + h["t"] + (0.25 if h["lam"] == "bien_thanh" else 0.0), 2)
                if AM_HANH_DONG.get(h["lam"]) and t_am - cuoi_am >= 0.5:
                    am.append({"t": t_am, "kieu": AM_HANH_DONG[h["lam"]], "ly_do": f"diễn cảnh: {h['lam']}"})
                    cuoi_am = t_am
            ma_am[n] = am
            ma[n] = "diễn cảnh: " + ", ".join(v["ten"] for v in vai if v)
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
        else:
            vai = [{"ten": y.get("ten") or "", "bieu_tuong": y.get("bieu_tuong") or "❓"} for y in (x.get("vai") or [])
                   if isinstance(y, dict)][:3]
            hd = []
            for y in (x.get("hanh_dong") or [])[:4]:
                try:
                    ai = int(y.get("ai"))
                    toi = None if y.get("toi") in (None, "", "null") else int(y.get("toi"))
                except (TypeError, ValueError, AttributeError):
                    continue
                if 0 <= ai < len(vai) and (toi is None or 0 <= toi < len(vai)) and toi != ai:
                    hd.append({"ai": ai, "lam": y.get("lam"), "toi": toi, "moc": y.get("moc")})
            if not vai or not hd:
                continue
            ts = _moc_con(hd, ds_c, bd, dai, tang=True)
            for y, t in zip(hd, ts):
                y["t"] = max(0.6, t)
                y.pop("moc", None)
            pr.update(vai=vai, hanh_dong=hd)
            ma[n] = "mô phỏng: " + ", ".join(v["ten"] for v in vai)
        if not pr["nen"] or not (pr.get("muc") or pr.get("vai")) or (k not in ("mo_phong", "dien_canh") and len(pr.get("muc") or []) < 2):
            continue
        jobs.append((n, dai, pr))
    clip.update(_render_so_do(jobs) if jobs else {})
    ra = []
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan):
        if clip.get(n):
            ra.append({"kieu": k, "cau": x["cau"], "bd": bd, "dai": dai, "file": clip[n], "mo_ta": ma.get(n, ""),
                       "am": ma_am.get(n, [])})
    dem = {}
    for y in ra:
        dem[y["kieu"]] = dem.get(y["kieu"], 0) + 1
    log(f"    minh hoạ dựng được: {', '.join(f'{k} {v}' for k, v in sorted(dem.items())) or 'không có'} "
        f"(đề xuất {len(ung)}, sau khi bỏ chồng giờ {len(nhan)})")
    return ra
