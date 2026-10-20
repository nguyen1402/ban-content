# -*- coding: utf-8 -*-
"""Giao diện web (chạy trên máy) cho bộ công cụ: nhập kịch bản -> chọn giọng -> chạy -> duyệt bản thô.

    python giao_dien/may_chu.py            # mở http://127.0.0.1:8777
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["BC_DU_AN"] = "kichbantest"                 # chỉ để nạp common; mỗi lần chạy sẽ đặt lại theo dự án
import bottle                                           # noqa: E402
from bottle import Bottle, HTTPError, request, response, static_file   # noqa: E402

import common                                           # noqa: E402

PORT = int(os.environ.get("BC_PORT", "8777"))      # 8765 hay bị app khác (CapCut TTS Studio) chiếm
PY = sys.executable
FF = common.FFMPEG
KB = os.path.join(ROOT, "kich_ban")
VOICES = os.path.join(ROOT, "voices")
OMNI_PY = os.environ.get("BC_OMNI_PY", r"D:\CapCutTTS\omnivoice-env\Scripts\python.exe")   # env OmniVoice riêng
TRANG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trang.html")
app = Bottle()
procs = {}                                              # slug -> Popen


# --------------------------------------------------------------------------- tiện ích
def slug(s):
    return common._slug(s)                              # noqa: SLF001


def duong_kich_ban(du_an):
    for p in (os.path.join(KB, du_an + ".txt"), os.path.join(ROOT, du_an + ".txt")):
        if os.path.isfile(p):
            return p
    return os.path.join(KB, du_an + ".txt")


def doc_text(p):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return f.read()
    except OSError:
        return ""


def tach_cau(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+|\n+", text) if s.strip()]


def _pid_file(du_an):
    return os.path.join(common.thu_muc_du_an(du_an)[1], "chay.pid")


def _pid_song(pid):
    """Tiến trình còn sống? (hỏi thẳng Windows, ~0 ms — 19/10: tránh gọi PowerShell ~1 s cho mỗi chay.pid cũ)."""
    if os.name != "nt":
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, ValueError):
            return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))              # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        ma = ctypes.c_ulong()
        return bool(k.GetExitCodeProcess(h, ctypes.byref(ma))) and ma.value == 259   # STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def _pid_la_chay_py(pid, du_an):
    """Tiến trình `pid` còn sống VÀ đúng là chay.py của dự án này (tránh nhầm khi Windows tái dùng pid)."""
    try:
        if not _pid_song(pid):
            return False
    except Exception:                                        # noqa: BLE001
        pass
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"],
                           capture_output=True, timeout=20, creationflags=0x08000000)
        cl = r.stdout.decode("utf-8", "ignore")
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return "chay.py" in cl and f"--du-an {du_an}" in cl


def pid_cu(du_an):
    """pid của lần chạy còn sống do máy chủ TRƯỚC khởi động (đọc từ chay.pid), hoặc None."""
    try:
        pid = int(doc_text(_pid_file(du_an)).strip())
    except ValueError:
        return None
    return pid if _pid_la_chay_py(pid, du_an) else None


def dang_chay(du_an):
    p = procs.get(du_an)
    if p:
        return p.poll() is None
    return pid_cu(du_an) is not None


def trong_root(p):
    p = os.path.realpath(p)
    return p.lower().startswith(os.path.realpath(ROOT).lower())


def tham_so_q(ten, mac_dinh=""):
    """Tham số trên URL, giải mã UTF-8 đúng (bottle mặc định giải mã latin-1 làm hỏng chữ có dấu trong đường dẫn)."""
    return request.query.decode().get(ten, mac_dinh)


def url_tep(p, kieu="file"):
    return f"/{kieu}?p=" + urllib.parse.quote(p, safe="")


def json_ok(d):
    response.content_type = "application/json; charset=utf-8"
    return json.dumps(d, ensure_ascii=False)


# --------------------------------------------------------------------------- trang + tệp
@app.get("/")
def trang():
    response.content_type = "text/html; charset=utf-8"
    return doc_text(TRANG)


@app.get("/file")
def tep():
    p = tham_so_q("p")
    if not p or not trong_root(p) or not os.path.isfile(p):
        raise HTTPError(404, "không thấy tệp")
    return static_file(os.path.basename(p), root=os.path.dirname(p))


@app.get("/thumb")
def thumb():
    p = tham_so_q("p")
    if not p or not trong_root(p) or not os.path.isfile(p):
        raise HTTPError(404)
    h = hashlib.md5((p + str(os.path.getmtime(p))).encode()).hexdigest()[:16]
    d = os.path.join(ROOT, "cache", "thumb_gd")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, h + ".jpg")
    if not os.path.isfile(out):
        subprocess.run([FF, "-v", "error", "-y", "-ss", "1.0", "-i", p, "-frames:v", "1", "-vf", "scale=320:180", out],
                       creationflags=0x08000000)
        if not os.path.isfile(out):
            subprocess.run([FF, "-v", "error", "-y", "-i", p, "-frames:v", "1", "-vf", "scale=320:180", out],
                           creationflags=0x08000000)
    return static_file(h + ".jpg", root=d)


# --------------------------------------------------------------------------- dự án + kịch bản
def _ten_du_an():
    """Tên mọi dự án (kịch bản + dữ liệu riêng) — không kiểm tra đang chạy (nhanh)."""
    ten = set()
    for d in (KB, ROOT):
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".txt") and not f.endswith(".link.txt")                         and (d == KB or f in ("kichbantest.txt", "kich_ban_thu_coc.txt")):   # .link.txt = link tải, không phải dự án
                    ten.add(f[:-4])
    du = os.path.join(ROOT, "cache", "du_an")
    if os.path.isdir(du):
        ten.update(os.listdir(du))
    return ten


@app.get("/api/du_an")
def ds_du_an():
    ten = _ten_du_an()
    ra = []
    for t in sorted(ten):
        cache, out = common.thu_muc_du_an(t)
        ra.append({"ten": t, "co_ket_qua": os.path.isfile(os.path.join(out, "tu_khoa.json"))
                   or os.path.isfile(os.path.join(out, "ket_qua.json")),
                   "dang_chay": dang_chay(t)})
    return json_ok({"du_an": ra, "cuoi": doc_text(os.path.join(ROOT, "cache", "du_an_cuoi.txt")).strip()})


@app.get("/api/kich_ban")
def lay_kich_ban():
    t = slug(tham_so_q("du_an"))
    text = doc_text(duong_kich_ban(t))
    return json_ok({"text": text, "cau": tach_cau(text)})


@app.post("/api/kich_ban")
def luu_kich_ban():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or t == "mac_dinh":
        raise HTTPError(400, "thiếu tên dự án")
    os.makedirs(KB, exist_ok=True)
    p = os.path.join(KB, t + ".txt") if not os.path.isfile(os.path.join(ROOT, t + ".txt")) else os.path.join(ROOT, t + ".txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(d.get("text", ""))
    return json_ok({"ok": True, "ten": t, "cau": tach_cau(d.get("text", ""))})


@app.get("/api/goi_y_ten")
def goi_y_ten():
    t = slug(tham_so_q("du_an"))
    cache, _ = common.thu_muc_du_an(t)
    d = common.doc_json(os.path.join(cache, "ten.json"), {}) or {}
    return json_ok({"ten": d.get("ten", {}), "tom_tat": d.get("tom_tat", "")})


@app.post("/api/ap_dung_ten")
def ap_dung_ten():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    p = duong_kich_ban(t)
    text = doc_text(p)
    n = 0
    for sai, dung in (d.get("ten") or {}).items():
        n += text.count(sai)
        text = text.replace(sai, dung)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return json_ok({"da_thay": n, "cau": tach_cau(text)})


# --------------------------------------------------------------------------- giọng


@app.get("/api/giong")
def ds_giong():
    ra = sorted(f for f in os.listdir(VOICES) if f.lower().endswith(".wav")) if os.path.isdir(VOICES) else []
    ds = [{"ten": f[:-4], "tep": os.path.join(VOICES, f)} for f in ra]
    return json_ok({"giong": ds})


def doc_van_ban_tep(path):
    """Chữ trong file kịch bản: .txt (tự nhận mã hoá), .docx (đọc thẳng XML), .doc/.rtf/.odt (qua Microsoft Word)."""
    duoi = os.path.splitext(path)[1].lower()
    if duoi == ".txt":
        raw = open(path, "rb").read()
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return raw.decode("utf-16")
        for ma in ("utf-8-sig", "cp1258", "cp1252"):
            try:
                return raw.decode(ma)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", "ignore")
    if duoi == ".docx":
        import zipfile
        from xml.etree import ElementTree as ET
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with zipfile.ZipFile(path) as z:
            goc = ET.fromstring(z.read("word/document.xml"))
        doan = []
        for p in goc.iter(ns + "p"):
            chu = []
            for e in p.iter():
                if e.tag == ns + "t" and e.text:
                    chu.append(e.text)
                elif e.tag == ns + "tab":
                    chu.append(" ")
                elif e.tag in (ns + "br", ns + "cr"):
                    chu.append(chr(10))
            doan.append("".join(chu))
        return chr(10).join(doan)
    if duoi in (".doc", ".rtf", ".odt"):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        word = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            d = word.Documents.Open(os.path.abspath(path), ReadOnly=True, AddToRecentFiles=False)
            try:
                t = d.Content.Text
            finally:
                d.Close(False)
            return t.replace(chr(13), chr(10)).replace(chr(7), "")
        finally:
            if word is not None:
                word.Quit()
            pythoncom.CoUninitialize()
    raise HTTPError(400, "chỉ nhận file .txt, .docx, .doc")


@app.post("/api/kich_ban/tep")
def kich_ban_tu_tep():
    """Nhận file kịch bản tải lên, trả chữ để điền vào ô kịch bản."""
    up = request.files.get("tep")
    if not up:
        raise HTTPError(400, "thiếu tệp")
    duoi = os.path.splitext(up.raw_filename or up.filename)[1].lower()
    if duoi not in (".txt", ".docx", ".doc", ".rtf", ".odt"):
        raise HTTPError(400, "chỉ nhận file .txt, .docx, .doc")
    tam_dir = os.path.join(common.CACHE_CHUNG, "tep_tai_len")
    os.makedirs(tam_dir, exist_ok=True)
    tam = os.path.join(tam_dir, "kich_ban_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8] + duoi)
    up.save(tam, overwrite=True)
    try:
        text = doc_van_ban_tep(tam)
    except HTTPError:
        raise
    except Exception as e:                                  # noqa: BLE001
        raise HTTPError(400, f"không đọc được file: {str(e)[:150]}")
    finally:
        try:
            os.remove(tam)
        except OSError:
            pass
    text = re.sub(r"\n{3,}", chr(10) + chr(10), text.replace(chr(13) + chr(10), chr(10))).strip()
    if not text:
        raise HTTPError(400, "file không có chữ")
    return json_ok({"text": text, "ten": os.path.splitext(up.raw_filename or up.filename)[0]})


@app.post("/api/giong/them")
def them_giong():
    up = request.files.get("tep")
    if not up:
        raise HTTPError(400, "thiếu tệp")
    ten = re.sub(r"[\\/:*?\"<>|]+", "_", os.path.splitext(up.filename)[0]).strip() or "giong_moi"
    os.makedirs(VOICES, exist_ok=True)
    dich = os.path.join(VOICES, ten + ".wav")
    tam = dich + ".tam"
    up.save(tam, overwrite=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", tam, "-ac", "1", "-ar", "24000", dich], creationflags=0x08000000)
    os.remove(tam)
    return json_ok({"ok": os.path.isfile(dich), "ten": ten})


@app.get("/api/giong_canh")
def giong_canh():
    """Giọng ĐÃ ĐỌC của dự án theo từng cảnh (kể cả lần chạy dừng giữa chừng), nhóm theo giọng/tốc độ/step."""
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    goc = os.path.join(cache, "giong_omni")
    try:
        import tach_canh
        canh = tach_canh.tach_canh(doc_text(duong_kich_ban(t)), tach_canh.KY_TU_MOI_GIAY)
        chu = {c["id"]: c["text"] for c in canh}
    except Exception:                                      # noqa: BLE001
        chu = {}
    bo = []
    if os.path.isdir(goc):
        thu = [("Tự tin (mặc định)", goc)] + [(d, os.path.join(goc, d)) for d in sorted(os.listdir(goc))
                                              if os.path.isdir(os.path.join(goc, d))]
        for ten, d in thu:
            ds = []
            for f in sorted(os.listdir(d)):
                m = re.fullmatch(r"(\d{4})\.wav", f)
                if m and os.path.getsize(os.path.join(d, f)) > 2000:
                    i = int(m.group(1))
                    ds.append({"id": i, "text": chu.get(i, ""), "url": url_tep(os.path.join(d, f))})
            if ds:
                bo.append({"ten": ten, "so": len(ds), "tong": len(chu), "canh": ds,
                           "moi": max(os.path.getmtime(os.path.join(d, f)) for f in os.listdir(d)
                                      if f.endswith(".wav"))})
    bo.sort(key=lambda x: -x["moi"])                       # giọng vừa đọc gần nhất lên đầu
    return json_ok({"bo": bo})


@app.post("/api/giong/thu")
def nghe_thu():
    d = request.json or {}
    ref = d.get("giong") or ""
    if not trong_root(ref) or not os.path.isfile(ref):
        raise HTTPError(400, "giọng không hợp lệ")
    text = (d.get("text") or "").strip()[:300] or "Xin chào, đây là giọng đọc thử cho video của bạn."
    toc = float(d.get("toc_do") or 1.0)
    h = hashlib.md5((ref + text + str(toc)).encode()).hexdigest()[:12]
    out = os.path.join(VOICES, "_thu", h + ".wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.isfile(out):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        lenh = [OMNI_PY, os.path.join(ROOT, "tts", "omnivoice_tts.py"), "--text", text, "--out", out,
                "--ref", ref, "--rate", str(toc)]
        subprocess.run(lenh, env=env, capture_output=True, timeout=300, creationflags=0x08000000)
    if not os.path.isfile(out):
        raise HTTPError(500, "không đọc thử được")
    return json_ok({"url": url_tep(out)})


# --------------------------------------------------------------------------- chạy
def lenh_chay(du_an, tham_so):
    cache, out = common.thu_muc_du_an(du_an)
    os.makedirs(out, exist_ok=True)
    os.makedirs(cache, exist_ok=True)
    lenh = [PY, "-X", "utf8", os.path.join(ROOT, "chay.py"), duong_kich_ban(du_an), "--du-an", du_an,
            "--ten", tham_so.get("ten_nhap") or du_an]
    if tham_so.get("giong"):
        lenh += ["--giong-clip", tham_so["giong"]]
    if tham_so.get("toc_do"):
        lenh += ["--toc-do", str(tham_so["toc_do"])]
    if tham_so.get("gioi_han"):
        lenh += ["--gioi-han", str(int(tham_so["gioi_han"]))]
    if tham_so.get("num_step"):
        lenh += ["--num-step", str(int(tham_so["num_step"]))]
    if tham_so.get("chat_luong"):
        lenh += ["--chat-luong", str(int(tham_so["chat_luong"]))]
    if tham_so.get("tat_ocr"):
        lenh += ["--khong-ocr"]
    if not tham_so.get("tao_nhap", True):
        lenh += ["--khong-nhap"]
    return lenh, cache, out


def khoi_dong(du_an, tham_so):
    if dang_chay(du_an):
        raise HTTPError(409, "dự án đang chạy")
    lenh, cache, out = lenh_chay(du_an, tham_so)
    with open(os.path.join(out, "lan_chay.json"), "w", encoding="utf-8") as f:
        json.dump(tham_so, f, ensure_ascii=False)
    env = dict(os.environ, BC_DU_AN=du_an, PYTHONIOENCODING="utf-8")
    log = open(os.path.join(out, "chay.log"), "w", encoding="utf-8")
    procs[du_an] = subprocess.Popen(lenh, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=0x08000000)
    with open(_pid_file(du_an), "w") as f:
        f.write(str(procs[du_an].pid))
    return procs[du_an].pid


@app.post("/api/chay")
def chay():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if d.get("text") is not None:
        os.makedirs(KB, exist_ok=True)
        p = duong_kich_ban(t)
        with open(p, "w", encoding="utf-8") as f:
            f.write(d["text"])
    if not doc_text(duong_kich_ban(t)).strip():
        raise HTTPError(400, "kịch bản trống")
    pid = khoi_dong(t, {k: d.get(k) for k in ("giong", "toc_do", "gioi_han", "ten_nhap", "tao_nhap", "tat_ocr", "chat_luong", "num_step")})
    return json_ok({"ok": True, "pid": pid, "du_an": t})


def _dung_luong(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    n = 0
    for goc, _, fs in os.walk(p):
        for f in fs:
            try:
                n += os.path.getsize(os.path.join(goc, f))
            except OSError:
                pass
    return n


def _ke_hoach_don(t, ten_tat_ca=None):
    """Những gì 🧹 Dọn dự án sẽ xoá: thư mục dự án (ra/<t>), dữ liệu riêng (cache/du_an/<t>) và các bản nháp CapCut của
    dự án (tên = tên nháp bước 1, <t>, <t>_… — trừ bản nháp thuộc dự án khác có tên dài hơn bắt đầu bằng <t>_).
    KỊCH BẢN (kich_ban/<t>.txt) và kho/bộ nhớ đệm dùng chung được GIỮ."""
    cache, out = common.thu_muc_du_an(t)
    goc_ra = os.path.realpath(os.path.join(ROOT, "ra"))
    goc_du = os.path.realpath(os.path.join(common.CACHE_CHUNG, "du_an"))
    muc = []
    for d, nhom in ((out, "dự án (video/ảnh đã tải, kế hoạch, giọng đọc)"), (cache, "dữ liệu riêng (giọng đã lưu, mô tả cảnh)")):
        rp = os.path.realpath(d)
        if os.path.isdir(rp) and (rp.startswith(goc_ra + os.sep) or rp.startswith(goc_du + os.sep)):
            muc.append({"duong": rp, "loai": nhom, "dung_luong": _dung_luong(rp)})
    nhap = []
    dd = common.thu_muc_nhap_capcut()
    if dd and os.path.isdir(dd):
        ten_nhap = ""
        try:
            ten_nhap = (json.load(open(os.path.join(out, "lan_chay.json"), encoding="utf-8")) or {}).get("ten_nhap") or ""
        except (OSError, ValueError):
            pass
        tat_ca = ten_tat_ca if ten_tat_ca is not None else _ten_du_an()
        khac = [x for x in tat_ca if x != t and x.startswith(t + "_")]
        for f in sorted(os.listdir(dd)):
            if not os.path.isdir(os.path.join(dd, f)) or any(f == k or f.startswith(k + "_") for k in khac):
                continue
            if f == t or f.startswith(t + "_") or (ten_nhap and (f == ten_nhap or f.startswith(ten_nhap + "_"))):
                nhap.append({"ten": f, "duong": os.path.join(dd, f), "dung_luong": _dung_luong(os.path.join(dd, f))})
    return muc, nhap


def _dang_ban(t):
    import tu_dong_tim
    if dang_chay(t):
        return "đang chạy bước 1"
    p = procs_ht.get(t)
    if p and p.poll() is None:
        return "đang hoàn thiện bản nháp"
    p = procs_tai.get(t)
    if p and p.poll() is None:
        return "đang tải link"
    if (tu_dong_tim.TT.get(t) or {}).get("dang"):
        return "đang tự tìm + tải"
    return ""


# --------------------------------------------------------------------------- 🍪 cookie (kho RIÊNG của bán-content)
# 14/10/2026 user: tách kho cookie khỏi CapCut TTS Studio -> %LOCALAPPDATA%\\BanContent, cổng 8785 (Gemini) / 8786
# (ChatGPT), tiện ích riêng ở cookie_ext/. Bộ nhận bật cùng giao diện nên tiện ích tự gửi lại cookie mới mỗi 5 phút.
_CK = {}                                                # dich_vu -> (module kho, CookieServer | None, lỗi)


def _ck_mod(dv):
    if os.path.join(ROOT, "tts") not in sys.path:
        sys.path.insert(0, os.path.join(ROOT, "tts"))
    if dv == "gemini":
        import gemini_cookie_store as m
    elif dv == "chatgpt":
        import chatgpt_cookie_store as m
    else:
        raise HTTPError(400, "dịch vụ phải là gemini hoặc chatgpt")
    return m


def bat_nhan_cookie():
    for dv in ("gemini", "chatgpt"):
        m = _ck_mod(dv)
        try:
            srv = m.CookieServer()
            srv.start()
            _CK[dv] = (m, srv, "")
            print(f"Nhận cookie {dv}: 127.0.0.1:{m.DEFAULT_PORT}", flush=True)
        except Exception as e:                          # noqa: BLE001  cổng bận (bản giao diện khác đang nghe)
            _CK[dv] = (m, None, str(e)[:160])


_CK_KT = {}                                             # dịch vụ -> {dang, xong, tong, kq: {id: {ok, msg, credit}}, loi}


@app.post("/api/cookie/kiem_tra")
def cookie_kiem_tra():
    """15/10 user: kiểm tra nhanh mọi tài khoản ĐÃ ĐẶT TÊN của một dịch vụ (hỏi thử một câu ngắn; Gemini kèm điểm vẽ
    ảnh còn lại) — lỗi thì người dùng nạp cookie mới. Chạy nền, giao diện hỏi tiến độ qua /api/cookie."""
    dv = (request.json or {}).get("dich_vu")
    m = _ck_mod(dv)
    if (_CK_KT.get(dv) or {}).get("dang"):
        raise HTTPError(400, "đang kiểm tra")
    ids = list(m.KHO.named_account_ids())
    _CK_KT[dv] = {"dang": True, "xong": 0, "tong": len(ids), "kq": {}, "loi": "", "luc": time.time()}

    def chay():
        st = _CK_KT[dv]
        try:
            if dv == "gemini":
                import gemini_web_client as cl
            else:
                import chatgpt_web_client as cl

            def on(acc, r, xong, tong):
                st["kq"][acc] = {"ok": bool(r.get("ok")), "kind": str(r.get("kind") or ""),
                                 "msg": str(r.get("msg") or r.get("kind") or "")[:180]}
                st["xong"] = xong
            cl.check_all(ids, timeout=90, max_workers=4, on_result=on)
            if dv == "gemini":                              # điểm vẽ ảnh còn lại (Gemini app trừ ~17 điểm/ảnh)
                import asyncio
                sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
                import anh_ve
                from concurrent.futures import ThreadPoolExecutor

                def diem(acc):
                    try:
                        ck = (m.get_account(acc) or {}).get("cookies") or {}
                        return acc, asyncio.run(asyncio.wait_for(anh_ve._do_credit(ck), 90))   # noqa: SLF001
                    except Exception:                       # noqa: BLE001
                        return acc, None
                with ThreadPoolExecutor(4) as ex:
                    for acc, c in ex.map(diem, [a for a, r in st["kq"].items() if r["ok"]]):
                        st["kq"][acc]["credit"] = c
        except Exception as e:                              # noqa: BLE001
            st["loi"] = str(e)[:200]
        finally:
            st["dang"] = False
    threading.Thread(target=chay, daemon=True).start()
    return json_ok({"ok": True, "tong": len(ids)})


@app.get("/api/cookie")
def cookie_ds():
    ra = {}
    for dv in ("gemini", "chatgpt"):
        m = _ck_mod(dv)
        _, srv, loi = _CK.get(dv, (m, None, ""))
        dat_ten = set(m.KHO.named_account_ids())
        ra[dv] = {"kho": m.store_path(), "chung": "CapCutTTS" in m.store_path(), "cong": m.DEFAULT_PORT, "dang_nghe": bool(srv and srv.running), "loi": loi,
                  "tai_khoan": [dict(a, dat_ten=a["id"] in dat_ten) for a in m.list_accounts()],
                  "kiem_tra": _CK_KT.get(dv)}

    # YouTube cookie
    import common
    ck_yt = common.yt_cookie_path()
    co_yt = os.path.isfile(ck_yt) and os.path.getsize(ck_yt) > 10
    so_dong = 0
    if co_yt:
        try:
            with open(ck_yt, "r", encoding="utf-8", errors="ignore") as f:
                so_dong = sum(1 for line in f if line.strip() and not line.startswith("#"))
        except Exception:
            pass
    ra["youtube"] = {
        "co_cookie": co_yt,
        "duong_dan": ck_yt,
        "so_dong": so_dong,
        "kich_thuoc": os.path.getsize(ck_yt) if co_yt else 0,
        "sua_cuoi": time.strftime("%H:%M %d/%m/%Y", time.localtime(os.path.getmtime(ck_yt))) if co_yt else ""
    }
    return json_ok(ra)


@app.post("/api/cookie/dan")
def cookie_dan():
    d = request.json or {}
    dv = d.get("dich_vu")
    if dv == "youtube":
        return cookie_yt_dan()
    m = _ck_mod(dv)
    ten = (d.get("ten") or "").strip()
    if not ten:
        raise HTTPError(400, "Đặt tên tài khoản (vd acc1) — bán-content chỉ dùng tài khoản đã đặt tên")
    try:
        r = m.import_json(d.get("json") or "", label=ten)
    except Exception as e:                              # noqa: BLE001
        raise HTTPError(400, f"JSON cookie không hợp lệ: {str(e)[:160]}")
    return json_ok({"ok": True, "ket_qua": r if isinstance(r, (str, int, dict, list)) else str(r)})


@app.post("/api/cookie/xoa")
def cookie_xoa():
    d = request.json or {}
    dv = d.get("dich_vu")
    if dv == "youtube":
        return cookie_yt_xoa()
    m = _ck_mod(dv)
    m.delete_account(str(d.get("id") or ""))
    return json_ok({"ok": True})


@app.post("/api/cookie/youtube/dan")
def cookie_yt_dan():
    d = request.json or {}
    raw = (d.get("noi_dung") or d.get("json") or "").strip()
    if not raw:
        raise HTTPError(400, "Nội dung cookie trống")
    import common
    netscape_text = raw
    try:
        j = json.loads(raw)
        lines = ["# Netscape HTTP Cookie File", "# https://curl.se/docs/http-cookies.html", ""]
        if isinstance(j, list):
            for c in j:
                if isinstance(c, dict) and c.get("name"):
                    dom = c.get("domain") or ".youtube.com"
                    flag = "TRUE" if dom.startswith(".") else "FALSE"
                    path = c.get("path") or "/"
                    sec = "TRUE" if c.get("secure") else "FALSE"
                    exp = int(c.get("expirationDate") or c.get("expiry") or (time.time() + 365 * 86400))
                    name = c["name"]
                    val = c.get("value") or ""
                    lines.append(f"{dom}\t{flag}\t{path}\t{sec}\t{exp}\t{name}\t{val}")
            netscape_text = "\n".join(lines)
        elif isinstance(j, dict):
            exp = int(time.time() + 365 * 86400)
            for k, v in j.items():
                lines.append(f".youtube.com\tTRUE\t/\tTRUE\t{exp}\t{k}\t{v}")
            netscape_text = "\n".join(lines)
    except Exception:
        pass

    target = common.yt_cookie_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(netscape_text)
    root_ck = os.path.join(common.ROOT, "cookies.txt")
    try:
        with open(root_ck, "w", encoding="utf-8") as f:
            f.write(netscape_text)
    except Exception:
        pass
    common.log(f"  [cookie] Đã lưu cookie YouTube vào {target} ({len(netscape_text)} bytes)")
    return json_ok({"ok": True, "duong_dan": target})


@app.post("/api/cookie/youtube/xoa")
def cookie_yt_xoa():
    import common
    cac = [
        common.yt_cookie_path(),
        os.path.join(common.ROOT, "cookies.txt"),
        os.path.join(common.ROOT, "youtube_cookies.txt"),
        os.path.join(common.CACHE_CHUNG, "youtube_cookies.txt"),
        os.path.join(common.CACHE_CHUNG, "cookies.txt"),
    ]
    xoa_dem = 0
    for p in set(cac):
        try:
            if os.path.isfile(p):
                os.remove(p)
                xoa_dem += 1
        except Exception:
            pass
    return json_ok({"ok": True, "da_xoa": xoa_dem})


# --------------------------------------------------------------------------- 🎨 Flow (hồ sơ Chrome riêng để vẽ ảnh 0 điểm)
# 15/10/2026 user: nút tạo hồ sơ Chrome đặt tên -> tự đăng nhập Flow trong đó; bước vẽ ảnh mở ẩn hồ sơ, tạo, tải về.
_FLOW_THU = {}                                          # tên hồ sơ -> {dang, kq, loi}


@app.get("/api/flow")
def flow_ds():
    import flow_ve
    return json_ok({"ho_so": flow_ve.ds_ho_so(), "thu": _FLOW_THU})


@app.post("/api/flow/tao")
def flow_tao():
    import flow_ve
    try:
        flow_ve.tao_ho_so((request.json or {}).get("ten"))
    except ValueError as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True})


@app.post("/api/flow/mo")
def flow_mo():
    import flow_ve
    flow_ve.mo_dang_nhap(str((request.json or {}).get("ten") or ""))
    return json_ok({"ok": True})


@app.post("/api/flow/xoa")
def flow_xoa():
    import flow_ve
    flow_ve.xoa_ho_so(str((request.json or {}).get("ten") or ""))
    return json_ok({"ok": True})


@app.post("/api/flow/thu")
def flow_thu():
    """Vẽ thử MỘT ảnh bằng hồ sơ (chạy nền) — kiểm tra đã đăng nhập + Flow còn 0 điểm."""
    import flow_ve
    ten = str((request.json or {}).get("ten") or "")
    if _FLOW_THU.get(ten, {}).get("dang"):
        raise HTTPError(400, "đang thử hồ sơ này")
    _FLOW_THU[ten] = {"dang": True}

    def chay():
        thu = os.path.join(ROOT, "cache", "flow_thu")
        d = flow_ve._doc_so()                                # noqa: SLF001  chỉ dùng đúng hồ sơ được thử
        khac = {k: v for k, v in d.items() if k != ten}
        try:
            for k in khac:
                flow_ve._cap_nhat(k, nghi_den=time.time() + 300)   # noqa: SLF001
            f = flow_ve.ve("Ultra-photorealistic stock cut-out photo of a red apple, isolated on a seamless pure white "
                           "studio background, no text", thu, f"thu_{flow_ve._slug(ten)}.png")   # noqa: SLF001
            _FLOW_THU[ten] = {"dang": False, "kq": url_tep(f) if f else "",
                              "loi": "" if f else (flow_ve._doc_so().get(ten, {}).get("loi") or "không tạo được ảnh")}   # noqa: SLF001
        except Exception as e:                              # noqa: BLE001
            _FLOW_THU[ten] = {"dang": False, "loi": str(e)[:200]}
        finally:
            for k, v in khac.items():
                flow_ve._cap_nhat(k, nghi_den=v.get("nghi_den", 0))   # noqa: SLF001
            flow_ve.dong(ten)
    threading.Thread(target=chay, daemon=True).start()
    return json_ok({"ok": True})


# --------------------------------------------------------------------------- 🖼️ Flow Tạo hàng loạt ảnh
@app.get("/api/flow/hang_loat/trang_thai")
def flow_hang_loat_trang_thai():
    import flow_hang_loat
    runner = flow_hang_loat.lay_runner()
    st = runner.lay_trang_thai()
    # Thêm url xem ảnh cho các mục đã hoàn thành
    for m in st.get("cac_muc", []):
        if m.get("trang_thai") == "xong" and m.get("tep") and os.path.isfile(m["tep"]):
            m["url"] = url_tep(m["tep"])
    return json_ok(st)


@app.post("/api/flow/hang_loat/bat_dau")
def flow_hang_loat_bat_dau():
    import flow_hang_loat
    d = request.json or {}
    prompts = str(d.get("prompts") or "").strip()
    if not prompts:
        raise HTTPError(400, "chưa nhập câu lệnh tạo ảnh")
    du_an = slug(d.get("du_an") or "")
    thu_muc = str(d.get("thu_muc") or "").strip()
    if not thu_muc:
        if du_an:
            thu_muc = os.path.join(ROOT, "ra", du_an, "anh_flow")
        else:
            thu_muc = os.path.join(ROOT, "ra", "anh_flow")
    elif not os.path.isabs(thu_muc):
        thu_muc = os.path.join(ROOT, thu_muc)

    ti_le = str(d.get("ti_le") or "16:9")
    tien_to = str(d.get("tien_to") or "")
    hau_to = str(d.get("hau_to") or "")

    runner = flow_hang_loat.lay_runner()
    try:
        runner.bat_dau(prompts, thu_muc=thu_muc, ti_le=ti_le, tien_to=tien_to, hau_to=hau_to)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True})


@app.post("/api/flow/hang_loat/dung")
def flow_hang_loat_dung():
    import flow_hang_loat
    runner = flow_hang_loat.lay_runner()
    runner.dung()
    return json_ok({"ok": True})


@app.post("/api/flow/hang_loat/chay_lai_loi")
def flow_hang_loat_chay_lai_loi():
    import flow_hang_loat
    runner = flow_hang_loat.lay_runner()
    try:
        runner.bat_dau("", "", chi_chay_lai_loi=True)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True})


@app.post("/api/flow/hang_loat/mo_thu_muc")
def flow_hang_loat_mo_thu_muc():
    import flow_hang_loat
    runner = flow_hang_loat.lay_runner()
    thu = runner.thu_muc
    if not thu or not os.path.isdir(thu):
        du_an = slug((request.json or {}).get("du_an") or "")
        thu = os.path.join(ROOT, "ra", du_an, "anh_flow") if du_an else os.path.join(ROOT, "ra", "anh_flow")
    os.makedirs(thu, exist_ok=True)
    os.startfile(thu)
    return json_ok({"ok": True})


@app.get("/api/flow/hang_loat/goi_y_du_an")
def flow_hang_loat_goi_y():
    """Gợi ý danh sách câu tạo ảnh từ dự án đang chọn (kịch bản / mô tả cảnh)."""
    du_an = slug(tham_so_q("du_an"))
    if not du_an:
        raise HTTPError(400, "chưa chọn dự án")

    p_tk = os.path.join(ROOT, "ra", du_an, "tu_khoa.json")
    cac_dong = []
    if os.path.isfile(p_tk):
        ds = common.doc_json(p_tk, []) or []
        for x in ds:
            cid = x.get("id", len(cac_dong) + 1)
            canh_en = x.get("canh_en") or []
            if canh_en and isinstance(canh_en, list) and canh_en[0]:
                cau = canh_en[0]
            elif x.get("noi_dung"):
                cau = x.get("noi_dung")
            else:
                cau = x.get("text", "")
            if cau:
                cac_dong.append(f"canh_{cid:02d}: {cau}")
    else:
        p_kb = duong_kich_ban(du_an)
        if os.path.isfile(p_kb):
            text = doc_text(p_kb)
            for cid, cau in enumerate(tach_cau(text), 1):
                if cau.strip():
                    cac_dong.append(f"cau_{cid:02d}: {cau.strip()}")

    return json_ok({
        "prompts": "\n".join(cac_dong),
        "so_cau": len(cac_dong),
        "du_an": du_an,
    })


@app.get("/api/don_du_an")
def xem_don_du_an():
    t = slug(tham_so_q("du_an"))
    if not t or t in common._CU:                             # noqa: SLF001
        raise HTTPError(400, "dự án này không dọn được")
    muc, nhap = _ke_hoach_don(t)
    return json_ok({"muc": muc, "nhap": nhap, "ban": _dang_ban(t)})


@app.post("/api/don_du_an")
def don_du_an():
    """🧹 Dọn dự án ĐÃ LÀM XONG (13/10 user): xoá thư mục dự án + dữ liệu riêng (+ bản nháp CapCut nếu chọn).
    Bản nháp CapCut trỏ thẳng vào video trong ra/<dự án>/kho — chỉ dọn sau khi đã xuất MP4."""
    import shutil
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or t in common._CU:                             # noqa: SLF001
        raise HTTPError(400, "dự án này không dọn được")
    ban = _dang_ban(t)
    if ban:
        raise HTTPError(409, f"dự án {ban} — chờ xong hoặc dừng trước")
    muc, nhap = _ke_hoach_don(t)
    if d.get("xoa_nhap"):
        muc += [dict(x, loai="bản nháp CapCut") for x in nhap]
    xong, loi, giai = [], [], 0
    for x in muc:
        hong = []
        shutil.rmtree(x["duong"], onerror=lambda f, pth, e: hong.append(pth))
        if hong or os.path.exists(x["duong"]):
            loi.append(f"{os.path.basename(x['duong'])}: {len(hong)} tệp không xoá được (đang mở trong CapCut?)")
            giai += max(0, x["dung_luong"] - _dung_luong(x["duong"]))
        else:
            xong.append(os.path.basename(x["duong"]))
            giai += x["dung_luong"]
    return json_ok({"ok": not loi, "xong": xong, "loi": loi, "giai_phong": giai})


def _xoa_duong(ds):
    """Xoá các tệp / thư mục -> (xong, loi, giai_phong byte)."""
    import shutil
    xong, loi, giai = [], [], 0
    for p in ds:
        if not os.path.exists(p):
            continue
        dl = _dung_luong(p) if os.path.isdir(p) else os.path.getsize(p)
        hong = []
        if os.path.isdir(p):
            shutil.rmtree(p, onerror=lambda f, pth, e: hong.append(pth))
        else:
            try:
                os.remove(p)
            except OSError:
                hong.append(p)
        if hong or os.path.exists(p):
            loi.append(f"{os.path.basename(p)}: {len(hong)} tệp không xoá được (đang mở trong CapCut?)")
            giai += max(0, dl - (_dung_luong(p) if os.path.isdir(p) else 0))
        else:
            xong.append(os.path.basename(p))
            giai += dl
    return xong, loi, giai


def _ds_don_nhieu():
    """Mọi dự án có thư mục ra/<t> hoặc dữ liệu riêng cache/du_an/<t> (trừ dự án cũ không dọn được)."""
    ten = _ten_du_an()
    goc_ra = os.path.join(ROOT, "ra")
    if os.path.isdir(goc_ra):
        ten.update(f for f in os.listdir(goc_ra) if os.path.isdir(os.path.join(goc_ra, f)))
    return sorted(t for t in ten if t and t not in common._CU and slug(t) == t)   # noqa: SLF001


@app.get("/api/don_nhieu")
def xem_don_nhieu():
    """19/10 user: bảng 🧹 Dọn nhiều dự án — dung lượng từng dự án (tổng / riêng kho đã tải) + bản nháp CapCut."""
    ra = []
    ds = _ds_don_nhieu()
    for t in ds:
        muc, nhap = _ke_hoach_don(t, ds)
        kho = os.path.join(common.thu_muc_du_an(t)[1], "kho")
        ra.append({"ten": t, "tong": sum(x["dung_luong"] for x in muc), "kho": _dung_luong(kho) if os.path.isdir(kho) else 0,
                   "nhap": len(nhap), "nhap_dl": sum(x["dung_luong"] for x in nhap), "ban": _dang_ban(t) or ""})
    return json_ok({"ds": ra})


@app.post("/api/don_nhieu")
def don_nhieu():
    """{ds: [{du_an, muc: "kho" | "het"}], xoa_nhap}: "kho" = chỉ kho đã tải (ra/<t>/kho) + kế hoạch ghép hình cũ
    (dung.json, chỗ thiếu hình) — giữ giọng đọc, kịch bản, chia đoạn; "het" = như 🧹 Dọn dự án. Dự án đang chạy: bỏ qua."""
    d = request.json or {}
    tat_ca = _ds_don_nhieu()
    hop_le = set(tat_ca)
    kq, giai = [], 0
    for y in d.get("ds") or []:
        t = slug(str(y.get("du_an") or ""))
        if t not in hop_le:
            continue
        ban = _dang_ban(t)
        if ban:
            kq.append({"du_an": t, "loi": [f"bỏ qua: {ban}"], "giai_phong": 0})
            continue
        muc, nhap = _ke_hoach_don(t, tat_ca)
        out = common.thu_muc_du_an(t)[1]
        if y.get("muc") == "het":
            duong = [x["duong"] for x in muc]
        else:
            duong = [os.path.join(out, "kho")] + [os.path.join(out, f) for f in
                                                 ("dung.json", "thieu_hinh.json", "thieu_chi_tiet.json")]
        if d.get("xoa_nhap"):
            duong += [x["duong"] for x in nhap]
        xong, loi, g = _xoa_duong(duong)
        giai += g
        kq.append({"du_an": t, "loi": loi, "giai_phong": g})
    return json_ok({"ok": not any(x["loi"] for x in kq), "kq": kq, "giai_phong": giai})


@app.post("/api/lam_lai")
def lam_lai():
    """Xoá DỮ LIỆU RIÊNG của dự án (giọng, nhịp, truy vấn, mốc, clip đã dựng) để lần chạy sau làm lại từ đầu.
    Kho tìm kiếm/video đã tải/OCR dùng chung cho mọi dự án nên GIỮ — làm lại vẫn không phải tải lại video."""
    import shutil
    t = slug((request.json or {}).get("du_an", ""))
    if not t or t in common._CU:                         # noqa: SLF001  (dự án cũ dùng chung thư mục gốc: không xoá)
        raise HTTPError(400, "dự án này không xoá được")
    if dang_chay(t):
        raise HTTPError(409, "dự án đang chạy — hãy dừng trước")
    cache, out = common.thu_muc_du_an(t)
    goc = os.path.realpath(os.path.join(common.CACHE_CHUNG, "du_an"))
    if os.path.realpath(cache).startswith(goc + os.sep) and os.path.isdir(cache):
        shutil.rmtree(cache)
    for f in ("trang_thai.json", "chay.pid"):
        try:
            os.remove(os.path.join(out, f))
        except OSError:
            pass
    return json_ok({"ok": True})


def _tep_kb(t, hau):
    return os.path.join(KB, f"{t}.{hau}")


@app.get("/api/chu_luc")
def chu_luc_ds():
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    ds = common.doc_json(os.path.join(out, "chu_luc.json"), []) or []
    bo = {l.strip() for l in doc_text(_tep_kb(t, "bo_video.txt")).splitlines() if l.strip()}
    for v in ds:
        v["bo"] = v["id"] in bo
    return json_ok({"ds": ds, "link": doc_text(_tep_kb(t, "link.txt"))})


@app.post("/api/bo_video")
def bo_video():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    vid = str(d.get("id", "")).strip()
    if not t or not vid:
        raise HTTPError(400, "thiếu dự án hoặc id video")
    p = _tep_kb(t, "bo_video.txt")
    ds = [l.strip() for l in doc_text(p).splitlines() if l.strip()]
    if d.get("bo", True):
        if vid not in ds:
            ds.append(vid)
    else:
        ds = [x for x in ds if x != vid]
    os.makedirs(KB, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(ds) + ("\n" if ds else ""))
    return json_ok({"ok": True, "so": len(ds)})


@app.post("/api/link")
def luu_link():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    dong = [l.strip() for l in str(d.get("text", "")).splitlines() if l.strip().startswith("http")]
    os.makedirs(KB, exist_ok=True)
    with open(_tep_kb(t, "link.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(dong) + ("\n" if dong else ""))
    return json_ok({"ok": True, "so": len(dong)})


@app.get("/api/tu_khoa")
def tu_khoa_ds():
    """Từ khoá tìm nguồn của từng cảnh (ra/<dự án>/tu_khoa.json) + link mở clip bản đồ."""
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    ds = common.doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    wav = os.path.join(out, "giong_doc.wav")
    return json_ok({"ds": ds, "giong_url": url_tep(wav) if os.path.isfile(wav) else None})


procs_tai = {}                                           # dự án -> Popen tải link


@app.post("/api/tai_link")
def tai_link_bat_dau():
    """Lưu danh sách link (mỗi dòng một link) rồi tải về ra/<dự án>/video_tai/ bằng tai_link.py (chạy nền)."""
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    p = procs_tai.get(t)
    if p and p.poll() is None:
        raise HTTPError(409, "đang tải — chờ xong rồi thêm link")
    dong = [l.strip() for l in str(d.get("text", "")).splitlines() if l.strip().startswith("http")]
    if not dong:
        raise HTTPError(400, "chưa có link nào (mỗi dòng một link bắt đầu bằng http)")
    os.makedirs(KB, exist_ok=True)
    with open(_tep_kb(t, "link.txt"), "w", encoding="utf-8") as f:
        f.write(chr(10).join(dong) + chr(10))
    cache, out = common.thu_muc_du_an(t)
    os.makedirs(out, exist_ok=True)
    log = open(os.path.join(out, "tai_link.log"), "w", encoding="utf-8")
    procs_tai[t] = subprocess.Popen([PY, "-X", "utf8", os.path.join(ROOT, "tai_link.py"), t], cwd=ROOT,
                                    env=dict(os.environ, PYTHONIOENCODING="utf-8"), stdout=log,
                                    stderr=subprocess.STDOUT, creationflags=0x08000000)
    return json_ok({"ok": True, "so": len(dong)})


@app.get("/api/tai_link")
def tai_link_trang_thai():
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    d = common.doc_json(os.path.join(out, "tai_link.json"), {}) or {}
    p = procs_tai.get(t)
    for x in d.get("links", []):
        x["ten"] = os.path.basename(x.get("file") or "")
        x["url_file"] = url_tep(x["file"]) if x.get("file") and os.path.isfile(x["file"]) else None
    return json_ok({"links": d.get("links", []), "dang_tai": bool(p and p.poll() is None),
                    "text": doc_text(_tep_kb(t, "link.txt"))})


@app.post("/api/mo_video")
def mo_video():
    t = slug((request.json or {}).get("du_an", ""))
    cache, out = common.thu_muc_du_an(t)
    thu = os.path.join(out, "video_tai")
    os.makedirs(thu, exist_ok=True)
    os.startfile(thu)
    return json_ok({"ok": True})


TRANG_DUNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dung.html")


@app.get("/dung")
def trang_dung():
    response.content_type = "text/html; charset=utf-8"
    return doc_text(TRANG_DUNG)


def _kho_ra(t):
    import dung_tay
    ra = []
    for kid, m in sorted(dung_tay.doc_kho(t).items(), key=lambda x: -x[1].get("luc", 0)):
        f = m.get("file", "")
        co = os.path.isfile(f) and m.get("trang_thai") == "xong"
        thumb = (f"https://i.ytimg.com/vi/{kid[2:]}/mqdefault.jpg" if m.get("loai") == "video" and "youtube" in m.get("nguon", "")
                 else (url_tep(f) if co and m.get("loai") == "anh" else ""))
        ra.append(dict(m, id=kid, url=url_tep(f) if co else None, thumb=thumb))
    return ra


@app.get("/api/dung/du_lieu")
def dung_du_lieu():
    """Mọi thứ trình dựng tay cần: cảnh (lời, mốc, từ khoá), kế hoạch đã lưu, kho media, giọng đọc nguyên bài."""
    import dung_tay
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    canh = common.doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    dung = dung_tay.doc_dung(t)
    for kh in dung.values():
        for d in kh.get("cat", []):
            d["url"] = url_tep(d["file"]) if os.path.isfile(d.get("file", "")) else None
    wav = os.path.join(out, "giong_doc.wav")
    return json_ok({"canh": canh, "dung": dung, "kho": _kho_ra(t), "giong_url": url_tep(wav) if os.path.isfile(wav) else None})


@app.get("/api/kho")
def kho_ds():
    return json_ok({"kho": _kho_ra(slug(tham_so_q("du_an")))})


@app.get("/api/tim_video")
def tim_video():
    import dung_tay
    q = tham_so_q("q").strip()
    if not q:
        raise HTTPError(400, "thiếu từ khoá")
    return json_ok({"ds": dung_tay.tim_youtube(q, n=int(tham_so_q("n") or 12))})


@app.get("/api/tim_anh")
def tim_anh():
    import dung_tay
    q = tham_so_q("q").strip()
    if not q:
        raise HTTPError(400, "thiếu từ khoá")
    return json_ok({"ds": dung_tay.tim_anh(q, n=int(tham_so_q("n") or 40))})


def _vec_tim(d):
    """Vector truy vấn để chấm kết quả tìm: theo cảnh đang chọn nếu có, không thì theo từ khoá."""
    import xep_hang
    canh = None
    if d.get("canh_id") is not None and d.get("du_an"):
        ds = common.doc_json(os.path.join(common.thu_muc_du_an(slug(d["du_an"]))[1], "tu_khoa.json"), []) or []
        canh = next((c for c in ds if c.get("id") == int(d["canh_id"])), None)
    return xep_hang.vec_canh(canh, (d.get("q") or "").strip())


@app.post("/api/diem_video")
def diem_video():
    """Chấm video YouTube (storyboard, không tải video) theo cảnh: {diem: {id: {diem, t}}}."""
    import xep_hang
    d = request.json or {}
    ids = [str(x) for x in (d.get("ids") or [])][:30]
    return json_ok({"diem": xep_hang.diem_video(ids, _vec_tim(d)), "nguong": xep_hang.NGUONG_THAP})


@app.post("/api/diem_anh")
def diem_anh():
    """Chấm ảnh (ảnh thu nhỏ) theo cảnh: {diem: [..]} cùng thứ tự urls."""
    import xep_hang
    d = request.json or {}
    urls = [str(x) for x in (d.get("urls") or [])][:60]
    diem, chu = xep_hang.diem_anh(urls, _vec_tim(d), chu=True)
    return json_ok({"diem": diem, "chu": chu, "nguong": xep_hang.NGUONG_THAP})


procs_ht = {}                                            # dự án -> Popen "hoàn thiện bản nháp" (skill)
BUOC_HT = [("[3] dự án CapCut", "xong"), ("[2] kế hoạch", "đặt lên bản nháp"), ("[LP]", "tìm ảnh highlight"),
           ("lớp ảnh phủ", "tìm ảnh highlight"), ("[HU]", "bản đồ đường đi"), ("Remotion dựng", "render bản đồ"),
           ("[KH]", "chia chương"), ("[1] dự án thô", "đọc dự án"), ("căn giờ từng chữ", "căn giờ theo giọng"),
           ("vệ tinh", "bản đồ vệ tinh")]


def _log_ht(t):
    return os.path.join(common.thu_muc_du_an(t)[1], "hoan_thien.log")


def _in(dong):
    """In ra console; console không in được ký tự (bảng mã cũ) thì bỏ dấu, không để luồng chép log chết."""
    try:
        print(dong, flush=True)
    except (UnicodeEncodeError, OSError):
        try:
            print(dong.encode("ascii", "replace").decode(), flush=True)
        except OSError:
            pass


def _chay_hoan_thien(t, ten, co_nhac=False, co_sfx=False):
    """Khởi chạy skill hoàn thiện ở nền -> tên bản nháp; ném RuntimeError nếu đang chạy."""
    p = procs_ht.get(t)
    if p and p.poll() is None:
        raise RuntimeError("đang hoàn thiện — chờ xong")
    log_f = open(_log_ht(t), "w", encoding="utf-8")
    # BC_DU_AN của máy chủ (dự án mặc định) thắng --du-an trong common.py -> phải đặt đúng dự án cho tiến trình con
    env = dict(os.environ, PYTHONIOENCODING="utf-8", BC_DU_AN=t)
    cmd = [sys.executable, "-X", "utf8", "dung_hoan_chinh.py", "--du-an", t, "--ten", ten]
    if co_nhac:
        cmd.append("--co-nhac")
    if co_sfx:
        cmd.append("--co-sfx")
    procs_ht[t] = subprocess.Popen(cmd,
                                   cwd=os.path.join(ROOT, "chinh_sua"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=env, creationflags=0x08000000 if os.name == "nt" else 0)
    procs_ht[t].ten_nhap = ten

    def chep(p=procs_ht[t]):
        """15/10 user: log ✨ vừa ghi file (giao diện đọc) vừa IN RA CONSOLE (lọc dòng nhiễu kỹ thuật)."""
        nhieu = ("gemini_webapi", "Loading weights", "HF Hub", "HF_TOKEN", "[transformers]", "Skip loading CUDA",
                 "This may result in", "warnings.warn", "UserWarning")
        for b in iter(p.stdout.readline, b""):
            dong = b.decode("utf-8", "replace")
            log_f.write(dong)
            log_f.flush()
            if dong.strip() and not any(x in dong for x in nhieu):
                _in(f"[✨ {t}] {dong.rstrip()}")
        log_f.close()
        _in(f"[✨ {t}] — kết thúc (mã {p.wait()})")
    threading.Thread(target=chep, daemon=True).start()
    return ten


def _anh_ai_ds(t):
    out = common.thu_muc_du_an(t)[1]
    kh = common.doc_json(os.path.join(out, "ke_hoach.json"), {}) or {}
    return out, kh


@app.get("/api/anh_ai")
def anh_ai_ds():
    """19/10 user: danh sách ảnh AI của lần ✨ gần nhất (ke_hoach.json) kèm câu mô tả để sửa tay / vẽ lại."""
    t = slug(tham_so_q("du_an"))
    out, kh = _anh_ai_ds(t)
    ra = []
    for i, y in enumerate(kh.get("anh_ai") or []):
        ds = y.get("ds_anh") or []
        for j, f in enumerate(ds):
            if not os.path.isfile(f):
                continue
            ra.append({"i": i, "j": j, "cau": y.get("cau"), "bd": y.get("bd"), "dai": y.get("dai"), "file": f,
                       "url": url_tep(f) + f"&v={int(os.path.getmtime(f))}", "ve": (y.get("ve") or [""] * len(ds))[j] if j < len(y.get("ve") or []) else "",
                       "text": y.get("text") or "", "thoi_dai": y.get("thoi_dai") or "", "mau": ds[0] if j else ""})
    return json_ok({"ds": ra})


@app.post("/api/anh_ai/ve_thu")
def anh_ai_ve_thu():
    """Vẽ một ảnh THỬ theo câu mô tả đã sửa -> ảnh xem trước (chưa thay ảnh cũ)."""
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    ve = str(d.get("ve") or "").strip()
    mau = d.get("mau") or ""
    if not t or not ve:
        raise HTTPError(400, "thiếu dự án / câu mô tả")
    sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
    import anh_ve
    import minh_hoa
    thu = os.path.join(common.thu_muc_du_an(t)[1], "anh_ai_thu")
    goc = d.get("goc") or ""                                 # 19/10 user: ẢNH CỦA NGƯỜI DÙNG + yêu cầu sửa
    if goc and trong_root(goc) and os.path.isfile(goc):
        p = (f"Edit the attached image: {ve}. Keep everything that the request does not mention exactly as it is (same "
             f"composition, subjects, colours, lighting). Realistic photograph, wide 16:9 landscape. Absolutely NO text, "
             f"NO letters, NO words.")
        tep = [goc]
    else:
        co_mau = bool(mau) and trong_root(mau) and os.path.isfile(mau)
        p = minh_hoa.lenh_ve(ve, d.get("thoi_dai") or "", co_mau=co_mau)
        tep = [mau] if co_mau else None
    ten = hashlib.md5((p + str(time.time())).encode("utf-8")).hexdigest()[:12] + ".png"
    f = anh_ve.ve_prompt(p, thu, ten, tep=tep, timeout=150, do_credit=False)
    if not f or not os.path.isfile(f):
        raise HTTPError(502, "Gemini không trả ảnh (thử lại hoặc sửa câu mô tả)")
    return json_ok({"thu": f, "url": url_tep(f)})


@app.post("/api/anh_ai/luu")
def anh_ai_luu():
    """Người dùng ưng ảnh thử -> thay ảnh cũ TẠI CHỖ (cùng đường dẫn: bản nháp CapCut + lần ✨ sau dùng luôn).
    Ảnh gốc giữ ở <tên>.goc.png; câu mô tả mới lưu ở anh_ai_sua.json + ke_hoach.json."""
    import shutil
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    f, thu, ve = d.get("file") or "", d.get("thu") or "", str(d.get("ve") or "").strip()
    if not (t and trong_root(f) and os.path.isfile(f) and trong_root(thu) and os.path.isfile(thu)):
        raise HTTPError(400, "thiếu / sai tệp")
    goc = os.path.splitext(f)[0] + ".goc.png"
    if not os.path.isfile(goc):
        shutil.copy2(f, goc)
    shutil.copy2(thu, f)
    try:
        os.remove(thu)
    except OSError:
        pass
    out, kh = _anh_ai_ds(t)
    for y in kh.get("anh_ai") or []:
        ds = y.get("ds_anh") or []
        if f in ds:
            v = list(y.get("ve") or [""] * len(ds))
            v += [""] * (len(ds) - len(v))
            v[ds.index(f)] = ve
            y["ve"] = v
    common.ghi_json(os.path.join(out, "ke_hoach.json"), kh)
    p_sua = os.path.join(out, "anh_ai_sua.json")
    sua_ = common.doc_json(p_sua, {}) or {}
    sua_[os.path.basename(f)] = ve
    common.ghi_json(p_sua, sua_)
    return json_ok({"ok": True, "url": url_tep(f) + f"&v={int(time.time())}"})


procs_dx = {}                                            # dự án -> Popen "lập danh sách chỗ vẽ ảnh AI"


def _cau_srt(out):
    """[{i, t0, text}] từ ra/<dự án>/kich_ban_cau.srt (câu của bước ✨)."""
    try:
        s = open(os.path.join(out, "kich_ban_cau.srt"), encoding="utf-8").read()
    except OSError:
        return []
    ra = []
    for m in re.finditer(r"(\d+)\s*\n(\d+):(\d+):(\d+)[,.](\d+) --> [\d:,.]+\s*\n(.*?)(?=\n\s*\n|\Z)", s, re.S):
        h, mi, se, ms = (int(m.group(k)) for k in (2, 3, 4, 5))
        ra.append({"i": int(m.group(1)), "t0": round(h * 3600 + mi * 60 + se + ms / 1000, 2), "text": m.group(6).replace("\n", " ")})
    return ra


@app.get("/api/anh_ai_ke_hoach")
def anh_ai_ke_hoach():
    """19/10 user: danh sách chỗ vẽ ảnh AI (đề xuất của AI, người dùng thêm / bỏ / sửa) + toàn bộ câu lời."""
    t = slug(tham_so_q("du_an"))
    out = common.thu_muc_du_an(t)[1]
    da = common.doc_json(os.path.join(out, "anh_ai_ke_hoach.json"), {}) or {}
    p = procs_dx.get(t)
    return json_ok({"co": isinstance(da.get("ds"), list), "ds": da.get("ds") or [], "cau": _cau_srt(out),
                    "dang": bool(p and p.poll() is None)})


@app.post("/api/anh_ai_ke_hoach/lap")
def lap_anh_ai_ke_hoach():
    """AI (lại) đề xuất danh sách: chạy ✨ ở chế độ --chi-de-xuat-ai (không vẽ, không dựng)."""
    t = slug((request.json or {}).get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    p = procs_dx.get(t)
    if p and p.poll() is None:
        return json_ok({"ok": True, "dang": True})
    out = common.thu_muc_du_an(t)[1]
    f = os.path.join(out, "anh_ai_ke_hoach.json")
    if (request.json or {}).get("lam_lai") and os.path.isfile(f):
        os.remove(f)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", BC_DU_AN=t)
    procs_dx[t] = subprocess.Popen([sys.executable, "-X", "utf8", "dung_hoan_chinh.py", "--du-an", t, "--chi-de-xuat-ai"],
                                   cwd=os.path.join(ROOT, "chinh_sua"), stdout=open(_log_ht(t), "w", encoding="utf-8"),
                                   stderr=subprocess.STDOUT, env=env, creationflags=0x08000000 if os.name == "nt" else 0)
    return json_ok({"ok": True, "dang": True})


@app.post("/api/anh_ai_ke_hoach/luu")
def luu_anh_ai_ke_hoach():
    """Lưu danh sách người dùng đã duyệt (giữ khoá câu lời để ✨ biết danh sách còn khớp)."""
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or not isinstance(d.get("ds"), list):
        raise HTTPError(400, "thiếu dữ liệu")
    p = os.path.join(common.thu_muc_du_an(t)[1], "anh_ai_ke_hoach.json")
    da = common.doc_json(p, {}) or {}
    ds = []
    for y in d["ds"]:
        try:
            i = int(y.get("cau"))
            den = max(i, int(y.get("den_cau") or i))
        except (TypeError, ValueError):
            continue
        z = {k: v for k, v in y.items() if k in ("ve_1", "ve_2", "ve_3", "moc_1", "moc_2", "moc_3", "thoi_dai", "tieu_de", "moc", "bo", "tay")}
        z.update(cau=i, den_cau=den)
        ds.append(z)
    common.ghi_json(p, dict(da, ds=sorted(ds, key=lambda z: z["cau"]), duyet=True))
    return json_ok({"ok": True, "so": len(ds)})


# --------------------------------------------------------------------------- 🎨 tạo ảnh rồi chèn thẳng vào bản nháp
def _chen_ds(t):
    return os.path.join(common.thu_muc_du_an(t)[1], "anh_chen.json")


@app.get("/api/chen_anh")
def chen_anh_ds():
    """19/10 user: câu lời (mốc giờ) + bản nháp CapCut của dự án + ảnh đã giữ để chèn."""
    t = slug(tham_so_q("du_an"))
    out = common.thu_muc_du_an(t)[1]
    cau = _cau_srt(out)
    if not cau:                                              # chưa chạy ✨: dùng cảnh của bản thô
        cau = [{"i": c["id"], "t0": float(c.get("bat_dau") or 0), "text": c.get("text") or ""}
               for c in common.doc_json(os.path.join(out, "tu_khoa.json"), []) or []]
    dd = common.thu_muc_nhap_capcut()
    nhap = []
    if dd and os.path.isdir(dd):
        nhap = sorted((f for f in os.listdir(dd) if os.path.isdir(os.path.join(dd, f)) and (f == t or f.startswith(t + "_"))),
                      key=lambda f: -os.path.getmtime(os.path.join(dd, f)))
    ds = [dict(y, url=url_tep(y["file"])) for y in (common.doc_json(_chen_ds(t), {}) or {}).get("ds") or []
          if os.path.isfile(y.get("file", ""))]
    return json_ok({"cau": cau, "nhap": nhap, "ds": ds, "thu": os.path.join(out, "anh_chen")})


@app.post("/api/chen_anh/giu")
def chen_anh_giu():
    """Giữ ảnh vừa vẽ (ảnh thử) cho một mốc giờ -> ra/<dự án>/anh_chen/."""
    import shutil
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    thu = d.get("thu") or ""
    if not t or not (trong_root(thu) and os.path.isfile(thu)):
        raise HTTPError(400, "thiếu ảnh")
    f = _ten_anh_chen(t, d.get("bd"), d.get("cau"), os.path.splitext(thu)[1])
    shutil.move(thu, f)
    _them_anh_chen(t, f, d.get("bd"), d.get("dai") or 3, d.get("ve"), d.get("cau"))
    return json_ok({"ok": True})


def _ten_anh_chen(t, bd, cau, duoi):
    """ra/<dự án>/anh_chen/<mốc giờ>[_cau<i>].<đuôi> — 19/10 user: tên file theo MỐC GIỜ để kéo thả tay vào CapCut."""
    out = common.thu_muc_du_an(t)[1]
    os.makedirs(os.path.join(out, "anh_chen"), exist_ok=True)
    bd = max(0.0, float(bd or 0))
    ten = f"{int(bd // 60):02d}m{bd % 60:04.1f}s" + (f"_cau{cau}" if cau is not None else "")
    f = os.path.join(out, "anh_chen", ten + duoi)
    k = 2
    while os.path.exists(f):
        f = os.path.join(out, "anh_chen", f"{ten}_{k}{duoi}")
        k += 1
    return f


def _them_anh_chen(t, f, bd, dai, ve, cau):
    da = common.doc_json(_chen_ds(t), {}) or {}
    ds = da.get("ds") or []
    ds.append({"file": f, "bd": round(float(bd or 0), 2), "dai": round(max(0.5, float(dai or 3)), 2),
               "ve": str(ve or ""), "cau": cau, "da_chen": []})
    common.ghi_json(_chen_ds(t), dict(da, ds=sorted(ds, key=lambda y: y["bd"])))


@app.post("/api/chen_anh/tai_video")
def chen_anh_tai_video():
    """20/10 user: kéo VIDEO Gemini vào -> xoá logo ✦ (dò vị trí tự động, gwt từng khung) -> lưu thẳng vào kho ảnh đã giữ
    của dự án (ra/<dự án>/anh_chen/, tên theo mốc giờ đang chọn). Chạy nền, trả job."""
    t = slug(request.forms.get("du_an", ""))
    up = request.files.get("tep")
    if not t or not up:
        raise HTTPError(400, "thiếu dự án / video")
    duoi = os.path.splitext(up.raw_filename or up.filename)[1].lower()
    if duoi not in (".mp4", ".mov", ".webm", ".mkv"):
        raise HTTPError(400, "chỉ nhận video .mp4 .mov .webm .mkv")
    thu = os.path.join(common.thu_muc_du_an(t)[1], "anh_ai_thu")
    os.makedirs(thu, exist_ok=True)
    goc = os.path.join(thu, "vgoc_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:10] + duoi)
    up.save(goc, overwrite=True)
    ten_goc = up.raw_filename or up.filename
    bd, cau = request.forms.get("bd") or 0, request.forms.get("cau")
    cau = int(cau) if str(cau or "").lstrip("-").isdigit() else None

    def lam(bao):
        sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
        import anh_ve
        f = _ten_anh_chen(t, bd, cau, ".mp4")
        try:
            kq = anh_ve.xoa_logo_video(goc, f, bao)
        finally:
            if os.path.isfile(goc):
                os.remove(goc)
        _them_anh_chen(t, f, bd, kq["giay"], f"video: {ten_goc}", cau)
        return {"file": f, "co_logo": kq["co_logo"], "giay": kq["giay"]}
    return json_ok({"job": _job_doi_thu(lam)})


@app.post("/api/chen_anh/tai_len")
def chen_anh_tai_len():
    """Ảnh người dùng tải lên (làm ảnh gốc để Gemini sửa theo yêu cầu) -> ra/<dự án>/anh_ai_thu/goc_*.ext"""
    t = slug(request.forms.get("du_an", ""))
    up = request.files.get("tep")
    if not t or not up:
        raise HTTPError(400, "thiếu dự án / ảnh")
    duoi = os.path.splitext(up.raw_filename or up.filename)[1].lower()
    if duoi not in (".png", ".jpg", ".jpeg", ".webp"):
        raise HTTPError(400, "chỉ nhận ảnh .png .jpg .webp")
    thu = os.path.join(common.thu_muc_du_an(t)[1], "anh_ai_thu")
    os.makedirs(thu, exist_ok=True)
    f = os.path.join(thu, "goc_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:10] + duoi)
    up.save(f, overwrite=True)
    sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
    import anh_ve
    anh_ve.xoa_logo(f)                                       # 19/10: ảnh gốc còn logo -> Gemini vẽ lại cả logo cũ vào ảnh
    return json_ok({"file": f, "url": url_tep(f) + f"&v={int(time.time())}"})


@app.post("/api/flow_video")
def flow_video_tao():
    """20/10 user: ô nhập câu lệnh tạo VIDEO bằng Google Flow (giống ô của Flow) -> MP4 xem trước ở anh_ai_thu/ (chạy nền).
    Video về được soát logo ✦ Gemini, có thì xoá (anh_ve.xoa_logo_video). Ưng thì ✅ Giữ -> kho ảnh đã giữ."""
    import flow_video
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    anh = {}
    for k in ("anh_dau", "anh_cuoi"):
        f = str(d.get(k) or "")
        anh[k] = f if f and trong_root(f) and os.path.isfile(f) else None
    prompt = str(d.get("prompt") or "").strip()
    if not prompt and not anh["anh_dau"]:
        raise HTTPError(400, "chưa có câu lệnh")
    model = d.get("model") if d.get("model") in flow_video.MODEL else flow_video.MODEL[0]
    thu = os.path.join(common.thu_muc_du_an(t)[1], "anh_ai_thu")
    ten_goc = "flow_" + hashlib.md5((prompt + str(time.time())).encode("utf-8")).hexdigest()[:10]

    def lam(bao):
        kq = flow_video.tao(prompt, thu, ten_goc, ti_le="9:16" if d.get("ti_le") == "9:16" else "16:9", model=model,
                            phan_giai=str(d.get("phan_giai") or ""), do_dai=str(d.get("do_dai") or ""),
                            so=int(d.get("so") or 1), anh_dau=anh["anh_dau"], anh_cuoi=anh["anh_cuoi"],
                            ho_so=str(d.get("ho_so") or ""), bao=bao)
        sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
        import anh_ve
        ds = []
        for f in kq["tep"]:
            bao(f"Soát logo {os.path.basename(f)}…")
            tam = f[:-4] + "._sach.mp4"
            r = anh_ve.xoa_logo_video(f, tam, bao)
            os.replace(tam, f)
            ds.append({"file": f, "url": url_tep(f) + f"&v={int(time.time())}", "giay": r["giay"], "co_logo": r["co_logo"]})
        return {"ds": ds, "ho_so": kq["ho_so"], "cai_dat": kq["cai_dat"], "diem": kq["diem"]}
    return json_ok({"job": _job_doi_thu(lam)})


@app.post("/api/canh_remotion")
def canh_remotion():
    """20/10 user: 🎬 cảnh Remotion theo mô tả -> MP4 xem trước (chạy nền: AI viết kịch bản cảnh + Remotion dựng)."""
    import canh_mo_ta
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    mo_ta = str(d.get("mo_ta") or "").strip()
    giay = max(1.0, min(60.0, float(d.get("giay") or 4)))
    goc = d.get("goc") or ""
    goc = goc if goc and trong_root(goc) and os.path.isfile(goc) else None
    if not t or not mo_ta:
        raise HTTPError(400, "thiếu dự án / mô tả")
    out = os.path.join(common.thu_muc_du_an(t)[1], "anh_ai_thu",
                       "canh_" + hashlib.md5((mo_ta + str(time.time())).encode("utf-8")).hexdigest()[:10] + ".mp4")

    def lam(bao):
        bao("AI viết kịch bản cảnh…")
        kb = canh_mo_ta.lap(mo_ta, giay, goc)
        bd = kb.get("ban_do")
        if bd:
            bao("Địa danh tìm thấy: " + " · ".join(d["ten_day_du"] for d in bd["diem"]))
        else:
            bao(f"Remotion dựng cảnh ({len(kb['lop'])} lớp)…")
        canh_mo_ta.dung(kb, giay, out, bao)
        return {"thu": out, "url": url_tep(out) + f"&v={int(time.time())}", "kb": kb}
    return json_ok({"job": _job_doi_thu(lam)})


@app.post("/api/chen_anh/xoa_logo")
def chen_anh_xoa_logo():
    """Xoá logo ✦ Gemini cho mọi ảnh đã giữ của dự án (ảnh giữ trước khi có công cụ). Ảnh không có logo để nguyên."""
    t = slug((request.json or {}).get("du_an", ""))
    sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
    import anh_ve
    thu = os.path.join(common.thu_muc_du_an(t)[1], "anh_chen")
    n = sum(1 for f in (os.listdir(thu) if os.path.isdir(thu) else [])
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and anh_ve.xoa_logo(os.path.join(thu, f)))   # mp4 bỏ qua
    return json_ok({"ok": True, "so": n})


@app.post("/api/chen_anh/mo_thu_muc")
def chen_anh_mo_thu_muc():
    """Mở thư mục ảnh đã giữ (kéo thả tay vào CapCut khi bản nháp đang mở)."""
    t = slug((request.json or {}).get("du_an", ""))
    thu = os.path.join(common.thu_muc_du_an(t)[1], "anh_chen")
    os.makedirs(thu, exist_ok=True)
    os.startfile(thu)
    return json_ok({"ok": True, "thu": thu})


@app.post("/api/chen_anh/xoa")
def chen_anh_xoa():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    da = common.doc_json(_chen_ds(t), {}) or {}
    da["ds"] = [y for y in da.get("ds") or [] if y.get("file") != d.get("file")]
    common.ghi_json(_chen_ds(t), da)
    return json_ok({"ok": True})


@app.post("/api/chen_anh/chen")
def chen_anh_chen():
    """Chèn mọi ảnh đã giữ (chưa chèn vào bản nháp này) vào bản nháp CapCut: MỘT track mới phía trên, ảnh 120% (giấu dấu
    Gemini) phóng chậm. Bản nháp phải ĐÓNG trong CapCut (CapCut đang mở sẽ ghi đè)."""
    import pycapcut as draft
    from pycapcut import trange
    import dung_tay
    sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
    import anh_ve
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    ten = str(d.get("nhap") or "")
    dd = common.thu_muc_nhap_capcut()
    if not (t and dd and ten and os.path.isdir(os.path.join(dd, ten))):
        raise HTTPError(400, "không thấy bản nháp")
    da = common.doc_json(_chen_ds(t), {}) or {}
    can = [y for y in da.get("ds") or [] if os.path.isfile(y.get("file", "")) and ten not in (y.get("da_chen") or [])]
    if not can:
        raise HTTPError(400, "không còn ảnh nào chưa chèn vào bản nháp này")
    SEC = 1_000_000
    sc = draft.DraftFolder(dd).load_template(ten)
    tr = "anh_chen_" + time.strftime("%H%M%S")
    sc.add_track(draft.TrackType.video, track_name=tr, relative_index=30)
    KP = draft.KeyframeProperty
    cuoi, n = 0, 0
    for y in sorted(can, key=lambda z: z["bd"]):
        st, dl = max(int(y["bd"] * SEC), cuoi), int((y["bd"] + y["dai"]) * SEC) - max(int(y["bd"] * SEC), cuoi)
        if dl < int(0.4 * SEC):
            continue
        mat = draft.VideoMaterial(y["file"])
        la_video = y["file"].lower().endswith(".mp4")        # cảnh Remotion: giữ nguyên khung, không quá độ dài clip
        if la_video:
            dl = min(dl, int(mat.duration) - 1000)
            if dl < int(0.4 * SEC):
                continue
        seg = draft.VideoSegment(mat, trange(st, dl))
        if not la_video:
            ph = anh_ve.PHONG_ANH_AI                         # 1.0 khi đã xoá được logo (cũ: 120% giấu logo)
            seg.add_keyframe(KP.uniform_scale, 0, ph)
            seg.add_keyframe(KP.uniform_scale, dl - 1000, ph * 1.06)
        sc.add_segment(seg, track_name=tr)
        cuoi = st + dl
        y.setdefault("da_chen", []).append(ten)
        n += 1
    sc.save()
    try:
        dung_tay._sua_nhap(os.path.join(dd, ten), [y["file"] for y in can])   # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        pass
    common.ghi_json(_chen_ds(t), da)
    return json_ok({"ok": True, "so": n, "track": tr})


TT_SUA_GIONG = {}                                        # dự án -> {dang, dong[], kq}


@app.post("/api/sua_giong")
def sua_giong():
    """19/10 user: 🔁 Sửa câu đọc sai — soát lại giọng, đọc lại câu sai, ghép lại giong_doc.wav (giữ mốc giờ), chạy nền."""
    import giong
    t = slug((request.json or {}).get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    if (TT_SUA_GIONG.get(t) or {}).get("dang"):
        return json_ok({"ok": True, "dang": True})
    tt = TT_SUA_GIONG[t] = {"dang": True, "dong": [], "kq": None, "loi": ""}

    def chay():
        try:
            tt["kq"] = giong.sua_cau_sai(t, bao=lambda m: (tt["dong"].append(m), _in(f"[🔁 {t}] {m}")))
        except Exception as e:                               # noqa: BLE001
            tt["loi"] = str(e)[:300]
        tt["dang"] = False
    threading.Thread(target=chay, daemon=True).start()
    return json_ok({"ok": True, "dang": True})


@app.get("/api/sua_giong_tt")
def sua_giong_tt():
    t = slug(tham_so_q("du_an"))
    return json_ok(TT_SUA_GIONG.get(t) or {"dang": False, "dong": [], "kq": None, "loi": ""})


# --------------------------------------------------------------------------- 📈 đối thủ YouTube (20/10 user)
TRANG_DOI_THU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doi_thu.html")
TT_DOI_THU = {}                                          # job -> {dang, dong, kq, loi}


@app.get("/doi_thu")
def trang_doi_thu():
    response.content_type = "text/html; charset=utf-8"
    return doc_text(TRANG_DOI_THU)


def _job_doi_thu(ham):
    job = hashlib.md5(str(time.time()).encode()).hexdigest()[:10]
    tt = TT_DOI_THU[job] = {"dang": True, "dong": "Bắt đầu…", "kq": None, "loi": ""}

    def bao(m, *_):
        tt["dong"] = m

    def chay():
        try:
            tt["kq"] = ham(bao)
        except Exception as e:                               # noqa: BLE001
            tt["loi"] = str(e)[:300]
        tt["dang"] = False
    threading.Thread(target=chay, daemon=True).start()
    return job


@app.post("/api/doi_thu/gio")
def doi_thu_gio():
    import doi_thu
    d = request.json or {}
    kenh, n = str(d.get("kenh") or "").strip(), max(5, min(300, int(d.get("n") or 50)))
    if not kenh:
        raise HTTPError(400, "thiếu kênh")
    return json_ok({"job": _job_doi_thu(lambda bao: doi_thu.quet_gio(kenh, n, bao))})


@app.post("/api/doi_thu/dot_bien")
def doi_thu_dot_bien():
    import doi_thu
    d = request.json or {}
    tk = [str(t) for t in d.get("tu_khoa") or [] if str(t).strip()]
    if not tk:
        raise HTTPError(400, "thiếu từ khoá")
    return json_ok({"job": _job_doi_thu(lambda bao: doi_thu.tim_dot_bien(
        tk, n_moi_tu=max(5, min(100, int(d.get("n") or 30))), sub_toi_da=int(d.get("sub_max") or 50000),
        ngay_toi_da=int(d.get("ngay_max") or 30), view_toi_thieu=int(d.get("view_min") or 0),
        bo_short=bool(d.get("bo_short", True)), bo_tieng_viet=bool(d.get("bo_vi")), bao=bao))})


@app.post("/api/doi_thu/tu_khoa")
def doi_thu_tu_khoa():
    """AI lấy ngách + từ khoá tìm tiếng Anh từ kênh đối thủ."""
    import doi_thu
    kenh = str((request.json or {}).get("kenh") or "").strip()
    if not kenh:
        raise HTTPError(400, "thiếu kênh")
    return json_ok({"job": _job_doi_thu(lambda bao: doi_thu.tu_khoa_tu_kenh(kenh, bao=bao))})


@app.get("/api/doi_thu/tt")
def doi_thu_tt():
    return json_ok(TT_DOI_THU.get(tham_so_q("job")) or {"dang": False, "loi": "không thấy việc"})


@app.post("/api/dung/hoan_thien")
def dung_hoan_thien():
    """Chạy skill hoàn thiện (chinh_sua/dung_hoan_chinh.py) ở nền cho dự án: diễn cảnh, bản đồ, nhạc, chuyển cảnh
    -> bản nháp CapCut mới. Log ở ra/<dự án>/hoan_thien.log."""
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    ten = (d.get("ten") or f"{t}_hoan_chinh").strip()
    co_nhac = bool(d.get("co_nhac", False))
    co_sfx = bool(d.get("co_sfx", False))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    try:
        return json_ok({"ok": True, "ten": _chay_hoan_thien(t, ten, co_nhac=co_nhac, co_sfx=co_sfx)})
    except RuntimeError as e:
        raise HTTPError(409, str(e))


@app.get("/api/dung/hoan_thien_tt")
def dung_hoan_thien_tt():
    t = slug(tham_so_q("du_an"))
    p = procs_ht.get(t)
    try:
        dong = [x.rstrip() for x in open(_log_ht(t), encoding="utf-8", errors="ignore").read().splitlines() if x.strip()]
    except OSError:
        dong = []
    dong = [x for x in dong if not re.search(r"Warning|Loading weights|transformers\]|Some weights|You should|chatgpt '", x)]
    buoc = ""
    for x in reversed(dong):
        hit = next((b for k, b in BUOC_HT if k in x), None)
        if hit:
            buoc = hit
            break
    dang = bool(p and p.poll() is None)
    loi = ""
    if p and not dang and p.returncode != 0:
        loi = next((x for x in reversed(dong) if "Error" in x or "Traceback" in x), "lỗi (xem hoan_thien.log)")[:300]
    return json_ok({"dang": dang, "buoc": buoc, "cuoi": dong[-1][:160] if dong else "", "loi": loi,
                    "xong": bool(p and not dang and p.returncode == 0), "ten": getattr(p, "ten_nhap", "")})


@app.post("/api/dung/tu_dong")
def dung_tu_dong():
    """Tự tìm + tải (ngân sách phút video) + khớp + ảnh bù + bản nháp — chạy nền.
    Hỗ trợ che_do='chu_de' (mặc định) hoặc 'canh'."""
    import tu_dong_tim
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    che_do = (d.get("che_do") or "chu_de").strip().lower()
    try:
        ten_ht = (d.get("ten_ht") or f"{t}_hoan_chinh").strip()
        tu_dong_tim.chay_nen(t, float(d.get("ngan_sach") or tu_dong_tim.NGAN_SACH_PHUT),
                             (d.get("ten_nhap") or "").strip() or None,
                             sau=(lambda: _chay_hoan_thien(t, ten_ht)) if d.get("hoan_thien") else None,
                             dung_stock=bool(d.get("dung_stock", True)),
                             che_do=che_do)
    except ValueError as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "che_do": che_do})


@app.get("/api/dung/tu_dong_tt")
def dung_tu_dong_tt():
    import tu_dong_tim
    return json_ok(tu_dong_tim.TT.get(slug(tham_so_q("du_an")), {}))


def _tom_chu_the(t):
    import chu_the
    out = common.thu_muc_du_an(t)[1]
    cd = (common.doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("chu_de") or []
    dem = {}
    for d in cd:
        if d.get("chu_the") is not None and not d.get("chi_tim"):
            dem[d["chu_the"]] = dem.get(d["chu_the"], 0) + int(d.get("so_canh") or 0)
    return {"ok": True, "chu_the": chu_the.doc_goc(t), "tu_khoa_them": chu_the.tu_khoa_them(t), "so_canh": dem,
            "tong_canh": sum(dem.values()),
            "canh": chu_the.ds_canh(t)}


@app.get("/api/chu_the")
def lay_chu_the():
    """19/10 user: chủ thể của cả video (hỏi AI một lần nếu chưa có) + số cảnh mỗi chủ thể."""
    import chu_the
    t = slug(tham_so_q("du_an"))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    try:
        if not chu_the.doc(t):
            chu_the.chia_doan(t)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok(_tom_chu_the(t))


@app.post("/api/chu_the/luu")
def luu_chu_the():
    """Lưu danh sách chủ thể người dùng sửa -> chia lại đoạn (cục bộ, không hỏi AI)."""
    import chu_the
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or not isinstance(d.get("chu_the"), list):
        raise HTTPError(400, "thiếu dữ liệu")
    try:
        chu_the.luu(t, d["chu_the"], d.get("gan_tay") if isinstance(d.get("gan_tay"), dict) else None,
                    d.get("tu_khoa_them") if isinstance(d.get("tu_khoa_them"), list) else None,
                    d.get("tk_cau") if isinstance(d.get("tk_cau"), dict) else None)
    except Exception as e:                                   # noqa: BLE001  (dịch từ khoá hỏng)
        raise HTTPError(400, str(e)[:200])
    chu_the.chia_doan(t)
    return json_ok(_tom_chu_the(t))


@app.post("/api/chu_the/lap")
def lap_lai_chu_the():
    """Hỏi AI lập lại danh sách chủ thể từ đầu."""
    import chu_the
    t = slug((request.json or {}).get("du_an", ""))
    try:
        chu_the.chia_doan(t, hoi_lai=True)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok(_tom_chu_the(t))


@app.get("/api/chu_de")
def lay_chu_de():
    """Lấy danh sách chủ đề kịch bản (chia mới nếu chưa có)."""
    import chu_de
    t = slug(tham_so_q("du_an"))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    try:
        ds = chu_de.doc_chu_de(t)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "du_an": t, "chu_de": ds})


@app.post("/api/chu_de/chia")
def chia_lai_chu_de():
    """Buộc chia lại chủ đề kịch bản từ Gemini / ChatGPT."""
    import chu_de
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    try:
        ds = chu_de.chia_chu_de(t, buoc_lai=True)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "du_an": t, "chu_de": ds})


@app.post("/api/chu_de/luu")
def luu_chu_de():
    """Lưu danh sách chủ đề sau khi người dùng sửa từ khoá trên giao diện."""
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    ds = d.get("chu_de")
    if not t or not isinstance(ds, list):
        raise HTTPError(400, "thiếu dữ liệu chủ đề")
    _, out = common.thu_muc_du_an(t)
    p = os.path.join(out, "chu_de.json")
    cu = common.doc_json(p, {}) or {}
    cu["chu_de"] = ds
    cu["so_chu_de"] = len(ds)
    common.ghi_json(p, cu)
    return json_ok({"ok": True, "so_chu_de": len(ds)})


def _cot_loi_kem_file(t, da):
    """Gắn đường dẫn ảnh đã vẽ (nếu có) vào từng ảnh của danh sách ý cốt lõi — để bảng 🎯 xem ảnh."""
    import dung_tay
    kho = dung_tay.doc_kho(t)
    for y in da.get("y") or []:
        for a in y.get("anh") or []:
            m = kho.get(a.get("kho_id") or "") or {}
            a["file"] = m.get("file") if m.get("trang_thai") == "xong" else ""
    return da


@app.get("/api/cot_loi")
def lay_cot_loi():
    """18/10: danh sách Ý CỐT LÕI (ảnh AI thay hẳn video) của dự án — lập mới nếu chưa có."""
    import cot_loi
    t = slug(tham_so_q("du_an"))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    try:
        da = cot_loi.lap(t)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "du_an": t, **_cot_loi_kem_file(t, da), "tt": cot_loi.TT.get(t, {})})


@app.post("/api/cot_loi/lap")
def lap_lai_cot_loi():
    """Buộc AI chọn lại ý cốt lõi."""
    import cot_loi
    t = slug((request.json or {}).get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    try:
        da = cot_loi.lap(t, buoc_lai=True)
    except Exception as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "du_an": t, **_cot_loi_kem_file(t, da)})


@app.post("/api/cot_loi/luu")
def luu_cot_loi():
    """Lưu danh sách ý cốt lõi sau khi người dùng sửa câu mô tả / xoá ý / xoá ảnh."""
    import cot_loi
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    ys = d.get("y")
    if not t or not isinstance(ys, list):
        raise HTTPError(400, "thiếu dữ liệu ý cốt lõi")
    da = cot_loi.luu(t, ys)
    return json_ok({"ok": True, **_cot_loi_kem_file(t, da)})


@app.post("/api/cot_loi/ve")
def ve_cot_loi():
    """Vẽ (chạy nền) mọi ảnh cốt lõi còn thiếu."""
    import cot_loi
    t = slug((request.json or {}).get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    if cot_loi.TT.get(t, {}).get("dang"):
        raise HTTPError(400, "đang vẽ — chờ xong")
    cot_loi.TT[t] = {"dang": True, "xong": 0, "tong": 0}
    cot_loi.ve_nen(t)
    return json_ok({"ok": True})


@app.get("/api/cot_loi/tt")
def tt_cot_loi():
    import cot_loi
    t = slug(tham_so_q("du_an"))
    return json_ok({**cot_loi.TT.get(t, {}), **_cot_loi_kem_file(t, cot_loi.doc(t))})


@app.get("/api/duyet_nguon/ds")
def duyet_nguon_ds():
    """Lấy danh sách video và ảnh tư liệu lịch sử cho từng chủ đề để người dùng duyệt và chọn."""
    import duyet_nguon
    t = slug(tham_so_q("du_an"))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    nam_truoc = tham_so_q("nam_truoc") or None
    bo_kenh_lon = tham_so_q("bo_kenh_lon") in ("1", "true")
    lam_moi = tham_so_q("lam_moi") in ("1", "true")
    try:
        ds_cd = duyet_nguon.tim_video_theo_chu_de(t, nam_truoc=nam_truoc, bo_kenh_lon=bo_kenh_lon, lam_moi=lam_moi)
        ds_ls = duyet_nguon.tim_anh_lich_su(t)
        return json_ok({"ok": True, "du_an": t, "chu_de": ds_cd, "lich_su": ds_ls})
    except Exception as e:
        raise HTTPError(400, str(e))


@app.post("/api/duyet_nguon/tai_va_ghep")
def duyet_nguon_tai_va_ghep():
    """Tải các video và ảnh tư liệu đã được người dùng tick chọn, sau đó ghép và tạo bản nháp CapCut."""
    import duyet_nguon
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    chon_video = d.get("chon_video") or {}
    chon_anh = d.get("chon_anh") or {}
    ten_nhap = d.get("ten_nhap") or f"{t}_tu_chon"

    def chay():
        try:
            duyet_nguon.tai_va_ghep_da_chon(t, chon_video, chon_anh, ten_nhap=ten_nhap)
        except Exception as e:
            common.log(f"  [duyệt nguồn] lỗi: {e}")
            duyet_nguon._tt(t, buoc="loi", dang=False, loi=str(e))

    threading.Thread(target=chay, daemon=True).start()
    return json_ok({"ok": True, "dang_chay": True})


@app.get("/api/duyet_nguon/tien_do")
def duyet_nguon_tien_do():
    """Xem tiến độ tải và ghép nguồn đã chọn."""
    import duyet_nguon
    t = slug(tham_so_q("du_an"))
    if not t:
        raise HTTPError(400, "thiếu dự án")
    return json_ok(duyet_nguon.TT.get(t, {}))



@app.post("/api/kho/tai_video")
def kho_tai_video():
    import dung_tay
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or not d.get("id"):
        raise HTTPError(400, "thiếu dự án hoặc video")
    kid = dung_tay.tai_video(t, str(d["id"]), d.get("tieu_de", ""), d.get("dai") or 0, tay=True)
    return json_ok({"ok": True, "kho_id": kid})


@app.post("/api/kho/tai_anh")
def kho_tai_anh():
    import dung_tay
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or not d.get("url"):
        raise HTTPError(400, "thiếu dự án hoặc link ảnh")
    try:
        kid = dung_tay.tai_anh(t, d["url"], d.get("tieu_de", ""))
    except Exception as e:                                  # noqa: BLE001
        raise HTTPError(400, f"không tải được ảnh: {common.gon_loi(e)}")
    return json_ok({"ok": True, "kho_id": kid})


@app.post("/api/dung/luu")
def dung_luu():
    import dung_tay
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    if not t or d.get("canh_id") is None:
        raise HTTPError(400, "thiếu dự án hoặc cảnh")
    return json_ok({"ok": True, "canh": dung_tay.luu_canh(t, int(d["canh_id"]), d.get("doan") or [])})


@app.post("/api/dung/cat")
def dung_cat():
    import dung_tay
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    try:
        cat = dung_tay.cat_canh(t, int(d["canh_id"]))
    except ValueError as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "so": len(cat)})


@app.post("/api/dung/goi_y")
def dung_goi_y():
    """Gợi ý tự động: có canh_id -> làm ngay cho cảnh đó (ghi đè); không -> chạy nền cho mọi cảnh CHƯA dựng."""
    import goi_y
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    try:
        if d.get("canh_id") is not None:
            n = goi_y.goi_y(t, [int(d["canh_id"])], chi_canh_trong=False)
            return json_ok({"ok": True, "so_canh": n})
        goi_y.goi_y_nen(t, ten_nhap=(d.get("ten_nhap") or "").strip() or None)
    except ValueError as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True, "nen": True})


@app.get("/api/dung/goi_y_tt")
def dung_goi_y_tt():
    import goi_y
    return json_ok(goi_y.TT.get(slug(tham_so_q("du_an")), {}))


@app.post("/api/dung/nhap")
def dung_nhap():
    import dung_tay
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    dd = common.thu_muc_nhap_capcut()
    if not dd:
        raise HTTPError(400, "không dò được thư mục CapCut Drafts")
    ten = (d.get("ten") or t).strip()
    n = dung_tay.tao_nhap(t, ten, dd)
    return json_ok({"ok": True, "so": n, "ten": ten})


@app.post("/api/dung")
def dung():
    t = slug((request.json or {}).get("du_an", ""))
    p = procs.get(t)
    pid = p.pid if p and p.poll() is None else pid_cu(t)
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=0x08000000)
    return json_ok({"ok": True})


@app.get("/api/trang_thai")
def trang_thai():
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    st = common.doc_json(os.path.join(out, "trang_thai.json"), {}) or {}
    log = doc_text(os.path.join(out, "chay.log"))
    dong = [l for l in log.splitlines() if l.strip() and not re.search(r"warn|symlink|Loading weights", l, re.I)]
    chay_khong = dang_chay(t)
    buoc = st.get("buoc", {})
    if not chay_khong:                                   # tiến trình đã dừng/chết giữa chừng: đừng hiện "đang chạy" mãi
        buoc = {k: (dict(v, tt="dung", ghi_chu="đã dừng") if v.get("tt") == "dang" else v) for k, v in buoc.items()}
    return json_ok({"bay_gio": time.time(), "dang_chay": chay_khong, "buoc": buoc, "log": dong[-25:],
                    "xong": os.path.isfile(os.path.join(out, "tu_khoa.json")),
                    "lan_chay": common.doc_json(os.path.join(out, "lan_chay.json"), {})})


# --------------------------------------------------------------------------- duyệt bản thô
@app.get("/api/ket_qua")
def ket_qua():
    t = slug(tham_so_q("du_an"))
    cache, out = common.thu_muc_du_an(t)
    canh = common.doc_json(os.path.join(out, "ket_qua.json"), None)
    if not canh:
        return json_ok({"o": []})
    cam = common.doc_json(os.path.join(cache, "cam_chon.json"), {}) or {}
    o_ra = []
    for c in canh:
        nh = c.get("nhip") or []
        for k, o in enumerate(c.get("o", [])):
            n = nh[o["nhip"]] if nh and o.get("nhip") is not None and o["nhip"] < len(nh) else {}
            khoa = f"{c['id']}.{o.get('nhip', k)}"
            clip = o.get("clip") or ""
            o_ra.append({"khoa": khoa, "canh": c["id"], "text": n.get("text") or c.get("text", ""),
                         "mo_ta": n.get("mo_ta", ""), "nguon": o.get("nguon"), "tieu_de": (o.get("tieu_de") or "")[:70],
                         "kenh": o.get("kenh", ""), "diem": o.get("diem"), "co_chu": bool(o.get("co_chu")),
                         "dai": o.get("dai"), "dohoa": o.get("do_hoa"), "clip": clip,
                         "thumb": url_tep(clip, "thumb") if clip else "",
                         "video": url_tep(clip) if clip else "",
                         "sai": bool(cam.get(khoa)),
                         "ma": o.get("id") or os.path.splitext(os.path.basename(o.get("anh", "")))[0]})
    return json_ok({"o": o_ra})


@app.post("/api/danh_dau")
def danh_dau():
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    cache, _ = common.thu_muc_du_an(t)
    p = os.path.join(cache, "cam_chon.json")
    cam = common.doc_json(p, {}) or {}
    khoa, ma = d.get("khoa"), d.get("ma")
    if d.get("sai"):
        cam.setdefault(khoa, [])
        if ma and ma not in cam[khoa]:
            cam[khoa].append(ma)
    else:
        cam.pop(khoa, None)
    common.ghi_json(p, cam)
    return json_ok({"ok": True, "so_sai": len(cam)})


@app.post("/api/chon_lai")
def chon_lai():
    t = slug((request.json or {}).get("du_an", ""))
    cache, out = common.thu_muc_du_an(t)
    tham = common.doc_json(os.path.join(out, "lan_chay.json"), {}) or {}
    pid = khoi_dong(t, tham)
    return json_ok({"ok": True, "pid": pid})


@app.post("/api/mo_thu_muc")
def mo_thu_muc():
    t = slug((request.json or {}).get("du_an", ""))
    cache, out = common.thu_muc_du_an(t)
    os.startfile(out)
    return json_ok({"ok": True})


# --------------------------------------------------------------------------- khởi động
class _LuongMay(ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = False      # Windows: True cho phép HAI máy chủ cùng nghe một cổng -> bản mới không bao giờ nhận yêu cầu


class _Im(WSGIRequestHandler):
    def log_message(self, *a):
        pass


def main():
    srv, cong = None, PORT
    for cong in range(PORT, PORT + 20):                 # cổng bận (app khác/bản chạy trước) thì lấy cổng kế
        try:
            srv = make_server("127.0.0.1", cong, app, server_class=_LuongMay, handler_class=_Im)
            break
        except OSError:
            continue
    if srv is None:
        raise SystemExit(f"Không mở được cổng nào trong {PORT}-{PORT + 19}")
    url = f"http://127.0.0.1:{cong}/"
    print("Giao diện:", url, flush=True)
    bat_nhan_cookie()
    if "--khong-mo" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
