# -*- coding: utf-8 -*-
"""CHỖ ĐÃ PHỦ BẰNG HÌNH AI (27/10 user: "chỗ nào tôi đã chấm điểm rồi thì chỗ đấy không cần băm video đặt vào nữa").

Hai nguồn:
  - đoạn HOOK: mỗi câu lệnh video hook (hook_video.json) phủ khúc 10 s của nó;
  - danh sách 📝 Chỗ ảnh AI & Veo (anh_ai_ke_hoach.json): mỗi chỗ không bị bỏ phủ từ câu đầu tới câu cuối của nó
    (Veo tối đa VEO_GIAY, chuỗi ảnh tối đa ANH_TOI_DA giây — đúng như lúc ✨ đặt hình).
Cảnh (tu_khoa.json) bị phủ >= TI_LE_PHU thời lượng thì bước 🤖 không tìm, không băm, không đặt footage.
27/10 user: chỉ tính chỗ ĐÃ CÓ hình AI thật (bước 🎨 Tạo hình AI chạy trước) — chỗ Veo / ảnh không ra hình thì 🤖 băm
footage lấp vào, ✨ chỉ ghép."""
import os
import re

from common import doc_json, ghi_json, thu_muc_du_an

HINH_AI = "hinh_ai.json"     # 27/10: kết quả bước 🎨 Tạo hình AI (ảnh đã vẽ theo từng chỗ 📝)
VEO_GIAY = 8.0               # 28/10 user: clip Veo mặc định 8 s (khúc hook có clip ghi độ dài thật ở "giay")
ANH_TOI_DA = 13.5            # = dieu_phoi.AI_CHUOI_TOI_DA + 1.5 (minh_hoa.lap)
TI_LE_PHU = 0.8


def doc_cau(out):
    """[{i, t0, t1, text}] từ kich_ban_cau.srt (câu dùng cho danh sách 📝)."""
    try:
        s = open(os.path.join(out, "kich_ban_cau.srt"), encoding="utf-8").read()
    except OSError:
        return []

    def giay(h, m, s_, ms):
        return int(h) * 3600 + int(m) * 60 + int(s_) + int(ms) / 1000
    ra = []
    for k in re.finditer(r"(\d+)\s*\n(\d+):(\d+):(\d+)[,.](\d+) --> (\d+):(\d+):(\d+)[,.](\d+)\s*\n(.*?)(?=\n\s*\n|\Z)", s, re.S):
        g = k.groups()
        txt = g[9].replace("\n", " ").strip()
        if txt:
            ra.append({"i": len(ra) + 1, "t0": round(giay(*g[1:5]), 3), "t1": round(giay(*g[5:9]), 3), "text": txt})
    return ra


def dong_bo_cau(out, cau, luu=True):
    """27/10 user ("vừa hoàn thiện bản nháp sao nó lủng nhiều chỗ vậy"): 📝 / 🎨 đánh số theo câu của giọng đọc (164 câu =
    kich_ban.srt) còn ✨ chia lại theo bản thô (186 câu) -> clip Veo đặt theo SỐ câu bị lệch. Mỗi chỗ 📝 NEO THEO GIÂY
    (t0 = đầu câu đầu, t1 = cuối câu cuối, lấy lúc đánh dấu); danh sách câu đổi thì tính lại cau / den_cau theo giây.
    cau: [{i, t0, t1, text}] của danh sách câu đang dùng. -> dict danh sách (đã lưu nếu có đổi và luu)."""
    p = os.path.join(out, "anh_ai_ke_hoach.json")
    da = doc_json(p, {}) or {}
    ds = da.get("ds")
    if not isinstance(ds, list) or not cau:
        return da
    theo = {c["i"]: c for c in cau}
    doi = False
    for y in ds:
        if not isinstance(y, dict):
            continue
        try:
            i = int(y.get("cau"))
            den = max(i, int(y.get("den_cau") or i))
        except (TypeError, ValueError):
            continue
        if y.get("t0") is None or y.get("t1") is None:      # chưa neo: neo theo danh sách câu đang hiện
            if i in theo:
                y["t0"], y["t1"] = float(theo[i]["t0"]), float((theo.get(den) or theo[i])["t1"])
                doi = True
            continue
        t0, t1 = float(y["t0"]), float(y["t1"])
        i2 = min(cau, key=lambda c: abs(float(c["t0"]) - t0))["i"]
        den2 = max([c["i"] for c in cau if i2 <= c["i"] <= i2 + 2 and float(c["t0"]) < t1 - 0.3] or [i2])
        if (i2, den2) != (i, int(y.get("den_cau") or i)):
            y["cau"], y["den_cau"] = i2, den2
            doi = True
    if doi and luu:
        ghi_json(p, da)
    return da


def khoang_hook(out):
    """[(t0, t1)] các khúc hook đã có câu lệnh."""
    hk = doc_json(os.path.join(out, "hook_video.json"), {}) or {}
    het = float(hk.get("het_hook") or hk.get("giay_hook") or 0)
    ds = sorted([y for y in hk.get("ds") or [] if str(y.get("prompt_en") or "").strip()], key=lambda y: float(y.get("t0") or 0))
    ra = []
    for k, y in enumerate(ds):
        a = float(y.get("t0") or 0)
        g_ = float(y.get("giay") or VEO_GIAY)              # 28/10: độ dài clip thật của khúc (clip cũ 10 s, mới 8 s)
        b = min(a + g_, het or a + g_)
        sau = next((float(z.get("t0") or 0) for z in ds[k + 1:] if float(z.get("t0") or 0) > a), None)
        if sau is not None:
            b = min(b, sau)
        if b > a:
            ra.append((a, b))
    return ra


def het_hook_du_kien(out):
    """27/10 user ("khi tôi tích hook bằng veo3 rồi thì phải trừ đi những câu trong thời gian đọc đó chứ"): CHƯA có câu
    lệnh hook (hook_video.json) -> ước hết đoạn hook đúng như hook_video.lap: các cảnh (tu_khoa.json) bắt đầu trước
    HOOK_GIAY, tới hết cảnh cuối trong số đó. Không có tu_khoa.json -> 0."""
    import hook_video
    da = doc_json(os.path.join(out, "hook_video.json"), {}) or {}
    giay = float(da.get("giay_hook") or hook_video.HOOK_GIAY)
    hook = []
    for c in sorted(doc_json(os.path.join(out, "tu_khoa.json"), []) or [], key=lambda c: c.get("id") or 0):
        if hook and float(c.get("bat_dau") or 0) >= giay:
            break
        hook.append(c)
    return max((float(c.get("bat_dau") or 0) + float(c.get("dai") or 0) for c in hook), default=0.0)


def khoang_ke_hoach(out, cau=None, chi_co_hinh=False):
    """[(t0, t1, loai)] các chỗ trong danh sách 📝 (không bị bỏ). chi_co_hinh: chỉ chỗ đã có hình AI thật (_co_hinh)."""
    da = doc_json(os.path.join(out, "anh_ai_ke_hoach.json"), {}) or {}
    if da.get("duyet") is False:                             # 27/10: danh sách AI tự đề xuất (chưa lưu) không tính
        return []
    cau = cau if cau is not None else doc_cau(out)
    da = dong_bo_cau(out, cau, luu=False) or da              # 27/10: chỗ neo theo giây -> số câu của danh sách này
    theo = {c["i"]: c for c in cau}
    ra = []
    for y in da.get("ds") or []:
        if not isinstance(y, dict) or y.get("bo"):
            continue
        try:
            i = int(y.get("cau"))
            den = max(i, min(int(y.get("den_cau") or i), i + 2))
        except (TypeError, ValueError):
            continue
        if i not in theo or (chi_co_hinh and not _co_hinh(out, y)):
            continue
        a = float(theo[i]["t0"])
        cuoi = theo.get(den) or theo[i]
        b = float(cuoi["t1"])
        ke = theo.get(cuoi["i"] + 1)
        if ke and 0 <= float(ke["t0"]) - b < 1.5:              # như minh_hoa: phủ cả quãng nghỉ tới câu sau
            b = float(ke["t0"])
        loai = "veo" if y.get("loai") == "veo" else "anh"
        b = min(b, a + (VEO_GIAY if loai == "veo" else ANH_TOI_DA))
        ra.append((a, b, loai))
    return ra


def khoang_hook_co_clip(out):
    """[(t0, t1)] các khúc hook ĐÃ CÓ clip Veo (khúc chưa có / tạo hỏng -> băm footage vào)."""
    import hook_video
    hk = doc_json(os.path.join(out, "hook_video.json"), {}) or {}
    co = {round(float(y.get("t0") or 0), 1) for y in hk.get("ds") or []
          if str(y.get("prompt_en") or "").strip() and hook_video.clip_co(y, out)}
    return [(a, b) for a, b in khoang_hook(out) if round(a, 1) in co]


def _co_hinh(out, y):
    """Chỗ y của 📝 đã có hình AI THẬT chưa: 🎬 Veo = có clip theo câu lệnh hiện tại; 🖼 ảnh = bước 🎨 đã vẽ được ảnh
    cho đúng câu mô tả hiện tại (hinh_ai.json)."""
    if y.get("loai") == "veo":
        import veo_canh
        v = str(y.get("veo_en") or "").strip()
        f = os.path.join(out, "veo", veo_canh._ten(v) + ".mp4") if v else ""     # noqa: SLF001
        return bool(f and os.path.isfile(f) and os.path.getsize(f) > 20000)
    da = doc_json(os.path.join(out, HINH_AI), {}) or {}
    return any(int(z.get("cau") or 0) == int(y.get("cau") or 0) and z.get("ve_1") == y.get("ve_1") and z.get("so_anh")
               for z in da.get("anh") or [])


def khoang(out):
    """Mọi khoảng đã phủ (giây tuyệt đối, đã gộp chồng) -> [(t0, t1)].
    27/10 user ("tạo Veo + ảnh trước (bước riêng), chỗ Veo hỏng thì lấp footage, rồi băm footage vào chỗ trống"): chỉ
    tính chỗ ĐÃ CÓ hình AI thật (clip hook / clip Veo / ảnh bước 🎨 đã vẽ) — chỗ đánh dấu mà chưa có hình thì 🤖 băm
    footage vào như chỗ thường."""
    k = sorted([(a, b) for a, b in khoang_hook_co_clip(out)] + [(a, b) for a, b, _ in khoang_ke_hoach(out, chi_co_hinh=True)])
    gop = []
    for a, b in k:
        if gop and a <= gop[-1][1] + 0.05:
            gop[-1] = (gop[-1][0], max(gop[-1][1], b))
        else:
            gop.append((a, b))
    return gop


def canh_phu(du_an):
    """{id cảnh tu_khoa.json} bị hình AI phủ >= TI_LE_PHU thời lượng -> không băm footage."""
    out = thu_muc_du_an(du_an)[1]
    k = khoang(out)
    if not k:
        return set()
    ra = set()
    for c in doc_json(os.path.join(out, "tu_khoa.json"), []) or []:
        a = float(c.get("bat_dau") or 0)
        b = a + float(c.get("dai") or 0)
        if b - a < 0.3:
            continue
        phu = sum(max(0.0, min(b, y) - max(a, x)) for x, y in k)
        if phu >= TI_LE_PHU * (b - a):
            ra.add(c["id"])
    return ra
