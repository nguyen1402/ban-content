# -*- coding: utf-8 -*-
"""🏛 NHÂN VẬT & SỰ KIỆN LỊCH SỬ THẬT (04/11 user: "phần chủ thể phải có 1 danh sách sự kiện lịch sử hoặc nhân vật lịch
sử xuất hiện thật — để tìm hình ảnh cụ thể nhân vật, tôi tìm và lưu ảnh đó vào làm tham chiếu cho AI làm nét và làm
remotion liên quan tới nhân vật đó cho chuẩn với lời thoại").

AI đọc kịch bản (theo lô, song song) -> danh sách người thật có tên + sự kiện thật, mỗi mục: tên, tên gốc (để tìm ảnh),
các TÊN GỌI trong lời (để dò câu nào nhắc), thời kỳ / năm, câu. Ghi ra/<dự án>/lich_su.json; người dùng sửa / thêm tay.
Ảnh người dùng tự tìm và thả vào: kho CHUNG mọi dự án cache/lich_su/<khoá>/ (cùng một nhân vật dùng lại ở video sau).
Mặt người thật CHỈ dùng trong Remotion, từ đúng ảnh này (user 04/11) — Veo / ảnh AI vẫn không vẽ mặt người thật."""
import hashlib
import os
import re
import unicodedata

from common import CACHE_CHUNG, doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

KHO = os.path.join(CACHE_CHUNG, "lich_su")
CAU_MOI_LO = 60            # danh từ riêng dễ bắt hơn chủ thể -> lô to hơn chu_the (25)
LO_CHO = 200
DUOI_ANH = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif")

_P = """Read this part of a documentary narration (Vietnamese, numbered sentences). List every REAL HISTORICAL PERSON and
every REAL HISTORICAL EVENT it names or clearly refers to, so the editor can find real photos / paintings of them.
  - "nhan_vat": real, named individuals who existed (rulers, generals, scientists, explorers, artists, politicians...).
    NOT generic people ("a soldier", "the farmers"), NOT fictional characters, NOT animals.
  - "su_kien": real, specific events (battles, wars, disasters, treaties, revolutions, discoveries, expeditions...).
    NOT general trends or ideas.
For each give:
  "ten": the name as Vietnamese viewers know it;
  "ten_goc": the name in its common English / original form (used to search images);
  "goi": EVERY word or phrase this narration uses for it, copied exactly as written (full name, short name, titles,
    nicknames — e.g. "Napoleon", "Hoàng đế Napoleon") — used to find which sentences show it. Every phrase must
    contain the proper name itself: NO pronouns or bare titles ("ông", "giáo sư"), NO vague phrases ("dự án này",
    "vụ việc đó", "đợt đầu tiên");
  "thoi_ky": years / era (e.g. "1769-1821", "năm 1815", "thế kỷ 13");
  "mo_ta": one short Vietnamese line: who / what it is in this story;
  "tim": one English image-search query for real photos, portraits or paintings of it;
  "cau": the numbers of the sentences that mention it.
Nothing found -> empty lists. Only JSON:
{{"nhan_vat": [{{"ten": "...", "ten_goc": "...", "goi": ["..."], "thoi_ky": "...", "mo_ta": "...", "tim": "...", "cau": [1]}}],
 "su_kien": [{{"ten": "...", "ten_goc": "...", "goi": ["..."], "thoi_ky": "...", "mo_ta": "...", "tim": "...", "cau": [2]}}]}}

NARRATION:
{kb}"""


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "lich_su.json")


def _bo_dau(s):
    s = unicodedata.normalize("NFD", str(s or "").lower().replace("đ", "d"))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))).strip()


def khoa(x):
    """Khoá kho ảnh chung của một mục: theo tên gốc (cùng người ở dự án khác -> cùng thư mục ảnh)."""
    return re.sub(r"[^a-z0-9]+", "_", _bo_dau(x.get("ten_goc") or x.get("ten"))).strip("_")[:60] or "khong_ten"


# 04/11 (chạy thử lopxe): AI ghi tên gọi chung chung ("Ông", "dự án này", "vụ tai tiếng đó") -> câu nào cũng khớp nhầm
_DAI_TU = {"ong", "ba", "anh", "chi", "co", "chu", "bac", "ngai", "vi", "nguoi", "ho", "han", "y", "no", "em", "cau",
           "giao su", "tien si", "chuyen gia", "tho", "anh tho", "vi tuong", "nha vua", "hoang de", "tong thong"}
_CHI_DINH = {"nay", "do", "ay", "kia", "no"}


def _goi_ok(g):
    """Tên gọi đủ riêng để dò câu: không là đại từ / chức danh trơn, không có chữ chỉ định (này / đó / ấy), có ít nhất
    một chữ viết hoa ngoài chữ đầu (tên riêng) hoặc là một chữ viết hoa; tối đa 6 chữ."""
    ch = _bo_dau(g).split()
    if not ch or len(ch) > 6 or " ".join(ch) in _DAI_TU or _CHI_DINH & set(ch[1:]):
        return False
    tu = str(g).split()
    return any(w[:1].isupper() for w in tu[1:]) or (len(tu) == 1 and tu[0][:1].isupper())


def _sach(x, loai):
    if not isinstance(x, dict) or not str(x.get("ten") or "").strip():
        return None
    ten = str(x["ten"]).strip()[:80]
    goi = [str(g).strip() for g in (x.get("goi") or []) if str(g).strip()]
    if not x.get("tay"):                                     # tên gọi user tự gõ: giữ nguyên
        goi = [g for g in goi if _goi_ok(g)]
    goi = list(dict.fromkeys([ten] + goi))[:12]
    cau = sorted({int(c) for c in x.get("cau") or [] if str(c).strip().isdigit()})
    ra = {"loai": loai, "ten": ten, "ten_goc": str(x.get("ten_goc") or ten).strip()[:80], "goi": goi,
          "thoi_ky": str(x.get("thoi_ky") or "").strip()[:60], "mo_ta": str(x.get("mo_ta") or "").strip()[:200],
          "tim": str(x.get("tim") or x.get("ten_goc") or ten).strip()[:120], "cau": cau, "tay": bool(x.get("tay"))}
    ra["khoa"] = str(x.get("khoa") or "") or khoa(ra)
    ra["khoa_khac"] = [k for k in x.get("khoa_khac") or [] if k != ra["khoa"]]
    return ra


def _gop(ds):
    """Gộp mục trùng giữa các lô: cùng khoá, hoặc chung một tên gọi (04/11 lopxe: "Stewart Honig" lô 1 và "Honig" lô 3
    là một người). Hợp tên gọi + câu; khoá của mục gộp vào giữ trong khoa_khac để ảnh đã lưu theo khoá đó vẫn dùng."""
    ra = []
    for x in ds:
        if not x:
            continue
        gx = {_bo_dau(g) for g in x["goi"]}
        y = next((y for y in ra if y["loai"] == x["loai"] and (y["khoa"] == x["khoa"] or gx & {_bo_dau(g) for g in y["goi"]})), None)
        if not y:
            ra.append(x)
            continue
        y["goi"] = list(dict.fromkeys(y["goi"] + x["goi"]))[:12]
        y["cau"] = sorted(set(y["cau"]) | set(x["cau"]))
        y["khoa_khac"] = [k for k in dict.fromkeys(y["khoa_khac"] + [x["khoa"]] + x["khoa_khac"]) if k != y["khoa"]]
        y["tay"] = y["tay"] or x["tay"]
        for f in ("thoi_ky", "mo_ta"):
            y[f] = y[f] or x[f]
    return ra


def lap(du_an, bao=None):
    """Hỏi AI lập danh sách (mục người dùng thêm tay giữ nguyên). -> danh sách mục."""
    bao = bao or (lambda m: log("[lịch sử] " + m))
    canh = doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — chạy bước đọc giọng trước")
    lots = [canh[i:i + CAU_MOI_LO] for i in range(0, len(canh), CAU_MOI_LO)]
    p = [_P.format(kb="\n".join(f"[{c['id']}] {str(c.get('text') or '').strip()}" for c in lot)) for lot in lots]
    bao(f"AI đọc {len(canh)} câu ({len(lots)} lô) tìm nhân vật / sự kiện lịch sử thật…")
    kq = [None] * len(lots)
    for lan in range(3):
        can = [k for k in range(len(lots)) if kq[k] is None]
        if not can:
            break
        for k, r in zip(can, hoi_nhieu([p[k] for k in can], timeout=LO_CHO)):
            j = rut_json(r or "")
            if isinstance(j, dict) and ("nhan_vat" in j or "su_kien" in j):
                id_lo = {c["id"] for c in lots[k]}
                ds_ = [_sach(x, "nhan_vat") for x in j.get("nhan_vat") or []] + [_sach(x, "su_kien") for x in j.get("su_kien") or []]
                for x in ds_:
                    if x:
                        x["cau"] = [c for c in x["cau"] if c in id_lo]
                kq[k] = ds_
    hong = [k + 1 for k in range(len(lots)) if kq[k] is None]
    if hong:
        bao(f"! lô {hong} không trả lời — bỏ qua")
    moi = _gop([x for ds_ in kq if ds_ for x in ds_])
    tay = [x for x in doc(du_an, anh=False) if x.get("tay")]
    co = {(x["loai"], x["khoa"]) for x in moi}
    ds = moi + [x for x in tay if (x["loai"], x["khoa"]) not in co]
    ghi_json(_p(du_an), {"ds": ds})
    bao(f"{sum(x['loai'] == 'nhan_vat' for x in ds)} nhân vật, {sum(x['loai'] == 'su_kien' for x in ds)} sự kiện")
    return doc(du_an)


def doc(du_an, anh=True):
    # lọc tên gọi + gộp trùng cả khi đọc: danh sách lập trước bản sửa 04/11 cũng sạch, không cần hỏi AI lại
    ds = _gop([_sach(x, x.get("loai") if x.get("loai") in ("nhan_vat", "su_kien") else "nhan_vat")
               for x in ((doc_json(_p(du_an), {}) or {}).get("ds") or [])])
    if anh:
        for x in ds:
            x["anh"] = [f for k in [x["khoa"]] + x["khoa_khac"] for f in ds_anh(k)]
    return ds


def luu(du_an, ds):
    """Người dùng sửa / thêm / xoá mục trên giao diện."""
    gon = _gop([_sach(x, x.get("loai") if x.get("loai") in ("nhan_vat", "su_kien") else "nhan_vat") for x in ds or []])
    ghi_json(_p(du_an), {"ds": gon})
    return doc(du_an)


# --- kho ảnh tham chiếu -------------------------------------------------------------------------------------------------
def ds_anh(k):
    d = os.path.join(KHO, k)
    if not os.path.isdir(d):
        return []
    return sorted((os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".jpg")), key=os.path.getmtime)


def them_anh(k, f_vao):
    """Ảnh người dùng thả vào (mọi định dạng PIL đọc được) -> JPEG trong kho chung. -> đường dẫn | ValueError."""
    from PIL import Image, ImageOps
    if not re.fullmatch(r"[a-z0-9_]{1,60}", k or ""):
        raise ValueError("khoá mục không hợp lệ")
    try:
        im = ImageOps.exif_transpose(Image.open(f_vao))
        im.load()
    except Exception as e:                                   # noqa: BLE001
        raise ValueError(f"không đọc được ảnh: {str(e)[:100]}") from e
    if min(im.size) < 64:
        raise ValueError("ảnh quá nhỏ")
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        nen = Image.new("RGB", im.size, (255, 255, 255))
        nen.paste(im, mask=im.split()[-1])
        im = nen
    im = im.convert("RGB")
    d = os.path.join(KHO, k)
    os.makedirs(d, exist_ok=True)
    h = hashlib.md5(im.tobytes()).hexdigest()[:14]
    ra = os.path.join(d, f"{h}.jpg")
    if not os.path.isfile(ra):
        im.save(ra, quality=95)
    return ra


def xoa_anh(f):
    f = os.path.abspath(f)
    if os.path.dirname(os.path.dirname(f)) != os.path.abspath(KHO) or not os.path.isfile(f):
        raise ValueError("không phải ảnh trong kho lịch sử")
    os.remove(f)


def lam_net(f_vao, f_ra, cao_toi_thieu=1080):
    """Ảnh lịch sử thường nhỏ / mờ: phóng (LANCZOS) tới cao_toi_thieu, tăng tương phản nhẹ + làm sắc. Làm tại máy, không
    vẽ lại -> mặt giữ đúng người thật."""
    from PIL import Image, ImageFilter, ImageOps
    im = Image.open(f_vao).convert("RGB")
    if im.size[1] < cao_toi_thieu:
        s = cao_toi_thieu / im.size[1]
        im = im.resize((round(im.size[0] * s), cao_toi_thieu), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=0.5)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=110, threshold=3))
    os.makedirs(os.path.dirname(f_ra), exist_ok=True)
    im.save(f_ra, quality=93)
    return im.size


# --- dùng khi dựng ------------------------------------------------------------------------------------------------------
def _giong_cau(a, b):
    """Hai câu (đã bỏ dấu) là một: câu này nằm trong câu kia, hoặc chung >= 60% chữ của câu ngắn hơn."""
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) >= 0.6 * min(len(wa), len(wb))


def nhac_trong(du_an, text):
    """Mục mà đoạn lời nhắc tới -> [mục] (có ảnh hay chưa: xem x["anh"]). Hai cách: lời có tên gọi của mục, hoặc lời trùng
    một câu AI đã ghi cho mục (04/11 lopxe: sự kiện ít khi được gọi đúng tên — "Vụ cháy bãi lốp Winchester (1983)" không có
    nguyên văn trong lời). Câu so theo CHỮ, không theo số: Remotion tách câu khác tu_khoa.json (lopxe 124 / 121)."""
    t = " " + _bo_dau(text) + " "
    cau = {c["id"]: _bo_dau(c.get("text")) for c in doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []}
    ra = []
    for x in doc(du_an):
        goi = (_bo_dau(re.sub(r"\(.*?\)", " ", g)) for g in x["goi"])
        if any(len(g) >= 3 and f" {g} " in t for g in goi) or any(_giong_cau(cau.get(i), t.strip()) for i in x["cau"]):
            ra.append(x)
    return ra
