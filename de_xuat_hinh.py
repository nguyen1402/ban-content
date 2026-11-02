# -*- coding: utf-8 -*-
"""🪄 ĐỀ XUẤT CHỖ ĐÁNG DÙNG ẢNH AI / VEO — 01/11 user: không lấp đều mọi chỗ trống, dùng AI cho khoảnh khắc footage không
quay được và các bước ngoặt. AI đọc cả bài, chấm mức quan trọng từng chỗ; máy chọn theo ngân sách, cách nhau >= CACH_GIAY.
Kết quả chỉ là ĐỀ XUẤT (de_xuat_ai.json): người dùng duyệt xong mới ghi vào danh sách 📝 (anh_ai_ke_hoach.json), bước 🎨 tạo
hình và ✨ ghép đọc danh sách đó như các chỗ đánh dấu tay."""
import os

import cho_phu
from common import doc_json, ghi_json, hoi_nhieu, log, rut_json, thu_muc_du_an

TEP = "de_xuat_ai.json"
KE_HOACH = "anh_ai_ke_hoach.json"
# 02/11 user: bỏ số cố định 8 Veo / 15 ảnh. Veo tối đa = số clip điểm Flow còn tạo được, ảnh chỉ ở chỗ thật cần.
# 0 / None = tự tính (giữ hai tên này cho máy chủ đang chạy bản cũ của endpoint).
SO_VEO = 0
SO_ANH = 0
CACH_GIAY = 20.0           # 01/11 user: hình AI thưa, hai chỗ cách nhau ít nhất bấy nhiêu giây
HE_SO_UNG_VIEN = 2         # xin AI gấp mấy lần trần Veo để còn chỗ giãn cách
MUC_CAN = 4                # mức quan trọng tối thiểu của chỗ đề xuất
TRONG_CAN = 3.0            # chỗ trống footage từ bấy nhiêu giây mà footage thường không quay được -> đáng có ảnh
VAI_TRO = {"khong_quay_duoc": "Không quay được", "buoc_ngoat": "Bước ngoặt", "giai_thich": "Giải thích", "doi_nhip": "Đổi nhịp"}

_P = """You plan the AI-generated visuals of a documentary video. Most of the video is REAL footage. AI visuals are rare and
must be the moments viewers remember, not filler.

STORY BIBLE (keep every subject exactly like this):
{ho_so}

Numbered narration lines below; "[Ns]" is the duration, "(NO FOOTAGE Ns)" means real footage is missing there.

Only pick moments that truly need AI. Fewer is better than filler; an empty list is fine.
- "veo" (8-second video): action nobody could film, or the turning points of the story. {veo}
- "anh" (still image): a detail that must be seen clearly, an explanation of how something works, or a NO FOOTAGE gap
  that real footage cannot show. No fixed number: only where it is really needed.
Priorities, highest first:
1. "khong_quay_duoc": hypothetical scenes, inventions, unusual looks that do not exist in real footage.
2. "buoc_ngoat": turning points and surprises of the story.
3. "giai_thich": mechanisms that are hard to understand from ordinary footage.
4. "doi_nhip": a change of pace in a long stretch of ordinary footage.
Rules:
- The line must show a concrete subject doing something visible. Skip questions, opinions, transitions, statistics.
- Do not pick something ordinary footage shows easily (an animal grazing, a person walking).
- Spread the moments over the whole video. Avoid close-up faces of real named people.
- Do not pick plain scenery, a resting animal or a tired person just to fill the list; those are ordinary footage.
- "prompt_en": ONE clear shot description in English only (no Vietnamese word) of ONE action: subject, action, place, camera, light. Realistic documentary
  look, natural daylight colours, same style as real wildlife footage, no fantasy glow. For "veo" describe the movement.
- "muc": importance from 1 to 5. "ly_do": a short reason in Vietnamese, under 15 words.
- "co_footage": true if ordinary real footage (animals moving, people working, landscapes) could show this line; then
  the user would rather search more footage than use AI.
- "den_cau": last line covered, at most 2 lines after "cau".

Return ONLY a JSON array:
[{{"cau": 12, "den_cau": 12, "loai": "veo", "vai": "khong_quay_duoc", "muc": 5, "co_footage": false, "ly_do": "...", "prompt_en": "..."}}]

NARRATION:
{ds}"""


def _ho_so(out):
    """Khối chữ hồ sơ câu chuyện cho câu lệnh (bối cảnh + nhân vật + đặc điểm bắt buộc)."""
    j = (doc_json(os.path.join(out, "ho_so_truyen.json"), {}) or {}).get("ho_so") or {}
    dong = [f"- SETTING {x.get('noi_en') or x.get('noi', '')}: {x.get('mo_ta_en', '')}" for x in j.get("boi_canh") or []]
    # tên tiếng Anh: tên tiếng Việt trong hồ sơ lọt nguyên vào câu lệnh ("shot of đàn cừu")
    dong += [f"- {(x.get('khoa_en') or [x.get('ten', '')])[0]}: {x.get('mo_ta_en', '')} {x.get('bat_buoc_en', '')}".strip()
             for x in j.get("nhan_vat") or []]
    return "\n".join(dong) or "(none)"


def _khoang_trong(du_an, out):
    """[(t0, t1)] giây tuyệt đối các nhịp chưa có hình trong kế hoạch Bàn dựng."""
    cau = (doc_json(os.path.join(out, "ban_dung.json"), {}) or {}).get("cau") or {}
    ra = []
    for c in doc_json(os.path.join(out, "tu_khoa.json"), []) or []:
        for n in (cau.get(str(c.get("id"))) or {}).get("nhip") or []:
            if not n.get("kho_id"):
                a = float(c.get("bat_dau") or 0) + float(n.get("bd") or 0)
                ra.append((a, a + float(n.get("dai") or 0)))
    return ra


def _veo_con(out):
    """(số clip Veo còn được đề xuất, số clip điểm Flow còn tạo được) — trừ clip Veo đã duyệt ở 📝 mà chưa tạo.
    Không đọc được điểm thì (0, None): thà không đề xuất Veo còn hơn đề xuất quá điểm."""
    try:
        import flow_ve
        import flow_video
        import veo_canh
        can = flow_video.uoc_diem("Omni 1.1 Flash", "720p")
        con = sum(int(h["diem_con"] // can) for h in flow_ve.ds_ho_so() if not h["dang_nghi"])
        da = doc_json(os.path.join(out, KE_HOACH), {}) or {}
        cho = sum(1 for y in da.get("ds") or [] if isinstance(y, dict) and not y.get("bo") and y.get("loai") == "veo"
                  and str(y.get("veo_en") or "").strip() and not os.path.isfile(
                      os.path.join(out, "veo", veo_canh._ten(str(y["veo_en"]).strip()) + ".mp4")))   # noqa: SLF001
        return max(0, con - cho), con
    except Exception as e:                                   # noqa: BLE001
        log(f"! đề xuất AI: không đọc được điểm Flow ({str(e)[:100]}) -> không đề xuất Veo")
        return 0, None


def _chon(ung, so_veo, so_anh=None, giu=()):
    """Chọn theo mức quan trọng, ưu tiên chỗ thiếu footage; mọi chỗ cách nhau (kể cả chỗ `giu` đã đánh dấu) >= CACH_GIAY.
    so_anh None = không giới hạn (02/11: ảnh chỉ cần qua ngưỡng cần thiết)."""
    chon, dem = [], {"veo": so_veo, "anh": float("inf") if so_anh is None else so_anh}
    da = list(giu)
    for y in sorted(ung, key=lambda y: (-y["muc"], -y["trong"], y["t0"])):
        if dem[y["loai"]] > 0 and all(y["t0"] - b >= CACH_GIAY or a - y["t1"] >= CACH_GIAY for a, b in da):
            chon.append(y)
            da.append((y["t0"], y["t1"]))
            dem[y["loai"]] -= 1
    return sorted(chon, key=lambda y: y["t0"])


def lap(du_an, so_veo=None, so_anh=None, bao=None):
    """Hỏi AI, lọc, lưu de_xuat_ai.json -> {ds, ...}. KHÔNG tốn điểm Flow, không đổi danh sách 📝.
    so_veo / so_anh 0 hoặc None = tự tính: Veo theo điểm còn, ảnh không giới hạn số."""
    out = thu_muc_du_an(du_an)[1]
    veo_con, veo_diem = _veo_con(out)
    so_veo = int(so_veo) if so_veo else veo_con
    so_anh = int(so_anh) if so_anh else None
    cau = cho_phu.doc_cau(out)
    if not cau:
        raise ValueError("Chưa có kich_ban_cau.srt — mở 📝 Chỗ ảnh AI & Veo một lần để nạp câu lời")
    trong = _khoang_trong(du_an, out)
    het_hook = max((b for _, b in cho_phu.khoang_hook_co_clip(out)), default=0.0)   # 02/11: không còn hook tự tạo
    da = cho_phu.dong_bo_cau(out, cau) or {}
    giu = [(float(y.get("t0") or 0), float(y.get("t1") or 0)) for y in da.get("ds") or [] if not y.get("bo")]

    def _trong(a, b):
        return sum(max(0.0, min(b, y) - max(a, x)) for x, y in trong)

    dong = []
    for c in cau:
        if c["t0"] < het_hook:
            continue
        t = _trong(c["t0"], c["t1"])
        dong.append(f"{c['i']}. [{c['t1'] - c['t0']:.0f}s]" + (f" (NO FOOTAGE {t:.0f}s)" if t >= 1 else "") + f" {c['text']}")
    if bao:
        bao("AI đang đọc cả bài để chọn chỗ đáng đầu tư...")
    veo = (f"Budget: propose at most {so_veo * HE_SO_UNG_VIEN} veo candidates, only the strongest." if so_veo
           else 'No budget left: do NOT propose any "veo".')
    r = (hoi_nhieu([_P.format(ho_so=_ho_so(out), veo=veo, ds="\n".join(dong))],
                   timeout=300, ai="gemini") or [""])[0]
    j = rut_json(r or "")
    if not isinstance(j, list):
        raise RuntimeError("AI không trả về danh sách hợp lệ — thử lại")

    theo = {c["i"]: c for c in cau}
    ung = []
    for x in j:
        try:
            i = int(x.get("cau"))
            den = max(i, min(int(x.get("den_cau") or i), i + 2))
            muc = max(1, min(int(x.get("muc") or 1), 5))
        except (AttributeError, TypeError, ValueError):
            continue
        p = str(x.get("prompt_en") or "").strip()
        loai = "veo" if x.get("loai") == "veo" else "anh"
        if i not in theo or not p or theo[i]["t0"] < het_hook:
            continue
        while den > i and (den not in theo or theo[den]["t1"] - theo[i]["t0"] > (cho_phu.VEO_GIAY + 1 if loai == "veo" else cho_phu.ANH_TOI_DA)):
            den -= 1
        a, b = theo[i]["t0"], theo[den]["t1"]
        ung.append({"cau": i, "den_cau": den, "t0": a, "t1": b, "text": " ".join(theo[k]["text"] for k in range(i, den + 1) if k in theo),
                    "loai": loai, "vai": x.get("vai") if x.get("vai") in VAI_TRO else "buoc_ngoat", "muc": muc,
                    "ly_do": str(x.get("ly_do") or "")[:120], "prompt_en": p, "trong": round(_trong(a, b), 1),
                    "co_footage": x.get("co_footage") is True})
    # 02/11 user: chỉ chỗ thật cần. Chỗ trống mà footage thường quay được -> báo tìm thêm nguồn thay vì vẽ.
    can = [y for y in ung if (y["muc"] >= MUC_CAN if y["loai"] == "veo"
                              else not y["co_footage"] and (y["muc"] >= MUC_CAN or y["trong"] >= TRONG_CAN))]
    tim = sorted({(y["cau"], y["text"]) for y in ung if y["co_footage"] and y["trong"] >= TRONG_CAN})
    ds = _chon(can, so_veo, so_anh, giu)
    ket = {"ds": ds, "so_ung_vien": len(ung), "so_veo": so_veo, "veo_diem": veo_diem,
           "tim_nguon": [{"cau": i, "text": t} for i, t in tim]}
    ghi_json(os.path.join(out, TEP), ket)
    log(f"[đề xuất AI] {len(ds)} chỗ từ {len(ung)} ứng viên (Veo tối đa {so_veo}), {len(tim)} chỗ nên tìm thêm footage")
    return ket


def doc(du_an):
    return doc_json(os.path.join(thu_muc_du_an(du_an)[1], TEP), {}) or {}


def duyet(du_an, ds):
    """Ghi các chỗ người dùng đã duyệt vào danh sách 📝 (giữ nguyên chỗ cũ, câu đã có chỗ thì không thêm) -> số chỗ thêm."""
    out = thu_muc_du_an(du_an)[1]
    p = os.path.join(out, KE_HOACH)
    da = doc_json(p, {}) or {}
    cu = [y for y in da.get("ds") or [] if isinstance(y, dict)]
    co = {int(y.get("cau") or 0) for y in cu}
    them = 0
    for y in ds or []:
        i = int(y.get("cau") or 0)
        prompt = str(y.get("prompt_en") or "").strip()
        if not i or i in co or not prompt:
            continue
        z = {"cau": i, "den_cau": max(i, int(y.get("den_cau") or i)), "t0": y.get("t0"), "t1": y.get("t1"), "tay": True,
             "loai": "veo" if y.get("loai") == "veo" else "anh", "tieu_de": VAI_TRO.get(y.get("vai"), "")}
        z["veo_en" if z["loai"] == "veo" else "ve_1"] = prompt
        cu.append(z)
        co.add(i)
        them += 1
    ghi_json(p, dict(da, ds=sorted(cu, key=lambda z: int(z.get("cau") or 0)), duyet=True))
    cho_phu.dong_bo_cau(out, cho_phu.doc_cau(out))
    return them
