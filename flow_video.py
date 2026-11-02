# -*- coding: utf-8 -*-
"""TẠO VIDEO QUA GOOGLE FLOW (Veo / Omni) — 20/10/2026 user: "phần nhập câu lệnh để tạo video trên google flow, làm đầu vào
như google flow". Dùng chung hồ sơ Chrome + phiên của flow_ve.py (đăng nhập một lần, cửa sổ đẩy ra ngoài màn hình).

Giao diện Flow (đọc 20/10, bản tiếng Anh): Settings trigger -> "Video" -> chế độ "Frames" (ô Start / End, để TRỐNG = tạo từ
chữ) hoặc "Ingredients"; tỉ lệ 16:9 / 9:16; "Select model family" -> Omni 1.1 Flash | Veo 3.1 - Lite | Fast | Quality;
Omni thêm 360p/720p và 4s/6s/8s/10s; x1..x4. Dòng "Generating will use N credits" = giá thật -> đọc và báo trước khi tạo.
Đo 20/10 (x1): Omni 360p 8s 6 điểm, 720p 8s 12; Veo Lite 6-10; Fast 20; Quality 100 — TỐN ĐIỂM, khác vẽ ảnh (0 điểm).

Ảnh khung đầu/cuối: bấm ô Start/End -> bảng "Select a frame image" -> "Upload media" (chặn input.click() để lấy ô chọn
file, đưa file bằng DOM.setFileInputFiles) -> chờ ảnh hết quay -> bấm ảnh đó (tên file duy nhất) -> bảng đóng, ô có ảnh.
Kết quả (02/11): đọc phản hồi hỏi trạng thái của trang -> mã video có câu lệnh trùng nguyên văn -> chờ xong -> tải theo mã."""
import base64
import json
import os
import re
import threading
import time
import urllib.request

import flow_ve
from common import log

MODEL = ["Veo 3.1 - Fast", "Veo 3.1 - Lite", "Veo 3.1 - Quality", "Omni 1.1 Flash"]
CHO_VIDEO = 600              # giây chờ một video ĐÃ ĐƯỢC FLOW NHẬN (đã có mã) tạo xong — đo 02/11: Veo Fast ~2 phút
CHO_NHAN = 60                # giây chờ Flow nhận lệnh (mã video hiện trong phản hồi) — đo 02/11: ~6 s sau khi bấm
_DEBUG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "flow_video_phan_hoi.txt")

# 02/11 (ghi mạng một lượt tạo thật trên acc1): trang hỏi trạng thái 5 s một lần qua batchexecute rpcids=jwpduf; mỗi mục
# = [mã video, mã dự án, …, [[giây tạo, ns], "câu lệnh nguyên văn", …, [trạng thái] ở vị trí 8]] — 6 vừa nhận, 2 đang tạo,
# 3 xong. as29s (chi tiết một video) và thẻ <video> trang chi tiết có link tải ký sẵn flow-content.google/video/<mã>?Expires…
# -> nhận video của lượt bằng MÃ trong phản hồi (khớp nguyên văn câu lệnh), không dò lưới (lưới trộn ảnh / video cũ).
_MOC_V = r"""(() => {
  if (window.__bc_v2) return 'da';
  window.__bc_v2 = 1; window.__bc_ma = [];
  const giu = (t) => { try { t = String(t); if (t.length < 3e6) { window.__bc_ma.push(t);
      if (window.__bc_ma.length > 300) window.__bc_ma.shift(); } } catch (e) {} };
  const can = (u, t) => /rpcids=[^&]*(jwpduf|as29s)/.test(u) || /flow-content\.google\/video/.test(t || '');
  const op = XMLHttpRequest.prototype.open, sd = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m, u) { this.__bc_u2 = String(u); return op.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function() {
    this.addEventListener('load', () => { try { if (can(this.__bc_u2, this.responseText)) giu(this.responseText) } catch (e) {} });
    return sd.apply(this, arguments);
  };
  const f0 = window.fetch;
  window.fetch = function() { return f0.apply(this, arguments).then(r => { try { const u = String(r.url);
      if (/flow-content\.google\/video\//.test(u)) giu('URL ' + u);
      else if (/rpcids=[^&]*(jwpduf|as29s)/.test(u)) r.clone().text().then(giu).catch(() => {}); } catch (e) {}
    return r; }); };
  return 'moc';
})()"""

_URL_V = re.compile(r'https://flow-content\.google/video/([0-9A-Za-z_-]+)\?(?:[^"\\\s]|\\+u00[0-9a-fA-F]{2})*')
_VIDEO_DOM = r"""(() => [...document.querySelectorAll('video')].map(v => v.currentSrc || v.src ||
  (v.querySelector('source') || {}).src || '').filter(Boolean))()"""


def _thoat(u):
    u = re.sub(r"\\+u003d", "=", u)
    return re.sub(r"\\+u0026", "&", u)


_chuan, _rpc = flow_ve._chuan, flow_ve._rpc        # bộ đọc phản hồi batchexecute dùng chung với ảnh


def _luot_cua(ds, lenh, tu):
    """{mã video: {"tt": trạng thái, "du_an": mã dự án, "luc": giây tạo}} của các video có câu lệnh trùng NGUYÊN VĂN `lenh`
    (đã chuẩn hoá khoảng trắng) và tạo từ giây `tu` trở đi."""
    ra = {}
    for ten, d in _rpc(ds):
        muc = (d[2] if isinstance(d, list) and len(d) > 2 and isinstance(d[2], list) else []) if ten == "jwpduf" else [d]
        for e in muc:
            try:
                ma, du_an, the = e[0], e[1], e[5]
                luc, cau, tt = float(the[0][0]), the[1], the[8][0]
            except (TypeError, IndexError, KeyError, ValueError):
                continue
            c = _chuan(cau)
            if isinstance(ma, str) and c == lenh and luc >= tu:
                ra[ma] = {"tt": tt, "du_an": du_an, "luc": luc}
    return ra


def _link_cua(ds, ma):
    """Link tải ký sẵn flow-content.google/video/<ma>?Expires… trong các phản hồi / URL đã ghi."""
    for t in ds or []:
        for m in _URL_V.finditer(str(t)):
            if m.group(1) == ma:
                return _thoat(m.group(0))
    return None


def _bam_xy(ph, js_phan_tu):
    """Bấm chuột THẬT vào giữa phần tử (biểu thức JS trả phần tử)."""
    xy = ph.js("(() => { const x = " + js_phan_tu + "; if (!x) return null; x.scrollIntoView({block: 'nearest'});"
               " const r = x.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
    if xy:
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            ph.ws.goi("Input.dispatchMouseEvent", type=t, x=xy[0], y=xy[1], button="left", clickCount=1)
    return bool(xy)


def _esc(ph):
    for t in ("keyDown", "keyUp"):
        ph.ws.goi("Input.dispatchKeyEvent", type=t, key="Escape", code="Escape", windowsVirtualKeyCode=27)


def _chu(ph, chu):
    return ph.js(flow_ve._BAM_CHU + f"({json.dumps(chu)})")      # noqa: SLF001


def _cai_dat(ph, ti_le, model, phan_giai, do_dai, so):
    """Chọn Video + Frames + tỉ lệ + model (+ độ phân giải / độ dài nếu model có) + xN -> (dòng cài đặt, điểm)."""
    ph.cai_dat = None                                             # flow_ve vẽ ảnh phải chọn lại "Image"
    ph.js("document.querySelector('button[aria-label=\"Settings trigger\"]').click()")
    time.sleep(1.0)
    _chu(ph, "Video")
    time.sleep(0.6)
    _chu(ph, "Frames")
    time.sleep(0.5)
    _chu(ph, ti_le)
    time.sleep(0.3)
    if model:
        ph.js("document.querySelector('button[aria-label=\"Select model family\"]').click()")
        time.sleep(0.8)
        if not _chu(ph, model):
            _esc(ph)
            raise RuntimeError(f"Flow không có model «{model}»")
        time.sleep(0.8)
        if not ph.js("!!document.querySelector('button[aria-label=\"Select model family\"]')"):   # menu đóng cả bảng
            ph.js("document.querySelector('button[aria-label=\"Settings trigger\"]').click()")
            time.sleep(0.8)
    for chon in (phan_giai, do_dai):                              # chỉ Omni có; model khác bỏ qua
        if chon:
            _chu(ph, chon)
            time.sleep(0.3)
    _chu(ph, f"x{so}")
    time.sleep(0.5)
    gia = r"""(() => { const t = document.body.innerText.match(/Generating will use ([\d,.]+) credits?/); return t ? t[1] : '' })()"""
    ton = ph.js(gia)
    if not ton:                                                   # bảng đã tự đóng (đổi model) -> mở lại để đọc giá
        ph.js("document.querySelector('button[aria-label=\"Settings trigger\"]').click()")
        ton = ph.cho(gia, 4) or ""
    dong = ph.js("(document.querySelector('button[aria-label=\"Settings trigger\"]') || {}).innerText || ''")
    _esc(ph)
    time.sleep(0.4)
    return re.sub(r"\s*\n\s*", " ", dong).replace("crop_16_9", "16:9").replace("crop_9_16", "9:16"), ton


def _bo_khung_cu(ph):
    """Gỡ ảnh khung đầu/cuối còn từ lần trước (nút 'cancel' trên ô)."""
    for _ in range(3):
        if not _bam_xy(ph, "[...document.querySelectorAll('button')].find(e => e.offsetParent && (e.innerText||'').trim() === 'cancel'"
                           " && e.getBoundingClientRect().y > innerHeight * 0.5)"):
            return
        time.sleep(0.6)


def _dat_khung(ph, o, anh):
    """Đưa ảnh vào ô 'Start' / 'End'."""
    if not _bam_xy(ph, f"[...document.querySelectorAll('button')].find(e => e.offsetParent && (e.innerText||'').trim() === {json.dumps(o)})"):
        raise RuntimeError(f"không thấy ô {o} (chế độ Frames)")
    if not ph.cho("document.body.innerText.includes('Upload media')", 10):
        raise RuntimeError("không mở được bảng chọn ảnh khung")
    ph.js(r"""(() => { window.__bc_in = null; if (!window.__bc_click) { const c = HTMLInputElement.prototype.click;
      window.__bc_click = c; HTMLInputElement.prototype.click = function() { if (this.type === 'file') { window.__bc_in = this; return; }
      return c.apply(this, arguments); }; } return true })()""")
    _chu(ph, "Upload media")
    time.sleep(1.0)
    r = ph.ws.goi("Runtime.evaluate", expression="window.__bc_in || document.querySelector('input[type=file]')")
    oid = (r.get("result") or {}).get("objectId")
    if not oid:
        raise RuntimeError("không thấy ô chọn file của Flow")
    ph.ws.goi("DOM.enable")
    ph.ws.goi("DOM.setFileInputFiles", files=[os.path.abspath(anh)], objectId=oid)
    ten = os.path.basename(anh)
    item = f"[...document.querySelectorAll('button.asset-item')].find(e => (e.innerText||'').trim() === {json.dumps(ten)})"
    # 20/10 đo: ảnh mới hiện trong danh sách sau ~11 s; bấm ngay khi vừa có ảnh nhỏ thì Flow lờ đi -> bấm lại tới khi bảng đóng
    han = time.time() + 120
    while time.time() < han:
        q = ph.js(f"(() => {{ const e = {item}; if (!e || e.querySelector('mat-spinner')) return false;"
                  " const i = e.querySelector('img'); return !!(i && i.complete && i.naturalWidth) })()")
        if q:
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"tải ảnh khung {o} lên Flow quá lâu")
    for _ in range(5):
        time.sleep(1.0)
        _bam_xy(ph, item)
        if ph.cho("!document.body.innerText.includes('Select a frame image')", 3):
            return
    _esc(ph)
    raise RuntimeError(f"không gắn được ảnh vào ô {o}")


_KHOA_TAI = threading.Lock()


def _tai_ma(ph, ma, du_an, thu, ten_tep, bao):
    """Tải video mã `ma`: link ký sẵn đã bắt được -> tải thẳng; chưa có thì mở trang chi tiết /project/<du_an>/edit/<ma> (thẻ
    <video> ở đó mang link ký); vẫn không có thì bấm download trong trang chi tiết (menu chất lượng -> "Original size").
    -> đường dẫn | None. Không bao giờ chọn video theo vị trí trên lưới."""
    dich = os.path.join(thu, ten_tep)
    u = _link_cua(ph.js("window.__bc_ma || []"), ma)
    if u and _tai(ph, u, dich):
        return dich
    import shutil
    import tempfile
    cu = ph.js("location.href")
    with _KHOA_TAI:                                          # thư mục tải của Chrome đặt cho cả trình duyệt
        rieng = tempfile.mkdtemp(prefix="_tai_", dir=thu)
        try:
            bao("Mở trang chi tiết video để lấy link tải…")
            ph.js(f"location.assign({json.dumps(f'https://flow.google.com/project/{du_an}/edit/{ma}')})")
            ph.cho(f"location.pathname.includes({json.dumps(ma)}) && document.readyState === 'complete'", 30)
            han = time.time() + 20
            while time.time() < han:
                u = next((x for x in (ph.js(_VIDEO_DOM) or []) if ma in x), None)
                if u:
                    break
                time.sleep(1)
            if u and _tai(ph, u, dich):
                return dich
            ph.ws.goi("Browser.setDownloadBehavior", behavior="allow", downloadPath=os.path.abspath(rieng))
            if not _bam_xy(ph, "[...document.querySelectorAll('button')].find(b => b.getBoundingClientRect().width > 0"
                           " && /download/i.test((b.getAttribute('aria-label') || '') + (b.innerText || '')))"):
                return None
            time.sleep(1.5)
            _bam_xy(ph, "[...document.querySelectorAll('[role=menuitem], .mat-mdc-menu-item')]"
                        ".find(e => /Original size/i.test(e.innerText || ''))")
            han = time.time() + 60
            while time.time() < han:
                time.sleep(1)
                xong = [f for f in os.listdir(rieng) if not f.endswith(('.crdownload', '.tmp'))
                        and os.path.getsize(os.path.join(rieng, f)) > 20000]
                if xong:
                    for _ in range(10):                      # Chrome / trình diệt virus có thể còn giữ tệp vài giây
                        try:
                            os.replace(os.path.join(rieng, xong[0]), dich)
                            return dich
                        except PermissionError:
                            time.sleep(1)
            return None
        finally:
            shutil.rmtree(rieng, ignore_errors=True)
            if cu and ph.js("location.href") != cu:
                ph.js(f"location.assign({json.dumps(cu)})")
                ph.cho("document.readyState === 'complete' && !location.pathname.includes('/edit/')", 30)
                time.sleep(2)
                ph.js(_MOC_V)                                # tải lại trang làm mất bộ ghi mạng


def _tai(ph, u, dich):
    """Tải video: link có chữ ký tải thẳng; link khác (cần cookie / blob) tải TRONG trang rồi gửi về theo khúc."""
    if "flow-content.google" in u:
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=180) as r:
                open(dich, "wb").write(r.read())
            if os.path.getsize(dich) > 20000:
                return True
        except Exception as e:                                    # noqa: BLE001
            log(f"    ! Flow tải video thẳng lỗi: {str(e)[:100]} — thử tải trong trang")
    n = ph.ws.goi("Runtime.evaluate", awaitPromise=True, returnByValue=True, expression=(
        "(async () => { const b = await (await fetch(" + json.dumps(u) + ", {credentials: 'include'})).arrayBuffer();"
        " const a = new Uint8Array(b); let s = ''; for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);"
        " window.__bc_tep = btoa(s); return window.__bc_tep.length })()"))
    n = int(((n.get("result") or {}).get("value")) or 0)
    if n < 20000:
        return False
    with open(dich, "wb") as f:
        buoc = 4_000_000
        for i in range(0, n, buoc):
            f.write(base64.b64decode(ph.js(f"window.__bc_tep.slice({i}, {i + buoc})")))
    ph.js("window.__bc_tep = null")
    return True


_KHOA_DAT = threading.Lock()
_DAT = {}                    # tên hồ sơ -> điểm đang giữ chỗ (lượt tạo chưa xong) — nhiều luồng không vượt hạn ngày


def uoc_diem(model, phan_giai="", do_dai="", so=1):
    """Điểm ước tính trước khi mở Flow (giá thật đọc ở dòng "Generating will use N credits")."""
    m = str(model or "")
    if "Omni" in m:
        # 28/10 user ("12 điểm là tạo 8s chứ không phải 10 s"): Omni 720p 8 s = 12 điểm, 10 s = 15 điểm (đo acc1).
        # Mặc định Veo nay 8 s -> không ghi độ dài thì tính 8 s
        g = 6 if "360" in str(phan_giai) else 15 if str(do_dai).startswith("10") else 12
    else:
        g = 100 if "Quality" in m else 20 if "Fast" in m else 10
    return g * max(1, int(so or 1))


def clip_con_hom_nay(can=12):
    """Số clip (mỗi clip `can` điểm) còn tạo được hôm nay trên mọi hồ sơ dùng được."""
    return sum(flow_ve.diem_con(h["ten"], h) // can for h in flow_ve.ds_ho_so() if not h["dang_nghi"])


def _chon_theo_diem(ds, can):
    """Chọn hồ sơ còn đủ điểm hôm nay (ít luồng giữ nhất, rồi còn nhiều điểm nhất); giữ chỗ `can` điểm -> tên | None."""
    with _KHOA_DAT:
        ung = [h for h in ds if flow_ve.diem_con(h["ten"], h) - _DAT.get(h["ten"], 0) >= can]
        if not ung:
            return None
        h = min(ung, key=lambda x: (flow_ve._GIU.get(x["ten"], 0),                       # noqa: SLF001
                                    -(flow_ve.diem_con(x["ten"], x) - _DAT.get(x["ten"], 0))))
        _DAT[h["ten"]] = _DAT.get(h["ten"], 0) + can
        return h["ten"]


def _bo_dat(ten, can):
    with _KHOA_DAT:
        _DAT[ten] = max(0, _DAT.get(ten, 0) - can)


# 27/10 user: "khi bật Chrome rồi thì chạy hết điểm thì lưu video lại rồi đóng Chrome sang tiếp tài khoản khác để làm tiếp.
# tối đa 4 tài khoản làm việc cùng 1 lúc" + "mỗi tài khoản chạy 2 video cùng lúc" -> mỗi tài khoản đang nhận chạy MOI_TK khe
# (tab chính + tab phụ, mỗi tab một dự án Flow riêng), mỗi khe lần lượt lấy việc trong hàng chờ tới khi tài khoản không còn
# đủ điểm (tính cả lượt đang chạy), rồi đóng Chrome, nhận tài khoản kế. Việc lỗi do tài khoản (hết điểm, xác minh…) trả lại
# hàng chờ cho tài khoản khác.
SONG_SONG_VIDEO = max(1, int(os.environ.get("BC_FLOW_VIDEO_SONG_SONG") or 4))     # số tài khoản cùng lúc
MOI_TK = max(1, min(2, int(os.environ.get("BC_FLOW_VIDEO_MOI_TK") or 2)))         # số video cùng lúc trên một tài khoản
_LOI_TAI_KHOAN = re.compile(r"hết điểm|chỉ còn|credits|unusual|verify|captcha|hồ sơ Flow|Chrome|tab phụ|đăng nhập|quota|"
                            r"limit|later", re.I)


def chay_theo_tai_khoan(viec, lam, can=12, song_song=SONG_SONG_VIDEO, moi_tk=MOI_TK, bao=None):
    """viec: [x…]; lam(x, ten_ho_so, khe) -> kết quả (ném lỗi nếu hỏng). -> [kết quả | None] cùng thứ tự viec.
    Tối đa `song_song` tài khoản (cửa sổ Chrome) cùng lúc, mỗi tài khoản `moi_tk` video cùng lúc."""
    from collections import deque
    bao = bao or (lambda m: log("    " + m))
    hang = deque((i, x, 0) for i, x in enumerate(viec))
    kq = [None] * len(viec)
    khoa = threading.Lock()
    dang_dung, da_bo, dang_chay = set(), set(), {}          # tài khoản đang nhận / hỏng lượt này / số việc đang chạy

    def nhan():
        with khoa:
            ung = [h for h in flow_ve.ds_ho_so() if not h["dang_nghi"] and h["ten"] not in dang_dung
                   and h["ten"] not in da_bo and flow_ve.diem_con(h["ten"], h) >= can]
            if not ung:
                return None
            # đang mở Chrome trước; rồi tài khoản đã dùng dở (ít điểm còn) -> dùng cho hết, ít tài khoản phải mở
            h = min(ung, key=lambda x: (not x["dang_mo"], flow_ve.diem_con(x["ten"], x), x.get("tao", 0)))
            dang_dung.add(h["ten"])
            return h["ten"]

    def lay_viec(ten):
        with khoa:
            if not hang or ten in da_bo or flow_ve.diem_con(ten) - dang_chay.get(ten, 0) * can < can:
                return None
            dang_chay[ten] = dang_chay.get(ten, 0) + 1
            return hang.popleft()

    def khe(ten, k):
        while True:
            v = lay_viec(ten)
            if v is None:
                return
            i, x, lan = v
            try:
                kq[i] = lam(x, ten, k)
            except Exception as e:                           # noqa: BLE001
                loi = str(e)
                # 27/10 user ("tại sao lại chưa hết điểm lại không tạo được"): Flow TỪ CHỐI NỘI DUNG ("Flow báo: …policy… /
                # Something went wrong… try again later") khớp "later|limit" -> trước đây coi là lỗi TÀI KHOẢN: bỏ cả tài khoản
                # cho hết lượt + đẩy câu lệnh hỏng sang tài khoản khác (một câu lệnh hỏng làm hỏng 3 tài khoản). Nay lỗi
                # "Flow báo" chỉ là lỗi tài khoản khi nói về điểm / xác minh; còn lại bỏ đúng câu lệnh đó.
                noi_dung = loi.startswith("Flow báo") and not re.search(r"credits|unusual|verify|captcha|quota", loi, re.I)
                if _LOI_TAI_KHOAN.search(loi) and not noi_dung:
                    with khoa:
                        if lan < 2:                          # việc trả lại hàng chờ cho tài khoản khác
                            hang.appendleft((i, x, lan + 1))
                        da_bo.add(ten)
                    bao(f"tài khoản «{ten}» (tab {k}): lỗi tài khoản ({loi[:100]})")
                else:
                    bao(f"! việc {i + 1}: {loi[:120]}")
            finally:
                with khoa:
                    dang_chay[ten] -= 1

    def dong(ten, ly_do):
        bao(f"tài khoản «{ten}»: {ly_do} -> đóng Chrome")
        with _KHOA_MO.setdefault(ten, threading.Lock()):
            flow_ve.dong(ten)

    def chu():
        while True:
            with khoa:
                if not hang:
                    return
            ten = nhan()
            if ten is None:
                return
            try:                                             # mở Chrome + đọc điểm thật / giờ reset trên bảng tài khoản
                tt = flow_ve.doc_diem(mo_phien(ten, 1, bao))
            except Exception as e:                           # noqa: BLE001
                bao(f"tài khoản «{ten}»: không mở được ({str(e)[:100]})")
                with khoa:
                    da_bo.add(ten)
                    dang_dung.discard(ten)
                dong(ten, "lỗi mở")
                continue
            bao(f"tài khoản «{ten}»: còn {flow_ve.diem_con(ten)} điểm"
                + (f" (Flow báo {tt['diem']}, reset {tt.get('reset', '?')})" if tt.get("diem") is not None else "")
                + f" -> chạy {moi_tk} video cùng lúc")
            ts = [threading.Thread(target=khe, args=(ten, k + 1), daemon=True) for k in range(moi_tk)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            try:                                             # đọc lại số điểm thật trước khi rời tài khoản
                if ten not in da_bo:
                    flow_ve.doc_diem(mo_phien(ten, 1))
            except Exception:                                # noqa: BLE001
                pass
            with khoa:
                het = ten in da_bo or flow_ve.diem_con(ten) < can
                dang_dung.discard(ten)
            if het:
                dong(ten, "dùng hết điểm" if ten not in da_bo else "lỗi tài khoản")

    n = max(1, min(song_song, -(-len(viec) // moi_tk)))
    ts = [threading.Thread(target=chu, daemon=True) for _ in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    if hang:
        bao(f"còn {len(hang)} việc chưa làm: hết tài khoản đủ điểm -> chạy tiếp sau giờ reset")
    return kq


def tao(prompt, thu, ten_goc, ti_le="16:9", model="Veo 3.1 - Fast", phan_giai="", do_dai="", so=1,
        anh_dau=None, anh_cuoi=None, ho_so="", bao=None, gioi_han=False, khe=1):
    """Tạo video qua Flow -> {"tep": [mp4…], "ho_so", "cai_dat", "diem"}. Ném lỗi (không lùi đường khác: video tốn điểm).
    gioi_han=True (tạo tự động): chỉ dùng hồ sơ còn đủ điểm trong hạn DIEM_NGAY/ngày, free trước Pro sau."""
    bao = bao or (lambda *_: None)
    prompt = str(prompt or "").strip()
    if not prompt and not anh_dau:
        raise ValueError("chưa có câu lệnh")
    from common import giu_dac_diem                          # 30/10: đặc điểm bắt buộc của nhân vật (gai nhím…)
    prompt = giu_dac_diem(prompt, thu)
    so = max(1, min(4, int(so or 1)))
    ds = [h for h in flow_ve.ds_ho_so() if not h["dang_nghi"] and (not ho_so or h["ten"] == ho_so)]
    if not ds:
        raise RuntimeError("chưa có hồ sơ Flow dùng được — tạo / đăng nhập ở «🎨 Hồ sơ Flow» trên trang chính")
    can = uoc_diem(model, phan_giai, do_dai, so)
    if gioi_han:
        ten = _chon_theo_diem(ds, can)
        if not ten:
            raise RuntimeError(f"hết điểm video hôm nay (mỗi hồ sơ {flow_ve.DIEM_NGAY} điểm/ngày, cần {can}) — mai tạo tiếp")
        flow_ve._giu_ho_so([ten])                                # noqa: SLF001
    else:
        # 22/10 user: nhiều video cùng lúc -> mỗi lượt GIỮ CHỖ một hồ sơ rảnh (flow_ve._giu_ho_so), không giành nhau
        ten = flow_ve._giu_ho_so([h["ten"] for h in ds])       # noqa: SLF001
    try:
        return _tao_tren(ten, prompt, thu, ten_goc, ti_le, model, phan_giai, do_dai, so, anh_dau, anh_cuoi, bao,
                         can, gioi_han, khe)
    finally:
        flow_ve._tha_ho_so(ten)                                  # noqa: SLF001
        if gioi_han:
            _bo_dat(ten, can)


def _so_diem(ton):
    try:
        return int(float(str(ton).replace(",", "")))
    except ValueError:
        return 0


_KHOA_MO = {}                # tên -> Lock chỉ lúc MỞ Chrome / tab (không giữ suốt lượt tạo)


def mo_phien(ten, khe=1, bao=None):
    """Phiên Flow của hồ sơ: khe 1 = tab chính, khe 2 = tab phụ (dự án riêng, flow_ve.phien_phu)."""
    with _KHOA_MO.setdefault(ten, threading.Lock()):
        ph = flow_ve._PHIEN.get(ten)                              # noqa: SLF001
        if ph is None:
            (bao or (lambda m: None))(f"Mở Chrome hồ sơ «{ten}»…")
            ph = flow_ve._Phien(ten, flow_ve.CONG_DAU + list(flow_ve._doc_so()).index(ten) % 40)   # noqa: SLF001
            flow_ve._PHIEN[ten] = ph                              # noqa: SLF001
            flow_ve._vao_du_an(ph)                                # noqa: SLF001
        return ph if khe == 1 else flow_ve.phien_phu(ten)


def _cuu(ten, khe):
    if khe == 1:
        flow_ve.cuu_phien(ten)
        return
    ph = flow_ve._PHIEN_PHU.get(ten)                              # noqa: SLF001
    try:
        if ph is not None and ph.con_song():
            flow_ve._vao_du_an(ph)                                # noqa: SLF001
            return
    except Exception:                                             # noqa: BLE001
        pass
    flow_ve._PHIEN_PHU.pop(ten, None)                             # noqa: SLF001  (lần sau mở tab phụ mới)


def _tao_tren(ten, prompt, thu, ten_goc, ti_le, model, phan_giai, do_dai, so, anh_dau, anh_cuoi, bao, can=0, gioi_han=False,
              khe=1):
    # 27/10: mỗi khe (tab) một khoá riêng -> tab chính và tab phụ của cùng hồ sơ tạo video SONG SONG
    with flow_ve._KHOA_PHIEN.setdefault(ten if khe == 1 else f"{ten}#{khe}", threading.Lock()):  # noqa: SLF001
        try:
            ph = mo_phien(ten, khe, bao)
            ph.js(_MOC_V)
            bao("Chọn cài đặt video…")
            dong, ton = _cai_dat(ph, ti_le, model, phan_giai, do_dai, so)
            bao(f"{dong} — Flow báo tốn {ton or '?'} điểm")
            if not re.search(rf"\bx{so}\b", dong):              # 27/10 user: mỗi câu lệnh đúng {so} video — chọn xN hỏng
                raise RuntimeError(f"Flow chưa chọn được x{so} (cài đặt: {dong}) — không tạo để khỏi tốn điểm")
            log(f"    Flow video '{ten}': {dong}, {ton or '?'} điểm")
            if gioi_han and _so_diem(ton) > flow_ve.diem_con(ten):
                raise RuntimeError(f"hồ sơ «{ten}» chỉ còn {flow_ve.diem_con(ten)} điểm hôm nay, lượt này cần {ton}")
            _bo_khung_cu(ph)
            if anh_dau:
                bao("Tải ảnh khung đầu lên Flow…")
                _dat_khung(ph, "Start", anh_dau)
            if anh_cuoi:
                bao("Tải ảnh khung cuối lên Flow…")
                _dat_khung(ph, "End", anh_cuoi)
            ph.js("(() => { const e = document.querySelector('[role=textbox][aria-label]'); e.focus();"
                  " document.execCommand('selectAll'); document.execCommand('delete'); return true })()")
            if prompt:
                ph.ws.goi("Input.insertText", text=prompt)
            if not ph.cho("(() => { const b = document.querySelector('button[aria-label=\"Start generation\"]');"
                          " return b && !b.disabled })()", 10):
                raise RuntimeError("nút tạo không bật (câu lệnh chưa vào ô?)")
            lenh = _chuan(prompt)
            os.makedirs(thu, exist_ok=True)
            tu = time.time() - 300                           # giờ máy / giờ Flow có thể lệch: lượt cũ hơn 5 phút không tính
            _bam_xy(ph, "document.querySelector('button[aria-label=\"Start generation\"]')")
            bao(f"Flow đang tạo {so} video (thường 1–4 phút)…")
            t0, han, luot, xong = time.time(), time.time() + CHO_NHAN, {}, []   # chưa có mã: chờ ngắn
            while time.time() < han:
                time.sleep(4)
                try:
                    luot = _luot_cua(ph.js("window.__bc_ma || []"), lenh, tu)
                    pct = ph.js(r"""(() => { const m = [...document.querySelectorAll('main *')].filter(e => e.children.length === 0
                      && /^\d{1,3}%$/.test((e.textContent||'').trim())).map(e => e.textContent.trim()); return m.slice(0, 4).join(' ') })()""")
                except Exception:                                 # noqa: BLE001  (trang đang vẽ lại)
                    continue
                moi = sorted(luot, key=lambda k: -luot[k]["luc"])[:so]      # video mới nhất của ĐÚNG câu lệnh này
                if moi and han < t0 + CHO_VIDEO:
                    han = time.time() + CHO_VIDEO                 # Flow đã nhận lệnh: giờ mới chờ video tạo xong
                xong = [k for k in moi if luot[k]["tt"] == 3]
                bao(f"Flow đang tạo video… {int(time.time() - t0)} s" + (f" ({pct})" if pct else "")
                    + (f" — mã {', '.join(k[:8] for k in moi)}: trạng thái {[luot[k]['tt'] for k in moi]}" if moi else ""))
                if len(xong) >= so:
                    break
                hong = [k for k in moi if luot[k]["tt"] not in (2, 3, 6)]
                if hong:
                    raise RuntimeError(f"Flow báo trạng thái {luot[hong[0]]['tt']} cho video {hong[0][:8]} (không tạo được)")
                loi = ph.js(r"""(() => { const t = document.body.innerText; const m = t.match(/(unusual traffic|verify|captcha|
                  not enough credits|out of credits|limit|quota|try again later|couldn.t generate|failed to generate|violat|policy|
                  Something went wrong)[^\n]{0,140}/i); return m ? m[0] : '' })()""".replace("\n                  ", ""))
                if loi and not moi and time.time() - t0 > 8:
                    if re.search(r"credits", loi, re.I):
                        flow_ve.ghi_diem(ten, 0, het=True)        # hết điểm thật -> hôm nay không xếp hồ sơ này nữa
                    if re.search(r"unusual|verify|captcha", loi, re.I):
                        ph.hien_cua_so()
                    raise RuntimeError("Flow báo: " + loi[:200])
            else:
                os.makedirs(os.path.dirname(_DEBUG), exist_ok=True)
                open(_DEBUG, "w", encoding="utf-8").write("\n\n=====\n".join(ph.js("window.__bc_ma || []") or [])[-2_000_000:])
                raise RuntimeError((f"hết {CHO_VIDEO // 60} phút chờ mà video chưa xong" if luot else
                                    f"{CHO_NHAN} s sau khi bấm tạo Flow vẫn chưa nhận lệnh (không có mã video nào khớp câu lệnh)")
                                   + f" — đã ghi phản hồi vào {_DEBUG}")
            tep = []
            for k, ma in enumerate(xong[:so]):
                bao(f"Tải video {k + 1}/{so} (mã {ma[:8]})…")
                f = _tai_ma(ph, ma, luot[ma]["du_an"], thu, f"{ten_goc}_{k + 1}.mp4" if so > 1 else f"{ten_goc}.mp4", bao)
                if f:
                    tep.append(f)
            if not tep:
                raise RuntimeError(f"video {xong[0][:8]} đã tạo xong trên Flow nhưng tải về không được")
            flow_ve.ghi_diem(ten, _so_diem(ton) or can or uoc_diem(model, phan_giai, do_dai, so))
            flow_ve._cap_nhat(ten, dung_luc=time.time(), loi="",  # noqa: SLF001
                              so_video=int(flow_ve._doc_so().get(ten, {}).get("so_video") or 0) + len(tep))   # noqa: SLF001
            return {"tep": tep, "ho_so": ten, "cai_dat": dong, "diem": ton, "ma": xong[:so]}
        except Exception:
            _cuu(ten, khe)                                        # trang hỏng giữa chừng: về lại dự án trong cùng cửa sổ
            raise
