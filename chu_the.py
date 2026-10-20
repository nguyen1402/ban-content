# -*- coding: utf-8 -*-
"""CHỦ THỂ của cả video (19/10 user: "chỉ tìm những từ khoá quan trọng… hỏi AI từng đoạn một rất dễ đi lầm đường").

MỘT lần hỏi AI cho cả kịch bản -> danh sách chủ thể nhìn thấy được (con vật, người, phương tiện, nơi chốn, vật quan trọng),
mỗi chủ thể có: tên, các TÊN GỌI trong lời (để dò cục bộ), mô tả hình tiếng Anh, 6-10 từ khoá tìm YouTube.
Người dùng sửa danh sách trên giao diện (👥 Chủ thể). Sau đó KHÔNG hỏi AI nữa:
  - cảnh nhắc tên gọi của chủ thể nào -> cảnh đó thuộc chủ thể ấy (nhắc nhiều nhất; hoà thì chủ thể quan trọng hơn);
    cảnh không nhắc ai -> theo cảnh trước;
  - các cảnh liền nhau cùng chủ thể = một đoạn; đoạn ĐẦU TIÊN của mỗi chủ thể là đoạn tìm nguồn, các đoạn sau của cùng
    chủ thể dùng chung kho của nó (ghi như đoạn "binh_luan" có kho_cd -> máy tìm / tải / ghép hiện có dùng lại nguyên);
  - vế (giữa hai chỗ nghỉ giọng) nhắc tên chủ thể KHÁC chủ thể của cảnh -> vế đó chiếu chủ thể kia (ve_rieng).
Ghi ra/<dự án>/chu_the.json (chủ thể) và chu_de.json (đoạn, "nguon": "chu_the")."""
import hashlib
import os
import re
import unicodedata

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

TOI_DA = 10

_P = """Read this documentary narration (Vietnamese). List the KEY VISIBLE SUBJECTS the video must show as footage:
animals, people or groups, vehicles, places / landscapes, key physical objects. At most {n}, the most important first.
Skip abstract things (ideas, money, laws, statistics, news, opinions).
For each subject give:
  - "ten": short Vietnamese name;
  - "loai": "song" (animal, person, group), "vat" (vehicle, object) or "noi" (place, landscape);
  - "goi": EVERY word or phrase the narration uses to refer to it, copied exactly as written (common noun, species,
    proper names / nicknames of individuals, place names) — used to find which sentences talk about it;
  - "mo_ta_en": one short English description of how it looks on screen (max 15 words);
  - "tu_khoa": 6-10 English YouTube search phrases (2-6 words) for real footage of it: what it DOES in this story and how
    it is usually filmed ("<subject> hunting", "<subject> running", "<subject> close up", "aerial <subject>" …).
    No channel names, no "4k", no "cinematic".
Only JSON: {{"chu_the": [{{"ten": "...", "loai": "song", "goi": ["..."], "mo_ta_en": "...", "tu_khoa": ["..."]}}]}}

NARRATION:
{kb}"""


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "chu_the.json")


def _canh(du_an):
    return doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []


def _hash(canh):
    return hashlib.md5(("ct1|" + "|".join(str(c.get("text") or "") for c in canh)).encode("utf-8")).hexdigest()[:16]


def _chuan(s):
    return unicodedata.normalize("NFC", str(s or "")).lower()


def _sach(ds):
    ra = []
    for x in ds or []:
        if not isinstance(x, dict) or not str(x.get("ten") or "").strip():
            continue
        goi = [str(g).strip() for g in (x.get("goi") or []) if str(g).strip()]
        ten = str(x["ten"]).strip()
        loai = str(x.get("loai") or "").strip().lower()
        ra.append({"ten": ten, "loai": loai if loai in ("song", "vat", "noi") else "song", "goi": list(dict.fromkeys([ten] + goi)),
                   "mo_ta_en": str(x.get("mo_ta_en") or "").strip(),
                   "tu_khoa": [str(t).strip() for t in (x.get("tu_khoa") or []) if str(t).strip()][:10]})
    return ra[:TOI_DA]


def doc_goc(du_an):
    """Danh sách chủ thể (AI lập / người dùng sửa), CHƯA gồm từ khoá tìm thêm."""
    return (doc_json(_p(du_an), {}) or {}).get("chu_the") or []


def tu_khoa_them(du_an):
    """19/10 user: "từ khoá tìm thêm" — mỗi từ khoá là một chủ thể ĐỘC LẬP (tìm đúng y nguyên, chỉ gán tay cho câu)."""
    return [str(t).strip() for t in (doc_json(_p(du_an), {}) or {}).get("tu_khoa_them") or [] if str(t).strip()]


def tk_cau(du_an):
    """20/10 user: TỪ KHOÁ RIÊNG của từng câu {id cảnh: [{vi, en}]} — người dùng gõ (tiếng Việt / Anh), máy dịch sẵn."""
    return {int(k): [x for x in v if isinstance(x, dict) and x.get("en")]
            for k, v in ((doc_json(_p(du_an), {}) or {}).get("tk_cau") or {}).items() if str(k).isdigit() and v}


def doc(du_an):
    """Chủ thể dùng để chia đoạn / tìm / ghép = danh sách chủ thể + mỗi từ khoá tìm thêm / từ khoá riêng của câu thành một
    chủ thể (không tên gọi, nên không tự dò — chỉ gán cho câu)."""
    ds = doc_goc(du_an)
    ten = {x["ten"] for x in ds}
    tk = list(tu_khoa_them(du_an)) + [x["en"] for v in tk_cau(du_an).values() for x in v]
    them = [{"ten": t, "loai": "vat", "goi": [], "mo_ta_en": t, "tu_khoa": [t], "them": True}
            for t in dict.fromkeys(tk) if t not in ten]
    return ds + them


_P_DICH = """Translate each Vietnamese phrase below into a short natural ENGLISH YouTube search phrase (2-6 words) that finds
real footage of that thing / scene. Translate faithfully: keep proper names, do NOT add extra words such as "footage",
"video", "b-roll", "4k", "cinematic". Return ONLY JSON: {{"<phrase exactly as given>": "<english>"}}

{ds}"""


def _dich(cum, cu):
    """Dịch các cụm tiếng Việt sang cụm tìm tiếng Anh (một lần hỏi AI); cụm chỉ chữ Latin không dấu giữ nguyên."""
    from common import hoi_llm
    ra = {}
    can = []
    for c in dict.fromkeys(cum):
        if c in cu:
            ra[c] = cu[c]
        elif all(ord(ch) < 128 for ch in c):
            ra[c] = c
        else:
            can.append(c)
    if can:
        j = rut_json(hoi_llm(_P_DICH.format(ds="\n".join(f"- {c}" for c in can)), timeout=180) or "")
        for c in can:
            en = str((j or {}).get(c) or "").strip() if isinstance(j, dict) else ""
            if not en and isinstance(j, dict):                # AI đổi nhẹ khoá (thêm dấu chấm, gạch đầu dòng…)
                en = next((str(v).strip() for k, v in j.items() if str(k).strip(" -.").lower() == c.lower()), "")
            ra[c] = en or c
    return ra


def lap(du_an, hoi_lai=False):
    """Hỏi AI MỘT lần cho cả kịch bản (đã có và kịch bản không đổi -> dùng lại, trừ khi hoi_lai)."""
    canh = _canh(du_an)
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — chạy bước đọc giọng trước")
    h = _hash(canh)
    da = doc_json(_p(du_an), {}) or {}
    if not hoi_lai and da.get("_hash") == h and da.get("chu_the"):
        return da["chu_the"]
    kb = " ".join(str(c.get("text") or "") for c in canh)[:30000]
    log(f"[chủ thể] hỏi AI chủ thể chính + từ khoá cho cả kịch bản ({len(canh)} cảnh)…")
    ds = []
    for _ in range(3):
        j = rut_json(hoi_llm(_P.format(n=TOI_DA, kb=kb), timeout=300) or "")
        ds = _sach((j or {}).get("chu_the") if isinstance(j, dict) else j)
        if ds:
            break
    if not ds:
        raise ValueError("AI không trả danh sách chủ thể (thử lại)")
    ghi_json(_p(du_an), {"_hash": h, "chu_the": ds})
    log(f"[chủ thể] {len(ds)}: " + ", ".join(x["ten"] for x in ds))
    return ds


def luu(du_an, ds, gan_tay=None, them=None, tk=None):
    """Người dùng sửa danh sách trên giao diện. gan_tay: {id cảnh: [tên chủ thể, ...]} người dùng gán tay (thắng dò tên;
    một câu được nhiều chủ thể — 19/10 user)."""
    canh = _canh(du_an)
    cu = doc_json(_p(du_an), {}) or {}
    if gan_tay is None:
        gt = cu.get("gan_tay") or {}
    else:
        gt = {}
        for k, v in gan_tay.items():
            v = [str(x) for x in (v if isinstance(v, list) else [v]) if str(x or "").strip()]
            if v:
                gt[str(k)] = list(dict.fromkeys(v))
    tkt = cu.get("tu_khoa_them") or [] if them is None else [str(t).strip() for t in them if str(t).strip()]
    tkc = cu.get("tk_cau") or {}
    if tk is not None:                                       # {id: "cụm, cụm"} hoặc {id: [cụm]} — dịch cụm mới
        moi = {}
        for k, v in tk.items():
            v = v if isinstance(v, list) else str(v or "").split(",")
            v = [str(x).strip() for x in v if str(x).strip()]
            if v and str(k).isdigit():
                moi[str(k)] = v
        cu_dich = {x["vi"]: x["en"] for vv in tkc.values() for x in vv if isinstance(x, dict) and x.get("vi")}
        dich = _dich([c for v in moi.values() for c in v], cu_dich) if moi else {}
        tkc = {k: [{"vi": c, "en": dich.get(c, c)} for c in v] for k, v in moi.items()}
    ghi_json(_p(du_an), {"_hash": _hash(canh), "chu_the": _sach(ds), "sua_tay": True, "gan_tay": gt,
                         "tu_khoa_them": list(dict.fromkeys(tkt)), "tk_cau": tkc})


def gan_tay(du_an):
    """{id cảnh (int): [tên chủ thể, ...]} người dùng gán tay (bản cũ lưu một tên -> danh sách một phần tử). Câu có TỪ KHOÁ
    RIÊNG: chiếu đúng các từ khoá đó (thắng gán tay / dò tên)."""
    gt = {int(k): (v if isinstance(v, list) else [v])
          for k, v in ((doc_json(_p(du_an), {}) or {}).get("gan_tay") or {}).items() if str(k).isdigit() and v}
    for k, v in tk_cau(du_an).items():
        gt[k] = list(dict.fromkeys(x["en"] for x in v))
    return gt


def ds_canh(du_an):
    """19/10 user: MỌI câu (cảnh) kèm các chủ thể đang chiếu -> [{id, text, ds: [tên], tay, nhac}]. Tự dò: chủ thể chính
    + các chủ thể khác được nhắc rõ trong câu (theo thứ tự nhắc); gán tay: đúng danh sách người dùng chọn."""
    ds = doc(du_an)
    if not ds:
        return []
    canh = sorted(_canh(du_an), key=lambda c: c["id"])
    gt = gan_tay(du_an)
    tkc = tk_cau(du_an)
    gan = gan_canh(canh, ds, gt)
    mau = _mau(ds)
    ra = []
    for c in canh:
        ks = _ds_k(c, ds, gan, gt, mau)
        d = nhac(c.get("text"), mau)
        ra.append({"id": c["id"], "text": c.get("text") or "", "ds": [ds[k]["ten"] for k in ks], "tay": c["id"] in gt,
                   "nhac": bool(d) and max(d.values()) >= 1.0, "tk": tkc.get(c["id"]) or []})
    return ra


def _ds_k(c, ds, gan, gt, mau):
    """Chỉ số các chủ thể của một cảnh (phần tử đầu = chủ thể chính)."""
    ten_k = {x["ten"]: k for k, x in enumerate(ds)}
    if c["id"] in gt:
        ks = [ten_k[t] for t in gt[c["id"]] if t in ten_k]
        if ks:
            return list(dict.fromkeys(ks))
    ks = [gan[c["id"]]]
    t = _chuan(c.get("text"))
    vt = []
    for k, rx, yeu in mau:
        if not yeu and k not in ks:
            m = rx.search(t)
            if m:
                vt.append((m.start(), k))
    for _, k in sorted(vt):
        if k not in ks:
            ks.append(k)
    return ks


def khong_nhac(du_an):
    """19/10 user ("quét thiếu thì sao"): các cảnh KHÔNG nhắc tên gọi chủ thể nào (hoặc chỉ nhắc nơi chốn chung) / đã gán
    tay -> [{id, text, dang (chủ thể đang dùng), tay}] để người dùng thấy chỗ thiếu chủ thể và gán tay."""
    ds = doc(du_an)
    if not ds:
        return []
    canh = sorted(_canh(du_an), key=lambda c: c["id"])
    gt = gan_tay(du_an)
    gan = gan_canh(canh, ds, gt)
    mau = _mau(ds)
    ra = []
    for c in canh:
        d = nhac(c.get("text"), mau)
        if c["id"] in gt or not d or max(d.values()) < 1.0:
            ra.append({"id": c["id"], "text": c.get("text") or "", "dang": ds[gan[c["id"]]]["ten"], "tay": gt.get(c["id"], "")})
    return ra


def _mau(ds):
    """[(chỉ số chủ thể, regex, yếu)] — tên gọi dài trước để 'chó sói' không bị 'chó' ăn mất. YẾU = tên gọi MỘT chữ của
    chủ thể nơi chốn ('đảo', 'rừng'): chỉ nói nơi xảy ra, không đổi chủ thể của cảnh (đo cho_digo: 'đưa khỏi đảo')."""
    cap = sorted(((k, _chuan(g), ds[k].get("loai") == "noi" and len(_chuan(g).split()) == 1)
                  for k, x in enumerate(ds) for g in x["goi"] if len(_chuan(g)) >= 2), key=lambda z: -len(z[1]))
    return [(k, re.compile(r"(?<!\w)" + re.escape(g) + r"(?!\w)"), yeu) for k, g, yeu in cap]


def nhac(text, mau):
    """{chỉ số chủ thể: số lần nhắc} trong một câu / vế (mỗi chỗ chỉ tính cho tên gọi dài nhất khớp)."""
    t = _chuan(text)
    dem, che = {}, [False] * len(t)
    for k, rx, yeu in mau:
        for m in rx.finditer(t):
            if any(che[m.start():m.end()]):
                continue
            che[m.start():m.end()] = [True] * (m.end() - m.start())
            dem[k] = dem.get(k, 0) + (0.4 if yeu else 1.0)
    return dem


def _chon(d, truoc):
    """Chủ thể của một câu / vế: nhắc nhiều nhất (hoà: quan trọng hơn); chỉ có tín hiệu yếu -> giữ chủ thể trước."""
    if not d:
        return truoc
    k = min(d, key=lambda z: (-d[z], z))
    return truoc if d[k] < 1.0 and truoc is not None else k


def gan_canh(canh, ds, tay=None):
    """{id cảnh: chỉ số chủ thể} — gán tay thắng; nhắc nhiều nhất (hoà: chủ thể quan trọng hơn); không nhắc -> cảnh trước."""
    mau = _mau(ds)
    ten_k = {x["ten"]: k for k, x in enumerate(ds)}
    tay = tay or {}
    ra, truoc = {}, None
    cho = []
    for c in canh:
        k = next((ten_k[t] for t in (tay.get(c["id"]) or []) if t in ten_k), None)
        if k is None:
            k = _chon(nhac(c.get("text"), mau), truoc)
        if k is None:
            cho.append(c["id"])
            continue
        for i in cho:                                        # các cảnh đầu chưa nhắc ai -> chủ thể đầu tiên được nhắc
            ra[i] = k
        cho = []
        ra[c["id"]] = k
        truoc = k
    for i in cho:
        ra[i] = 0
    return ra


def chia_doan(du_an, hoi_lai=False):
    """Chủ thể -> các đoạn (ghi chu_de.json, cùng khuôn với chu_de.py để máy tìm / tải / ghép dùng lại)."""
    ds = doc(du_an) if not hoi_lai else []
    if not doc_goc(du_an) or hoi_lai or (doc_json(_p(du_an), {}) or {}).get("_hash") != _hash(_canh(du_an)):
        lap(du_an, hoi_lai=hoi_lai)
        ds = doc(du_an)
    canh = sorted(_canh(du_an), key=lambda c: c["id"])
    gan = gan_canh(canh, ds, gan_tay(du_an))
    doan = []
    for c in canh:
        k = gan[c["id"]]
        if doan and doan[-1]["_k"] == k:
            doan[-1]["canh_den"] = c["id"]
            doan[-1]["ket_thuc"] = round(float(c.get("bat_dau") or 0) + float(c.get("dai") or 0), 2)
        else:
            doan.append({"_k": k, "canh_tu": c["id"], "canh_den": c["id"], "bat_dau": round(float(c.get("bat_dau") or 0), 2),
                         "ket_thuc": round(float(c.get("bat_dau") or 0) + float(c.get("dai") or 0), 2)})
    dau = {}
    for n, d in enumerate(doan, 1):
        x = ds[d["_k"]]
        d.update(id=n, ten=x["ten"], doi_tuong=x["ten"], mo_ta_en=x["mo_ta_en"] or x["ten"], tu_khoa_en=list(x["tu_khoa"]),
                 chu_the=d["_k"], dai=round(d["ket_thuc"] - d["bat_dau"], 2), so_canh=d["canh_den"] - d["canh_tu"] + 1,
                 bang_chung="", tranh="")
        if d["_k"] in dau:                                   # chủ thể đã có đoạn trước: dùng chung kho của đoạn đó
            d.update(loai="binh_luan", kho_cd=dau[d["_k"]], kho_ds=[dau[d["_k"]]], thua_ke=dau[d["_k"]])
        else:
            dau[d["_k"]] = n
            d.update(loai="ke", kho_cd=n, kho_ds=[n])
        d.pop("_k")
    # 19/10 user: chủ thể / từ khoá tìm thêm chỉ được gán làm chủ thể PHỤ của câu (không chính ở cảnh nào) vẫn phải được
    # tìm + tải -> đoạn "chỉ tìm" (chi_tim): không chiếm cảnh nào khi ghép, số mảnh cần = số câu dùng nó
    gt = gan_tay(du_an)
    mau = _mau(ds)
    dung_phu = {}
    for c in canh:
        for k in _ds_k(c, ds, gan, gt, mau)[1:]:
            dung_phu[k] = dung_phu.get(k, 0) + 1
    for k, so in dung_phu.items():
        if k in dau:
            continue
        n = len(doan) + 1
        x = ds[k]
        doan.append({"id": n, "ten": x["ten"], "doi_tuong": x["ten"], "mo_ta_en": x["mo_ta_en"] or x["ten"],
                     "tu_khoa_en": list(x["tu_khoa"]), "chu_the": k, "loai": "ke", "kho_cd": n, "kho_ds": [n],
                     "chi_tim": True, "so_dung": so, "canh_tu": -1, "canh_den": -2, "so_canh": 0, "dai": 0.0,
                     "bat_dau": 0.0, "ket_thuc": 0.0, "bang_chung": "", "tranh": ""})
        dau[k] = n
    ghi_json(os.path.join(thu_muc_du_an(du_an)[1], "chu_de.json"),
             {"_hash": _hash(canh), "nguon": "chu_the", "so_chu_de": len(doan), "chu_de": doan})
    log(f"[chủ thể] {len(canh)} cảnh -> {len(doan)} đoạn, {len(dau)} chủ thể có cảnh: "
        + ", ".join(f"{ds[k]['ten']} ({sum(1 for v in gan.values() if v == k)} cảnh)" for k in dau))
    return doan


def ve_rieng(du_an, lang=None):
    """{id cảnh: [{bd, kt, mo_ta_en, rieng: True}]} — vế nhắc tên một chủ thể KHÁC chủ thể của cảnh (khuôn mo_ta_ve)."""
    import mo_ta_ve
    ds = doc(du_an)
    if not ds:
        return {}
    canh = _canh(du_an)
    gt = gan_tay(du_an)
    gan = gan_canh(sorted(canh, key=lambda c: c["id"]), ds, gt)
    mau = _mau(ds)
    ra = {}
    for c in canh:
        ks = _ds_k(c, ds, gan, gt, mau)
        ves = mo_ta_ve.ve_canh(du_an, c, lang)
        for p, (bd, kt, s) in enumerate(ves):
            d = nhac(s, mau)
            k = _chon(d, None) if d and max(d.values()) >= 1.0 else None
            if c["id"] in gt:                                # gán tay nhiều chủ thể: vế nhắc tên chủ thể nào trong danh sách
                if k not in ks:                              # thì chiếu nó, không nhắc thì chia đều các vế theo thứ tự
                    k = ks[min(len(ks) - 1, p * len(ks) // max(1, len(ves)))]
            if k is not None and k != ks[0]:
                ra.setdefault(str(c["id"]), []).append({"bd": bd, "kt": kt, "mo_ta_en": ds[k]["mo_ta_en"] or ds[k]["ten"],
                                                        "rieng": True, "nhac_lai": False, "chu_the": k})
    return ra
