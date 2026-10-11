# -*- coding: utf-8 -*-
"""Căn MỐC THỜI GIAN THẬT của từng chữ trong lời kể theo file giọng đọc.

Whisper (chạy trong env omnivoice) nghe lại từng file giọng và cho mốc từng âm tiết; ta khớp các âm tiết đó
với chữ trong kịch bản (khớp mờ, vì Whisper có thể ghi số thay chữ hay nghe lệch vài âm tiết) rồi nội suy cho
chữ nào không khớp. Kết quả c['moc_tu'] = [[t0, t1], ...] — một cặp cho mỗi chữ của c['text'].split()."""
import difflib
import json
import os
import re
import subprocess
import unicodedata

from common import ROOT, duong_cache, doc_json, ghi_json, log

OMNI_PY = os.environ.get("BC_OMNI_PY", r"D:\CapCutTTS\omnivoice-env\Scripts\python.exe")   # env OmniVoice riêng
SCRIPT = os.path.join(ROOT, "tts", "whisper_tu.py")


def chuan(s):
    """Chữ thường, bỏ dấu câu và dấu thanh -> so khớp mờ giữa kịch bản và Whisper."""
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


def can_tu(text, words, dai):
    """Với mỗi chữ của text.split() trả [t0, t1]. words = [{w,t0,t1}] từ Whisper; dai = độ dài file giọng (s)."""
    toks = text.split()
    a = [chuan(t) for t in toks]
    b = [chuan(w["w"]) for w in words]
    t0 = [None] * len(toks)
    t1 = [None] * len(toks)
    for i, j, n in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(n):
            t0[i + k], t1[i + k] = words[j + k]["t0"], words[j + k]["t1"]
    neo = [i for i, v in enumerate(t0) if v is not None]
    if not neo:
        return None                                        # không khớp được chữ nào -> để bên gọi dùng ước lượng
    for i in range(len(toks)):                             # nội suy tuyến tính giữa hai chữ đã khớp gần nhất
        if t0[i] is not None:
            continue
        truoc = max((k for k in neo if k < i), default=None)
        sau = min((k for k in neo if k > i), default=None)
        if truoc is None:
            lo, hi, kl, kh = 0.0, t0[sau], -1, sau
        elif sau is None:
            lo, hi, kl, kh = t1[truoc], dai, truoc, len(toks)
        else:
            lo, hi, kl, kh = t1[truoc], t0[sau], truoc, sau
        buoc = (hi - lo) / max(kh - kl, 1)
        t0[i] = round(lo + buoc * (i - kl - 1), 3) if truoc is not None or sau is not None else 0.0
        t1[i] = round(t0[i] + buoc, 3)
    return [[a_, b_] for a_, b_ in zip(t0, t1)]


def _cache_moc(canh):
    """Mốc chữ phụ thuộc FILE GIỌNG: giọng mặc định dùng moc_tu.json (như cũ), giọng khác dùng moc_tu_<nhãn>.json."""
    for c in canh:
        if c.get("giong"):
            cha = os.path.basename(os.path.dirname(c["giong"]))
            return "moc_tu.json" if cha == "giong_omni" else f"moc_tu_{cha}.json"
    return "moc_tu.json"


def can_tat_ca(canh):
    """Chạy Whisper cho các cảnh có giọng mà chưa có mốc, rồi gán c['moc_tu']."""
    cache = duong_cache(_cache_moc(canh))
    da = doc_json(cache, {})
    can = [c for c in canh if c.get("giong") and not c.get("do_hoa") and str(c["id"]) not in da]
    if can:
        log(f"[1c] Whisper căn từng chữ theo giọng: {len(can)} cảnh…")
        vao = duong_cache("wh_vao.json")
        ra = duong_cache("wh_ra.json")
        ghi_json(vao, [{"id": c["id"], "wav": os.path.abspath(c["giong"])} for c in can])
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([OMNI_PY, SCRIPT, vao, ra], capture_output=True, env=env, timeout=3600,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        if p.returncode != 0:
            log("    ! Whisper lỗi: " + p.stderr.decode("utf-8", "ignore")[-300:])
        da.update(doc_json(ra, {}) or {})
        ghi_json(cache, da)
    n_ok = 0
    for c in canh:
        w = da.get(str(c["id"]))
        if not w or not c.get("giong"):
            continue
        moc = can_tu(c["text"], w, c.get("giong_dai") or w[-1]["t1"])
        if moc:
            c["moc_tu"] = moc
            n_ok += 1
    log(f"    căn từng chữ: {n_ok}/{sum(1 for c in canh if c.get('giong'))} cảnh")
    return canh
