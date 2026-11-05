# -*- coding: utf-8 -*-
"""Hỏi DeepSeek (chat.deepseek.com, chế độ DeepThink) qua các hồ sơ Chrome của dự án (cache flow_chrome/acc*, cùng cửa
sổ với Gemini / Flow — mỗi câu hỏi một tab mới, hỏi xong đóng tab).

04/11 user: Gemini Pro không có, chỉ Flash bản free; DeepSeek bản suy nghĩ dùng miễn phí và "không thấy có giới hạn gì".
Thử câu 30 lopxe cùng câu lệnh thiết kế: Gemini Flash 3 nhịp / 3 ảnh, DeepSeek 6 nhịp / 7 ảnh, chuyển động đa dạng, 54 s.
Dùng cho khâu thiết kế + viết code cảnh 🎞 Remotion (nhan_y_ai); hỏng thì bên gọi lùi về common.hoi_llm (Gemini)."""
import threading
import time

from common import log

TRANG = "https://chat.deepseek.com/"
CHO = 420                    # giây chờ một câu trả lời (DeepThink nghĩ lâu với câu lệnh dài / viết code)
CHO_PHAN_HOI = 90            # gửi xong mà chưa có chữ trả lời = treo -> thử hồ sơ khác
DUNG_YEN = 8                 # chữ đứng yên bấy nhiêu giây (và không còn nút dừng) = trả lời xong
_DANG = {}                   # hồ sơ -> đang hỏi
_HONG = {}                   # hồ sơ -> hỏng tới (không mở được / chưa đăng nhập)
_KHOA = threading.Lock()
XANH = "rgb(57, 100, 254)"   # nút DeepThink / Search đang BẬT thì chữ màu này

# câu trả lời cuối -> markdown (khối code giữ ``` để nhan_y_ai._tach_tra_loi tách được)
_DOC = r"""(() => {
  const m = [...document.querySelectorAll('.ds-markdown')];
  if (!m.length) return '';
  const e = m[m.length - 1].cloneNode(true);
  e.querySelectorAll('pre').forEach(p => {
    // khối code của DeepSeek = khung gồm thanh đầu ("jsx" + Copy + Download) và <pre>: thay CẢ khung bằng ```ngôn ngữ
    let w = p;
    while (w.parentElement && w.parentElement !== e && w.parentElement.querySelectorAll('pre').length === 1) w = w.parentElement;
    const code = (p.querySelector('code') || p).textContent.replace(/\n$/, '');
    const dau = (w.textContent || '').replace(code, '').trim().toLowerCase();
    const lang = /^json/.test(dau) ? 'json' : /^(jsx|javascript|js|tsx|typescript|react)/.test(dau) ? 'jsx' : '';
    w.replaceWith(document.createTextNode('\n```' + lang + '\n' + code + '\n```\n'));
  });
  return e.innerText;
})()"""
_DANG_VIET = r"""(() => [...document.querySelectorAll('div[role=button], button')].some(b =>
  /stop|dừng/i.test(b.getAttribute('aria-label') || '') ) || !!document.querySelector('[class*=stop], [class*=Stop]'))()"""


def _ho_so():
    import gemini_chrome
    import flow_ve
    return [(t, c) for t, c in gemini_chrome.tat_ca() if _HONG.get(t, 0) < time.time() and flow_ve.duoc_dung(t, "deepseek")]


def co():
    return bool(_ho_so())


def _giu():
    with _KHOA:
        ds = sorted(_ho_so(), key=lambda x: _DANG.get(x[0], 0))
        for t, c in ds:
            if not _DANG.get(t):
                _DANG[t] = 1
                return t, c
    return None


def _tha(t):
    with _KHOA:
        _DANG[t] = 0


def _cho(ws, bt, giay):
    han = time.time() + giay
    while time.time() < han:
        try:
            v = ws.js(bt)
            if v:
                return v
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.5)
    return None


def _mot_lan(ten, cong, prompt, cho):
    import os
    import flow_ve
    import gemini_chrome as g
    from anh_google import _WS
    try:
        g._json(cong)                                        # noqa: SLF001  (đã mở có cổng)
    except OSError:
        # Chrome của hồ sơ đang mở THƯỜNG (user tự mở để đăng nhập — có 'lockfile', không cổng): bỏ qua ngay, khỏi chờ 20 s
        if os.path.exists(os.path.join(flow_ve.GOC, flow_ve._slug(ten), "lockfile")):   # noqa: SLF001
            raise ConnectionError("hồ sơ đang mở ở chế độ thường (không có cổng điều khiển)") from None
    if not g._mo_chrome(ten, cong):                          # noqa: SLF001  (hồ sơ đang mở thường, không cổng)
        raise ConnectionError("không mở được Chrome có cổng điều khiển (hồ sơ đang mở ở chế độ thường?)")
    tab = g._json(cong, "/new?" + TRANG, put=True)           # noqa: SLF001
    ws = _WS(tab["webSocketDebuggerUrl"])
    try:
        ws.goi("Runtime.enable")
        if not _cho(ws, "!!document.querySelector('textarea')", 45):
            raise PermissionError("không thấy ô chat DeepSeek (chưa đăng nhập?)")
        time.sleep(1.2)
        ws.js(f"""(() => {{ for (const s of [...document.querySelectorAll('span')].filter(e =>
            /^(DeepThink|Search)$/.test(e.textContent.trim()) && e.offsetParent)) {{
            const bat = getComputedStyle(s).color === '{XANH}', can = s.textContent.trim() === 'DeepThink';
            if (bat !== can) (s.closest('[role=button],button,div[tabindex]') || s.parentElement).click(); }} }})()""")
        time.sleep(0.6)
        ws.js("document.querySelector('textarea').focus()")
        ws.goi("Input.insertText", text=prompt)
        time.sleep(0.6)
        ws.goi("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13, text="\r")
        ws.goi("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter", windowsVirtualKeyCode=13)
        t0 = time.time()
        if not _cho(ws, "document.querySelectorAll('.ds-markdown').length > 0 || document.body.innerText.length > 0 && "
                        "location.href.includes('/chat/s/')", CHO_PHAN_HOI):
            raise TimeoutError("gửi xong mà DeepSeek không phản hồi")
        cu, yen = "", 0.0
        while time.time() - t0 < cho:
            time.sleep(2)
            try:
                t = ws.js(_DOC) or ""
                viet = ws.js(_DANG_VIET)
            except Exception:                                # noqa: BLE001
                continue
            if t and t == cu and not viet:
                yen += 2
                if yen >= DUNG_YEN:
                    return t
            else:
                cu, yen = t, 0.0
        if cu:
            return cu
        raise TimeoutError("hết giờ chờ DeepSeek")
    finally:
        try:
            g._json(cong, f"/close/{tab['id']}")              # noqa: SLF001
        except Exception:                                    # noqa: BLE001
            pass
        ws.dong()
        g._hen_dong(cong)                                    # noqa: SLF001  (Chrome tự mở: rảnh thì tự đóng)


CHO_HANG = 25 * 60           # 05/11: tối đa chờ XẾP HÀNG (mọi hồ sơ DeepSeek đang bận) — không tính vào giờ trả lời


def hoi(prompt, timeout=CHO, cho_hang=CHO_HANG):
    """Một câu hỏi DeepThink -> câu trả lời (markdown) | '' (mọi hồ sơ hỏng / bận quá lâu). Hồ sơ hỏng -> thử hồ sơ khác.
    05/11 user ("chờ deepseek quá hạn xong lùi về gemini"): trước đây một hạn chung tính CẢ lúc xếp hàng chờ hồ sơ rảnh
    (9 cảnh cùng lúc, ít hồ sơ) -> tới lượt thì hết giờ. Nay: giờ trả lời (timeout) tính từ lúc GỬI, xếp hàng có hạn riêng."""
    han_hang = time.time() + cho_hang
    da = set()
    while True:
        x = _giu()
        if not x:
            if time.time() > han_hang or not _ho_so():
                break
            time.sleep(2)                                   # mọi hồ sơ đang hỏi: chờ chỗ trống
            continue
        ten, cong = x
        if ten in da and len(da) < len(_ho_so()):
            _tha(ten)                                       # hồ sơ vừa hỏng: chờ hồ sơ khác rảnh
            if time.time() > han_hang:
                break
            time.sleep(2)
            continue
        han_hang = time.time() + cho_hang                    # có hồ sơ rồi: lần thử sau (nếu hỏng) lại được chờ đủ
        da.add(ten)
        try:
            t = _mot_lan(ten, cong, prompt, timeout)
            if t:
                return t
        except (ConnectionError, PermissionError) as e:
            log(f"    DeepSeek '{ten}': {str(e)[:120]} — bỏ hồ sơ này 30 phút")
            _HONG[ten] = time.time() + 1800
        except Exception as e:                               # noqa: BLE001
            log(f"    DeepSeek '{ten}': {type(e).__name__}: {str(e)[:120]}")
        finally:
            _tha(ten)
        if len(da) >= max(1, len(_ho_so())):
            break
    return ""
