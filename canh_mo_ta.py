# -*- coding: utf-8 -*-
"""CẢNH REMOTION THEO MÔ TẢ (20/10 user): mô tả tiếng Việt -> AI viết KỊCH BẢN CẢNH (JSON, khuôn của
remotion/src/CanhMoTa.jsx: chữ, số đếm chạy, hình khối, mũi tên, ảnh, nền màu / ảnh) -> Remotion dựng MP4 1920x1080.
AI KHÔNG viết code: chỉ điền khuôn -> không lỗi biên dịch, phong cách đồng bộ. Ảnh dùng trong cảnh được chép vào
remotion/public/tu_mo_ta/."""
import hashlib
import json
import os
import shutil

from common import hoi_llm, log, rut_json

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "remotion", "public", "tu_mo_ta")

_P = """You design a short motion-graphics scene (1920x1080, {giay} seconds) for a Vietnamese documentary video, rendered
by a FIXED template. Turn the user's Vietnamese description into the template's JSON — do not write code.

Template:
{{"nen": "#0b0d12" | {{"anh": "<IMAGE>", "phong": [1, 1.1], "toi": 0.35}},
  "lop": [ layers drawn in order, each with "vao" and "ra" (seconds, 0..{giay}) and "hieu_ung":
           "mo" (fade) | "truot_len" | "truot_trai" | "phong" (zoom in) | "nay" (pop) | "go" (typewriter, text only)
    {{"loai": "chu", "text": "...", "x": 0.5, "y": 0.5, "co": 72, "mau": "#ffffff", "dam": true, "nen_chu": "#00000099"(optional box), "rong": 0.85}},
    {{"loai": "so", "tu": 300, "den": 0, "dem": 2.5, "truoc": "", "sau": " con", "x": 0.5, "y": 0.45, "co": 180, "mau": "#ffffff"}},
    {{"loai": "hinh", "dang": "tron"|"chu_nhat"|"vien_tron"|"vien_chu_nhat", "x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "mau": "#e53935", "day": 6}},
    {{"loai": "mui_ten", "tu": [0.3, 0.5], "den": [0.7, 0.5], "mau": "#ffd54f", "day": 10}},
    {{"loai": "anh", "src": "<IMAGE>", "x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5, "phong": [1, 1.08], "bo": 14}}
  ],
  "ban_do": null | SATELLITE MAP background (replaces "nen") — use it whenever the description is about a map, satellite
    view, places, regions, routes or "from place A to place B":
    {{"diem": [ places, in order of appearance:
        {{"tim": "<FULL official English name + region/state + country, e.g. 'Blackwater National Wildlife Refuge, Maryland,
                  USA', or exact coordinates 'lat,lon' if the user gave them>",
          "nhan": "<short Vietnamese label shown on the map, as the user names it>",
          "khoanh": true (outline the real boundary of an area: park, refuge, island, peninsula, country…) | false (just a pin),
          "vao": seconds, "ra": seconds}} ],
      "camera": [ keyframes the camera flies through, in time order:
        {{"luc": seconds, "nhin": "xa" (seen from space, very far) | "tat_ca" (frame all places) | [place indexes to frame],
          "zoom_them": 0 (optional, + = closer, - = farther)}} ],
      "duong": [ optional dashed lines drawn between places: {{"tu": index, "den": index, "vao": s, "ra": s}} ]}}
}}
Rules: x, y are the CENTRE (0..1 of width / height); w, h are 0..1. Keep text inside the frame (rong <= 0.9, big numbers
co <= 220). Text in Vietnamese exactly as the user wants.
MAP rules: NEVER invent coordinates — give names precise enough to find the right place (official name + state/province
+ country); real positions and boundaries are looked up afterwards. A satellite / map scene usually starts with the
camera "xa" or framing everything, then flies to each place as it is mentioned (show the place's pin/label slightly
before the camera arrives). On a map scene do NOT repeat the place names as "chu" layers — the map labels already show
them; use "chu" only for extra text the user asks for (title, numbers…). "duong" only when the user describes a route /
movement between places, not when one place lies inside the other. Respect the order and timing the user describes; spread
appearances over the {giay} seconds; keep important elements on screen until the end unless told otherwise.
{anh}
Return ONLY the JSON.

DESCRIPTION: {mo_ta}"""


def _so(v, mac, lo, hi):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return mac


def _sach(j, giay, anh_ok):
    """Kẹp số liệu về khoảng hợp lệ; bỏ lớp lạ / ảnh không có."""
    if not isinstance(j, dict):
        raise ValueError("AI không trả kịch bản cảnh")
    nen = j.get("nen")
    if isinstance(nen, dict) and nen.get("anh") not in anh_ok:
        nen = "#0b0d12"
    lop = []
    for l in j.get("lop") or []:
        if not isinstance(l, dict) or l.get("loai") not in ("chu", "so", "hinh", "mui_ten", "anh"):
            continue
        if l["loai"] == "anh" and l.get("src") not in anh_ok:
            continue
        l = dict(l)
        l["vao"] = _so(l.get("vao"), 0.0, 0.0, giay)
        l["ra"] = _so(l.get("ra"), giay, l["vao"] + 0.3, giay)
        for k in ("x", "y", "w", "h"):
            if k in l:
                l[k] = _so(l[k], 0.5, 0.0, 1.0)
        if "co" in l:
            l["co"] = _so(l["co"], 72, 16, 240)
        lop.append(l)
    bd = j.get("ban_do")
    if isinstance(bd, dict) and isinstance(bd.get("diem"), list) and bd["diem"]:
        diem = []
        for d in bd["diem"][:8]:
            if isinstance(d, dict) and str(d.get("tim") or "").strip():
                d = dict(d)
                d["vao"] = _so(d.get("vao"), 0.0, 0.0, giay)
                d["ra"] = _so(d.get("ra"), giay, d["vao"] + 0.3, giay)
                diem.append(d)
        bd = {"diem": diem, "camera": [c for c in bd.get("camera") or [] if isinstance(c, dict)],
              "duong": [{**x, "vao": _so(x.get("vao"), 0.0, 0.0, giay), "ra": _so(x.get("ra"), giay, 0.3, giay)}
                        for x in bd.get("duong") or [] if isinstance(x, dict)
                        and isinstance(x.get("tu"), int) and isinstance(x.get("den"), int)]} if diem else None
    else:
        bd = None
    if not lop and not (isinstance(nen, dict)) and not bd:
        raise ValueError("kịch bản cảnh rỗng")
    return {"nen": nen or "#0b0d12", "lop": lop, "ban_do": bd}


def lap(mo_ta, giay, anh=None):
    """Mô tả -> kịch bản cảnh (dict). anh: đường dẫn ảnh người dùng đưa (dùng làm nền / lớp ảnh)."""
    anh_ok, ghi_anh = set(), ""
    if anh and os.path.isfile(anh):
        os.makedirs(PUB, exist_ok=True)
        ten = hashlib.md5(open(anh, "rb").read()).hexdigest()[:12] + os.path.splitext(anh)[1].lower()
        dich = os.path.join(PUB, ten)
        if not os.path.isfile(dich):
            shutil.copyfile(anh, dich)
        anh_ok.add(f"tu_mo_ta/{ten}")
        ghi_anh = (f'An image is available as "tu_mo_ta/{ten}" — use it (as the background "nen.anh" or an "anh" layer) '
                   f"when the description mentions an image / photo / background picture.")
    else:
        ghi_anh = "No image is available: do not use \"anh\" layers or an image background."
    p = _P.format(giay=round(giay, 1), mo_ta=mo_ta.strip(), anh=ghi_anh).replace("<IMAGE>", "tu_mo_ta/<file>")
    j = None
    for _ in range(2):
        j = rut_json(hoi_llm(p, timeout=180) or "")
        if isinstance(j, dict):
            break
    kb = _sach(j, giay, anh_ok)
    if kb["ban_do"]:                                         # toạ độ + viền THẬT (OpenStreetMap), không lấy của AI
        import ban_do
        for d in kb["ban_do"]["diem"]:
            r = ban_do.tra(d["tim"])
            d.update(lat=r["lat"], lon=r["lon"], vien=r["vien"], ten_day_du=r["ten_day_du"])
            log(f"    Địa danh «{d['tim']}» -> {r['ten_day_du']} ({r['lat']:.4f}, {r['lon']:.4f})")
    return kb


def dung(kb, giay, out, bao=None):
    """Kịch bản cảnh -> MP4 (remotion/render.mjs, composition CanhMoTa). Trả out hoặc ném lỗi."""
    import subprocess
    import do_hoa
    thu = os.path.dirname(out)
    os.makedirs(thu, exist_ok=True)
    props = dict(kb)
    if kb.get("ban_do"):
        import ban_do
        props["ban_do"] = ban_do.chuan_bi(kb["ban_do"], giay, bao)
        if bao:
            bao("Remotion dựng cảnh bản đồ…")
    p = os.path.join(thu, "_jobs_canh.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump([{"comp": "CanhMoTa", "props": props, "giay": round(giay, 2), "out": out}], f, ensure_ascii=False)
    env = dict(os.environ, RENDER_SONG_SONG="1")
    ch = do_hoa._chrome()                                    # noqa: SLF001
    if ch:
        env["BROWSER_EXE"] = ch
    log(f"    Remotion dựng cảnh theo mô tả ({giay:.1f}s)…")
    r = subprocess.run(["node", "render.mjs", p], cwd=do_hoa.REMOTION, env=env, capture_output=True, timeout=900,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    if not os.path.isfile(out):
        raise ValueError("Remotion không dựng được: " + r.stdout.decode("utf-8", "ignore")[-300:])
    return out
