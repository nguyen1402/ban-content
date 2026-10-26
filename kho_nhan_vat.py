# -*- coding: utf-8 -*-
"""KHO NHÂN VẬT (con rối) — 25/10 user: "code vẽ mỗi đầu thân người thôi, còn biểu cảm và cử chỉ để AI vẽ, xong tôi duyệt,
ok thì chọn". Kênh kiểu Lạnh Vcl dán CÙNG MỘT nhân vật vẽ tay vào mọi cảnh; AI vẽ nhân vật mỗi cảnh thì "hoàn hảo quá".

  1. PHÔI: con_roi.py vẽ đầu + thân + tóc + quần áo cố định kiểu MS Paint (nền trắng).
  2. BIẾN THỂ: Flow vẽ lại ĐÚNG phôi đó (gắn làm ảnh tham chiếu) với từng tư thế + biểu cảm — đo 25/10: Flow giữ nguyên nét
     MS Paint của phôi, cử chỉ sinh động hơn code; mỗi lượt 2 phương án ~50 s.
  3. TÁCH NỀN: loang từ mép ảnh qua vùng trắng (mặt trắng nằm trong viền đen nên giữ nguyên) -> PNG trong suốt.
  4. DUYỆT: người dùng chọn biến thể đạt (một lần cho mỗi nhân vật); storyboard chỉ dán biến thể ĐÃ DUYỆT.

Dữ liệu: kho_nhan_vat/<id>/nv.json, phoi.png, bt/<tư thế>_<n>.png (+ _trong.png)."""
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from common import ROOT, log

GOC = os.path.join(ROOT, "kho_nhan_vat")
_KHOA = threading.RLock()
TT = {}                      # id -> {dang, dong[], loi}

# tư thế + biểu cảm hay dùng cho video kể chuyện (khoá: mô tả cho Flow)
TU_THE = {
    "dung_binh_thuong": ("Đứng bình thường", "Pose: standing still, arms down. Expression: neutral deadpan."),
    "dung_liec": ("Đứng liếc mắt", "Pose: standing, arms down. Expression: bored deadpan side-eye glance to the side."),
    "cui_dau_buon": ("Cúi đầu buồn", "Pose: head bowed low, shoulders slumped, arms hanging. Expression: sad, small frown."),
    "cuoi": ("Cười vui", "Pose: standing relaxed, one hand raised waving. Expression: happy open smile."),
    "cuoi_meo": ("Cười méo gượng", "Pose: standing stiffly, hands clasped in front. Expression: forced awkward crooked smile, a sweat drop."),
    "soc": ("Sốc", "Pose: leaning back, both hands up in shock. Expression: wide round eyes, open mouth."),
    "gian_chi_tay": ("Giận chỉ tay", "Pose: pointing forward angrily with one arm stretched out, other hand on hip. Expression: angry frown."),
    "khoanh_tay": ("Khoanh tay", "Pose: arms crossed over the chest. Expression: unimpressed deadpan."),
    "om_mat_khoc": ("Ôm mặt khóc", "Pose: both hands covering the face, body hunched. Expression: crying with tears."),
    "om_dau": ("Ôm đầu căng thẳng", "Pose: both hands gripping the head. Expression: stressed, worried, sweat drops."),
    "nhun_vai": ("Nhún vai", "Pose: shrugging with both palms up. Expression: helpless half smile."),
    "cui_chao": ("Cúi chào lễ phép", "Pose: bowing politely from the waist, hands together in front. Expression: polite small smile."),
    "dua_do": ("Đưa đồ cho người khác", "Pose: both arms stretched forward handing over a small box. Expression: reluctant."),
    "cam_dien_thoai": ("Cầm điện thoại", "Pose: holding a smartphone in front of the chest, looking down at it. Expression: neutral."),
    "ngoi_buon": ("Ngồi buồn", "Pose: sitting on a small plastic stool, elbows on knees, head down. Expression: sad. Draw the stool too."),
    "di_bo": ("Đi bộ", "Pose: walking to the right, mid-stride, arms swinging. Expression: neutral."),
    "chay": ("Chạy vội", "Pose: running fast to the right, leaning forward. Expression: worried."),
    "quay_lung": ("Quay lưng", "Pose: standing seen from behind (back view), head slightly down. Show the back of the hair, no face."),
}
_GIU = ("Redraw EXACTLY the character in the reference image — the same crude MS Paint drawing: same thick wobbly black "
        "outlines, same flat colors with no shading, same big round white head, same hair shape and color, same tiny black "
        "dot eyes and single-line mouth, same clothes and colors, same body proportions. Do NOT make it more detailed, more "
        "polished or more realistic; no anime features, no nose, no extra facial details. Full body, centered, on a plain "
        "pure white background, nothing else in the image. No text.")


def _slug(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40] or "nv"


def thu_muc(nid):
    return os.path.join(GOC, nid)


def doc(nid):
    p = os.path.join(thu_muc(nid), "nv.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(f"không thấy nhân vật {nid}")


def luu(nv):
    with _KHOA:
        os.makedirs(thu_muc(nv["id"]), exist_ok=True)
        p = os.path.join(thu_muc(nv["id"]), "nv.json")
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(nv, f, ensure_ascii=False, indent=1)
        for lan in range(20):                              # Windows: file đang được đọc (giao diện) -> thay thế bị từ chối
            try:
                os.replace(p + ".tmp", p)
                break
            except PermissionError:
                if lan == 19:
                    raise
                time.sleep(0.15)


def ds():
    os.makedirs(GOC, exist_ok=True)
    ra = []
    for d in sorted(os.listdir(GOC)):
        try:
            ra.append(doc(d))
        except ValueError:
            continue
    return ra


def _ve_phoi(nv):
    """Phôi = con rối code đứng thẳng, mặt bình thường, trên nền trắng vuông (ảnh tham chiếu cho Flow)."""
    import con_roi
    from PIL import Image
    nen = Image.new("RGBA", (1200, 1200), (255, 255, 255, 255))
    r = con_roi.ve(nv["hinh"], "dung", "binh_thuong")
    nen.alpha_composite(r, ((1200 - r.width) // 2, 1200 - r.height - 60))
    p = os.path.join(thu_muc(nv["id"]), "phoi.png")
    nen.convert("RGB").save(p)
    return p


def tao(ten, hinh, mo_ta=""):
    """Nhân vật mới từ thông số hình (con_roi: toc, mau_toc, ao, mau_ao, mau_quan, mau_giay, mau_da) -> vẽ phôi."""
    ten = str(ten or "").strip()
    if not ten:
        raise ValueError("đặt tên nhân vật")
    nid = _slug(ten)
    if os.path.isfile(os.path.join(thu_muc(nid), "nv.json")):
        nid += time.strftime("_%H%M%S")
    nv = {"id": nid, "ten": ten, "mo_ta": str(mo_ta or ""), "hinh": dict(hinh or {}), "bien_the": [], "tao": time.time()}
    os.makedirs(thu_muc(nid), exist_ok=True)
    nv["phoi"] = _ve_phoi(nv)
    luu(nv)
    return nv


def sua_hinh(nid, hinh):
    """Đổi thông số phôi -> vẽ lại phôi (biến thể cũ giữ nguyên, nên vẽ lại nếu đổi nhiều)."""
    nv = doc(nid)
    nv["hinh"] = dict(hinh or {})
    nv["phoi"] = _ve_phoi(nv)
    luu(nv)
    return nv


def tach_nen_trang(vao, ra, nguong=40):
    """Nền trắng -> trong suốt bằng LOANG từ mép (vùng trắng nằm trong viền đen như mặt, áo trắng giữ nguyên); cắt sát."""
    from PIL import Image, ImageDraw
    im = Image.open(vao).convert("RGB")
    W, H = im.size
    loang = im.copy()
    DAU = (255, 0, 255)                                        # màu đánh dấu vùng nền
    for x, y in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1), (W // 2, 0), (W // 2, H - 1), (0, H // 2), (W - 1, H // 2)]:
        px = loang.getpixel((x, y))
        if min(px) > 255 - nguong * 2 and px != DAU:
            ImageDraw.floodfill(loang, (x, y), DAU, thresh=nguong)
    a = Image.new("L", (W, H), 255)
    lp, ap = loang.load(), a.load()
    for y in range(H):
        for x in range(W):
            if lp[x, y] == DAU:
                ap[x, y] = 0
    rgba = im.convert("RGBA")
    rgba.putalpha(a)
    hop = a.getbbox()
    if hop:
        rgba = rgba.crop(hop)
    rgba.save(ra)
    return ra


def _bao(nid, m):
    tt = TT.setdefault(nid, {})
    tt.setdefault("dong", []).append(time.strftime("%H:%M:%S ") + m)
    tt["dong"] = tt["dong"][-80:]
    log(f"[nhân vật {nid}] {m}")


def ve_bien_the(nid, khoa=None, tu_do=""):
    """Flow vẽ các tư thế (khoá trong TU_THE, mặc định tư thế CHƯA có biến thể được duyệt) + yêu cầu tự do -> mỗi tư thế 2
    phương án, tách nền, trạng thái "cho" (chờ duyệt). Chạy nền; xem TT[nid]."""
    import flow_ve
    nv = doc(nid)
    tt = TT.setdefault(nid, {})
    if tt.get("dang"):
        raise RuntimeError("đang vẽ — chờ xong")
    if not flow_ve.co_ho_so():
        raise RuntimeError("chưa có hồ sơ Flow — tạo ở «🎨 Hồ sơ Flow» trên trang chính")
    da_duyet = {b["tu_the"] for b in nv["bien_the"] if b.get("tt") == "duyet"}
    viec = [(k, TU_THE[k][1]) for k in (khoa or [k for k in TU_THE if k not in da_duyet]) if k in TU_THE]
    if str(tu_do or "").strip():
        viec.append(("tu_do_" + time.strftime("%H%M%S"), str(tu_do).strip()))
    if not viec:
        raise ValueError("mọi tư thế đã có biến thể được duyệt")
    tt.update(dang=True, loi="", dong=[])
    thu = os.path.join(thu_muc(nid), "bt")
    os.makedirs(thu, exist_ok=True)

    def mot(kv):
        k, mo_ta = kv
        t0 = time.time()
        try:
            tep = flow_ve.ve_nhieu(f"{mo_ta}\n{_GIU}", thu, f"{k}_{time.strftime('%H%M%S')}", "1:1", [nv["phoi"]])
        except Exception as e:                               # noqa: BLE001
            tep = []
            _bao(nid, f"✖ {k}: {str(e)[:120]}")
        moi = []
        for f in tep:
            try:
                trong = tach_nen_trang(f, f[:-4] + "_trong.png")
            except Exception as e:                           # noqa: BLE001
                _bao(nid, f"! tách nền {os.path.basename(f)}: {str(e)[:80]}")
                trong = ""
            moi.append({"id": os.path.basename(f)[:-4], "tu_the": k, "ten": TU_THE.get(k, (mo_ta[:40],))[0],
                        "mo_ta_en": mo_ta, "file": f, "trong": trong, "tt": "cho", "luc": time.time()})
        with _KHOA:
            n = doc(nid)
            n["bien_the"] += moi
            luu(n)
        _bao(nid, (f"✔ {k}: {len(moi)} phương án" if moi else f"✖ {k}: Flow không trả ảnh") + f" ({time.time() - t0:.0f}s)")

    def chay():
        try:
            _bao(nid, f"Flow vẽ {len(viec)} tư thế từ phôi ({flow_ve.so_luong_ve()} luồng)…")
            with ThreadPoolExecutor(flow_ve.so_luong_ve()) as ex:
                list(ex.map(mot, viec))
            _bao(nid, "✔ Xong — chọn các phương án đạt rồi bấm Duyệt")
        except Exception as e:                               # noqa: BLE001
            tt["loi"] = str(e)[:300]
            _bao(nid, f"✖ {str(e)[:200]}")
        tt["dang"] = False
    threading.Thread(target=chay, daemon=True).start()


def dat_tt(nid, bid, trang_thai):
    """Duyệt / bỏ một biến thể. Mỗi tư thế giữ NHIỀU biến thể duyệt (storyboard xoay vòng cho đỡ lặp)."""
    if trang_thai not in ("duyet", "bo", "cho"):
        raise ValueError("trạng thái không hợp lệ")
    with _KHOA:
        nv = doc(nid)
        for b in nv["bien_the"]:
            if b["id"] == bid:
                b["tt"] = trang_thai
        luu(nv)
    return nv


def xoa(nid):
    import shutil
    shutil.rmtree(thu_muc(nid), ignore_errors=True)


def chon(nid, tu_the, so=0):
    """PNG trong suốt ĐÃ DUYỆT của tư thế (so: chỉ số xoay vòng) -> đường dẫn | None."""
    try:
        nv = doc(nid)
    except ValueError:
        return None
    ds_ = [b["trong"] for b in nv["bien_the"] if b.get("tt") == "duyet" and b["tu_the"] == tu_the and b.get("trong")
           and os.path.isfile(b["trong"])]
    return ds_[so % len(ds_)] if ds_ else None


def tu_the_da_duyet(nid):
    """{tư thế: số biến thể đã duyệt} — storyboard chỉ cho AI chọn trong các tư thế này."""
    try:
        nv = doc(nid)
    except ValueError:
        return {}
    ra = {}
    for b in nv["bien_the"]:
        if b.get("tt") == "duyet":
            ra[b["tu_the"]] = ra.get(b["tu_the"], 0) + 1
    return ra
