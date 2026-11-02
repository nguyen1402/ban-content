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

du_an = "chosoi"
print(f"=== BẮT ĐẦU ĐIỀU PHỐI DỰNG THÔNG MINH THEO CHỦ THỂ (SMART ACT-BASED) CHO '{du_an}' ===")
t0 = time.time()

out = thu_muc_du_an(du_an)[1]
canh_list = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
ds_canh_ct = chu_the.ds_canh(du_an)
ct_map = {c["id"]: c for c in ds_canh_ct}
tt_cau = chu_the.trang_thai_cau(du_an)
cds = (doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("chu_de") or []
cd_map = {item["id"]: item.get("ten") or item.get("doi_tuong") for item in cds}
kho = dung_tay.doc_kho(du_an, quet=False)

# 1. Danh sách clean roots đã lọc kỹ thuật
import ban_dung
bd_data = ban_dung.doc(du_an)

# Nạp SigLIP cache
siglip_cache_file = os.path.join(common.CACHE_CHUNG, f"{du_an}_siglip_roots.npz")
if not os.path.isfile(siglip_cache_file):
    siglip_cache_file = "cache/chosoi_siglip_roots.npz"
data = np.load(siglip_cache_file)
cached_roots = list(data["roots"])
e_roots_matrix = data["e"]
root_idx_map = {r: i for i, r in enumerate(cached_roots)}

# 2. Phân loại từng video root trong kho theo Chủ thể thực tế
def classify_root(r):
    clips = []
    for kid, m in kho.items():
        if kid.startswith(r) or m.get("file", "").find(r) != -1:
            clips.append((kid, m.get("file", ""), m.get("tieu_de", ""), m.get("chu_de")))
    c_names = [cd_map.get(c[3], "") for c in clips if c[3]]
    titles = [c[2] for c in clips]
    all_s = (" ".join(c_names + titles)).lower()
    cats = set()
    if any(w in all_s for w in ["drone", "máy bay", "aerial", "thermal", "flycam", "ai drones"]):
        cats.add("DRONE")
    if any(w in all_s for w in ["camera", "surveillance", "monitoring", "fmc-ip1", "cctv", "security camera"]):
        cats.add("CAMERA")
    if any(w in all_s for w in ["gps", "collar", "fencing", "virtual", "smartshepherd", "vòng cổ"]):
        cats.add("VONG_CO")
    if any(w in all_s for w in ["kangal", "shepherd dog", "sheepdog", "guard dog", "chó", "chó chăn cừu", "dog that hunts wolves"]):
        cats.add("CHO")
    if any(w in all_s for w in ["llama", "alpaca", "lạc đà"]):
        cats.add("LLAMA")
    if any(w in all_s for w in ["donkey", "kicked by her", "lừa", "donkey attacks"]):
        cats.add("LUA")
    if any(w in all_s for w in ["porcupine", "hedgehog", "nhím"]):
        cats.add("NHIM")
    if any(w in all_s for w in ["farmer", "ranch", "sorting 140 sheep", "selling vs", "farm success", "farm management", "nông dân", "cover crops"]):
        cats.add("NONG_DAN")
    if any(w in all_s for w in ["wolf", "wolves", "sói", "grey wolf", "cho soi"]):
        cats.add("SOI")
    if any(w in all_s for w in ["sheep", "lamb", "flock", "grazing", "cừu", "pasture", "meadow", "grasses"]):
        cats.add("CUU")
    return cats

root_cats = {r: classify_root(r) for r in cached_roots}

# 3. Phân loại Chủ thể của từng cảnh
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

# Vectorize Negative Person Prompt
prompt_human = ["a photo of a person, human face, woman, man, talking to camera, presenter, interview"]
e_human = nhung_siglip.nhung_chu(prompt_human)
human_scores = (e_roots_matrix @ e_human.T).squeeze()

cau_map = bd_data.setdefault("cau", {})
used_counts = Counter()
last_root = None
recent_roots = []

print("=== TIẾN HÀNH ĐIỀU PHỐI THEO CHỦ THỂ CỦA TỪNG CẢNH ===")
da_phu = 0

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
        clause_text = clauses[i] if i < len(clauses) else text_cau
        vis_prompt = f"{ten_ct}, {clause_text}"
        e_query = nhung_siglip.nhung_chu([vis_prompt])[0]
        vis_scores = (e_roots_matrix @ e_query).squeeze()

        scores = []
        for idx, r in enumerate(cached_roots):
            r_cats = root_cats.get(r, set())
            v_sc = float(vis_scores[idx])
            h_sc = float(human_scores[idx])

            # 1. KHÓA CỨNG CHỦ THỂ (Category Strict Router)
            if target_cat in ["CHO", "DRONE", "CAMERA", "VONG_CO", "LLAMA", "LUA", "NHIM"]:
                if target_cat not in r_cats:
                    continue  # Không đúng chủ thể chuyên biệt -> LOẠI THẲNG TAY
                sc = v_sc * 40.0 + 30.0
            elif target_cat == "NONG_DAN":
                if "NONG_DAN" in r_cats or "CUU" in r_cats:
                    sc = v_sc * 40.0 + 15.0
                elif "SOI" in r_cats:
                    continue  # Cảnh nông dân không được chiếu sói
                else:
                    sc = v_sc * 40.0
            elif target_cat == "SOI":
                if "SOI" not in r_cats:
                    continue  # Cảnh sói chỉ lấy sói
                if h_sc >= 0.055 or h_sc > v_sc:
                    continue  # Zero-Human Gatekeeper
                sc = v_sc * 40.0 + 20.0
            elif target_cat == "CUU":
                if "CUU" not in r_cats:
                    continue  # Cảnh cừu chỉ lấy cừu
                if h_sc >= 0.055 or h_sc > v_sc:
                    continue  # Zero-Human Gatekeeper
                sc = v_sc * 40.0 + 20.0
            else:
                sc = v_sc * 40.0

            # 2. Trần cứng số lần dùng (Hard Cap: tối đa 4 lần / video gốc)
            if used_counts[r] >= 4:
                sc -= 9999.0

            # 3. Chống lặp liên tiếp
            if last_root and r == last_root:
                sc -= 9999.0

            # 4. Hồi chiêu 20 cảnh
            if r in recent_roots:
                idx_from_end = len(recent_roots) - 1 - recent_roots.index(r)
                if idx_from_end < 20:
                    sc -= 4.0 * (20 - idx_from_end)

            # 5. Phạt tần suất mạnh
            sc -= 3.0 * used_counts[r]
            scores.append((r, sc))

        if not scores:
            # Fallback nếu hết slot: nới lỏng trần cứng
            scores = [(r, float(vis_scores[idx]) * 40.0 - 2.0 * used_counts[r]) for idx, r in enumerate(cached_roots) if (r != last_root)]

        scores.sort(key=lambda x: x[1], reverse=True)
        chosen_root = scores[0][0]

        # Tìm clip hợp lệ trong chosen_root
        clips_in_root = [k for k, m in kho.items() if (k.startswith(chosen_root) or m.get("file", "").find(chosen_root) != -1) and m.get("loai") == "video" and not m.get("file", "").endswith(".png")]
        valid_clips = [k for k in clips_in_root if float(kho[k].get("dai") or 0) >= n["dai"] - 0.5]
        if not valid_clips:
            valid_clips = clips_in_root if clips_in_root else [chosen_root]

        chosen_clip = min(valid_clips, key=lambda k: used_counts[k])

        used_counts[chosen_root] += 1
        used_counts[chosen_clip] += 1
        last_root = chosen_root
        recent_roots.append(chosen_root)
        if len(recent_roots) > 22:
            recent_roots.pop(0)

        m_info = kho.get(chosen_clip) or {}
        n["kho_id"] = chosen_clip
        n["da_tai"] = True
        n["thieu"] = False
        n["chu_the"] = ten_ct
        n["nguon"] = {
            "vid": m_info.get("video_goc", ""),
            "tieu_de": m_info.get("tieu_de", chosen_clip),
            "vao": float(m_info.get("giay_bat_dau") or 0.0),
            "ra": float(m_info.get("giay_ket_thuc") or (m_info.get("dai") or 3.0)),
            "file": m_info.get("file", "")
        }
        nhip_da_gan.append(n)

    cau_map[cid_str] = {
        "cach": "footage",
        "loai_goi_y": "quay_duoc",
        "tin_cay": "xanh",
        "thieu": False,
        "chu_the": ten_ct,
        "nhip": nhip_da_gan,
        "sua_luc": time.time()
    }
    da_phu += 1

ban_dung.ghi(du_an, bd_data)
print(f"Đã gán xong {da_phu}/{len(canh_list)} câu chuẩn theo Chủ thể!")

# 4. Đồng bộ sang dung.json
dung_data = dung_tay.doc_dung(du_an)
for cid_str, c_info in cau_map.items():
    if not c_info.get("nhip"):
        continue
    doan_list = []
    for n in c_info["nhip"]:
        kid = n.get("kho_id")
        if kid and kid in kho:
            doan_list.append({
                "loai": "video",
                "kho_id": kid,
                "file": kho[kid].get("file", ""),
                "vao": 0.0,
                "bd": float(n.get("bd", 0.0)),
                "dai": float(n.get("dai", 3.0))
            })
    if doan_list:
        dung_data[str(cid_str)] = {"doan": doan_list, "ban_dung": True, "goi_y": False, "luc": time.time()}

common.ghi_json(os.path.join(out, "dung.json"), dung_data)
print("Đã lưu dung.json!")

# 5. Ghi đè bản nháp CapCut
drafts_dir = r"D:\CapCut\Draft\CapCut Drafts"
draft_name = "chosoi_hoan_chinh"
print(f"Ghi đè bản nháp CapCut '{draft_name}'...")
draft_path = dung_tay.tao_nhap(du_an, draft_name, drafts_dir)
print(f"=== HOÀN TẤT GHI ĐÈ BẢN NHÁP CAPCUT THÀNH CÔNG trong {time.time()-t0:.2f}s! ===")

