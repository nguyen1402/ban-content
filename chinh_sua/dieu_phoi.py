# -*- coding: utf-8 -*-
"""ĐIỀU PHỐI lớp minh hoạ theo lời (13/10 user): MỘT lần hỏi ChatGPT cho mỗi đoạn lời, mỗi câu tối đa MỘT lớp:

  the          thẻ ảnh highlight (lop_phu.py)                  — số liệu, bước ngoặt, so sánh, nhấn mạnh
  khoanh_vung  bản đồ vệ tinh khoanh vùng / ghim điểm           — nhắc một vùng / nước / thành phố thật
  duong_di     bản đồ đường đi A -> B + icon phương tiện       — di chuyển giữa hai địa danh thật
  lan_rong     bản đồ một nơi toả ra nhiều nơi                  — "lan ra khắp…"
  dien_canh    ẢNH THẬT ĐÃ TÁCH NỀN diễn lại hành động / giai đoạn / biến đổi theo lời — Remotion trên nền video TỐI
               (13/10 user: bỏ icon emoji và kiểu ô tròn nối mũi tên; bản thử chỉ tới minh_hoa.MO_PHONG_DEN giây)

Câu trả lời lưu ở ra/<dự án>/dieu_phoi_hoi.json (khoá = md5 câu lệnh + đoạn lời): chạy lại giữ nguyên lựa chọn."""
import hashlib
import os

from common import doc_json, ghi_json, hoi_nhieu, log, rut_json

CAU_MOI_DOAN = 20
KIEU = {"the", "nhan_vat", "ban_do_ve", "khoanh_vung", "duong_di", "lan_rong", "dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong",
        "so_sanh", "su_kien", "giai_thich", "tai_hien"}
PHUONG_TIEN = {"may_bay", "tau_thuy", "tau_hoa", "xe", "di_bo", "tu_lan", "khac"}
HANH_DONG = {"bay_toi", "tan_cong", "bao_vay", "lan_ra", "sinh_soi", "bo_chay", "an", "mang_di"}
DONG_THE = """- "the": a HIGHLIGHT CARD (real photo + short caption) for an IMPORTANT idea. Fields: "anh", "chu", "moc".
"""
_P = """You are the lead visual director and editor of a premium documentary series (style: Vox, Netflix, Bloomberg Quicktake, Johnny Harris). B-roll footage plays while the narrator speaks. Your job is to select sentences to trigger dynamic visual layers (maps, data visualizations, timeline milestones). At most ONE layer per sentence.

- "so_sanh": KEY NUMBER shown as big white text on a dark overlay (19/10 user: no charts).
  ONLY for one striking figure, or two figures compared, that the narrator says (e.g. "300 con", "3.000 USD mỗi ngày").
  Fields:
  * "tieu_de": short Vietnamese title (what the number is about).
  * "ben_a": {{"ten": "short label", "gia_tri": "the figure as written, digits"}}.
  * "ben_b": {{"ten": "...", "gia_tri": "..."}} only when two figures are compared.
  * "moc": 2-6 words from sentence.

- "su_kien": HISTORICAL YEAR OR TIMELINE DATE (CHỮ MỐC THỜI GIAN TINH GỌN).
  Use for historical dates, years, centuries or era milestones (e.g. "Năm 1859", "Thế kỷ 19", "Năm 1954").
  Fields:
  * "nam": the clean short year/milestone text ONLY (e.g. "THẾ KỶ 19", "NĂM 1859", "NĂM 1990").
  * "moc": 2-6 words from the sentence.

- "khoanh_vung": REAL SATELLITE MAP seen from space, zooming down to a real place with its territory outlined.
  Use when the narrator mentions or focuses on a real geographic place (country, state, island, bay, coast, river, lake,
  city, reserve). It will appear early so viewers have time to locate it!
  Fields: "dia_danh" (FULL official English name + region + country, precise enough to find on a map, e.g.
  "Delaware Bay, Delaware, United States"), "ten_vi" (short Vietnamese name, e.g. "Vịnh Delaware").

- "duong_di": MAP ROUTE / MOVEMENT (BẢN ĐỒ ĐƯỜNG ĐI A -> B).
  Movement or spread between two distant locations. Fields: "tu", "den", "tu_vi", "den_vi", "phuong_tien".

Rules:
- Every layer MUST have "moc": 2-8 words copied EXACTLY from the sentence where it starts.
- Return ONLY JSON array: [{{"cau": <sentence index>, "kieu": "<kind>", "moc": "...", ...fields}}]

PASSAGE:
{ds}"""

# 19/10 user ("nội dung cần tổng quát"): ảnh AI hỏi RIÊNG, lệnh ngắn một việc, KHÔNG ví dụ riêng của phim nào
_P_AI = """You plan AI-generated still photos for a documentary video. Real b-roll footage already plays under the narration;
an AI photo is added only where the viewer needs to SEE a specific moment of the story.

{ho_so}
Read the narration (each line: index. [spoken seconds] sentence) and split it into the SCENES a viewer should see:
- Images go to the MOMENTS OF THE STORY that real stock footage cannot show — a specific event, action or turn of events
  that helps the viewer UNDERSTAND what happened (an animal released from a boat, a capsule held in a gloved hand, a
  predator cornering prey, a helicopter hunt, workers stripping a machine, an object sinking). About one image per
  15-25 seconds of narration. Lines marked (WEAK FOOTAGE) are where the real footage does not match the words: give
  them an image whenever they describe something visible. A sentence that only says a subject exists, lives somewhere,
  roams or looks like something gets NO image (footage already shows it). Opinion, questions, transitions, summaries,
  statistics, money, news / public reaction and abstract reasoning get NO image.
- REAL, NAMED people (officials, scientists, activists, photographers…): do NOT try to show who they are. Show the
  ACTION or SITUATION the narration says they are in, with NO recognisable face — hands signing a document at a desk,
  a crowd of protesters holding signs seen from behind, a person speaking at a podium seen from the back of the room,
  a photographer's silhouette behind a camera. Never put a name, likeness or portrait of the real person in the image.
- Consecutive sentences about the same moment form ONE scene with ONE image: "cau" = its first sentence, "den_cau" = its
  last sentence (at most 3 sentences).
- "ve_1": ONE simple English description, max 25 words: camera angle + main subject + what it does + where. One clear
  idea a viewer understands in one second; do not cram details. It must include what the action is aimed at or about,
  with the narration's numbers. Sensible camera: a person acting on something -> from behind them toward it; a moving
  vehicle -> from outside; an object or detail -> close-up of the object itself.
- A scene spoken for more than 8 seconds may get "ve_2" (and "ve_3") for its next moments, each with its own "moc_n".
- Describe the SPECIFIC action of that moment in your own words; take only the subject's short look and the place from
  the story bible — never paste the bible description, and never give two images the same description.
Return ONLY a JSON array, one object per image, exactly in this form ("cau" / "den_cau" are sentence NUMBERS):
[{{"cau": 4, "den_cau": 5, "ve_1": "<english shot>", "moc_1": "<2-5 words copied verbatim from sentence 4 where the image
starts>", "huong_1": "<camera move that follows the action: trai | phai | len | xuong | vao | ra>",
"thoi_dai": "<the YEAR or period this moment happens in (e.g. 1904, 1960s, 2001), or present day>",
"tieu_de": "<short Vietnamese title>"}}]
"thoi_dai" is about WHEN THIS MOMENT HAPPENS in the story (a flashback to 1904 is 1904 even in a modern story) — it sets
the photographic look and colours of that era. "huong_n" (one per image): trai / phai = pan left / right (movement or
gaze sideways), len / xuong = tilt up / down (lifting, falling, sinking, climbing), vao = push in (detail, tension), ra =
pull out (reveal, scale).

NARRATION:
{ds}"""


VE_AI_HOAN_THIEN = True     # 22/10 user: BẬT LẠI ảnh AI diễn biến ở ✨ (kho video + ảnh AI mô tả diễn biến, đúng thời đại);
#                             danh sách 📝 Chỗ vẽ ảnh AI để duyệt. (19/10 từng tắt, chuyển sang nút 🎨 tự tạo.)
AI_DIEU_PHOI = "gemini"      # 19/10 user: lên kế hoạch ảnh bằng Gemini (ChatGPT hay bỏ đối tượng bị ngắm); hỏng -> ChatGPT
KIEU_TAT = set()             # 22/10 user: BẬT bản đồ vệ tinh địa danh (ban_do.clip_dia_danh: từ vũ trụ bay xuống + viền
#                             lãnh thổ thật) — 18/10 từng tắt khung BanDoNen cũ
HO_SO_THU = 3                # số lần thử lập hồ sơ câu chuyện (lỗi thường nhất thời)
YEU_DIEM = 0.14             # 22/10: đoạn bản thô khớp dưới mức này (~20% kém nhất, đo America_thu_bam) = FOOTAGE YẾU
YEU_TI_LE = 0.4              # câu có >= 40% thời lượng là footage yếu / trống -> đánh dấu cho lệnh ảnh AI ưu tiên
AI_CACH_GIAY = 0.0          # 18/10 user: bỏ giới hạn cách 20 s — chỗ nào kể quá trình / chuỗi hành động là có ảnh slow         # 18/10 user: hai chuỗi ảnh AI tái hiện cách nhau ít nhất bấy nhiêu giây (thay mật độ 65-85%)
_KHONG_AI = __import__("re").compile(r"\?")   # 19/10 user: bỏ danh sách từ gõ tay — câu hỏi thì không vẽ, còn lại AI tự xét


def _khong_hop_ai(x, c):
    """Lý do loại một lớp ảnh AI tái hiện ('' = giữ): câu không có hành động nhìn thấy được."""
    tx = str(c.get("text") or "")
    if _KHONG_AI.search(tx):
        return "câu hỏi"
    if not str(x.get("ve_1") or x.get("ve") or "").strip():
        return "thiếu mô tả ảnh"
    return ""                                                # 19/10: lệnh ảnh AI riêng tự xét câu nào cần ảnh


_P_HO_SO = """Read this documentary narration (Vietnamese) and write a STORY BIBLE so that every AI image of the video looks
like the same real story. Only VISIBLE recurring things: places, animals, people, vehicles, key objects.
  * "boi_canh": the real settings — for each: "noi" (place as named) and "mo_ta_en" (English: landscape, vegetation,
    terrain, climate, typical light).
  * "nhan_vat": recurring subjects — for each: "ten" (as named in the script) and "mo_ta_en" (English, FIXED look reused in
    every image, SHORT (max 12 words): species / number / colour / one key marking or clothing / vehicle colour; invent plausible
    fixed details when the script does not say). Note changes of look over time explicitly. People wear ordinary clothes
    of their role and era unless the script says otherwise. A REAL, NAMED person gets ONLY their role and era clothing
    (e.g. "official in a dark suit", "activist in a rain jacket") — never a face, age or likeness, never their name.
Only JSON: {{"boi_canh": [{{"noi": "...", "mo_ta_en": "..."}}], "nhan_vat": [{{"ten": "...", "mo_ta_en": "..."}}]}}

NARRATION:
{kb}"""


def ho_so(cau, out):
    """19/10 user (ảnh lệch bối cảnh / nhân vật đổi dạng giữa các ảnh): MỘT lần hỏi cho cả kịch bản -> khối chữ
    "STORY BIBLE" gắn vào mọi lần điều phối. Lưu ra/<dự án>/ho_so_truyen.json theo băm kịch bản. Lỗi -> ""."""
    kb = " ".join(str(c.get("text") or "") for c in cau)[:30000]
    k = hashlib.md5(("hs4|" + kb).encode("utf-8")).hexdigest()[:16]   # hs4 (22/10): người thật chỉ vai trò + trang phục
    p_luu = os.path.join(out, "ho_so_truyen.json")
    da = doc_json(p_luu, {}) or {}
    j = da.get("ho_so") if da.get("_k") == k else None
    if not isinstance(j, dict):
        log("[ĐP] lập hồ sơ câu chuyện (bối cảnh + ngoại hình cố định của nhân vật)…")
        # 22/10 user ("không lập được hồ sơ thì phải làm thế nào"): lỗi thường là NHẤT THỜI (một tài khoản treo 300 s) ->
        # thử lại tối đa HO_SO_THU lần (hoi_nhieu tự đổi tài khoản / sang ChatGPT), ghi rõ lý do từng lần
        for lan in range(HO_SO_THU):
            try:
                r = (hoi_nhieu([_P_HO_SO.format(kb=kb)], timeout=300, ai=AI_DIEU_PHOI) or [""])[0] or ""
                j = rut_json(r)
                ly = "" if isinstance(j, dict) else ("AI không trả lời" if not r.strip() else "trả lời sai dạng JSON")
            except Exception as e:                           # noqa: BLE001
                j, ly = None, f"{type(e).__name__}: {str(e)[:80]}"
            if isinstance(j, dict):
                break
            log(f"[ĐP] ! lập hồ sơ câu chuyện lần {lan + 1}/{HO_SO_THU} hỏng ({ly})" + (" — thử lại" if lan + 1 < HO_SO_THU else ""))
        if not isinstance(j, dict):
            log("[ĐP] ! KHÔNG lập được hồ sơ câu chuyện sau nhiều lần — ảnh AI lần này chưa đồng bộ ngoại hình; "
                "lần ✨ sau tự lập lại (và tự làm lại danh sách 📝 nếu bạn chưa duyệt)")
            return ""
        ghi_json(p_luu, {"_k": k, "ho_so": j})
    dong = [f"  - SETTING {x.get('noi', '')}: {x.get('mo_ta_en', '')}" for x in j.get("boi_canh") or [] if isinstance(x, dict)]
    dong += [f"  - {x.get('ten', '')}: {x.get('mo_ta_en', '')}" for x in j.get("nhan_vat") or [] if isinstance(x, dict)]
    if not dong:
        return ""
    return ("STORY BIBLE — use these SHORT looks so the same subject looks the same in every image (keep shots simple):\n" + "\n".join(dong) + "\n")


def _cau_footage_yeu(cau, out):
    """22/10 user ("chỗ cần hình minh hoạ"): câu mà BẢN THÔ khớp kém — đoạn hình điểm < YEU_DIEM hoặc trống chiếm
    >= YEU_TI_LE thời lượng câu (dung.json + tu_khoa.json của dự án; theo giây tuyệt đối). Không có bản thô -> rỗng."""
    dung = doc_json(os.path.join(out, "dung.json"), {}) or {}
    canh = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    if not dung or not canh:
        return set()
    tot = []                                                 # khoảng (giây tuyệt đối) có hình khớp ĐỦ
    for c in canh:
        kh = dung.get(str(c.get("id"))) or {}
        c0 = float(c.get("bat_dau") or 0)
        for d, sc in zip(kh.get("doan") or [], kh.get("diem") or [None] * len(kh.get("doan") or [])):
            if sc is not None and float(sc) >= YEU_DIEM:
                tot.append((c0 + float(d.get("bd") or 0), c0 + float(d.get("bd") or 0) + float(d.get("dai") or 0)))
    ra = set()
    for c in cau:
        a, b = float(c.get("t0") or 0), float(c.get("t1") or 0)
        if b - a < 0.5:
            continue
        phu = sum(max(0.0, min(b, y) - max(a, x)) for x, y in tot)
        if 1 - phu / (b - a) >= YEU_TI_LE:
            ra.add(c["i"])
    return ra


def hoi(cau, out, co_the=True, toan_bo=None):
    """[{cau(int), kieu, moc, ...}] — mỗi câu tối đa một lớp; câu nằm trong den_cau của sơ đồ trước thì bỏ lớp khác.
    toan_bo: mọi câu của kịch bản (cho hồ sơ câu chuyện) khi `cau` chỉ là một phần."""
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    hs = ho_so(toan_bo or cau, out) if VE_AI_HOAN_THIEN else ""
    ds_lot = [chr(10).join(f"{c['i']}. [{max(0.5, float(c.get('t1', 0)) - float(c.get('t0', 0))):.0f}s] {c['text']}" for c in lot)
              for lot in lots]
    yeu = _cau_footage_yeu(cau, out) if VE_AI_HOAN_THIEN else set()
    ds_lot_ai = [chr(10).join(f"{c['i']}. [{max(0.5, float(c.get('t1', 0)) - float(c.get('t0', 0))):.0f}s]"
                              f"{' (WEAK FOOTAGE)' if c['i'] in yeu else ''} {c['text']}" for c in lot) for lot in lots]
    if yeu:
        log(f"[ĐP] {len(yeu)} câu footage yếu ở bản thô -> lệnh ảnh AI ưu tiên")
    p_hoi = [_P.format(ds=d) for d in ds_lot] + ([_P_AI.format(ho_so=hs, ds=d) for d in ds_lot_ai] if VE_AI_HOAN_THIEN else [])
    khoa = [hashlib.md5(p.encode("utf-8")).hexdigest()[:16] for p in p_hoi]
    khoa_ai = set(khoa[len(lots):])
    p_luu = os.path.join(out, "dieu_phoi_hoi.json")
    da = doc_json(p_luu, {}) or {}
    can = [k for k, kk in enumerate(khoa) if rut_json(da.get(kk) or "") is None]
    log(f"[ĐP] điều phối lớp minh hoạ + ảnh AI: hỏi {AI_DIEU_PHOI} {len(can)}/{len(p_hoi)} lệnh (còn lại dùng câu trả lời đã lưu)…")
    if can:
        for k, r in zip(can, hoi_nhieu([p_hoi[k] for k in can], timeout=300, ai=AI_DIEU_PHOI)):
            if rut_json(r or "") is not None:
                da[khoa[k]] = r
        ghi_json(p_luu, da)
    co = {c["i"] for c in cau}
    phu_ai = set()
    ra, phu = [], set()
    for kk in khoa:
        for x in (rut_json(da.get(kk) or "") or []):
            if not isinstance(x, dict) or (x.get("kieu") not in KIEU and kk not in khoa_ai):
                continue
            if kk in khoa_ai:                                # lệnh ảnh AI: mọi phần tử là ảnh AI
                x = dict(x, kieu="tai_hien", moc=x.get("moc") or x.get("moc_1"))
                for f_ in ("cau", "den_cau"):                # AI đôi khi ghi nguyên văn câu thay cho số câu
                    if not str(x.get(f_, "")).strip().isdigit():
                        x[f_] = next((c["i"] for c in cau if str(x.get(f_) or "").strip()[:40] in c["text"]), None)
            elif x.get("kieu") == "tai_hien":                # lệnh chung không còn vẽ ảnh AI
                continue
            try:
                i = int(x.get("cau"))
                den = int(x.get("den_cau") or i)
            except (TypeError, ValueError):
                continue
            la_ai = x["kieu"] in ("tai_hien", "dien_canh")   # 19/10 user: câu có cả mốc thời gian + hành động giữ CẢ HAI
            phu_ = phu_ai if la_ai else phu
            if i not in co or i in phu_:
                continue
            x = dict(x, cau=i, den_cau=max(i, min(den, i + 2)) if x["kieu"] in ("dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong", "tai_hien") else i)
            phu_.update(range(i, x["den_cau"] + 1))
            ra.append(x)

    # Lọc chất lượng cao & tăng tối đa mật độ AI Storytelling theo yêu cầu người dùng
    KIEU_BO = {"mo_phong", "cau_tao", "vong_doi"}
    ra_loc = []
    cuoi_bando, dem_bando = -999, 0
    cuoi_taihien, dem_taihien = -999, 0
    cau_theo_i = {c["i"]: c for c in cau}
    t_ai_cuoi, bo_ai = -1e9, {}
    cuoi_callout = -999
    da_nv = set()

    for x in sorted(ra, key=lambda z: z["cau"]):
        k = x["kieu"]
        if k in KIEU_BO or k in KIEU_TAT:
            continue
        # Khống chế bản đồ: tối đa 3 lần/video, cách nhau tối thiểu 20 câu
        if k in ("khoanh_vung", "duong_di", "lan_rong", "ban_do_ve"):
            if dem_bando >= 3 or (x["cau"] - cuoi_bando < 15):
                continue
            dem_bando += 1
            cuoi_bando = x["den_cau"]
            ra_loc.append(x)
        # 18/10 user (ảnh AI "vớ vẩn, không cần thiết"): chỉ câu có CHỦ THỂ + HÀNH ĐỘNG nguyên văn, không phải câu
        # bình luận / hỏi / kêu gọi / chuyển ý / số liệu; các chuỗi ảnh cách nhau >= AI_CACH_GIAY (thay trần 80 lần)
        elif k in ("tai_hien", "dien_canh"):
            ly_do = _khong_hop_ai(x, cau_theo_i.get(x["cau"]) or {})
            if ly_do:
                bo_ai[ly_do] = bo_ai.get(ly_do, 0) + 1
                continue
            t_ = float((cau_theo_i.get(x["cau"]) or {}).get("t0") or 0)
            if x["cau"] <= cuoi_taihien or t_ - t_ai_cuoi < AI_CACH_GIAY:
                bo_ai["gần chuỗi trước"] = bo_ai.get("gần chuỗi trước", 0) + 1
                continue
            dem_taihien += 1
            cuoi_taihien = x["den_cau"]
            t_ai_cuoi = t_
            ra_loc.append(x)
        # 22/10 user: NHÂN VẬT THẬT -> ảnh thật (Google) phủ lên footage, mỗi người MỘT lần (lần nhắc đầu)
        elif k == "nhan_vat":
            ten_ = str(x.get("ten") or "").strip().lower()
            if not ten_ or not str(x.get("anh") or "").strip() or ten_ in da_nv:
                continue
            da_nv.add(ten_)
            ra_loc.append(x)
        # Các HUD callout (so_sanh, su_kien, giai_thich, con_so, song): cách nhau tối thiểu 2 câu
        elif k in ("so_sanh", "su_kien", "giai_thich", "quy_trinh", "con_so", "song"):
            if x["cau"] - cuoi_callout < 2:
                continue
            cuoi_callout = x["den_cau"]
            ra_loc.append(x)
        else:
            ra_loc.append(x)
    ra = ra_loc
    if bo_ai:
        log("    ảnh AI tái hiện bị loại: " + ", ".join(f"{k} {v}" for k, v in bo_ai.items()))
    if VE_AI_HOAN_THIEN:
        ra = _ap_ke_hoach_ai(ra, cau, out, toan_bo or cau, co_ho_so=bool(hs))

    _bu_tieu_de(ra, out)
    dem = {}
    for x in ra:
        dem[x["kieu"]] = dem.get(x["kieu"], 0) + 1
    log("    " + ", ".join(f"{k} {v}" for k, v in sorted(dem.items())))
    return ra


KE_HOACH_AI = "anh_ai_ke_hoach.json"


def _khoa_cau(cau):
    return hashlib.md5("|".join(f"{c['i']}:{c.get('text', '')}" for c in cau).encode("utf-8")).hexdigest()[:16]


def _ap_ke_hoach_ai(ra, cau, out, toan_bo, co_ho_so=True):
    """19/10 user: DANH SÁCH CHỖ VẼ ẢNH AI do người dùng duyệt (thêm / bỏ / sửa trên giao diện 📝).
    Chưa có (hoặc lời đã đổi) -> ghi đề xuất của AI làm danh sách. Đã có -> ảnh AI lấy ĐÚNG theo danh sách (bỏ mục bị
    tắt; mục người dùng thêm mà chưa có câu mô tả -> hỏi AI viết một lượt)."""
    p = os.path.join(out, KE_HOACH_AI)
    k = _khoa_cau(cau)
    theo_i = {c["i"]: c for c in cau}
    ai = [x for x in ra if x.get("kieu") == "tai_hien"]
    khac = [x for x in ra if x.get("kieu") != "tai_hien"]
    da = doc_json(p, {}) or {}
    # 22/10 user: danh sách lập lúc THIẾU hồ sơ câu chuyện mà người dùng CHƯA duyệt -> nay có hồ sơ thì lập lại cho đồng bộ
    lam_lai = da.get("co_ho_so") is False and co_ho_so and not da.get("duyet")
    if lam_lai:
        log("    danh sách 📝 trước lập lúc thiếu hồ sơ câu chuyện (chưa duyệt) -> lập lại theo hồ sơ")
    if da.get("_k") != k or not isinstance(da.get("ds"), list) or lam_lai:
        ds = [{f: x[f] for f in ("cau", "den_cau", "ve_1", "ve_2", "ve_3", "moc_1", "moc_2", "moc_3", "huong_1", "huong_2",
                                 "huong_3", "thoi_dai", "tieu_de", "moc")
               if x.get(f) not in (None, "")} for x in ai]
        ghi_json(p, {"_k": k, "ds": ds, "duyet": False, "co_ho_so": bool(co_ho_so)})
        log(f"    danh sách chỗ vẽ ảnh AI: {len(ds)} chỗ (sửa ở 📝 Chỗ vẽ ảnh AI)")
        return ra
    ds = [dict(y) for y in da["ds"] if isinstance(y, dict) and not y.get("bo") and int(y.get("cau") or 0) in theo_i]
    thieu = [y for y in ds if not str(y.get("ve_1") or "").strip()]
    if thieu:
        hs = ho_so(toan_bo, out)
        t = (hoi_nhieu([_P_VE_TAY.format(ho_so=hs, ds="\n".join(
            f"{y['cau']}: " + " ".join(theo_i[j]["text"] for j in range(int(y["cau"]), int(y.get("den_cau") or y["cau"]) + 1)
                                        if j in theo_i) for y in thieu))], timeout=200, ai=AI_DIEU_PHOI) or [""])[0]
        j = rut_json(t or "") or {}
        for y in thieu:
            y["ve_1"] = str((j.get(str(y["cau"])) if isinstance(j, dict) else "") or "").strip()
        da_ds = [dict(z) for z in da["ds"]]
        for z in da_ds:                                       # lưu câu mô tả vừa viết để người dùng thấy / sửa
            m = next((y for y in thieu if y["cau"] == z.get("cau") and y.get("den_cau") == z.get("den_cau")), None)
            if m and m["ve_1"]:
                z["ve_1"] = m["ve_1"]
        ghi_json(p, dict(da, ds=da_ds))
    td = [(int(y["cau"]), y["thoi_dai"]) for y in ds if y.get("thoi_dai")]
    moi = []
    for y in ds:
        if not str(y.get("ve_1") or "").strip():
            continue
        i = int(y["cau"])
        den = max(i, min(int(y.get("den_cau") or i), i + 2))
        moc = y.get("moc_1") or y.get("moc") or " ".join(str(theo_i[i]["text"]).split()[:4])
        if not y.get("thoi_dai") and td:                      # chỗ người dùng thêm: thời đại của chỗ gần nhất
            y["thoi_dai"] = min(td, key=lambda z: abs(z[0] - i))[1]
        moi.append(dict(y, kieu="tai_hien", cau=i, den_cau=den, moc=moc, moc_1=moc, tay=True))
    log(f"    ảnh AI theo danh sách đã duyệt: {len(moi)} chỗ (AI đề xuất {len(ai)})")
    return khac + moi


_P_VE_TAY = """For each numbered narration line below (a documentary scene) write ONE simple English photo description,
max 25 words: camera angle + main subject + what it does + where. One clear idea; include what the action is aimed at.
{ho_so}
{ds}
Return ONLY JSON: {{"<number>": "<description>"}}"""


def _bu_tieu_de(ra, out):
    """14/10: ảnh tổng quát mà ChatGPT quên "tieu_de" (đo chuot_newyor: cả lô câu 1-20 thiếu) -> hỏi MỘT lượt cho mọi cảnh
    thiếu, từ y_tuong + câu lời. Cache ra/<dự án>/tieu_de_bu.json."""
    thieu = [x for x in ra if x.get("kieu") == "dien_canh" and x.get("khuon") == "tong_quat" and not x.get("tieu_de")]
    if not thieu:
        return
    p_luu = os.path.join(out, "tieu_de_bu.json")
    da = doc_json(p_luu, {}) or {}
    khoa = lambda x: hashlib.md5(str(x.get("y_tuong") or x.get("ve") or "").encode("utf-8")).hexdigest()[:12]   # noqa: E731
    can = [x for x in thieu if khoa(x) not in da]
    if can:
        t = hoi_nhieu(["For each numbered illustration idea below, write a short Vietnamese caption (3-8 words) that sums "
                       "up the idea, numbers as digits. Return ONLY JSON: {\"1\": \"...\", \"2\": \"...\"}\n\n"
                       + "\n".join(f"{n}. {x.get('y_tuong') or x.get('ve')}" for n, x in enumerate(can, 1))], timeout=120)[0]
        j = rut_json(t or "")
        if isinstance(j, dict):
            for n, x in enumerate(can, 1):
                c = str(j.get(str(n)) or "").strip()
                if 2 <= len(c.split()) <= 12:
                    da[khoa(x)] = c
            ghi_json(p_luu, da)
    for x in thieu:
        if da.get(khoa(x)):
            x["tieu_de"] = da[khoa(x)]
