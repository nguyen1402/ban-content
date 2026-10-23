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
    if not hoi_lai and da.get("_k") == k and da.get("ds"):
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
    theo = {c["id"]: c for c in hook}
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
    t_het = max(float(c.get("bat_dau") or 0) + float(c.get("dai") or 0) for c in hook)
    kq = {"_k": k, "giay_hook": giay, "het_hook": round(t_het, 2), "ds": ra}
    ghi_json(_p(du_an), kq)
    log(f"[hook] {len(ra)} câu lệnh video -> hook_video.json")
    return kq


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

    def mot(y):
        ten = "hook_" + hashlib.md5((HOOK_MODEL + HOOK_PHAN_GIAI + y["prompt_en"]).encode("utf-8")).hexdigest()[:12]
        f = os.path.join(thu, ten + ".mp4")
        if os.path.isfile(f) and os.path.getsize(f) > 20000:
            return f
        try:
            r = flow_video.tao(y["prompt_en"], thu, ten, model=HOOK_MODEL, phan_giai=HOOK_PHAN_GIAI,
                               do_dai=f"{HOOK_CLIP_GIAY}s", bao=lambda m: None)
        except Exception as e:                               # noqa: BLE001
            bao(f"! hook câu {y['cau']}: Flow lỗi ({str(e)[:100]})")
            return None
        if not r.get("tep"):
            return None
        g = r["tep"][0]
        tam = f[:-4] + "._sach.mp4"
        try:
            anh_ve.xoa_logo_video(g, tam, lambda m: None)  # logo ✦ của video Flow
            os.replace(tam, f)
        except Exception as e:                               # noqa: BLE001
            bao(f"! hook câu {y['cau']}: xoá logo lỗi ({str(e)[:80]}) -> dùng bản gốc")
            os.replace(g, f)
        if os.path.isfile(g):                                # bản gốc còn logo: bỏ
            os.remove(g)
        bao(f"hook câu {y['cau']}: xong video ({r.get('diem')} điểm, hồ sơ {r.get('ho_so')})")
        return f
    luong = max(1, min(len(ds), flow_ve.so_ho_so_dung_duoc() if hasattr(flow_ve, "so_ho_so_dung_duoc") else 1))
    bao(f"tạo {len(ds)} video hook bằng Flow {HOOK_MODEL} {HOOK_CLIP_GIAY}s ({luong} hồ sơ song song)…")
    with ThreadPoolExecutor(luong) as ex:
        tep = list(ex.map(mot, ds))
    for y, f in zip(ds, tep):
        y["file"] = f or ""
    ghi_json(_p(du_an), kq)
    het = float(kq.get("het_hook") or kq.get("giay_hook") or HOOK_GIAY)
    ra = sorted([{"bd": float(y["t0"]), "file": f, "am": y.get("am") or "tieng_dong"} for y, f in zip(ds, tep) if f],
                key=lambda z: z["bd"])
    for k, z in enumerate(ra):                               # clip kéo tới clip sau / hết đoạn hook, tối đa độ dài clip
        sau = ra[k + 1]["bd"] if k + 1 < len(ra) else het
        z["het"] = round(min(sau, z["bd"] + HOOK_CLIP_GIAY), 2)
    ra = [z for z in ra if z["het"] - z["bd"] >= 1.0]
    bao(f"{len(ra)}/{len(ds)} video hook dùng được")
    return ra
