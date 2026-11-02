# -*- coding: utf-8 -*-
import sys
import time
import os
import json
import re
from collections import Counter
import numpy as np

import common
from common import doc_json, ghi_json, log, thu_muc_du_an
import dung_tay
import chu_the
import nhung_siglip
import goi_y

du_an = "chosoi"
print("=== BẮT ĐẦU ĐIỀU PHỐI: BĂM DÀY THEO NGẮT GIỌNG THỰC TẾ & CHẤM CHỦ THỂ SIÊU CHUẨN ===")
t_start = time.time()

# 1. Cấu hình BĂM DÀY theo ngắt giọng thực tế
goi_y.DOAN_GOP_NGAN = 1.2   # Chỗ ngắt nghỉ thực tế >= 1.2s là băm chuyển cảnh
goi_y.DOAN_MAX_NGHI = 3.5   # Không để cảnh nào đứng hình quá 3.5s
import ban_dung
ban_dung.NHIP_TOI_THIEU = 1.2

out = thu_muc_du_an(du_an)[1]
canh_list = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
ds_canh_ct = chu_the.ds_canh(du_an)
ct_map = {c["id"]: c for c in ds_canh_ct}
cds = (doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("chu_de") or []
cd_map = {item["id"]: item.get("ten") or item.get("doi_tuong") for item in cds}
kho = dung_tay.doc_kho(du_an, quet=False)
bd_data = ban_dung.doc(du_an)

# 2. Tải chỉ mục thị giác cấp mảnh (1616 clips, 1152 chiều)
cache_file = os.path.join("cache", "du_an", du_an, "chi_muc_manh_clip.npz")
if not os.path.exists(cache_file):
    raise FileNotFoundError(f"Chưa có tệp chỉ mục {cache_file}")

d_idx = np.load(cache_file)
idx_kids = list(d_idx["kids"])
feats = d_idx["e"].astype(np.float32)
clip_vec_map = {k: feats[i] for i, k in enumerate(idx_kids)}
print(f"Đã nạp {len(clip_vec_map)} vector thị giác thực tế của từng mảnh clip từ cache!")

# 3. Chuẩn bị Vector Khái niệm Thị giác chuẩn
QUERIES = {
    "WOLF": "a photo of a wild wolf, grey wolf pack in nature",
    "WOLF_HUNT": "a photo of wild wolves hunting, wolf chasing attacking running after prey in nature",
    "SHEEP": "a photo of a flock of sheep grazing, white sheep in green pasture meadow",
    "FARM": "a photo of a sheep farm ranch, pastoral farmland, barn, livestock pasture landscape",
    "DOG": "a photo of a shepherd dog, guard dog, kangal dog protecting sheep",
    "DONKEY": "a photo of a donkey in pasture, donkey kicking fighting predator",
    "LLAMA": "a photo of a llama, alpaca in pasture standing with sheep flock",
    "BOAR": "a photo of a wild boar, wild pig with tusks in nature",
    "PORCUPINE": "a photo of a porcupine with sharp defensive quills in wild",
    "DRONE": "a photo of a drone flying, aerial view from drone of farm, thermal camera drone",
    "CAMERA": "a photo of a security surveillance camera cctv on farm pole",
    "COLLAR": "a photo of sheep wearing gps tracking collar, smart livestock collar",
    "HUMAN": "a photo of a person, human face, presenter talking to camera, interview in studio",
    "EAGLE": "a photo of a flying bird, golden eagle, bird raptor flying with wings"
}

q_keys = list(QUERIES.keys())
q_texts = [QUERIES[k] for k in q_keys]
E_all = nhung_siglip.nhung_chu(q_texts)
E_map = {q_keys[i]: E_all[i] for i in range(len(q_keys))}
print("Đã tính xong các vector truy vấn thị giác.")

# Ma trận tương đồng của toàn bộ kho với các khái niệm
sim_matrix = feats @ E_all.T
q_idx = {k: i for i, k in enumerate(q_keys)}

# Phân loại clip kết hợp chính xác giữa nguồn gốc & hình ảnh thật
clean_clips = {}
clip_cats = {}
clip_roots = {}

for i, kid in enumerate(idx_kids):
    v = kho.get(kid)
    if not v:
        continue
    vg = str(v.get("video_goc") or "")
    root_id = "v_" + vg if not vg.startswith("v_") else vg
    if not vg:
        root_id = kid.rsplit("_", 1)[0]
    
    clean_clips[kid] = v
    clip_roots[kid] = root_id

    row = sim_matrix[i]
    w_sc = row[q_idx["WOLF"]]
    s_sc = row[q_idx["SHEEP"]]
    f_sc = row[q_idx["FARM"]]
    d_sc = row[q_idx["DOG"]]
    dnk_sc = row[q_idx["DONKEY"]]
    llm_sc = row[q_idx["LLAMA"]]
    boar_sc = row[q_idx["BOAR"]]
    porc_sc = row[q_idx["PORCUPINE"]]
    h_sc = row[q_idx["HUMAN"]]
    eag_sc = row[q_idx["EAGLE"]]

    c_name = cd_map.get(v.get("chu_de"), "").lower()
    t = (v.get("tieu_de", "") + " " + root_id).lower()
    all_s = f"{c_name} {t}"

    cats = set()

    # SÓI: Từ nguồn sói VÀ trong hình không dính người / đại bàng
    if any(w in all_s for w in ["wolf", "wolves", "sói", "drlq2jzbzvc", "z3kv_kbry24", "fyaajvon6vdy", "hyuy61zfzas", "lnwmlnpqh08", "lwi9u3nz0lq", "aifjguvhzbc", "yrujfpt1an8", "wcqvzivcokk", "r76gjdgp0uwq", "oixg82sfl5i", "yskzyvoqmua", "dgt0ftfyhl8", "-0cepasdara", "gb4cbzrayfy", "wp63knm9bki", "hkd0fwbsdto", "4_bqqezqojw"]):
        if w_sc > h_sc and w_sc > eag_sc and h_sc < 0.045:
            cats.add("SOI")

    # CỪU: Từ nguồn cừu VÀ không dính người
    if any(w in all_s for w in ["sheep", "lamb", "cừu", "flock", "i1tvyozeew4", "vwilk16j_e4", "orakrywrmcg", "banepsp7hx4", "qgq6-eurf7a", "cseycjlg98c", "0t-bwqybq7e", "5tfbpbs7vru", "7fjdufy2lpk", "d7lw6ht0jk0", "mgbukvm3rty", "sngthh1ivay", "unfpp0zcvna", "vrb0bbtejqg"]):
        if s_sc > h_sc and h_sc < 0.05:
            cats.add("CUU")

    # TRANG TRẠI: Bối cảnh nông trại / đồng cỏ
    if any(w in all_s for w in ["farm", "pasture", "ranch", "meadow", "trang trại", "đồng cỏ", "nông dân", "cover crops", "vzutsgm-dvy", "8rkptmt-f2a", "fxovtryxyxw", "tmh265jmjag"]):
        cats.add("TRANG_TRAI")

    # CHÓ: Chó chăn cừu / Kangal
    if any(w in all_s for w in ["kangal", "shepherd dog", "sheepdog", "guard dog", "chó", "chó chăn cừu", "dog that hunts wolves", "53dzzm_98ac", "_7wx4moecl0", "vqd0fhuhd3w", "tq10kjtvesk", "2dsvm4gfn74", "4hv2dft1weu", "dhis1irjj5e", "i4t_bcjlwwm", "jsopmimimda0"]):
        cats.add("CHO")

    # LỪA
    if any(w in all_s for w in ["donkey", "lừa", "gs6e3t-5its", "a0gvyrjn8hy", "nr9womlqbbq"]):
        cats.add("LUA")

    # LLAMA
    if any(w in all_s for w in ["llama", "alpaca", "lạc đà", "1o_-lwr69sy", "_-htbs_qrbq"]):
        cats.add("LLAMA")

    # LỢN RỪNG: Khóa chặt vào nguồn video lợn rừng thật txRKUAquIjk
    if any(w in all_s for w in ["txrkuaquijk", "wild boar", "lợn rừng", "heo rừng"]) and "sheep" not in all_s and "lamb" not in all_s:
        cats.add("LON_RUNG")

    # NHÍM
    if any(w in all_s for w in ["porcupine", "hedgehog", "nhím", "xybjziydvtc", "6p4lt-siufu"]):
        cats.add("NHIM")

    # DRONE
    if any(w in all_s for w in ["drone", "máy bay", "aerial", "thermal", "flycam", "ai drones", "vy1o6ajvd54", "b_bro3lobli", "i8sjxdpch04"]):
        cats.add("DRONE")

    # CAMERA
    if any(w in all_s for w in ["camera", "surveillance", "monitoring", "fmc-ip1", "cctv", "security camera", "z3dthn-r2lm", "mvz_umy0nhi", "sqjfs18xzay", "npgl4nrzfke"]):
        cats.add("CAMERA")

    # VÒNG CỔ
    if any(w in all_s for w in ["gps", "collar", "fencing", "virtual", "smartshepherd", "vòng cổ", "4ftw_si2kxu", "8suvkn0ijmw", "p8g0-2xk5ei"]):
        cats.add("VONG_CO")

    clip_cats[kid] = cats

print(f"Tổng số clip sẵn sàng: {len(clean_clips)} clips")

# 4. Phân loại Khái niệm từng nhịp
def xac_dinh_khai_niem_cau(ten_ct, text_cau, current_context):
    s_ct = str(ten_ct or "").lower()
    s_txt = str(text_cau or "").lower()
    
    if any(w in s_txt for w in ["dê núi", "sừng nhọn", "sừng cứng"]):
        return "DE_NUI", current_context
    if any(w in s_txt for w in ["hươu", "nai", "hàng chục km mỗi giờ"]):
        return "HUOU", current_context
    if any(w in s_txt for w in ["lợn rừng", "heo rừng"]):
        return "LON_RUNG", "LON_RUNG"
    if any(w in s_txt for w in ["nhím", "lông gai", "chiếc gai"]):
        return "NHIM", "NHIM"
    if any(w in s_txt for w in ["lừa", "con lừa", "cú đá"]):
        return "LUA", "LUA"
    if any(w in s_txt for w in ["llama", "lạc đà"]):
        return "LLAMA", "LLAMA"
    if any(w in s_txt for w in ["máy bay", "drone", "camera tầm nhiệt"]):
        return "DRONE", "DRONE"
    if any(w in s_txt for w in ["camera", "giám sát", "cctv"]):
        return "CAMERA", "CAMERA"
    if any(w in s_txt for w in ["vòng cổ", "thiết bị đeo", "hàng rào ảo", "gps"]):
        return "VONG_CO", "VONG_CO"
    if any(w in s_txt for w in ["chó chăn cừu", "chó bảo vệ", "chó kangal", "great pyrenees", "đàn chó", "con chó", "tiếng sủa"]):
        return "CHO", "CHO"

    if any(w in s_txt for w in ["săn mồi", "lao vào tấn công", "rình rập", "chọn con mồi", "ngoạm chặt", "xé xác", "bài toán về năng lượng", "cuộc tấn công"]):
        return "WOLF_HUNT", "SOI"

    if any(w in s_txt for w in ["sói", "dã thú", "kẻ săn mồi", "chó sói", "chiếc răng", "bộ hàm"]):
        return "WOLF", "SOI"

    if any(w in s_txt for w in ["cừu", "đàn cừu", "cừu non", "con mồi"]):
        return "SHEEP", "CUU"

    if any(w in s_txt for w in ["nông dân", "trang trại", "chuồng", "hàng rào", "đồng cỏ rộng", "hộ chăn nuôi", "người chăn nuôi", "nghiên cứu"]):
        return "FARM", "TRANG_TRAI"

    inherited = current_context or "TRANG_TRAI"
    if inherited == "SOI":
        return "WOLF", "SOI"
    elif inherited == "CUU":
        return "SHEEP", "CUU"
    return "FARM", inherited

# 5. ĐIỀU PHỐI VỚI NGUYÊN TẮC BĂM DÀY, KHÔNG DÙNG LẠI CLIP, KHÓA KHOẢNG CÁCH NGUỒN
KACH_XA_CANH = 3
root_last_scene = {}
used_clips = set()
cau_map = {}
tong_nhip = 0
nhip_co_hinh = 0
nhip_de_trong = 0
current_context = "SOI"

print(f"=== BẮT ĐẦU ĐIỀU PHỐI BĂM DÀY DÀI TRÊN 500+ NHỊP ===")

for s_idx, c in enumerate(canh_list, start=1):
    cid = c.get("id")
    cid_str = str(cid)
    text_cau = c.get("text", "")

    ct_item = ct_map.get(cid)
    ds_ten = ct_item.get("ds") if ct_item else []
    ten_ct = ds_ten[0] if ds_ten else "Chung"

    nhips = ban_dung.nhip_cua_cau(du_an, cid)
    clauses = [cl.strip() for cl in re.split(r"[,;]", text_cau) if cl.strip()]

    nhip_da_gan = []
    for i, n in enumerate(nhips):
        tong_nhip += 1
        clause_text = clauses[i] if i < len(clauses) else text_cau

        concept, current_context = xac_dinh_khai_niem_cau(ten_ct, clause_text, current_context)

        avail_candidates = []
        if concept in ["DE_NUI", "HUOU"]:
            pass
        else:
            cat_target = "SOI" if concept in ["WOLF", "WOLF_HUNT"] else "CUU" if concept == "SHEEP" else "TRANG_TRAI" if concept == "FARM" else concept

            for kid, info in clean_clips.items():
                if kid in used_clips:
                    continue
                dur = float(info.get("dai") or 0.0)
                if dur < n["dai"] - 0.4:
                    continue

                r_id = clip_roots[kid]
                last_used_s = root_last_scene.get(r_id, -999)
                if (s_idx - last_used_s) < KACH_XA_CANH:
                    continue

                k_cats = clip_cats.get(kid, set())
                if cat_target in k_cats:
                    avail_candidates.append(kid)
                elif cat_target == "TRANG_TRAI" and ("CUU" in k_cats or "TRANG_TRAI" in k_cats):
                    avail_candidates.append(kid)
                elif cat_target == "CUU" and ("CUU" in k_cats or "TRANG_TRAI" in k_cats):
                    avail_candidates.append(kid)

            # Nới lỏng tạm nếu do khoảng cách nguồn mà không còn ứng viên
            if not avail_candidates and concept not in ["DE_NUI", "HUOU"]:
                for kid, info in clean_clips.items():
                    if kid in used_clips:
                        continue
                    dur = float(info.get("dai") or 0.0)
                    if dur < n["dai"] - 0.4:
                        continue
                    k_cats = clip_cats.get(kid, set())
                    if cat_target in k_cats:
                        avail_candidates.append(kid)

        if not avail_candidates:
            n["kho_id"] = None
            n["da_tai"] = False
            n["thieu"] = True
            n["chu_the"] = ten_ct
            nhip_da_gan.append(n)
            nhip_de_trong += 1
            continue

        target_vec = E_map.get(concept, E_map["SHEEP"])

        best_kid = None
        best_sc = -9999.0
        for kid in avail_candidates:
            cand_vec = clip_vec_map.get(kid)
            if cand_vec is None:
                continue

            v_sc = float(np.dot(cand_vec, target_vec))
            h_sc = float(np.dot(cand_vec, E_map["HUMAN"]))
            eagle_sc = float(np.dot(cand_vec, E_map["EAGLE"]))

            if concept in ["WOLF", "WOLF_HUNT", "SHEEP", "LON_RUNG"] and h_sc >= 0.045:
                continue

            if concept in ["WOLF", "WOLF_HUNT", "SHEEP"] and eagle_sc > v_sc:
                continue

            sc = v_sc * 60.0 - h_sc * 30.0 - eagle_sc * 25.0
            if sc > best_sc:
                best_sc = sc
                best_kid = kid

        if not best_kid:
            best_kid = avail_candidates[0]

        used_clips.add(best_kid)
        r_id = clip_roots[best_kid]
        root_last_scene[r_id] = s_idx

        m_info = kho.get(best_kid) or {}
        n["kho_id"] = best_kid
        n["da_tai"] = True
        n["thieu"] = False
        n["chu_the"] = ten_ct
        n["khai_niem"] = concept
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
print(f"Tổng số nhịp băm dày: {tong_nhip} | Nhịp có hình chuẩn: {nhip_co_hinh} | Nhịp để trống: {nhip_de_trong}")

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