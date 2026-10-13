# -*- coding: utf-8 -*-
"""VẼ ẢNH MINH HOẠ bằng Gemini web (Nano Banana) qua COOKIE (13/10 user: thứ trừu tượng / không có ảnh thật cụ thể —
vi khuẩn, enzyme, chuỗi phân tử, dòng tiền… — nhờ AI vẽ cho khớp lời).

Không khoá API: dùng kho cookie Gemini chung %LOCALAPPDATA%\\CapCutTTS\\gemini_cookies.json (CHỈ tài khoản đã đặt tên),
thư viện gemini_webapi. Ảnh vẽ trên NỀN TRẮNG trơn để tách nền sạch (dấu nhỏ ở góc của Gemini nằm ở nền -> mất khi tách).
Xoay tài khoản khi một tài khoản lỗi / hết lượt."""
import asyncio
import json
import os

from common import log

KHO = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CapCutTTS", "gemini_cookies.json")
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


def _xep_tai_khoan():
    """13/10 user: ưu tiên tài khoản còn NHIỀU credit nhất. Đo một lần mỗi lượt chạy, sau đó trừ dần theo ảnh đã vẽ;
    tài khoản không báo số xếp cuối; còn < 2 ảnh thì bỏ."""
    ds = _tai_khoan()
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


async def _ve(ck, prompt, thu, ten, timeout, tep=None):
    from gemini_webapi import GeminiClient
    cli = GeminiClient(ck.get("__Secure-1PSID"), ck.get("__Secure-1PSIDTS"))
    them = {k: v for k, v in ck.items() if k not in ("__Secure-1PSID", "__Secure-1PSIDTS")}
    if them:
        cli.cookies = them
    try:
        await cli.init(timeout=timeout, auto_close=False, auto_refresh=False, verbose=False)
        r = await cli.generate_content(prompt, files=list(tep)) if tep else await cli.generate_content(prompt)
        anh = list(getattr(r, "images", None) or [])
        sinh = [a for a in anh if type(a).__name__ == "GeneratedImage"] or anh
        if not sinh:
            return None, (getattr(r, "text", "") or "")[:120]
        f = await sinh[0].save(path=thu, filename=ten, verbose=False)
        return f, ""
    finally:
        try:
            await cli.close()
        except Exception:                                    # noqa: BLE001
            pass


def ve_prompt(prompt, thu, ten, tep=None, timeout=150):
    """Vẽ theo câu lệnh đầy đủ (kèm ảnh mẫu `tep` nếu có) -> đường dẫn ảnh hoặc None; xoay tài khoản khi lỗi."""
    os.makedirs(thu, exist_ok=True)
    for a in _xep_tai_khoan():
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
            return f
        log(f"    ! vẽ ảnh (tài khoản {nhan}): không trả ảnh ({ly})")
    return None


def ve(mo_ta, thu, ten, timeout=120):
    """mo_ta: mô tả tiếng Anh vật cần vẽ -> đường dẫn ảnh đã lưu (nền trắng) hoặc None."""
    prompt = (f"Generate an image of {mo_ta}. Realistic, highly detailed (photorealistic, or a realistic 3D scientific "
              f"render for microscopic or abstract things). ONE single subject, centered, fully visible, isolated on a "
              f"plain pure white background. No text, no letters, no numbers, no labels, no arrows, no border, no frame; "
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
    return None
