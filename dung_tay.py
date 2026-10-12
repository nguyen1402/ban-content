# -*- coding: utf-8 -*-
"""Trình DỰNG TAY: người dùng tự chọn video/ảnh cho từng cảnh trên giao diện, công cụ chỉ tìm, tải, cắt, ghép.

Dữ liệu một dự án (ra/<dự án>/):
  kho/kho.json            thư viện media đã tải: {id: {loai: video|anh, tieu_de, file, dai, nguon, trang_thai, pt}}
  kho/video/<id>.mp4      video tải về (720p, có tiếng)
  kho/anh/<id>.<đuôi>     ảnh tải về
  dung.json               kế hoạch dựng: {id cảnh: {doan: [{loai, kho_id, vao, bd, dai}], da_cat: bool, cat: [...]}}
                            bd/dai = vị trí trong CẢNH (giây, theo giọng đọc); vao = giây bắt đầu trong video gốc
  cat/<cảnh>_<k>.mp4      đoạn video đã cắt (chỉ hình, không tiếng) — ảnh dùng thẳng file trong kho
Một video trong kho dùng được cho nhiều cảnh; sửa kế hoạch cảnh nào thì cắt lại cảnh đó."""
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request

from common import CACHE_CHUNG, FFMPEG, YT_JS, YTDLP, doc_json, ghi_json, log, thu_muc_du_an

_KHOA = threading.Lock()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
CHIEU_CAO = 720


def _ra(du_an):
    return thu_muc_du_an(du_an)[1]


def _kho_path(du_an):
    return os.path.join(_ra(du_an), "kho", "kho.json")


def doc_kho(du_an):
    return doc_json(_kho_path(du_an), {}) or {}


def _ghi_kho(du_an, kho):
    os.makedirs(os.path.dirname(_kho_path(du_an)), exist_ok=True)
    ghi_json(_kho_path(du_an), kho)


def _cap_nhat_kho(du_an, kid, **kw):
    with _KHOA:
        kho = doc_kho(du_an)
        kho.setdefault(kid, {}).update(kw)
        _ghi_kho(du_an, kho)


def _sach_ten(s, n=60):
    return (re.sub(r'[\\/:*?"<>|\s]+', "_", s or "").strip("_") or "x")[:n]


# --------------------------------------------------------------------------- tìm
def tim_youtube(q, n=12):
    """Kết quả tìm YouTube (không tải): [{id, tieu_de, dai, kenh, luot_xem}] — dùng yt-dlp --flat-playlist."""
    cache = os.path.join(CACHE_CHUNG, "tim_tay.json")
    da = doc_json(cache, {}) or {}
    k = f"yt|{n}|{q.strip().lower()}"
    if k in da and time.time() - da[k].get("luc", 0) < 7 * 86400:
        return da[k]["ds"]
    for n2 in (10, 12, 15, 20):                              # đã tìm cùng từ khoá với nhiều kết quả hơn: cắt bớt
        k2 = f"yt|{n2}|{q.strip().lower()}"
        if n2 > n and k2 in da and time.time() - da[k2].get("luc", 0) < 7 * 86400:
            return da[k2]["ds"][:n]
    p = subprocess.run([YTDLP, *YT_JS, "--flat-playlist", "-J", "--no-warnings", f"ytsearch{n}:{q}"],
                       capture_output=True, timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        j = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
    except ValueError:
        j = {}
    ds = []
    for e in j.get("entries") or []:
        if not e or not e.get("id"):
            continue
        ds.append({"id": e["id"], "tieu_de": e.get("title") or "", "dai": e.get("duration") or 0,
                   "kenh": e.get("channel") or e.get("uploader") or "", "luot_xem": e.get("view_count") or 0})
    with _KHOA:
        da = doc_json(cache, {}) or {}
        da[k] = {"luc": time.time(), "ds": ds}
        ghi_json(cache, da)
    return ds


def tim_anh(q, n=40):
    """Kết quả tìm ảnh trên Google Images (cửa sổ Chrome hiện, anh_google) — không tải: [{url, thumb, tieu_de, kenh,
    trang, rong, cao}]. Google hỏi captcha thì người dùng tự giải trong cửa sổ đó. (11/10: user bỏ Bing.)"""
    import anh_google
    try:
        return anh_google.google_anh(q, n=n)
    except ValueError:
        raise
    except Exception as e:                                      # noqa: BLE001
        raise ValueError(f"Google Images lỗi: {str(e)[:150]}") from e


# --------------------------------------------------------------------------- tải
def tai_video(du_an, vid, tieu_de="", dai=0, url=None):
    """Tải video YouTube (hoặc link yt-dlp hỗ trợ) bản <=720p có tiếng vào kho dự án — chạy nền."""
    kid = "v_" + re.sub(r"[^\w-]", "", vid)[:40]
    kho = doc_kho(du_an)
    if kho.get(kid, {}).get("trang_thai") in ("dang", "xong"):
        return kid
    thu = os.path.join(_ra(du_an), "kho", "video")
    os.makedirs(thu, exist_ok=True)
    dich = os.path.join(thu, kid + ".mp4")
    _cap_nhat_kho(du_an, kid, loai="video", tieu_de=tieu_de, dai=dai, nguon=url or f"https://www.youtube.com/watch?v={vid}",
                  file=dich, trang_thai="dang", pt=0.0, luc=time.time())

    def chay():
        lenh = [YTDLP, *YT_JS, "--no-playlist", "--newline", "--no-warnings", "--no-part",
                # ưu tiên ĐỘ PHÂN GIẢI (<=720) rồi mới tới h264: lọc [ext=mp4] trước từng làm tụt xuống 360p
                "-f", "bv*+ba/b", "-S", f"res:{CHIEU_CAO},vcodec:h264,acodec:m4a",
                "--merge-output-format", "mp4", "--ffmpeg-location", os.path.dirname(FFMPEG) or ".",
                "--progress-template", "download:PT %(progress._percent_str)s",
                "-o", dich, url or f"https://www.youtube.com/watch?v={vid}"]
        p = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             creationflags=0x08000000 if os.name == "nt" else 0)
        cuoi, t_ghi = [], 0.0
        for raw in iter(p.stdout.readline, b""):
            s = raw.decode("utf-8", "ignore").strip()
            cuoi = (cuoi + [s])[-5:]
            m = re.match(r"PT\s+([\d.]+)%", s)
            if m and time.time() - t_ghi > 1.0:
                _cap_nhat_kho(du_an, kid, pt=float(m.group(1)))
                t_ghi = time.time()
        p.wait()
        if p.returncode == 0 and os.path.isfile(dich):
            _cap_nhat_kho(du_an, kid, trang_thai="xong", pt=100.0, dai=_do_dai(dich) or dai)
        else:
            _cap_nhat_kho(du_an, kid, trang_thai="loi", loi=" | ".join(x for x in cuoi if "ERROR" in x)[-300:])
    threading.Thread(target=chay, daemon=True).start()
    return kid


def tai_file(du_an, kid, url, tieu_de="", nguon=""):
    """Tải thẳng một file video (Pexels/Pixabay: mp4 không watermark) vào kho — chạy nền như tai_video.
    Kho ghi sach=True (nguồn sạch, không logo) để bước khớp ưu tiên."""
    kho = doc_kho(du_an)
    if kho.get(kid, {}).get("trang_thai") in ("dang", "xong"):
        return kid
    thu = os.path.join(_ra(du_an), "kho", "video")
    os.makedirs(thu, exist_ok=True)
    dich = os.path.join(thu, kid + ".mp4")
    _cap_nhat_kho(du_an, kid, loai="video", tieu_de=tieu_de, dai=0, nguon=url, nguon_kho=nguon, sach=True,
                  file=dich, trang_thai="dang", pt=0.0, luc=time.time())

    def chay():
        tam = dich + ".part"
        import urllib.error
        for lan in range(4):                                # Pixabay trả 429 khi tải dồn: chờ rồi thử lại
            try:
                urllib.request.urlopen(urllib.request.Request(url, headers=UA, method="HEAD"), timeout=30).close()
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or lan == 3:
                    break
                time.sleep(8 * (lan + 1))
            except Exception:                               # noqa: BLE001
                break
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r, open(tam, "wb") as f:
                tong = int(r.headers.get("Content-Length") or 0)
                da, t_ghi = 0, 0.0
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
                    da += len(b)
                    if tong and time.time() - t_ghi > 1.0:
                        _cap_nhat_kho(du_an, kid, pt=round(da * 100 / tong, 1))
                        t_ghi = time.time()
            os.replace(tam, dich)
            _cap_nhat_kho(du_an, kid, trang_thai="xong", pt=100.0, dai=_do_dai(dich))
        except Exception as e:                              # noqa: BLE001
            _cap_nhat_kho(du_an, kid, trang_thai="loi", loi=str(e)[:200])
    threading.Thread(target=chay, daemon=True).start()
    return kid


PHONG_LOGO = 1.25            # video có logo/watermark tĩnh ở góc: phóng to bấy nhiêu lần để đẩy logo ra khỏi khung


def danh_dau_logo(du_an):
    """Video YouTube trong kho: dò logo tĩnh ở 4 góc (sach_hinh.logo_video); có thì ghi phong=PHONG_LOGO (12/10 user
    chọn PHÓNG TO giấu logo thay vì bỏ cảnh). Nguồn sạch (Pexels/Pixabay) bỏ qua."""
    import sach_hinh
    n = 0
    for kid, m in doc_kho(du_an).items():
        if m.get("loai") != "video" or m.get("trang_thai") != "xong" or m.get("sach") or "logo" in m:
            continue
        try:
            goc = sach_hinh.logo_video(m["file"], "tay_" + kid)
        except Exception:                                   # noqa: BLE001
            goc = []
        _cap_nhat_kho(du_an, kid, logo=goc, phong=PHONG_LOGO if goc else 1.0)
        n += bool(goc)
    return n


def tai_anh(du_an, url, tieu_de=""):
    """Tải ảnh (ảnh gốc) vào kho dự án; trả id kho."""
    kid = "a_" + hashlib.md5(url.encode()).hexdigest()[:12]
    kho = doc_kho(du_an)
    if kho.get(kid, {}).get("trang_thai") == "xong" and os.path.isfile(kho[kid].get("file", "")):
        return kid
    thu = os.path.join(_ra(du_an), "kho", "anh")
    os.makedirs(thu, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        data = r.read(25 << 20)
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    duoi = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}.get(im.format, ".jpg")
    dich = os.path.join(thu, kid + duoi)
    if duoi in (".webp", ".gif"):                           # CapCut nhận jpg/png chắc nhất
        dich = os.path.join(thu, kid + ".jpg")
        im.convert("RGB").save(dich, quality=95)
    else:
        with open(dich, "wb") as f:
            f.write(data)
    _cap_nhat_kho(du_an, kid, loai="anh", tieu_de=tieu_de or urllib.parse.urlparse(url).netloc, file=dich,
                  nguon=url, trang_thai="xong", pt=100.0, rong=im.size[0], cao=im.size[1], luc=time.time())
    return kid


def them_tep(du_an, duong_dan, loai):
    """Thêm file video/ảnh có sẵn trên máy vào kho dự án (không chép, chỉ ghi đường dẫn)."""
    kid = ("v_" if loai == "video" else "a_") + hashlib.md5(os.path.abspath(duong_dan).encode()).hexdigest()[:12]
    _cap_nhat_kho(du_an, kid, loai=loai, tieu_de=os.path.basename(duong_dan), file=os.path.abspath(duong_dan),
                  nguon="máy", trang_thai="xong", pt=100.0, dai=_do_dai(duong_dan) if loai == "video" else 0,
                  luc=time.time())
    return kid


def _do_dai(path):
    p = subprocess.run([FFMPEG, "-i", path], capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    m = re.search(rb"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    return round(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), 2) if m else 0


# --------------------------------------------------------------------------- kế hoạch dựng
def _dung_path(du_an):
    return os.path.join(_ra(du_an), "dung.json")


def doc_dung(du_an):
    return doc_json(_dung_path(du_an), {}) or {}


def luu_canh(du_an, canh_id, doan):
    """Lưu kế hoạch một cảnh. Đổi kế hoạch -> cảnh về trạng thái CHƯA CẮT (đoạn cắt cũ bị bỏ khi cắt lại)."""
    sach = []
    for d in doan or []:
        if d.get("loai") not in ("video", "anh") or not d.get("kho_id"):
            continue
        sach.append({"loai": d["loai"], "kho_id": str(d["kho_id"]), "vao": round(max(0.0, float(d.get("vao") or 0)), 2),
                     "bd": round(max(0.0, float(d.get("bd") or 0)), 2), "dai": round(max(0.05, float(d.get("dai") or 0)), 2)})
    sach.sort(key=lambda x: x["bd"])
    with _KHOA:
        dung = doc_dung(du_an)
        cu = dung.get(str(canh_id), {})
        doi = [{k: x[k] for k in ("loai", "kho_id", "vao", "bd", "dai")} for x in cu.get("doan", [])] != sach
        dung[str(canh_id)] = {"doan": sach, "da_cat": cu.get("da_cat", False) and not doi,
                              "cat": cu.get("cat", []) if not doi else [], "luc": time.time()}
        ghi_json(_dung_path(du_an), dung)
    return dung[str(canh_id)]


def cat_canh(du_an, canh_id):
    """Cắt các đoạn video của cảnh từ file trong kho (khớp khung hình, bỏ tiếng); ảnh giữ nguyên file kho."""
    dung = doc_dung(du_an)
    kh = dung.get(str(canh_id))
    if not kh or not kh.get("doan"):
        raise ValueError("cảnh chưa có đoạn nào")
    kho = doc_kho(du_an)
    thu = os.path.join(_ra(du_an), "cat")
    os.makedirs(thu, exist_ok=True)
    for f in os.listdir(thu):                                  # bỏ đoạn cắt cũ của cảnh này
        if f.startswith(f"{int(canh_id):04d}_"):
            try:
                os.remove(os.path.join(thu, f))
            except OSError:
                pass
    cat = []
    for k, d in enumerate(kh["doan"]):
        m = kho.get(d["kho_id"]) or {}
        if m.get("trang_thai") != "xong" or not os.path.isfile(m.get("file", "")):
            raise ValueError(f"đoạn {k + 1}: media chưa tải xong")
        if d["loai"] == "anh":
            cat.append({"loai": "anh", "file": m["file"], "bd": d["bd"], "dai": d["dai"]})
            continue
        dich = os.path.join(thu, f"{int(canh_id):04d}_{k}.mp4")
        lenh = [FFMPEG, "-y", "-v", "error", "-ss", f"{d['vao']:.3f}", "-i", m["file"], "-t", f"{d['dai']:.3f}",
                "-an", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", dich]
        p = subprocess.run(lenh, capture_output=True, timeout=600, creationflags=0x08000000 if os.name == "nt" else 0)
        if p.returncode != 0 or not os.path.isfile(dich):
            raise ValueError(f"đoạn {k + 1}: cắt lỗi {p.stderr.decode('utf-8', 'ignore')[-200:]}")
        cat.append({"loai": "video", "file": dich, "bd": d["bd"], "dai": d["dai"]})
    with _KHOA:
        dung = doc_dung(du_an)
        dung[str(canh_id)].update(da_cat=True, cat=cat, luc_cat=time.time())
        ghi_json(_dung_path(du_an), dung)
    return cat


def _sua_nhap(thu, files):
    """Sửa bản nháp sau khi pycapcut ghi:
      * TẮT 'hút vào đoạn chính' (config.maintrack_adsorb) — bật thì CapCut dồn các đoạn sát nhau, mất khoảng trống
        giữa cảnh và lệch khỏi giọng đọc;
      * đưa từng VIDEO/ẢNH GỐC vào khung 'Phương tiện' của dự án (draft_meta_info.draft_materials) để người dùng
        kéo đoạn khác của video gốc vào timeline."""
    import uuid
    p = os.path.join(thu, "draft_content.json")
    c = doc_json(p, {}) or {}
    c.setdefault("config", {})["maintrack_adsorb"] = False
    ghi_json(p, c)
    vids = {}
    for v in (c.get("materials") or {}).get("videos", []):
        vids.setdefault(os.path.normcase(os.path.abspath(v.get("path", ""))), v)
    pm = os.path.join(thu, "draft_meta_info.json")
    m = doc_json(pm, {}) or {}
    nhom = next((g for g in m.get("draft_materials", []) if g.get("type") == 0), None)
    if nhom is None:
        nhom = {"type": 0, "value": []}
        m.setdefault("draft_materials", []).insert(0, nhom)
    co = {os.path.normcase(os.path.abspath(x.get("file_Path", ""))) for x in nhom["value"] if x.get("file_Path")}
    bay_gio = int(time.time())
    for f in files:
        k = os.path.normcase(os.path.abspath(f))
        if k in co:
            continue
        v = vids.get(k, {})
        anh = v.get("type") == "photo" or os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")
        dai = int(v.get("duration") or 0) if not anh else 5_000_000
        nhom["value"].append({"ai_group_type": "", "create_time": bay_gio, "duration": dai, "enter_from": 0,
                              "extra_info": os.path.basename(f), "file_Path": os.path.abspath(f).replace("\\", "/"),
                              "height": int(v.get("height") or 0), "id": uuid.uuid4().hex, "import_time": bay_gio,
                              "import_time_ms": bay_gio * 1_000_000, "item_source": 1, "material_color_tag": "", "md5": "",
                              "metetype": "photo" if anh else "video", "roughcut_time_range": {"duration": dai, "start": 0},
                              "sub_time_range": {"duration": -1, "start": -1}, "type": 0, "width": int(v.get("width") or 0)})
        co.add(k)
    ghi_json(pm, m)


def tao_nhap(du_an, ten, drafts_dir, dung=None):
    """Bản nháp CapCut: track giọng (giong_doc.wav nguyên bài) + đoạn hình của mọi cảnh ĐÃ CÓ kế hoạch (người dùng
    dựng hoặc gợi ý). Đoạn video trỏ vào VIDEO GỐC đầy đủ trong kho, chỉ đặt điểm vào/ra (source_timerange) —
    trong CapCut kéo mép đoạn hoặc trượt sang chỗ khác của chính video đó được. Tiếng gốc tắt (âm lượng 0)."""
    import pycapcut as draft
    from pycapcut import trange
    out = _ra(du_an)
    canh = {int(x["id"]): x for x in (doc_json(os.path.join(out, "tu_khoa.json"), []) or [])}
    dung = doc_dung(du_an) if dung is None else dung       # dung: kế hoạch truyền vào (so sánh), mặc định dung.json
    kho = doc_kho(du_an)
    wav = os.path.join(out, "giong_doc.wav")
    folder = draft.DraftFolder(drafts_dir)
    script = folder.create_draft(ten, 1920, 1080, allow_replace=True)
    script.add_track(draft.TrackType.video, track_name="hinh")
    script.add_track(draft.TrackType.audio, track_name="giong")
    vat_lieu = {}                                            # mỗi file gốc là MỘT vật liệu dùng chung cho mọi đoạn
    n = 0
    het = -1
    for cid in sorted(int(k) for k in dung):
        kh = dung[str(cid)]
        if not kh.get("doan") or cid not in canh:
            continue
        goc = canh[cid]["bat_dau"]
        for d in sorted(kh["doan"], key=lambda x: x["bd"]):
            m = kho.get(d["kho_id"]) or {}
            f = m.get("file", "")
            if m.get("trang_thai") != "xong" or not os.path.isfile(f):
                continue
            t0 = max(int(round((goc + d["bd"]) * 1_000_000)), het)
            if 0 <= het < t0 and t0 - het < 1_500_000:      # khoảng hở nhỏ (đoạn trước chạm cuối file) -> đoạn này lấp vào
                t0 = het
            dl = int(round((goc + d["bd"] + d["dai"]) * 1_000_000)) - t0
            if f not in vat_lieu:
                vat_lieu[f] = draft.VideoMaterial(f)
            mat = vat_lieu[f]
            if d["loai"] == "video":
                vao = int(round(d["vao"] * 1_000_000))
                dl = min(dl, int(mat.duration) - vao - 1000)
                if dl <= 0:
                    continue
                ph = float(m.get("phong") or 1.0)               # logo ở góc -> phóng to giấu logo
                seg = draft.VideoSegment(mat, trange(t0, dl), source_timerange=trange(vao, dl), volume=0.0,
                                         clip_settings=draft.ClipSettings(scale_x=ph, scale_y=ph) if ph > 1.0 else None)
            else:
                if dl <= 0:
                    continue
                seg = draft.VideoSegment(mat, trange(t0, dl))
            script.add_segment(seg, track_name="hinh")
            het = t0 + dl
            n += 1
    if os.path.isfile(wav):
        dai = _do_dai(wav)
        script.add_segment(draft.AudioSegment(draft.AudioMaterial(wav), trange(0, int(dai * 1_000_000) - 1000)),
                           track_name="giong")
    script.save()
    _sua_nhap(os.path.join(drafts_dir, ten), list(vat_lieu))
    log(f"bản nháp dựng tay '{ten}': {n} đoạn hình (trỏ video gốc)")
    return n
