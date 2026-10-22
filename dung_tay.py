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
def tim_youtube(q, n=12, lam_moi=False, chi_cc=False):
    """Kết quả tìm YouTube (không tải): [{id, tieu_de, dai, kenh, luot_xem, xac_minh}] — dùng yt-dlp --flat-playlist.
    chi_cc (22/10 user "an toàn nhất"): chỉ video giấy phép CREATIVE COMMONS (bộ lọc của trang kết quả YouTube)."""
    cache = os.path.join(CACHE_CHUNG, "tim_tay.json")
    da = doc_json(cache, {}) or {}
    dau = "ytcc" if chi_cc else "yt"
    k = f"{dau}|{n}|{q.strip().lower()}"
    if not lam_moi:
        if k in da and time.time() - da[k].get("luc", 0) < 7 * 86400:
            return da[k]["ds"]
        for n2 in (10, 12, 15, 20, 25, 30):                          # đã tìm cùng từ khoá với nhiều kết quả hơn: cắt bớt
            k2 = f"{dau}|{n2}|{q.strip().lower()}"
            if n2 > n and k2 in da and time.time() - da[k2].get("luc", 0) < 7 * 86400:
                return da[k2]["ds"][:n]
    nguon = (["--playlist-end", str(n), "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
              + "&sp=EgIwAQ%3D%3D"] if chi_cc else [f"ytsearch{n}:{q}"])
    p = subprocess.run([YTDLP, *YT_JS, "--flat-playlist", "-J", "--no-warnings", *nguon],
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
                   "kenh": e.get("channel") or e.get("uploader") or "", "luot_xem": e.get("view_count") or 0,
                   "xac_minh": bool(e.get("channel_is_verified"))})
    with _KHOA:
        da = doc_json(cache, {}) or {}
        da[k] = {"luc": time.time(), "ds": ds}
        ghi_json(cache, da)
    return ds


# 22/10 user ("làm an toàn nhất" về bản quyền): nguồn YouTube chỉ nhận Creative Commons (kiểm lại từng video) hoặc kênh
# CƠ QUAN CHÍNH PHỦ MỸ (tác phẩm của chính phủ liên bang thường là public domain); CHẶN hẳn đài tin tức / truyền hình,
# kho stock bán bản quyền (bản xem trước có watermark), hãng phim — kể cả khi gắn nhãn CC (thường là đăng lại trái phép).
KENH_CONG = re.compile(r"\b(NOAA|NASA|U\.?S\.? ?Navy\w*|US Navy|U\.?S\.? ?Army|Army Corps of Engineers|USACE|DVIDS\w*|USGS|"
                       r"National Park Service|NPS|U\.?S\.? Fish (and|&) Wildlife|USFWS|U\.?S\.? ?EPA|"
                       r"National Archives|Library of Congress|U\.?S\.? Coast Guard|USCG|U\.?S\.? ?Air Force|"
                       r"U\.?S\.? Marine Corps|USMC|Department of (Defense|Energy|the Interior|Agriculture)|"
                       r"National Ocean Service|NOAA Fisheries|Smithsonian Environmental)\b", re.I)
CHAN_NGUON = re.compile(r"\b(CNN|BBC|NBC|ABC|CBS|Fox|PIX ?11|WPIX|Sky News|Al Jazeera|Reuters|AP Archive|Associated Press|"
                        r"Bloomberg|CNBC|MSNBC|Yahoo Finance|Euronews|DW News|France 24|Channel 4|ITV|NHK|CGTN|"
                        r"Insider|Business Insider|Vox|Vice|NowThis|Washington Post|New York Times|NYT|Guardian|"
                        r"National Geographic|Nat Geo|Discovery|Smithsonian Channel|History Channel|PBS|Netflix|"
                        r"Disney|HBO|Warner|Universal|Paramount|Sony Pictures|Pathe|Pathé|CriticalPast|Getty|"
                        r"Shutterstock|Pond5|Storyblocks|Videoblocks|Alamy|Adobe Stock|iStock|Dissolve|Framepool|"
                        r"Artgrid|Envato|Motion Array|MyFootage|Film Supply|Filmsupply|Footage Farm|Huntley Film|"
                        r"British Movietone|Movietone|Archive Films)\b", re.I)


def la_kenh_cong(kenh):
    return bool(KENH_CONG.search(str(kenh or "")))


def bi_chan(v):
    """Kênh / tiêu đề thuộc nguồn rủi ro cao (tin tức, truyền hình, stock bán bản quyền, hãng phim)."""
    return bool(CHAN_NGUON.search(f"{v.get('kenh') or ''} | {v.get('tieu_de') or ''}"))


def giay_phep_youtube(vid):
    """Giấy phép THẬT của một video YouTube ('Creative Commons Attribution license (reuse allowed)' / '' = chuẩn YouTube)
    + tên kênh — đọc metadata đầy đủ, cache vĩnh viễn ở cache/giay_phep_yt.json. Lỗi đọc -> None."""
    cache = os.path.join(CACHE_CHUNG, "giay_phep_yt.json")
    da = doc_json(cache, {}) or {}
    if vid in da:
        return da[vid]
    p = subprocess.run([YTDLP, *YT_JS, "-J", "--skip-download", "--no-warnings", "--no-playlist",
                        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, timeout=120,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        d = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
    except ValueError:
        return None
    if not d.get("id"):
        return None
    kq = {"license": d.get("license") or "", "kenh": d.get("channel") or d.get("uploader") or "",
          "tieu_de": d.get("title") or ""}
    with _KHOA:
        da = doc_json(cache, {}) or {}
        da[vid] = kq
        ghi_json(cache, da)
    return kq


def nguon_an_toan(vid, kenh=""):
    """(được dùng?, giấy phép ghi nguồn) — Creative Commons thật hoặc kênh cơ quan chính phủ Mỹ, không thuộc nguồn chặn."""
    gp = giay_phep_youtube(vid)
    if not gp:
        return False, ""
    if bi_chan({"kenh": gp["kenh"], "tieu_de": gp["tieu_de"]}):
        return False, ""
    if "creative commons" in gp["license"].lower():
        return True, "CC BY (YouTube Creative Commons)"
    if la_kenh_cong(gp["kenh"] or kenh):
        return True, "tư liệu cơ quan chính phủ Mỹ (public domain)"
    return False, ""


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
def tai_video(du_an, vid, tieu_de="", dai=0, url=None, tay=False):
    """Tải video YouTube (hoặc link yt-dlp hỗ trợ) bản <=720p có tiếng vào kho dự án — chạy nền."""
    kid = "v_" + re.sub(r"[^\w-]", "", vid)[:40]
    kho = doc_kho(du_an)
    if kho.get(kid, {}).get("trang_thai") in ("dang", "xong"):
        return kid
    thu = os.path.join(_ra(du_an), "kho", "video")
    os.makedirs(thu, exist_ok=True)
    dich = os.path.join(thu, kid + ".mp4")
    _cap_nhat_kho(du_an, kid, loai="video", tieu_de=tieu_de, dai=dai, nguon=url or f"https://www.youtube.com/watch?v={vid}",
                  file=dich, trang_thai="dang", pt=0.0, luc=time.time(), tay=tay)   # tay: người dùng tự bấm tải

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


def tai_file(du_an, kid, url, tieu_de="", nguon="", ghi_nguon=""):
    """Tải thẳng một file video (Pexels/Pixabay: mp4 không watermark) vào kho — chạy nền như tai_video.
    Kho ghi sach=True (nguồn sạch, không logo) để bước khớp ưu tiên."""
    kho = doc_kho(du_an)
    if kho.get(kid, {}).get("trang_thai") in ("dang", "xong"):
        return kid
    thu = os.path.join(_ra(du_an), "kho", "video")
    os.makedirs(thu, exist_ok=True)
    dich = os.path.join(thu, kid + ".mp4")
    _cap_nhat_kho(du_an, kid, loai="video", tieu_de=tieu_de, dai=0, nguon=url, nguon_kho=nguon, sach=True,
                  ghi_nguon=ghi_nguon, file=dich, trang_thai="dang", pt=0.0, luc=time.time())

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
            if url.split("?")[0].lower().endswith((".webm", ".ogv", ".ogg")):   # Wikimedia: đổi sang mp4 cho CapCut
                p = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", tam, "-an", "-c:v", "libx264", "-crf", "20",
                                    "-preset", "veryfast", "-pix_fmt", "yuv420p", dich], capture_output=True, timeout=1800,
                                   creationflags=0x08000000 if os.name == "nt" else 0)
                os.remove(tam)
                if p.returncode != 0:
                    raise RuntimeError("đổi sang mp4 lỗi: " + p.stderr.decode("utf-8", "ignore")[-150:])
            else:
                os.replace(tam, dich)
            w, h = _kich_thuoc(dich)
            if w and h and w <= h:                          # 13/10 user: chỉ lấy video NGANG (dọc / vuông -> bỏ)
                os.remove(dich)
                _cap_nhat_kho(du_an, kid, trang_thai="loi", loi=f"video dọc {w}x{h} — bỏ (chỉ lấy video ngang)")
                return
            _cap_nhat_kho(du_an, kid, trang_thai="xong", pt=100.0, dai=_do_dai(dich), rong=w, cao=h)
        except Exception as e:                              # noqa: BLE001
            _cap_nhat_kho(du_an, kid, trang_thai="loi", loi=str(e)[:200])
    threading.Thread(target=chay, daemon=True).start()
    return kid


def _kich_thuoc(f):
    """(rộng, cao) HIỂN THỊ của video — tính cả cờ xoay (video quay điện thoại lưu ngang + rotate 90 là video dọc)."""
    import json as _json
    ffprobe = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe") if FFMPEG else "ffprobe"
    try:
        p = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:stream_tags=rotate:stream_side_data=rotation", "-of", "json", f],
                           capture_output=True, timeout=60, creationflags=0x08000000 if os.name == "nt" else 0)
        st = (_json.loads(p.stdout.decode("utf-8", "ignore") or "{}").get("streams") or [{}])[0]
    except Exception:                                       # noqa: BLE001
        return 0, 0
    w, h = int(st.get("width") or 0), int(st.get("height") or 0)
    xoay = st.get("tags", {}).get("rotate") or next((d.get("rotation") for d in st.get("side_data_list") or []
                                                      if "rotation" in d), 0)
    try:
        if abs(int(float(xoay))) % 180 == 90:
            w, h = h, w
    except (TypeError, ValueError):
        pass
    return w, h


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


NGUONG_KHUNG_SB = 0.12      # 18/10: khung storyboard khớp mô tả cảnh từ mức này (đo cho_digo: ~p90-p97 điểm khung)
NGUONG_KHUNG_THAT = 0.10    # khung THẬT (2 khung/giây) khớp từ mức này khi cắt sát
KHOANG_TOI_DA = 25.0        # một khoảng tải tối đa bấy nhiêu giây
LOC_CHU_KHI_CAT = False     # 18/10 user: KHÔNG lọc phụ đề / chữ khi cắt mảnh (tự zoom bỏ chữ, logo); đo: 3 s/clip
MANH_GIAY = 7.0             # 19/10: đoạn băm gộp < 2 s nên dài tới ~6,6 s -> mảnh 7 s (đủ phủ trọn một đoạn, dùng 2 lần)


def khoang_khop(t, s, tong, toi_da=3):
    """18/10 user ("chỉ lấy mỗi chỗ khớp mô tả cảnh"): [(bd, kt, điểm đỉnh)] — các DÃY khung storyboard liền nhau có
    điểm >= NGUONG_KHUNG_SB (cho hở 1 khung), nới nửa khoảng cách khung + 1 s mỗi bên; dãy dài thì lấy cửa sổ
    KHOANG_TOI_DA quanh đỉnh. s: điểm mỗi khung (đã lấy max theo các cảnh). Storyboard ~120 khung/video bất kể độ dài
    (đo: video 2 phút cách 1 s, 10 phút 5 s, 40 phút 20 s) -> video dài định vị thô, cắt sát lại ở cat_sat_khop."""
    import numpy as np
    t, s = np.asarray(t, float), np.asarray(s, float)
    if not len(t):
        return []
    buoc = float(np.median(np.diff(t))) if len(t) > 1 else 2.0
    tot = np.nonzero(s >= NGUONG_KHUNG_SB)[0]
    ra, i = [], 0
    while i < len(tot):
        j = i
        while j + 1 < len(tot) and tot[j + 1] - tot[j] <= 2:
            j += 1
        a, b = int(tot[i]), int(tot[j])
        dinh = a + int(np.argmax(s[a:b + 1]))
        bd, kt = max(0.0, t[a] - buoc / 2 - 1), min(float(tong), t[b] + buoc / 2 + 1)
        if kt - bd > KHOANG_TOI_DA:
            bd = max(0.0, t[dinh] - KHOANG_TOI_DA / 2)
            kt = min(float(tong), bd + KHOANG_TOI_DA)
        ra.append((round(float(bd), 1), round(float(kt), 1), float(s[dinh])))
        i = j + 1
    return sorted(ra, key=lambda x: -x[2])[:toi_da]


def cat_sat_khop(du_an, kid, Q):
    """18/10: clip vừa tải (khoảng định vị thô từ storyboard, có nới) -> chấm KHUNG THẬT 2 khung/giây với mô tả các
    cảnh của chủ đề (Q: ma trận vector cảnh), cắt MỌI dãy khớp thành các mảnh ~MANH_GIAY (mỗi mảnh 1 mục kho riêng
    "<kid>_m<i>"; khoảng thô -> trang_thai "tach", xoá file). Không khớp / toàn phụ đề -> "loi". Trả (giây giữ, số mảnh)."""
    import numpy as np
    from PIL import Image
    import nhung_siglip
    m = doc_kho(du_an).get(kid) or {}
    f = m.get("file", "")
    if m.get("trang_thai") != "xong" or m.get("cat_sat") or not os.path.isfile(f):
        return 0.0, 0
    W, H = 256, 144
    buf = subprocess.run([FFMPEG, "-v", "error", "-i", f, "-vf", f"fps=2,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, timeout=180, creationflags=0x08000000 if os.name == "nt" else 0).stdout
    n = len(buf) // (W * H * 3)
    if n < 2:
        return 0.0, 0
    khung = [np.frombuffer(buf, np.uint8, W * H * 3, k * W * H * 3).reshape(H, W, 3) for k in range(n)]
    E_khung = nhung_siglip.nhung_anh([Image.fromarray(x) for x in khung])
    best = (E_khung @ np.asarray(Q).T).max(1)
    try:                                                     # 18/10 user: lẫn hoạt hình / game -> khung đó coi như không khớp
        import loc_minh_hoa
        xau_k = (loc_minh_hoa.diem_hoat_hinh(E_khung) > loc_minh_hoa.NGUONG_HOAT_HINH)
        _ = loc_minh_hoa.la_game(E_khung[:1])                # nạp vector mẫu game
        xau_k = xau_k | ((((E_khung @ loc_minh_hoa._V["game"].T).max(1)   # noqa: SLF001
                           - (E_khung @ loc_minh_hoa._V["t"].T).max(1)) > loc_minh_hoa.LE_GAME))   # noqa: SLF001
        best = np.where(xau_k, -1.0, best)
    except Exception:                                        # noqa: BLE001
        pass
    try:                                                     # 19/10 user: khúc ẢNH TĨNH phóng / lia chậm -> không cắt mảnh
        import loc_minh_hoa
        for a_, b_ in loc_minh_hoa.keo_tinh("goc_" + kid, f):
            best[max(0, int(a_ * 2)):min(n, int(np.ceil(b_ * 2)) + 1)] = -1.0
    except Exception:                                        # noqa: BLE001
        pass
    runs, k = [], 0
    while k < n:
        if best[k] >= NGUONG_KHUNG_THAT:
            j = k
            while j + 1 < n and best[j + 1] >= NGUONG_KHUNG_THAT:
                j += 1
            runs.append((k, j))
            k = j + 1
        else:
            k += 1
    if not runs:
        _cap_nhat_kho(du_an, kid, trang_thai="loi", loi="không có khung khớp mô tả cảnh", cat_sat=True)
        return 0.0, 0
    # 18/10 user: hình băm theo NHỊP NGHỈ của giọng (đoạn 0,8-5,5 s, trung vị ~2 s) và mỗi clip dùng tối đa 2 lần
    # -> cắt MỌI dãy khớp thành các mảnh ~MANH_GIAY (mỗi mảnh = 1 clip riêng, đủ dài cho nhịp dài nhất, dùng được 2 lần);
    # dãy ngắn hơn thì nới hai bên cho đủ (không chồng mảnh trước). Mảnh > 25% khung có chữ (phụ đề) -> bỏ.
    try:
        import loc_chu
    except Exception:                                        # noqa: BLE001
        loc_chu = None
    if not LOC_CHU_KHI_CAT:
        loc_chu = None
    tong_giay = n / 2
    bd_goc = float(m.get("giay_bat_dau") or 0) - 1.5         # _cat_khoang_local đã nới 1,5 s đầu
    manh, toi = [], 0.0
    for a, b in runs:
        t0, t1 = max(a / 2, toi), (b + 1) / 2
        if t1 - t0 < 1.5:
            continue
        if t1 - t0 < MANH_GIAY:                              # nới cho đủ một mảnh
            thieu = MANH_GIAY - (t1 - t0)
            t0, t1 = max(toi, t0 - thieu / 2), min(tong_giay, t1 + thieu / 2)
            if t1 - t0 < MANH_GIAY:
                t0 = max(toi, t1 - MANH_GIAY)
        so = max(1, int(round((t1 - t0) / MANH_GIAY)))
        d = (t1 - t0) / so
        manh += [(t0 + q * d, t0 + (q + 1) * d) for q in range(so)]
        toi = t1
    giu, so_giu, so_chu = 0.0, 0, 0
    base = f[:-4]
    for q, (t0, t1) in enumerate(manh):
        k0, k1 = int(t0 * 2), max(int(t0 * 2) + 1, int(t1 * 2))
        if loc_chu is not None:
            try:
                co = [loc_chu.dien_tich_chu(np.ascontiguousarray(x)) > loc_chu.NGUONG_DIEN_TICH for x in khung[k0:k1]]
                if co and sum(co) / len(co) > 0.25:
                    so_chu += 1
                    continue
            except Exception:                                # noqa: BLE001
                pass
        dich = f"{base}_m{q}.mp4"
        p = subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t0:.2f}", "-i", f, "-t", f"{t1 - t0:.2f}", "-an",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", dich],
                           capture_output=True, timeout=180, creationflags=0x08000000 if os.name == "nt" else 0)
        if p.returncode != 0 or not os.path.isfile(dich) or os.path.getsize(dich) < 5000:
            continue
        w, h = _kich_thuoc(dich)
        _cap_nhat_kho(du_an, f"{kid}_m{q}", **{**m, "file": dich, "dai": _do_dai(dich) or round(t1 - t0, 2), "rong": w, "cao": h,
                                               "cat_sat": True, "manh_cua": kid,
                                               "diem_khop": round(float(best[k0:k1].max()), 3),
                                               "giay_bat_dau": round(max(0.0, bd_goc + t0), 2),
                                               "giay_ket_thuc": round(max(0.0, bd_goc + t1), 2), "luc": time.time()})
        giu += t1 - t0
        so_giu += 1
    try:                                                     # khoảng thô đã tách thành mảnh -> bỏ file thô
        os.remove(f)
    except OSError:
        pass
    _cap_nhat_kho(du_an, kid, trang_thai="tach" if so_giu else "loi", cat_sat=True, so_manh=so_giu,
                  loi="" if so_giu else ("đoạn khớp có phụ đề / chữ" if so_chu else "không cắt được mảnh"))
    return giu, so_giu


BAM_CA_VIDEO = True         # 22/10 user: tải về thì BĂM CẢ VIDEO theo cảnh quay (không chỉ vài khoảng khớp ảnh xem trước)
BAM_SHOT_MIN = 1.5          # cảnh quay ngắn hơn bỏ (chớp nhoáng / chuyển cảnh)
BAM_TOI_DA = 12             # tối đa bấy nhiêu mảnh / video (điểm cao trước) — 22/10 user: băm từ NHIỀU video khác nhau
BAM_DU = 1.0                # 22/10 user ("cắt hụt"): file mảnh cắt DƯ bấy nhiêu giây mỗi đầu; khớp chỉ trong phần LÕI
#                             (loi_bd / loi_kt = giây lõi tính trong file mảnh)
BAM_LE = 0.15               # cắt lùi vào trong mỗi đầu cảnh (tránh dính khung cảnh bên cạnh)


def bam_theo_canh(du_an, vid, file_goc, Q, chu_de=None, meta=None):
    """22/10 user ("băm video gần chủ thể lấp vào"): băm CẢ video gốc vừa tải thành MẢNH = MỘT CẢNH QUAY (điểm đổi cảnh
    sach_hinh.canh_cat); cảnh dài quá 1,5 x MANH_GIAY chia đều ~MANH_GIAY. Mỗi mảnh chấm SigLIP (nửa khung tốt nhất) với
    các mô tả chủ thể Q, đạt NGUONG_KHUNG_THAT mới giữ; khung hoạt hình / game / ẢNH TĨNH kéo chậm > 30% mảnh -> bỏ.
    Mảnh = mục kho "v_<vid>_c<i>" (manh_cua = video gốc). Trả (giây giữ, số mảnh)."""
    import numpy as np
    from PIL import Image
    import nhung_siglip
    import sach_hinh
    meta = meta or {}
    vid_safe = re.sub(r"[^\w-]", "", vid)[:30]
    tong = _do_dai(file_goc) or 0.0
    if tong < 2:
        return 0.0, 0
    fps = 2 if tong <= 300 else 1                            # video dài: 1 khung/giây cho nhẹ (cảnh >= 1,5 s vẫn có khung)
    W, H = 256, 144
    buf = subprocess.run([FFMPEG, "-v", "error", "-i", file_goc, "-an", "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=1800,
                         creationflags=0x08000000 if os.name == "nt" else 0).stdout
    n = len(buf) // (W * H * 3)
    if n < 2:
        return 0.0, 0
    E = nhung_siglip.nhung_anh([Image.fromarray(np.frombuffer(buf, np.uint8, W * H * 3, k * W * H * 3).reshape(H, W, 3))
                               for k in range(n)])
    del buf
    diem = (E @ np.asarray(Q).T).max(1)
    xau = np.zeros(n, bool)
    try:                                                     # hoạt hình / game: như cat_sat_khop
        import loc_minh_hoa
        xau |= loc_minh_hoa.diem_hoat_hinh(E) > loc_minh_hoa.NGUONG_HOAT_HINH
        _ = loc_minh_hoa.la_game(E[:1])
        xau |= ((E @ loc_minh_hoa._V["game"].T).max(1) - (E @ loc_minh_hoa._V["t"].T).max(1)) > loc_minh_hoa.LE_GAME   # noqa: SLF001
        for a_, b_ in loc_minh_hoa.keo_tinh("goc_" + vid_safe, file_goc):   # ảnh tĩnh phóng / lia chậm
            xau[max(0, int(a_ * fps)):min(n, int(np.ceil(b_ * fps)) + 1)] = True
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! băm {vid_safe}: lọc hoạt hình / ảnh tĩnh lỗi ({str(e)[:80]})")
    moc = [0.0] + [b for b in sach_hinh.canh_cat(file_goc, "goc_" + vid_safe) if 0 < b < tong] + [tong]
    ung = []
    for a, b in zip(moc, moc[1:]):
        a, b = a + BAM_LE, b - BAM_LE
        if b - a < BAM_SHOT_MIN:
            continue
        so = max(1, int(round((b - a) / MANH_GIAY))) if b - a > 1.5 * MANH_GIAY else 1
        d = (b - a) / so
        for q in range(so):
            t0, t1 = a + q * d, a + (q + 1) * d
            k0, k1 = int(t0 * fps), max(int(t0 * fps) + 1, int(t1 * fps))
            s = diem[k0:k1]
            if not len(s) or xau[k0:k1].mean() > 0.3:
                continue
            sc = float(np.sort(s)[-max(1, len(s) // 2):].mean())
            if sc >= NGUONG_KHUNG_THAT:
                ung.append((sc, t0, t1))
    ung = sorted(sorted(ung, key=lambda x: -x[0])[:BAM_TOI_DA], key=lambda x: x[1])
    thu = os.path.dirname(file_goc)
    giu, so_giu = 0.0, 0
    for i, (sc, t0, t1) in enumerate(ung):
        kid = f"v_{vid_safe}_c{i}"
        dich = os.path.join(thu, kid + ".mp4")
        a0, b0 = max(0.0, t0 - BAM_DU), min(tong, t1 + BAM_DU)   # cắt DƯ hai đầu
        if not (os.path.isfile(dich) and os.path.getsize(dich) > 5000):
            p = subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{a0:.2f}", "-i", file_goc, "-t", f"{b0 - a0:.2f}", "-an",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", dich],
                               capture_output=True, timeout=180, creationflags=0x08000000 if os.name == "nt" else 0)
            if p.returncode != 0 or not os.path.isfile(dich) or os.path.getsize(dich) < 5000:
                continue
        w, h = _kich_thuoc(dich)
        _cap_nhat_kho(du_an, kid, loai="video", video_goc=vid, manh_cua=f"v_{vid_safe}", chu_de=chu_de,
                      kenh=meta.get("kenh", ""), tieu_de=f"{meta.get('tieu_de', '')} [cảnh {int(t0)}s-{int(t1)}s]",
                      file=dich, dai=_do_dai(dich) or round(b0 - a0, 2), rong=w, cao=h, trang_thai="xong", pt=100.0,
                      ghi_nguon=meta.get("ghi_nguon", ""), giay_phep=meta.get("giay_phep", ""),
                      nguon_kho=meta.get("nguon_kho", "youtube"),
                      cat_sat=True, bam_canh=True, diem_khop=round(sc, 3), giay_bat_dau=round(a0, 2),
                      giay_ket_thuc=round(b0, 2), loi_bd=round(t0 - a0, 2), loi_kt=round(t1 - a0, 2),
                      luc=time.time(), tay=True)
        giu += t1 - t0
        so_giu += 1
    log(f"    băm {vid_safe}: {len(moc) - 1} cảnh quay / {tong:.0f}s -> giữ {so_giu} mảnh ({giu:.0f}s)")
    return giu, so_giu


def chon_khoang_video(t, e, qv, tong, min_dai=20.0, max_dai=40.0, toi_da_khoang=4):
    """Giai đoạn 3: Chọn 1–4 khoảng tốt nhất (20–40s) dựa vào điểm chấm ảnh xem trước (storyboard) so với mô tả chủ đề qv.
    Các khoảng không chồng nhau. Hai khoảng cách nhau dưới 10 giây thì gộp làm một."""
    if len(t) < 1 or tong <= 0:
        return []
    import numpy as np
    t = np.asarray(t, dtype=float)
    e = np.asarray(e, dtype=float)
    qv = np.asarray(qv, dtype=float)
    s = np.atleast_1d(e @ qv)
    if tong <= max_dai:
        return [(0.0, round(float(tong), 2), float(s.mean() if len(s) else 0.0))]

    muc_tieu = min(30.0, max(min_dai, float(tong)))
    cands = []
    for i in range(len(t)):
        t_start = float(t[i])
        t_end = min(float(tong), t_start + muc_tieu)
        if t_end - t_start < min_dai and t_end < float(tong):
            continue
        mask = (t >= t_start) & (t <= t_end)
        if not mask.any():
            continue
        score = float(s[mask].mean())
        cands.append((score, t_start, t_end))

    cands.sort(key=lambda x: -x[0])
    chon = []
    for sc, bd, kt in cands:
        chong = False
        for c_sc, c_bd, c_kt in chon:
            if not (kt <= c_bd or bd >= c_kt):
                chong = True
                break
        if not chong:
            chon.append((sc, bd, kt))
            if len(chon) >= toi_da_khoang * 2:
                break

    chon_theo_tg = sorted([(bd, kt, sc) for sc, bd, kt in chon], key=lambda x: x[0])
    gop = []
    for bd, kt, sc in chon_theo_tg:
        if not gop:
            gop.append([bd, kt, sc, 1])
        else:
            prev = gop[-1]
            if bd - prev[1] < 10.0:  # cách nhau dưới 10 giây -> gộp làm một
                prev[1] = max(prev[1], kt)
                prev[2] = (prev[2] * prev[3] + sc) / (prev[3] + 1)
                prev[3] += 1
            else:
                gop.append([bd, kt, sc, 1])

    ket_qua = []
    for bd, kt, sc, _ in gop:
        d = kt - bd
        if d < min_dai:
            thieu = min_dai - d
            bd = max(0.0, bd - thieu / 2)
            kt = min(float(tong), kt + thieu / 2)
        elif d > max_dai:
            kt = min(float(tong), bd + max_dai)
        ket_qua.append((round(bd, 2), round(kt, 2), round(sc, 3)))

    ket_qua.sort(key=lambda x: -x[2])
    ket_qua = ket_qua[:toi_da_khoang]
    ket_qua.sort(key=lambda x: x[0])
    return ket_qua


def _cat_khoang_local(file_goc, bd, kt, dich):
    """Cắt một khoảng video từ file gốc cục bộ bằng ffmpeg (-c copy nhanh 0.05s).
    Lấy dư 1.5s mỗi đầu để bảo toàn khung khoá (keyframe buffer).
    Nếu copy lỗi nhẹ thì fallback ultrafast encode."""
    bd_du = max(0.0, float(bd) - 1.5)
    kt_du = float(kt) + 1.5
    thoi_luong = round(kt_du - bd_du, 2)
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    # 1. Thử -c copy siêu tốc (không re-encode)
    cat_lenh = [FFMPEG, "-y", "-ss", f"{bd_du:.2f}", "-i", file_goc,
                "-t", f"{thoi_luong:.2f}", "-c", "copy", dich]
    p = subprocess.run(cat_lenh, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    if p.returncode == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 10000:
        return True, thoi_luong
    # 2. Nếu copy lỗi (do keyframe lệch): encode lại siêu tốc (chỉ 30s)
    cat_lenh_enc = [FFMPEG, "-y", "-ss", f"{bd_du:.2f}", "-i", file_goc,
                    "-t", f"{thoi_luong:.2f}", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", dich]
    p2 = subprocess.run(cat_lenh_enc, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60,
                        creationflags=0x08000000 if os.name == "nt" else 0)
    if p2.returncode == 0 and os.path.isfile(dich) and os.path.getsize(dich) > 10000:
        return True, thoi_luong
    return False, thoi_luong


TAI_GOC_TOI_DA = 1200        # giây cho MỘT lần tải video gốc (19/10: video 20 phút tải riêng mất 126 s; 5 luồng chia mạng)
TAI_LAI_CHO = 30            # video lỗi: chờ bấy nhiêu giây rồi tải lại TỪNG VIDEO MỘT sau đợt tải chính


def _tai_video_goc(vid, file_goc, chi_hinh=False):
    """Tải 1 video YouTube 720p hoàn chỉnh bằng bộ tải gốc yt-dlp (nhanh 10-15s, không bị bóp băng thông)."""
    if os.path.isfile(file_goc) and os.path.getsize(file_goc) > 50000:
        return True
    thu_goc = os.path.dirname(file_goc)
    os.makedirs(thu_goc, exist_ok=True)
    vid_safe = re.sub(r"[^\w-]", "", vid)[:30]

    def _don_dep_tam():
        import glob
        for f_tam in glob.glob(os.path.join(thu_goc, f"goc_{vid_safe}*")):
            if f_tam != file_goc:
                try:
                    os.remove(f_tam)
                except Exception:
                    pass

    # yt-dlp: bỏ --no-part vì --no-part khiến yt-dlp không nhận diện được file .part đã tải xong một phần,
    # dẫn đến HTTP Error 416 (Requested range not satisfiable) khi cố resume stream đã đủ.
    # 18/10: --concurrent-fragments 4 (DASH tải 4 phần cùng lúc); chi_hinh: chỉ luồng hình (mảnh cắt ra đều tắt tiếng)
    lenh = [YTDLP, *YT_JS, "--no-playlist", "--no-warnings",
            "--retries", "5", "--fragment-retries", "5", "--concurrent-fragments", "4",
            "-f", "bv*/b" if chi_hinh else "bv*+ba/b", "-S", f"res:{CHIEU_CAO},vcodec:h264,acodec:m4a",
            "--merge-output-format", "mp4", "--ffmpeg-location", os.path.dirname(FFMPEG) or ".",
            "-o", file_goc, f"https://www.youtube.com/watch?v={vid}"]
    err_cuoi = ""
    for lan in range(2):
        try:                                                 # 19/10: 300 s cứng cắt video dài khi 5 luồng chia mạng
            p = subprocess.run(lenh, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=TAI_GOC_TOI_DA,
                               creationflags=0x08000000 if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            err_cuoi = f"ERROR: quá thời gian tải ({TAI_GOC_TOI_DA} s)"
            _don_dep_tam()
            continue
        if p.returncode == 0 and os.path.isfile(file_goc) and os.path.getsize(file_goc) > 50000:
            return True
        if p.stderr:
            err_cuoi = p.stderr.decode("utf-8", errors="ignore").strip()
        # Khi gặp lỗi 416 hoặc lỗi tải, xóa file tải dở để lần sau tải sạch từ đầu
        _don_dep_tam()
        time.sleep(2 * (lan + 1))

    if err_cuoi:
        # 19/10 user (log chỉ còn "ERROR:"): lỗi yt-dlp có thể nhiều dòng -> ghép từ dòng ERROR đầu tới hết; lưu bản đầy đủ
        dong = [x.strip() for x in err_cuoi.splitlines() if x.strip()]
        dau = next((k for k, x in enumerate(dong) if "ERROR" in x or "Sign in" in x), max(0, len(dong) - 3))
        msg = " | ".join(dong[dau:])
        log(f"    ! yt-dlp {vid}: {msg[:300]}")
        try:
            thu_loi = os.path.join(os.path.dirname(os.path.dirname(thu_goc)), "loi_tai")
            os.makedirs(thu_loi, exist_ok=True)
            with open(os.path.join(thu_loi, f"{vid_safe}.txt"), "w", encoding="utf-8") as f:
                f.write(" ".join(lenh) + chr(10) * 2 + err_cuoi)
        except OSError:
            pass
    _don_dep_tam()
    return False



def tai_khoang_video_dong_bo(du_an, vid, bd, kt, tieu_de="", kenh="", chu_de_id=None):
    r"""Tải một khoảng video đồng bộ (chạy trong luồng worker).
    Đúng ID YouTube bằng regex r'[^\w-]'.
    Tải video gốc 720p về tệp tạm rồi cắt bằng ffmpeg trong 0.05s."""
    vid_safe = re.sub(r"[^\w-]", "", vid)[:30]
    kid = f"v_{vid_safe}_{int(bd)}"
    kho = doc_kho(du_an)
    thu = os.path.join(_ra(du_an), "kho", "video")
    os.makedirs(thu, exist_ok=True)
    dich = os.path.join(thu, kid + ".mp4")

    if kho.get(kid, {}).get("trang_thai") == "xong" and os.path.isfile(dich) and os.path.getsize(dich) > 10000:
        return kid

    _cap_nhat_kho(du_an, kid, loai="video", video_goc=vid, giay_bat_dau=round(bd, 2),
                  giay_ket_thuc=round(kt, 2), kenh=kenh, chu_de=chu_de_id,
                  tieu_de=f"{tieu_de} [{int(bd)}s-{int(kt)}s]", file=dich,
                  trang_thai="dang", pt=0.0, luc=time.time())

    file_goc = os.path.join(thu, f"goc_{vid_safe}.mp4")
    ok_goc = _tai_video_goc(vid, file_goc)
    if not ok_goc:
        _cap_nhat_kho(du_an, kid, trang_thai="loi", loi="Không tải được video gốc")
        return kid

    ok_cat, thoi_luong = _cat_khoang_local(file_goc, bd, kt, dich)
    if ok_cat and os.path.isfile(dich):
        dai_that = _do_dai(dich) or thoi_luong
        w, h = _kich_thuoc(dich)
        _cap_nhat_kho(du_an, kid, loai="video", video_goc=vid, giay_bat_dau=round(bd, 2),
                      giay_ket_thuc=round(kt, 2), kenh=kenh, chu_de=chu_de_id,
                      tieu_de=f"{tieu_de} [{int(bd)}s-{int(kt)}s]", file=dich,
                      dai=dai_that, rong=w, cao=h, trang_thai="xong", pt=100.0, luc=time.time())
    else:
        _cap_nhat_kho(du_an, kid, trang_thai="loi", loi="Cắt khoảng video lỗi")

    try:
        if os.path.isfile(file_goc):
            os.remove(file_goc)
    except Exception:
        pass
    return kid


def tai_khoang_video(du_an, vid, bd, kt, tieu_de="", kenh="", chu_de_id=None, tay=False):
    """Tải một khoảng video chạy nền (async)."""
    vid_safe = re.sub(r"[^\w-]", "", vid)[:30]
    kid = f"v_{vid_safe}_{int(bd)}"
    threading.Thread(target=tai_khoang_video_dong_bo,
                     args=(du_an, vid, bd, kt, tieu_de, kenh, chu_de_id),
                     daemon=True).start()
    return kid


def tai_khoang_cuon(du_an, ds_khoang, ten_buoc="tai_khoang", max_cung_luc=3, on_tien_do=None, sau_moi_video=None,
                    chi_hinh=False, bam_ca=None):
    """Tải các khoảng video theo cơ chế Batch-per-source:
    Gom các khoảng theo từng video nguồn (vid). Với mỗi video nguồn:
    1. Tải bản 720p một lần bằng bộ tải gốc yt-dlp (nhanh 10-15s, không bị bóp băng thông).
    2. Cắt các khoảng cần thiết bằng ffmpeg cục bộ (-c copy chỉ mất 0.05s/khoảng).
    3. Xoá file gốc tạm để giải phóng ổ cứng.
    Chạy song song 2-3 video nguồn cùng lúc, cập nhật tiến độ mượt mà."""
    tong = len(ds_khoang)
    if tong == 0:
        return []

    from concurrent.futures import ThreadPoolExecutor
    kho = doc_kho(du_an)
    thu = os.path.join(_ra(du_an), "kho", "video")
    os.makedirs(thu, exist_ok=True)

    # Gom các khoảng theo từng video nguồn
    theo_vid = {}
    for item in ds_khoang:
        theo_vid.setdefault(item["vid"], []).append(item)

    xong = [0]
    kids = []
    khoa_local = threading.Lock()

    that_bai = []

    def xu_ly_video(vid, danh_sach, lan_cuoi=False):
        vid_safe = re.sub(r"[^\w-]", "", vid)[:30]
        # Lọc các khoảng chưa có
        can_cat = []
        for it in danh_sach:
            kid = f"v_{vid_safe}_{int(it['bd'])}"
            dich = os.path.join(thu, kid + ".mp4")
            with khoa_local:
                if kid not in kids:                          # lần tải lại (video lỗi) không thêm trùng
                    kids.append(kid)
            if kho.get(kid, {}).get("trang_thai") == "xong" and os.path.isfile(dich) and os.path.getsize(dich) > 10000:
                with khoa_local:
                    xong[0] += 1
                    if on_tien_do:
                        on_tien_do(xong[0], tong)
            else:
                can_cat.append((it, kid, dich))

        if not can_cat:
            return

        # Đánh dấu đang tải
        for it, kid, dich in can_cat:
            _cap_nhat_kho(du_an, kid, loai="video", video_goc=vid, giay_bat_dau=round(it["bd"], 2),
                          giay_ket_thuc=round(it["kt"], 2), kenh=it.get("kenh", ""),
                          chu_de=it.get("chu_de_id"),
                          tieu_de=f"{it.get('tieu_de', '')} [{int(it['bd'])}s-{int(it['kt'])}s]",
                          file=dich, trang_thai="dang", pt=0.0, luc=time.time(), tay=True)

        # 1. Tải video gốc 720p về tệp tạm
        file_goc = os.path.join(thu, f"goc_{vid_safe}.mp4")
        ok_goc = _tai_video_goc(vid, file_goc, chi_hinh=chi_hinh)

        if not ok_goc and not lan_cuoi:                      # 19/10: lỗi nhất thời -> tải lại từng video một ở cuối
            with khoa_local:
                that_bai.append((vid, danh_sach))
            log(f"    ! chưa tải được video gốc {vid_safe} -> thử lại sau đợt tải chính")
            return
        if not ok_goc:
            log(f"    ! không tải được video gốc {vid_safe} (đã thử lại) -> đánh dấu lỗi các khoảng")
            for it, kid, dich in can_cat:
                _cap_nhat_kho(du_an, kid, trang_thai="loi", loi="Không tải được video gốc", tay=True)
                with khoa_local:
                    xong[0] += 1
                    if on_tien_do:
                        on_tien_do(xong[0], tong)
            return

        # 2'. 22/10 user: BĂM CẢ VIDEO theo cảnh quay (bam_ca(vid, file gốc, danh sách khoảng) -> (giây, số mảnh)); các
        #     khoảng định vị thô chỉ còn là dấu "đã xử lý" (trang_thai "tach") — không cắt khoảng ±1,5 s nữa
        if bam_ca is not None:
            try:
                _g, so_m = bam_ca(vid, file_goc, danh_sach)
            except Exception as e:                           # noqa: BLE001
                log(f"    ! băm cả video {vid_safe}: {str(e)[:120]}")
                so_m = 0
            for it, kid, dich in can_cat:
                _cap_nhat_kho(du_an, kid, trang_thai="tach" if so_m else "loi", cat_sat=True, so_manh=so_m,
                              loi="" if so_m else "băm cả video: không cảnh nào khớp", tay=True)
                with khoa_local:
                    xong[0] += 1
                    if on_tien_do:
                        on_tien_do(xong[0], tong)
            try:
                os.remove(file_goc)
            except OSError:
                pass
            return

        # 2. Cắt từng khoảng cục bộ bằng ffmpeg (-c copy)
        for it, kid, dich in can_cat:
            ok_cat, thoi_luong = _cat_khoang_local(file_goc, it["bd"], it["kt"], dich)
            if ok_cat and os.path.isfile(dich):
                dai_that = _do_dai(dich) or thoi_luong
                w, h = _kich_thuoc(dich)
                _cap_nhat_kho(du_an, kid, loai="video", video_goc=vid, giay_bat_dau=round(it["bd"], 2),
                              giay_ket_thuc=round(it["kt"], 2), kenh=it.get("kenh", ""),
                              chu_de=it.get("chu_de_id"),
                              tieu_de=f"{it.get('tieu_de', '')} [{int(it['bd'])}s-{int(it['kt'])}s]",
                              file=dich, dai=dai_that, rong=w, cao=h, trang_thai="xong", pt=100.0, luc=time.time(), tay=True)
            else:
                _cap_nhat_kho(du_an, kid, trang_thai="loi", loi="Cắt khoảng video lỗi", tay=True)
            with khoa_local:
                xong[0] += 1
                if on_tien_do:
                    on_tien_do(xong[0], tong)

        # 3. Dọn dẹp tệp gốc tạm
        try:
            if os.path.isfile(file_goc):
                os.remove(file_goc)
        except Exception:
            pass
        if sau_moi_video:                                    # 18/10: xử lý tiếp (cắt sát) NGAY khi video này xong,
            try:                                             # chạy chồng lên lúc các video khác còn đang tải
                sau_moi_video(vid, [kid for _, kid, _ in can_cat])
            except Exception as e:                           # noqa: BLE001
                log(f"    ! xử lý sau tải {vid_safe}: {str(e)[:100]}")

    so_luong_thread = min(max(1, max_cung_luc), len(theo_vid), 10)  # 22/10: tối đa 10 video cùng lúc (trước: 5)
    with ThreadPoolExecutor(max_workers=so_luong_thread) as executor:
        for vid, ds_it in theo_vid.items():
            executor.submit(xu_ly_video, vid, ds_it)
    if that_bai:
        log(f"    tải lại {len(that_bai)} video lỗi, từng video một (chờ {TAI_LAI_CHO} s)…")
        time.sleep(TAI_LAI_CHO)
        for vid, ds_it in that_bai:
            xu_ly_video(vid, ds_it, lan_cuoi=True)

    return kids


TI_LE_CHU_BO = 0.25         # 16/10 user: video YouTube có chữ (phụ đề to, tiêu đề) ở hơn bấy nhiêu khung -> bỏ cả video
KENH_BO = os.path.join(CACHE_CHUNG, "kenh_bo.json")   # kênh từng bị bỏ (logo / phụ đề) -> lần sau khỏi tải video kênh đó


def loc_youtube(du_an, kenh_cua=None):
    """Giai đoạn 4 — Lọc logo và phụ đề sau khi tải:
    - Phụ đề và chữ to: dùng loc_chu.chu_video chạy trên từng khoảng. Khoảng có chữ > 25% khung thì bỏ.
    - Logo kênh: gộp khung hình của MỌI khoảng cùng một video gốc rồi mới dò (sach_hinh.logo_kenh_gop).
      Logo kênh giống nhau ở mọi khoảng, nên dò chung là đủ cảnh quay.
      Có logo thì bỏ mọi khoảng của video đó và ghi tên kênh vào kenh_bo.json.
    kenh_cua: {id YouTube: tên kênh}. Trả (số khoảng/video bỏ, tổng số đã soát)."""
    import loc_chu
    import sach_hinh
    kenh_cua = kenh_cua or {}
    bo = soat = 0
    kenh_moi = {}

    kho = doc_kho(du_an)
    nhom_goc = {}
    for kid, m in kho.items():
        if m.get("loai") != "video" or m.get("trang_thai") != "xong" or m.get("sach") or m.get("tay"):
            continue
        vid_goc = m.get("video_goc") or (kid[2:] if kid.startswith("v_") else kid)
        if "chu_yt" in m and "logo" in m:
            continue
        nhom_goc.setdefault(vid_goc, []).append((kid, m))

    for vid_goc, items in nhom_goc.items():
        soat += len(items)

        # 1. Phụ đề và chữ to trên từng khoảng
        co_chu_khoang = {}
        for kid, m in items:
            f = m.get("file", "")
            if not os.path.isfile(f):
                continue
            try:
                s = loc_chu.chu_video("tay_" + kid, f)
                ti = float((s > loc_chu.NGUONG_DIEN_TICH).mean()) if len(s) else 0.0
            except Exception:
                ti = 0.0
            co_chu_khoang[kid] = (ti, ti > TI_LE_CHU_BO)

        # 2. Logo kênh: gộp khung hình của mọi khoảng cùng một video gốc rồi mới dò
        paths = [m["file"] for _, m in items if os.path.isfile(m.get("file", ""))]
        try:
            goc_logo = sach_hinh.logo_kenh_gop(paths, "gop_" + vid_goc) if paths else []
        except Exception:
            goc_logo = []

        k = (kenh_cua.get(vid_goc) or
             next((m.get("kenh") for _, m in items if m.get("kenh")), "") or
             kenh_cua.get(vid_goc.split("_")[0]) or "")

        if goc_logo:
            # Có logo: BỎ MỌI KHOẢNG của video đó
            bo += len(items)
            log(f"    bỏ MỌI khoảng của video YouTube {vid_goc} (logo kênh {goc_logo}){' — kênh ' + k if k else ''}")
            if k:
                kenh_moi[k] = f"logo kênh {goc_logo}"
            for kid, m in items:
                ti, _ = co_chu_khoang.get(kid, (0.0, False))
                _cap_nhat_kho(du_an, kid, chu_yt=round(ti, 3), logo=goc_logo, bo_yt="logo kênh")
        else:
            # Không có logo kênh: xét từng khoảng theo chữ / phụ đề
            for kid, m in items:
                ti, co_chu = co_chu_khoang.get(kid, (0.0, False))
                ly_do = f"chữ/phụ đề {ti * 100:.0f}% khung" if co_chu else ""
                _cap_nhat_kho(du_an, kid, chu_yt=round(ti, 3), logo=[], bo_yt=ly_do)
                if ly_do:
                    bo += 1
                    log(f"    bỏ khoảng YouTube {kid} ({ly_do}){' — kênh ' + k if k else ''}")
                    if k:
                        kenh_moi[k] = ly_do

    if kenh_moi:
        with _KHOA:
            da = doc_json(KENH_BO, {}) or {}
            da.update(kenh_moi)
            ghi_json(KENH_BO, da)

    return bo, soat



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


def _phong_ai():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    return anh_ve.PHONG_ANH_AI


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
                ph = _phong_ai() if m.get("nguon") == "gemini" else 1.0   # 19/10: 120% giấu ✦ chỉ khi chưa xoá được logo
                seg = draft.VideoSegment(mat, trange(t0, dl),
                                         clip_settings=draft.ClipSettings(scale_x=ph, scale_y=ph) if ph > 1.0 else None)
            script.add_segment(seg, track_name="hinh")
            het = t0 + dl
            n += 1
    if os.path.isfile(wav):
        dai = _do_dai(wav)
        script.add_segment(draft.AudioSegment(draft.AudioMaterial(wav), trange(0, int(dai * 1_000_000) - 1000)),
                           track_name="giong")
    script.save()
    _sua_nhap(os.path.join(drafts_dir, ten), list(vat_lieu))
    try:                                                    # 13/10 user: 2 dòng chữ mẫu (chu_mau.json) trên mọi bản nháp
        import chu_mau
        chu_mau.gan(os.path.join(drafts_dir, ten))
    except Exception as e:                                  # noqa: BLE001
        log(f"  ! gắn chữ mẫu lỗi: {e}")
    log(f"bản nháp dựng tay '{ten}': {n} đoạn hình (trỏ video gốc)")
    return n
