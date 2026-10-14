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
- "dien_canh": a short ANIMATED illustration with cut-out pictures (AI-drawn, realistic) over the footage. Use it ONLY where it really helps understanding: EMPHASIS (a striking number, a key question), EXPLANATION (a comparison, why something happens), MECHANISM (how something works inside), SIMULATION (an action or change the narration describes). Pick ONE template in "khuon":
  * "truoc_sau" — something CHANGES state (collapses, burns, empties, dies, grows fat…): each changing thing is shown in its BEFORE state and switches (bien_thanh) to its AFTER state at the words that say it. When the sentence lists several changing things, "bo_cuc": "liet_ke" and do them one after another. Show ONLY the things the sentence names — never add an actor the narration does not mention.
  * "con_so" — a striking NUMBER or a key QUESTION about an amount: ONE actor (a crowd with "dan": true when it is many) in the centre and a big counter. Extra fields: "so": the number text exactly as it should appear, short (e.g. "3 triệu con", "90%", "12.000 lán"), "moc_so": exact words where the number is said, "hoi": true when the sentence is a question (a "?" is shown right after the number).
  * "so_sanh" — TWO things or amounts compared: two actors side by side with bars proportional to their values. Extra fields: "gia_tri": [<number for actor 0>, <number for actor 1>], "nhan_gt": ["<short label with unit, e.g. 15 dB>", "<e.g. 70 dB>"].
  * "co_che" — what happens INSIDE something (in the body, in the gut, in a machine, under the ground): actor 0 is the outer thing shown whole; the other actors live inside a MAGNIFIER circle next to it and act there.
  * "hanh_dong" — an ACTION between actors (hunt, attack, nibble, carry, flee…): at most 3 actors.
  Fields (all templates):
  "y_tuong": "<REQUIRED, write it FIRST: Vietnamese, 1-3 sentences describing what will be seen, in order>",
  "khuon": "<one template name above>", "bo_cuc": "liet_ke" or "",
  "vai": [{{"ten": "<Vietnamese 1-3 words>", "anh": "<English Google Images query for a REAL PHOTO of that one thing (reference); empty if none>", "ve": "<English description for the AI to DRAW it — realistic; a STATE VARIANT is written \"SAME as actor <index from 0> but …\">", "truu_tuong": <true if it cannot be photographed as one clear object>, "vi_tri": "trai" | "giua" | "phai", "dan": <true when MANY of it act together>}}] (1-3 actors; a list in "liet_ke" may have up to 6 including their after-states),
  "hanh_dong": 1-5 beats (up to 8 in "liet_ke": one beat for each item and each change) [{{"ai": <actor index from 0>, "lam": one of xuat_hien, bien_thanh (SAME thing changes state into actor "toi"), bay_toi, tan_cong, gam, an, keo_di, thay_the, bao_vay, lan_ra, sinh_soi, bo_chay, mang_di, lon_len, thu_nho, bien_mat, tach_ra, ket_hop, "toi": <target index or null>, "moc": "<exact words>"}}].
  Examples (other topics — adapt the IDEA, never copy): "floods, fires and strikes hit the town" -> truoc_sau, liet_ke: a calm river -> SAME river flooding; a house -> SAME house on fire; a factory -> SAME factory with picket signs, each at its words. "Why did 4 million bees vanish?" -> con_so: a swarm of bees, so "4 triệu con", hoi true. "A cheetah runs 110 km/h, a horse 70" -> so_sanh with gia_tri [110, 70]. "the virus enters the cell and copies itself" -> co_che: a cell (outer), inside the magnifier the virus bay_toi the nucleus then sinh_soi. "the hawk dives and seizes the snake" -> hanh_dong.
Rules:
- Do NOT illustrate: negations ("it is not X"), opinions, morals, transitions, greetings, calls to subscribe, or ideas with no concrete picture. Leave those on the real footage. There is NO coverage target — fewer, clearer scenes are better.
- Keep at least ~2 sentences of plain footage between two "dien_canh" when possible.
- A scene stays inside its own sentence(s): give "den_cau" only when the NEXT sentence continues the SAME illustration; it must never spill into an unrelated sentence.
- Every layer has "moc": 2-8 words COPIED EXACTLY from its sentence (same spelling, numbers as written) — the layer appears when the narrator says them. Give each beat its own "moc" at the words that describe THAT beat, in order; beats need time between them (not two beats on the same few words).
- bien_thanh is ONLY for the SAME thing changing state; never turn one thing into a DIFFERENT thing. Actors appear in the ORDER the narration mentions them; an actor must not be on screen before its words are spoken.
- Use the SAME "ten" for the same creature / object every time it appears in different scenes (it is drawn once and reused).
- "anh" must return a photo of THAT thing alone. For things that cannot be photographed as ONE clear object (microscopic, molecular, abstract made concrete) set "truu_tuong": true and describe them well in "ve".
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
    dem = {}
    for x in ra:
        dem[x["kieu"]] = dem.get(x["kieu"], 0) + 1
    log("    " + ", ".join(f"{k} {v}" for k, v in sorted(dem.items())))
    return ra
