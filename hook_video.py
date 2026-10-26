# -*- coding: utf-8 -*-
"""CÂU LỆNH VIDEO ĐOẠN HOOK (22/10 user: "phần 4 tôi muốn nó làm video đoạn hook, càng kịch tính càng tốt, nhưng không cho
tự tạo mà chỉ cho tôi danh sách câu lệnh để tôi xem xét tự tạo vì nó có điểm giới hạn").
23/10 user: ✨ TỰ TẠO luôn bằng Flow (Omni 1.1 Flash 10 s ~15 điểm/clip) rồi đè lên footage đúng lúc giọng nói tới khoảnh
khắc đó trong ~30 s đầu; clip tiếng động (sóng, máy, nổ…) giữ tiếng Veo NHỎ, clip có người nói chuyện thì TẮT tiếng.

MỘT lần hỏi AI: lời của đoạn mở đầu (HOOK_GIAY giây đầu) + hồ sơ câu chuyện (bối cảnh, ngoại hình cố định) -> 3-6 câu lệnh
video ngắn (Veo / Flow) kịch tính, mỗi câu ứng một khoảnh khắc của lời hook: tiếng Anh cho model + mô tả tiếng Việt + gợi ý
khung đầu. KHÔNG tạo video — người dùng chép / điền vào ô 🎞 Tạo video Google Flow. Lưu ra/<dự án>/hook_video.json."""
import hashlib
import os

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

HOOK_GIAY = 30.0            # đoạn hook = ~30 giây lời đầu tiên (hết câu đang dở)
SO_TOI_DA = 6
HOOK_CLIP_GIAY = 10         # 23/10 user: Omni 1.1 Flash 10 s (~15 điểm/clip)
HOOK_MODEL = "Omni 1.1 Flash"
HOOK_PHAN_GIAI = "720p"
AM_TIENG_DONG = 0.3         # tiếng Veo của clip tiếng động: nhỏ dưới giọng đọc

_P = """You are the trailer editor of a documentary. Below is the OPENING HOOK of the narration (Vietnamese, numbered
sentences with their start second). Write {so} short AI VIDEO prompts (Google Veo / Flow, 10-second clips, 16:9) that make
this hook as GRIPPING and DRAMATIC as possible: tension, scale, mystery, a striking reveal — while staying TRUE to what the
narration says (no invented events).
{ho_so}
For each clip:
  - "cau": the sentence number it illustrates (in order of the narration; one clip per moment);
  - "prompt_en": ONE English video prompt, 40-80 words: the subject and its action, the setting and the ERA of that moment
    (period-correct clothing, vehicles, buildings; film look of that era if it is in the past), a cinematic CAMERA MOVE
    (slow push-in, crane up, low-angle tracking, aerial reveal, handheld close-up…), lighting and atmosphere (storm,
    dusk, fog, underwater god rays…), and the ONE dramatic beat of the clip. Real-looking live action, no text, no
    captions, no logos, no on-screen titles. Never show the face of a real named person (use silhouettes, from behind,
    hands, or wide shots).
  - "khung_dau": one English sentence describing a strong FIRST FRAME for the clip (can be generated as an image first
    and used as the Start frame);
  - "mo_ta_vi": short Vietnamese description of the clip (1-2 sentences) for the editor;
  - "am": "noi_chuyen" if the clip shows people TALKING to each other (dialogue), otherwise "tieng_dong" (the clip's
    sound is natural action sound: waves, engines, cranes, crowds, explosions…). For "tieng_dong" clips END the prompt
    with: "Natural ambient sound effects only, no dialogue, no voice-over, no music."
Each clip is 10 seconds long.
Only JSON: [{{"cau": 1, "prompt_en": "...", "khung_dau": "...", "mo_ta_vi": "...", "am": "tieng_dong"}}]

HOOK NARRATION:
{ds}"""


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "hook_video.json")


def doc(du_an):
    return doc_json(_p(du_an), {}) or {}


def lap(du_an, hoi_lai=False, giay=HOOK_GIAY, so=5):
    """-> {"ds": [{cau, text, t0, prompt_en, khung_dau, mo_ta_vi, giay}], "giay_hook"}. Lời hook không đổi và đã có -> dùng lại."""
    out = thu_muc_du_an(du_an)[1]
    canh = sorted(doc_json(os.path.join(out, "tu_khoa.json"), []) or [], key=lambda c: c["id"])
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — đọc giọng trước")
    hook = []
    for c in canh:
        t0 = float(c.get("bat_dau") or 0)
        if hook and t0 >= giay:
            break
        hook.append(c)
    ds_txt = "\n".join(f"{c['id']}. [{float(c.get('bat_dau') or 0):.0f}s] {str(c.get('text') or '').strip()}" for c in hook)
    k = hashlib.md5(("hk2|" + ds_txt + f"|{so}").encode("utf-8")).hexdigest()[:16]
    da = doc(du_an)
    t_het = max(float(c.get("bat_dau") or 0) + float(c.get("dai") or 0) for c in hook)
    if not hoi_lai and da.get("_k") == k and da.get("ds"):
        return da
    theo = {c["id"]: c for c in hook}
    if not hoi_lai and da.get("ds") and float(da.get("giay_hook") or 0) == float(giay) and all(
            y.get("cau") in theo and str(theo[y["cau"]].get("text") or "") == y.get("text") for y in da["ds"]):
        # 25/10: đọc lại giọng chỉ lệch GIỜ (lời giữ nguyên) -> giữ câu lệnh + clip đã tạo (không hỏi AI / tốn điểm Flow
        # lần nữa), chỉ dời mốc t0 theo giọng mới
        for y in da["ds"]:
            y["t0"] = round(float(theo[y["cau"]].get("bat_dau") or 0), 1)
        da.update(_k=k, het_hook=round(t_het, 2))
        ghi_json(_p(du_an), da)
        return da
    hs = ""
    try:                                                     # hồ sơ câu chuyện (bối cảnh + ngoại hình) — dùng chung với ảnh AI
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
        import dieu_phoi
        hs = dieu_phoi.ho_so([{"i": c["id"], "text": c.get("text") or ""} for c in canh], out)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! hook video: không lập được hồ sơ câu chuyện ({str(e)[:80]})")
    log(f"[hook] hỏi AI câu lệnh video cho {len(hook)} câu mở đầu ({giay:.0f} s)…")
    j = None
    for _ in range(2):
        j = rut_json(hoi_llm(_P.format(so=min(SO_TOI_DA, max(3, so)), ho_so=hs, ds=ds_txt), timeout=240) or "")
        if isinstance(j, list) and j:
            break
    if not isinstance(j, list) or not j:
        raise ValueError("AI không trả câu lệnh video hook (thử lại)")
    ra = []
    for x in j[:SO_TOI_DA]:
        if not isinstance(x, dict) or not str(x.get("prompt_en") or "").strip():
            continue
        try:
            ci = int(str(x.get("cau")).strip(" []"))
        except (TypeError, ValueError):
            ci = hook[0]["id"]
        c = theo.get(ci) or hook[0]
        g = HOOK_CLIP_GIAY
        ra.append({"cau": c["id"], "text": str(c.get("text") or ""), "t0": round(float(c.get("bat_dau") or 0), 1),
                   "prompt_en": str(x["prompt_en"]).strip(), "khung_dau": str(x.get("khung_dau") or "").strip(),
                   "mo_ta_vi": str(x.get("mo_ta_vi") or "").strip(), "giay": g,
                   "am": "noi_chuyen" if str(x.get("am") or "").strip() == "noi_chuyen" else "tieng_dong"})
    ra.sort(key=lambda y: y["t0"])                           # thứ tự theo lời (AI có khi trả lộn)
    kq = {"_k": k, "giay_hook": giay, "het_hook": round(t_het, 2), "ds": ra}
    ghi_json(_p(du_an), kq)
    log(f"[hook] {len(ra)} câu lệnh video -> hook_video.json")
    return kq


def xep_lich(ds, het):
    """[{t0, file, am}] -> [{bd, het, file, am}] trên trục bản dựng (giây). 25/10: nhiều clip cùng MỘT câu (cùng t0) trước
    đây chồng lên nhau rồi clip sau bị loại (het = bd) -> nay nối tiếp: clip sau bắt đầu khi clip trước hết; mỗi clip dài
    tối đa HOOK_CLIP_GIAY, dừng ở mốc câu kế tiếp (nếu còn >= 2 s) và không quá hết đoạn hook."""
    ds = sorted([y for y in ds if y.get("file") and os.path.isfile(y["file"])], key=lambda y: float(y.get("t0") or 0))
    ra, cuoi = [], 0.0
    for k, y in enumerate(ds):
        bd = max(float(y.get("t0") or 0), cuoi)
        h = min(bd + HOOK_CLIP_GIAY, het)
        sau = next((float(z.get("t0") or 0) for z in ds[k + 1:] if float(z.get("t0") or 0) >= bd + 2.0), None)
        if sau is not None:
            h = min(h, sau)
        if h - bd < 1.0:
            continue
        ra.append({"bd": round(bd, 2), "het": round(h, 2), "file": y["file"], "am": y.get("am") or "tieng_dong",
                   "cau": y.get("cau")})
        cuoi = h
    return ra


def ke_hoach_hook(du_an):
    """Lịch hook từ hook_video.json với các clip ĐÃ CÓ (không gọi Flow) — dùng khi lưu / tạo lại clip trên giao diện."""
    kq = doc(du_an)
    return xep_lich(kq.get("ds") or [], float(kq.get("het_hook") or kq.get("giay_hook") or HOOK_GIAY))


def ghi_ke_hoach(du_an):
    """25/10: cập nhật kh["hook"] trong ke_hoach.json theo clip hiện có (✨ lần sau đọc lại từ hook_video.json)."""
    p = os.path.join(thu_muc_du_an(du_an)[1], "ke_hoach.json")
    if not os.path.isfile(p):
        return []
    kh = doc_json(p, {}) or {}
    kh["hook"] = ke_hoach_hook(du_an)
    ghi_json(p, kh)
    return kh["hook"]


def tao_video(du_an, bao=None):
    """23/10 user: ✨ tự tạo video hook -> [{bd, het, file, am}] (giây trên trục bản dựng). Clip đã tạo (cùng câu lệnh) dùng
    lại, không tốn điểm lần nữa. Flow lỗi thì bỏ clip đó (không chặn bước ✨)."""
    import sys
    from concurrent.futures import ThreadPoolExecutor
    import flow_ve
    import flow_video
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    bao = bao or (lambda m: log("    " + m))
    kq = lap(du_an)
    ds = kq.get("ds") or []
    thu = os.path.join(thu_muc_du_an(du_an)[1], "hook")
    os.makedirs(thu, exist_ok=True)

    def sach(g, f, y):
        """Xoá logo ✦ của video Flow g -> f. Lỗi thì dùng bản gốc, đánh dấu con_logo để lần sau xoá lại."""
        tam = f[:-4] + "._sach.mp4"
        try:
            anh_ve.xoa_logo_video(g, tam, lambda m: None)
            os.replace(tam, f)
            y.pop("con_logo", None)
        except Exception as e:                               # noqa: BLE001
            bao(f"! hook câu {y['cau']}: xoá logo lỗi ({str(e)[:80]}) -> tạm dùng bản gốc")
            if os.path.isfile(tam):
                os.remove(tam)
            if os.path.abspath(g) != os.path.abspath(f):
                os.replace(g, f)
            y["con_logo"] = True
        if os.path.isfile(g) and os.path.abspath(g) != os.path.abspath(f):  # bản gốc còn logo: bỏ
            os.remove(g)

    def mot(y):
        # 25/10: clip người dùng đã 💾 Lưu trên giao diện (y["file"], tên không theo băm câu lệnh) -> DÙNG ĐÚNG clip đó;
        # trước đây tính lại tên theo băm câu lệnh đã sửa -> không thấy -> tạo lại bằng Flow (tốn điểm, mất clip đã chọn)
        cu = y.get("file") or ""
        if cu and os.path.isfile(cu) and os.path.getsize(cu) > 20000 \
                and y.get("file_prompt", y["prompt_en"]) == y["prompt_en"]:
            if y.get("con_logo"):
                sach(cu, cu, y)
            return cu
        ten = "hook_" + hashlib.md5((HOOK_MODEL + HOOK_PHAN_GIAI + y["prompt_en"]).encode("utf-8")).hexdigest()[:12]
        f = os.path.join(thu, ten + ".mp4")
        if os.path.isfile(f) and os.path.getsize(f) > 20000:
            y["file_prompt"] = y["prompt_en"]
            return f
        try:                                                 # 25/10: tải về tên RIÊNG (…_goc): đứt giữa chừng không để
            r = flow_video.tao(y["prompt_en"], thu, ten + "_goc", model=HOOK_MODEL, phan_giai=HOOK_PHAN_GIAI,
                               do_dai=f"{HOOK_CLIP_GIAY}s", bao=lambda m: None)   # lại f còn logo bị coi là xong
        except Exception as e:                               # noqa: BLE001
            bao(f"! hook câu {y['cau']}: Flow lỗi ({str(e)[:100]})")
            return None
        if not r.get("tep"):
            return None
        sach(r["tep"][0], f, y)                              # logo ✦ của video Flow
        y["file_prompt"] = y["prompt_en"]
        bao(f"hook câu {y['cau']}: xong video ({r.get('diem')} điểm, hồ sơ {r.get('ho_so')})")
        return f
    luong = max(1, min(len(ds), flow_ve.so_ho_so_dung_duoc() if hasattr(flow_ve, "so_ho_so_dung_duoc") else 1))
    bao(f"tạo {len(ds)} video hook bằng Flow {HOOK_MODEL} {HOOK_CLIP_GIAY}s ({luong} hồ sơ song song)…")
    with ThreadPoolExecutor(luong) as ex:
        tep = list(ex.map(mot, ds))
    for y, f in zip(ds, tep):
        y["file"] = f or ""
    ghi_json(_p(du_an), kq)
    ra = xep_lich(ds, float(kq.get("het_hook") or kq.get("giay_hook") or HOOK_GIAY))
    bao(f"{len(ra)}/{len(ds)} video hook dùng được" + (f" (đặt {ra[0]['bd']:.1f}-{ra[-1]['het']:.1f} s)" if ra else ""))
    return ra
