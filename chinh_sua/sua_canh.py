# -*- coding: utf-8 -*-
"""🎞 DUYỆT + SỬA TỪNG CẢNH REMOTION AI (04/11 user: "giao diện liệt kê toàn bộ video dựng remotion, tôi xem và đánh giá theo
ý mình, mỗi lần gửi đánh giá thì AI sửa theo góp ý đó; cho phép tôi tự sửa tay — giao diện sửa tay (Studio) khó dùng quá;
mỗi khi AI sửa hoặc tôi tự sửa bấm lưu thì chỉ cảnh đó ghi đè lại bản nháp, không được làm lại bản nháp").

  - danh_gia(): 👍 / 👎 + góp ý lưu vào bản ghi cảnh (nhan_y_ai.json).
  - phan_tu() / ap_phan_tu(): đọc / sửa giờ hiện, độ dài, vị trí của từng <Interactive.Div name=…> (và <Img name=…>) trong
    code cảnh — số literal, đúng chỗ Studio vẫn sửa — để trang duyệt có ô số thay cho kéo thả trong Studio.
  - xem_khung(): dựng MỘT khung với thông số đang sửa (chưa lưu) để xem trước.
  - luu_tay() / gop_y(): lưu -> dựng lại video cảnh -> ghep_mot().
  - ghep_mot(): thay ĐÚNG đoạn của cảnh này (video track nhan_y + tiếng của nó ở nhan_y_sfx) trong bản nháp _hoan_chinh;
    đoạn khác, track khác, phần user sửa tay trong CapCut giữ nguyên."""
import glob
import json
import os
import re
import time

import nhan_y
import nhan_y_ai as ai
from common import CACHE_CHUNG, doc_json, log, thu_muc_du_an

FPS = 30


def _ban_ghi(du_an, cau):
    v = (doc_json(ai._ds(du_an), {}) or {}).get(str(cau))               # noqa: SLF001
    if not v or not v.get("ma"):
        raise ValueError(f"chưa có cảnh câu {cau}")
    return v


def _code(v):
    return open(os.path.join(ai.THU_AI, f"{v['ma']}.jsx"), encoding="utf-8").read()


# --- đánh giá -----------------------------------------------------------------------------------------------------------
def danh_gia(du_an, cau, thich=None, y_kien=""):
    """thich: True 👍 / False 👎 / None bỏ đánh giá. Ghi cả lịch sử góp ý."""
    v = _ban_ghi(du_an, cau)
    dg = dict(v.get("danh_gia") or {})
    dg.update(thich=thich, luc=time.time())
    if y_kien:
        dg["lich_su"] = (dg.get("lich_su") or []) + [{"y_kien": y_kien, "luc": time.time()}]
    ai._ghi_ds(du_an, {str(cau): dict(v, danh_gia=dg)})                   # noqa: SLF001
    return dg


# --- phần tử trong code -------------------------------------------------------------------------------------------------
_THE = re.compile(r"<(Interactive\.Div|Img)\b")


def _cac_the(code):
    """[(đầu, cuối, tên thẻ)] của mọi thẻ mở <Interactive.Div …> / <Img …> — quét ngoặc để không cắt ở '>' trong {…}."""
    ra = []
    for m in _THE.finditer(code):
        sau, i, sau_ngoac = m.start(), m.end(), 0
        while i < len(code):
            ch = code[i]
            if ch in "{":
                sau_ngoac += 1
            elif ch == "}":
                sau_ngoac -= 1
            elif ch == ">" and sau_ngoac == 0:
                ra.append((sau, i + 1, m.group(1)))
                break
            i += 1
    return ra


def _so(the, ten):
    m = re.search(r"\b" + ten + r"\s*=\s*\{\s*(-?\d+(?:\.\d+)?)\s*\}", the)
    return float(m.group(1)) if m else None


def _so_style(the, ten):
    m = re.search(r"\b" + ten + r"\s*:\s*(-?\d+(?:\.\d+)?)\b", the)
    return float(m.group(1)) if m else None


def phan_tu(code):
    """-> [{i, the, ten, tu (giây), dai (giây), trai, tren}] — chỉ thẻ có name=; None = code không ghi số literal."""
    ra = []
    for k, (a, b, loai) in enumerate(_cac_the(code)):
        the = code[a:b]
        m = re.search(r"\bname\s*=\s*[\"'{]+([^\"'}]+)", the)
        if not m:
            continue
        tu, dai = _so(the, "from"), _so(the, "durationInFrames")
        ra.append({"i": k, "the": loai, "ten": m.group(1).strip(), "tu": round(tu / FPS, 2) if tu is not None else None,
                   "dai": round(dai / FPS, 2) if dai is not None else None,
                   "trai": _so_style(the, "left"), "tren": _so_style(the, "top")})
    return ra


def ap_phan_tu(code, ds):
    """Ghi lại giờ / vị trí user sửa vào đúng thẻ (theo số thứ tự i). Chỉ thay số literal đã có."""
    the = _cac_the(code)
    moi = {int(x["i"]): x for x in ds or [] if str(x.get("i", "")).lstrip("-").isdigit()}
    for k in sorted(moi, reverse=True):                                 # từ cuối lên: vị trí phía trước không xê dịch
        if k >= len(the):
            continue
        a, b, _ = the[k]
        t, x = code[a:b], moi[k]

        def dat(t, ten, gia, style=False):
            if gia is None or gia == "":
                return t
            gia = float(gia)
            s = str(int(round(gia))) if style or ten in ("from", "durationInFrames") else f"{gia:g}"
            if style:
                return re.sub(r"(\b" + ten + r"\s*:\s*)-?\d+(?:\.\d+)?\b", lambda m: m.group(1) + s, t, count=1)
            return re.sub(r"(\b" + ten + r"\s*=\s*\{\s*)-?\d+(?:\.\d+)?(\s*\})", lambda m: m.group(1) + s + m.group(2), t, count=1)
        if x.get("tu") not in (None, ""):
            t = dat(t, "from", float(x["tu"]) * FPS)
        if x.get("dai") not in (None, ""):
            t = dat(t, "durationInFrames", max(1.0, float(x["dai"]) * FPS))
        t = dat(t, "left", x.get("trai"), True)
        t = dat(t, "top", x.get("tren"), True)
        code = code[:a] + t + code[b:]
    return code


def thong_tin(du_an, cau):
    """Mọi thứ trang sửa tay cần: thông số (props + nhãn), phần tử, ảnh của cảnh, thời lượng."""
    v = _ban_ghi(du_an, cau)
    code = _code(v)
    nhan = dict(re.findall(r"(\w+)\s*:\s*z\.[^\n]*?\.describe\(\s*['\"`]([^'\"`]+)['\"`]", code))
    anh = [{"ten": a.get("ten"), "loai": a.get("loai"), "file": a.get("file")} for a in v.get("anh") or []]
    return {"cau": v["cau"], "text": v.get("text", ""), "giay": v["giay"], "props": ai._props_hien(v), "nhan": nhan,   # noqa: SLF001
            "phan_tu": phan_tu(code), "anh": anh, "danh_gia": v.get("danh_gia") or {}}


# --- xem trước một khung ------------------------------------------------------------------------------------------------
def xem_khung(du_an, cau, giay_xem, props=None, ds_pt=None):
    """Dựng 1 khung tại giay_xem với thông số đang sửa (chưa lưu) -> đường png | ValueError(lỗi)."""
    v = _ban_ghi(du_an, cau)
    code = ap_phan_tu(_code(v), ds_pt) if ds_pt else _code(v)
    mod = f"{v['ma']}__xem.jsx"
    with open(os.path.join(ai.THU_AI, mod), "w", encoding="utf-8", newline="\n") as f:
        f.write(code)
    pr = ai._props_hien(v) | (props or {})                              # noqa: SLF001
    k = max(0, min(round(float(giay_xem) * FPS), round(v["giay"] * FPS) - 1))
    thu = os.path.join(CACHE_CHUNG, "nhan_y", "xem")
    try:
        loi, anh = ai._thu_dung(v["ma"] + "__xem", pr, v["giay"], [k], mod=mod, thu=thu)   # noqa: SLF001
    finally:
        for f in (os.path.join(ai.THU_AI, mod), os.path.join(ai.THU_AI, f"_thu_{v['ma']}__xem.jsx")):
            if os.path.isfile(f):
                os.remove(f)
    if not anh:
        f = os.path.join(thu, f"{v['ma']}__xem_{k}.png")                  # bộ đo khung trống vẫn trả ảnh: cho xem
        if os.path.isfile(f):
            return f
        raise ValueError((loi or "không dựng được khung")[:400])
    return anh[0]


# --- lưu: dựng lại cảnh + ghép đúng cảnh đó ------------------------------------------------------------------------------
def _dung_lai(du_an, v, pr, bao):
    ai._giong(du_an, v | {"giay": v["giay"]})                            # noqa: SLF001
    ai._dang_ky({v["ma"]: pr})                                           # noqa: SLF001
    mp4 = ai._render(v["ma"], pr, v["giay"])                             # noqa: SLF001
    if not mp4:
        raise ValueError("dựng video hỏng — xem lại thông số / code")
    v.update(mp4=mp4, trang_thai="xong", props=pr, ai_code="deepseek" if ai.CODE_CHI_DEEPSEEK else v.get("ai_code"))
    ai._ghi_ds(du_an, {str(v["cau"]): v})                                # noqa: SLF001
    return {"mp4": mp4, "nhap": ghep_mot(du_an, v["cau"], bao)}


def luu_tay(du_an, cau, props=None, ds_pt=None, bao=None):
    """✏️ Lưu sửa tay: ghi code (giờ / vị trí) + thông số -> kiểm khung -> dựng lại -> ghép đúng cảnh này."""
    bao = bao or (lambda m: log("  " + m))
    v = _ban_ghi(du_an, cau)
    f = os.path.join(ai.THU_AI, f"{v['ma']}.jsx")
    cu = _code(v)
    code = ap_phan_tu(cu, ds_pt) if ds_pt else cu
    pr = ai._props_hien(v) | (props or {})                              # noqa: SLF001
    pr["giay"] = v["giay"]
    # sửa tay: không dựng thử 6 khung (≈2 phút, user đã xem khung bằng 👁) — dựng thẳng, hỏng thì trả code cũ
    with open(f, "w", encoding="utf-8", newline="\n") as g:
        g.write(code)
    v.update(sua_tay=True)
    bao(f"câu {cau}: dựng lại video…")
    try:
        return _dung_lai(du_an, v, pr, bao)
    except Exception:
        with open(f, "w", encoding="utf-8", newline="\n") as g:
            g.write(cu)
        raise


def gop_y(du_an, cau, y_kien, bao=None):
    """💬 Góp ý -> AI sửa code theo đúng ý đó -> dựng lại -> ghép đúng cảnh này. Lưu góp ý vào lịch sử đánh giá."""
    bao = bao or (lambda m: log("  " + m))
    danh_gia(du_an, cau, False, y_kien)
    v = _ban_ghi(du_an, cau)
    f = os.path.join(ai.THU_AI, f"{v['ma']}.jsx")
    cu = _code(v)
    pr0 = ai._props_hien(v)                                              # noqa: SLF001
    anh = "\n".join(f"  - {a['ten']} ({a['loai']}): '{a['file']}'" for a in v.get("anh") or [])
    yk = y_kien + (f"\n(Ảnh có sẵn dùng được, đúng đường dẫn: \n{anh})" if anh else "")
    bao(f"câu {cau}: AI sửa theo góp ý…")
    code, pr = ai._viet_code(v["ma"], ai._HOI_GOP_Y.format(y_kien=yk, code=cu, props=json.dumps(pr0, ensure_ascii=False)),   # noqa: SLF001
                             pr0, v["giay"], lambda m: bao(f"câu {cau}: {m}"))
    if code is None:
        with open(f, "w", encoding="utf-8", newline="\n") as g:
            g.write(cu)
        raise ValueError(f"AI sửa không chạy được: {str(pr)[:200]}")
    pr["giay"] = v["giay"]
    v.update(props=pr)
    bao(f"câu {cau}: dựng lại video…")
    return _dung_lai(du_an, v, pr, bao)


def lam_lai(du_an, cau, bao=None):
    """🗑 (05/11 user: "xoá toàn bộ cảnh remotion làm lại"): bỏ thiết kế, ảnh, code, chỉnh tay của cảnh này, thiết kế + vẽ +
    viết + dựng lại từ đầu (dựng nhanh, không tự sửa) rồi thay ĐÚNG cảnh này trong bản nháp. Lượt mới hỏng thì giữ cảnh cũ."""
    bao = bao or (lambda m: log("  " + m))
    _ban_ghi(du_an, cau)                                                 # chưa có cảnh -> báo lỗi
    r = ai.dung(du_an, chi=[int(cau)], bao=bao, lam_lai=True, tu_sua=False, song_song=1, ghep_cuoi=False)
    v = _ban_ghi(du_an, cau)
    if v.get("cho_anh"):
        raise ValueError("Flow chưa vẽ đủ ảnh — cảnh mới đã vào hàng chờ (giữ thiết kế + ảnh đã vẽ), bản nháp giữ cảnh cũ. "
                         "Bấm lại sau khi Flow hết nghỉ: chỉ vẽ bù ảnh còn thiếu rồi dựng")
    if v.get("loi_moi") or not r.get("xong") or not os.path.isfile(v.get("mp4") or ""):
        raise ValueError("dựng lại không thành — vẫn giữ cảnh cũ" + (f": {str(v.get('loi_moi'))[:200]}" if v.get("loi_moi") else ""))
    return {"mp4": v["mp4"], "nhap": ghep_mot(du_an, cau, bao)}


def _cat_chong(d):
    """Track nhấn ý: đoạn nào lấn sang đoạn sau (lệch làm tròn vài khung khi thay cảnh) -> cắt cho khít. -> số đoạn cắt."""
    n = 0
    for t in d["tracks"]:
        if t.get("name") not in ("nhan_y", "nhan_y_sfx"):
            continue
        seg = sorted(t["segments"], key=lambda s: s["target_timerange"]["start"])
        for a, b in zip(seg, seg[1:]):
            A, B = a["target_timerange"], b["target_timerange"]
            if A["start"] + A["duration"] > B["start"]:
                moi = max(33_334, B["start"] - A["start"])
                for k in ("source_timerange", "render_timerange"):
                    if (a.get(k) or {}).get("duration"):
                        a[k]["duration"] = min(a[k]["duration"], int(moi * float(a.get("speed") or 1.0)))
                A["duration"] = moi
                n += 1
        t["segments"] = seg
    return n


def ghep_mot(du_an, cau, bao=None):
    """Thay đúng cảnh `cau` trong bản nháp _hoan_chinh: bỏ đoạn video cũ của nó (track nhan_y, cùng giờ bắt đầu) + tiếng SFX
    trong khoảng của nó (nhan_y_sfx), thêm video mới + SFX mới. Track nhấn ý chưa có thì ghép cả lượt (ai.ghep)."""
    import pycapcut as draft
    from pycapcut import trange
    import dung_tay
    bao = bao or (lambda m: log("  " + m))
    p = ai.ban_nhap_dich(du_an)
    if not p:
        bao("chưa có bản nháp _hoan_chinh — chưa ghép")
        return None
    v = _ban_ghi(du_an, cau)
    f = os.path.join(p, "draft_content.json")
    d = nhan_y._doc(f)                                                   # noqa: SLF001
    tv = next((t for t in d["tracks"] if t.get("name") == "nhan_y"), None)
    if not tv:
        return ai.ghep(du_an, bao)
    ts = next((t for t in d["tracks"] if t.get("name") == "nhan_y_sfx"), None)
    US = 1_000_000
    a0, g = int(round(v["t0"] * US)), int(round(v["giay"] * US))
    mv = {m["id"]: m.get("path") for m in d["materials"].get("videos", [])}
    thu_ai = os.path.normcase(os.path.join(CACHE_CHUNG, "nhan_y", "ai"))
    cu = [s for s in tv["segments"] if abs(s["target_timerange"]["start"] - a0) < 60_000
          and os.path.normcase(os.path.dirname(mv.get(s["material_id"]) or "")) == thu_ai]
    het = max([a0 + g] + [s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in cu])
    tv["segments"] = [s for s in tv["segments"] if s not in cu]
    if ts:
        ts["segments"] = [s for s in ts["segments"] if not (a0 - 300_000 <= s["target_timerange"]["start"] < het)]
    # đoạn mới (pycapcut dựng vật liệu) — SFX đặt như ai.ghep
    sc = draft.ScriptFile(1920, 1080)
    sc.add_track(draft.TrackType.video, track_name="nhan_y")
    sc.add_track(draft.TrackType.audio, track_name="nhan_y_sfx")
    m = draft.VideoMaterial(v["mp4"])
    sau = min([s["target_timerange"]["start"] for s in tv["segments"] if s["target_timerange"]["start"] > a0 + 10_000] + [10 ** 13])
    dai = min(v["giay"], m.duration / US, max(0.5, (sau - a0) / US))     # không lấn sang cảnh sau (như ai.ghep)
    sc.add_segment(draft.VideoSegment(m, trange(f"{v['t0']:.3f}s", f"{dai:.3f}s"), volume=0.0), "nhan_y")
    gd_f = os.path.join(thu_muc_du_an(du_an)[1], "giong_doc.wav")
    gd = nhan_y._ebur(gd_f)[0] if os.path.isfile(gd_f) else -18.0       # noqa: SLF001
    sfx, lan = [], {}
    for q in (v.get("sfx") or [])[:5]:
        x = nhan_y._sfx(q.get("loai"), lan.get(q.get("loai"), 0))        # noqa: SLF001
        lan[q.get("loai")] = lan.get(q.get("loai"), 0) + 1
        if x:
            vol = nhan_y._am_luong(x[0], gd, bool(q.get("chot")))        # noqa: SLF001
            if vol < 4.0:
                sfx.append((max(0.0, v["t0"] + float(q.get("t") or 0) - x[1]), x[0], vol))
    sfx.sort()
    for j, (t, fa, vol) in enumerate(sfx):
        if j and t - sfx[j - 1][0] < 0.1:
            continue
        ma = draft.AudioMaterial(fa)
        a = int(round(t * US))
        sau = int(round(sfx[j + 1][0] * US)) if j + 1 < len(sfx) else a0 + g
        dai = min(int(ma.duration), 3_000_000, max(50_000, sau - a))
        sc.add_segment(draft.AudioSegment(ma, draft.Timerange(a, dai), volume=vol), "nhan_y_sfx")
    moi = json.loads(sc.dumps())
    for kk, ds_ in moi["materials"].items():
        if isinstance(ds_, list) and ds_:
            co = {x.get("id") for x in d["materials"].setdefault(kk, [])}
            d["materials"][kk] += [x for x in ds_ if x.get("id") not in co]
    for t_moi in moi["tracks"]:
        dich = tv if t_moi.get("name") == "nhan_y" else ts
        if dich is None and t_moi["segments"]:                           # chưa có track tiếng nhấn ý: thêm track
            dich = dict(t_moi, segments=[])
            d["tracks"].append(dich)
        if dich is None:
            continue
        ri = max([s.get("render_index", 0) for s in dich["segments"]] + [0]) or \
            max([s.get("render_index", 0) for t in d["tracks"] for s in t["segments"]] + [0]) + 1
        for s in t_moi["segments"]:
            s["render_index"] = ri
            dich["segments"].append(s)
        dich["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    _cat_chong(d)
    for gg in [f] + glob.glob(os.path.join(p, "Timelines", "*", "draft_content.json")):
        nhan_y._ghi(gg, d)                                               # noqa: SLF001
        if os.path.isfile(gg + ".bak"):
            os.remove(gg + ".bak")
    dung_tay._sua_nhap(p, [v["mp4"]])                                     # noqa: SLF001
    bao(f"câu {cau}: đã thay đúng cảnh này trong bản nháp '{os.path.basename(p)}' (bỏ {len(cu)} đoạn cũ)"
        + (" — ⚠ CapCut ĐANG MỞ: đóng hẳn CapCut rồi mở lại bản nháp" if ai.capcut_dang_mo() else " — mở lại bản nháp trong CapCut"))
    return os.path.basename(p)


def sua_lop(du_an, chi=None, bao=None, song_song=6):
    """05/11 user ("hết câu rồi vẫn dùng lại ảnh nền cũ, hiệu ứng zoom lại"): cảnh đã dựng vi phạm luật lớp ảnh
    (ai._kiem_lop: gắn lại cùng ảnh ở khối sau / ảnh cuối hết sớm) -> AI sửa code đúng lỗi đó (giữ thiết kế + ảnh, không vẽ
    lại), dựng lại video MỘT lượt, rồi thay từng cảnh trong bản nháp (ghep_mot). Sửa hỏng thì giữ cảnh cũ. -> {sua, xong, nhap}"""
    from concurrent.futures import ThreadPoolExecutor
    bao = bao or (lambda m: log("  " + m))
    ds = doc_json(ai._ds(du_an), {}) or {}                              # noqa: SLF001
    loi = {}
    for k, v in ds.items():
        if v.get("trang_thai") == "xong" and v.get("ma") and (not chi or int(k) in chi):
            f = os.path.join(ai.THU_AI, f"{v['ma']}.jsx")
            if os.path.isfile(f):
                e = ai._kiem_lop(open(f, encoding="utf-8").read(), v["giay"])   # noqa: SLF001
                if e:
                    loi[k] = e
    cau = sorted(int(k) for k in loi)
    if not cau:
        return {"sua": 0, "xong": 0, "nhap": None}
    td = ai.TienDo(du_an, cau, "🧩 sửa lớp ảnh (ảnh cũ quay lại / zoom chạy lại)", song_song)
    bao = td.bao_qua(bao)
    duoc = {}

    def mot(k):
        v = dict(ds[k])
        f = os.path.join(ai.THU_AI, f"{v['ma']}.jsx")
        cu = open(f, encoding="utf-8").read()
        pr0 = ai._props_hien(v)                                          # noqa: SLF001
        anh = "\n".join(f"  - {a['ten']} ({a['loai']}): '{a['file']}'" for a in v.get("anh") or [])
        nc = {"cau": v.get("text", ""), "mo_ta": (v.get("thiet_ke") or {}).get("mo_ta", ""), "anh": anh, "tu_sua": False}
        hoi = ai._HOI_SUA.format(loi=loi[k], code=cu) + (f"\nImages you may use — ONLY these, with src('<path>') exactly as "
                                                          f"written; NEVER any http(s) URL:\n{anh}" if anh else "")
        bao(f"câu {k}: AI sửa lớp ảnh…")
        try:
            code, pr = ai._viet_code(v["ma"], hoi, pr0, v["giay"], lambda m: bao(f"câu {k}: {m}"), nc)   # noqa: SLF001
        except Exception as e:                                           # noqa: BLE001
            code, pr = None, str(e)
        if code is None:
            with open(f, "w", encoding="utf-8", newline="\n") as g:
                g.write(cu)                                             # sửa hỏng: trả code cũ, giữ video cũ
            td.loi(int(k), f"sửa không được — giữ cảnh cũ ({str(pr)[:120]})")
            return
        pr["giay"] = v["giay"]
        v.update(props=pr)
        duoc[k] = v
        td.xong(int(k), "đã sửa code")

    with ThreadPoolExecutor(song_song) as ex:
        list(ex.map(mot, [str(c) for c in cau]))
    if not duoc:
        td.het("không cảnh nào sửa được")
        return {"sua": len(cau), "xong": 0, "nhap": None}
    for v in duoc.values():
        ai._giong(du_an, v)                                              # noqa: SLF001
    ai._dang_ky({v["ma"]: v["props"] for v in duoc.values()})            # noqa: SLF001
    td.buoc(f"dựng video {len(duoc)} cảnh")
    mp4 = ai._render_nhieu([(v["ma"], ai._props_hien(v), v["giay"]) for v in duoc.values()])   # noqa: SLF001
    xong = {k: dict(v, mp4=mp4[v["ma"]], trang_thai="xong") for k, v in duoc.items() if mp4.get(v["ma"])}
    ai._ghi_ds(du_an, xong)                                              # noqa: SLF001
    td.buoc("thay từng cảnh trong bản nháp")
    nhap = None
    for k in sorted(xong, key=int):
        nhap = ghep_mot(du_an, int(k), bao) or nhap
    td.het(f"sửa {len(xong)}/{len(cau)} cảnh" + (f" — đã thay trong '{nhap}'" if nhap else ""))
    return {"sua": len(cau), "xong": len(xong), "nhap": nhap}


# --- 🎚 sửa lớp kiểu CapCut (05/11 user: "xem lớp thằng nào xuất hiện trước, sau, trên dưới, phóng to thu nhỏ hay xoá
# bỏ… giống cách xếp lớp trong CapCut; chỉnh phải mượt, phát lại không vấp") ---------------------------------------------
def _style_cua(the):
    """Khối style={{…}} trong thẻ -> (đầu, cuối) của phần bên trong {{ }} | None."""
    m = re.search(r"\bstyle\s*=\s*\{\{", the)
    if not m:
        return None
    i, sau = m.end(), 2
    while i < len(the) and sau:
        sau += {"{": 1, "}": -1}.get(the[i], 0)
        i += 1
    return (m.end(), i - 2) if not sau else None


def _doc_style(the, ten):
    k = _style_cua(the)
    if not k:
        return None
    m = re.search(r"\b" + ten + r"\s*:\s*(['\"]?)(-?[\w.]+)\1", the[k[0]:k[1]])
    return m.group(2) if m else None


def _dat_style(the, ten, gia):
    """Đặt / thay khoá ten trong style={{…}} của thẻ (gia None = bỏ khoá). Không có style literal thì thêm style mới."""
    k = _style_cua(the)
    gia_s = None if gia is None else (repr(gia) if isinstance(gia, str) else f"{gia:g}")
    if not k:
        if gia_s is None:
            return the
        j = the.rstrip().rstrip("/").rstrip(">").rstrip()
        return the[:len(j)] + f" style={{{{{ten}: {gia_s}}}}}" + the[len(j):]
    trong = the[k[0]:k[1]]
    bo = re.sub(r"\s*,?\s*\b" + ten + r"\s*:\s*(['\"][^'\"]*['\"]|-?[\w.]+)\s*", " ", trong, count=1)
    if gia_s is not None:
        bo = f"{ten}: {gia_s}, " + bo.strip().lstrip(",").strip()
    bo = re.sub(r",\s*,", ",", bo).strip().rstrip(",")
    return the[:k[0]] + bo + the[k[1]:]


_DK_TRUOC = re.compile(r"\{\s*(?:[\w.]*frame[\w.]*\s*[<>]=?\s*[\w.]+|[\w.]+\s*[<>]=?\s*[\w.]*frame[\w.]*)"
                       r"(?:\s*&&\s*(?:[\w.]*frame[\w.]*\s*[<>]=?\s*[\w.]+|[\w.]+\s*[<>]=?\s*[\w.]*frame[\w.]*))*\s*&&\s*\(?\s*$")


def bo_dieu_kien(code):
    """05/11 (lopxe câu 18: kéo dài lớp chữ mà không hiện thêm): AI hay bọc lớp trong {frame >= A && frame <= B && (…)} —
    thừa (Interactive.Div from / durationInFrames đã lo) và chặn việc chỉnh giờ -> gỡ điều kiện, giữ nguyên lớp."""
    for a, b, _, _ in sorted(ai._khoi_div(code), key=lambda k: -k[0]):  # noqa: SLF001  (từ cuối lên)
        m = _DK_TRUOC.search(code[max(0, a - 200):a])
        n = re.match(r"\s*\)?\s*\}", code[b:b + 20])
        if m and n:
            dau = max(0, a - 200) + m.start()
            code = code[:dau] + code[a:b] + code[b + n.end():]
    return code


def lop(du_an, cau):
    """Lớp của cảnh cho trang 🎚: phan_tu + cỡ / độ mờ / thứ tự lớp / ẩn đang ghi trong code."""
    v = _ban_ghi(du_an, cau)
    code = _code(v)
    the = _cac_the(code)
    ra = []
    for p in phan_tu(code):
        t = code[the[p["i"]][0]:the[p["i"]][1]]
        co, mo, z = _doc_style(t, "scale"), _doc_style(t, "opacity"), _doc_style(t, "zIndex")
        an = _doc_style(t, "display") == "none"

        def so(x, mac):
            try:
                return float(x)
            except (TypeError, ValueError):
                return mac
        ra.append(p | {"co": so(co, 1.0), "mo": so(mo, 1.0), "z": so(z, None), "an": an})
    return ra


def ap_lop(code, ds):
    """Ghi lớp user chỉnh (i, tu, dai, trai, tren, co, mo, z, an / xoa) vào đúng thẻ trong code."""
    code = ap_phan_tu(bo_dieu_kien(code), ds)                           # giờ + vị trí (số literal đã có)
    the = _cac_the(code)
    for x in sorted(ds or [], key=lambda x: -int(x.get("i", -1))):
        k = int(x.get("i", -1))
        if not 0 <= k < len(the):
            continue
        a, b, _ = the[k]
        t = code[a:b]
        if x.get("trai") is not None and _so_style(t, "left") is None:
            t = _dat_style(t, "left", float(x["trai"]))
        if x.get("tren") is not None and _so_style(t, "top") is None:
            t = _dat_style(t, "top", float(x["tren"]))
        if "co" in x:
            t = _dat_style(t, "scale", None if float(x["co"] or 1) == 1 else float(x["co"]))
        if "mo" in x:
            t = _dat_style(t, "opacity", None if float(x["mo"] if x["mo"] is not None else 1) >= 1 else float(x["mo"]))
        if x.get("z") is not None:
            t = _dat_style(t, "zIndex", int(x["z"]))
        if "an" in x or "xoa" in x:
            t = _dat_style(t, "display", "none" if (x.get("an") or x.get("xoa")) else None)
        code = code[:a] + t + code[b:]
    return code


def luu_lop(du_an, cau, ds, bao=None):
    """🎚 Lưu: ghi lớp vào code -> dựng lại video -> thay đúng cảnh trong bản nháp. Dựng hỏng thì trả code cũ."""
    bao = bao or (lambda m: log("  " + m))
    v = _ban_ghi(du_an, cau)
    f = os.path.join(ai.THU_AI, f"{v['ma']}.jsx")
    cu = _code(v)
    # 05/11: chữ + hiệu ứng ghi TRƯỚC (vị trí chữ tính trên code gốc), rồi giờ / vị trí / cỡ / lớp
    moi, pr = ap_chu_hieu(cu, ds, ai._props_hien(v))                     # noqa: SLF001
    with open(f, "w", encoding="utf-8", newline="\n") as g:
        g.write(ap_lop(moi, ds))
    v.update(sua_tay=True)
    pr = pr | {"giay": v["giay"]}
    bao(f"câu {cau}: dựng lại video…")
    try:
        return _dung_lai(du_an, v, pr, bao)
    except Exception:
        with open(f, "w", encoding="utf-8", newline="\n") as g:
            g.write(cu)
        raise


def goi_js(du_an, cau):
    """Đóng gói cảnh + Remotion Player cho trang 🎚 (cache theo nội dung code) -> đường tệp .js | ValueError."""
    import hashlib
    import subprocess
    v = _ban_ghi(du_an, cau)
    goc = os.path.join(ai.THU_AI, f"{v['ma']}.jsx")
    f = os.path.join(ai.THU_AI, f"_sua_{v['ma']}.jsx")                    # bản xem: đã gỡ điều kiện thời gian thừa
    with open(f, "w", encoding="utf-8", newline="\n") as g:
        g.write(bo_hieu_ung(bo_dieu_kien(open(goc, encoding="utf-8").read())))   # hiệu ứng đã lưu: trình sửa tự áp lại
    tv = os.path.join(ai.THU_AI, "thu_vien.jsx")
    them = [tv, os.path.join(ai.REMOTION, "sua_lop_shim.jsx"), os.path.join(ai.THU_AI, "hieu_ung_tinh.js")]
    h = hashlib.md5((open(f, encoding="utf-8").read() + "".join(open(x, encoding="utf-8").read() for x in them))
                    .encode("utf-8")).hexdigest()[:14]
    thu = os.path.join(CACHE_CHUNG, "sua_lop")
    os.makedirs(thu, exist_ok=True)
    ra = os.path.join(thu, f"{v['ma']}_{h}.js")
    if not os.path.isfile(ra):
        ai._giong(du_an, v)                                              # noqa: SLF001  (giọng đọc của cảnh để nghe khi sửa)
        r = subprocess.run(["node", "sua_lop_dong_goi.mjs", f, ra, f"{nhan_y.THU_PUB}/giong_{v['ma']}.wav"], cwd=ai.REMOTION,
                           capture_output=True, timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
        if not os.path.isfile(ra):
            raise ValueError(((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "ignore")[-1500:] or "đóng gói hỏng")
    return ra


# --- dọn dung lượng ---------------------------------------------------------------------------------------------------------
# 05/11 user: "xoá toàn bộ tất cả các cảnh remotion … để đỡ nặng máy khi tôi làm xong".
# Bản nháp CapCut trỏ THẲNG vào video cảnh (cache/nhan_y/ai/*.mp4) -> chia hai mức:
#   don (an toàn, lúc nào cũng được): chỉ bỏ thứ không bản nháp / dự án nào dùng — khung dựng thử, ảnh chấm Antigravity,
#       video cảnh cũ đã bị thay, ảnh Remotion không còn cảnh nào dùng, bản đóng gói của trình sửa lớp;
#   xoa_het (sau khi ĐÃ XUẤT video): thêm toàn bộ cảnh Remotion của dự án — video, code, ảnh riêng, bản ghi, tiến độ.
#       Bản nháp CapCut của dự án sẽ báo thiếu các đoạn Remotion.
MOI_DUNG = 2 * 3600            # tệp mới sửa trong 2 giờ: có thể đang dựng dở -> không động


def _mo_ai():
    return os.path.join(CACHE_CHUNG, "nhan_y", "ai")


def _ten_mp4_trong_nhap(tru=None):
    """Tên video cảnh AI mà các bản nháp CapCut đang dùng (tru: bỏ qua bản nháp có tên bắt đầu bằng dự án này)."""
    from common import thu_muc_nhap_capcut
    ra = set()
    for f in glob.glob(os.path.join(thu_muc_nhap_capcut(), "*", "draft_content.json")) + \
            glob.glob(os.path.join(thu_muc_nhap_capcut(), "*", "Timelines", "*", "draft_content.json")):
        ten = os.path.relpath(f, thu_muc_nhap_capcut()).split(os.sep)[0]
        if tru and ten.lower().startswith(tru.lower()):
            continue
        try:
            s = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        ra.update(m.lower() for m in re.findall(r"[0-9a-f]{12,20}\.mp4", s))
    return ra


def _ban_ghi_moi_du_an():
    """{dự án: {câu: bản ghi}} của mọi dự án có cảnh Remotion."""
    from common import thu_muc_du_an as _t
    ra = {}
    for f in glob.glob(os.path.join(os.path.dirname(_t("x")[1]), "*", "nhan_y_ai.json")):
        ra[os.path.basename(os.path.dirname(f))] = doc_json(f, {}) or {}
    return ra


def _anh_cua(v):
    """Đường public (nhan_y/...) mọi ảnh một bản ghi nhắc tới."""
    s = json.dumps([v.get("anh"), v.get("props"), v.get("khoa_that")], ensure_ascii=False)
    return {m.lower() for m in re.findall(r"nhan_y/[\w.\-]+\.(?:png|jpe?g|webp)", s)}


def don_remotion(du_an=None, xoa_het=False, thu=True):
    """thu=True: chỉ đếm (xem trước). -> {so, gb, muc: {nhóm: [số tệp, GB]}, da_xoa}"""
    now = time.time()
    tat = _ban_ghi_moi_du_an()
    if xoa_het and not du_an:
        raise ValueError("xoá hết cần chọn dự án")
    giu_ds = {k: v for k, v in tat.items() if not (xoa_het and k == du_an)}
    # video / ảnh còn được dùng
    mp4_dung = {os.path.basename(v.get("mp4") or "").lower() for d in giu_ds.values() for v in d.values() if v.get("mp4")}
    from common import thu_muc_du_an as _t
    for f in glob.glob(os.path.join(os.path.dirname(_t("x")[1]), "*", "nhan_y_giu.json")):
        if xoa_het and os.path.basename(os.path.dirname(f)) == du_an:
            continue
        mp4_dung |= {os.path.basename(c[2]).lower() for c in (doc_json(f, {}) or {}).get("clip") or [] if len(c) > 2}
    mp4_dung |= _ten_mp4_trong_nhap(du_an if xoa_het else None)       # bản nháp dự án KHÁC luôn được giữ
    anh_dung = set().union(*[_anh_cua(v) for d in giu_ds.values() for v in d.values()]) if giu_ds else set()
    ma_bo = {v.get("ma") for v in (tat.get(du_an) or {}).values()} if xoa_het else set()
    for f in glob.glob(os.path.join(ai.THU_AI, "*.jsx")):                 # ảnh code cảnh còn lại nhắc tới
        b = os.path.basename(f)[:-4]
        if b.startswith("_sua_") or b == "thu_vien" or b in ma_bo:
            continue
        try:
            anh_dung |= {m.lower() for m in re.findall(r"nhan_y/[\w.\-]+\.(?:png|jpe?g|webp)", open(f, encoding="utf-8").read())}
        except OSError:
            pass

    muc = {}

    def them(nhom, f, ep=False):
        try:
            if not ep and now - os.path.getmtime(f) < MOI_DUNG:
                return
            muc.setdefault(nhom, []).append((f, os.path.getsize(f) if os.path.isfile(f) else _co_thu_muc(f)))
        except OSError:
            pass

    for f in glob.glob(os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai", "*")):
        them("khung dựng thử", f)
    for f in glob.glob(os.path.join(CACHE_CHUNG, "nhan_y", "agy_canh", "*")):
        them("ảnh chấm Antigravity", f)
    for f in glob.glob(os.path.join(_mo_ai(), "*.mp4")):
        if os.path.basename(f).lower() not in mp4_dung:
            them("video cảnh" + (" của dự án" if xoa_het else " cũ không bản nháp nào dùng"), f, ep=xoa_het)
    for f in glob.glob(os.path.join(ai.THU_AI, "_sua_*.jsx")):
        them("bản đóng gói trình sửa lớp", f)
    pub = os.path.join(os.path.dirname(ai.THU_AI), "..", "public", "nhan_y")
    for f in glob.glob(os.path.join(pub, "*")):
        if os.path.isfile(f) and "nhan_y/" + os.path.basename(f).lower() not in anh_dung:
            them("ảnh Remotion" + (" của dự án" if xoa_het else " không cảnh nào dùng"), f, ep=xoa_het)
    if xoa_het:
        for m in ma_bo:
            for f in glob.glob(os.path.join(ai.THU_AI, f"{m}.jsx*")) + glob.glob(os.path.join(ai.THU_AI, f"_sua_{m}.jsx")):
                them("code cảnh", f, ep=True)
        thu_da = _t(du_an)[1]
        for f in glob.glob(os.path.join(thu_da, "nhan_y_ai.json*")) + [os.path.join(thu_da, x) for x in (
                "nhan_y_tien_do.json", "nhan_y_nhat_ky.txt", "nhan_y_giu.json", "nhac_chuong_remotion.json")]:
            if os.path.exists(f):
                them("bản ghi / tiến độ Remotion", f, ep=True)
        for f in glob.glob(os.path.join(thu_da, "sao_luu_*")):
            them("bản sao lưu cũ", f, ep=True)

    so = sum(len(x) for x in muc.values())
    gb = sum(s for x in muc.values() for _, s in x) / 1e9
    tom = {k: [len(x), round(sum(s for _, s in x) / 1e9, 2)] for k, x in muc.items()}
    if thu:
        return {"so": so, "gb": round(gb, 2), "muc": tom, "da_xoa": False}
    import shutil
    loi = 0
    for x in muc.values():
        for f, _ in x:
            try:
                shutil.rmtree(f) if os.path.isdir(f) else os.remove(f)
            except OSError:
                loi += 1
    if xoa_het:
        ai._dang_ky({})                                                  # noqa: SLF001  bỏ mục Studio của code đã xoá
    log(f"🧹 dọn Remotion{' — xoá hết ' + du_an if xoa_het else ''}: {so - loi} tệp, {gb:.2f} GB" + (f", {loi} tệp không xoá được" if loi else ""))
    return {"so": so - loi, "gb": round(gb, 2), "muc": tom, "da_xoa": True, "loi": loi}


def _co_thu_muc(d):
    return sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(d) for f in fs)


# --- sửa số liệu sai ------------------------------------------------------------------------------------------------------
def _quanh(du_an, cau):
    ds = sorted((doc_json(ai._ds(du_an), {}) or {}).values(), key=lambda v: int(v["cau"]))   # noqa: SLF001
    k = next((i for i, v in enumerate(ds) if int(v["cau"]) == int(cau)), None)
    if k is None:
        return ""
    return " ".join(x.get("text", "") for x in ds[max(0, k - 1):k] + ds[k + 1:k + 2])


def kiem_so(du_an, chi=None, bao=None, song_song=4):
    """🔢 Đọc chữ THẬT trên khung của các cảnh đã dựng -> {câu: [(số, chữ)]} số hiện mà lời kể không nói."""
    import so_lieu
    from concurrent.futures import ThreadPoolExecutor
    bao = bao or (lambda m: log("  " + m))
    ds = doc_json(ai._ds(du_an), {}) or {}                              # noqa: SLF001
    can = [v for v in ds.values() if v.get("ma") and (not chi or int(v["cau"]) in chi)
           and os.path.isfile(os.path.join(ai.THU_AI, f"{v['ma']}.jsx"))]

    def mot(v):
        sai, _ = so_lieu.kiem_hinh(v["ma"], ai._props_hien(v), v["giay"], v.get("text", ""), _quanh(du_an, v["cau"]))   # noqa: SLF001
        return int(v["cau"]), sai
    with ThreadPoolExecutor(song_song) as ex:
        kq = dict(ex.map(mot, can))
    sai = {c: x for c, x in sorted(kq.items()) if x}
    bao(f"🔢 đã đọc số trên {len(can)} cảnh — {len(sai)} cảnh có số không khớp lời")
    return sai


def sua_so(du_an, chi=None, bao=None, song_song=3):
    """🔢 Cảnh có số sai -> DeepSeek sửa đúng số (vòng sửa có kiểm số lại) -> dựng lại -> thay ĐÚNG cảnh đó trong bản nháp.
    -> {sua: [câu], hong: {câu: lỗi}, nhap}"""
    from concurrent.futures import ThreadPoolExecutor
    bao = bao or (lambda m: log("  " + m))
    sai = kiem_so(du_an, chi, bao)
    if not sai:
        return {"sua": [], "hong": {}, "nhap": None}
    viet, hong = {}, {}

    def mot(cau):
        v = _ban_ghi(du_an, cau)
        b = lambda m: bao(f"câu {cau}: {m}")                             # noqa: E731
        cu, pr0 = _code(v), ai._props_hien(v)                            # noqa: SLF001
        anh = "\n".join(f"  - {a['ten']} ({a['loai']}): '{a['file']}'" for a in v.get("anh") or [])
        nc = {"cau": v.get("text", ""), "quanh": _quanh(du_an, cau), "mo_ta": (v.get("thiet_ke") or {}).get("mo_ta", ""),
              "anh": anh, "tu_sua": False}
        y = ai._kiem_so(v["ma"], pr0, v["giay"], nc, b)                  # noqa: SLF001  (câu hỏi sửa: đúng danh sách số sai)
        if not y:
            return
        b("DeepSeek sửa số liệu…")
        try:
            code, pr = ai._viet_code(v["ma"], ai._HOI_GOP_Y.format(y_kien=y, code=cu, props=json.dumps(pr0, ensure_ascii=False)),   # noqa: SLF001
                                     pr0, v["giay"], b, nc)
        except Exception as e:                                           # noqa: BLE001
            code, pr = None, str(e)
        if code is None:
            with open(os.path.join(ai.THU_AI, f"{v['ma']}.jsx"), "w", encoding="utf-8", newline="\n") as g:
                g.write(cu)                                              # sửa hỏng: trả code cũ
            hong[cau] = str(pr)[:200]
            b(f"sửa không được — giữ cảnh cũ ({str(pr)[:80]})")
            return
        pr["giay"] = v["giay"]
        viet[cau] = (v, pr)

    with ThreadPoolExecutor(song_song) as ex:
        list(ex.map(mot, list(sai)))
    nhap = None
    for cau, (v, pr) in sorted(viet.items()):                           # dựng + ghép LẦN LƯỢT (một bản nháp)
        bao(f"câu {cau}: dựng lại video…")
        try:
            nhap = _dung_lai(du_an, dict(v, props=pr), pr, bao)["nhap"] or nhap
        except Exception as e:                                           # noqa: BLE001
            hong[cau] = str(e)[:200]
    bao(f"🔢 xong: sửa {len(viet) - len([c for c in viet if c in hong])} cảnh, hỏng {len(hong)}")
    return {"sua": sorted(c for c in viet if c not in hong), "hong": hong, "nhap": nhap}


# --- so bản Gemini (sao lưu) với bản ChatGPT thiết kế ---------------------------------------------------------------------
def _thu_sao_luu(du_an, sl=None):
    return os.path.join(thu_muc_du_an(du_an)[1], re.sub(r"[^\w]", "", sl or "") or "sao_luu_gemini_0511")


def so_sanh_ds(du_an, thu=None):
    """[{cau, text, gemini: {mp4, y_tuong, anh}, chatgpt: {...}}] các cảnh có bản sao lưu (thu: thư mục sao lưu)."""
    sl = doc_json(os.path.join(_thu_sao_luu(du_an, thu), "ban_ghi.json"), {}) or {}
    ds = doc_json(ai._ds(du_an), {}) or {}                              # noqa: SLF001
    tom = lambda v: {"mp4": v.get("mp4"), "y_tuong": (v.get("thiet_ke") or {}).get("y_tuong", ""),   # noqa: E731
                     "nhip": len((v.get("thiet_ke") or {}).get("nhip") or []),
                     "chon": (v.get("thiet_ke") or {}).get("_chon"), "phuong_an": (v.get("thiet_ke") or {}).get("_phuong_an"),
                     "anh": [a.get("loai") for a in v.get("anh") or []]}
    return [{"cau": int(c), "text": sl[c].get("text", ""), "gemini": tom(sl[c]), "chatgpt": tom(ds.get(c) or {}),
             "da_tra": (ds.get(c) or {}).get("mp4") == sl[c].get("mp4")} for c in sorted(sl, key=int)]


def tra_gemini(du_an, cau, bao=None, thu=None):
    """Trả cảnh về bản đã sao lưu (bản ghi + code) rồi thay đúng cảnh đó trong bản nháp."""
    sl = doc_json(os.path.join(_thu_sao_luu(du_an, thu), "ban_ghi.json"), {}) or {}
    v = sl.get(str(cau))
    if not v:
        raise ValueError(f"không có bản sao lưu câu {cau}")
    import shutil
    shutil.copy2(os.path.join(_thu_sao_luu(du_an, thu), f"{v['ma']}.jsx"), os.path.join(ai.THU_AI, f"{v['ma']}.jsx"))
    ai._ghi_ds(du_an, {str(cau): v})                                     # noqa: SLF001
    ai._dang_ky({v["ma"]: ai._props_hien(v)})                            # noqa: SLF001
    return {"nhap": ghep_mot(du_an, cau, bao)}


# --- 🎚 sửa CHỮ + HIỆU ỨNG của lớp (05/11 user: "hiện tại tôi không thể sửa chữ nếu có chữ hoặc sửa mấy cái hiệu ứng") -----
_HU_MO = re.compile(r"<HieuUng\b(?:[^>{}]|\{[^{}]*\})*>")
_HU_DONG = "</HieuUng>"


def _khoi_cua(code):
    """{đầu thẻ mở: (cuối thẻ mở, đầu thẻ đóng, cuối thẻ đóng)} của mọi <Interactive.Div> có thẻ đóng."""
    ra = {}
    the = {a: b for a, b, l in _cac_the(code) if l == "Interactive.Div"}
    for a, c, _, _ in ai._khoi_div(code):                               # noqa: SLF001
        if a in the:
            ra[a] = (the[a], c - len("</Interactive.Div>"), c)
    return ra


def _hu_doc(trong):
    """Nội dung ngay sau thẻ mở -> ({vao, ra, khung, lien} | None, (đầu, cuối) thẻ <HieuUng …>)."""
    m = re.match(r"\s*(" + _HU_MO.pattern + r")", trong)
    if not m:
        return None, None
    t = m.group(1)
    h = {k: (re.search(k + r"\s*=\s*['\"]([^'\"]*)['\"]", t) or [None, ""])[1] for k in ("vao", "ra", "lien")}
    kh = re.search(r"khung\s*=\s*\{\s*(\d+)\s*\}", t)
    h["khung"] = int(kh.group(1)) if kh else 12
    return h, (m.start(1), m.end(1))


def bo_hieu_ung(code):
    """Bản xem của trình sửa lớp: gỡ <HieuUng> đã lưu (trình sửa tự áp lại theo thông số, không áp hai lần)."""
    return _HU_MO.sub("", code).replace(_HU_DONG, "")


def _chu_cac_lop(code, pr):
    """Chữ của từng lớp -> {đầu thẻ mở: [{k, loai: code|prop, goc, vt?, khoa?}]} — mỗi chữ thuộc lớp TRONG CÙNG chứa nó."""
    khoi = _khoi_cua(code)
    body = code.find("export const Canh")
    pr = pr or {}
    gom = []
    for m in re.finditer(r">([^<>{}]+)<", code):                        # chữ giữa thẻ
        t = re.sub(r"\s+", " ", m.group(1)).strip()
        if t and re.search(r"[^\W_]", t) and m.start() > body:
            gom.append((m.start(1) + m.group(1).find(m.group(1).strip()), {"loai": "code", "goc": t, "raw": m.group(1).strip()}))
    for m in re.finditer(r"\bchu\s*=\s*(\"([^\"]+)\"|'([^']+)')", code):     # chu="…" của ChuNoi / Nhan
        t = m.group(2) or m.group(3)
        if m.start() > body:
            gom.append((m.start(1) + 1, {"loai": "code", "goc": t, "raw": t}))
    for m in re.finditer(r"(?:>\s*\{\s*|\bchu\s*=\s*\{\s*)(?:props\.)?(\w+)\s*\}", code):   # chữ lấy từ thông số
        if m.start() > body and isinstance(pr.get(m.group(1)), str) and re.search(r"[^\W_]", pr[m.group(1)]):
            gom.append((m.start(), {"loai": "prop", "goc": pr[m.group(1)], "khoa": m.group(1)}))
    ra = {}
    for vt, x in gom:
        chua = [a for a, (b, c, _) in khoi.items() if b <= vt < c]
        if not chua:
            continue
        a = max(chua)                                                    # lớp trong cùng
        ds = ra.setdefault(a, [])
        if x["loai"] == "prop" and any(y.get("khoa") == x["khoa"] for y in ds):
            continue
        ds.append(dict(x, vt=vt, k=f"{a}_{len(ds)}"))
    return ra


def lop_day_du(du_an, cau):
    """lop() + chữ của lớp + hiệu ứng đã lưu + lớp có kích thước hay tự co (cho trang 🎚)."""
    v = _ban_ghi(du_an, cau)
    code = _code(v)
    the = _cac_the(code)
    khoi = _khoi_cua(code)
    chu = _chu_cac_lop(code, ai._props_hien(v))                          # noqa: SLF001
    ra = []
    for x in lop(du_an, cau):
        a, b, loai = the[x["i"]]
        h = None
        if a in khoi:
            h, _ = _hu_doc(code[khoi[a][0]:khoi[a][1]])
        st = code[a:b]
        ra.append(x | {"chu": [{k: y[k] for k in ("k", "loai", "goc", "khoa") if k in y} for y in chu.get(a, [])],
                       "hieu": h, "co_hieu": loai == "Interactive.Div" and a in khoi,
                       "kieu": _kieu_lop(st)})
    return ra


def _kieu_lop(the):
    """Như kieuLop (hieu_ung_tinh.js): lớp dời góc (left / top khác 0, không width / height) -> 'goc', còn lại 'day'."""
    doi = any((_so_style(the, k) or 0) != 0 for k in ("left", "top"))
    return "goc" if doi and _doc_style(the, "width") is None and _doc_style(the, "height") is None else "day"


def _js_chu(t):
    """Chữ user gõ -> an toàn trong JSX text (không phá cú pháp)."""
    return re.sub(r"[{}<>]", "", str(t or "")).strip()


def ap_chu_hieu(code, ds, pr):
    """Ghi chữ (chu: [{k, moi}]) + hiệu ứng (hieu) user sửa vào code / thông số. -> (code, props)"""
    pr = dict(pr or {})
    chu = _chu_cac_lop(code, pr)
    the = _cac_the(code)
    sua = []                                                             # (vt, độ dài cũ, chữ mới) — chữ trong code
    for x in ds or []:
        k = int(x.get("i", -1))
        if not 0 <= k < len(the) or not x.get("chu"):
            continue
        cua = {y["k"]: y for y in chu.get(the[k][0], [])}
        for c in x["chu"]:
            y, moi = cua.get(c.get("k")), _js_chu(c.get("moi"))
            if not y or not moi or moi == y["goc"]:
                continue
            if y["loai"] == "prop":
                pr[y["khoa"]] = str(c.get("moi")).strip()
            elif code[y["vt"]:y["vt"] + len(y["raw"])] == y["raw"]:
                sua.append((y["vt"], len(y["raw"]), moi.replace('"', "'") if code[y["vt"] - 1] in "\"'" else moi))
    for vt, n, moi in sorted(sua, reverse=True):
        code = code[:vt] + moi + code[vt + n:]
    # hiệu ứng: từ lớp cuối lên (chèn / gỡ <HieuUng> không đổi thứ tự thẻ Interactive.Div / Img)
    co_hu = False
    for x in sorted(ds or [], key=lambda x: -int(x.get("i", -1))):
        if "hieu" not in x:
            continue
        the = _cac_the(code)
        k = int(x.get("i", -1))
        if not 0 <= k < len(the):
            continue
        khoi = _khoi_cua(code)
        a = the[k][0]
        if a not in khoi:
            continue
        b, c, _ = khoi[a]
        trong = code[b:c]
        _, vt = _hu_doc(trong)
        if vt:                                                           # gỡ bọc cũ
            j = trong.rfind(_HU_DONG)
            trong = trong[:vt[0]] + trong[vt[1]:j] + trong[j + len(_HU_DONG):] if j > vt[1] else trong[:vt[0]] + trong[vt[1]:]
        h = x.get("hieu") or {}
        if h.get("vao") or h.get("ra") or h.get("lien"):
            the_k = _cac_the(code)[k]
            st_k = code[the_k[0]:the_k[1]]
            doi = any((x.get(f) if x.get(f) is not None else (_so_style(st_k, c) or 0)) != 0
                      for f, c in (("trai", "left"), ("tren", "top")))
            kieu = "goc" if doi and _doc_style(st_k, "width") is None and _doc_style(st_k, "height") is None else "day"
            mo = (f'<HieuUng vao="{h.get("vao") or ""}" ra="{h.get("ra") or ""}" khung={{{int(h.get("khung") or 12)}}} '
                  f'lien="{h.get("lien") or ""}" kieu="{kieu}">')
            trong = mo + trong + _HU_DONG
            co_hu = True
        code = code[:b] + trong + code[c:]
    if co_hu and not re.search(r"import\s*\{[^}]*\bHieuUng\b[^}]*\}\s*from\s*['\"]\./thu_vien\.jsx['\"]", code):
        m = re.search(r"import\s*\{([^}]*)\}\s*from\s*(['\"])\./thu_vien\.jsx\2\s*;?", code)
        if m:
            code = code[:m.start(1)] + m.group(1).rstrip().rstrip(",") + ", HieuUng" + code[m.end(1):]
        else:
            code = "import {HieuUng} from './thu_vien.jsx';\n" + code
    return code, pr
