# -*- coding: utf-8 -*-
"""CHỖ ĐÃ PHỦ BẰNG HÌNH AI (27/10 user: "chỗ nào tôi đã chấm điểm rồi thì chỗ đấy không cần băm video đặt vào nữa").

Hai nguồn:
  - đoạn HOOK: mỗi câu lệnh video hook (hook_video.json) phủ khúc 10 s của nó;
  - danh sách 📝 Chỗ ảnh AI & Veo (anh_ai_ke_hoach.json): mỗi chỗ không bị bỏ phủ từ câu đầu tới câu cuối của nó
    (Veo tối đa VEO_GIAY, chuỗi ảnh tối đa ANH_TOI_DA giây — đúng như lúc ✨ đặt hình).
Cảnh (tu_khoa.json) bị phủ >= TI_LE_PHU thời lượng thì bước 🤖 không tìm, không băm, không đặt footage. Lúc ✨ chỗ nào
thiếu clip Veo (hết điểm / lỗi) thì vẽ ảnh AI thay (0 điểm) — không để màn đen."""
import os
import re

from common import doc_json, thu_muc_du_an

VEO_GIAY = 10.0
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


def khoang_hook(out):
    """[(t0, t1)] các khúc hook đã có câu lệnh."""
    hk = doc_json(os.path.join(out, "hook_video.json"), {}) or {}
    het = float(hk.get("het_hook") or hk.get("giay_hook") or 0)
    ds = sorted([y for y in hk.get("ds") or [] if str(y.get("prompt_en") or "").strip()], key=lambda y: float(y.get("t0") or 0))
    ra = []
    for k, y in enumerate(ds):
        a = float(y.get("t0") or 0)
        b = min(a + VEO_GIAY, het or a + VEO_GIAY)
        sau = next((float(z.get("t0") or 0) for z in ds[k + 1:] if float(z.get("t0") or 0) > a), None)
        if sau is not None:
            b = min(b, sau)
        if b > a:
            ra.append((a, b))
    return ra


def khoang_ke_hoach(out, cau=None):
    """[(t0, t1, loai)] các chỗ trong danh sách 📝 (không bị bỏ)."""
    da = doc_json(os.path.join(out, "anh_ai_ke_hoach.json"), {}) or {}
    theo = {c["i"]: c for c in (cau if cau is not None else doc_cau(out))}
    ra = []
    for y in da.get("ds") or []:
        if not isinstance(y, dict) or y.get("bo"):
            continue
        try:
            i = int(y.get("cau"))
            den = max(i, min(int(y.get("den_cau") or i), i + 2))
        except (TypeError, ValueError):
            continue
        if i not in theo:
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


def khoang(out):
    """Mọi khoảng đã phủ (giây tuyệt đối, đã gộp chồng) -> [(t0, t1)]."""
    k = sorted([(a, b) for a, b in khoang_hook(out)] + [(a, b) for a, b, _ in khoang_ke_hoach(out)])
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
