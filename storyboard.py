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
    "dien_anh": "cinematic photorealistic film still, natural light, shallow depth of field, rich but natural color grade",
    "tai_lieu": "documentary photograph, real-life candid moment, natural available light, true-to-life colors",
    "hoat_hinh_3d": "high-quality 3D animated film still (Pixar-like), soft global illumination, expressive stylized characters",
    "anime": "anime film key frame, clean line art, cel shading, detailed painted background",
    "minh_hoa": "detailed digital illustration, painterly storybook style, soft textured brushwork",
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
            "phong_cach_them": str(c.get("phong_cach_them") or "").strip()[:300],
            # 23/10 user "quá chậm": nối tiếp bắt vẽ LẦN LƯỢT trong scene (~90 s/ảnh, chỉ 1 hồ sơ/scene) -> mặc định TẮT,
            # mọi ảnh vẽ song song; nhân vật vẫn giữ nhờ ảnh asset tham chiếu + mô tả cố định
            "noi_tiep": c.get("noi_tiep") is True,
            "giay_anh": max(0.5, min(20.0, float(c.get("giay_anh") or 3)))}


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

Global look chosen by the user: {phong_cach}

Return:
  "phong_cach_chung": ONE English sentence fixing the visual style for EVERY image (medium, lens/film look, color grade,
     lighting mood, era look if the story is set in the past). Respect the user's look above.
  "assets": every RECURRING CHARACTER (named or not: "the mother", "the soldier"…, also animals/creatures that act), every
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
Keep the cast small and essential (usually 1-6 characters, 1-6 locations, 0-5 props).
Only JSON: {{"phong_cach_chung": "...", "assets": [{{"id": "NV1", "loai": "nhan_vat", "ten": "...", "mo_ta_vi": "...", "mo_ta_en": "..."}}]}}

SCRIPT:
{kb}"""


def lap_assets(sid, bao):
    sb = doc(sid)
    kb = (sb.get("kich_ban") or "").strip()
    if not kb:
        raise ValueError("chưa nhập kịch bản")
    cd = sb["cai_dat"]
    pc = PHONG_CACH[cd["phong_cach"]] + ((". " + cd["phong_cach_them"]) if cd.get("phong_cach_them") else "")
    bao("AI đang đọc kịch bản và lập danh sách assets (nhân vật, bối cảnh, đạo cụ)…")
    j = None
    for _ in range(3):
        j = rut_json(hoi_llm(_P_ASSET.format(phong_cach=pc, kb=kb[:24000]), timeout=300) or "")
        if isinstance(j, dict) and j.get("assets"):
            break
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
        c = cu.get(aid)
        if c and c.get("mo_ta_en") == x["mo_ta_en"]:            # mô tả không đổi -> giữ ảnh đã vẽ
            x.update(bien_the=c.get("bien_the") or [], chon=c.get("chon") or 0, tt=c.get("tt") or "cho")
        ra.append(x)
    with _KHOA:
        sb["phong_cach_chung"] = str(j.get("phong_cach_chung") or pc).strip()
        sb["assets"] = ra
    luu(sid)
    bao(f"Có {len(ra)} assets: " + ", ".join(f"{a['id']} {a['ten']}" for a in ra))


# --------------------------------------------------------------------------- AI: scene
_P_DAN_Y = """You are the director of an AI-generated film. Split the SCRIPT into SCENES that follow each other in story
order and together cover the WHOLE script (no gap, no overlap, no invented events). {so_canh}
A new scene starts when the place, the time or the dramatic beat changes.

ASSET BIBLE (use these ids only):
{assets}

For each scene:
  - "id": 1, 2, 3…
  - "tieu_de": short Vietnamese title
  - "loi": the exact part of the script this scene covers (copy it, keep the original language)
  - "tom_tat_vi": 1-2 Vietnamese sentences: what happens visually
  - "boi_canh": the location id (BC…) or "" if none fits
  - "nhan_vat": ids of the characters who appear (NV…), and props (DC…) that matter
  - "noi_tiep": one English sentence: how this scene picks up from the end of the previous one (continuity: who is where,
    what they carry, time of day, weather). For scene 1: how the film opens.
  - "video_prompt_en": an 8-second AI video prompt (Google Veo) used as a HOOK for this scene, 50-90 words: starts from the
    first image of the scene, the characters (by name) DOING a clear fluid action with natural body motion and facial
    expression, one cinematic camera move (slow push-in, tracking, crane, handheld follow…), atmosphere, the dramatic beat.
    No text, no captions, no logos.
Only JSON: [{{"id": 1, "tieu_de": "...", "loi": "...", "tom_tat_vi": "...", "boi_canh": "BC1", "nhan_vat": ["NV1"], "noi_tiep": "...", "video_prompt_en": "..."}}]

SCRIPT:
{kb}"""

_P_ANH = """You are the storyboard artist of an AI-generated film. Write the IMAGE PROMPTS (Google Flow / Nano Banana) for
the scenes below. The images of one scene are consecutive frames of ONE continuous action, like a real storyboard.

GLOBAL STYLE (same for every image): {pc}
ASSET BIBLE (characters must look EXACTLY like this in every image — same face, age, hair, build, outfit and colors —
whatever the location, time or weather; change clothes ONLY if the script explicitly says so):
{assets}

RULES for every image prompt ("prompt_en", 45-90 English words):
  1. Continuity: frame k starts where frame k-1 ended (same place, light, props in hand, wounds, dirt, wet clothes…);
     the first frame of a scene follows the scene's "noi_tiep". The action PROGRESSES from frame to frame.
  2. Vary the shot like a film editor: establishing wide -> medium -> close-up / over-the-shoulder / low angle / insert
     detail -> reaction… Never two identical framings in a row.
  3. Name the characters exactly as in the bible (e.g. "Minh (NV1)") and restate their 2-3 most recognizable features
     (hair, outfit colors) in the prompt.
  4. NOT STIFF: every frame is a moment CAUGHT MID-ACTION — a specific verb (running, grabbing, turning, shouting,
     kneeling, pushing a door…), weight shift and natural asymmetric pose, hands doing something, a clear facial
     expression matching the emotion, eyes looking at what they interact with (never at the camera), motion cues (hair or
     cloth moving, dust, splashes, slight motion blur). Never "standing and looking at the camera", never posed or
     mannequin-like, never a frozen neutral face.
  5. Describe the setting with the location's key landmarks so the place stays recognizable.
  6. No text, no captions, no subtitles, no logos, no watermarks, no split panels.
Also for each frame:
  - "mo_ta_vi": one short Vietnamese sentence for the editor
  - "nhan_vat": ids of the characters / props VISIBLE in this frame (empty list if none)
Write EXACTLY the number of frames asked for each scene.
Only JSON: [{{"canh": 1, "anh": [{{"prompt_en": "...", "mo_ta_vi": "...", "nhan_vat": ["NV1"]}}]}}]

SCENES:
{ds}"""


def _bible(sb, chi=None):
    return "\n".join(f"- {a['id']} ({a['loai']}) {a['ten']}: {a['mo_ta_en']}" for a in sb.get("assets") or []
                     if chi is None or a["id"] in chi)


def lap_canh(sid, bao):
    sb = doc(sid)
    if not sb.get("assets"):
        lap_assets(sid, bao)
        sb = doc(sid)
    kb = (sb.get("kich_ban") or "").strip()
    cd = sb["cai_dat"]
    n = cd["so_canh"]
    bao("AI đang chia kịch bản thành các scene nối tiếp…")
    j = None
    for _ in range(3):
        j = rut_json(hoi_llm(_P_DAN_Y.format(
            so_canh=f"Make EXACTLY {n} scenes." if n else "Choose the number of scenes yourself (usually 3-12, one per story beat).",
            assets=_bible(sb), kb=kb[:24000]), timeout=300) or "")
        if isinstance(j, list) and j:
            break
    if not isinstance(j, list) or not j:
        raise ValueError("AI không chia được scene (thử lại)")
    ids = {a["id"] for a in sb["assets"]}
    canh = []
    for i, c in enumerate(x for x in j if isinstance(x, dict)):
        canh.append({"id": i + 1, "tieu_de": str(c.get("tieu_de") or f"Scene {i + 1}").strip(),
                     "loi": str(c.get("loi") or "").strip(), "tom_tat_vi": str(c.get("tom_tat_vi") or "").strip(),
                     "boi_canh": c.get("boi_canh") if c.get("boi_canh") in ids else "",
                     "nhan_vat": [x for x in (c.get("nhan_vat") or []) if x in ids],
                     "noi_tiep": str(c.get("noi_tiep") or "").strip(),
                     "video_prompt_en": str(c.get("video_prompt_en") or "").strip(),
                     "so_anh": cd["so_anh"], "anh": [], "video": {}})
    with _KHOA:
        sb["canh"] = canh
    luu(sid)
    bao(f"Có {len(canh)} scene — đang viết câu lệnh {cd['so_anh']} ảnh mỗi scene…")
    lap_anh_canh(sid, [c["id"] for c in canh], bao)


def lap_anh_canh(sid, ids, bao):
    """AI viết câu lệnh ảnh cho các scene `ids` (lô 4 scene, hỏi song song)."""
    sb = doc(sid)
    canh = [c for c in sb["canh"] if c["id"] in ids]
    lo = [canh[i:i + 4] for i in range(0, len(canh), 4)]
    truoc = {c["id"]: (sb["canh"][k - 1] if k else None) for k, c in enumerate(sb["canh"])}

    def mo_ta(c):
        t = truoc.get(c["id"])
        return (f"Scene {c['id']} — {c['so_anh']} frames. Location: {c['boi_canh'] or 'see script'}. "
                f"Cast: {', '.join(c['nhan_vat']) or 'none'}.\n  Continuity: {c['noi_tiep']}\n"
                f"  What happens: {c['tom_tat_vi']}\n  Script part: {c['loi'][:1500]}"
                + (f"\n  (Previous scene {t['id']} ended with: {t['tom_tat_vi']})" if t else ""))
    prompts = [_P_ANH.format(pc=sb.get("phong_cach_chung") or "", assets=_bible(sb), ds="\n\n".join(mo_ta(c) for c in l))
               for l in lo]
    kq = hoi_nhieu(prompts, timeout=300)
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
                    bao(f"  ! scene {c['id']}: AI không trả câu lệnh ảnh")
                    continue
                c["anh"] = [{"id": i + 1, "prompt_en": str(a["prompt_en"]).strip(), "mo_ta_vi": str(a.get("mo_ta_vi") or "").strip(),
                             "nhan_vat": [x for x in (a.get("nhan_vat") or []) if _asset(sb, x)] or list(c["nhan_vat"]),
                             "bien_the": [], "chon": 0, "tt": "cho", "loi": ""}
                            for i, a in enumerate(ds_anh[:c["so_anh"]])]
        luu(sid)
    bao("Đã có câu lệnh ảnh: " + ", ".join(f"scene {c['id']} ({len(c['anh'])} ảnh)" for c in canh))


# --------------------------------------------------------------------------- vẽ
_KHONG_DO = ("Natural candid moment caught mid-motion: dynamic body language, weight shift, hands busy, expressive face "
             "matching the emotion, eyes on what they interact with, subtle motion blur in hair and clothing; not posed, "
             "not stiff, not looking at the camera. No text, no captions, no logos, no watermark, single frame.")


def _cau_asset(sb, a):
    pc = sb.get("phong_cach_chung") or ""
    if a["loai"] == "nhan_vat":
        return (f"Character reference sheet of {a['ten']}: {a['mo_ta_en']} Two views side by side on one image: on the "
                f"left a full-body view in a relaxed natural three-quarter stance, on the right a close-up portrait of the "
                f"face with a natural expression. Plain seamless light-grey studio background, soft even lighting, the "
                f"whole outfit clearly visible. {pc}. No text, no labels, no logos.")
    if a["loai"] == "boi_canh":
        return (f"Establishing wide shot of {a['ten']}: {a['mo_ta_en']} No people. {pc}. No text, no logos, no watermark.")
    return (f"Prop reference photo of {a['ten']}: {a['mo_ta_en']} Isolated, centered, on a plain neutral background, soft "
            f"studio light. {pc}. No text, no logos.")


def _cau_anh(sb, c, a, co_truoc, tham):
    """Câu lệnh đầy đủ của một ảnh scene + chú thích thứ tự ảnh tham chiếu."""
    nv = [_asset(sb, x) for x in a.get("nhan_vat") or []]
    nv = [x for x in nv if x]
    bc = _asset(sb, c.get("boi_canh"))
    dong = [a["prompt_en"]]
    if nv:
        dong.append("Characters — keep them EXACTLY identical to their reference images and descriptions (same face, age, "
                    "hairstyle, build, outfit and colors): " + " ".join(f"{x['ten']} ({x['id']}): {x['mo_ta_en']}" for x in nv))
    if bc:
        dong.append(f"Setting — {bc['ten']}: {bc['mo_ta_en']}")
    if tham:
        dong.append("Reference images in order: " + "; ".join(tham) + "."
                    + (" The reference marked previous frame is the frame just before this one: continue from it (same place, light and "
                       "continuity) but with a NEW camera angle and the action moved forward." if co_truoc else ""))
    dong.append(f"Style: {sb.get('phong_cach_chung') or ''}")
    dong.append(_KHONG_DO)
    return "\n".join(dong)


def _so_luong():
    import flow_ve
    return max(1, min(8, flow_ve.so_ho_so_dung_duoc()))


def _sach_logo(files):
    try:
        import sys
        sys.path.insert(0, os.path.join(ROOT, "chinh_sua"))
        import anh_ve
        for f in files:
            anh_ve.xoa_logo(f)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! storyboard: xoá logo lỗi {str(e)[:80]}")


def _ve(sb, muc, prompt, thu, ten_goc, tham_chieu, bao, nhan):
    import flow_ve
    with _KHOA:
        muc.update(tt="dang", loi="")
    t0 = time.time()
    try:
        tep = flow_ve.ve_nhieu(prompt, thu, ten_goc + "_" + time.strftime("%H%M%S"), sb["cai_dat"]["ti_le"], tham_chieu)
    except Exception as e:                                   # noqa: BLE001
        tep, muc["loi"] = [], str(e)[:200]
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
    bao(f"Vẽ {len(can)} ảnh asset qua Flow ({_so_luong()} luồng)…")

    def lam(a):
        if not _da_dung(sid):
            _ve(sb, a, _cau_asset(sb, a), thu, a["id"], None, bao, f"asset {a['id']} {a['ten']}")
    with ThreadPoolExecutor(_so_luong()) as ex:
        list(ex.map(lam, can))


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

    def lam_anh(c, k):
        a = c["anh"][k]
        thu = os.path.join(thu_muc(sid), f"canh_{c['id']:02d}")
        # ảnh tham chiếu (Flow nhận tối đa 3): nhân vật trước, rồi ảnh trước (nối tiếp) / bối cảnh, rồi đạo cụ
        ung = []
        for loai in ("nhan_vat", "dao_cu"):
            for x in a.get("nhan_vat") or []:
                m = _asset(sb, x) or {}
                if m.get("loai") == loai and anh_chon(m):
                    ung.append((anh_chon(m), f"{m.get('ten', x)} ({x})"))
            if loai == "nhan_vat":
                truoc = anh_chon(c["anh"][k - 1]) if (noi and k > 0) else None
                bc = anh_chon(_asset(sb, c.get("boi_canh")) or {})
                if truoc:
                    ung.append((truoc, "previous frame"))
                elif bc:
                    ung.append((bc, f"location {c['boi_canh']}"))
        ung = ung[:3]
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
