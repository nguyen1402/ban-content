# -*- coding: utf-8 -*-
"""Đổi SỐ VIẾT BẰNG CHỮ (kịch bản viết chữ cho giọng đọc chuẩn) sang CHỮ SỐ để HIỂN THỊ trên màn hình:
"hai trăm ba mươi nghìn" -> "230.000", "sáu mươi mốt phần trăm" -> "61%", "một trăm bốn mươi triệu" -> "140 triệu",
"một phẩy hai" -> "1,2". Chỉ đổi cụm chắc chắn là số (có từ hàng như mươi/trăm/nghìn/triệu/tỷ, hoặc >= 2 từ số);
"năm" đứng một mình (năm = year) giữ nguyên."""
import re

SO = {"không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5, "nhăm": 5,
      "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9}
HANG = {"mười", "mươi", "trăm", "nghìn", "ngàn", "triệu", "tỷ", "tỉ", "linh", "lẻ"}
TU = set(SO) | HANG | {"phẩy"}


def _gia_tri(ws):
    tong, cur, cho = 0, 0, 0
    for w in ws:
        if w in SO:
            cho = SO[w]
        elif w == "mười":
            cur += 10
            cho = 0
        elif w == "mươi":
            cur += cho * 10
            cho = 0
        elif w == "trăm":
            cur += cho * 100
            cho = 0
        elif w in ("nghìn", "ngàn"):
            tong += (cur + cho) * 1000
            cur = cho = 0
        elif w == "triệu":
            tong = (tong + cur + cho) * 1_000_000
            cur = cho = 0
        elif w in ("tỷ", "tỉ"):
            tong = (tong + cur + cho) * 1_000_000_000
            cur = cho = 0
    return tong + cur + cho


def _dinh_dang(n):
    if n >= 1_000_000_000 and n % 100_000_000 == 0:
        x = n / 1_000_000_000
        return (f"{x:.1f}".rstrip("0").rstrip(".").replace(".", ",")) + " tỷ"
    if n >= 1_000_000 and n % 100_000 == 0:
        x = n / 1_000_000
        return (f"{x:.1f}".rstrip("0").rstrip(".").replace(".", ",")) + " triệu"
    return f"{n:,}".replace(",", ".")


def doi(text):
    """Đổi mọi cụm số viết bằng chữ trong text sang chữ số (giữ chữ hoa/thường của phần còn lại)."""
    text = re.sub(r"phần\s+trăm", "PHANTRAM", text, flags=re.I)     # "trăm" của phần trăm không phải hàng trăm
    tokens = re.split(r"(\s+)", text)
    ra, i = [], 0
    while i < len(tokens):
        w = tokens[i].lower()
        if w in TU and w not in ("linh", "lẻ", "phẩy"):
            j, cum = i, []
            while j < len(tokens) and (tokens[j].isspace() or tokens[j].lower() in TU):
                if not tokens[j].isspace():
                    cum.append(tokens[j].lower())
                j += 1
            while j > i and tokens[j - 1].isspace():
                j -= 1
            # "năm" cuối cụm/đầu cụm mà không có từ hàng đi kèm -> là "năm" (year), không phải số 5
            if len(cum) >= 2 and cum[0] == "năm" and cum[1] in SO:
                ra.append(tokens[i])
                i += 1
                continue
            chac = any(x in HANG for x in cum) or len(cum) >= 2
            if not chac:
                ra.append(tokens[i])
                i += 1
                continue
            if "phẩy" in cum:
                k = cum.index("phẩy")
                nguyen, le = _gia_tri(cum[:k]), "".join(str(SO.get(x, "")) for x in cum[k + 1:])
                s = f"{nguyen:,}".replace(",", ".") + ("," + le if le else "")
            else:
                v = _gia_tri(cum)
                truoc = "".join(ra).rstrip().split(" ")[-1].lower() if ra else ""
                s = str(v) if truoc == "năm" and 1000 <= v <= 2100 else _dinh_dang(v)   # "năm 2004", không "2.004"
            ra.append(s)
            i = j
            continue
        ra.append(tokens[i])
        i += 1
    s = "".join(ra)
    s = re.sub(r"(\d)\s*PHANTRAM", r"\1%", s)
    s = s.replace("PHANTRAM", "phần trăm")
    return s


if __name__ == "__main__":
    for x in ["HAI TRĂM BA MƯƠI NGHÌN", "HƠN MƯỜI TÁM NGHÌN NĂM TRĂM", "MƯỜI BA NGHÌN CON", "CHÍN TRĂM BA MƯƠI",
              "HƠN MỘT TRĂM BỐN MƯƠI TRIỆU", "BA TRĂM LINH TÁM TẤN", "SÁU MƯƠI MỐT PHẦN TRĂM", "BA ĐẾN NĂM MÉT",
              "SUỐT HAI THẬP KỶ", "NĂM HAI NGHÌN KHÔNG TRĂM LẺ BỐN", "MỘT PHẨY HAI", "HAI CÁCH", "TÁM MƯƠI CHÍN PHẨY BA PHẦN TRĂM"]:
        print(x, "->", doi(x).upper())
