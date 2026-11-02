# -*- coding: utf-8 -*-
import sys
import time
import os
import json
import ban_dung
import dung_tay

du_an = "chosoi"
print(f"=== BẮT ĐẦU CHẠY ĐIỀU PHỐI SIGLIP CHO DỰ ÁN '{du_an}' ===")
t0 = time.time()

# 1. Chạy băm tự động với SigLIP (giu_da_dung=False để chấm lại toàn bộ bản dựng theo thị giác SigLIP)
res = ban_dung.tu_dong_bam_chu_the(du_an, giu_da_dung=False, loc_sub=True, chi_ngang_16_9=True)
print(f"Hoàn tất tu_dong_bam_chu_the trong {time.time()-t0:.2f}s: {res}")

# 2. Ghi đè bản nháp CapCut
drafts_dir = r"D:\CapCut\Draft\CapCut Drafts"
draft_name = "chosoi_hoan_chinh"
print(f"Đang ghi đè bản nháp '{draft_name}' tại {drafts_dir}...")
draft_path = dung_tay.tao_nhap(du_an, draft_name, drafts_dir)
print(f"ĐÃ GHI ĐÈ THÀNH CÔNG BẢN NHÁP CAPCUT: {draft_path}")
print(f"Tổng thời gian: {time.time()-t0:.2f}s")
