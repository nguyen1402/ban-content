# -*- coding: utf-8 -*-
"""VẼ ẢNH MINH HOẠ bằng Gemini web (Nano Banana) qua COOKIE (13/10 user: thứ trừu tượng / không có ảnh thật cụ thể —
vi khuẩn, enzyme, chuỗi phân tử, dòng tiền… — nhờ AI vẽ cho khớp lời).

Không khoá API: dùng kho cookie Gemini RIÊNG của bán-content %LOCALAPPDATA%\\BanContent\\gemini_cookies.json (CHỈ tài khoản đã đặt tên),
thư viện gemini_webapi. Ảnh vẽ trên NỀN TRẮNG trơn để tách nền sạch (dấu nhỏ ở góc của Gemini nằm ở nền -> mất khi tách).
Xoay tài khoản khi một tài khoản lỗi / hết lượt."""
import asyncio
import json
import os
import re
import subprocess

from common import log

__import__("sys").path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tts"))
import gemini_cookie_store as _kho_gemini                   # noqa: E402  kho RIÊNG %LOCALAPPDATA%\BanContent

KHO = _kho_gemini.store_path()
_HONG = set()                                                # tài khoản lỗi trong lượt chạy này
CREDIT_MOI_ANH = 17        # 13/10 đo: vẽ 1 ảnh trừ 17 credit (tài khoản lớn 12.096 / đợt ~5 giờ, nhỏ 600)
_CON = {}                                                    # nhãn tài khoản -> credit còn (ước, trừ dần sau mỗi ảnh)
_KHOA_CON = __import__("threading").Lock()


async def _do_credit(ck):
    """Credit còn lại của một tài khoản (số nhỏ nhất trong các hạn mức máy chủ báo); None nếu không báo."""
    from gemini_webapi import GeminiClient
    cli = GeminiClient(ck.get("__Secure-1PSID"), ck.get("__Secure-1PSIDTS"))
    them = {k: v for k, v in ck.items() if k not in ("__Secure-1PSID", "__Secure-1PSIDTS")}
    if them:
        cli.cookies = them
    try:
        await cli.init(timeout=60, auto_close=False, auto_refresh=False, verbose=False)
        con = [v.get("remaining") for k, v in (cli.quotas or {}).items() if k != "extra" and isinstance(v, dict)]
        con = [x for x in con if isinstance(x, (int, float))]
        return min(con) if con else None
    finally:
        try:
            await cli.close()
        except Exception:                                    # noqa: BLE001
            pass


def _xep_tai_khoan(do_credit=True):
    """13/10 user: ưu tiên tài khoản còn NHIỀU credit nhất. Đo một lần mỗi lượt chạy, sau đó trừ dần theo ảnh đã vẽ;
    tài khoản không báo số xếp cuối; còn < 2 ảnh thì bỏ. do_credit=False (vẽ lẻ trên giao diện): không đo, dùng số đã biết."""
    ds = _tai_khoan()
    if not do_credit:
        with _KHOA_CON:
            ds = [a for a in ds if _dung_duoc(a["label"])]
        return sorted(ds, key=lambda a: -(_CON.get(a["label"]) if _CON.get(a["label"]) is not None else 10 ** 9))
    with _KHOA_CON:
        for a in ds:
            if a.get("label") not in _CON:
                try:
                    _CON[a["label"]] = asyncio.run(asyncio.wait_for(_do_credit(a["cookies"]), 90))
                except Exception:                            # noqa: BLE001
                    _CON[a["label"]] = None
        if not getattr(_xep_tai_khoan, "da_bao", False):
            log("    credit Gemini: " + ", ".join(f"{a['label']} {_CON.get(a['label'])}" for a in ds))
            _xep_tai_khoan.da_bao = True
        ds = [a for a in ds if _dung_duoc(a["label"])]
        return sorted(ds, key=lambda a: -_CON[a["label"]])


def _dung_duoc(nhan):
    """23/10 user: đã đo credit mà tài khoản báo None (không đọc được hạn mức) hoặc còn < 2 ảnh -> KHÔNG vẽ — vẽ cũng chỉ
    nhận câu "can't create any for you / signed out". Chưa đo (vẽ lẻ trước lần đo đầu) thì vẫn cho dùng."""
    if nhan not in _CON:
        return True
    c = _CON[nhan]
    return c is not None and c >= 2 * CREDIT_MOI_ANH


_KHONG_VE_DUOC = re.compile(r"can.?t (create|seem to create|make|generate)|signed (out|in)|image creation", re.I)


LUONG_VE_TOI_DA = 8         # 22/10 user ("nhiều cookie được nghỉ ngơi"): số luồng vẽ = số tài khoản dùng được, tối đa bấy nhiêu
_DANG = {}                  # nhãn tài khoản -> số lượt vẽ đang chạy trên nó
_KHOA_DANG = __import__("threading").Lock()


def so_luong_ve():
    """Số luồng vẽ song song nên dùng = số tài khoản Gemini còn dùng được (3..LUONG_VE_TOI_DA)."""
    n = sum(1 for a in _tai_khoan() if a.get("label") not in _HONG and _dung_duoc(a.get("label")))
    return max(3, min(LUONG_VE_TOI_DA, n))


def _lan_luot(ds):
    """22/10: chia đều — tài khoản ĐANG ÍT VIỆC nhất lên trước (cùng mức thì giữ thứ tự credit). Trước đây mọi luồng
    cùng chọn tài khoản nhiều credit nhất -> 3 luồng dồn một tài khoản, 7 tài khoản kia ngồi không."""
    with _KHOA_DANG:
        return sorted(ds, key=lambda a: _DANG.get(a.get("label"), 0))


class _Giu:
    """Đánh dấu tài khoản đang có một lượt vẽ (with _Giu(nhan): ...)."""

    def __init__(self, nhan):
        self.nhan = nhan

    def __enter__(self):
        with _KHOA_DANG:
            _DANG[self.nhan] = _DANG.get(self.nhan, 0) + 1

    def __exit__(self, *a):
        with _KHOA_DANG:
            _DANG[self.nhan] = max(0, _DANG.get(self.nhan, 1) - 1)


def _loai_han(e):
    """Lỗi làm tài khoản hỏng hẳn trong lượt chạy (cookie hết hạn, bị chặn, hết lượt) — khác lỗi mạng tạm thời."""
    t = (type(e).__name__ + " " + str(e)).lower()
    tam = ("connection", "timeout", "timed out", "temporar", "lost", "reset", "try again", "503", "502", "500")
    if any(k in t for k in tam) and not any(k in t for k in ("auth", "cookie", "quota", "exhaust", "usage limit")):
        return False
    return True


def _tru(nhan):
    with _KHOA_CON:
        if isinstance(_CON.get(nhan), (int, float)):
            _CON[nhan] -= CREDIT_MOI_ANH


def _tai_khoan():
    try:
        d = json.load(open(KHO, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    ds = d.get("accounts") or []
    if isinstance(ds, dict):
        ds = list(ds.values())
    return [a for a in ds if isinstance(a, dict) and (a.get("label") or "").strip()
            and (a.get("cookies") or {}).get("__Secure-1PSID")]


DAU_CACH_MEP = 120          # 14/10 đo: dấu ✦ Gemini tâm cách mép phải và mép dưới ~120 px (ảnh 1408x768 lẫn 1024x1024)
DAU_BAN_KINH = 34           # dấu rộng ~50 px -> xoá vòng bán kính 34 px quanh tâm
DAU_FLOW_CACH_MEP = 97      # 23/10 đo: ảnh Google Flow 1376x768: dấu ✦ 48x48, tâm cách mép phải / dưới ~97 px (gwt không dò ra)
DAU_FLOW_BAN_KINH = 30
XOA_DAU = False             # 19/10 user: KHÔNG làm mờ dấu ✦ nữa (vệt mờ lộ trên ảnh) — bản nháp phóng to ảnh AI 120% giấu dấu
GWT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "gwt", "gwt-mini.exe")
XOA_LOGO = True             # 19/10 user: xoá logo ✦ Gemini bằng GeminiWatermarkTool (allenk, MIT): TÍNH NGƯỢC lớp trong suốt
#                             đã biết -> ra lại điểm ảnh gốc (không làm mờ, không vẽ bù); dấu ẩn SynthID giữ nguyên
PHONG_ANH_AI = 1.0 if XOA_LOGO and os.path.isfile(GWT) else 1.20   # đã xoá được logo -> không cần phóng 120% giấu dấu


def xoa_logo(f):
    """Xoá logo ✦ Gemini tại chỗ (tự dò; ảnh không có logo thì để nguyên). True = đã xoá."""
    if not (XOA_LOGO and os.path.isfile(GWT) and f and os.path.isfile(f)):
        return False
    tam = os.path.splitext(f)[0] + "._gwt" + os.path.splitext(f)[1]
    try:
        r = subprocess.run([GWT, "--no-banner", "-q", "-i", f, "-o", tam, "--denoise", "soft"], capture_output=True,
                           timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError) as e:
        log(f"    ! xoá logo Gemini lỗi: {str(e)[:80]}")
        return False
    if r.returncode == 0 and os.path.isfile(tam) and os.path.getsize(tam) > 4000:
        os.replace(tam, f)
        return True
    if os.path.isfile(tam):
        os.remove(tam)
    return xoa_dau_flow(f)                                   # gwt không tự dò ra: ảnh Google Flow -> khuôn riêng của Flow


_KHUON = []                                                  # khuôn alpha logo ✦ 96x96 của gwt (lấy một lần)


def _khuon_logo():
    """Khuôn alpha logo của gwt: cho gwt 'xoá' logo trên ảnh xám 200 phẳng rồi giải ngược a = (200-I)/(255-I)."""
    if _KHUON:
        return _KHUON[0]
    import tempfile
    import cv2
    import numpy as np
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "x.png"), os.path.join(d, "y.png")
        cv2.imwrite(a, np.full((300, 300, 3), 200, np.uint8))
        _chay([GWT, "--no-banner", "-q", "-f", "-i", a, "-o", b, "--region", "100,100,96,96", "--denoise", "off"], 60)
        i = cv2.imread(b, 0).astype(np.float32)[100:196, 100:196]
    _KHUON.append(np.clip((200 - i) / (255 - i), 0, 1))
    return _KHUON[0]


def _chay(cmd, timeout=3600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=0x08000000 if os.name == "nt" else 0)


def _khop_logo(med, ngan):
    """Khớp khuôn logo ✦ của gwt trên ảnh xám `med` (góc dưới phải đã cắt ra), qua nhiều cỡ.
    ngan = cạnh ngắn của khung gốc. -> (điểm khớp, x, y, cỡ, tỉ lệ sáng) — x, y tính trong `med`."""
    import cv2
    import numpy as np
    rh, rw = med.shape
    khuon = _khuon_logo()
    tot = (0.0, 0, 0, 0)
    for co in range(max(24, int(ngan * 0.045)) // 2 * 2, min(int(ngan * 0.11), rw, rh) + 1, 2):   # 1080p: logo 72 = 6,7%
        t = cv2.resize(khuon, (co, co), interpolation=cv2.INTER_AREA)
        k = max(15, co // 2 * 2 + 1)
        d = med - cv2.GaussianBlur(med, (k, k), 0)            # bỏ nền mượt, giữ nét logo
        r = cv2.matchTemplate(d, t - t.mean(), cv2.TM_CCOEFF_NORMED)
        le = int(ngan * 0.25)                                 # logo nằm sát góc: cách mép phải/dưới tối đa 25% cạnh ngắn
        r[:max(0, rh - co - le), :] = -1
        r[:, :max(0, rw - co - le)] = -1
        _, mx, _, (lx, ly) = cv2.minMaxLoc(r)
        if mx > tot[0] and float((d[ly:ly + co, lx:lx + co] * t).sum()) > 0:   # logo SÁNG hơn nền
            tot = (mx, lx, ly, co)
    diem, lx, ly, co = tot
    ty_le = 0.0
    if co:                                                   # KIỂM VẬT LÝ: logo trắng phủ alpha -> độ sáng nổi lên = (255 - nền) * alpha
        t = np.zeros_like(med)
        t[ly:ly + co, lx:lx + co] = cv2.resize(khuon, (co, co), interpolation=cv2.INTER_AREA)
        k = max(15, co // 2 * 2 + 1)
        d = med - cv2.GaussianBlur(med, (k, k), 0)
        tc = t - cv2.GaussianBlur(t, (k, k), 0)
        vung = np.zeros(med.shape, bool)
        vung[max(0, ly - co):ly + 2 * co, max(0, lx - co):lx + 2 * co] = True
        nen = float(np.median(med[vung & (t < 0.01)]))
        ty_le = float((d * tc)[vung].sum() / max(1e-6, (tc * tc)[vung].sum())) / max(1.0, 255 - nen)
    return diem, lx, ly, co, ty_le


# 26/10 user (ảnh storyboard Flow còn vệt tô lấp ở góc — "tưởng dùng tools xoá cơ mà"): gwt tự dò KHÔNG nhận dấu ✦ của
# ảnh Flow ("No watermark detected (-8%)"); ép gwt xoá đúng vùng thì còn BÓNG TỐI hình sao vì khuôn alpha của gwt là của
# logo Gemini (đục hơn, viền mềm). Đo 26/10 trên 6 ảnh Flow 1376x768 (nền inpaint từ xung quanh, trung bình, đối xứng 8
# phía của ✦): dấu Flow là sao 4 cánh viền sắc ~48px, alpha phẳng ~0,29, tâm cách mép phải / dưới ~97px -> khuôn riêng
# tools/gwt/khuon_flow.npy (64x64, tâm ở giữa) và tính ngược nền: B = (I - a*255) / (1 - a). Flow không đóng dấu mọi ảnh
# (ảnh nền phẳng không có) -> phải dò, không thấy thì để nguyên ảnh.
KHUON_FLOW = os.path.join(os.path.dirname(GWT), "khuon_flow.npy")
FLOW_CACH_MEP = 97          # tâm dấu cách mép phải / dưới (ảnh cạnh ngắn 768)


def do_logo_flow(f, a=None):
    """Tìm dấu ✦ Flow quanh vị trí quen thuộc -> (tâm x, tâm y, hệ số cỡ, khuôn alpha đã co giãn) | None."""
    import cv2
    import numpy as np
    if not os.path.isfile(KHUON_FLOW):
        return None
    if a is None:
        a = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
    if a is None:
        return None
    h, w = a.shape[:2]
    k = min(w, h) / 768
    al = np.load(KHUON_FLOW)
    n = max(16, int(round(al.shape[0] * k)) // 2 * 2)
    al = cv2.resize(al, (n, n), interpolation=cv2.INTER_AREA) if n != al.shape[0] else al
    vien = int(24 * k) + 4
    m0 = np.zeros((n + 2 * vien, n + 2 * vien), np.uint8)
    m0[vien:vien + n, vien:vien + n][al > 0.03] = 255
    m0 = cv2.dilate(m0, np.ones((5, 5), np.uint8))

    def thu(x, y):
        """Tại góc (x, y): đoán nền dưới dấu bằng lấp từ xung quanh, suy ra độ đục từng điểm, so với khuôn.
        -> (độ khớp hình dạng, độ đục so với khuôn). Dấu thật: khớp cao, độ đục ~1."""
        if x - vien < 0 or y - vien < 0 or x + n + vien > w or y + n + vien > h:
            return -1.0, 0.0
        nen = cv2.inpaint(a[y - vien:y + n + vien, x - vien:x + n + vien], m0, 5, cv2.INPAINT_TELEA)
        nen = nen.astype(np.float32)[vien:vien + n, vien:vien + n]
        uoc = ((a[y:y + n, x:x + n].astype(np.float32) - nen) / np.maximum(255 - nen, 20)).mean(2)
        if uoc.std() < 1e-6:
            return -1.0, 0.0
        return float(np.corrcoef(uoc.ravel(), al.ravel())[0, 1]), float((uoc * al).sum() / (al * al).sum())

    cx, cy = int(w - FLOW_CACH_MEP * k - n / 2), int(h - FLOW_CACH_MEP * k - n / 2)
    le = int(6 * k) + 2                                      # dò lệch ±le px quanh chỗ quen thuộc: bước 2 rồi tinh 1
    tot = max(((thu(cx + dx, cy + dy), cx + dx, cy + dy) for dy in range(-le, le + 1, 2) for dx in range(-le, le + 1, 2)),
              key=lambda t: t[0][0])
    (_, _), bx, by = tot
    tot = max(((thu(bx + dx, by + dy), bx + dx, by + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)), key=lambda t: t[0][0])
    (khop, duc), x, y = tot
    # 26/10 đo: 8 ảnh có dấu khớp 0,58-0,99 (7/8 >= 0,76), độ đục 1,05-1,56; 120 ảnh storyboard cũ (đã tô lấp) + ảnh
    # nền phẳng: cao nhất 0,56 (vết tô lấp) — riêng một ảnh cũ 0,79 là ảnh VẪN CÒN dấu (tô lấp cũ bỏ sót)
    if khop < 0.6 or not 0.7 <= duc <= 1.7:
        log(f"    Dò dấu Flow: không thấy (khớp {khop:.2f}, độ đục {duc:.2f})")
        return None
    return x, y, n, al


def xoa_dau_flow(f):
    """Xoá dấu ✦ của ảnh Google Flow bằng tính ngược alpha (không làm mờ, không vẽ bù). True = đã xoá."""
    import cv2
    import numpy as np
    try:
        a = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
        vt = do_logo_flow(f, a)
        if not vt:
            return False
        x, y, n, al = vt
        # viền dấu thật mềm / lệch nhẹ so với khuôn -> tính ngược thô để lại đường viền mảnh. Chọn vị trí (±2px) và độ mềm
        # viền khuôn làm VIỀN ÍT LỘ NHẤT (năng lượng nét ở dải viền sau khi tính ngược) — chỉ tính ngược, không lấp / làm mờ
        # (26/10 thử lấp dải viền: cánh ✦ mảnh nên dải viền phủ gần hết dấu, cắt đứt nét nền như cách tô lấp cũ)
        h, w = a.shape[:2]
        # mỗi ảnh tự chọn vị trí (±3px), cỡ (94-100%) và độ đục (±10%) của khuôn: thước đo = độ lệch so với NỀN ĐOÁN (lấp
        # vùng dấu từ xung quanh) — chỉ để chọn thông số, ảnh ra vẫn là tính ngược (giữ nguyên nét thật của nền)
        vien = int(12 * n / 64) + 6
        if x - vien - 3 < 0 or y - vien - 3 < 0 or x + n + vien + 3 > w or y + n + vien + 3 > h:
            return False
        vung = cv2.dilate((al > 0.01).astype(np.uint8), np.ones((5, 5), np.uint8))
        m = np.zeros((n + 2 * vien, n + 2 * vien), np.uint8)
        m[vien:vien + n, vien:vien + n] = vung * 255
        nen = cv2.inpaint(a[y - vien:y + n + vien, x - vien:x + n + vien], m, 5, cv2.INPAINT_TELEA)
        nen = nen.astype(np.float32)[vien:vien + n, vien:vien + n]
        khuon = {}
        for co in (0.94, 0.97, 1.0):
            M = cv2.getRotationMatrix2D(((n - 1) / 2, (n - 1) / 2), 0, co)
            for duc in (0.9, 1.0, 1.1):
                khuon[co, duc] = np.clip(cv2.warpAffine(al, M, (n, n), flags=cv2.INTER_LINEAR) * duc, 0, 0.95)[..., None]

        def go(dx, dy, k):
            o = a[y + dy:y + dy + n, x + dx:x + dx + n].astype(np.float32)
            return np.clip((o - khuon[k] * 255) / (1 - khuon[k]), 0, 255)
        vg = vung > 0
        thu = [(dx, dy, k) for dy in range(-3, 4) for dx in range(-3, 4) for k in khuon]
        dx, dy, k = min(thu, key=lambda t: float(np.abs(go(*t) - np.roll(nen, (t[1], t[0]), (0, 1)))[vg].mean()))
        # còn sót đường viền rất mảnh (quầng tối ~1px quanh ✦ của Flow, đo được nhưng khuôn 2 lớp không làm sai số giảm);
        # thử lấp dải 1px thì ảnh nền cỏ thành vết gợn -> giữ thuần tính ngược
        a[y + dy:y + dy + n, x + dx:x + dx + n] = go(dx, dy, k).round().astype(np.uint8)
        ok, buf = cv2.imencode(os.path.splitext(f)[1] or ".png", a)
        if ok:
            buf.tofile(f)
        return bool(ok)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! xoá dấu Flow lỗi: {str(e)[:80]}")
        return False


def do_logo_video(f):
    """Tìm logo ✦ trong video (20/10 đo video Gemini 1920x1080: logo 72px ở (1704,864), lệch vào trong hơn ảnh nên gwt
    không tự dò được). Logo ĐỨNG YÊN còn hình chạy -> trung vị theo thời gian làm lộ logo; khớp khuôn gwt ở góc dưới phải
    qua nhiều cỡ. Trả (x, y, cỡ, điểm khớp, rộng, cao, fps, giây) — x None nếu không thấy logo."""
    import cv2
    import numpy as np
    p = json.loads(_chay(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", f]).stdout or b"{}")
    s = (p.get("streams") or [{}])[0]
    w, h = int(s.get("width") or 0), int(s.get("height") or 0)
    a, b = (s.get("r_frame_rate") or "30/1").split("/")
    fps = float(a) / max(1.0, float(b))
    giay = float((p.get("format") or {}).get("duration") or 0)
    if not w or not h:
        raise ValueError("không đọc được video")
    x0, y0 = int(w * 0.6), int(h * 0.55)                     # logo Gemini nằm ở góc dưới phải
    rw, rh = w - x0, h - y0
    lay = min(fps, max(2.0, 90 / max(giay, 0.1)))             # ~90 khung rải đều cả video
    raw = _chay(["ffmpeg", "-v", "error", "-i", f, "-vf", f"fps={lay:.3f},crop={rw}:{rh}:{x0}:{y0},format=gray",
                 "-f", "rawvideo", "-"]).stdout
    n = len(raw) // (rw * rh)
    if n < 3:
        raise ValueError("video quá ngắn để dò logo")
    med = np.median(np.frombuffer(raw[:n * rw * rh], np.uint8).reshape(n, rh, rw), 0).astype(np.float32)
    diem, x, y, co, ty_le = _khop_logo(med, min(w, h))
    x, y = (x + x0, y + y0) if co else (x, y)
    log(f"    Dò logo video: điểm khớp {diem:.2f}, tỉ lệ sáng {ty_le:.2f} tại ({x},{y}) cỡ {co}px")
    # 20/10 đo: 2 video Gemini khớp 0,82/0,85 + tỉ lệ 1,04/0,96; 27 video thường: khớp <= 0,6 hoặc tỉ lệ -0,0 / 0,08
    if diem < 0.6 or not 0.7 <= ty_le <= 1.35:
        return None, None, None, diem, w, h, fps, giay
    return x, y, co, diem, w, h, fps, giay


def xoa_logo_video(f, out, bao=None):
    """Xoá logo ✦ Gemini trong VIDEO: gwt tính ngược alpha trên TỪNG khung tại vị trí đã dò, ghép lại giữ nguyên tiếng.
    Không thấy logo -> chép nguyên video. Trả {"co_logo", "giay", "out"}."""
    import shutil
    import tempfile
    bao = bao or (lambda *_: None)
    if not os.path.isfile(GWT):
        raise ValueError("thiếu tools/gwt/gwt-mini.exe")
    bao("Dò vị trí logo…")
    x, y, co, _diem, _w, _h, fps, giay = do_logo_video(f)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if x is None:
        shutil.copyfile(f, out)
        return {"co_logo": False, "giay": giay, "out": out}
    with tempfile.TemporaryDirectory(dir=os.path.dirname(out)) as d:
        vao, ra = os.path.join(d, "vao"), os.path.join(d, "ra")
        os.makedirs(vao)
        os.makedirs(ra)
        bao("Tách khung hình…")
        _chay(["ffmpeg", "-v", "error", "-i", f, "-fps_mode", "passthrough", os.path.join(vao, "%06d.png")])
        bao(f"Xoá logo {len(os.listdir(vao))} khung hình…")
        _chay([GWT, "--no-banner", "-q", "-f", "-i", vao, "-o", ra, "--region", f"{x},{y},{co},{co}", "--denoise", "soft"])
        if len(os.listdir(ra)) < len(os.listdir(vao)):
            raise ValueError(f"xoá logo được {len(os.listdir(ra))}/{len(os.listdir(vao))} khung")
        bao("Ghép lại video (giữ tiếng)…")
        r = _chay(["ffmpeg", "-v", "error", "-y", "-framerate", f"{fps:.6f}", "-i", os.path.join(ra, "%06d.png"), "-i", f,
                   "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "192k", "-shortest", out])
        if not os.path.isfile(out):
            raise ValueError("ghép video lỗi: " + r.stderr.decode("utf-8", "ignore")[-200:])
    return {"co_logo": True, "giay": giay, "out": out}


# 19/10 user: phong cách CỐ ĐỊNH cho MỌI ảnh chụp AI ("Phong cách ảnh chụp thật, ống kính 50mm, khẩu độ F1.8, nền mờ nhẹ.
# Ánh sáng tự nhiên ban ngày, cân bằng trắng khoảng 5500K, không ám vàng, không lệch màu. Xóa hết chi tiết thừa, bóng đổ
# mềm, tự nhiên, màu điềm đạm, không quá rực.")
PHONG_CACH = ("Style: a REAL photograph, 50mm lens, aperture f/1.8, softly blurred background. Natural daylight, white "
              "balance about 5500K, no yellow cast, no colour shift. Remove all unnecessary clutter, soft natural shadows, "
              "calm muted colours, not oversaturated.")


NAM_QUA_KHU = 1990          # 22/10 user ("màu ảnh phù hợp với năm"): cảnh trước năm này -> màu / chất ảnh THEO THỜI ĐẠI
PHONG_CACH_CU = ("Style: a REAL photograph, 50mm lens, softly blurred background, clean composition with no unnecessary "
                 "clutter, soft natural shadows.")


def nam_cua(thoi_dai):
    """Năm sớm nhất đọc được trong chữ thời đại ('1904', 'the 1960s', 'early 20th century', 'thế kỷ 19') | None."""
    import re
    t = str(thoi_dai or "").lower()
    ds = [int(x) for x in re.findall(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)", t)]
    for m in re.finditer(r"(\d{1,2})(?:st|nd|rd|th)?\s*century|thế kỷ\s*(\d{1,2})", t):
        tk = int(m.group(1) or m.group(2))
        ds.append((tk - 1) * 100 + (30 if "early" in t or "đầu" in t else 50))
    return min(ds) if ds else None


def phong_cach(thoi_dai=""):
    """Đuôi câu lệnh vẽ: thời đại của cảnh (trang phục, xe cộ, đồ vật đúng thời ấy) + phong cách ảnh.
    22/10 user: cảnh QUÁ KHỨ (trước NAM_QUA_KHU) — màu, độ hạt, đen trắng / màu đời đầu do THỜI ĐẠI quyết (như ảnh chụp
    thật thời đó), thắng màu cố định 5500K; cảnh hiện đại giữ nguyên phong cách cố định của user (PHONG_CACH)."""
    td = str(thoi_dai or "").strip()
    if not td:
        return PHONG_CACH
    nam = nam_cua(td)
    if nam is not None and nam < NAM_QUA_KHU:
        return (f"Period: the scene takes place in {td} — clothing, hairstyles, vehicles, equipment and buildings exactly of "
                f"that time. It must look like an AUTHENTIC photograph actually taken in {td}: the camera, film stock, grain, "
                f"tonality and colours of real photographs from that era (black-and-white, sepia or early colour film as was "
                f"usual then) — the era decides the colours, not a modern neutral grade. " + PHONG_CACH_CU)
    return (f"Period: the scene takes place in {td} — clothing, hairstyles, vehicles, equipment, buildings and the colour "
            f"palette must match real photographs of that period (white balance stays neutral). ") + PHONG_CACH


def xoa_dau_gemini(f, cach_mep=DAU_CACH_MEP, ban_kinh=DAU_BAN_KINH):
    """14/10 user "logo gemini kia bỏ đi": tô lấp (inpaint) đúng chỗ dấu ✦ ở góc phải dưới ngay khi ảnh về — trên nền
    trắng thành trắng, đè lên nội dung thì lấp theo vùng quanh (vết rất nhỏ). Lỗi đọc/ghi: để nguyên ảnh.
    Ảnh Google Flow: cach_mep=DAU_FLOW_CACH_MEP, ban_kinh=DAU_FLOW_BAN_KINH."""
    try:
        import cv2
        import numpy as np
        a = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
        if a is None:
            return
        h, w = a.shape[:2]
        # 15/10 đo: ảnh 2752x1536 / 2816x1536 (độ phân giải gấp đôi) có dấu ở ~240 px, rộng ~100 px -> co giãn theo cỡ ảnh
        k = max(1, round(max(w, h) / 1400))
        cach, bk = cach_mep * k, ban_kinh * k
        if w < 4 * cach or h < 4 * cach:
            return
        m = np.zeros((h, w), np.uint8)
        cv2.circle(m, (w - cach, h - cach), bk, 255, -1)
        # 23/10 user (ảnh Flow lộ vệt tròn mịn trên nền có hạt): trong vòng đó chỉ tô ĐÚNG HÌNH dấu ✦ (chỗ sáng hơn nền
        # quanh nó) nới 2 px; không thấy hình rõ thì tô cả vòng như cũ
        x0, y0 = max(0, w - cach - bk), max(0, h - cach - bk)
        xam = cv2.cvtColor(a[y0:h - cach + bk, x0:w - cach + bk], cv2.COLOR_BGR2GRAY).astype(np.int16)
        nang = xam - cv2.medianBlur(xam.astype(np.uint8), 2 * bk + 1).astype(np.int16)
        hinh = ((nang > 10) & (m[y0:h - cach + bk, x0:w - cach + bk] > 0)).astype(np.uint8) * 255
        r = 7
        if 0.08 < hinh.mean() / 255 / (np.pi / 4) < 0.8:     # tỉ lệ diện tích hình / diện tích vòng
            hinh = cv2.dilate(hinh, np.ones((5, 5), np.uint8))
            m[:] = 0
            m[y0:h - cach + bk, x0:w - cach + bk] = hinh
            r = 3
        a = cv2.inpaint(a, m, r, cv2.INPAINT_TELEA)
        if r == 3:                                           # chỗ tô mịn hơn nền có hạt -> rắc hạt bằng độ nhám vùng quanh
            o = a[y0:h - cach + bk, x0:w - cach + bk].astype(np.float32)
            mo = m[y0:h - cach + bk, x0:w - cach + bk] > 0
            nham = (o - cv2.GaussianBlur(o, (0, 0), 1.5))[~mo].std()
            o[mo] += np.random.default_rng(0).normal(0, nham, (int(mo.sum()), 1)).astype(np.float32)
            a[y0:h - cach + bk, x0:w - cach + bk] = np.clip(o, 0, 255).astype(np.uint8)
        ok, buf = cv2.imencode(os.path.splitext(f)[1] or ".png", a)
        if ok:
            buf.tofile(f)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! xoá dấu Gemini lỗi: {str(e)[:80]}")


async def _ve(ck, prompt, thu, ten, timeout, tep=None):
    from gemini_webapi import GeminiClient
    cli = GeminiClient(ck.get("__Secure-1PSID"), ck.get("__Secure-1PSIDTS"))
    them = {k: v for k, v in ck.items() if k not in ("__Secure-1PSID", "__Secure-1PSIDTS")}
    if them:
        cli.cookies = them

    async def _bo_qua(*_a, **_k):
        return None
    for ten_ in ("_fetch_usage_info", "_fetch_quota", "_fetch_extra_quota", "_fetch_abuse_status"):
        if hasattr(cli, ten_):                               # 19/10 user: không hỏi lại điểm / hạn mức mỗi lần vẽ
            setattr(cli, ten_, _bo_qua)
    try:
        await cli.init(timeout=timeout, auto_close=False, auto_refresh=False, verbose=False)
        r = await cli.generate_content(prompt, files=list(tep)) if tep else await cli.generate_content(prompt)
        anh = list(getattr(r, "images", None) or [])
        sinh = [a for a in anh if type(a).__name__ == "GeneratedImage"] or anh
        if not sinh:
            return None, (getattr(r, "text", "") or "")[:120]
        f = await sinh[0].save(path=thu, filename=ten, verbose=False)
        if not xoa_logo(f) and XOA_DAU:                      # 19/10: tính ngược logo; không được mới tới cách cũ
            xoa_dau_gemini(f)
        return f, ""
    finally:
        try:
            await cli.close()
        except Exception:                                    # noqa: BLE001
            pass


_P_SOAT = """You are a strict photo editor for a documentary video. This image must illustrate the narration below.
Narration (Vietnamese): "{cau}"
Intended shot: "{ve}"
First LOOK carefully and write down facts, then judge:
  - "thay": what is in the image — each kind of subject with its EXACT count (count animals one by one), where the camera
    is, and for every person: what exactly their gaze / weapon / hands point at (a herd? an animal? empty bushes? sky?);
  - "dat": false if ANY of: the narration's action is not readable at a glance; a person aims or looks at empty scenery
    instead of the subject the narration is about; a posing portrait when the sentence is about the action; a stated
    subject is missing or its count differs from the intended shot; setting / era / clothing contradicts the shot
    (military gear not described counts as wrong); anything absurd or AI-looking (merged or extra limbs, malformed
    animals or hands, floating objects, wrong scale, plastic skin, fake text). Ignore the small star logo in a corner.
  - "loi": the concrete problems in short English (empty if dat).
Reply ONLY JSON: {{"thay": "...", "dat": true or false, "loi": "..."}}"""


async def _hoi_anh(ck, prompt, f, timeout):
    from gemini_webapi import GeminiClient
    cli = GeminiClient(ck.get("__Secure-1PSID"), ck.get("__Secure-1PSIDTS"))
    them = {k: v for k, v in ck.items() if k not in ("__Secure-1PSID", "__Secure-1PSIDTS")}
    if them:
        cli.cookies = them
    try:
        await cli.init(timeout=timeout, auto_close=False, auto_refresh=False, verbose=False)
        r = await cli.generate_content(prompt, files=[f])
        return getattr(r, "text", "") or ""
    finally:
        try:
            await cli.close()
        except Exception:                                    # noqa: BLE001
            pass


def soat(f, cau, ve, timeout=90):
    """19/10 user ("làm sao ảnh không trông ngu"): Gemini XEM ảnh vừa vẽ, chấm theo câu đọc + câu lệnh vẽ.
    Trả (dat, loi). Không hỏi được -> (True, "") (không chặn ảnh)."""
    import json
    import re
    p = _P_SOAT.format(cau=str(cau or "")[:600], ve=str(ve or "")[:900])
    for a in _lan_luot(_xep_tai_khoan()):
        nhan = a.get("label")
        if nhan in _HONG:
            continue
        try:
            with _Giu(nhan):
                t = asyncio.run(asyncio.wait_for(_hoi_anh(a["cookies"], p, f, timeout), timeout + 30))
        except Exception as e:                               # noqa: BLE001
            log(f"    ! soát ảnh (tài khoản {nhan}): {type(e).__name__}: {str(e)[:80]}")
            continue
        m = re.search(r"\{.*\}", t or "", re.S)
        try:
            j = json.loads(m.group(0)) if m else None
        except ValueError:
            j = None
        if isinstance(j, dict):
            return bool(j.get("dat", True)), str(j.get("loi") or "").strip()
    return True, ""


def _qua_flow(prompt, thu, ten):
    """Vẽ qua Google Flow (hồ sơ Chrome riêng, 0 điểm) — 15/10 user: chỉ dùng khi MỌI tài khoản Gemini (cookie) đã hết
    điểm hoặc đều lỗi. Chưa có hồ sơ Flow -> None."""
    try:
        import flow_ve
        if not flow_ve.co_ho_so():
            return None
        if not getattr(_qua_flow, "da_bao", False):
            log("    Gemini (cookie) hết điểm / lỗi hết -> chuyển sang vẽ bằng Flow")
            _qua_flow.da_bao = True
        f = flow_ve.ve(prompt, thu, ten)
        if f:
            log(f"    (Flow) vẽ xong {os.path.basename(f)}")
        return f
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! Flow lỗi: {type(e).__name__}: {str(e)[:120]}")
        return None


def ve_prompt(prompt, thu, ten, tep=None, timeout=150, do_credit=True):
    """Vẽ theo câu lệnh đầy đủ (kèm ảnh mẫu `tep` nếu có) -> đường dẫn ảnh hoặc None; xoay tài khoản khi lỗi."""
    os.makedirs(thu, exist_ok=True)
    for a in _lan_luot(_xep_tai_khoan(do_credit)):
        nhan = a.get("label")
        if nhan in _HONG:
            continue
        try:
            _tru(nhan)
            with _Giu(nhan):
                f, ly = asyncio.run(asyncio.wait_for(_ve(a["cookies"], prompt, thu, ten, timeout, tep), timeout + 30))
        except Exception as e:                               # noqa: BLE001
            log(f"    ! vẽ ảnh (tài khoản {nhan}): {type(e).__name__}: {str(e)[:100]}")
            if _loai_han(e):                                 # 13/10: chỉ loại tài khoản khi lỗi đăng nhập / hết lượt;
                _HONG.add(nhan)                              # mất kết nối tạm thời thì để lần sau dùng lại
            continue
        if f and os.path.isfile(f):
            if os.path.getsize(f) > 4000:
                return f
            try:
                os.remove(f)
            except OSError:
                pass
        log(f"    ! vẽ ảnh (tài khoản {nhan}): không trả ảnh hợp lệ ({ly})")
        if _KHONG_VE_DUOC.search(str(ly or "")):              # tài khoản không được vẽ -> bỏ hẳn trong lượt này
            _HONG.add(nhan)
    # 15/10 user: Gemini (cookie) TRƯỚC; chỉ khi mọi tài khoản Gemini hết điểm / lỗi mới chuyển sang Flow
    return _qua_flow(prompt, thu, ten)


def ve(mo_ta, thu, ten, timeout=120):
    """mo_ta: mô tả tiếng Anh vật cần vẽ -> đường dẫn ảnh đã lưu (nền trắng) hoặc None."""
    prompt = (f"Generate an image of {mo_ta}. ULTRA-PHOTOREALISTIC: every element must look like a REAL PHOTOGRAPH taken with a professional camera — real textures, natural light, true-to-life colours and proportions. NOT an illustration, NOT a drawing, NOT a sketch, NOT a painting, NOT cartoon, NOT anime, NOT clay or 3D-render look. (Only microscopic or abstract things may be a "
              f"realistic scientific render.) ONE single COMPLETE subject (all parts present, nothing cut "
              f"off by the image border), centered with white margin around it, isolated on a plain pure white background, "
              f"no background scene, NOTHING under it (no rock, slab, pedestal, platform, base or ground) unless the "
              f"subject itself is a flat thing. No text, no letters, no numbers, no labels, no arrows, no border, no frame; "
              f"any screen or display must be blank.")
    os.makedirs(thu, exist_ok=True)
    for a in _lan_luot(_xep_tai_khoan()):
        nhan = a.get("label")
        if nhan in _HONG:
            continue
        try:
            _tru(nhan)
            with _Giu(nhan):
                f, ly = asyncio.run(asyncio.wait_for(_ve(a["cookies"], prompt, thu, ten, timeout), timeout + 30))
        except Exception as e:                               # noqa: BLE001
            log(f"    ! vẽ ảnh (tài khoản {nhan}): {type(e).__name__}: {str(e)[:100]}")
            if _loai_han(e):                                 # 13/10: chỉ loại tài khoản khi lỗi đăng nhập / hết lượt;
                _HONG.add(nhan)                              # mất kết nối tạm thời thì để lần sau dùng lại
            continue
        if f and os.path.isfile(f):
            return f
        log(f"    ! vẽ ảnh (tài khoản {nhan}): không trả ảnh ({ly})")
        if _KHONG_VE_DUOC.search(str(ly or "")):
            _HONG.add(nhan)
    # 15/10 user: Gemini (cookie) TRƯỚC; chỉ khi mọi tài khoản Gemini hết điểm / lỗi mới chuyển sang Flow
    return _qua_flow(prompt, thu, ten)
