# -*- coding: utf-8 -*-
import sys
import time
import os
import json
import re
from collections import Counter
import numpy as np
import cv2

import common
from common import doc_json, ghi_json, log, thu_muc_du_an
import dung_tay
import chu_the
import nhung_siglip

du_an = "chosoi"
print("=== BẮT ĐẦU ĐIỀU PHỐI THÔNG MINH: BĂM NHỎ, KHÔNG LẶP, THIẾU ĐỂ TRỐNG, CHUẨN VẬT THỂ ===")
t_start = time.time()

out = thu_muc_du_an(du_an)[1]
canh_list = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
ds_canh_ct = chu_the.ds_canh(du_an)
ct_map = {c["id"]: c for c in ds_canh_ct}
cds = (doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("chu_de") or []
cd_map = {item["id"]: item.get("ten") or item.get("doi_tuong") for item in cds}
kho = dung_tay.doc_kho(du_an, quet=False)

import ban_dung
ban_dung.NHIP_TOI_THIEU = 2.0  # Băm nhỏ chuẩn nhịp 2.0s
bd_data = ban_dung.doc(du_an)

# 1. Tải SigLIP precomputed root embeddings & khởi tạo model
npz_path = "cache/chosoi_siglip_roots.npz"
if os.path.exists(npz_path):
    d_npz = np.load(npz_path)
    root_emb = {r: d_npz["e"][i] for i, r in enumerate(d_npz["roots"])}
    print(f"Đã tải {len(root_emb)} vector đặc trưng SigLIP từ {npz_path}")
else:
    root_emb = {}

prompt_human = ["a photo of a person, human face, woman, man, talking to camera, presenter, interview"]
e_human = nhung_siglip.nhung_chu(prompt_human)[0]

# 2. Bộ lọc loại bỏ 100% video dọc / Shorts / Pillarbox (Kiểm tra theo tệp gốc để tối ưu tốc độ)
def is_pillarbox_frame(frame):
    if frame is None:
        return True
    h, w, _ = frame.shape
    if w < h * 1.55:
        return True
    left = frame[:, :int(w * 0.12)]
    right = frame[:, int(w * 0.88):]
    center = frame[:, int(w * 0.35):int(w * 0.65)]
    if np.mean(left) < 22 and np.mean(right) < 22 and np.mean(center) > 28:
        return True
    return False

file_valid_cache = {}

def check_video_file(fp, title):
    if fp in file_valid_cache:
        return file_valid_cache[fp]
    if not os.path.isfile(fp):
        file_valid_cache[fp] = (False, 0, 0)
        return file_valid_cache[fp]
    
    # Lọc tiêu đề Shorts / TikTok
    t_low = (title + " " + fp).lower()
    if re.search(r"#shorts|\bshorts\b|\btiktok\b", t_low):
        file_valid_cache[fp] = (False, 0, 0)
        return file_valid_cache[fp]
    
    # Kiểm tra kích thước khung hình
    cap = cv2.VideoCapture(fp)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if w < h * 1.55:
        cap.release()
        file_valid_cache[fp] = (False, w, h)
        return file_valid_cache[fp]
    
    # Kiểm tra pillarbox
    ret, frame = cap.read()
    cap.release()
    if not ret or is_pillarbox_frame(frame):
        file_valid_cache[fp] = (False, w, h)
        return file_valid_cache[fp]
    
    file_valid_cache[fp] = (True, w, h)
    return file_valid_cache[fp]

print("Đang quét và kiểm tra tỉ lệ khung hình kho video...")
clean_clips = {}
for kid, v in kho.items():
    if v.get("loai") != "video" or kid.startswith("g_"):
        continue
    # Loại trừ tuyệt đối video kpW63PbyE00 (video dọc có viền đen người dùng phản ánh)
    if "kpW63PbyE00" in kid or "kpW63PbyE00" in v.get("video_goc", ""):
        continue
    fp = v.get("file", "")
    tieu_de = v.get("tieu_de", "")
    dur = float(v.get("dai") or 0.0)
    if dur < 1.8:
        continue
    
    valid, w, h = check_video_file(fp, tieu_de)
    if not valid:
        continue
    
    vg = str(v.get("video_goc") or "")
    root_id = "v_" + vg if not vg.startswith("v_") else vg
    if not vg:
        root_id = kid.rsplit("_", 1)[0]
    
    clean_clips[kid] = {
        "file": fp,
        "title": tieu_de,
        "dur": dur,
        "w": w,
        "h": h,
        "chu_de": v.get("chu_de"),
        "root_id": root_id
    }

print(f"Tổng số clip sạch 16:9 đạt chuẩn: {len(clean_clips)} clips")

# 3. Phân loại Chủ thể Clip
def classify_clip(kid, info):
    c_name = cd_map.get(info.get("chu_de"), "").lower()
    t = (info.get("title", "") + " " + info.get("root_id", "")).lower()
    all_s = f"{c_name} {t}"
    cats = set()
    if any(w in all_s for w in ["drone", "máy bay", "aerial", "thermal", "flycam", "ai drones", "vy1o6ajvd54", "b_bro3lobli"]):
        cats.add("DRONE")
    if any(w in all_s for w in ["camera", "surveillance", "monitoring", "fmc-ip1", "cctv", "security camera", "z3dthn-r2lm", "npgl4nrzfke"]):
        cats.add("CAMERA")
    if any(w in all_s for w in ["gps", "collar", "fencing", "virtual", "smartshepherd", "vòng cổ", "4ftw_si2kxu", "p8g0-2xk5ei"]):
        cats.add("VONG_CO")
    if any(w in all_s for w in ["kangal", "shepherd dog", "sheepdog", "guard dog", "chó", "chó chăn cừu", "dog that hunts wolves", "2dsvm4gfn74", "4hv2dft1weu", "53dzzm_98ac", "6tte13klghu", "7xk1lthg10", "8ss4zdx1utc", "8suvkn0ijmw", "9swtw_ethki", "cseycjlg98c", "dhis1irjj5e", "i4t_bcjlwwm", "jsopmimimda0", "mvz_umy0nhi", "q85elksah_q", "ruyoch9elvy", "rxnurmaqslq", "sxh49et-mr0", "scd25e0jh_e", "banepsp7hx4", "gntvd2yp6_0", "hkd0fwbsdto", "pa4unupd5yq"]):
        cats.add("CHO")
    if any(w in all_s for w in ["llama", "alpaca", "lạc đà", "1o_-lwr69sy", "_-htbs_qrbq"]):
        cats.add("LLAMA")
    if any(w in all_s for w in ["donkey", "kicked by her", "lừa", "donkey attacks", "gs6e3t-5its", "nr9womlqbbq", "a0gvyrjn8hy"]):
        cats.add("LUA")
    if any(w in all_s for w in ["porcupine", "hedgehog", "nhím", "xybjziydvtc", "6p4lt-siufu"]):
        cats.add("NHIM")
    if any(w in all_s for w in ["farmer", "ranch", "sorting 140 sheep", "selling vs", "farm success", "farm management", "nông dân", "cover crops", "vzutsgm-dvy", "8rkptmt-f2a", "fxovtryxyxw", "tmh265jmjag"]):
        cats.add("NONG_DAN")
    if any(w in all_s for w in ["boar", "wild boar", "piglets", "lợn rừng", "heo rừng", "txrkuaquijk"]):
        cats.add("LON_RUNG")
    if any(w in all_s for w in ["wolf", "wolves", "sói", "grey wolf", "cho soi", "fyaajvon6vdy", "hyuy61zfzas", "lnwmlnpqh08", "lwi9u3nz0lq", "aifjguvhzbc", "z3kv_kbry24", "yrujfpt1an8", "wcqvzivcokk", "r76gjdgp0uwq", "oixg82sfl5i", "yskzyvoqmua", "dgt0ftfyhl8", "-0cepasdara", "gb4cbzrayfy"]):
        cats.add("SOI")
    if any(w in all_s for w in ["sheep", "lamb", "flock", "grazing", "cừu", "pasture", "meadow", "grasses"]):
        cats.add("CUU")
    return cats

clip_cats = {kid: classify_clip(kid, info) for kid, info in clean_clips.items()}

# Bổ sung embedding cho các root chưa có
for kid, info in clean_clips.items():
    r = info["root_id"]
    if r not in root_emb and os.path.isfile(info["file"]):
        try:
            cap = cv2.VideoCapture(info["file"])
            tot = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, tot // 2)
            ret, fr = cap.read()
            cap.release()
            if ret and fr is not None:
                from PIL import Image
                rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
                im = Image.fromarray(rgb)
                root_emb[r] = nhung_siglip.nhung_anh([im])[0]
        except Exception:
            pass

# 4. Phân loại Chủ thể Cảnh & Đoạn câu
def xac_dinh_danh_muc_canh(ten_ct, text_cau):
    s_ct = str(ten_ct or "").lower()
    s_txt = str(text_cau or "").lower()
    if "chó" in s_ct: return "CHO"
    if "lừa" in s_ct: return "LUA"
    if "llama" in s_ct or "lạc đà" in s_ct: return "LLAMA"
    if "máy bay" in s_ct or "drone" in s_ct: return "DRONE"
    if "camera" in s_ct: return "CAMERA"
    if "vòng cổ" in s_ct: return "VONG_CO"
    if "nhím" in s_ct: return "NHIM"
    if "nông dân" in s_ct or "con người" in s_ct: return "NONG_DAN"
    if "sói" in s_ct: return "SOI"
    if "cừu" in s_ct or "đồng cỏ" in s_ct or "trang trại" in s_ct: return "CUU"
    if any(w in s_txt for w in ["máy bay", "drone", "cảm biến nhiệt"]): return "DRONE"
    if any(w in s_txt for w in ["camera", "giám sát", "cctv"]): return "CAMERA"
    if any(w in s_txt for w in ["vòng cổ", "thiết bị đeo", "hàng rào ảo"]): return "VONG_CO"
    if any(w in s_txt for w in ["chó chăn cừu", "chó bảo vệ", "chó kangal", "con chó", "đàn chó"]): return "CHO"
    if any(w in s_txt for w in ["lạc đà", "llama"]): return "LLAMA"
    if any(w in s_txt for w in ["loài lừa", "con lừa", "cú đá của con lừa"]): return "LUA"
    if any(w in s_txt for w in ["nhím", "lông gai"]): return "NHIM"
    if any(w in s_txt for w in ["nông dân", "hộ chăn nuôi", "chủ trang trại"]): return "NONG_DAN"
    if any(w in s_txt for w in ["sói", "dã thú", "kẻ săn mồi", "chó sói"]): return "SOI"
    if any(w in s_txt for w in ["cừu", "đàn cừu", "cừu non"]): return "CUU"
    return "SOI"

# 5. Gán nhịp với nguyên tắc: BĂM NHỎ (2s), KHÔNG DÙNG LẠI CLIP, THIẾU ĐỂ TRỐNG
used_clips = set()
cau_map = {}
tong_nhip = 0
nhip_co_hinh = 0
nhip_de_trong = 0

print("=== BẮT ĐẦU ĐIỀU PHỐI TỪNG NHỊP CÂU ===")

for c in canh_list:
    cid = c.get("id")
    cid_str = str(cid)
    text_cau = c.get("text", "")

    ct_item = ct_map.get(cid)
    ds_ten = ct_item.get("ds") if ct_item else []
    ten_ct = ds_ten[0] if ds_ten else "Chung"

    target_cat = xac_dinh_danh_muc_canh(ten_ct, text_cau)
    nhips = ban_dung.nhip_cua_cau(du_an, cid)
    clauses = [cl.strip() for cl in re.split(r"[,;]", text_cau) if cl.strip()]

    nhip_da_gan = []
    for i, n in enumerate(nhips):
        tong_nhip += 1
        clause_text = clauses[i] if i < len(clauses) else text_cau
        clause_lower = clause_text.lower()

        # Xác định vật thể chính xác nhắc tới trong nhịp
        beat_cat = target_cat
        if any(w in clause_lower for w in ["dê núi", "sừng nhọn", "sừng cứng"]):
            beat_cat = "DE_NUI"
        elif any(w in clause_lower for w in ["hươu", "nai"]):
            beat_cat = "HUOU"
        elif any(w in clause_lower for w in ["lợn rừng", "heo rừng"]):
            beat_cat = "LON_RUNG"
        elif any(w in clause_lower for w in ["chó", "chó chăn cừu", "kangal", "great pyrenees"]):
            beat_cat = "CHO"
        elif any(w in clause_lower for w in ["lừa", "con lừa"]):
            beat_cat = "LUA"
        elif any(w in clause_lower for w in ["llama", "lạc đà"]):
            beat_cat = "LLAMA"
        elif any(w in clause_lower for w in ["drone", "máy bay", "camera tầm nhiệt"]):
            beat_cat = "DRONE"
        elif any(w in clause_lower for w in ["camera", "giám sát", "cctv"]):
            beat_cat = "CAMERA"
        elif any(w in clause_lower for w in ["vòng cổ", "gps", "hàng rào ảo"]):
            beat_cat = "VONG_CO"
        elif any(w in clause_lower for w in ["nhím", "lông gai"]):
            beat_cat = "NHIM"

        # Lọc danh sách ứng viên hợp lệ: CHƯA DÙNG (DÙNG 1 LẦN DUY NHẤT)
        avail_candidates = []
        for kid, info in clean_clips.items():
            if kid in used_clips:
                continue  # KHÔNG CHO PHÉP DÙNG LẠI CLIP ĐÃ BĂM!
            if info["dur"] < n["dai"] - 0.5:
                continue
            k_cats = clip_cats.get(kid, set())

            if beat_cat in ["DE_NUI", "HUOU"]:
                # Không có trong kho -> ĐỂ TRỐNG chuẩn theo yêu cầu!
                continue
            elif beat_cat == "LON_RUNG":
                if "LON_RUNG" in k_cats:
                    avail_candidates.append(kid)
            elif beat_cat in ["CHO", "DRONE", "CAMERA", "VONG_CO", "LLAMA", "LUA", "NHIM"]:
                if beat_cat in k_cats:
                    avail_candidates.append(kid)
            elif beat_cat == "NONG_DAN":
                if "NONG_DAN" in k_cats or "CUU" in k_cats:
                    avail_candidates.append(kid)
            elif beat_cat == "SOI":
                if "SOI" in k_cats:
                    avail_candidates.append(kid)
            elif beat_cat == "CUU":
                if "CUU" in k_cats:
                    avail_candidates.append(kid)
            else:
                # Ngữ cảnh xung quanh được phép sử dụng kho xoay quanh vật thể chính
                if target_cat in k_cats:
                    avail_candidates.append(kid)

        if not avail_candidates:
            # "CHỖ CÒN THIẾU CẢNH ĐỂ TRỐNG"
            n["kho_id"] = None
            n["da_tai"] = False
            n["thieu"] = True
            n["chu_the"] = ten_ct
            nhip_da_gan.append(n)
            nhip_de_trong += 1
            continue

        # Chấm SigLIP
        vis_prompt = f"{ten_ct}, {clause_text}"
        try:
            e_q = nhung_siglip.nhung_chu([vis_prompt])[0]
        except Exception:
            e_q = None

        best_kid = None
        best_sc = -9999.0
        for kid in avail_candidates:
            r = clean_clips[kid]["root_id"]
            vec = root_emb.get(r)
            if vec is None:
                sc = 10.0
            else:
                h_sc = float(np.dot(vec, e_human))
                # Khử người đối với cảnh dã thú/động vật tự nhiên
                if beat_cat in ["SOI", "CUU"] and h_sc >= 0.045:
                    continue
                v_sc = float(np.dot(vec, e_q)) if e_q is not None else 0.5
                sc = v_sc * 40.0 - h_sc * 20.0

            if sc > best_sc:
                best_sc = sc
                best_kid = kid

        if not best_kid:
            best_kid = avail_candidates[0]

        used_clips.add(best_kid)
        m_info = kho.get(best_kid) or {}
        n["kho_id"] = best_kid
        n["da_tai"] = True
        n["thieu"] = False
        n["chu_the"] = ten_ct
        n["nguon"] = {
            "vid": m_info.get("video_goc", ""),
            "tieu_de": m_info.get("tieu_de", best_kid),
            "vao": float(m_info.get("giay_bat_dau") or 0.0),
            "ra": float(m_info.get("giay_ket_thuc") or (m_info.get("dai") or 3.0)),
            "file": m_info.get("file", "")
        }
        nhip_da_gan.append(n)
        nhip_co_hinh += 1

    cau_map[cid_str] = {
        "cach": "footage",
        "loai_goi_y": "quay_duoc",
        "tin_cay": "xanh" if all(not n.get("thieu") for n in nhip_da_gan) else "vang",
        "thieu": any(n.get("thieu") for n in nhip_da_gan),
        "chu_the": ten_ct,
        "nhip": nhip_da_gan,
        "sua_luc": time.time()
    }

bd_data["cau"] = cau_map
ban_dung.ghi(du_an, bd_data)
print(f"Tổng số nhịp: {tong_nhip} | Nhịp có hình chuẩn: {nhip_co_hinh} | Nhịp để trống: {nhip_de_trong}")

# 6. Đồng bộ sang dung.json (Các nhịp để trống hoàn toàn KHÔNG có trong danh sách đoạn)
dung_data = dung_tay.doc_dung(du_an)
for cid_str, c_info in cau_map.items():
    nhips = c_info.get("nhip") or []
    doan_list = []
    for n in nhips:
        kid = n.get("kho_id")
        if kid and not n.get("thieu") and kid in kho:
            doan_list.append({
                "loai": "video",
                "kho_id": kid,
                "file": kho[kid].get("file", ""),
                "vao": 0.0,
                "bd": float(n.get("bd", 0.0)),
                "dai": float(n.get("dai", 3.0))
            })
    dung_data[str(cid_str)] = {"doan": doan_list, "ban_dung": True, "goi_y": False, "luc": time.time()}

common.ghi_json(os.path.join(out, "dung.json"), dung_data)
print("Đã lưu dung.json!")

# 7. Ghi đè bản nháp CapCut
drafts_dir = r"D:\CapCut\Draft\CapCut Drafts"
draft_name = "chosoi_hoan_chinh"
print(f"Ghi đè bản nháp CapCut '{draft_name}'...")
n_segs = dung_tay.tao_nhap(du_an, draft_name, drafts_dir)
print(f"=== ĐIỀU PHỐI HOÀN TẤT THÀNH CÔNG! Tạo {n_segs} segments trong CapCut ({time.time()-t_start:.2f}s) ===")
