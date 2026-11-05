# -*- coding: utf-8 -*-
"""Lệnh DUY NHẤT Antigravity được phép chạy (agy.tac_nhan_sua): dựng thử cảnh Remotion trong thư mục làm việc của nó.

    python thu_canh.py <ma>

Đọc cache/nhan_y/agy_canh/<ma>/{canh.jsx, props.json, giay.txt} -> chép sang remotion/src/ai/_agy_<ma>.jsx (không đụng
cảnh thật) -> bộ đo của nhan_y_ai (chữ dài, 6 khung, khung trống / tối) -> ảnh khung ghi vào chính thư mục đó, in kết quả.
Tệp này nằm ngoài thư mục agent được ghi, nên agent không sửa được thứ lệnh này chạy.
"""
import json
import os
import re
import sys

AQ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQ)
sys.path.insert(0, os.path.dirname(AQ))

import nhan_y_ai as m  # noqa: E402
from common import CACHE_CHUNG  # noqa: E402


def thu_muc(ma):
    return os.path.join(CACHE_CHUNG, "nhan_y", "agy_canh", ma)


def chay(ma):
    if not re.fullmatch(r"[a-z0-9_]+", ma or ""):
        return "LOI: mã cảnh không hợp lệ"
    d = thu_muc(ma)
    try:
        code = open(os.path.join(d, "canh.jsx"), encoding="utf-8").read()
        pr = json.load(open(os.path.join(d, "props.json"), encoding="utf-8"))
        giay = float(open(os.path.join(d, "giay.txt"), encoding="utf-8").read().strip())
    except (OSError, ValueError) as e:
        return f"LOI: không đọc được tệp làm việc: {e}"
    if "export const Canh" not in code or "export const schema" not in code:
        return "LOI: canh.jsx must contain `export const schema` and `export const Canh`"
    loi = m._chu_dai(pr) or m._chu_dai_code(code) or m._kiem_lop(code, giay) or m._kiem_chu_lop(code, pr, giay)   # 05/11: cùng luật với bộ đo
    if loi:
        return "LOI: " + loi
    for f in os.listdir(d):
        if f.endswith(".png"):
            os.remove(os.path.join(d, f))
    mod = f"_agy_{ma}.jsx"
    f_mod = os.path.join(m.THU_AI, mod)
    with open(f_mod, "w", encoding="utf-8", newline="\n") as f:
        f.write(code + "\n")
    try:
        dau, cuoi = 0.6 * 30, (giay - 0.4) * 30
        khung = [round(dau + (cuoi - dau) * k) for k in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
        loi, anh = m._thu_dung(ma, pr, giay, khung, mod=mod, thu=d)
    finally:
        if os.path.isfile(f_mod):
            os.remove(f_mod)
    if loi:
        return "LOI: " + loi
    return "OK — rendered frames (look at them):\n" + "\n".join(f"{a} (t={k / 30:.1f}s)" for k, a in zip(khung, anh))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(chay(sys.argv[1] if len(sys.argv) > 1 else ""))
