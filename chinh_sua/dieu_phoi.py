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
KIEU = {"the", "ban_do_ve", "khoanh_vung", "duong_di", "lan_rong", "dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong",
        "so_sanh", "su_kien", "giai_thich", "tai_hien"}
PHUONG_TIEN = {"may_bay", "tau_thuy", "tau_hoa", "xe", "di_bo", "tu_lan", "khac"}
HANH_DONG = {"bay_toi", "tan_cong", "bao_vay", "lan_ra", "sinh_soi", "bo_chay", "an", "mang_di"}
DONG_THE = """- "the": a HIGHLIGHT CARD (real photo + short caption) for an IMPORTANT idea. Fields: "anh", "chu", "moc".
"""
_P = """You are the lead visual director and editor of a premium documentary series (style: Vox, Netflix, Bloomberg Quicktake, Johnny Harris). B-roll footage plays while the narrator speaks. Your job is to select sentences to trigger dynamic visual layers (cinematic AI storytelling reconstructions, maps, data visualizations, timeline milestones). At most ONE layer per sentence.

CRITICAL DIRECTIVE ON MAXIMUM AI IMAGE COVERAGE & MULTI-SHOT ACTION DECOMPOSITION:
The user explicitly requires: "Mật độ ảnh AI phải tăng phủ lên bất kể chỗ nào có giải thích, so sánh, mô tả trừu tượng, ẩn dụ, hoặc kể lại một quá trình, hành động nào đó... có những đoạn mô tả hành động, quá trình thì phải slow vài tấm ảnh để thể hiện được quá trình đấy, khớp theo voice: đến hành động A thì hiện ảnh A, hành động B đến ảnh B".

MANDATORY RULES:
1. Whenever a sentence describes an ACTION, PROCESS, BIOLOGICAL BEHAVIOR, PREDATION, ESCAPE, PHYSICAL MOVEMENT, or SEQUENTIAL INTERVENTION:
   You MUST generate a 2-to-3 shot continuous sequence ("ve_1", "ve_2", "ve_3") to portray the full progression in slow motion:
   * "ve_1": Beginning / Setup (Khởi đầu hành động, e.g. xe bồn đậu cạnh bờ hồ, hoặc cá chép bắt đầu cắm đầu húc bùn).
   * "moc_1": 2-5 words COPIED VERBATIM from the sentence where action 1 starts.
   * "ve_2": Main Action / Climax Close-up (Cận cảnh diễn biến cốt lõi, e.g. van xả mở ra cá săn mồi lao qua vòi, hoặc mang cá lọc giun phun bùn cát mù mịt).
   * "moc_2": 2-5 words COPIED VERBATIM from the sentence where action 2 starts (e.g. "thả xuống", "phun bùn cát", "lao ra").
   * "ve_3" (if sentence has a 3rd stage/impact): Consequence / Result (Kết quả/hậu quả, e.g. cá săn mồi khổng lồ quẫy đuôi lặn xuống lòng hồ, hoặc nước đục ngầu che khuất ánh sáng).
   * "moc_3": 2-5 words COPIED VERBATIM from the sentence where action 3 starts.
   CRITICAL: "moc_1", "moc_2", "moc_3" MUST be exact substrings from the sentence so visual cuts sync seamlessly with the narrator voice!

2. DO NOT use "giai_thich" (cards with step text) for physical actions, wildlife hunts, or mechanical events; ALWAYS use "tai_hien" multi-shot cinematic AI imagery!

3. Also generate 'tai_hien' for:
   - Any explanation or reasoning (giải thích nguyên nhân, hậu quả).
   - Any comparison, metaphor, or analogy (so sánh, ẩn dụ, ví von, hình tượng hóa).
   - Any abstract description or atmosphere (mô tả trừu tượng, cảm giác, khí hậu).
   - Mentioning any specific object, vehicle, creature, device, facility, or landmark.

Aim for 65-85% of sentences having "tai_hien" so the video is visually saturated with stunning cinematic AI imagery!

Kinds of Visual Layers:
- "tai_hien": CINEMATIC AI VISUAL STORYTELLING (PHÂN CẢNH TÁI HIỆN BẰNG AI).
  Generate photorealistic AI cinematic imagery for ANY sentence that describes: action, process, wildlife behavior, predation, ecological damage, flooding, escape, historical events, scientific experiments, or dramatic scenes.
  Fields:
  * "ve_1": Establishing / shot 1 (English, photorealistic, 16:9, e.g. "Wide cinematic shot of a specialized tanker truck parked by an Australian lake at dawn, 8k documentary photograph, award-winning lighting, no text").
  * "moc_1": 2-5 words verbatim from sentence.
  * "ve_2": Action / shot 2 (English, photorealistic, 16:9, e.g. "Action close-up shot of the tanker release valve opening, huge predatory fish tumbling out in a rush of water, authentic, no text").
  * "moc_2": 2-5 words verbatim from sentence (e.g. "thả xuống một hồ").
  * "ve_3" (optional): Climax/result / shot 3 (English, photorealistic, 16:9, e.g. "Underwater cinematic shot of the massive predatory fish diving into the deep blue lake water, splashing ripples, authentic, no text").
  * "moc_3" (optional): 2-5 words verbatim from sentence (e.g. "quét sạch kẻ xâm lấn").
  * "tieu_de": Short Vietnamese description.
  * "moc": Same as moc_1.

- "so_sanh": DIVERSE DATA VISUALIZATION (BIỂU ĐỒ & ĐỒ THỊ SỐ LIỆU ĐA DẠNG).
  ONLY for dry technical parameters, measurements, or budgets. Choose the best format ("dang"):
  * "song": Smooth Wave Trend Curve (ĐỒ THỊ LƯỢN SÓNG). Ideal for percentages, efficiency, filter rates, trends, or levels (e.g. "Hiệu suất lọc cá 88% vs 99.9%").
  * "con_so": Single Big Number / Metric Callout (CON SỐ ĐƠN LẺ). Ideal when there is ONE technical statistic to highlight (e.g. "15 triệu USD", "500.000 tấn rác"). No boxes, pure bold white numbers with clean label below.
  * "cot": Comparative Bar Chart (BIỂU ĐỒ CỘT). Ideal for comparing two contrasting quantities (Count vs Weight, Standard vs Actual).
  Fields:
  * "tieu_de": Clean Vietnamese title.
  * "dang": "song" | "con_so" | "cot".
  * "ben_a": {{"ten": "Label A", "gia_tri": "Value A"}}.
  * "ben_b": {{"ten": "Label B", "gia_tri": "Value B"}} (omit if dang is "con_so").
  * "moc": 2-6 words from sentence.

- "su_kien": HISTORICAL YEAR OR TIMELINE DATE (CHỮ MỐC THỜI GIAN TINH GỌN).
  Use for historical dates, years, centuries or era milestones (e.g. "Năm 1859", "Thế kỷ 19", "Năm 1954").
  Fields:
  * "nam": the clean short year/milestone text ONLY (e.g. "THẾ KỶ 19", "NĂM 1859", "NĂM 1990").
  * "moc": 2-6 words from the sentence.

- "khoanh_vung": SATELLITE MAP or AI MAP (BẢN ĐỒ KHOANH VÙNG ĐỊA DANH).
  Use when the narrator mentions or focuses on a real geographic place (country, island, province, river, lake). It will appear early so viewers have time to locate it!
  Fields: "dia_danh" (English name with country, e.g. "Victoria, Australia"), "ten_vi" (short Vietnamese name, e.g. "Bang Victoria, Úc").

- "duong_di": MAP ROUTE / MOVEMENT (BẢN ĐỒ ĐƯỜNG ĐI A -> B).
  Movement or spread between two distant locations. Fields: "tu", "den", "tu_vi", "den_vi", "phuong_tien".

Rules:
- High priority to "tai_hien" for any narrative, descriptive or action scenes to keep the video visually rich!
- For data, flexibly choose between "song", "con_so", and "cot" to prevent monotony.
- Every layer MUST have "moc": 2-8 words copied EXACTLY from the sentence where it starts.
- Return ONLY JSON array: [{{"cau": <sentence index>, "kieu": "<kind>", "moc": "...", ...fields}}]

PASSAGE:
{ds}"""


def hoi(cau, out, co_the=True):
    """[{cau(int), kieu, moc, ...}] — mỗi câu tối đa một lớp; câu nằm trong den_cau của sơ đồ trước thì bỏ lớp khác."""
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    p_hoi = [_P.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot))
             for lot in lots]
    khoa = [hashlib.md5(p.encode("utf-8")).hexdigest()[:16] for p in p_hoi]
    p_luu = os.path.join(out, "dieu_phoi_hoi.json")
    da = doc_json(p_luu, {}) or {}
    can = [k for k, kk in enumerate(khoa) if rut_json(da.get(kk) or "") is None]
    log(f"[ĐP] điều phối lớp minh hoạ: hỏi ChatGPT {len(can)}/{len(lots)} đoạn (còn lại dùng câu trả lời đã lưu)…")
    if can:
        for k, r in zip(can, hoi_nhieu([p_hoi[k] for k in can], timeout=300)):
            if rut_json(r or "") is not None:
                da[khoa[k]] = r
        ghi_json(p_luu, da)
    co = {c["i"] for c in cau}
    ra, phu = [], set()
    for kk in khoa:
        for x in (rut_json(da.get(kk) or "") or []):
            if not isinstance(x, dict) or x.get("kieu") not in KIEU:
                continue
            try:
                i = int(x.get("cau"))
                den = int(x.get("den_cau") or i)
            except (TypeError, ValueError):
                continue
            if i not in co or i in phu:
                continue
            x = dict(x, cau=i, den_cau=max(i, min(den, i + 2)) if x["kieu"] in ("dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong") else i)
            phu.update(range(i, x["den_cau"] + 1))
            ra.append(x)

    # Lọc chất lượng cao & tăng tối đa mật độ AI Storytelling theo yêu cầu người dùng
    KIEU_BO = {"mo_phong", "cau_tao", "vong_doi"}
    ra_loc = []
    cuoi_bando, dem_bando = -999, 0
    cuoi_taihien, dem_taihien = -999, 0
    cuoi_callout = -999

    for x in sorted(ra, key=lambda z: z["cau"]):
        k = x["kieu"]
        if k in KIEU_BO:
            continue
        # Khống chế bản đồ: tối đa 3 lần/video, cách nhau tối thiểu 20 câu
        if k in ("khoanh_vung", "duong_di", "lan_rong", "ban_do_ve"):
            if dem_bando >= 3 or (x["cau"] - cuoi_bando < 15):
                continue
            dem_bando += 1
            cuoi_bando = x["den_cau"]
            ra_loc.append(x)
        # Tái hiện tư liệu AI: Nâng tối đa mật độ (tối đa 80 lần/video), không ép khoảng cách
        elif k in ("tai_hien", "dien_canh"):
            if dem_taihien >= 80 or (x["cau"] <= cuoi_taihien):
                continue
            dem_taihien += 1
            cuoi_taihien = x["den_cau"]
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

    _bu_tieu_de(ra, out)
    dem = {}
    for x in ra:
        dem[x["kieu"]] = dem.get(x["kieu"], 0) + 1
    log("    " + ", ".join(f"{k} {v}" for k, v in sorted(dem.items())))
    return ra


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
