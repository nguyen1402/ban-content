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

SEC = 1_000_000
#: Người dùng chốt 09/10: BỎ hết hiệu ứng âm thanh (chỗ chèn không hợp). Mã SFX còn đó, bật lại bằng True.
SFX_BAT = False
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
                            "t1": round(c["_t0"] / SEC + moc[j + nt - 1][1], 2), "text": s, "canh": c["id"]})
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
    for i in range(0, len(cau), 70):
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

    # SFX: theo gợi ý của ChatGPT + khi chữ nhấn mạnh hiện
    sfx = list(sfx_cung)
    for x in sfx_llm:
        c = theo_i.get(int(x.get("cau", 0)))
        if c and x.get("kieu") in ("hit", "ting", "riser", "whoosh", "pop"):
            t = c["t0"] if x["kieu"] != "riser" else max(0.0, c["t0"] - 1.0)
            sfx.append({"t": round(t, 2), "kieu": x["kieu"], "ly_do": f"câu {c['i']}"})
    for x in chu_ra:
        sfx.append({"t": x["bd"], "kieu": "pop" if x["kieu"] in ("ten", "y_chinh") else "hit", "ly_do": "chữ nhấn mạnh"})
    sfx.sort(key=lambda z: z["t"])
    gon = []
    for s in sfx:                                           # không dồn hai SFX trong 1,2s
        if not gon or s["t"] - gon[-1]["t"] >= 1.2:
            gon.append(s)

    return {"tong_giay": round(tong_s, 2), "chuong": chuong, "chu": chu_ra, "chuyen_canh": chuyen, "sfx": gon,
            "ghi_chu": "Sửa tay file này rồi chạy lại với --giu-ke-hoach. Thời gian tính bằng giây."}


# --------------------------------------------------------------------------- chọn file âm thanh
def _kho_am_thanh():
    d = doc_json(os.path.join(kho_capcut.KHO, "am_thanh.json"))
    d = d if d else kho_capcut.quet_am_thanh()
    yt = doc_json(os.path.join(kho_capcut.KHO, "nhac_youtube.json"))
    if yt:                                                      # nhạc nền: kho YouTube thay cho nhạc trong cache CapCut
        d = {k: v for k, v in d.items() if v.get("loai") != "nhac"}
        d.update({"yt_" + k: v for k, v in yt.items()})
    return d


def chon_nhac(chuong, am):
    nhac = [v for v in am.values() if v["loai"] == "nhac"]
    da_dung, ra = set(), []
    for x in chuong:
        can = x["den"] - x["tu"]
        t = x["tu"]
        ung = [v for v in nhac if v.get("tam_trang") == x["tam_trang"]] or nhac
        while t < x["den"] - 8.0:                              # chỗ trống <8s thì để nhạc cũ tắt dần, không chèn bài mới
            con = [v for v in ung if v["file"] not in da_dung] or [v for v in nhac if v["file"] not in da_dung] or nhac
            v = sorted(con, key=lambda z: -z["dai"])[0] if can > 120 else sorted(con, key=lambda z: abs(z["dai"] - can))[0]
            da_dung.add(v["file"])
            d = min(v["dai"] - 0.2, x["den"] - t)
            ra.append({"tu": round(t, 2), "den": round(t + d, 2), "file": v["file"], "tam_trang": v.get("tam_trang"),
                       "vol": round(max(0.05, min(0.2, 0.11 * 10 ** ((-20 - v.get("do_to_db", -20)) / 20))), 3)})
            t += d
    return ra


def chon_sfx(sfx, am):
    khoang = {"whoosh": (0.4, 2.6), "hit": (0.3, 3.0), "ting": (0.3, 3.0), "riser": (1.0, 6.0), "pop": (0.0, 0.8)}
    theo = {}
    for v in am.values():
        if v["loai"] == "sfx" and v.get("kieu") in khoang:
            lo, hi = khoang[v["kieu"]]
            if lo <= v["dai"] <= hi:
                theo.setdefault(v["kieu"], []).append(v)
    dem = {}
    for s in sfx:
        ds = theo.get(s["kieu"]) or []
        if not ds:
            s["bo"] = True
            continue
        k = dem.get(s["kieu"], 0)
        dem[s["kieu"]] = k + 1
        v = sorted(ds, key=lambda z: z["file"])[k % len(ds)]
        s["file"], s["dai"] = v["file"], v["dai"]
        s["vol"] = round(max(0.15, min(1.0, 0.5 * 10 ** ((-18 - v.get("do_to_db", -18)) / 20))), 3)
    return [s for s in sfx if not s.get("bo")]


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


def dung_du_an(canh, kh, ten):
    import pycapcut as draft
    from pycapcut import trange
    dd = thu_muc_nhap_capcut()
    folder = draft.DraftFolder(dd)
    script = folder.create_draft(ten, ghep.W, ghep.H, allow_replace=True)
    for nm, tp in (("hinh", draft.TrackType.video), ("giong", draft.TrackType.audio), ("nhac", draft.TrackType.audio),
                   ("sfx", draft.TrackType.audio), ("chu", draft.TrackType.text)):
        if nm == "sfx" and not kh["sfx"]:
            continue
        script.add_track(tp, track_name=nm)
    KP0 = draft.KeyframeProperty
    kieu_anh = 0
    for c in canh:
        for (t, d, o) in c["_os"]:
            vs = draft.VideoSegment(draft.VideoMaterial(o["clip"]), trange(t, d))
            if o.get("anh"):                                  # MỌI ẢNH đều có chuyển động (yêu cầu của người dùng)
                chuyen_dong_anh(vs, d, kieu_anh, KP0)
                kieu_anh += 1
            script.add_segment(vs, track_name="hinh")
        if c.get("giong") and c["_os"]:
            ad = min(int(c["giong_dai"] * SEC), c["_t1"] - c["_t0"])
            if ad > 0:
                script.add_segment(draft.AudioSegment(draft.AudioMaterial(c["giong"]), trange(c["_t0"], ad)),
                                   track_name="giong")
    for m in kh["nhac"]:
        mat = draft.AudioMaterial(m["file"])
        d = min(int((m["den"] - m["tu"]) * SEC), mat.duration)
        seg = draft.AudioSegment(mat, trange(int(m["tu"] * SEC), d), source_timerange=trange(0, d), volume=m["vol"])
        seg.add_fade(int(1.5 * SEC), int(1.8 * SEC))
        script.add_segment(seg, track_name="nhac")
    ds_sfx = sorted(kh["sfx"], key=lambda z: z["t"])
    for k, s in enumerate(ds_sfx):
        toi_da = (ds_sfx[k + 1]["t"] - s["t"] - 0.05) if k + 1 < len(ds_sfx) else s["dai"]
        mat = draft.AudioMaterial(s["file"])
        d = min(int(min(s["dai"], toi_da) * SEC), mat.duration)   # vừa khoảng trống VÀ không quá độ dài thật của file
        if d < int(0.2 * SEC):
            continue
        seg = draft.AudioSegment(mat, trange(int(s["t"] * SEC), d), source_timerange=trange(0, d), volume=s["vol"])
        if d < int(s["dai"] * SEC):
            seg.add_fade(0, int(min(0.15 * SEC, d // 2)))
        script.add_segment(seg, track_name="sfx")
    KP = draft.KeyframeProperty
    for x in kh["chu"]:
        d = int(x["dai"] * SEC)
        seg = draft.TextSegment(
            x["text"], trange(int(x["bd"] * SEC), d),
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
    script.save()
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
    ap.add_argument("--sua-nhanh", action="store_true",
                    help="giữ kế hoạch: bỏ SFX, làm lại chữ (chỉ số liệu/dữ kiện) và chọn lại nhạc từ kho YouTube")
    ap.add_argument("--tinh-lai-chuyen-canh", action="store_true",
                    help="giữ kế hoạch cũ, chỉ dựng lại chuyển cảnh theo các ô hình hiện tại")
    a = ap.parse_args()

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
            kh["chu"] = lap_chu_so_lieu(cau)
            kh["sfx"] = []
            kh["nhac"] = chon_nhac(kh["chuong"], am)
            ghi_json(KE_HOACH, kh)
            log(f"    kế hoạch sửa: {len(kh['chu'])} chữ số liệu, 0 SFX, {len(kh['nhac'])} đoạn nhạc (kho YouTube)")
        if a.tinh_lai_chuyen_canh:
            kh = tinh_lai_chuyen_canh(canh, cau, kh)
            ghi_json(KE_HOACH, kh)
            log(f"    dựng lại {len(kh['chuyen_canh'])} chuyển cảnh theo ô hiện tại")
        doi = doi_chuyen_canh_nhay(kh)
        if doi:
            log(f"    đã thay {doi} chuyển cảnh gây nháy bằng chuyển cảnh sạch")
    else:
        kh = lap_ke_hoach(canh, cau, tong)
        kh["nhac"] = chon_nhac(kh["chuong"], am)
        kh["sfx"] = chon_sfx(kh["sfx"], am) if SFX_BAT else []
        ghi_json(KE_HOACH, kh)
        log(f"[2] kế hoạch: {len(kh['chuong'])} chương, {len(kh['chu'])} chữ nhấn mạnh, "
            f"{len(kh['chuyen_canh'])} chuyển cảnh, {len(kh['nhac'])} đoạn nhạc, {len(kh['sfx'])} SFX -> ra/ke_hoach.json")
    if a.chi_lap_ke_hoach:
        return
    if not SFX_BAT:
        kh["sfx"] = []
    thu_muc = dung_du_an(canh, kh, a.ten)
    n = gan_chuyen_canh(thu_muc, kh)
    log(f"[3] dự án CapCut: {thu_muc}  (chuyển cảnh gắn được: {n}/{len(kh['chuyen_canh'])})")


if __name__ == "__main__":
    main()
