# -*- coding: utf-8 -*-
"""Bước 1 — kịch bản -> các CẢNH (mỗi cảnh ~5-9 giây lời) + truy vấn tìm hình bằng tiếng Anh.

Cắt cảnh làm bằng luật (chắc, lặp lại được); ChatGPT chỉ lo phần "hiểu": sửa tên riêng bị
nghe nhầm (Middle Iceland -> Middle Island ...) và đặt từ khóa tìm hình theo thang
cụ thể -> chung.
"""
import re

from common import duong_cache, doc_json, ghi_json, hoi_llm, hoi_nhieu, log, rut_json

#: tốc độ đọc ước lượng (ký tự/giây) khi chưa có giọng đọc thật.
KY_TU_MOI_GIAY = 15.0
CANH_MIN, CANH_MAX = 90, 190          # ký tự mỗi cảnh


def doc_kich_ban(path):
    with open(path, encoding="utf-8-sig") as f:
        t = f.read()
    return re.sub(r"[ \t]+", " ", t.replace("\r", "")).strip()


def tach_cau(text):
    cau = re.split(r"(?<=[.!?…])\s+|\n+", text)
    return [c.strip() for c in cau if c and c.strip()]


def tach_canh(text, cps=KY_TU_MOI_GIAY):
    """Gộp câu liền nhau tới khi đủ ~CANH_MIN ký tự; câu quá dài thì cắt ở dấu phẩy."""
    cau = []
    for c in tach_cau(text):
        while len(c) > CANH_MAX * 1.4:
            cut = c.rfind(",", 0, CANH_MAX + 40)
            if cut < CANH_MIN // 2:
                cut = c.rfind(" ", 0, CANH_MAX)
            if cut <= 0:
                break
            cau.append(c[:cut + 1].strip())
            c = c[cut + 1:].strip()
        if c:
            cau.append(c)
    canh, cur = [], ""
    for c in cau:
        if cur and len(cur) + 1 + len(c) > CANH_MAX:
            canh.append(cur)
            cur = c
        else:
            cur = (cur + " " + c).strip()
        if len(cur) >= CANH_MIN:
            canh.append(cur)
            cur = ""
    if cur:
        if canh and len(cur) < CANH_MIN // 2:
            canh[-1] += " " + cur
        else:
            canh.append(cur)
    ra, t = [], 0.0
    for i, s in enumerate(canh, 1):
        d = max(2.5, len(s) / cps)
        ra.append({"id": i, "text": s, "bat_dau": round(t, 2), "dai": round(d, 2)})
        t += d
    return ra


_P_TEN = """Below is a Vietnamese video narration about a wildlife / conservation story. It was produced by speech recognition, so many proper names are misspelled or mistranscribed (e.g. places, animals, people, film titles).

Return ONLY JSON: {{"tom_tat": "<3-sentence English summary of the story>", "ten": {{"<wrong spelling as it appears>": "<correct English name to use when searching for footage>"}}}}
Include every mistranscribed or Vietnamized proper name you can identify. Leave out names that are already correct.

NARRATION:
{van_ban}"""

_P_CANH = """You are a documentary video editor choosing STOCK / ARCHIVE FOOTAGE to illustrate a narration. Story summary: {tom_tat}
Correct names: {ten}

For each numbered narration scene below, decide what a viewer should SEE while it is spoken, using real filmable footage or photos that exist on YouTube/stock sites (animals, landscapes, places, people at work, archive scenes, maps). The match only has to be illustrative, not exact. Avoid anything that needs on-screen text.

Return ONLY a JSON array, one object per scene:
{{"id": <scene id>, "loai": "video" | "anh" | "do_hoa", "mo_ta": "<one concrete English sentence describing the shot, as it would be captioned>", "q": ["<specific YouTube search>", "<more general search>", "<generic mood / category search>"]}}
- q items are 2-6 English words, no quotes, most specific first, last one very generic (e.g. "sea fog coast", "fox hunting night").
- loai "do_hoa" only for maps, charts, timelines, "subscribe" calls to action, or abstract reflective lines with nothing filmable.

SCENES:
{canh}"""


_P_ANH = """For each documentary scene below, give 2-3 SHORT search terms (1-3 words each) for finding a STILL PHOTO on Wikipedia / Wikimedia Commons / iNaturalist: prefer the exact species name (common or scientific, e.g. "Eudyptula minor", "Maremma sheepdog", "red fox"), a place name ("Warrnambool"), an object or event ("breakwater", "sand bar"). Do not use full sentences or adjectives. Use the correct names given.
Correct names: {ten}
Return ONLY a JSON array: [{{"id": <scene id>, "anh_q": ["term1", "term2"]}}]

SCENES (id. English description):
{canh}"""


def lam_tu_khoa_anh(canh, ctx, cache, lo=12):
    """Điền c['anh_q'] — từ khóa NGẮN cho kho ảnh (khác c['q'] là cụm dài để tìm video)."""
    da = {int(k): v for k, v in (doc_json(cache, {}) or {}).items()}
    for c in canh:
        if c["id"] in da:
            c["anh_q"] = da[c["id"]]
    can = [c for c in canh if not c.get("anh_q")]
    lots = [can[i:i + lo] for i in range(0, len(can), lo)]
    ps = [_P_ANH.format(ten=ctx["ten"], canh=chr(10).join(f"{c['id']}. {c.get('mo_ta') or c['q'][0]}" for c in lot))
          for lot in lots]
    log(f"  từ khóa ảnh: {len(lots)} lô, mỗi cookie một luồng…")

    def xu_ly(i, tra):
        mp = {int(x.get("id", -1)): x for x in (rut_json(tra) or []) if isinstance(x, dict)}
        for c in lots[i]:
            ds = [str(s).strip() for s in (mp.get(c["id"]) or {}).get("anh_q", []) if str(s).strip()]
            c["anh_q"] = ds[:3] or [c["q"][-1]]
            da[c["id"]] = c["anh_q"]
        ghi_json(cache, {str(k): v for k, v in da.items()})
    hoi_nhieu(ps, timeout=200, on_xong=xu_ly)
    return canh


_P_NHIP = """You are a documentary video editor. Each numbered SCENE below is Vietnamese narration. Split every scene into consecutive BEATS (phrases): start a new beat whenever the narration moves to a new thing that should be SHOWN on screen — in particular whenever a NEW concrete named thing (place, organization, person, species, substance, object) is mentioned. Rules:
- 1 to 8 beats per scene. A beat must last at least ~1.6 seconds of speech (about 24+ characters); never split a short scene. When the narration only describes things in general, keep ONE longer beat instead of many short ones.
- The "text" of the beats of one scene, joined with single spaces, must equal the scene text EXACTLY (do not change, drop, add or reorder a word).
- Show ONLY what the narration says at that very phrase. NEVER show a subject before the narration has mentioned it. Subjects NOT yet mentioned at these scenes (do not depict them at all): {chua}.
- If the phrase is abstract (change, disaster, loss, hope, lesson, a rhetorical question), show an atmospheric ENVIRONMENT shot (empty shoreline, waves, dusk sky, sand, burrows, fog) — never invent a specific animal or person that the phrase does not name.
- If the phrase describes movement, use a motion verb (walks, runs, swims, prowls, waddles) so that moving footage is searched.
- For each beat give:
  "mo_ta" = one concrete English sentence describing what to show for THAT phrase;
  "ents" = the CONCRETE named things this phrase mentions, each {{"vi": the words as written in the narration, "name": the thing's proper English/Latin name only (no extra words like logo/map/video), "kind": one of "footage" | "photo" | "map" | "logo" | "document"}}. Use kind "map" for a place the viewer should be located, "logo" for an organization, "document" for a sign/report/paper/label, "photo" for a specific person/species/object, "footage" otherwise. Leave "ents" empty [] if the phrase names nothing concrete;
  "q" = 3 English YouTube search phrases: FIRST one built around the main entity name (for example "RSPCA Queensland logo", "Palm Island aerial drone", "1080 poison warning sign"), then a more general one, then a generic one (2-6 words each);
  "anh_q" = 1-3 SHORT terms (entity / species / place / object name) to find a still photo, entity names first.
Story summary: {tom_tat}
Correct names: {ten}

Return ONLY JSON: [{{"id": <scene id>, "nhip": [{{"text": "...", "mo_ta": "...", "ents": [{{"vi": "...", "name": "...", "kind": "footage"}}], "q": ["..."], "anh_q": ["..."]}}]}}]

SCENES (id [seconds]. text):
{canh}"""


def _lam_sach_ents(x):
    """Danh sách thực thể hợp lệ [{vi, name, kind}] (tối đa 4) từ trả lời của model."""
    ra = []
    for e in (x if isinstance(x, list) else []):
        if isinstance(e, dict) and str(e.get("name", "")).strip():
            k = str(e.get("kind", "footage")).lower()
            ra.append({"vi": str(e.get("vi", "")).strip(), "name": str(e["name"]).strip(),
                       "kind": k if k in ("footage", "photo", "map", "logo", "document") else "footage"})
    return ra[:4]


def _chuan_chu(s):
    return "".join(s.split())


_P_CHU_THE = """Below is a Vietnamese narration (speech-recognition output, so names may be misspelled) and a summary. List the MAIN recurring SUBJECTS that could be shown on screen: animals, people, notable objects (max 8). For each give every spelling/word variant the narration uses (Vietnamese, lowercase) and a short English phrase describing how it looks on camera.
Return ONLY JSON: [{{"vi": ["cáo", "cáo đỏ"], "en": "a red fox"}}]
SUMMARY: {tom_tat}
NARRATION:
{van_ban}"""


def lam_chu_the(canh, ctx, cache):
    """Các chủ thể chính + CẢNH ĐẦU TIÊN lời kể nhắc tới (để không minh họa chúng trước khi được nhắc)."""
    ds = doc_json(cache)
    if not ds:
        van = chr(10).join(f"{c['id']}. {c['text']}" for c in canh)
        kq = rut_json(hoi_llm(_P_CHU_THE.format(tom_tat=ctx["tom_tat"], van_ban=van[:30000]), timeout=300)) or []
        ds = [x for x in kq if isinstance(x, dict) and x.get("vi") and x.get("en")]
        ghi_json(cache, ds)
    for s in ds:
        mau = [re.escape(w.lower()) for w in s["vi"] if w.strip()]
        rx = re.compile(r"(?<!\w)(" + "|".join(mau) + r")(?!\w)") if mau else None
        s["dau"] = next((c["id"] for c in canh if rx and rx.search(c["text"].lower())), None)
    log("    chủ thể: " + "; ".join(f"{s['en']}→cảnh {s['dau']}" for s in ds))
    return ds


def gan_chu_the(canh, chu_the):
    """c['cam_them'] = mô tả (EN) các chủ thể CHƯA được nhắc tới ở cảnh này — dùng làm khái niệm cấm cho CLIP."""
    for c in canh:
        c["cam_them"] = [s["en"] for s in chu_the if s.get("dau") and s["dau"] > c["id"]]
    return canh


def lam_nhip(canh, ctx, cache, lo=6):
    """Điền c['nhip_tho'] = các cụm lời + mô tả hình RIÊNG cho từng cụm (cache theo id cảnh)."""
    da = {int(k): v for k, v in (doc_json(cache, {}) or {}).items()}
    # bản nhịp cũ (chưa có "ents" — thực thể cụ thể của từng cụm) coi như chưa có, để hỏi lại
    can = [c for c in canh if not c.get("do_hoa") and (c["id"] not in da or not all("ents" in n for n in da[c["id"]]))]
    lots = [can[i:i + lo] for i in range(0, len(can), lo)]
    ps = []
    for lot in lots:
        txt = chr(10).join(f"{c['id']} [{c['dai']:.1f}s]. {c['text']}" for c in lot)
        chua = "; ".join(f"{s['en']} (first mentioned in scene {s['dau']})" for s in ctx.get("chu_the", [])
                         if s.get("dau") and s["dau"] > lot[0]["id"]) or "none"
        ps.append(_P_NHIP.format(tom_tat=ctx["tom_tat"], ten=ctx["ten"], canh=txt, chua=chua))
    log(f"  tách nhịp: {len(lots)} lô, mỗi cookie một luồng…")

    def xu_ly(i, tra):
        mp = {int(x.get("id", -1)): x for x in (rut_json(tra) or []) if isinstance(x, dict)}
        for c in lots[i]:
            ns = (mp.get(c["id"]) or {}).get("nhip") or []
            ok = ns and all(isinstance(n, dict) and n.get("text") for n in ns) and                 _chuan_chu("".join(n["text"] for n in ns)) == _chuan_chu(c["text"])
            if not ok:
                log(f"    ! cảnh {c['id']}: nhịp không khớp lời gốc — giữ một nhịp")
                ns = [{"text": c["text"], "mo_ta": c.get("mo_ta", ""), "q": c.get("q", []),
                       "anh_q": c.get("anh_q", [])}]
            da[c["id"]] = [{"text": n["text"].strip(), "mo_ta": str(n.get("mo_ta", "")),
                            "ents": _lam_sach_ents(n.get("ents")),
                            "q": [str(q) for q in (n.get("q") or [])][:3] or c.get("q", []),
                            "anh_q": [str(q) for q in (n.get("anh_q") or [])][:3]} for n in ns]
        ghi_json(cache, {str(k): v for k, v in da.items()})
    hoi_nhieu(ps, timeout=240, on_xong=xu_ly)
    for c in canh:
        if c["id"] in da:
            c["nhip_tho"] = da[c["id"]]
    return canh


def _bd_theo_moc(c, ns):
    """Thời điểm bắt đầu (s, tính từ đầu cảnh) của từng nhịp theo MỐC TỪNG CHỮ THẬT của giọng đọc (c['moc_tu']);
    đổi hình sớm ~0,08s trước khi giọng bắt đầu cụm. None nếu thiếu mốc hoặc số chữ không khớp."""
    moc = c.get("moc_tu")
    n_tok = [len(n["text"].split()) for n in ns]
    if moc and sum(n_tok) != len(moc):
        # ChatGPT có thể đổi khoảng trắng/dấu câu làm lệch số "chữ": quy theo số ký tự KHÔNG-khoảng-trắng, rồi
        # đặt ranh giới nhịp vào đầu chữ gần nhất của lời gốc (đủ chính xác, thay vì rơi về ước lượng theo độ dài).
        toks = c["text"].split()
        if len(toks) == len(moc):
            cum, t_ = [], 0
            for tk in toks:
                cum.append(t_)                                     # vị trí ký tự (không tính khoảng trắng) đầu mỗi chữ
                t_ += len(tk)
            tong_ = max(t_, 1)
            n_tok, pos = [], 0
            goc = [len("".join(n["text"].split())) for n in ns]
            ranh = [0]
            for g in goc[:-1]:
                ranh.append(ranh[-1] + g)
            idx = [min(range(len(cum)), key=lambda i: abs(cum[i] - r)) for r in ranh]
            if idx == sorted(idx) and len(set(idx)) == len(idx):
                n_tok = [(idx[k + 1] if k + 1 < len(idx) else len(toks)) - idx[k] for k in range(len(idx))]
            else:
                return None
    if not moc or sum(n_tok) != len(moc):
        return None
    bd, i = [], 0
    for k, n in enumerate(n_tok):
        t = 0.0 if k == 0 else max(0.0, moc[i][0] - 0.08)
        bd.append(max(t, bd[-1] + 0.3) if bd else 0.0)               # luôn tăng dần
        i += n
    return bd


NHIP_MIN = 1.6       # giây — nhịp ngắn hơn mức này bị gộp vào nhịp bên cạnh


def tinh_gio_nhip(canh):
    """Thời điểm/độ dài từng nhịp theo vị trí chữ trong lời (chữ + khoảng nghỉ ở dấu câu), tổng = độ dài cảnh."""
    for c in canh:
        ns = c.get("nhip_tho")
        if not ns or c.get("do_hoa"):
            continue
        def trong(n):
            tx = n["text"]
            return (sum(ch.isalnum() for ch in tx) + 3 * sum(tx.count(x) for x in ",;:")
                    + 6 * sum(tx.count(x) for x in ".!?…"))
        ws = [max(trong(n), 1) for n in ns]
        tong = float(sum(ws))
        ds = [c["dai"] * w / tong for w in ws]
        bd_that = _bd_theo_moc(c, ns)
        if bd_that and bd_that[-1] < c["dai"] - 0.3:                  # có mốc thật: độ dài = khoảng cách giữa các mốc
            ds = [(bd_that[k + 1] if k + 1 < len(bd_that) else c["dai"]) - bd_that[k] for k in range(len(bd_that))]
            c["nhip_theo_moc"] = True
        nh = [dict(n, dai=d) for n, d in zip(ns, ds)]
        while len(nh) > 1 and min(x["dai"] for x in nh) < NHIP_MIN:
            i = min(range(len(nh)), key=lambda k: nh[k]["dai"])
            j = i - 1 if i > 0 and (i == len(nh) - 1 or nh[i - 1]["dai"] >= nh[i + 1]["dai"]) else i + 1
            a, b = (min(i, j), max(i, j))
            giu = nh[a] if nh[a]["dai"] >= nh[b]["dai"] else nh[b]    # giữ mô tả của nhịp dài hơn
            ents = list(nh[a].get("ents") or []) + [e for e in (nh[b].get("ents") or [])
                                                    if e not in (nh[a].get("ents") or [])]
            nh[a:b + 1] = [dict(giu, text=(nh[a]["text"] + " " + nh[b]["text"]).strip(),
                                dai=nh[a]["dai"] + nh[b]["dai"], ents=ents[:4])]
        bd = 0.0
        for x in nh:
            x["bd"] = round(bd, 2)
            x["dai"] = round(x["dai"], 2)
            bd += x["dai"]
        nh[-1]["dai"] = round(c["dai"] - nh[-1]["bd"], 2)
        c["nhip"] = nh
    return canh


def lam_ten_va_tom_tat(text, cache):
    d = doc_json(cache)
    if d:
        return d
    kq = rut_json(hoi_llm(_P_TEN.format(van_ban=text[:30000]), timeout=180)) or {}
    d = {"tom_tat": str(kq.get("tom_tat", "")), "ten": kq.get("ten") or {}}
    ghi_json(cache, d)
    return d


def _gop_cache(da, canh):
    """Danh sách để ghi cache truy vấn: các cảnh đang chạy + các cảnh đã có từ lần chạy KHÁC (vd chạy thử N cảnh đầu
    không được xoá cache của cả kịch bản)."""
    ids = {c["id"] for c in canh}
    return list(canh) + [v for k, v in da.items() if k not in ids]


def lam_truy_van(canh, ctx, cache, lo=8):
    """Điền mo_ta/q/loai cho từng cảnh, theo lô; cảnh nào đã có thì bỏ qua (chạy tiếp được)."""
    da = {c["id"]: c for c in (doc_json(cache) or [])}
    for c in canh:
        if c["id"] in da:
            c.update({k: da[c["id"]][k] for k in ("loai", "mo_ta", "q") if k in da[c["id"]]})
    can = [c for c in canh if not c.get("q")]
    lots = [can[i:i + lo] for i in range(0, len(can), lo)]
    ps = [_P_CANH.format(tom_tat=ctx["tom_tat"], ten=ctx["ten"],
                         canh=chr(10).join(f"{c['id']}. {c['text']}" for c in lot)) for lot in lots]
    log(f"  hỏi ChatGPT: {len(lots)} lô, mỗi cookie một luồng…")
    dem = [0]

    def xu_ly(i, tra):
        mp = {int(x.get("id", -1)): x for x in (rut_json(tra) or []) if isinstance(x, dict)}
        for c in lots[i]:
            x = mp.get(c["id"])
            if not x:
                log(f"  ! cảnh {c['id']}: ChatGPT không trả — để dự phòng chung")
                x = {"loai": "video", "mo_ta": "nature wildlife coast footage",
                     "q": ["wildlife nature footage"]}
            c["loai"] = x.get("loai", "video")
            c["mo_ta"] = str(x.get("mo_ta", ""))
            c["q"] = [str(q) for q in (x.get("q") or []) if str(q).strip()][:3]                 or ["wildlife nature footage"]
        dem[0] += len(lots[i])
        ghi_json(cache, _gop_cache(da, canh))
        log(f"  truy vấn: {dem[0]}/{len(can)} cảnh")
    hoi_nhieu(ps, timeout=200, on_xong=xu_ly)
    ghi_json(cache, _gop_cache(da, canh))
    return canh


def tach_don_gian(path, gioi_han=0, cps=KY_TU_MOI_GIAY):
    """Chỉ tách kịch bản thành cảnh (luật, không gọi ChatGPT) — để đọc giọng chạy NGAY, song song với phần còn lại."""
    text = doc_kich_ban(path)
    canh = tach_canh(text, cps)
    if gioi_han:
        canh = canh[:gioi_han]
    log(f"[1] {len(canh)} cảnh, ~{sum(c['dai'] for c in canh):.0f}s")
    return text, canh


def chay_buoc1(path, gioi_han=0, cps=KY_TU_MOI_GIAY):
    text = doc_kich_ban(path)
    canh = tach_canh(text, cps)
    if gioi_han:
        canh = canh[:gioi_han]
    log(f"[1] {len(canh)} cảnh, ~{sum(c['dai'] for c in canh):.0f}s")
    ctx = lam_ten_va_tom_tat(text, duong_cache("ten.json"))
    log(f"    tên chuẩn: {ctx['ten']}")
    return lam_truy_van(canh, ctx, duong_cache("canh.json"))
