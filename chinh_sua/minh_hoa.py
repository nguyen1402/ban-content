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
KHOANG_NGAT = 4.0          # 13/10: hai hành động cách hơn 4 s -> tắt cảnh ở giữa, bật lại đúng lúc hành động sau
LAM = {"xuat_hien", "bien_thanh", "bay_toi", "tan_cong", "bao_vay", "lan_ra", "sinh_soi", "bo_chay", "an", "mang_di",
       "lon_len", "bien_mat", "tach_ra", "ket_hop", "gam", "keo_di", "thay_the", "thu_nho"}
BAN_DO = ("khoanh_vung", "duong_di", "lan_rong")


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
    tim_o = ds_c + ([ke] if ke else [])
    vai = x.get("vai") or []
    hd = []
    for y in (x.get("hanh_dong") or [])[:5]:
        try:
            ai = int(y.get("ai"))
            toi = None if y.get("toi") in (None, "", "null") else int(y.get("toi"))
        except (TypeError, ValueError, AttributeError):
            continue
        if y.get("lam") not in LAM or not (0 <= ai < len(vai)) or (toi is not None and not (0 <= toi < len(vai)) or toi == ai):
            continue
        if y["lam"] == "bien_thanh" and toi is None:
            continue
        t = _tim(tim_o, y.get("moc"))
        if t is None:
            continue
        hd.append({"ai": ai, "lam": y["lam"], "toi": toi, "nhan": str(y.get("nhan") or ""), "t": t})
    hd.sort(key=lambda h: h["t"])
    for k in range(1, len(hd)):                               # hai hành động sát nhau: cách ít nhất 0,6 s
        hd[k]["t"] = max(hd[k]["t"], hd[k - 1]["t"] + 0.6)
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
    for k, g in enumerate(nhom):
        bd = g[0]["t"] - 0.35
        cuoi = g[-1]["t"]
        tran = nhom[k + 1][0]["t"] - 0.9 if k + 1 < len(nhom) else 1e9
        ket = next((c["t1"] for c in tim_o if c["t0"] - 0.3 <= cuoi <= c["t1"] + 0.3), cuoi)   # hết câu chứa nhịp cuối
        it_nhat = cuoi + HOAT_CANH + GIU_CUOI                # nhịp cuối hiện xong + đứng yên 2 s cho người xem kịp hiểu
        kt = max(min(tran, max(it_nhat, min(max(het_cau, ket + 0.3), cuoi + 5.0))), min(it_nhat, tran + 0.9))
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
            elif (v or {}).get("vi_tri") in ("trai", "giua", "phai") and k == 0:
                vao.append(bd)                               # vai ChatGPT đặt sẵn chỗ: có mặt ngay khi cảnh mở
            elif dung or ten is not None:
                vao.append(max(bd, min([t - 0.35 for t in dung] + ([ten - 0.1] if ten is not None else []))))
            else:
                vao.append(None)                             # vai không dính tới nhóm này: không hiện
        ra.append({"bd": round(bd, 2), "dai": round(max(2.4, kt - bd), 2), "hd": g, "vao": vao})
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
        out = os.path.join(thu, hashlib.md5((json.dumps(pr, ensure_ascii=False, sort_keys=True) + f"|{giay}|v11")
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
        if k not in SO_DO + BAN_DO:
            continue
        c = theo_i.get(x["cau"])
        if not c:
            continue
        ds_c = [theo_i[j] for j in range(x["cau"], x.get("den_cau", x["cau"]) + 1) if j in theo_i]
        if k == "dien_canh":
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
        dai = round(max(4.5, min(8.0, kt - bd)) if k in BAN_DO else max(5.5, min(14.0, kt - bd)), 2)
        if any(bd < b_ + 0.3 and bd + dai > a_ - 0.3 for a_, b_ in vt):
            continue                                         # trùng cảnh bản đồ vệ tinh đã có trên track hình
        ung.append((bd, dai, k, x, ds_c))
    ung.sort(key=lambda z: z[0])
    # không chồng nhau. 13/10: cảnh nối sát nhau -> CẮT ĐUÔI cảnh trước tới lúc cảnh sau bật (đuôi chỉ là phần giữ hình
    # sau hành động cuối); chỉ bỏ cảnh sau khi cắt xong cảnh trước còn < 1,2 s sau hành động cuối của nó.
    def _xong(u):                                            # sớm nhất được tắt: nhịp cuối hiện xong + giữ GIU_CUOI s
        g = (u[3] or {}).get("_gio")
        return (g["hd"][-1]["t"] if g and g.get("hd") else u[0] + 1.0) + HOAT_CANH + GIU_CUOI
    nhan = []
    for u in ung:
        u = list(u)
        if nhan:
            tr = nhan[-1]
            if u[0] < tr[0] + tr[1] + 0.15:
                if u[0] - 0.15 >= _xong(tr):
                    tr[1] = round(u[0] - 0.15 - tr[0], 2)
                else:
                    continue
        nhan.append(u)
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
        ds = [y for y in (x.get("vai") or []) if isinstance(y, dict)][:4]
        bo = anh_tach.bo_canh(ds) if BO_VAI_AI else None
        if bo:                                               # 13/10 user: AI vẽ cả bộ vai một lượt
            return [{"ten": str(y.get("ten") or ""), "src": b["src"],
                     "vi_tri": y.get("vi_tri") if y.get("vi_tri") in ("trai", "giua", "phai") else ""} for y, b in zip(ds, bo)]
        vai, da_url = [], []
        for y in (x.get("vai") or [])[:4]:
            r = anh_tach.lay(str(y.get("anh") or ""), tranh=da_url, ve=str(y.get("ve") or "") or None,
                             truu_tuong=bool(y.get("truu_tuong"))) if isinstance(y, dict) else None
            if r and r.get("url"):
                da_url.append(r["url"])
            vai.append({"ten": str(y.get("ten") or ""), "src": r["src"],
                        "vi_tri": y.get("vi_tri") if y.get("vi_tri") in ("trai", "giua", "phai") else ""} if r else None)
        return vai
    dc = [u[3] for u in nhan if u[2] == "dien_canh"]
    log(f"    lấy ảnh vai cho {len(dc)} diễn cảnh (ảnh thật tách nền / AI vẽ)…")
    with ThreadPoolExecutor(3) as ex:
        san = list(ex.map(_vai_canh, dc))
    for x, v in zip(dc, san):
        x["_vai"] = v
    # ---- sơ đồ trên nền video tối
    jobs, ma_am = [], {}
    for n, (bd, dai, k, x, ds_c) in enumerate(nhan):
        if k not in SO_DO:
            continue
        pr = {"kieu": k, "nen": bang_giay._clips(canh, bd, bd + dai)}                      # noqa: SLF001
        if k == "dien_canh":                                 # 13/10 user: ảnh thật tách nền thay icon
            vai = [dict(v) if v else None for v in x["_vai"]]
            g = x["_gio"]
            hd = [dict(h, t=round(h["t"] - bd, 2)) for h in g["hd"]
                  if h["ai"] < len(vai) and vai[h["ai"]] and (h["toi"] is None or (h["toi"] < len(vai) and vai[h["toi"]]))]
            if not any(h["lam"] != "xuat_hien" for h in hd) and not any(
                    h["lam"] != "xuat_hien" for h in (x.get("hanh_dong") or []) if isinstance(h, dict)):
                log(f"    ! diễn cảnh câu {x['cau']}: không còn hành động chuyển động (chỉ xuất hiện / thiếu ảnh / mốc không khớp lời) — bỏ")
                continue
            for k2, v in enumerate(vai):
                if v:
                    v["vao"] = None if k2 >= len(g["vao"]) or g["vao"][k2] is None else round(max(0.0, g["vao"][k2] - bd), 2)
            pr.update(vai=[v or {"ten": "", "src": ""} for v in vai], hanh_dong=hd)
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
