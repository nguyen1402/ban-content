# -*- coding: utf-8 -*-
"""STORYBOARD FLOW — 23/10/2026 user: thay "Tạo hàng loạt ảnh Flow" bằng storyboard như trong Flow: nhập kịch bản -> AI
lập ASSETS (nhân vật, bối cảnh, đạo cụ) -> AI chia SCENE nối tiếp nhau, mỗi scene 3-6 ảnh (tuỳ chỉnh) -> vẽ bằng Flow;
nhân vật BẮT BUỘC nhất quán xuyên suốt, đổi bối cảnh không làm đổi nhân vật, nhân vật KHÔNG ĐƠ -> tạo video cho scene
(làm hook) -> xuất JSON hoặc bản nháp CapCut.

Giữ nhân vật nhất quán bằng 3 lớp:
  1. "Kinh thánh" nhân vật: AI viết mô tả ngoại hình CỐ ĐỊNH (mặt, tóc, tuổi, trang phục + màu) một lần, mọi câu lệnh ảnh
     chép nguyên mô tả đó (không để AI tự diễn lại mỗi ảnh).
  2. Ảnh asset (tờ nhân vật: toàn thân + cận mặt) vẽ trước, gắn làm ẢNH THAM CHIẾU (ingredients) của Flow cho mọi ảnh có
     nhân vật đó (flow_ve._gan_tham_chieu — đo 23/10: Flow giữ đúng người / đồ vật của ảnh tham chiếu).
  3. Nối tiếp: ảnh trước của cùng scene gắn kèm làm tham chiếu (cùng nơi, cùng ánh sáng) nhưng góc máy mới, hành động tiến.
Chống đơ: câu lệnh từng ảnh là một khoảnh khắc ĐANG chuyển động (động từ cụ thể, dồn trọng tâm, cử chỉ, nét mặt theo cảm
xúc, ánh mắt nhìn vào việc đang làm) + câu chốt cấm dáng đứng tạo dáng / nhìn thẳng ống kính.

Dữ liệu: ra/storyboard/<id>/storyboard.json, ảnh trong assets/ và canh_XX/, video trong video/."""
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from common import ROOT, doc_json, ghi_json, hoi_llm, hoi_nhieu, log, rut_json

GOC = os.path.join(ROOT, "ra", "storyboard")
SO_ANH_MAC_DINH = 4
TI_LE = ("16:9", "9:16", "1:1", "4:3", "3:4")
KICH_THUOC = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:3": (1440, 1080), "3:4": (1080, 1440)}
PHONG_CACH = {
    # 25/10 xem khung hình thật của kênh Lạnh Vcl: vẽ tay kiểu MS Paint, đầu to thân nhỏ, mặt meme trắng, nền tường một màu
    "lanh_vcl_meme": "crude hand-drawn 2D cartoon in MS Paint style, thick slightly uneven black outlines, flat solid fill colors with zero shading and no gradients, plain single-color walls and a flat floor plane, simple flat furniture drawn in basic perspective, chibi characters with oversized round heads on small thin bodies, blank white meme faces drawn with almost nothing: two tiny black dot eyes (or two flat lines for a bored side-eye), a single short line mouth, no nose, no eyelashes, no irises, no eye highlights, no blush (NOT anime, NOT manga, NOT webtoon faces), a deadpan side-eye look, characters told apart by hair color and outfit color, occasional realistic photo cut-out objects pasted onto the cartoon scene like a collage, amateur YouTube storytelling animation look, no 3D, no realistic rendering of people",
    "manhwa_clean": "clean modern 2D graphic novel illustration, semi-realistic manhwa art style, sharp stylish character with neat hair and clear eyes, cinematic atmospheric lighting, crisp ink outlines, clean aesthetics without dark eye bags or tired look",
    "dien_anh": "cinematic photorealistic film still, natural light, shallow depth of field, rich natural color grade, 35mm photography",
    "dark_gritty": "2D dark gritty comic graphic novel art style, deep high-contrast shadows, chiaroscuro dramatic lighting, muted desaturated tones with intense accent colors, sharp ink line art",
    "hoat_hinh_3d": "high-quality 3D animated film still (Pixar/Dreamworks style), soft global illumination, expressive stylized characters, rich textures",
    "anime": "anime film key frame, clean expressive line art, cel shading, detailed painted background, vibrant cinematic anime aesthetic",
    "minh_hoa": "detailed digital illustration, painterly storybook style, soft textured brushwork, rich atmospheric mood",
    "tai_lieu": "documentary photograph, real-life candid moment, natural available light, authentic true-to-life colors",
    "cyberpunk": "cyberpunk cinematic aesthetic, neon blue and magenta lighting, atmospheric volumetric fog, futuristic urban tech mood",
    "tu_do": "custom artistic style, consistent rendering technique and lighting mood",
}


_KHOA = threading.RLock()
_SB = {}                     # id -> dict storyboard (bản trong bộ nhớ, ghi đĩa sau mỗi thay đổi)
TT = {}                      # id -> {dang, viec, dong[], loi, dung}


# --------------------------------------------------------------------------- lưu / đọc
def _slug(s):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", _bo_dau(str(s or ""))).strip("_")
    return s[:40] or "storyboard"


def _bo_dau(s):
    import unicodedata
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def thu_muc(sid):
    return os.path.join(GOC, sid)


def _p(sid):
    return os.path.join(thu_muc(sid), "storyboard.json")


def doc(sid):
    with _KHOA:
        if sid not in _SB:
            sb = doc_json(_p(sid), None)
            if not sb:
                raise ValueError(f"không thấy storyboard «{sid}»")
            _SB[sid] = sb
        return _SB[sid]


def luu(sid):
    with _KHOA:
        sb = _SB.get(sid)
        if sb:
            sb["cap_nhat"] = time.time()
            os.makedirs(thu_muc(sid), exist_ok=True)
            ghi_json(_p(sid), sb)


def ds():
    ra = []
    if os.path.isdir(GOC):
        for f in os.listdir(GOC):
            sb = doc_json(os.path.join(GOC, f, "storyboard.json"), None)
            if sb:
                ra.append({"id": f, "ten": sb.get("ten") or f, "cap_nhat": sb.get("cap_nhat") or 0,
                           "so_canh": len(sb.get("canh") or []), "so_asset": len(sb.get("assets") or [])})
    return sorted(ra, key=lambda x: -x["cap_nhat"])


def tao(ten, kich_ban, cai_dat=None):
    sid = _slug(ten) + "_" + time.strftime("%m%d%H%M%S")
    sb = {"id": sid, "ten": str(ten or sid).strip(), "kich_ban": str(kich_ban or ""), "tao": time.time(),
          "cai_dat": _cai_dat(cai_dat), "phong_cach_chung": "", "assets": [], "canh": []}
    with _KHOA:
        _SB[sid] = sb
    luu(sid)
    return sb


def _cai_dat(c):
    c = dict(c or {})
    return {"so_anh": max(1, min(10, int(c.get("so_anh") or SO_ANH_MAC_DINH))),
            "so_canh": max(0, min(40, int(c.get("so_canh") or 0))),
            "ti_le": c.get("ti_le") if c.get("ti_le") in TI_LE else "16:9",
            "phong_cach": c.get("phong_cach") if c.get("phong_cach") in PHONG_CACH else "dien_anh",
            "phong_cach_them": str(c.get("phong_cach_them") or "").strip()[:800],
            "nhan_vat_dong_nhat": str(c.get("nhan_vat_dong_nhat") or "").strip()[:1000],
            # 23/10 user "quá chậm": nối tiếp bắt vẽ LẦN LƯỢT trong scene (~90 s/ảnh, chỉ 1 hồ sơ/scene) -> mặc định TẮT,
            # mọi ảnh vẽ song song; nhân vật vẫn giữ nhờ ảnh asset tham chiếu + mô tả cố định
            "noi_tiep": c.get("noi_tiep") is True,
            "giay_anh": max(0.5, min(20.0, float(c.get("giay_anh") or 3))),
            "khoa_boi_canh": c.get("khoa_boi_canh", True) is not False,
            "che_do_canh": c.get("che_do_canh") if c.get("che_do_canh") in ("tu_dong", "theo_thoai") else "tu_dong",
            "plugin_id": str(c.get("plugin_id") or "").strip()[:80],   # plugin kênh: chia cảnh theo cách kênh minh hoạ
            # 25/10 user: nhân vật KHÔNG để AI vẽ mỗi cảnh -> dán con rối (kho nhân vật đã duyệt / con rối code) vào nền
            "con_roi": c.get("con_roi") is True,
            "kho_nv": [str(x) for x in (c.get("kho_nv") or []) if str(x).strip()][:8]}



def sua(sid, d):
    """Lưu chỉnh tay từ giao diện: tên, kịch bản, cài đặt, mô tả asset, câu lệnh ảnh / video của scene."""
    with _KHOA:
        sb = doc(sid)
        if "ten" in d:
            sb["ten"] = str(d["ten"] or sb["ten"]).strip()
        if "kich_ban" in d:
            sb["kich_ban"] = str(d["kich_ban"] or "")
        if "cai_dat" in d:
            sb["cai_dat"] = _cai_dat(dict(sb.get("cai_dat") or {}, **(d["cai_dat"] or {})))
        if "phong_cach_chung" in d:
            sb["phong_cach_chung"] = str(d["phong_cach_chung"] or "")
        for a in d.get("assets") or []:
            x = _asset(sb, a.get("id"))
            if x:
                for k in ("ten", "mo_ta_vi", "mo_ta_en"):
                    if k in a:
                        x[k] = str(a[k] or "")
                if "chon" in a:
                    x["chon"] = int(a["chon"] or 0)
        for c in d.get("canh") or []:
            x = _canh(sb, c.get("id"))
            if not x:
                continue
            for k in ("tieu_de", "tom_tat_vi", "video_prompt_en"):
                if k in c:
                    x[k] = str(c[k] or "")
            if "so_anh" in c:
                x["so_anh"] = max(1, min(10, int(c["so_anh"] or 1)))
            for a in c.get("anh") or []:
                y = next((z for z in x["anh"] if z["id"] == a.get("id")), None)
                if y:
                    for k in ("prompt_en", "mo_ta_vi"):
                        if k in a:
                            y[k] = str(a[k] or "")
                    if "chon" in a:
                        y["chon"] = int(a["chon"] or 0)
    luu(sid)
    return doc(sid)


def xoa(sid):
    import shutil
    with _KHOA:
        _SB.pop(sid, None)
    p = os.path.realpath(thu_muc(sid))
    if p.startswith(os.path.realpath(GOC) + os.sep):
        shutil.rmtree(p, ignore_errors=True)


def _asset(sb, aid):
    return next((a for a in sb.get("assets") or [] if a["id"] == aid), None)


def _canh(sb, cid):
    try:
        cid = int(cid)
    except (TypeError, ValueError):
        return None
    return next((c for c in sb.get("canh") or [] if c["id"] == cid), None)


def anh_chon(muc):
    """Ảnh đang chọn của một asset / một ảnh scene (None nếu chưa vẽ)."""
    bt = [f for f in muc.get("bien_the") or [] if f and os.path.isfile(f)]
    if not bt:
        return None
    return bt[min(int(muc.get("chon") or 0), len(bt) - 1)]


# --------------------------------------------------------------------------- việc chạy nền
def _bao(sid, m):
    tt = TT.setdefault(sid, {})
    tt.setdefault("dong", []).append(time.strftime("%H:%M:%S ") + m)
    tt["dong"] = tt["dong"][-120:]
    log(f"[storyboard {sid}] {m}")


def dang_chay(sid):
    return bool((TT.get(sid) or {}).get("dang"))


def chay(sid, viec, ham):
    """Chạy ham(bao) ở luồng nền; một storyboard một việc lớn một lúc (video chạy riêng, xem tao_video)."""
    doc(sid)
    tt = TT.setdefault(sid, {})
    if tt.get("dang"):
        raise RuntimeError(f"đang chạy «{tt.get('viec')}» — chờ xong hoặc bấm Dừng")
    tt.update(dang=True, viec=viec, loi="", dung=False, bd=time.time())

    def chay_nen():
        try:
            ham(lambda m: _bao(sid, m))
            _bao(sid, f"✔ Xong: {viec}" + (" (đã dừng giữa chừng)" if tt.get("dung") else ""))
        except Exception as e:                               # noqa: BLE001
            tt["loi"] = str(e)[:400]
            _bao(sid, f"✖ Lỗi {viec}: {str(e)[:300]}")
        tt["dang"] = False
        luu(sid)
    threading.Thread(target=chay_nen, daemon=True).start()


def dung(sid):
    tt = TT.get(sid) or {}
    if tt.get("dang"):
        tt["dung"] = True
        _bao(sid, "⚠ Đã yêu cầu dừng — ảnh đang vẽ dở sẽ xong rồi mới dừng")


def _da_dung(sid):
    return bool((TT.get(sid) or {}).get("dung"))


# --------------------------------------------------------------------------- AI: assets
_P_ASSET = """You are the pre-production designer of an AI-generated film. Read the SCRIPT (any language, usually Vietnamese)
and build the ASSET BIBLE that every image of the storyboard will reuse, so that characters stay 100% IDENTICAL from the
first frame to the last.

Global visual art style chosen by the user: {phong_cach}
{user_nv_rule}

Return:
  "phong_cach_chung": ONE English sentence fixing the visual style for EVERY image (medium, lens/film look, color grade,
     lighting mood, art style). Respect the user's chosen style above.
  "assets": every RECURRING CHARACTER (named or not: "the protagonist", "the mother"…, also animals/creatures that act), every
     main LOCATION, and only the PROPS that matter to the plot (a letter, a car, a sword…). Each item:
     - "id": "NV1","NV2"… for characters, "BC1"… for locations, "DC1"… for props
     - "loai": "nhan_vat" | "boi_canh" | "dao_cu"
     - "ten": short name as used in the script (keep the script's language)
     - "mo_ta_vi": 1-2 Vietnamese sentences for the editor
     - "mo_ta_en": the FIXED visual identity in English, written so a painter could redraw the exact same thing every time.
         Characters (70-110 words): gender, exact age, ethnicity, height and build, face shape, eyes, eyebrows, nose, skin
         tone, hairstyle + hair color + length, facial hair, distinctive marks; ONE default outfit with exact garments,
         colors, materials and footwear; accessories. Period-correct for the story's era. No personality words, only
         visible facts. Never a real famous person.
         Locations (50-80 words): place type, era, architecture/nature, materials, colors, key landmarks/objects that
         make it recognizable, default time of day and weather.
         Props (25-50 words): shape, size, material, color, wear and tear.
CAST THE WHOLE WORLD OF THE SCRIPT, not only the protagonist. The script is often a NARRATION (second person "bạn", an
essay, a life lesson) with few named people — you must still cast every kind of person it mentions or implies (the boss,
coworkers, friends who take advantage, family members, a partner, strangers, "thiên hạ" / the crowd, a rich man, a
beggar…) as supporting characters NV2, NV3… (a recurring group may be ONE asset, e.g. "nhóm đồng nghiệp"), and one LOCATION
for EVERY distinct real-life situation the narration evokes (office, crowded bus, family dinner table, rainy street,
café, hospital corridor, rooftop at night…) — never a single empty room for the whole film.
Supporting characters use the same art style but must be instantly distinguishable from NV1 and from each other
(different hair, build, outfit colors, accessories).
SETTING: when the script is Vietnamese and does not say otherwise, the story happens in present-day VIETNAM — Vietnamese
tube houses, narrow alleys, motorbikes, plastic stools, street food stalls, Vietnamese apartments, offices and buses;
never American or European streets and buildings.
Usually 3-8 characters and 2-8 props. LOCATIONS: a narration needs about ONE location per 3-4 sentences (20 sentences ->
at least 5 locations, e.g. bedroom, apartment corridor, bus, office, street, family table) because every abstract line
will be illustrated by an everyday example situation somewhere else.
Only JSON: {{"phong_cach_chung": "...", "assets": [{{"id": "NV1", "loai": "nhan_vat", "ten": "...", "mo_ta_vi": "...", "mo_ta_en": "..."}}]}}

SCRIPT:
{kb}"""


# bảng màu vai phụ con rối code (khi AI không chọn) — tóc / áo / quần khác hẳn nhau
_BANG_VAI_PHU = [
    {"toc": "hoi", "mau_toc": "#8a5a2b", "ao": "so_mi", "mau_ao": "#f2d24b", "mau_quan": "#3b3b3b"},
    {"toc": "dau_dinh", "mau_toc": "#c0392b", "ao": "phong", "mau_ao": "#3fae5a", "mau_quan": "#1f2a5a"},
    {"toc": "mai_dai", "mau_toc": "#2b1d14", "ao": "ba_lo", "mau_ao": "#f4a6c0", "mau_quan": "#222222"},
    {"toc": "ngan", "mau_toc": "#555555", "ao": "khoac", "mau_ao": "#e67e22", "mau_quan": "#4a3b2a"},
    {"toc": "buoc", "mau_toc": "#d4a017", "ao": "phong", "mau_ao": "#9b59b6", "mau_quan": "#2b2b2b"},
]


def _kieu_nv_kenh(cd):
    """Dáng thân / cỡ đầu / màu da nhân vật của kênh gốc (plugin) -> áp cho mọi con rối code của storyboard."""
    pid = cd.get("plugin_id")
    if not pid:
        return {}
    import json
    try:
        cr = json.load(open(os.path.join(ROOT, "plugins_doi_thu", f"{pid}.json"), encoding="utf-8"))["nhan_vat"].get("con_roi") or {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    return {k: cr[k] for k in ("than", "dau", "mau_da") if cr.get(k)}


def _luat_con_roi_asset(cd):
    """Chế độ con rối: AI gán vai trong kịch bản cho nhân vật trong kho (đã duyệt) hoặc chọn thông số con rối code."""
    if not cd.get("con_roi"):
        return ""
    import con_roi
    import kho_nhan_vat
    kho = []
    for nid in cd.get("kho_nv") or []:
        try:
            n = kho_nhan_vat.doc(nid)
            kho.append(f'- "{nid}": {n["ten"]} — {n.get("mo_ta") or ""}')
        except ValueError:
            continue
    return ("\n\nPUPPET MODE: characters are NOT drawn by the image generator — they are hand-drawn puppets pasted onto the "
            "backgrounds. For every character asset (loai nhan_vat) add:\n"
            + ('  "kho": the id of the puppet below that plays this role (the protagonist MUST use one of them), or "" if none fits:\n'
               + "\n".join(kho) + "\n" if kho else "")
            + f'  "hinh": for roles without a puppet, its look as {{"toc": one of {list(con_roi.TOC)}, "mau_toc": "#hex", '
            f'"ao": one of {list(con_roi.AO)}, "mau_ao": "#hex", "mau_quan": "#hex"}} — colors clearly different from the '
            "other characters.\nLocations (BC…) are EMPTY places with no people, drawn in the channel's crude style.")


def lap_assets(sid, bao):
    sb = doc(sid)
    kb = (sb.get("kich_ban") or "").strip()
    if not kb:
        raise ValueError("chưa nhập kịch bản")
    cd = sb["cai_dat"]
    pc = PHONG_CACH.get(cd.get("phong_cach")) or PHONG_CACH["dien_anh"]
    if cd.get("phong_cach_them"):
        pc = pc + ". " + cd["phong_cach_them"]

    user_nv = str(cd.get("nhan_vat_dong_nhat") or "").strip()
    if user_nv:
        user_nv_rule = f"""
CRITICAL MANDATORY INSTRUCTION FOR MAIN CHARACTER (NV1):
The user has specified an exact fixed character appearance:
"{user_nv}"
You MUST adopt this EXACT character identity for the protagonist (NV1) in "mo_ta_en" (enrich with concrete physical details: age, hairstyle, face, specific clothing and colors), ensuring NV1 represents this exact character throughout."""
    else:
        user_nv_rule = ""

    bao("AI đang đọc kịch bản và lập danh sách assets đồng nhất (nhân vật, phong cách, bối cảnh)…")
    j = None
    # 25/10 (thử 20 câu Lạnh Vcl, 2 lần): AI chỉ lập 2 bối cảnh dù được dặn 5+ -> cả phim dồn vào một phòng. Đếm số câu,
    # thiếu bối cảnh thì hỏi lại kèm lời nhắc cụ thể
    from tach_canh import tach_cau
    can_bc = max(2, min(12, len(tach_cau(kb)) // 4))
    nhac, tot = "", None
    them_roi = _luat_con_roi_asset(cd)
    for _ in range(3):
        prompt_txt = _P_ASSET.format(phong_cach=pc, user_nv_rule=user_nv_rule, kb=kb[:24000]) + them_roi + nhac
        j = rut_json(hoi_llm(prompt_txt, timeout=300) or "")
        if not (isinstance(j, dict) and j.get("assets")):
            continue
        so_bc = sum(1 for a in j["assets"] if isinstance(a, dict) and (a.get("loai") == "boi_canh"
                                                                     or str(a.get("id", "")).upper().startswith("BC")))
        if tot is None or so_bc > tot[0]:
            tot = (so_bc, j)
        if so_bc >= can_bc:
            break
        bao(f"  AI chỉ lập {so_bc} bối cảnh (cần ≥ {can_bc}) — hỏi lại…")
        nhac = (f"\n\nYOUR PREVIOUS ANSWER HAD ONLY {so_bc} LOCATIONS. This script has {len(tach_cau(kb))} sentences: return AT "
                f"LEAST {can_bc} distinct everyday locations (BC…) where its example situations happen.")
    j = tot[1] if tot else j
    if not isinstance(j, dict) or not j.get("assets"):
        raise ValueError("AI không trả danh sách assets (thử lại)")
    cu = {a["id"]: a for a in sb.get("assets") or []}
    ra = []
    for a in j["assets"]:
        if not isinstance(a, dict) or not str(a.get("mo_ta_en") or "").strip():
            continue
        aid = str(a.get("id") or "").strip().upper() or f"A{len(ra) + 1}"
        loai = a.get("loai") if a.get("loai") in ("nhan_vat", "boi_canh", "dao_cu") else (
            "boi_canh" if aid.startswith("BC") else "dao_cu" if aid.startswith("DC") else "nhan_vat")
        x = {"id": aid, "loai": loai, "ten": str(a.get("ten") or aid).strip(), "mo_ta_vi": str(a.get("mo_ta_vi") or "").strip(),
             "mo_ta_en": str(a["mo_ta_en"]).strip(), "bien_the": [], "chon": 0, "tt": "cho", "loi": ""}
        if cd.get("con_roi") and loai == "nhan_vat":
            kho = str(a.get("kho") or "").strip()
            x["kho"] = kho if kho in (cd.get("kho_nv") or []) else ""
            hinh = a.get("hinh") if isinstance(a.get("hinh"), dict) and a["hinh"].get("mau_ao") else {}
            if not x["kho"] and not hinh:                    # AI không chọn màu: gán bảng màu riêng, khác nhân vật khác
                hinh = dict(_BANG_VAI_PHU[sum(1 for y in ra if y["loai"] == "nhan_vat") % len(_BANG_VAI_PHU)])
            x["hinh"] = dict(hinh, **_kieu_nv_kenh(cd))
        c = cu.get(aid)
        if c and c.get("mo_ta_en") == x["mo_ta_en"]:            # mô tả không đổi -> giữ ảnh đã vẽ
            x.update(bien_the=c.get("bien_the") or [], chon=c.get("chon") or 0, tt=c.get("tt") or "cho")
        ra.append(x)
    with _KHOA:
        # 25/10 (thử Lạnh Vcl): AI viết lại phong cách thành một câu ngắn và LÀM RƠI chi tiết (mặt meme -> mặt truyện tranh)
        # -> người dùng đã chọn preset / tự nhập phong cách thì giữ NGUYÊN VĂN; chỉ preset mặc định mới dùng câu của AI
        tu_chon = cd.get("phong_cach") not in (None, "", "dien_anh", "tu_do") or cd.get("phong_cach_them")
        sb["phong_cach_chung"] = (pc if tu_chon else str(j.get("phong_cach_chung") or pc)).strip().rstrip(".") + "."
        sb["assets"] = ra
    luu(sid)
    bao(f"Có {len(ra)} assets: " + ", ".join(f"{a['id']} {a['ten']}" for a in ra))



# --------------------------------------------------------------------------- AI: scene
_P_DAN_Y = """You are the director of an AI-generated film. Split the SCRIPT into SCENES that follow each other in story
order and together cover the WHOLE script (no gap, no overlap, no invented events). {so_canh}
A new scene starts when the place, the time, or a dramatic dialogue beat changes.

CONTINUITY & BACKGROUND LOCK:
Consecutive beats that REALLY stay in the same situation keep the SAME 'boi_canh' (BC...) — background identical, only
camera framing and actions change. But as soon as a line evokes ANOTHER situation (an example, a memory, a consequence,
"people out there", work, family, money…), switch to the location where that situation actually happens. A narration
must travel through the places of the story, not stay in one room.

SHOW WHAT IS SAID: every scene must make its line understandable with the sound OFF. Turn abstract or inner lines into
a concrete, filmable moment with OTHER PEOPLE and OBJECTS: "you always give way to others" -> the protagonist steps aside
on a crowded bus while others push past; "they only call you when they need money" -> a friend grinning, hand out, the
protagonist opening a thin wallet; "you smile to please everyone" -> a forced smile at a noisy table of relatives.
Use a clear VISUAL METAPHOR when the line has no literal action.

VISUAL RHYTHM (like a YouTube storytelling channel — cut often, show examples):
- Never more than 3 scenes in a row in the same location; never 2 face close-ups in a row.
- An ABSTRACT line (a belief, a feeling, a moral, "that is a sweet trap") is NEVER the protagonist making a face: cut to a
  concrete EVERYDAY EXAMPLE of it in its own place with other people, to a close-up INSERT of a meaningful object, or to
  a visual METAPHOR.
- Mix the frame types: "rong" (wide situation shot with the people involved), "trung" (medium, two people interacting),
  "can_mat" (face close-up, only for a strong reaction), "can_do_vat" (insert: hands, wallet, shoes, door, food…),
  "man_hinh" (a phone / laptop / TV screen held by a hand: messages, calls, social media, bank balance),
  "an_du" (visual metaphor), "ngoai_canh" (exterior of a new place).
{minh_hoa}
{che_do_thoai_rule}

ASSET BIBLE (use these ids only):
{assets}
{continuity_context}

For each scene:
  - "id": 1, 2, 3… (sequential index)
  - "tieu_de": short Vietnamese title
  - "loi": the exact part of the script this scene covers (copy it, keep the original language)
  - "tom_tat_vi": 1-2 Vietnamese sentences: what happens visually
  - "boi_canh": the location id (BC…), or "" for a one-off place / an insert (then describe the place in "dan_dung_en")
  - "khung": the frame type, one of rong | trung | can_mat | can_do_vat | man_hinh | an_du | ngoai_canh
  - "nhan_vat": ids of ALL characters who appear (protagonist AND supporting characters / crowd NV…), and props (DC…).
    Every person visible in the frame MUST be a bible character listed here — never invent a new person (a metaphor
    showing "you" lists NV1); a frame with no id listed shows NO people at all
  - "dan_dung_en": STAGING, 2-3 English sentences: the concrete moment that shows this line — exact spot in the location,
    what the supporting characters / crowd are doing and how they relate to the protagonist, the key props, foreground /
    background elements, and the visual metaphor if the line is abstract
  - "noi_tiep": one English sentence: how this scene picks up from the previous one (continuity: location, characters, time of day).
  - "video_prompt_en": an 8-second AI video prompt (Google Veo) used as a HOOK for this scene, 50-90 words: starts from the
    first image of the scene, the characters (by name) DOING a clear fluid action with natural body motion and facial
    expression, one cinematic camera move (slow push-in, tracking, crane, handheld follow…), atmosphere, the dramatic beat.
    No text, no captions, no logos.
Only JSON: [{{"id": 1, "tieu_de": "...", "loi": "...", "tom_tat_vi": "...", "boi_canh": "BC1", "khung": "rong", "nhan_vat": ["NV1", "NV2"], "dan_dung_en": "...", "noi_tiep": "...", "video_prompt_en": "..."}}]

SCRIPT:
{kb}"""

_P_ANH = """You are the storyboard artist of an AI-generated film. Write the IMAGE PROMPTS (Google Flow / Nano Banana) for
the scenes below. The images of one scene are consecutive frames of ONE continuous action, like a real storyboard.

GLOBAL STYLE (MUST BE ENFORCED IN EVERY SINGLE PROMPT): {pc}
ASSET BIBLE (characters must look EXACTLY like this in every image — same face, age, hair, build, outfit and colors —
whatever the location, time or weather; change clothes ONLY if the script explicitly says so):
{assets}

RULES for every image prompt ("prompt_en", 70-120 English words):
  0. SHOW WHAT THE LINE SAYS (most important): a viewer with the sound OFF must understand the scene's line from the
     image alone. Build the frame from the scene's "Staging": a concrete setting with at least 3 specific details
     (furniture, signs, weather, objects, light sources), the SUPPORTING CHARACTERS / crowd doing something that relates
     to the protagonist (talking, laughing at, ignoring, taking, pushing, hugging…), meaningful props, and a visual
     metaphor for abstract lines. Compose in depth: foreground element, subject in midground, story detail in background.
     NEVER a lone character on a plain or empty background showing only a facial expression; even a line about
     loneliness shows it through a meaningful place (a crowd walking past, an empty chair at a full table…).
  1. UNIFIED ART STYLE: the image style is prepended automatically — do not spend words repeating it.
  2. CHARACTERS: call them by name + id exactly as in the bible (e.g. "Minh (NV1)") with at most 2 recognizable features;
     their full appearance is appended automatically — spend the words on place, action, other people and props.
  3. BACKGROUND CONTINUITY: frames of the same location keep the same recognizable layout and landmarks; only camera
     angle, framing and acting change. A different location = a different, clearly described place.
     FRAME TYPE: when a scene gives a "Frame type", compose exactly that frame (an insert shows the object big in frame,
     an exterior shows the building / storefront, a wide shot shows the whole situation with the other people).
  4. VARY THE SHOT LIKE A CINEMATOGRAPHER: For dialogue and continuous scenes, rotate camera framing logically:
     - Establishing wide shot (sets the scene and characters in space)
     - Medium waist-up shot (character speaking, expressive hands and body posture)
     - Dynamic close-up shot (emotional facial expression matching the dialogue: warm smiling, joyful laughter, calm serenity, shocked wide eyes, intense anger, thoughtful reflection)
     - Over-the-shoulder / Reaction shot (listener's reaction or side profile).
     Never two identical framings in a row.
  5. NOT STIFF: every frame is a moment CAUGHT MID-ACTION — dynamic gesture matching the dialogue, natural asymmetric posture, hands busy, eyes focused on what they interact with. Never posed, never stiff, never looking directly into the camera lens.
  6. Describe the setting with the location's key landmarks so the place stays recognizable.
  7. No text, no captions, no subtitles, no logos, no watermarks, no split panels.
Also for each frame:
  - "mo_ta_vi": one short Vietnamese sentence for the editor
  - "nhan_vat": ids of the characters / props VISIBLE in this frame (empty list if none)
Write EXACTLY the number of frames asked for each scene.
Only JSON: [{{"canh": 1, "anh": [{{"prompt_en": "...", "mo_ta_vi": "...", "nhan_vat": ["NV1"]}}]}}]

SCENES:
{ds}"""


_KHUNG = {"rong": "wide situation shot showing the place and everyone involved",
          "trung": "medium shot of two or more people interacting",
          "can_mat": "big centered face close-up of the reacting character",
          "can_do_vat": "close-up insert of the key object (hands, wallet, phone screen held by a hand, shoes…), little or no face",
          "man_hinh": "close-up of a phone / laptop screen held by a hand",
          "an_du": "visual metaphor image",
          "ngoai_canh": "exterior establishing shot of the new place (storefront, building, street)"}


def _bible(sb, chi=None):
    return "\n".join(f"- {a['id']} ({a['loai']}) {a['ten']}: {a['mo_ta_en']}" for a in sb.get("assets") or []
                     if chi is None or a["id"] in chi)


def _chia_doan_kich_ban(kb, max_chars=3200):
    """Chia kịch bản dài thành các đoạn hợp lý theo đoạn văn hoặc câu để AI xử lý tuần tự không bị nuốt chữ."""
    kb = str(kb or "").strip()
    if len(kb) <= max_chars:
        return [kb]
    doan = [d.strip() for d in re.split(r"\n\s*\n", kb) if d.strip()]
    if len(doan) <= 1:
        doan = [d.strip() for d in kb.split("\n") if d.strip()]
    if len(doan) <= 1:
        from tach_canh import tach_cau
        doan = tach_cau(kb)

    chunks, hien_tai, dai = [], [], 0
    for d in doan:
        if dai + len(d) > max_chars and hien_tai:
            chunks.append("\n\n".join(hien_tai))
            hien_tai, dai = [d], len(d)
        else:
            hien_tai.append(d)
            dai += len(d)
    if hien_tai:
        chunks.append("\n\n".join(hien_tai))
    return chunks


def _minh_hoa_kenh(sb):
    """Khối "kênh gốc minh hoạ thế nào" từ plugin kênh (thư viện học ở bước phân tích kênh) -> ví dụ mẫu cho bước chia cảnh."""
    pid = (sb.get("cai_dat") or {}).get("plugin_id")
    if not pid:
        return ""
    import json
    try:
        mh = json.load(open(os.path.join(ROOT, "plugins_doi_thu", f"{pid}.json"), encoding="utf-8")).get("minh_hoa") or {}
    except (OSError, ValueError):
        return ""
    vi_du = [x for x in mh.get("vi_du") or [] if x.get("cach_en")]
    if not vi_du and not mh.get("quy_tac"):
        return ""
    return ("\nHOW THE ORIGINAL CHANNEL ILLUSTRATES ITS NARRATION (learned from its real video frames) — illustrate the same "
            "kinds of lines the same way:\n" + "\n".join(f"- {q}" for q in mh.get("quy_tac") or [])
            + ("\nExamples (line -> frame type -> what the channel drew):\n"
               + "\n".join(f"- «{x['cau']}» -> {x.get('khung')} -> {x['cach_en']}" for x in vi_du[:30]) if vi_du else "") + "\n")


def _kiem_nhip(ds):
    """Lỗi nhịp hình của danh sách scene AI trả: >3 scene liền cùng bối cảnh, 2 cận mặt liền nhau -> [mô tả lỗi]."""
    loi, i = [], 0
    while i < len(ds):
        k = i
        bc = str(ds[i].get("boi_canh") or "")
        while k + 1 < len(ds) and bc and str(ds[k + 1].get("boi_canh") or "") == bc:
            k += 1
        if bc and k - i + 1 > 3:
            loi.append(f"scenes {ds[i].get('id')}-{ds[k].get('id')} are {k - i + 1} in a row in {bc} (max 3)")
        i = k + 1
    for a, b in zip(ds, ds[1:]):
        if a.get("khung") == "can_mat" and b.get("khung") == "can_mat":
            loi.append(f"scenes {a.get('id')} and {b.get('id')} are two face close-ups in a row")
    return loi


def lap_canh(sid, bao):
    sb = doc(sid)
    if not sb.get("assets"):
        lap_assets(sid, bao)
        sb = doc(sid)
    kb = (sb.get("kich_ban") or "").strip()
    cd = sb["cai_dat"]
    n = cd["so_canh"]
    che_do = cd.get("che_do_canh", "tu_dong")

    che_do_thoai_rule = ""
    if che_do == "theo_thoai":
        che_do_thoai_rule = """CRITICAL DIALOGUE-DRIVEN RULE (1 SPOKEN SENTENCE = 1 SCENE WITH DEDICATED IMAGE DESCRIPTION):
Break down the script closely so that EVERY SINGLE SPOKEN SENTENCE or dialogue line becomes its own separate scene.
- MANDATORY: Do NOT merge multiple sentences into one scene. If the script has N sentences, output N scenes in exact order, with 'loi' being that exact sentence text.
- For each scene, create a distinct visual frame tailored specifically to what is spoken in that sentence.
- Identify the specific speaker character (NV...) and their conversational facial expression (warm smiling, joyful laughing, calm tranquil, serious, angry, shocked, thoughtful, anxious...).
- A facial expression alone is NOT a scene: every sentence gets its own concrete situation in "dan_dung_en" (place, other people, props or a visual metaphor) that illustrates exactly what the sentence says.
- Keep the same 'boi_canh' only while the sentences stay in the same situation (vary the shot: wide, medium, close-up, over-the-shoulder); change location when the sentence talks about another situation."""

    chunks = _chia_doan_kich_ban(kb, max_chars=3200)
    if len(chunks) > 1:
        bao(f"Kịch bản dài ({len(kb)} ký tự) — chia thành {len(chunks)} phần để AI mô tả chi tiết, giữ nguyên mọi câu thoại…")
    else:
        bao("AI đang chia kịch bản thành các scene nối tiếp" + (" (đồng bộ theo từng câu thoại)" if che_do == "theo_thoai" else "") + "…")

    ids = {a["id"] for a in sb["assets"]}
    canh_tat_ca = []

    for idx, chunk_txt in enumerate(chunks):
        if _da_dung(sid):
            return
        if len(chunks) > 1:
            bao(f"Đang xử lý phần {idx + 1}/{len(chunks)} của kịch bản…")

        continuity_ctx = ""
        if canh_tat_ca:
            prev = canh_tat_ca[-1]
            continuity_ctx = (f"PREVIOUS SCENE CONTEXT: Scene {len(canh_tat_ca)} ended in location '{prev.get('boi_canh')}' "
                              f"with characters {prev.get('nhan_vat')}. What happened: {prev.get('tom_tat_vi')}. "
                              f"Continue seamlessly from this state.")

        so_canh_prompt = ""
        if n:
            so_canh_prompt = f"Make around {max(1, n // len(chunks))} scenes for this part."
        else:
            so_canh_prompt = ("Create one scene per key dialogue beat/spoken sentence." if che_do == "theo_thoai"
                              else "Choose the number of scenes yourself (usually 3-12, one per story beat).")

        prompt_txt = _P_DAN_Y.format(
            so_canh=so_canh_prompt,
            che_do_thoai_rule=che_do_thoai_rule,
            minh_hoa=_minh_hoa_kenh(sb),
            assets=_bible(sb),
            continuity_context=continuity_ctx,
            kb=chunk_txt
        )

        j = None
        nhac, tot = "", None
        for _ in range(3):
            j = rut_json(hoi_llm(prompt_txt + nhac, timeout=300) or "")
            if not (isinstance(j, list) and j):
                continue
            loi_nhip = _kiem_nhip([x for x in j if isinstance(x, dict)])
            if tot is None or len(loi_nhip) < len(tot[0]):
                tot = (loi_nhip, j)
            if not loi_nhip:
                break
            bao(f"  Nhịp cảnh chưa đạt ({'; '.join(loi_nhip)[:160]}) — hỏi lại…")
            nhac = ("\n\nYOUR PREVIOUS SPLIT BROKE THE VISUAL RHYTHM: " + "; ".join(loi_nhip) + ". Redo it: move abstract lines "
                    "to everyday example situations in OTHER locations, object inserts or metaphors.")
        j = tot[1] if tot else j
        if not isinstance(j, list) or not j:
            if len(chunks) == 1:
                raise ValueError("AI không chia được scene (thử lại)")
            bao(f"  ! phần {idx + 1} AI không trả scene, bỏ qua phần này")
            continue

        for c in (x for x in j if isinstance(x, dict)):
            new_id = len(canh_tat_ca) + 1
            canh_tat_ca.append({
                "id": new_id,
                "tieu_de": str(c.get("tieu_de") or f"Scene {new_id}").strip(),
                "loi": str(c.get("loi") or "").strip(),
                "tom_tat_vi": str(c.get("tom_tat_vi") or "").strip(),
                "boi_canh": c.get("boi_canh") if c.get("boi_canh") in ids else "",
                "nhan_vat": [x for x in (c.get("nhan_vat") or []) if x in ids],
                "noi_tiep": str(c.get("noi_tiep") or "").strip(),
                "dan_dung_en": str(c.get("dan_dung_en") or "").strip(),
                "khung": str(c.get("khung") or "").strip(),
                "video_prompt_en": str(c.get("video_prompt_en") or "").strip(),
                "so_anh": 1 if che_do == "theo_thoai" else cd["so_anh"], "anh": [], "video": {}
            })

    if not canh_tat_ca:
        raise ValueError("AI không tạo được scene nào từ kịch bản (thử lại)")

    with _KHOA:
        sb["canh"] = canh_tat_ca
    luu(sid)
    bao(f"Có {len(canh_tat_ca)} scene — đang viết câu lệnh {cd['so_anh']} ảnh mỗi scene…")
    lap_anh_canh(sid, [c["id"] for c in canh_tat_ca], bao)


def _tu_the_cho(sb, a):
    """Tư thế được phép của một nhân vật: con rối kho -> chỉ tư thế ĐÃ DUYỆT; con rối code -> mọi tư thế."""
    import kho_nhan_vat
    if a.get("kho"):
        da = list(kho_nhan_vat.tu_the_da_duyet(a["kho"]))
        if da:
            return da
    return list(kho_nhan_vat.TU_THE)


def _luat_con_roi_anh(sb):
    if not (sb.get("cai_dat") or {}).get("con_roi"):
        return ""
    import kho_nhan_vat
    dong = [f'  {a["id"]} ({a["ten"]}): ' + ", ".join(f'{k} ({kho_nhan_vat.TU_THE[k][0]})' for k in _tu_the_cho(sb, a)
                                                    if k in kho_nhan_vat.TU_THE)
            for a in sb.get("assets") or [] if a["loai"] == "nhan_vat"]
    return ("\n\nPUPPET MODE — characters are hand-drawn puppets pasted in by code, NOT drawn by the image generator:\n"
            "- Wide / medium / face close-up frames of a location: the location image is reused as the background; "
            "\"prompt_en\" is only a short note. Object inserts, screens, metaphors and exteriors are drawn by the image "
            "generator: their \"prompt_en\" must contain NO people at all (hands only as plain black silhouettes).\n"
            "- Add \"dat\" to every frame that shows characters: [{\"nv\": \"NV1\", \"tu_the\": <pose key>, \"x\": 0.15-0.85}] "
            "(x = horizontal position; people facing each other stand apart). A face close-up has exactly one character.\n"
            "Allowed pose keys per character (choose the one that best acts out the line):\n" + "\n".join(dong)
            + "\nJSON per frame: {\"prompt_en\": \"...\", \"mo_ta_vi\": \"...\", \"nhan_vat\": [\"NV1\"], \"dat\": [{\"nv\": \"NV1\", "
            "\"tu_the\": \"cui_dau_buon\", \"x\": 0.5}]}")


def _doc_dat(sb, dat):
    if not (sb.get("cai_dat") or {}).get("con_roi") or not isinstance(dat, list):
        return []
    import kho_nhan_vat
    ra = []
    for d in dat:
        if not isinstance(d, dict) or not _asset(sb, str(d.get("nv") or "")):
            continue
        tt = str(d.get("tu_the") or "")
        try:
            x = min(0.88, max(0.12, float(d.get("x"))))
        except (TypeError, ValueError):
            x = None
        ra.append({"nv": str(d["nv"]), "tu_the": tt if tt in kho_nhan_vat.TU_THE else "dung_binh_thuong", "x": x})
    return ra


def lap_anh_canh(sid, ids, bao, _lan=0):
    """AI viết câu lệnh ảnh cho các scene `ids` (lô 4 scene, hỏi song song); scene AI bỏ sót thì hỏi lại một lượt."""
    sb = doc(sid)
    canh = [c for c in sb["canh"] if c["id"] in ids]
    lo = [canh[i:i + 4] for i in range(0, len(canh), 4)]
    truoc = {c["id"]: (sb["canh"][k - 1] if k else None) for k, c in enumerate(sb["canh"])}

    def mo_ta(c):
        t = truoc.get(c["id"])
        return (f"Scene {c['id']} — {c['so_anh']} frames. Location: {c['boi_canh'] or 'see script'}. "
                f"Cast: {', '.join(c['nhan_vat']) or 'none'}.\n  Continuity: {c['noi_tiep']}\n"
                f"  What happens: {c['tom_tat_vi']}\n"
                + (f"  Frame type: {_KHUNG.get(c.get('khung'), c.get('khung'))}\n" if c.get("khung") else "")
                + (f"  Staging: {c['dan_dung_en']}\n" if c.get("dan_dung_en") else "")
                + f"  Script part: {c['loi'][:1500]}"
                + (f"\n  (Previous scene {t['id']} ended with: {t['tom_tat_vi']})" if t else ""))
    prompts = [_P_ANH.format(pc=sb.get("phong_cach_chung") or "", assets=_bible(sb), ds="\n\n".join(mo_ta(c) for c in l))
               + _luat_con_roi_anh(sb) for l in lo]
    kq = hoi_nhieu(prompts, timeout=300)
    thieu = []
    for k, l in enumerate(lo):
        j = rut_json(kq[k] or "")
        if not isinstance(j, list):                          # lô hỏng -> hỏi lại một lần
            j = rut_json(hoi_llm(prompts[k], timeout=300) or "")
        theo = {}
        for x in j if isinstance(j, list) else []:
            try:
                theo[int(str(x.get("canh")).strip())] = x.get("anh") or []
            except (TypeError, ValueError, AttributeError):
                continue
        with _KHOA:
            for c in l:
                ds_anh = [a for a in theo.get(c["id"], []) if isinstance(a, dict) and str(a.get("prompt_en") or "").strip()]
                if not ds_anh:
                    if _lan:
                        bao(f"  ! scene {c['id']}: AI không trả câu lệnh ảnh")
                    else:
                        thieu.append(c["id"])
                    continue
                c["anh"] = [{"id": i + 1, "prompt_en": str(a["prompt_en"]).strip(), "mo_ta_vi": str(a.get("mo_ta_vi") or "").strip(),
                             "nhan_vat": [x for x in (a.get("nhan_vat") or []) if _asset(sb, x)] or list(c["nhan_vat"]),
                             "dat": _doc_dat(sb, a.get("dat")),
                             "bien_the": [], "chon": 0, "tt": "cho", "loi": ""}
                            for i, a in enumerate(ds_anh[:c["so_anh"]])]
        luu(sid)
    if thieu:
        bao(f"  AI bỏ sót câu lệnh ảnh của {len(thieu)} scene — hỏi lại…")
        lap_anh_canh(sid, thieu, bao, _lan=1)
        return
    bao("Đã có câu lệnh ảnh: " + ", ".join(f"scene {c['id']} ({len(c['anh'])} ảnh)" for c in canh))


# --------------------------------------------------------------------------- vẽ
_KHONG_DO = ("Natural candid moment caught mid-motion: dynamic body language, weight shift, hands busy, expressive face "
             "matching the emotion, eyes on what they interact with, subtle motion blur in hair and clothing; not posed, "
             "not stiff, not looking at the camera. No text, no captions, no logos, no watermark, single frame.")


def _cau_asset(sb, a):
    # 25/10 user (thử kênh Lạnh Vcl): PHONG CÁCH ĐỨNG ĐẦU và nhắc "vẽ đúng phong cách này" — câu lệnh cũ ("animation production
    # model sheet", "studio light", 4 góc + 6 biểu cảm) kéo ảnh tham chiếu thành tranh hoạt hình bóng bẩy khác hẳn ảnh cảnh,
    # rồi ảnh cảnh bắt chước theo tham chiếu -> lệch phong cách kênh
    pc = sb.get("phong_cach_chung") or ""
    giu = ("drawn EXACTLY in the art style above (same line work, same flat colors, same proportions and the same level of "
           "detail — do not make it more polished, more detailed or more realistic)")
    if a["loai"] == "nhan_vat":
        return (f"{pc}\nCharacter reference sheet of {a['ten']}, {giu}: {a['mo_ta_en']}\n"
                f"On one plain white sheet, left to right: full body front view, full body three-quarter view, full body side "
                f"view, then two big head close-ups (the signature expression, and one strong emotion). Identical face, hair, "
                f"outfit and colors in every view. Plain white background, no scenery. No text, no labels, no logos, no watermark.")
    if a["loai"] == "boi_canh":
        return (f"{pc}\nEstablishing wide shot of the empty location {a['ten']}, {giu}: {a['mo_ta_en']} "
                f"No people. No text, no logos, no watermark.")
    return (f"{pc}\nProp reference of {a['ten']}, {giu}: {a['mo_ta_en']} Isolated, centered, on a plain white background. "
            f"No text, no logos.")


def _khung_anh(c, a):
    """Loại khung của ẢNH: scene một ảnh / ảnh đầu của scene theo loại khung AI định; ảnh sau để tự do."""
    k = str(c.get("khung") or "")
    return k if k in _KHUNG and (len(c.get("anh") or []) <= 1 or a.get("id") == 1) else ""


def _lenh_khung(khung, so_nguoi):
    """25/10 user ("tự động hoàn toàn", không duyệt tay): khuôn câu lệnh CỐ ĐỊNH theo loại khung đứng đầu câu lệnh — lượt
    thử 4 có ảnh định cận đồ vật ra cảnh nhìn lưng, ảnh cảnh rộng nhân vật bé xíu giữa nền trống."""
    if khung == "rong":
        return ("FRAMING (mandatory): wide shot of the whole situation; the main character fills at least a quarter of the "
                "frame height" + ("; every person involved is clearly visible and interacting." if so_nguoi >= 2 else "."))
    return {"trung": "FRAMING (mandatory): medium shot, waist-up, of the people interacting; faces, hands and gestures "
                     "clearly visible.",
            "can_mat": "FRAMING (mandatory): big close-up of ONE face filling most of the frame; the background barely visible.",
            "can_do_vat": "FRAMING (mandatory): extreme close-up insert — the key object fills most of the frame; at most hands "
                          "or a sleeve are visible, no face.",
            "man_hinh": "FRAMING (mandatory): close-up of a smartphone or laptop screen filling most of the frame, held by a "
                        "plain black silhouette hand; the screen shows simple app shapes (avatar circle, message bubbles, "
                        "call buttons, numbers) with NO readable words.",
            "an_du": "FRAMING (mandatory): one clear symbolic image — the symbolic object large and centered, simple "
                     "uncluttered composition.",
            "ngoai_canh": "FRAMING (mandatory): exterior establishing shot from the outside (building, storefront, street); "
                          "people small or absent."}.get(khung, "")


def _cau_anh(sb, c, a, co_truoc, tham):
    """Câu lệnh đầy đủ của một ảnh scene + chú thích thứ tự ảnh tham chiếu."""
    nv = [_asset(sb, x) for x in a.get("nhan_vat") or []]
    nv = [x for x in nv if x and not ((sb.get("cai_dat") or {}).get("con_roi") and x.get("loai") == "nhan_vat")]
    bc = _asset(sb, c.get("boi_canh"))
    cd = sb.get("cai_dat") or {}
    khoa_bc = cd.get("khoa_boi_canh", True) is not False
    dong = []

    # 1. Phong cách ảnh đồng nhất luôn đứng đầu câu lệnh, rồi lệnh khung hình bắt buộc
    pc = sb.get("phong_cach_chung") or ""
    if pc:
        dong.append(f"Visual Art Style: {pc}.")
    lk = _lenh_khung(_khung_anh(c, a), sum(1 for x in nv if x.get("loai") == "nhan_vat"))
    if lk:
        dong.append(lk)

    # 2. Câu lệnh hành động và góc máy cụ thể của ảnh
    dong.append(a["prompt_en"])

    # 3. Nhân vật đồng nhất (Character Consistency)
    if nv:
        dong.append("Characters — keep them 100% identical to reference images and bible descriptions (same face, age, "
                    "hairstyle, build, outfit and colors): " + " ".join(f"{x['ten']} ({x['id']}): {x['mo_ta_en']}" for x in nv)
                    + " Nobody else appears unless the action above names them.")
    elif (sb.get("cai_dat") or {}).get("con_roi"):
        dong.append("No people and no characters in this frame (they are added separately); hands only as plain black "
                    "silhouettes.")
    elif not any(_asset(sb, x) for x in a.get("nhan_vat") or []):
        # 25/10 (thử 20 ảnh): khung ẩn dụ không khai nhân vật -> Flow tự vẽ một người lạ khác phong cách
        dong.append("No people and no characters in this frame — only the objects and the place described.")

    # 4. Khóa bối cảnh đồng nhất (Background Continuity Lock)
    if bc:
        if khoa_bc:
            dong.append(f"Locked Background Continuity — Setting {bc['ten']}: {bc['mo_ta_en']}. "
                        f"Maintain 100% identical room layout, architectural details, and lighting mood as the reference setting. "
                        f"Do not alter the background scenery; only camera framing and character actions change.")
        else:
            dong.append(f"Setting — {bc['ten']}: {bc['mo_ta_en']}")

    if tham:
        dong.append("Reference images in order: " + "; ".join(tham) + "."
                    + (" The reference marked previous frame is the frame just before this one: continue from it (same place, light and "
                       "continuity) but with a NEW camera angle and the action moved forward." if co_truoc else ""))
    dong.append(_KHONG_DO + _tranh(sb))
    return "\n".join(dong)


def _tranh(sb):
    """Danh sách "không được có" của phong cách kênh (plugin) — trước đây phân tích ra mà storyboard không dùng."""
    pid = (sb.get("cai_dat") or {}).get("plugin_id")
    if not pid:
        return ""
    import json
    try:
        neg = json.load(open(os.path.join(ROOT, "plugins_doi_thu", f"{pid}.json"), encoding="utf-8"))["nhan_vat"]["negative_prompt"]
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    return f" Avoid: {neg}." if str(neg or "").strip() else ""



def _so_luong():
    import flow_ve
    return flow_ve.so_luong_ve()                         # 25/10: mỗi hồ sơ nhiều lượt cùng lúc


def _sach_logo(files):
    try:
        import sys
        sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
        import anh_ve
        for f in files:
            # gwt chỉ nhận dấu ✦ của Gemini; ảnh Flow (dấu nhỏ hơn, gần mép hơn) -> tô lấp đúng chỗ bằng xoa_dau_gemini
            if not anh_ve.xoa_logo(f):
                anh_ve.xoa_dau_gemini(f, anh_ve.DAU_FLOW_CACH_MEP, anh_ve.DAU_FLOW_BAN_KINH)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! storyboard: xoá logo lỗi {str(e)[:80]}")


def _viet_lai_an_toan(prompt):
    """Câu lệnh bị Flow chặn vì chính sách -> bản viết lại tránh từ nhạy cảm (máu, vũ khí, bạo lực, trẻ em gặp nguy, thương
    hiệu thật…) nhưng giữ nguyên cảnh, nhân vật, khung hình và phong cách. '' nếu AI không trả."""
    p = ("This image-generation prompt was REJECTED by the generator's content policy. Rewrite it so it passes: keep the same "
         "scene meaning, characters, framing and the full style text, but replace anything violent, bloody, sexual, "
         "self-harm, weapons, injuries, children in danger, real people or brand names with mild, suggestive, symbolic "
         "wording. Return ONLY the rewritten prompt, nothing else.\n\nPROMPT:\n" + prompt)
    kq = (hoi_llm(p, timeout=120) or "").strip().strip("`").strip()
    return kq if len(kq) > 40 else ""


def _ve(sb, muc, prompt, thu, ten_goc, tham_chieu, bao, nhan):
    import flow_ve
    with _KHOA:
        muc.update(tt="dang", loi="")
    t0 = time.time()
    for lan in range(2):
        try:
            tep = flow_ve.ve_nhieu(prompt, thu, ten_goc + "_" + time.strftime("%H%M%S"), sb["cai_dat"]["ti_le"], tham_chieu)
        except Exception as e:                               # noqa: BLE001
            tep, muc["loi"] = [], str(e)[:200]
        loi = muc.get("loi") or flow_ve.loi_cuoi()
        if loi:
            muc["loi"] = loi
        if tep or lan or not re.search(r"violat|policy|couldn.t generate|failed to generate|safety", loi or "", re.I):
            break
        # 25/10 user: ảnh bị chặn vì chính sách nội dung -> AI viết lại mô tả nhẹ nhàng hơn (giữ ý cảnh) rồi vẽ lại một lần
        moi = _viet_lai_an_toan(prompt)
        if not moi:
            break
        bao(f"  ↻ {nhan}: Flow chặn vì nội dung — viết lại mô tả nhẹ hơn rồi vẽ lại")
        prompt = moi
    if tep:
        _sach_logo(tep)
        with _KHOA:
            muc.update(bien_the=tep, chon=0, tt="xong", loi="")
        bao(f"  ✔ {nhan} ({time.time() - t0:.0f}s)")
    else:
        loi = muc.get("loi") or next((v.get("loi") for v in flow_ve._doc_so().values() if v.get("loi")), "") or "Flow không trả ảnh"   # noqa: SLF001
        with _KHOA:
            muc.update(tt="loi", loi=loi)
        bao(f"  ✖ {nhan}: {loi[:150]}")
    luu(sb["id"])
    return bool(tep)


def ve_assets(sid, bao, ids=None, ve_lai=False):
    import flow_ve
    if not flow_ve.co_ho_so():
        raise RuntimeError("chưa có hồ sơ Flow — tạo ở «🎨 Hồ sơ Flow» trên trang chính")
    sb = doc(sid)
    can = [a for a in sb["assets"] if (ids is None or a["id"] in ids) and (ve_lai or not anh_chon(a))]
    if not can:
        bao("Assets đều đã có ảnh")
        return
    thu = os.path.join(thu_muc(sid), "assets")
    if sb["cai_dat"].get("con_roi"):                        # nhân vật = con rối: không vẽ bằng Flow
        import ghep_canh
        import kho_nhan_vat
        for a in [x for x in can if x["loai"] == "nhan_vat"]:
            try:
                f = kho_nhan_vat.doc(a["kho"])["phoi"] if a.get("kho") else ghep_canh.anh_nhan_vat_code(a, os.path.join(thu, f"{a['id']}.png"))
            except ValueError:
                f = ghep_canh.anh_nhan_vat_code(a, os.path.join(thu, f"{a['id']}.png"))
            with _KHOA:
                a.update(bien_the=[f], chon=0, tt="xong", loi="")
            bao(f"  ✔ asset {a['id']} {a['ten']}: con rối " + (f"kho «{a['kho']}»" if a.get("kho") else "code"))
        luu(sid)
        can = [x for x in can if x["loai"] != "nhan_vat"]
        if not can:
            return
    bao(f"Vẽ {len(can)} ảnh asset qua Flow ({_so_luong()} luồng)…")

    mau = _khung_kenh(sb)
    if mau:
        bao(f"Gắn {len(mau)} khung hình thật của kênh làm tham chiếu phong cách cho ảnh asset")

    def lam(a):
        if not _da_dung(sid):
            p = _cau_asset(sb, a) + (_MAU_KENH if mau else "") + _tranh(sb)
            _ve(sb, a, p, thu, a["id"], mau or None, bao, f"asset {a['id']} {a['ten']}")
    with ThreadPoolExecutor(_so_luong()) as ex:
        list(ex.map(lam, can))


_MAU_KENH = ("\nThe attached reference images are frames from the original channel: copy their ART STYLE exactly (line "
             "quality, flat colors, how faces and bodies are drawn, level of detail). Do NOT copy their characters, places, "
             "text or logos.")


def _khung_kenh(sb, n=2):
    """25/10 (thử 20 câu, lượt 5): tả phong cách bằng chữ không đủ — AI đọc khung hình kênh Lạnh Vcl (vẽ thô, mặt meme)
    thành "vector tối giản, nét gọn" và Flow vẽ ra webcomic bóng bẩy. -> lấy n khung hình THẬT của kênh trong plugin
    (khung nhiều hình nhất, bỏ khung toàn chữ), cắt bỏ dải dưới có logo kênh, gắn làm tham chiếu phong cách."""
    pid = (sb.get("cai_dat") or {}).get("plugin_id")
    if not pid:
        return []
    import json
    try:
        ds = json.load(open(os.path.join(ROOT, "plugins_doi_thu", f"{pid}.json"), encoding="utf-8"))["boi_canh"]["khung_hinh"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    from PIL import Image, ImageStat
    diem = []
    for f in ds or []:
        try:
            im = Image.open(f).convert("RGB")
        except (OSError, ValueError):
            continue
        w, h = im.size
        im = im.crop((0, 0, w, int(h * 0.8)))              # dải dưới 20% có logo kênh
        mau = len(im.resize((96, 54)).quantize(colors=32).getcolors() or [])
        diem.append((mau * sum(ImageStat.Stat(im.convert("L")).stddev), im))
    diem.sort(key=lambda x: -x[0])
    thu = os.path.join(thu_muc(sb["id"]), "assets")
    os.makedirs(thu, exist_ok=True)
    ra = []
    for i, (_, im) in enumerate(diem[:n]):
        p = os.path.join(thu, f"mau_kenh_{i + 1}.png")
        im.save(p)
        ra.append(p)
    return ra


def _ghep_con_roi(sb, c, a, khung, thu, k, bao):
    """Chế độ con rối: cảnh rộng / trung / cận mặt có người -> nền = ảnh bối cảnh, dán con rối (không gọi Flow).
    -> True nếu đã ghép (ảnh đồ vật / màn hình / ẩn dụ / ngoại cảnh / cảnh không có nền: để Flow vẽ, không người)."""
    import ghep_canh
    nen = anh_chon(_asset(sb, c.get("boi_canh")) or {})
    dat = [d for d in a.get("dat") or [] if _asset(sb, d["nv"])]
    if not dat:                                              # AI không khai "dat": lấy nhân vật của ảnh
        dat = [{"nv": x, "tu_the": "dung_binh_thuong", "x": None} for x in a.get("nhan_vat") or []
               if (_asset(sb, x) or {}).get("loai") == "nhan_vat"]
    if not nen or not dat or khung not in ("rong", "trung", "can_mat", ""):
        return False
    vt = ghep_canh.vi_tri(len(dat))
    ds = [(_asset(sb, d["nv"]), d["tu_the"], d["x"] if d.get("x") is not None else vt[i]) for i, d in enumerate(dat)]
    os.makedirs(thu, exist_ok=True)
    f = os.path.join(thu, f"anh_{a['id']:02d}_{time.strftime('%H%M%S')}_ghep.png")
    try:
        ghep_canh.ghep(nen, ds, khung or "rong", KICH_THUOC[sb["cai_dat"]["ti_le"]], f, so=c["id"] + k)
    except Exception as e:                                   # noqa: BLE001
        bao(f"  ! ghép scene {c['id']}: {str(e)[:120]} -> để Flow vẽ")
        return False
    with _KHOA:
        a.update(bien_the=[f], chon=0, tt="xong", loi="")
    luu(sb["id"])
    bao(f"  ✔ scene {c['id']} ảnh {a['id']}: ghép con rối ({', '.join(x['nv'] + ':' + x['tu_the'] for x in dat)})")
    return True


def ve_canh(sid, bao, ids=None, anh_ids=None, ve_lai=False):
    """Vẽ ảnh các scene. Song song theo scene; trong một scene vẽ LẦN LƯỢT khi 'nối tiếp' bật (ảnh trước làm tham chiếu)."""
    import flow_ve
    if not flow_ve.co_ho_so():
        raise RuntimeError("chưa có hồ sơ Flow — tạo ở «🎨 Hồ sơ Flow» trên trang chính")
    sb = doc(sid)
    if any(not anh_chon(a) for a in sb["assets"]):
        bao("Vẽ trước các asset còn thiếu (ảnh tham chiếu giữ nhân vật nhất quán)…")
        ve_assets(sid, bao)
    canh = [c for c in sb["canh"] if ids is None or c["id"] in ids]
    noi = sb["cai_dat"].get("noi_tiep", True)
    mau_kenh = _khung_kenh(sb, 1)

    con_roi = sb["cai_dat"].get("con_roi")

    def lam_anh(c, k):
        a = c["anh"][k]
        thu = os.path.join(thu_muc(sid), f"canh_{c['id']:02d}")
        khung = _khung_anh(c, a)
        if con_roi and _ghep_con_roi(sb, c, a, khung, thu, k, bao):
            return
        # ảnh tham chiếu (Flow nhận tối đa 3): nhân vật trước, rồi ảnh trước (nối tiếp) / bối cảnh, rồi đạo cụ
        ung = []
        so_nv = 0
        for loai in ("nhan_vat", "dao_cu"):
            for x in a.get("nhan_vat") or []:
                m = _asset(sb, x) or {}
                if loai == "nhan_vat" and con_roi:              # con rối: Flow không vẽ người
                    continue
                if m.get("loai") == loai and anh_chon(m):
                    # cận đồ vật: không gắn tờ nhân vật (kéo ảnh thành dáng toàn thân); cận mặt: chỉ một nhân vật
                    if loai == "nhan_vat" and (khung in ("can_do_vat", "man_hinh") or (khung == "can_mat" and so_nv >= 1)):
                        continue
                    so_nv += loai == "nhan_vat"
                    ung.append((anh_chon(m), f"{m.get('ten', x)} ({x})"))
            if loai == "nhan_vat":
                truoc = anh_chon(c["anh"][k - 1]) if (noi and k > 0) else None
                bc = anh_chon(_asset(sb, c.get("boi_canh")) or {})
                if truoc:
                    ung.append((truoc, "previous frame"))
                elif bc:
                    ung.append((bc, f"location {c['boi_canh']}"))
        ung = ung[:3]
        if len(ung) < 3 and mau_kenh:                        # còn chỗ: thêm một khung thật của kênh giữ nét vẽ
            ung.append((mau_kenh[0], "channel style sample (copy only its drawing style, not its content)"))
        tham, chu = [u[0] for u in ung], [u[1] for u in ung]
        truoc = truoc if "previous frame" in chu else None
        _ve(sb, a, _cau_anh(sb, c, a, bool(truoc), chu), thu, f"anh_{a['id']:02d}", tham, bao,
            f"scene {c['id']} ảnh {a['id']}/{len(c['anh'])}")

    can = [(c, k) for c in canh for k, a in enumerate(c["anh"])
           if (anh_ids is None or a["id"] in anh_ids) and (ve_lai or not anh_chon(a))]
    if not can:
        bao("Các ảnh scene đều đã có")
        return
    if noi:                                                  # nối tiếp: trong scene vẽ lần lượt, song song giữa các scene
        viec = [[x for x in can if x[0] is c] for c in canh]
        viec = [v for v in viec if v]
    else:                                                    # mặc định: MỌI ảnh song song (mỗi hồ sơ Flow một ảnh)
        viec = [[x] for x in can]

    def lam(nhom):
        for c, k in nhom:
            if _da_dung(sid):
                return
            lam_anh(c, k)
    bao(f"Vẽ {len(can)} ảnh của {len(canh)} scene qua Flow, {_so_luong()} luồng"
        + (" (nối tiếp: lần lượt trong mỗi scene)" if noi else " song song") + "…")
    with ThreadPoolExecutor(_so_luong()) as ex:
        list(ex.map(lam, viec))


def lam_tat_ca(sid, bao):
    sb = doc(sid)
    if not sb.get("assets"):
        lap_assets(sid, bao)
    if _da_dung(sid):
        return
    ve_assets(sid, bao)
    if _da_dung(sid):
        return
    if not doc(sid).get("canh"):
        lap_canh(sid, bao)
    if _da_dung(sid):
        return
    ve_canh(sid, bao)


def lam_lai_canh(sid, cid, so_anh, bao):
    """Viết lại câu lệnh ảnh của MỘT scene với số ảnh mới rồi vẽ lại."""
    sb = doc(sid)
    c = _canh(sb, cid)
    if not c:
        raise ValueError("không thấy scene")
    with _KHOA:
        c["so_anh"] = max(1, min(10, int(so_anh or c.get("so_anh") or 1)))
    lap_anh_canh(sid, [c["id"]], bao)
    ve_canh(sid, bao, ids=[c["id"]], ve_lai=True)


# --------------------------------------------------------------------------- video hook cho scene
def tao_video(sid, cid, anh_id=None, model="", bao=None):
    """Video Flow cho một scene: khung đầu = ảnh đang chọn (mặc định ảnh 1 của scene). TỐN ĐIỂM Flow."""
    import flow_video
    bao = bao or (lambda *_: None)
    sb = doc(sid)
    c = _canh(sb, cid)
    if not c:
        raise ValueError("không thấy scene")
    a = next((x for x in c["anh"] if x["id"] == anh_id), None) if anh_id else None
    a = a or next((x for x in c["anh"] if anh_chon(x)), None)
    dau = anh_chon(a) if a else None
    nv = [_asset(sb, x) for x in c.get("nhan_vat") or []]
    prompt = (c.get("video_prompt_en") or c.get("tom_tat_vi") or "").strip()
    if not prompt:
        raise ValueError("scene chưa có câu lệnh video")
    prompt += (" Keep every character exactly as in the start frame (" + "; ".join(f"{x['ten']}: {x['mo_ta_en'][:160]}"
               for x in nv if x and x["loai"] == "nhan_vat") + ").") if any(x and x["loai"] == "nhan_vat" for x in nv) else ""
    prompt += " Fluid natural motion, expressive faces, no frozen poses. No text, no captions, no logos."
    with _KHOA:
        c["video"] = {"tt": "dang", "loi": "", "tep": (c.get("video") or {}).get("tep") or "", "bd": time.time()}
    luu(sid)
    thu = os.path.join(thu_muc(sid), "video")
    ti_le = "9:16" if sb["cai_dat"]["ti_le"] in ("9:16", "3:4") else "16:9"
    try:
        kq = flow_video.tao(prompt, thu, f"canh_{c['id']:02d}_{time.strftime('%H%M%S')}", ti_le=ti_le,
                            model=model if model in flow_video.MODEL else flow_video.MODEL[0], so=1, anh_dau=dau,
                            bao=lambda m, *_: (c["video"].__setitem__("dong", m), bao(m)))
        f = kq["tep"][0]
        try:
            import sys
            sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
            import anh_ve
            tam = f[:-4] + "._sach.mp4"
            anh_ve.xoa_logo_video(f, tam, bao)
            os.replace(tam, f)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! storyboard: xoá logo video lỗi {str(e)[:80]}")
        with _KHOA:
            c["video"] = {"tt": "xong", "loi": "", "tep": f, "diem": kq.get("diem"), "cai_dat": kq.get("cai_dat")}
    except Exception as e:                                   # noqa: BLE001
        with _KHOA:
            c["video"] = dict(c.get("video") or {}, tt="loi", loi=str(e)[:300])
        raise
    finally:
        luu(sid)
    return c["video"]


# --------------------------------------------------------------------------- giọng đọc
KHOANG_LANG = 0.25           # giây lặng sau mỗi câu
GIONG_MAC_DINH = os.path.join(ROOT, "voices", "Tự tin.wav")


def _tach_cau(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+|\n+", str(text or "")) if s.strip()]


def doc_loi(sid, bao, ref=None, toc_do=1.0, num_step=32):
    """23/10 user: đọc lời kịch bản của từng scene (OmniVoice, clone giọng mẫu như bước đọc chính) -> mỗi câu một wav
    trong giong/, lưu sb["giong"] để xuất CapCut khớp ảnh theo lời. Câu đã đọc (cùng chữ, giọng, tốc độ) dùng lại."""
    import hashlib
    import json
    import giong as G
    sb = doc(sid)
    ref = ref if ref and os.path.isfile(ref) else GIONG_MAC_DINH
    toc_do = float(toc_do or 1.0)
    cau = []
    for c in sb["canh"]:
        for k, t in enumerate(_tach_cau(c.get("loi"))):
            cau.append({"canh": c["id"], "id": c["id"] * 1000 + k + 1, "text": t})
    if not cau:
        raise ValueError("scene chưa có lời kịch bản để đọc (tạo scene trước)")
    nhan = hashlib.md5(f"{os.path.basename(ref)}|{toc_do}|{num_step}".encode("utf-8")).hexdigest()[:8]
    thu = os.path.join(thu_muc(sid), "giong", nhan)
    os.makedirs(thu, exist_ok=True)
    dau = doc_json(os.path.join(thu, "_dau.json"), {}) or {}          # id -> chữ đã đọc (chữ đổi thì đọc lại)
    can = [x for x in cau if dau.get(str(x["id"])) != x["text"]
           or not os.path.isfile(os.path.join(thu, f"{x['id']:04d}.wav"))]
    lenh_goc = [G.OMNI_PY, os.path.join(ROOT, "tts", "omnivoice_tts.py"), "--ref", ref, "--batch", "16",
                "--num-step", str(num_step), "--rate", str(toc_do), "--name-fmt", "{:04d}.wav"]
    if can:
        bao(f"Đọc {len(can)}/{len(cau)} câu bằng giọng «{os.path.splitext(os.path.basename(ref))[0]}» x{toc_do} (OmniVoice, GPU)…")
        jobs = os.path.join(thu, "_jobs.json")
        json.dump([{"idx": x["id"], "text": x["text"]} for x in can], open(jobs, "w", encoding="utf-8"), ensure_ascii=False)
        rc, cuoi = G._chay_hien_log(lenh_goc + ["--jobs-json", jobs, "--out-dir", thu], len(can))   # noqa: SLF001
        if rc != 0:
            bao(f"  ! OmniVoice mã {rc}: {' | '.join(cuoi)[-200:]}")
        try:                                                 # soát nuốt / méo chữ, câu lỗi đọc lại (như bước đọc chính)
            import soat_giong
            bao("Soát giọng đọc (câu lỗi đọc lại)…")
            soat_giong.soat_va_doc_lai(
                [{"id": x["id"], "text": x["text"]} for x in can], thu,
                lambda j, o, seed: G._chay_hien_log(lenh_goc + ["--jobs-json", j, "--out-dir", o, "--seed", str(seed)],   # noqa: SLF001
                                                    len(json.load(open(j, encoding="utf-8"))))[0])
        except Exception as e:                               # noqa: BLE001
            bao(f"  ! soát giọng lỗi (giữ bản đọc hiện có): {str(e)[:120]}")
    thieu = 0
    for x in cau:
        p = os.path.join(thu, f"{x['id']:04d}.wav")
        if os.path.isfile(p) and os.path.getsize(p) > 2000:
            x["file"], x["dai"] = p, round(G.thoi_luong(p), 2)
            dau[str(x["id"])] = x["text"]
        else:
            thieu += 1
    ghi_json(os.path.join(thu, "_dau.json"), dau)
    with _KHOA:
        sb["giong"] = {"ref": ref, "toc_do": toc_do, "cau": cau}
    luu(sid)
    tong = sum(x.get("dai") or 0 for x in cau) + KHOANG_LANG * len(cau)
    bao(f"Đọc xong {len(cau) - thieu}/{len(cau)} câu, tổng ~{tong:.0f} giây" + (f" — {thieu} câu chưa có giọng" if thieu else ""))


# --------------------------------------------------------------------------- xuất
def xuat_json(sid):
    """Bản JSON gọn để tải về / đưa công cụ khác: assets, scene, câu lệnh, ảnh đang chọn, video."""
    sb = doc(sid)
    return {
        "id": sb["id"], "ten": sb["ten"], "cai_dat": sb["cai_dat"], "phong_cach_chung": sb.get("phong_cach_chung"),
        "kich_ban": sb.get("kich_ban"),
        "assets": [{"id": a["id"], "loai": a["loai"], "ten": a["ten"], "mo_ta_vi": a["mo_ta_vi"], "mo_ta_en": a["mo_ta_en"],
                    "anh": anh_chon(a), "bien_the": a.get("bien_the") or []} for a in sb["assets"]],
        "canh": [{"id": c["id"], "tieu_de": c["tieu_de"], "loi": c["loi"], "tom_tat_vi": c["tom_tat_vi"],
                  "boi_canh": c["boi_canh"], "nhan_vat": c["nhan_vat"], "noi_tiep": c.get("noi_tiep"),
                  "video_prompt_en": c.get("video_prompt_en"), "video": (c.get("video") or {}).get("tep") or None,
                  "anh": [{"id": a["id"], "prompt_en": a["prompt_en"], "mo_ta_vi": a["mo_ta_vi"], "nhan_vat": a["nhan_vat"],
                           "anh": anh_chon(a), "bien_the": a.get("bien_the") or []} for a in c["anh"]]}
                 for c in sb["canh"]],
    }


def xuat_capcut(sid, ten_nhap=None, giay_anh=None, co_video=True, co_giong=True):
    """Bản nháp CapCut. Có giọng đọc (doc_loi) và co_giong: track 'giong' = từng câu đọc nối nhau, mỗi scene dài đúng
    bằng lời của nó; track 'storyboard' = video hook (nếu có, tắt tiếng) rồi các ảnh đang chọn chia đều phần còn lại
    (mỗi ảnh tối thiểu 1 giây). Không có giọng: mỗi ảnh giay_anh giây. Ảnh phóng / thu nhẹ xen kẽ (không đứng hình).
    Bản nháp phải ĐÓNG trong CapCut."""
    import pycapcut as draft
    from pycapcut import trange
    import common
    import dung_tay
    SEC = 1_000_000
    sb = doc(sid)
    dd = common.thu_muc_nhap_capcut()
    if not dd:
        raise RuntimeError("không dò được thư mục CapCut Drafts (mở CapCut một lần trước)")
    ten = re.sub(r'[\\/:*?"<>|]+', "_", str(ten_nhap or "").strip()) or f"SB_{sid}"
    g = int(float(giay_anh or sb["cai_dat"].get("giay_anh") or 3) * SEC)
    gi = (sb.get("giong") or {}).get("cau") or [] if co_giong else []
    gi = [x for x in gi if x.get("file") and os.path.isfile(x["file"])]
    w, h = KICH_THUOC.get(sb["cai_dat"]["ti_le"], (1920, 1080))
    sc = draft.DraftFolder(dd).create_draft(ten, w, h, allow_replace=True)
    sc.add_track(draft.TrackType.video, track_name="storyboard")
    if gi:
        sc.add_track(draft.TrackType.audio, track_name="giong")
    KP = draft.KeyframeProperty
    t, n, n_cau, files, vl = 0, 0, 0, [], {}
    for c in sb["canh"]:
        anh = [f for f in (anh_chon(a) for a in c["anh"]) if f]
        cau = [x for x in gi if x["canh"] == c["id"]]
        # lời của scene -> track giọng, bắt đầu cùng lúc với hình của scene
        ta = t
        for x in cau:
            dl = int(x["dai"] * SEC) - 1000
            sc.add_segment(draft.AudioSegment(draft.AudioMaterial(x["file"]), trange(ta, dl)), track_name="giong")
            ta += dl + 1000 + int(KHOANG_LANG * SEC)
            n_cau += 1
        D = ta - t                                           # độ dài lời của scene (0 = không có giọng)
        v = (c.get("video") or {}).get("tep")
        vd = 0
        if co_video and v and os.path.isfile(v):
            mat = vl.setdefault(v, draft.VideoMaterial(v))
            vd = int(mat.duration) - 1000
            if D and anh:                                    # chừa chỗ cho ảnh (tối thiểu 1 giây mỗi ảnh)
                vd = min(vd, max(SEC, D - len(anh) * SEC))
            elif D:
                vd = min(vd, D)
            sc.add_segment(draft.VideoSegment(mat, trange(t, vd), volume=0.0 if gi else 1.0), track_name="storyboard")
            n += 1
            files.append(v)
        moi = max(SEC, (D - vd) // len(anh)) if (D and anh) else g
        tt = t + vd
        for f in anh:
            seg = draft.VideoSegment(vl.setdefault(f, draft.VideoMaterial(f)), trange(tt, moi))
            vao, ra = (1.0, 1.08) if (n % 2 == 0) else (1.08, 1.0)
            seg.add_keyframe(KP.uniform_scale, 0, vao)
            seg.add_keyframe(KP.uniform_scale, moi - 1000, ra)
            sc.add_segment(seg, track_name="storyboard")
            tt += moi
            n += 1
            files.append(f)
        t = max(tt, ta)
    if not n:
        raise RuntimeError("chưa có ảnh nào để xuất")
    sc.save()
    try:
        dung_tay._sua_nhap(os.path.join(dd, ten), files)    # noqa: SLF001  (tắt hút đoạn + đưa ảnh vào khung Phương tiện)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! storyboard: sửa bản nháp lỗi {str(e)[:80]}")
    return {"ten": ten, "so_doan": n, "so_cau": n_cau, "giay": round(t / SEC, 1), "thu_muc": os.path.join(dd, ten)}
