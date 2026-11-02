# -*- coding: utf-8 -*-
"""HỎI CHATGPT QUA CHROME THẬT — 30/10/2026 user: một số tài khoản bị hạn chế Gemini (myaccount.google.com/restrictions)
-> hỗ trợ dùng ChatGPT bằng giao diện trình duyệt Chrome thật và gọi tự động qua Chrome CDP.

Dùng chung kho hồ sơ Chrome với Flow & Gemini (flow_ve: ~/BanContent/flow_chrome/<hồ sơ>, cổng DevTools 9350+):
  1. Người dùng bấm "💬 Mở ChatGPT" trên giao diện hồ sơ để đăng nhập ChatGPT một lần trên profile đó.
  2. Khi gọi AI: mở tab https://chatgpt.com (nền), nhập prompt vào #prompt-textarea, bấm gửi hoặc phím Enter,
     chờ nút Stop biến mất và chữ trả lời hoàn tất, đọc chữ trả lời từ [data-message-author-role="assistant"].
  3. Cổng kết nối và cơ chế đóng êm tương thích hoàn toàn với flow_ve & gemini_chrome.
"""
import atexit
import json
import os
import re
import subprocess
import threading
import time
import urllib.request

from common import log

TRANG = "https://chatgpt.com/"
CHO = 300                    # giây chờ một câu trả lời
MOI_HO_SO = 1                # mỗi hồ sơ một câu cùng lúc
CHO_PHAN_HOI = 60            # giây: gửi xong mà chưa có chữ nào = treo
CHO_DUNG = 60                # giây: đang viết mà chữ đứng im = treo
NGHI = {}                    # hồ sơ -> nghỉ tới (đăng xuất / lỗi)
_DANG = {}                   # hồ sơ -> số câu đang hỏi
_KHOA = threading.Lock()
_KHOA_MO = threading.Lock()

_TU_MO = set()
DONG_SAU = 20
TU_MO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "chatgpt_tu_mo.json")
_KHOA_TU_MO = threading.Lock()
_TRONG_TU = {}

DUNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "chatgpt_dung.json")
DUNG_GIU = 12 * 3600
HONG_GIU = 6 * 3600
_CAU_THU = "Reply with exactly one word: OK"
_KHOA_DUNG = threading.Lock()
_KHOA_THU = {}


class KhongTaoChat(RuntimeError):
    """Hồ sơ mở được ChatGPT nhưng không gửi được tin (không có ô nhập / nút gửi)."""


def _ds_tu_mo():
    from common import doc_json
    return {int(k): v for k, v in (doc_json(TU_MO_FILE, {}) or {}).items()}


def _dat_tu_mo(cong, co):
    from common import ghi_json
    with _KHOA_TU_MO:
        d = _ds_tu_mo()
        if co:
            d[int(cong)] = time.time()
        else:
            d.pop(int(cong), None)
        os.makedirs(os.path.dirname(TU_MO_FILE), exist_ok=True)
        ghi_json(TU_MO_FILE, {str(k): v for k, v in d.items()})
    (_TU_MO.add if co else _TU_MO.discard)(cong)


def _ho_so():
    import flow_ve
    ds = list(flow_ve._doc_so())                               # noqa: SLF001
    return [(t, flow_ve.CONG_DAU + i % 40) for i, t in enumerate(ds)]


def co_ho_so():
    return bool(_ho_so())


def _json(cong, duong="/json"):
    req = urllib.request.Request(f"http://127.0.0.1:{cong}{duong}", headers={"User-Agent": "BanContent"})
    return json.load(urllib.request.urlopen(req, timeout=5))


def _ranh(cong):
    try:
        trang = [t for t in _json(cong) if t.get("type") == "page"]
    except OSError:
        return None
    return all(t.get("url", "").startswith(("about:blank", "chrome://newtab")) for t in trang)


def _dong(cong, ly_do):
    import flow_ve
    ten = next((t for t, c in _ho_so() if c == cong), cong)
    _dat_tu_mo(cong, False)
    flow_ve.dong_em(cong)
    log(f"    ChatGPT Chrome '{ten}': {ly_do} — đã đóng Chrome")


def _dong_khi_thoat():
    for cong in list(_TU_MO):
        try:
            for _ in range(10):
                r = _ranh(cong)
                if r is not False:
                    break
                time.sleep(0.5)
            if r:
                _dong(cong, "tiến trình xong việc")
        except Exception as e:                               # noqa: BLE001
            log(f"    (đóng Chrome ChatGPT khi thoát lỗi: {str(e)[:100]})")


atexit.register(_dong_khi_thoat)


def _doc_dung():
    from common import doc_json
    return doc_json(DUNG, {}) or {}


def _ghi_dung(ten, ok, msg=""):
    from common import ghi_json
    with _KHOA_DUNG:
        d = _doc_dung()
        d[ten] = {"ok": bool(ok), "luc": time.time(), "msg": str(msg or "")[:200]}
        os.makedirs(os.path.dirname(DUNG), exist_ok=True)
        ghi_json(DUNG, d)


def dung_duoc(ten):
    m = _doc_dung().get(ten) or {}
    tuoi = time.time() - float(m.get("luc") or 0)
    if m.get("ok") and tuoi < DUNG_GIU:
        return True
    if m and not m.get("ok") and tuoi < HONG_GIU:
        return False
    return None


def _san(ten):
    return NGHI.get(ten, 0) < time.time() and dung_duoc(ten) is not False


def _mo_chrome(ten, cong):
    with _KHOA_MO:
        try:
            _json(cong)
            return True
        except OSError:
            pass
        import flow_ve
        thu = os.path.join(flow_ve.GOC, flow_ve._slug(ten))           # noqa: SLF001
        if not os.path.isdir(thu):
            return False
        flow_ve.mo_chrome_tach([flow_ve._chrome(), f"--user-data-dir={thu}", f"--remote-debugging-port={cong}",   # noqa: SLF001
                          "--no-first-run", "--no-default-browser-check", "--window-position=80,60",
                          "--window-size=1280,860", "--disable-backgrounding-occluded-windows",
                          "--disable-renderer-backgrounding", "--disable-background-timer-throttling", "about:blank"], thu)
        for _ in range(40):
            time.sleep(0.5)
            try:
                _json(cong)
            except OSError:
                continue
            log(f"    ChatGPT Chrome: mở hồ sơ '{ten}' (thu nhỏ — bấm trên thanh tác vụ để xem)")
            _dat_tu_mo(cong, True)
            _cua_so(cong, "minimized")
            return True
        return False


def _cua_so(cong, dat=None):
    from anh_google import _WS
    try:
        trang = [t for t in _json(cong) if t.get("type") == "page"]
        if not trang:
            return ""
        w = _WS(_json(cong, "/version")["webSocketDebuggerUrl"])
        try:
            wid = w.goi("Browser.getWindowForTarget", targetId=trang[0]["id"])["windowId"]
            if dat:
                w.goi("Browser.setWindowBounds", windowId=wid, bounds={"windowState": dat})
                return dat
            return w.goi("Browser.getWindowBounds", windowId=wid)["bounds"].get("windowState", "")
        finally:
            w.dong()
    except Exception:                                        # noqa: BLE001
        return ""


def _hen_dong(cong):
    if cong in _TU_MO:
        t = threading.Timer(DONG_SAU, _dong_neu_ranh, (cong,))
        t.daemon = True
        t.start()


def _dong_neu_ranh(cong):
    with _KHOA:
        if cong not in _TU_MO:
            return
        ten = next((t for t, c in _ho_so() if c == cong), None)
        if ten and _DANG.get(ten):
            return
        r = _ranh(cong)
        if r is None:
            _dat_tu_mo(cong, False)
            return
        if not r:
            return
    _dong(cong, "hỏi xong")


def _cho(ws, bieu_thuc, giay, buoc=0.5):
    han = time.time() + giay
    while time.time() < han:
        try:
            v = ws.js(bieu_thuc)
            if v:
                return v
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(buoc)
    return None


_JS_TIM_O_NHAP = """(() => {
    const el = document.querySelector('#prompt-textarea') ||
               document.querySelector('div[contenteditable=true]#prompt-textarea') ||
               document.querySelector('textarea[data-id=root]') ||
               document.querySelector('form textarea');
    return !!el;
})()"""


def _kiem_tra_trang_chatgpt(ws):
    """Kiểm tra xem trang ChatGPT có đòi đăng nhập hoặc gặp Cloudflare / lỗi không."""
    try:
        href = str(ws.js("location.href") or "")
        if "/auth/login" in href:
            return "chưa đăng nhập ChatGPT (trang login)"
        body = str(ws.js("(document.body && document.body.innerText) || ''") or "")
        if "cf-turnstile" in body or "Checking your browser" in body or "challenge-running" in body:
            return "yêu cầu xác minh Cloudflare / Turnstile"
        if ws.js("!!document.querySelector('button[data-testid=login-button], a[href*=\"/auth/login\"]') && !document.querySelector('#prompt-textarea')"):
            return "chưa đăng nhập ChatGPT"
    except Exception:
        pass
    return None


def _cho_o_nhap(ten, ws):
    """Chờ ô nhập của ChatGPT. Chưa đăng nhập -> PermissionError; không có ô nhập -> KhongTaoChat."""
    han = time.time() + 45
    while time.time() < han:
        try:
            if ws.js(_JS_TIM_O_NHAP):
                return
        except Exception:
            pass
        loi = _kiem_tra_trang_chatgpt(ws)
        if loi:
            if "chưa đăng nhập" in loi:
                NGHI[ten] = time.time() + 6 * 3600
                _ghi_dung(ten, False, loi)
                try:
                    import flow_ve
                    flow_ve._cap_nhat(ten, chatgpt_loi=loi)
                except Exception:
                    pass
                raise PermissionError("hồ sơ chưa đăng nhập ChatGPT — bấm 'Mở ChatGPT' trên giao diện để đăng nhập")
            if "Cloudflare" in loi:
                raise RuntimeError("ChatGPT yêu cầu giải Turnstile — bấm 'Mở ChatGPT' trên giao diện để thao tác")
        time.sleep(1)

    trang = " ".join(str(ws.js("(document.body && document.body.innerText) || ''") or "").split())[:140]
    raise KhongTaoChat("ChatGPT không hiện ô nhập" + (f" (trang: {trang})" if trang else ""))


_JS_GUI = """((txt) => {
    const el = document.querySelector('#prompt-textarea') ||
               document.querySelector('div[contenteditable=true]#prompt-textarea') ||
               document.querySelector('form textarea');
    if (!el) return false;
    el.focus();
    if (el.tagName === 'TEXTAREA') {
        el.value = txt;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
    } else {
        el.innerText = txt;
        el.dispatchEvent(new InputEvent('input', {bubbles: true}));
    }
    return true;
})"""


def _gui_cau(ws, prompt):
    """Gõ câu vào ô nhập ChatGPT và bấm nút gửi hoặc phím Enter."""
    ws.js("document.querySelectorAll('[data-message-author-role=assistant]').forEach(e => e.dataset.bcCu = '1')")
    ws.js(f"({_JS_GUI})({json.dumps(prompt)})")
    time.sleep(0.4)

    # Thử bấm nút gửi bằng chuột thật hoặc JS
    gui_duoc = ws.js("""(() => {
        const b = document.querySelector('button[data-testid="send-button"]') ||
                  document.querySelector('button[aria-label*="Send"]') ||
                  document.querySelector('button[data-testid*="send"]');
        if (b && !b.disabled) { b.click(); return true; }
        return false;
    })()""")

    if not gui_duoc:
        # Nhấn phím Enter qua CDP
        ws.goi("Input.dispatchKeyEvent", type="rawKeyDown", windowsVirtualKeyCode=13, text="\r", unmodifiedText="\r")
        ws.goi("Input.dispatchKeyEvent", type="keyUp", windowsVirtualKeyCode=13)
        time.sleep(0.5)


_JS_DOC_MOI = """(() => {
    const stop = !!(document.querySelector('button[data-testid="stop-button"]') ||
                    document.querySelector('button[aria-label*="Stop"]'));
    const msgs = [...document.querySelectorAll('[data-message-author-role="assistant"]:not([data-bc-cu])')];
    if (!msgs.length) {
        const allAss = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
        if (allAss.length) {
            const last = allAss[allAss.length - 1];
            const p = last.querySelector('.markdown, .prose') || last;
            return JSON.stringify({stop: stop, n: 1, txt: (p.innerText || '').trim()});
        }
        return JSON.stringify({stop: stop, n: 0, txt: ''});
    }
    const last = msgs[msgs.length - 1];
    const prose = last.querySelector('.markdown, .prose') || last;
    return JSON.stringify({stop: stop, n: msgs.length, txt: (prose.innerText || '').trim()});
})()"""


def _cho_tra_loi(ws, han, cho_phan_hoi=CHO_PHAN_HOI, cho_dung=CHO_DUNG):
    """Chờ ChatGPT viết xong câu trả lời mới."""
    t0 = time.time()
    cu, doi, mat = None, t0, 0
    while time.time() < han:
        time.sleep(2)
        try:
            d = json.loads(ws.js(_JS_DOC_MOI) or "{}")
            mat = 0
        except Exception as e:                               # noqa: BLE001
            mat += 1
            if mat >= 3:
                raise RuntimeError(f"mất kết nối tab ChatGPT (Chrome bị tắt?): {str(e)[:60]}") from e
            continue
        txt = (d.get("txt") or "").strip()
        if txt != cu:
            doi = time.time()
        if not txt and time.time() - t0 > cho_phan_hoi:
            return None
        if txt and d.get("stop") and time.time() - doi > cho_dung:
            return None
        if txt and not d.get("stop") and txt == cu and time.time() - doi >= 2.0:
            return txt
        cu = txt
    return None


def _hoi_tab(ten, cong, prompt, timeout):
    """Mở tab mới trên Chrome hồ sơ để hỏi ChatGPT một câu và đóng tab khi xong."""
    from anh_google import _WS
    trinh = _WS(_json(cong, "/version")["webSocketDebuggerUrl"])
    try:
        tid = trinh.goi("Target.createTarget", url=TRANG, background=True)["targetId"]
    finally:
        trinh.dong()
    tab = next((t for t in _json(cong) if t.get("id") == tid), None)
    if not tab:
        raise RuntimeError("không mở được tab ChatGPT")
    ws = None
    try:
        ws = _WS(tab["webSocketDebuggerUrl"])
        try:
            ws.goi("Emulation.setFocusEmulationEnabled", enabled=True)
        except Exception:
            pass
        _cho_o_nhap(ten, ws)
        _gui_cau(ws, prompt)
        han = time.time() + timeout
        txt = _cho_tra_loi(ws, han)
        if not txt:
            raise TimeoutError(f"quá hạn {timeout}s chờ ChatGPT trả lời")
        return txt
    finally:
        if ws:
            ws.dong()
        try:
            _json(cong, "/close/" + tab["id"])
        except Exception:
            pass
        _hen_dong(cong)


def _giu(tranh=()):
    with _KHOA:
        ds = [(t in tranh, not _ranh(c) is not None, _DANG.get(t, 0), t, c) for t, c in _ho_so()
              if _san(t) and _DANG.get(t, 0) < MOI_HO_SO]
        if not ds:
            return None
        *_, t, c = min(ds)
        _DANG[t] = _DANG.get(t, 0) + 1
        return t, c


def _tha(ten):
    with _KHOA:
        _DANG[ten] = max(0, _DANG.get(ten, 1) - 1)


def kiem_tai_khoan(ten, cong, lam_moi=False):
    """Kiểm tra hồ sơ có dùng được ChatGPT không -> (ok, msg)."""
    with _KHOA:
        khoa = _KHOA_THU.setdefault(ten, threading.Lock())
    with khoa:
        m = _doc_dung().get(ten) or {}
        if not lam_moi and dung_duoc(ten) is not None:
            return bool(m.get("ok")), m.get("msg") or ""
        try:
            if not _mo_chrome(ten, cong):
                raise RuntimeError("không mở được Chrome của hồ sơ")
            kq = _hoi_tab(ten, cong, _CAU_THU, 90)
            ok, msg = bool(kq and kq.strip()), "ChatGPT sẵn sàng và phản hồi tốt"
        except Exception as e:                               # noqa: BLE001
            ok, msg = False, "không dùng được ChatGPT: " + str(e)[:150]
        _ghi_dung(ten, ok, msg)
        log(f"    ChatGPT Chrome '{ten}': {'dùng được' if ok else msg}")
        return ok, msg


def hoi(prompt, timeout=CHO, so_lan=3):
    """Hỏi ChatGPT qua Chrome thật -> text kết quả ('' nếu hỏng)."""
    da_thu = set()
    for _ in range(so_lan):
        g, han = None, time.time() + timeout
        while g is None and time.time() < han and co_ho_so():
            g = _giu(da_thu)
            if g is None:
                time.sleep(1)
        if g is None:
            return ""
        ten, cong = g
        da_thu.add(ten)
        try:
            if not _mo_chrome(ten, cong):
                raise RuntimeError("không mở được Chrome của hồ sơ")
            t0 = time.time()
            kq = _hoi_tab(ten, cong, prompt, timeout)
            log(f"    ChatGPT Chrome '{ten}': trả lời sau {time.time() - t0:.0f}s ({len(kq)} ký tự)")
            _ghi_dung(ten, True, "câu hỏi gần nhất trả lời được")
            return kq
        except Exception as e:                               # noqa: BLE001
            _ghi_dung(ten, False, str(e)[:150])
            log(f"    (ChatGPT Chrome '{ten}' lỗi: {str(e)[:120]} → thử hồ sơ khác)")
        finally:
            _tha(ten)
    return ""


def hoi_nhieu(prompts, timeout=CHO, on_xong=None):
    from concurrent.futures import ThreadPoolExecutor
    ra = [""] * len(prompts)
    if not prompts:
        return ra

    def lam(i):
        ra[i] = hoi(prompts[i], timeout, so_lan=2)
        if on_xong and ra[i]:
            on_xong(i, ra[i])

    so = max(1, min(len(prompts), sum(1 for t, _ in _ho_so() if _san(t)) * MOI_HO_SO))
    with ThreadPoolExecutor(so) as ex:
        list(ex.map(lam, range(len(prompts))))
    return ra

