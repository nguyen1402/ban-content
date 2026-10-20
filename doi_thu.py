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

from common import CACHE_CHUNG, log

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
