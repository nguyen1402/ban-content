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


def tao(prompt, thu, ten_goc, ti_le="16:9", model="Veo 3.1 - Fast", phan_giai="", do_dai="", so=1,
        anh_dau=None, anh_cuoi=None, ho_so="", bao=None):
    """Tạo video qua Flow -> {"tep": [mp4…], "ho_so", "cai_dat", "diem"}. Ném lỗi (không lùi đường khác: video tốn điểm)."""
    bao = bao or (lambda *_: None)
    prompt = str(prompt or "").strip()
    if not prompt and not anh_dau:
        raise ValueError("chưa có câu lệnh")
    so = max(1, min(4, int(so or 1)))
    ds = [h for h in flow_ve.ds_ho_so() if not h["dang_nghi"] and (not ho_so or h["ten"] == ho_so)]
    if not ds:
        raise RuntimeError("chưa có hồ sơ Flow dùng được — tạo / đăng nhập ở «🎨 Hồ sơ Flow» trên trang chính")
    ds.sort(key=lambda h: flow_ve._KHOA_PHIEN.setdefault(h["ten"], threading.Lock()).locked())   # noqa: SLF001
    ten = ds[0]["ten"]
    with flow_ve._KHOA_PHIEN.setdefault(ten, threading.Lock()):  # noqa: SLF001
        ph = flow_ve._PHIEN.get(ten)                              # noqa: SLF001
        try:
            if ph is None:
                bao(f"Mở Chrome hồ sơ «{ten}»…")
                ph = flow_ve._Phien(ten, flow_ve.CONG_DAU + list(flow_ve._doc_so()).index(ten) % 40)   # noqa: SLF001
                flow_ve._PHIEN[ten] = ph                          # noqa: SLF001
                flow_ve._vao_du_an(ph)                            # noqa: SLF001
            ph.js(_MOC_V)
            bao("Chọn cài đặt video…")
            dong, ton = _cai_dat(ph, ti_le, model, phan_giai, do_dai, so)
            bao(f"{dong} — Flow báo tốn {ton or '?'} điểm")
            log(f"    Flow video '{ten}': {dong}, {ton or '?'} điểm")
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
            flow_ve._cap_nhat(ten, dung_luc=time.time(), loi="",  # noqa: SLF001
                              so_video=int(flow_ve._doc_so().get(ten, {}).get("so_video") or 0) + len(tep))   # noqa: SLF001
            return {"tep": tep, "ho_so": ten, "cai_dat": dong, "diem": ton}
        except Exception:
            flow_ve.dong(ten)                                     # trang hỏng giữa chừng: lần sau mở lại sạch
            raise
