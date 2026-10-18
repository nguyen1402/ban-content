# -*- coding: utf-8 -*-
"""Skill chỉnh sửa: dự án THÔ (ra/ket_qua.json + clip đã dựng) -> dự án CapCut HOÀN CHỈNH có chuyển cảnh,
chữ nhấn mạnh, nhạc nền, hiệu ứng âm thanh — lấy từ kho CapCut.

  python dung_hoan_chinh.py --ten "Chim canh cut - ban tho v6 hoan chinh"
      Lập kế hoạch tự động (ra/ke_hoach.json) rồi dựng. Chạy lại với --giu-ke-hoach để dựng theo kế hoạch đã sửa tay.
  --chi-lap-ke-hoach   chỉ lập kế hoạch, chưa dựng.
"""
import argparse
import json
import math
import os
import random
import re
import sys
import uuid

AQ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQ)
for p in (ROOT, AQ):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import OUT, doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_nhap_capcut     # noqa: E402
import ghep                                                                                  # noqa: E402
import kho_capcut                                                                            # noqa: E402
import so_hien_thi                                                                           # noqa: E402

SEC = 1_000_000
#: 16/10: SFX tinh gọn chuẩn tài liệu (chỉ whoosh đổi chương + hit cao trào). Bật bằng True / cờ --co-sfx
SFX_BAT = False
#: 16/10: Nhạc nền từ kho sạch không bản quyền (kho_am_thanh). Bật bằng True / cờ --co-nhac
NHAC_BAT = True
NHAC_NGUON = "kho_chuan"  # "kho_chuan" (kho_am_thanh sạch) | "mixkit" | "kho"
CHU_BAT = False
#: 12/10 user: lớp ẢNH PHỦ minh hoạ khi cần (chinh_sua/lop_phu.py). Tắt bằng --khong-lop-phu.
LOP_PHU_BAT = False        # 13/10 user: ẨN thẻ highlight ("hiện tại chưa cần dùng tới") — bật lại: True / bỏ --khong-lop-phu
#: 12/10 user: hiệu ứng kiểu video mẫu (chinh_sua/hieu_ung.py): bản đồ đường đi A->B, khung highlight viền vàng,
#: phủ màu khi đổi chương. Tắt bằng --khong-hieu-ung.
HIEU_UNG_BAT = True
#: 12/10 user: lớp Remotion "BẢNG GIẤY" khớp lời (chinh_sua/bang_giay.py, kiểu kênh "Вся жизнь пчелы"): thẻ video trên
#: nền giấy + tiêu đề/nhãn, mũi tên, thẻ câu hỏi, cột so sánh, mốc năm, bản đồ phẳng. Tắt: --khong-bang-giay.
#: 13/10 user: điều phối chung (dieu_phoi.py) — mỗi câu tối đa MỘT lớp: thẻ highlight / bản đồ (khoanh vùng, đường đi
#: có icon phương tiện, lan rộng) / sơ đồ Remotion trên nền video tối (cấu tạo, quy trình, vòng đời, mô phỏng).
#: Tắt (về cách cũ: thẻ và đường đi hỏi riêng): --khong-dieu-phoi.
DIEU_PHOI_BAT = True
#: 13/10 user nghe thử rồi BỎ NGAY tiếng động diễn cảnh ("nghe không hợp"). 17/10 user bật lại cho mốc chữ, biểu đồ cột và AI slow.
TIENG_DONG_BAT = True
DEN_THEM = 1.0             # 15/10 user: đen màn ở chỗ (nghỉ X) kéo dài thêm bấy nhiêu giây MỖI BÊN (tối dần / sáng lại)
BANG_GIAY_BAT = False     # 12/10 user xem bản thử rồi BỎ ("không muốn vẽ kiểu đấy") — bật lại bằng --co-bang-giay
KE_HOACH = os.path.join(OUT, "ke_hoach.json")

MILD = ["Mờ dần", "Rõ dần", "Trượt sang trái", "Trượt sang phải"]
STRONG = ["Phóng to", "Trượt sang phải", "Mờ dần"]
#: chuyển cảnh ĐO ĐƯỢC là làm nháy khung khi clip không có phần dư đầu/cuối (đo trên MP4 xuất từ CapCut, 09/10:
#: Zoom gần nhẹ 15/15 chỗ nháy, Lật hiện ra 5/5, Hòa trộn rực rỡ 1/1; Mờ dần/Rõ dần/Trượt gần như sạch).
BO_NHAY = {"Zoom gần nhẹ", "Lật hiện ra", "Hòa trộn rực rỡ", "Chớp sét", "Xoay và hiện ra", "Rung chấn"}


# --------------------------------------------------------------------------- dòng thời gian của dự án thô
def dong_thoi_gian(canh):
    """Giống ghep.xuat_nhap_capcut: mỗi ô nối liền nhau; ghi c['_t0'], c['_t1'] (µs) và c['_os']."""
    t = 0
    for c in canh:
        c["_t0"] = t
        c["_os"] = []
        for o in c["o"]:
            if not o.get("clip"):
                continue
            d = min(int(round(o["dai"] * SEC)), ghep._dai_that(o["clip"]) - 1000)      # noqa: SLF001
            c["_os"].append((t, d, o))
            t += d
        c["_t1"] = t
    return t


def tach_cau(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]


def tao_srt(canh):
    """Mỗi CÂU một dòng SRT; giờ chia theo số chữ + khoảng nghỉ dấu câu trong phạm vi giọng đọc của cảnh."""
    cau, idx = [], 0
    for c in canh:
        ss = tach_cau(c["text"])
        if not ss:
            continue
        w = [max(sum(ch.isalnum() for ch in s) + 3 * s.count(",") + 6 * sum(s.count(x) for x in ".!?…"), 1)
             for s in ss]
        dai = min(c.get("giong_dai") or (c["_t1"] - c["_t0"]) / SEC, (c["_t1"] - c["_t0"]) / SEC)
        t, tong = c["_t0"] / SEC, float(sum(w))
        moc = c.get("moc_tu")
        n_tok = [len(s.split()) for s in ss]
        if moc and sum(n_tok) == len(moc):                              # mốc từng chữ THẬT của giọng đọc
            j = 0
            for s, nt in zip(ss, n_tok):
                idx += 1
                cau.append({"i": idx, "t0": round(c["_t0"] / SEC + moc[j][0], 2),
                            "t1": round(c["_t0"] / SEC + moc[j + nt - 1][1], 2), "text": s, "canh": c["id"],
                            "tu": [(tk, round(c["_t0"] / SEC + moc[j + q][0], 3), round(c["_t0"] / SEC + moc[j + q][1], 3))
                                   for q, tk in enumerate(s.split())]})     # giờ từng chữ (căn theo giọng thật)
                j += nt
            continue
        for s, wi in zip(ss, w):
            idx += 1
            d = dai * wi / tong
            cau.append({"i": idx, "t0": round(t, 2), "t1": round(t + d, 2), "text": s, "canh": c["id"]})
            t += d
    return cau


def _srt_gio(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ghi_srt(cau, path):
    with open(path, "w", encoding="utf-8") as f:
        for c in cau:
            f.write(f"{c['i']}\n{_srt_gio(c['t0'])} --> {_srt_gio(c['t1'])}\n{c['text']}\n\n")


# --------------------------------------------------------------------------- kế hoạch (ChatGPT + luật)
_P_CHUONG = """Below is the full list of sentences (index + start of text) of a Vietnamese documentary narration about a wildlife conservation story. Divide it into 4-9 consecutive SECTIONS by narrative arc and pick the background-music mood for each.
mood must be one of: "huyen_bi" (mysterious/slow), "dien_anh" (cinematic), "soi_dong" (tense/energetic, for crises and action), "nhe_nhang" (gentle/hopeful).
Return ONLY JSON: [{{"tu_cau": <first index>, "den_cau": <last index>, "ten": "<short Vietnamese name>", "tam_trang": "<mood>"}}]; sections must cover every index from 1 to {n} without gaps.

SENTENCES:
{ds}"""

_P_NHAN = """You are a documentary editor adding ON-SCREEN EMPHASIS TEXT and sound effects to a Vietnamese narration. Sentences (index. [start second] text):
{ds}

Choose:
- "chu": at most ONE emphasis text per ~6 sentences, only for genuinely striking things (shocking numbers, key names, a turning point, a rhetorical question). "text" = 1-5 Vietnamese words condensed or copied from that sentence, UPPERCASE (e.g. "800 CON CHIM", "CHỈ CÒN 4 CON", "NĂM 2005"). "kieu": "so_lieu" | "ten" | "cam_xuc" | "y_chinh".
- "sfx": sparse sound-effect cues for dramatic moments: "hit" (shock, deaths, disaster), "ting" (hopeful reveal, success), "riser" (building up to a big reveal), at most ~1 per 15 sentences.
Return ONLY JSON: {{"chu": [{{"cau": <index>, "text": "...", "kieu": "..."}}], "sfx": [{{"cau": <index>, "kieu": "hit"}}]}}"""


def chuyen_canh_theo_luat(canh, cau, chuong, theo_i, chuong_cua_cau, rnd):
    """Chuyển cảnh theo luật: cùng cảnh = cắt thẳng; đổi cảnh ≈45% chuyển nhẹ; đổi chương = chuyển mạnh + whoosh."""
    dm = doc_json(os.path.join(kho_capcut.KHO, "danh_muc.json")) or kho_capcut.quet_danh_muc()
    mien_phi = {}
    for it in dm.get("chuyen_canh", []):
        if not it["vip"] and it["md5"]:
            mien_phi.setdefault(it["ten"], it)
    nhe = [mien_phi[n] for n in MILD if n in mien_phi]
    manh = [mien_phi[n] for n in STRONG if n in mien_phi]
    cau_dau_canh = {}
    for c in cau:
        cau_dau_canh.setdefault(c["canh"], c["i"])
    seg = [(t, d, c["id"]) for c in canh for (t, d, _o) in c["_os"]]
    chuyen = []
    sfx_cung = []
    for k in range(len(seg) - 1):
        a, b = seg[k], seg[k + 1]
        if a[2] == b[2]:
            continue                                        # nhịp trong cùng một cảnh: cắt thẳng
        if abs(a[0] + a[1] - b[0]) > int(0.05 * SEC):
            continue                                        # hai đoạn không liền nhau (có khoảng nghỉ): không chuyển
        ca, cb = chuong_cua_cau(cau_dau_canh.get(a[2], 1)), chuong_cua_cau(cau_dau_canh.get(b[2], 1))
        ranh = (b[0]) / SEC
        if ca != cb and manh:
            it = manh[len(chuyen) % len(manh)]
            chuyen.append({"sau_o": k, "ten": it["ten"], "id": it["id"], "dai": 0.6, "manh": True})
            sfx_cung.append({"t": round(ranh - 0.25, 2), "kieu": "whoosh", "ly_do": "đổi chương"})
        elif nhe and rnd.random() < 0.45:
            it = nhe[rnd.randrange(len(nhe))]
            chuyen.append({"sau_o": k, "ten": it["ten"], "id": it["id"], "dai": 0.4, "manh": False})

    return chuyen, sfx_cung


def cap_nhat_gio(kh, cau, tong_s):
    """Giữ nguyên NỘI DUNG kế hoạch (chữ, chương, kiểu SFX) nhưng cập nhật GIỜ theo SRT hiện tại (mốc giọng thật)."""
    theo_i = {c["i"]: c for c in cau}
    for x in kh["chu"]:
        c = theo_i.get(x["cau"])
        if c:
            goc, tx = c["text"].lower(), x["text"]
            vt = goc.find(tx.lower().split()[0]) if tx else -1
            x["bd"] = round(c["t0"] + (c["t1"] - c["t0"]) * (max(vt, 0) / max(len(goc), 1)) + 0.1, 2)
    for ch in kh["chuong"]:
        ch["tu"] = theo_i[min(max(ch["tu_cau"], 1), len(cau))]["t0"]
        ch["den"] = theo_i[ch["den_cau"]]["t1"] if ch["den_cau"] < len(cau) else round(tong_s, 2)
    kh["chuong"][0]["tu"] = 0.0
    kh["chuong"][-1]["den"] = round(tong_s, 2)
    cu = []
    for sf in kh["sfx"]:
        m = re.match(r"câu (\d+)", sf.get("ly_do", ""))
        if m and theo_i.get(int(m.group(1))):                      # gợi ý theo câu: dịch theo giờ câu mới
            c = theo_i[int(m.group(1))]
            sf["t"] = round(c["t0"] if sf["kieu"] != "riser" else max(0.0, c["t0"] - 1.0), 2)
            cu.append(sf)
    for x in kh["chu"]:                                             # SFX theo chữ nhấn mạnh: dựng lại từ giờ chữ mới
        cu.append({"t": x["bd"], "kieu": "pop" if x["kieu"] in ("ten", "y_chinh") else "hit", "ly_do": "chữ nhấn mạnh"})
    return kh, cu


def tinh_lai_chuyen_canh(canh, cau, kh):
    """Giữ nguyên nội dung kế hoạch đã duyệt; dựng lại chuyển cảnh theo các ô hiện tại và cập nhật giờ theo SRT mới."""
    theo_i = {c["i"]: c for c in cau}
    tong_s = max(c["_t1"] for c in canh) / SEC
    kh, cu = cap_nhat_gio(kh, cau, tong_s)

    def chuong_cua_cau(i):
        for k, x in enumerate(kh["chuong"]):
            if x["tu_cau"] <= i <= x["den_cau"]:
                return k
        return len(kh["chuong"]) - 1
    chuyen, sfx_cung = chuyen_canh_theo_luat(canh, cau, kh["chuong"], theo_i, chuong_cua_cau, random.Random(7))
    kh["chuyen_canh"] = chuyen
    tat_ca = sorted(cu + sfx_cung, key=lambda z: z["t"])
    gon = []
    for sf in tat_ca:                                               # không dồn hai SFX trong 1,2s
        if not gon or sf["t"] - gon[-1]["t"] >= 1.2:
            gon.append(sf)
    am = _kho_am_thanh()
    kh["sfx"] = chon_sfx(gon, am) if SFX_BAT else []
    kh["nhac"] = chon_nhac(kh["chuong"], am)
    return kh


_P_SO_LIEU = """You are adding ON-SCREEN TEXT to a Vietnamese documentary narration, ONLY where the narration states a concrete NUMBER or an IMPORTANT FACT. Sentences (index. [start second] text):
{ds}

Pick a sentence if it states: a count or quantity (800 birds, four survivors, 140 killed), a year / date / duration (2005, 13 years, four weeks), a measurement (33 cm, under 1 kg, 50 kg), a percentage, or a key fact the viewer must remember (a technical term such as "surplus killing", the exact name of the species or place when it is first introduced). Numbers spelled out in words (bốn, mười, hai trăm) COUNT — write them as digits.
Do NOT add slogans, emotional lines or summaries.
"text" = the figure with its noun, 1-5 Vietnamese words, UPPERCASE (examples: "800 CON CHIM", "CHỈ CÒN 4 CÁ THỂ", "NĂM 2005", "33 CM · DƯỚI 1 KG").
Return ONLY JSON: [{{"cau": <sentence index>, "text": "...", "kieu": "so_lieu" | "moc_thoi_gian" | "du_kien"}}]"""

_RX_SO = re.compile(r"(\d[\d.,]*)\s+([^\s,.;:!?]+(?:\s+[^\s,.;:!?]+)?)")


THUAT_NGU_GIU = ("SURPLUS KILLING",)


def loc_chu_so_lieu(chu):
    """Chỉ giữ chữ CÓ CHỮ SỐ (năm, số lượng, thời lượng, số đo) + thuật ngữ quan trọng; bỏ tên riêng/nhãn (kịch bản hay
    nghe sai tên) và chữ lặp trong 90s."""
    ra, thay = [], {}
    for x in sorted(chu, key=lambda z: z["bd"]):
        tx = x["text"].upper()
        if not (re.search(r"\d", tx) or any(t in tx for t in THUAT_NGU_GIU)):
            continue
        if tx in thay and x["bd"] - thay[tx] < 90:
            continue
        thay[tx] = x["bd"]
        ra.append(x)
    return ra


def lap_chu_so_lieu(cau):
    """Chữ nhấn mạnh CHỈ cho con số / dữ kiện quan trọng: ChatGPT chọn, rồi bổ sung câu có chữ số mà nó bỏ sót."""
    chu = []
    for i in range(0, len(cau), 70):
        lot = cau[i:i + 70]
        log(f"[KH] chữ số liệu cho câu {lot[0]['i']}-{lot[-1]['i']}…")
        r = rut_json(hoi_llm(_P_SO_LIEU.format(ds=chr(10).join(f"{c['i']}. [{c['t0']:.0f}s] {c['text']}" for c in lot)),
                             timeout=300)) or []
        chu += [x for x in r if isinstance(x, dict) and x.get("text") and x.get("cau")]
    da = {int(x["cau"]) for x in chu}
    for c in cau:                                                # sót: câu có chữ số mà ChatGPT không chọn
        if c["i"] in da:
            continue
        m = _RX_SO.search(c["text"])
        if m:
            chu.append({"cau": c["i"], "text": (m.group(1) + " " + m.group(2)).upper(), "kieu": "so_lieu"})
    theo_i = {c["i"]: c for c in cau}
    ra, cuoi = [], -99.0
    for x in sorted(chu, key=lambda z: int(z["cau"])):
        c = theo_i.get(int(x["cau"]))
        if not c:
            continue
        tx = str(x["text"]).strip().upper()
        goc = c["text"].lower()
        vt = goc.find(tx.lower().split()[0]) if tx else -1
        t = c["t0"] + (c["t1"] - c["t0"]) * (max(vt, 0) / max(len(goc), 1)) + 0.1
        if t - cuoi < 2.5:                                       # không dồn chữ liên tiếp
            continue
        ra.append({"cau": c["i"], "text": tx, "kieu": x.get("kieu", "so_lieu"), "bd": round(t, 2),
                   "dai": round(max(1.8, min(2.8, c["t1"] - t + 0.7)), 2)})
        cuoi = t
    return loc_chu_so_lieu(ra)


CHU_CACH_TOI_THIEU = 6.0      # hai chữ nhấn mạnh cách nhau tối thiểu (giây)
CAU_MOI_DOAN = 20              # mỗi lần hỏi ChatGPT một đoạn nội dung ~20 câu

_P_NHAN_DOAN = """You are the editor of a Vietnamese documentary video. Below is ONE PASSAGE of the narration (sentence index. text).
Decide which words should be EMPHASISED ON SCREEN as text while the narrator says them — the words a viewer must catch to follow this passage: key numbers and amounts, the name of a species/place/organisation when it is first introduced, a key term, or the turning-point word of a dramatic sentence.
Rules:
- "cum" MUST be copied EXACTLY (same words, same order) from that sentence, 1-5 words. Never rewrite, translate or summarise.
- Pick only what really matters: about 1 emphasis per 4-6 sentences, never two in a row; skip the passage entirely if nothing stands out.
- No slogans, no full sentences, no generic words.
Return ONLY JSON: [{{"cau": <sentence index>, "cum": "<exact words from the sentence>"}}]

PASSAGE:
{ds}"""


def lap_chu_nhan(cau):
    """12/10 user: chữ nhấn mạnh do ChatGPT chọn THEO TỪNG ĐOẠN NỘI DUNG (~20 câu), cụm chép NGUYÊN VĂN từ câu,
    hiện đúng lúc giọng đọc tới cụm đó. Các đoạn hỏi song song (mỗi cookie một luồng)."""
    from common import hoi_nhieu
    lots = [cau[i:i + CAU_MOI_DOAN] for i in range(0, len(cau), CAU_MOI_DOAN)]
    log(f"[KH] chữ nhấn mạnh: hỏi ChatGPT {len(lots)} đoạn nội dung…")
    tra = hoi_nhieu([_P_NHAN_DOAN.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot)) for lot in lots],
                    timeout=240)
    theo_i = {c["i"]: c for c in cau}
    chu = []
    for r in tra:
        for x in (rut_json(r) or []):
            if not isinstance(x, dict):
                continue
            try:
                c = theo_i.get(int(x.get("cau", 0)))
            except (TypeError, ValueError):
                continue
            cum = str(x.get("cum", "")).strip().strip(".,;:!?\"'")
            if not c or not cum or len(cum.split()) > 6:
                continue
            vt = c["text"].lower().find(cum.lower())
            if vt < 0:                                        # không chép nguyên văn -> bỏ (tránh chữ sai lời)
                continue
            goc = c["text"]
            t = c["t0"] + (c["t1"] - c["t0"]) * (vt / max(len(goc), 1))
            chu.append({"cau": c["i"], "text": goc[vt:vt + len(cum)].upper(), "kieu": "nhan",
                        "bd": round(t, 2), "dai": round(max(1.8, min(2.8, c["t1"] - t + 0.6)), 2)})
    ra, cuoi = [], -1e9
    for x in sorted(chu, key=lambda z: z["bd"]):
        if x["bd"] - cuoi >= CHU_CACH_TOI_THIEU:
            ra.append(x)
            cuoi = x["bd"]
    log(f"    {len(ra)} chữ nhấn mạnh")
    return ra


def chu_dat(chu, tong_s):
    """Chỉ giữ chữ CÓ CON SỐ (loc_chu_so_lieu), cách nhau >= CHU_CACH_TOI_THIEU giây, tối đa ~1 chữ/phút."""
    ra, cuoi = [], -1e9
    for x in loc_chu_so_lieu(chu):
        if x["bd"] - cuoi >= CHU_CACH_TOI_THIEU:
            ra.append(x)
            cuoi = x["bd"]
    return ra[:max(1, int(tong_s // 60))]


def lap_ke_hoach(canh, cau, tong_s):
    rnd = random.Random(7)
    ds_ngan = chr(10).join(f"{c['i']}. {c['text'][:45]}" for c in cau)
    log("[KH] hỏi ChatGPT: chia chương + tâm trạng nhạc…")
    ch = rut_json(hoi_llm(_P_CHUONG.format(n=len(cau), ds=ds_ngan), timeout=300)) or []
    ch = [x for x in ch if isinstance(x, dict) and "tu_cau" in x and "den_cau" in x]
    if not ch or ch[0]["tu_cau"] != 1:
        log("    ! chia chương hỏng — chia đều 5 chương, nhạc điện ảnh")
        k = max(1, len(cau) // 5)
        ch = [{"tu_cau": i * k + 1, "den_cau": (i + 1) * k if i < 4 else len(cau), "ten": f"Phần {i + 1}",
               "tam_trang": "dien_anh"} for i in range(5)]
    chu, sfx_llm = [], []
    for i in (range(0, len(cau), 70) if SFX_BAT else []):
        lot = cau[i:i + 70]
        log(f"[KH] chữ nhấn mạnh + SFX cho câu {lot[0]['i']}-{lot[-1]['i']}…")
        r = rut_json(hoi_llm(_P_NHAN.format(ds=chr(10).join(f"{c['i']}. [{c['t0']:.0f}s] {c['text']}"
                                                              for c in lot)), timeout=300)) or {}
        chu += [x for x in r.get("chu", []) if isinstance(x, dict) and x.get("text")]
        sfx_llm += [x for x in r.get("sfx", []) if isinstance(x, dict)]
    theo_i = {c["i"]: c for c in cau}

    # chữ: thời điểm xuất hiện = lúc cụm đó được đọc (vị trí chữ trong câu)
    chu_ra = []
    cuoi = -99.0
    for x in sorted(chu, key=lambda z: int(z.get("cau", 0))):
        c = theo_i.get(int(x.get("cau", 0)))
        if not c:
            continue
        tx = str(x["text"]).strip()
        goc = c["text"].lower()
        vt = goc.find(tx.lower().split()[0]) if tx else -1
        t = c["t0"] + (c["t1"] - c["t0"]) * (max(vt, 0) / max(len(goc), 1)) + 0.1
        if t - cuoi < 3.5:
            continue                                        # không dồn chữ liên tiếp
        d = max(1.6, min(2.6, c["t1"] - t + 0.6))
        chu_ra.append({"cau": c["i"], "text": tx.upper(), "kieu": x.get("kieu", "y_chinh"),
                       "bd": round(t, 2), "dai": round(d, 2)})
        cuoi = t

    # chương -> thời gian + tâm trạng
    def thoi_gian_cau(i):
        return theo_i[min(max(i, 1), len(cau))]
    chuong = []
    for x in sorted(ch, key=lambda z: int(z["tu_cau"])):
        a, b = int(x["tu_cau"]), int(x["den_cau"])
        chuong.append({"tu_cau": a, "den_cau": b, "ten": x.get("ten", ""), "tam_trang": x.get("tam_trang", "dien_anh"),
                       "tu": thoi_gian_cau(a)["t0"], "den": (thoi_gian_cau(b)["t1"] if b < len(cau) else tong_s)})
    chuong[0]["tu"] = 0.0
    chuong[-1]["den"] = round(tong_s, 2)

    def chuong_cua_cau(i):
        for k, x in enumerate(chuong):
            if x["tu_cau"] <= i <= x["den_cau"]:
                return k
        return len(chuong) - 1

    chuyen, sfx_cung = chuyen_canh_theo_luat(canh, cau, chuong, theo_i, chuong_cua_cau, rnd)

    # SFX tinh gọn: chỉ whoosh đổi chương và tối đa điểm nhấn kịch tính thật sự (bỏ pop/ting tràn lan)
    sfx = list(sfx_cung)
    for x in sfx_llm:
        c = theo_i.get(int(x.get("cau", 0)))
        if c and x.get("kieu") == "hit":
            sfx.append({"t": round(c["t0"], 2), "kieu": "hit", "ly_do": f"câu {c['i']}"})
    sfx.sort(key=lambda z: z["t"])
    gon = []
    for s in sfx:                                           # không dồn hai SFX trong 3.0s
        if not gon or s["t"] - gon[-1]["t"] >= 3.0:
            gon.append(s)

    return {"tong_giay": round(tong_s, 2), "chuong": chuong, "chu": lap_chu_nhan(cau) if CHU_BAT else [], "chuyen_canh": chuyen, "sfx": gon,
            "ghi_chu": "Sửa tay file này rồi chạy lại với --giu-ke-hoach. Thời gian tính bằng giây."}


# --------------------------------------------------------------------------- chọn file âm thanh
def _kho_am_thanh():
    # Ưu tiên số 1: Kho âm thanh sạch không bản quyền (kho_am_thanh/)
    try:
        import kho_am_thanh
        chuan = kho_am_thanh.quet_kho_chuan()
        if chuan:
            return chuan
    except Exception as e:
        log(f"  ! Lỗi nạp kho_am_thanh: {e}")
    d = doc_json(os.path.join(kho_capcut.KHO, "am_thanh.json"))
    d = d if d else kho_capcut.quet_am_thanh()
    yt = doc_json(os.path.join(kho_capcut.KHO, "nhac_youtube.json"))
    if yt:                                                      # nhạc nền: kho YouTube thay cho nhạc trong cache CapCut
        d = {k: v for k, v in d.items() if v.get("loai") != "nhac"}
        d.update({"yt_" + k: v for k, v in yt.items()})
    return d


def chon_nhac(chuong, am):
    nhac = [v for v in am.values() if v["loai"] == "nhac"]
    if not nhac:
        return []
    da_dung, ra = set(), []

    # Gộp các chương ngắn (< 75s) hoặc cùng tâm trạng để nhạc không nhảy bài liên tục
    doan_nhac = []
    for x in chuong:
        if doan_nhac and (x["den"] - x["tu"] < 75.0 or doan_nhac[-1]["tam_trang"] == x.get("tam_trang")):
            doan_nhac[-1]["den"] = x["den"]
        else:
            doan_nhac.append({"tu": x["tu"], "den": x["den"], "tam_trang": x.get("tam_trang", "dien_anh")})

    for x in doan_nhac:
        can = x["den"] - x["tu"]
        t = x["tu"]
        ung = [v for v in nhac if v.get("tam_trang") == x["tam_trang"]] or nhac
        while t < x["den"] - 10.0:
            con = [v for v in ung if v["file"] not in da_dung] or [v for v in nhac if v["file"] not in da_dung] or nhac
            v = sorted(con, key=lambda z: -z["dai"])[0] if can > 120 else sorted(con, key=lambda z: abs(z["dai"] - can))[0]
            da_dung.add(v["file"])
            d = min(v["dai"] - 0.2, x["den"] - t)
            do_to = v.get("do_to_db", -15)
            # Âm lượng chuẩn tài liệu: ~ -24 dB (nhỏ hơn giọng đọc -14dB đúng 10dB)
            vol = round(max(0.06, min(0.22, 0.10 * 10 ** ((-24 - do_to) / 20))), 3)
            ra.append({"tu": round(t, 2), "den": round(t + d, 2), "file": v["file"], "tam_trang": v.get("tam_trang"),
                       "vol": vol})
            t += d
    return ra


def chon_sfx(sfx, am):
    # Chỉ giữ whoosh (chuyển cảnh) và hit (nhấn mạnh cao trào), loại bỏ pop/ting
    theo = {"whoosh": [], "hit": []}
    for v in am.values():
        if v["loai"] == "sfx":
            kieu = v.get("kieu")
            if kieu in ("whoosh", "hit"):
                theo[kieu].append(v)

    dem = {}
    ra = []
    cuoi_t = -99.0
    for s in sorted(sfx, key=lambda z: z["t"]):
        kieu = s.get("kieu")
        if kieu not in theo or not theo[kieu]:
            continue
        if s["t"] - cuoi_t < 2.5:
            continue
        k = dem.get(kieu, 0)
        dem[kieu] = k + 1
        ds = theo[kieu]
        v = sorted(ds, key=lambda z: z["file"])[k % len(ds)]
        s["file"] = v["file"]
        s["dai"] = min(v["dai"], 2.2)
        muc_tieu = -22 if kieu == "whoosh" else -16
        do_to = v.get("do_to_db", -18)
        s["vol"] = round(max(0.12, min(0.65, 0.35 * 10 ** ((muc_tieu - do_to) / 20))), 3)
        ra.append(s)
        cuoi_t = s["t"]
    return ra


# --------------------------------------------------------------------------- dựng dự án CapCut
def chuyen_dong_anh(seg, d, k, KP):
    """Keyframe chuyển động cho ảnh tĩnh: luân phiên phóng vào, thu ra, lia trái, lia phải, phóng vào lệch."""
    kieu = k % 5
    if kieu == 0:                                             # phóng vào giữa
        seg.add_keyframe(KP.uniform_scale, 0, 1.0)
        seg.add_keyframe(KP.uniform_scale, d - 1000, 1.18)
    elif kieu == 1:                                           # thu ra
        seg.add_keyframe(KP.uniform_scale, 0, 1.18)
        seg.add_keyframe(KP.uniform_scale, d - 1000, 1.0)
    elif kieu == 2:                                           # lia từ phải sang trái
        seg.add_keyframe(KP.uniform_scale, 0, 1.14)
        seg.add_keyframe(KP.position_x, 0, 0.06)
        seg.add_keyframe(KP.position_x, d - 1000, -0.06)
    elif kieu == 3:                                           # lia từ trái sang phải
        seg.add_keyframe(KP.uniform_scale, 0, 1.14)
        seg.add_keyframe(KP.position_x, 0, -0.06)
        seg.add_keyframe(KP.position_x, d - 1000, 0.06)
    else:                                                     # phóng vào kèm lia nhẹ lên
        seg.add_keyframe(KP.uniform_scale, 0, 1.05)
        seg.add_keyframe(KP.uniform_scale, d - 1000, 1.20)
        seg.add_keyframe(KP.position_y, 0, -0.03)
        seg.add_keyframe(KP.position_y, d - 1000, 0.03)


def chuyen_dong_anh_ai(seg, d, k, KP):
    """Chuyển động lia máy Ken Burns chậm rãi, điện ảnh cho chuỗi ảnh AI."""
    kieu = k % 4
    if kieu == 0:                                             # zoom in chậm rãi
        seg.add_keyframe(KP.uniform_scale, 0, 1.02)
        seg.add_keyframe(KP.uniform_scale, d - 1000, 1.08)
    elif kieu == 1:                                           # zoom out nhẹ nhàng
        seg.add_keyframe(KP.uniform_scale, 0, 1.08)
        seg.add_keyframe(KP.uniform_scale, d - 1000, 1.02)
    elif kieu == 2:                                           # lia chậm từ trái sang phải
        seg.add_keyframe(KP.uniform_scale, 0, 1.06)
        seg.add_keyframe(KP.position_x, 0, -0.025)
        seg.add_keyframe(KP.position_x, d - 1000, 0.025)
    else:                                                     # đẩy nhẹ vào kèm lia góc
        seg.add_keyframe(KP.uniform_scale, 0, 1.03)
        seg.add_keyframe(KP.uniform_scale, d - 1000, 1.07)
        seg.add_keyframe(KP.position_x, 0, 0.02)
        seg.add_keyframe(KP.position_x, d - 1000, -0.02)


def dung_du_an(canh, kh, ten, giong_chung=None, tong_s=0.0):
    """giong_chung: dự án kiểu mới — một file giọng nguyên bài (giong_doc.wav) đặt từ giây 0."""
    import pycapcut as draft
    from pycapcut import trange
    dd = thu_muc_nhap_capcut()
    folder = draft.DraftFolder(dd)
    script = folder.create_draft(ten, ghep.W, ghep.H, allow_replace=True)
    for nm, tp in (("hinh", draft.TrackType.video), ("giong", draft.TrackType.audio), ("nhac", draft.TrackType.audio),
                   ("sfx", draft.TrackType.audio), ("chu", draft.TrackType.text)):
        if (nm == "sfx" and not kh["sfx"]) or (nm == "nhac" and not kh["nhac"]) or (nm == "chu" and not kh["chu"]):
            continue
        script.add_track(tp, track_name=nm)
    if kh.get("anh_ai"):
        script.add_track(draft.TrackType.video, track_name="anh_ai", relative_index=1)
    if kh.get("hieu_ung"):
        script.add_track(draft.TrackType.video, track_name="hieu_ung", relative_index=2)  # trên track anh_ai
    if kh.get("bang_giay"):
        script.add_track(draft.TrackType.video, track_name="bang_giay", relative_index=4)  # trên cùng: khối bảng giấy
    man_den = [c for c in canh if float(c.get("nghi_sau") or 0) > 0]
    if man_den:                                             # 14/10 user: chỗ (nghỉ X) -> chuyển cảnh ĐEN MÀN, track trên cùng
        script.add_track(draft.TrackType.video, track_name="man_den", relative_index=9)
    if kh.get("tieng_dong") and TIENG_DONG_BAT:
        script.add_track(draft.TrackType.audio, track_name="tieng_dong")
    if kh.get("lop_phu"):
        script.add_track(draft.TrackType.video, track_name="lop_phu", relative_index=5)   # thẻ: ảnh thật
        script.add_track(draft.TrackType.video, track_name="lop_phu_khung", relative_index=6)   # thẻ: khung trắng
        script.add_track(draft.TrackType.text, track_name="lop_phu_chu", relative_index=1)   # thẻ: chữ (sửa tay được)
    KP0 = draft.KeyframeProperty
    kieu_anh = 0
    vat_lieu = {}
    for c in canh:
        for (t, d, o) in c["_os"]:
            if o["clip"] not in vat_lieu:
                vat_lieu[o["clip"]] = draft.VideoMaterial(o["clip"])
            mat = vat_lieu[o["clip"]]
            if o.get("vao") is not None and not o.get("anh"):   # dự án mới: trỏ VIDEO GỐC, chọn lại đoạn trong CapCut được
                vao = int(round(o["vao"] * SEC))
                d = min(d, int(mat.duration) - vao - 1000)
                ph = float(o.get("phong") or 1.0)               # logo ở góc -> phóng to giấu logo
                vs = draft.VideoSegment(mat, trange(t, d), source_timerange=trange(vao, d), volume=0.0,
                                        clip_settings=draft.ClipSettings(scale_x=ph, scale_y=ph) if ph > 1.0 else None)
            else:
                vs = draft.VideoSegment(mat, trange(t, d))
            if o.get("anh"):                                  # MỌI ẢNH đều có chuyển động (yêu cầu của người dùng)
                chuyen_dong_anh(vs, d, kieu_anh, KP0)
                kieu_anh += 1
            script.add_segment(vs, track_name="hinh")
        if not giong_chung and c.get("giong") and c["_os"]:
            ad = min(int(c["giong_dai"] * SEC), c["_t1"] - c["_t0"])
            if ad > 0:
                script.add_segment(draft.AudioSegment(draft.AudioMaterial(c["giong"]), trange(c["_t0"], ad)),
                                   track_name="giong")
    if giong_chung:
        gm = draft.AudioMaterial(giong_chung)
        script.add_segment(draft.AudioSegment(gm, trange(0, int(gm.duration) - 1000)), track_name="giong")
    for m in kh["nhac"]:
        mat = draft.AudioMaterial(m["file"])
        d = min(int((m["den"] - m["tu"]) * SEC), mat.duration)
        seg = draft.AudioSegment(mat, trange(int(m["tu"] * SEC), d), source_timerange=trange(0, d), volume=m["vol"])
        seg.add_fade(int(2.0 * SEC), int(2.5 * SEC))
        script.add_segment(seg, track_name="nhac")
    ds_sfx = sorted(kh["sfx"], key=lambda z: z["t"])
    cuoi_sfx = 0
    for k, s in enumerate(ds_sfx):
        st = int(s["t"] * SEC)
        if st < cuoi_sfx + int(0.1 * SEC):
            continue
        toi_da = (ds_sfx[k + 1]["t"] - s["t"] - 0.08) if k + 1 < len(ds_sfx) else s["dai"]
        mat = draft.AudioMaterial(s["file"])
        d = min(int(min(s["dai"], toi_da) * SEC), mat.duration)   # vừa khoảng trống VÀ không quá độ dài thật của file
        if d < int(0.2 * SEC):
            continue
        seg = draft.AudioSegment(mat, trange(st, d), source_timerange=trange(0, d), volume=s["vol"])
        if d < int(s["dai"] * SEC):
            seg.add_fade(0, int(min(0.15 * SEC, d // 2)))
        script.add_segment(seg, track_name="sfx")
        cuoi_sfx = st + d
    if man_den:
        from PIL import Image
        den = os.path.join(OUT, "_man_den.png")
        if not os.path.isfile(den):
            Image.new("RGB", (1920, 1080), (0, 0, 0)).save(den)
        KPd = draft.KeyframeProperty
        mep = 0.3 + DEN_THEM                                    # 15/10 user: mỗi bên thêm 1 s (che chỗ chuyển cảnh mượt hơn)
        for c in man_den:
            x = float(c["nghi_sau"])
            het = float(c["bat_dau"]) + float(c["dai"])            # hết cảnh = lúc cảnh sau bắt đầu
            bd, d = het - x - mep, x + 2 * mep                  # tối dần trước quãng nghỉ, đen hẳn trong quãng nghỉ, sáng lại sau
            lech = max(0.0, -bd)                                 # chỗ nghỉ sát đầu video: bỏ phần trước giây 0
            bd, d = bd + lech, d - lech
            di = int(d * SEC)
            seg = draft.VideoSegment(draft.VideoMaterial(den), trange(int(bd * SEC), di))
            seg.add_keyframe(KPd.alpha, 0, 0.0 if lech < mep else 1.0)
            seg.add_keyframe(KPd.alpha, int(max(0.0, mep + x * 0.5 - lech) * SEC), 1.0)
            seg.add_keyframe(KPd.alpha, int(max(0.0, mep + x - lech) * SEC), 1.0)
            seg.add_keyframe(KPd.alpha, di - 1000, 0.0)
            script.add_segment(seg, track_name="man_den")
        log(f"    màn đen chuyển cảnh: {len(man_den)} chỗ nghỉ")
    ds_td = sorted(kh.get("tieng_dong") or [], key=lambda z: z["t"]) if TIENG_DONG_BAT else []
    for k, s in enumerate(ds_td):                            # tiếng động diễn cảnh (13/10 user)
        toi_da = (ds_td[k + 1]["t"] - s["t"] - 0.05) if k + 1 < len(ds_td) else s["dai"]
        mat = draft.AudioMaterial(s["file"])
        d = min(int(min(s["dai"], toi_da) * SEC), mat.duration)
        if d < int(0.15 * SEC):
            continue
        seg = draft.AudioSegment(mat, trange(int(s["t"] * SEC), d), source_timerange=trange(0, d), volume=s["vol"])
        if d < int(float(s.get("dai_goc", s["dai"])) * SEC):
            seg.add_fade(0, int(min(0.12 * SEC, d // 2)))
        script.add_segment(seg, track_name="tieng_dong")
    KP = draft.KeyframeProperty
    for x in kh["chu"]:
        d = int(x["dai"] * SEC)
        seg = draft.TextSegment(
            so_hien_thi.doi(x["text"]).upper(), trange(int(x["bd"] * SEC), d),   # số viết chữ -> chữ số khi hiện
            style=draft.TextStyle(size=16.0, bold=True, color=(1.0, 0.84, 0.1), align=1, auto_wrapping=True,
                                  max_line_width=0.8),
            border=draft.TextBorder(color=(0.0, 0.0, 0.0), width=60.0),
            clip_settings=draft.ClipSettings(transform_y=-0.55))
        seg.add_keyframe(KP.uniform_scale, 0, 0.55)               # nảy vào: nhỏ -> hơi quá -> vừa
        seg.add_keyframe(KP.uniform_scale, int(0.18 * SEC), 1.12)
        seg.add_keyframe(KP.uniform_scale, int(0.32 * SEC), 1.0)
        seg.add_keyframe(KP.alpha, 0, 0.0)
        seg.add_keyframe(KP.alpha, int(0.12 * SEC), 1.0)
        seg.add_keyframe(KP.alpha, max(d - int(0.25 * SEC), int(0.4 * SEC)), 1.0)
        seg.add_keyframe(KP.alpha, d - 1000, 0.0)
        script.add_segment(seg, track_name="chu")
    if kh.get("anh_ai"):
        ds_pd = []
        for x in kh["anh_ai"]:
            for pd in x.get("phan_doan", []):
                f_anh = pd["file"]
                if os.path.isfile(f_anh) and os.path.getsize(f_anh) > 5000:
                    ds_pd.append({"bd": pd["bd"], "dai": pd["dai"], "file": f_anh})
        ds_pd.sort(key=lambda z: z["bd"])
        cuoi_ai = 0
        k_anh_ai = 0
        for pd in ds_pd:
            st = int(round(pd["bd"] * SEC))
            d = int(round(pd["dai"] * SEC))
            if st < cuoi_ai:
                lech = cuoi_ai - st
                st = cuoi_ai
                d -= lech
            if d < int(0.5 * SEC):
                continue
            mat = draft.VideoMaterial(pd["file"])
            seg = draft.VideoSegment(mat, trange(st, d), volume=0.0)
            chuyen_dong_anh_ai(seg, d, k_anh_ai, KP)
            script.add_segment(seg, track_name="anh_ai")
            cuoi_ai = st + d
            k_anh_ai += 1
    if kh.get("hieu_ung"):
        import hieu_ung
        hieu_ung.dat(script, kh["hieu_ung"], SEC)
    if kh.get("lop_phu"):
        import lop_phu
        lop_phu.dat(script, kh["lop_phu"], SEC)
    if kh.get("bang_giay"):
        import bang_giay
        bang_giay.dat(script, kh["bang_giay"], SEC)
    script.save()
    if giong_chung:
        import dung_tay
        dung_tay._sua_nhap(os.path.join(dd, ten), list(vat_lieu))   # noqa: SLF001  (tắt hút + video gốc vào Phương tiện)
    return os.path.join(dd, ten)


def gan_chuyen_canh(thu_muc, kh):
    """pycapcut không biết mã chuyển cảnh của CapCut hiện tại -> ghi thẳng JSON, kèm cài gói tài nguyên."""
    p = os.path.join(thu_muc, "draft_content.json")
    j = json.load(open(p, encoding="utf-8"))
    video = next(t for t in j["tracks"] if t["type"] == "video")
    segs = sorted(video["segments"], key=lambda s: s["target_timerange"]["start"])
    dm = {it["id"]: it for it in doc_json(os.path.join(kho_capcut.KHO, "danh_muc.json"))["chuyen_canh"]}
    j["materials"].setdefault("transitions", [])
    n = 0
    for ch in kh["chuyen_canh"]:
        if ch["sau_o"] >= len(segs) - 1:
            continue
        it = dm.get(ch["id"])
        if not it:
            continue
        try:
            duong = kho_capcut.cai_goi(it).replace("\\", "/")
        except Exception as e:                                         # noqa: BLE001
            log(f"    ! không cài được chuyển cảnh '{it['ten']}': {e}")
            continue
        a, b = segs[ch["sau_o"]], segs[ch["sau_o"] + 1]
        dai = int(min(ch["dai"] * SEC, 0.8 * min(a["target_timerange"]["duration"], b["target_timerange"]["duration"])))
        tid = str(uuid.uuid4()).upper()
        j["materials"]["transitions"].append({
            "id": tid, "type": "transition", "name": it["ten"], "effect_id": it["id"], "resource_id": it["id"],
            "third_resource_id": it["id"], "source_platform": 1, "path": duong, "duration": dai, "is_overlap": True,
            "platform": "all", "category_id": "100000", "category_name": "", "request_id": "",
            "is_ai_transition": False, "video_path": "", "task_id": ""})
        a.setdefault("extra_material_refs", []).append(tid)
        n += 1

    # 18/10 user: gắn chuyển cảnh 'Mờ dần' (Mix/Dissolve) giữa các ảnh AI liền kề trên track 'anh_ai'
    track_ai = next((t for t in j["tracks"] if t.get("name") == "anh_ai"), None)
    if track_ai and len(track_ai.get("segments", [])) > 1:
        it_mo = dm.get("6798320902548230669")  # Mờ dần (Dissolve)
        if it_mo:
            try:
                duong_mo = kho_capcut.cai_goi(it_mo).replace("\\", "/")
                segs_ai = sorted(track_ai["segments"], key=lambda s: s["target_timerange"]["start"])
                n_ai_trans = 0
                for i in range(len(segs_ai) - 1):
                    seg_a = segs_ai[i]
                    seg_b = segs_ai[i + 1]
                    end_a = seg_a["target_timerange"]["start"] + seg_a["target_timerange"]["duration"]
                    start_b = seg_b["target_timerange"]["start"]
                    # Chỉ gắn nếu 2 ảnh liền kề (khoảng cách <= 0.06s)
                    if abs(start_b - end_a) <= 60000:
                        dai_trans = int(min(0.5 * SEC, 0.4 * min(seg_a["target_timerange"]["duration"], seg_b["target_timerange"]["duration"])))
                        tid = str(uuid.uuid4()).upper()
                        j["materials"]["transitions"].append({
                            "id": tid, "type": "transition", "name": it_mo["ten"], "effect_id": it_mo["id"],
                            "resource_id": it_mo["id"], "third_resource_id": it_mo["id"], "source_platform": 1,
                            "path": duong_mo, "duration": dai_trans, "is_overlap": True,
                            "platform": "all", "category_id": "100000", "category_name": "", "request_id": "",
                            "is_ai_transition": False, "video_path": "", "task_id": ""
                        })
                        seg_a.setdefault("extra_material_refs", []).append(tid)
                        n_ai_trans += 1
                if n_ai_trans:
                    log(f"    chuyển cảnh ảnh AI: gắn {n_ai_trans} hiệu ứng 'Mờ dần'")
            except Exception as e:
                log(f"    ! lỗi gắn chuyển cảnh ảnh AI: {e}")

    json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return n


def doi_chuyen_canh_nhay(kh):
    """Thay các chuyển cảnh trong BO_NHAY (đã đo là gây nháy) bằng chuyển cảnh sạch, luân phiên."""
    dm = doc_json(os.path.join(kho_capcut.KHO, "danh_muc.json"))
    mf = {}
    for it in dm.get("chuyen_canh", []):
        if not it["vip"] and it["md5"]:
            mf.setdefault(it["ten"], it)
    nhe = [mf[n] for n in MILD if n in mf]
    n = 0
    for ch in kh["chuyen_canh"]:
        if ch["ten"] in BO_NHAY and nhe:
            it = nhe[n % len(nhe)]
            ch.update({"ten": it["ten"], "id": it["id"], "dai": 0.5 if ch.get("manh") else 0.4})
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ten", default="Chim canh cut - ban tho v6 hoan chinh")
    ap.add_argument("--giu-ke-hoach", action="store_true", help="dùng ra/ke_hoach.json đã có (đã sửa tay)")
    ap.add_argument("--du-an", default=None, help="tên dự án (mặc định: dự án chạy gần nhất)")
    ap.add_argument("--chi-lap-ke-hoach", action="store_true")
    ap.add_argument("--co-ban-do-canh", action="store_true",
                    help="kiểu cũ: thay đoạn đầu MỌI cảnh địa điểm bằng bản đồ vệ tinh (mặc định tắt từ 14/10)")
    ap.add_argument("--khong-ban-do", action="store_true", help="dự án mới: không thay cảnh địa điểm bằng bản đồ vệ tinh")
    ap.add_argument("--co-nhac", action="store_true", help="bật lại tự thêm nhạc nền")
    ap.add_argument("--co-sfx", action="store_true", help="bật lại SFX chuyển cảnh & điểm nhấn tinh gọn")
    ap.add_argument("--khong-sfx", action="store_true", help="không thêm SFX")
    ap.add_argument("--co-chu", action="store_true", help="bật lại chữ nhấn mạnh")
    ap.add_argument("--khong-dieu-phoi", action="store_true", help="không dùng điều phối chung (thẻ/bản đồ hỏi riêng như cũ)")
    ap.add_argument("--khong-nhac", action="store_true", help="không thêm nhạc nền")
    ap.add_argument("--co-lop-phu", action="store_true", help="bật lại thẻ ảnh highlight (mặc định tắt từ 13/10)")
    ap.add_argument("--khong-lop-phu", action="store_true", help="không thêm lớp ảnh phủ minh hoạ")
    ap.add_argument("--khong-hieu-ung", action="store_true", help="không thêm bản đồ đường đi / highlight / phủ màu")
    ap.add_argument("--khong-bang-giay", action="store_true", help="không dựng lớp Remotion bảng giấy")
    ap.add_argument("--co-bang-giay", action="store_true", help="bật lớp Remotion bảng giấy (mặc định tắt)")
    ap.add_argument("--bang-giay-den", type=float, default=None, help="bảng giấy chỉ làm tới giây này (bản thử)")
    ap.add_argument("--khong-tieng-dong", action="store_true", help="không thêm tiếng động diễn cảnh / SFX minh hoạ")
    ap.add_argument("--co-tieng-dong", action="store_true", help="bật tiếng động diễn cảnh")
    ap.add_argument("--sua-nhanh", action="store_true",
                    help="giữ kế hoạch: bỏ SFX, làm lại chữ (chỉ số liệu/dữ kiện) và chọn lại nhạc từ kho sạch")
    ap.add_argument("--tinh-lai-chuyen-canh", action="store_true",
                    help="giữ kế hoạch cũ, chỉ dựng lại chuyển cảnh theo các ô hình hiện tại")
    a = ap.parse_args()
    global NHAC_BAT, SFX_BAT, CHU_BAT, LOP_PHU_BAT, HIEU_UNG_BAT, BANG_GIAY_BAT, DIEU_PHOI_BAT, TIENG_DONG_BAT
    TIENG_DONG_BAT = (TIENG_DONG_BAT or a.co_tieng_dong) and not a.khong_tieng_dong
    DIEU_PHOI_BAT = DIEU_PHOI_BAT and not a.khong_dieu_phoi
    BANG_GIAY_BAT = (BANG_GIAY_BAT or a.co_bang_giay) and not a.khong_bang_giay
    HIEU_UNG_BAT = HIEU_UNG_BAT and not a.khong_hieu_ung
    NHAC_BAT = (NHAC_BAT or a.co_nhac) and not a.khong_nhac
    SFX_BAT = (SFX_BAT or a.co_sfx) and not a.khong_sfx
    CHU_BAT = CHU_BAT or a.co_chu
    LOP_PHU_BAT = (LOP_PHU_BAT or a.co_lop_phu) and not a.khong_lop_phu

    giong_chung = None
    if not os.path.isfile(os.path.join(OUT, "ket_qua.json")) and os.path.isfile(os.path.join(OUT, "dung.json")):
        import du_an_moi                                    # dự án kiểu mới (trình dựng tay / nút 🤖)
        from common import DU_AN
        # 14/10 user: không gò mọi địa điểm vào vệ tinh phóng từ trên cao -> mặc định KHÔNG tự thay; ChatGPT (điều phối)
        # chọn: vệ tinh khi lời dừng lâu ở nơi đó, bản đồ AI vẽ khi chỉ nhắc nhanh. Bật lại kiểu cũ: --co-ban-do-canh
        canh, giong_chung, tong = du_an_moi.tai(DU_AN, ban_do=a.co_ban_do_canh and not a.khong_ban_do)
    else:
        canh = json.load(open(os.path.join(OUT, "ket_qua.json"), encoding="utf-8"))
        tong = dong_thoi_gian(canh) / SEC
    cau = tao_srt(canh)
    ghi_srt(cau, os.path.join(OUT, "kich_ban_cau.srt"))
    log(f"[1] dự án thô: {len(canh)} cảnh, {sum(len(c['_os']) for c in canh)} đoạn hình, {tong:.0f}s; "
        f"{len(cau)} câu -> ra/kich_ban_cau.srt")

    am = _kho_am_thanh()
    if (a.giu_ke_hoach or a.tinh_lai_chuyen_canh or a.sua_nhanh) and os.path.isfile(KE_HOACH):
        kh = json.load(open(KE_HOACH, encoding="utf-8"))
        log("[2] dùng kế hoạch đã có")
        if a.sua_nhanh:
            kh["chu"] = lap_chu_nhan(cau) if CHU_BAT else []
            kh["sfx"] = []
            kh["nhac"] = chon_nhac(kh["chuong"], am) if NHAC_BAT else []
            ghi_json(KE_HOACH, kh)
            log(f"    kế hoạch sửa: {len(kh['chu'])} chữ số liệu, 0 SFX, {len(kh['nhac'])} đoạn nhạc (kho YouTube)")
        if a.tinh_lai_chuyen_canh:
            kh = tinh_lai_chuyen_canh(canh, cau, kh)
            ghi_json(KE_HOACH, kh)
            log(f"    dựng lại {len(kh['chuyen_canh'])} chuyển cảnh theo ô hiện tại")
        if NHAC_BAT and not kh.get("nhac"):
            if NHAC_NGUON == "mixkit":
                import nhac_mixkit
                kh["nhac"] = nhac_mixkit.chon(kh["chuong"], cau, OUT)
            else:
                kh["nhac"] = chon_nhac(kh["chuong"], am)
            ghi_json(KE_HOACH, kh)
        if SFX_BAT and not kh.get("sfx"):
            kh["sfx"] = chon_sfx(kh.get("sfx") or [], am)
            ghi_json(KE_HOACH, kh)
        doi = doi_chuyen_canh_nhay(kh)
        if doi:
            log(f"    đã thay {doi} chuyển cảnh gây nháy bằng chuyển cảnh sạch")
    else:
        kh = lap_ke_hoach(canh, cau, tong)
        if NHAC_BAT and NHAC_NGUON == "mixkit":
            import nhac_mixkit
            kh["nhac"] = nhac_mixkit.chon(kh["chuong"], cau, OUT)
        else:
            kh["nhac"] = chon_nhac(kh["chuong"], am) if NHAC_BAT else []
        if BANG_GIAY_BAT:
            import bang_giay
            kh["bang_giay"] = bang_giay.lap(cau, canh, OUT, den_giay=a.bang_giay_den)
        bg = [(y["bd"], y["bd"] + y["dai"]) for y in kh.get("bang_giay") or []]

        def ngoai_bg(x):                                     # hiệu ứng/thẻ ảnh không trùng khoảng đã có khối bảng giấy
            return all(x["bd"] + x["dai"] <= a_ or x["bd"] >= b_ for a_, b_ in bg)
        # 13/10 user: MỘT lần hỏi ChatGPT chọn cho mỗi câu tối đa một lớp: thẻ highlight / bản đồ / sơ đồ Remotion
        de = None
        if DIEU_PHOI_BAT and (HIEU_UNG_BAT or LOP_PHU_BAT):
            import dieu_phoi
            de = dieu_phoi.hoi(cau, OUT, co_the=LOP_PHU_BAT)
        if HIEU_UNG_BAT:
            import hieu_ung
            if de is not None:
                import minh_hoa
                san_hu, san_ai = minh_hoa.lap(cau, canh, de)
                kh["hieu_ung"] = [x for x in hieu_ung.lap(cau, canh, kh["chuong"], OUT, san=san_hu)
                                  if ngoai_bg(x)]
                kh["anh_ai"] = [x for x in san_ai if ngoai_bg(x)]
            else:
                kh["hieu_ung"] = [x for x in hieu_ung.lap(cau, canh, kh["chuong"], OUT) if ngoai_bg(x)]
                kh["anh_ai"] = []
        # 13/10 user: tiếng động đi kèm diễn cảnh (độc lập với SFX_BAT cũ đã tắt)
        su_kien_hu = [a_ for y in (kh.get("hieu_ung") or []) for a_ in (y.get("am") or [])]
        su_kien_ai = [a_ for y in (kh.get("anh_ai") or []) for a_ in (y.get("am") or [])]
        su_kien = sorted(su_kien_hu + su_kien_ai, key=lambda z: z["t"])
        kh["tieng_dong"] = []
        for s_ in chon_sfx([dict(z) for z in su_kien], am):
            s_["dai_goc"] = float(s_["dai"])
            s_["dai"] = min(float(s_["dai"]), 1.6)
            s_["vol"] = round(float(s_["vol"]) * 0.6, 3)            # nhỏ hơn giọng đọc
            kh["tieng_dong"].append(s_)
        if LOP_PHU_BAT:
            import lop_phu
            cam = [(y["bd"], y["bd"] + y["dai"]) for y in kh.get("hieu_ung") or [] if y["kieu"] != "phu_mau"]
            cam += [(t / SEC, (t + d) / SEC) for c in canh for (t, d, o) in c["_os"] if o.get("ban_do")]
            kh["lop_phu"] = lop_phu.lap(cau, OUT, de_xuat=de, cam=cam)
            hu = [(y["bd"], y["bd"] + y["dai"]) for y in kh.get("hieu_ung") or [] if y["kieu"] != "phu_mau"]
            kh["lop_phu"] = [x for x in kh["lop_phu"]                          # thẻ ảnh không đè lên bản đồ/highlight
                             if all(x["bd"] + x["dai"] <= a or x["bd"] >= b for a, b in hu) and ngoai_bg(x)]
        kh["sfx"] = chon_sfx(kh["sfx"], am) if SFX_BAT else []
        ghi_json(KE_HOACH, kh)
        log(f"[2] kế hoạch: {len(kh['chuong'])} chương, {len(kh['chu'])} chữ nhấn mạnh, {len(kh.get('lop_phu') or [])} ảnh phủ, "
            f"{len(kh.get('hieu_ung') or [])} hiệu ứng, {len(kh.get('anh_ai') or [])} cảnh AI ({sum(len(y.get('phan_doan') or []) for y in kh.get('anh_ai') or [])} ảnh), "
            f"{len(kh.get('bang_giay') or [])} khối bảng giấy, {len(kh['chuyen_canh'])} chuyển cảnh, {len(kh['nhac'])} đoạn nhạc, "
            f"{len(kh['sfx'])} SFX, {len(kh.get('tieng_dong') or [])} tiếng động diễn cảnh -> ra/ke_hoach.json")
    if a.chi_lap_ke_hoach:
        return
    if not SFX_BAT:
        kh["sfx"] = []
    if not NHAC_BAT:
        kh["nhac"] = []
    if not CHU_BAT:
        kh["chu"] = []
    thu_muc = dung_du_an(canh, kh, a.ten, giong_chung, tong)
    n = gan_chuyen_canh(thu_muc, kh)
    try:                                                    # 13/10 user: 2 dòng chữ mẫu (chu_mau.json) trên mọi bản nháp
        import chu_mau
        n_chu = chu_mau.gan(thu_muc)
        if n_chu:
            log(f"    chữ mẫu: gắn {n_chu} dòng")
    except Exception as e:                                  # noqa: BLE001
        log(f"    ! gắn chữ mẫu lỗi: {e}")
    log(f"[3] dự án CapCut: {thu_muc}  (chuyển cảnh gắn được: {n}/{len(kh['chuyen_canh'])})")


if __name__ == "__main__":
    main()
