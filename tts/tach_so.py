# -*- coding: utf-8 -*-
"""Tách câu có SỐ DÀI viết bằng chữ thành các đoạn ngắn để OmniVoice đọc đủ chữ.

Đo 11/10/2026 (nhận dạng lại bằng wav2vec2 tiếng Việt, chép đúng từng âm tiết): OmniVoice đọc
"hai mươi tám nghìn ba trăm bảy mươi sáu" thành "hai tám ba bảy sáu" — với MỌI giọng, mọi step, seed,
tốc độ, guidance; viết bằng chữ số cũng sai. Đọc RIÊNG từng cụm ngắn ("hai mươi tám nghìn" /
"ba trăm bảy mươi sáu") thì đủ chữ. Nên: câu có cụm số dài -> chia đoạn, đọc từng đoạn, nối lại."""
import re

SO = {"không", "một", "mốt", "hai", "ba", "bốn", "tư", "năm", "lăm", "nhăm", "sáu", "bảy", "bẩy", "tám", "chín",
      "mười", "mươi", "linh", "lẻ", "trăm", "nghìn", "ngàn", "vạn", "triệu", "tỷ", "tỉ", "rưỡi",
      "phẩy"}   # 18/10: "một phẩy năm triệu" viết rời -> OmniVoice nuốt "phẩy" 3/3 seed (fish câu 30); nối gạch: đủ 9/9
DON_VI_LON = {"nghìn", "ngàn", "vạn", "triệu", "tỷ", "tỉ"}
DAU_HIEU = {"mươi", "trăm"} | DON_VI_LON          # cụm có các chữ này mới là SỐ NHIỀU CHỮ (không phải "hai con")
DAI_TOI_THIEU = 4                                  # cụm số từ 4 chữ trở lên mới tách
TACH_CUM_DAI_HON = 6                               # cụm số dài hơn thế mới chia nhỏ tại nghìn/triệu/tỷ
NGAN_NHAT = 2                                      # đoạn chữ thường ngắn hơn thế thì gộp vào đoạn bên cạnh


def _loi(w):
    return re.sub(r"[^\w]", "", w.lower())


def tach(text, chia_khi_dai_hon=TACH_CUM_DAI_HON):
    """Danh sách đoạn để đọc riêng. Câu không có cụm số dài -> [text] (giữ nguyên, không đổi gì)."""
    tu = text.split()
    if not tu:
        return [text]
    la_so = [_loi(w) in SO for w in tu]
    cum = []                                       # (đầu, cuối) các cụm số dài
    i = 0
    while i < len(tu):
        if la_so[i]:
            j = i
            while j < len(tu) and la_so[j] and (j == i or not re.search(r"[,.;:!?]$", tu[j - 1])):
                j += 1
            if (_loi(tu[i]) == "năm" and j - i >= 3 and _loi(tu[i + 1]) in ("một", "hai")
                    and _loi(tu[i + 2]) in ("nghìn", "ngàn")):
                i += 1                                 # "năm hai nghìn…" = chữ NĂM (năm tháng), không phải số 5
                continue
            nhom = {_loi(w) for w in tu[i:j]}
            if j - i >= DAI_TOI_THIEU and nhom & DAU_HIEU:
                cum.append((i, j))
            i = j
        else:
            i += 1
    if not cum:
        return [text]
    doan = []                                      # (danh sách chữ, có phải số)
    vt = 0
    for a, b in cum:
        if a > vt:
            doan.append((tu[vt:a], False))
        phan = []
        for w in tu[a:b]:                          # cụm số DÀI: chia sau mỗi đơn vị lớn (nghìn/triệu/tỷ)
            phan.append(w)
            if _loi(w) in DON_VI_LON and b - a > chia_khi_dai_hon and w is not tu[b - 1]:
                doan.append((phan, True))
                phan = []
        if phan:
            doan.append((phan, True))
        vt = b
    if vt < len(tu):
        doan.append((tu[vt:], False))
    gon = []                                       # đoạn chữ thường quá ngắn gộp vào đoạn kế (hoặc trước)
    for k, (ws, so) in enumerate(doan):
        if not so and len(ws) < NGAN_NHAT and k + 1 < len(doan):
            doan[k + 1] = (ws + doan[k + 1][0], doan[k + 1][1])
            continue
        if not so and len(ws) < NGAN_NHAT and gon:
            gon[-1] = (gon[-1][0] + ws, gon[-1][1])
            continue
        gon.append((ws, so))
    ra = [" ".join(ws) for ws, _ in gon if ws]
    return ra if len(ra) > 1 else [text]


if __name__ == "__main__":
    import sys
    for c in sys.argv[1:] or ["Cuối năm hai nghìn không trăm hai mươi, con số chạm mốc hai mươi tám nghìn ba trăm bảy mươi sáu."]:
        print(tach(c))


def noi_gach(text):
    """Nối các chữ trong MỖI cụm số dài bằng gạch nối ("chín-trăm-ba-mươi"): đo 11/10, OmniVoice đọc đủ
    "trăm"/"mươi" khi có gạch nối (28/28 chữ) mà viết rời thì nuốt. Câu không có cụm số dài giữ nguyên."""
    tu = chu_so_thanh_chu(text).split()
    la_so = [_loi(w) in SO for w in tu]
    ra, i = [], 0
    while i < len(tu):
        if la_so[i]:
            j = i
            while j < len(tu) and la_so[j] and (j == i or not re.search(r"[,.;:!?]$", tu[j - 1])):
                j += 1
            k = i
            if (_loi(tu[i]) == "năm" and j - i >= 3 and _loi(tu[i + 1]) in ("một", "hai")
                    and _loi(tu[i + 2]) in ("nghìn", "ngàn")):
                ra.append(tu[i])                       # "năm" (năm tháng) đứng riêng
                k = i + 1
            while j - k > 1 and _loi(tu[j - 1]) == "năm" and not re.search(r"[,.;:!?]$", tu[j - 2]):
                j -= 1                                 # "hai mươi hai năm sau": "năm" cuối cụm là NĂM (thời gian)
            nhom = {_loi(w) for w in tu[k:j]}
            if j - k >= 2 and nhom & DAU_HIEU:
                ra.append("-".join(tu[k:j]))
            else:
                ra.extend(tu[k:j])
            i = j
        else:
            ra.append(tu[i])
            i += 1
    return " ".join(ra)


_CS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _ba_chu_so(n, day_du):
    """0..999 -> chữ. day_du=True: nhóm đứng sau nhóm lớn hơn nên đọc đủ "không trăm", "linh"."""
    tram, chuc, dv = n // 100, n // 10 % 10, n % 10
    ra = []
    if tram or day_du:
        ra += [_CS[tram], "trăm"]
    if chuc == 0:
        if dv and (tram or day_du):
            ra.append("linh")
    elif chuc == 1:
        ra.append("mười")
    else:
        ra += [_CS[chuc], "mươi"]
    if dv:
        if dv == 1 and chuc > 1:
            ra.append("mốt")
        elif dv == 5 and chuc > 0:
            ra.append("lăm")
        elif dv == 4 and chuc > 1:
            ra.append("tư")
        else:
            ra.append(_CS[dv])
    return ra


def so_thanh_chu(n):
    """Số nguyên >= 0 -> chữ tiếng Việt ("28376" -> "hai mươi tám nghìn ba trăm bảy mươi sáu")."""
    if n == 0:
        return "không"
    don_vi = ["", "nghìn", "triệu", "tỷ"]
    nhom = []
    while n:
        nhom.append(n % 1000)
        n //= 1000
    ra = []
    for i in range(len(nhom) - 1, -1, -1):
        g = nhom[i]
        if g == 0:
            continue
        ra += _ba_chu_so(g, day_du=bool(ra))
        dv = don_vi[i % 3] if i < 4 else don_vi[i % 3]
        if i >= 3 and i % 3 == 0:
            dv = "tỷ"
        if dv:
            ra.append(dv)
    return " ".join(ra)


def chu_so_thanh_chu(text):
    """Số viết bằng CHỮ SỐ (28.376 / 28376 / 2020) -> chữ, để nối gạch như mọi cụm số. Số thập phân kiểu Việt
    ("3,5") -> "ba phẩy năm". Đo 11/10: OmniVoice đọc sai 28.376 viết bằng chữ số."""
    def doi(m):
        so = m.group(0)
        if re.fullmatch(r"\d+,\d+", so):
            a, b = so.split(",")
            return so_thanh_chu(int(a)) + " phẩy " + " ".join(_CS[int(c)] for c in b)
        return so_thanh_chu(int(so.replace(".", "")))
    return re.sub(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+,\d+|\d+)(?![\w])", doi, text)
