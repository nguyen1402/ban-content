# -*- coding: utf-8 -*-
"""VẼ ẢNH QUA GOOGLE FLOW (Nano Banana, 0 điểm) — 15/10/2026 user: Gemini app trừ ~17 điểm/ảnh và cạn sau một dự án;
Flow (flow.google.com) ghi "Generating will use 0 credits" cho ảnh.

Vì sao phải lái Chrome thật: lệnh tạo ảnh của Flow (batchexecute rpcid ogiZ0b) kèm mã reCAPTCHA Enterprise do trang tự
sinh bằng JavaScript cho MỖI lần tạo -> không gọi thẳng từ Python được. Chrome đời mới (>=136) cũng không cho điều khiển
hồ sơ hằng ngày qua DevTools -> dùng HỒ SƠ RIÊNG do người dùng tạo bằng nút "＋ Hồ sơ Chrome Flow" trên giao diện, đăng
nhập một lần.

  * Hồ sơ: %USERPROFILE%\\BanContent\\flow_chrome\\<tên>\\ ; sổ: flow_chrome\\ho_so.json (dự án Flow, hết lượt…).
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

# 23/10 user: dữ liệu riêng ra NGOÀI AppData (C:\Users\<tên>\BanContent). Mở app từ trong ứng dụng Claude (gói Store) thì
# Windows chuyển hướng mọi thứ ghi vào AppData\Local sang thư mục riêng của Claude -> mở bằng bấm đúp .bat không thấy hồ sơ.
GOC = os.path.join(os.environ.get("BAN_CONTENT_DATA") or os.path.join(os.path.expanduser("~"), "BanContent"), "flow_chrome")
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


def _cong_anh(ten, n):
    """Cộng số ảnh đã vẽ của hồ sơ (đọc + ghi trong cùng khoá: nhiều luồng xong cùng lúc không đếm thiếu)."""
    with _KHOA_SO:
        d = _doc_so()
        m = d.setdefault(ten, {})
        m.update(so_anh=int(m.get("so_anh") or 0) + n, dung_luc=time.time(), loi="")
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


# 26/10 user: "mỗi lần mở tab toàn bị báo thoát đột ngột" — Chrome hồ sơ bị TẮT CƯỠNG BỨC: (1) là tiến trình con của
# Python nên dừng server / lượt chạy là Windows giết luôn, (2) dong() dùng terminate(). Nay: mở Chrome TÁCH khỏi tiến
# trình Python, đóng êm bằng Browser.close (như bấm X), trước mỗi lần mở đánh dấu lần thoát trước là bình thường và
# thêm cờ ẩn bảng "khôi phục trang".
CO_EM = ["--hide-crash-restore-bubble", "--disable-session-crashed-bubble"]


def danh_dau_thoat_em(thu):
    """Sửa Default/Preferences của hồ sơ: lần thoát trước = bình thường (Chrome thôi hỏi khôi phục trang)."""
    p = os.path.join(thu, "Default", "Preferences")
    try:
        d = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return
    pr = d.setdefault("profile", {})
    if pr.get("exit_type") == "Normal" and pr.get("exited_cleanly") is True:
        return
    pr["exit_type"], pr["exited_cleanly"] = "Normal", True
    try:
        tam = p + ".bc_tam"
        json.dump(d, open(tam, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tam, p)
    except OSError:
        pass


def mo_chrome_tach(args, thu):
    """Mở Chrome TÁCH khỏi tiến trình Python (dừng server / lượt chạy không kéo Chrome chết theo) -> Popen."""
    danh_dau_thoat_em(thu)
    args = [args[0]] + CO_EM + list(args[1:])
    if os.name != "nt":
        return subprocess.Popen(args, start_new_session=True)
    co = 0x00000008 | 0x00000200                           # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    try:
        return subprocess.Popen(args, creationflags=co | 0x01000000)   # + CREATE_BREAKAWAY_FROM_JOB (thoát job của Python)
    except OSError:                                          # job không cho tách ra: vẫn mở được, chỉ không thoát job
        return subprocess.Popen(args, creationflags=co)


def dong_em(cong, cho=10):
    """Đóng Chrome ở cổng DevTools bằng Browser.close (như bấm X) -> True nếu đã đóng hẳn."""
    from anh_google import _WS
    try:
        u = json.load(urllib.request.urlopen(f"http://127.0.0.1:{cong}/json/version", timeout=2))["webSocketDebuggerUrl"]
    except (OSError, ValueError, KeyError):
        return True                                          # không còn mở
    try:
        w = _WS(u)
        try:
            w.goi("Browser.close")
        finally:
            w.dong()
    except Exception:                                        # noqa: BLE001  (Chrome đóng ngay khi nhận lệnh)
        pass
    han = time.time() + cho
    while time.time() < han:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{cong}/json/version", timeout=1)
        except OSError:
            return True
        time.sleep(0.5)
    return False


def _giet_chrome_ho_so(ten):
    """Đóng MỌI Chrome đang giữ thư mục hồ sơ (kể cả do tiến trình khác mở, cửa sổ ẩn ngoài màn hình). 23/10 user: bấm
    'Mở' mà không thấy gì — Chrome của hồ sơ đang chạy ẩn ở -32000 (một lượt vẽ khác) nên lệnh mở chỉ thêm cửa sổ vào
    phiên ẩn đó. 26/10: đóng êm qua cổng DevTools trước, còn sót mới tắt cưỡng bức."""
    if ten in _doc_so():
        dong_em(CONG_DAU + list(_doc_so()).index(ten) % 40)
    if os.name != "nt":
        return
    thu = os.path.join(GOC, _slug(ten)).replace("'", "''")
    lenh = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -and "
            f"$_.CommandLine -match ([regex]::Escape('--user-data-dir={thu}') + '(\\s|\"|$)') }} | "   # acc1 ≠ acc10
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", lenh], capture_output=True, timeout=30,
                       creationflags=0x08000000)
    except (OSError, subprocess.SubprocessError):
        pass
    time.sleep(1.0)


def mo_dang_nhap(ten):
    """Mở Chrome HIỆN của hồ sơ (không cổng DevTools) ở trang Flow — để đăng nhập / giải xác minh."""
    dong(ten)
    _giet_chrome_ho_so(ten)
    mo_chrome_tach([_chrome(), f"--user-data-dir={os.path.join(GOC, _slug(ten))}", "--no-first-run",
                      # 23/10 user: không ép vị trí thì Chrome mở lại ở chỗ NHỚ từ lần chạy ẩn (-1250 / -32000) -> người dùng
                      # không thấy cửa sổ để đăng nhập
                      "--no-default-browser-check", "--window-position=80,60", "--window-size=1280,900", TRANG],
                   os.path.join(GOC, _slug(ten)))
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
        self.the_he = 0                      # tăng mỗi lần trang tải lại (_vao_du_an) -> lượt đang chờ biết kết quả cũ mất
        self.dang_cho = []                   # các lượt tạo đang chờ ảnh trên tab này (gửi song song)
        self.da_nhan = set()                 # id ảnh đã có lượt nhận (không chia nhầm cho lượt khác)
        self.p = None
        # 25/10: Chrome của hồ sơ còn mở sẵn ở đúng cổng (server trước tắt đột ngột, atexit không chạy) -> GẮN VÀO luôn,
        # trước đây mở Chrome mới bị từ chối ("cửa sổ hồ sơ này đang mở sẵn") và hồ sơ hỏng tới khi tự đóng cửa sổ
        if not self._tab_flow():
            self.p = mo_chrome_tach([_chrome(), f"--user-data-dir={os.path.join(GOC, _slug(ten))}",
                                       f"--remote-debugging-port={cong}", "--no-first-run", "--no-default-browser-check",
                                       "--window-position=80,60", "--window-size=1280,860",
                                       # Giữ trang "đang hiện" để reCAPTCHA và lệnh tạo ảnh chạy mượt
                                       "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
                                       "--disable-background-timer-throttling", TRANG], os.path.join(GOC, _slug(ten)))
        else:
            log(f"    Flow '{ten}': dùng lại Chrome đang mở ở cổng {cong}")
        tab = None
        for _ in range(60):
            time.sleep(0.5)
            try:
                ds = json.load(urllib.request.urlopen(f"http://127.0.0.1:{cong}/json", timeout=2))
            except (OSError, ValueError):
                continue
            trang = [t for t in ds if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            tab = next((t for t in trang if "flow.google" in str(t.get("url"))), trang[0] if trang else None)
            if tab:
                break
        if not tab:
            if self.p is not None:
                self.p.terminate()
            raise RuntimeError("không mở được Chrome của hồ sơ (cửa sổ hồ sơ này đang mở sẵn? — đóng nó rồi thử lại)")
        self.ws = _WS(tab["webSocketDebuggerUrl"])
        self.ws.goi("Page.enable")
        try:
            self.hien_cua_so()
        except Exception:
            pass
        try:
            self.ws.goi("Emulation.setFocusEmulationEnabled", enabled=True)   # trang tưởng đang được chọn
        except Exception:                                    # noqa: BLE001
            pass
        self.cai_dat = None

    def _tab_flow(self):
        try:
            ds = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.cong}/json", timeout=1))
        except (OSError, ValueError):
            return False
        return any(t.get("type") == "page" and "flow.google" in str(t.get("url")) for t in ds)

    def con_song(self):
        try:
            return (self.p is None or self.p.poll() is None) and self.js("1") == 1
        except Exception:                                        # noqa: BLE001
            return False

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
        """26/10: đóng ÊM (Browser.close, như bấm X) rồi mới tắt cưỡng bức nếu Chrome không chịu đóng — terminate() ngay
        làm lần mở sau hiện báo "Chrome thoát đột ngột"."""
        try:
            self.ws.dong()
        except Exception:                                        # noqa: BLE001
            pass
        if dong_em(self.cong) or self.p is None:
            return
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


def hien_tat_ca_cua_so():
    """Đưa toàn bộ cửa sổ Chrome đang chạy của các hồ sơ Flow lên màn hình chính."""
    from anh_google import _WS
    dem = 0
    with _KHOA_SO:
        for ten, ph in list(_PHIEN.items()):
            try:
                ph.hien_cua_so()
                dem += 1
            except Exception:
                pass
    for cong in range(9350, 9360):
        try:
            ds = json.load(urllib.request.urlopen(f"http://127.0.0.1:{cong}/json", timeout=0.5))
            tab = next((t for t in ds if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
            if tab:
                ws = _WS(tab["webSocketDebuggerUrl"])
                w = ws.goi("Browser.getWindowForTarget")
                ws.goi("Browser.setWindowBounds", windowId=w["windowId"],
                       bounds={"left": 100 + (cong - 9350) * 30, "top": 80 + (cong - 9350) * 30, "width": 1280, "height": 860, "windowState": "normal"})
                ws.dong()
                dem += 1
        except Exception:
            pass
    return dem


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
  // 23/10 đo (bản boq 20261021): lệnh tạo ảnh ogiZ0b đi qua fetch, không còn XHR -> móc cả fetch
  const f0 = window.fetch;
  window.__bc_gui = 0;   // 25/10: số lệnh tạo ảnh (ogiZ0b) ĐÃ GỬI ĐI — bấm tạo mà số này không tăng = Flow chưa nhận lệnh
  window.fetch = function(x) { try { if (String((x && x.url) || x).includes('ogiZ0b')) window.__bc_gui++; } catch (e) {}
    return f0.apply(this, arguments).then(r => { try { const u = String(r.url);
      if (u.includes('rpcids=')) r.clone().text().then(t => { if (t.includes('flow-content.google/image')) window.__bc_kq.push(t); }).catch(() => {});
    } catch (e) {} return r; }); };
  return 'moc';
})()"""

_BAM_CHU = r"""((chu) => {
  const b = [...document.querySelectorAll('button,[role=button],[role=radio]')].find(e => (e.innerText || '').split('\n').map(s => s.trim()).includes(chu));
  if (!b) return false; b.click(); return true;
})"""


# 26/10 user (acc3/acc4/acc5 cùng bị báo "chưa đăng nhập Flow" lúc 20:21, tự bấm vào vẫn vào bình thường): trước đây
# (1) thấy accounts.google.com / flow.google.com/about MỘT lần là kết luận đăng xuất — mà Chrome vừa mở thường đi vòng qua
# accounts.google.com để làm mới phiên rồi tự quay về, Flow cũng hiện /about thoáng qua; (2) 45 s chưa tải xong (nhiều Chrome
# mở cùng lúc, máy lag) cũng bị coi là đăng xuất -> nghỉ 6 giờ oan. Nay trang đăng nhập phải ĐỨNG YÊN ĐĂNG_NHAP_GIU giây
# (có ô nhập email / nút Sign in) mới tính là đăng xuất; tải chậm thì báo lỗi thường.
_TRANG_THAI = ("(() => { const u = location.href, t = document.body ? (document.body.innerText || '') : '';"
               " if (t.includes('Project not found')) return 'khong_thay';"
               " if (document.querySelector('[role=textbox][aria-label]')) return 'du_an';"
               # trang Google (đòi email / mật khẩu, hay "Verify it's you" đòi đăng nhập lại — acc4/acc5 26/10): đứng yên
               # đủ DANG_NHAP_GIU giây mới tính là cần đăng nhập; chuyển tiếp làm mới phiên thì đi qua nhanh
               " if (u.includes('accounts.google.com')) return 'dang_nhap';"
               " if (u.includes('flow.google.com/about')) return 'gioi_thieu';"
               " if ([...document.querySelectorAll('*')].some(e => e.children.length < 3 && /New project/.test(e.innerText||'')))"
               " return 'trang_chu'; return ''; })()")
DANG_NHAP_GIU = 20


_SIGN_IN = ("(() => { const a = [...document.querySelectorAll('a[href*=\"accounts.google.com/ServiceLogin\"]')]"
            ".find(e => e.offsetParent); return a ? a.href : '' })()")


def _trang_thai(ph, giay=60):
    """'du_an' | 'trang_chu' | 'khong_thay' | 'dang_nhap' (trang đăng nhập đứng yên) | '' (tải không xong).
    Đo 26/10 (acc3-acc5): tài khoản Google vẫn đăng nhập (cookie SID) nhưng phiên Flow hết hạn -> dự án chuyển về /about có
    link "Sign in" passive; bấm là Google tự đăng nhập lại không hỏi mật khẩu (người dùng bấm tay thấy "vào bình thường").
    -> tự đi theo link đó một lần trước khi kết luận."""
    han, tu, da_bam = time.time() + giay, None, False
    while time.time() < han:
        try:
            o = ph.js(_TRANG_THAI) or ""
        except Exception:                                    # noqa: BLE001  (trang đang chuyển)
            o = ""
        if o in ("du_an", "trang_chu", "khong_thay"):
            return o
        if o == "gioi_thieu" and not da_bam:
            try:
                href = ph.js(_SIGN_IN)
            except Exception:                                # noqa: BLE001
                href = ""
            if href:
                da_bam, tu = True, None
                log(f"    Flow '{getattr(ph, 'ten', '')}': phiên Flow hết hạn -> tự bấm Sign in (tài khoản Google còn đăng nhập)")
                ph.ws.goi("Page.navigate", url=href)
                time.sleep(2)
                continue
        if o in ("dang_nhap", "gioi_thieu"):
            tu = tu or time.time()
            if time.time() - tu >= DANG_NHAP_GIU:
                return "dang_nhap"
        else:
            tu = None                                        # đang chuyển trang / đang tải: chưa kết luận
        time.sleep(1)
    return ""


def _vao_du_an(ph):
    """Mở dự án Flow của hồ sơ (tạo mới nếu chưa có) -> True; chưa đăng nhập -> raise."""
    m = _doc_so().get(ph.ten, {})
    url = m.get("du_an_url") or TRANG
    if "hl=" not in url:
        url += ("&" if "?" in url else "?") + "hl=en"
    ph.ws.goi("Page.navigate", url=url)
    ph.the_he = getattr(ph, "the_he", 0) + 1                  # trang tải lại: kết quả các lượt đang chờ đã mất
    time.sleep(2)
    o = _trang_thai(ph)
    if o == "khong_thay":
        # Dự án cũ đã hết hạn hoặc bị xóa trên Flow -> chuyển về trang chủ để tự tạo dự án mới
        ph.ws.goi("Page.navigate", url=TRANG)
        time.sleep(2)
        o = ph.cho("(() => { if (document.querySelector('[role=textbox][aria-label]')) return 'du_an';"
                   " if ([...document.querySelectorAll('*')].some(e => e.children.length < 3 && /New project/.test(e.innerText||'')))"
                   " return 'trang_chu'; return ''; })()", 45)
    if o == "dang_nhap":
        raise PermissionError("hồ sơ chưa đăng nhập Flow — bấm 'Mở' trên giao diện để đăng nhập")
    if not o:                                                  # tải chậm (máy bận) — KHÔNG phải đăng xuất, không nghỉ 6 giờ
        raise RuntimeError("trang Flow tải quá chậm (chưa hiện ô câu lệnh)")
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


# 26/10 user (ảnh chụp: ô câu lệnh hiện "Start / End" và "Video · 720p · 10s x1", lượt vẽ đứng im): tab còn ở chế độ VIDEO
# (Flow nhớ chế độ cuối của dự án; tạo video hook / người dùng bấm tay trong cửa sổ) nhưng ph.cai_dat vẫn nhớ "đã chọn Image"
# nên bỏ qua bước chọn -> gõ câu lệnh vào ô video, chờ ảnh 4 phút. Nay mỗi lượt đọc lại chế độ thật trên trang.
_LA_VIDEO = ("(() => { const t = document.querySelector('button[aria-label=\"Settings trigger\"]');"
             " if (t && /\\bVideo\\b/.test(t.innerText || '')) return true;"
             " const nut = [...document.querySelectorAll('button,[role=button]')].filter(e => e.offsetParent)"
             ".map(e => (e.innerText || '').trim());"
             " return nut.includes('Start') && nut.includes('End'); })()")


def _thoat(ph):
    for t in ("keyDown", "keyUp"):
        ph.ws.goi("Input.dispatchKeyEvent", type=t, key="Escape", code="Escape", windowsVirtualKeyCode=27)


def _chon_cai_dat(ph, ti_le):
    if ph.cai_dat == ti_le and not ph.js(_LA_VIDEO):
        return
    for lan in range(3):
        _bam_js(ph, "document.querySelector('button[aria-label=\"Settings trigger\"]')")   # bấm chuột thật
        time.sleep(0.8)
        for chu in ("Image", ti_le, "x2"):
            ph.js(_BAM_CHU + f"({json.dumps(chu)})")
            time.sleep(0.4)
        ton = ph.js("(() => { const t = document.body.innerText.match(/Generating will use ([\\d,.]+) credits?/); return t ? t[1] : '' })()")
        _thoat(ph)
        time.sleep(0.5)
        if not ph.js(_LA_VIDEO):
            break
        log(f"    Flow '{ph.ten}': tab đang ở chế độ Video -> chọn lại Image (lần {lan + 1})")
    else:
        ph.cai_dat = None
        raise RuntimeError("tab Flow kẹt ở chế độ Video, không chuyển được sang Image")
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


def _bam_js(ph, js_phan_tu):
    """Bấm chuột THẬT vào giữa phần tử (biểu thức JS trả phần tử) -> True nếu thấy phần tử."""
    xy = ph.js("(() => { const x = " + js_phan_tu + "; if (!x) return null; x.scrollIntoView({block: 'nearest'});"
               " const r = x.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
    if xy:
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            ph.ws.goi("Input.dispatchMouseEvent", type=t, x=xy[0], y=xy[1], button="left", clickCount=1)
    return bool(xy)


_SO_CHIP = "document.querySelectorAll('button.chip-container').length"


class ChuaDongY(PermissionError):
    """Tài khoản Flow chưa bấm 'I agree' cho việc tải ảnh lên — hồ sơ nghỉ tới khi người dùng mở lại."""
THAM_CHIEU_TOI_DA = 3            # 23/10 đo: gắn 4 ảnh thì nút tạo của Flow không bật


def _bo_tham_chieu(ph):
    """Gỡ mọi ảnh tham chiếu (chip 'Ingredient') còn trong ô câu lệnh."""
    for _ in range(8):
        if not ph.js(_SO_CHIP):
            return
        if not _bam_js(ph, "document.querySelector('button[aria-label=\"Clear prompt\"]')"):
            _bam_js(ph, "document.querySelector('button.chip-container')")
        time.sleep(0.6)


def _ten_tham_chieu(f):
    """Tên tải lên Flow theo NỘI DUNG ảnh (sb_<md5>.png) — cùng ảnh thì cùng tên, tìm lại được trong kho của dự án Flow."""
    import hashlib
    h = hashlib.md5(open(f, "rb").read()).hexdigest()[:14]
    thu = os.path.join(GOC, "_tham_chieu")
    os.makedirs(thu, exist_ok=True)
    dich = os.path.join(thu, f"sb_{h}.png")
    if not os.path.isfile(dich):
        from PIL import Image
        Image.open(f).convert("RGB").save(dich)
    return dich


def _gan_tham_chieu(ph, files):
    """23/10 user (storyboard nhân vật nhất quán): gắn ảnh tham chiếu vào ô câu lệnh — nút 'Add ingredients to the prompt
    box' -> bảng kho ảnh (tải lên nếu chưa có, chặn input.click() như flow_video) -> bấm ảnh -> 'Add to prompt' -> chip.
    Đo 23/10: Flow giữ đúng nhân vật / đồ vật của ảnh tham chiếu; chip tự gỡ sau mỗi lượt tạo."""
    t0 = time.time()
    _bo_tham_chieu(ph)
    anh_ds = [_ten_tham_chieu(f) for f in files[:THAM_CHIEU_TOI_DA]]

    def mo_bang():
        if ph.js("document.body.innerText.includes('Upload media')"):
            return
        if not _bam_js(ph, "document.querySelector('button[aria-label=\"Add ingredients to the prompt box\"]')"):
            raise RuntimeError("không thấy nút thêm ảnh tham chiếu của Flow")
        if not ph.cho("document.body.innerText.includes('Upload media')", 10):
            raise RuntimeError("không mở được bảng ảnh tham chiếu")

    def item(ten):
        return ("[...document.querySelectorAll('button.asset-item')].find(e => (e.innerText||'').trim()"
                ".split(String.fromCharCode(10))[0].trim() === " + json.dumps(ten) + ")")

    def san_sang(ten):
        return ph.js(f"(() => {{ const e = {item(ten)}; if (!e || e.querySelector('mat-spinner')) return false;"
                     " const i = e.querySelector('img'); return !!(i && i.complete && i.naturalWidth) })()")

    # 23/10 user "quá chậm": ảnh tham chiếu đã có trong kho của dự án Flow (tên theo nội dung) thì dùng lại; ảnh chưa có
    # thì tải lên CÙNG MỘT LẦN (trước đây mỗi ảnh mở bảng + tải + chờ riêng)
    mo_bang()
    time.sleep(0.8)
    thieu = [a for a in anh_ds if not ph.js(f"!!({item(os.path.basename(a))})")]
    if thieu:
        ph.js(r"""(() => { window.__bc_in = null; if (!window.__bc_click) { const c = HTMLInputElement.prototype.click;
          window.__bc_click = c; HTMLInputElement.prototype.click = function() { if (this.type === 'file') { window.__bc_in = this; return; }
          return c.apply(this, arguments); }; } return true })()""")
        ph.js(_BAM_CHU + "('Upload media')")
        time.sleep(1.0)
        r = ph.ws.goi("Runtime.evaluate", expression="window.__bc_in || document.querySelector('input[type=file]')")
        oid = (r.get("result") or {}).get("objectId")
        if not oid:
            raise RuntimeError("không thấy ô chọn file của Flow")
        ph.ws.goi("DOM.enable")
        nhieu = ph.ws.goi("Runtime.callFunctionOn", objectId=oid, functionDeclaration="function() { return this.multiple }",
                          returnByValue=True).get("result", {}).get("value")
        cum = [thieu] if nhieu else [[a] for a in thieu]
        for c in cum:
            ph.ws.goi("DOM.setFileInputFiles", files=[os.path.abspath(a) for a in c], objectId=oid)
            if not nhieu and c is not cum[-1]:
                ph.cho(f"!!({item(os.path.basename(c[0]))})", 30, 1)
                mo_bang()
                ph.js(_BAM_CHU + "('Upload media')")
                time.sleep(1.0)
                r = ph.ws.goi("Runtime.evaluate", expression="window.__bc_in || document.querySelector('input[type=file]')")
                oid = (r.get("result") or {}).get("objectId") or oid
    han = time.time() + 120
    while time.time() < han and not all(san_sang(os.path.basename(a)) for a in anh_ds):
        if ph.js("document.body.innerText.includes('Rights to use this image')"):
            # 23/10 đo (acc5-acc8): lần ĐẦU tải ảnh lên, Flow hỏi xác nhận quyền dùng ảnh ("I agree") — người dùng tự bấm
            # một lần cho tài khoản (Mở hồ sơ -> tải một ảnh bất kỳ -> I agree); không tự đồng ý thay
            ph.js(_BAM_CHU + "('Cancel')")
            raise ChuaDongY("tài khoản chưa xác nhận 'Rights to use this image' khi tải ảnh lên Flow — bấm 'Mở' hồ sơ, "
                            "tải một ảnh bất kỳ lên và bấm I agree một lần")
        time.sleep(1)
    for k, anh in enumerate(anh_ds):
        ten = os.path.basename(anh)
        mo_bang()
        if not ph.cho(f"!!({item(ten)})", 5) or not san_sang(ten):
            raise RuntimeError("tải ảnh tham chiếu lên Flow quá lâu")
        nut = "[...document.querySelectorAll('button')].find(e => e.offsetParent && (e.innerText||'').trim() === 'Add to prompt')"
        for _ in range(5):
            mo_bang()
            _bam_js(ph, item(ten))
            ph.cho(f"!!({nut})", 3, 0.2)
            _bam_js(ph, nut)
            if ph.cho(f"{_SO_CHIP} >= {k + 1}", 4, 0.2):
                break
        else:
            raise RuntimeError("không gắn được ảnh tham chiếu vào ô câu lệnh")
    log(f"    Flow '{ph.ten}': gắn {len(anh_ds)} ảnh tham chiếu ({time.time() - t0:.0f}s"
        + (f", tải lên {len(thieu)}" if thieu else "") + ")")


_O_TAO = ("(() => { const e = document.querySelector('[role=textbox][aria-label]'); return !!(e && e.offsetParent"
          " && !/change/i.test(e.getAttribute('aria-label') || '')) })()")


def _ve_luoi(ph):
    """25/10 user ("tạo xong lại tắt tab mở tab mới"): đo 25/10 — Flow hay tự mở ảnh vừa tạo / ảnh bấm trúng ở màn hình
    SỬA (/edit/<id>, ô "What do you want to change?"): gõ câu lệnh ở đó là SỬA ảnh đó, lượt tạo hỏng -> trước đây đóng
    Chrome rồi mở lại. Quay về lưới dự án NGAY TRONG TAB (nút Back / history.back), chỉ tải lại trang khi không về được."""
    for _ in range(3):
        if not ph.js("location.pathname.includes('/edit/')"):
            break
        if not _bam_js(ph, "document.querySelector('button[aria-label=\"Back button to go to previous page\"]')"):
            ph.js("history.back()")
        ph.cho("!location.pathname.includes('/edit/')", 8)
    if not ph.cho(_O_TAO, 5):
        _vao_du_an(ph)


def cuu_phien(ten):
    """Trang Flow hỏng giữa chừng: thử về lại dự án trong CÙNG cửa sổ (không tắt Chrome); Chrome chết hẳn mới đóng."""
    ph = _PHIEN.get(ten)
    if ph is None:
        return
    try:
        if ph.con_song():
            _vao_du_an(ph)
            return
    except Exception as e:                                       # noqa: BLE001
        log(f"    Flow '{ten}': không cứu được trang ({str(e)[:80]}) -> mở lại Chrome")
    dong(ten)


def _cac_loi(ph, prompt):
    """Các dòng báo lỗi đang có trên trang — BỎ dòng là chữ câu lệnh (ô câu lệnh, lưới ảnh có 'Expand prompt'): câu lệnh có
    chữ 'limit' / 'verify' / 'later'… từng bị tưởng là Flow báo hết lượt -> hồ sơ bị tắt và nghỉ 6 giờ.
    25/10 user (ảnh chụp ô "Failed — We noticed some unusual activity"): Flow chống spam ghi "unusual ACTIVITY", bản cũ chỉ
    dò "unusual traffic" -> lượt đó chờ đủ 4 phút (acc4 lần nào cũng "hết giờ chờ")."""
    ds = ph.js(r"""(() => { const t = document.body.innerText.split('\n'); const re = /(unusual|verify|captcha|limit|quota|try again later|couldn.t generate|failed to generate|violat|policy|Something went wrong)/i;
      return t.map(s => s.trim()).filter(s => s && s.length < 220 && re.test(s)).slice(0, 60) })()""") or []
    cu = getattr(ph, "da_gui", [])
    return [x for x in ds if not any(x in p or x[:60] in p for p in [prompt] + cu)]


def _loi_trang(ph, prompt, cu=0):
    """Lỗi MỚI (sau lúc gửi): ô lỗi của lượt trước vẫn nằm trên trang -> chỉ tính khi số dòng lỗi tăng so với lúc gửi."""
    ds = _cac_loi(ph, prompt)
    return ds[0] if len(ds) > cu else ""


def _dau_rieng(ph, prompt):
    """Đoạn chữ ĐẶC TRƯNG của câu lệnh để nhận ra ảnh của nó trong phản hồi: chỉ chữ / số / cách (dấu ' " ( … Flow trả về
    dạng thoát \\u0027…), dài nhất và KHÔNG có trong câu lệnh của lượt khác đang chờ cùng tab (25/10: câu lệnh storyboard
    nào cũng mở bằng cùng dòng phong cách -> lấy đoạn ở dòng hành động riêng của ảnh)."""
    return _dau_khac(prompt, [c["prompt"] for c in ph.dang_cho] + list(getattr(ph, "da_gui", [])))


def _dau_khac(prompt, khac):
    return _dau_ds(prompt, khac)[0]


def _dau_ds(prompt, khac, n=3):
    """Tới n đoạn chữ riêng của câu lệnh (không có trong câu lệnh nào của `khac`), dài trước. 25/10 (thử 20 câu, lượt 3:
    lượt NV2 vẫn nhận ảnh của lượt BC5) -> phản hồi phải chứa ĐỦ các đoạn này mới là của lượt, không chỉ một đoạn."""
    doan = sorted({x.strip()[-60:] for x in re.findall(r"[A-Za-z0-9 ]{12,}", prompt)}, key=len, reverse=True)
    rieng = [d for d in doan if len(d) >= 12 and not any(d in k for k in khac)][:n]
    return rieng or (doan[:1] if doan else [prompt[-40:]])


def _gui(ph, prompt, ti_le, tham_chieu=None):
    """Gõ câu lệnh (kèm ảnh tham chiếu nếu có) và bấm tạo — KHÔNG chờ ảnh. Trả 'lượt' để _cho() chờ; gọi trong khoá hồ sơ.
    25/10 (thử 20 ảnh, nhiều lượt cùng tab): gắn tham chiếu đôi khi hỏng ("nút tạo không bật", "không mở được bảng ảnh
    tham chiếu") khi lưới ảnh đang đổi -> đóng bảng, gỡ chip, thử lại MỘT lần ngay trên tab trước khi tính là lỗi."""
    for lan in range(2):
        try:
            return _gui_mot(ph, prompt, ti_le, tham_chieu)
        except PermissionError:
            raise
        except Exception as e:                                   # noqa: BLE001
            if lan:
                raise
            log(f"    Flow '{ph.ten}': {str(e)[:80]} -> thử gửi lại")
            for t in ("keyDown", "keyUp"):
                ph.ws.goi("Input.dispatchKeyEvent", type=t, key="Escape", code="Escape", windowsVirtualKeyCode=27)
            time.sleep(0.8)
            _ve_luoi(ph)
            _bo_tham_chieu(ph)


def _gui_mot(ph, prompt, ti_le, tham_chieu=None):
    _ve_luoi(ph)
    _chon_cai_dat(ph, ti_le)
    truoc = ph.js("window.__bc_kq ? window.__bc_kq.length : -1")
    if truoc == -1:
        ph.js(_MOC)
        truoc = 0
    if tham_chieu:
        _gan_tham_chieu(ph, tham_chieu)
    else:
        _bo_tham_chieu(ph)
    if ph.js("location.pathname.includes('/edit/')"):            # bấm chip tham chiếu có lúc mở ảnh ở màn hình sửa
        _ve_luoi(ph)
        if tham_chieu:
            _gan_tham_chieu(ph, tham_chieu)
    ph.js("(() => { const e = document.querySelector('[role=textbox][aria-label]'); e.focus();"
          " document.execCommand('selectAll'); document.execCommand('delete'); return true })()")
    ph.ws.goi("Input.insertText", text=prompt)
    if not ph.cho("(() => { const b = document.querySelector('button[aria-label=\"Start generation\"]');"
                  " return b && !b.disabled })()", 10):
        raise RuntimeError("nút tạo không bật (câu lệnh chưa vào ô?)")
    if ph.js(_LA_VIDEO):                                         # chốt chặn: không bao giờ bấm tạo khi đang ở Video (tốn điểm)
        ph.cai_dat = None
        raise RuntimeError("ô câu lệnh đang ở chế độ Video — không bấm tạo")
    ds_dau = _dau_ds(prompt, [c["prompt"] for c in ph.dang_cho] + list(getattr(ph, "da_gui", [])))
    try:
        loi_cu = len(_cac_loi(ph, prompt))
    except Exception:                                            # noqa: BLE001
        loi_cu = 0
    luot = {"prompt": prompt, "truoc": int(truoc), "the_he": ph.the_he, "dau": ds_dau[0], "dau_ds": ds_dau, "loi_cu": loi_cu,
            "da_co": {i for i, _ in _link(ph.js("(window.__bc_kq || [])") or [], None)}}   # ảnh CŨ của dự án
    # 25/10 (thử 20 ảnh: scene 6 nhận ảnh của scene 15): đoạn đặc trưng của lượt ĐANG CHỜ có thể nằm trong câu lệnh MỚI
    # (đoạn đó chọn lúc lượt cũ gửi, khi chưa có câu lệnh mới để so — thường rơi vào mô tả nhân vật dùng chung) -> lượt cũ
    # nhận luôn ảnh của lượt mới. Chọn lại đoạn cho lượt cũ, khác hẳn câu lệnh mới.
    for c in ph.dang_cho:
        con = [d for d in c.get("dau_ds") or [c["dau"]] if d not in prompt]
        c["dau_ds"] = con or _dau_ds(c["prompt"], [prompt] + [x["prompt"] for x in ph.dang_cho if x is not c])
        c["dau"] = c["dau_ds"][0]
    ph.dang_cho.append(luot)
    # 25/10 (đo: lượt "hết giờ chờ" = 55 phản hồi sau khi bấm, KHÔNG phản hồi nào có câu lệnh của lượt -> lần bấm không ăn,
    # trước đây chờ đủ 4 phút): bấm rồi đợi lệnh tạo thật sự đi khỏi trang; 8 s chưa đi thì bấm lại, vẫn không thì báo lỗi
    gui0 = ph.js("window.__bc_gui === undefined ? -1 : window.__bc_gui")
    for _ in range(2):
        _bam(ph, 'button[aria-label="Start generation"]')   # bấm chuột THẬT (sự kiện tin cậy) — .click() JS có lúc bị bỏ qua
        if gui0 is None or gui0 < 0 or ph.cho(f"(window.__bc_gui || 0) > {int(gui0)}", 8, 0.25):
            break                                            # (trang móc bản cũ, không đếm được: bấm một lần như trước)
    else:
        ph.dang_cho.remove(luot)
        raise RuntimeError("Flow không nhận lệnh tạo (bấm 2 lần)")
    luot["t0"] = time.time()
    ph.da_gui = (getattr(ph, "da_gui", []) + [prompt])[-60:]
    # chờ ô câu lệnh trống lại (Flow đã nhận lượt này) rồi mới nhả khoá cho lượt kế gõ tiếp
    ph.cho("(() => { const e = document.querySelector('[role=textbox][aria-label]');"
           " return !e || !(e.innerText || '').trim() })()", 4, 0.25)
    return luot


_LOI_CHUNG = re.compile(r"verify|captcha|limit|quota|later", re.I)   # lỗi của cả tài khoản / tab, không riêng lượt


def _cho(ph, luot):
    """Chờ ảnh của MỘT lượt đã gửi (không giữ khoá hồ sơ — các lượt khác vẫn gửi tiếp) -> [link] ([] nếu lỗi: ph.loi)."""
    prompt, dau, t0 = luot["prompt"], luot["dau"], luot["t0"]
    han = t0 + CHO_ANH
    link, mot, loi_tu = [], 0, 0
    try:
        while time.time() < han:
            time.sleep(1.5)
            if _PHIEN.get(ph.ten) is not ph or ph.the_he != luot["the_he"]:
                luot["loi"] = "trang Flow đã tải lại / đóng giữa chừng"
                return []
            try:
                kq = ph.js(f"(window.__bc_kq || []).slice({luot['truoc']})") or []
            except Exception:                                    # noqa: BLE001
                kq = []
            khac = [c["dau"] for c in ph.dang_cho if c is not luot]
            link = [x for x in _link(kq, luot["dau"], len(prompt) + 3000, khac, luot.get("dau_ds"))
                    if x[0] not in luot["da_co"] and x[0] not in ph.da_nhan]
            if len(link) >= 2:
                break
            if link:                                             # Flow chỉ trả 1 ảnh (ảnh kia bị lọc): chờ thêm 20 s rồi dùng
                mot = mot or time.time()
                if time.time() - mot > 20:
                    break
            try:
                loi = _loi_trang(ph, prompt, luot.get("loi_cu", 0)) if time.time() - t0 > 6 else ""
            except Exception:                                    # noqa: BLE001  (trang đang vẽ lại)
                loi = ""
            if loi and re.search(r"unusual", loi, re.I) and not luot.get("da_nghi"):
                # chống spam của Flow: ngừng GỬI THÊM vào hồ sơ này ngay (lượt đang chờ vẫn chờ nốt theo luật bên dưới)
                luot["da_nghi"] = True
                _cap_nhat(ph.ten, nghi_den=time.time() + NGHI_LOI, loi="Flow chống spam: " + loi[:100])
                log(f"    Flow '{ph.ten}': Flow báo 'unusual activity' -> nghỉ {NGHI_LOI // 60} phút")
            if loi and not link:
                # nhiều lượt cùng chờ: lỗi chung (xác minh / hết lượt) dừng ngay; lỗi riêng một ảnh ("couldn't generate"…)
                # chưa biết của lượt nào -> lượt đứng một mình thì dừng, đang chờ cùng lượt khác thì chờ thêm 45 s
                loi_tu = loi_tu or time.time()
                if _LOI_CHUNG.search(loi) or len(ph.dang_cho) <= 1 or time.time() - loi_tu > 45:
                    luot["loi"] = loi
                    return []
        else:
            luot["loi"] = "hết giờ chờ"
            if not link:
                link = _vot_lai(ph, luot)
                if link:
                    luot["loi"] = ""
        link = link[:2]                                         # một lượt Flow ra 2 ảnh: không nhận quá (ảnh lượt khác)
        ph.da_nhan.update(i for i, _ in link)
        return [u for _, u in link]
    finally:
        if luot in ph.dang_cho:
            ph.dang_cho.remove(luot)


def _vot_lai(ph, luot):
    """25/10 (thử 20 ảnh: 4-6 lượt "hết giờ chờ" mỗi lần chạy, mỗi lượt mất 4 phút rồi vẽ lại): trước khi bỏ lượt, dò lại
    MỌI phản hồi từ lúc gửi với luật nới (có ÍT NHẤT một đoạn riêng, không có đoạn của lượt khác đang chờ). Không thấy thì
    ghi các phản hồi + đoạn đặc trưng ra cache/flow_het_gio.txt để tìm nguyên nhân."""
    try:
        kq = ph.js(f"(window.__bc_kq || []).slice({luot['truoc']})") or []
    except Exception:                                            # noqa: BLE001
        return []
    khac = [d for c in ph.dang_cho if c is not luot for d in c.get("dau_ds") or [c["dau"]]]
    for t in kq:
        if any(d in t for d in luot.get("dau_ds") or [luot["dau"]]) and not any(k in t for k in khac):
            link = [x for x in _link([t], None) if x[0] not in luot["da_co"] and x[0] not in ph.da_nhan]
            if link:
                log(f"    Flow '{ph.ten}': hết giờ nhưng dò lại thấy {len(link)} ảnh của lượt")
                return link
    try:
        from common import CACHE_CHUNG
        with open(os.path.join(CACHE_CHUNG, "flow_het_gio.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n\n===== {time.strftime('%d/%m %H:%M:%S')} hồ sơ {ph.ten} | đoạn {luot.get('dau_ds')} | "
                    f"{len(kq)} phản hồi | đang chờ {len(ph.dang_cho)}\n--- câu lệnh:\n{luot['prompt'][:4000]}\n")
            for t in kq:
                f.write(f"--- phản hồi ({len(t)} ký tự, {len(_URL.findall(t))} link, có đoạn: "
                        f"{[d in t for d in luot.get('dau_ds') or []]}):\n{t[:3000]}\n")
    except OSError:
        pass
    return []


# link ảnh trong phản hồi: "...image/<id>?Expires\\u003d…\\u0026KeyName…" (dấu = và & bị thoát 1-2 lớp)
_URL = re.compile(r'https://flow-content\.google/image/([0-9a-f-]+)\?(?:[^"\\]|\\+u00[0-9a-fA-F]{2})*')


def _link(kq, dau, tam=2500, khac=(), du=()):
    """[(id, url)] ảnh trong các phản hồi; dau: đoạn câu lệnh phải đứng trước link (None = mọi ảnh); khac: đoạn đặc trưng
    của các lượt khác đang chờ — link gần đoạn của lượt khác hơn thì là ảnh của lượt đó."""
    ra, thay = [], set()
    for t in kq:
        if du and not all(d in t for d in du):                   # phản hồi không chứa đủ các đoạn riêng: không phải của lượt
            continue
        for m in _URL.finditer(t):
            if m.group(1) in thay:
                continue
            if dau is not None:
                # 23/10: câu lệnh storyboard dài ~3000 ký tự -> cửa sổ dò phải dài hơn câu lệnh (trước cố định 2500)
                lo = max(0, m.start() - tam)
                vt = t.rfind(dau, lo, m.start())
                if vt < 0 or any(t.rfind(k, lo, m.start()) > vt for k in khac if k and k != dau):
                    continue
            thay.add(m.group(1))
            u = re.sub(r"\\+u003d", "=", m.group(0))
            u = re.sub(r"\\+u0026", "&", u)
            ra.append((m.group(1), u))
    return ra


def _tao(ph, prompt, ti_le, tham_chieu=None):
    """Gửi + chờ một lượt (lối cũ, một lượt một lúc) -> [link ảnh] (rỗng nếu lỗi; lỗi chữ trên trang trong ph.loi)."""
    luot = _gui(ph, prompt, ti_le, tham_chieu)
    link = _cho(ph, luot)
    ph.loi = luot.get("loi", "")
    return link


# 25/10 user "tối ưu tốc độ nhất có thể": mỗi hồ sơ GỬI TIẾP lượt mới khi lượt trước còn đang vẽ (Flow vẽ song song),
# khoá hồ sơ chỉ giữ lúc gõ + bấm tạo (vài giây) chứ không suốt ~30-60 s chờ ảnh. BC_FLOW_SONG_SONG=1 để quay về lối cũ.
SONG_SONG = max(1, min(6, int(os.environ.get("BC_FLOW_SONG_SONG") or 3)))   # đo 25/10: 6 lượt chạy được nhưng dồn nhiều thì Flow báo "unusual activity"
LOI_LIEN_TOI_DA = 2          # hồ sơ lỗi liên tiếp bấy nhiêu lượt -> nghỉ NGHI_LOI giây (không để luồng phí thời gian vào nó)
_LOI_LIEN = {}
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


def so_luong_ve():
    """Số luồng vẽ ảnh Flow nên chạy: mỗi hồ sơ dùng được SONG_SONG lượt cùng lúc."""
    return max(1, min(32, so_ho_so_dung_duoc() * SONG_SONG))


def _ghi_loi(ten, loi):
    """Đếm lỗi liên tiếp của hồ sơ; quá LOI_LIEN_TOI_DA thì cho nghỉ (lượt sau xếp sang hồ sơ khác)."""
    with _KHOA_GIU:
        _LOI_LIEN[ten] = _LOI_LIEN.get(ten, 0) + 1
        n = _LOI_LIEN[ten]
    if n >= LOI_LIEN_TOI_DA:
        log(f"    Flow '{ten}': lỗi {n} lượt liền -> nghỉ {NGHI_LOI // 60} phút")
        _cap_nhat(ten, nghi_den=time.time() + NGHI_LOI, loi=f"lỗi {n} lượt liền: {str(loi)[:120]}")
        with _KHOA_GIU:
            _LOI_LIEN[ten] = 0


def ve(prompt, thu, ten_file, ti_le="16:9", tham_chieu=None):
    """Vẽ một ảnh qua Flow -> đường dẫn file đã tải | None (chưa có hồ sơ / mọi hồ sơ lỗi — bên gọi lùi về Gemini).
    tham_chieu: [đường dẫn ảnh] gắn làm 'ingredients' (giữ nhân vật / bối cảnh nhất quán)."""
    goc = re.sub(r"\s*(Remember: NO writing at all\.|Absolutely NO writing anywhere\.)\s*$", "", prompt).strip()
    goc += "|" + "|".join(tham_chieu or [])
    du = _DU.get(goc)
    while du:                                                  # ảnh thứ hai của lần tạo trước (lượt vẽ lại)
        f = du.pop(0)
        if os.path.isfile(f):
            dich = os.path.join(thu, ten_file)
            os.replace(f, dich)
            return dich
    tep = _ve_flow(prompt, thu, [ten_file, f"_du_{os.getpid()}_{time.time_ns()}.png"], ti_le, tham_chieu)
    if not tep:
        return None
    if len(tep) > 1:
        _DU.setdefault(goc, []).extend(tep[1:])
    return tep[0]


def ve_nhieu(prompt, thu, ten_goc, ti_le="16:9", tham_chieu=None):
    """Như ve() nhưng GIỮ CẢ HAI ảnh của một lượt tạo (2 phương án) -> [<ten_goc>_1.png, <ten_goc>_2.png] | []."""
    return _ve_flow(prompt, thu, [f"{ten_goc}_1.png", f"{ten_goc}_2.png"], ti_le, tham_chieu)


_LOI_LUONG = {}              # luồng -> lỗi Flow của lượt cuối (bên gọi biết vì sao hỏng: chính sách / chống spam…)


def loi_cuoi():
    """Lỗi Flow lượt cuối của luồng đang gọi ('' nếu lượt cuối được ảnh)."""
    return _LOI_LUONG.get(threading.get_ident(), "")


def _ve_flow(prompt, thu, ten_files, ti_le, tham_chieu):
    """Một lượt tạo trên hồ sơ ít việc nhất (xoay vòng khi lỗi) -> [file đã tải theo ten_files] | []."""
    _LOI_LUONG[threading.get_ident()] = ""
    ds = [h for h in ds_ho_so() if not h["dang_nghi"]]
    # 22/10 user ("nhiều luồng"): mỗi luồng GIỮ CHỖ một hồ sơ (dưới khoá chung), ít luồng giữ nhất trước. 25/10: mỗi hồ sơ
    # nhận tới SONG_SONG lượt cùng lúc — khoá hồ sơ chỉ giữ lúc gõ + bấm tạo, chờ ảnh thì không giữ.
    da_thu = set()
    while True:
        ten = _giu_ho_so([h["ten"] for h in ds], da_thu)
        if ten is None:
            break
        da_thu.add(ten)
        if float(_doc_so().get(ten, {}).get("nghi_den") or 0) > time.time():   # luồng khác vừa cho nghỉ (đăng xuất…)
            _tha_ho_so(ten)
            continue
        try:
            ph = None
            khoa = _KHOA_PHIEN.setdefault(ten, threading.Lock())
            with khoa:
                try:
                    ph = _PHIEN.get(ten)
                    if ph is None:
                        ph = _Phien(ten, CONG_DAU + list(_doc_so()).index(ten) % 40)
                        _PHIEN[ten] = ph
                        _vao_du_an(ph)
                    luot = _gui(ph, prompt, ti_le, tham_chieu)
                except PermissionError as e:
                    log(f"    ! Flow '{ten}': {e}")
                    # 23/10: hồ sơ bị ĐĂNG XUẤT (acc3/acc4 về trang /about) -> nghỉ 6 giờ (bấm 'Mở' đăng nhập lại sẽ xoá nghỉ),
                    # trước đây nghỉ 10 phút rồi lại thử -> mỗi lượt mất thêm thời gian
                    _cap_nhat(ten, nghi_den=time.time() + 6 * 3600, loi=str(e)[:160])
                    dong(ten)
                    continue
                except Exception as e:                               # noqa: BLE001
                    log(f"    ! Flow '{ten}': {type(e).__name__}: {str(e)[:140]}")
                    _ghi_loi(ten, e)
                    # 25/10: giữ cửa sổ, về lại dự án (không tắt / mở Chrome) — trừ khi lượt khác còn chờ ảnh trên tab
                    # (tải lại trang làm mất kết quả của chúng): khi đó chỉ chuyển lượt này sang hồ sơ khác
                    if not (ph and ph.dang_cho):
                        cuu_phien(ten)
                    continue
            link = _cho(ph, luot)
            if not link:
                loi = luot.get("loi") or "không có ảnh"
                _LOI_LUONG[threading.get_ident()] = loi
                log(f"    ! Flow '{ten}': {loi[:140]}")
                if re.search(r"unusual", loi, re.I):                  # chống spam: đã cho nghỉ ở _cho
                    pass
                elif re.search(r"verify|captcha", loi, re.I):
                    ph.hien_cua_so()                           # để người dùng giải xác minh
                    _cap_nhat(ten, nghi_den=time.time() + NGHI_LOI, loi="cần xác minh: " + loi[:120])
                elif re.search(r"limit|quota|later", loi, re.I):
                    _cap_nhat(ten, nghi_den=time.time() + 6 * 3600, loi="hết lượt: " + loi[:120])
                    dong(ten)
                else:
                    _ghi_loi(ten, loi)
                continue
            os.makedirs(thu, exist_ok=True)
            tep = []
            for i, u in enumerate(link[:len(ten_files)]):
                dich = os.path.join(thu, ten_files[i])
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
                with _KHOA_GIU:
                    _LOI_LIEN[ten] = 0
                _cong_anh(ten, len(tep))
                if tep[0] != os.path.join(thu, ten_files[0]):          # ảnh 1 tải hỏng, ảnh 2 được -> đứng tên ảnh 1
                    os.replace(tep[0], os.path.join(thu, ten_files[0]))
                    tep[0] = os.path.join(thu, ten_files[0])
                return tep
        finally:
            _tha_ho_so(ten)
    return []
