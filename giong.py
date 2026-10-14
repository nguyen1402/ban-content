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
    _ghi_dau(canh, thu_muc)
    for c in canh:
        p = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if os.path.isfile(p) and os.path.getsize(p) > 2000:
            c["giong"], c["giong_dai"] = p, round(thoi_luong(p), 2)
        else:
            log(f"    ! cảnh {c['id']} chưa có giọng")
    _dat_moc(canh)
    return canh


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
