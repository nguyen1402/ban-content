# -*- coding: utf-8 -*-
"""Nền bản đồ THẬT cho cảnh bản đồ Remotion: ghép ô OpenStreetMap ở 3 mức zoom (để camera phóng
dần vẫn nét) + lấy đường viền thật của địa điểm từ Nominatim.

Dùng nhẹ nhàng đúng chính sách của OSM: có User-Agent, nghỉ giữa các ô, lưu cache vĩnh viễn
(mỗi địa điểm chỉ tải một lần), và video ghi nguồn "© OpenStreetMap contributors"."""
import base64
import io
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

from common import CACHE_CHUNG, duong_cache, log

UA = {"User-Agent": "ban-content/0.3 (documentary illustration tool; cached tiles)"}
R0 = 156543.03392
BUOC_ZOOM = 2                  # mỗi lớp chênh 2 mức zoom (4 lần) -> 3 lớp, mờ tạm thời tối đa ~4x khi chuyển lớp
SO_O = (6, 6, 8)               # số ô mỗi cạnh của lớp rộng, giữa, gần


def _world(lon, lat, z):
    s = math.sin(math.radians(lat))
    x = (lon + 180) / 360 * 256 * 2 ** z
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 256 * 2 ** z
    return x, y


#: nền VỆ TINH: Sentinel-2 cloudless 2016 của EOX — giấy phép CC BY 4.0 (dùng thương mại được, phải ghi nguồn);
#: các năm 2017+ là CC BY-NC-SA nên KHÔNG dùng. Ảnh thật ~10 m/điểm -> nét tới mức zoom ~13-14.
NGUON = {"osm": ("tiles", "https://tile.openstreetmap.org/{z}/{x}/{y}.png", ".png", 17),
         "vetinh": ("tiles_vt", "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg", ".jpg", 13)}
GHI_NGUON = {"osm": "© OpenStreetMap contributors",
             "vetinh": "Sentinel-2 cloudless 2016 by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016)"}


def _tai_o(z, x, y, nguon="osm"):
    thu, mau, duoi, _zmax = NGUON[nguon]
    p = os.path.join(CACHE_CHUNG, thu, f"{z}_{x}_{y}{duoi}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.isfile(p) and os.path.getsize(p) > 100:
        return p
    url = mau.format(z=z, x=x, y=y)
    for lan in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r, \
                    open(p, "wb") as f:
                f.write(r.read())
            time.sleep(0.3)                              # lịch sự với máy chủ OSM
            return p
        except Exception:                                # noqa: BLE001
            time.sleep(1.5 * (lan + 1))
    return None


def ghep_lop(lat, lon, z, n, nguon="osm"):
    """Lớp ảnh n×n ô quanh (lat,lon) ở mức zoom z. Trả dict {src(data-URI), z, ox, oy, w, h} hoặc None."""
    wx, wy = _world(lon, lat, z)
    tx0, ty0 = int(wx // 256) - n // 2, int(wy // 256) - n // 2
    anh = Image.new("RGB", (n * 256, n * 256), (230, 230, 230))
    thieu = 0
    for i in range(n):
        for j in range(n):
            x, y = tx0 + i, ty0 + j
            if not (0 <= y < 2 ** z):
                continue
            p = _tai_o(z, x % 2 ** z, y, nguon)
            if not p:
                thieu += 1
                continue
            anh.paste(Image.open(p).convert("RGB"), (i * 256, j * 256))
    if thieu > n * n // 4:
        return None
    buf = io.BytesIO()
    anh.save(buf, "JPEG", quality=88)
    return {"src": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
            "z": z, "ox": tx0 * 256, "oy": ty0 * 256, "w": n * 256, "h": n * 256}


def chon_zoom_gan(lat, rong_km, nguon="osm"):
    """Mức zoom gần nhất mà ô còn >= độ nét cần cho bề ngang rong_km trên màn 1920px."""
    mpp = rong_km * 1000 / 1920
    z = math.log2(R0 * math.cos(math.radians(lat)) / mpp)
    return max(5, min(NGUON[nguon][3], int(math.floor(z))))     # floor: lớp gần 8x8 ô vẫn phủ kín khung ở cuối


def lop_nen(lat, lon, rong_km, nguon="osm"):
    khoa = f"{lat:.3f}_{lon:.3f}_{int(rong_km)}" + ("" if nguon == "osm" else "_" + nguon)
    cache = duong_cache("nen_lop", khoa + ".json")
    if os.path.isfile(cache):
        try:
            return json.load(open(cache, encoding="utf-8"))
        except ValueError:
            pass
    zg = chon_zoom_gan(lat, rong_km, nguon)
    zs = [max(3, zg - 2 * BUOC_ZOOM), max(3, zg - BUOC_ZOOM), zg]
    lop = []
    for z, n in zip(zs, SO_O):
        l = ghep_lop(lat, lon, z, n, nguon)
        if not l:
            return None
        lop.append(l)
    json.dump(lop, open(cache, "w", encoding="utf-8"))
    return lop


def _nominatim(q, polygon=True):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "polygon_geojson": 1 if polygon else 0,
         "polygon_threshold": 0.0004})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        time.sleep(1.1)
        return d[0] if d else None
    except Exception:                                    # noqa: BLE001
        return None


def _vong_tu_geojson(g):
    if g.get("type") == "Polygon":
        vong = [g["coordinates"][0]]
    elif g.get("type") == "MultiPolygon":
        vong = [p[0] for p in g["coordinates"]]
    else:
        return []
    ra = []
    for v in sorted(vong, key=len, reverse=True)[:12]:   # vùng có đảo/bán đảo: giữ nhiều mảnh
        b = max(1, len(v) // 220)                        # thưa bớt điểm cho nhẹ
        ra.append([[round(p[0], 6), round(p[1], 6)] for p in v[::b]])
    return ra


def duong_vien(ten, lat=None, lon=None):
    """Vòng [[lon,lat],…] của địa điểm. Thử tên đầy đủ rồi các dạng ngắn hơn (tên đầy đủ hay bị Nominatim
    hiểu thành một cửa hàng); chỉ nhận đa giác nằm trong ~0,4° quanh (lat,lon) để khỏi vẽ nhầm nơi khác."""
    phan = [p.strip() for p in ten.split(",") if p.strip()]
    dang = [ten]
    if len(phan) >= 3:
        dang += [phan[0] + " " + " ".join(phan[-2:]), phan[0] + " " + phan[-1]]
    if len(phan) >= 2:
        dang.append(phan[0] + " " + phan[1])
    for q in dict.fromkeys(dang):
        d = _nominatim(q)
        g = (d or {}).get("geojson") or {}
        vong = _vong_tu_geojson(g)
        if not vong:
            continue
        if lat is not None and lon is not None:
            la, lo = float(d["lat"]), float(d["lon"])
            if abs(la - lat) > 0.4 or abs(lo - lon) > 0.4:
                continue
        return vong
    return []


def _tam_va_co(vong):
    """Tâm và cạnh lớn nhất (km) của vòng lớn nhất."""
    v = max(vong, key=len)
    lons, lats = [p[0] for p in v], [p[1] for p in v]
    la = sum(lats) / len(lats)
    lo = sum(lons) / len(lons)
    dx = (max(lons) - min(lons)) * 111.32 * math.cos(math.radians(la))
    dy = (max(lats) - min(lats)) * 110.57
    return la, lo, max(dx, dy)


def chuan_bi(b):
    """Bổ sung vào props bản đồ: lop (ảnh nền 3 mức), vien (đường viền địa điểm chính).

    Tọa độ do mô hình đưa hay lệch vài km, còn đa giác OSM thì chính xác: có đa giác thì lấy TÂM của nó
    làm tâm camera, và đặt độ rộng khung cuối theo kích thước thật của địa điểm (đảo nhỏ -> zoom sát)."""
    b = dict(b)
    vien = duong_vien(b.get("dia_diem", ""), b["lat"], b["lon"])
    if vien:
        la, lo, co = _tam_va_co(vien)
        if co < 40:
            b["lat"], b["lon"] = la, lo
            b["rong_km"] = max(2.5, min(b.get("rong_km", 20), co * 7))
    lop = lop_nen(b["lat"], b["lon"], b.get("rong_km", 20))
    if not lop:
        return b
    ra = dict(b)
    ra["lop"] = lop
    ra["vien"] = vien
    for m in ra.get("dau") or []:
        m["vien"] = duong_vien(m.get("ten", ""), m.get("lat"), m.get("lon"))
    log(f"    nền OSM {b.get('dia_diem', '')[:30]}: z={[l['z'] for l in lop]}, rộng {b.get('rong_km'):.1f}km, "
        f"viền {sum(len(v) for v in vien)} điểm")
    return ra


def chuan_bi_vetinh(ten, ten_hien=None):
    """Props cho cảnh bản đồ VỆ TINH khoanh vùng một địa danh (12/10 user): camera phóng từ rất xa vào trên ảnh vệ
    tinh, đường viền thật của nơi đó chạy nét + tô mờ. Khung cuối vừa ôm trọn địa danh (vùng/nước lớn cũng được)."""
    def hop_le(d):                                          # vùng hành chính / địa danh thật, không phải "bãi cát"
        return bool(d) and d.get("class") in ("boundary", "place") and int(d.get("place_rank") or 99) <= 18             and (d.get("geojson") or {}).get("type") in ("Polygon", "MultiPolygon")
    huong = r"\b(northern|southern|eastern|western|central|north|south|east|west|northwest|northeast|southwest|southeast)\b"
    phan = [x.strip() for x in ten.split(",") if x.strip()]
    thu = [ten, phan[0]] + [re.sub(huong, "", x, flags=re.I).strip() for x in [ten] + phan] + phan[1:]
    d = None
    for q in dict.fromkeys(x for x in thu if x):
        d = _nominatim(q)
        if hop_le(d):
            break
        d = None
    if not d:
        log(f"    ! bản đồ vệ tinh: không tìm thấy vùng '{ten}'")
        return None
    vien = _vong_tu_geojson(d.get("geojson") or {})
    v = max(vien, key=lambda r: (max(p[0] for p in r) - min(p[0] for p in r)) * (max(p[1] for p in r) - min(p[1] for p in r)))
    w_, e_ = min(p[0] for p in v), max(p[0] for p in v)       # khung theo MẢNH LỚN NHẤT (bỏ đảo xa như Canary)
    s_, n_ = min(p[1] for p in v), max(p[1] for p in v)
    lat, lon = (s_ + n_) / 2, (w_ + e_) / 2
    dx = (e_ - w_) * 111.32 * math.cos(math.radians(lat))
    dy = (n_ - s_) * 110.57
    rong_km = max(8.0, max(dx, dy * 16 / 9) * 1.35)       # ôm trọn địa danh, chừa lề
    lop = lop_nen(lat, lon, rong_km, "vetinh")
    if not lop:
        log(f"    ! bản đồ vệ tinh: thiếu ô ảnh cho '{ten}'")
        return None
    log(f"    vệ tinh '{ten}': rộng {rong_km:.0f} km, z={[l['z'] for l in lop]}, viền {sum(len(v) for v in vien)} điểm")
    return {"dia_diem": ten_hien or ten.split(",")[0].strip(), "lat": lat, "lon": lon, "rong_km": rong_km,
            "lop": lop, "vien": vien, "nguon": "vetinh", "ghi_nguon": GHI_NGUON["vetinh"]}


def dung_clip_vetinh(viec):
    """Render clip bản đồ vệ tinh bằng Remotion. viec: [(ten_dia_danh, giay, ten_hien)] -> {(ten, giay): mp4 | None}.
    Cache theo (địa danh, độ dài) ở cache/ban_do_vt/ — chạy lại không render lại."""
    import hashlib
    import subprocess
    import do_hoa
    from common import ghi_json
    thu = os.path.join(CACHE_CHUNG, "ban_do_vt")
    os.makedirs(thu, exist_ok=True)
    ra, jobs = {}, []
    for ten, giay, ten_hien in viec:
        giay = round(float(giay), 2)
        out = os.path.join(thu, hashlib.md5(f"{ten}|{giay}|{ten_hien}|v5".encode()).hexdigest()[:16] + ".mp4")
        ra[(ten, giay)] = out
        if os.path.isfile(out) and os.path.getsize(out) > 5000:
            continue
        pr = chuan_bi_vetinh(ten, ten_hien)
        if not pr:
            ra[(ten, giay)] = None
            continue
        jobs.append({"comp": "BanDoNen", "giay": giay, "out": out, "props": pr})
    if jobs:
        log(f"    Remotion dựng {len(jobs)} clip bản đồ vệ tinh…")
        p = os.path.join(thu, "jobs.json")
        ghi_json(p, jobs)
        env = dict(os.environ)
        ch = do_hoa._chrome()                                       # noqa: SLF001
        if ch:
            env["BROWSER_EXE"] = ch
        r = subprocess.run(["node", "render.mjs", p], cwd=do_hoa.REMOTION, env=env, capture_output=True,
                           timeout=3600, creationflags=0x08000000 if os.name == "nt" else 0)
        log("    " + "\n    ".join(r.stdout.decode("utf-8", "ignore").strip().splitlines()[-3:]))
    return {k: (v if v and os.path.isfile(v) and os.path.getsize(v) > 5000 else None) for k, v in ra.items()}


def _diem(ten):
    """(lat, lon, d) điểm của một địa danh qua Nominatim (ưu tiên vùng hành chính / địa danh thật)."""
    phan = [x.strip() for x in ten.split(",") if x.strip()]
    huong = r"\b(northern|southern|eastern|western|central|north|south|east|west)\b"
    bo_huong = [re.sub(huong, "", x, flags=re.I).strip() for x in [ten] + phan]   # "Northern Spain" -> "Spain"
    for q in dict.fromkeys(x for x in [ten, phan[0] if phan else ten] + bo_huong if x):
        d = _nominatim(q, polygon=False)
        if d and d.get("class") in ("boundary", "place") and int(d.get("place_rank") or 99) <= 16:
            return float(d["lat"]), float(d["lon"]), d
    return None                                             # không phải địa danh thật cấp thành phố trở lên -> bỏ


def chuan_bi_duong(tu, den, ten_tu=None, ten_den=None, phuong_tien=""):
    """Props bản đồ VỆ TINH kiểu ĐƯỜNG ĐI A -> B (12/10 user): camera ôm cả hai điểm, đường vàng cong vẽ dần từ A tới B,
    chấm sáng chạy ở mũi đường; điểm A có nhãn, điểm B có chấm đỏ; tiêu đề 'A → B'."""
    a, b = _diem(tu), _diem(den)
    if a and b and (_luc_dia(a[2]) or _luc_dia(b[2])):
        log(f"    ! bản đồ đường đi: '{tu}' / '{den}' là cả lục địa — bỏ")
        return None
    if not a or not b:
        log(f"    ! bản đồ đường đi: '{tu}' hoặc '{den}' không phải địa danh thật — bỏ")
        return None
    ten_a, ten_b = a[2].get("display_name", ""), b[2].get("display_name", "")
    if ten_b.split(",")[0].strip() in ten_a or ten_a.split(",")[0].strip() in ten_b:
        log(f"    ! bản đồ đường đi: '{tu}' nằm trong '{den}' (hoặc ngược lại) — bỏ")
        return None
    if math.hypot((a[1] - b[1]) * 111.32 * math.cos(math.radians((a[0] + b[0]) / 2)), (a[0] - b[0]) * 110.57) < 50:
        log(f"    ! bản đồ đường đi: '{tu}' và '{den}' gần nhau dưới 50 km — bỏ")
        return None
    la, lo = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx = abs(a[1] - b[1]) * 111.32 * math.cos(math.radians(la))
    dy = abs(a[0] - b[0]) * 110.57
    rong_km = max(60.0, max(dx, dy * 16 / 9) * 1.8)       # chừa lề: hai điểm không dính mép khung
    lop = lop_nen(la, lo, rong_km, "vetinh")
    if not lop:
        return None
    ten_tu = ten_tu or tu.split(",")[0].strip()
    ten_den = ten_den or den.split(",")[0].strip()
    log(f"    đường đi '{ten_tu}' -> '{ten_den}': rộng {rong_km:.0f} km, z={[l['z'] for l in lop]}")
    return {"dia_diem": f"{ten_tu} → {ten_den}", "lat": b[0], "lon": b[1], "cam_lat": la, "cam_lon": lo,
            "rong_km": rong_km, "lop": lop, "vien": [], "noi": True,
            "dau": [{"ten": ten_tu, "lat": a[0], "lon": a[1], "vien": []}], "phuong_tien": phuong_tien or "",
            "nguon": "vetinh", "ghi_nguon": GHI_NGUON["vetinh"]}


def _luc_dia(d):
    """Địa danh là cả LỤC ĐỊA ("Asia", "Europe") -> điểm giữa lục địa vô nghĩa trên bản đồ đường đi -> bỏ."""
    return (d.get("type") == "continent" or d.get("addresstype") == "continent"
            or int(d.get("place_rank") or 99) <= 2)


def _km(a, b):
    return math.hypot((a[1] - b[1]) * 111.32 * math.cos(math.radians((a[0] + b[0]) / 2)), (a[0] - b[0]) * 110.57)


def chuan_bi_lan_rong(goc, noi, goc_vi=None, phuong_tien=""):
    """Props bản đồ vệ tinh LAN RỘNG (13/10 user): một nơi gốc toả nhiều tuyến tới nhiều nơi, vẽ lần lượt.
    noi: [(en, vi)]. Bỏ nơi không phải địa danh thật / nằm trong nơi gốc / gần dưới 50 km. Cần >= 2 tuyến."""
    a = _diem(goc)
    if a and _luc_dia(a[2]):
        a = None
    if not a:
        log(f"    ! lan rộng: gốc '{goc}' không phải địa danh thật — bỏ")
        return None
    ten_a = a[2].get("display_name", "")
    tuyen = []
    for en, vi in noi:
        b = _diem(en)
        if not b or _luc_dia(b[2]):
            continue
        ten_b = b[2].get("display_name", "")
        if ten_b.split(",")[0].strip() in ten_a or ten_a.split(",")[0].strip() in ten_b or _km(a, b) < 50:
            continue
        tuyen.append({"tu": {"lat": a[0], "lon": a[1]}, "den": {"lat": b[0], "lon": b[1], "ten": vi or en.split(",")[0]}})
    if len(tuyen) < 2:
        log(f"    ! lan rộng từ '{goc}': chỉ {len(tuyen)} nơi đến hợp lệ — bỏ")
        return None
    las = [a[0]] + [t["den"]["lat"] for t in tuyen]
    los = [a[1]] + [t["den"]["lon"] for t in tuyen]
    la, lo = (min(las) + max(las)) / 2, (min(los) + max(los)) / 2
    dx = (max(los) - min(los)) * 111.32 * math.cos(math.radians(la))
    dy = (max(las) - min(las)) * 110.57
    rong_km = max(80.0, max(dx, dy * 16 / 9) * 1.5)
    lop = lop_nen(la, lo, rong_km, "vetinh")
    if not lop:
        return None
    ten_goc = goc_vi or goc.split(",")[0].strip()
    log(f"    lan rộng '{ten_goc}' -> {len(tuyen)} nơi: rộng {rong_km:.0f} km")
    return {"dia_diem": ten_goc, "lat": a[0], "lon": a[1], "cam_lat": la, "cam_lon": lo, "rong_km": rong_km,
            "lop": lop, "vien": [], "noi": False, "tuyen": tuyen, "phuong_tien": phuong_tien or "",
            "dau": [{"ten": ten_goc, "lat": a[0], "lon": a[1], "vien": []}],
            "nguon": "vetinh", "ghi_nguon": GHI_NGUON["vetinh"]}


def dung_clip(viec):
    """viec: [(khoa, giay, ham_props, args)] -> {khoa: mp4 | None}. Render chung một lần, cache cache/ban_do_vt/."""
    import hashlib
    import json as _json
    thu = os.path.join(CACHE_CHUNG, "ban_do_vt")
    os.makedirs(thu, exist_ok=True)
    ra, jobs = {}, []
    for khoa, giay, ham, args in viec:
        giay = round(float(giay), 2)
        out = os.path.join(thu, "bd_" + hashlib.md5(f"{ham.__name__}|{_json.dumps(args, ensure_ascii=False)}|{giay}|v7"
                                                   .encode()).hexdigest()[:14] + ".mp4")
        ra[khoa] = out
        if os.path.isfile(out) and os.path.getsize(out) > 5000:
            continue
        pr = ham(*args)
        if not pr:
            ra[khoa] = None
            continue
        jobs.append({"comp": "BanDoNen", "giay": giay, "out": out, "props": pr})
    _render(jobs, thu)
    return {k: (v if v and os.path.isfile(v) and os.path.getsize(v) > 5000 else None) for k, v in ra.items()}


def dung_clip_duong(viec):
    """viec: [(tu, den, giay, ten_tu, ten_den)] -> {(tu, den, giay): mp4 | None}. Cache cache/ban_do_vt/."""
    import hashlib
    thu = os.path.join(CACHE_CHUNG, "ban_do_vt")
    os.makedirs(thu, exist_ok=True)
    ra, jobs = {}, []
    for tu, den, giay, ten_tu, ten_den in viec:
        giay = round(float(giay), 2)
        out = os.path.join(thu, "duong_" + hashlib.md5(f"{tu}|{den}|{giay}|{ten_tu}|{ten_den}|v2".encode()).hexdigest()[:14] + ".mp4")
        ra[(tu, den, giay)] = out
        if os.path.isfile(out) and os.path.getsize(out) > 5000:
            continue
        pr = chuan_bi_duong(tu, den, ten_tu, ten_den)
        if not pr:
            ra[(tu, den, giay)] = None
            continue
        jobs.append({"comp": "BanDoNen", "giay": giay, "out": out, "props": pr})
    _render(jobs, thu)
    return {k: (v if v and os.path.isfile(v) and os.path.getsize(v) > 5000 else None) for k, v in ra.items()}


def _render(jobs, thu, ten="clip bản đồ"):
    if not jobs:
        return
    import subprocess
    import do_hoa
    from common import ghi_json
    log(f"    Remotion render {len(jobs)} {ten}…")          # 19/10: hàm dùng chung (cả sơ đồ minh hoạ) — ghi đúng tên
    p = os.path.join(thu, "jobs.json")
    ghi_json(p, jobs)
    env = dict(os.environ)
    ch = do_hoa._chrome()                                           # noqa: SLF001
    if ch:
        env["BROWSER_EXE"] = ch
    r = subprocess.run(["node", "render.mjs", p], cwd=do_hoa.REMOTION, env=env, capture_output=True,
                       timeout=3600, creationflags=0x08000000 if os.name == "nt" else 0)
    log("    " + "\n    ".join(r.stdout.decode("utf-8", "ignore").strip().splitlines()[-3:]))
