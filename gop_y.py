# -*- coding: utf-8 -*-
"""GÓP Ý CHO AI VIẾT LẠI (27/10 user: "hỏi AI xong sẽ có 1 ô để tôi góp ý kiến để AI dựa vào ý kiến của tôi viết lại theo
ý tôi — cả hình ảnh và tạo Veo").

  ke_hoach(du_an, y_kien, ds)  — danh sách 📝 Chỗ ảnh AI & Veo (anh_ai_ke_hoach.json) viết lại theo góp ý
  hook(du_an, y_kien)          — câu lệnh video hook (hook_video.json) viết lại theo góp ý
Một lần hỏi AI; chỗ / câu lệnh góp ý không nhắc tới thì giữ nguyên."""
import json
import os
import re

from common import doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

_P_KH = """You revise the list of places in a documentary where an AI picture is shown INSTEAD of real footage.
Two kinds of place:
  "anh" = a chain of AI still photos (free): "ve_1", "ve_2", … each ONE simple English photo description (max 25 words:
          camera angle + main subject + what it does + where); one photo per <= 5 seconds of narration;
  "veo" = ONE 10-second AI VIDEO clip (costs credits — about {con} clips are left today): "veo_en" = ONE English video
          prompt, 50-100 words, 2-3 shots with hard cuts ("Shot 1: … Cut to shot 2: …"), real-looking live action, no
          text, ending with "Natural ambient sound effects only, no dialogue, no voice-over, no music."; also give "ve_1"
          (one photo description of the same moment, used if the clip cannot be made).
{ho_so}
THE USER'S FEEDBACK (Vietnamese) — follow it exactly:
{y_kien}

Rules:
- Places the feedback does not mention stay EXACTLY as they are (copy every field unchanged, including "bo").
- A place covers sentences "cau" .. "den_cau" (sentence numbers, at most 3 sentences).
- Never put a place in a sentence that starts before {het_hook:.0f} s — the opening hook is already covered by AI video.
- Never show the face of a real named person (silhouettes, from behind, hands, wide shots).
- "bo": true means the user switched the place off — keep it off unless the feedback asks to bring it back.

CURRENT LIST (JSON):
{ds}

NARRATION (sentence number. [start second] text):
{cau}

Return ONLY the full new JSON list, sorted by "cau":
[{{"cau": 12, "den_cau": 13, "loai": "anh", "ve_1": "...", "ve_2": "...", "tieu_de": "<short Vietnamese title>"}},
 {{"cau": 30, "den_cau": 31, "loai": "veo", "veo_en": "...", "ve_1": "...", "tieu_de": "..."}}]"""

_P_HK = """You revise the AI VIDEO prompts (Google Veo / Flow, 10-second clips, 16:9) of a documentary's OPENING HOOK.
Each clip covers one 10-second window of the narration (shown below with its sentences).
{ho_so}
THE USER'S FEEDBACK (Vietnamese) — follow it exactly:
{y_kien}

Rules: keep EXACTLY {so} clips, same "clip" numbers and order. Clips the feedback does not mention stay unchanged (copy
them). A rewritten "prompt_en": 60-110 words, 2-3 shots with hard cuts ("Shot 1: … Cut to shot 2: …"), what the narration
says during that window, same characters / colour grade / light in every clip, real-looking live action, no text, never
the face of a real named person; if "am" is "tieng_dong" end it with "Natural ambient sound effects only, no dialogue, no
voice-over, no music." Also update "khung_dau" (one English sentence: a strong first frame) and "mo_ta_vi" (short
Vietnamese description) when the prompt changes.

CURRENT CLIPS (JSON):
{ds}

Return ONLY JSON: [{{"clip": 1, "prompt_en": "...", "khung_dau": "...", "mo_ta_vi": "...", "am": "tieng_dong"}}]"""


def _ho_so(out, cau):
    import veo_canh
    return veo_canh.ho_so(out, cau)


def _hoi(p):
    for _ in range(2):
        j = rut_json((hoi_nhieu([p], timeout=300, ai="gemini") or [""])[0] or "")
        if isinstance(j, list) and j:
            return j
    raise ValueError("AI không trả danh sách mới (thử lại)")


def ke_hoach(du_an, y_kien, ds=None):
    """Viết lại danh sách 📝 theo góp ý -> {"ds": [...]} (đã lưu, coi như người dùng đã duyệt)."""
    import cho_phu
    import flow_video
    y_kien = str(y_kien or "").strip()
    if not y_kien:
        raise ValueError("chưa có góp ý")
    out = thu_muc_du_an(du_an)[1]
    p = os.path.join(out, "anh_ai_ke_hoach.json")
    da = doc_json(p, {}) or {}
    ds = ds if isinstance(ds, list) else da.get("ds") or []
    cau = cho_phu.doc_cau(out)
    if not cau:
        raise ValueError("chưa có câu lời (kich_ban_cau.srt) — bấm 🔄 AI đề xuất trước")
    theo = {c["i"]: c for c in cau}
    hk = cho_phu.khoang_hook(out)
    het_hook = max((b for _, b in hk), default=0.0)
    gon = [{k: v for k, v in y.items() if k in ("cau", "den_cau", "loai", "veo_en", "tieu_de", "bo", "thoi_dai")
            or re.match(r"ve_\d+$", str(k))} for y in ds if isinstance(y, dict)]
    log(f"[góp ý] AI viết lại danh sách {len(gon)} chỗ ảnh AI & Veo theo góp ý…")
    j = _hoi(_P_KH.format(con=flow_video.clip_con_hom_nay(flow_video.uoc_diem("Omni 1.1 Flash", "720p")),
                          ho_so=_ho_so(out, cau), y_kien=y_kien, het_hook=het_hook,
                          ds=json.dumps(gon, ensure_ascii=False, indent=0),
                          cau="\n".join(f"{c['i']}. [{c['t0']:.0f}s] {c['text']}" for c in cau)))
    cu = {(int(y.get("cau") or 0), int(y.get("den_cau") or y.get("cau") or 0)): y for y in ds if isinstance(y, dict)}
    moi = []
    for x in j:
        if not isinstance(x, dict):
            continue
        try:
            i = int(x.get("cau"))
            den = max(i, min(int(x.get("den_cau") or i), i + 2))
        except (TypeError, ValueError):
            continue
        if i not in theo or float(theo[i]["t0"]) < het_hook - 0.3:
            continue
        loai = "veo" if x.get("loai") == "veo" else "anh"
        z = {k: v for k, v in x.items() if (k in ("tieu_de", "thoi_dai", "bo") or re.match(r"ve_\d+$", str(k)))
             and v not in (None, "")}
        if loai == "veo" and str(x.get("veo_en") or "").strip():
            z["veo_en"] = str(x["veo_en"]).strip()
        z.update(cau=i, den_cau=den, loai=loai)
        y0 = cu.get((i, den))
        if y0 and y0.get("tay"):
            z["tay"] = True
        for k in ("moc", "moc_1", "thoi_dai"):               # giữ mốc / thời đại của chỗ cũ cùng câu
            if y0 and y0.get(k) and k not in z:
                z[k] = y0[k]
        moi.append(z)
    if not moi:
        raise ValueError("AI trả danh sách rỗng — viết góp ý rõ hơn rồi thử lại")
    moi.sort(key=lambda z: z["cau"])
    ghi_json(p, dict(da, ds=moi, duyet=True))
    log(f"[góp ý] danh sách mới: {sum(1 for z in moi if not z.get('bo'))} chỗ "
        f"({sum(1 for z in moi if z['loai'] == 'veo' and not z.get('bo'))} Veo)")
    return {"ds": moi}


def hook(du_an, y_kien):
    """Viết lại câu lệnh video hook theo góp ý -> hook_video.json mới (câu lệnh đổi thì clip cũ không dùng nữa)."""
    import cho_phu
    import hook_video
    y_kien = str(y_kien or "").strip()
    if not y_kien:
        raise ValueError("chưa có góp ý")
    out = thu_muc_du_an(du_an)[1]
    kq = hook_video.doc(du_an)
    ds = kq.get("ds") or []
    if not ds:
        raise ValueError("chưa có câu lệnh hook — bấm ✍️ Lập câu lệnh hook trước")
    gon = [{"clip": k + 1, "giay": f"{y.get('t0', 0):.0f}-{float(y.get('t0', 0)) + hook_video.HOOK_CLIP_GIAY:.0f}s",
            "loi": y.get("text"), "prompt_en": y.get("prompt_en"), "khung_dau": y.get("khung_dau"),
            "mo_ta_vi": y.get("mo_ta_vi"), "am": y.get("am")} for k, y in enumerate(ds)]
    log(f"[góp ý] AI viết lại {len(ds)} câu lệnh hook theo góp ý…")
    j = _hoi(_P_HK.format(ho_so=_ho_so(out, cho_phu.doc_cau(out)), y_kien=y_kien, so=len(ds),
                          ds=json.dumps(gon, ensure_ascii=False, indent=0)))
    doi = 0
    for n, x in enumerate(j):
        if not isinstance(x, dict) or not str(x.get("prompt_en") or "").strip():
            continue
        try:
            k = int(x.get("clip")) - 1
        except (TypeError, ValueError):
            k = n
        if not 0 <= k < len(ds):
            continue
        y = ds[k]
        p_moi = str(x["prompt_en"]).strip()
        if p_moi != y.get("prompt_en"):
            doi += 1
            y["prompt_en"] = p_moi
            for f in ("khung_dau", "mo_ta_vi"):
                if str(x.get(f) or "").strip():
                    y[f] = str(x[f]).strip()
            if x.get("am") in ("tieng_dong", "noi_chuyen"):
                y["am"] = x["am"]
    ghi_json(hook_video._p(du_an), kq)                       # noqa: SLF001
    log(f"[góp ý] đổi {doi}/{len(ds)} câu lệnh hook")
    return kq
