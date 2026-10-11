# -*- coding: utf-8 -*-
"""Kịch bản -> (đọc giọng ∥ phân tích + tìm nguồn) -> chọn đoạn khớp lời -> clip -> bản nháp CapCut.

    python chay.py kichban.txt --ten "Tên bản nháp"
    python chay.py kichban.txt --gioi-han 12 --khong-nhap          # thử 12 cảnh đầu, chưa tạo bản nháp
    python chay.py kichban.txt --giong-clip "voices/Hoài An review.wav" --toc-do 1.1

Hai nhánh chạy SONG SONG: (A) đọc giọng OmniVoice + Whisper căn từng chữ, (B) ChatGPT mô tả hình + tìm nguồn + tải +
lập chỉ mục CLIP. Gặp nhau ở bước chọn đoạn. Tiến độ từng bước ghi vào ra/<dự án>/trang_thai.json cho giao diện.
"""
import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from common import eta_chu, CACHE, CACHE_CHUNG, DU_AN, OUT, ghi_json, log, thu_muc_nhap_capcut, tien_do, xoa_tien_do

import can_giong
import chon_anh
import chon_doan
import do_hoa
import ghep
import giong
import tach_canh
import tim_nguon

KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kich_ban")


def doc_dong(p):
    """Các dòng không rỗng của một file văn bản nhỏ ([] nếu chưa có)."""
    try:
        with open(p, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except OSError:
        return []


BUOC = ("tach", "phan_tich", "giong", "can", "tim", "tai", "chon", "dung", "nhap")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kich_ban")
    ap.add_argument("--gioi-han", type=int, default=0, help="chỉ làm N cảnh đầu (0 = hết)")
    ap.add_argument("--ten", default="Ban content test")
    ap.add_argument("--kho", type=int, default=0,
                    help="số video tối đa trong kho chấm điểm (0 = theo số cảnh: 40%%, 8..60)")
    ap.add_argument("--cps", type=float, default=tach_canh.KY_TU_MOI_GIAY)
    ap.add_argument("--giong", choices=("omni", "cloud"), default="omni",
                    help="omni = OmniVoice (mặc định); cloud = giọng CapCut")
    ap.add_argument("--giong-clip", default=giong.OMNI_REF, help="clip mẫu giọng OmniVoice (3-10 giây)")
    ap.add_argument("--toc-do", type=float, default=1.0, help="tốc độ đọc OmniVoice (1.0 = gốc)")
    ap.add_argument("--num-step", type=int, default=32, help="số bước khuếch tán OmniVoice (cao = tự nhiên hơn, chậm hơn)")
    ap.add_argument("--khong-giong", action="store_true", help="không đọc giọng, dùng thời lượng ước lượng")
    ap.add_argument("--chat-luong", type=int, choices=(360, 720, 1080), default=720,
                    help="độ phân giải đoạn dựng: 360 = nháp nhanh (mờ), 720/1080 = tải riêng đúng đoạn đã chọn")
    ap.add_argument("--khong-ocr", action="store_true", help="không lọc hình có chữ cứng bằng OCR (nhanh hơn, hình có chữ sẽ lọt)")
    ap.add_argument("--khong-nhap", action="store_true", help="không ghi bản nháp CapCut")
    ap.add_argument("--du-an", default=None, help="tên dự án (mặc định = tên file kịch bản)")
    a = ap.parse_args()
    os.environ["BC_CHAT_LUONG"] = str(a.chat_luong)
    if a.khong_ocr:
        os.environ["BC_TAT_OCR"] = "1"
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

    def nhanh_giong():                                      # NHÁNH A: đọc giọng rồi căn từng chữ
        try:
            if a.khong_giong:
                tien_do("giong", "xong", "bỏ qua")
                tien_do("can", "xong", "bỏ qua")
                return
            tien_do("giong", "dang")
            if a.giong == "omni":
                giong.doc_omni(canh, ref=a.giong_clip, toc_do=a.toc_do, num_step=a.num_step)
            else:
                giong.doc_tat_ca(canh)
            tien_do("giong", "xong", f"{sum(1 for c in canh if c.get('giong'))}/{len(canh)} cảnh")
            tien_do("can", "dang")
            can_giong.can_tat_ca(canh)
            tien_do("can", "xong", f"{sum(1 for c in canh if c.get('moc_tu'))}/{len(canh)} cảnh")
        except BaseException as e:                          # noqa: BLE001
            loi["giong"] = e
            tien_do("giong", "loi", str(e)[:200])

    def nhanh_tim():                                        # NHÁNH B: ChatGPT mô tả -> tìm nguồn -> tải -> chỉ mục
        try:
            tien_do("phan_tich", "dang")
            ctx = tach_canh.lam_ten_va_tom_tat(text, os.path.join(CACHE, "ten.json"))
            kq_ct = {}
            th_ct = threading.Thread(                       # chủ thể chỉ cần lời kể + tóm tắt -> hỏi CÙNG LÚC với truy vấn từng cảnh
                target=lambda: kq_ct.update(r=tach_canh.lam_chu_the(canh, ctx, os.path.join(CACHE, "chu_the.json"))),
                name="chu_the")
            th_ct.start()
            tach_canh.lam_truy_van(canh, ctx, os.path.join(CACHE, "canh.json"))
            do_hoa.chuan_bi(canh, ctx)
            tach_canh.lam_tu_khoa_anh([x for x in canh if not x.get("do_hoa")], ctx, os.path.join(CACHE, "anh_q.json"))
            th_ct.join()
            if "r" not in kq_ct:
                raise RuntimeError("bước chủ thể lỗi")
            ctx["chu_the"] = kq_ct["r"]
            tach_canh.lam_nhip(canh, ctx, os.path.join(CACHE, "nhip.json"))
            tach_canh.gan_chu_the(canh, ctx["chu_the"])
            tien_do("phan_tich", "xong", f"{sum(len(x.get('nhip_tho', [])) for x in canh)} nhịp hình")
            tien_do("tim", "dang")
            tim = tim_nguon.tim_tat_ca(canh)
            cap_kho = a.kho or max(8, min(60, int(len(canh) * 0.4)))
            ung_vien = tim_nguon.kho_ung_vien(canh, tim, toi_da=cap_kho)
            ds_link = [u for u in doc_dong(os.path.join(KB_DIR, f"{DU_AN}.link.txt"))]
            ung_vien_link = tim_nguon.them_link(ds_link) if ds_link else []
            if ung_vien_link:
                co = {u["id"] for u in ung_vien}
                ung_vien = [dict(u, uu_tien=True) for u in ung_vien_link] + [u for u in ung_vien if u["id"] not in
                                                                         {x["id"] for x in ung_vien_link}]
                log(f"    video do bạn chỉ định: {len(ung_vien_link)} link")
            tien_do("tim", "xong", f"{len(ung_vien)} video ứng viên")
            tien_do("tai", "dang")
            kho = tim_nguon.tai_kho(ung_vien, 10 ** 6)
            def lap_chi_muc(it):                            # ffmpeg trích khung chạy song song, GPU nhúng xếp hàng
                try:
                    chon_doan.chi_muc_video(it)
                except Exception as e:                      # noqa: BLE001
                    log(f"    ! chỉ mục hỏng {it['id']}: {e}")
            t_cm = time.time()
            log(f"    lập chỉ mục CLIP {len(kho)} video…")
            with ThreadPoolExecutor(4) as ex:
                for i, _ in enumerate(ex.map(lap_chi_muc, kho), 1):
                    if i % 5 == 0 or i == len(kho):
                        log(f"    chỉ mục {i}/{len(kho)}{eta_chu(t_cm, i, len(kho))}")
                        tien_do("tai", "dang", f"chỉ mục {i}/{len(kho)}")
            tien_do("tai", "xong", f"{len(kho)} video")
            return ctx, tim, kho
        except BaseException as e:                          # noqa: BLE001
            loi["tim"] = e
            tien_do("tim", "loi", str(e)[:200])

    ket_qua_b = {}
    ta = threading.Thread(target=nhanh_giong, name="giong")
    tb = threading.Thread(target=lambda: ket_qua_b.update(r=nhanh_tim()), name="tim")
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    if loi:
        for k, e in loi.items():
            log(f"! nhánh {k} lỗi: {e}")
        raise SystemExit(f"Dừng: nhánh {', '.join(loi)} lỗi")
    ctx, tim, kho = ket_qua_b["r"]

    tach_canh.tinh_gio_nhip(canh)
    log(f"    nhịp căn theo giọng thật: {sum(1 for x in canh if x.get('nhip_theo_moc'))}/{len(canh)} cảnh")
    log(f"[2c] {sum(len(x.get('nhip', [])) for x in canh)} nhịp hình cho {len(canh)} cảnh")
    tien_do("chon", "dang")
    do_hoa.dung_het(canh)
    bo_video = set(doc_dong(os.path.join(KB_DIR, f"{DU_AN}.bo_video.txt")))
    uu_tien = {v["id"] for v in kho if v.get("uu_tien")}
    chon_doan.chon(canh, kho, ctx=ctx, bo_video=bo_video, uu_tien=uu_tien)
    chon_anh.thay_bang_anh(canh, tim)
    ghep.va_bang_anh(canh, tim)
    tien_do("chon", "xong")
    tien_do("dung", "dang")
    ghep.dung_clip(canh)
    tien_do("dung", "xong")

    ghi_json(os.path.join(OUT, "ket_qua.json"), canh)
    ghep.xuat_srt(canh, os.path.join(OUT, "kich_ban.srt"))
    thieu, n = ghep.bao_cao(canh, os.path.join(OUT, "bao_cao.md"))
    log(f"[5] thiếu {thieu}/{n} ô — xem bao_cao.md")
    if not a.khong_nhap:
        tien_do("nhap", "dang")
        dd = thu_muc_nhap_capcut()
        if not dd:
            log("    ! không dò được thư mục CapCut Drafts — bỏ qua bản nháp")
            tien_do("nhap", "loi", "không thấy thư mục CapCut Drafts")
            return
        dai = ghep.xuat_nhap_capcut(canh, a.ten, dd)
        log(f"    bản nháp CapCut: {os.path.join(dd, a.ten)} ({dai:.0f}s)")
        tien_do("nhap", "xong", a.ten)
    else:
        tien_do("nhap", "xong", "bỏ qua")


if __name__ == "__main__":
    main()
