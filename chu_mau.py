# -*- coding: utf-8 -*-
"""CHỮ MẪU cố định trên mọi bản nháp (13/10 user: "lần sau tạo bản nháp tự động thêm 2 dòng chữ đó vào đúng vị trí, font,
độ mờ, cỡ chữ như vậy").

  python chu_mau.py chup "<tên bản nháp CapCut>"   # chụp MỌI dòng chữ của bản nháp làm mẫu -> chu_mau.json
  python chu_mau.py gan  "<tên bản nháp CapCut>"   # gắn mẫu vào một bản nháp (thường tự gọi sau khi dựng)

Mẫu giữ NGUYÊN chất liệu chữ CapCut (font, cỡ, màu, viền, bóng, độ mờ) + vị trí/scale của đoạn; khi gắn: mã mới, mỗi dòng
một track chữ, chạy SUỐT video (0 -> hết)."""
import copy
import json
import os
import sys
import uuid

GOC = os.path.dirname(os.path.abspath(__file__))
MAU = os.path.join(GOC, "chu_mau.json")


def _thu_muc(ten):
    from common import thu_muc_nhap_capcut
    if os.path.isdir(ten):
        return ten
    return os.path.join(thu_muc_nhap_capcut() or r"D:\CapCut\Draft\CapCut Drafts", ten)


def chup(ban_nhap):
    """Chụp các dòng chữ (track chữ) của bản nháp -> chu_mau.json. Trả số dòng."""
    j = json.load(open(os.path.join(_thu_muc(ban_nhap), "draft_content.json"), encoding="utf-8"))
    theo_id = {m["id"]: (k, m) for k, v in j["materials"].items() if isinstance(v, list)
               for m in v if isinstance(m, dict) and m.get("id")}
    ds = []
    for t in j["tracks"]:
        if t.get("type") != "text":
            continue
        for s in t["segments"]:
            loai_m, m = theo_id.get(s.get("material_id"), (None, None))
            if not m:
                continue
            phu = [{"loai": theo_id[r][0], "m": theo_id[r][1]} for r in s.get("extra_material_refs") or [] if r in theo_id]
            ds.append({"track": {k: v for k, v in t.items() if k != "segments"}, "segment": s, "material": m, "phu": phu,
                       "chu": json.loads(m.get("content") or "{}").get("text", "")})
    json.dump({"tu": os.path.basename(_thu_muc(ban_nhap)), "dong": ds}, open(MAU, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(ds)


def gan(thu_muc_nhap):
    """Gắn các dòng chữ mẫu vào bản nháp (chạy suốt video). Không có mẫu -> bỏ qua. Trả số dòng đã gắn."""
    if not os.path.isfile(MAU):
        return 0
    mau = json.load(open(MAU, encoding="utf-8")).get("dong") or []
    if not mau:
        return 0
    f = os.path.join(_thu_muc(thu_muc_nhap), "draft_content.json")
    j = json.load(open(f, encoding="utf-8"))
    tong = int(j.get("duration") or 0)
    if tong <= 0:
        tong = max((s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                    for t in j["tracks"] for s in t["segments"]), default=0)
    da_co = {json.loads(m.get("content") or "{}").get("text", "") for m in j["materials"].get("texts", [])}

    def moi():
        return str(uuid.uuid4()).upper()
    n = 0
    for x in mau:
        if x["chu"] in da_co:                                # bản nháp đã có dòng này (chạy lại): không gắn trùng
            continue
        m = copy.deepcopy(x["material"])
        m["id"] = moi()
        j["materials"].setdefault("texts", []).append(m)
        refs = []
        for p in x["phu"]:
            pm = copy.deepcopy(p["m"])
            pm["id"] = moi()
            j["materials"].setdefault(p["loai"], []).append(pm)
            refs.append(pm["id"])
        s = copy.deepcopy(x["segment"])
        s.update(id=moi(), material_id=m["id"], extra_material_refs=refs,
                 target_timerange={"start": 0, "duration": tong})
        if s.get("render_timerange"):
            s["render_timerange"] = {"start": 0, "duration": 0}
        t = copy.deepcopy(x["track"])
        t.update(id=moi(), segments=[s])
        j["tracks"].append(t)
        n += 1
    if n:
        json.dump(j, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    return n


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("chup", "gan"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "chup":
        print(f"đã chụp {chup(sys.argv[2])} dòng chữ mẫu -> {MAU}")
    else:
        print(f"đã gắn {gan(sys.argv[2])} dòng chữ mẫu")
