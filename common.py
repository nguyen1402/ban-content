# -*- coding: utf-8 -*-
"""Dùng chung: đường dẫn, gọi Gemini (xoay key/model), dò thư mục CapCut Drafts, chạy lệnh."""
import json
import os
import re
import subprocess
import time
import threading
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                  # noqa: BLE001
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_CHUNG = os.path.join(ROOT, "cache")


def _slug(s):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(os.path.basename(str(s)))[0]).strip("_")
    return s[:40] or "mac_dinh"


def _doc_du_an():
    """Tên DỰ ÁN (mỗi kịch bản một dự án): --du-an <tên>, hoặc tên file .txt kịch bản trên dòng lệnh, hoặc dự án
    chạy gần nhất (cache/du_an_cuoi.txt). Dữ liệu theo từng cảnh (giọng, mô tả, hình đã chọn…) nằm riêng theo dự án
    để kịch bản mới KHÔNG dùng nhầm kết quả của kịch bản cũ."""
    if os.environ.get("BC_DU_AN"):
        return os.environ["BC_DU_AN"]
    a = sys.argv
    if "--du-an" in a and a.index("--du-an") + 1 < len(a):
        return _slug(a[a.index("--du-an") + 1])
    for x in a[1:]:
        if x.lower().endswith(".txt") and os.path.isfile(x):
            return _slug(x)
    try:
        with open(os.path.join(CACHE_CHUNG, "du_an_cuoi.txt"), encoding="utf-8") as f:
            return f.read().strip() or "kichbantest"
    except OSError:
        return "kichbantest"


DU_AN = _doc_du_an()
os.environ["BC_DU_AN"] = DU_AN                        # tiến trình con thừa hưởng
#: dự án đầu tiên (kichbantest) giữ nguyên chỗ cũ để các bản nháp CapCut đã dựng không mất đường dẫn.
_CU = {"kichbantest"}
CACHE = CACHE_CHUNG if DU_AN in _CU else os.path.join(CACHE_CHUNG, "du_an", DU_AN)
OUT = os.path.join(ROOT, "ra") if DU_AN in _CU else os.path.join(ROOT, "ra", DU_AN)
#: những thứ KHÔNG phụ thuộc kịch bản (theo id video/ảnh/truy vấn) -> dùng chung mọi dự án.
CHUNG = {"xem_truoc", "chi_muc", "chi_muc_l14", "ocr.json", "shots.json", "logo.json", "tim.json", "tiles",
         "nen_lop", "anh", "kho", "doan_tho", "nhac_yt"}
FFMPEG = os.environ.get("BC_FFMPEG") or (r"C:\yt-dlp\ffmpeg.exe" if os.path.isfile(r"C:\yt-dlp\ffmpeg.exe") else "ffmpeg")
YTDLP = os.path.join(ROOT, "tools", "yt-dlp.exe")
#: YouTube bắt buộc chạy JS để giải chữ ký — không có cờ này thì tải bị 403.
YT_JS = ["--js-runtimes", "node"]
MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]

#: kênh lớn bật Content ID rất chặt — bỏ ngay từ lúc tìm (khớp một phần tên, không phân hoa/thường).
KENH_CHAN = ("bbc", "national geographic", "nat geo", "disney", "netflix", "discovery",
             "animal planet", "cnn", "reuters", "sky news", "pbs", "nbc", "cbs", "fox ",
             "warner", "universal", "paramount", "hbo", "vevo", "getty", "storyblocks",
             "shutterstock", "abc ")

for _d in (CACHE_CHUNG, CACHE, OUT):
    os.makedirs(_d, exist_ok=True)


def duong_cache(*phan):
    p = os.path.join(CACHE_CHUNG if phan[0] in CHUNG else CACHE, *phan)
    os.makedirs(os.path.dirname(p) if os.path.splitext(p)[1] else p, exist_ok=True)
    return p


def doc_json(path, mac_dinh=None):
    for lan in range(8):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:                              # Windows: file đang bị luồng khác thay (os.replace) — thử lại
            time.sleep(0.05 * (lan + 1))
        except (OSError, ValueError):
            return mac_dinh
    return mac_dinh


def ghi_json(path, obj):
    """Ghi nguyên tử, an toàn khi NHIỀU LUỒNG cùng ghi/đọc một file: tên tạm riêng mỗi luồng; os.replace bị
    Windows từ chối (file đang có luồng khác mở đọc) thì thử lại."""
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    for lan in range(12):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05 * (lan + 1))
    os.replace(tmp, path)                                    # lần cuối: để lỗi nổi lên nếu vẫn bị chặn


_TK = {"ds": None, "i": 0}
_CHAN = set()                # 15/10 user: tài khoản ChatGPT bị Turnstile trong lượt chạy này -> không dùng nữa (Gemini thay)


def _la_turnstile(e):
    """Lỗi ChatGPT do bị đòi Turnstile (Cloudflare chặn máy) — cookie vẫn sống nhưng đường cookie không qua được."""
    return "turnstile" in str(e).lower()


def _gemini_ds():
    """Tài khoản Gemini ĐÃ ĐẶT TÊN (không trùng phiên) — làn dự phòng khi ChatGPT bị chặn."""
    sys.path.insert(0, os.path.join(ROOT, "tts"))
    try:
        import gemini_cookie_store as kg
        return list(kg.unique_account_ids(kg.named_account_ids()))
    except Exception:                                      # noqa: BLE001
        return []


def _tai_khoan():
    """Id tài khoản ChatGPT (cookie) trong kho dùng chung của máy, mới cập nhật xếp trước.
    Máy có CapCut TTS Studio: dùng chung kho của nó; không có: kho riêng %LOCALAPPDATA%\\BanContent (thẻ 🍪 Cookie).
    14/10: CHỈ tài khoản ĐÃ ĐẶT TÊN (log từng dùng 'acc-yXAm7Bw' tên tự sinh, cookie hết hạn)."""
    if _TK["ds"] is None:
        sys.path.insert(0, os.path.join(ROOT, "tts"))
        import chatgpt_cookie_store as kho
        ds = sorted(kho.list_accounts(), key=lambda a: a.get("tuoi_giay", 1e12))
        ten = set(kho.KHO.named_account_ids())
        _TK["ds"] = [a["id"] for a in ds if a.get("co_session") and a["id"] in ten]
    return [a for a in _TK["ds"] if a not in _CHAN]


def gon_loi(e, n=90):
    """Lỗi gọn MỘT dòng cho log: bỏ thẻ HTML (trang lỗi 403 của ChatGPT) và xuống dòng."""
    t = re.sub(r"<[^>]*>", " ", str(e))
    return re.sub(r"\s+", " ", t).strip()[:n]


_GM = {"i": 0, "da_bao": False}


def hoi_gemini(prompt, timeout=240):
    """15/10 user: "nếu toàn bộ ChatGPT lỗi thì dùng Gemini để hỏi". Một lượt hỏi Gemini web (cookie, chỉ tài khoản ĐÃ
    ĐẶT TÊN, xoay vòng; chế độ trò chuyện tạm) -> text ('' nếu mọi tài khoản đều hỏng)."""
    sys.path.insert(0, os.path.join(ROOT, "tts"))
    try:
        import gemini_cookie_store as kg
        import gemini_web_client as gw
        ds = kg.unique_account_ids(kg.named_account_ids())
    except Exception as e:                                 # noqa: BLE001
        log(f"    (gemini dự phòng không dùng được: {gon_loi(e)})")
        return ""
    if not _GM["da_bao"]:
        log("    ChatGPT lỗi hết -> hỏi Gemini (cookie) thay")
        _GM["da_bao"] = True
    for _ in range(min(len(ds), 4)):
        acc = ds[_GM["i"] % len(ds)]
        _GM["i"] += 1
        try:
            kq = gw.ask(acc, prompt, timeout=timeout, retries=1)
            if kq:
                return kq
        except Exception as e:                             # noqa: BLE001
            log(f"    (gemini '{acc}' lỗi: {gon_loi(e)} → đổi tài khoản)")
    return ""


def _tat_chatgpt():
    """BC_TAT_CHATGPT=1: giả lập mọi tài khoản ChatGPT đều hỏng (để thử đường Gemini dự phòng)."""
    return bool(os.environ.get("BC_TAT_CHATGPT"))


def hoi_llm(prompt, timeout=240):
    """Một lượt hỏi ChatGPT web bằng cookie; tài khoản lỗi thì xoay sang tài khoản kế.
    Trả text; mọi tài khoản ChatGPT hỏng -> hỏi Gemini (15/10 user); vẫn hỏng -> ''."""
    sys.path.insert(0, os.path.join(ROOT, "tts"))
    import chatgpt_web_client as cw
    ds = [] if _tat_chatgpt() else _tai_khoan()
    for _ in range(min(len(ds), 5)):
        acc = ds[_TK["i"] % len(ds)]
        try:
            kq = cw.ask(acc, prompt, timeout=timeout, retries=1)
            if kq:
                return kq
        except Exception as e:                             # noqa: BLE001
            if _la_turnstile(e):                           # 15/10 user: bị Turnstile -> nghỉ tài khoản này cả lượt chạy
                _CHAN.add(acc)
                log(f"    (chatgpt '{acc}' bị Turnstile — nghỉ trong lượt này)")
            else:
                log(f"    (chatgpt '{acc}' lỗi: {gon_loi(e)} → đổi tài khoản)")
        _TK["i"] += 1
    return hoi_gemini(prompt, timeout=timeout)


def hoi_nhieu(prompts, timeout=240, on_xong=None):
    """Hỏi ChatGPT nhiều lô CÙNG LÚC: MỖI COOKIE MỘT LUỒNG (mỗi cookie phiên khác nhau là một làn, cookie trùng
    không tạo thêm làn), các luồng lấy lô từ một hàng đợi chung nên luồng nào xong trước nhận lô kế.
    Lô lỗi được trả lại hàng đợi cho cookie khác (tối đa 3 lần); cookie lỗi 3 lô liên tiếp thì nghỉ.
    Trả list text theo thứ tự `prompts` ('' nếu thử hết không được). on_xong(i, text) gọi ở luồng gọi, ngay khi
    lô i xong (để ghi cache dần, dừng giữa chừng không mất phần đã có)."""
    import queue
    import threading
    sys.path.insert(0, os.path.join(ROOT, "tts"))
    import chatgpt_web_client as cw
    import chatgpt_cookie_store as kho
    ds = [] if _tat_chatgpt() else _tai_khoan()
    lan = [a for a in kho.unique_account_ids(ds)] if len(ds) > 1 else list(ds)
    ra = [""] * len(prompts)
    if not lan and len(prompts) > 1:                      # không còn tài khoản ChatGPT nào: thẳng sang Gemini
        return _bu_gemini(prompts, ra, timeout, on_xong)
    if len(prompts) <= 1 or len(lan) <= 1:
        for i, p in enumerate(prompts):
            ra[i] = hoi_llm(p, timeout=timeout)
            if on_xong:
                on_xong(i, ra[i])
        return ra
    viec = queue.Queue()
    for i in range(len(prompts)):
        viec.put((i, 0))
    xong_q = queue.Queue()
    con = [len(prompts)]                                  # số lô chưa có kết quả cuối (chỉ luồng chính đụng)

    ths = []
    gm = _gemini_ds()
    khoa_gm = threading.Lock()

    def mo_luong_gemini():
        """15/10 user: một tài khoản ChatGPT bị Turnstile -> mở NGAY một luồng Gemini thay chỗ (cùng hàng đợi)."""
        with khoa_gm:
            if not gm:
                return
            g = gm[_GM["i"] % len(gm)]
            _GM["i"] += 1
        t = threading.Thread(target=luong_gemini, args=(g,), daemon=True)
        ths.append(t)
        t.start()

    def luong_gemini(acc):
        import gemini_web_client as gw
        loi_lien_tiep = 0
        while loi_lien_tiep < 3:
            try:
                i, lan_thu = viec.get_nowait()
            except queue.Empty:
                return
            kq = ""
            try:
                kq = gw.ask(acc, prompts[i], timeout=timeout, retries=1) or ""
            except Exception as e:                        # noqa: BLE001
                log(f"    (gemini '{acc}' lỗi: {gon_loi(e)})")
            if kq:
                loi_lien_tiep = 0
                xong_q.put((i, kq))
            else:
                loi_lien_tiep += 1
                if lan_thu + 1 < 3:
                    viec.put((i, lan_thu + 1))
                else:
                    xong_q.put((i, ""))

    def luong(acc):
        loi_lien_tiep = 0
        while loi_lien_tiep < 3:
            try:
                i, lan_thu = viec.get_nowait()
            except queue.Empty:
                return
            kq = ""
            try:
                kq = cw.ask(acc, prompts[i], timeout=timeout, retries=1) or ""
            except Exception as e:                        # noqa: BLE001
                if _la_turnstile(e):                      # 15/10 user: bị Turnstile -> nghỉ hẳn tài khoản này, Gemini thay
                    _CHAN.add(acc)
                    log(f"    (chatgpt '{acc}' bị Turnstile — nghỉ trong lượt này, chuyển sang Gemini)")
                    viec.put((i, lan_thu))                # lô không tính lần thử (lỗi do tài khoản, không do lô)
                    mo_luong_gemini()
                    return
                log(f"    (chatgpt '{acc}' lỗi: {gon_loi(e)} — tài khoản khác làm thay)")
            if kq:
                loi_lien_tiep = 0
                xong_q.put((i, kq))
            else:
                loi_lien_tiep += 1
                if lan_thu + 1 < 3:
                    viec.put((i, lan_thu + 1))            # lô này để cookie khác thử
                else:
                    xong_q.put((i, ""))
        # luồng nghỉ: nếu còn lô mà mọi luồng đã nghỉ, luồng chính sẽ phát hiện ở dưới
    for a in lan:
        ths.append(threading.Thread(target=luong, args=(a,), daemon=True))
    for t in list(ths):
        t.start()
    while con[0] > 0:
        try:
            i, kq = xong_q.get(timeout=2)
        except queue.Empty:
            if not any(t.is_alive() for t in list(ths)) and xong_q.empty():
                break                                     # mọi cookie đã nghỉ mà còn lô -> bỏ phần còn lại
            continue
        ra[i] = kq
        con[0] -= 1
        if on_xong and kq:
            on_xong(i, kq)
    return _bu_gemini(prompts, ra, timeout, on_xong)


def _bu_gemini(prompts, ra, timeout, on_xong):
    """15/10 user: lô mà MỌI tài khoản ChatGPT đều hỏng -> hỏi Gemini (cookie) thay, song song 4 luồng."""
    thieu = [i for i, t in enumerate(ra) if not t]
    if thieu:
        from concurrent.futures import ThreadPoolExecutor
        log(f"    {len(thieu)}/{len(prompts)} lô ChatGPT không trả lời -> hỏi Gemini")
        with ThreadPoolExecutor(min(4, len(thieu))) as ex:
            for i, kq in zip(thieu, ex.map(lambda k: hoi_gemini(prompts[k], timeout=timeout), thieu)):
                ra[i] = kq or ""
                if on_xong:
                    on_xong(i, ra[i])
    return ra


def thu_muc_nhap_capcut():
    """Thư mục 'CapCut Drafts' CapCut đang dùng (dò từ chỉ mục của CapCut); None nếu không thấy."""
    meta = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CapCut", "User Data",
                        "Projects", "com.lveditor.draft", "root_meta_info.json")
    try:
        with open(meta, encoding="utf-8") as f:
            ds = json.load(f).get("all_draft_store", [])
    except (OSError, ValueError):
        return None
    for it in ds:
        p = it.get("draft_fold_path") or ""
        if p:
            cha = os.path.dirname(p.replace("/", os.sep))
            if os.path.isdir(cha):
                return cha
    return None


def rut_json(text):
    """Lấy khối JSON đầu tiên (object hoặc mảng) trong câu trả lời của model."""
    if not text:
        return None
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    for mo, dong in (("{", "}"), ("[", "]")):
        i, j = t.find(mo), t.rfind(dong)
        if i >= 0 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                continue
    return None


def chay(lenh, timeout=None):
    """subprocess ngầm, không hiện cửa sổ. Trả (mã, stdout, stderr)."""
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000
    p = subprocess.run(lenh, capture_output=True, timeout=timeout, **kw)
    return (p.returncode, p.stdout.decode("utf-8", "ignore"),
            p.stderr.decode("utf-8", "ignore"))


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------- tiến độ cho giao diện
import threading
import time

_KHOA_TD = threading.Lock()


def thu_muc_du_an(ten):
    """(cache, out) của một dự án — cùng quy tắc với DU_AN ở trên (dự án đầu tiên giữ chỗ cũ)."""
    if ten in _CU:
        return CACHE_CHUNG, os.path.join(ROOT, "ra")
    return os.path.join(CACHE_CHUNG, "du_an", ten), os.path.join(ROOT, "ra", ten)


def eta_chu(bd, xong, tong):
    """'còn ~2:10' theo tốc độ đã chạy (bd = time.time() lúc bắt đầu); '' nếu chưa đủ dữ liệu."""
    if xong < 2 or tong <= xong:
        return ""
    con = (time.time() - bd) / xong * (tong - xong)
    return f" · còn ~{int(con // 60)}:{int(con % 60):02d}"


def tien_do(buoc, trang_thai, ghi_chu=""):
    """Ghi trạng thái một bước (cho giao diện đọc): trang_thai = 'cho' | 'dang' | 'xong' | 'loi'."""
    p = os.path.join(OUT, "trang_thai.json")
    with _KHOA_TD:
        d = doc_json(p, {}) or {}
        cu = d.setdefault("buoc", {}).get(buoc) or {}
        bay_gio = time.time()
        bd = cu.get("bd") if cu.get("tt") == "dang" else None          # giữ mốc bắt đầu khi chỉ cập nhật ghi chú
        if trang_thai in ("dang", "xong", "loi") and bd is None:
            bd = bay_gio
        d["buoc"][buoc] = {"tt": trang_thai, "ghi_chu": ghi_chu, "luc": bay_gio, "bd": bd if trang_thai != "cho" else None,
                           "kt": bay_gio if trang_thai in ("xong", "loi") else None}
        d["cap_nhat"] = time.time()
        ghi_json(p, d)


def xoa_tien_do():
    p = os.path.join(OUT, "trang_thai.json")
    if os.path.isfile(p):
        os.remove(p)


# onnxruntime bản GPU (CUDA 12) cài riêng ở ort_gpu/ để không đụng môi trường chung; có thì ưu tiên cho OCR.
_ORT_GPU = os.path.join(ROOT, "ort_gpu")
if os.path.isdir(_ORT_GPU) and _ORT_GPU not in sys.path and "onnxruntime" not in sys.modules:
    sys.path.insert(0, _ORT_GPU)
