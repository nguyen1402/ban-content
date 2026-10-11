# -*- coding: utf-8 -*-
"""Cảnh ĐỒ HỌA: bản đồ phóng to + năm chạy, biểu đồ cột — vẽ bằng Remotion (đã bỏ cảnh kêu gọi đăng ký kênh).

Dữ liệu (địa điểm, năm, số liệu) do ChatGPT rút từ CHÍNH lời kể của cảnh, không tự bịa; tọa độ
được đối chiếu lại bằng Nominatim vì mô hình hay lệch vài chục km."""
import json
import math
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

from common import ROOT, chay, doc_json, duong_cache, ghi_json, hoi_llm, log, rut_json

REMOTION = os.path.join(ROOT, "remotion")

_P = """You are preparing DATA for animated infographic scenes in a Vietnamese documentary. Use ONLY facts stated in the narration of each scene (plus your geographic knowledge for coordinates). Never invent numbers or years that the narration does not give.
Story summary: {tom_tat}
Correct names: {ten}

For each scene choose ONE kind:
- "ban_do": the narration locates a place or a place changing over time. Fields: dia_diem (English place name for the title), lat, lon (the focus place, decimal degrees), rong_km (width of the final map view in km: 8-20 for an island/town, 50-200 for a region), nam_tu and nam_den (years ONLY if the narration gives a time span, else null), dau (up to 3 extra labelled places [{{ten, lat, lon}}] mentioned in the narration), chu_thich (up to 3 short VIETNAMESE captions taken from the narration, max 8 words each).
- "bieu_do": the narration gives numbers that change (population counts). Fields: tieu_de (short VIETNAMESE title), don_vi (VIETNAMESE unit), diem (array of {{nam, gia_tri}} from the narration, nam as short text like "2005", gia_tri a number).
- "khac": nothing sensible to draw — the scene will use normal footage instead.

Return ONLY a JSON array: [{{"id": <scene id>, "kieu": "ban_do"|"bieu_do"|"khac", "ban_do": {{...}} or null, "bieu_do": {{...}} or null}}]

SCENES:
{canh}"""


def _khoang_cach_do(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _nominatim(ten):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": ten, "format": "json", "limit": 1})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ban-content/0.2 (illustration tool)"})
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8"))
        time.sleep(1.1)                                  # chính sách Nominatim: tối đa 1 lượt/giây
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    except Exception:                                    # noqa: BLE001
        pass
    return None


def kiem_toa_do(ten, lat, lon):
    """Trả (lat, lon) đáng tin: nếu Nominatim lệch hẳn >0,3° so với mô hình thì tin Nominatim."""
    ng = _nominatim(ten)
    if ng and (lat is None or lon is None or _khoang_cach_do(ng, (lat, lon)) > 0.3):
        return ng
    return (lat, lon) if lat is not None and lon is not None else ng


def chuan_bi(canh, ctx):
    """Gán c['do_hoa'] cho cảnh đồ họa. Cảnh 'khac' trở về video/ảnh thường."""
    cache = duong_cache("do_hoa.json")
    da = doc_json(cache, {})
    cho_hoi = []
    for c in canh:
        if c.get("loai") != "do_hoa":
            continue
        if str(c["id"]) in da:
            c["do_hoa"] = da[str(c["id"])]
            if c["do_hoa"].get("kieu") == "ban_do":
                c["do_hoa"]["ban_do"]["chu_thich"] = []
        else:
            cho_hoi.append(c)
    for i in range(0, len(cho_hoi), 6):
        lot = cho_hoi[i:i + 6]
        txt = "\n".join(f"{c['id']}. {c['text']}" for c in lot)
        kq = rut_json(hoi_llm(_P.format(tom_tat=ctx["tom_tat"], ten=ctx["ten"], canh=txt),
                              timeout=200)) or []
        mp = {int(x.get("id", -1)): x for x in kq if isinstance(x, dict)}
        for c in lot:
            x = mp.get(c["id"]) or {"kieu": "khac"}
            if x.get("kieu") == "ban_do" and isinstance(x.get("ban_do"), dict):
                b = x["ban_do"]
                b["chu_thich"] = []                          # người dùng không muốn dòng chú thích trên bản đồ
                toa = kiem_toa_do(b.get("dia_diem", ""), b.get("lat"), b.get("lon"))
                if toa:
                    b["lat"], b["lon"] = toa
                    for m in b.get("dau") or []:
                        t2 = kiem_toa_do(m.get("ten", ""), m.get("lat"), m.get("lon"))
                        if t2:
                            m["lat"], m["lon"] = t2
                    b["rong_km"] = max(5, min(800, float(b.get("rong_km") or 20)))
                    da[str(c["id"])] = {"kieu": "ban_do", "ban_do": b}
                    c["do_hoa"] = da[str(c["id"])]
                    continue
            if x.get("kieu") == "bieu_do" and isinstance(x.get("bieu_do"), dict) \
                    and len(x["bieu_do"].get("diem") or []) >= 2:
                da[str(c["id"])] = {"kieu": "bieu_do", "bieu_do": x["bieu_do"]}
                c["do_hoa"] = da[str(c["id"])]
                continue
            da[str(c["id"])] = {"kieu": "khac"}
            c["do_hoa"] = da[str(c["id"])]
        ghi_json(cache, da)
    for c in canh:
        if c.get("do_hoa", {}).get("kieu") == "khac":
            c["loai"] = "video"
            c.pop("do_hoa")
    n = sum(1 for c in canh if c.get("do_hoa"))
    log(f"[2b] cảnh đồ họa Remotion: {n} "
        f"(bản đồ {sum(1 for c in canh if c.get('do_hoa', {}).get('kieu') == 'ban_do')}, "
        f"biểu đồ {sum(1 for c in canh if c.get('do_hoa', {}).get('kieu') == 'bieu_do')})")
    return canh


def _chrome():
    p = os.environ.get("BROWSER_EXE")
    if p and os.path.isfile(p):
        return p
    goc = r"D:\CapCutTTS\hoat_hinh_remotion\node_modules\.remotion"      # dùng lại Chrome đã tải sẵn
    for r, _, fs in os.walk(goc):
        if "chrome-headless-shell.exe" in fs:
            return os.path.join(r, "chrome-headless-shell.exe")
    return None


def dung_het(canh):
    """Render mọi cảnh đồ họa -> cache/clip/<id>_0.mp4 và đặt c['o'] sẵn (chon_doan sẽ bỏ qua)."""
    viec = []
    for c in canh:
        h = c.get("do_hoa")
        if not h:
            continue
        out = duong_cache("clip", f"{c['id']:04d}_0.mp4")
        c["o"] = [{"do_hoa": h["kieu"], "dai": c["dai"], "diem": 1.0, "nguon": "remotion",
                   "tieu_de": h["kieu"], "clip": out}]
        if os.path.isfile(out) and os.path.getsize(out) > 5000:
            continue
        if h["kieu"] == "ban_do":
            import nen_ban_do
            try:
                p = nen_ban_do.chuan_bi(h["ban_do"])         # nền OSM thật + đường viền + camera phóng dần
            except Exception as e:                           # noqa: BLE001
                log(f"    ! nền bản đồ lỗi ({str(e)[:80]}) — dùng bản đồ vector")
                p = h["ban_do"]
            if p.get("lop"):
                viec.append({"comp": "BanDoNen", "giay": c["dai"], "out": out, "props": p})
            else:
                viec.append({"comp": "BanDo", "giay": c["dai"], "out": out, "props": h["ban_do"]})
        elif h["kieu"] == "bieu_do":
            viec.append({"comp": "BieuDo", "giay": c["dai"], "out": out, "props": h["bieu_do"]})
    if not viec:
        return canh
    log(f"[3c] Remotion dựng {len(viec)} cảnh đồ họa…")
    jobs = duong_cache("do_hoa_jobs", "jobs.json")
    ghi_json(jobs, viec)
    env = dict(os.environ)
    ch = _chrome()
    if ch:
        env["BROWSER_EXE"] = ch
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    p = subprocess.run(["node", "render.mjs", jobs], cwd=REMOTION, env=env, capture_output=True,
                       timeout=3600, **kw)
    out = p.stdout.decode("utf-8", "ignore")
    log("    " + "\n    ".join(out.strip().splitlines()[-3:]))
    for c in canh:
        for o in c.get("o") or []:
            if o.get("do_hoa") and not (os.path.isfile(o["clip"]) and os.path.getsize(o["clip"]) > 5000):
                o.pop("do_hoa"), o.pop("clip")
                o["thieu"] = True                        # hỏng -> để dựng thẻ THIẾU, không đổ cả pipeline
    return canh
