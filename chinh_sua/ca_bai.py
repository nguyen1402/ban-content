# -*- coding: utf-8 -*-
"""🎬 REMOTION CẢ BÀI — một nút (05/11 user: "bấm vào nó làm 1 việc: remotion toàn bộ, ghép nhạc, hiệu ứng âm thanh cho nội
dung đã đọc"; "an toàn tránh quá tải"; thêm hồ sơ "chỉ để tránh tạo ảnh AI nhiều — lánh sang tạo").

  1. bản nháp MỚI <dự án>_hoan_chinh_remotion_<ngày>_<giờ> chép từ bản nháp giọng đọc <dự án> (không ghi đè bản cũ);
  2. kế hoạch 🎞 phủ mọi câu chưa có chỗ (gộp câu ngắn liền nhau, như nút «🎞 Remotion mọi câu trống»);
  3. dựng nhanh (Gemini thiết kế, DeepSeek viết code, Flow vẽ ảnh) — số cảnh cùng lúc theo hồ sơ + RAM, ảnh Flow rải đều
     mọi hồ sơ (mỗi hồ sơ ~1 ảnh cùng lúc, trần cứng 3); cảnh đã có giữ nguyên trừ khi lam_lai;
  4. cảnh lỗi làm lại một lượt (ít cảnh cùng lúc);
  5. ghép cảnh + SFX từng cảnh vào bản nháp mới, thêm nhạc nền theo chương / tâm trạng (kho nhạc sạch)."""
import ctypes
import json
import os
import shutil
import threading
import time
import uuid

import nhan_y
import nhan_y_ai as ai
from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an, thu_muc_nhap_capcut

CANH_TOI_DA = 9              # thêm hồ sơ là để rải ảnh Flow, không phải để dồn thêm cảnh (user 05/11)
GB_MOI_CANH = 2.0            # mỗi cảnh làm cùng lúc cần ~bấy nhiêu GB RAM trống (Chrome Gemini / DeepSeek / Flow + dựng thử)
GOP_CAU, GOP_GIAY = 3, 13.5  # kế hoạch: gộp tối đa bấy nhiêu câu liền nhau / giây lời vào một cảnh


def ram_trong():
    """(GB trống, % trống) của máy (Windows)."""
    class M(ctypes.Structure):
        _fields_ = [("l", ctypes.c_ulong), ("tai", ctypes.c_ulong), ("tong", ctypes.c_ulonglong),
                    ("trong", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                    ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
    m = M()
    m.l = ctypes.sizeof(M)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return 8.0, 50.0
    return m.trong / 2 ** 30, 100.0 * m.trong / max(1, m.tong)


def so_ho_so():
    """{gemini, deepseek, flow}: số hồ sơ dùng được lúc này."""
    import flow_ve
    import gemini_chrome as g
    ra = {"gemini": sum(1 for t, _ in g._ho_so() if g._san(t)), "flow": flow_ve.so_ho_so_dung_duoc()}   # noqa: SLF001
    try:
        ds = 0
        for t, c in g._ho_so():                                          # noqa: SLF001
            try:
                g._json(c)                                               # noqa: SLF001  (đã mở có cổng: dùng được)
                ds += 1
                continue
            except OSError:
                pass
            if not os.path.exists(os.path.join(flow_ve.GOC, flow_ve._slug(t), "lockfile")):   # noqa: SLF001
                ds += 1                                                  # chưa mở: tự mở có cổng được
        ra["deepseek"] = ds
    except Exception:                                                    # noqa: BLE001
        ra["deepseek"] = ra["gemini"]
    return ra


def can_bang(bao):
    """Số cảnh cùng lúc (theo hồ sơ + RAM, trần CANH_TOI_DA) và số ảnh Flow cùng lúc (~1 / hồ sơ Flow)."""
    hs = so_ho_so()
    gb, _ = ram_trong()
    can = [hs["gemini"]] + ([hs["deepseek"]] if "deepseek" in (ai.AI_CODE, ai.AI_THIET_KE) else [])
    n = max(2, min(CANH_TOI_DA, min(can), int(gb // GB_MOI_CANH)))
    nf = max(2, hs["flow"])
    ai.FLOW_TOI_DA = nf
    ai._FLOW_KHOA = threading.BoundedSemaphore(nf)                       # noqa: SLF001
    bao(f"hồ sơ dùng được: Gemini {hs['gemini']}, DeepSeek {hs.get('deepseek')}, Flow {hs['flow']} · RAM trống "
        f"{gb:.0f} GB -> {n} cảnh cùng lúc, {nf} ảnh Flow cùng lúc (mỗi hồ sơ tối đa 3)")
    return n


def ke_hoach_day(du_an):
    """Thêm chỗ 🎞 cho mọi câu chưa có chỗ (giữ nguyên chỗ đã có, kể cả chỗ user bỏ tích). -> số chỗ thêm."""
    cau = ai._cau_ke_hoach(du_an)                                       # noqa: SLF001
    kh = ai.doc_ke_hoach(du_an)
    phu = {i for y in kh for i in range(y["cau"], (y.get("den_cau") or y["cau"]) + 1)}
    them, g = [], None
    for c in cau:
        if c["i"] in phu:
            g = None
            continue
        if g and c["i"] == g["den_cau"] + 1 and c["i"] - g["cau"] < GOP_CAU and c["t1"] - g["_t0"] <= GOP_GIAY:
            g["den_cau"] = c["i"]
            continue
        g = {"cau": c["i"], "den_cau": c["i"], "y_chinh": "", "tay": True, "bo": False, "_t0": c["t0"]}
        them.append(g)
    if them:
        ai.luu_ke_hoach(du_an, kh + [{k: v for k, v in x.items() if k != "_t0"} for x in them])
    return len(them)


def ban_nhap_moi(du_an):
    """Chép bản nháp giọng đọc <dự án> thành <dự án>_hoan_chinh_remotion_<ngày>_<giờ> (mới nhất -> nơi ghép). -> đường."""
    dd = thu_muc_nhap_capcut()
    goc = os.path.join(dd, du_an)
    if not os.path.isfile(os.path.join(goc, "draft_content.json")):
        raise ValueError(f"chưa có bản nháp giọng đọc '{du_an}' — chạy bước đọc giọng / tạo bản nháp trước")
    ten = f"{du_an}_hoan_chinh_remotion_{time.strftime('%d%m_%H%M')}"
    moi = os.path.join(dd, ten)
    if os.path.exists(moi):
        raise ValueError(f"bản nháp '{ten}' đã có")
    shutil.copytree(goc, moi)
    pm = os.path.join(moi, "draft_meta_info.json")
    m = doc_json(pm, {}) or {}
    m.update(draft_name=ten, draft_id=str(uuid.uuid4()).upper(), draft_fold_path=moi.replace(os.sep, "/"))
    ghi_json(pm, m)
    os.utime(os.path.join(moi, "draft_content.json"))
    return moi


def them_nhac(du_an, p, bao):
    """Nhạc nền theo chương + tâm trạng (AI chia chương như ✨ Hoàn thiện, kho nhạc sạch) -> track 'nhac_nen' của bản nháp."""
    import glob
    import pycapcut as draft
    from pycapcut import trange
    import dung_hoan_chinh as dh
    cau = ai._cau_ke_hoach(du_an)                                       # noqa: SLF001
    if not cau:
        return 0
    am = dh._kho_am_thanh()                                              # noqa: SLF001
    if not any(v.get("loai") == "nhac" for v in am.values()):
        bao("kho chưa có nhạc nền — bỏ qua nhạc")
        return 0
    f_ch = os.path.join(thu_muc_du_an(du_an)[1], "nhac_chuong_remotion.json")
    nho = doc_json(f_ch, {}) or {}
    khoa = ai.nhan_y._md5(*[c["text"] for c in cau])                    # noqa: SLF001
    ch = nho.get("ch") if nho.get("khoa") == khoa else None
    if not ch:
        bao("AI chia chương + tâm trạng nhạc…")
        ds = "\n".join(f"{c['i']}. {c['text'][:45]}" for c in cau)
        ch = rut_json(hoi_llm(dh._P_CHUONG.format(n=len(cau), ds=ds), timeout=300)) or []   # noqa: SLF001
        ch = [x for x in ch if isinstance(x, dict) and "tu_cau" in x and "den_cau" in x]
        if not ch:
            k = max(1, len(cau) // 5)
            ch = [{"tu_cau": i * k + 1, "den_cau": (i + 1) * k if i < 4 else len(cau), "tam_trang": "dien_anh"} for i in range(5)]
        ghi_json(f_ch, {"khoa": khoa, "ch": ch})
    theo = {c["i"]: c for c in cau}
    tong = cau[-1]["t1"]
    chuong = []
    for x in sorted(ch, key=lambda z: int(z["tu_cau"])):
        a, b = int(x["tu_cau"]), int(x["den_cau"])
        ca, cb = theo.get(a) or cau[0], theo.get(b) or cau[-1]
        chuong.append({"tu_cau": a, "den_cau": b, "tam_trang": x.get("tam_trang", "dien_anh"), "tu": ca["t0"], "den": cb["t1"]})
    chuong[0]["tu"], chuong[-1]["den"] = 0.0, tong
    nhac = dh.chon_nhac(chuong, am)
    f = os.path.join(p, "draft_content.json")
    d = nhan_y._doc(f)                                                   # noqa: SLF001
    sc = draft.ScriptFile(1920, 1080)
    sc.add_track(draft.TrackType.audio, track_name="nhac_nen")
    US = 1_000_000
    for m in nhac:
        mat = draft.AudioMaterial(m["file"])
        dai = min(int((m["den"] - m["tu"]) * US), int(mat.duration))
        seg = draft.AudioSegment(mat, trange(int(m["tu"] * US), dai), source_timerange=trange(0, dai), volume=m["vol"])
        seg.add_fade(int(2.0 * US), int(2.5 * US))
        sc.add_segment(seg, "nhac_nen")
    moi = json.loads(sc.dumps())
    for kk, v in moi["materials"].items():
        if isinstance(v, list) and v:
            co = {x.get("id") for x in d["materials"].setdefault(kk, [])}
            d["materials"][kk] += [x for x in v if x.get("id") not in co]
    d["tracks"] = [t for t in d["tracks"] if t.get("name") != "nhac_nen"] + [t for t in moi["tracks"] if t["segments"]]
    for g in [f] + glob.glob(os.path.join(p, "Timelines", "*", "draft_content.json")):
        nhan_y._ghi(g, d)                                                # noqa: SLF001
    bao(f"nhạc nền: {len(nhac)} đoạn theo {len(chuong)} chương")
    return len(nhac)


def chay(du_an, lam_lai=False, bao=None):
    """Cả quy trình. -> {nhap, xong, loi, them_ke_hoach, nhac}"""
    bao = bao or (lambda m: log("  " + m))
    p = ban_nhap_moi(du_an)
    bao(f"bản nháp mới: {os.path.basename(p)}")
    them = ke_hoach_day(du_an)
    bao(f"kế hoạch: thêm {them} chỗ 🎞 cho câu chưa có" if them else "kế hoạch: mọi câu đã có chỗ 🎞")
    n = can_bang(bao)
    r = ai.dung(du_an, None, bao, lam_lai=lam_lai, song_song=n, tu_sua=False)
    ds = doc_json(ai._ds(du_an), {}) or {}                              # noqa: SLF001
    loi = sorted(int(k) for k, v in ds.items() if v.get("trang_thai") != "xong"
                 and any(y["cau"] == int(k) and not y.get("bo") for y in ai.doc_ke_hoach(du_an)))
    if loi:
        bao(f"làm lại {len(loi)} cảnh lỗi (ít cảnh cùng lúc)…")
        r = ai.dung(du_an, loi, bao, song_song=min(4, n), tu_sua=False)
    if not r.get("nhap"):
        ai.ghep(du_an, bao)
    try:
        nh = them_nhac(du_an, p, bao)
    except Exception as e:                                               # noqa: BLE001
        bao(f"! nhạc nền lỗi: {str(e)[:150]}")
        nh = 0
    ds = doc_json(ai._ds(du_an), {}) or {}                              # noqa: SLF001
    xong = sum(1 for v in ds.values() if v.get("trang_thai") == "xong")
    con = sum(1 for v in ds.values() if v.get("trang_thai") != "xong")
    bao(f"🎬 xong: {xong} cảnh, {con} cảnh lỗi, {nh} đoạn nhạc — bản nháp '{os.path.basename(p)}'")
    return {"nhap": os.path.basename(p), "xong": xong, "loi": con, "them_ke_hoach": them, "nhac": nh}
