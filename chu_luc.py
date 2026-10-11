# -*- coding: utf-8 -*-
"""Chọn bộ VIDEO CHỦ LỰC: vài video đúng chủ đề, sạch, phủ được nhiều nhịp — rồi ghép nhịp từ đó trước.

Thay vì mỗi nhịp nhặt đoạn tốt nhất từ BẤT KỲ video nào (kết quả: ~20 video, mỗi video dùng 1-2 đoạn, nhiều video lạc
đề), ta chấm CHẤT LƯỢNG từng video rồi chọn tham lam một tập nhỏ phủ nhiều nhịp nhất (bài toán phủ cơ sở)."""
import re
import unicodedata

import numpy as np

NGUONG_PHU = 0.215               # điểm CLIP tối thiểu để coi một video "phủ" được nhịp (trùng chon_doan.NGUONG)
K_TOI_DA = 14                    # bộ chủ lực tối đa bấy nhiêu video
LOI_TOI_THIEU = 0.25            # dừng khi video kế thêm không còn tăng độ phủ đáng kể (tính theo tổng điểm các nhịp)
THUONG_CHAT_LUONG = 0.10         # điểm cộng (nhân q) mỗi nhịp mà video phủ được
_STOP = {"the", "and", "with", "for", "from", "island", "river", "lake", "national", "park", "north", "south", "east",
         "west", "new", "old", "video", "map", "logo", "sign", "world", "animal", "animals", "wildlife", "nature"}


def toks(s):
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return {t for t in re.findall(r"[a-z0-9]+", s) if (len(t) >= 3 or any(c.isdigit() for c in t)) and t not in _STOP}


def tu_khoa_neo(canh, ctx):
    """{từ khoá: trọng số} của 'mỏ neo' câu chuyện: tần suất trong thực thể các nhịp (từ nhắc nhiều = trọng tâm câu chuyện:
    dingo, goat… nặng hơn địa danh chung như australia/queensland) cộng chủ thể chính và tên riêng trong ctx."""
    dem = {}
    for c in canh:
        for n in c.get("nhip") or c.get("nhip_tho") or []:
            for e in n.get("ents") or []:
                for t in toks(e.get("name", "")):
                    dem[t] = dem.get(t, 0) + 1
    for s in (ctx or {}).get("chu_the", []) or []:
        for t in toks(s.get("en", "")):
            dem[t] = dem.get(t, 0) + 3
    for v in ((ctx or {}).get("ten") or {}).values():
        for t in toks(str(v)):
            dem[t] = dem.get(t, 0) + 2
    return {t: k for t, k in dem.items() if k >= 2}


def chat_luong_video(it, e, p_hh, neo, vec_neo, ty_le_chu):
    """q in [0,1]: 0.5 đúng chủ đề (tiêu đề/kênh khớp mỏ neo, có trọng số) + 0.3 CLIP khớp chủ thể chính + 0.2 hình sạch."""
    tt = toks((it.get("tieu_de") or "") + " " + (it.get("kenh") or ""))
    topic = 0.0
    if neo:
        top3 = sorted(neo.values(), reverse=True)[:3]
        khop = [t for t in tt if t in neo]
        topic = min(1.0, sum(neo[t] for t in khop) / max(sum(top3), 1))
        if len(khop) < 2:                                    # chỉ trùng MỘT từ (vd "pelorus" của vịnh ở New Zealand) -> nghi trùng tên
            topic *= 0.4
    if vec_neo is not None and len(vec_neo) and len(e):
        m = float((e @ vec_neo.T).max(1).mean())
        clip = float(np.clip((m - 0.17) / 0.10, 0.0, 1.0))
    else:
        clip = 0.0
    sach = float((1.0 - np.mean(p_hh > 0.5)) * (1.0 - ty_le_chu))
    return 0.5 * topic + 0.3 * clip + 0.2 * sach


def ma_tran_phu(vids, nhips, cua_so_cua):
    """S[b, v] = điểm CLIP trung bình tốt nhất của một cửa sổ (đúng độ dài nhịp b) trong video v."""
    S = np.zeros((len(nhips), len(vids)), np.float32)
    for j, (it, t, e) in enumerate(vids):
        for b, (qv, dai) in enumerate(nhips):
            cs = cua_so_cua(dai)
            s = e @ qv
            if len(s) < cs:
                continue
            S[b, j] = float(np.convolve(s, np.ones(cs) / cs, mode="valid").max())
    return S


def chon_bo(S, q, uu_tien=(), k_max=K_TOI_DA):
    """Chọn tham lam tập video làm tăng độ phủ nhiều nhất. uu_tien = chỉ số video LUÔN có (link người dùng chỉ định)."""
    B, V = S.shape
    cur = np.zeros(B, np.float32)
    chon, con = [], set(range(V))

    def gia_tri(j):
        g = np.clip(S[:, j] - NGUONG_PHU, 0, None) * (0.4 + 1.2 * q[j])             + THUONG_CHAT_LUONG * q[j] * (S[:, j] >= NGUONG_PHU)
        return g

    for j in uu_tien:
        if j in con:
            chon.append(j)
            con.discard(j)
            cur = np.maximum(cur, gia_tri(j))
    while con and len(chon) < k_max:
        best, bg = None, 0.0
        for j in con:
            gain = float(np.clip(gia_tri(j) - cur, 0, None).sum())
            if gain > bg:
                best, bg = j, gain
        if best is None or bg < LOI_TOI_THIEU:
            break
        chon.append(best)
        con.discard(best)
        cur = np.maximum(cur, gia_tri(best))
    return chon, cur
