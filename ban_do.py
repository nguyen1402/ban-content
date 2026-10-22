# -*- coding: utf-8 -*-
"""BẢN ĐỒ VỆ TINH cho cảnh Remotion theo mô tả (20/10 user: "chủ yếu tôi sẽ làm kiểu vậy nhưng nó phải đúng").

ĐÚNG = toạ độ không do AI đoán: AI chỉ viết TÊN địa danh đầy đủ (tiếng Anh, kèm vùng + nước) hoặc toạ độ "lat,lon";
toạ độ + đường viền lấy từ OpenStreetMap (Nominatim), ảnh nền là ảnh vệ tinh thật — DÙNG LẠI nguồn của nen_ban_do.py
(Sentinel-2 cloudless 2016 của EOX, CC BY 4.0 dùng thương mại được, phải ghi nguồn; nét tới zoom 13).
Khác nen_ban_do (một vùng / một đường A->B): ở đây nhiều điểm + camera bay nhiều chặng kiểu "flyTo" (van Wijk, như
d3.interpolateZoom), nơi này nằm trong nơi kia vẫn được (Blackwater nằm trên bán đảo Delmarva).
Khung hình nào cần ô ảnh nào được tính ở đây, tải bằng nen_ban_do._tai_o rồi chép đúng các ô cần vào
remotion/public/ban_do/ — BanDoVeTinh.jsx tính lại cùng công thức và chỉ vẽ ô có trong danh sách (không gọi mạng lúc dựng)."""
import json
import math
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor

import nen_ban_do
from common import CACHE_CHUNG, log

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DD = os.path.join(CACHE_CHUNG, "dia_danh_canh.json")
PUB = os.path.join(ROOT, "remotion", "public", "ban_do")
W, H, FPS = 1920, 1080, 30
Z_MAX = nen_ban_do.NGUON["vetinh"][3]   # 13: mức ô vệ tinh cao nhất có (Sentinel-2 ~10 m/điểm)
Z_CAM = Z_MAX + 0.3                     # camera được phóng quá mức ô một chút (đo 20/10: +0,8 đã mềm rõ)
Z_DIEM = 12.0                           # zoom khi nhìn MỘT điểm không có viền (thị trấn, ngọn núi…)
Z_XA = 3.0                              # "nhìn từ vũ trụ"
LAP_DAY = 0.62                          # vùng cần nhìn chiếm ~62% khung
O_TOI_DA = 5000


# ---------- Tra địa danh ----------
def _doc_cache():
    try:
        return json.load(open(CACHE_DD, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _vong_lon_nhat(gj):
    """GeoJSON -> vòng ngoài của mảnh LỚN NHẤT [[lat, lon]…] (bỏ mảnh lẻ xa: Blackwater có thửa cách 100 km)."""
    if not gj or gj.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    ps = [gj["coordinates"]] if gj["type"] == "Polygon" else gj["coordinates"]

    def dt(v):
        return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(v, v[1:] + v[:1]))) / 2
    v = max((p[0] for p in ps if p and len(p[0]) >= 4), key=dt, default=None)
    if not v:
        return None
    buoc = max(1, len(v) // 500)
    return [[round(b, 5), round(a, 5)] for a, b in v[::buoc]]


def tra(ten):
    """Tên địa danh (hoặc 'lat,lon') -> {ten_day_du, lat, lon, vien}. Ném lỗi nếu không tìm thấy (không đoán)."""
    ten = str(ten or "").strip()
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)\s*", ten)
    if m:
        return {"ten_day_du": f"toạ độ {ten}", "lat": float(m[1]), "lon": float(m[2]), "vien": None}
    c = _doc_cache()
    k = ten.lower()
    if k in c:
        return c[k]
    r = nen_ban_do._nominatim(ten)                       # noqa: SLF001 — có User-Agent + nghỉ 1,1 s
    if not r:
        raise ValueError(f"Không tìm thấy địa danh «{ten}» trên OpenStreetMap — ghi rõ hơn (tên đầy đủ, tỉnh/bang, "
                         f"nước) hoặc ghi toạ độ")
    kq = {"ten_day_du": r["display_name"], "lat": float(r["lat"]), "lon": float(r["lon"]),
          "vien": _vong_lon_nhat(r.get("geojson"))}
    c[k] = kq
    os.makedirs(os.path.dirname(CACHE_DD), exist_ok=True)
    json.dump(c, open(CACHE_DD, "w", encoding="utf-8"), ensure_ascii=False)
    return kq


# ---------- Phép chiếu Web Mercator (đơn vị: px thế giới ở zoom 0, 0..256) ----------
def chieu(lat, lon):
    lat = max(-85.0, min(85.0, lat))
    s = math.sin(math.radians(lat))
    return (lon + 180) / 360 * 256, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 256


def _khung(diem, ids):
    """Các điểm (theo chỉ số) -> (tâm x, tâm y, zoom) vừa khung."""
    xs, ys, co_vien = [], [], False
    for i in ids:
        d = diem[i]
        pts = d.get("vien")                                  # 22/10: viền luôn dùng để ÔM VỪA vùng; "khoanh" chỉ quyết VẼ viền
        for la, lo in (pts or [[d["lat"], d["lon"]]]):
            x, y = chieu(la, lo)
            xs.append(x)
            ys.append(y)
        co_vien = co_vien or bool(pts)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    dx, dy = max(xs) - min(xs), max(ys) - min(ys)
    if (dx < 1e-9 and dy < 1e-9) or not (co_vien or len(ids) > 1):
        return cx, cy, Z_DIEM
    z = math.log2(min(W * LAP_DAY / max(dx, 1e-9), H * LAP_DAY / max(dy, 1e-9)))
    return cx, cy, max(2.0, min(Z_CAM, z))


def _bay(p0, p1):
    """d3.interpolateZoom (van Wijk & Nuij): p = (x, y, w) với w = bề rộng khung (đơn vị zoom 0)."""
    rho, rho2, rho4 = math.sqrt(2), 2.0, 4.0
    ux0, uy0, w0 = p0
    ux1, uy1, w1 = p1
    dx, dy = ux1 - ux0, uy1 - uy0
    d2 = dx * dx + dy * dy
    if d2 < 1e-12:
        S = math.log(w1 / w0) / rho
        return lambda t: (ux0 + t * dx, uy0 + t * dy, w0 * math.exp(rho * t * S))
    d1 = math.sqrt(d2)
    b0 = (w1 * w1 - w0 * w0 + rho4 * d2) / (2 * w0 * rho2 * d1)
    b1 = (w1 * w1 - w0 * w0 - rho4 * d2) / (2 * w1 * rho2 * d1)
    r0 = math.log(math.sqrt(b0 * b0 + 1) - b0)
    r1 = math.log(math.sqrt(b1 * b1 + 1) - b1)
    S = (r1 - r0) / rho

    def f(t):
        s = t * S
        u = w0 / (rho2 * d1) * (math.cosh(r0) * math.tanh(rho * s + r0) - math.sinh(r0))
        return ux0 + u * dx, uy0 + u * dy, w0 * math.cosh(r0) / math.cosh(rho * s + r0)
    return f


def _em(t):
    return t * t * (3 - 2 * t)


def duong_camera(bd, giay):
    """Mốc camera -> danh sách [x, y, zoom] cho TỪNG khung hình."""
    diem = bd["diem"]
    tat = list(range(len(diem)))
    moc = []
    for c in bd.get("camera") or []:
        nh = c.get("nhin")
        if nh == "xa":
            cx, cy, _ = _khung(diem, tat)
            p = (cx, cy, Z_XA)
        else:
            ids = tat if nh in (None, "tat_ca") else [i for i in (nh if isinstance(nh, list) else [nh])
                                                     if isinstance(i, int) and 0 <= i < len(diem)]
            if not ids:
                continue
            p = _khung(diem, ids)
        try:
            them = max(-3.0, min(0.5, float(c.get("zoom_them") or 0)))   # +1 đo 20/10: viền tràn khỏi khung
        except (TypeError, ValueError):
            them = 0.0
        try:
            luc = float(c.get("luc") or 0)
        except (TypeError, ValueError):
            luc = 0.0
        moc.append((max(0.0, min(giay, luc)), p[0], p[1], max(1.5, min(Z_CAM, p[2] + them))))
    if not moc:
        moc = [(0.0, *_khung(diem, tat))]
    moc.sort(key=lambda m: m[0])
    n = max(30, round(giay * FPS))
    ra = []
    for f in range(n):
        t = f / FPS
        if t <= moc[0][0]:
            m = moc[0]
            ra.append([m[1], m[2], m[3]])
            continue
        k = next((k for k in range(len(moc) - 1) if moc[k][0] <= t < moc[k + 1][0]), None)
        if k is None:                                        # sau mốc cuối: trôi zoom nhẹ cho khỏi đứng hình
            m = moc[-1]
            du = max(0.5, giay - m[0])
            ra.append([m[1], m[2], min(Z_CAM, m[3] + 0.2 * (t - m[0]) / du)])
            continue
        a, b = moc[k], moc[k + 1]
        if b[0] - a[0] < 1e-6:
            ra.append([b[1], b[2], b[3]])
            continue
        x, y, w = _bay((a[1], a[2], W / 2 ** a[3]), (b[1], b[2], W / 2 ** b[3]))(_em((t - a[0]) / (b[0] - a[0])))
        ra.append([x, y, math.log2(W / w)])
    return [[round(x, 6), round(y, 6), round(z, 4)] for x, y, z in ra]


def o_can(cam):
    """Ô ảnh cần cho mọi khung: mức tz = ceil(zoom) (tối đa Z_MAX) và tz-1 lót dưới — BanDoVeTinh.jsx tính y hệt
    (ở đây nới thêm 1 ô mỗi phía cho chắc)."""
    can = set()
    for x, y, z in cam:
        tz = max(1, min(Z_MAX, math.ceil(z)))
        for lv in (tz - 1, tz):
            k = 2 ** (z - lv)                                # px màn hình / px ô
            n = 2 ** lv
            x0, x1 = (x * n - W / 2 / k) / 256, (x * n + W / 2 / k) / 256
            y0, y1 = (y * n - H / 2 / k) / 256, (y * n + H / 2 / k) / 256
            for ty in range(max(0, math.floor(y0) - 1), min(n - 1, math.floor(y1) + 1) + 1):
                for tx in range(math.floor(x0) - 1, math.floor(x1) + 2):
                    can.add((lv, tx % n, ty))
    return can


def _trong(lat, lon, vien):
    """Điểm nằm trong đa giác [[lat, lon]…] (tia ngang)."""
    ok = False
    for (a1, o1), (a2, o2) in zip(vien, vien[1:] + vien[:1]):
        if (a1 > lat) != (a2 > lat) and lon < o1 + (lat - a1) * (o2 - o1) / (a2 - a1):
            ok = not ok
    return ok


def bo_duong_long_nhau(bd):
    """Bỏ đường nối giữa hai nơi mà nơi này NẰM TRONG nơi kia (20/10: AI nối Blackwater -> bán đảo Delmarva chứa nó)."""
    d = bd["diem"]
    giu = []
    for x in bd.get("duong") or []:
        a, b = d[x["tu"]] if 0 <= x["tu"] < len(d) else None, d[x["den"]] if 0 <= x["den"] < len(d) else None
        if not a or not b or a is b:
            continue
        if (b.get("vien") and _trong(a["lat"], a["lon"], b["vien"])) or (a.get("vien") and _trong(b["lat"], b["lon"], a["vien"])):
            log(f"    bỏ đường nối «{a.get('nhan')}» – «{b.get('nhan')}»: nơi này nằm trong nơi kia")
            continue
        giu.append(x)
    bd["duong"] = giu
    return bd


def _tai_o(o):
    return nen_ban_do._tai_o(o[0], o[1], o[2], "vetinh")    # noqa: SLF001


def chuan_bi(bd, giay, bao=None):
    """bd (đã tra toạ độ) -> props cho BanDoVeTinh.jsx: cam theo khung + danh sách ô có sẵn trong public/ban_do/."""
    bd = bo_duong_long_nhau(dict(bd))
    cam = duong_camera(bd, giay)
    can = sorted(o_can(cam))
    if len(can) > O_TOI_DA:
        raise ValueError(f"Cảnh cần {len(can)} ô ảnh vệ tinh — quá nhiều, bớt chặng bay hoặc kéo dài thời gian")
    log(f"    Bản đồ vệ tinh: {len(can)} ô ảnh")
    if bao:
        bao(f"Tải ảnh vệ tinh ({len(can)} ô, lần đầu hơi lâu)…")
    with ThreadPoolExecutor(6) as ex:
        tep = list(ex.map(_tai_o, can))
    shutil.rmtree(PUB, ignore_errors=True)
    os.makedirs(PUB, exist_ok=True)
    co = []
    for (z, x, y), p in zip(can, tep):
        if p:
            shutil.copyfile(p, os.path.join(PUB, f"{z}_{x}_{y}.jpg"))
            co.append(f"{z}_{x}_{y}")
    if len(co) < len(can) * 0.9:
        raise ValueError(f"Chỉ tải được {len(co)}/{len(can)} ô ảnh vệ tinh — kiểm tra mạng rồi dựng lại")
    diem = [{"lat": d["lat"], "lon": d["lon"], "nhan": d.get("nhan") or "",
             "vien": d.get("vien") if d.get("khoanh") else None,   # 22/10 user: chỉ VẼ viền khi được yêu cầu khoanh lãnh thổ
             "vao": float(d.get("vao") or 0), "ra": float(d.get("ra") or giay)} for d in bd["diem"]]
    return {"cam": cam, "o": co, "diem": diem, "duong": bd.get("duong") or [], "zmax": Z_MAX,
            "ghi_nguon": nen_ban_do.GHI_NGUON["vetinh"]}


def clip_dia_danh(dia_danh, ten_vi, giay, khoanh=True):
    """22/10 user ("ảnh địa chỉ A nhìn siêu thực từ ngoài trái đất, đánh dấu lãnh thổ" — AI vẽ không ra): clip bản đồ
    VỆ TINH THẬT cho một địa danh — camera từ ngoài trái đất bay xuống, viền lãnh thổ thật (OpenStreetMap) chạy dần,
    ghim + tên tiếng Việt. Dùng ở bước ✨ (dieu_phoi "khoanh_vung"). Cache theo (địa danh, tên, độ dài). Lỗi -> None."""
    import hashlib
    import canh_mo_ta
    giay = round(max(3.0, float(giay)), 2)
    thu = os.path.join(CACHE_CHUNG, "ban_do_canh")
    os.makedirs(thu, exist_ok=True)
    out = os.path.join(thu, hashlib.md5(f"{dia_danh}|{ten_vi}|{giay}|{khoanh}|v1".encode("utf-8")).hexdigest()[:16] + ".mp4")
    if os.path.isfile(out) and os.path.getsize(out) > 5000:
        return out
    try:
        r = tra(dia_danh)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! bản đồ vệ tinh '{dia_danh}': {str(e)[:100]}")
        return None
    log(f"    bản đồ vệ tinh: «{dia_danh}» -> {r['ten_day_du'][:80]} ({r['lat']:.3f}, {r['lon']:.3f})")
    bd = {"diem": [dict(r, tim=dia_danh, nhan=ten_vi or dia_danh.split(",")[0], khoanh=bool(khoanh and r.get("vien")),
                        vao=min(0.8, giay * 0.2), ra=giay)],
          "camera": [{"luc": 0.0, "nhin": "xa"}, {"luc": round(giay * 0.6, 2), "nhin": [0]}], "duong": []}
    try:
        canh_mo_ta.dung({"nen": "#05070b", "lop": [], "ban_do": bd}, giay, out)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! dựng bản đồ vệ tinh '{dia_danh}': {str(e)[:120]}")
        return None
    return out if os.path.isfile(out) else None
