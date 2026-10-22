# -*- coding: utf-8 -*-
"""CÂU LỆNH VIDEO ĐOẠN HOOK (22/10 user: "phần 4 tôi muốn nó làm video đoạn hook, càng kịch tính càng tốt, nhưng không cho
tự tạo mà chỉ cho tôi danh sách câu lệnh để tôi xem xét tự tạo vì nó có điểm giới hạn").

MỘT lần hỏi AI: lời của đoạn mở đầu (HOOK_GIAY giây đầu) + hồ sơ câu chuyện (bối cảnh, ngoại hình cố định) -> 3-6 câu lệnh
video ngắn (Veo / Flow) kịch tính, mỗi câu ứng một khoảnh khắc của lời hook: tiếng Anh cho model + mô tả tiếng Việt + gợi ý
khung đầu. KHÔNG tạo video — người dùng chép / điền vào ô 🎞 Tạo video Google Flow. Lưu ra/<dự án>/hook_video.json."""
import hashlib
import os

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

HOOK_GIAY = 30.0            # đoạn hook = ~30 giây lời đầu tiên (hết câu đang dở)
SO_TOI_DA = 6

_P = """You are the trailer editor of a documentary. Below is the OPENING HOOK of the narration (Vietnamese, numbered
sentences with their start second). Write {so} short AI VIDEO prompts (Google Veo / Flow, 8-second clips, 16:9) that make
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
  - "giay": 4, 6 or 8 (clip length that fits the spoken time of the moment).
Only JSON: [{{"cau": 1, "prompt_en": "...", "khung_dau": "...", "mo_ta_vi": "...", "giay": 8}}]

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
    k = hashlib.md5(("hk1|" + ds_txt + f"|{so}").encode("utf-8")).hexdigest()[:16]
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
        g = x.get("giay") if x.get("giay") in (4, 6, 8) else 8
        ra.append({"cau": c["id"], "text": str(c.get("text") or ""), "t0": round(float(c.get("bat_dau") or 0), 1),
                   "prompt_en": str(x["prompt_en"]).strip(), "khung_dau": str(x.get("khung_dau") or "").strip(),
                   "mo_ta_vi": str(x.get("mo_ta_vi") or "").strip(), "giay": g})
    kq = {"_k": k, "giay_hook": giay, "ds": ra}
    ghi_json(_p(du_an), kq)
    log(f"[hook] {len(ra)} câu lệnh video -> hook_video.json")
    return kq
