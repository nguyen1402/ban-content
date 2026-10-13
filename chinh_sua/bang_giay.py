# -*- coding: utf-8 -*-
"""LỚP REMOTION "BẢNG GIẤY" khớp lời đọc (12/10 user, theo kênh mẫu "Вся жизнь пчелы"): giữ việc cắt ghép video/ảnh
theo lời, thêm lớp dàn dựng chuyên nghiệp — nói tới ý nào thì cảnh đó hiện trong THẺ trên nền giấy kèm tiêu đề/nhãn,
mũi tên cam nối ý trước -> ý sau, camera lướt giữa các thẻ; câu hỏi -> thẻ câu hỏi; số liệu -> cột so sánh; năm ->
mốc năm; nước/vùng -> bản đồ phẳng tô màu. Xen các câu 'toan_canh' (video tràn màn hình như cũ) để đổi nhịp.

  1. ChatGPT chọn kiểu dàn dựng cho TỪNG CÂU theo đoạn ~20 câu (lap_kich_ban).
  2. Cảnh quay mỗi câu lấy từ kế hoạch cắt ghép (canh[_os] của du_an_moi) -> cắt sẵn clip ngắn vào remotion/public/bg/.
  3. Gom các câu không phải 'toan_canh' liên tiếp thành KHỐI (<= KHOI_TOI_DA s), Remotion 'BangGiay' render mỗi khối.
  4. dung_hoan_chinh đặt clip khối lên track 'bang_giay' trên cùng (che hình, bản đồ, thẻ ảnh trong khoảng đó)."""
import hashlib
import json
import os
import subprocess

from common import FFMPEG, hoi_nhieu, log, rut_json

CAU_MOI_DOAN = 20
KHOI_TOI_DA = 45.0
FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "remotion")
PUB = os.path.join(REMOTION, "public", "bg")
#: tên nước trong world-atlas countries-110m (bản đồ phẳng chỉ tô được nước có trong danh sách này)
TEN_NUOC = {x.lower() for x in ['Afghanistan', 'Albania', 'Algeria', 'Angola', 'Antarctica', 'Argentina', 'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bangladesh', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herz.', 'Botswana', 'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada', 'Central African Rep.', 'Chad', 'Chile', 'China', 'Colombia', 'Congo', 'Costa Rica', 'Croatia', 'Cuba', 'Cyprus', 'Czechia', "Côte d'Ivoire", 'Dem. Rep. Congo', 'Denmark', 'Djibouti', 'Dominican Rep.', 'Ecuador', 'Egypt', 'El Salvador', 'Eq. Guinea', 'Eritrea', 'Estonia', 'Ethiopia', 'Falkland Is.', 'Fiji', 'Finland', 'Fr. S. Antarctic Lands', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Greece', 'Greenland', 'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kosovo', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Lithuania', 'Luxembourg', 'Macedonia', 'Madagascar', 'Malawi', 'Malaysia', 'Mali', 'Mauritania', 'Mexico', 'Moldova', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'N. Cyprus', 'Namibia', 'Nepal', 'Netherlands', 'New Caledonia', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'North Korea', 'Norway', 'Oman', 'Pakistan', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda', 'S. Sudan', 'Saudi Arabia', 'Senegal', 'Serbia', 'Sierra Leone', 'Slovakia', 'Slovenia', 'Solomon Is.', 'Somalia', 'Somaliland', 'South Africa', 'South Korea', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 'Timor-Leste', 'Togo', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States of America', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Venezuela', 'Vietnam', 'W. Sahara', 'Yemen', 'Zambia', 'Zimbabwe', 'eSwatini']}
KIEU = ("toan_canh", "the", "cau_hoi", "so_sanh", "moc", "ban_do")
_P = """You are a motion-graphics editor of a Vietnamese documentary in a "paper board" style: footage shown inside framed cards on a beige paper board with short bold titles, labels pointing at details, dashed arrows between ideas, question cards, comparison bars, year markers and flat maps. Below is ONE PASSAGE of narration (sentence index. text). For EVERY sentence choose how it is staged:
- "toan_canh": plain full-screen footage (no graphics). Use for about 30% of sentences — descriptive or emotional ones — and never 3 in a row.
- "the": footage in a framed card with "tieu_de" = a SHORT Vietnamese title of 1-4 words naming the key subject or idea of THIS sentence (e.g. "Ong chúa", "Tổ thứ cấp", "Bẫy mùa xuân"); optional "nhan" = 1-3 word Vietnamese label of a detail the viewer should notice.
- "cau_hoi": the sentence is a rhetorical question or a striking statement → "chu" = that question/statement in Vietnamese, at most 12 words.
- "so_sanh": the sentence compares or states 2-3 quantities → "tieu_de" (1-4 words) and "so": [{{"nhan": "1-3 word Vietnamese label", "gia_tri": number, "don_vi": "short unit"}}]. Numbers MUST come from the sentence (spelled-out Vietnamese numbers → digits).
- "moc": a year is the focus → "nam": the year (integer), "nhan": 2-6 word Vietnamese caption.
- "ban_do": a country or large region is the focus → "dia_danh_en": the country name exactly as in Natural Earth (e.g. "Spain", "France", "China"), "nhan": Vietnamese name.
Titles and labels must be accurate to the sentence. Prefer "the" when unsure.
Return ONLY JSON: [{{"cau": <index>, "kieu": "...", ...}}] with one object per sentence.

PASSAGE:
{ds}"""


def lap_kich_ban(cau):
    """{chỉ số câu: dàn dựng} — ChatGPT, song song theo đoạn; câu thiếu (lô hỏng) hỏi lại 2 vòng với lô nhỏ hơn."""
    ra = {}
    for vong, co in enumerate((CAU_MOI_DOAN, 8, 4)):
        thieu = [c for c in cau if c["i"] not in ra]
        if not thieu:
            break
        ra.update(_hoi(thieu, co, vong))
    return ra


def _hoi(cau, co, vong):
    lots = [cau[i:i + co] for i in range(0, len(cau), co)]
    log(f"[BG] bảng giấy: hỏi ChatGPT dàn dựng {len(cau)} câu ({len(lots)} đoạn){' — hỏi lại' if vong else ''}…")
    tra = hoi_nhieu([_P.format(ds=chr(10).join(f"{c['i']}. {c['text']}" for c in lot)) for lot in lots], timeout=300)
    ra = {}
    for r in tra:
        for x in (rut_json(r) or []):
            try:
                if isinstance(x, dict) and x.get("kieu") in KIEU:
                    ra[int(x["cau"])] = x
            except (TypeError, ValueError, KeyError):
                continue
    return ra


def _cat(o, src0, dai, phong=1.0):
    """Cắt đoạn [src0, src0+dai] của video gốc -> remotion/public/bg/<băm>.mp4 (1280x720, không tiếng). Trả tên tương đối."""
    os.makedirs(PUB, exist_ok=True)
    k = hashlib.md5(f"{o['clip']}|{src0:.2f}|{dai:.2f}|{phong}|v2".encode()).hexdigest()[:16]
    ten = f"bg/{k}.{'jpg' if o.get('anh') else 'mp4'}"
    dich = os.path.join(REMOTION, "public", ten)
    if os.path.isfile(dich) and os.path.getsize(dich) > 1000:
        return ten
    vf = f"crop=iw/{phong}:ih/{phong},scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1"
    if o.get("anh"):
        lenh = [FFMPEG, "-y", "-v", "error", "-i", o["clip"], "-vf", vf, "-frames:v", "1", "-q:v", "3", dich]
    else:
        # tpad: giữ khung cuối thêm 2 s — clip cắt sát cuối file nguồn hay thiếu vài khung, và thẻ cũ còn hiện khi camera lướt
        lenh = [FFMPEG, "-y", "-v", "error", "-ss", f"{src0:.3f}", "-t", f"{dai + 0.15:.3f}", "-i", o["clip"], "-an", "-vf",
                vf + ",fps=30,tpad=stop_mode=clone:stop_duration=2", "-c:v", "libx264", "-crf", "21", "-preset", "veryfast",
                "-pix_fmt", "yuv420p", dich]
    p = subprocess.run(lenh, capture_output=True, timeout=300, creationflags=0x08000000 if os.name == "nt" else 0)
    return ten if p.returncode == 0 and os.path.isfile(dich) else None


def _clips(canh, a, b, SEC=1_000_000):
    """Các mảnh cảnh quay (theo kế hoạch cắt ghép) phủ khoảng [a, b) giây -> [{src, tu, dai, anh}] (tu tính từ a)."""
    ra = []
    for c in canh:
        for (t, d, o) in c["_os"]:
            t0, t1 = t / SEC, (t + d) / SEC
            x0, x1 = max(a, t0), min(b, t1)
            if x1 - x0 < 0.08 or o.get("ban_do"):
                continue
            src = _cat(o, (o.get("vao") or 0.0) + (x0 - t0), x1 - x0, float(o.get("phong") or 1.0))
            if src:
                ra.append({"src": src, "tu": round(x0 - a, 3), "dai": round(x1 - x0, 3), "anh": bool(o.get("anh"))})
    return sorted(ra, key=lambda z: z["tu"])


def lap(cau, canh, out, den_giay=None):
    """Kế hoạch + render. cau: [{i, t0, t1, text}] (giây). den_giay: chỉ làm tới giây này (bản thử).
    Trả [{bd, dai, file, so_nhip}] — các khối Remotion đặt lên track 'bang_giay'."""
    ds = [c for c in cau if den_giay is None or c["t0"] < den_giay]
    cache = os.path.join(out, "bang_giay_kich_ban.json")
    from common import doc_json, ghi_json
    da = {int(k): v for k, v in (doc_json(cache, {}) or {}).items()}
    thieu = [c for c in ds if c["i"] not in da]
    if thieu:
        da.update(lap_kich_ban(thieu))
        ghi_json(cache, {str(k): v for k, v in da.items()})
    kb = da
    nhip = []
    for k, c in enumerate(ds):
        x = dict(kb.get(c["i"]) or {"kieu": "the", "tieu_de": ""})
        if x["kieu"] == "ban_do" and (x.get("dia_danh_en") or "").lower() not in TEN_NUOC:
            x.update(kieu="the", tieu_de=x.get("nhan") or x.get("tieu_de") or "")     # không phải tên nước -> thẻ thường
        het = ds[k + 1]["t0"] if k + 1 < len(ds) else c["t1"]
        x.update(cau=c["i"], t0=c["t0"], t1=max(het, c["t0"] + 0.5))
        nhip.append(x)
    # gom KHỐI: các nhịp không phải toan_canh liên tiếp
    khoi, cur = [], []
    for n in nhip:
        if n["kieu"] == "toan_canh" or (cur and n["t1"] - cur[0]["t0"] > KHOI_TOI_DA):
            if cur:
                khoi.append(cur)
            cur = [] if n["kieu"] == "toan_canh" else [n]
        else:
            cur.append(n)
    if cur:
        khoi.append(cur)
    thu = os.path.join(out, "bang_giay")
    os.makedirs(thu, exist_ok=True)
    jobs, ra = [], []
    for kk, ks in enumerate(khoi):
        a, b = ks[0]["t0"], ks[-1]["t1"]
        props = []
        for n in ks:
            p = {k: n[k] for k in ("kieu", "tieu_de", "nhan", "chu", "so", "nam", "dia_danh_en") if n.get(k) is not None}
            p.update(bd=round(n["t0"] - a, 3), dai=round(n["t1"] - n["t0"], 3))
            if n["kieu"] in ("the", "cau_hoi", "moc"):
                p["clips"] = [dict(z, tu=round(z["tu"], 3)) for z in _clips(canh, n["t0"], n["t1"])]
            if n["kieu"] == "moc":
                try:
                    p["nam"] = int(n.get("nam"))
                except (TypeError, ValueError):
                    p["kieu"], p["tieu_de"] = "the", n.get("nhan", "")
                    p["clips"] = p.get("clips") or _clips(canh, n["t0"], n["t1"])
            props.append(p)
        h = hashlib.md5(json.dumps(props, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:14]
        f = os.path.join(thu, f"khoi_{kk:03d}_{h}.mp4")
        ra.append({"bd": round(a, 3), "dai": round(b - a, 3), "file": f, "so_nhip": len(ks),
                   "kieu": [n["kieu"] for n in ks]})
        if not (os.path.isfile(f) and os.path.getsize(f) > 5000):
            jobs.append({"comp": "BangGiay", "giay": round(b - a, 3), "out": f, "props": {"nhip": props}})
    from collections import Counter
    log(f"    bảng giấy: {len(nhip)} câu → {dict(Counter(n['kieu'] for n in nhip))}; {len(khoi)} khối Remotion "
        f"({sum(x['dai'] for x in ra):.0f}s / {(ds[-1]['t1'] - ds[0]['t0']) if ds else 0:.0f}s)")
    if jobs:
        import do_hoa
        from common import ghi_json
        p = os.path.join(thu, "jobs.json")
        ghi_json(p, jobs)
        env = dict(os.environ)
        ch = do_hoa._chrome()                                       # noqa: SLF001
        if ch:
            env["BROWSER_EXE"] = ch
        log(f"    Remotion dựng {len(jobs)} khối bảng giấy…")
        r = subprocess.run(["node", "render.mjs", p], cwd=REMOTION, env=env, capture_output=True, timeout=6 * 3600,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        log("    " + "\n    ".join(r.stdout.decode("utf-8", "ignore").strip().splitlines()[-4:]))
    return [x for x in ra if os.path.isfile(x["file"]) and os.path.getsize(x["file"]) > 5000]


def dat(script, ds, SEC=1_000_000):
    """Đặt các khối lên track 'bang_giay' (đã tạo, trên cùng)."""
    import pycapcut as draft
    from pycapcut import trange
    for x in ds:
        mat = draft.VideoMaterial(x["file"])
        d = min(int(x["dai"] * SEC), int(mat.duration) - 1000)
        script.add_segment(draft.VideoSegment(mat, trange(int(x["bd"] * SEC), d)), track_name="bang_giay")
    return len(ds)
