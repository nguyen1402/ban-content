# -*- coding: utf-8 -*-
"""03/11 user: hiệu ứng NHẤN Ý cho câu ví von / câu then chốt ("key cho người xem không thoát ra ngoài ý"), dùng chung
mọi dự án. Chuyển động BÁM TỪNG CỤM TỪ của câu đang đọc ("remotion đúng theo từng chuyển động của câu nói"):
  1. AI đọc lời -> chọn câu + vẽ MỘT ảnh riêng cho câu (đúng vật / giai đoạn / nơi chốn, bố cục chừa chỗ cho từng vật)
     + các NHỊP: mỗi nhịp gắn một cụm từ NGUYÊN VĂN của câu và một động tác (phóng vào vật, khoanh, mũi tên, chữ nổi,
     số đếm). Cache ra/<dự án>/nhan_y_hoi.json.
  2. Flow vẽ ảnh; SigLIP dò VÙNG của từng vật trên ảnh (trượt cửa sổ) — vật không thấy rõ thì bỏ nhịp chỉ vào nó.
  3. Giờ của nhịp = giờ chữ đầu của cụm trong giọng đọc (mốc từng chữ wav2vec2 của can_chu).
  4. Remotion NhanY.jsx dựng clip (vào cảnh từ khung footage ngay trước); SFX chọn trong kho của user
     (kho_am_thanh/sfx/sfx-thu-vien-skill, tim_sfx.py theo loại sự kiện) đặt đúng nhịp, trừ onset.
  5. Ghép vào BẢN SAO bản nháp (tên mới, không đè): track hình 'nhan_y' trên cùng + 'nhan_y_sfx' (chỉnh / xoá tay được).

User 03/11 chê: kiểu sticker lắc lắc (cắt dán) và kiểu đóng băng khung — đã bỏ; không rung / lắc.

  python -X utf8 nhan_y.py --du-an caloc --goc caloc_hoan_chinh [--so 3]
"""
import argparse
import copy
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import uuid

AQ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQ)
for p in (ROOT, AQ):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import CACHE_CHUNG, FFMPEG, doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an, thu_muc_nhap_capcut  # noqa: E402

PUB = os.path.join(ROOT, "remotion", "public")
THU_PUB = "nhan_y"                     # ảnh của các clip nằm ở remotion/public/nhan_y/
LAM = ("toan_canh", "phong_vao", "khoanh", "mui_ten", "chu", "so_dem", "roi_xep", "nhan_ban")
VAO = ("mo", "xuyen", "cheo")
KIEU_XEP = ("dong", "chong", "tuong")  # đống (kim tự tháp) / chồng cao một cột / tường xếp hàng
VI_TRI = {"trai": [0.04, 0.22, 0.48, 0.93], "phai": [0.52, 0.22, 0.96, 0.93], "giua": [0.25, 0.2, 0.75, 0.93],
          "toan": [0.03, 0.12, 0.97, 0.93], "duoi": [0.06, 0.55, 0.94, 0.93]}
XEP_TOI_DA = 36                        # số bản sao tối đa của một vật trên hình (con số thật hiện bằng số đếm)
ROI_GIAY = 0.5                         # một bản sao rơi từ trên khung xuống chỗ nằm trong bấy nhiêu giây
VAT_NHO_NHAT = 0.12                    # bản sao rơi / nhân bản cao ít nhất bấy nhiêu phần chiều cao khung
MAT_DAT = 0.93                        # mép dưới của vật đứng / đống (0..1 theo chiều cao khung) — nền vẽ ngang tầm mắt
DUNG = {"trai": 0.27, "giua": 0.5, "phai": 0.73}
MOI_GIAY = 60.0                        # khoảng một chỗ nhấn ý mỗi bấy nhiêu giây lời đọc
CACH_TOI_THIEU = 30.0                  # hai chỗ nhấn ý cách nhau ít nhất bấy nhiêu giây
DAI_TOI_DA, DAI_TOI_THIEU = 10.0, 3.0  # độ dài clip (giây) = cả câu, câu quá dài thì cắt
SAU_CAU = 0.4                          # giữ thêm sau chữ cuối của câu
VUNG_LECH = 0.012                      # SigLIP: vùng của vật phải khớp vật đó hơn các vật khác ít nhất bấy nhiêu
# kho SFX của user (03/11): skill sfx-thu-vien — loại sự kiện trong data/su_kien.json
KHO_SFX = os.path.join(ROOT, "kho_am_thanh", "sfx", "sfx-thu-vien-skill", "sfx-thu-vien")
SFX_NHIP = {"phong_vao": "luot-qua", "khoanh": "nhan-nhe", "mui_ten": "chu-bay-vao", "chu": "dap-dau",
            "so_dem": "nhan-nhe", "xuyen": "chuyen-canh", "cheo": "chuyen-canh", "mo": "luot-qua"}
# 03/11 user ("nhức tai"): độ to theo CHUẨN của kho (SKILL.md "Chuẩn âm lượng"): mức nghe = 400 ms to nhất của âm, tính
# bằng LU so với độ to tích hợp của giọng đọc. Nhấn ý đặt nhỏ hơn chuẩn kho một chút (đè lên lời đọc).
SFX_LU, SFX_LU_CHOT = -15.0, -12.0     # tiếng thường / cú chốt
SFX_MOI_CLIP = 3                       # tối đa bấy nhiêu tiếng mỗi clip nhấn ý
TRACK_RIENG = ("nhan_y", "nhan_y_sfx")

_HOI = """You are a documentary motion designer. Below are the narration sentences of a video (index, start second,
text). Pick the sentences that most deserve a short ANIMATED EMPHASIS so the viewer cannot miss the idea: metaphors /
similes / vivid comparisons, turning points, shocking facts or numbers, the key conclusion. About one pick per {moi:.0f}
seconds, at least {cach:.0f} seconds apart, never in the first 5 seconds. Skip sentences marked [X].

For each pick, first invent a CINEMATIC IDEA ("y_tuong", one English sentence) the way a top motion designer of
documentary explainers would — the visual should make the idea physical and memorable, e.g.:
- "the city throws away 9,000 tonnes of plastic every day" -> ONE bottle drops onto an empty street, then hundreds rain
  down and pile into a mountain taller than the buildings while a counter climbs to 9,000.
- "a child would need to drink 40 litres of milk a day" -> start tight on the child alone; on "40 litres", milk cartons
  rain down beside the child and stack into a tower that dwarfs them, camera pulls back to reveal the scale.
Then build it from these pieces:
- The scene is COMPOSITED: an empty background plate + actors / objects drawn alone, cut out and placed by us, so we
  know exactly where everything is.
- "nen": English prompt for the photorealistic 16:9 BACKGROUND plate: EYE-LEVEL view (never aerial / top-down), flat
  empty ground across the lower part of the frame, nothing standing on it, no people. It sets place and mood only.
- "tach": every actor / object drawn ALONE (side view, full object in frame, isolated on a plain pure white background),
  {{"<key>": {{"ve": "<English prompt>", "dung": "trai"|"giua"|"phai", "cao": 0.2-0.8}}}}. Give "dung" (where it stands
  on the ground from the first frame) and "cao" (its height as a fraction of the frame) ONLY to things that are in the
  scene from the start (the person, the house…); things that fall / multiply have no "dung". 1-3 entries.
- "vat": things in the BACKGROUND worth pointing at (rarely needed), {{"<key>": "<short English description>"}}.
- "nhip": 2-6 beats IN NARRATION ORDER. "cum" = 1-4 words copied EXACTLY from the sentence (the beat starts when the
  narrator says them); "lam" = one of:
    "toan_canh" (whole frame), "phong_vao" ("vung" = a vat key or a tach key: camera moves onto it / onto its pile),
    "khoanh" (circle "vung"), "mui_ten" (arrow "vung" -> "den"),
    "roi_xep" ("tach" key falls from above and copies stack up: "so" = how many copies to SHOW (1-36), "kieu" = "dong"
      (heap/pyramid) | "chong" (one tall stack) | "tuong" (wall in rows), "vi_tri" = "trai"|"phai"|"giua"|"toan"|"duoi",
      "trong" = seconds the falling lasts 0.6-3),
    "nhan_ban" (the "tach" object multiplies, popping into a grid: "so", "vi_tri", "trong"),
    "canh_3d" (a REAL 3D scene instead of the composited image — use it when the 2D pieces cannot show the idea; give
      "mau" = the template and its fields. Templates: "nuoc_dang" — water floods into a walled basin (canal lock,
      reservoir, flooded street…) up to a depth: "muc" (final depth in metres), "cao_thanh" (wall height in metres,
      above "muc"), "rong" and "dai" (basin width / length in metres), "tuong" (English prompt: seamless flat texture
      of the wall surface, e.g. "weathered wet concrete"), "troi" (English prompt: the sky / landscape far behind),
      "nguoi" (English prompt of ONE person alone for scale — the person only, no place, or ""), "chu" (Vietnamese text
      when it is full).
      The beat's "cum" is when the water starts rising. A pick with "canh_3d" needs no "nen"/"tach").
      "giai_phau" — ANATOMY / STRUCTURE: the sentence describes the parts of something (a mouth, an organ, a
      machine…): "toan" (English prompt: the whole subject, side view, in its real habitat), "can" (English prompt:
      extreme close-up seen straight-on of the described part, centered — be anatomically exact), "chu_thich": a list
      IN NARRATION ORDER of {{"cum": words from the sentence, "kieu": "vien" (the rim / outline of the part) | "vong" (an
      inner ring) | "tam" (the very center) | "diem" (one spot), "r": 0-1 (distance from the center as a fraction of
      the part's radius), "goc": label direction in degrees (0 right, 90 down, 180 left, -90 up), "chu": 1-5
      Vietnamese words, "mo_ta_en": what that spot looks like in English}}; for "tam", "r" is the SIZE of the
      central part (0.15-0.5 of the radius). And
      optional "vi_von": {{"cum": words, "ve": English prompt of the compared object alone,
      "chu": short Vietnamese label}} when the sentence says "like / as" something.
      PREFER "canh_3d" whenever a template fits the sentence (depth, digging deeper, flooding, water level, filling up,
      "X metres deep", or describing the parts of something): these templates look far more professional than flat
      cut-outs for those ideas),
    "chu" (big on-screen text "chu": 2-6 Vietnamese words, numbers as digits),
    "so_dem" (number counting up: "so" = digits only, "chu" = 1-4 word unit/label).
  Optional "sfx" on any beat: one key of {sfx_loai}.
- STAGING RULES: never show a thing before the narration names it; the FIRST beat frames the first thing named
  ("phong_vao" on its vat key, cum = its words) and the rest stays out of frame or not yet fallen; the biggest visual
  change lands on the most important words; at most 2 text beats. Every "roi_xep" / "nhan_ban" beat MUST say which
  object in "tach".
- Things that fall land on the ground NEXT TO the standing actors (pick a "vi_tri" on the other side), and the pile
  should be bigger than the actor when the point is scale.
- Be literal and correct: the right species AND life stage (larva vs adult), objects exactly as named (trucks are
  modern motor trucks, not wagons), never invent an era the narration does not state. No text, labels or logos in
  any image.
- "vao": entry from the previous footage: "mo" (dissolve), "xuyen" (punch through, reveal), "cheo" (wipe, contrast).
Return ONLY JSON: {{"chon": [{{"i": <index>, "y_tuong": "...", "nen": "...", "tach": {{...}}, "vat": {{...}},
"nhip": [...], "vao": "..."}}]}}

Sentences:
{ds}"""


def _md5(*a):
    return hashlib.md5("|".join(map(str, a)).encode("utf-8")).hexdigest()[:14]


def _bo_dau(s):
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d"))
    return re.sub(r"[^a-z0-9 ]", "", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))


# --- lời + giờ từng chữ ---------------------------------------------------------------------------------------------
def _cau(du_an):
    """[{i, t0, t1, text, tu: [(chữ, bd, kt)]}] — cùng cách tách câu và giờ chữ với ✨ Hoàn thiện."""
    import du_an_moi
    import dung_hoan_chinh
    canh, _, _ = du_an_moi.tai(du_an, ban_do=False)
    return dung_hoan_chinh.tao_srt(canh)


def _gio_cum(c, cum):
    """Giây (tuyệt đối) chữ đầu của cụm trong câu c | None."""
    tu = c.get("tu") or []
    can = _bo_dau(cum).split()
    if not tu or not can:
        return None
    ds = [_bo_dau(w) for w, _, _ in tu]
    for j in range(len(ds) - len(can) + 1):
        if ds[j:j + len(can)] == can:
            return tu[j][1]
    for j, w in enumerate(ds):                                          # không khớp cả cụm: chữ đầu của cụm
        if w and w == can[0]:
            return tu[j][1]
    return None


# --- bản nháp -------------------------------------------------------------------------------------------------------
def _doc(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _ghi(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def _track_chinh(d):
    return next((t for t in d["tracks"] if t["type"] == "video"), None)


def _vung_ban(d):
    """Khoảng (giây) đã có lớp hình phủ (Veo, bản đồ, hiệu ứng, thẻ ảnh…) — không đặt nhấn ý đè lên."""
    chinh = _track_chinh(d)
    ra = []
    for t in d["tracks"]:
        if t["type"] != "video" or t is chinh or t.get("name") in TRACK_RIENG:
            continue
        for s in t["segments"]:
            tr = s["target_timerange"]
            ra.append((tr["start"] / 1e6, (tr["start"] + tr["duration"]) / 1e6))
    return ra


def _khung(d, t, out):
    """Ảnh khung hình track chính ở giây t (đúng điểm vào nguồn + phóng của đoạn) -> out.jpg | None."""
    mats = {m["id"]: m for m in d["materials"].get("videos", [])}
    for s in _track_chinh(d)["segments"]:
        tr, sr = s["target_timerange"], s.get("source_timerange") or {"start": 0}
        if not (tr["start"] <= t * 1e6 < tr["start"] + tr["duration"]):
            continue
        m = mats.get(s["material_id"]) or {}
        f = m.get("path")
        if not f or not os.path.isfile(f):
            return None
        sc = float(((s.get("clip") or {}).get("scale") or {}).get("x") or 1.0)
        loc = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        if sc > 1.01:                                                    # đoạn được phóng (giấu logo góc) -> cắt giữa
            loc += f",crop=iw/{sc:.3f}:ih/{sc:.3f},scale=1920:1080"
        lenh = [FFMPEG, "-y", "-loglevel", "error"]
        if m.get("type") != "photo":
            lenh += ["-ss", f"{(sr['start'] + t * 1e6 - tr['start']) / 1e6:.3f}"]
        lenh += ["-i", f, "-frames:v", "1", "-vf", loc, "-q:v", "2", out]
        subprocess.run(lenh, capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
        return out if os.path.isfile(out) else None
    return None


# --- chọn câu + lên nhịp --------------------------------------------------------------------------------------------
def _sfx_loai():
    return [k for k, v in (doc_json(os.path.join(KHO_SFX, "data", "su_kien.json"), {}) or {}).items() if not v.get("nhac")]


def chon(du_an, cau, ban, chi=None):
    """AI nghĩ ý tưởng + nền + vật tách + nhịp (cache ra/<dự án>/nhan_y_hoi.json theo lời).
    chi: chỉ lên ý tưởng cho đúng các câu này (thử / làm lại một chỗ). -> [{i, y_tuong, nen, tach, vat, nhip, vao}]"""
    out = thu_muc_du_an(du_an)[1]
    p = os.path.join(out, "nhan_y_hoi.json")
    khoa = _md5("v10", sorted(chi or []), *[c["text"] for c in cau])
    cu = doc_json(p, {}) or {}
    if cu.get("khoa") == khoa and cu.get("chon"):
        return cu["chon"]
    trung = lambda c: any(a < c["t1"] and c["t0"] < b for a, b in ban)          # noqa: E731
    ds = "\n".join(f"{c['i']} [{c['t0']:.0f}s]{' [X]' if trung(c) else ''} {c['text']}" for c in cau)
    hoi = _HOI.format(moi=MOI_GIAY, cach=CACH_TOI_THIEU, ds=ds, sfx_loai=", ".join(_sfx_loai()))
    if chi:
        hoi = hoi.replace("Pick the sentences that most deserve", f"Design ONLY for sentences {', '.join(map(str, chi))}"
                          " (ignore the spacing rule below). They deserve")
    log(f"[nhấn ý] hỏi AI nghĩ ý tưởng + lên nhịp chuyển động ({len(chi) if chi else len(cau)} câu)…")
    r = rut_json(hoi_llm(hoi)) or {}
    ra = [x for x in r.get("chon") or [] if isinstance(x, dict) and isinstance(x.get("i"), int) and isinstance(x.get("nhip"), list)
          and (x.get("nen") or any(isinstance(n, dict) and n.get("lam") == "canh_3d" for n in x["nhip"]))
          and (not chi or x["i"] in chi)]
    if ra:
        ghi_json(p, {"khoa": khoa, "chon": ra})
    return ra


# --- ảnh + vùng -------------------------------------------------------------------------------------------------------
def _ve(prompt, k):
    """Flow vẽ (2 ảnh/lượt) -> [đường dẫn PNG] (cache theo câu lệnh)."""
    import flow_ve
    thu = os.path.join(CACHE_CHUNG, "nhan_y", "ve")
    os.makedirs(thu, exist_ok=True)
    co = sorted(glob.glob(os.path.join(thu, f"{k}_*.png")))
    return co or flow_ve.ve_nhieu(prompt, thu, k, "16:9") or []


def _do_vung(f, vat):
    """SigLIP trượt cửa sổ trên ảnh -> ({khoá: [x0, y0, x1, y1]}, điểm trung bình). Vật không nổi rõ hơn các vật khác
    ở đâu cả thì không có vùng."""
    import numpy as np
    import nhung_siglip
    from PIL import Image
    im = Image.open(f).convert("RGB")
    W, H = im.size
    o = []
    for s in (0.32, 0.45, 0.62):
        w, h = int(H * s * 1.25), int(H * s)
        for y in np.linspace(0, H - h, 4).astype(int):
            for x in np.linspace(0, W - w, 6).astype(int):
                o.append((x, y, x + w, y + h))
    khoa = list(vat)
    E = nhung_siglip.nhung_anh([im.crop(b) for b in o])
    T = nhung_siglip.nhung_chu([f"a photo of {vat[k]}" for k in khoa])
    S = E @ T.T                                                          # [cửa sổ, vật]
    ra, diem = {}, []
    for j, k in enumerate(khoa):
        khac = np.delete(S, j, axis=1).max(axis=1) if len(khoa) > 1 else np.full(len(o), S[:, j].mean())
        lech = S[:, j] - khac
        b = int(np.argmax(S[:, j] + lech))
        if lech[b] >= VUNG_LECH or len(khoa) == 1:
            x0, y0, x1, y1 = o[b]
            ra[k] = [round(x0 / W, 3), round(y0 / H, 3), round(x1 / W, 3), round(y1 / H, 3)]
            diem.append(float(S[b, j]))
    return ra, (sum(diem) / len(diem) if diem else 0.0)


def _tach(prompt):
    """Vật vẽ riêng trên nền trắng -> tách nền sạch -> ('nhan_y/<k>.png', rộng/cao) | (None, 1)."""
    import anh_tach
    import cat_nen
    from PIL import Image
    # Flow hay vẽ kèm mảng đất / bóng dưới vật -> tách ra cả miếng đất (03/11 xem thử caloc)
    prompt = f"{prompt.rstrip('. ')}. The object alone floating in empty white space: no ground, no surface, no shadow, no text."
    k = _md5("tach", prompt)
    dich = os.path.join(PUB, THU_PUB, f"{k}.png")
    if not os.path.isfile(dich):
        for f in _ve(prompt, k):
            cat_nen.tach_nen(f, dich, nen_trang=True)
            ok, ly_do = anh_tach._sach(dich, nhieu_manh=False)           # noqa: SLF001
            if ok:
                break
            log(f"    ! vật tách '{prompt[:50]}': {ly_do}")
            os.remove(dich)
    if not os.path.isfile(dich):
        return None, 1.0
    im = Image.open(dich)
    if max(im.size) > 700:                                               # nhiều bản sao: ảnh nhỏ cho nhẹ
        im.thumbnail((700, 700), Image.LANCZOS)
        im.save(dich)
    return f"{THU_PUB}/{k}.png", im.size[0] / max(1, im.size[1])


def _xep(kieu, n, vt, ti, trong, roi=True, hat=0):
    """Vị trí từng bản sao (toạ độ 0..1 trên khung 16:9): [{x, y (tâm), w, r (độ), d (giây trễ), roi}] + khung bao.
    ti = rộng/cao của vật. Xếp từ dưới lên (rơi trước nằm dưới), lệch nhẹ cố định (không lắc)."""
    import math
    import random
    rd = random.Random(hat)
    x0, y0, x1, y1 = vt
    R = x1 - x0
    hw = lambda w: w * (16 / 9) / ti                                    # noqa: E731  chiều cao (theo khung) của vật rộng w
    wh = lambda h: h * ti * 9 / 16                                      # noqa: E731  chiều rộng của vật cao h
    Hr = y1 - y0
    # 03/11 (xem thử caloc: 28 khay thịt thành cột mảnh, xe tải thành dải tí xíu): vật không nhỏ hơn VAT_NHO_NHAT chiều
    # cao khung — thiếu chỗ thì BỚT bản sao (con số thật đã có số đếm), không thu nhỏ vật
    o = []
    if kieu == "chong":
        h = min(Hr / ((n - 1) * 0.82 + 1), hw(R * 0.8))
        if h < VAT_NHO_NHAT:
            h = min(VAT_NHO_NHAT, hw(R * 0.8))
            n = max(1, int((Hr / h - 1) / 0.82) + 1)
        w = wh(h)
        for i in range(n):
            o.append(((x0 + x1) / 2 + rd.uniform(-0.06, 0.06) * w, y1 - h / 2 - i * h * 0.82, w, rd.uniform(-4, 4)))
    elif kieu == "tuong":
        cot = 1
        while True:
            w = R / cot
            h = hw(w)
            hang = math.ceil(n / cot)
            if hang * h * 0.92 <= Hr or h <= VAT_NHO_NHAT:
                break
            cot += 1
        if h < VAT_NHO_NHAT:
            h = min(VAT_NHO_NHAT, Hr)
            w = min(R, wh(h))
            cot = max(1, int(R / w))
            n = min(n, cot * max(1, int(Hr / (h * 0.92))))
        for i in range(n):
            r_, c_ = divmod(i, cot)
            con = min(cot, n - r_ * cot)                                   # hàng trên thiếu: căn giữa
            o.append(((x0 + x1) / 2 + (c_ - (con - 1) / 2) * w, y1 - h / 2 - r_ * h * 0.92, w * 0.96, rd.uniform(-1.5, 1.5)))
    else:                                                                # đống: hàng dưới nhiều, lên trên ít dần (chồng dày)
        k = 1
        while k * (k + 1) // 2 < n:
            k += 1
        # 03/11 (xem cả bài caloc: súc thịt / cá dáng dài -> đống chỉ 2-3 cái): vật càng dẹt càng gối lên nhau nhiều theo
        # chiều ngang, và đống được loang rộng ra hai bên vùng
        bx = 0.62 if ti <= 1.3 else max(0.36, 0.62 / ti ** 0.5)
        R = max(R, 0.62)
        cx0 = min(1 - R / 2, max(R / 2, (x0 + x1) / 2))
        while True:
            h = Hr / ((k - 1) * 0.7 + 1)                                 # đống cao kín vùng
            w = wh(h)
            if (k - 1) * bx * w + w > R:                                 # hàng dưới rộng quá vùng: thu theo chiều ngang
                w = R / ((k - 1) * bx + 1)
                h = hw(w)
            if h >= VAT_NHO_NHAT or k == 1:
                break
            k -= 1
        n = min(n, k * (k + 1) // 2)
        i = 0
        for r_ in range(k):
            m = k - r_
            for c_ in range(m):
                if i >= n:
                    break
                x = cx0 + (c_ - (m - 1) / 2) * w * bx + rd.uniform(-0.1, 0.1) * w
                o.append((x, y1 - h / 2 - r_ * h * 0.7, w, rd.uniform(-9, 9)))
                i += 1
    buoc = trong / max(1, len(o))
    ds = [{"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "r": round(r, 1), "d": round(j * buoc, 3), "roi": roi}
          for j, (x, y, w, r) in enumerate(o)]
    bao = [min(i["x"] - i["w"] / 2 for i in ds), min(i["y"] - hw(i["w"]) / 2 for i in ds),
           max(i["x"] + i["w"] / 2 for i in ds), max(i["y"] + hw(i["w"]) / 2 for i in ds)] if ds else list(vt)
    return ds, [round(max(0.0, v), 3) if j < 2 else round(min(1.0, v), 3) for j, v in enumerate(bao)]


def _anh(x):
    """Ảnh nền của chỗ nhấn ý: trong 2 ảnh Flow lấy ảnh dò được nhiều vật nhất -> ('nhan_y/<k>.jpg', vùng) | (None, {})."""
    k = _md5("anh", x["nen"])
    ds = _ve(x["nen"] + " Absolutely no text, letters or labels anywhere.", k)
    if not ds:
        return None, {}
    vat = {str(a): str(b) for a, b in (x.get("vat") or {}).items() if b}
    tot = None
    for f in ds:
        vg, dd = _do_vung(f, vat) if vat else ({}, 0.0)
        if tot is None or (len(vg), dd) > (len(tot[1]), tot[2]):
            tot = (f, vg, dd)
    f, vg, _ = tot
    dich = os.path.join(PUB, THU_PUB, f"{k}.jpg")
    if not os.path.isfile(dich):
        try:
            import anh_ve
            anh_ve.xoa_logo(f, moi=True)                                 # dấu ✦ của Flow
        except Exception:                                                # noqa: BLE001
            pass
        from PIL import Image
        Image.open(f).convert("RGB").resize((1920, 1080)).save(dich, quality=92)
    return f"{THU_PUB}/{k}.jpg", vg


# --- SFX (kho của user) -----------------------------------------------------------------------------------------------
_SFX_CACHE = {}


def _ebur(f, dai=None):
    """(độ to tích hợp LUFS, 400 ms to nhất LUFS) của tệp (ffmpeg ebur128)."""
    lenh = [FFMPEG, "-hide_banner", "-nostats"] + (["-t", f"{dai:.3f}"] if dai else []) + ["-i", f, "-af", "apad=pad_dur=0.5,ebur128",
                                                                                           "-f", "null", "-"]
    r = subprocess.run(lenh, capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    t = r.stderr.decode("utf-8", "ignore")
    m = [float(v) for v in re.findall(r"\bM:\s*(-?[\d.]+)", t)]
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", t)
    return (float(i[-1]) if i else -23.0), (max(m) if m else -70.0)


def _am_luong(f, gd, chinh):
    """Âm lượng (hệ số) để tiếng nghe ở SFX_LU / SFX_LU_CHOT so với giọng đọc gd (LUFS); tối đa x4 như bộ trộn của kho."""
    _, mm = _ebur(f, 3.0)
    db = gd + (SFX_LU_CHOT if chinh else SFX_LU) - mm
    return round(min(4.0, max(0.05, 10 ** (db / 20))), 3)


def _sfx(loai, lan):
    """Âm cho loại sự kiện `loai` (data/su_kien.json) — xoay vòng 3 âm hợp nhất để không lặp một âm. -> (file, onset)"""
    if loai not in _SFX_CACHE:
        sk = (doc_json(os.path.join(KHO_SFX, "data", "su_kien.json"), {}) or {}).get(loai) or {}
        lenh = [sys.executable, os.path.join(KHO_SFX, "scripts", "tim_sfx.py"), sk.get("nhan") or loai, "-n", "3", "--json"]
        if sk.get("duoi"):
            lenh += ["--duoi", str(sk["duoi"])]
        lenh += ["--ngu-canh", f"su_kien={loai},video=tai-lieu"]
        r = subprocess.run(lenh, capture_output=True, cwd=KHO_SFX, env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                           creationflags=0x08000000 if os.name == "nt" else 0)
        try:
            _SFX_CACHE[loai] = [(x["path"], float(x.get("onset") or 0)) for x in json.loads(r.stdout.decode("utf-8"))
                                if os.path.isfile(x.get("path", ""))]
        except ValueError:
            _SFX_CACHE[loai] = []
    ds = _SFX_CACHE[loai]
    return ds[lan % len(ds)] if ds else None


# --- dựng -------------------------------------------------------------------------------------------------------------
# --- cảnh mẫu 3D + chỉnh tay trong Remotion Studio ------------------------------------------------------------------------
# 03/11 user: "tôi phải được phép động tay vào chỉnh sửa": mỗi chỗ dựng bằng cảnh mẫu 3D là một mục trong thư mục
# "sua-tay" của Remotion Studio. Studio chỉ LƯU NGƯỢC được vào chính tệp Root viết bằng TypeScript, với defaultProps là
# object viết thẳng (docs: troubleshooting/cannot-save-default-props) -> các mục nằm trong remotion/src/Root.tsx, giữa hai
# dấu NHAN_Y_SUA_BAT_DAU / NHAN_Y_SUA_KET_THUC. Lần chạy sau đọc lại: thông số khác bản máy ghi lần trước = user đã sửa
# tay -> giữ nguyên, không lấy bản AI mới đè lên.
ROOT_TSX = os.path.join(ROOT, "remotion", "src", "Root.tsx")
MOC_DAU, MOC_CUOI = "{/* NHAN_Y_SUA_BAT_DAU", "{/* NHAN_Y_SUA_KET_THUC */}"
MAU_3D = {"nuoc_dang": ("NuocDang", "nuocDangSchema", "NUOC_DANG_MAC_DINH", "Canh3D.jsx"),
          "giai_phau": ("GiaiPhau", "giaiPhauSchema", "GIAI_PHAU_MAC_DINH", "GiaiPhau.jsx")}


def _cho_sua_doc():
    """{id: (comp, props)} đang có trong khối sửa tay của Root.tsx (Studio có thể đã ghi lại) — đọc bằng node."""
    if not os.path.isfile(ROOT_TSX):
        return {}
    js = r"""const t=require('fs').readFileSync(process.argv[1],'utf8');const a=t.indexOf('NHAN_Y_SUA_BAT_DAU'),
b=t.indexOf('NHAN_Y_SUA_KET_THUC');const s=a<0||b<0?'':t.slice(a,b);const ra={};
const re=/<Composition\s+id="([^"]+)"\s+component=\{(\w+)\}/g;let m;
while((m=re.exec(s))){const i=s.indexOf('defaultProps={',m.index);if(i<0)continue;let j=i+14,d=0;
for(let k=j;k<s.length;k++){const ch=s[k];if(ch==='{')d++;else if(ch==='}'){if(d===0){j=k;break}d--}}
const staticFile=(x)=>x;try{ra[m[1]]=[m[2],eval('('+s.slice(i+14,j)+')')]}catch(e){}}
process.stdout.write(JSON.stringify(ra));"""
    r = subprocess.run(["node", "-e", js, ROOT_TSX], capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        return {k: (v[0], v[1]) for k, v in json.loads(r.stdout.decode("utf-8") or "{}").items()}
    except ValueError:
        return {}


def _cho_sua_ghi(muc):
    """Thay khối sửa tay trong Root.tsx bằng các mục muc = {id: (comp, props)} (phần còn lại của Root giữ nguyên)."""
    t = open(ROOT_TSX, encoding="utf-8").read()
    a, b = t.find(MOC_DAU), t.find(MOC_CUOI)
    if a < 0 or b < 0:
        raise SystemExit("Root.tsx thiếu dấu NHAN_Y_SUA_BAT_DAU / NHAN_Y_SUA_KET_THUC")
    a = t.index("*/}", a) + 3
    dong = []
    for k, (comp, pr) in sorted(muc.items()):
        sch = next((v[1] for v in MAU_3D.values() if v[0] == comp), (comp[:-1] if comp.endswith("G") else comp) + "Schema" if comp.startswith("Ai") else None)
        dong.append(f'      <Composition id="{k}" component={{{comp}}} width={{1920}} height={{1080}} fps={{FPS}}'
                    f' durationInFrames={{150}}{" schema={" + sch + "}" if sch else ""} calculateMetadata={{meta}}' + chr(10) +
                    f'        defaultProps={{{json.dumps(pr, ensure_ascii=False)}}} />')
    t = t[:a] + chr(10) + chr(10).join(dong) + (chr(10) if dong else "") + "      " + t[b:]
    with open(ROOT_TSX, "w", encoding="utf-8", newline=chr(10)) as f:
        f.write(t)


def _mac_dinh_3d(comp):
    """Thông số mặc định của cảnh mẫu 3D (đọc thẳng từ Canh3D.jsx để Studio có đủ ô)."""
    ten, tep = next(((v[2], v[3]) for v in MAU_3D.values() if v[0] == comp), (None, "Canh3D.jsx"))
    js = r"""const s=require('fs').readFileSync(process.argv[1],'utf8');const i=s.indexOf('export const '+process.argv[2]+' = {');
let j=s.indexOf('{',i),d=0,k=j;for(;k<s.length;k++){if(s[k]==='{')d++;else if(s[k]==='}'){d--;if(!d)break}}
process.stdout.write(JSON.stringify(eval('('+s.slice(j,k+1)+')')));"""
    r = subprocess.run(["node", "-e", js, os.path.join(ROOT, "remotion", "src", tep), ten or ""], capture_output=True,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        return json.loads(r.stdout.decode("utf-8") or "{}")
    except ValueError:
        return {}


def _anh_jpg(prompt, k, cat=(1920, 1080)):
    """Flow vẽ -> 'nhan_y/<k>.jpg' (đã xoá dấu ✦) | None."""
    from PIL import Image
    dich = os.path.join(PUB, THU_PUB, f"{k}.jpg")
    if not os.path.isfile(dich):
        ds = _ve(prompt, k)
        if not ds:
            return None
        try:
            import anh_ve
            anh_ve.xoa_logo(ds[0], moi=True)
        except Exception:                                                # noqa: BLE001
            pass
        Image.open(ds[0]).convert("RGB").resize(cat).save(dich, quality=92)
    return f"{THU_PUB}/{k}.jpg"


def _bo_phan(f):
    """Tâm + bán kính (theo chiều rộng) của bộ phận nổi bật nhất trên ảnh cận cảnh (mặt nạ tách nền)."""
    import cat_nen
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    tam = os.path.join(CACHE_CHUNG, "nhan_y", "_bo_phan.png")
    cat_nen.tach_nen(f, tam, cat_vien=False)
    a = np.asarray(Image.open(tam).getchannel("A")) > 128
    nhan, n = ndimage.label(a)
    if not n:
        return [0.5, 0.5], 0.3
    lon = 1 + int(np.argmax(ndimage.sum(np.ones_like(nhan), nhan, range(1, n + 1))))
    ys, xs = np.nonzero(nhan == lon)
    h, w = a.shape
    r = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 / w
    if r < 0.08:                                                         # dò hỏng: lấy giữa khung
        return [0.5, 0.5], 0.3
    return [round(float((xs.min() + xs.max()) / 2 / w), 3), round(float((ys.min() + ys.max()) / 2 / h), 3)], round(float(r), 3)


def _diem_trong(f, tam, ban_kinh, mo_ta):
    """SigLIP: tâm cửa sổ nhỏ trong vùng bộ phận khớp mô tả nhất -> [x, y] (0..1 của ảnh) | None.
    03/11 (câu 52: vòng "lưỡi" khoanh vào lỗ họng ở giữa, lưỡi thật nằm thấp hơn): AI không nhìn ảnh nên không biết."""
    import numpy as np
    import nhung_siglip
    from PIL import Image
    im = Image.open(f).convert("RGB")
    W, H = im.size
    cx, cy, R = tam[0] * W, tam[1] * H, min(ban_kinh * W, 0.48 * H)
    o = []
    for k in (0.22, 0.32):
        s_ = int(R * k * 2)
        for dy in np.linspace(-0.5, 0.5, 7):
            for dx in np.linspace(-0.5, 0.5, 7):
                x0, y0 = int(cx + dx * R - s_ / 2), int(cy + dy * R - s_ / 2)
                if 0 <= x0 and 0 <= y0 and x0 + s_ <= W and y0 + s_ <= H:
                    o.append((x0, y0, x0 + s_, y0 + s_))
    if not o:
        return None
    E = nhung_siglip.nhung_anh([im.crop(b) for b in o])
    T = nhung_siglip.nhung_chu([f"a close-up photo of {mo_ta}"])
    b = o[int(np.argmax((E @ T.T)[:, 0]))]
    return [round((b[0] + b[2]) / 2 / W, 3), round((b[1] + b[3]) / 2 / H, 3)]


def _ben_trong(ct):
    """Góc khung không có nhãn nào -> chỗ đặt thẻ ví von (duoi_phai / duoi_trai / tren_phai / tren_trai)."""
    import math
    co = set()
    for q in ct:
        g = math.radians(q["goc"])
        co.add(("tren" if math.sin(g) < -0.2 else "duoi" if math.sin(g) > 0.2 else "giua") + "_" +
               ("phai" if math.cos(g) >= 0 else "trai"))
    return next((b for b in ("duoi_phai", "duoi_trai", "tren_phai", "tren_trai") if b not in co), "duoi_phai")


def _giai_phau(x, c, n, du_an):
    """Cảnh mẫu GIẢI PHẪU: toàn thân -> kính lúp mở cận cảnh -> chú thích từng bộ phận đúng lúc lời đọc nhắc."""
    if not n.get("can"):
        return None
    can = _anh_jpg(f"{n['can']}. Extreme close-up, straight-on, the part perfectly centered and filling about 60% of the "
                   "frame, photorealistic, sharp detail. No text, no labels.", _md5("gp-can", n["can"]))
    if not can:
        log(f"    ! câu {x['i']}: không vẽ được ảnh cận cảnh")
        return None
    toan = _anh_jpg(f"{n['toan']}. Photorealistic. No text.", _md5("gp-toan", n["toan"])) if n.get("toan") else ""
    tam, ban_kinh = _bo_phan(os.path.join(PUB, can))

    def gio(cum, mac):
        g = _gio_cum(c, cum or "")
        return round(g - x["t0"], 2) if g is not None else mac
    ct, sk = [], []
    for j, q in enumerate(n.get("chu_thich") or []):
        if not isinstance(q, dict) or not q.get("chu"):
            continue
        t = max(gio(q.get("cum"), 1.5 + 1.8 * j), (ct[-1]["t"] + 1.2) if ct else 0.0)
        kieu = q.get("kieu") if q.get("kieu") in ("vien", "vong", "tam", "diem") else "diem"
        r = 1.0 if kieu == "vien" else (max(0.12, min(0.6, float(q.get("r") or 0.3))) if kieu == "tam"
                                         else max(0.0, min(1.2, float(q.get("r") or 0.6))))
        goc = float(q["goc"]) if q.get("goc") is not None else [-35, 35, 150, -150][j % 4]
        diem = (_diem_trong(os.path.join(PUB, can), tam, ban_kinh, str(q["mo_ta_en"]))
                if kieu == "diem" and q.get("mo_ta_en") else None) or [-1, -1]
        ct.append({"t": round(t, 2), "kieu": kieu, "r": r, "goc": goc, "chu": str(q["chu"]), "x": diem[0], "y": diem[1]})
        sk.append((t + 0.3, "dap-dau", False))
    if not ct:
        return None
    vao = round(max(0.5, ct[0]["t"] - 1.0), 2) if toan else 0.0
    for q in ct:                                                         # chú thích hiện sau khi kính lúp mở xong
        q["t"] = round(max(q["t"], vao + 0.9), 2)
    vv = n.get("vi_von") if isinstance(n.get("vi_von"), dict) else {}
    vv_anh = _tach(str(vv["ve"]))[0] if vv.get("ve") else None
    vv_t = round(max(gio(vv.get("cum"), ct[-1]["t"] + 0.6), ct[-1]["t"] + 0.6), 2) if vv_anh else 0
    x["giay"] = round(max(x["giay"], max([q["t"] for q in ct] + [vv_t]) + 1.8), 2)
    pr = _mac_dinh_3d("GiaiPhau") | {"giay": x["giay"], "toan": toan, "can": can, "tam": tam, "ban_kinh": ban_kinh,
                                      "vao_can": vao, "chu_thich": ct, "vi_von_anh": vv_anh or "",
                                      "vi_von_chu": str(vv.get("chu") or ""), "vi_von_t": vv_t,
                                      # thẻ ví von về góc dưới phía có ít nhãn (xem thử: đè lên nhãn dưới phải)
                                      "vi_von_ben": _ben_trong(ct)}
    sk = [(vao, "luot-qua", False)] + sk[:2] + ([(vv_t, "pop", True)] if vv_anh else [])
    return pr | {"_comp": "GiaiPhau", "_id": f"{du_an}-cau{x['i']}".replace("_", "-")}, sk


def _canh_3d(x, n, du_an):
    """Chỗ nhấn ý dựng bằng cảnh mẫu 3D -> (id trong Studio, comp, props máy dựng) | None."""
    mau = n.get("mau")
    if mau not in MAU_3D:
        return None
    from PIL import Image
    pr = {}
    if mau == "nuoc_dang":
        muc = max(0.5, float(n.get("muc") or 8))
        cao = max(muc * 1.2, float(n.get("cao_thanh") or muc * 1.3))
        rong = max(6.0, min(60.0, float(n.get("rong") or 16)))
        pr = _mac_dinh_3d(MAU_3D[mau][0]) | {"muc_nuoc": round(muc, 2), "cao_thanh": round(cao, 2), "rong": rong,
                                             "dai": max(rong * 2, min(rong * 4, float(n.get("dai") or 60))),   # vừa khung
                                             "chu": str(n.get("chu") or "")}
        k_ = (rong / 16) ** 0.5                                          # camera mặc định chỉnh cho lòng rộng 16 m
        for kk in ("cam_dau", "cam_giua", "cam_cuoi", "nhin"):
            pr[kk] = [round(v * k_, 2) for v in pr[kk]]
        pr["cam_cuoi"][1] = round(max(pr["cam_cuoi"][1], cao + 4), 2)    # cuối cảnh vẫn ở trên mặt nước
        for kk, mo_ta, cat in (("tuong", n.get("tuong"), (1024, 1024)), ("troi", n.get("troi"), (1920, 1080))):
            if not mo_ta:
                continue
            k = _md5("3d-v2", kk, mo_ta)
            dich = os.path.join(PUB, THU_PUB, f"{k}.jpg")
            if not os.path.isfile(dich):
                # 03/11 (xem thử: AI tả cả thang sắt, khớp nối -> lặp lại trông giả): chỉ lấy CHẤT LIỆU bề mặt
                cau_lenh = (f"Plain close-up photo of the bare surface material only: {mo_ta}. Flat even lighting, "
                            "straight-on, seamless tileable texture, no objects, no ladders, no joints, no edges"
                            if kk == "tuong" else f"{mo_ta}. Photorealistic")
                ds = _ve(cau_lenh + ". No text, no people.", k)
                if not ds:
                    continue
                im = Image.open(ds[0]).convert("RGB")
                if kk == "tuong":                                        # lấy ô vuông giữa làm texture lặp
                    w, h = im.size
                    im = im.crop(((w - h) // 2, 0, (w + h) // 2, h))
                im.resize(cat).save(dich, quality=90)
            pr[kk] = f"{THU_PUB}/{k}.jpg"
        if n.get("nguoi"):                                               # chỉ MỘT người đứng, không cảnh vật (xem thử: AI
            mo = re.sub(r"(standing|on|at|atop|near|beside).*$", "", str(n["nguoi"]), flags=re.I).strip(" ,.")
            f, ti = _tach(f"{mo or 'a worker'}, ONE person alone, full body standing upright, front view, no ground, no scenery")
            if f and ti < 0.8:                                           # dáng người đứng: cao hơn rộng rõ rệt
                pr["nguoi"] = f
            elif f:
                log(f"    ! câu {x['i']}: ảnh người không phải dáng đứng (rộng/cao {ti:.2f}) — bỏ người")
    return f"{du_an}-cau{x['i']}".replace("_", "-"), MAU_3D[mau][0], pr


def _chuan_bi(x, c, d, du_an):
    """Một chỗ nhấn ý -> (props, [(giây so với đầu clip, loại SFX, cú chốt)]) | (None, []).
    props có "_comp" = cảnh Remotion dựng nó (NhanY ảnh ghép lớp, hoặc cảnh mẫu 3D); "_id" = mục trong Studio."""
    os.makedirs(os.path.join(PUB, THU_PUB), exist_ok=True)
    n3 = next((n for n in x.get("nhip") or [] if n.get("lam") == "canh_3d"), None)
    if n3 and n3.get("mau") == "giai_phau":
        r3 = _giai_phau(x, c, n3, du_an)
        if r3:
            return r3
    elif n3:
        r3 = _canh_3d(x, n3, du_an)
        if r3:
            ma, comp, pr = r3
            g = _gio_cum(c, n3.get("cum") or "")
            bd = round(max(0.3, (g - x["t0"]) if g is not None else 0.8), 2)
            x["giay"] = round(max(x["giay"], bd + 5.5), 2)
            pr = pr | {"giay": x["giay"], "bat_dau_dang": bd, "thoi_gian_dang": round(min(5.0, x["giay"] - bd - 1.6), 2),
                       "chu_luc": round(x["giay"] - 1.5, 2)}
            return pr | {"_comp": comp, "_id": ma}, [(bd, "nuoc", False), (bd + pr["thoi_gian_dang"], "nhan-nhe", True)]
    if not x.get("nen"):
        return None, []
    anh, vung = _anh(x)
    if not anh:
        log(f"    ! câu {x['i']}: Flow không vẽ được ảnh")
        return None, []
    k = _md5(du_an, x["i"], x["t0"])
    nen = _khung(d, max(0.0, x["t0"] - 0.05), os.path.join(PUB, THU_PUB, f"{k}_nen.jpg"))
    tach, xep = {}, []
    for kk, p in (x.get("tach") or {}).items():
        p = p if isinstance(p, dict) else {"ve": p}
        f, ti = _tach(str(p.get("ve") or ""))
        if not f:
            log(f"    ! câu {x['i']}: vật '{kk}' không tách nền được — bỏ các nhịp của nó")
            continue
        tach[str(kk)] = (f, ti)
        if p.get("dung") in DUNG:                                        # diễn viên đứng sẵn trên mặt đất từ đầu cảnh
            h = max(0.15, min(0.85, float(p.get("cao") or 0.5)))
            w = min(0.6, h * ti * 9 / 16)
            cx = DUNG[p["dung"]]
            xep.append({"t": 0, "src": f, "ti": round(ti, 4), "o": [{"x": cx, "y": round(MAT_DAT - h / 2, 4), "w": round(w, 4),
                                                                      "r": 0, "d": 0, "roi": False, "tinh": True}]})
            vung[str(kk)] = [round(cx - w / 2, 3), round(MAT_DAT - h, 3), round(cx + w / 2, 3), MAT_DAT]
    loai_sfx = set(_sfx_loai())
    # đống / tường của vật tách: tính trước để nhịp phong_vao / khoanh nhắm được vào đống (kể cả nhịp đứng trước)
    xep_cua = {}
    for j, n in enumerate(x.get("nhip") or []):
        if n.get("lam") in ("roi_xep", "nhan_ban") and str(n.get("tach")) not in tach and len(tach) == 1:
            n["tach"] = next(iter(tach))                                 # AI quên ghi vật nào rơi mà chỉ có một vật
        if n.get("lam") in ("roi_xep", "nhan_ban") and str(n.get("tach")) in tach:
            f, ti = tach[str(n["tach"])]
            so = max(1, min(XEP_TOI_DA, int(float(re.sub(r"[^\d.]", "", str(n.get("so") or "")) or 12))))
            vt = VI_TRI.get(n.get("vi_tri"), VI_TRI["giua"])
            trong = max(0.3, min(3.0, float(n.get("trong") or 1.5)))
            kieu = n.get("kieu") if n.get("kieu") in KIEU_XEP else ("tuong" if n["lam"] == "nhan_ban" else "dong")
            ds, bao = _xep(kieu, so, vt, ti, trong, roi=n["lam"] == "roi_xep", hat=j)
            xep_cua[j] = {"src": f, "ti": round(ti, 4), "o": ds, "trong": trong}
            vung.setdefault(str(n["tach"]), bao)
    nhip, sk = [], []
    for j, n in enumerate(x.get("nhip") or []):
        lam = n.get("lam")
        if lam not in LAM:
            continue
        if lam in ("roi_xep", "nhan_ban") and j not in xep_cua:
            continue
        if lam in ("phong_vao", "khoanh") and n.get("vung") not in vung:
            lam = "toan_canh" if lam == "phong_vao" else None            # vật không dò thấy trên ảnh: không chỉ sai chỗ
        if lam == "mui_ten" and not (n.get("vung") in vung and n.get("den") in vung):
            lam = None
        if lam in ("chu", "so_dem") and not n.get("chu") and not n.get("so"):
            lam = None
        if not lam:
            continue
        g = _gio_cum(c, n.get("cum") or "")
        t = round(max(0.0, (g - x["t0"]) if g is not None else (nhip[-1]["t"] + 1.2 if nhip else 0.3)), 2)
        if lam in ("chu", "so_dem") and t > x["giay"] - 1.6:             # chữ ở cuối câu: kéo clip cho đọc kịp
            x["giay"] = round(min(t + 1.6, x["giay"] + 1.2), 2)
        t = min(t, x["giay"] - (1.4 if lam in ("chu", "so_dem") else 0.8))
        if nhip and t < nhip[-1]["t"] + 0.5:                             # nhịp sát nhau quá: lùi nhịp sau
            t = round(nhip[-1]["t"] + 0.5, 2)
        so = re.sub(r"[^\d.,]", "", str(n.get("so") or "")).replace(".", "").replace(",", ".")
        nhip.append({"t": t, "lam": lam, "vung": str(n["tach"]) if j in xep_cua else n.get("vung"), "den": n.get("den"),
                     "chu": n.get("chu"), "so": float(so) if so and lam == "so_dem" else None})
        am = n.get("sfx") if n.get("sfx") in loai_sfx else None
        if j in xep_cua:                                                 # vật rơi: tiếng chạm ở vài lần chạm + cú chốt
            xe = xep_cua[j] | {"t": t}
            # rơi phải XONG trong clip (nhịp rơi hay ở cuối câu): kéo clip dài thêm tới 1,5 s, không đủ thì rơi dồn nhanh
            can = t + xe["trong"] + ROI_GIAY + 0.7
            x["giay"] = round(max(x["giay"], min(can, x["giay"] + 1.5)), 2)
            if can > x["giay"]:
                k_ = max(0.25, (x["giay"] - t - ROI_GIAY - 0.7) / xe["trong"])
                xe["o"] = [i | {"d": round(i["d"] * k_, 3)} for i in xe["o"]]
            xep.append(xe)
            # 03/11 user ("hiệu ứng âm thanh nghe chán quá nhức tai"): không gõ tiếng ở từng lần chạm — một tiếng lướt
            # lúc bắt đầu rơi + MỘT cú chốt khi bản cuối chạm đất
            cham = [t + i["d"] + (ROI_GIAY if i["roi"] else 0.12) for i in xe["o"]]
            sk.append((t, "luot-qua", False))
            sk.append((cham[-1], am or ("va-cham-lon" if lam == "roi_xep" else "pop"), True))
        elif lam in SFX_NHIP and lam not in ("phong_vao", "toan_canh"):    # camera di chuyển thì im
            sk.append((t, am or SFX_NHIP[lam], False))
    if not nhip:
        nhip = [{"t": 0.3, "lam": "toan_canh"}]
    vao = x.get("vao") if x.get("vao") in VAO else "mo"
    if vao == "xuyen":                                                   # chỉ cú xuyên mới có tiếng vào cảnh
        sk.insert(0, (0.0, SFX_NHIP[vao], False))
    giu = sorted([z for z in sk if z[2]], key=lambda z: z[0])            # cú chốt trước, rồi các tiếng khác không sát nó
    for z in sorted([z for z in sk if not z[2]], key=lambda z: z[0]):
        if len(giu) < SFX_MOI_CLIP and all(abs(z[0] - g[0]) >= 0.8 for g in giu):
            giu.append(z)
    sk = sorted(giu, key=lambda z: z[0])
    return {"giay": x["giay"], "anh": anh, "nen": f"{THU_PUB}/{k}_nen.jpg" if nen else "", "vao": vao,
            "vung": vung, "nhip": nhip, "xep": xep, "roi": ROI_GIAY}, sk


def _chuan_pr(pr):
    """Dạng so sánh được của props (8 và 8.0 như nhau, bỏ khoá nội bộ)."""
    def c(v):
        if isinstance(v, float):
            return int(v) if v.is_integer() else round(v, 5)
        if isinstance(v, list):
            return [c(i) for i in v]
        if isinstance(v, dict):
            return {k: c(i) for k, i in sorted(v.items()) if not k.startswith("_")}
        return v
    return c(pr)


def _dong_bo_sua(du_an, out, viec):
    """Chỗ 3D: ghi vào ChoSua.jsx cho Studio; chỗ user đã sửa tay trong Studio thì lấy thông số của user (sửa viec)."""
    if not any(pr.get("_id") for _, pr in viec):
        return
    p_tt = os.path.join(out, "nhan_y_sua.json")
    tt = doc_json(p_tt, {}) or {}
    co = _cho_sua_doc()
    muc = {k: v for k, v in co.items() if not k.startswith(du_an.replace("_", "-") + "-cau")}   # dự án khác: giữ
    for j, (i, pr) in enumerate(viec):
        ma = pr.get("_id")
        if not ma:
            continue
        may = _chuan_pr(pr)
        if ma in co and tt.get(ma) and _md5(json.dumps(_chuan_pr(co[ma][1]), sort_keys=True)) != tt[ma]:
            dung = _chuan_pr(co[ma][1])                                   # user đã sửa trong Studio: giữ bản của user
            log(f"    câu {i}: giữ thông số đã chỉnh tay trong Studio ({ma})")
            viec[j] = (i, dung | {"_comp": pr["_comp"], "_id": ma})
        else:
            dung = may
            tt[ma] = _md5(json.dumps(may, sort_keys=True))
        muc[ma] = (pr["_comp"], dung)
    _cho_sua_ghi(muc)
    ghi_json(p_tt, tt)


def _render(viec):
    """[(khoá, props)] -> {khoá: mp4}; cache theo props ở cache/nhan_y/."""
    import nen_ban_do
    thu = os.path.join(CACHE_CHUNG, "nhan_y")
    os.makedirs(thu, exist_ok=True)
    ra, jobs = {}, []
    for k, pr in viec:
        out = os.path.join(thu, _md5(json.dumps(pr, sort_keys=True), "v16") + ".mp4")
        ra[k] = out
        if not (os.path.isfile(out) and os.path.getsize(out) > 5000):
            jobs.append({"comp": pr.get("_comp", "NhanY"), "giay": pr["giay"], "out": out,
                         "props": {a: b for a, b in pr.items() if not a.startswith("_")}})
    nen_ban_do._render(jobs, thu, ten="clip nhấn ý")                    # noqa: SLF001
    return {k: v for k, v in ra.items() if os.path.isfile(v) and os.path.getsize(v) > 5000}


def _ghep(d, clip, sfx):
    """Thêm track 'nhan_y' (trên cùng) + 'nhan_y_sfx' vào nội dung bản nháp d (dict) — vật liệu do pycapcut tạo."""
    import pycapcut as draft
    from pycapcut import trange
    sc = draft.ScriptFile(1920, 1080)
    sc.add_track(draft.TrackType.video, track_name="nhan_y")
    sc.add_track(draft.TrackType.audio, track_name="nhan_y_sfx")
    us = lambda g: f"{g:.3f}s"                                           # noqa: E731
    cuoi = -1.0
    for t0, dai, f in sorted(clip):
        if t0 < cuoi - 0.01:                                             # clip chồng clip trước: bỏ
            continue
        cuoi = t0 + dai
        m = draft.VideoMaterial(f)                                       # clip làm tròn theo khung hình: có thể ngắn hơn 0,01 s
        sc.add_segment(draft.VideoSegment(m, trange(us(t0), us(min(dai, m.duration / 1e6))), volume=0.0), "nhan_y")
    sfx = sorted(sfx)
    gon = []                                                             # cùng một track: bỏ tiếng vào sát tiếng trước
    for z in sfx:
        if not gon or z[0] - gon[-1][0] >= 0.1:
            gon.append(z)
    sfx = gon
    for j, (t0, f, vol) in enumerate(sfx):
        m = draft.AudioMaterial(f)
        a = int(round(t0 * 1e6))                                         # micro-giây nguyên: làm tròn mili-giây từng chồng
        sau = int(round(sfx[j + 1][0] * 1e6)) if j + 1 < len(sfx) else 10 ** 12   # tiếng trước dừng khi tiếng sau vào
        dai = min(int(m.duration), 3_000_000, sau - a)
        if dai < 50_000:
            continue
        sc.add_segment(draft.AudioSegment(m, draft.Timerange(a, dai), volume=vol), "nhan_y_sfx")
    moi = json.loads(sc.dumps())
    for kk, v in moi["materials"].items():
        if isinstance(v, list) and v:
            co = {x.get("id") for x in d["materials"].setdefault(kk, [])}
            d["materials"][kk] += [x for x in v if x.get("id") not in co]
    top = max([s.get("render_index", 0) for t in d["tracks"] for s in t["segments"]] + [0]) + 1
    d["tracks"] = [t for t in d["tracks"] if t.get("name") not in TRACK_RIENG]
    for t in moi["tracks"]:
        if t["segments"]:
            for s in t["segments"]:
                s["render_index"] = top
            d["tracks"].append(copy.deepcopy(t))
    return d


def _thung_rac(p):
    """Chuyển thư mục vào Thùng rác Windows (khôi phục được), không xoá hẳn."""
    lenh = ("Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory("
            f"'{p}', 'OnlyErrorDialogs', 'SendToRecycleBin')")
    subprocess.run(["powershell", "-NoProfile", "-Command", lenh], capture_output=True,
                   creationflags=0x08000000 if os.name == "nt" else 0)
    return not os.path.exists(p)


def lam(du_an, goc, ten=None, so=None, chi=None):
    """Bản nháp `<goc>_nhan_y` = bản nháp `goc` + clip nhấn ý. -> tên bản nháp.
    03/11 user ("sinh 1 bản nháp tôi check thôi"): MỘT bản nháp cố định — chạy lại thì bản cũ cùng tên vào Thùng rác.
    Bản nháp `goc` (có thể đã sửa tay) không bao giờ bị đụng tới. chi: chỉ làm đúng các câu này."""
    import dung_tay
    dd = thu_muc_nhap_capcut()
    p_goc = os.path.join(dd, goc)
    d = _doc(os.path.join(p_goc, "draft_content.json"))
    out = thu_muc_du_an(du_an)[1]
    cau = _cau(du_an)
    if not cau:
        raise SystemExit("dự án chưa có giọng đọc / cảnh")
    ban = _vung_ban(d)
    theo_i = {c["i"]: c for c in cau}
    ds, cuoi = [], -1e9
    for x in sorted(chon(du_an, cau, ban, chi), key=lambda z: z["i"]):
        c = theo_i.get(x["i"])
        if not c or (not chi and (c["t0"] < 5 or c["t0"] - cuoi < CACH_TOI_THIEU)):
            continue
        giay = round(min(DAI_TOI_DA, c["t1"] - c["t0"] + SAU_CAU), 2)
        if giay < DAI_TOI_THIEU or (not chi and any(a < c["t0"] + giay and c["t0"] < b for a, b in ban)):
            continue
        ds.append(x | {"t0": c["t0"], "giay": giay, "text": c["text"]})
        cuoi = c["t0"]
    if so:                                                               # thử ít chỗ: rải đều trong bài
        ds = [ds[round(j * (len(ds) - 1) / max(1, so - 1))] for j in range(min(so, len(ds)))] if ds else []
    log(f"[nhấn ý] {len(ds)} chỗ: " + ", ".join(f"câu {x['i']}" for x in ds))
    viec, sk_cua = [], {}
    for x in ds:
        pr, sk = _chuan_bi(x, theo_i[x["i"]], d, du_an)
        if pr:
            viec.append((x["i"], pr))
            sk_cua[x["i"]] = sk
            x["props"] = pr
    _dong_bo_sua(du_an, out, viec)
    mp4 = _render(viec)
    gd = _ebur(os.path.join(out, "giong_doc.wav"))[0] if os.path.isfile(os.path.join(out, "giong_doc.wav")) else -18.0
    clip, sfx, lan = [], [], {}
    for x in ds:
        f = mp4.get(x["i"])
        if not f:
            continue
        clip.append((x["t0"], x["giay"], f))
        for dt, loai, chinh in sk_cua[x["i"]]:
            for _ in range(3):                                           # âm gần như im (phải nâng quá x4): lấy âm khác
                a = _sfx(loai, lan.get(loai, 0)) if loai else None
                lan[loai] = lan.get(loai, 0) + 1
                vol = _am_luong(a[0], gd, chinh) if a else None
                if a and vol < 4.0:
                    sfx.append((round(max(0.0, x["t0"] + dt - a[1]), 3), a[0], vol))
                    break
        log(f"    {x['t0']:7.1f}s  câu {x['i']:3d}  {len(x['props'].get('nhip', [])) or '3D'} nhịp  {x['text'][:70]}")
    if not clip:
        raise SystemExit("không dựng được clip nhấn ý nào")
    ten = ten or f"{goc}_nhan_y"
    if ten == goc:
        raise SystemExit("tên bản nháp nhấn ý trùng bản nháp gốc")
    p_ra = os.path.join(dd, ten)
    if chi and os.path.isfile(os.path.join(p_ra, "draft_content.json")):
        # 03/11 (thử --cau 42 làm mất 8 chỗ khác): làm lại VÀI câu thì giữ mọi chỗ nhấn ý khác đang có trong bản nháp
        cu = _doc(os.path.join(p_ra, "draft_content.json"))
        mv = {m["id"]: m.get("path") for m in cu["materials"].get("videos", []) + cu["materials"].get("audios", [])}
        moi = [(t0, t0 + dai) for t0, dai, _ in clip]
        trung = lambda a, b: any(a < y and x < b for x, y in moi)       # noqa: E731
        giu_c = giu_s = 0
        for t in cu["tracks"]:
            if t.get("name") not in TRACK_RIENG:
                continue
            for s_ in t["segments"]:
                a = s_["target_timerange"]["start"] / 1e6
                b = a + s_["target_timerange"]["duration"] / 1e6
                f = mv.get(s_["material_id"])
                if not f or not os.path.isfile(f) or trung(a, b if t["name"] == "nhan_y" else a + 0.01):
                    continue
                if t["name"] == "nhan_y":
                    clip.append((a, b - a, f))
                    giu_c += 1
                else:
                    sfx.append((a, f, float(s_.get("volume", 1.0))))
                    giu_s += 1
        log(f"    giữ {giu_c} chỗ nhấn ý khác ({giu_s} tiếng) đang có trong '{ten}'")
    d = _ghep(d, clip, sfx)                                              # dựng xong rồi mới thay bản cũ (lỗi thì bản cũ còn)
    if os.path.exists(p_ra) and not _thung_rac(p_ra):
        ten = dung_tay.ten_nhap_moi(dd, ten)                             # bản cũ đang mở trong CapCut: không thay được
        p_ra = os.path.join(dd, ten)
    shutil.copytree(p_goc, p_ra)
    for f in [os.path.join(p_ra, "draft_content.json")] + glob.glob(os.path.join(p_ra, "Timelines", "*", "draft_content.json")):
        _ghi(f, d)
        if os.path.isfile(f + ".bak"):
            os.remove(f + ".bak")
    pm = os.path.join(p_ra, "draft_meta_info.json")
    m = _doc(pm)
    m.update(draft_name=ten, draft_id=str(uuid.uuid4()).upper(), draft_fold_path=p_ra.replace("\\", "/"))
    _ghi(pm, m)
    dung_tay._sua_nhap(p_ra, [f for _, _, f in clip])                     # noqa: SLF001
    ghi_json(os.path.join(out, "nhan_y.json"), ds)
    log(f"[nhấn ý] xong: bản nháp '{ten}' ({len(clip)} clip trên track 'nhan_y', {len(sfx)} SFX trên 'nhan_y_sfx')")
    return ten


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--du-an", required=True)
    ap.add_argument("--goc", required=True, help="bản nháp CapCut làm nền (thường là bản hoàn chỉnh đã sửa tay)")
    ap.add_argument("--ten", default=None)
    ap.add_argument("--so", type=int, default=None, help="chỉ làm bấy nhiêu chỗ (thử), rải đều trong bài")
    ap.add_argument("--cau", default=None, help="chỉ làm đúng các câu này, vd 6,70")
    a = ap.parse_args()
    lam(a.du_an, a.goc, a.ten, a.so, [int(v) for v in a.cau.split(",")] if a.cau else None)
