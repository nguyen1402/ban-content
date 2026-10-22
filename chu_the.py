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
TK_CHU_THE = 3             # 22/10 user: mỗi chủ thể chỉ 2-3 từ khoá (trước 6-10) — chủ thể KHÔNG có trạng thái
TT_TOI_DA = 5              # 22/10 user: từ khoá = TRẠNG THÁI của chủ thể trong truyện (đang bị làm sao / đang thế nào),
#                            mỗi trạng thái 1 từ khoá; chủ thể chính tối đa 5, chủ thể nhắc qua 1-2
GOI_Y_TU_KHOA_CAU = False  # 22/10 user: bỏ gợi ý từ khoá TỪNG CÂU ("quét nhiều quá mà vẫn không đủ video") -> tìm theo
#                            chủ thể; ô từ khoá riêng của câu vẫn dùng khi người dùng TỰ GÕ. Gợi ý AI cũ (goi_y) bỏ qua.

_P = """Read this documentary narration (Vietnamese). List the KEY VISIBLE SUBJECTS the video must show as footage:
animals, people or groups, vehicles, places / landscapes, key physical objects. At most {n}, the most important first.
Skip abstract things (ideas, money, laws, statistics, news, opinions).
For each subject give:
  - "ten": short Vietnamese name;
  - "loai": "song" (animal, person, group), "vat" (vehicle, object) or "noi" (place, landscape);
  - "goi": EVERY word or phrase the narration uses to refer to it, copied exactly as written (common noun, species,
    proper names / nicknames of individuals, place names) — used to find which sentences talk about it;
  - "mo_ta_en": one short English description of how it looks on screen (max 15 words);
  - "trang_thai": the different STATES / SITUATIONS the narration shows this subject in — what is happening to it or
    what it is doing (e.g. a subway car: running in New York -> stripped by workers -> lifted by a crane -> dropped into
    the sea -> lying on the seabed as a reef). In story order; at most {tt} for a subject the narration talks about a lot,
    only 1-2 for a subject mentioned briefly; merge near-identical states. Each state:
      "mo_ta": short Vietnamese description of the state;
      "en": how that state looks on screen, in English (max 15 words, the subject named);
      "tu_khoa": ONE English YouTube search phrase (2-6 words) for real footage of the subject in this state
        (no channel names, no "4k", no "cinematic", no "footage");
      "cau": the numbers of the sentences that show the subject in this state.
{them_cau}Only JSON: {{"chu_the": [{{"ten": "...", "loai": "song", "goi": ["..."], "mo_ta_en": "...",
  "trang_thai": [{{"mo_ta": "...", "en": "...", "tu_khoa": "...", "cau": [1, 2]}}]}}]{them_json}}}

NARRATION (numbered sentences):
{kb}"""

_P_CAU = """ALSO, for EVERY numbered sentence give ONE Vietnamese search keyword (2-6 words) to find real footage for that sentence:
built AROUND the sentence's main visible subject (name it) plus what this sentence shows — its action, place, angle or
detail — so consecutive sentences get DIFFERENT shots of the subject (e.g. "chó dingo đuổi dê", "đàn dê trên vách đá",
"xạ thủ trên trực thăng"). Concrete and filmable, no abstract words. A sentence that only continues the exact same
moment may repeat the previous keyword.
"""
_P_CAU_JSON = ',\n  "cau": {"<sentence number>": "<Vietnamese keyword>"}'


def _p(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "chu_the.json")


def _canh(du_an):
    return doc_json(os.path.join(thu_muc_du_an(du_an)[1], "tu_khoa.json"), []) or []


def _hash(canh):
    return hashlib.md5(("ct1|" + "|".join(str(c.get("text") or "") for c in canh)).encode("utf-8")).hexdigest()[:16]


def _chuan(s):
    return unicodedata.normalize("NFC", str(s or "")).lower()


def chuan_tk(s):
    """22/10 user: ép từ khoá về MỘT kiểu chữ (chữ thường, NFC, một dấu cách, bỏ dấu câu ở hai đầu) -> gõ hoa / thường /
    thừa dấu cách khác nhau vẫn là cùng một từ khoá, cùng một kho."""
    s = re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(s or "")).lower()).strip(" .,;:!?-–—\"'“”‘’")
    return s


def _sach(ds):
    ra = []
    for x in ds or []:
        if not isinstance(x, dict) or not str(x.get("ten") or "").strip():
            continue
        goi = [str(g).strip() for g in (x.get("goi") or []) if str(g).strip()]
        ten = str(x["ten"]).strip()
        loai = str(x.get("loai") or "").strip().lower()
        tt = []
        for s in x.get("trang_thai") or []:
            if not isinstance(s, dict) or not str(s.get("en") or s.get("tu_khoa") or "").strip():
                continue
            so = [str(c).strip(" []") for c in (s.get("cau") or [])]
            cau = sorted({int(c) for c in so if c.isdigit()})
            tt.append({"mo_ta": str(s.get("mo_ta") or "").strip(), "en": str(s.get("en") or s.get("tu_khoa")).strip(),
                       "tu_khoa": chuan_tk(s.get("tu_khoa") or s.get("en")), "cau": cau})
        tt = tt[:TT_TOI_DA_GOP]                            # 23/10: gộp nhiều lô -> tối đa TT_TOI_DA_GOP
        tk = [str(t).strip() for t in (x.get("tu_khoa") or []) if str(t).strip()]
        if not tk:                                           # từ khoá tìm = từ khoá các trạng thái (người dùng sửa thì giữ)
            tk = list(dict.fromkeys(s["tu_khoa"] for s in tt if s["tu_khoa"]))
        y = {"ten": ten, "loai": loai if loai in ("song", "vat", "noi") else "song", "goi": list(dict.fromkeys([ten] + goi)),
             "mo_ta_en": str(x.get("mo_ta_en") or "").strip(), "trang_thai": tt,
             "tu_khoa": tk[:max(TK_CHU_THE, len(tt))]}
        pv = x.get("pham_vi")
        if isinstance(pv, (list, tuple)) and len(pv) == 2 and all(str(v).isdigit() for v in pv):
            y["pham_vi"] = [int(pv[0]), int(pv[1])]          # 23/10: chủ thể THEO LÔ — chỉ dùng cho câu trong lô
        ra.append(y)
    return ra if any("pham_vi" in y for y in ra) else ra[:TOI_DA]


def doc_goc(du_an):
    """Danh sách chủ thể (AI lập / người dùng sửa), CHƯA gồm từ khoá tìm thêm."""
    return (doc_json(_p(du_an), {}) or {}).get("chu_the") or []


def tu_khoa_them(du_an):
    """19/10 user: "từ khoá tìm thêm" — mỗi từ khoá là một chủ thể ĐỘC LẬP (tìm đúng y nguyên, chỉ gán tay cho câu)."""
    return list(dict.fromkeys(chuan_tk(t) for t in (doc_json(_p(du_an), {}) or {}).get("tu_khoa_them") or [] if chuan_tk(t)))


def tk_cau(du_an):
    """20/10 user: TỪ KHOÁ RIÊNG của từng câu {id cảnh: [{vi, en}]} — người dùng gõ (tiếng Việt / Anh), máy dịch sẵn."""
    ra = {}
    for k, v in ((doc_json(_p(du_an), {}) or {}).get("tk_cau") or {}).items():
        v = [dict(x, vi=chuan_tk(x.get("vi") or x["en"]), en=chuan_tk(x["en"])) for x in v or []
             if isinstance(x, dict) and x.get("en") and (GOI_Y_TU_KHOA_CAU or not x.get("goi_y"))]
        if str(k).isdigit() and v:
            ra[int(k)] = v
    return ra


def doc(du_an):
    """Chủ thể dùng để chia đoạn / tìm / ghép = danh sách chủ thể + mỗi từ khoá tìm thêm / từ khoá riêng của câu thành một
    chủ thể (không tên gọi, nên không tự dò — chỉ gán cho câu)."""
    ds = doc_goc(du_an)
    ten = {x["ten"] for x in ds}
    tk = [chuan_tk(t) for t in list(tu_khoa_them(du_an)) + [x["en"] for v in tk_cau(du_an).values() for x in v]]
    them = [{"ten": t, "loai": "vat", "goi": [], "mo_ta_en": t, "tu_khoa": [t], "them": True}
            for t in dict.fromkeys(tk) if t and t not in ten]
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


CAU_MOI_LO = 25            # 23/10 user: kịch bản dài -> hỏi chủ thể theo LÔ ~25 câu (song song nhiều tài khoản) rồi gộp
LO_CHO = 150               # giây chờ một lô (lô 25 câu thường 20-40 s; tài khoản treo thì sang tài khoản khác sớm)
TT_TOI_DA_GOP = 8          # mỗi chủ thể giữ tối đa bấy nhiêu trạng thái

_P_LO = """Read PART {lo}/{tong} of a documentary narration (Vietnamese, numbered sentences). List the VISIBLE SUBJECTS this
part talks about: animals, people or groups, vehicles, places / landscapes, key physical objects — at most 6, the most
important first. Skip abstract things (ideas, money, laws, statistics, news, opinions).
For each subject give:
  - "ten": short Vietnamese name;
  - "loai": "song" (animal, person, group), "vat" (vehicle, object) or "noi" (place, landscape);
  - "goi": EVERY word or phrase THIS PART uses to refer to it, copied exactly as written;
  - "mo_ta_en": one short English description of how it looks on screen (max 15 words);
  - "trang_thai": the STATES / SITUATIONS this part shows the subject in — what is happening to it or what it does — in
    story order, at most 4, near-identical ones merged. Each state:
      "mo_ta": short Vietnamese description; "en": how it looks on screen in English (max 15 words, subject named);
      "tu_khoa": ONE English YouTube search phrase (2-6 words) for real footage of the subject in this state (no channel
      names, no "4k", no "cinematic", no "footage"); "cau": the sentence numbers that show the subject in this state.
Read EVERY sentence, including the middle and the end of the part: every sentence that shows or talks about a visible
subject must be listed in the "cau" of exactly ONE state (of the subject it is mainly about).
Only JSON: {{"chu_the": [{{"ten": "...", "loai": "song", "goi": ["..."], "mo_ta_en": "...",
  "trang_thai": [{{"mo_ta": "...", "en": "...", "tu_khoa": "...", "cau": [1, 2]}}]}}]}}

PART {lo}/{tong}:
{kb}"""

def _hoi_theo_lo(canh):
    """Kịch bản dài: hỏi chủ thể + trạng thái THEO LÔ CAU_MOI_LO câu (song song — hoi_nhieu chia các tài khoản; lô hỏng
    hỏi lại tối đa 2 lượt). KHÔNG gộp giữa các lô: mỗi chủ thể giữ phạm vi câu của lô (đo 23/10: AI gộp các lô dồn 26 chủ
    thể còn 2; user chốt mỗi lô tìm / băm riêng). Trả danh sách chủ thể đã _sach."""
    from common import hoi_nhieu
    lots = [canh[i:i + CAU_MOI_LO] for i in range(0, len(canh), CAU_MOI_LO)]
    p = [_P_LO.format(lo=k + 1, tong=len(lots),
                      kb="\n".join(f"[{c['id']}] {str(c.get('text') or '').strip()}" for c in lot))
         for k, lot in enumerate(lots)]
    log(f"[chủ thể] hỏi AI chủ thể + trạng thái THEO {len(lots)} LÔ ~{CAU_MOI_LO} câu (song song)…")
    kq = [None] * len(lots)
    for lan in range(3):
        can = [k for k in range(len(lots)) if kq[k] is None]
        if not can:
            break
        if lan:
            log(f"[chủ thể] hỏi lại {len(can)} lô hỏng (lượt {lan + 1})")
        for k, r in zip(can, hoi_nhieu([p[k] for k in can], timeout=LO_CHO)):
            j = rut_json(r or "")
            ds_ = _sach((j or {}).get("chu_the") if isinstance(j, dict) else j)
            if ds_:
                id_lo = {c["id"] for c in lots[k]}
                for x in ds_:                                # câu ngoài lô (AI ghi nhầm) -> bỏ
                    for s in x["trang_thai"]:
                        s["cau"] = [c for c in s["cau"] if c in id_lo]
                kq[k] = ds_
    hong = [k + 1 for k in range(len(lots)) if kq[k] is None]
    if hong:
        log(f"[chủ thể] ! lô {hong} vẫn không trả chủ thể — bỏ qua các lô đó")
    # 23/10 user ("đã hỏi tách lô thì không gộp, mỗi lô đều phải tìm kiếm kết quả của lô đó rồi băm"): KHÔNG gộp — mỗi
    # chủ thể của lô là một chủ thể riêng (tên kèm "· lô k", phạm vi câu của lô) -> đoạn / kho / tìm / băm riêng theo lô
    ra = []
    for k, ds_ in enumerate(kq):
        if not ds_:
            continue
        pv = [lots[k][0]["id"], lots[k][-1]["id"]]
        for x in ds_:
            ra.append(dict(x, ten=f"{x['ten']} · lô {k + 1}", pham_vi=pv))
    ds = _sach(ra)
    log(f"[chủ thể] {len(ds)} chủ thể của {len(lots)} lô (không gộp — mỗi lô tìm / băm riêng); câu có trạng thái: "
        f"{len({c for x in ds for s in x['trang_thai'] for c in s['cau']})}/{len(canh)}")
    return ds


def lap(du_an, hoi_lai=False):
    """Hỏi AI MỘT lần cho cả kịch bản (đã có và kịch bản không đổi -> dùng lại, trừ khi hoi_lai)."""
    canh = _canh(du_an)
    if not canh:
        raise ValueError("dự án chưa có tu_khoa.json — chạy bước đọc giọng trước")
    h = _hash(canh)
    da = doc_json(_p(du_an), {}) or {}
    if not hoi_lai and da.get("_hash") == h and da.get("chu_the"):
        return da["chu_the"]
    ds, j = [], None
    if len(canh) > CAU_MOI_LO and not GOI_Y_TU_KHOA_CAU:
        # 23/10 user ("dài quá nó trả lời cho có, phải chia ra nhiều đoạn để nó bắt chủ thể"): hỏi THEO LÔ rồi gộp
        ds = _hoi_theo_lo(canh)
    else:
        kb = "\n".join(f"[{c['id']}] {str(c.get('text') or '').strip()}" for c in canh)[:30000]
        log(f"[chủ thể] hỏi AI chủ thể chính + từ khoá cho cả kịch bản ({len(canh)} cảnh)…")
        for _ in range(3):
            j = rut_json(hoi_llm(_P.format(n=TOI_DA, tt=TT_TOI_DA, kb=kb, them_cau=_P_CAU if GOI_Y_TU_KHOA_CAU else "",
                                           them_json=_P_CAU_JSON if GOI_Y_TU_KHOA_CAU else ""), timeout=300) or "")
            ds = _sach((j or {}).get("chu_the") if isinstance(j, dict) else j)
            if ds:
                break
    if not ds:
        raise ValueError("AI không trả danh sách chủ thể (thử lại)")
    # 22/10 user: GỢI Ý SẴN một từ khoá cho từng câu (cùng lần hỏi) -> điền vào từ khoá riêng của câu (dịch Anh như khi
    # gõ tay). Người dùng soát thì sửa, không soát thì tìm luôn theo gợi ý. Câu người dùng đã tự gõ: giữ nguyên.
    id_ok = {c["id"] for c in canh}
    goi_y = {}
    for k, v in ((j or {}).get("cau") or {}).items() if GOI_Y_TU_KHOA_CAU and isinstance(j, dict) and isinstance(j.get("cau"), dict) else []:
        k = str(k).strip(" []")
        if k.isdigit() and int(k) in id_ok and str(v or "").strip():
            goi_y[k] = chuan_tk(v)
    tkc = {k: v for k, v in (da.get("tk_cau") or {}).items() if v and not all(x.get("goi_y") for x in v)}
    if goi_y:
        dich = _dich([v for k, v in goi_y.items() if k not in tkc], {})
        for k, v in goi_y.items():
            if k not in tkc:
                tkc[k] = [{"vi": v, "en": chuan_tk(dich.get(v, v)), "goi_y": True}]
    if GOI_Y_TU_KHOA_CAU:
        log(f"[chủ thể] gợi ý từ khoá cho {len(goi_y)}/{len(canh)} câu")
    ghi_json(_p(du_an), {"_hash": h, "chu_the": ds, "tk_cau": tkc})
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
    tkt = cu.get("tu_khoa_them") or [] if them is None else [chuan_tk(t) for t in them if chuan_tk(t)]
    tkc = cu.get("tk_cau") or {}
    if tk is not None:                                       # {id: "cụm, cụm"} hoặc {id: [cụm]} — dịch cụm mới
        moi = {}
        for k, v in tk.items():
            v = v if isinstance(v, list) else str(v or "").split(",")
            v = list(dict.fromkeys(chuan_tk(x) for x in v if chuan_tk(x)))
            if v and str(k).isdigit():
                moi[str(k)] = v
        cu_dich = {chuan_tk(x["vi"]): x["en"] for vv in tkc.values() for x in vv if isinstance(x, dict) and x.get("vi")}
        dich = _dich([c for v in moi.values() for c in v], cu_dich) if moi else {}
        da_goi_y = {k: {x["vi"] for x in vv if isinstance(x, dict) and x.get("goi_y")} for k, vv in tkc.items()}
        tkc = {k: [dict({"vi": c, "en": chuan_tk(dich.get(c, c))}, **({"goi_y": True} if c in da_goi_y.get(k, ()) else {}))
                   for c in v] for k, v in moi.items()}
    tt_cu = {x.get("ten"): x.get("trang_thai") or [] for x in cu.get("chu_the") or []}
    pv_cu = {x.get("ten"): x.get("pham_vi") for x in cu.get("chu_the") or [] if x.get("pham_vi")}
    ds = [dict(x, trang_thai=x.get("trang_thai") or tt_cu.get(str(x.get("ten") or "").strip(), []),
               pham_vi=x.get("pham_vi") or pv_cu.get(str(x.get("ten") or "").strip()))   # 23/10: giữ phạm vi lô
          for x in ds or [] if isinstance(x, dict)]
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
        d = nhac(c.get("text"), mau, c["id"])
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
    for k, rx, yeu, pv in mau:
        if not yeu and k not in ks and _hop(pv, c["id"]):
            m = rx.search(t)
            if m:
                vt.append((m.start(), k))
    for _, k in sorted(vt):
        if k not in ks:
            ks.append(k)
    return ks


def trang_thai_cau(du_an):
    """22/10 user: {id cảnh: mô tả hình (en) của TRẠNG THÁI chủ thể chính ở câu đó} — goi_y chấm mảnh theo trạng thái này
    trước (cùng kho chủ thể), hết hình trạng thái đó mới tới hình trạng thái khác của chủ thể. Câu AI xếp vào trạng thái
    của chủ thể KHÁC chủ thể chính của câu thì bỏ qua."""
    ds = doc(du_an)
    if not ds:
        return {}
    ks = ds_k_cau(du_an)
    ra = {}
    for k, x in enumerate(ds):
        for s in x.get("trang_thai") or []:
            for c in s.get("cau") or []:
                if ks.get(c) and ks[c][0] == k and s.get("en"):
                    ra.setdefault(c, s["en"])
    return ra


def ds_k_cau(du_an):
    """22/10: {id cảnh: [chỉ số chủ thể]} (phần tử đầu = chủ thể chính) — cho bước lấp mở rộng của goi_y."""
    ds = doc(du_an)
    if not ds:
        return {}
    canh = sorted(_canh(du_an), key=lambda c: c["id"])
    gt = gan_tay(du_an)
    gan = gan_canh(canh, ds, gt)
    mau = _mau(ds)
    return {c["id"]: _ds_k(c, ds, gan, gt, mau) for c in canh}


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
        d = nhac(c.get("text"), mau, c["id"])
        if c["id"] in gt or not d or max(d.values()) < 1.0:
            ra.append({"id": c["id"], "text": c.get("text") or "", "dang": ds[gan[c["id"]]]["ten"], "tay": gt.get(c["id"], "")})
    return ra


def _mau(ds):
    """[(chỉ số chủ thể, regex, yếu)] — tên gọi dài trước để 'chó sói' không bị 'chó' ăn mất. YẾU = tên gọi MỘT chữ của
    chủ thể nơi chốn ('đảo', 'rừng'): chỉ nói nơi xảy ra, không đổi chủ thể của cảnh (đo cho_digo: 'đưa khỏi đảo')."""
    cap = sorted(((k, _chuan(g), ds[k].get("loai") == "noi" and len(_chuan(g).split()) == 1)
                  for k, x in enumerate(ds) for g in x["goi"] if len(_chuan(g)) >= 2), key=lambda z: -len(z[1]))
    return [(k, re.compile(r"(?<!\w)" + re.escape(g) + r"(?!\w)"), yeu, ds[k].get("pham_vi")) for k, g, yeu in cap]


def _hop(pv, cid):
    """Chủ thể (phạm vi lô pv) có áp cho câu cid không — không theo lô / không biết câu: có."""
    return not pv or cid is None or pv[0] <= int(cid) <= pv[1]


def nhac(text, mau, cid=None):
    """{chỉ số chủ thể: số lần nhắc} trong một câu / vế (mỗi chỗ chỉ tính cho tên gọi dài nhất khớp). cid: id câu — chủ
    thể theo lô chỉ tính trong lô của nó (23/10 user: mỗi lô độc lập)."""
    t = _chuan(text)
    dem, che = {}, [False] * len(t)
    for k, rx, yeu, pv in mau:
        if not _hop(pv, cid):
            continue
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
            k = _chon(nhac(c.get("text"), mau, c["id"]), truoc)
            if k is not None and not _hop(ds[k].get("pham_vi"), c["id"]):   # sang lô mới mà câu không nhắc ai:
                k = next((j for j, x in enumerate(ds) if x.get("pham_vi") and _hop(x["pham_vi"], c["id"])), k)  # chủ thể chính của lô
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
                 trang_thai=list(x.get("trang_thai") or []),
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
                     "tu_khoa_en": list(x["tu_khoa"]), "trang_thai": list(x.get("trang_thai") or []),
                     "chu_the": k, "loai": "ke", "kho_cd": n, "kho_ds": [n],
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
            d = nhac(s, mau, c["id"])
            k = _chon(d, None) if d and max(d.values()) >= 1.0 else None
            if c["id"] in gt:                                # gán tay nhiều chủ thể: vế nhắc tên chủ thể nào trong danh sách
                if k not in ks:                              # thì chiếu nó, không nhắc thì chia đều các vế theo thứ tự
                    k = ks[min(len(ks) - 1, p * len(ks) // max(1, len(ves)))]
            if k is not None and k != ks[0]:
                ra.setdefault(str(c["id"]), []).append({"bd": bd, "kt": kt, "mo_ta_en": ds[k]["mo_ta_en"] or ds[k]["ten"],
                                                        "rieng": True, "nhac_lai": False, "chu_the": k})
    return ra
