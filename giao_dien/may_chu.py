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


def _pid_la_chay_py(pid, du_an):
    """Tiến trình `pid` còn sống VÀ đúng là chay.py của dự án này (tránh nhầm khi Windows tái dùng pid)."""
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
@app.get("/api/du_an")
def ds_du_an():
    ten = set()
    for d in (KB, ROOT):
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".txt") and (d == KB or f in ("kichbantest.txt", "kich_ban_thu_coc.txt")):
                    ten.add(f[:-4])
    du = os.path.join(ROOT, "cache", "du_an")
    if os.path.isdir(du):
        ten.update(os.listdir(du))
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


@app.post("/api/dung/hoan_thien")
def dung_hoan_thien():
    """Chạy skill hoàn thiện (chinh_sua/dung_hoan_chinh.py) ở nền cho dự án: bản đồ, thẻ ảnh highlight, hiệu ứng,
    chuyển cảnh -> bản nháp CapCut mới. Log ở ra/<dự án>/hoan_thien.log."""
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    ten = (d.get("ten") or f"{t}_hoan_chinh").strip()
    if not t:
        raise HTTPError(400, "thiếu dự án")
    p = procs_ht.get(t)
    if p and p.poll() is None:
        raise HTTPError(409, "đang hoàn thiện — chờ xong")
    log_f = open(_log_ht(t), "w", encoding="utf-8")
    # BC_DU_AN của máy chủ (dự án mặc định) thắng --du-an trong common.py -> phải đặt đúng dự án cho tiến trình con
    env = dict(os.environ, PYTHONIOENCODING="utf-8", BC_DU_AN=t)
    procs_ht[t] = subprocess.Popen([sys.executable, "-X", "utf8", "dung_hoan_chinh.py", "--du-an", t, "--ten", ten],
                                   cwd=os.path.join(ROOT, "chinh_sua"), stdout=log_f, stderr=subprocess.STDOUT, env=env,
                                   creationflags=0x08000000 if os.name == "nt" else 0)
    procs_ht[t].ten_nhap = ten
    return json_ok({"ok": True, "ten": ten})


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
    """Tự tìm + tải (ngân sách phút video) + khớp + ảnh bù + bản nháp — chạy nền."""
    import tu_dong_tim
    d = request.json or {}
    t = slug(d.get("du_an", ""))
    try:
        tu_dong_tim.chay_nen(t, float(d.get("ngan_sach") or tu_dong_tim.NGAN_SACH_PHUT),
                             (d.get("ten_nhap") or "").strip() or None)
    except ValueError as e:
        raise HTTPError(400, str(e))
    return json_ok({"ok": True})


@app.get("/api/dung/tu_dong_tt")
def dung_tu_dong_tt():
    import tu_dong_tim
    return json_ok(tu_dong_tim.TT.get(slug(tham_so_q("du_an")), {}))


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
    if "--khong-mo" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
