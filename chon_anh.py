# -*- coding: utf-8 -*-
"""Chọn ẢNH từ kho web cho từng ô và so điểm TRỰC TIẾP với đoạn video đã chọn: ảnh khớp
hơn thì thay vào (ảnh loài/địa điểm thường đúng ý hơn một đoạn video ngẫu nhiên)."""
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

import chon_doan as cdn
from common import doc_json, duong_cache, log

UA = {"User-Agent": "ban-content/0.2 (video illustration research tool)"}
#: ảnh chỉ thay đoạn video khi điểm >= điểm video + mức này (âm = ưu ái ảnh).
THUONG_ANH = 0.06            # ảnh phải khớp RÕ HƠN đoạn video mới được thay (trước: 0,01 -> ảnh chiếm ~44% số ô)
MIN_ANH_THIEU = 0.26         # ảnh vá ô THIẾU phải đạt mức này (trước: không có ngưỡng -> ảnh điểm 0,15 sai nghĩa)
MIN_ANH = 0.26               # và phải đạt mức khớp tối thiểu tuyệt đối
DEM_TOI = ("night", "dusk", "dark", "moonlit", "thermal", "evening")
TOI_DA_ANH_MOI_CANH = 60


def _tai(it):
    p = duong_cache("anh", it["id"] + ".jpg")
    if os.path.isfile(p) and os.path.getsize(p) > 3000:
        return p
    try:
        h = ({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
             if it.get("nguon") == "bing" else UA)
        with urllib.request.urlopen(urllib.request.Request(it["url"], headers=h), timeout=25) as r:
            data = r.read(12 << 20)                       # ảnh web có thể rất nặng: lấy tối đa 12 MB
        if len(data) < 3000:
            return None
        import io
        from PIL import Image
        Image.open(io.BytesIO(data)).verify()              # không phải ảnh (trang lỗi, svg...) thì bỏ
        with open(p, "wb") as f:
            f.write(data)
        return p
    except Exception:                                   # noqa: BLE001
        if os.path.isfile(p):
            os.remove(p)
        return None


def ung_vien_cua_canh(c, tim):
    seen, ds = set(), []
    qs = list(c.get("q", [])) + [q for nh in c.get("nhip_tho") or [] for q in nh.get("q", [])]
    aq = list(c.get("anh_q", [])) + [q for nh in c.get("nhip_tho") or [] for q in nh.get("anh_q", [])]
    ent = [e.get("name", "").strip().lower() for nh in c.get("nhip_tho") or [] for e in nh.get("ents") or []]
    nguon = [tim.get("anh:" + n, {}) for n in dict.fromkeys(x for x in ent if x)]      # ảnh theo TÊN THỰC THỂ trước
    nguon += [tim.get("anh:" + q.strip().lower(), {}) for q in aq]
    nguon += [tim.get("anh:" + str(q).strip().lower(), {}) for nh in c.get("nhip_tho") or [] for q in (nh.get("q") or [])[:2]]
    nguon += [tim.get(q.strip().lower(), {}) for q in qs]
    for e in nguon:
        for k in ("bg", "wp", "inat", "wc"):
            for it in e.get(k) or []:
                if it["id"] not in seen:
                    seen.add(it["id"])
                    ds.append(it)
    return ds[:TOI_DA_ANH_MOI_CANH]


def _nhung_anh_file(paths):
    from PIL import Image
    ra, ok = [], []
    for p in paths:
        npy = p + ".l14.npy"
        if os.path.isfile(npy):
            ra.append(np.load(npy))
            ok.append(True)
            continue
        try:
            e = cdn.nhung_anh([Image.open(p).convert("RGB")])[0]
            np.save(npy, e)
            ra.append(e)
            ok.append(True)
        except Exception:                               # noqa: BLE001
            ok.append(False)
    return ra, ok


def luma_cua(co):
    """Mảng bool: độ sáng trung bình của từng ảnh ứng viên (co = [(item, path)])."""
    from PIL import Image
    ra = []
    for _it, p in co:
        try:
            ra.append(float(np.asarray(Image.open(p).convert("L").resize((48, 27))).mean()))
        except Exception:                                               # noqa: BLE001
            ra.append(0.0)
    return np.array(ra)


def thay_bang_anh(canh, tim, song_song=6):
    """Cho mỗi cảnh (trừ cảnh đồ họa): chấm ảnh, thay ô video nào kém hơn ảnh tốt nhất còn lại."""
    viec = [(c, ung_vien_cua_canh(c, tim)) for c in canh if not c.get("do_hoa")]
    tat_ca = {it["id"]: it for _, ds in viec for it in ds}
    log(f"[3b] kho ảnh web: {len(tat_ca)} ảnh ứng viên cho {len(viec)} cảnh")
    with ThreadPoolExecutor(song_song) as ex:
        file_cua = dict(zip(tat_ca, ex.map(_tai, tat_ca.values())))
    n_thay = 0
    dung = set()
    for c, ds in viec:
        co = [(it, file_cua[it["id"]]) for it in ds if file_cua.get(it["id"])]
        if not co:
            continue
        embs, ok = _nhung_anh_file([p for _, p in co])
        co = [x for x, k in zip(co, ok) if k]
        if not co:
            continue
        E = np.array(embs)
        BO = doc_json(os.path.join(__import__("common").CACHE, "cam_chon.json"), {}) or {}
        for o in c["o"]:
            nhs = c.get("nhip") or []
            nh = nhs[o["nhip"]] if o.get("nhip") is not None and o["nhip"] < len(nhs) else None
            qv = cdn.vec_nhip(nh) if nh else cdn.vec_canh(c)          # so với ĐÚNG cụm lời của ô
            diem = E @ qv
            van = ((nh or {}).get("mo_ta", "") + " " + c.get("mo_ta", "")).lower()
            if not any(w in van for w in DEM_TOI):                       # ảnh tối đen chỉ được dùng khi cảnh nói về ban đêm
                diem = diem - 1.0 * (luma_cua(co) < 45)
            cam_ap = cdn.cam_cua_nhip(nh or {"mo_ta": c.get("mo_ta", ""), "text": c.get("text", "")})
            van_n = ((nh or {}).get("mo_ta", "") + " " + (nh or {}).get("text", "")).lower()
            cam_tu = [p for p in c.get("cam_them", []) if not any(w in van_n for w in __import__("re").findall(r"[a-z]{4,}", p.lower()))]
            if cam_tu:                                                  # ảnh có chủ thể CHƯA được nhắc tới
                diem = diem - cdn.PHAT_CAM * np.clip((E @ np.array([cdn.vec_tu(p) for p in cam_tu]).T).max(1) - 0.215, 0, None)
            if cam_ap:                                                  # phạt ảnh có khái niệm cấm (tuyết, rừng thông…)
                diem = diem - cdn.PHAT_CAM * np.clip((E @ np.array([cdn.vec_cam()[k] for k in cam_ap]).T).max(1) - 0.215, 0, None)
            thu_tu = [int(i) for i in np.argsort(-diem)]
            for i in thu_tu:
                it, p = co[i]
                if it["id"] in dung or it["id"] in BO.get(f"{c['id']}.{o.get('nhip', 0)}", ()):
                    continue
                kinds = {e_.get("kind") for e_ in ((nh or {}).get("ents") or [])}
                bien = 0.0 if kinds & {"logo", "document", "photo", "map"} else THUONG_ANH               # nhịp cần logo/tài liệu: ảnh không phải thắng xa
                if o.get("thieu"):
                    chap = float(diem[i]) >= MIN_ANH_THIEU                                # ô trống cũng không nhận ảnh điểm quá thấp
                else:
                    chap = float(diem[i]) >= MIN_ANH and float(diem[i]) >= o.get("clip", o.get("diem", 0)) + bien
                if chap:
                    dai = o.get("dai") or round(c["dai"] / len(c["o"]), 2)
                    giu = {k: o[k] for k in ("nhip", "text") if k in o}
                    o.clear()
                    o.update(giu)
                    o.update({"anh": p, "dai": dai, "diem": round(float(diem[i]), 4),
                              "tieu_de": it["tieu_de"], "nguon": it["nguon"],
                              "giay_phep": it.get("giay_phep", ""), "tac_gia": it.get("tac_gia", "")})
                    dung.add(it["id"])
                    n_thay += 1
                break
    tong = sum(len(c.get("o", [])) for c in canh)
    log(f"    ảnh web thay {n_thay}/{tong} ô")
    return canh
