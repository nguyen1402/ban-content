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
KIEU = {"the", "khoanh_vung", "duong_di", "lan_rong", "dien_canh", "cau_tao", "quy_trinh", "vong_doi", "mo_phong"}
PHUONG_TIEN = {"may_bay", "tau_thuy", "tau_hoa", "xe", "di_bo", "tu_lan", "khac"}
HANH_DONG = {"bay_toi", "tan_cong", "bao_vay", "lan_ra", "sinh_soi", "bo_chay", "an", "mang_di"}
DONG_THE = """- "the": a HIGHLIGHT CARD (real photo + short caption) for an IMPORTANT idea: key number, turning point, striking comparison, first mention of a key species/person/object/place. About 1 card every 3-5 sentences, never two cards about the same fact. Fields: "anh" (English Google Images query, 2-6 words, real photograph, no text in it), "chu" (Vietnamese caption 2-7 words, punchy, numbers as digits).
"""
_P = """You are the editor of a Vietnamese documentary video. B-roll footage plays full screen while the narrator reads. For the sentences of the PASSAGE below (sentence index. text) you may add visual layers — AT MOST ONE layer per sentence. Layer kinds:
{dong_the}- "khoanh_vung": the sentence names a real REGION / COUNTRY / ISLAND / CITY that matters to the story -> satellite map outlining it. Fields: "dia_danh" (English name with country, e.g. "Kyoto, Japan", "Patagonia, Argentina"), "ten_vi" (short Vietnamese name as in the narration).
- "duong_di": MOVEMENT / TRAVEL / SHIPPING / SPREAD from one named real place to another named real place far apart (neither inside the other). Fields: "tu", "den" (English names with country), "tu_vi", "den_vi", "phuong_tien": one of may_bay (airplane), tau_thuy (ship/boat), tau_hoa (train), xe (truck/car/road), di_bo (on foot), tu_lan (animal/insect/disease spreading by itself), khac.
- "lan_rong": SPREAD from one origin to SEVERAL named real places. Fields: "goc" (English origin with country), "goc_vi", "noi": [{{"en": "...", "vi": "..."}}] (2-6 places), "phuong_tien" (as above).
- "dien_canh": a short ANIMATED STORYBOARD that acts out the sentence(s) the way a good motion designer would, with cut-out pictures (AI-drawn, realistic) moving over the footage — for ANY topic (nature, science, history, technology, economy, society). THINK FIRST: what would make a viewer instantly SEE the meaning? Show cause -> effect and before -> after, and animate the CONCRETE DETAIL the narration mentions (something taken away and replaced, a bite / hole / tunnel / crack, getting fat or thin, filling up or emptying, breaking, joining, changing state). Fields:
  "y_tuong": "<Vietnamese, 1-2 sentences: the beats you will animate, in order>",
  "vai": [{{"ten": "<Vietnamese 1-3 words>", "anh": "<English Google Images query for a REAL PHOTO of that one thing (used as a reference picture) — specific species / life stage / object type / person role and era; empty if none>", "ve": "<English description for the AI to DRAW it — what it looks like, realistic>", "truu_tuong": <true if it cannot be photographed as one clear object (microscopic, molecular, conceptual)>, "vi_tri": "trai" | "giua" | "phai" (where it stands when the scene starts; omit for actors that only come in later)}}] — 1-4 actors. A STATE VARIANT of the same thing is its OWN actor (e.g. the same creature but plump and round / skinny and weak, the same object but full / empty / cracked / riddled with holes): write its "ve" as "SAME as actor <that actor's index, counted from 0 like in hanh_dong> but …" so it is drawn identical except that change, and switch to it with bien_thanh.
  "hanh_dong": 2-6 beats [{{"ai": <actor index from 0>, "lam": one of xuat_hien (appears), bien_thanh (actor "ai" turns into actor "toi" — stage / state change), bay_toi (moves to "toi"; if toi is null it moves across the frame), tan_cong (attacks / acts on), gam (nibbles / bites / works on "toi" repeatedly without destroying it), an (eats up / consumes "toi" completely), keo_di (actor "ai" is pulled / taken away out of the frame), thay_the (actor "ai" slides in and takes the place of "toi", which leaves), bao_vay (surrounds), lan_ra (spreads out in many copies), sinh_soi (multiplies into many), bo_chay (flees), mang_di (carries "toi" away), lon_len (grows bigger / fatter), thu_nho (shrinks / gets thinner / weaker), bien_mat (disappears / dies / is used up), tach_ra (breaks / is cut into small pieces), ket_hop (joins / merges with "toi"), "toi": <target actor index or null>, "nhan": "<optional Vietnamese label 1-4 words shown during this beat>", "moc": "<exact words>"}}].
  Examples of good thinking (other topics — adapt the IDEA, never copy): "they took the grain away and left only sand" -> a sack of grain beside a mouse; keo_di the grain; thay_the: a pile of sand slides into its place. "the snake swallowed the egg and its body bulged" -> snake gam the egg, an the egg, bien_thanh to "SAME snake but with a big bulge". "her savings grew until the jar overflowed" -> coins sinh_soi into the jar, bien_thanh to "SAME jar overflowing with coins". "the old bridge cracked under the tanks" -> tank bay_toi the bridge, tan_cong, bien_thanh to "SAME bridge with a deep crack". "group A ate, group B starved" -> two copies side by side: one lon_len (or bien_thanh to a plump variant), the other thu_nho (or bien_thanh to a skinny variant).
Rules:
- The goal is that a viewer UNDERSTANDS the story by watching: give a "dien_canh" to EVERY sentence (or run of 1-3 sentences) where something happens, changes, works, or acts, so that the scenes together cover about 60-70% of the narration — the remaining sentences (commentary, opinion, rhetorical questions, transitions) stay on the real footage so the viewer can breathe. The actors must be the things that DO or UNDERGO the action: when the sentence is about people observing / studying / discovering something, act out WHAT they found (the thing itself), not people looking. Use maps for places. Skip only pure opinion, morals, rhetorical questions and transitions. Maps ONLY for real named geographic places. Skip filler, transitions and pure emotion.
- A "dien_canh" may continue over the next 1-2 sentences when its actions are told there: give "den_cau" = last sentence index it covers (those sentences get no other layer); each action "moc" may come from any covered sentence.
- Every layer has "moc": 2-8 words COPIED EXACTLY from its sentence (same spelling, numbers as written) — the layer appears when the narrator says them.
- A "dien_canh" must carry the WHOLE idea of its sentence(s) through to the RESULT: the LAST beat shows the outcome / consequence that the sentence ends with (e.g. "…and by the end they had become visibly weaker" -> the last beat is thu_nho at those words). Give each beat its own "moc" at the words that describe THAT beat, in order, spread over the whole sentence. When the next sentence continues the same comparison / process / story (e.g. "the other group…", "then…", "as a result…"), cover it with "den_cau" in the SAME scene instead of starting a new one.
- Every "dien_canh" needs at least ONE real movement beat (anything except xuat_hien) whose "moc" is words actually said in the covered sentences — an actor only appearing is not a scene. Prefer 2-4 beats that tell a little story over one generic move.
- "anh" must be a query that returns a photo of THAT thing alone (no scenes, no diagrams). For things that cannot be photographed as ONE clear object (anything microscopic — bacteria, cells, enzymes, molecules, chemical chains — or data, abstract ideas made concrete) set "truu_tuong": true and describe them well in "ve".
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
