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
import time
import urllib.parse
import urllib.request

from PIL import Image

from common import duong_cache, log

UA = {"User-Agent": "ban-content/0.3 (documentary illustration tool; cached tiles)"}
R0 = 156543.03392
BUOC_ZOOM = 2                  # mỗi lớp chênh 2 mức zoom (4 lần) -> 3 lớp, mờ tạm thời tối đa ~4x khi chuyển lớp
SO_O = (6, 6, 8)               # số ô mỗi cạnh của lớp rộng, giữa, gần


def _world(lon, lat, z):
    s = math.sin(math.radians(lat))
    x = (lon + 180) / 360 * 256 * 2 ** z
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 256 * 2 ** z
    return x, y


def _tai_o(z, x, y):
    p = duong_cache("tiles", f"{z}_{x}_{y}.png")
    if os.path.isfile(p) and os.path.getsize(p) > 100:
        return p
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
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


def ghep_lop(lat, lon, z, n):
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
            p = _tai_o(z, x % 2 ** z, y)
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


def chon_zoom_gan(lat, rong_km):
    """Mức zoom gần nhất mà ô OSM còn >= độ nét cần cho bề ngang rong_km trên màn 1920px."""
    mpp = rong_km * 1000 / 1920
    z = math.log2(R0 * math.cos(math.radians(lat)) / mpp)
    return max(8, min(17, int(math.floor(z))))     # floor: lớp gần 8x8 ô vẫn phủ kín khung ở cuối


def lop_nen(lat, lon, rong_km):
    khoa = f"{lat:.3f}_{lon:.3f}_{int(rong_km)}"
    cache = duong_cache("nen_lop", khoa + ".json")
    if os.path.isfile(cache):
        try:
            return json.load(open(cache, encoding="utf-8"))
        except ValueError:
            pass
    zg = chon_zoom_gan(lat, rong_km)
    zs = [max(3, zg - 2 * BUOC_ZOOM), max(3, zg - BUOC_ZOOM), zg]
    lop = []
    for z, n in zip(zs, SO_O):
        l = ghep_lop(lat, lon, z, n)
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
    for v in sorted(vong, key=len, reverse=True)[:4]:
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
