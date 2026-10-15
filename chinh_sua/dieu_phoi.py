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
KIEU = {"the", "ban_do_ve", "khoanh_vung", "duong_di", "lan_rong", "dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong"}
PHUONG_TIEN = {"may_bay", "tau_thuy", "tau_hoa", "xe", "di_bo", "tu_lan", "khac"}
HANH_DONG = {"bay_toi", "tan_cong", "bao_vay", "lan_ra", "sinh_soi", "bo_chay", "an", "mang_di"}
DONG_THE = """- "the": a HIGHLIGHT CARD (real photo + short caption) for an IMPORTANT idea: key number, turning point, striking comparison, first mention of a key species/person/object/place. About 1 card every 3-5 sentences, never two cards about the same fact. Fields: "anh" (English Google Images query, 2-6 words, real photograph, no text in it), "chu" (Vietnamese caption 2-7 words, punchy, numbers as digits).
"""
_P = """You are the editor of a Vietnamese documentary video. B-roll footage plays full screen while the narrator reads. For the sentences of the PASSAGE below (sentence index. text) you may add visual layers — AT MOST ONE layer per sentence. Layer kinds:
{dong_the}- "khoanh_vung": a SATELLITE map zooming down from space and outlining a real REGION / COUNTRY / ISLAND / CITY — use it ONLY when the narration LINGERS on that place (at least a full sentence about it, its geography matters). Fields: "dia_danh" (English name with country, e.g. "Kyoto, Japan", "Patagonia, Argentina"), "ten_vi" (short Vietnamese name as in the narration).
- "ban_do_ve": an AI-DRAWN ILLUSTRATED MAP for a place that is only MENTIONED QUICKLY (read fast, a few words) — fresher than the satellite zoom. Fields: "dia_danh" (English name with country), "ten_vi", "ve" (English: what the map shows — the place at the centre plus its surroundings, coastline, mountains, rivers or neighbouring land that make it recognisable). (It is drawn as a hyper-realistic satellite photograph.)
- "duong_di": MOVEMENT / TRAVEL / SHIPPING / SPREAD from one named real place to another named real place far apart (neither inside the other). Fields: "tu", "den" (English names with country), "tu_vi", "den_vi", "phuong_tien": one of may_bay (airplane), tau_thuy (ship/boat), tau_hoa (train), xe (truck/car/road), di_bo (on foot), tu_lan (animal/insect/disease spreading by itself), khac.
- "lan_rong": SPREAD from one origin to SEVERAL named real places. Fields: "goc" (English origin with country), "goc_vi", "noi": [{{"en": "...", "vi": "..."}}] (2-6 places), "phuong_tien" (as above).
- "dien_canh": ONE still illustration (AI-drawn, realistic, background removed) shown over the footage for a WHOLE idea: it appears ONCE when the idea starts and stays until the idea has been read — no animation, no step-by-step build-up, nothing moves. Use it ONLY where a picture really helps understanding (emphasis, explanation, mechanism, a chain of events). Pick "khuon":
  * "tong_quat" (default) — ONE picture that sums up the WHOLE idea at once. An action or scene -> one realistic picture with the action ALREADY HAPPENING (a black rat squeezing through a crack in a wall; a brown rat digging a burrow through packed soil). A chain, cycle, process or cause -> effect -> ONE diagram made of realistic pictures connected by bold arrows (a cycle drawn in a circle). Something hidden underground or inside -> a 3D cut-away cross-section block showing it. Fields: "ve" (English, detailed description of that ONE picture), "tieu_de" (Vietnamese caption 3-8 words summing up the idea, numbers as digits).
  * "liet_ke" — the narration LISTS 2-5 separate things: each is its own picture, all shown together side by side at once. Fields: "vai": [{{"ten": "<Vietnamese 1-4 words>", "ve": "<English: that ONE thing, already in the state the narration says, e.g. a road caving in, an underground cable chewed with sparks>"}}]. ONE item = ONE thing: never two things in one item, never the same thing twice. Show the things AFFECTED or named — not the doer again when the doer is the obvious subject of the video.
  * "con_so" — a striking NUMBER: ONE picture plus the number. Fields: "ve" (English), "so" (the number written with DIGITS exactly as it should appear, short, keeping a qualifier word that is said: "Gần 90%", "3 triệu con", "12.000 lán" — NEVER spell numbers out in words), "moc_so" (exact words where the number is said).
  Fields (all): "y_tuong" (REQUIRED, write it FIRST: Vietnamese 1-2 sentences — what the one picture shows), "khuon".
  Examples (other topics — adapt the IDEA, never copy): "floods, fires and strikes hit the town" -> liet_ke: a river bursting its banks; a house on fire; factory workers holding picket signs. "Pesticide washes into rivers, fish absorb it, herons eat the fish and lay eggs with thin shells" -> tong_quat: a cycle diagram with arrows: a field being sprayed -> a river with fish -> a heron eating a fish -> cracked thin eggs in a nest; tieu_de "Thuốc trừ sâu đi vào chuỗi thức ăn". "Nearly 4 million bees vanished" -> con_so: a swarm of honeybees, so "Gần 4 triệu con". "The virus enters the cell and copies itself" -> tong_quat: a 3D cut-away of a cell with viruses entering and many copies inside.
Rules:
- Do NOT illustrate: negations ("it is not X"), opinions, morals, transitions, greetings, calls to subscribe, or ideas with no concrete picture. Leave those on the real footage. There is NO coverage target — fewer, clearer scenes are better.
- Keep at least ~2 sentences of plain footage between two "dien_canh" when possible.
- One "dien_canh" = one idea. Give "den_cau" (last sentence index) when the idea continues over the NEXT sentence(s); it must never spill into an unrelated sentence.
- Every layer has "moc": 2-8 words COPIED EXACTLY from the sentence where it starts (same spelling, numbers as written).
- Never ask for text, letters, numbers or labels INSIDE a picture ("ve") — captions are added separately.
- Every "ve" describes a REAL PHOTOGRAPH (ultra-photorealistic, as if shot with a camera) — never call it an illustration, drawing, painting or cartoon.
- Maps ONLY for real named geographic places.
Return ONLY a JSON array: [{{"cau": <sentence index>, "kieu": "<kind>", "moc": "...", ...fields}}]

PASSAGE:
{ds}"""


def hoi(cau, out, co_the=True):
    """[{cau(int), kieu, moc, ...}] — mỗi câu tối đa một lớp; câu nằm trong den_cau của sơ đồ trước thì bỏ lớp khác."""
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    # 13/10 user: tắt thẻ highlight -> bỏ hẳn loại "the" khỏi câu lệnh (câu đó dành cho diễn cảnh / bản đồ)
    p_hoi = [_P.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot), dong_the=DONG_THE if co_the else "")
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
