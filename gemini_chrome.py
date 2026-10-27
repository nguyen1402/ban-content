# -*- coding: utf-8 -*-
"""HỎI GEMINI QUA CHROME THẬT — 26/10/2026 user: đường cookie (gemini_webapi) hay "quá hạn 297s (Gemini web không trả lời)"
-> "mở chrome trong kho của tôi lưu xong rồi mở gemini hỏi nó trên đó".

Dùng lại các hồ sơ Chrome của Flow (flow_ve: ~/BanContent/flow_chrome/<hồ sơ>, đã đăng nhập Google, cổng DevTools 9350+):
  1. Chrome của hồ sơ đang mở thì gắn vào; chưa mở thì mở (cùng cờ như flow_ve, Flow mở sau sẽ dùng chung cửa sổ).
  2. Mỗi câu hỏi một TAB MỚI gemini.google.com (đóng sau khi xong) -> nhiều luồng / nhiều tiến trình không giẫm nhau.
  3. Bật "Temporary chat" (không lưu lịch sử tài khoản), gõ câu lệnh, bấm gửi, chờ nút Stop tắt và chữ trả lời đứng
     yên, đọc chữ của khung trả lời cuối.
Đo 26/10 trên acc1: đã đăng nhập sẵn, model mặc định Flash, trả JSON đúng; trò chuyện tạm giữ URL /app (không lưu)."""
import json
import os
import subprocess
import threading
import time
import urllib.request

from common import log

TRANG = "https://gemini.google.com/app?hl=en"
CHO = 300                    # giây chờ một câu trả lời
MOI_HO_SO = 2                # số câu hỏi cùng lúc trên một hồ sơ (mỗi câu một tab)
CHO_BAT_DAU = 75             # giây: gửi xong mà chưa ra chữ nào = treo (đo 26/10: câu dài nhất bắt đầu ra chữ < 30 s)
CHO_DUNG = 60                # giây: đang viết mà chữ đứng im = treo
NGHI_TREO = 15 * 60          # hồ sơ bị treo nghỉ bấy nhiêu giây (các câu sau hỏi hồ sơ khác)
NGHI = {}                    # hồ sơ -> nghỉ tới (đăng xuất / hết lượt)
_DANG = {}                   # hồ sơ -> số câu đang hỏi
_KHOA = threading.Lock()
_KHOA_MO = threading.Lock()

_O_NHAP = "document.querySelector('.ql-editor[role=textbox]')"
_DOC = """JSON.stringify({stop: !!document.querySelector('button[aria-label*="Stop"]'),
  n: document.querySelectorAll('model-response').length,
  txt: [...document.querySelectorAll('model-response')].map(e => (e.querySelector('message-content') || e).innerText).pop() || '',
  url: location.href})"""


def _ho_so():
    """[(tên, cổng)] các hồ sơ Chrome của Flow (cổng giống flow_ve)."""
    import flow_ve
    return [(ten, flow_ve.CONG_DAU + i % 40) for i, ten in enumerate(flow_ve._doc_so())]   # noqa: SLF001


def co_ho_so():
    return any(NGHI.get(t, 0) < time.time() for t, _ in _ho_so())


def _json(cong, duong="", put=False):
    req = urllib.request.Request(f"http://127.0.0.1:{cong}/json{duong}", method="PUT" if put else "GET")
    return json.load(urllib.request.urlopen(req, timeout=5))


def _mo_chrome(ten, cong):
    """Chrome của hồ sơ có cổng DevTools sống -> True (mở mới nếu cần)."""
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
        # trang đầu để trống (about:blank): không treo sẵn một tab Gemini; Flow mở sau sẽ dùng chính tab này
        flow_ve.mo_chrome_tach([flow_ve._chrome(), f"--user-data-dir={thu}", f"--remote-debugging-port={cong}",   # noqa: SLF001
                          "--no-first-run", "--no-default-browser-check", "--window-position=80,60",
                          "--window-size=1280,860", "--disable-backgrounding-occluded-windows",
                          "--disable-renderer-backgrounding", "--disable-background-timer-throttling", "about:blank"], thu)
        for _ in range(40):
            time.sleep(0.5)
            try:
                _json(cong)
                log(f"    Gemini Chrome: mở hồ sơ '{ten}'")
                return True
            except OSError:
                continue
        return False


def _cho(ws, bieu_thuc, giay, buoc=0.5):
    han = time.time() + giay
    while time.time() < han:
        try:
            v = ws.js(bieu_thuc)
            if v:
                return v
        except Exception:                                    # noqa: BLE001  (trang đang chuyển)
            pass
        time.sleep(buoc)
    return None


def _bam_that(ws, sel):
    """Bấm chuột THẬT (sự kiện tin cậy) vào giữa phần tử -> True nếu thấy phần tử."""
    xy = ws.js(f"(() => {{ const e = document.querySelector({json.dumps(sel)}); if (!e) return null;"
               " const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
    if not xy:
        return False
    for t in ("mouseMoved", "mousePressed", "mouseReleased"):
        ws.goi("Input.dispatchMouseEvent", type=t, x=xy[0], y=xy[1], button="left", clickCount=1)
    return True


def _dinh_anh(ws, url_ws, files):
    """26/10 user (tình báo đối thủ gửi ảnh khung hình bị lỗi cookie): đính tệp vào câu hỏi Gemini trên Chrome.
    Đo 26/10: .click() bằng JS không mở hộp chọn tệp (cần thao tác thật) và ô <input type=file> tạo ra rồi xoá ngay ->
    chặn hộp chọn tệp (Page.setInterceptFileChooserDialog) trên một kết nối RIÊNG chỉ để nghe sự kiện (kết nối kia đang
    chờ phản hồi lệnh sẽ nuốt mất sự kiện), bấm chuột thật "Upload & tools" -> "Upload files", nhận
    Page.fileChooserOpened rồi giao tệp bằng DOM.setFileInputFiles."""
    from anh_google import _WS
    nghe = _WS(url_ws)
    try:
        nghe.goi("Page.enable")
        nghe.goi("Page.setInterceptFileChooserDialog", enabled=True)
        if not _bam_that(ws, 'button[aria-label="Upload & tools"]'):
            raise RuntimeError("không thấy nút Upload & tools")
        if not _cho(ws, "!!document.querySelector('[data-test-id=local-images-files-uploader-button]')", 5):
            raise RuntimeError("không thấy mục Upload files")
        _bam_that(ws, "[data-test-id=local-images-files-uploader-button]")
        bn, han = None, time.time() + 10
        nghe.s.settimeout(2)
        while bn is None and time.time() < han:
            try:
                m = json.loads(nghe._nhan())                    # noqa: SLF001
            except Exception:                                # noqa: BLE001
                continue
            if m.get("method") == "Page.fileChooserOpened":
                bn = m["params"].get("backendNodeId")
        if not bn:
            raise RuntimeError("Gemini không mở hộp chọn tệp")
        nghe.s.settimeout(30)
        nghe.goi("DOM.setFileInputFiles", files=[os.path.abspath(f) for f in files], backendNodeId=bn)
        nghe.goi("Page.setInterceptFileChooserDialog", enabled=False)
    finally:
        nghe.dong()
    # chờ ảnh tải lên xong: nút gửi chỉ bật khi tệp đã lên (và ô nhập có chữ — kiểm sau khi gõ)
    if not _cho(ws, f"document.querySelectorAll('.attachment-preview-wrapper img, uploader-file-preview, "
                    f"[data-test-id*=file-preview]').length >= {len(files)} || "
                    "(document.querySelector('.attachment-preview-wrapper')||{innerHTML:''}).innerHTML.length > 500", 30):
        raise RuntimeError("ảnh chưa tải lên Gemini")
    time.sleep(1.5)


def _hoi_tab(ten, cong, prompt, timeout, files=None):
    """Một câu hỏi trên một tab mới của hồ sơ -> chữ trả lời. Lỗi -> raise."""
    from anh_google import _WS
    # 26/10 user ("bật mấy cái chrome này cứ lag lag"): /json/new mở tab Ở TRƯỚC — cửa sổ nhảy sang tab Gemini, tab Flow
    # đang vẽ bị đẩy ra sau. Mở tab NỀN (Target.createTarget background) để cửa sổ đứng yên ở tab đang xem.
    trinh = _WS(_json(cong, "/version")["webSocketDebuggerUrl"])
    try:
        tid = trinh.goi("Target.createTarget", url=TRANG, background=True)["targetId"]
    finally:
        trinh.dong()
    tab = next((t for t in _json(cong) if t.get("id") == tid), None)
    if not tab:
        raise RuntimeError("không mở được tab Gemini")
    ws = None
    try:
        ws = _WS(tab["webSocketDebuggerUrl"])
        try:
            ws.goi("Emulation.setFocusEmulationEnabled", enabled=True)   # tab nền vẫn chạy như đang được chọn
        except Exception:                                    # noqa: BLE001
            pass
        # chỉ coi là đăng xuất khi hết giờ chờ mà vẫn đứng ở trang có ô nhập email / mật khẩu (Chrome vừa mở hay đi vòng
        # qua accounts.google.com để làm mới phiên rồi tự quay về — như lỗi báo oan của flow_ve 26/10)
        if not _cho(ws, f"!!{_O_NHAP}", 45):
            if ws.js("location.href.includes('accounts.google.com') && !!document.querySelector('input[type=email],input[type=password]')"):
                NGHI[ten] = time.time() + 6 * 3600
                raise PermissionError("hồ sơ chưa đăng nhập Google")
            raise RuntimeError("Gemini tải quá chậm (chưa hiện ô nhập)")
        # tab nền vẽ chậm hơn: chờ nút "Temporary chat" hiện rồi mới bấm (bấm hụt = cuộc trò chuyện lưu vào lịch sử)
        if _cho(ws, "!!document.querySelector('button[aria-label=\"Temporary chat\"]')", 10):
            ws.js("document.querySelector('button[aria-label=\"Temporary chat\"]').click()")
        time.sleep(1.5)
        if files:
            _dinh_anh(ws, tab["webSocketDebuggerUrl"], files)
        ws.js(_O_NHAP + ".focus()")
        ws.goi("Input.insertText", text=prompt)
        if not _cho(ws, "(() => { const b = document.querySelector('button[aria-label*=\"Send\"]'); return !!(b && !b.disabled) })()", 20):
            raise RuntimeError("nút gửi không bật")
        time.sleep(0.4)
        ws.js("document.querySelector('button[aria-label*=\"Send\"]').click()")
        t0 = time.time()
        han, cu, dung_yen, doi = t0 + timeout, None, 0, t0
        while time.time() < han:
            time.sleep(2)
            try:
                d = json.loads(ws.js(_DOC) or "{}")
            except Exception:                                # noqa: BLE001
                continue
            txt = (d.get("txt") or "").strip()
            if txt != cu:
                doi = time.time()
            # 26/10 user (ảnh: chỉ có vòng quay, nút Stop vẫn sáng): "bị treo thì không hỏi thằng này nữa" -> chưa ra chữ
            # sau CHO_BAT_DAU giây, hoặc chữ đứng im CHO_DUNG giây mà vẫn đang "viết" = treo: bỏ, hồ sơ nghỉ NGHI_TREO
            if (not txt and time.time() - t0 > CHO_BAT_DAU) or (txt and d.get("stop") and time.time() - doi > CHO_DUNG):
                NGHI[ten] = time.time() + NGHI_TREO
                raise TimeoutError(f"Gemini treo ({'không ra chữ' if not txt else 'đứng im'} {time.time() - (t0 if not txt else doi):.0f}s)"
                                   f" — hồ sơ nghỉ {NGHI_TREO // 60} phút")
            if d.get("n") and not d.get("stop") and txt:
                dung_yen = dung_yen + 1 if txt == cu else 0   # chữ đứng yên 2 lượt đọc liền (4 s) mới coi là xong
                if dung_yen >= 1:
                    if len(txt) < 300 and any(k in txt.lower() for k in ("reached your limit", "đã đạt giới hạn",
                                                                         "try again later", "something went wrong")):
                        NGHI[ten] = time.time() + 3600
                        raise RuntimeError("Gemini báo: " + txt[:120])
                    return txt
            cu = txt
        raise TimeoutError(f"quá hạn {timeout}s chờ Gemini trả lời")
    finally:
        if ws:
            ws.dong()
        try:
            _json(cong, "/close/" + tab["id"])
        except Exception:                                    # noqa: BLE001
            pass


def _dang_mo(cong):
    try:
        _json(cong)
        return True
    except OSError:
        return False


def _giu(tranh=()):
    """Giữ chỗ một hồ sơ còn dưới MOI_HO_SO câu đang hỏi: hồ sơ chưa thử trước, Chrome đang mở trước (khỏi mở cửa sổ
    mới), ít việc trước -> (tên, cổng) | None nếu không còn chỗ."""
    with _KHOA:
        ds = [(t in tranh, not _dang_mo(c), _DANG.get(t, 0), t, c) for t, c in _ho_so()
              if NGHI.get(t, 0) < time.time() and _DANG.get(t, 0) < MOI_HO_SO]
        # 26/10 user (lag): KHÔNG tự mở thêm Chrome để hỏi song song — đã có hồ sơ đang mở thì chỉ dùng hồ sơ đang mở
        # (bận thì chờ); chỉ khi chưa có Chrome nào mở mới mở một cửa sổ
        if any(_dang_mo(c) for t, c in _ho_so() if NGHI.get(t, 0) < time.time()):
            ds = [x for x in ds if not x[1]]
        if not ds:
            return None
        *_, t, c = min(ds)
        _DANG[t] = _DANG.get(t, 0) + 1
        return t, c


def _tha(ten):
    with _KHOA:
        _DANG[ten] = max(0, _DANG.get(ten, 1) - 1)


def hoi(prompt, timeout=CHO, so_lan=3, files=None):
    """Hỏi Gemini qua Chrome thật -> chữ trả lời ('' nếu mọi lần thử đều hỏng). Hồ sơ lỗi thì thử hồ sơ khác.
    files: [đường dẫn ảnh / tệp] đính kèm câu hỏi."""
    da_thu = set()
    for _ in range(so_lan):
        g, han = None, time.time() + timeout
        while g is None and time.time() < han and co_ho_so():   # mọi hồ sơ đang bận: chờ chỗ trống
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
            kq = _hoi_tab(ten, cong, prompt, timeout, files)
            log(f"    Gemini Chrome '{ten}': trả lời sau {time.time() - t0:.0f}s ({len(kq)} ký tự)")
            return kq
        except Exception as e:                               # noqa: BLE001
            log(f"    (Gemini Chrome '{ten}' lỗi: {str(e)[:120]} → thử hồ sơ khác)")
        finally:
            _tha(ten)
    return ""


def hoi_nhieu(prompts, timeout=CHO, on_xong=None):
    """Hỏi nhiều câu cùng lúc (mỗi hồ sơ tối đa MOI_HO_SO tab) -> list chữ theo thứ tự ('' = câu hỏng)."""
    from concurrent.futures import ThreadPoolExecutor
    ra = [""] * len(prompts)
    if not prompts:
        return ra

    def lam(i):
        ra[i] = hoi(prompts[i], timeout, so_lan=2)
        if on_xong and ra[i]:
            on_xong(i, ra[i])
    so = max(1, min(len(prompts), sum(1 for t, _ in _ho_so() if NGHI.get(t, 0) < time.time()) * MOI_HO_SO))
    with ThreadPoolExecutor(so) as ex:
        list(ex.map(lam, range(len(prompts))))
    return ra


# --------------------------------------------------------------------------- phiên chat nhiều lượt (quy trình viết)
# 26/10 user: quy trình viết kịch bản = gửi LẦN LƯỢT nhiều câu lệnh trong CÙNG MỘT cuộc chat (chờ trả lời xong mới gửi
# tiếp), chỉ dùng tài khoản Gemini PRO. Đo 26/10: tài khoản Pro có nhãn hạng "Pro" trên avatar (.mavatar-tier-label —
# acc1 có, acc2 không); ô chọn chế độ có "3.1 Pro  Advanced reasoning" (cả tài khoản thường cũng thấy nhưng bị giới hạn).
HANG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "gemini_hang.json")   # hồ sơ -> {hang, luc}
HANG_GIU = 24 * 3600


def _mo_tab(cong, url=TRANG):
    """Mở tab NỀN mới -> (tab, ws) đã giả lập đang được chọn."""
    from anh_google import _WS
    trinh = _WS(_json(cong, "/version")["webSocketDebuggerUrl"])
    try:
        tid = trinh.goi("Target.createTarget", url=url, background=True)["targetId"]
    finally:
        trinh.dong()
    tab = next((t for t in _json(cong) if t.get("id") == tid), None)
    if not tab:
        raise RuntimeError("không mở được tab Gemini")
    ws = _WS(tab["webSocketDebuggerUrl"])
    try:
        ws.goi("Emulation.setFocusEmulationEnabled", enabled=True)
    except Exception:                                        # noqa: BLE001
        pass
    return tab, ws


def _dong_tab(cong, tab, ws):
    try:
        ws.dong()
    except Exception:                                        # noqa: BLE001
        pass
    try:
        _json(cong, "/close/" + tab["id"])
    except Exception:                                        # noqa: BLE001
        pass


def hang_tai_khoan(ten, cong, lam_moi=False):
    """'pro' | 'ultra' | 'thuong' | '' (không xem được) — nhớ HANG_GIU giây trong cache/gemini_hang.json."""
    from common import doc_json, ghi_json
    d = doc_json(HANG, {}) or {}
    m = d.get(ten) or {}
    if not lam_moi and m.get("hang") and time.time() - float(m.get("luc") or 0) < HANG_GIU:
        return m["hang"]
    if not _mo_chrome(ten, cong):
        return ""
    tab, ws = _mo_tab(cong)
    try:
        if not _cho(ws, f"!!{_O_NHAP}", 45):
            return ""
        time.sleep(2)
        nhan = (ws.js("(document.querySelector('.mavatar-tier-label') || {}).innerText || ''") or "").strip().lower()
    finally:
        _dong_tab(cong, tab, ws)
    hang = "ultra" if "ultra" in nhan else "pro" if "pro" in nhan else "thuong"
    d[ten] = {"hang": hang, "luc": time.time()}
    os.makedirs(os.path.dirname(HANG), exist_ok=True)
    ghi_json(HANG, d)
    return hang


def ho_so_pro(bao=None):
    """Hồ sơ Gemini Pro / Ultra dùng được (Chrome đang mở trước) -> (tên, cổng) | None."""
    ds = sorted((t for t in _ho_so() if NGHI.get(t[0], 0) < time.time()), key=lambda t: not _dang_mo(t[1]))
    for ten, cong in ds:
        try:
            h = hang_tai_khoan(ten, cong)
        except Exception as e:                               # noqa: BLE001
            log(f"    (Gemini Chrome '{ten}': không xem được hạng tài khoản: {str(e)[:80]})")
            continue
        if bao:
            bao(f"  hồ sơ {ten}: Gemini {'PRO' if h == 'pro' else h.upper() if h else '?'}")
        if h in ("pro", "ultra"):
            return ten, cong
    return None


_TU_CHOI = ("mô hình ngôn ngữ", "không thể giúp", "không thể trợ giúp", "language model", "can't help", "cannot help",
            "i'm not able to help", "không có khả năng", "ngoài khả năng", "chỉ có thể tạo văn bản", "dựa trên văn bản",
            "only process and generate text", "outside of my capabilities", "encountered an error", "try again",
            "không được lập trình", "thử lại")


def la_tu_choi(txt):
    """Câu từ chối soạn sẵn của Gemini (26/10 chạy thật: dàn ý A / bản sâu sắc / hook trả "Tôi là một mô hình ngôn ngữ nên
    điều đó nằm ngoài mục đích…" — lỗi nội bộ, cùng câu lệnh lượt trước làm được) -> coi như lượt lỗi, gửi lại."""
    t = str(txt or "").strip().lower()
    return len(t) < 400 and any(k in t for k in _TU_CHOI)


class PhienChat:
    """Một cuộc chat Gemini giữ nguyên qua nhiều lượt: gui() chờ trả lời XONG rồi mới trả về, lượt sau gửi tiếp trong
    cùng cuộc chat (Gemini nhớ dàn bài / bài đã viết ở các lượt trước)."""

    def __init__(self, ten, cong, model="pro", tam=False, url=None):
        """url: địa chỉ một cuộc chat đã có (gemini.google.com/app/<ID>) -> mở lại để viết tiếp."""
        self.ten, self.cong, self.model = ten, cong, model
        self.url = url or ""                                 # ID chat — có sau lượt trả lời đầu (chat thường, không tạm)
        if not _mo_chrome(ten, cong):
            raise RuntimeError(f"không mở được Chrome hồ sơ {ten}")
        self.tab, self.ws = _mo_tab(cong, url or TRANG)
        if url:
            _cho(self.ws, "document.querySelectorAll('model-response').length > 0", 45)   # chờ chat cũ tải xong
        if not _cho(self.ws, f"!!{_O_NHAP}", 45):
            self.dong()
            raise RuntimeError(f"Gemini hồ sơ {ten} không hiện ô nhập (chưa đăng nhập?)")
        if tam and _cho(self.ws, "!!document.querySelector('button[aria-label=\"Temporary chat\"]')", 10):
            self.ws.js("document.querySelector('button[aria-label=\"Temporary chat\"]').click()")
            time.sleep(1.5)
        if model:
            self.chon_model(model)

    def chon_model(self, model):
        """Chọn model trong ô chế độ -> tên mục đã chọn | ''. model = 'flash' (26/10 user: "bản pro 3.1 không bằng flash
        3.8" — mục Flash, KHÔNG lấy Flash-Lite) | 'pro' (mục Pro, không lấy Argon) | chữ bất kỳ trong tên mục."""
        if not _bam_that(self.ws, 'button[aria-label^="Open mode picker"]'):
            return ""
        time.sleep(1.2)
        tranh = "" if "lite" in model.lower() else "lite|"
        chon = self.ws.js(r"(() => { const ds = [...document.querySelectorAll('[role=menuitem],[role=menuitemradio],[role=option]')]"
                          r".filter(e => e.offsetParent); const e = ds.find(e => new RegExp('\\b' + " + json.dumps(model) +
                          r" + '\\b', 'i').test(e.innerText) && !new RegExp(" + json.dumps(tranh + "argon") +
                          r", 'i').test(e.innerText)); if (!e) return '';"
                          r" e.click(); return e.innerText.replace(/\s+/g, ' ').trim() })()") or ""
        time.sleep(1)
        if not chon:
            for t in ("keyDown", "keyUp"):
                self.ws.goi("Input.dispatchKeyEvent", type=t, key="Escape", code="Escape", windowsVirtualKeyCode=27)
        log(f"    Gemini Chrome '{self.ten}': model {chon or '(không đổi được — giữ mặc định)'}")
        return chon

    def gui(self, text, timeout=900, cho_bat_dau=None, cho_dung=120):
        """Gửi một lượt, chờ câu trả lời MỚI viết xong -> chữ trả lời. cho_bat_dau: giây chờ ra chữ đầu tiên — 26/10 đo:
        Flash bắt đầu viết < 30 s (cả dàn ý ~35 s), lần treo phía Gemini thì nút Stop sáng mãi mà không có khung trả lời
        (tab đang hiện, có focus) -> Flash 90 s là coi như treo; Pro suy nghĩ lâu nên 240 s."""
        if cho_bat_dau is None:
            cho_bat_dau = 240 if "pro" in str(self.model or "").lower() else 90
        ws = self.ws
        # 26/10 (chạy thật: lượt thứ 8 "không ra chữ"): ĐẾM số khung trả lời không tin được ở chat dài — đánh dấu các khung
        # đã có, câu trả lời mới = khung chưa đánh dấu; gửi xong phải thấy ô nhập trống (tin đã đi), không thì bấm lại
        ws.js("document.querySelectorAll('model-response').forEach(e => e.dataset.bcCu = '1')")
        ws.js(_O_NHAP + ".focus()")
        ws.goi("Input.insertText", text=text)
        nut = "button[aria-label*=\"Send\"]"
        if not _cho(ws, f"(() => {{ const b = document.querySelector('{nut}'); return !!(b && !b.disabled) }})()", 30):
            raise RuntimeError("nút gửi không bật")
        time.sleep(0.4)
        for _ in range(3):
            _bam_that(ws, nut)
            if _cho(ws, f"!({_O_NHAP}.innerText || '').trim() || !!document.querySelector('model-response:not([data-bc-cu])')", 8):
                break
        else:
            raise RuntimeError("Gemini không nhận tin nhắn (bấm Gửi 3 lần)")
        doc_moi = ("JSON.stringify({stop: !!document.querySelector('button[aria-label*=\"Stop\"]'),"
                   " n: document.querySelectorAll('model-response:not([data-bc-cu])').length,"
                   " txt: [...document.querySelectorAll('model-response:not([data-bc-cu])')]"
                   ".map(e => (e.querySelector('message-content') || e).innerText).pop() || ''})")
        t0 = time.time()
        han, cu, dung_yen, doi, mat = t0 + timeout, None, 0, t0, 0
        cho_tai_lai = 120 if "pro" in str(self.model or "").lower() else 40
        sau_tai, lan_tai, t_tai = False, 0, t0
        while time.time() < han:
            time.sleep(2)
            ws = self.ws                                     # _tai_lai giữ nguyên tab nhưng đọc qua self.ws cho chắc
            try:
                d = json.loads(ws.js(doc_moi) or "{}")
                mat = 0
            except Exception as e:                           # noqa: BLE001
                # 26/10 user tắt Chrome giữa chừng: trước đây bỏ qua lỗi và chờ đủ 15 phút -> mất kết nối 3 lần liền
                # (~6 s) thì báo ngay; bên gọi tự mở lại Chrome + chat theo ID
                mat += 1
                if mat >= 3:
                    raise RuntimeError(f"mất kết nối tab Gemini (Chrome bị tắt?): {str(e)[:60]}")
                continue
            if sau_tai:                                      # đã tải lại trang: đọc câu trả lời cho đúng câu vừa gửi
                r = self.tra_loi_cho(text, bo_tu_choi=False)
                if r:
                    if la_tu_choi(r):
                        raise RuntimeError("Gemini trả câu từ chối soạn sẵn: " + r[:80])
                    log(f"    Gemini Chrome '{self.ten}': tải lại trang là thấy câu trả lời ({len(r)} ký tự)")
                    return r
                if time.time() - t_tai > cho_tai_lai:
                    if lan_tai < 2 and self._tai_lai():
                        lan_tai, t_tai = lan_tai + 1, time.time()
                        continue
                    raise TimeoutError("Gemini treo (tải lại trang vẫn chưa có câu trả lời)")
                continue
            moi = int(d.get("n") or 0) > 0
            txt = (d.get("txt") or "").strip() if moi else ""
            if txt != cu:
                doi = time.time()
            # 26/10 user: "nó cứ phải load lại trang hỏi lại thì nó mới có câu trả lời" (đo: mở lại chat là câu trả lời đã
            # nằm sẵn — Gemini viết xong trên máy chủ nhưng tab không nhận luồng) -> chưa ra chữ sau cho_tai_lai giây thì
            # TẢI LẠI đúng chat đó và đọc câu trả lời, tối đa 2 lần, rồi mới coi là treo
            if not txt and time.time() - t0 > cho_tai_lai and lan_tai < 2 and self._tai_lai():
                sau_tai, lan_tai, t_tai = True, lan_tai + 1, time.time()
                continue
            if (not txt and time.time() - t0 > cho_bat_dau) or (txt and d.get("stop") and time.time() - doi > cho_dung):
                raise TimeoutError(f"Gemini treo ({'không ra chữ' if not txt else 'đứng im'})")
            if moi and not d.get("stop") and txt:
                dung_yen = dung_yen + 1 if txt == cu else 0
                if dung_yen >= 1:
                    if len(txt) < 300 and any(k in txt.lower() for k in ("reached your limit", "đã đạt giới hạn",
                                                                         "something went wrong")):
                        raise RuntimeError("Gemini báo: " + txt[:120])
                    u = ws.js("location.href") or ""
                    if "/app/" in u:
                        self.url = u                             # nhớ ID chat để mở lại khi lượt sau bị treo
                    if la_tu_choi(txt):
                        raise RuntimeError("Gemini trả câu từ chối soạn sẵn: " + txt[:80])
                    return txt
            cu = txt
        raise TimeoutError(f"quá hạn {timeout}s chờ Gemini trả lời")

    def mo_lai(self):
        """26/10 user: "nếu nó bị lỗi kiểu này bạn có thể lưu lại ID chat xong mở lại vào viết vẫn ok" — đóng tab đang
        treo, mở lại ĐÚNG cuộc chat theo ID (Gemini còn nhớ dàn ý A và các phần đã viết), chọn lại model."""
        if not self.url:
            raise RuntimeError("chưa có ID chat để mở lại")
        _dong_tab(self.cong, self.tab, self.ws)
        if not _mo_chrome(self.ten, self.cong):
            raise RuntimeError(f"không mở được Chrome hồ sơ {self.ten}")
        self.tab, self.ws = _mo_tab(self.cong, self.url)
        if not _cho(self.ws, f"!!{_O_NHAP} && document.querySelectorAll('model-response').length > 0", 60):
            raise RuntimeError("mở lại chat không thấy nội dung cũ")
        time.sleep(2)
        log(f"    Gemini Chrome '{self.ten}': đã mở lại chat {self.url.split('/app/')[-1][:16]}")
        if self.model:
            self.chon_model(self.model)

    def _tai_lai(self):
        """Tải lại đúng cuộc chat đang viết (theo ID trên thanh địa chỉ) -> True nếu trang đã hiện lại các câu hỏi."""
        try:
            u = self.ws.js("location.href") or ""
        except Exception:                                    # noqa: BLE001
            u = ""
        if "/app/" in u:
            self.url = u
        if not self.url:                                     # chat mới chưa có ID: tải lại là mất — để bên gọi mở chat mới
            return False
        log(f"    Gemini Chrome '{self.ten}': chưa thấy câu trả lời — tải lại chat {self.url.split('/app/')[-1][:16]}")
        self.ws.goi("Page.navigate", url=self.url)
        time.sleep(2)
        return bool(_cho(self.ws, f"!!{_O_NHAP} && document.querySelectorAll('user-query').length > 0", 45))

    def tra_loi_cho(self, text, bo_tu_choi=True):
        """Sau khi mở lại: câu trả lời đã có trong chat cho tin nhắn `text` (tin cuối của người dùng khớp `text` và
        Gemini đã viết xong) -> chữ trả lời | '' (chưa có — cần gửi lại). bo_tu_choi: câu từ chối coi như chưa có."""
        js = ("(() => { const q = [...document.querySelectorAll('user-query')].pop();"
              " const r = [...document.querySelectorAll('model-response')].pop();"
              " if (!q || !r || document.querySelector('button[aria-label*=\"Stop\"]')) return null;"
              " if (q.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_PRECEDING) return null;"   # trả lời phải SAU câu hỏi
              " return JSON.stringify({q: (q.innerText || '').replace(/\\s+/g, ' '),"
              " r: ((r.querySelector('message-content') || r).innerText || '').trim()}) })()")
        d = self.ws.js(js)
        if not d:
            return ""
        d = json.loads(d)
        dau = " ".join(str(text).split())[:80]
        return d["r"] if dau and dau[:60] in d["q"] and d["r"] and not (bo_tu_choi and la_tu_choi(d["r"])) else ""

    def dong(self):
        _dong_tab(self.cong, self.tab, self.ws)
