# -*- coding: utf-8 -*-
"""VIDEO VEO Ở THÂN BÀI (27/10 user: "đoạn sau không tạo ảnh nữa mà dùng Veo 3 lấp vào những cảnh nên lấp" — người dùng tự
đánh dấu chỗ 🎬 Veo trong danh sách 📝 Chỗ ảnh AI & Veo, giống đánh dấu chỗ vẽ ảnh).

Mỗi chỗ Veo = MỘT clip 10 s (x1) phủ từ câu đầu của chỗ đó (tối đa 10 s), câu lệnh tiếng Anh `veo_en` (AI viết, người
dùng sửa). Tạo bằng flow_video.chay_theo_tai_khoan (hạn điểm/ngày, 4 tài khoản × 2 tab). Clip đã có (cùng câu lệnh) dùng
lại. Chỗ không có clip (hết điểm / lỗi / không tick tạo) -> bên gọi vẽ ẢNH AI thay (0 điểm), không để màn đen."""
import hashlib
import os
import re
import sys

from common import LUAT_NGOAI_TRUYEN, LUAT_THUC_TE, doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

VEO_MODEL = "Omni 1.1 Flash"
VEO_PHAN_GIAI = "720p"
VEO_GIAY = 8                 # 28/10 user: Veo 8 s = 12 điểm (10 s = 15 điểm) — mặc định 8 s
KE_HOACH_AI = "anh_ai_ke_hoach.json"

_P_VEO = """You write AI VIDEO prompts (Google Veo / Flow, 10-second clips, 16:9) for scenes of a documentary narration.
{ho_so}
For each numbered scene below write ONE English video prompt, 50-100 words, as 2-3 SHOTS with hard cuts ("Shot 1: … Cut to
shot 2: …") showing exactly what the narration describes at that moment: subject and action, setting and the ERA of that
moment (period-correct clothing, vehicles, buildings), a cinematic camera move, lighting and atmosphere. The same
characters, costumes, colour grade and light as the story profile. Real-looking live action, no text, no captions, no
logos. Never show the face of a real named person (silhouettes, from behind, hands, wide shots). End every prompt with:
"Natural ambient sound effects only, no dialogue, no voice-over, no music."
Show the event exactly as the narration describes it, even if it is raw nature (carcasses, scavengers, decay) — do not soften
or replace it; the editor blurs on-screen if needed. """ + LUAT_THUC_TE + " " + LUAT_NGOAI_TRUYEN + """
{ds}
Return ONLY JSON: {{"<scene number>": "<prompt>"}}"""


# 28/10 user ("trường hợp nó không tạo cho mình thì lúc đó sửa câu lệnh khác để tạo"): Flow TỪ CHỐI NỘI DUNG -> AI viết lại
# câu lệnh (giữ đúng khoảnh khắc, đổi cách tả chỗ dễ bị chặn) và thử lại MỘT lần; câu lệnh mới lưu vào 📝. Tắt: False
VIET_LAI_KHI_BI_CHAN = True
_P_VIET_LAI = """Google Veo REFUSED this AI video prompt for a documentary (Flow said: "{loi}").
Rewrite it so Veo accepts it while showing the SAME moment of the narration (same subject, place, action and era): keep it
real-looking live action, 2-3 shots with hard cuts, 50-100 words; describe the sensitive part more factually and less
explicitly (e.g. wide or partly hidden view, natural-history tone) instead of removing it. Never a real person's face.
End with: "Natural ambient sound effects only, no dialogue, no voice-over, no music."
NARRATION: {loi_doc}
REFUSED PROMPT: {lenh}
Return ONLY the new prompt text."""


def _bi_tu_choi(loi):
    """Lỗi do Flow từ chối NỘI DUNG (không phải hết điểm / xác minh / chờ quá lâu)."""
    loi = str(loi or "")
    return "Flow báo" in loi and not re.search(r"credits|unusual|verify|captcha|quota", loi, re.I)


def _viet_lai(out, y, cau_theo):
    """AI viết lại câu lệnh bị chặn của chỗ y -> True nếu đã đổi (lưu luôn vào 📝)."""
    i = int(y["cau"])
    loi_doc = " ".join(cau_theo[j]["text"] for j in range(i, int(y.get("den_cau") or i) + 1) if j in cau_theo)
    moi = (hoi_llm(_P_VIET_LAI.format(loi=str(y.get("_loi") or "")[:200], loi_doc=loi_doc, lenh=y["veo_en"]),
                   timeout=180) or "").strip().strip('"')
    if len(moi.split()) < 25 or moi == y["veo_en"]:
        return False
    da = doc_json(_p(out), {}) or {}
    for z in da.get("ds") or []:
        if isinstance(z, dict) and str(z.get("veo_en") or "").strip() == y["veo_en"].strip():
            z["veo_en"] = moi
    ghi_json(_p(out), da)
    log(f"    Veo câu {i}: bị Flow từ chối -> AI viết lại câu lệnh, thử lại")
    y["veo_en"] = moi
    return True


def _p(out):
    return os.path.join(out, KE_HOACH_AI)


def ho_so(out, cau):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
        import dieu_phoi
        return dieu_phoi.ho_so([{"i": c["i"], "text": c.get("text") or ""} for c in cau], out)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! Veo: không lập được hồ sơ câu chuyện ({str(e)[:80]})")
        return ""


def viet_lenh(out, cau, tu_giay=0.0):
    """Chỗ 🎬 Veo chưa có câu lệnh -> AI viết một lượt, lưu vào danh sách 📝 (người dùng thấy / sửa)."""
    da = doc_json(_p(out), {}) or {}
    theo = {c["i"]: c for c in cau}
    thieu = [y for y in da.get("ds") or [] if isinstance(y, dict) and y.get("loai") == "veo" and not y.get("bo")
             and not str(y.get("veo_en") or "").strip() and int(y.get("cau") or 0) in theo
             and float(theo[int(y["cau"])].get("t0") or 0) >= tu_giay - 0.3]   # 27/10: chỗ trong đoạn hook Veo bỏ qua
    if not thieu:
        return 0
    ds = "\n".join(f"{y['cau']}: " + " ".join(theo[j]["text"] for j in range(int(y["cau"]), int(y.get("den_cau") or y["cau"]) + 1)
                                              if j in theo) for y in thieu)
    log(f"[Veo] AI viết câu lệnh cho {len(thieu)} chỗ Veo…")
    j = rut_json(hoi_llm(_P_VEO.format(ho_so=ho_so(out, cau), ds=ds), timeout=240) or "") or {}
    n = 0
    for y in thieu:
        v = str((j.get(str(y["cau"])) if isinstance(j, dict) else "") or "").strip()
        if v:
            y["veo_en"] = v
            n += 1
    ghi_json(_p(out), da)
    return n


def _dai_clip(f):
    """Độ dài (giây) của file clip; đọc lỗi -> VEO_GIAY."""
    try:
        import pycapcut as draft
        return draft.VideoMaterial(f).duration / 1e6
    except Exception:                                        # noqa: BLE001
        return float(VEO_GIAY)


def _ten(prompt):
    return "veo_" + hashlib.md5((VEO_MODEL + VEO_PHAN_GIAI + prompt).encode("utf-8")).hexdigest()[:12]


def _sach(g, f):
    """Xoá logo ✦ của video Flow g -> f (lỗi thì dùng bản gốc)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinh_sua"))
    import anh_ve
    tam = f[:-4] + "._sach.mp4"
    try:
        anh_ve.xoa_logo_video(g, tam, lambda m: None)
        os.replace(tam, f)
    except Exception as e:                                   # noqa: BLE001
        log(f"    ! Veo: xoá logo lỗi ({str(e)[:80]}) -> dùng bản gốc")
        if os.path.isfile(tam):
            os.remove(tam)
        os.replace(g, f)
    if os.path.isfile(g):
        os.remove(g)


def lich(du_an, cho, cau, tao_moi=False, bao=None):
    """cho: các chỗ 🎬 Veo (dict có cau, den_cau, veo_en). -> (lich [{bd, het, file, am, cau}], [chỗ KHÔNG có clip]).
    tao_moi=True: chỗ chưa có clip thì tạo bằng Flow (tốn điểm); False: chỉ dùng clip đã có."""
    import flow_video
    bao = bao or (lambda m: log("    " + m))
    out = thu_muc_du_an(du_an)[1]
    thu = os.path.join(out, "veo")
    os.makedirs(thu, exist_ok=True)
    theo = {c["i"]: c for c in cau}
    co, thieu = {}, []
    for y in cho:
        v = str(y.get("veo_en") or "").strip()
        f = os.path.join(thu, _ten(v) + ".mp4") if v else ""
        if f and os.path.isfile(f) and os.path.getsize(f) > 20000:
            co[id(y)] = f
        elif v:
            thieu.append(y)
    if thieu and tao_moi:
        can = flow_video.uoc_diem(VEO_MODEL, VEO_PHAN_GIAI)
        bao(f"Veo thân bài: tạo {len(thieu)} clip (hôm nay còn điểm cho {flow_video.clip_con_hom_nay(can)} clip — "
            f"hook tạo trước)")

        def tao(y, ho_so_, khe):
            ten = _ten(y["veo_en"].strip())
            try:
                r = flow_video.tao(y["veo_en"].strip(), thu, ten + "_goc", model=VEO_MODEL, phan_giai=VEO_PHAN_GIAI,
                                   do_dai=f"{VEO_GIAY}s", so=1, ho_so=ho_so_, khe=khe, gioi_han=True, bao=lambda m: None)
            except Exception as e:                           # noqa: BLE001  27/10: giữ lý do cho 📝
                y["_loi"] = f"{ho_so_}: {str(e)[:160]}"
                raise
            if not r.get("tep"):
                return None
            f = os.path.join(thu, ten + ".mp4")
            _sach(r["tep"][0], f)
            bao(f"Veo câu {y['cau']}: xong ({r.get('diem')} điểm, hồ sơ {r.get('ho_so')})")
            return f
        for y, f in zip(thieu, flow_video.chay_theo_tai_khoan(thieu, tao, can=can, bao=bao)):
            if f:
                co[id(y)] = f
        bi_chan = [y for y in thieu if id(y) not in co and _bi_tu_choi(y.get("_loi"))] if VIET_LAI_KHI_BI_CHAN else []
        lai = [y for y in bi_chan if _viet_lai(out, y, theo)]
        if lai:
            bao(f"Veo thân bài: {len(lai)} câu lệnh bị Flow từ chối đã viết lại -> tạo lại")
            for y in lai:
                y.pop("_loi", None)
            for y, f in zip(lai, flow_video.chay_theo_tai_khoan(lai, tao, can=can, bao=bao)):
                if f:
                    co[id(y)] = f
        _ghi_loi(out, thieu, co, can)
    ra, khong = [], []
    for y in cho:
        f = co.get(id(y))
        i = int(y["cau"])
        if not f or i not in theo:
            khong.append(y)
            continue
        den = max(i, min(int(y.get("den_cau") or i), i + 2))
        cuoi = theo.get(den) or theo[i]
        bd, het = float(theo[i]["t0"]), float(cuoi["t1"])
        ke = theo.get(cuoi["i"] + 1)
        if ke and 0 <= float(ke["t0"]) - het < 1.5:
            het = float(ke["t0"])
        het = min(het, bd + _dai_clip(f))                    # 28/10: độ dài THẬT của clip (cũ 10 s, mới 8 s)
        if het - bd >= 1.0:
            ra.append({"bd": round(bd, 2), "het": round(het, 2), "file": f, "am": "tieng_dong", "cau": i})
    if cho:
        bao(f"Veo thân bài: {len(ra)}/{len(cho)} chỗ có clip" + (f", {len(khong)} chỗ chưa có clip (lấp footage)" if khong else ""))
    return ra, khong


def _ghi_loi(out, thieu, co, can):
    """27/10 user ("tại sao lại chưa hết điểm lại không tạo được"): lý do từng chỗ 🎬 không ra clip -> loi_veo trong 📝
    (Flow từ chối nội dung / hết điểm / chưa tới lượt); chỗ ra clip thì xoá lý do cũ."""
    import flow_video
    da = doc_json(_p(out), {}) or {}
    con = flow_video.clip_con_hom_nay(can)
    theo = {str(y.get("veo_en") or "").strip(): y for y in thieu}
    for z in da.get("ds") or []:
        y = theo.get(str(z.get("veo_en") or "").strip()) if isinstance(z, dict) else None
        if y is None:
            continue
        if id(y) in co:
            z.pop("loi_veo", None)
        else:
            z["loi_veo"] = y.get("_loi") or ("hết điểm Flow (mọi tài khoản) — mai bấm 🎨 tiếp" if not con
                                             else "chưa tới lượt / tài khoản bị bỏ giữa chừng — bấm 🎨 lại")
    ghi_json(_p(out), da)


def so_clip_can(out, cau, tu_giay=0.0):
    """27/10 user: số clip Veo thân bài CÒN PHẢI TẠO = chỗ 🎬 Veo trong 📝 (không bỏ, sau đoạn hook) chưa có clip."""
    da = doc_json(_p(out), {}) or {}
    theo = {c["i"]: c for c in cau}
    n = 0
    for y in da.get("ds") or [] if da.get("duyet") is not False else []:
        if not isinstance(y, dict) or y.get("loai") != "veo" or y.get("bo") or int(y.get("cau") or 0) not in theo \
                or float(theo[int(y["cau"])].get("t0") or 0) < tu_giay - 0.3:
            continue
        v = str(y.get("veo_en") or "").strip()
        f = os.path.join(out, "veo", _ten(v) + ".mp4") if v else ""
        if not (f and os.path.isfile(f) and os.path.getsize(f) > 20000):
            n += 1
    return n
