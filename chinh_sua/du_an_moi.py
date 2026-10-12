# -*- coding: utf-8 -*-
"""Đọc dự án KIỂU MỚI (trình dựng tay / nút 🤖: ra/<dự án>/tu_khoa.json + dung.json + kho + giong_doc.wav) thành
danh sách cảnh cùng khuôn mà dung_hoan_chinh.py dùng cho dự án thô kiểu cũ (ket_qua.json):

  c = {id, text, giong_dai, _t0, _t1 (µs), _os: [(t, d, o)]}, o = {clip, anh, vao (giây trong video gốc)}

Giờ đặt đúng như bản nháp thô (dung_tay.tao_nhap): đoạn ở bat_dau cảnh + bd, video trỏ VIDEO GỐC (vao).
Cảnh ĐỊA ĐIỂM (loai=dia_diem có dia_danh_en, từ mo_ta_canh.py): đoạn ĐẦU thay bằng clip Remotion bản đồ VỆ TINH
phóng vào + khoanh viền địa danh (nen_ban_do.dung_clip_vetinh) — 12/10 user chọn thay cho ảnh phong cảnh."""
import os

SEC = 1_000_000


def _ten_hien(c):
    """Tên hiện trên bản đồ: tên tiếng Việt trong kịch bản nếu từ khoá bản đồ có, không thì tên tiếng Anh ngắn."""
    en = (c.get("dia_danh_en") or "").split(",")[0].strip()
    for b in c.get("ban_do") or []:
        t = (b.get("ten") or "").strip()
        if t and len(t.split()) <= 4:
            return t[:1].upper() + t[1:]
    return en


def tai(du_an, ban_do=True):
    """(canh, giong_wav, tong_giay) của dự án kiểu mới."""
    import dung_tay
    import nen_ban_do
    from common import doc_json, log, thu_muc_du_an
    out = thu_muc_du_an(du_an)[1]
    tk = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    dung = dung_tay.doc_dung(du_an)
    kho = dung_tay.doc_kho(du_an)
    wav = os.path.join(out, "giong_doc.wav")
    tong = dung_tay._do_dai(wav) if os.path.isfile(wav) else 0.0       # noqa: SLF001
    canh, het = [], -1
    for c in sorted(tk, key=lambda x: int(x["id"])):
        c = dict(c)
        c["_t0"] = int(round(c["bat_dau"] * SEC))
        c["_t1"] = int(round((c["bat_dau"] + c["dai"]) * SEC))
        c["giong_dai"] = c["dai"]
        c["_os"] = []
        for d in sorted((dung.get(str(c["id"])) or {}).get("doan") or [], key=lambda x: x["bd"]):
            m = kho.get(d["kho_id"]) or {}
            f = m.get("file", "")
            if m.get("trang_thai") != "xong" or not os.path.isfile(f):
                continue
            t0 = max(int(round((c["bat_dau"] + d["bd"]) * SEC)), het)
            if 0 <= het < t0 and t0 - het < int(1.5 * SEC):  # khoảng hở nhỏ -> đoạn này bắt đầu sớm hơn lấp vào
                t0 = het
            dl = int(round((c["bat_dau"] + d["bd"] + d["dai"]) * SEC)) - t0
            if d["loai"] == "video":
                dl = min(dl, int(float(m.get("dai") or 1e9) * SEC) - int(d["vao"] * SEC) - 1000)
            if dl <= int(0.2 * SEC):
                continue
            c["_os"].append((t0, dl, {"clip": f, "anh": d["loai"] == "anh", "vao": float(d.get("vao") or 0.0),
                                      "phong": float(m.get("phong") or 1.0) if d["loai"] == "video" else 1.0}))
            het = t0 + dl
        tong = max(tong, c["_t1"] / SEC)
        canh.append(c)
    if ban_do:
        viec = []
        for c in canh:
            if c.get("loai") == "dia_diem" and c.get("dia_danh_en") and c["_os"]:
                viec.append((c["dia_danh_en"], round(c["_os"][0][1] / SEC, 2), _ten_hien(c)))
        if viec:
            clip = nen_ban_do.dung_clip_vetinh(viec)
            n = 0
            for c in canh:
                if c.get("loai") == "dia_diem" and c.get("dia_danh_en") and c["_os"]:
                    t, d, _o = c["_os"][0]
                    f = clip.get((c["dia_danh_en"], round(d / SEC, 2)))
                    if f:
                        c["_os"][0] = (t, d, {"clip": f, "anh": False, "vao": 0.0, "ban_do": True})
                        n += 1
            log(f"    bản đồ vệ tinh: {n}/{len(viec)} cảnh địa điểm")
    return canh, (wav if os.path.isfile(wav) else None), tong
