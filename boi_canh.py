# -*- coding: utf-8 -*-
"""BỐI CẢNH HÌNH cho băm footage (28/10 user: "ghép kiểu này không được vì nó vẫn không đúng cảnh mấy").

Đo casauthabien 28/10 (soát bằng mắt 48 đoạn từ phút 10): ~một nửa sai cảnh — 80/141 mảnh kho là cá sấu SỐNG ở đầm lầy
bị đặt vào câu nói về XÁC cá sấu dưới đáy biển sâu. SigLIP chấm "có cá sấu" chứ không phân biệt sống / chết, đầm lầy /
đáy biển. Cách chữa:
  1. AI đặt 2-5 MÔI TRƯỜNG LỚN của video (đáy biển tối / boong tàu / đầm lầy… — nhãn chi tiết kiểu "giáp xác ăn xác" vs
     "giun trên xương" thì SigLIP xếp nhầm: thử 28/10 sứa -> giun, cá -> cá mập).
  2. Gán mỗi cảnh (tu_khoa.json) một môi trường — 28/10 user ("sao không thay luôn đoạn hỏi chủ thể? hỏi 1 lần làm sao
     mà nó kĩ được"): gán NGAY TRONG các lô hỏi chủ thể (chu_the._hoi_theo_lo, ~25 cảnh / lô); dự án đã có chủ thể (không
     hỏi lại để khỏi đổi kho / nguồn 🎯) thì hỏi riêng THEO LÔ ~25 cảnh, song song, kèm vài cảnh trước làm ngữ cảnh.
     Câu bình luận / kêu gọi -> môi trường của đoạn truyện đang kể. Lưu ra/<dự án>/boi_canh.json.
  3. Mỗi mảnh footage: SigLIP so vector hình (trung bình các khung) với mô tả các môi trường + vài nhãn "khác" -> nhãn.
  4. goi_y chỉ ghép footage CÙNG môi trường với cảnh đang đọc (cả bước lặp lại); hết mảnh đúng môi trường -> ảnh AI."""
import hashlib
import os

import numpy as np

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

PHIEN_BAN = 3                # đổi câu hỏi AI -> tăng để hỏi lại (3: gán theo lô ~25 cảnh thay một lần cả bài)
BAT = True                   # tắt: False (goi_y ghép như cũ, không lọc bối cảnh)
CANH_MOI_LO = 25             # số cảnh mỗi lô gán môi trường (cùng cỡ lô hỏi chủ thể)
NGU_CANH = 4                 # số cảnh trước lô gửi kèm làm ngữ cảnh (không gán)
# nhãn "khác": mảnh không thuộc bối cảnh nào của video (người nói chuyện, chữ / đồ hoạ, cảnh lạc đề) -> không ghép
KHAC = ("people talking to the camera, interview, presenter",
        "text, title card, graphics, logo, black screen",
        "a city street, buildings, cars")

_P_MT = """You plan the B-ROLL of a narrated documentary video. Below is its script (numbered scenes).

Define the ENVIRONMENTS of this video: 2-5 BROAD places where the camera is, each one VERY different to the eye (light,
colors, above or under water, indoors or outdoors) so that a single frame tells them apart at a glance. Broad, not
detailed: NOT "isopods eating a carcass" vs "worms on a skeleton" (both are the same dark deep sea floor).
Example for a story about dead alligators sunk to the deep sea: "dark deep sea floor underwater lit by lamps", "ship deck
and ocean surface in daylight", "swamp, river or riverbank in daylight with live alligators".
"en": 6-14 English words describing what such footage looks like (for an image-text matching model).

Only JSON: {{"boi_canh": [{{"id": "A", "en": "..."}}]}}

SCRIPT:
{ds}"""

# đoạn gắn vào câu hỏi chủ thể theo lô (chu_the._P_LO) và câu hỏi gán riêng theo lô (_P_GAN)
LUAT_GAN = """ENVIRONMENTS of the whole video (broad places where the camera is):
{mt}
For EVERY numbered sentence of this part give the environment where the story IS at that moment — read it carefully
with the sentences around it (who / what is where right now: alive or dead, above or under water, on the ship or on the
sea floor). A sentence that is commentary, a question, a number, a lesson, a call to like / subscribe or an outro takes
the environment of the story part it belongs to."""

_P_GAN = LUAT_GAN + """

Only JSON: {{"moi_truong": {{"<sentence number>": "<environment id>"}}}}

{truoc}PART {lo}/{tong} (give EVERY sentence of this part):
{ds}"""


def _p(out):
    return os.path.join(out, "boi_canh.json")


def _dong(c):
    return f"[{c['id']}] {str(c.get('text') or '').strip()}"


def ds_mt(bc):
    """{id: en} -> các dòng liệt kê môi trường cho câu hỏi AI."""
    return "\n".join(f'  "{k}": {v}' for k, v in bc.items())


def dinh_nghia(canh):
    """Một lần hỏi (cả bài, vì chỉ cần cái nhìn tổng): 2-5 môi trường lớn -> {id: en} | {}."""
    kb = "\n".join(_dong(c) for c in canh)[:30000]
    for _ in range(2):
        j = rut_json(hoi_llm(_P_MT.format(ds=kb), timeout=240) or "")
        bc = {str(b["id"]): str(b["en"]).strip() for b in (j or {}).get("boi_canh") or []
              if isinstance(b, dict) and b.get("id") and b.get("en")} if isinstance(j, dict) else {}
        if 2 <= len(bc) <= 6:
            return bc
    return {}


def doc_gan(j, bc, id_lo):
    """Đọc {"moi_truong": {...}} của một lô -> {id cảnh (int): id môi trường} (chỉ cảnh trong lô, môi trường hợp lệ)."""
    mt = (j or {}).get("moi_truong") if isinstance(j, dict) else None
    ra = {}
    for k, v in (mt or {}).items() if isinstance(mt, dict) else []:
        k = str(k).strip(" []")
        if k.isdigit() and int(k) in id_lo and str(v) in bc:
            ra[int(k)] = str(v)
    return ra


def gan_theo_lo(canh, bc):
    """Gán môi trường cho từng cảnh, hỏi THEO LÔ CANH_MOI_LO cảnh song song (kèm NGU_CANH cảnh trước làm ngữ cảnh);
    lô hỏng / thiếu cảnh hỏi lại tối đa 2 lượt. -> {id cảnh: id môi trường}."""
    from common import hoi_nhieu
    lots = [canh[i:i + CANH_MOI_LO] for i in range(0, len(canh), CANH_MOI_LO)]

    def cau_hoi(k):
        tr = canh[max(0, k * CANH_MOI_LO - NGU_CANH):k * CANH_MOI_LO]
        truoc = ("STORY JUST BEFORE THIS PART (context only, do not label):\n" + "\n".join(_dong(c) for c in tr) + "\n\n"
                 if tr else "")
        return _P_GAN.format(mt=ds_mt(bc), truoc=truoc, lo=k + 1, tong=len(lots), ds="\n".join(_dong(c) for c in lots[k]))
    ra = {}
    for lan in range(3):
        can = [k for k in range(len(lots)) if sum(1 for c in lots[k] if c["id"] in ra) < 0.9 * len(lots[k])]
        if not can:
            break
        log(f"  bối cảnh hình: gán môi trường {len(can)} lô ~{CANH_MOI_LO} cảnh" + (f" (hỏi lại lượt {lan + 1})" if lan else ""))
        for k, r in zip(can, hoi_nhieu([cau_hoi(k) for k in can], timeout=150)):
            ra.update(doc_gan(rut_json(r or ""), bc, {c["id"] for c in lots[k]}))
    return ra


def lap(du_an, canh=None):
    """{"boi_canh": {id: en}, "canh": {id cảnh: id môi trường}} — ưu tiên môi trường đã gán trong lúc hỏi chủ thể
    (chu_the.json); chưa có thì hỏi riêng theo lô. Cache theo nội dung cảnh. Lỗi -> {}."""
    out = thu_muc_du_an(du_an)[1]
    canh = canh or doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    if not canh:
        return {}
    h = hashlib.md5((f"v{PHIEN_BAN}|" + "|".join(str(c.get("text") or "") for c in canh)).encode("utf-8")).hexdigest()[:16]
    cu = doc_json(_p(out), {}) or {}
    if cu.get("_hash") == h and cu.get("boi_canh") and cu.get("canh"):
        return cu
    bc, gan = {}, {}
    try:                                                     # môi trường đã gán ngay trong các lô hỏi chủ thể
        import chu_the
        ct = doc_json(os.path.join(out, "chu_the.json"), {}) or {}
        if ct.get("_hash") == chu_the._hash(canh) and ct.get("moi_truong_ds") and ct.get("moi_truong"):   # noqa: SLF001
            bc, gan = ct["moi_truong_ds"], {int(k): v for k, v in ct["moi_truong"].items()}
            log("  bối cảnh hình: dùng môi trường đã gán lúc hỏi chủ thể")
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! bối cảnh hình (chủ thể): {str(e)[:100]}")
    if not (bc and len(gan) >= 0.8 * len(canh)):
        log(f"  bối cảnh hình: AI đặt môi trường cho {len(canh)} cảnh (đặt chung 1 lần, gán theo lô)…")
        bc = dinh_nghia(canh)
        gan = gan_theo_lo(canh, bc) if bc else {}
    if not bc or len(gan) < 0.8 * len(canh):
        log("    ! bối cảnh hình: AI không trả đủ — băm không lọc bối cảnh")
        return {}
    d = {"_hash": h, "boi_canh": bc, "canh": {str(k): v for k, v in gan.items()}}
    ghi_json(_p(out), d)
    log("  bối cảnh hình: " + "; ".join(f"{k} = {v}" for k, v in bc.items()))
    return d


def nhan_manh(d, E):
    """E: {kho_id: ma trận vector khung (SigLIP)} -> {kho_id: id bối cảnh | "khac"}."""
    import nhung_siglip
    if not d or not E:
        return {}
    ten = list(d["boi_canh"]) + ["khac"] * len(KHAC)
    T = nhung_siglip.nhung_chu(list(d["boi_canh"].values()) + list(KHAC))
    ids, V = [], []
    for kid, e in E.items():
        v = np.asarray(e, dtype=np.float32)
        v = v.mean(0) if v.ndim == 2 else v
        ids.append(kid)
        V.append(v / (np.linalg.norm(v) + 1e-8))
    S = np.stack(V) @ T.T
    # 28/10: điểm SigLIP mỗi câu mô tả lệch một mức riêng (câu có chữ "alligator" hút 108/156 mảnh) -> trừ điểm trung
    # bình của từng nhãn trên cả kho rồi mới lấy nhãn cao nhất. Đo casauthabien (soát bằng mắt): trừ trung bình đúng nhất;
    # chia thêm độ lệch (z) đẩy 10 cảnh đáy biển (sứa, cá) sang "phòng thí nghiệm"
    if len(ids) >= 8:
        S = S - S.mean(0)
    return {kid: ten[int(i)] for kid, i in zip(ids, S.argmax(1))}


def theo_giay(d, canh):
    """-> hàm(giây tuyệt đối) -> id môi trường của cảnh đang đọc (cảnh chưa gán: theo cảnh trước; None nếu không biết)."""
    if not d:
        return lambda t: None
    ds, k_truoc = [], None
    for c in sorted(canh, key=lambda z: float(z.get("bat_dau") or 0)):
        k_truoc = d["canh"].get(str(c["id"])) or k_truoc
        ds.append((float(c.get("bat_dau") or 0), float(c.get("bat_dau") or 0) + float(c.get("dai") or 0), k_truoc))

    def f(t):
        for a, b, k in ds:
            if a - 0.05 <= t < b + 0.05:
                return k
        return None
    return f
