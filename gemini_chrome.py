# -*- coding: utf-8 -*-
"""HỎI GEMINI QUA CHROME THẬT — 26/10/2026 user: đường cookie (gemini_webapi) hay "quá hạn 297s (Gemini web không trả lời)"
-> "mở chrome trong kho của tôi lưu xong rồi mở gemini hỏi nó trên đó".

Dùng lại các hồ sơ Chrome của Flow (flow_ve: ~/BanContent/flow_chrome/<hồ sơ>, đã đăng nhập Google, cổng DevTools 9350+):
  1. Chrome của hồ sơ đang mở thì gắn vào; chưa mở thì mở (cùng cờ như flow_ve, Flow mở sau sẽ dùng chung cửa sổ).
  2. Mỗi câu hỏi một TAB MỚI gemini.google.com (đóng sau khi xong) -> nhiều luồng / nhiều tiến trình không giẫm nhau.
  3. Chat thường (27/10 user bỏ "Temporary chat"), gõ câu lệnh, bấm gửi, chờ nút Stop tắt và chữ trả lời đứng
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
MOI_HO_SO = 1                # 27/10 user: "tôi bảo mở hồ sơ mới mà" — mỗi hồ sơ một câu; câu khác mở hồ sơ khác
# 27/10 user: "không có chuyện cho nghỉ nhé, nếu 60s mà không có bất kì phản hồi nào thì load lại trang rồi vào đúng bài
# đó hỏi lại rồi chờ lại 60s" -> treo KHÔNG cho hồ sơ nghỉ: tải lại trang, đúng cuộc chat đó, hỏi lại, lặp tới hết giờ
CHO_PHAN_HOI = 60            # giây: gửi xong mà chưa có chữ nào = treo -> tải lại trang, hỏi lại
CHO_DUNG = 60                # giây: đang viết mà chữ đứng im = treo -> như trên
# 27/10 user (ảnh: "Tôi không thể trợ giúp về điều đó, vì tôi chỉ là một mô hình ngôn ngữ…"): "bạn cần bảo nó là nó lại
# viết đó" -> Gemini trả câu từ chối thì nhắn câu này trong CÙNG cuộc chat, lấy câu trả lời sau đó (tối đa NHAC_TOI_DA lần)
NHAC_TU_CHOI = "tôi nhờ bạn viết nội dung sao bạn cứ từ chối vậy ?"
NHAC_TOI_DA = 2
TAI_LAI_TOI_DA = 2           # 27/10 user: "load lại vài lần mà không được thì đẩy sang cho thằng khác làm" (câu hỏi lẻ)
NGHI = {}                    # hồ sơ -> nghỉ tới (đăng xuất / hết lượt)
_DANG = {}                   # hồ sơ -> số câu đang hỏi
_KHOA = threading.Lock()
_KHOA_MO = threading.Lock()

# 27/10 user: "có 1 số tài khoản tôi không tạo chat được với gemini trong hồ sơ… check nếu dùng được mới sử dụng" ->
# trước khi dùng một hồ sơ: hỏi thật một câu ngắn; được thì nhớ DUNG_GIU giây, hỏng thì bỏ qua hồ
# sơ đó HONG_GIU giây rồi mới thử lại. Câu hỏi thật trả lời được cũng tính là "dùng được".
DUNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "gemini_dung.json")   # hồ sơ -> {ok, luc, msg}
DUNG_GIU = 12 * 3600
HONG_GIU = 6 * 3600
_CAU_THU = "Reply with exactly one word: OK"
_KHOA_DUNG = threading.Lock()
_KHOA_THU = {}                                               # hồ sơ -> khoá (hai luồng không cùng thử một hồ sơ)


class KhongTaoChat(RuntimeError):
    """Hồ sơ mở được Gemini nhưng không tạo được cuộc chat (không có ô nhập / nút gửi không bật)."""


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
    """True (thử được gần đây) | False (thử hỏng, chưa hết HONG_GIU) | None (chưa thử / kết quả đã cũ)."""
    m = _doc_dung().get(ten) or {}
    tuoi = time.time() - float(m.get("luc") or 0)
    if m.get("ok") and tuoi < DUNG_GIU:
        return True
    if m and not m.get("ok") and tuoi < HONG_GIU:
        return False
    return None


def kiem_tai_khoan(ten, cong, lam_moi=False):
    """Hồ sơ tạo được chat Gemini không -> (ok, lời nhắn). Hỏi thật _CAU_THU; nhớ kết quả trong cache/gemini_dung.json."""
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
            ok, msg = bool(kq.strip()), "tạo chat và nhận trả lời được"
        except Exception as e:                               # noqa: BLE001
            ok, msg = False, "không tạo chat được: " + str(e)[:150]
        _ghi_dung(ten, ok, msg)
        log(f"    Gemini Chrome '{ten}': {'dùng được' if ok else msg}")
        return ok, msg


def _san(ten):
    """Hồ sơ đang không nghỉ và không bị đánh dấu "không tạo chat được"."""
    return NGHI.get(ten, 0) < time.time() and dung_duoc(ten) is not False

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
    return any(_san(t) for t, _ in _ho_so())


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


def _hien_neu_trong(cong, tid):
    """27/10 user (ảnh: cửa sổ đứng mãi ở about:blank): tab Gemini mở NỀN để không giật tab Flow đang xem — nhưng cửa sổ
    chỉ có tab trống / tab Gemini thì chẳng có gì để giữ: cho hiện tab Gemini vừa mở."""
    try:
        khac = [t for t in _json(cong) if t.get("type") == "page" and t.get("id") != tid]
        if all(t.get("url", "").startswith(("about:blank", "chrome://newtab", "https://gemini.google.com")) for t in khac):
            urllib.request.urlopen(f"http://127.0.0.1:{cong}/json/activate/{tid}", timeout=5).read()
    except Exception:                                        # noqa: BLE001
        pass


def _cho_o_nhap(ten, ws):
    """Chờ ô nhập của Gemini. Chưa đăng nhập -> PermissionError; không có ô nhập -> KhongTaoChat."""
    # chỉ coi là đăng xuất khi hết giờ chờ mà vẫn đứng ở trang có ô nhập email / mật khẩu (Chrome vừa mở hay đi vòng
    # qua accounts.google.com để làm mới phiên rồi tự quay về — như lỗi báo oan của flow_ve 26/10)
    if _cho(ws, f"!!{_O_NHAP}", 45):
        return
    if ws.js("location.href.includes('accounts.google.com') && !!document.querySelector('input[type=email],input[type=password]')"):
        NGHI[ten] = time.time() + 6 * 3600
        raise PermissionError("hồ sơ chưa đăng nhập Google")
    trang = " ".join(str(ws.js("(document.body && document.body.innerText) || ''") or "").split())[:140]
    raise KhongTaoChat("Gemini không hiện ô nhập" + (f" (trang: {trang})" if trang else ""))


def _bat_tam(ws):
    # tab nền vẽ chậm hơn: chờ nút "Temporary chat" hiện rồi mới bấm (bấm hụt = cuộc trò chuyện lưu vào lịch sử)
    if _cho(ws, "!!document.querySelector('button[aria-label=\"Temporary chat\"]')", 10):
        ws.js("document.querySelector('button[aria-label=\"Temporary chat\"]').click()")
    time.sleep(1.5)


def _gui_cau(ws, url_ws, prompt, files=None):
    """Đánh dấu các khung trả lời đã có (câu trả lời mới = khung chưa đánh dấu), đính tệp, gõ câu, bấm gửi."""
    ws.js("document.querySelectorAll('model-response').forEach(e => e.dataset.bcCu = '1')")
    if files:
        _dinh_anh(ws, url_ws, files)
    ws.js(_O_NHAP + ".focus()")
    ws.goi("Input.insertText", text=prompt)
    if not _cho(ws, "(() => { const b = document.querySelector('button[aria-label*=\"Send\"]'); return !!(b && !b.disabled) })()", 20):
        raise KhongTaoChat("nút gửi không bật")
    time.sleep(0.4)
    ws.js("document.querySelector('button[aria-label*=\"Send\"]').click()")


_DOC_MOI = ("JSON.stringify({stop: !!document.querySelector('button[aria-label*=\"Stop\"]'),"
            " n: document.querySelectorAll('model-response:not([data-bc-cu])').length,"
            " txt: [...document.querySelectorAll('model-response:not([data-bc-cu])')]"
            ".map(e => (e.querySelector('message-content') || e).innerText).pop() || ''})")


def _cho_tra_loi(ws, han, cho_phan_hoi=CHO_PHAN_HOI, cho_dung=CHO_DUNG):
    """Chờ câu trả lời MỚI viết xong -> chữ | None (cho_phan_hoi giây chưa có chữ nào, hay đang viết mà chữ đứng im
    cho_dung giây, hay hết hạn `han`). Mất kết nối tab 3 lần liền -> RuntimeError."""
    t0 = time.time()
    cu, doi, mat = None, t0, 0
    while time.time() < han:
        time.sleep(2)
        try:
            d = json.loads(ws.js(_DOC_MOI) or "{}")
            mat = 0
        except Exception as e:                               # noqa: BLE001
            # 26/10 user tắt Chrome giữa chừng: mất kết nối 3 lần liền (~6 s) thì báo ngay
            mat += 1
            if mat >= 3:
                raise RuntimeError(f"mất kết nối tab Gemini (Chrome bị tắt?): {str(e)[:60]}") from e
            continue
        txt = (d.get("txt") or "").strip() if d.get("n") else ""
        if txt != cu:
            doi = time.time()
        if (not txt and time.time() - t0 > cho_phan_hoi) or (txt and d.get("stop") and time.time() - doi > cho_dung):
            return None
        if txt and not d.get("stop") and txt == cu:          # chữ đứng yên 2 lượt đọc liền (4 s) mới coi là xong
            return txt
        cu = txt
    return None


def _tra_loi_cho(ws, text, bo_tu_choi=True):
    """Câu trả lời đã có trong chat cho tin nhắn `text` (tin cuối của người dùng khớp `text` và Gemini đã viết xong)
    -> chữ trả lời | '' (chưa có — cần gửi lại). bo_tu_choi: câu từ chối coi như chưa có."""
    js = ("(() => { const q = [...document.querySelectorAll('user-query')].pop();"
          " const r = [...document.querySelectorAll('model-response')].pop();"
          " if (!q || !r || document.querySelector('button[aria-label*=\"Stop\"]')) return null;"
          " if (q.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_PRECEDING) return null;"   # trả lời phải SAU câu hỏi
          " return JSON.stringify({q: (q.innerText || '').replace(/\\s+/g, ' '),"
          " r: ((r.querySelector('message-content') || r).innerText || '').trim()}) })()")
    d = ws.js(js)
    if not d:
        return ""
    d = json.loads(d)
    dau = " ".join(str(text).split())[:80]
    return d["r"] if dau and dau[:60] in d["q"] and d["r"] and not (bo_tu_choi and la_tu_choi(d["r"])) else ""


def _tai_lai_tab(ten, ws, text, lan, url=""):
    """Treo: tải lại trang, vào ĐÚNG cuộc chat đó (theo ID trên thanh địa chỉ / `url`) -> (chữ trả lời đã có | '',
    cần gửi lại?). Đo 26/10: Gemini hay viết xong trên máy chủ mà tab không nhận luồng — tải lại là thấy câu trả lời;
    Gemini còn đang viết (nút Stop) thì không gửi lại, chờ tiếp. Chat chưa có ID (chưa trả lời lượt nào) ->
    về trang chat mới, gửi lại."""
    try:
        u = ws.js("location.href") or ""
    except Exception:                                        # noqa: BLE001
        u = ""
    url = u if "/app/" in u else url
    log(f"    Gemini Chrome '{ten}': {CHO_PHAN_HOI}s không có phản hồi — tải lại trang, hỏi lại (lần {lan})")
    ws.goi("Page.navigate", url=url or TRANG)
    time.sleep(2)
    _cho_o_nhap(ten, ws)
    if not url:
        return "", True
    _cho(ws, "document.querySelectorAll('user-query').length > 0", 20)
    time.sleep(2)
    r = _tra_loi_cho(ws, text, bo_tu_choi=False)
    if r:
        log(f"    Gemini Chrome '{ten}': tải lại trang là thấy câu trả lời ({len(r)} ký tự)")
        return r, False
    dang_viet = ws.js("!!document.querySelector('button[aria-label*=\"Stop\"]')")
    if dang_viet:   # câu trả lời đang viết dở = khung chưa đánh dấu (trang mới tải không có dấu cũ): đánh dấu các khung trước
        ws.js("[...document.querySelectorAll('model-response')].slice(0, -1).forEach(e => e.dataset.bcCu = '1')")
    return "", not dang_viet


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
    _hien_neu_trong(cong, tid)
    ws = None
    try:
        ws = _WS(tab["webSocketDebuggerUrl"])
        try:
            ws.goi("Emulation.setFocusEmulationEnabled", enabled=True)   # tab nền vẫn chạy như đang được chọn
        except Exception:                                    # noqa: BLE001
            pass
        # 27/10 user: KHÔNG dùng "Temporary chat" (nghi hỏi ở đó không nhận được kết quả) -> chat thường, có ID để tải lại
        # đúng cuộc chat đó
        _cho_o_nhap(ten, ws)
        han, lan, gui = time.time() + timeout, 0, True
        cau, nhac = prompt, 0                                # cau: tin vừa gửi (câu hỏi, hay câu nhắc khi bị từ chối)
        while True:
            if gui:
                _gui_cau(ws, tab["webSocketDebuggerUrl"], cau, files if cau is prompt else None)
            txt = _cho_tra_loi(ws, han)
            if not txt:
                if time.time() >= han:
                    raise TimeoutError(f"quá hạn {timeout}s chờ Gemini trả lời")
                if lan >= TAI_LAI_TOI_DA:
                    raise TimeoutError(f"tải lại {lan} lần vẫn không có trả lời — chuyển hồ sơ khác")
                lan += 1
                txt, gui = _tai_lai_tab(ten, ws, cau, lan)
                if not txt:
                    continue
            if len(txt) < 300 and any(k in txt.lower() for k in ("reached your limit", "đã đạt giới hạn",
                                                                 "try again later", "something went wrong")):
                NGHI[ten] = time.time() + 3600
                raise RuntimeError("Gemini báo: " + txt[:120])
            if la_tu_choi(txt):
                if nhac >= NHAC_TOI_DA:
                    raise RuntimeError(f"Gemini vẫn từ chối sau {nhac} lần nhắc: " + txt[:80])
                nhac += 1
                log(f"    Gemini Chrome '{ten}': trả câu từ chối — nhắc lại (lần {nhac})")
                cau, gui = NHAC_TU_CHOI, True
                continue
            return txt
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
              if _san(t) and _DANG.get(t, 0) < MOI_HO_SO]
        # hồ sơ có Chrome đang mở được chọn trước; bận hết thì MỞ hồ sơ khác (27/10 user: hỏi song song trên nhiều hồ sơ,
        # không dồn nhiều tab vào một hồ sơ)
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
            if dung_duoc(ten) is None and not kiem_tai_khoan(ten, cong)[0]:
                raise KhongTaoChat("hồ sơ không tạo được chat Gemini — bỏ qua")
            t0 = time.time()
            kq = _hoi_tab(ten, cong, prompt, timeout, files)
            log(f"    Gemini Chrome '{ten}': trả lời sau {time.time() - t0:.0f}s ({len(kq)} ký tự)")
            _ghi_dung(ten, True, "câu hỏi gần nhất trả lời được")
            return kq
        except (KhongTaoChat, PermissionError) as e:
            _ghi_dung(ten, False, "không tạo chat được: " + str(e)[:150])
            log(f"    (Gemini Chrome '{ten}': {str(e)[:120]} → dùng hồ sơ khác)")
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
    so = max(1, min(len(prompts), sum(1 for t, _ in _ho_so() if _san(t)) * MOI_HO_SO))
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
    _hien_neu_trong(cong, tid)
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
    ds = sorted((t for t in _ho_so() if _san(t[0])), key=lambda t: not _dang_mo(t[1]))
    for ten, cong in ds:
        try:
            h = hang_tai_khoan(ten, cong)
        except Exception as e:                               # noqa: BLE001
            log(f"    (Gemini Chrome '{ten}': không xem được hạng tài khoản: {str(e)[:80]})")
            continue
        if bao:
            bao(f"  hồ sơ {ten}: Gemini {'PRO' if h == 'pro' else h.upper() if h else '?'}")
        if h in ("pro", "ultra"):
            ok, msg = kiem_tai_khoan(ten, cong)
            if ok:
                return ten, cong
            if bao:
                bao(f"  hồ sơ {ten}: {msg} — bỏ qua")
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
        self.ten, self.cong, self.model, self.tam = ten, cong, model, tam
        self.url = url or ""                                 # ID chat — có sau lượt trả lời đầu (chat thường, không tạm)
        if not _mo_chrome(ten, cong):
            raise RuntimeError(f"không mở được Chrome hồ sơ {ten}")
        self.tab, self.ws = _mo_tab(cong, url or TRANG)
        if url:
            _cho(self.ws, "document.querySelectorAll('model-response').length > 0", 45)   # chờ chat cũ tải xong
        try:
            _cho_o_nhap(ten, self.ws)
        except Exception:
            self.dong()
            raise
        if tam:
            _bat_tam(self.ws)
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

    def _gui(self, text):
        ws = self.ws
        # 26/10 (chạy thật: lượt thứ 8 "không ra chữ"): ĐẾM số khung trả lời không tin được ở chat dài — đánh dấu các khung
        # đã có, câu trả lời mới = khung chưa đánh dấu; gửi xong phải thấy ô nhập trống (tin đã đi), không thì bấm lại
        ws.js("document.querySelectorAll('model-response').forEach(e => e.dataset.bcCu = '1')")
        ws.js(_O_NHAP + ".focus()")
        ws.goi("Input.insertText", text=text)
        nut = "button[aria-label*=\"Send\"]"
        if not _cho(ws, f"(() => {{ const b = document.querySelector('{nut}'); return !!(b && !b.disabled) }})()", 30):
            raise KhongTaoChat("nút gửi không bật")
        time.sleep(0.4)
        for _ in range(3):
            _bam_that(ws, nut)
            if _cho(ws, f"!({_O_NHAP}.innerText || '').trim() || !!document.querySelector('model-response:not([data-bc-cu])')", 8):
                return
        raise RuntimeError("Gemini không nhận tin nhắn (bấm Gửi 3 lần)")

    def gui(self, text, timeout=900, cho_phan_hoi=None, cho_dung=120):
        """Gửi một lượt, chờ câu trả lời MỚI viết xong -> chữ trả lời. 27/10 user: "nếu 60s mà không có bất kì phản hồi
        nào thì load lại trang rồi vào đúng bài đó hỏi lại rồi chờ lại 60s" -> cho_phan_hoi giây (Flash 60 s; Pro suy
        nghĩ lâu nên 180 s) chưa ra chữ nào, hay chữ đứng im cho_dung giây: tải lại trang, đúng cuộc chat này (có câu trả
        lời rồi thì lấy, Gemini đang viết thì chờ, chưa có thì hỏi lại) — lặp tới hết `timeout`, không cho hồ sơ nghỉ."""
        if cho_phan_hoi is None:
            cho_phan_hoi = 180 if "pro" in str(self.model or "").lower() else CHO_PHAN_HOI
        han, lan, gui = time.time() + timeout, 0, True
        cau, nhac = text, 0                                  # cau: tin vừa gửi (lệnh, hay câu nhắc khi bị từ chối)
        while True:
            if gui:
                self._gui(cau)
            txt = _cho_tra_loi(self.ws, han, cho_phan_hoi, cho_dung)
            if not txt and time.time() < han:
                lan += 1
                txt, gui = _tai_lai_tab(self.ten, self.ws, cau, lan, self.url)
                if not txt:                                  # trang mới tải: bật lại chat tạm / chọn lại model
                    if gui and not self.url and self.tam:
                        _bat_tam(self.ws)
                    if gui and self.model:
                        self.chon_model(self.model)
                    continue
            if not txt:
                raise TimeoutError(f"quá hạn {timeout}s chờ Gemini trả lời")
            if len(txt) < 300 and any(k in txt.lower() for k in ("reached your limit", "đã đạt giới hạn",
                                                                 "something went wrong")):
                raise RuntimeError("Gemini báo: " + txt[:120])
            u = self.ws.js("location.href") or ""
            if "/app/" in u:
                self.url = u                                 # nhớ ID chat để mở lại / tải lại khi lượt sau bị treo
            if la_tu_choi(txt):
                if nhac >= NHAC_TOI_DA:
                    raise RuntimeError(f"Gemini vẫn từ chối sau {nhac} lần nhắc: " + txt[:80])
                nhac += 1
                log(f"    Gemini Chrome '{self.ten}': trả câu từ chối — nhắc lại trong chat (lần {nhac})")
                cau, gui = NHAC_TU_CHOI, True
                continue
            return txt

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

    def tra_loi_cho(self, text, bo_tu_choi=True):
        """Sau khi mở lại: câu trả lời đã có trong chat cho tin nhắn `text` -> chữ | '' (chưa có — cần gửi lại)."""
        return _tra_loi_cho(self.ws, text, bo_tu_choi)

    def dong(self):
        _dong_tab(self.cong, self.tab, self.ws)
