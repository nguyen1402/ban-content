# -*- coding: utf-8 -*-
"""ĐỐI THỦ YouTube (20/10 user) — chỉ đọc dữ liệu công khai bằng yt-dlp (không tải video, không cần khoá API):

  quet_gio(kenh, n)        giờ đăng CHÍNH XÁC (giây, đổi sang giờ Việt Nam) của n video mới nhất một kênh + thống kê
                           khung giờ / thứ trong tuần hay đăng và lượt xem trung bình theo khung.
  tim_dot_bien(tu_khoa…)   video của KÊNH ÍT SUB cùng ngách mà lượt xem / tương tác ĐỘT BIẾN: tìm theo từ khoá ngách
                           (mới nhất + liên quan nhất), đọc số sub kênh, view, like, bình luận, giờ đăng; xếp theo
                           hệ số view / sub, view mỗi ngày, tỉ lệ tương tác.

Chi tiết từng video lưu đệm ở cache/doi_thu/<id>.json (6 giờ) — quét lại nhanh."""
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from common import CACHE_CHUNG, ROOT, _slug, log

THU_MUC_PLUGIN = os.path.join(ROOT, "plugins_doi_thu")

VN = timezone(timedelta(hours=7))
LUONG = 6                   # số video đọc chi tiết cùng lúc
HAN_DEM = 6 * 3600          # chi tiết video lưu đệm bấy nhiêu giây (view / like đổi theo giờ)
THU = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
_KHOA = threading.Lock()


def _ytdlp():
    import dung_tay
    return dung_tay.YTDLP, list(dung_tay.YT_JS)


def _chay_json(args, timeout=120):
    yt, js = _ytdlp()
    p = subprocess.run([yt, *js, "--no-warnings", "-J", *args], capture_output=True, timeout=timeout,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        j = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
    except ValueError:
        j = None
    if not isinstance(j, dict):
        log(f"    ! yt-dlp {' '.join(args)[-80:]}: {p.stderr.decode('utf-8', 'ignore').strip()[-160:]}")
        return {}
    return j


def _url_kenh(kenh):
    """@handle / link kênh / link /channel/… -> link danh sách video (tab Video, mới nhất trước)."""
    k = str(kenh or "").strip()
    if not k:
        raise ValueError("thiếu kênh")
    if k.startswith("@"):
        k = "https://www.youtube.com/" + k
    if "youtube.com" not in k and "youtu.be" not in k:
        k = "https://www.youtube.com/@" + k.lstrip("@")
    k = k.split("?")[0].rstrip("/")
    for duoi in ("/videos", "/shorts", "/streams", "/featured", "/playlists", "/about"):
        if k.endswith(duoi):
            k = k[: -len(duoi)]
    return k + "/videos"


def chi_tiet(vid, lam_moi=False):
    """Chi tiết công khai của một video: giờ đăng (mốc giây), view, like, bình luận, sub kênh… (lưu đệm 6 giờ)."""
    thu = os.path.join(CACHE_CHUNG, "doi_thu")
    os.makedirs(thu, exist_ok=True)
    p = os.path.join(thu, f"{vid}.json")
    if not lam_moi and os.path.isfile(p) and time.time() - os.path.getmtime(p) < HAN_DEM:
        try:
            return json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            pass
    j = _chay_json(["--skip-download", "--no-playlist", f"https://www.youtube.com/watch?v={vid}"])
    if not j.get("id"):
        return None
    ts = j.get("release_timestamp") or j.get("timestamp")
    x = {"id": j["id"], "tieu_de": j.get("title") or "", "kenh": j.get("channel") or j.get("uploader") or "",
         "kenh_id": j.get("channel_id") or "", "kenh_url": j.get("channel_url") or "",
         "sub": j.get("channel_follower_count"), "view": j.get("view_count") or 0, "like": j.get("like_count"),
         "binh_luan": j.get("comment_count"), "dai": j.get("duration") or 0, "ts": ts,
         "cong_chieu": bool(j.get("release_timestamp")) and j.get("release_timestamp") != j.get("timestamp"),
         "ngay": j.get("upload_date") or "", "anh": j.get("thumbnail") or "",
         "short": "/shorts/" in str(j.get("webpage_url") or "") or (j.get("duration") or 0) <= 60,
         "tags": list(j.get("tags") or [])[:20], "ngon_ngu": j.get("language") or ""}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(x, f, ensure_ascii=False)
    return x


def _them_gio(x):
    """Thêm giờ Việt Nam, thứ, tuổi (ngày), view/ngày, tỉ lệ tương tác."""
    if x.get("ts"):
        d = datetime.fromtimestamp(int(x["ts"]), VN)
        x["gio_vn"] = d.strftime("%d/%m/%Y %H:%M:%S")
        x["gio"], x["thu"] = d.hour, THU[d.weekday()]
        tuoi = max(1 / 24, (time.time() - int(x["ts"])) / 86400)
    else:
        x["gio_vn"], x["gio"], x["thu"] = (x.get("ngay") or "?"), None, ""
        tuoi = None
    x["tuoi_ngay"] = round(tuoi, 1) if tuoi else None
    x["view_ngay"] = int(x["view"] / tuoi) if tuoi else None
    tt = (x.get("like") or 0) + (x.get("binh_luan") or 0)
    x["tuong_tac"] = round(100 * tt / x["view"], 2) if x.get("view") else None
    x["he_so"] = round(x["view"] / x["sub"], 2) if x.get("sub") else None
    return x


def _doc_nhieu(ids, bao=None):
    ra, xong = [], [0]

    def mot(v):
        try:
            x = chi_tiet(v)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! đọc video {v}: {str(e)[:80]}")
            x = None
        with _KHOA:
            xong[0] += 1
            if bao:
                bao(f"Đọc chi tiết {xong[0]}/{len(ids)} video…", xong[0], len(ids))
        return x
    with ThreadPoolExecutor(LUONG) as ex:
        for x in ex.map(mot, ids):
            if x:
                ra.append(_them_gio(dict(x)))
    return ra


def quet_gio(kenh, n=50, bao=None):
    """Giờ đăng của n video mới nhất một kênh (tab Video) + thống kê theo giờ / thứ."""
    url = _url_kenh(kenh)
    if bao:
        bao(f"Lấy danh sách video của {url}…", 0, n)
    j = _chay_json(["--flat-playlist", "--playlist-end", str(int(n)), url], timeout=180)
    ids = [e["id"] for e in (j.get("entries") or []) if e and e.get("id")][: int(n)]
    if not ids:
        raise ValueError(f"không đọc được video nào của {url} (sai link kênh?)")
    ds = sorted(_doc_nhieu(ids, bao), key=lambda x: -(x.get("ts") or 0))
    theo_gio = {h: {"so": 0, "view": 0} for h in range(24)}
    theo_thu = {t: {"so": 0, "view": 0} for t in THU}
    for x in ds:
        if x.get("gio") is not None:
            theo_gio[x["gio"]]["so"] += 1
            theo_gio[x["gio"]]["view"] += x["view"]
            theo_thu[x["thu"]]["so"] += 1
            theo_thu[x["thu"]]["view"] += x["view"]
    for d in list(theo_gio.values()) + list(theo_thu.values()):
        d["view_tb"] = int(d["view"] / d["so"]) if d["so"] else 0
    cach = [round((a["ts"] - b["ts"]) / 86400, 2) for a, b in zip(ds, ds[1:]) if a.get("ts") and b.get("ts")]
    return {"kenh": ds[0]["kenh"] if ds else "", "url": url, "sub": ds[0].get("sub") if ds else None, "ds": ds,
            "theo_gio": theo_gio, "theo_thu": theo_thu,
            "cach_tb_ngay": round(sum(cach) / len(cach), 2) if cach else None}


_P_TU_KHOA = """Below are recent video titles and tags of a YouTube channel (any language). Identify the channel's NICHE
and write ENGLISH YouTube search phrases that would find SIMILAR English-language videos (same topics, same angle / format),
so a creator can study English videos for ideas.
Return ONLY JSON: {{"ngach": "<short Vietnamese description of the niche>", "tu_khoa_en": ["<8-15 English search phrases,
2-6 words each, specific topics first, then broader niche phrases; no channel names>"]}}

CHANNEL: {kenh}
{ds}"""


def tu_khoa_tu_kenh(kenh, n=40, bao=None):
    """20/10 user: AI đọc tiêu đề + tag các video mới của kênh đối thủ -> ngách + từ khoá tìm TIẾNG ANH (một lần hỏi)."""
    from common import hoi_llm, rut_json
    url = _url_kenh(kenh)
    if bao:
        bao(f"Đọc tiêu đề video của {url}…", 0, n)
    j = _chay_json(["--flat-playlist", "--playlist-end", str(int(n)), url], timeout=180)
    vs = [e for e in (j.get("entries") or []) if e and e.get("id")][: int(n)]
    if len(vs) < 15:                                         # tab Video ít bài: đọc thêm tab Shorts
        j2 = _chay_json(["--flat-playlist", "--playlist-end", str(int(n)), url[:-len("/videos")] + "/shorts"], timeout=180)
        vs += [e for e in (j2.get("entries") or []) if e and e.get("id") and all(e["id"] != v["id"] for v in vs)]
        vs = vs[: int(n)]
        j = j if j.get("channel") or not j2 else j2
    if not vs:
        raise ValueError(f"không đọc được video nào của {url}")
    tags = {}
    for x in _doc_nhieu([e["id"] for e in vs[:15]], bao):  # tag của 15 video mới nhất (đọc chi tiết)
        tags[x["id"]] = x.get("tags") or []
    ds = "\n".join(f"- {e.get('title') or ''}" + (f"  [tags: {', '.join(tags[e['id']][:8])}]" if tags.get(e["id"]) else "")
                   for e in vs)
    if bao:
        bao("Hỏi AI ngách + từ khoá tiếng Anh…", n, n)
    r = rut_json(hoi_llm(_P_TU_KHOA.format(kenh=j.get("channel") or j.get("title") or url, ds=ds[:12000]), timeout=240) or "")
    if not isinstance(r, dict) or not r.get("tu_khoa_en"):
        raise ValueError("AI không trả từ khoá (thử lại)")
    return {"kenh": j.get("channel") or j.get("title") or "", "ngach": str(r.get("ngach") or ""),
            "tu_khoa_en": [str(t).strip() for t in r["tu_khoa_en"] if str(t).strip()][:15], "so_video": len(vs)}


_VIET = set("ăâđêôơưĂÂĐÊÔƠƯ")
_DAU_VIET = set("ạảãàáặẳẵằắậẩẫầấẹẻẽèéệểễềếịỉĩìíọỏõòóộổỗồốợởỡờớụủũùúựửữừứỵỷỹỳýẠẢÃÀÁẶẲẴẰẮẬẨẪẦẤẸẺẼÈÉỆỂỄỀẾỊỈĨÌÍỌỎÕÒÓỘỔỖỒỐỢỞỠỜỚỤỦŨÙÚỰỬỮỪỨỴỶỸỲÝ")


def la_tieng_viet(x):
    """20/10 user: chỉ bỏ video TIẾNG VIỆT (tiếng Anh hay tiếng nào khác đều giữ). Theo trường ngôn ngữ YouTube nếu có,
    không thì theo tiêu đề: có chữ riêng của tiếng Việt (ă â đ ê ô ơ ư) hoặc >= 2 chữ mang dấu thanh tiếng Việt."""
    nn = str(x.get("ngon_ngu") or "").lower()
    if nn:
        return nn.startswith("vi")
    t = str(x.get("tieu_de") or "")
    return any(c in _VIET for c in t) or sum(1 for c in t if c in _DAU_VIET) >= 2


def tim_dot_bien(tu_khoa, n_moi_tu=30, sub_toi_da=50000, ngay_toi_da=60, view_toi_thieu=10000, bo_short=True, bao=None,
                 bo_tieng_viet=False):
    """Video đột biến của kênh ít sub cùng ngách: mỗi từ khoá tìm n_moi_tu kết quả MỚI ĐĂNG + n_moi_tu LIÊN QUAN NHẤT,
    đọc chi tiết rồi lọc (sub <= sub_toi_da, đăng trong ngay_toi_da ngày, view >= view_toi_thieu, bỏ Shorts nếu chọn);
    xếp theo hệ số view/sub (đột biến so với cỡ kênh)."""
    tus = [t.strip() for t in tu_khoa if str(t).strip()]
    if not tus:
        raise ValueError("thiếu từ khoá ngách")
    import urllib.parse
    # bộ lọc "thời gian tải lên" của YouTube (sp): tuần này / tháng này / năm nay — kèm kết quả LIÊN QUAN không lọc
    # (đo 20/10: lọc "tháng này" ra video 1-22 ngày; sắp "mới nhất" của yt-dlp không chạy)
    sp = "EgQIAxAB" if ngay_toi_da <= 7 else ("EgQIBBAB" if ngay_toi_da <= 31 else "EgQIBRAB")
    ids, xong = [], 0
    for q in tus:
        for ten, loc in (("mới đăng", sp), ("liên quan", "EgIQAQ==")):
            xong += 1
            if bao:
                bao(f"Tìm «{q}» ({ten})…", xong, len(tus) * 2)
            u = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q, "sp": loc})
            j = _chay_json(["--flat-playlist", "--playlist-end", str(int(n_moi_tu)), u], timeout=180)
            for e in j.get("entries") or []:
                if e and e.get("id") and e["id"] not in ids:
                    ids.append(e["id"])
    ds = _doc_nhieu(ids, bao)
    ra = []
    for x in ds:
        if bo_short and x.get("short"):
            continue
        if bo_tieng_viet and la_tieng_viet(x):
            continue
        if x.get("sub") is None or x["sub"] > sub_toi_da:
            continue
        if x.get("tuoi_ngay") is None or x["tuoi_ngay"] > ngay_toi_da:
            continue
        if x["view"] < view_toi_thieu:
            continue
        ra.append(x)
    ra.sort(key=lambda x: -(x.get("he_so") or 0))
    return {"tong_tim": len(ids), "doc_duoc": len(ds), "ds": ra}


def _tai_phu_de(vid):
    """Lời thoại (phụ đề tay hoặc tự động, ưu tiên tiếng Việt rồi tiếng Anh) -> [dòng]; lưu đệm cache/doi_thu/<id>.sub.txt.
    25/10: bản cũ chạy '-o -' với --skip-download -> yt-dlp ghi phụ đề ra FILE chứ không ra stdout, nên lời thoại luôn rỗng
    (số từ / tốc độ đọc / câu hook đều là số mặc định)."""
    import glob
    import re
    import shutil
    import tempfile
    thu = os.path.join(CACHE_CHUNG, "doi_thu")
    os.makedirs(thu, exist_ok=True)
    p = os.path.join(thu, f"{vid}.sub.txt")
    pg = os.path.join(thu, f"{vid}.subgio.json")              # [[giây bắt đầu, câu]] cho thư viện minh hoạ
    if os.path.isfile(p) and os.path.isfile(pg):
        return [l for l in open(p, encoding="utf-8").read().splitlines() if l.strip()]
    tam = tempfile.mkdtemp(prefix="sub_", dir=thu)
    try:
        yt, js = _ytdlp()
        subprocess.run([yt, *js, "--no-warnings", "--skip-download", "--write-subs", "--write-auto-subs",
                        "--sub-langs", "vi,vi-orig,en,en-orig", "--sub-format", "vtt", "-o", os.path.join(tam, "%(id)s.%(ext)s"),
                        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, timeout=90,
                       creationflags=0x08000000 if os.name == "nt" else 0)
        ds = glob.glob(os.path.join(tam, "*.vtt"))
        ds.sort(key=lambda f: (0 if ".vi" in os.path.basename(f) else 1, "-orig" in f))
        if not ds:
            return []
        dong, gio, t = [], [], 0.0
        for l in open(ds[0], encoding="utf-8", errors="ignore").read().splitlines():
            m = re.match(r"(\d+):(\d\d):(\d\d)[.,](\d+) -->", l)
            if m:
                t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4][:3].ljust(3, "0")) / 1000
                continue
            if "-->" in l or not l.strip() or re.match(r"^(WEBVTT|Kind:|Language:|NOTE)", l):
                continue
            s = re.sub(r"<[^>]+>", "", l).strip()
            if s and (not dong or (s != dong[-1] and not dong[-1].endswith(s))):   # phụ đề tự động lặp dòng cuộn
                dong.append(s)
                gio.append([round(t, 1), s])
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(dong))
        with open(pg, "w", encoding="utf-8") as f:
            json.dump(gio, f, ensure_ascii=False)
        return dong
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! phụ đề {vid}: {str(e)[:100]}")
        return []
    finally:
        shutil.rmtree(tam, ignore_errors=True)


def _khung_hinh(vid, dai, n=6):
    """n khung hình rải đều trong video (bản chất lượng thấp nhất, chỉ để NHÌN phong cách vẽ / bố cục) -> [jpg]."""
    from common import FFMPEG
    thu = os.path.join(CACHE_CHUNG, "doi_thu", "khung", vid)
    co = sorted(f for f in (os.listdir(thu) if os.path.isdir(thu) else []) if f.startswith("k_"))
    if len(co) >= n and _khung_day(vid):
        return [os.path.join(thu, f) for f in co[:n]]
    os.makedirs(thu, exist_ok=True)
    vf = os.path.join(thu, "v.mp4")
    try:
        yt, js = _ytdlp()
        subprocess.run([yt, *js, "--no-warnings", "--no-playlist", "--no-part", "-f",
                        # chỉ cần HÌNH: luồng video-only <=480p (nhiều video chỉ còn định dạng DASH tách hình/tiếng)
                        "bv*[height<=480][ext=mp4]/bv*[height<=480]/wv*/w", "--max-filesize", "150M",
                        "-o", vf, f"https://www.youtube.com/watch?v={vid}"], capture_output=True, timeout=300,
                       creationflags=0x08000000 if os.name == "nt" else 0)
        if not os.path.isfile(vf):
            return []
        dai = float(dai or 0) or 120.0
        ra = []
        for i in range(n):
            t = dai * (0.06 + 0.88 * i / max(1, n - 1))
            f = os.path.join(thu, f"k_{i:02d}.jpg")
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.1f}", "-i", vf, "-frames:v", "1", "-vf", "scale=640:-2", f],
                           capture_output=True, timeout=60, creationflags=0x08000000 if os.name == "nt" else 0)
            if os.path.isfile(f):
                ra.append(f)
        # khung DÀY ở 3 phút đầu (mỗi 5 giây) cho thư viện minh hoạ: ghép với câu thoại đang đọc đúng lúc đó
        for t in range(3, int(min(dai, MINH_HOA_GIAY)), MINH_HOA_BUOC):
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", vf, "-frames:v", "1", "-vf", "scale=480:-2",
                            os.path.join(thu, f"m_{t:04d}.jpg")], capture_output=True, timeout=60,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        return ra
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! khung hình {vid}: {str(e)[:100]}")
        return []
    finally:
        try:
            os.remove(vf)
        except OSError:
            pass


MINH_HOA_GIAY = 180          # thư viện minh hoạ: xem 3 phút đầu video
MINH_HOA_BUOC = 5            # mỗi 5 giây một khung


def _khung_day(vid):
    """[(giây, jpg)] khung dày của video (cắt trong _khung_hinh)."""
    import re
    thu = os.path.join(CACHE_CHUNG, "doi_thu", "khung", vid)
    ra = []
    for f in sorted(os.listdir(thu)) if os.path.isdir(thu) else []:
        m = re.match(r"m_(\d+)\.jpg$", f)
        if m:
            ra.append((int(m[1]), os.path.join(thu, f)))
    return ra


_P_MINH_HOA = """These are consecutive frames of a YouTube storytelling video, each with the narration being spoken at that
moment. Study HOW THE CHANNEL ILLUSTRATES each line (this will be copied by another creator).
For every frame return:
  "i": the frame number,
  "khung": rong (wide shot of the situation) | trung (medium, people interacting) | can_mat (face close-up) |
           can_do_vat (close-up insert of an object / body part) | man_hinh (phone / laptop / TV screen) |
           an_du (symbolic image) | ngoai_canh (exterior of a place) | chu (text card / title),
  "cach_en": one English sentence: what is drawn and why it fits the line (people, place, object, device used).
Then "quy_tac": 4-8 GENERAL rules in English of the form "When the line <type of content>, the channel shows <type of
image>" (only rules the frames really show).
Only JSON: {{"khung": [{{"i": 1, "khung": "...", "cach_en": "..."}}], "quy_tac": ["..."]}}

{ds}"""


def _thu_vien_minh_hoa(vid, bao=None):
    """25/10 user (ảnh tự động phải tốt mà không duyệt tay): HỌC CÁCH KÊNH MINH HOẠ — khung dày 3 phút đầu + câu thoại
    đang đọc đúng lúc đó -> Gemini (kèm ảnh, lô 12 khung) mô tả từng khung minh hoạ câu thế nào + rút quy tắc chung.
    -> {"vi_du": [{"cau", "khung", "cach_en"}], "quy_tac": [...]}; storyboard dùng làm ví dụ mẫu khi chia cảnh."""
    from common import rut_json
    khung = _khung_day(vid)
    p = os.path.join(CACHE_CHUNG, "doi_thu", f"{vid}.subgio.json")
    gio = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else []
    if not khung or not gio:
        return {}
    cap = []
    for t, f in khung:
        cau = " ".join(s for g, s in gio if t - MINH_HOA_BUOC / 2 <= g < t + MINH_HOA_BUOC / 2)
        cau = cau or next((s for g, s in reversed(gio) if g <= t), "")
        if cau:
            cap.append((cau, f))
    # 27/10 user ("mãi nó không xong 1 kênh"): các lô hỏi LẦN LƯỢT -> nay hỏi cùng lúc, mỗi lô một tab Gemini
    cac_lo = [cap[k:k + 12] for k in range(0, len(cap), 12)]
    if bao:
        bao(f"Học cách kênh minh hoạ: {len(cap)} khung, {len(cac_lo)} lô hỏi cùng lúc…")

    def hoi_lo(lo):
        ds = "\n".join(f"Frame {i + 1}: «{c}»" for i, (c, _) in enumerate(lo))
        return _hoi_kem_anh(_P_MINH_HOA.format(ds=ds), [f for _, f in lo], timeout=240)[0]
    with ThreadPoolExecutor(max(1, len(cac_lo))) as ex:
        tra_loi = list(ex.map(hoi_lo, cac_lo))
    vi_du, quy_tac = [], []
    for lo, kq in zip(cac_lo, tra_loi):
        j = rut_json(kq or "")
        if not isinstance(j, dict):
            continue
        for x in j.get("khung") or []:
            try:
                i = int(x.get("i")) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(lo) and str(x.get("cach_en") or "").strip():
                vi_du.append({"cau": lo[i][0], "khung": str(x.get("khung") or "").strip(), "cach_en": str(x["cach_en"]).strip()})
        quy_tac += [str(q).strip() for q in j.get("quy_tac") or [] if str(q).strip()]
    return {"vi_du": vi_du[:40], "quy_tac": quy_tac[:16]}


def _tai_anh(url, dich):
    import urllib.request
    try:
        if not os.path.isfile(dich):
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10) as r:
                open(dich, "wb").write(r.read())
        return dich
    except Exception:                                        # noqa: BLE001
        return None


def _bang_mau(files, n=6):
    """Màu chủ đạo (gom cụm, không phải điểm ảnh lẻ) của các khung hình -> ['#rrggbb'…] xếp theo độ phủ."""
    from PIL import Image
    ims = []
    for f in files:
        try:
            ims.append(Image.open(f).convert("RGB").resize((160, 90)))
        except Exception:                                    # noqa: BLE001
            pass
    if not ims:
        return []
    ghep = Image.new("RGB", (160, 90 * len(ims)))
    for i, im in enumerate(ims):
        ghep.paste(im, (0, 90 * i))
    q = ghep.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 3 * n]
    dem = sorted(q.getcolors(), key=lambda x: -x[0])
    return ["#%02x%02x%02x" % tuple(pal[3 * k: 3 * k + 3]) for _, k in dem]


def _hoi_kem_anh(prompt, files, timeout=300):
    """Hỏi Gemini KÈM ẢNH theo cài đặt chung (trình duyệt / cookie — common.hoi_kem_tep); không gửi được ảnh thì hỏi chữ
    (AI suy từ tiêu đề + lời thoại)."""
    from common import hoi_kem_tep, hoi_llm
    if files:
        kq = hoi_kem_tep(prompt, files, timeout=timeout)
        if kq:
            return kq, True
    return hoi_llm(prompt + "\n\n(NO IMAGES ATTACHED: infer the visual DNA from titles, tags and transcript, and say so in "
                   "\"ghi_chu\".)", timeout=timeout), False


_P_ADN = """You are a YouTube channel strategist and art director. Reverse-engineer the CHANNEL DNA of «{kenh}» so another
creator can make videos with the SAME look and the SAME storytelling — from REAL evidence only (attached images, titles,
transcript). Do not invent a generic template: every field must describe THIS channel specifically.

ATTACHED IMAGES: {mo_ta_anh}
STATS: {so_video} recent videos, avg {view_tb} views, avg length {dai_tb} s, most viewed: «{tieu_de_viral}» ({view_viral} views).
RECENT TITLES (views):
{tieu_de}

TRANSCRIPT OF THE MOST VIEWED VIDEO ({so_tu} words, {wpm} words/min):
{loi}

Return ONLY JSON (Vietnamese text where marked _vi, English where marked _en):
{{
 "ngach_vi": "the niche and the audience in one sentence",
 "visual_dna": {{
   "art_style_vi": "art style seen in the frames (medium, line work, shading, level of detail, realism)",
   "style_prompt_en": "50-90 words image-generation style prompt reproducing EXACTLY the in-video frames (not the thumbnails). It must state: line quality (clean vector / crude hand-drawn / ink…), how FACES are drawn (realistic / anime / simple meme face with dot eyes…), head-to-body proportion, how detailed backgrounds are, shading (none / cel / soft), color palette, and any collage or photo cut-outs. Style only — no character, no scene",
   "nhan_vat_chinh_vi": "the recurring main character as seen in the frames (or 'không có nhân vật cố định')",
   "nhan_vat_chinh_en": "40-80 words: fixed visual identity of that character (head/face, hair, body proportions, outfit, colors, signature accessories). Identity only — no style words, no scene, no other people",
   "nhan_vat_phu": [{{"ten_vi": "...", "mo_ta_en": "20-40 words"}}],
   "con_roi": {{"than": "que (stick-man thin limbs) | gon (small simple body) | thuong (normal proportions)",
               "dau": "to (oversized head) | vua | nho", "mau_da": "#hex skin color as drawn (pure white for meme faces)",
               "tuoi": "age group of the channel's characters, e.g. 'trẻ 18-30'", "mo_ta_vi": "how the channel's
               characters are drawn in one Vietnamese sentence (proportions, face, body, how emotions are shown)"}},
   "boi_canh_hay_dung_vi": ["typical locations / backgrounds seen or implied (4-8)"],
   "bo_cuc_canh_vi": "how a typical frame is staged: how many characters, how detailed the background is, props, visual metaphors, text overlays, camera framing",
   "bo_cuc_canh_en": "the same as an English instruction for an image generator (30-60 words)",
   "mau_sac_vi": "color palette and mood",
   "negative_en": "what must NEVER appear to stay on-style (comma list)",
   "nhip_hinh_vi": "editing pace: approx seconds per image / shot, motion, transitions"
 }},
 "kich_ban": {{
   "ngoi_ke_vi": "point of view and narrator voice, with evidence",
   "giong_van_vi": "tone, vocabulary, sentence length and rhythm, rhetorical devices actually used",
   "cau_truc_vi": "the beat structure of the video with approximate timing (e.g. 0-10s hook: …; 10-60s: …)",
   "hook_cong_thuc_vi": "the formula of the opening seconds",
   "ky_thuat_giu_chan_vi": ["retention techniques actually used (open loops, questions, reveals…)"],
   "ket_bai_vi": "how videos end (lesson, twist, CTA…)",
   "nhip_ngat_cau_vi": "sentence-length rule observed (e.g. 'câu 5-12 từ, xen câu 2-3 từ để nhấn')",
   "huong_dan_viet_vi": "a 120-200 word Vietnamese STYLE GUIDE instructing a writer to write a NEW script in exactly this voice (no topic, no length)",
   "cau_mau": ["4-6 sentences copied verbatim from the transcript that best show the voice"],
   "tu_huyet_vi": "weaknesses of the channel a competitor can beat"
 }},
 "am_thanh": {{"the_loai_vi": "...", "bpm": "...", "sfx_vi": ["..."], "prompt_suno_en": "..."}},
 "so_canh_tb": <estimated number of images/shots per video>,
 "de_tai_viral": [{{"loai": "...", "tieu_de": "<new Vietnamese title in the channel's title style>", "ly_do": "..."}}] (6 items, derived from the best performing titles),
 "canh_mau": [{{"hinh_vi": "...", "loi": "..."}}] (5 opening scenes of a NEW video in this channel's style),
 "ghi_chu": "what the analysis is based on"
}}"""


def _con_roi_kenh(x):
    """Phong cách nhân vật AI rút từ khung hình -> thông số con_roi hợp lệ."""
    import re
    x = x if isinstance(x, dict) else {}

    def chon(v, ds, md):
        v = str(v or "").strip().lower()
        return next((d for d in ds if v.startswith(d)), md)
    da = str(x.get("mau_da") or "").strip()
    return {"than": chon(x.get("than"), ("que", "gon", "thuong"), "gon"), "dau": chon(x.get("dau"), ("to", "vua", "nho"), "to"),
            "mau_da": da if re.fullmatch(r"#[0-9a-fA-F]{6}", da) else "#fbfaf5",
            "tuoi": str(x.get("tuoi") or "").strip(), "mo_ta_vi": str(x.get("mo_ta_vi") or "").strip()}


def tinh_bao_kenh(danh_sach_kenh, n_vid=10, bao=None):
    """Tình báo & giải mã danh sách kênh đối thủ — 25/10 user: ADN phải lấy TỪ KÊNH THẬT. Bản cũ ghép chuỗi viết sẵn
    (phong cách vẽ đoán theo chữ "lanh/meme" trong tên kênh, cấu trúc 6 nhịp / âm thanh / đề tài giống hệt nhau cho mọi
    kênh, lời thoại không tải được). Nay:
    - Quét n_vid video mới nhất: view trung bình, video nổi nhất.
    - Lời thoại thật của video nổi nhất (phụ đề) -> số từ, tốc độ đọc, câu mở đầu.
    - 6 khung hình rải đều trong video nổi nhất + thumbnail 3 video nổi nhất -> bảng màu (gom cụm) và AI NHÌN ảnh.
    - Một lượt AI (Gemini kèm ảnh): ADN hình ảnh (phong cách, nhân vật chính / phụ, bối cảnh, bố cục cảnh), ADN kịch bản
      (ngôi kể, giọng văn, cấu trúc, hook, câu mẫu, hướng dẫn viết), âm thanh, đề tài, cảnh mẫu -> lưu thành Plugin."""
    from common import rut_json

    ket_qua = []
    tong_kenh = len(danh_sach_kenh)

    for i, kenh_raw in enumerate(danh_sach_kenh):
        kenh_str = str(kenh_raw).strip()
        if not kenh_str:
            continue
        dau = f"[{i + 1}/{tong_kenh}]"
        if bao:
            bao(f"{dau} Đang quét kênh: {kenh_str}…")

        u = _url_kenh(kenh_str)
        j = _chay_json(["--flat-playlist", "--playlist-end", str(int(n_vid)), u], timeout=120)
        entries = j.get("entries") or []
        if not entries:
            u_goc = kenh_str if kenh_str.startswith("http") else f"https://www.youtube.com/{kenh_str.lstrip('/')}"
            j = _chay_json(["--flat-playlist", "--playlist-end", str(int(n_vid)), u_goc], timeout=120)
            entries = j.get("entries") or []
        ids = [e["id"] for e in entries if e and e.get("id")]
        if not ids:
            ket_qua.append({"kenh_input": kenh_str,
                            "loi": "Không đọc được video nào từ kênh này. Hãy kiểm tra lại link hoặc @handle."})
            continue

        if bao:
            bao(f"{dau} Đang đọc chi tiết {len(ids)} video của {kenh_str}…")
        chi_tiet_ds = _doc_nhieu(ids, bao=None)
        if not chi_tiet_ds:
            ket_qua.append({"kenh_input": kenh_str, "loi": "Không đọc được chi tiết video nào của kênh."})
            continue

        kenh_ten = chi_tiet_ds[0].get("kenh") or j.get("title") or kenh_str
        sub_count = chi_tiet_ds[0].get("sub") or 0
        kenh_url = chi_tiet_ds[0].get("kenh_url") or u
        view_tb = int(sum(v.get("view") or 0 for v in chi_tiet_ds) / max(1, len(chi_tiet_ds)))
        chi_tiet_ds.sort(key=lambda x: -(x.get("view") or 0))
        top_video = chi_tiet_ds[0]
        top_video["he_so_viral"] = round(top_video["view"] / max(1, view_tb), 2)
        tieu_de = top_video.get("tieu_de", "")

        # --- lời thoại thật
        if bao:
            bao(f"{dau} Tải lời thoại video nổi nhất: «{tieu_de[:40]}»…")
        loi = _tai_phu_de(top_video["id"])
        tong_tu = sum(len(l.split()) for l in loi)
        dai_viral = int(top_video.get("dai") or 0)
        dai_cac = [int(v.get("dai") or 0) for v in chi_tiet_ds if (v.get("dai") or 0) > 0]
        thoi_luong_tb = int(sum(dai_cac) / len(dai_cac)) if dai_cac else (dai_viral or 180)
        wpm = int(tong_tu / dai_viral * 60) if tong_tu > 50 and dai_viral > 30 else 160
        so_tu_tb = max(120, int(thoi_luong_tb * wpm / 60))

        # --- hình ảnh thật: khung hình trong video + thumbnail
        if bao:
            bao(f"{dau} Lấy khung hình trong video nổi nhất để đọc ADN hình ảnh…")
        khung = _khung_hinh(top_video["id"], dai_viral)
        # 27/10: học cách minh hoạ chạy NỀN, cùng lúc với câu hỏi ADN bên dưới (hai việc không phụ thuộc nhau)
        ex_mh = ThreadPoolExecutor(1)
        tuong_lai_mh = ex_mh.submit(_thu_vien_minh_hoa, top_video["id"], (lambda m: bao(f"{dau} {m}")) if bao else None)
        thu_anh = os.path.join(CACHE_CHUNG, "doi_thu", "khung")
        os.makedirs(thu_anh, exist_ok=True)
        thumbs = [t for t in (_tai_anh(f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg", os.path.join(thu_anh, f"{v['id']}_thumb.jpg"))
                              for v in chi_tiet_ds[:3]) if t]
        palette = _bang_mau(khung or thumbs) or ["#121418", "#000000", "#f2b588", "#38bdf8", "#ef4444"]
        files = khung + thumbs
        mo_ta_anh = (f"{len(khung)} frames evenly spread through the most viewed video" if khung else "no video frames")
        mo_ta_anh += f", then {len(thumbs)} thumbnails of the top videos (thumbnails exaggerate — trust the frames for the in-video style)."
        mo_ta_anh += f" Dominant colors measured on the frames: {', '.join(palette)}."

        if bao:
            bao(f"{dau} AI đang phân tích ADN kênh ({len(files)} ảnh, {tong_tu} từ lời thoại)…")
        ds_td = "\n".join(f"- {v.get('tieu_de', '')} ({v.get('view') or 0:,} views)" for v in chi_tiet_ds[:30])
        p = _P_ADN.format(kenh=kenh_ten, mo_ta_anh=mo_ta_anh, so_video=len(chi_tiet_ds), view_tb=f"{view_tb:,}",
                          dai_tb=thoi_luong_tb, tieu_de_viral=tieu_de, view_viral=f"{top_video.get('view') or 0:,}",
                          tieu_de=ds_td, so_tu=tong_tu, wpm=wpm,
                          loi=("\n".join(loi))[:9000] or "(no transcript available — infer from titles)")
        adn, co_anh = {}, False
        for _ in range(2):
            kq, co_anh = _hoi_kem_anh(p, files)
            adn = rut_json(kq or "")
            if isinstance(adn, dict) and adn.get("visual_dna"):
                break
        try:
            minh_hoa = tuong_lai_mh.result()
        except Exception as e:                               # noqa: BLE001
            log(f"    ! học cách minh hoạ {top_video['id']}: {str(e)[:100]}")
            minh_hoa = {}
        finally:
            ex_mh.shutdown(wait=False)
        if not isinstance(adn, dict) or not adn.get("visual_dna"):
            ket_qua.append({"kenh_input": kenh_str, "kenh_ten": kenh_ten, "loi": "AI không trả phân tích ADN (thử lại)."})
            continue
        vd, kb, am = adn.get("visual_dna") or {}, adn.get("kich_ban") or {}, adn.get("am_thanh") or {}

        def s(x):
            return str(x or "").strip()
        style_en = s(vd.get("style_prompt_en"))
        nv_en = s(vd.get("nhan_vat_chinh_en"))
        so_canh = int(adn.get("so_canh_tb") or 0) or max(10, min(60, int(thoi_luong_tb / 6)))
        canh_mau = [c for c in adn.get("canh_mau") or [] if isinstance(c, dict)]
        super_script = (f"# CẢM HỨNG TỪ: {kenh_ten} - {tieu_de}\n# ĐỘ DÀI: ~{so_tu_tb} từ (~{round(thoi_luong_tb / 60, 1)} phút)"
                        f" | PHONG CÁCH: {s(vd.get('art_style_vi'))}\n\n"
                        + "\n\n".join(f"--- CẢNH {k + 1:02d}\nHÌNH: {s(c.get('hinh_vi'))}\nTEXT_NARRATOR: \"{s(c.get('loi'))}\""
                                      for k, c in enumerate(canh_mau)))
        kenh_data = {
            "kenh_input": kenh_str,
            "kenh_ten": kenh_ten,
            "kenh_url": kenh_url,
            "sub": sub_count,
            "tong_video_quet": len(chi_tiet_ds),
            "view_tb": view_tb,
            "video_viral": top_video,
            "bang_mau": palette,
            "ngach": s(adn.get("ngach_vi")),
            "co_anh": co_anh,
            "ghi_chu": s(adn.get("ghi_chu")),
            "chi_so_kich_ban": {"so_tu_tb": so_tu_tb, "thoi_luong_tb_giay": thoi_luong_tb,
                                "thoi_luong_tb_phut": round(thoi_luong_tb / 60, 1), "toc_do_wpm": wpm, "so_tu_viral": tong_tu},
            "cach_trien_khai": {"cau_truc_mach_truyen": s(kb.get("cau_truc_vi")), "so_canh_tb": so_canh,
                                "nhip_ngat_cau": s(kb.get("nhip_ngat_cau_vi"))},
            "giai_ma_kich_ban": {
                "hook_30s": " ".join(loi[:15]) or s(kb.get("hook_cong_thuc_vi")),
                "hook_cong_thuc": s(kb.get("hook_cong_thuc_vi")),
                "ngoi_ke": s(kb.get("ngoi_ke_vi")),
                "giong_van": s(kb.get("giong_van_vi")),
                "nhip_cam_xuc": s(kb.get("cau_truc_vi")),
                "ky_thuat_giu_chan": [s(x) for x in kb.get("ky_thuat_giu_chan_vi") or [] if s(x)],
                "ket_bai": s(kb.get("ket_bai_vi")),
                "cau_mau": [s(x) for x in kb.get("cau_mau") or [] if s(x)][:6],
                "tu_huyet_doi_thu": s(kb.get("tu_huyet_vi")),
            },
            "visual_dna": {
                "art_style": s(vd.get("art_style_vi")),
                "style_prompt_en": style_en,
                "dac_diem_nv": s(vd.get("nhan_vat_chinh_vi")),
                "nhan_vat_chinh_en": nv_en,
                "nhan_vat_phu": [x for x in vd.get("nhan_vat_phu") or [] if isinstance(x, dict)],
                "con_roi": _con_roi_kenh(vd.get("con_roi")),
                "boi_canh_hay_dung": [s(x) for x in vd.get("boi_canh_hay_dung_vi") or [] if s(x)],
                "bo_cuc_canh": s(vd.get("bo_cuc_canh_vi")),
                "bo_cuc_canh_en": s(vd.get("bo_cuc_canh_en")),
                "mau_sac": s(vd.get("mau_sac_vi")),
                "nhip_hinh": s(vd.get("nhip_hinh_vi")),
                "bang_mau": palette,
                "prompt_tao_anh": ". ".join(x for x in (style_en, nv_en) if x),
                "negative_prompt": s(vd.get("negative_en")),
                "khung_hinh": khung,
                "minh_hoa": minh_hoa,
            },
            "am_thanh": {"the_loai": s(am.get("the_loai_vi")), "bpm": s(am.get("bpm")),
                         "sfx": [s(x) for x in am.get("sfx_vi") or [] if s(x)], "prompt_suno": s(am.get("prompt_suno_en"))},
            "master_prompts": {"script_prompt": s(kb.get("huong_dan_viet_vi")), "image_prompt": ". ".join(x for x in (style_en, nv_en) if x),
                               "audio_prompt": s(am.get("prompt_suno_en"))},
            "de_tai_viral": [x for x in adn.get("de_tai_viral") or [] if isinstance(x, dict) and x.get("tieu_de")],
            "super_script": super_script,
        }
        try:
            pl = tao_plugin_kenh(kenh_data)
            luu_plugin_kenh(pl)
            kenh_data["plugin_id"] = pl["id"]
        except Exception as e:                               # noqa: BLE001
            log(f"    ! Lưu plugin kênh {kenh_ten}: {e}")
        ket_qua.append(kenh_data)

    if bao:
        bao(f"Đã hoàn thành tình báo {len(ket_qua)} kênh và tự động lưu thành bộ Plugin!")
    return {"tong_kenh": len(ket_qua), "ds": ket_qua}


# =============================================================================
# BỘ PLUGIN KÊNH ĐỐI THỦ & VIẾT LẠI KỊCH BẢN GIỮ CỐT LÕI
# =============================================================================

def tao_plugin_kenh(k):
    """Đóng gói dữ liệu phân tích thành một bộ Plugin hoàn chỉnh cho 1 kênh."""
    ten = k.get("kenh_ten") or k.get("kenh_input") or "kenh_doi_thu"
    pid = _slug(ten)
    v = k.get("video_viral") or {}
    pal = k.get("bang_mau") or ["#121418", "#000000", "#f2b588", "#38bdf8", "#ef4444"]
    cs = k.get("chi_so_kich_ban") or {
        "so_tu_tb": 480,
        "thoi_luong_tb_giay": 180,
        "thoi_luong_tb_phut": 3.0,
        "toc_do_wpm": 160,
        "so_tu_viral": 450
    }
    ctk = k.get("cach_trien_khai") or {
        "cau_truc_mach_truyen": "6 nhịp kinh điển: Hook 3s -> Mồi nhử cám dỗ -> Trượt dốc -> Đổ vỡ -> Thức tỉnh -> Bài học",
        "so_canh_tb": 20,
        "nhip_ngat_cau": "Dưới 8 từ mỗi câu, ngắt bằng dấu chấm"
    }
    vd = k.get("visual_dna") or {}
    gm = k.get("giai_ma_kich_ban") or {}

    return {
        "id": pid,
        "kenh_ten": ten,
        "kenh_url": k.get("kenh_url") or "",
        "thumb": v.get("anh") or "",
        "sub": k.get("sub") or 0,
        "view_tb": k.get("view_tb") or 0,
        "ngay_tao": datetime.now(VN).strftime("%d/%m/%Y %H:%M"),
        "chi_so_kich_ban": cs,
        "cach_trien_khai": ctk,
        "de_tai_viral": k.get("de_tai_viral") or [],
        "ngach": k.get("ngach") or "",
        "minh_hoa": vd.get("minh_hoa") or {},          # cách kênh minh hoạ từng loại câu (storyboard dùng làm mẫu)
        "nhan_vat": {
            # 25/10: chỉ NHẬN DẠNG nhân vật (không lẫn phong cách / cảnh) — storyboard dán vào ô "nhân vật đồng nhất"
            "prompt_nhan_vat": vd.get("nhan_vat_chinh_en") or vd.get("prompt_tao_anh") or k.get("master_prompts", {}).get("image_prompt") or "",
            "negative_prompt": vd.get("negative_prompt") or "",
            "dac_diem": vd.get("dac_diem_nv") or "Nhân vật đồng nhất theo phong cách kênh",
            "nhan_vat_phu": vd.get("nhan_vat_phu") or [],
            # 25/10 user: PHONG CÁCH nhân vật của kênh (dáng thân, cỡ đầu, màu da, độ tuổi) cho phôi con rối — không chép
            # nhân vật cụ thể của kênh, không để AI tự nghĩ người theo kịch bản
            "con_roi": vd.get("con_roi") or {}
        },
        "boi_canh": {
            "art_style": vd.get("style_prompt_en") or vd.get("art_style") or "",     # câu lệnh phong cách (tiếng Anh)
            "art_style_vi": vd.get("art_style") or "",
            "bang_mau": pal,
            "khong_gian": "; ".join(vd.get("boi_canh_hay_dung") or []),
            "bo_cuc_canh": vd.get("bo_cuc_canh") or "",
            "bo_cuc_canh_en": vd.get("bo_cuc_canh_en") or "",
            "khung_hinh": vd.get("khung_hinh") or [],     # khung hình thật của kênh: storyboard gắn làm tham chiếu phong cách
            "nhip_hinh": vd.get("nhip_hinh") or ""
        },
        "kich_ban": {
            "ngoi_ke": gm.get("ngoi_ke") or "",
            "giong_van": gm.get("giong_van") or "",
            "nhip_cam_xuc": gm.get("nhip_cam_xuc") or "",
            "hook_mau": gm.get("hook_30s") or "",
            "hook_cong_thuc": gm.get("hook_cong_thuc") or "",
            "ky_thuat_giu_chan": gm.get("ky_thuat_giu_chan") or [],
            "ket_bai": gm.get("ket_bai") or "",
            "cau_mau": gm.get("cau_mau") or [],
            "prompt_viet": k.get("master_prompts", {}).get("script_prompt") or "",   # hướng dẫn giọng văn (sửa được)
            "super_script": k.get("super_script") or ""
        },
        "am_thanh": {
            "the_loai": k.get("am_thanh", {}).get("the_loai") or "",
            "bpm": k.get("am_thanh", {}).get("bpm") or "",
            "sfx": k.get("am_thanh", {}).get("sfx") or [],
            "prompt_suno": k.get("am_thanh", {}).get("prompt_suno") or ""
        }
    }


def luu_plugin_kenh(plugin):
    """Lưu bộ Plugin của kênh vào thư mục plugins_doi_thu/<id>.json."""
    os.makedirs(THU_MUC_PLUGIN, exist_ok=True)
    pid = plugin.get("id") or _slug(plugin.get("kenh_ten") or "plugin_kenh")
    plugin["id"] = pid
    p = os.path.join(THU_MUC_PLUGIN, f"{pid}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(plugin, f, ensure_ascii=False, indent=2)
    return plugin


def danh_sach_plugins():
    """Lấy danh sách tất cả các bộ Plugin kênh đã lưu."""
    os.makedirs(THU_MUC_PLUGIN, exist_ok=True)
    ra = []
    for f in os.listdir(THU_MUC_PLUGIN):
        if f.endswith(".json"):
            p = os.path.join(THU_MUC_PLUGIN, f)
            try:
                with open(p, encoding="utf-8") as fp:
                    j = json.load(fp)
                    if isinstance(j, dict) and j.get("id"):
                        ra.append(j)
            except Exception:
                pass
    ra.sort(key=lambda x: str(x.get("ngay_tao") or ""), reverse=True)
    return ra


def xoa_plugin_kenh(pid):
    """Xóa bộ Plugin của kênh."""
    p = os.path.join(THU_MUC_PLUGIN, f"{pid}.json")
    if os.path.isfile(p):
        os.remove(p)
        return True
    return False


def lam_sach_van_doc(text):
    """Làm sạch triệt để văn bản kịch bản để đạt chuẩn THUẦN ĐỌC:
    - Xóa mọi icon, emoji, ký hiệu minh họa.
    - Xóa các thẻ phân cảnh cũ: --- CẢNH 01, HÌNH:, BGM:, SFX:, HUD:, TEXT_NARRATOR:, TEXT_SHADOW:...
    - Xóa các nhãn tiêu đề phân đoạn: Phần 1:, Hồi 1:, Chương 1:, ###...
    - Ghép thành văn xuôi liên tục, giữ nhịp ngắt câu tự nhiên để đọc thu âm / TTS.
    """
    if not text:
        return ""
    import re

    # 1. Xóa emoji và icon unicode
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b00-\u2bff\u3030\u303d\u00a9\u00ae\u2122\ufe0f]+",
        flags=re.UNICODE,
    )
    t = emoji_pattern.sub("", text)

    lines = []
    for raw_line in t.split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue

        # Bỏ qua các dòng phân cảnh kiểu cũ
        if re.match(r"^---*\s*(CẢNH|SCENE|HỒI|PHẦN|CHƯƠNG)\b", line, re.IGNORECASE):
            continue
        if re.match(r"^(HÌNH|HUD|BGM|SFX|TEXT_SHADOW|HÌNH ẢNH|ÂM THANH|HIỆU ỨNG|TIÊU ĐỀ|DÀN BÀI)\s*:", line, re.IGNORECASE):
            continue

        # Nếu có TEXT_NARRATOR: "..." hoặc LỜI BÌNH: "..." -> chỉ trích xuất phần lời thoại bên trong
        m_nar = re.match(r"^(TEXT_NARRATOR|LỜI THOẠI|LỜI BÌNH|NARRATOR|VOICEOVER)\s*:\s*[\"“]?(.*?)[\"”]?$", line, re.IGNORECASE)
        if m_nar and m_nar.group(2):
            lines.append(m_nar.group(2).strip())
            continue

        # Bỏ qua các tiêu đề markdown hoặc nhãn phần: # Phần 1, Hồi 1, Đoạn 1...
        if re.match(r"^(#{1,6}\s+|(?:\*{1,2})?(?:Hồi|Phần|Chương|Đoạn)\s+\d+[:\.]?|(?:\*{1,2})?(?:Mở đầu|Thân bài|Kết bài|Hook|Kêu gọi)[:\.]?)", line, re.IGNORECASE):
            continue

        # Bỏ các dấu gạch đầu dòng danh sách nếu AI trả về dạng bullet point
        if line.startswith("- ") or line.startswith("* "):
            line = line[2:].strip()

        # Bỏ dấu ngoặc kép bọc cả dòng
        if (line.startswith('"') and line.endswith('"')) or (line.startswith('“') and line.endswith('”')):
            line = line[1:-1].strip()

        lines.append(line)

    cleaned = "\n".join(lines)
    # Rút gọn các dòng trống liên tiếp thành tối đa 1 dòng trống
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def phan_tich_dan_bai_text(dan_bai_text, so_tu_tong=500):
    """Tách dàn bài text thành danh sách các phần để xử lý AI theo từng chặng."""
    import re
    blocks = re.split(r"(?i)(?:^|\n)(?:PHẦN|HỒI|CHƯƠNG)\s*(\d+)[:\.\-]", dan_bai_text.strip())
    parts = []
    if len(blocks) >= 3:
        for i in range(1, len(blocks), 2):
            num = int(blocks[i])
            content = blocks[i+1].strip()
            c_lines = [l for l in content.split("\n") if l.strip()]
            first_line = c_lines[0] if c_lines else f"Phần {num}"
            m_tu = re.search(r"~(\d+)\s*từ", first_line)
            w = int(m_tu.group(1)) if m_tu else 0
            title = re.sub(r"\(~?\d+\s*từ\)", "", first_line).strip(" :-–—")
            body = "\n".join(c_lines[1:]).strip() if len(c_lines) > 1 else first_line
            parts.append({
                "phan": num,
                "tieu_de": title or f"Phần {num}",
                "so_tu": w,
                "muc_tieu": body
            })

    if not parts:
        lines = [l.strip() for l in dan_bai_text.split("\n") if l.strip() and not l.strip().startswith("#")]
        if not lines:
            lines = ["Mở đầu câu chuyện và Hook", "Diễn biến cao trào biến cố", "Thức tỉnh và bài học đắt giá"]
        part_w = max(150, int(so_tu_tong / len(lines)))
        for idx, l in enumerate(lines, 1):
            parts.append({
                "phan": idx,
                "tieu_de": l[:60],
                "so_tu": part_w,
                "muc_tieu": l
            })

    # Cân đối số từ nếu các phần chưa có số từ cụ thể
    so_tu_tong_thuc = sum(p.get("so_tu") or 0 for p in parts)
    if so_tu_tong_thuc <= 0:
        part_w = max(150, int(so_tu_tong / len(parts)))
        for p in parts:
            p["so_tu"] = part_w
    return parts


def _phong_cach_viet(pl):
    """Khối "ADN giọng văn" của kênh dùng chung cho lập dàn bài / viết mới / viết lại.
    25/10: plugin cũ để trong prompt_viet cả "chủ đề tương tự video X" và "Độ dài khoảng N từ" -> bài viết mới bị kéo về
    chủ đề video gốc và sai độ dài: bỏ các câu đó, chỉ giữ hướng dẫn giọng văn."""
    import re
    kb = pl.get("kich_ban") or {}
    ctk = pl.get("cach_trien_khai") or {}
    pv = " ".join(c for c in re.split(r"(?<=[.!?])\s+", str(kb.get("prompt_viet") or ""))
                  if not re.search(r"(?i)độ dài|chủ đề tương tự|nối tiếp video|đóng vai", c))
    dong = [("Ngôi kể", kb.get("ngoi_ke")), ("Giọng văn", kb.get("giong_van")), ("Hướng dẫn giọng văn", pv),
            ("Cấu trúc mạch truyện của kênh", ctk.get("cau_truc_mach_truyen")), ("Nhịp cảm xúc", kb.get("nhip_cam_xuc")),
            ("Công thức mở đầu (hook)", kb.get("hook_cong_thuc")),
            ("Kỹ thuật giữ chân", "; ".join(kb.get("ky_thuat_giu_chan") or [])), ("Cách kết bài", kb.get("ket_bai")),
            ("Nhịp câu", ctk.get("nhip_ngat_cau"))]
    ra, da = [], set()
    for t, v in dong:                                        # plugin mới: nhịp cảm xúc = cấu trúc -> không lặp
        v = str(v or "").strip()
        if v and v not in da:
            da.add(v)
            ra.append(f"- {t}: {v}")
    ra = "\n".join(ra)
    mau = [str(x).strip() for x in kb.get("cau_mau") or [] if str(x).strip()]
    if mau:
        ra += "\n- Câu mẫu đúng giọng kênh (chỉ học GIỌNG, KHÔNG chép nội dung):\n" + "\n".join(f"  «{x}»" for x in mau[:6])
    return ra or "- Giọng kể tự nhiên, câu ngắn gọn, cụ thể, gắn với hành động và chi tiết đời thực."


# 26/10 user: "tôi có ADN của đối thủ rồi nhưng tôi chưa có ý tưởng tiêu đề và viết dàn bài từ ý tưởng đấy thì sao?" —
# trước đây chỉ có "đề tài viral phái sinh" = đưa lại chính tiêu đề của đối thủ. Nay AI nghĩ ý tưởng MỚI theo ADN
# (ngách, công thức hook / tiêu đề, cấu trúc mạch truyện, đề tài từng viral làm mẫu), mỗi ý tưởng kèm góc khai thác,
# câu mở đầu và lý do ăn view; bấm chọn -> điền tiêu đề -> "Bước 1: Lập dàn bài" như cũ.
_P_Y_TUONG = """Bạn là trưởng nhóm nội dung của một kênh YouTube muốn cạnh tranh trực tiếp với kênh «{kenh}».
Dưới đây là ADN của kênh đó. Hãy nghĩ {n} Ý TƯỞNG VIDEO MỚI mà khán giả của kênh này chắc chắn muốn bấm xem.

NGÁCH & KHÁN GIẢ: {ngach}
ADN KỊCH BẢN:
{adn}
CẤU TRÚC MẠCH TRUYỆN: {mach}
ĐỀ TÀI ĐÃ VIRAL CỦA KÊNH (chỉ để học CÔNG THỨC tiêu đề và loại đề tài ăn view — KHÔNG chép, KHÔNG đổi vài chữ):
{viral}
{goi_y}
YÊU CẦU:
- Mỗi ý tưởng là một đề tài KHÁC HẲN các tiêu đề trên (đối tượng, nghề, tình huống, con số khác), nhưng cùng ngách và
  cùng kiểu cảm xúc khiến khán giả kênh này bấm xem.
- Tiêu đề viết theo ĐÚNG công thức tiêu đề của kênh (cách viết hoa, dấu hai chấm, câu hỏi, con số cụ thể…), tiếng Việt,
  dưới 100 ký tự, gây tò mò nhưng không lừa.
- Trải đều nhiều kiểu: mổ xẻ một con số / mô hình, đảo ngược định kiến, câu chuyện một nhân vật, danh sách sai lầm,
  so sánh hai lựa chọn, bí mật ngành nghề… (theo những kiểu kênh này làm được).
- Ưu tiên đề tài làm được bằng ảnh minh hoạ / hoạt hình (không cần quay thực tế), hợp thời điểm hiện tại.
- Không dùng emoji.

Chỉ trả JSON: [{{"tieu_de": "...", "loai": "kiểu đề tài (2-5 chữ)", "goc_khai_thac": "1 câu: đào vào khía cạnh nào",
"hook": "câu mở đầu video (dưới 25 chữ, theo công thức hook của kênh)", "vi_sao": "1 câu: vì sao khán giả kênh này sẽ bấm",
"diem": số 1-10 khả năng viral}}]"""


def _gan_giong(a, b):
    """Hai tiêu đề gần như trùng (tỉ lệ từ chung) — lọc ý tưởng AI chỉ đổi vài chữ của tiêu đề đối thủ."""
    import re
    ta, tb = (set(re.findall(r"\w+", str(x).lower())) for x in (a, b))
    return bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) > 0.7


def goi_y_y_tuong(plugin_data, goi_y="", n=10, bao=None):
    """Ý tưởng video MỚI theo ADN kênh -> [{tieu_de, loai, goc_khai_thac, hook, vi_sao, diem}] (điểm cao trước)."""
    from common import hoi_llm, rut_json
    p = plugin_data or {}
    viral = [x for x in p.get("de_tai_viral") or [] if isinstance(x, dict) and x.get("tieu_de")]
    goc = [x["tieu_de"] for x in viral]
    prompt = _P_Y_TUONG.format(
        kenh=p.get("kenh_ten") or "đối thủ", n=n, ngach=p.get("ngach") or "(xem ADN)", adn=_phong_cach_viet(p),
        mach=(p.get("cach_trien_khai") or {}).get("cau_truc_mach_truyen") or "",
        viral="\n".join(f"- «{x['tieu_de']}» ({x.get('loai') or ''}: {x.get('ly_do') or ''})" for x in viral[:12]) or "(chưa có)",
        goi_y=(f"\nNGƯỜI DÙNG MUỐN Ý TƯỞNG XOAY QUANH: «{goi_y.strip()}» — mọi ý tưởng phải bám chủ đề này.\n"
               if str(goi_y or "").strip() else ""))
    if bao:
        bao(f"AI đang nghĩ {n} ý tưởng mới theo ADN «{p.get('kenh_ten') or 'kênh'}»…")
    ra = []
    for _ in range(2):
        j = rut_json(hoi_llm(prompt, timeout=180) or "")
        for x in j if isinstance(j, list) else []:
            t = str((x or {}).get("tieu_de") or "").strip() if isinstance(x, dict) else ""
            if not t or any(_gan_giong(t, g) for g in goc) or any(_gan_giong(t, y["tieu_de"]) for y in ra):
                continue
            try:
                diem = max(1, min(10, int(float(x.get("diem") or 5))))
            except (TypeError, ValueError):
                diem = 5
            ra.append({"tieu_de": t, "loai": str(x.get("loai") or "").strip(), "goc_khai_thac": str(x.get("goc_khai_thac") or "").strip(),
                       "hook": str(x.get("hook") or "").strip(), "vi_sao": str(x.get("vi_sao") or "").strip(), "diem": diem})
        if len(ra) >= max(3, n // 2):
            break
        if bao:
            bao("  AI trả ít ý tưởng dùng được (trùng tiêu đề đối thủ) — hỏi lại…")
    if not ra:
        raise ValueError("AI không trả ý tưởng nào dùng được (thử lại)")
    return {"y_tuong": sorted(ra, key=lambda y: -y["diem"])}


def _y_tuong_them(y):
    """Góc khai thác + hook của ý tưởng đã chọn (bước 💡) -> dòng thêm cho câu lệnh lập dàn bài."""
    if not isinstance(y, dict):
        return ""
    dong = [f"- Góc khai thác đã chọn: {y['goc_khai_thac']}" if y.get("goc_khai_thac") else "",
            f"- Câu mở đầu (hook) đã chọn, dùng làm câu đầu của PHẦN 1: «{y['hook']}»" if y.get("hook") else ""]
    dong = [d for d in dong if d]
    return ("\nÝ TƯỞNG ĐÃ CHỌN (dàn bài phải đi đúng hướng này):\n" + "\n".join(dong) + "\n") if dong else ""


def lap_dan_bai_kenh(tieu_de, plugin_data, so_tu_mong_muon=None, bao=None, y_tuong=None):
    """Bước 1: Lên DÀN BÀI kịch bản theo phong cách triển khai của kênh đối thủ.
    Phân chia thành N phần với số từ định danh cho từng phần khớp với số từ mong muốn.
    """
    from common import hoi_llm
    prompt, so_phan, so_tu_chuan, kenh_ten = cau_lenh_dan_bai(tieu_de, plugin_data, so_tu_mong_muon, y_tuong)
    if bao:
        bao(f"Đang lên dàn bài {so_phan} phần ({so_tu_chuan} từ) theo phong cách {kenh_ten}…")
    kq = hoi_llm(prompt, timeout=120)
    if not kq or len(kq.strip()) < 30:
        raise ValueError("AI không phản hồi dàn bài. Vui lòng thử lại.")
    return doc_dan_bai(kq, tieu_de, so_tu_chuan)


def doc_dan_bai(kq, tieu_de, so_tu_chuan):
    """Chữ dàn bài AI trả -> {tieu_de, so_tu_tong, so_phan, danh_sach_phan, dan_bai_text}."""
    # 25/10: KHÔNG qua lam_sach_van_doc — nó xoá dòng "PHẦN 1: …" (nhãn phần) nên dàn bài luôn tách sai
    import re
    dan_bai_text = re.sub(r"(?m)^[#* \t]+(?=(PHẦN|Phần|HỒI|CHƯƠNG)\s*\d)", "", kq.strip()).replace("**", "")
    ds_phan = phan_tich_dan_bai_text(dan_bai_text, so_tu_chuan)
    return {
        "tieu_de": str(tieu_de or "").strip(),
        "so_tu_tong": so_tu_chuan,
        "so_phan": len(ds_phan),
        "danh_sach_phan": ds_phan,
        "dan_bai_text": dan_bai_text
    }


def cau_lenh_dan_bai(tieu_de, plugin_data, so_tu_mong_muon=None, y_tuong=None):
    """Câu lệnh lập dàn bài theo ADN kênh -> (prompt, số phần, tổng số từ, tên kênh)."""
    tieu_de_raw = str(tieu_de or "").strip()
    if not tieu_de_raw:
        raise ValueError("Chưa nhập tiêu đề hoặc ý tưởng kịch bản mới")

    kenh_ten = plugin_data.get("kenh_ten", "Kênh đối thủ")
    cs = plugin_data.get("chi_so_kich_ban") or {}
    so_tu_chuan = int(so_tu_mong_muon or cs.get("so_tu_tb") or 500)

    # Tính số phần tối ưu (mỗi phần từ 250 - 450 từ)
    if so_tu_chuan <= 450:
        so_phan = 2
    elif so_tu_chuan <= 850:
        so_phan = 3
    elif so_tu_chuan <= 1350:
        so_phan = 4
    elif so_tu_chuan <= 1900:
        so_phan = 5
    else:
        so_phan = min(8, max(5, round(so_tu_chuan / 350)))

    w_per_part = int(so_tu_chuan / so_phan)

    prompt = f"""Bạn là một chuyên gia biên kịch video YouTube triệu view hàng đầu.
NHIỆM VỤ:
Từ TIÊU ĐỀ / ĐỀ TÀI dưới đây, hãy áp dụng CÁCH TRIỂN KHAI VÀ PHONG CÁCH KỂ CHUYỆN của kênh «{kenh_ten}» để lập một DÀN BÀI CHI TIẾT gồm ĐÚNG {so_phan} PHẦN.

ADN KỊCH BẢN CỦA KÊNH (phân bổ các phần theo đúng cấu trúc mạch truyện này):
{_phong_cach_viet(plugin_data)}
- Tổng số từ mục tiêu của cả bài hoàn chỉnh: {so_tu_chuan} TỪ.

TIÊU ĐỀ / ĐỀ TÀI:
«{tieu_de_raw}»
{_y_tuong_them(y_tuong)}
YÊU CẦU ĐẶC BIỆT KHI LÊN DÀN BÀI:
1. Chia thành ĐÚNG {so_phan} PHẦN. Tổng số từ của các phần phải cộng lại đúng bằng ~{so_tu_chuan} từ (mỗi phần xấp xỉ ~{w_per_part} từ).
2. Từng phần phải có logic nhân quả chặt chẽ, cuốn hút, mạch lạc xuyên suốt, không đứt đoạn.
3. TUYỆT ĐỐI KHÔNG dùng bất kỳ ICON hay EMOJI nào.
4. Trả về đúng theo cấu trúc chuẩn bên dưới để phần mềm tự động xử lý:

PHẦN 1: [Tiêu đề phần 1] (~[số từ] từ)
- Mục tiêu: [Mô tả chi tiết xung đột, diễn biến và ý đồ tâm lý cần viết ở phần này...]

PHẦN 2: [Tiêu đề phần 2] (~[số từ] từ)
- Mục tiêu: [Mô tả chi tiết xung đột, diễn biến và ý đồ tâm lý cần viết ở phần này...]
... (tiếp tục cho đến hết PHẦN {so_phan})

CHỈ TRẢ VỀ DANH SÁCH CÁC PHẦN TRÊN, KHÔNG CÓ LỜI CHÀO HAY DẪN DẮT NGOÀI LỀ.
"""
    return prompt, so_phan, so_tu_chuan, kenh_ten


def viet_kich_ban_tung_phan(tieu_de, dan_bai_input, plugin_data, so_tu_muc_tieu=None, bao=None):
    """Bước 2: Chấp bút kịch bản theo từng phần của dàn bài để vượt qua giới hạn từ của AI,
    sau đó ghép nối thành 1 bài viết hoàn chỉnh thuần để đọc, không chia từng phần, không dùng icon.
    """
    from common import hoi_llm
    tieu_de_raw = str(tieu_de or "").strip()
    kenh_ten = plugin_data.get("kenh_ten", "Kênh đối thủ")
    phong_cach = _phong_cach_viet(plugin_data)

    # Phân tích dàn bài
    if isinstance(dan_bai_input, dict) and dan_bai_input.get("danh_sach_phan"):
        ds_phan = dan_bai_input["danh_sach_phan"]
        so_tu_tong = dan_bai_input.get("so_tu_tong") or so_tu_muc_tieu or 500
    elif isinstance(dan_bai_input, str):
        so_tu_tong = so_tu_muc_tieu or 500
        ds_phan = phan_tich_dan_bai_text(dan_bai_input, so_tu_tong)
    else:
        raise ValueError("Dàn bài không hợp lệ")

    if not ds_phan:
        raise ValueError("Không tìm thấy các phần trong dàn bài để viết")

    tong_phan = len(ds_phan)
    cac_doan_viet = []
    dan_bai_tom = "\n".join(f"  Phần {k}: {p.get('tieu_de') or ''} — {str(p.get('muc_tieu') or '')[:160]}"
                             for k, p in enumerate(ds_phan, 1))

    for idx, p in enumerate(ds_phan, 1):
        p_title = p.get("tieu_de") or f"Phần {idx}"
        p_words = int(p.get("so_tu") or int(so_tu_tong / tong_phan))
        p_goal = p.get("muc_tieu") or ""

        if bao:
            bao(f"Đang viết phần {idx}/{tong_phan}: «{p_title}» (Mục tiêu ~{p_words} từ)…", idx, tong_phan)

        prompt_part = f"""Bạn là bậc thầy biên kịch video voiceover triệu view trên YouTube, đang chấp bút kịch bản nói (lời bình / narration) thuần để đọc.

ADN GIỌNG VĂN KÊNH «{kenh_ten}» (BẮT BUỘC TUÂN THỦ TRIỆT ĐỂ):
{phong_cach}
- Không dùng từ ngữ sáo rỗng. Mọi tâm trạng phải được cụ thể hóa qua hành vi và tình huống đời thực (để dựng hình được).

DÀN BÀI TOÀN BÀI (để biết phần này nằm ở đâu trong mạch truyện):
{dan_bai_tom}

THÔNG TIN BÀI VIẾT:
- Đề tài kịch bản: «{tieu_de_raw}»
- Bạn đang viết: PHẦN {idx}/{tong_phan}: «{p_title}»
- Mục tiêu nội dung cần viết sâu ở phần này:
{p_goal}

- ĐỘ DÀI LỜI ĐỌC CỦA PHẦN NÀY: BẮT BUỘC XẤP XỈ ~{p_words} TỪ (tối thiểu {int(p_words * 0.85)} từ, tối đa {int(p_words * 1.15)} từ). Viết thật kỹ lưỡng, sâu sắc, lôi cuốn, không viết lướt qua hay tóm tắt ngắn ngủn.
"""

        if idx > 1 and cac_doan_viet:
            # Lấy khoảng 150 từ cuối của phần trước để đảm bảo tính liên tục tuyệt đối
            doan_truoc = " ".join(cac_doan_viet[-1].split()[-150:])
            prompt_part += f"""
---
ĐOẠN TRƯỚC VỪA KẾT THÚC TẠI ĐÂY:
«...{doan_truoc}»

YÊU CẦU NỐI TIẾP LIỀN MẠCH:
- Hãy BẮT ĐẦU viết tiếp câu chuyện ngay từ khoảnh khắc câu trên vừa dừng lại, tạo thành một mạch đọc xuyên suốt, trơn tru, không đứt đoạn.
- TUYỆT ĐỐI KHÔNG mở đầu bằng câu tóm tắt lại ("Như đã thấy", "Ở đoạn trước...").
- TUYỆT ĐỐI KHÔNG có lời chào hỏi hay câu chuyển ý vụng về.
"""

        if idx == tong_phan:
            prompt_part += """
---
ĐÂY LÀ PHẦN KẾT THÚC CỦA TOÀN BỘ KỊCH BẢN:
- Đẩy cao trào nhận thức lên đỉnh điểm.
- Đúc kết bài học sâu sắc, để lại một câu chốt hạ đanh thép găm thẳng vào tâm trí người nghe trước khi dừng lại.
"""

        prompt_part += """
---
YÊU CẦU ĐỊNH DẠNG ĐẦU RA (NGHIÊM NGẶT):
1. CHỈ VIẾT ĐOẠN VĂN XUÔI LỜI BÌNH (VOICEOVER NARRATION) THUẦN ĐỂ ĐỌC.
2. TUYỆT ĐỐI KHÔNG ghi tiêu đề phần (KHÔNG ghi 'Phần 1', KHÔNG ghi tên phần).
3. TUYỆT ĐỐI KHÔNG dùng bất kỳ ICON hay EMOJI nào.
4. TUYỆT ĐỐI KHÔNG có mô tả phân cảnh, hình ảnh, góc máy, âm thanh (KHÔNG CẢNH, KHÔNG HÌNH, KHÔNG BGM, KHÔNG SFX).
5. CHỈ TRẢ VỀ NỘI DUNG VĂN XUÔI THUẦN ĐỂ ĐỌC.
"""
        kq_part = hoi_llm(prompt_part, timeout=180)
        if not kq_part or len(kq_part.strip()) < 30:
            raise ValueError(f"AI không phản hồi phần {idx}. Vui lòng thử lại.")

        part_clean = lam_sach_van_doc(kq_part.strip())
        cac_doan_viet.append(part_clean)

    # Ghép nối toàn bộ các phần thành 1 bài viết hoàn chỉnh duy nhất
    bai_hoan_chinh = "\n\n".join(cac_doan_viet)
    bai_hoan_chinh = lam_sach_van_doc(bai_hoan_chinh)
    return bai_hoan_chinh


def viet_moi_kich_ban_plugin(tieu_de, plugin_data, so_tu_muc_tieu=None, bao=None):
    """Quy trình trọn gói tự động: Lên dàn bài -> Viết từng phần -> Ghép thành 1 bài hoàn chỉnh thuần đọc."""
    tieu_de_raw = str(tieu_de or "").strip()
    if not tieu_de_raw:
        raise ValueError("Chưa nhập tiêu đề hoặc ý tưởng kịch bản mới")

    cs = plugin_data.get("chi_so_kich_ban") or {}
    so_tu_chuan = int(so_tu_muc_tieu or cs.get("so_tu_tb") or 500)

    # 1. Lập dàn bài
    dan_bai_data = lap_dan_bai_kenh(tieu_de_raw, plugin_data, so_tu_mong_muon=so_tu_chuan, bao=bao)

    # 2. Viết từng phần theo dàn bài
    bai_viet = viet_kich_ban_tung_phan(tieu_de_raw, dan_bai_data, plugin_data, so_tu_muc_tieu=so_tu_chuan, bao=bao)
    return bai_viet


def viet_lai_kich_ban_plugin(kich_ban_goc, plugin_data, so_tu_muc_tieu=None, bao=None):
    """Chuyển thể / Viết lại kịch bản sẵn có theo phong cách bộ Plugin kênh:
    - BẢO TOÀN 100% CỐT LÕI VẤN ĐỀ, CHUỖI NHÂN QUẢ VÀ LOGIC BÀI HỌC CỦA KỊCH BẢN GỐC.
    - Chuyển đổi toàn diện giọng văn, ngôi kể, cách dẫn dắt theo kênh đối thủ.
    - Đầu ra là BÀI VIẾT HOÀN CHỈNH THUẦN ĐỂ ĐỌC: không chia từng phần, không mô tả cảnh, không dùng icon.
    """
    from common import hoi_llm
    kb_raw = str(kich_ban_goc or "").strip()
    if not kb_raw:
        raise ValueError("Chưa có nội dung kịch bản gốc để viết lại")

    kenh_ten = plugin_data.get("kenh_ten", "Kênh chuẩn")
    cs = plugin_data.get("chi_so_kich_ban") or {}
    so_tu_chuan = int(so_tu_muc_tieu or cs.get("so_tu_tb") or 500)

    phong_cach = _phong_cach_viet(plugin_data)

    # Nếu số từ yêu cầu lớn (> 750 từ), chia thành 2 phần để viết sâu không bị cụt
    if so_tu_chuan > 750:
        w_p1 = int(so_tu_chuan * 0.52)
        w_p2 = so_tu_chuan - w_p1

        if bao:
            bao(f"Đang chuyển thể phần 1/2 (~{w_p1} từ): Bối cảnh, mâu thuẫn & cám dỗ ban đầu…", 1, 2)

        prompt_1 = f"""Bạn là một bậc thầy biên kịch kịch bản video YouTube.
NHIỆM VỤ:
Viết lại nửa đầu của kịch bản gốc dưới đây thành kịch bản nói (lời bình / voiceover) thuần để đọc theo phong cách kênh «{kenh_ten}».

NGUYÊN TẮC BẢO TOÀN CỐT LÕI:
- Giữ nguyên 100% mâu thuẫn trung tâm và nỗi đau tâm lý của nhân vật từ kịch bản gốc.

ADN GIỌNG VĂN KÊNH «{kenh_ten}»:
{phong_cach}

KỊCH BẢN GỐC:
{kb_raw}

YÊU CẦU CHO NỬA ĐẦU NÀY:
- Viết NỬA ĐẦU câu chuyện của kịch bản gốc theo cấu trúc mạch truyện của kênh: mở bằng hook đúng công thức của kênh, triển khai tới khoảng giữa câu chuyện gốc rồi dừng ở một điểm treo (chưa giải quyết).
- ĐỘ DÀI: Đạt chuẩn khoảng ~{w_p1} TỪ.
- ĐẦU RA: VĂN XUÔI THUẦN ĐỂ ĐỌC. KHÔNG ICON, KHÔNG PHÂN CẢNH, KHÔNG TIÊU ĐỀ PHẦN.
"""
        kq1 = hoi_llm(prompt_1, timeout=180)
        p1_clean = lam_sach_van_doc(kq1)

        if bao:
            bao(f"Đang chuyển thể phần 2/2 (~{w_p2} từ): Đỉnh điểm đổ vỡ, thức tỉnh & bài học…", 2, 2)

        tail = " ".join(p1_clean.split()[-150:])
        prompt_2 = f"""Bạn đang viết tiếp nửa sau của kịch bản nói theo phong cách kênh «{kenh_ten}».
ADN GIỌNG VĂN KÊNH «{kenh_ten}» (giữ y như nửa đầu):
{phong_cach}

ĐOẠN TRƯỚC VỪA KẾT THÚC TẠI ĐÂY:
«...{tail}»

KỊCH BẢN GỐC THAM CHIẾU:
{kb_raw}

YÊU CẦU CHO NỬA SAU:
- BẮT ĐẦU viết tiếp câu chuyện từ điểm dừng trên một cách liền mạch, đi hết phần còn lại của kịch bản gốc (cao trào, chuyển biến, thông điệp) đúng logic nhân quả của bản gốc và kết theo cách kết bài của kênh.
- KHÔNG lặp lại nội dung nửa đầu đã viết.
- ĐỘ DÀI: Đạt chuẩn khoảng ~{w_p2} TỪ.
- ĐẦU RA: VĂN XUÔI THUẦN ĐỂ ĐỌC. KHÔNG ICON, KHÔNG PHÂN CẢNH, KHÔNG TIÊU ĐỀ PHẦN.
"""
        kq2 = hoi_llm(prompt_2, timeout=180)
        p2_clean = lam_sach_van_doc(kq2)

        bai_viet = p1_clean + "\n\n" + p2_clean
        return lam_sach_van_doc(bai_viet)

    # Nếu số từ <= 750, viết trong 1 lượt với hướng dẫn chi tiết
    prompt = f"""Bạn là bậc thầy chuyển thể kịch bản video ngắn triệu view.

MỤC TIÊU:
Viết lại (chuyển thể) kịch bản gốc dưới đây thành MỘT BÀI VIẾT HOÀN CHỈNH THUẦN ĐỂ ĐỌC (lời bình / voiceover narration) mang phong cách đặc trưng của kênh «{kenh_ten}».

NGUYÊN TẮC BẢO TOÀN CỐT LÕI (BẤT BIẾN - TUYỆT ĐỐI KHÔNG ĐƯỢC LỆCH):
1. CỐT LÕI VẤN ĐỀ: Giữ nguyên mâu thuẫn trung tâm, nỗi đau tâm lý và căn nguyên sai lầm của nhân vật trong kịch bản gốc.
2. CHUỖI NHÂN QUẢ: Hành động sai dẫn đến hậu quả gì, khoảnh khắc thức tỉnh tại đâu — logic nhân quả này phải được bảo toàn nguyên vẹn.
3. THÔNG ĐIỆP ĐỌNG LẠI: Người nghe sau khi nghe xong bài viết mới phải rút ra được chính xác bài học và cảm xúc giác ngộ như kịch bản gốc.

ADN GIỌNG VĂN KÊNH «{kenh_ten}»:
{phong_cach}
- Mọi biến chuyển nội tâm phải gắn chặt với hành vi, người, vật cụ thể (để dựng hình được).
- ĐỘ DÀI BẮT BUỘC: Đạt xấp xỉ ~{so_tu_chuan} TỪ (khoảng {int(so_tu_chuan * 0.9)} - {int(so_tu_chuan * 1.15)} từ).

--- KỊCH BẢN GỐC CẦN CHUYỂN THỂ ---
{kb_raw}

--- YÊU CẦU ĐẦU RA NGHIÊM NGẶT ---
1. ĐẦU RA LÀ BÀI VIẾT HOÀN CHỈNH XUYÊN SUỐT THUẦN ĐỂ ĐỌC THU ÂM (VOICEOVER NARRATION).
2. TUYỆT ĐỐI KHÔNG chia từng phần, KHÔNG có tiêu đề 'Hồi 1', 'Phần 1' hay bất kỳ phân đoạn nào.
3. TUYỆT ĐỐI KHÔNG dùng bất kỳ ICON hay EMOJI nào.
4. TUYỆT ĐỐI KHÔNG mô tả hình ảnh, góc máy, âm thanh (KHÔNG CẢNH, KHÔNG HÌNH, KHÔNG BGM, KHÔNG SFX).
5. CHỈ TRẢ VỀ NỘI DUNG VĂN XUÔI THUẦN ĐỂ ĐỌC.
"""
    if bao:
        bao(f"Đang bóc tách cốt lõi & viết lại kịch bản thuần đọc ({so_tu_chuan} từ) theo phong cách {kenh_ten}…")
    kq = hoi_llm(prompt, timeout=300)
    if not kq or len(kq.strip()) < 50:
        raise ValueError("AI không phản hồi kịch bản chuyển thể. Vui lòng thử lại.")
    return lam_sach_van_doc(kq.strip())

