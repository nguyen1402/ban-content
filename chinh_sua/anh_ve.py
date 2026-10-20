# -*- coding: utf-8 -*-
"""VẼ ẢNH MINH HOẠ bằng Gemini web (Nano Banana) qua COOKIE (13/10 user: thứ trừu tượng / không có ảnh thật cụ thể —
vi khuẩn, enzyme, chuỗi phân tử, dòng tiền… — nhờ AI vẽ cho khớp lời).

Không khoá API: dùng kho cookie Gemini RIÊNG của bán-content %LOCALAPPDATA%\\BanContent\\gemini_cookies.json (CHỈ tài khoản đã đặt tên),
thư viện gemini_webapi. Ảnh vẽ trên NỀN TRẮNG trơn để tách nền sạch (dấu nhỏ ở góc của Gemini nằm ở nền -> mất khi tách).
Xoay tài khoản khi một tài khoản lỗi / hết lượt."""
import asyncio
import json
import os
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
            ds = [a for a in ds if _CON.get(a["label"]) is None or _CON[a["label"]] >= 2 * CREDIT_MOI_ANH]
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
        ds = [a for a in ds if _CON.get(a["label"]) is None or _CON[a["label"]] >= 2 * CREDIT_MOI_ANH]
        return sorted(ds, key=lambda a: -(_CON.get(a["label"]) if _CON.get(a["label"]) is not None else -1))


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
    return False


# 19/10 user: phong cách CỐ ĐỊNH cho MỌI ảnh chụp AI ("Phong cách ảnh chụp thật, ống kính 50mm, khẩu độ F1.8, nền mờ nhẹ.
# Ánh sáng tự nhiên ban ngày, cân bằng trắng khoảng 5500K, không ám vàng, không lệch màu. Xóa hết chi tiết thừa, bóng đổ
# mềm, tự nhiên, màu điềm đạm, không quá rực.")
PHONG_CACH = ("Style: a REAL photograph, 50mm lens, aperture f/1.8, softly blurred background. Natural daylight, white "
              "balance about 5500K, no yellow cast, no colour shift. Remove all unnecessary clutter, soft natural shadows, "
              "calm muted colours, not oversaturated.")


def phong_cach(thoi_dai=""):
    """Đuôi câu lệnh vẽ: thời đại của cảnh (trang phục, xe cộ, đồ vật, tông màu đúng thời ấy) + PHONG_CACH."""
    td = str(thoi_dai or "").strip()
    return ((f"Period: the scene takes place in {td} — clothing, hairstyles, vehicles, equipment, buildings and the colour "
             f"palette must match real photographs of that period (white balance stays neutral). ") if td else "") + PHONG_CACH


def xoa_dau_gemini(f):
    """14/10 user "logo gemini kia bỏ đi": tô lấp (inpaint) đúng chỗ dấu ✦ ở góc phải dưới ngay khi ảnh về — trên nền
    trắng thành trắng, đè lên nội dung thì lấp theo vùng quanh (vết rất nhỏ). Lỗi đọc/ghi: để nguyên ảnh."""
    try:
        import cv2
        import numpy as np
        a = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
        if a is None:
            return
        h, w = a.shape[:2]
        # 15/10 đo: ảnh 2752x1536 / 2816x1536 (độ phân giải gấp đôi) có dấu ở ~240 px, rộng ~100 px -> co giãn theo cỡ ảnh
        k = max(1, round(max(w, h) / 1400))
        cach, bk = DAU_CACH_MEP * k, DAU_BAN_KINH * k
        if w < 4 * cach or h < 4 * cach:
            return
        m = np.zeros((h, w), np.uint8)
        cv2.circle(m, (w - cach, h - cach), bk, 255, -1)
        a = cv2.inpaint(a, m, 7, cv2.INPAINT_TELEA)
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
    for a in _xep_tai_khoan():
        nhan = a.get("label")
        if nhan in _HONG:
            continue
        try:
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
    for a in _xep_tai_khoan(do_credit):
        nhan = a.get("label")
        if nhan in _HONG:
            continue
        try:
            _tru(nhan)
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
    for a in _xep_tai_khoan():
        nhan = a.get("label")
        if nhan in _HONG:
            continue
        try:
            _tru(nhan)
            f, ly = asyncio.run(asyncio.wait_for(_ve(a["cookies"], prompt, thu, ten, timeout), timeout + 30))
        except Exception as e:                               # noqa: BLE001
            log(f"    ! vẽ ảnh (tài khoản {nhan}): {type(e).__name__}: {str(e)[:100]}")
            if _loai_han(e):                                 # 13/10: chỉ loại tài khoản khi lỗi đăng nhập / hết lượt;
                _HONG.add(nhan)                              # mất kết nối tạm thời thì để lần sau dùng lại
            continue
        if f and os.path.isfile(f):
            return f
        log(f"    ! vẽ ảnh (tài khoản {nhan}): không trả ảnh ({ly})")
    # 15/10 user: Gemini (cookie) TRƯỚC; chỉ khi mọi tài khoản Gemini hết điểm / lỗi mới chuyển sang Flow
    return _qua_flow(prompt, thu, ten)
