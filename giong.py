# -*- coding: utf-8 -*-
"""Đọc từng cảnh bằng giọng CapCut (mặc định 'Thanh Niên Tự Tin') rồi lấy THỜI LƯỢNG THẬT
của giọng làm thời lượng cảnh — thay cho ước lượng ký tự/giây."""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from common import FFMPEG, chay, duong_cache, log

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))

OMNI_PY = os.environ.get("BC_OMNI_PY", r"D:\CapCutTTS\omnivoice-env\Scripts\python.exe")   # env OmniVoice riêng
OMNI_REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "Tự tin.wav")
GIONG = "BV075_streaming"               # Thanh Niên Tự Tin (vi-VN)
RESOURCE_ID = "7102355803792740865"
KHOANG_LANG = 0.25                       # giây lặng cuối mỗi cảnh


def thoi_luong(path):
    _, _, err = chay([FFMPEG, "-i", path, "-f", "null", "-"], timeout=60)
    m = re.findall(r"time=(\d+):(\d+):([\d.]+)", err)
    if not m:
        return 0.0
    h, mi, s = m[-1]
    return int(h) * 3600 + int(mi) * 60 + float(s)


def _dat_moc(canh):
    t = 0.0
    for c in canh:                                       # dựng lại mốc thời gian theo giọng thật
        if c.get("giong_dai"):
            c["dai"] = round(c["giong_dai"] + KHOANG_LANG + float(c.get("nghi_sau") or 0), 2)   # (nghỉ X): lặng thêm X giây
        c["bat_dau"] = round(t, 2)
        t += c["dai"]
    log(f"    tổng thời lượng theo giọng: {t:.0f}s")


def nhan_giong(ref, toc_do, num_step=24):
    """Nhãn thư mục cho (giọng, tốc độ): đổi giọng/tốc độ thì KHÔNG dùng nhầm bản đọc cũ. Giọng mặc định
    'Tự tin' tốc độ 1.0 giữ thư mục cũ (giong_omni) để các bản nháp đã dựng còn nguyên đường dẫn."""
    ten = re.sub(r"[^A-Za-z0-9]+", "_", __import__("unicodedata").normalize("NFD", os.path.splitext(os.path.basename(ref))[0])
                 .encode("ascii", "ignore").decode()).strip("_") or "giong"
    buoc = "" if int(num_step) == 24 else f"_s{int(num_step)}"          # step 24 giữ nhãn cũ (cache đã đọc); step khác -> thư mục riêng
    if ten.lower() == "tu_tin" and abs(float(toc_do) - 1.0) < 1e-6 and not buoc:
        return ""
    return f"{ten}_x{float(toc_do):g}{buoc}"


_ON_TTS = ("warn", "symlink", "loading weights", "futurewarning", "userwarning", "deprecat", "it/s]", "%|")


def _chay_hien_log(lenh, tong, timeout=7200):
    """Chạy tiến trình TTS và đưa TỪNG DÒNG log ra ngay (giao diện đọc chay.log nên thấy đang đọc câu nào), đồng thời
    cập nhật ô tiến độ 'Đọc giọng'. Trả (mã thoát, vài dòng cuối)."""
    import re
    import subprocess
    import time
    from common import tien_do
    p = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1"),
                         creationflags=0x08000000 if os.name == "nt" else 0)
    cuoi, t0 = [], time.time()
    for raw in iter(p.stdout.readline, b""):
        dong = raw.decode("utf-8", "ignore").rstrip()
        if not dong.strip():
            continue
        cuoi = (cuoi + [dong.strip()])[-6:]
        if any(k in dong.lower() for k in _ON_TTS):
            continue
        log("    " + dong.strip()[:220])
        m = re.search(r"(\d+)/(\d+)", dong)
        if m and "[omni]" in dong:
            xong = int(m.group(1))
            con = (time.time() - t0) / max(xong, 1) * (tong - xong)
            try:
                tien_do("giong", "dang", f"{xong}/{tong} câu · còn ~{int(con // 60)}:{int(con % 60):02d}")
            except Exception:                              # noqa: BLE001
                pass
        if time.time() - t0 > timeout:
            p.kill()
            break
    p.wait()
    return p.returncode, cuoi


PHIEN_BAN_DOC = "g1"          # đổi cách đưa chữ vào máy đọc (vd nối gạch số dài) -> tăng để đọc lại câu bị ảnh hưởng
BAO_CAO_SOAT = {}             # báo cáo soát giọng của lần doc_omni gần nhất (chay.py hiện lên tiến độ)


def _chu_may_doc(text):
    """Chữ THẬT SỰ đưa vào OmniVoice (khớp tts/omnivoice_tts._text_may_doc): hiện chỉ nối gạch cụm số dài."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    from tach_so import noi_gach
    return noi_gach(" ".join(str(text).split()))


def _dau_van_ban(text):
    import hashlib
    return hashlib.md5((PHIEN_BAN_DOC + "|" + _chu_may_doc(text)).encode("utf-8")).hexdigest()[:12]


def _can_doc_lai(canh, thu_muc):
    """Cảnh cần đọc (lại): chưa có file giọng, HOẶC chữ đưa vào máy đọc đã khác lúc đọc (sửa kịch bản, đổi cách
    đọc số…). Dấu từng cảnh lưu ở <thư mục giọng>/_van_ban.json. Thư mục cũ chưa có dấu: cảnh có số dài (cách
    đọc mới khác cách cũ) thì đọc lại, cảnh khác giữ nguyên rồi ghi dấu."""
    import json
    p = os.path.join(thu_muc, "_van_ban.json")
    try:
        with open(p, encoding="utf-8") as f:
            dau = json.load(f)
    except (OSError, ValueError):
        dau = None
    can = []
    for c in canh:
        wav = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        co = os.path.isfile(wav) and os.path.getsize(wav) > 2000
        moi = _dau_van_ban(c["text"])
        if dau is None:
            cu = moi if _chu_may_doc(c["text"]) == " ".join(str(c["text"]).split()) else None
        else:
            cu = dau.get(str(c["id"]))
        if not co or cu != moi:
            can.append(c)
    return can


def _ghi_dau(canh, thu_muc):
    import json
    p = os.path.join(thu_muc, "_van_ban.json")
    try:
        with open(p, encoding="utf-8") as f:
            dau = json.load(f)
    except (OSError, ValueError):
        dau = {}
    for c in canh:
        wav = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if os.path.isfile(wav) and os.path.getsize(wav) > 2000:
            dau[str(c["id"])] = _dau_van_ban(c["text"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(dau, f, ensure_ascii=False)


def doc_omni(canh, ref=OMNI_REF, batch=16, num_step=32, toc_do=1.0):
    """Đọc bằng OmniVoice (clone từ clip mẫu `ref`) — một tiến trình đọc cả lô trên GPU."""
    import json
    nhan = nhan_giong(ref, toc_do, num_step)
    thu_muc = duong_cache("giong_omni", nhan) if nhan else duong_cache("giong_omni")
    can = _can_doc_lai(canh, thu_muc)
    ten_giong = os.path.splitext(os.path.basename(ref))[0]
    log(f"[1b] OmniVoice '{ten_giong}' x{toc_do} step {num_step}: {len(can)}/{len(canh)} cảnh cần đọc (còn lại đã có cache)")
    if can:
        jobs = os.path.join(duong_cache("giong_omni_jobs"), "jobs_" + (nhan or "mac_dinh") + ".json")
        with open(jobs, "w", encoding="utf-8") as f:
            json.dump([{"idx": c["id"], "text": c["text"]} for c in can], f, ensure_ascii=False)
        tts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts")
        lenh = [OMNI_PY, os.path.join(tts_dir, "omnivoice_tts.py"), "--jobs-json", jobs, "--out-dir", thu_muc,
                "--ref", ref, "--batch", str(batch), "--num-step", str(num_step),
                "--rate", str(toc_do), "--name-fmt", "{:04d}.wav"]
        rc, cuoi = _chay_hien_log(lenh, len(can))
        if rc != 0:
            log(f"    ! TTS mã {rc}: {' | '.join(cuoi)[-300:]}")
    # 18/10 user: soát nuốt / méo chữ (cụm số) + ngắt giữa cụm từ; câu lỗi đọc lại bằng seed khác, giữ bản ít lỗi nhất
    tts_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts", "omnivoice_tts.py")

    def doc_lai(jobs_json, out_dir, seed):
        if not (ref and os.path.isfile(ref)):                # không có clip mẫu -> model tự chọn giọng KHÁC: không đọc lại
            log(f"    ! soát giọng: không thấy clip mẫu '{ref}' — không đọc lại")
            return 1
        return _chay_hien_log([OMNI_PY, tts_py, "--jobs-json", jobs_json, "--out-dir", out_dir, "--ref", ref,
                               "--batch", str(batch), "--num-step", str(num_step), "--rate", str(toc_do),
                               "--name-fmt", "{:04d}.wav", "--seed", str(seed)],
                              len(json.load(open(jobs_json, encoding="utf-8"))))[0]
    bc = {}
    try:
        import soat_giong
        bc = soat_giong.soat_va_doc_lai([c for c in canh if c.get("text")], thu_muc, doc_lai)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! soát giọng lỗi (giữ bản đọc hiện có): {str(e)[:160]}")
        bc = {"loi_soat": str(e)[:160]}
    _ghi_dau(canh, thu_muc)
    for c in canh:
        p = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if os.path.isfile(p) and os.path.getsize(p) > 2000:
            c["giong"], c["giong_dai"] = p, round(thoi_luong(p), 2)
        else:
            log(f"    ! cảnh {c['id']} chưa có giọng")
    _dat_moc(canh)
    if bc.get("thay"):                                       # chạy lại trên dự án cũ: mốc chữ của câu vừa thay phải căn lại
        from common import CACHE, OUT
        _xoa_moc_cu(CACHE, OUT, [c for c in canh if c["id"] in bc["thay"]])
    BAO_CAO_SOAT.clear()
    BAO_CAO_SOAT.update(bc)
    return canh


NEN_TOI_DA = 1.20             # 1/11: bản đọc lại dài hơn câu cũ quá tỉ lệ này thì không nén (giọng méo) mà đổi mốc cả bài


def _vua_do_dai(wav, dai_cu):
    """Đưa bản đọc lại về đúng độ dài cũ -> mốc giờ cả bài không đổi. 1/11: ngắn hơn thì thêm lặng cuối (trước đây kéo
    giãn làm giọng lè nhè); dài hơn thì nén giữ cao độ tới NEN_TOI_DA. Trả False nếu dài quá, không nén được."""
    import subprocess
    import wave
    from common import FFMPEG
    dai_moi = thoi_luong(wav)
    if not dai_moi or not dai_cu or abs(dai_moi - dai_cu) < 0.03:
        return True
    if dai_moi < dai_cu:
        with wave.open(wav, "rb") as w:
            ts, du_lieu = w.getparams(), w.readframes(w.getnframes())
        them = int(round(dai_cu * ts.framerate)) - ts.nframes
        with wave.open(wav, "wb") as w:
            w.setparams(ts)
            w.writeframes(du_lieu + b"\0" * (max(0, them) * ts.nchannels * ts.sampwidth))
        return True
    r = dai_moi / dai_cu
    if r > NEN_TOI_DA:
        log(f"    ! {os.path.basename(wav)}: bản đọc lại dài {dai_moi:.2f}s, câu cũ {dai_cu:.2f}s — lệch quá nhiều, phải đổi mốc")
        return False
    tam = wav[:-4] + "._vua.wav"
    p = subprocess.run([FFMPEG, "-v", "error", "-y", "-i", wav, "-af", f"atempo={r:.5f}", "-c:a", "pcm_s16le", tam],
                       capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
    if p.returncode != 0 or not os.path.isfile(tam):
        return False
    os.replace(tam, wav)
    return True


def _xoa_moc_cu(cache, out, canh_doi):
    """Mốc từng chữ của câu vừa đọc lại đã hết đúng: moc_tu.json khoá theo chữ + giờ cảnh nên câu giữ nguyên độ dài vẫn
    trúng khoá cũ, phải xoá tay. Cả mốc Whisper theo id trong cache (can_giong)."""
    import glob
    import hashlib
    from common import doc_json, ghi_json
    p = os.path.join(out, "moc_tu.json")
    da = doc_json(p, None)
    if da:
        for c in canh_doi:
            da.pop(hashlib.md5(f"{c['text']}|{c['bat_dau']:.3f}|{c['dai']:.3f}".encode("utf-8")).hexdigest()[:16], None)
        ghi_json(p, da)
    for f in glob.glob(os.path.join(cache, "moc_tu*.json")):
        da = doc_json(f, None)
        if da:
            for c in canh_doi:
                da.pop(str(c["id"]), None)
            ghi_json(f, da)


def _cap_nhat_moc(du_an, out, tat_ca, doi, wav):
    """Sau khi ghép lại giong_doc.wav: căn lại giờ từng chữ của các câu đã thay (moc_tu.json) rồi ghi lại kich_ban_cau.srt
    bằng đúng hàm của bước ✨. Dự án chưa có các file này (chưa qua ✨) thì không tạo. lang.json tự đo lại theo mtime wav."""
    import sys
    if not os.path.isfile(os.path.join(out, "moc_tu.json")):
        return
    goc = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(goc, "chinh_sua"))
    import can_chu
    ds = [dict(c) for c in tat_ca if c.get("text")]
    can_chu.gan_moc(du_an, ds, wav)
    p = os.path.join(out, "kich_ban_cau.srt")
    if os.path.isfile(p):
        import dung_hoan_chinh as D
        for c in ds:
            c["_t0"], c["_t1"] = int(round(c["bat_dau"] * D.SEC)), int(round((c["bat_dau"] + c["dai"]) * D.SEC))
            c["giong_dai"] = c["dai"]
        D.ghi_srt(D.tao_srt(ds), p)
    log(f"    đã căn lại giờ từng chữ {len(doi)} câu, ghi lại kich_ban_cau.srt")


def sua_cau_sai(du_an, bao=None):
    """19/10 user: nút "Sửa câu đọc sai" — soát lại mọi câu đã đọc (soat_giong: sai từ / nuốt / méo / ngắt sai), câu sai
    đọc lại (giữ bản ít lỗi nhất), đưa về ĐÚNG ĐỘ DÀI câu cũ rồi ghép lại ra/<dự án>/giong_doc.wav TẠI CHỖ -> mốc câu
    không đổi, các bản nháp đang dùng file giọng này nhận luôn (mở lại bản nháp). 1/11: cập nhật luôn moc_tu.json +
    kich_ban_cau.srt của câu đã thay; bản đọc lại quá dài (> NEN_TOI_DA) thì dời mốc các câu sau, ghi lại tu_khoa.json +
    kich_ban.srt và báo. Bản trước khi sửa giữ ở _truoc_sua/. Trả {thay, con_loi, loi, doc_lai, luot, phat_hien,
    theo_loai, doi_moc, ke_hoach_lech}."""
    import json
    import shutil
    import ghep
    import soat_giong
    from common import doc_json, ghi_json, thu_muc_du_an
    bao = bao or (lambda m: log(m))
    cache, out = thu_muc_du_an(du_an)
    lc = doc_json(os.path.join(out, "lan_chay.json"), {}) or {}
    ref = lc.get("giong") or OMNI_REF
    toc_do, num_step = float(lc.get("toc_do") or 1.0), int(lc.get("num_step") or 32)
    nhan = nhan_giong(ref, toc_do, num_step)
    thu_muc = os.path.join(cache, "giong_omni", nhan) if nhan else os.path.join(cache, "giong_omni")
    tat_ca = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    canh = [c for c in tat_ca if c.get("text")]
    if not canh or not os.path.isdir(thu_muc):
        raise ValueError("dự án chưa có giọng đọc (chạy bước đọc giọng trước)")
    if not os.path.isfile(ref):
        raise ValueError(f"không thấy clip mẫu giọng {ref} — không đọc lại được")
    truoc = {}
    for c in canh:
        f = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if os.path.isfile(f):
            st = os.stat(f)
            truoc[c["id"]] = (st.st_size, st.st_mtime, thoi_luong(f))
    bao(f"Soát {len(truoc)} câu đã đọc…")
    tts_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts", "omnivoice_tts.py")

    def doc_lai(jobs_json, out_dir, seed):
        n = len(json.load(open(jobs_json, encoding="utf-8")))
        bao(f"Đọc lại {n} câu sai (seed {seed})…")
        return _chay_hien_log([OMNI_PY, tts_py, "--jobs-json", jobs_json, "--out-dir", out_dir, "--ref", ref,
                               "--batch", "16", "--num-step", str(num_step), "--rate", str(toc_do),
                               "--name-fmt", "{:04d}.wav", "--seed", str(seed)], n)[0]
    bc = soat_giong.soat_va_doc_lai(canh, thu_muc, doc_lai)
    doi, doi_moc = [], False
    lech = 0.0                                               # giây dồn thêm cho các câu sau khi có bản đọc lại quá dài
    canh_cu = [dict(c) for c in canh]                        # giờ trước khi dời: khoá moc_tu cũ
    for c in canh:
        f = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        c["bat_dau"] = round(c["bat_dau"] + lech, 2)
        if c["id"] in truoc and os.path.isfile(f):
            st = os.stat(f)
            if (st.st_size, st.st_mtime) != truoc[c["id"]][:2]:
                if not _vua_do_dai(f, truoc[c["id"]][2]):
                    them = thoi_luong(f) - truoc[c["id"]][2]
                    c["dai"] = round(c["dai"] + them, 2)
                    lech += them
                    doi_moc = True
                doi.append(c["id"])
        c["giong"] = f
    if doi:
        # bản đọc lại đã qua đổi độ dài -> soát lần cuối đúng file sẽ ghép, báo cáo phản ánh giọng thật trong bài
        theo_id = {c["id"]: c for c in canh}
        cuoi = soat_giong.soat_nhieu([(i, theo_id[i]["text"], theo_id[i]["giong"]) for i in doi])
        for i, v in cuoi.items():
            if v:
                bc["con_loi"][i] = v
            else:
                bc["con_loi"].pop(i, None)
    loi = bc["con_loi"]
    ke_hoach_lech = False
    if doi:
        wav = os.path.join(out, "giong_doc.wav")
        bk = os.path.join(out, "giong_doc.truoc_sua.wav")
        if os.path.isfile(wav) and not os.path.isfile(bk):
            shutil.copyfile(wav, bk)
        cu = os.path.join(out, "_truoc_sua")
        os.makedirs(cu, exist_ok=True)
        for t in ("tu_khoa.json", "moc_tu.json", "kich_ban_cau.srt", "kich_ban.srt"):
            if os.path.isfile(os.path.join(out, t)) and not os.path.isfile(os.path.join(cu, t)):
                shutil.copyfile(os.path.join(out, t), os.path.join(cu, t))
        ghep.noi_giong(canh, wav)
        _ghi_dau(canh, thu_muc)
        _xoa_moc_cu(cache, out, [c for c in canh_cu if c["id"] in doi])
        if doi_moc:
            for c in canh:
                c.pop("giong", None)
            ghi_json(os.path.join(out, "tu_khoa.json"), tat_ca)
            ghep.xuat_srt(canh, os.path.join(out, "kich_ban.srt"))
            ke_hoach_lech = any(os.path.isfile(os.path.join(out, t)) for t in ("ban_dung.json", "dung.json"))
        _cap_nhat_moc(du_an, out, tat_ca, doi, wav)
        bao(f"Đã thay {len(doi)} câu ({', '.join(map(str, doi[:20]))}) và ghép lại giong_doc.wav, "
            + (f"MỐC CÁC CÂU SAU ĐÃ DỜI {lech:+.2f}s" if doi_moc else "giữ nguyên mốc câu"))
        if ke_hoach_lech:
            bao("! Mốc giờ đã đổi: kế hoạch băm (ban_dung.json / dung.json) lệch giọng, cần băm lại trước khi xuất")
        elif os.path.isfile(os.path.join(out, "ban_dung.json")):
            bao("Mốc câu giữ nguyên; riêng các câu đã thay, chỗ ngắt trong câu có thể đổi — nên băm lại đúng các câu đó")
    else:
        bao("Không câu nào được thay")
    bao(f"Soát {bc['so_cau']} câu: phát hiện {bc['phat_hien']} câu lỗi {bc['theo_loai']}, đọc lại {bc['luot']} lượt, "
        f"thay {len(doi)} câu, còn {len(loi)} câu lỗi")
    for k, v in loi.items():
        bao(f"! CÒN LỖI câu {k}: " + "; ".join(x[1] for x in v[:3]))
    kq = {"thay": doi, "con_loi": sorted(loi), "loi": {k: [x[1] for x in v][:3] for k, v in loi.items()},
          "doc_lai": bc["doc_lai"], "luot": bc["luot"], "phat_hien": bc["phat_hien"], "theo_loai": bc["theo_loai"],
          "doi_moc": doi_moc, "ke_hoach_lech": ke_hoach_lech}
    ghi_json(os.path.join(out, "soat_giong.json"), kq)
    return kq


def rut_ngat_cau(du_an, ids, bao=None):
    """2/11 user: các câu `ids` chỉ ngắt sai chỗ -> cắt ngắn đoạn lặng sai (soat_giong.rut_ngat, không đọc lại), ghép lại
    giong_doc.wav, căn lại mốc chữ. Mốc câu không đổi. File trước khi cắt giữ ở ra/<dự án>/_truoc_rut/. Trả {id: [chỗ đã cắt]}."""
    import shutil
    import time
    import ghep
    import soat_giong
    from common import doc_json, thu_muc_du_an
    bao = bao or (lambda m: log(m))
    cache, out = thu_muc_du_an(du_an)
    lc = doc_json(os.path.join(out, "lan_chay.json"), {}) or {}
    nhan = nhan_giong(lc.get("giong") or OMNI_REF, float(lc.get("toc_do") or 1.0), int(lc.get("num_step") or 32))
    thu_muc = os.path.join(cache, "giong_omni", nhan) if nhan else os.path.join(cache, "giong_omni")
    tat_ca = doc_json(os.path.join(out, "tu_khoa.json"), []) or []
    canh = [c for c in tat_ca if c.get("text")]
    wav = os.path.join(out, "giong_doc.wav")
    bk = os.path.join(out, "_truoc_rut", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(bk, exist_ok=True)
    for t in ("giong_doc.wav", "moc_tu.json", "kich_ban_cau.srt"):
        if os.path.isfile(os.path.join(out, t)):
            shutil.copyfile(os.path.join(out, t), os.path.join(bk, t))
    kq = {}
    for c in canh:
        c["giong"] = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if c["id"] in ids:
            shutil.copyfile(c["giong"], os.path.join(bk, f"{c['id']:04d}.wav"))
            cat = soat_giong.rut_ngat(c["text"], c["giong"])
            if cat:
                kq[c["id"]] = cat
                bao(f"Câu {c['id']}: " + "; ".join(cat))
    if kq:
        ghep.noi_giong(canh, wav)
        _xoa_moc_cu(cache, out, [c for c in canh if c["id"] in kq])
        _cap_nhat_moc(du_an, out, tat_ca, list(kq), wav)
        bao(f"Đã cắt ngắn chỗ ngắt ở {len(kq)} câu, ghép lại giong_doc.wav, giữ nguyên mốc câu")
    else:
        bao("Không có chỗ ngắt nào cần cắt")
    return kq


def doc_tat_ca(canh, giong=GIONG, resource_id=RESOURCE_ID, toc_do="1.0", luong=5):
    import capcut_tts_core as T
    eng = T.TTSEngine(T.base_device_from(None), voice=giong, resource_id=resource_id,
                      rate=toc_do, max_attempts=8, task_fail_cap=5)
    thu_muc = duong_cache("giong")
    log(f"[1b] đọc {len(canh)} cảnh bằng giọng {giong}")

    def lam(c):
        p = os.path.join(thu_muc, f"{c['id']:04d}.mp3")
        if os.path.isfile(p) and os.path.getsize(p) > 2000:
            return c, p
        try:
            eng.synth_one(c["text"], p)
            return c, p
        except Exception as e:                           # noqa: BLE001
            log(f"    ! cảnh {c['id']} đọc hỏng: {str(e)[:100]}")
            return c, None

    with ThreadPoolExecutor(luong) as ex:
        for i, (c, p) in enumerate(ex.map(lam, canh), 1):
            if p:
                c["giong"], c["giong_dai"] = p, round(thoi_luong(p), 2)
            if i % 10 == 0 or i == len(canh):
                log(f"    đọc {i}/{len(canh)}")
    _dat_moc(canh)
    return canh
