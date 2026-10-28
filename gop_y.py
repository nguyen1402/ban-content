# -*- coding: utf-8 -*-
"""GÓP Ý CHO AI VIẾT LẠI (27/10 user: "hỏi AI xong sẽ có 1 ô để tôi góp ý kiến để AI dựa vào ý kiến của tôi viết lại theo
ý tôi — cả hình ảnh và tạo Veo").

  cau_lenh(du_an)              — AI viết câu lệnh cho các chỗ ảnh AI / Veo NGƯỜI DÙNG đã đánh dấu ở 📝 (27/10)
  ke_hoach(du_an, y_kien, ds)  — câu lệnh của danh sách 📝 Chỗ ảnh AI & Veo (anh_ai_ke_hoach.json) viết lại theo góp ý
  hook(du_an, y_kien)          — câu lệnh video hook (hook_video.json) viết lại theo góp ý
Một lần hỏi AI; chỗ / câu lệnh góp ý không nhắc tới thì giữ nguyên."""
import json
import os
import re

from common import LUAT_YOUTUBE, doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

_P_KH = """You revise the PROMPTS of the places in a documentary where an AI picture is shown INSTEAD of real footage.
The USER chose the places and their kind — never add, remove, move or change the kind of a place; only rewrite prompts.
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
- Places the feedback does not mention stay EXACTLY as they are (copy every field unchanged).
- Keep "cau", "den_cau", "loai" and "bo" of every place exactly as given (the user's choice).
- Never show the face of a real named person (silhouettes, from behind, hands, wide shots).
- For "anh" PHOTOS only: """ + LUAT_YOUTUBE + """ ("veo" prompts show the event exactly as narrated, even raw nature.)

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
Vietnamese description) when the prompt changes. Show exactly what the narration says, even raw nature (carcasses,
scavengers, decay) — do not soften or replace it.

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
    """Viết lại CÂU LỆNH của danh sách 📝 theo góp ý (chỗ giữ nguyên) -> {"ds": [...]} (đã lưu)."""
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
        raise ValueError("chưa có câu lời (kich_ban_cau.srt) — mở lại 📝 để nạp câu lời")
    hk = cho_phu.khoang_hook(out)
    het_hook = max((b for _, b in hk), default=0.0)
    gon = [{k: v for k, v in y.items() if k in ("cau", "den_cau", "loai", "veo_en", "tieu_de", "bo", "thoi_dai")
            or re.match(r"ve_\d+$", str(k))} for y in ds if isinstance(y, dict)]
    log(f"[góp ý] AI viết lại câu lệnh của {len(gon)} chỗ ảnh AI & Veo theo góp ý…")
    j = _hoi(_P_KH.format(con=flow_video.clip_con_hom_nay(flow_video.uoc_diem("Omni 1.1 Flash", "720p")),
                          ho_so=_ho_so(out, cau), y_kien=y_kien, het_hook=het_hook,
                          ds=json.dumps(gon, ensure_ascii=False, indent=0),
                          cau="\n".join(f"{c['i']}. [{c['t0']:.0f}s] {c['text']}" for c in cau)))
    # 27/10 user ("tôi chỉ định luôn chỗ nào dùng ảnh chỗ nào dùng veo"): chỗ / loại / bỏ do NGƯỜI DÙNG chọn -> chỉ nhận
    # câu lệnh AI viết lại (ve_n / moc_n / huong_n / veo_en / tieu_de / thoi_dai), khớp theo số câu đầu
    theo_ai = {}
    for x in j:
        if isinstance(x, dict) and str(x.get("cau", "")).strip().isdigit():
            theo_ai.setdefault(int(x["cau"]), x)
    moi, doi = [], 0
    for y in ds:
        if not isinstance(y, dict):
            continue
        z = dict(y)
        x = theo_ai.get(int(z.get("cau") or 0))
        if x:
            lenh = {k: str(v).strip() for k, v in x.items() if (k in ("tieu_de", "thoi_dai") or re.match(r"(ve|moc|huong)_\d+$", str(k)))
                    and str(v or "").strip()}
            if z.get("loai") == "veo" and str(x.get("veo_en") or "").strip():
                lenh["veo_en"] = str(x["veo_en"]).strip()
            if lenh.get("ve_1"):                             # chuỗi ảnh mới thay hẳn chuỗi cũ
                for k in [k for k in z if re.match(r"(ve|moc|huong)_\d+$", str(k))]:
                    del z[k]
            if any(z.get(k) != v for k, v in lenh.items()):
                doi += 1
            z.update(lenh)
        moi.append(z)
    if not moi:
        raise ValueError("danh sách 📝 đang rỗng — đánh dấu chỗ ảnh AI / Veo trước")
    moi.sort(key=lambda z: int(z.get("cau") or 0))
    ghi_json(p, dict(da, ds=moi, duyet=True))
    log(f"[góp ý] đã viết lại câu lệnh {doi}/{len(moi)} chỗ")
    return {"ds": moi}


def cau_lenh(du_an, lam_lai=False, het_hook=0.0):
    """27/10 user: "khi tôi chỉ định rồi thì mang đi hỏi AI câu lệnh tạo thôi" — các chỗ đánh dấu ở 📝 mà chưa có câu
    lệnh (🖼 câu mô tả ảnh, 🎬 câu lệnh Veo + ảnh dự phòng) -> AI viết theo hồ sơ câu chuyện, lưu vào 📝 để xem / sửa
    trước khi ✨ vẽ. lam_lai=True: viết lại cả chỗ đã có câu lệnh. het_hook: chỗ bắt đầu trong đoạn hook Veo (giây) thì
    không viết — ✨ bỏ các chỗ đó (27/10 user: tích hook Veo rồi thì trừ các câu trong thời gian đọc hook)."""
    import sys
    import cho_phu
    import veo_canh
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import dieu_phoi
    out = thu_muc_du_an(du_an)[1]
    cau = cho_phu.doc_cau(out)
    if not cau:
        raise ValueError("chưa có câu lời (kich_ban_cau.srt) — mở lại 📝 để nạp câu lời")
    p = os.path.join(out, "anh_ai_ke_hoach.json")
    da = doc_json(p, {}) or {}
    dung = [y for y in da.get("ds") or [] if isinstance(y, dict) and not y.get("bo")]
    if not dung:
        raise ValueError("chưa đánh dấu chỗ ảnh AI / Veo nào")
    if lam_lai:
        for y in dung:
            y.pop("veo_en", None)
        ghi_json(p, da)
    het_hook = max(float(het_hook or 0), max((b for _, b in cho_phu.khoang_hook(out)), default=0.0))
    trong = {c["i"] for c in cau if float(c["t0"]) >= het_hook - 0.3}   # câu trong hook không đưa cho AI viết
    n_anh = dieu_phoi.viet_lenh(cau, out, lam_lai=lam_lai, tu_giay=het_hook)
    n_veo = veo_canh.viet_lenh(out, cau, tu_giay=het_hook)
    da = doc_json(p, {}) or {}
    thieu = [y["cau"] for y in da.get("ds") or [] if isinstance(y, dict) and not y.get("bo") and int(y.get("cau") or 0) in trong
             and not str(y.get("veo_en" if y.get("loai") == "veo" else "ve_1") or "").strip()]
    log(f"[câu lệnh] AI viết {n_anh} câu mô tả ảnh, {n_veo} câu lệnh Veo" + (f"; còn thiếu ở câu {thieu}" if thieu else ""))
    hook = sorted(int(y.get("cau") or 0) for y in da.get("ds") or [] if isinstance(y, dict) and not y.get("bo")
                  and int(y.get("cau") or 0) not in trong)
    if hook:
        log(f"[câu lệnh] bỏ qua chỗ nằm trong đoạn hook Veo (câu {hook})")
    return {"ds": da.get("ds") or [], "anh": n_anh, "veo": n_veo, "thieu": thieu, "hook": hook}


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
