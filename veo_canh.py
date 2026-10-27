# -*- coding: utf-8 -*-
"""VIDEO VEO Ở THÂN BÀI (27/10 user: "đoạn sau không tạo ảnh nữa mà dùng Veo 3 lấp vào những cảnh nên lấp" — người dùng tự
đánh dấu chỗ 🎬 Veo trong danh sách 📝 Chỗ ảnh AI & Veo, giống đánh dấu chỗ vẽ ảnh).

Mỗi chỗ Veo = MỘT clip 10 s (x1) phủ từ câu đầu của chỗ đó (tối đa 10 s), câu lệnh tiếng Anh `veo_en` (AI viết, người
dùng sửa). Tạo bằng flow_video.chay_theo_tai_khoan (hạn điểm/ngày, 4 tài khoản × 2 tab). Clip đã có (cùng câu lệnh) dùng
lại. Chỗ không có clip (hết điểm / lỗi / không tick tạo) -> bên gọi vẽ ẢNH AI thay (0 điểm), không để màn đen."""
import hashlib
import os
import sys

from common import doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an

VEO_MODEL = "Omni 1.1 Flash"
VEO_PHAN_GIAI = "720p"
VEO_GIAY = 10
KE_HOACH_AI = "anh_ai_ke_hoach.json"

_P_VEO = """You write AI VIDEO prompts (Google Veo / Flow, 10-second clips, 16:9) for scenes of a documentary narration.
{ho_so}
For each numbered scene below write ONE English video prompt, 50-100 words, as 2-3 SHOTS with hard cuts ("Shot 1: … Cut to
shot 2: …") showing exactly what the narration describes at that moment: subject and action, setting and the ERA of that
moment (period-correct clothing, vehicles, buildings), a cinematic camera move, lighting and atmosphere. The same
characters, costumes, colour grade and light as the story profile. Real-looking live action, no text, no captions, no
logos. Never show the face of a real named person (silhouettes, from behind, hands, wide shots). End every prompt with:
"Natural ambient sound effects only, no dialogue, no voice-over, no music."
{ds}
Return ONLY JSON: {{"<scene number>": "<prompt>"}}"""


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


def viet_lenh(out, cau):
    """Chỗ 🎬 Veo chưa có câu lệnh -> AI viết một lượt, lưu vào danh sách 📝 (người dùng thấy / sửa)."""
    da = doc_json(_p(out), {}) or {}
    theo = {c["i"]: c for c in cau}
    thieu = [y for y in da.get("ds") or [] if isinstance(y, dict) and y.get("loai") == "veo" and not y.get("bo")
             and not str(y.get("veo_en") or "").strip() and int(y.get("cau") or 0) in theo]
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
            r = flow_video.tao(y["veo_en"].strip(), thu, ten + "_goc", model=VEO_MODEL, phan_giai=VEO_PHAN_GIAI,
                               do_dai=f"{VEO_GIAY}s", so=1, ho_so=ho_so_, khe=khe, gioi_han=True, bao=lambda m: None)
            if not r.get("tep"):
                return None
            f = os.path.join(thu, ten + ".mp4")
            _sach(r["tep"][0], f)
            bao(f"Veo câu {y['cau']}: xong ({r.get('diem')} điểm, hồ sơ {r.get('ho_so')})")
            return f
        for y, f in zip(thieu, flow_video.chay_theo_tai_khoan(thieu, tao, can=can, bao=bao)):
            if f:
                co[id(y)] = f
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
        het = min(het, bd + VEO_GIAY)
        if het - bd >= 1.0:
            ra.append({"bd": round(bd, 2), "het": round(het, 2), "file": f, "am": "tieng_dong", "cau": i})
    if cho:
        bao(f"Veo thân bài: {len(ra)}/{len(cho)} chỗ có clip" + (f", {len(khong)} chỗ vẽ ảnh AI thay" if khong else ""))
    return ra, khong
