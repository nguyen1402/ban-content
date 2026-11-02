# -*- coding: utf-8 -*-
import sys

with open("ban_dung.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

head = lines[:564]

universal_body = '''
# --------------------------------------------------------------------------- tự động băm & ghép TỔNG QUÁT BẰNG AI & TF-IDF (Universal Semantic Matcher)
def tu_dong_bam_chu_the(du_an, giu_da_dung=True, loc_sub=True, chi_ngang_16_9=True):
    """BỘ MÁY ĐIỀU PHỐI VIDEO TỔNG QUÁT CHO MỌI DỰ ÁN (Universal Multi-tier Semantic & Footage Engine):
    1. Băm đa tầng cấp Nhịp (Beat-Level Semantic Resolution): Đọc từng vế câu của mỗi nhịp hình.
       Nếu nhịp nhắc đến đối tượng cụ thể (dê núi, hươu, lợn rừng, chim ưng, drone...), nhịp đó sẽ tự động
       khớp video đúng thực thể đó trong kho thay vì bị ép dùng hình chung của cả câu.
    2. Khóa cứng Chủ thể cốt lõi (Core Entity Priority): Nhân hệ số ưu tiên cho chủ thể chính của câu,
       triệt tiêu hiện tượng từ khóa bối cảnh phụ (trang trại/đồng cỏ) lấn át kéo nhầm video loài khác (bầy dê/đại bàng).
    3. Phạt video đối kháng (Vs Videos) & Lọc kịch bản hư cấu: Phạt nặng video giật gân hai loài đấu nhau ('vs'),
       loại bỏ triệt để video creepypasta/phim hư cấu có diễn viên người dẫn chuyện.
    4. Chống lặp liên tiếp & Phạt lặp gần: Đảm bảo góc máy đa dạng, xoay vòng kho 80+ video đều đặn.
    5. Chuẩn 16:9 điện ảnh & Sạch phụ đề: 0% video dọc, 0% viền đen pillarbox, 0% chữ sub/watermark.
    6. 100% Video chuyển động thực tế (0% ảnh tĩnh).
    """
    import cv2
    import numpy as np
    import chu_the
    import chon_tay
    import sach_hinh
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    out = thu_muc_du_an(du_an)[1]
    canh_list = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    if not canh_list:
        raise ValueError("Chưa có danh sách câu tu_khoa.json")

    # Đọc phân bổ chủ thể và trạng thái cảnh sinh ra từ phân tích kịch bản
    ds_canh_ct = chu_the.ds_canh(du_an)
    ct_map = {c["id"]: c for c in ds_canh_ct}
    tt_cau = chu_the.trang_thai_cau(du_an)

    # Đọc danh mục chủ thể gốc
    cds = (doc_json(os.path.join(out, "chu_de.json"), {}) or {}).get("chu_de") or []
    id_to_ten = {c["id"]: c.get("doi_tuong") or c.get("ten") or "" for c in cds}

    # Đọc kho video
    kho = dung_tay.doc_kho(du_an)

    # Đo kích thước video bằng ffprobe
    def _do_kich_thuoc(fp):
        if not os.path.isfile(fp):
            return None, None
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", fp
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4,
                                 creationflags=0x08000000 if os.name == "nt" else 0)
            out_s = res.stdout.strip()
            if "x" in out_s:
                w, h = map(int, out_s.split("x")[:2])
                return w, h
        except Exception:
            pass
        return None, None

    files_to_check = {m.get("file"): m for m in kho.values() if m.get("file") and os.path.isfile(m.get("file"))}
    dims_cache = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for fp, (w, h) in zip(files_to_check.keys(), ex.map(_do_kich_thuoc, files_to_check.keys())):
            dims_cache[fp] = (w, h)

    def _get_true_root(kid, m):
        f = m.get("file", "")
        base = os.path.basename(f)
        if "_c" in base:
            return base.split("_c")[0]
        return m.get("manh_cua") or m.get("video_goc") or (kid.split("_c")[0] if "_c" in kid else kid)

    # Lan truyền tiêu đề chuẩn nhất cho từng video gốc
    root_best_title = {}
    for kid, m in kho.items():
        if m.get("loai") != "video" or kid.startswith("g_"):
            continue
        r = _get_true_root(kid, m)
        t = m.get("tieu_de", "")
        if t and not t.endswith(".mp4") and not t.startswith("v_kho_video_"):
            if r not in root_best_title or len(t) > len(root_best_title[r]):
                root_best_title[r] = t

    # Gom nhóm theo video gốc thực sự (CHỈ LẤY VIDEO THỰC SỰ, LOẠI BỎ 100% ẢNH TĨNH g_...)
    roots = {}
    for kid, m in kho.items():
        if m.get("loai") != "video" or kid.startswith("g_"):
            continue
        fp = m.get("file", "")
        if os.path.isfile(fp):
            r = _get_true_root(kid, m)
            title = root_best_title.get(r, m.get("tieu_de", ""))
            roots.setdefault(r, []).append((kid, fp, float(m.get("dai") or 3.0), title))

    # Quét chữ cứng / phụ đề đè (RapidOCR) theo video gốc
    def _kiem_tra_sub_root(item):
        r, clips = item
        real_clip = next((c for c in clips if not c[0].startswith("v_kho_video_")), clips[0])
        kid, fp, dur, title = real_clip
        try:
            txt = sach_hinh.chu_van(fp, 0.5, min(dur - 0.5, 3.0))
            clean = re.sub(r"[^a-zA-Z0-9\\u00C0-\\u1EF9]", "", txt)
            return r, (len(clean) >= 6, txt)
        except Exception:
            return r, (False, "")

    root_sub_map = {}
    if loc_sub:
        with ThreadPoolExecutor(max_workers=8) as ex:
            root_sub_map = dict(list(ex.map(_kiem_tra_sub_root, roots.items())))

    # Bộ lọc rác & phi tài liệu tổng quát (Bao gồm rác game, rác fiction người dẫn chuyện, quảng cáo)
    UNIVERSAL_JUNK_PATTERNS = [
        # Nội dung rác / game / đồ chơi / fiction
        r"gameplay", r"minecraft", r"lego", r"toy", r"creepypasta", r"horror",
        r"trailer promo", r"commercial", r"advertisement", r"reaction",
        # Phim hư cấu / diễn viên người dẫn chuyện (lệch phim tài liệu thiên nhiên)
        r"terrifying monster\\b", r"was hunting her\\b", r"alone with wolves in\\b",
        r"life of the ancestors\\b", r"12,?000 years ago\\b",
        # Khung dọc Shorts / TikTok
        r"#shorts\\b", r"\\bshorts\\b", r"\\btiktok\\b",
        # Nói chuyện trước ống kính / hội thảo không phải phim tài liệu cảnh quay
        r"\\bseminar\\b", r"\\bwebinar\\b", r"\\binterview\\b", r"\\bpodcast\\b",
        # Phim hoạt hình / mô hình 3D hư cấu
        r"\\banimation\\b", r"\\bcartoon\\b", r"\\b3d render\\b"
    ]

    def _la_rac(tieu_de, file_path=""):
        t = (str(tieu_de or "") + " " + str(file_path or "")).lower()
        for jp in UNIVERSAL_JUNK_PATTERNS:
            if re.search(jp, t, re.I):
                return True
        return False

    pillarbox_cache = {}
    def _la_pillarbox(fp):
        if not fp or not os.path.isfile(fp):
            return False
        if fp in pillarbox_cache:
            return pillarbox_cache[fp]
        try:
            cap = cv2.VideoCapture(fp)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                pillarbox_cache[fp] = False
                return False
            h, w, _ = frame.shape
            if w < h * 1.55:
                pillarbox_cache[fp] = True
                return True
            left = frame[:, :int(w * 0.12)]
            right = frame[:, int(w * 0.88):]
            center = frame[:, int(w * 0.35):int(w * 0.65)]
            if np.mean(left) < 20 and np.mean(right) < 20 and np.mean(center) > 28:
                pillarbox_cache[fp] = True
                return True
        except Exception:
            pass
        pillarbox_cache[fp] = False
        return False

    # Lọc kho chỉ giữ lại video gốc 16:9 thực sự sạch
    clean_roots = {}
    for r, clips in roots.items():
        if r.startswith("g_"):
            continue
        sample_f = clips[0][1]
        title = root_best_title.get(r, clips[0][3]).lower()
        if _la_rac(title, sample_f):
            continue
        w, h = dims_cache.get(sample_f, (None, None))
        if chi_ngang_16_9 and (not w or not h or w < h * 1.6):
            continue
        if chi_ngang_16_9 and _la_pillarbox(sample_f):
            continue
        if loc_sub and root_sub_map.get(r, (False, ""))[0]:
            continue
        # Lọc từng clip trong root để đảm bảo 100% không clip nào bị pillarbox
        clean_clips = [c for c in clips if not _la_pillarbox(c[1])]
        if clean_clips:
            clean_roots[r] = clean_clips

    log(f"[ban_dung] Tổng số video gốc sạch 16:9 đạt chuẩn: {len(clean_roots)} gốc")

    # Xây dựng mô hình TF-IDF Vectorizer tự động cho toàn bộ tiêu đề kho video
    clean_root_keys = list(clean_roots.keys())
    clean_root_texts = [root_best_title.get(r, clean_roots[r][0][3]) for r in clean_root_keys]

    tfidf_vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    root_tfidf_matrix = tfidf_vec.fit_transform(clean_root_texts)

    # Bản đồ thực thể đa tầng ở cấp nhịp (Universal Entity Resolver)
    BEAT_ENTITY_MAP = {
        "dê núi": ("mountain goat ibex horn grazing", ["goat", "ibex"]),
        "dê": ("goat flock grazing pasture", ["goat"]),
        "hươu": ("deer elk running fast in wild", ["deer", "elk"]),
        "nai": ("deer elk buck wildlife", ["deer", "elk"]),
        "lợn rừng": ("wild boar charging battle predator", ["boar", "warthog", "deadly moments", "predator"]),
        "heo rừng": ("wild boar charging battle predator", ["boar", "warthog"]),
        "lừa": ("guard donkey kicking predator", ["donkey"]),
        "llama": ("guard llama protecting sheep", ["llama", "alpaca"]),
        "lạc đà": ("guard llama protecting sheep", ["llama", "alpaca"]),
        "chó bảo vệ": ("livestock guard dog shepherd protect", ["guard dog", "kangal", "shepherd", "dogs"]),
        "chó chăn cừu": ("livestock guard dog shepherd sheepdog", ["guard dog", "kangal", "shepherd", "sheepdog"]),
        "chó": ("livestock guard dog shepherd canine", ["guard dog", "kangal", "shepherd"]),
        "sói": ("wolf wolves pack hunting wilderness", ["wolf", "wolves"]),
        "cừu": ("sheep lamb grazing flock meadow", ["sheep", "lamb"]),
        "drone": ("drone thermal camera aerial flight", ["drone"]),
        "máy bay": ("drone thermal camera aerial flight", ["drone"]),
        "camera": ("farm security surveillance camera monitoring", ["camera", "surveillance"])
    }

    bd_data = doc(du_an)
    cau_map = bd_data.setdefault("cau", {})

    last_root = None
    recent_roots = []
    used_counts = Counter()
    tong_cau = len(canh_list)
    da_phu = 0
    ds_thieu = []

    # Quét các câu đã dựng giữ lại nếu bật giu_da_dung
    if giu_da_dung:
        for cid_str, c_info in cau_map.items():
            if c_info.get("tin_cay") == "xanh" and not c_info.get("thieu"):
                da_phu += 1
                for n in c_info.get("nhip") or []:
                    kid = n.get("kho_id")
                    if kid and kid in kho:
                        mc = _get_true_root(kid, kho[kid])
                        used_counts[mc] += 1
                        used_counts[kid] += 1
                        last_root = mc
                        recent_roots.append(mc)
                        if len(recent_roots) > 8:
                            recent_roots.pop(0)

    for c in canh_list:
        cid = c.get("id")
        cid_str = str(cid)
        c_info = cau_map.get(cid_str) or {}

        if giu_da_dung and c_info.get("tin_cay") == "xanh" and not c_info.get("thieu"):
            continue

        ct_item = ct_map.get(cid)
        ds_ten = ct_item.get("ds") if ct_item else []
        ten_ct = ds_ten[0] if ds_ten else "Chung"

        nhips = nhip_cua_cau(du_an, cid)
        text_cau = c.get("text", "")
        # Lấy câu lệnh hình ảnh tiếng Anh do hệ thống phân tích kịch bản tự sinh
        en_desc = tt_cau.get(cid) or f"documentary footage of {ten_ct}"

        prompt_anh = f"Ultra-realistic National Geographic documentary photo of {en_desc}, highly detailed, 8k"
        prompt_veo = f"Cinematic documentary footage of {en_desc}, professional color grading, 4k"

        # Tách vế câu tương ứng với các nhịp (nếu câu có dấu phẩy / dấu chấm phẩy)
        clauses = [cl.strip() for cl in re.split(r"[,;]", text_cau) if cl.strip()]

        nhip_da_gan = []
        co_manh = True

        for i, n in enumerate(nhips):
            if not clean_root_keys:
                co_manh = False
                break

            # Kiểm tra xem nhịp này có thực thể riêng biệt được gọi tên cụ thể không
            clause_text = clauses[i].lower() if i < len(clauses) else text_cau.lower()
            detected_beat_entity = None
            for e_k, (e_en, e_kws) in BEAT_ENTITY_MAP.items():
                if e_k in clause_text:
                    detected_beat_entity = (e_k, e_en, e_kws)
                    break

            if detected_beat_entity:
                # Nếu nhịp gọi tên cụ thể thực thể (dê núi, hươu, lợn rừng...), ưu tiên query thực thể đó
                query_text = f"{detected_beat_entity[1]}"
            else:
                # Nhịp chung dùng mô tả kịch bản
                query_text = f"{en_desc}"

            query_vec = tfidf_vec.transform([query_text])
            sim_scores = cosine_similarity(query_vec, root_tfidf_matrix)[0]

            # Xác định chủ thể cốt lõi của cảnh để tránh bị bẫy từ bối cảnh phụ
            is_wolf_focus = ("sói" in ten_ct.lower()) or ("wolf" in en_desc.lower() and "sheep" not in en_desc.lower())
            is_sheep_focus = ("cừu" in ten_ct.lower()) or ("sheep" in en_desc.lower() and "wolf" not in en_desc.lower())

            scores = []
            for idx, r in enumerate(clean_root_keys):
                root_title = clean_root_texts[idx].lower()
                sc = float(sim_scores[idx]) * 10.0  # Thang điểm tương quan 0 -> 10

                # 1. Thưởng điểm thực thể cấp nhịp nếu nhịp có yêu cầu riêng
                if detected_beat_entity:
                    matched_kws = sum(1 for kw in detected_beat_entity[2] if kw in root_title)
                    if matched_kws > 0:
                        sc += 6.0 * matched_kws

                # 2. Khóa cứng Chủ thể cốt lõi (Core Entity Rule):
                # Nếu cảnh đang nói về Sói:
                if is_wolf_focus and not detected_beat_entity:
                    if any(w in root_title for w in ["wolf", "wolves"]):
                        sc += 4.0
                    # Phạt nặng nếu video chỉ thuần về loài khác (bầy dê, bầy bò, gia cầm) lấn sân vì từ bối cảnh trang trại
                    if any(w in root_title for w in ["goat flock", "goat", "cattle", "poultry"]) and not any(w in root_title for w in ["wolf", "wolves"]):
                        sc -= 12.0

                # 3. Phạt nặng video đối kháng hai loài ('vs') trừ khi kịch bản có yêu cầu giao chiến
                if re.search(r"\\b(vs|versus)\\b", root_title, re.I):
                    sc -= 5.0

                # 4. Khóa tuyệt đối không cho 2 clip cùng video gốc đi liền nhau
                if last_root and r == last_root:
                    sc -= 9999.0

                # 5. Phạt nặng lặp gần trong 6 cảnh vừa qua
                if r in recent_roots:
                    idx_from_end = len(recent_roots) - 1 - recent_roots.index(r)
                    if idx_from_end < 6:
                        sc -= 3.0 * (6 - idx_from_end)

                # 6. Phạt tần suất sử dụng để xoay vòng đều toàn bộ kho
                sc -= 0.5 * used_counts[r]
                scores.append((r, sc))

            scores.sort(key=lambda x: x[1], reverse=True)
            chosen_root = scores[0][0]

            # Danh sách clip sạch 100% của chosen_root (đã lọc pillarbox)
            clips_in_root = [k[0] for k in clean_roots.get(chosen_root, [])]
            valid_clips = [k for k in clips_in_root if float(kho[k].get("dai") or 0) >= n["dai"] - 0.5]
            if not valid_clips:
                valid_clips = clips_in_root

            chosen_clip = min(valid_clips, key=lambda k: used_counts[k])

            used_counts[chosen_root] += 1
            used_counts[chosen_clip] += 1
            last_root = chosen_root
            recent_roots.append(chosen_root)
            if len(recent_roots) > 8:
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

        if not co_manh or len(nhip_da_gan) < len(nhips):
            ds_thieu.append({
                "cau": cid,
                "text": text_cau,
                "chu_the": ten_ct,
                "mo_ta_en": en_desc,
                "prompt_anh": prompt_anh,
                "prompt_veo": prompt_veo
            })
            for n in nhips:
                n["kho_id"] = None
                n["da_tai"] = False
                n["thieu"] = True
                n["chu_the"] = ten_ct
                n["prompt_anh"] = prompt_anh
                n["prompt_veo"] = prompt_veo

            cau_map[cid_str] = {
                "cach": "thieu",
                "loai_goi_y": "khong_quay_duoc",
                "tin_cay": "do",
                "thieu": True,
                "chu_the": ten_ct,
                "tu_khoa": [en_desc],
                "nhip": nhips,
                "cau_lenh_anh": prompt_anh,
                "cau_lenh_veo": prompt_veo,
                "sua_luc": time.time()
            }
        else:
            da_phu += 1
            cau_map[cid_str] = {
                "cach": "footage",
                "loai_goi_y": "quay_duoc",
                "tin_cay": "xanh",
                "thieu": False,
                "chu_the": ten_ct,
                "tu_khoa": [en_desc],
                "nhip": nhip_da_gan,
                "cau_lenh_anh": prompt_anh,
                "cau_lenh_veo": prompt_veo,
                "sua_luc": time.time()
            }

    ghi(du_an, bd_data)

    # Đồng bộ sang dung.json cho các câu đã phủ
    try:
        dung_data = dung_tay.doc_dung(du_an)
        for cid_str, c_info in cau_map.items():
            if c_info.get("thieu") or not c_info.get("nhip"):
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
        ghi_json(os.path.join(out, "dung.json"), dung_data)
    except Exception as e:
        log(f"    ! [ban_dung] dong bo dung.json: {e}")

    log(f"[ban_dung] Băm theo ngữ nghĩa AI hoàn tất: {da_phu}/{tong_cau} câu đã phủ, {len(ds_thieu)} câu thiếu.")
    return {
        "ok": True,
        "da_phu": da_phu,
        "tong_cau": tong_cau,
        "thieu": len(ds_thieu),
        "ds_thieu": ds_thieu
    }
'''

full_code = "".join(head) + universal_body

with open("ban_dung.py", "w", encoding="utf-8") as f:
    f.write(full_code)

print(f"Reconstructed ban_dung.py with BEAT-LEVEL MULTI-TIER ENGINE ({len(full_code.splitlines())} lines)!")
