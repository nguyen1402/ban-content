# -*- coding: utf-8 -*-
"""Bước 3 — chấm điểm khung hình bằng CLIP rồi chọn đoạn khớp lời nhất cho từng cảnh."""
import os
import threading
import re

import cv2
import numpy as np

from common import doc_json, duong_cache, ghi_json, log

#: ViT-L/14 chính xác hơn hẳn B/32 (hiểu "chó trắng to trên bãi biển" chứ không chỉ "chó"); 3060 12GB thừa sức.
MODEL_CLIP = "openai/clip-vit-large-patch14"
THU_MUC_CHI_MUC = "chi_muc_l14"
BUOC_GIAY = 1.5                 # lấy 1 khung mỗi 1,5 giây
DOAN_MAX = 8.0                  # mỗi đoạn hình tối đa 8s — cảnh dài ghép nhiều đoạn
DOAN_MIN = 3.0
PHAT_CAT_GIUA = 0.03             # đoạn buộc phải chứa một điểm đổi cảnh của video gốc (hình nhảy giữa nhịp)
CORE_THUONG = 0.10              # đoạn thuộc VIDEO CHỦ LỰC được cộng điểm: ưu tiên ghép từ bộ chủ lực
THUONG_TIEU_DE = 0.04            # tiêu đề/kênh video chứa tên thực thể của nhịp
THUONG_CHU = 0.08                # chữ OCR trong đoạn khớp tên thực thể (logo, bảng, bản đồ ghi tên)
_STOP_TEN = {"the", "and", "with", "for", "from", "island", "river", "lake", "national", "park", "north", "south",
             "east", "west", "new", "old", "video", "map", "logo", "sign", "của", "và", "những", "các", "một"}


def _toks(s):
    """Tập từ khoá (không dấu, chữ thường, >=3 ký tự hoặc có chữ số) của một chuỗi."""
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return {t for t in re.findall(r"[a-z0-9]+", s) if (len(t) >= 3 or any(ch.isdigit() for ch in t)) and t not in _STOP_TEN}


PHAT_LOGO = 0.05                # (không còn dùng để chọn: video có logo tĩnh ở góc bị loại hẳn)
NGUONG = 0.215
NGUONG_MEM = 0.18               # bước chọn thứ hai khi không đoạn nào đạt NGUONG
#: khái niệm hình KHÔNG được xuất hiện trừ khi lời/mô tả của nhịp nhắc tới (từ khóa kích hoạt)
CAM_KHAI_NIEM = {
    "tuyet": ("snow covered ground, ice and winter landscape", ("snow", "ice", "winter", "cold", "frozen", "arctic")),
    "rung_thong": ("dense pine forest with tall conifer trees", ("forest", "pine", "woodland", "trees")),
    "phong_van": ("a person talking to the camera in an interview", ("interview", "talk", "speak", "explain", "worker", "ranger", "farmer", "marsh", "council", "officer", "researcher", "man ", "woman")),
    "thu_chet": ("dead animals lying on a car hood with a rifle, hunting trophy", ("dead", "carcass", "killed", "slaughter", "bodies", "hunt")),
    "hoa_la": ("a close-up of a flower, blossom or green plant leaves", ("flower", "bloom", "blossom", "leaf", "leaves", "plant close")),
    "chim_bien": ("flock of seagulls standing on rocks", ("gull", "seagull", "bird colony")),
}
PHAT_CAM = 3.0                  # cos CLIP thấp hơn mức này coi như KHÔNG khớp

_M = {}


def _clip():
    if not _M:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        m = CLIPModel.from_pretrained(MODEL_CLIP, torch_dtype=torch.float16 if dev == "cuda"
                                      else torch.float32).to(dev).eval()
        _M.update(m=m, p=CLIPProcessor.from_pretrained(MODEL_CLIP), dev=dev, t=torch)
    return _M


def _chuan(x):
    return x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-8, None)


_KHOA_GPU = threading.Lock()


def nhung_anh(imgs, lo=64):
    with _KHOA_GPU:                                      # GPU/CLIP dùng chung: nhiều luồng ffmpeg, MỘT luồng nhúng
        return _nhung_anh(imgs, lo)


def _nhung_anh(imgs, lo=64):
    M = _clip()
    ra = []
    for i in range(0, len(imgs), lo):
        inp = M["p"](images=imgs[i:i + lo], return_tensors="pt").to(M["dev"])
        with M["t"].no_grad():
            m = M["m"]
            f = m.visual_projection(m.vision_model(
                pixel_values=inp["pixel_values"].to(m.dtype)).pooler_output)
        ra.append(f.float().cpu().numpy())
    return _chuan(np.concatenate(ra)) if ra else np.zeros((0, 768), np.float32)


def nhung_chu(texts):
    with _KHOA_GPU:
        return _nhung_chu(texts)


def _nhung_chu(texts):
    M = _clip()
    inp = M["p"](text=texts, return_tensors="pt", padding=True, truncation=True,
                 max_length=77).to(M["dev"])
    with M["t"].no_grad():
        m = M["m"]
        f = m.text_projection(m.text_model(input_ids=inp["input_ids"],
                                           attention_mask=inp["attention_mask"]).pooler_output)
    return _chuan(f.float().cpu().numpy())


def _khung_ffmpeg(path):
    """Một lượt ffmpeg trích 1 khung/BUOC_GIAY giây, đã co 224x224 — nhanh hơn nhảy vị trí
    từng khung bằng cv2 rất nhiều (video 360p giải mã tuần tự nhanh hơn nhiều lần thời gian thực)."""
    import subprocess
    from PIL import Image
    from common import FFMPEG
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    vf = (f"fps=1/{BUOC_GIAY},scale=224:224:force_original_aspect_ratio=increase,"
          f"crop=224:224")
    try:
        p = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-an", "-vf", vf,
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, timeout=900, **kw)
    except Exception:                                     # noqa: BLE001
        return [], []
    n = 224 * 224 * 3
    buf = p.stdout
    imgs = [Image.frombytes("RGB", (224, 224), buf[i:i + n])
            for i in range(0, len(buf) - n + 1, n)]
    return imgs, [i * BUOC_GIAY for i in range(len(imgs))]


def _khung_cv2(path, dai_mac_dinh):
    from PIL import Image
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    tong = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    dai = tong / fps if tong else dai_mac_dinh
    ts, imgs, t = [], [], 0.0
    while t < dai:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        imgs.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
        ts.append(t)
        t += BUOC_GIAY
    cap.release()
    return imgs, ts


def chi_muc_video(it):
    """Nhúng khung hình của một video; lưu .npz cạnh cache (chạy lại không phải tính)."""
    npz = duong_cache(THU_MUC_CHI_MUC, it["id"] + ".npz")
    if os.path.isfile(npz):
        d = np.load(npz)
        return d["t"], d["e"]
    imgs, ts = _khung_ffmpeg(it["file"])
    if not imgs:                                          # ffmpeg hỏng -> đường cũ (chậm)
        imgs, ts = _khung_cv2(it["file"], it.get("dai", 0))
    e = nhung_anh(imgs)
    t = np.array(ts, np.float32)
    np.savez(npz, t=t, e=e)
    return t, e


def vec_canh(c):
    """Vector truy vấn của một cảnh: mô tả cảnh (trọng số cao) + hai từ khóa đầu."""
    return _vec(c.get("mo_ta") or c.get("q", [""])[0], c.get("q", []))


def _vec(mo_ta, q):
    qv = nhung_chu([mo_ta] + list(q[:2]))
    w = np.array([0.6, 0.25, 0.15][:len(qv)], np.float32)
    return _chuan((qv * w[:, None]).sum(0, keepdims=True))[0]


def vec_nhip(n):
    return _vec(n.get("mo_ta") or (n.get("q") or [""])[0], n.get("q", []))


_CAM = {}
_TU = {}
TU_CHUYEN_DONG = re.compile(r"\b(walk|run|trot|prowl|swim|waddle|stalk|chase|fly|flying|moving|crawl|patrol|pace|race|rush|dash|sweep|crash)", re.I)


def vec_tu(p):
    if p not in _TU:
        _TU[p] = nhung_chu([p])[0]
    return _TU[p]


def vec_cam():
    if not _CAM:
        for k, (mo, _kich) in CAM_KHAI_NIEM.items():
            _CAM[k] = nhung_chu([mo])[0]
    return _CAM


def cam_cua_nhip(nh):
    """Danh sách khái niệm cấm ÁP DỤNG cho nhịp này (bỏ khái niệm mà lời/mô tả của nhịp có nhắc tới)."""
    van = ((nh.get("mo_ta") or "") + " " + (nh.get("text") or "")).lower()
    return [k for k, (_mo, kich) in CAM_KHAI_NIEM.items() if not any(w in van for w in kich)]


def chon(canh, kho, ctx=None, bo_video=(), uu_tien=()):
    """Với mỗi NHỊP (cụm lời) của mỗi cảnh: chọn đoạn video khớp đúng cụm đó.

    Điểm đoạn = trung bình cos(khung, mô tả nhịp) trong cửa sổ, trừ nhẹ khi video đã dùng nhiều và
    khi có logo; đoạn phải không có chữ cứng và được căn theo điểm đổi cảnh của video gốc."""
    import sach_hinh
    vid = []
    for it in kho:
        try:
            t, e = chi_muc_video(it)
        except Exception as ex:                          # noqa: BLE001
            log(f"    ! chỉ mục hỏng {it['id']}: {ex}")
            continue
        if len(t) >= 2 and it["id"] not in set(bo_video):
            vid.append((it, t, e))
    log(f"[3] chấm điểm {len(vid)} video, {len(canh)} cảnh")
    file_cua = {it["id"]: it["file"] for it, _, _ in vid}
    tong_cua = {it["id"]: float(t[-1]) + BUOC_GIAY for it, t, _ in vid}
    tx = nhung_chu(["a cartoon, animation, illustration, drawing or computer graphics",
                    "a photograph or real camera footage of the real world"])
    p_hh = {}                                            # id -> xác suất 'hoạt hình/đồ họa' của TỪNG khung
    for it, t, e in vid:
        z = (e @ tx.T) * 100.0
        z = z - z.max(1, keepdims=True)
        ez = np.exp(z)
        p_hh[it["id"]] = ez[:, 0] / ez.sum(1)
    ids_ = [(it["id"], it["file"]) for it, _, _ in vid]
    logo_cua = dict(zip([i for i, _ in ids_], sach_hinh.song_song(lambda x: sach_hinh.logo_video(x[1], x[0]), ids_)))
    cat_cua = dict(zip([i for i, _ in ids_], sach_hinh.song_song(lambda x: sach_hinh.canh_cat(x[1], x[0]), ids_)))
    log(f"    video có logo tĩnh ở góc: {sum(1 for v in logo_cua.values() if v)}/{len(vid)} (bị trừ điểm); "
        f"điểm đổi cảnh dò được: {sum(len(v) for v in cat_cua.values())}")
    # ---- VIDEO CHỦ LỰC: chấm chất lượng từng video rồi chọn tập nhỏ phủ nhiều nhịp nhất (xem chu_luc.py)
    import chu_luc
    import json as _json
    from common import OUT
    nhips = []
    for c_ in canh:
        if c_.get("do_hoa"):
            continue
        for nh_ in c_.get("nhip") or [{"mo_ta": c_.get("mo_ta"), "q": c_.get("q", []), "bd": 0.0, "dai": c_["dai"],
                                      "text": c_["text"]}]:
            nhips.append((vec_nhip(nh_), nh_["dai"]))
    cua_so_cua = lambda d_: max(1, int(round(min(d_, DOAN_MAX) / BUOC_GIAY)))
    neo = chu_luc.tu_khoa_neo(canh, ctx)             # {từ khoá: trọng số}
    ten_neo = [s_["en"] for s_ in (ctx or {}).get("chu_the", []) or [] if s_.get("en")][:8]
    vec_neo = nhung_chu(ten_neo) if ten_neo else None

    def ty_le_chu(it_, t_):
        ts_ = np.linspace(float(t_[0]), float(t_[-1]), 6)[:5]
        ks = sach_hinh.song_song(lambda b_: bool(sach_hinh.chu_van(it_["file"], float(b_), 2.0)), list(ts_), 6)
        return float(np.mean(ks)) if ks else 0.0
    q_vid = np.array([chu_luc.chat_luong_video(it, e, p_hh[it["id"]], neo, vec_neo, ty_le_chu(it, t))
                      for it, t, e in vid], np.float32)
    S_phu = chu_luc.ma_tran_phu(vid, nhips, cua_so_cua) if nhips else np.zeros((0, len(vid)), np.float32)
    pri = [j for j, (it, _t, _e) in enumerate(vid) if it["id"] in set(uu_tien)]
    core_idx, _cur = chu_luc.chon_bo(S_phu, q_vid, pri) if len(vid) else ([], None)
    core = {vid[j][0]["id"] for j in core_idx}
    log(f"    VIDEO CHỦ LỰC: {len(core)}/{len(vid)} video phủ {int((S_phu[:, core_idx].max(1) >= NGUONG).sum()) if core_idx else 0}"
        f"/{len(nhips)} nhịp")
    try:
        ds_ = sorted(range(len(vid)), key=lambda j: (-(vid[j][0]["id"] in core), -float(q_vid[j])))
        with open(os.path.join(OUT, "chu_luc.json"), "w", encoding="utf-8") as f_:
            _json.dump([{"id": vid[j][0]["id"], "tieu_de": vid[j][0].get("tieu_de", ""),
                         "kenh": vid[j][0].get("kenh", ""), "dai": vid[j][0].get("dai", 0),
                         "nguon": vid[j][0].get("nguon", ""), "q": round(float(q_vid[j]), 3),
                         "phu": int((S_phu[:, j] >= NGUONG).sum()) if len(S_phu) else 0,
                         "chu_luc": vid[j][0]["id"] in core, "uu_tien": vid[j][0]["id"] in set(uu_tien)}
                        for j in ds_], f_, ensure_ascii=False, indent=1)
    except OSError:
        pass
    da_dung = {}                                         # id -> [(bd, kt)]
    so_lan = {}
    BO_QUA = doc_json(os.path.join(__import__("common").CACHE, "cam_chon.json"), {}) or {}
    import time
    from common import eta_chu, tien_do
    t_chon = time.time()
    for ci, c in enumerate(canh, 1):
        if ci % 10 == 0 or ci == len(canh):
            log(f"    chọn đoạn: cảnh {ci}/{len(canh)}{eta_chu(t_chon, ci, len(canh))}")
            tien_do("chon", "dang", f"cảnh {ci}/{len(canh)}")
        if c.get("do_hoa"):
            continue                                     # cảnh đồ họa: do_hoa.py đã dựng
        c["o"] = []
        ds_nhip = c.get("nhip") or [{"mo_ta": c.get("mo_ta"), "q": c.get("q", []),
                                      "bd": 0.0, "dai": c["dai"], "text": c["text"]}]
        for ni, nh in enumerate(ds_nhip):
            qv = vec_nhip(nh)
            cam_ap = cam_cua_nhip(nh)
            van_nhip = ((nh.get("mo_ta") or "") + " " + (nh.get("text") or "")).lower()
            cam_tu = [p for p in c.get("cam_them", []) if not any(w in van_nhip for w in re.findall(r"[a-z]{4,}", p.lower()))]
            cam_list = [vec_cam()[k] for k in cam_ap] + [vec_tu(p) for p in cam_tu]       # + chủ thể CHƯA được nhắc tới
            cam_vec = np.array(cam_list) if cam_list else None
            ent_tok = set()                                  # từ khoá tên thực thể cụ thể của nhịp (tiếng Anh + như trong lời)
            for e_ in nh.get("ents") or []:
                ent_tok |= _toks(e_.get("name", "")) | _toks(e_.get("vi", ""))
            khoa_o = f"{c['id']}.{ni}"
            so_o = max(1, int(np.ceil(nh["dai"] / DOAN_MAX)))
            dai_o = nh["dai"] / so_o
            for k in range(so_o):
                cua_so = max(1, int(round(min(dai_o, DOAN_MAX) / BUOC_GIAY)))
                cands = []
                for it, t, e in vid:
                    if logo_cua.get(it["id"]):
                        continue                          # video có logo kênh tĩnh ở góc: KHÔNG chọn
                    s = e @ qv
                    if len(s) < cua_so:
                        continue
                    if cam_vec is not None:                  # phạt khung có khái niệm cấm (tuyết, rừng thông, phỏng vấn…)
                        neg = (e @ cam_vec.T).max(1)
                        s = s - PHAT_CAM * np.clip(neg - 0.215, 0, None)
                    cs = np.convolve(s, np.ones(cua_so) / cua_so, mode="valid")
                    for i in np.argsort(-cs)[:8]:
                        if float(p_hh[it["id"]][i:i + cua_so].mean()) > 0.5:
                            continue                      # đoạn là hoạt hình/đồ họa, không phải quay thật
                        pen_cat = 0.0
                        bd = sach_hinh.can_cua_so(float(t[i]), dai_o, cat_cua[it["id"]], tong_cua[it["id"]], chat=True)
                        if bd is None:                    # không có chỗ nào nằm gọn trong MỘT cảnh gốc -> nới, trừ điểm
                            bd = sach_hinh.can_cua_so(float(t[i]), dai_o, cat_cua[it["id"]], tong_cua[it["id"]])
                            pen_cat = PHAT_CAT_GIUA
                        if bd is None:
                            continue                      # quanh đó toàn cảnh quá ngắn
                        kt = bd + dai_o
                        if any(bd < b and kt > a for a, b in da_dung.get(it["id"], [])):
                            continue
                        if it["id"] in BO_QUA.get(khoa_o, ()) or it["id"] in BO_QUA.get(str(c["id"]), ()):
                            continue                      # người dùng/kiểm tra đã loại video này cho nhịp này
                        trong_core = it["id"] in core
                        diem = (float(cs[i]) - pen_cat - (0.004 if trong_core else 0.012) * so_lan.get(it["id"], 0)
                                + (CORE_THUONG if trong_core else 0.0)
                                - PHAT_LOGO * (1 if logo_cua.get(it["id"]) else 0))
                        if ent_tok and (ent_tok & _toks((it.get("tieu_de") or "") + " " + (it.get("kenh") or ""))):
                            diem += THUONG_TIEU_DE
                        cands.append({"id": it["id"], "bd": round(bd, 2), "dai": round(dai_o, 2),
                                      "diem": round(diem, 4), "clip": round(diem - (CORE_THUONG if trong_core else 0.0), 4),
                                      "tieu_de": it["tieu_de"],
                                      "kenh": it.get("kenh", ""), "nguon": it.get("nguon", "youtube"),
                                      "url": it.get("url"), "trang": it.get("trang"),
                                      "nhip": ni, "text": nh.get("text", "")})
                        break
                cands.sort(key=lambda x: -x["diem"])
                if TU_CHUYEN_DONG.search(nh.get("mo_ta") or ""):          # nhịp tả chuyển động: ưu tiên đoạn có chuyển động
                    ms = sach_hinh.song_song(lambda cd: sach_hinh.chuyen_dong(file_cua[cd["id"]], cd["bd"], cd["dai"]), cands[:10])
                    for cd, m in zip(cands[:10], ms):
                        cd["mot"] = m
                    cands[:10] = sorted(cands[:10], key=lambda x: -(x["diem"] + 0.03 * min(x.get("mot", 0) / 5.0, 1.0)))
                tot = None
                sach_hinh.kiem_truoc([(file_cua[cd["id"]], cd["bd"], cd["dai"])
                                      for cd in cands[:6] if cd["clip"] >= NGUONG])      # OCR song song
                if ent_tok:                               # chữ trong hình khớp tên thực thể = TƯ LIỆU cần có -> cộng điểm
                    for cd in cands[:6]:
                        if cd["clip"] >= NGUONG - THUONG_CHU:
                            tx_ = sach_hinh.chu_van(file_cua[cd["id"]], cd["bd"], cd["dai"])
                            if tx_ and (ent_tok & _toks(tx_)):
                                cd["khop_chu"] = True
                                cd["diem"] = round(cd["diem"] + THUONG_CHU, 4)
                                cd["clip"] = round(cd["clip"] + THUONG_CHU, 4)
                    cands[:10] = sorted(cands[:10], key=lambda x: -x["diem"])
                for nguong_ in (NGUONG, NGUONG_MEM):      # bước 2 nới ngưỡng: video thật điểm hơi thấp vẫn hơn ảnh điểm rất thấp
                    for cd in cands[:10]:                 # lấy đoạn tốt nhất KHÔNG có chữ cứng / khung đen
                        if cd["clip"] < nguong_:
                            continue
                        if sach_hinh.dau_cuoi_toi(file_cua[cd["id"]], cd["bd"], cd["dai"]):
                            continue
                        if sach_hinh.anh_tinh(file_cua[cd["id"]], cd["bd"], cd["dai"]):
                            continue                      # ảnh tĩnh/ảnh bị phóng làm thành video: không chọn
                        if not cd.get("khop_chu") and sach_hinh.co_chu(file_cua[cd["id"]], cd["bd"], cd["dai"]):
                            cd["co_chu"] = True
                            continue
                        tot = cd
                        break
                    if tot is not None:
                        break
                # không còn đoạn sạch -> để ô THIẾU (sau đó vá bằng ảnh hoặc thẻ), TUYỆT ĐỐI không giữ đoạn có chữ/logo
                if tot and tot["clip"] >= NGUONG_MEM:
                    alt = []
                    for x in cands:                       # đoạn dự phòng cũng phải sạch; dừng khi đủ 3 để khỏi OCR thừa
                        if len(alt) >= 3:
                            break
                        if (x is tot or x.get("co_chu") or x["clip"] < NGUONG
                                or sach_hinh.dau_cuoi_toi(file_cua[x["id"]], x["bd"], x["dai"])
                                or sach_hinh.anh_tinh(file_cua[x["id"]], x["bd"], x["dai"])
                                or (not x.get("khop_chu") and sach_hinh.co_chu(file_cua[x["id"]], x["bd"], x["dai"]))):
                            continue
                        alt.append(x)
                    tot["alt"] = alt
                    da_dung.setdefault(tot["id"], []).append((tot["bd"], tot["bd"] + dai_o))
                    so_lan[tot["id"]] = so_lan.get(tot["id"], 0) + 1
                    c["o"].append(tot)
                else:
                    c["o"].append({"thieu": True, "dai": round(dai_o, 2), "nhip": ni,
                                   "text": nh.get("text", ""),
                                   "diem": round(cands[0]["diem"], 4) if cands else 0.0})
    n_tot = sum(1 for c in canh for x in c.get("o", []) if not x.get("thieu"))
    n_all = sum(len(c.get("o", [])) for c in canh)
    log(f"    ô có hình: {n_tot}/{n_all}")
    ghi_json(duong_cache("chon.json"), canh)
    return canh
