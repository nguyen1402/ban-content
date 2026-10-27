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

HOOK_GIAY = 60.0            # 27/10 user: ~1 phút đầu TOÀN video Veo (trước 30 s, chỉ đè vài khoảnh khắc)
SO_TOI_DA = 9
HOOK_CLIP_GIAY = 10         # 23/10 user: Omni 1.1 Flash 10 s (27/10: 720p = 12 điểm/clip)
HOOK_MODEL = "Omni 1.1 Flash"
HOOK_PHAN_GIAI = "720p"
AM_TIENG_DONG = 0.3         # tiếng Veo của clip tiếng động: nhỏ dưới giọng đọc

_P = """You are the trailer editor of a documentary. Below is the OPENING HOOK of the narration (Vietnamese, numbered
sentences with their start second), already split into {so} back-to-back 10-second CLIP WINDOWS. The whole hook is covered
by AI video only, so write EXACTLY {so} AI VIDEO prompts (Google Veo / Flow, 10-second clips, 16:9), one per window and in
order, each showing what the narration says DURING ITS WINDOW. Make the hook as GRIPPING and DRAMATIC as possible: tension,
scale, mystery, a striking reveal — while staying TRUE to what the narration says (no invented events). Pacing: clip 1 is
the most striking image of the hook, the last clip ends on an unresolved, ominous beat.
{ho_so}
For each clip:
  - "clip": the window number (1..{so});
  - "cau": the sentence number (inside that window) it mainly illustrates;
  - "prompt_en": ONE English video prompt, 60-110 words, built as 2-3 SHOTS with hard cuts ("Shot 1: … Cut to shot 2: …
    Cut to shot 3: …") so the 10 seconds feel fast like a trailer. Each shot: subject and action, setting and the ERA of
    that moment (period-correct clothing, vehicles, buildings; film look of that era if it is in the past), a cinematic
    CAMERA MOVE (slow push-in, crane up, low-angle tracking, aerial reveal, handheld close-up…), lighting and atmosphere
    (storm, dusk, fog, underwater god rays…). The same characters, costumes, colour grade and light in every shot and
    every clip (follow the story profile). Real-looking live action, no text, no captions, no logos, no on-screen titles.
    Never show the face of a real named person (use silhouettes, from behind, hands, or wide shots).
  - "khung_dau": one English sentence describing a strong FIRST FRAME for the clip (can be generated as an image first
    and used as the Start frame);
  - "mo_ta_vi": short Vietnamese description of the clip (1-2 sentences) for the editor;
  - "am": "noi_chuyen" if the clip shows people TALKING to each other (dialogue), otherwise "tieng_dong" (the clip's
    sound is natural action sound: waves, engines, cranes, crowds, explosions…). For "tieng_dong" clips END the prompt
    with: "Natural ambient sound effects only, no dialogue, no voice-over, no music."
Each clip is 10 seconds long.
Only JSON: [{{"clip": 1, "cau": 1, "prompt_en": "...", "khung_dau": "...", "mo_ta_vi": "...", "am": "tieng_dong"}}]

HOOK NARRATION (by clip window):
{ds}"""


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "hook_video.json")


def doc(du_an):
    return doc_json(_p(du_an), {}) or {}


def lap(du_an, hoi_lai=False, giay=HOOK_GIAY, so=None):
    """-> {"ds": [{o, cau, text, t0, prompt_en, khung_dau, mo_ta_vi, giay}], "giay_hook"}. Lời hook không đổi và đã có -> dùng lại.
    27/10: hook chia thành các cửa sổ HOOK_CLIP_GIAY giây NỐI LIỀN (clip o đặt ở o*10 s) -> cả đoạn hook toàn video Veo."""
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
    t_het = max(float(c.get("bat_dau") or 0) + float(c.get("dai") or 0) for c in hook)
    # đủ clip phủ hết hook; phần lẻ cuối <= 3 s để footage thường (không tốn 12 điểm cho 3 s)
    so = int(so or min(SO_TOI_DA, max(1, -(-int(t_het - 3) // HOOK_CLIP_GIAY))))

    def trong_o(o):                                          # câu đang được đọc trong cửa sổ o (câu dài trải nhiều cửa sổ)
        a, z = o * HOOK_CLIP_GIAY, (o + 1) * HOOK_CLIP_GIAY if o < so - 1 else t_het + 1
        return [c for c in hook if float(c.get("bat_dau") or 0) < z
                and float(c.get("bat_dau") or 0) + float(c.get("dai") or 0) > a] or [hook[-1]]
    ds_txt = "\n".join(
        f"CLIP {o + 1} [{o * HOOK_CLIP_GIAY}-{(o + 1) * HOOK_CLIP_GIAY}s]:\n" + "\n".join(
            f"  {c['id']}. [{float(c.get('bat_dau') or 0):.0f}s] {str(c.get('text') or '').strip()}"
            for c in trong_o(o)) for o in range(so))
    k = hashlib.md5(("hk3|" + ds_txt + f"|{so}").encode("utf-8")).hexdigest()[:16]
    da = doc(du_an)
    if not hoi_lai and da.get("_k") == k and da.get("ds"):
        return da
    theo = {c["id"]: c for c in hook}
    if not hoi_lai and da.get("ds") and float(da.get("giay_hook") or 0) == float(giay) and all(
            y.get("cau") in theo and str(theo[y["cau"]].get("text") or "") == y.get("text") for y in da["ds"]):
        # 25/10: đọc lại giọng chỉ lệch GIỜ (lời giữ nguyên) -> giữ câu lệnh + clip đã tạo (không hỏi AI / tốn điểm Flow
        # lần nữa), chỉ dời mốc t0 theo giọng mới
        for y in da["ds"]:                                   # clip theo cửa sổ (có "o") giữ mốc o*10 s
            y["t0"] = float(y["o"] * HOOK_CLIP_GIAY) if "o" in y else round(float(theo[y["cau"]].get("bat_dau") or 0), 1)
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
        j = rut_json(hoi_llm(_P.format(so=so, ho_so=hs, ds=ds_txt), timeout=240) or "")
        if isinstance(j, list) and j:
            break
    if not isinstance(j, list) or not j:
        raise ValueError("AI không trả câu lệnh video hook (thử lại)")
    ra, da_o = [], set()
    for n, x in enumerate(j[:so]):
        if not isinstance(x, dict) or not str(x.get("prompt_en") or "").strip():
            continue
        try:
            o = int(str(x.get("clip")).strip(" []")) - 1
        except (TypeError, ValueError):
            o = n
        o = o if 0 <= o < so and o not in da_o else n         # AI đánh số sai / trùng -> theo thứ tự trả về
        if o in da_o:
            continue
        da_o.add(o)
        trong = trong_o(o)
        try:
            ci = int(str(x.get("cau")).strip(" []"))
        except (TypeError, ValueError):
            ci = trong[0]["id"]
        c = theo.get(ci) if ci in {z["id"] for z in trong} else trong[0]
        g = HOOK_CLIP_GIAY
        ra.append({"o": o, "cau": c["id"], "text": str(c.get("text") or ""), "t0": float(o * HOOK_CLIP_GIAY),
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
    import flow_video
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    bao = bao or (lambda m: log("    " + m))
    da = doc(du_an)                                          # đã lập (vd hook 30 s cũ) -> giữ đúng độ dài đó,
    kq = lap(du_an, giay=float(da.get("giay_hook") or HOOK_GIAY))   # không hỏi AI lại (mất clip đã tạo)
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

    def co_san(y):
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
        return None

    def tao_moi(y, ho_so, khe=1):
        """Tạo clip trên đúng tài khoản ho_so (lỗi ném ra để bộ chạy đổi tài khoản / bỏ clip)."""
        ten = "hook_" + hashlib.md5((HOOK_MODEL + HOOK_PHAN_GIAI + y["prompt_en"]).encode("utf-8")).hexdigest()[:12]
        f = os.path.join(thu, ten + ".mp4")
        # 25/10: tải về tên RIÊNG (…_goc): đứt giữa chừng không để lại f còn logo bị coi là xong
        r = flow_video.tao(y["prompt_en"], thu, ten + "_goc", model=HOOK_MODEL, phan_giai=HOOK_PHAN_GIAI,
                           do_dai=f"{HOOK_CLIP_GIAY}s", bao=lambda m: None, ho_so=ho_so, gioi_han=True,
                           khe=khe, so=1)                     # 27/10 user: mỗi câu lệnh đúng 1 video (x1)
        if not r.get("tep"):
            return None
        sach(r["tep"][0], f, y)                              # logo ✦ của video Flow
        y["file_prompt"] = y["prompt_en"]
        bao(f"hook câu {y['cau']}: xong video ({r.get('diem')} điểm, hồ sơ {r.get('ho_so')})")
        return f
    tep = [co_san(y) for y in ds]                            # clip đã có: dùng lại, không mở tài khoản nào
    thieu = [y for y, f in zip(ds, tep) if not f]
    if thieu:
        can = flow_video.uoc_diem(HOOK_MODEL, HOOK_PHAN_GIAI)
        con = flow_video.clip_con_hom_nay(can)
        bao(f"tạo {len(thieu)}/{len(ds)} video hook bằng Flow {HOOK_MODEL} {HOOK_CLIP_GIAY}s (tối đa "
            f"{flow_video.SONG_SONG_VIDEO} tài khoản cùng lúc) — hôm nay còn điểm cho {con} clip"
            + (" -> phần thiếu mai bấm tạo tiếp" if con < len(thieu) else ""))
        moi = flow_video.chay_theo_tai_khoan(thieu, tao_moi, can=can, bao=bao)
        theo = {id(y): f for y, f in zip(thieu, moi)}
        tep = [f or theo.get(id(y)) for y, f in zip(ds, tep)]
    for y, f in zip(ds, tep):
        y["file"] = f or ""
    ghi_json(_p(du_an), kq)
    ra = xep_lich(ds, float(kq.get("het_hook") or kq.get("giay_hook") or HOOK_GIAY))
    bao(f"{len(ra)}/{len(ds)} video hook dùng được" + (f" (đặt {ra[0]['bd']:.1f}-{ra[-1]['het']:.1f} s)" if ra else ""))
    return ra
