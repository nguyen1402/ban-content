# -*- coding: utf-8 -*-
"""VẼ ẢNH QUA GOOGLE FLOW (Nano Banana, 0 điểm) — 15/10/2026 user: Gemini app trừ ~17 điểm/ảnh và cạn sau một dự án;
Flow (flow.google.com) ghi "Generating will use 0 credits" cho ảnh.

Vì sao phải lái Chrome thật: lệnh tạo ảnh của Flow (batchexecute rpcid ogiZ0b) kèm mã reCAPTCHA Enterprise do trang tự
sinh bằng JavaScript cho MỖI lần tạo -> không gọi thẳng từ Python được. Chrome đời mới (>=136) cũng không cho điều khiển
hồ sơ hằng ngày qua DevTools -> dùng HỒ SƠ RIÊNG do người dùng tạo bằng nút "＋ Hồ sơ Chrome Flow" trên giao diện, đăng
nhập một lần.

  * Hồ sơ: %LOCALAPPDATA%\\BanContent\\flow_chrome\\<tên>\\ ; sổ: flow_chrome\\ho_so.json (dự án Flow, hết lượt…).
  * Mỗi lần cần ảnh: mở Chrome hồ sơ đó với cổng DevTools, cửa sổ ĐẨY RA NGOÀI MÀN HÌNH (không headless — reCAPTCHA
    chấm điểm thấp), vào dự án Flow, chọn Image + tỉ lệ + x2, gõ câu lệnh, bấm tạo, đọc kết quả (link ảnh có chữ ký,
    tải không cần cookie), tải về. Chrome đóng khi tiến trình kết thúc (atexit) hoặc dong_tat_ca().
  * Mỗi lần tạo ra 2 ảnh: trả ảnh 1, giữ ảnh 2 cho lượt vẽ lại cùng câu lệnh (không tạo lại).
  * Báo lỗi xác minh / hết lượt: đưa cửa sổ ra màn hình (người dùng giải), tạm nghỉ hồ sơ; bên gọi lùi về Gemini app."""
import atexit
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request

from common import log

GOC = os.path.join(os.environ.get("BAN_CONTENT_DATA") or os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "BanContent"), "flow_chrome")
SO = os.path.join(GOC, "ho_so.json")
CONG_DAU = 9350
TRANG = "https://flow.google.com/?hl=en"     # 15/10: ép giao diện TIẾNG ANH (tài khoản tiếng Việt hiện "Dự án mới")
CHO_ANH = 240                # giây chờ một lượt tạo
NGHI_LOI = 600               # hồ sơ lỗi xác minh: nghỉ bấy nhiêu giây
_KHOA_SO = threading.Lock()
_PHIEN = {}                  # tên -> _Phien
_KHOA_PHIEN = {}             # tên -> Lock (mỗi hồ sơ một lượt tạo một lúc)
_DU = {}                     # câu lệnh gốc -> [ảnh còn dư]


def _slug(ten):
    return re.sub(r"[^\w.-]+", "_", str(ten or "").strip(), flags=re.U).strip("_")[:40] or "hoso"


def _doc_so():
    try:
        return json.load(open(SO, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ghi_so(d):
    os.makedirs(GOC, exist_ok=True)
    tam = SO + ".tmp"
    json.dump(d, open(tam, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tam, SO)


def _cap_nhat(ten, **kw):
    with _KHOA_SO:
        d = _doc_so()
        d.setdefault(ten, {}).update(kw)
        _ghi_so(d)


def ds_ho_so():
    """[{ten, thu_muc, tao, dung_luc, nghi_den, loi, so_anh}] — để hiện trên giao diện."""
    d = _doc_so()
    ra = []
    for ten, m in d.items():
        ra.append(dict(m, ten=ten, thu_muc=os.path.join(GOC, _slug(ten)),
                       dang_nghi=float(m.get("nghi_den") or 0) > time.time(), dang_mo=ten in _PHIEN))
    return sorted(ra, key=lambda x: x.get("tao", 0))


def co_ho_so():
    return bool(_doc_so())


def _chrome():
    import anh_trinh_duyet
    exe = anh_trinh_duyet._chrome()                           # noqa: SLF001
    if not exe:
        raise ValueError("không tìm thấy Chrome trên máy")
    return exe


def tao_ho_so(ten):
    """Tạo hồ sơ mới + mở Chrome HIỆN để người dùng đăng nhập Flow."""
    ten = str(ten or "").strip()
    if not ten:
        raise ValueError("đặt tên hồ sơ")
    if ten in _doc_so():
        raise ValueError(f"đã có hồ sơ '{ten}'")
    os.makedirs(os.path.join(GOC, _slug(ten)), exist_ok=True)
    _cap_nhat(ten, tao=time.time(), so_anh=0)
    mo_dang_nhap(ten)


def mo_dang_nhap(ten):
    """Mở Chrome HIỆN của hồ sơ (không cổng DevTools) ở trang Flow — để đăng nhập / giải xác minh."""
    dong(ten)
    subprocess.Popen([_chrome(), f"--user-data-dir={os.path.join(GOC, _slug(ten))}", "--no-first-run",
                      "--no-default-browser-check", "--window-size=1280,900", TRANG])
    _cap_nhat(ten, nghi_den=0, loi="")


def xoa_ho_so(ten):
    dong(ten)
    with _KHOA_SO:
        d = _doc_so()
        d.pop(ten, None)
        _ghi_so(d)
    shutil.rmtree(os.path.join(GOC, _slug(ten)), ignore_errors=True)


class _Phien:
    """Một Chrome đang chạy (ẩn ngoài màn hình) của một hồ sơ, có cổng DevTools."""

    def __init__(self, ten, cong):
        from anh_google import _WS
        self.ten, self.cong = ten, cong
        self.p = subprocess.Popen([_chrome(), f"--user-data-dir={os.path.join(GOC, _slug(ten))}",
                                   f"--remote-debugging-port={cong}", "--no-first-run", "--no-default-browser-check",
                                   "--window-position=-32000,-32000", "--window-size=1280,860",
                                   # 15/10 đo: cửa sổ ngoài màn hình -> visibilityState 'hidden' -> bấm tạo KHÔNG gửi lệnh
                                   # (reCAPTCHA / trang chờ khi ẩn). Các cờ này giữ trang "đang hiện".
                                   "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
                                   "--disable-background-timer-throttling", TRANG])
        tab = None
        for _ in range(60):
            time.sleep(0.5)
            try:
                ds = json.load(urllib.request.urlopen(f"http://127.0.0.1:{cong}/json", timeout=2))
            except (OSError, ValueError):
                continue
            tab = next((t for t in ds if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
            if tab:
                break
        if not tab:
            self.dong()
            raise RuntimeError("không mở được Chrome của hồ sơ (cửa sổ hồ sơ này đang mở sẵn? — đóng nó rồi thử lại)")
        self.ws = _WS(tab["webSocketDebuggerUrl"])
        self.ws.goi("Page.enable")
        try:
            self.ws.goi("Emulation.setFocusEmulationEnabled", enabled=True)   # trang tưởng đang được chọn
        except Exception:                                    # noqa: BLE001
            pass
        self.cai_dat = None

    def js(self, s):
        return self.ws.js(s)

    def cho(self, bieu_thuc, giay=30, buoc=0.5):
        han = time.time() + giay
        while time.time() < han:
            try:
                v = self.js(bieu_thuc)
            except Exception:                                    # noqa: BLE001  (trang đang chuyển)
                v = None
            if v:
                return v
            time.sleep(buoc)
        return None

    def hien_cua_so(self):
        """Đưa cửa sổ ra màn hình (giải xác minh)."""
        try:
            w = self.ws.goi("Browser.getWindowForTarget")
            self.ws.goi("Browser.setWindowBounds", windowId=w["windowId"],
                        bounds={"left": 80, "top": 60, "width": 1280, "height": 860, "windowState": "normal"})
        except Exception:                                        # noqa: BLE001
            pass

    def dong(self):
        try:
            self.ws.dong()
        except Exception:                                        # noqa: BLE001
            pass
        try:
            self.p.terminate()
            self.p.wait(10)
        except Exception:                                        # noqa: BLE001
            try:
                self.p.kill()
            except Exception:                                    # noqa: BLE001
                pass


def dong(ten):
    ph = _PHIEN.pop(ten, None)
    if ph:
        ph.dong()


def dong_tat_ca():
    for ten in list(_PHIEN):
        dong(ten)


atexit.register(dong_tat_ca)

_MOC = r"""(() => {
  if (window.__bc_kq) return 'da';
  window.__bc_kq = [];
  const op = XMLHttpRequest.prototype.open, sd = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m, u) { this.__bc_u = String(u); return op.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function() {
    this.addEventListener('load', () => { try {
      if (this.__bc_u.includes('rpcids=') && String(this.responseText).includes('flow-content.google/image'))
        window.__bc_kq.push(this.responseText);
    } catch (e) {} });
    return sd.apply(this, arguments);
  };
  return 'moc';
})()"""

_BAM_CHU = r"""((chu) => {
  const b = [...document.querySelectorAll('button,[role=button],[role=radio]')].find(e => (e.innerText || '').split('\n').map(s => s.trim()).includes(chu));
  if (!b) return false; b.click(); return true;
})"""


def _vao_du_an(ph):
    """Mở dự án Flow của hồ sơ (tạo mới nếu chưa có) -> True; chưa đăng nhập -> raise."""
    m = _doc_so().get(ph.ten, {})
    url = m.get("du_an_url") or TRANG
    if "hl=" not in url:
        url += ("&" if "?" in url else "?") + "hl=en"
    ph.ws.goi("Page.navigate", url=url)
    time.sleep(2)
    o = ph.cho("(() => { const u = location.href; if (u.includes('accounts.google.com')) return 'dang_nhap';"
               " if (document.querySelector('[role=textbox][aria-label]')) return 'du_an';"
               " if ([...document.querySelectorAll('*')].some(e => e.children.length < 3 && /New project/.test(e.innerText||'')))"
               " return 'trang_chu'; return ''; })()", 45)
    if o == "dang_nhap" or not o:
        raise PermissionError("hồ sơ chưa đăng nhập Flow — bấm 'Mở' trên giao diện để đăng nhập")
    if o == "trang_chu":
        ph.js(_BAM_CHU + "('New project')") or ph.js(
            "(() => { const e = [...document.querySelectorAll('*')].find(e => e.children.length < 3 && "
            "/New project/.test(e.innerText||'')); if (e) { e.click(); return true } return false })()")
        if not ph.cho("location.href.includes('/project/') && !!document.querySelector('[role=textbox][aria-label]')", 45):
            raise RuntimeError("không tạo được dự án Flow")
        _cap_nhat(ph.ten, du_an_url=ph.js("location.href"))
    for chu in ("Get started", "Got it", "Close", "Dismiss"):     # bảng giới thiệu / có gì mới
        ph.js(_BAM_CHU + f"({json.dumps(chu)})")
    # 20/10 đo: tài khoản mới (acc4-acc8) mở sẵn chế độ AGENT (khung chat "Untitled session") -> không có nút
    # "Settings trigger", vẽ ảnh / tạo video đều hỏng. Đóng khung chat (khi nó mở, chip Agent chưa hiện), rồi tắt chip Agent
    # (aria-pressed=true) bằng cú bấm thật.
    if ph.js("(() => { const t = document.querySelector('button[aria-label=\"Settings trigger\"]');"     # nút có trong DOM nhưng ẨN
             " return !(t && t.offsetParent) || document.body.innerText.includes('Untitled session') })()"):
        xy = ph.js("(() => { const e = [...document.querySelectorAll('button')].find(e => e.offsetParent && (e.innerText||'').trim() === 'close'"
                   " && e.getBoundingClientRect().x > innerWidth * 0.6 && e.getBoundingClientRect().y < 160); if (!e) return null;"
                   " const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        if xy:
            for t in ("mouseMoved", "mousePressed", "mouseReleased"):
                ph.ws.goi("Input.dispatchMouseEvent", type=t, x=xy[0], y=xy[1], button="left", clickCount=1)
            ph.cho("!!document.querySelector('button.agent-mode-chip')", 6)
    for _ in range(2):
        xy = ph.js("(() => { const e = document.querySelector('button.agent-mode-chip[aria-pressed=\"true\"]'); if (!e) return null;"
                   " const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        if not xy:
            break
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            ph.ws.goi("Input.dispatchMouseEvent", type=t, x=xy[0], y=xy[1], button="left", clickCount=1)
        time.sleep(1.2)
    ph.js(_MOC)
    ph.cai_dat = None


def _chon_cai_dat(ph, ti_le):
    if ph.cai_dat == ti_le:
        return
    ph.js("document.querySelector('button[aria-label=\"Settings trigger\"]').click()")
    time.sleep(0.8)
    for chu in ("Image", ti_le, "x2"):
        ph.js(_BAM_CHU + f"({json.dumps(chu)})")
        time.sleep(0.3)
    ton = ph.js("(() => { const t = document.body.innerText.match(/Generating will use ([\\d,.]+) credits?/); return t ? t[1] : '' })()")
    ph.ws.goi("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    ph.ws.goi("Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    if ton and ton.replace(",", "").replace(".", "") != "0":
        raise RuntimeError(f"Flow báo tạo ảnh tốn {ton} điểm — dừng dùng Flow (lùi về Gemini)")
    ph.cai_dat = ti_le


def _bam(ph, chon):
    """Bấm chuột thật (Input.dispatchMouseEvent) vào giữa phần tử khớp bộ chọn CSS."""
    r = ph.js("(() => { const e = document.querySelector(" + json.dumps(chon) + "); if (!e) return null;"
              " const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
    if not r:
        raise RuntimeError("không thấy nút " + chon)
    for t in ("mouseMoved", "mousePressed", "mouseReleased"):
        ph.ws.goi("Input.dispatchMouseEvent", type=t, x=r[0], y=r[1], button="left", clickCount=1)


def _tao(ph, prompt, ti_le):
    """Gõ câu lệnh, bấm tạo, chờ -> [link ảnh] (rỗng nếu lỗi; lỗi chữ trên trang trong ph.loi)."""
    _chon_cai_dat(ph, ti_le)
    truoc = ph.js("window.__bc_kq ? window.__bc_kq.length : -1")
    if truoc == -1:
        ph.js(_MOC)
        truoc = 0
    ph.js("(() => { const e = document.querySelector('[role=textbox][aria-label]'); e.focus();"
          " document.execCommand('selectAll'); document.execCommand('delete'); return true })()")
    ph.ws.goi("Input.insertText", text=prompt)
    if not ph.cho("(() => { const b = document.querySelector('button[aria-label=\"Start generation\"]');"
                  " return b && !b.disabled })()", 10):
        raise RuntimeError("nút tạo không bật (câu lệnh chưa vào ô?)")
    da_co = {i for i, _ in _link(ph.js("(window.__bc_kq || [])") or [], None)}   # ảnh CŨ của dự án (trả về kèm)
    _bam(ph, 'button[aria-label="Start generation"]')       # bấm chuột THẬT (sự kiện tin cậy) — .click() JS có lúc bị bỏ qua
    dong1 = prompt.split("\n", 1)[0]                          # đoạn ĐẶC TRƯNG của câu lệnh (câu nào cũng mở bằng "Create…")
    dau = max(re.findall(r"[A-Za-z0-9 ,.:;()'-]{8,}", dong1[-160:]) or [dong1[-40:]], key=len)[-50:]
    han = time.time() + CHO_ANH
    link = []
    while time.time() < han:
        time.sleep(3)
        try:
            kq = ph.js(f"(window.__bc_kq || []).slice({int(truoc)})") or []
        except Exception:                                        # noqa: BLE001
            kq = []
        link = [x for x in _link(kq, dau) if x[0] not in da_co]
        if len(link) >= 2:
            return [u for _, u in link]
        loi = ph.js("(() => { const t = document.body.innerText; const m = t.match(/(unusual traffic|verify|captcha|"
                    "limit|quota|try again later|couldn.t generate|violat|policy|Something went wrong)[^\\n]{0,120}/i);"
                    " return m ? m[0] : '' })()")
        if loi and not link:
            ph.loi = loi
            return []
    ph.loi = "hết giờ chờ"
    return [u for _, u in link]


# link ảnh trong phản hồi: "...image/<id>?Expires\\u003d…\\u0026KeyName…" (dấu = và & bị thoát 1-2 lớp)
_URL = re.compile(r'https://flow-content\.google/image/([0-9a-f-]+)\?(?:[^"\\]|\\+u00[0-9a-fA-F]{2})*')


def _link(kq, dau):
    """[(id, url)] ảnh trong các phản hồi; dau: đoạn câu lệnh phải đứng trước link (None = mọi ảnh)."""
    ra, thay = [], set()
    for t in kq:
        for m in _URL.finditer(t):
            if dau is not None and dau not in t[max(0, m.start() - 2500):m.start()]:
                continue
            if m.group(1) in thay:
                continue
            thay.add(m.group(1))
            u = re.sub(r"\\+u003d", "=", m.group(0))
            u = re.sub(r"\\+u0026", "&", u)
            ra.append((m.group(1), u))
    return ra


_GIU = {}                    # tên hồ sơ -> số luồng đang giữ (vẽ ảnh / tạo video)
_KHOA_GIU = threading.Lock()


def _giu_ho_so(ten_ds, bo=()):
    """Chọn và GIỮ một hồ sơ trong ten_ds (trừ bo): ít luồng giữ nhất trước (rảnh = 0). Trả tên | None."""
    with _KHOA_GIU:
        ung = [t for t in ten_ds if t not in bo]
        if not ung:
            return None
        t = min(ung, key=lambda x: _GIU.get(x, 0))
        _GIU[t] = _GIU.get(t, 0) + 1
        return t


def _tha_ho_so(ten):
    with _KHOA_GIU:
        _GIU[ten] = max(0, _GIU.get(ten, 1) - 1)


def so_ho_so_dung_duoc():
    return sum(1 for h in ds_ho_so() if not h["dang_nghi"])


def ve(prompt, thu, ten_file, ti_le="16:9"):
    """Vẽ một ảnh qua Flow -> đường dẫn file đã tải | None (chưa có hồ sơ / mọi hồ sơ lỗi — bên gọi lùi về Gemini)."""
    goc = re.sub(r"\s*(Remember: NO writing at all\.|Absolutely NO writing anywhere\.)\s*$", "", prompt).strip()
    du = _DU.get(goc)
    while du:                                                  # ảnh thứ hai của lần tạo trước (lượt vẽ lại)
        f = du.pop(0)
        if os.path.isfile(f):
            dich = os.path.join(thu, ten_file)
            os.replace(f, dich)
            return dich
    ds = [h for h in ds_ho_so() if not h["dang_nghi"]]
    # 22/10 user ("nhiều luồng"): mỗi luồng GIỮ CHỖ một hồ sơ RẢNH (dưới khoá chung) — trước đây các luồng cùng xếp
    # theo .locked() một lúc nên cùng chọn hồ sơ đầu rồi chờ nhau. Hết hồ sơ rảnh thì xếp hồ sơ ít người chờ nhất.
    da_thu = set()
    while True:
        ten = _giu_ho_so([h["ten"] for h in ds], da_thu)
        if ten is None:
            break
        da_thu.add(ten)
        try:
            khoa = _KHOA_PHIEN.setdefault(ten, threading.Lock())
            with khoa:
                try:
                    ph = _PHIEN.get(ten)
                    if ph is None:
                        ph = _Phien(ten, CONG_DAU + list(_doc_so()).index(ten) % 40)
                        _PHIEN[ten] = ph
                        _vao_du_an(ph)
                    ph.loi = ""
                    link = _tao(ph, prompt, ti_le)
                except PermissionError as e:
                    log(f"    ! Flow '{ten}': {e}")
                    _cap_nhat(ten, nghi_den=time.time() + NGHI_LOI, loi=str(e)[:160])
                    dong(ten)
                    continue
                except Exception as e:                               # noqa: BLE001
                    log(f"    ! Flow '{ten}': {type(e).__name__}: {str(e)[:140]}")
                    dong(ten)
                    continue
                if not link:
                    loi = getattr(ph, "loi", "") or "không có ảnh"
                    log(f"    ! Flow '{ten}': {loi[:140]}")
                    if re.search(r"unusual|verify|captcha", loi, re.I):
                        ph.hien_cua_so()                           # để người dùng giải xác minh
                        _cap_nhat(ten, nghi_den=time.time() + NGHI_LOI, loi="cần xác minh: " + loi[:120])
                    elif re.search(r"limit|quota|later", loi, re.I):
                        _cap_nhat(ten, nghi_den=time.time() + 6 * 3600, loi="hết lượt: " + loi[:120])
                        dong(ten)
                    continue
            os.makedirs(thu, exist_ok=True)
            tep = []
            for i, u in enumerate(link[:2]):
                dich = os.path.join(thu, ten_file if i == 0 else f"_du_{os.getpid()}_{time.time_ns()}.png")
                try:
                    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                        data = r.read()
                    from PIL import Image
                    import io
                    Image.open(io.BytesIO(data)).convert("RGB").save(dich)
                    tep.append(dich)
                except Exception as e:                               # noqa: BLE001
                    log(f"    ! Flow tải ảnh lỗi: {str(e)[:100]}")
            if tep:
                if len(tep) > 1:
                    _DU.setdefault(goc, []).extend(tep[1:])
                _cap_nhat(ten, dung_luc=time.time(), so_anh=int(_doc_so().get(ten, {}).get("so_anh") or 0) + len(tep), loi="")
                if tep[0] != os.path.join(thu, ten_file):
                    os.replace(tep[0], os.path.join(thu, ten_file))
                return os.path.join(thu, ten_file)
        finally:
            _tha_ho_so(ten)
    return None
