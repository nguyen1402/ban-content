# -*- coding: utf-8 -*-
"""TẠO VIDEO QUA GOOGLE FLOW (Veo / Omni) — 20/10/2026 user: "phần nhập câu lệnh để tạo video trên google flow, làm đầu vào
như google flow". Dùng chung hồ sơ Chrome + phiên của flow_ve.py (đăng nhập một lần, cửa sổ đẩy ra ngoài màn hình).

Giao diện Flow (đọc 20/10, bản tiếng Anh): Settings trigger -> "Video" -> chế độ "Frames" (ô Start / End, để TRỐNG = tạo từ
chữ) hoặc "Ingredients"; tỉ lệ 16:9 / 9:16; "Select model family" -> Omni 1.1 Flash | Veo 3.1 - Lite | Fast | Quality;
Omni thêm 360p/720p và 4s/6s/8s/10s; x1..x4. Dòng "Generating will use N credits" = giá thật -> đọc và báo trước khi tạo.
Đo 20/10 (x1): Omni 360p 8s 6 điểm, 720p 8s 12; Veo Lite 6-10; Fast 20; Quality 100 — TỐN ĐIỂM, khác vẽ ảnh (0 điểm).

Ảnh khung đầu/cuối: bấm ô Start/End -> bảng "Select a frame image" -> "Upload media" (chặn input.click() để lấy ô chọn
file, đưa file bằng DOM.setFileInputFiles) -> chờ ảnh hết quay -> bấm ảnh đó (tên file duy nhất) -> bảng đóng, ô có ảnh.
Kết quả: bắt phản hồi mạng có link flow-content.google/video + thẻ <video> mới trên trang; tải về."""
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
CHO_VIDEO = 900              # giây chờ một lượt tạo video
_DEBUG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "flow_video_phan_hoi.txt")

_MOC_V = r"""(() => {
  if (window.__bc_v) return 'da';
  window.__bc_v = [];
  const giu = (u, t) => { try { t = String(t); if (/flow-content\.google|\.mp4|video/i.test(t) && t.length < 3e6) {
      window.__bc_v.push(t); if (window.__bc_v.length > 60) window.__bc_v.shift(); } } catch (e) {} };
  const op = XMLHttpRequest.prototype.open, sd = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m, u) { this.__bc_u2 = String(u); return op.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function() {
    this.addEventListener('load', () => { if (this.__bc_u2.includes('rpcids=') || this.__bc_u2.includes('batchexecute')
        || this.__bc_u2.includes('/v1/')) giu(this.__bc_u2, this.responseText); });
    return sd.apply(this, arguments);
  };
  const f0 = window.fetch;
  window.fetch = function() { return f0.apply(this, arguments).then(r => { try { const u = String(r.url);
      if (!/\.(mp4|jpg|png|webp|js|css)(\?|$)/.test(u)) r.clone().text().then(t => giu(u, t)).catch(() => {}); } catch (e) {}
    return r; }); };
  return 'moc';
})()"""

_URL_V = re.compile(r'https://flow-content\.google/video/([0-9A-Za-z_-]+)\?(?:[^"\\\s]|\\+u00[0-9a-fA-F]{2})*')
_VIDEO_DOM = r"""(() => [...document.querySelectorAll('video')].map(v => v.currentSrc || v.src ||
  (v.querySelector('source') || {}).src || '').filter(Boolean))()"""


def _thoat(u):
    u = re.sub(r"\\+u003d", "=", u)
    return re.sub(r"\\+u0026", "&", u)


def _link_mang(kq):
    ra, thay = [], set()
    for t in kq or []:
        for m in _URL_V.finditer(t):
            if m.group(1) not in thay:
                thay.add(m.group(1))
                ra.append((m.group(1), _thoat(m.group(0))))
    return ra


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


# ô video trong lưới: ảnh xem trước /asb/ to + nhãn độ phân giải ("360p", "720p"…) cùng ô
_O_VIDEO = r"""(() => [...document.querySelectorAll('img')].filter(i => {
  if (!i.src.includes('/asb/') || i.getBoundingClientRect().width < 150) return false;
  let e = i;
  for (let k = 0; k < 7 && e.parentElement; k++) {          // ô = tầng cha lớn nhất còn chỉ chứa MỘT ảnh to
    const p = e.parentElement;
    if ([...p.querySelectorAll('img')].filter(x => x.getBoundingClientRect().width > 150).length > 1) break;
    e = p;
  }
  return /\b\d{3,4}p\b/.test(e.innerText || '');
}).map(i => i.src))()"""


def _mo_lay_link(ph, anh_o, cu_mang, bao):
    """Mở từng ô video (bấm ảnh xem trước) -> bắt link flow-content.google/video trong phản hồi -> quay về lưới."""
    ra = []
    for k, src in enumerate(anh_o):
        bao(f"Mở video {k + 1}/{len(anh_o)} trên Flow để lấy link…")
        _bam_xy(ph, "[...document.querySelectorAll('img')].find(i => i.src === " + json.dumps(src) + ")")
        han = time.time() + 20
        moi = []
        while time.time() < han and not moi:
            time.sleep(1)
            moi = [u for i, u in _link_mang(ph.js("window.__bc_v || []")) if i not in cu_mang and u not in ra]
        if moi:
            ra.append(moi[0])
            cu_mang = cu_mang | {i for i, _ in _link_mang(ph.js("window.__bc_v || []"))}
        ph.js("history.back()")
        ph.cho("!location.pathname.includes('/edit/')", 10)
        time.sleep(1.5)
    return ra


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
        g = 6 if "360" in str(phan_giai) else 12             # 27/10 user: Omni 720p 10 s = 12 điểm
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
                if _LOI_TAI_KHOAN.search(loi):
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
            cu_mang = {i for i, _ in _link_mang(ph.js("window.__bc_v || []"))}
            cu_dom = set(ph.js(_VIDEO_DOM) or [])
            cu_o = set(ph.js(_O_VIDEO) or [])
            truoc = len(ph.js("window.__bc_v || []") or [])
            _bam_xy(ph, "document.querySelector('button[aria-label=\"Start generation\"]')")
            bao(f"Flow đang tạo {so} video (thường 1–4 phút)…")
            t0, han, link = time.time(), time.time() + CHO_VIDEO, []
            while time.time() < han:
                time.sleep(4)
                try:
                    kq = ph.js("window.__bc_v || []") or []
                    moi_dom = [u for u in (ph.js(_VIDEO_DOM) or []) if u not in cu_dom]
                    pct = ph.js(r"""(() => { const m = [...document.querySelectorAll('main *')].filter(e => e.children.length === 0
                      && /^\d{1,3}%$/.test((e.textContent||'').trim())).map(e => e.textContent.trim()); return m.slice(0, 4).join(' ') })()""")
                except Exception:                                 # noqa: BLE001  (trang đang vẽ lại)
                    continue
                link = [u for i, u in _link_mang(kq) if i not in cu_mang] or moi_dom
                o_moi = [x for x in (ph.js(_O_VIDEO) or []) if x not in cu_o]
                if len(link) < so and len(o_moi) >= so and time.time() - t0 > 10:
                    # 20/10 đo (acc6/acc8, giao diện có mục "Videos"): tạo xong Flow KHÔNG gửi link video; mở ô video mới
                    # thì trang mới tải link flow-content.google/video -> mở từng ô, lấy link, quay về
                    link = _mo_lay_link(ph, o_moi[:so], cu_mang, bao)
                bao(f"Flow đang tạo video… {int(time.time() - t0)} s" + (f" ({pct})" if pct else "")
                    + (f" — có {len(link)}/{so}" if link else ""))
                if len(link) >= so:
                    break
                loi = ph.js(r"""(() => { const t = document.body.innerText; const m = t.match(/(unusual traffic|verify|captcha|
                  not enough credits|out of credits|limit|quota|try again later|couldn.t generate|failed to generate|violat|policy|
                  Something went wrong)[^\n]{0,140}/i); return m ? m[0] : '' })()""".replace("\n                  ", ""))
                if loi and not link and time.time() - t0 > 8:
                    if re.search(r"credits", loi, re.I):
                        flow_ve.ghi_diem(ten, 0, het=True)        # hết điểm thật -> hôm nay không xếp hồ sơ này nữa
                    if re.search(r"unusual|verify|captcha", loi, re.I):
                        ph.hien_cua_so()
                    raise RuntimeError("Flow báo: " + loi[:200])
            if not link:
                os.makedirs(os.path.dirname(_DEBUG), exist_ok=True)
                open(_DEBUG, "w", encoding="utf-8").write("\n\n=====\n".join(
                    (ph.js("window.__bc_v || []") or [])[truoc:])[-2_000_000:])
                raise RuntimeError(f"hết {CHO_VIDEO // 60} phút chờ mà chưa thấy video (đã ghi phản hồi vào {_DEBUG})")
            os.makedirs(thu, exist_ok=True)
            tep = []
            for k, u in enumerate(link[:so]):
                bao(f"Tải video {k + 1}/{min(so, len(link))}…")
                dich = os.path.join(thu, f"{ten_goc}_{k + 1}.mp4" if so > 1 else f"{ten_goc}.mp4")
                if _tai(ph, u, dich):
                    tep.append(dich)
            if not tep:
                raise RuntimeError("thấy video trên Flow nhưng tải về không được")
            flow_ve.ghi_diem(ten, _so_diem(ton) or can or uoc_diem(model, phan_giai, do_dai, so))
            flow_ve._cap_nhat(ten, dung_luc=time.time(), loi="",  # noqa: SLF001
                              so_video=int(flow_ve._doc_so().get(ten, {}).get("so_video") or 0) + len(tep))   # noqa: SLF001
            return {"tep": tep, "ho_so": ten, "cai_dat": dong, "diem": ton}
        except Exception:
            _cuu(ten, khe)                                        # trang hỏng giữa chừng: về lại dự án trong cùng cửa sổ
            raise
