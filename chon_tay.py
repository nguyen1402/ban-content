# -*- coding: utf-8 -*-
"""🎯 TỰ CHỌN NGUỒN TRÊN YOUTUBE — 25/10 user: "thôi phần quét video rồi tự chấm để lấy video băm; tôi muốn xem toàn bộ
video lọc ra cho mỗi chủ thể, tích vào thì tự tải về rồi băm ra, không cần xem trước (quét lâu mà nhiều lúc không chính
xác bằng tôi chọn). Danh sách lọc như cách YouTube lọc, xem được nhiều kết quả như trên YouTube."

  tim(du_an, cd_id, q, trang, loc)  -> kết quả tìm YouTube ĐÚNG THỨ TỰ YouTube (không chấm lại / xếp lại), 20 video / trang,
                                       bộ lọc như YouTube: sắp xếp, thời lượng, ngày tải lên, HD, Creative Commons.
  tai_va_bam(du_an, cd_id, videos)  -> chạy nền: tải TRỌN video 720p -> băm theo CẢNH QUAY, LỌC NHẸ (khớp chủ thể mức
                                       cơ bản; bỏ cảnh rác / tối / mờ / sai vật thể / hoạt hình / ảnh tĩnh / khung dọc) -> mảnh vào Kho dự án, gắn đúng chủ thể (đoạn kho_cd).
Không tải ảnh xem trước (storyboard), không chấm SigLIP để chọn video."""
import base64
import json
import os
import subprocess
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from common import CACHE_CHUNG, YTDLP, YT_JS, doc_json, ghi_json, log, thu_muc_du_an

MOI_TRANG = 20
TAI_CUNG_LUC = 3
TT = {}                      # dự án -> {dang, dong[], video: {vid: trạng thái}}
_KHOA = threading.Lock()


# --------------------------------------------------------------------------- bộ lọc kiểu YouTube (tham số sp)
_SAP = {"lien_quan": 0, "danh_gia": 1, "moi": 2, "luot_xem": 3}
_NGAY = {"": 0, "gio": 1, "ngay": 2, "tuan": 3, "thang": 4, "nam": 5}
_DAI = {"": 0, "ngan": 1, "dai": 2, "vua": 3}                 # ngắn < 4 phút, vừa 4-20 phút, dài > 20 phút


def _sp(sap="lien_quan", ngay="", dai="", hd=False, cc=False):
    """Tham số sp của trang tìm YouTube (protobuf base64) — giống bấm Bộ lọc trên YouTube; luôn chỉ lấy loại Video."""
    loc = bytes([0x10, 0x01])                                # loại: video
    if _NGAY.get(ngay):
        loc = bytes([0x08, _NGAY[ngay]]) + loc
    if _DAI.get(dai):
        loc += bytes([0x18, _DAI[dai]])
    if hd:
        loc += bytes([0x20, 0x01])
    if cc:
        loc += bytes([0x30, 0x01])
    b = (bytes([0x08, _SAP[sap]]) if _SAP.get(sap) else b"") + bytes([0x12, len(loc)]) + loc
    return base64.b64encode(b).decode()


def _gio(sec):
    sec = int(sec or 0)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _so(n):
    n = int(n or 0)
    return f"{n / 1e6:.1f} Tr" if n >= 1e6 else f"{n / 1e3:.0f} N" if n >= 1e3 else str(n)


def _tim_yt(q, n, sp):
    """n kết quả đầu (thứ tự YouTube) của truy vấn q với bộ lọc sp. Lưu đệm 1 ngày."""
    cache = os.path.join(CACHE_CHUNG, "chon_tay_tim.json")
    k = f"{sp}|{n}|{q.strip().lower()}"
    da = doc_json(cache, {}) or {}
    if k in da and time.time() - da[k].get("luc", 0) < 86400:
        return da[k]["ds"]
    u = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&sp=" + urllib.parse.quote(sp)
    p = subprocess.run([YTDLP, *YT_JS, "--flat-playlist", "-J", "--no-warnings", "--playlist-end", str(n), u],
                       capture_output=True, timeout=180, creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        j = json.loads(p.stdout.decode("utf-8", "ignore") or "{}")
    except ValueError:
        j = {}
    ds = []
    for e in j.get("entries") or []:
        if not e or not e.get("id") or len(str(e["id"])) != 11:
            continue
        ds.append({"id": e["id"], "tieu_de": e.get("title") or "", "dai": e.get("duration") or 0,
                   "kenh": e.get("channel") or e.get("uploader") or "", "luot_xem": e.get("view_count") or 0,
                   "xac_minh": bool(e.get("channel_is_verified")), "ngay": e.get("upload_date") or ""})
    with _KHOA:
        da = doc_json(cache, {}) or {}
        da[k] = {"luc": time.time(), "ds": ds}
        ghi_json(cache, da)
    return ds


def chu_the_ds(du_an):
    """Các chủ thể (đoạn giữ kho: kho_cd) của dự án -> [{id, ten, mo_ta_en, tu_khoa_en, so_manh}]."""
    import dung_tay
    cds = (doc_json(os.path.join(thu_muc_du_an(du_an)[1], "chu_de.json"), {}) or {}).get("chu_de") or []
    kho = dung_tay.doc_kho(du_an, quet=False)
    so = {}
    for m in kho.values():
        if m.get("loai") == "video" and m.get("trang_thai") == "xong" and m.get("chu_de") is not None:
            so[m["chu_de"]] = so.get(m["chu_de"], 0) + 1
    ra, da = [], set()
    for d in cds:
        k = d.get("kho_cd") or d["id"]
        if k in da:
            continue
        da.add(k)
        goc = next((x for x in cds if x["id"] == k), d)
        ra.append({"id": k, "ten": goc.get("doi_tuong") or goc.get("ten") or f"Chủ thể {k}", "mo_ta_en": goc.get("mo_ta_en") or "",
                   "tu_khoa_en": list(dict.fromkeys([str(t) for t in (goc.get("tu_khoa_en") or []) if str(t).strip()]
                                                    + [str(x.get("tu_khoa") or "") for x in goc.get("trang_thai") or []
                                                       if str(x.get("tu_khoa") or "").strip()])),
                   "trang_thai": list({str(x.get("tu_khoa") or x.get("mo_ta")): {   # 26/10: trạng thái theo kịch bản
                       "mo_ta": str(x.get("mo_ta") or "").strip(), "tu_khoa": str(x.get("tu_khoa") or "").strip(),
                       "cau": [int(i) for i in x.get("cau") or [] if str(i).isdigit()]}
                       for x in goc.get("trang_thai") or [] if isinstance(x, dict)}.values()),
                   "so_canh": sum(int(x.get("so_canh") or 0) for x in cds if (x.get("kho_cd") or x["id"]) == k),
                   "so_manh": so.get(k, 0)})
    return ra


# 26/10 user: từ khoá THEO KỊCH BẢN — mỗi trạng thái của chủ thể (gấu ra khỏi hang ngủ đông, gấu săn nai con, gấu bắt cá
# hồi họng đỏ…) một từ khoá NGẮN đúng chi tiết lời (con mồi, loài cá, hành động); tên lõi chủ thể cho dòng "chung".
# Đuôi chất lượng (documentary / 4k / b-roll) là Ô CHỌN trên giao diện, áp cho mọi từ khoá; kèm từ loại trừ.
DUOI_CL = ("documentary", "4k", "b-roll")   # đo gaubaccuc: documentary = phim dài đúng đề tài; 4k = cảnh đẹp; b-roll = clip ngắn
LOAI_TRU = "-cartoon -animation -animated -minecraft -roblox -toy -lego -drawing -kids -reaction"
_DUNG = {"in", "on", "at", "with", "under", "from", "into", "of", "near", "and", "that", "the", "a", "an", "to", "for",
         "by", "while", "over", "through", "along", "across", "during", "its", "their"}
_BOT = {"large", "small", "big", "huge", "various", "vast", "scenic", "historical", "old", "young", "giant", "wild"}
_P_LOI = """You write YouTube search keywords to find REAL footage for a documentary narration (Vietnamese).
For each subject below:
- "ten": the SHORT English name(s) someone types into YouTube for the subject itself: 1-3 words, just the animal / object /
  place / kind of people (e.g. "grizzly bear", "cutthroat trout", "fishing boat", "osprey"). No adjectives like large /
  various / scenic, no actions. Up to 2 names only if the subject groups clearly different things.
- "tt": for EACH numbered state, ONE short English keyword (3-6 words) = subject name + the SPECIFIC action + the SPECIFIC
  thing it acts on, exactly as the narration says (the prey animal, the fish species, the place, the tool), e.g.
  "grizzly bear hunting elk calf", "grizzly bear leaving winter den", "grizzly bear catching cutthroat trout",
  "grizzly bears fighting territory". Use the real species / object named in the sentences, not a generic word. Something
  a camera can film; no years, numbers, feelings or abstract ideas.
{ds}
Return ONLY JSON: {{"<subject id>": {{"ten": ["name", ...], "tt": {{"<state number>": "keyword", ...}}}}}}"""


def _cum_dau(tk, toi_da=3):
    """Dự phòng khi AI hỏng: cụm danh từ đầu của từ khoá (bỏ tính từ chung chung, dừng ở giới từ / động từ)."""
    import re
    ra = []
    for i, w in enumerate(str(tk or "").lower().split()):
        if w in _DUNG or (ra and re.search(r"(ing|ed)$", w)):
            break
        if (not ra and w in _BOT) or (i == 0 and w.endswith("ing")):
            continue
        ra.append(w)
    return " ".join(ra[:toi_da])


def _loi_cau(du_an):
    return {int(c["id"]): str(c.get("text") or "") for c in doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), [])
            or [] if str(c.get("id", "")).isdigit()}


# 27/10 user ("mọi chủ thể cùng thể loại cá sấu thì phải đi chung chứ"): LOÀI CHUNG của chủ thể lấy từ tên tiếng Việt (không
# hỏi AI): bỏ đuôi " · lô N" và tiền tố số lượng / dạng (ba con, xác, bộ xương, loài, cá thể, lớp, nhóm…), lấy danh từ chính —
# "Ba con cá sấu", "Xác cá sấu thí nghiệm", "Bộ xương con cá sấu thứ hai" -> "cá sấu"; "Cá mập ngủ", "Cá mập sáu mang" -> "cá
# mập"; chim ưng vẫn khác cá (26/10). Mảnh 🎯 của một chủ thể dùng chung cho mọi chủ thể cùng loài (goi_y).
_BO_DAU = ("cá thể", "bộ xương", "các nhà", "ba con", "hai con", "một con", "các", "những", "con", "xác", "loài", "lớp",
           "bầy", "đàn", "nhóm", "giới", "đôi", "cặp", "đám", "một", "hai", "ba")
_HAI_TIENG = {"cá", "chim", "tàu", "xe", "máy", "nhà", "khối", "cây", "thằn", "người", "đáy", "lái"}


def loai_chung(ten):
    """Tên chủ thể -> khoá loài chung (vd "cá sấu")."""
    import re
    t = re.sub(r"\s*·\s*lô\s*\d+\s*$", "", str(ten or "")).strip().lower()
    doi = True
    while doi:
        doi = False
        for p in _BO_DAU:
            if t.startswith(p + " "):
                t, doi = t[len(p) + 1:].strip(), True
                break
    w = t.split()
    if not w:
        return str(ten or "").strip().lower()
    return " ".join(w[:2]) if w[0] in _HAI_TIENG and len(w) > 1 else w[0]


# 27/10 user ("tại sao tôi có chủ thể rồi mà khi bấm vào chọn video theo chủ thể nó lại hỏi lại ai?"): mở 🎯 KHÔNG hỏi AI
# rút gọn từ khoá nữa (AI hỏng thì không lưu -> lần nào mở cũng hỏi lại, chờ tới 3 phút) — dùng từ khoá có sẵn của chủ
# thể / trạng thái (bước chủ thể đã viết), dự án đã có bản AI rút gọn (chon_tay_loi.json) thì dùng bản đó. Bật lại: True
HOI_AI_TU_KHOA = False


def tu_khoa_nhanh(du_an, ds):
    """Gắn cho từng chủ thể: "ten_loi" (tên ngắn) và "dong_tk" = [{nhan, cau, tk}] — dòng "chung" theo tên ngắn + một dòng
    cho mỗi trạng thái kịch bản (nhãn tiếng Việt, số câu, từ khoá đúng chi tiết lời). Hỏi AI MỘT lượt cho mọi chủ thể
    chưa có (lưu ra/<dự án>/chon_tay_loi.json theo nội dung), hỏng thì dùng từ khoá trạng thái cũ."""
    import hashlib
    from common import hoi_nhieu, rut_json
    p = os.path.join(thu_muc_du_an(du_an)[1], "chon_tay_loi.json")
    da = doc_json(p, {}) or {}
    loi = _loi_cau(du_an)
    khoa = {c["id"]: hashlib.md5(("tt2|" + c["mo_ta_en"] + "|" + "|".join(f'{s["mo_ta"]}:{s["cau"]}' for s in c["trang_thai"]))
                                 .encode("utf-8")).hexdigest()[:10] for c in ds}
    can = [c for c in ds if (da.get(str(c["id"])) or {}).get("k") != khoa[c["id"]]] if HOI_AI_TU_KHOA else []
    if can:
        dong = []
        for c in can:
            dong.append(f'SUBJECT {c["id"]}: {c["mo_ta_en"]}')
            for n, s in enumerate(c["trang_thai"], 1):
                lo = " ".join(loi.get(i, "") for i in s["cau"][:6])[:700]
                dong.append(f'  state {n}: {s["mo_ta"]} — narration: "{lo}"')
        try:
            r = hoi_nhieu([_P_LOI.format(ds="\n".join(dong))], timeout=180)[0]
            j = rut_json(r or "") or {}
        except Exception as e:                                # noqa: BLE001
            log(f"  [🎯] hỏi từ khoá theo kịch bản lỗi: {str(e)[:120]}")
            j = {}
        for c in can:
            x = j.get(str(c["id"])) if isinstance(j, dict) else None
            if not isinstance(x, dict):
                continue
            ten = [str(t).strip().lower() for t in (x.get("ten") or []) if 1 <= len(str(t).split()) <= 3][:2]
            tt = {str(k): str(v).strip().lower() for k, v in (x.get("tt") or {}).items() if 2 <= len(str(v).split()) <= 8}
            if ten:
                da[str(c["id"])] = {"k": khoa[c["id"]], "ten": ten, "tt": tt}
        ghi_json(p, da)
    for c in ds:
        m = da.get(str(c["id"])) or {}
        ten = m.get("ten") or [x for x in [_cum_dau((c["tu_khoa_en"] or [c["mo_ta_en"]])[0])] if x]
        c["ten_loi"] = ten
        c["dong_tk"] = [{"nhan": "Chung" + (f" ({t})" if len(ten) > 1 else ""), "cau": [], "tk": t} for t in ten]
        for n, s in enumerate(c["trang_thai"], 1):
            c["dong_tk"].append({"nhan": s["mo_ta"] or f"Trạng thái {n}", "cau": s["cau"],
                                 "tk": (m.get("tt") or {}).get(str(n)) or s["tu_khoa"]})
    return ds


def tim(du_an, q, trang=1, sap="lien_quan", ngay="", dai="", hd=False, cc=False, loai_tru=True):
    """Trang `trang` (20 video) của kết quả tìm YouTube, giữ thứ tự YouTube; đánh dấu video đã tải / đã băm cho dự án."""
    import dung_tay
    q = str(q or "").strip()
    if not q:
        raise ValueError("thiếu từ khoá")
    trang = max(1, int(trang or 1))
    if loai_tru and " -" not in f" {q}":                       # 26/10: loại hoạt hình / game / đồ chơi ngay từ lúc tìm
        q = f"{q} {LOAI_TRU}"
    ds = _tim_yt(q, trang * MOI_TRANG, _sp(sap, ngay, dai, hd, cc))
    kho = dung_tay.doc_kho(du_an)
    co = {}
    for m in kho.values():
        g = m.get("video_goc")
        if g and m.get("trang_thai") in ("xong", "tach"):
            co[g] = co.get(g, 0) + (1 if m.get("trang_thai") == "xong" else 0)
    tt = (TT.get(du_an) or {}).get("video") or {}
    ra = []
    for i, v in enumerate(ds[(trang - 1) * MOI_TRANG:trang * MOI_TRANG], (trang - 1) * MOI_TRANG + 1):
        ra.append(dict(v, hang=i, url=f"https://www.youtube.com/watch?v={v['id']}",
                       thumb=f"https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg", dai_str=_gio(v["dai"]),
                       luot_xem_str=_so(v["luot_xem"]), da_co=co.get(v["id"], 0), tt=tt.get(v["id"], ""),
                       loai=("tin tức / hoạt hình / nhạc" if dung_tay.la_kenh_loai(v) else "")))
    return {"ds": ra, "het": len(ds) < trang * MOI_TRANG}


def _bao(du_an, m):
    t = TT.setdefault(du_an, {})
    t.setdefault("dong", []).append(time.strftime("%H:%M:%S ") + m)
    t["dong"] = t["dong"][-120:]
    log(f"[🎯 {du_an}] {m}")


def tai_va_bam(du_an, cd_id, videos):
    """Chạy nền: mỗi video tích chọn -> tải trọn 720p (chỉ hình) -> băm theo cảnh quay, giữ hết -> kho, gắn chủ thể cd_id."""
    import dung_tay
    import nhung_siglip
    import numpy as np
    t = TT.setdefault(du_an, {})
    vs = [v for v in videos or [] if isinstance(v, dict) and len(str(v.get("id") or "")) == 11]
    if not vs:
        raise ValueError("chưa tích video nào")
    ct = next((x for x in chu_the_ds(du_an) if x["id"] == int(cd_id)), None)
    if ct is None:
        raise ValueError("không thấy chủ thể")
    with _KHOA:
        moi = [v for v in vs if t.get("video", {}).get(v["id"]) not in ("cho", "tai", "bam")]
        for v in moi:
            t.setdefault("video", {})[v["id"]] = "cho"
        t["dang"] = True
    Q = np.atleast_2d(nhung_siglip.vec_mo_ta(ct["mo_ta_en"] or ct["ten"], ct["tu_khoa_en"][:4]))   # chỉ để xếp mảnh
    thu = os.path.join(thu_muc_du_an(du_an)[1], "kho", "video")

    def mot(v):
        vid = v["id"]
        f = os.path.join(thu, f"goc_{vid}.mp4")
        try:
            t["video"][vid] = "tai"
            _bao(du_an, f"tải «{v.get('tieu_de', vid)[:60]}» ({_gio(v.get('dai'))})…")
            if not dung_tay._tai_video_goc(vid, f, chi_hinh=True):            # noqa: SLF001
                t["video"][vid] = "loi"
                _bao(du_an, f"✖ không tải được {vid}")
                return
            t["video"][vid] = "bam"
            meta = {"tieu_de": v.get("tieu_de", ""), "kenh": v.get("kenh", ""),
                    "ghi_nguon": f"{v.get('tieu_de', '')} — {v.get('kenh', '')} — https://www.youtube.com/watch?v={vid}"}
            g, n = dung_tay.bam_theo_canh(du_an, vid, f, Q, int(cd_id), meta, ct["mo_ta_en"], giu_het=True)
            t["video"][vid] = "xong" if n else "loi"
            _bao(du_an, (f"✔ {vid}: {n} mảnh ({g:.0f}s) -> chủ thể «{ct['ten']}»" if n
                         else f"✖ {vid}: không cắt được cảnh nào (toàn hoạt hình / ảnh tĩnh / khung dọc?)"))
        except Exception as e:                               # noqa: BLE001
            t["video"][vid] = "loi"
            _bao(du_an, f"✖ {vid}: {str(e)[:150]}")
        finally:
            try:
                os.remove(f)
            except OSError:
                pass

    def chay():
        _bao(du_an, f"tải + băm {len(moi)} video cho chủ thể «{ct['ten']}»")
        with ThreadPoolExecutor(TAI_CUNG_LUC) as ex:
            list(ex.map(mot, moi))
        with _KHOA:
            t["dang"] = any(x in ("cho", "tai", "bam") for x in t.get("video", {}).values())
        try:
            dung_tay.quet_va_dong_bo_kho(du_an)
        except Exception:                                    # noqa: BLE001
            pass
    threading.Thread(target=chay, daemon=True).start()
    return len(moi)
