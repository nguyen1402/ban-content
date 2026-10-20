# -*- coding: utf-8 -*-
"""Kịch bản -> tách cảnh -> (giọng đọc ∥ từ khoá tìm nguồn từ ChatGPT) -> xuất từ khoá + bản nháp giọng đọc.

    python chay.py kichban.txt --ten "Tên bản nháp"
    python chay.py kichban.txt --gioi-han 12 --khong-nhap          # thử 12 cảnh đầu, chưa tạo bản nháp

KHÔNG tự tìm/tải/ghép video nữa (người dùng tự tìm theo từ khoá). Kết quả ở ra/<dự án>/:
  tu_khoa.md / tu_khoa.json   từ khoá tìm video/ảnh/BẢN ĐỒ + nội dung nên chiếu cho từng cảnh
  giong_doc.wav, kich_ban.srt giọng đọc nối liền + phụ đề đúng mốc
  bản nháp CapCut             chỉ có giọng đọc đúng mốc, phần hình để trống cho người dùng ghép
Bản cũ (tự tìm + chấm CLIP + ghép từng câu) giữ ở chay_ghep_tu_dong.py."""
import argparse
import os
import threading

from common import CACHE, CACHE_CHUNG, DU_AN, OUT, log, thu_muc_nhap_capcut, tien_do, xoa_tien_do

import ghep
import giong
import tach_canh
import tu_khoa

BUOC = ("tach", "tu_khoa", "giong", "xuat", "nhap")
TU_KHOA_CANH = False        # 19/10 user ("tránh dư thừa"): bước 🤖 theo chủ đề tự lập từ khoá theo đoạn + theo vế ->
#                             không hỏi từ khoá TỪNG CẢNH trước khi đọc giọng nữa (chế độ tìm theo cảnh tự hỏi khi cần)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kich_ban")
    ap.add_argument("--gioi-han", type=int, default=0, help="chỉ làm N cảnh đầu (0 = hết)")
    ap.add_argument("--ten", default="Ban content test")
    ap.add_argument("--cps", type=float, default=tach_canh.KY_TU_MOI_GIAY)
    ap.add_argument("--giong-clip", default=giong.OMNI_REF, help="clip mẫu giọng OmniVoice (3-10 giây)")
    ap.add_argument("--toc-do", type=float, default=1.0, help="tốc độ đọc OmniVoice (1.0 = gốc)")
    ap.add_argument("--num-step", type=int, default=32, help="số bước khuếch tán OmniVoice")
    ap.add_argument("--khong-giong", action="store_true", help="không đọc giọng, dùng thời lượng ước lượng")
    ap.add_argument("--khong-nhap", action="store_true", help="không ghi bản nháp CapCut")
    ap.add_argument("--du-an", default=None, help="tên dự án (mặc định = tên file kịch bản)")
    a, _bo_qua = ap.parse_known_args()                    # cờ của bản cũ (--chat-luong, --khong-ocr…) bỏ qua
    with open(os.path.join(CACHE_CHUNG, "du_an_cuoi.txt"), "w", encoding="utf-8") as f:
        f.write(DU_AN)
    log(f"[0] dự án '{DU_AN}': dữ liệu ở {CACHE}, kết quả ở {OUT}")
    xoa_tien_do()
    for b in BUOC:
        tien_do(b, "cho")

    tien_do("tach", "dang")
    text, canh = tach_canh.tach_don_gian(a.kich_ban, a.gioi_han, a.cps)
    tien_do("tach", "xong", f"{len(canh)} cảnh")
    loi = {}
    kq = {}

    def nhanh_giong():                                      # NHÁNH A: đọc giọng (OmniVoice)
        try:
            if a.khong_giong:
                tien_do("giong", "xong", "bỏ qua")
                return
            tien_do("giong", "dang")
            giong.doc_omni(canh, ref=a.giong_clip, toc_do=a.toc_do, num_step=a.num_step)
            tien_do("giong", "xong", f"{sum(1 for c in canh if c.get('giong'))}/{len(canh)} cảnh")
        except BaseException as e:                          # noqa: BLE001
            loi["giong"] = e
            tien_do("giong", "loi", str(e)[:200])

    def nhanh_tu_khoa():                                    # NHÁNH B: ChatGPT tóm tắt + từ khoá + địa điểm
        try:
            tien_do("tu_khoa", "dang")
            ctx = tach_canh.lam_ten_va_tom_tat(tach_canh.bo_moc_nghi(text), os.path.join(CACHE, "ten.json"))
            if TU_KHOA_CANH:
                tu_khoa.lam_tu_khoa(canh, ctx, os.path.join(CACHE, "tu_khoa.json"))
                n_dd = sum(1 for c in canh if c["tu_khoa"].get("dia_diem"))
                tien_do("tu_khoa", "xong", f"{sum(1 for c in canh if c['tu_khoa'].get('video'))} cảnh · "
                                          f"{n_dd} có địa điểm")
            else:
                tien_do("tu_khoa", "xong", f"{len(ctx.get('ten') or {})} tên riêng")
            kq["ctx"] = ctx
        except BaseException as e:                          # noqa: BLE001
            loi["tu_khoa"] = e
            tien_do("tu_khoa", "loi", str(e)[:200])

    ta = threading.Thread(target=nhanh_giong, name="giong")
    tb = threading.Thread(target=nhanh_tu_khoa, name="tu_khoa")
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    if loi:
        for k, e in loi.items():
            log(f"! nhánh {k} lỗi: {e}")
        raise SystemExit(f"Dừng: nhánh {', '.join(loi)} lỗi")

    t_ = 0.0
    for c in canh:                                          # không đọc giọng: mốc theo độ dài ước lượng
        c.setdefault("bat_dau", round(t_, 2))
        t_ = c["bat_dau"] + c["dai"]

    tien_do("xuat", "dang")
    tu_khoa.xuat(canh, OUT)
    ghep.xuat_srt(canh, os.path.join(OUT, "kich_ban.srt"))
    wav = ghep.noi_giong(canh, os.path.join(OUT, "giong_doc.wav"))
    log(f"[5] đã xuất: tu_khoa.md, tu_khoa.json, kich_ban.srt{', giong_doc.wav' if wav else ''} ở {OUT}")
    tien_do("xuat", "xong", "tu_khoa.md")

    if not a.khong_nhap:
        tien_do("nhap", "dang")
        dd = thu_muc_nhap_capcut()
        if not dd:
            log("    ! không dò được thư mục CapCut Drafts — bỏ qua bản nháp")
            tien_do("nhap", "loi", "không thấy thư mục CapCut Drafts")
            return
        dai = ghep.xuat_nhap_giong(canh, a.ten, dd)
        log(f"    bản nháp CapCut (giọng đọc): {os.path.join(dd, a.ten)} ({dai:.0f}s)")
        tien_do("nhap", "xong", a.ten)
    else:
        tien_do("nhap", "xong", "bỏ qua")


if __name__ == "__main__":
    main()
