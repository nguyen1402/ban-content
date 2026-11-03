# -*- coding: utf-8 -*-
"""03/11 user: chỗ NHẤN Ý dựng bằng Remotion — AI TỰ VIẾT CODE từng cảnh, user duyệt chỗ và chỉnh tay.

Ba bước (user chốt 03/11):
  1. de_xuat(): AI đọc cả bài, TỰ suy luận câu nào người xem cần THẤY mới hiểu / mới nhớ — KHÔNG đưa cảnh mẫu, ví dụ hay
     gợi ý nào (để AI không bị kéo về thứ đang có). Ra danh sách {câu, lý do, ý chính}; chưa vẽ, chưa tốn điểm.
  2. User duyệt trong 📝 (loại 🎞 Remotion): bỏ tích / tự thêm câu -> lưu ra/<dự án>/nhan_y_ke_hoach.json.
  3. dung(): với từng chỗ đã duyệt:
       a. AI thiết kế bằng lời (2D hay 3D, chuyển động theo từng cụm từ) + danh sách ảnh cần vẽ;
       b. Flow vẽ ảnh (nền / vật tách nền / cận cảnh);
       c. AI VIẾT CODE cảnh Remotion (remotion/src/ai/<id>.jsx) dùng thư viện chung ai/thu_vien.jsx, mỗi thứ là một
          <Interactive.Div name=…> để user kéo / dời / cắt giờ trực tiếp trong Studio;
       d. dựng thử riêng (entry tạm, không đụng Root) -> lỗi / khung trống thì gửi lỗi lại cho AI sửa (tối đa SUA_TOI_DA);
       e. đạt: đăng ký vào khối sửa tay của Root.tsx (Studio) + dựng mp4 + ghép vào bản nháp _hoan_chinh.
Sửa sau khi dựng (🖼 panel): luu_lai() dựng lại từ code + thông số hiện tại (Studio có thể đã sửa); gop_y() để AI sửa
code theo góp ý của user. Ghép = thay track 'nhan_y' + 'nhan_y_sfx' của bản nháp _hoan_chinh (user 03/11: ghi đè thẳng).
"""
import glob
import json
import os
import re
import subprocess
import sys

AQ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQ)
for p in (ROOT, AQ):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import CACHE_CHUNG, doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an, thu_muc_nhap_capcut  # noqa: E402
import nhan_y  # noqa: E402

REMOTION = os.path.join(ROOT, "remotion")
THU_AI = os.path.join(REMOTION, "src", "ai")
SONG_SONG = 3                          # số chỗ dựng cùng lúc
SUA_TOI_DA = 3                         # số lượt gửi lỗi lại cho AI sửa code
MOI_GIAY = 45.0                        # bước 1: khoảng một chỗ mỗi bấy nhiêu giây (chỉ để AI biết mật độ, không bắt đủ số)
MOC_IMP_DAU, MOC_IMP_CUOI = "// NHAN_Y_AI_IMPORT_BAT_DAU", "// NHAN_Y_AI_IMPORT_KET_THUC"


def _kh(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_ke_hoach.json")


def _ds(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_ai.json")


def doc_ke_hoach(du_an):
    return (doc_json(_kh(du_an), {}) or {}).get("ds") or []


def luu_ke_hoach(du_an, ds):
    gon = []
    for y in ds or []:
        try:
            i = int(y.get("cau"))
        except (TypeError, ValueError):
            continue
        gon.append({"cau": i, "den_cau": max(i, int(y.get("den_cau") or i)), "bo": bool(y.get("bo")),
                    "y_chinh": str(y.get("y_chinh") or "")[:400], "ly_do": str(y.get("ly_do") or "")[:300],
                    "de_xuat": bool(y.get("de_xuat")), "tay": bool(y.get("tay"))})
    ghi_json(_kh(du_an), {"ds": sorted(gon, key=lambda z: z["cau"])})
    return len(gon)


# --- bước 1: AI tự đề xuất chỗ ---------------------------------------------------------------------------------------------
_HOI_CHO = """Below is the full narration of a documentary video (index, start second, text), in Vietnamese.
Think like the video's editor: in which sentences does the viewer need to SEE something animated to understand or to
remember the idea — something that ordinary stock footage cannot show? Decide this yourself from the meaning of the
sentences. It is fine to pick few; pick none rather than weak ones. Roughly at most one per {moi:.0f} seconds.
For each pick give, in Vietnamese: "ly_do" (why this sentence needs it, one short sentence) and "y_chinh" (the one idea the
viewer must walk away with). Do NOT describe how to animate it yet.
Return ONLY JSON: {{"chon": [{{"cau": <index>, "ly_do": "...", "y_chinh": "..."}}]}}

Sentences:
{ds}"""


def de_xuat(du_an, bao=None):
    """-> [{cau, den_cau, ly_do, y_chinh, de_xuat}] (CHƯA lưu: user duyệt trong 📝)."""
    bao = bao or (lambda m: log("  " + m))
    cau = nhan_y._cau(du_an)                                           # noqa: SLF001
    ds = "\n".join(f"{c['i']} [{c['t0']:.0f}s] {c['text']}" for c in cau)
    bao(f"AI đọc {len(cau)} câu, tự chọn chỗ cần dựng Remotion…")
    r = rut_json(hoi_llm(_HOI_CHO.format(moi=MOI_GIAY, ds=ds))) or {}
    co = {c["i"] for c in cau}
    return [{"cau": int(x["cau"]), "den_cau": int(x["cau"]), "ly_do": str(x.get("ly_do") or ""),
             "y_chinh": str(x.get("y_chinh") or ""), "de_xuat": True}
            for x in r.get("chon") or [] if isinstance(x, dict) and isinstance(x.get("cau"), int) and x["cau"] in co]


# --- bước 3a: thiết kế bằng lời + ảnh cần vẽ ----------------------------------------------------------------------------------
_HOI_THIET_KE = """You are a top motion designer for documentary explainer videos (2D motion graphics and simple 3D).
Design ONE short animated shot for this narration sentence (Vietnamese). The shot lasts {giay:.1f} seconds and must
follow the narration word by word. Previous sentence: «{truoc}». Sentence: «{cau}». Next sentence: «{sau}».
The one idea the viewer must remember: «{y_chinh}».
Word timings of the sentence (seconds from the start of the shot): {tu}.
Rules: be literal and factually correct (right species AND life stage, right era, objects exactly as named); never show a
thing before the narration names it; the biggest visual change lands on the most important words; no shaking; at most 2
on-screen text items (Vietnamese, numbers as digits); make it cinematic and specific to THIS sentence, not generic.
Decide freely whether it is 2D (layered photos, cut-outs, graphics) or 3D (a simple real 3D scene).
Also list the still images the AI image generator must draw for it (photorealistic, no text in images):
  "nen" = full 16:9 background or scene photo; "tach" = ONE object / person drawn alone on white (we cut it out);
  "can" = an extreme close-up 16:9 photo of a detail, seen straight-on and centered.
Sound effects: at most 3, only on the strongest beats, each tied to words of the sentence, "loai" one of: {sfx_loai}.
Return ONLY JSON: {{"kieu": "2d"|"3d", "mo_ta": "<the shot, beat by beat, which words trigger what>",
"anh": [{{"ten": "<short_key>", "loai": "nen"|"tach"|"can", "ve": "<English prompt>"}}],
"am": [{{"cum": "<1-4 words copied from the sentence>", "loai": "...", "chot": true|false}}]}}"""


def _ve_anh(a, du_an):
    """Một ảnh trong danh sách thiết kế -> {ten, loai, file (đường public), rong, cao} | None."""
    from PIL import Image
    loai, ve = a.get("loai"), str(a.get("ve") or "")
    if not ve:
        return None
    if loai == "tach":
        f, ti = nhan_y._tach(ve)                                       # noqa: SLF001
        if not f:
            return None
        im = Image.open(os.path.join(nhan_y.PUB, f))
        return {"ten": a.get("ten"), "loai": loai, "file": f, "rong": im.size[0], "cao": im.size[1]}
    them = (". Extreme close-up, straight-on, centered, sharp detail" if loai == "can" else "") + \
        ". Photorealistic, cinematic. No text, no labels, no watermark."
    f = nhan_y._anh_jpg(ve + them, nhan_y._md5("ai", loai, ve))         # noqa: SLF001
    return {"ten": a.get("ten"), "loai": loai, "file": f, "rong": 1920, "cao": 1080} if f else None


# --- bước 3c: AI viết code ------------------------------------------------------------------------------------------------
_HOI_CODE = """Write the Remotion (React, JSX, Remotion 4) component for this shot. Design: {mo_ta}
Canvas 1920x1080, 30 fps, duration {khung} frames ({giay:.1f} s). Sentence: «{cau}».
Word timings (frame where each word starts): {tu}.
Images you may use (paths for src(), already drawn; "tach" are transparent PNG cut-outs):
{anh}
Use ONLY these images, with the path EXACTLY as written (e.g. src('nhan_y/abc.jpg')): never add '/public', never call
staticFile yourself, never invent another file name, NEVER use any http(s) URL (internet images are blocked). Anything else must be drawn with HTML / SVG / CSS or 3D.
STRICT CONTRACT (the file is executed as-is):
- Start with these imports exactly (use only what you need from them):
  import React from 'react';
  import {{AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig}} from 'remotion';
  import {{z}} from 'zod';
  import {{src, kep, FONT, VANG, EM, AnhNen, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan}} from './thu_vien.jsx';
  For 3D also: import {{ThreeCanvas}} from '@remotion/three'; import * as THREE from 'three';
- Library (local frame 0 = when its block appears): AnhNen({{anh, tu, den, goc, toi}}) full-frame photo with slow push;
  ChuNoi({{chu, co}}) big text revealing word by word with a yellow underline; SoDem({{so, don_vi, giay, co}}) count-up
  number; Nhan({{chu, dx, dy, co}}) callout dot at its origin + leader line to a label box offset (dx, dy) px;
  VongBut({{w, h}}) hand-drawn ring; MuiTen({{dx, dy, cong}}) curved arrow drawn from origin; HienDan({{vao, het}}) fade-in.
  src(path) turns an image path into a URL. kep = clamp options for interpolate.
- export const schema = z.object({{ ... }}) with every value worth tweaking (texts, numbers, sizes, colours, speeds),
  each with .describe('<Vietnamese label>'). Image paths go in the schema too (z.string()).
- export const Canh = (props) => {{ ... }} reading those props. Every visible element the user may want to move or
  retime is its OWN <Interactive.Div name="<Vietnamese name>" from={{<frame>}} durationInFrames={{<frames>}}
  style={{{{position: 'absolute', left: <px>, top: <px>}}}}> with LITERAL numbers (Remotion Studio edits them by hand).
  Inside it, animate with useCurrentFrame() (local frames). <Img> is already interactive and also takes name / from.
- Animation ONLY through useCurrentFrame() + interpolate / spring / Easing; no CSS animation, no Math.random (use
  random('seed')), no useFrame. For 3D: <ThreeCanvas width={{1920}} height={{1080}}> with lights; move the camera
  from frame values.
- Keep every text inside the frame (x 60..1860, y 60..1020). No shaking, no jitter.
QUALITY RULES (the user rejected earlier shots for exactly these — the render is checked automatically and sent back):
- NEVER show the narration sentence as a subtitle / caption / karaoke text. On-screen text is ONLY the 1-2 short key
  texts of the design (at most 8 words each). Labels at most 5 words.
- The frame must be FULL the whole time: a full-frame background photo (AnhNen with one of the "nen" / "can" images,
  or a full 3D scene) covers the frame from the first to the last frame. No flat-colour or dark empty backgrounds, no
  black frames, no fading to black (the editor fades the clip).
- Make things BIG: the main subject fills at least about 40% of the frame height; key text font size >= 90 px,
  labels >= 56 px. Few large elements, not many tiny ones. If a cut-out is used it must be at least 500 px tall/wide.
- No decorative glows, blobs, particles or lens flares that do not mean anything in the narration.
Return the FULL code in ONE fenced ```jsx code block, then the default props (one JSON object matching the schema) in ONE fenced ```json code block. Never write code outside the fenced blocks."""

_HOI_SUA = """The Remotion component below fails. Fix it. Return the FULL code in ONE fenced ```jsx code block, then the default props (one JSON object matching the schema) in ONE fenced ```json code block. Never write code outside the fenced blocks. Keep the same contract (export const schema, export const Canh, Interactive.Div with
literal numbers, imports from './thu_vien.jsx'). Problem:
{loi}

```jsx
{code}
```"""

_HOI_GOP_Y = """Change this Remotion component according to the user's request (Vietnamese): «{y_kien}».
Keep the same contract and everything the user did not ask to change. Return the FULL code in ONE fenced ```jsx code block, then the default props (one JSON object matching the schema) in ONE fenced ```json code block. Never write code outside the fenced blocks.

```jsx
{code}
```
Current props: {props}"""


_NHAN_NGON_NGU = re.compile(r"^\s*(javascript|jsx|js|typescript|tsx|react|json|code|plaintext)\s*$", re.I)


def _bo_nhan(t):
    """Bỏ dòng tên ngôn ngữ đầu khối (Gemini web đổi khung ``` thành một dòng 'JavaScript' / 'JSON')."""
    dong = (t or "").strip("\n").splitlines()
    while dong and (not dong[0].strip() or _NHAN_NGON_NGU.match(dong[0]) or dong[0].strip().startswith("```")):
        dong.pop(0)
    while dong and (not dong[-1].strip() or dong[-1].strip().startswith("```")):
        dong.pop()
    return "\n".join(dong)


def _json_dau(t):
    i = (t or "").find("{")
    while i >= 0:
        try:
            return json.JSONDecoder().raw_decode(t[i:])[0]
        except ValueError:
            i = t.find("{", i + 1)
    return {}


def _tach_tra_loi(t):
    """(code, props) từ câu trả lời của AI — nhận 3 dạng: dấu mốc <<<CODE / CODE>>>, khung ```, hoặc dòng tên ngôn ngữ
    'JavaScript' … 'JSON' (03/11: Gemini web trả dạng này, mất hết dấu ```)."""
    t = t or ""
    code, pr = "", {}
    m = re.search(r"<<<CODE\s*\n(.*?)\n\s*CODE>>>", t, re.S)
    if m:
        code = _bo_nhan(m.group(1))
        q = re.search(r"<<<PROPS\s*\n(.*?)\n\s*PROPS>>>", t, re.S)
        pr = _json_dau(q.group(1)) if q else {}
    if not code:
        m = re.search(r"```(?:jsx|tsx|js|javascript)?\s*\n(.*?)```", t, re.S)
        if m:
            code = m.group(1).strip()
            js = re.findall(r"```json\s*\n(.*?)```", t, re.S)
            pr = _json_dau(js[-1]) if js else {}
    if not code:                                                         # dạng nhãn: JavaScript\n<code>\nJSON\n{…}
        dong = t.splitlines()
        i = next((k for k, d in enumerate(dong) if re.match(r"^\s*(javascript|jsx|typescript|tsx|react)\s*$", d, re.I)), None)
        j = next((k for k, d in enumerate(dong) if re.match(r"^\s*json\s*$", d, re.I) and (i is None or k > i)), None)
        if i is not None:
            code = "\n".join(dong[i + 1:j if j is not None else len(dong)]).strip()
            pr = _json_dau("\n".join(dong[j + 1:])) if j is not None else {}
        elif "export const Canh" in t:                                   # không nhãn gì: lấy từ dòng import đầu
            k = t.find("import ")
            code = t[k:].strip() if k >= 0 else ""
    return code, (pr if isinstance(pr, dict) else {})


def _ma(du_an, i):
    return f"{du_an}_cau{i}".replace("-", "_")


def _ten_comp(ma):
    return "Ai" + "".join(w.capitalize() for w in re.split(r"[_\W]+", ma) if w)


def _id_comp(ma):
    return "ai-" + ma.replace("_", "-")


def _thu_dung(ma, props, giay, khung_thu, mod=None, thu=None):
    """Dựng thử riêng (entry tạm chỉ chứa cảnh này) vài khung -> ("", [ảnh]) | (lỗi, []).
    mod: tệp cảnh trong src/ai (mặc định <ma>.jsx); thu: thư mục ghi khung hình."""
    import numpy as np
    from PIL import Image
    entry = os.path.join(THU_AI, f"_thu_{ma}.jsx")
    with open(entry, "w", encoding="utf-8") as f:
        f.write(f"""import React from 'react';
import {{Composition, registerRoot}} from 'remotion';
import {{Canh}} from './{mod or ma + ".jsx"}';
const P = {json.dumps(props, ensure_ascii=False)};
registerRoot(() => <Composition id="thu" component={{Canh}} width={{1920}} height={{1080}} fps={{30}}
  durationInFrames={{{max(30, round(giay * 30))}}} defaultProps={{P}} />);
""")
    thu = thu or os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai")
    os.makedirs(thu, exist_ok=True)
    ra = []
    try:
        for k in khung_thu:
            out = os.path.join(thu, f"{ma}_{k}.png")
            if os.path.isfile(out):
                os.remove(out)
            r = subprocess.run(["npx", "remotion", "still", os.path.relpath(entry, REMOTION), "thu", out, f"--frame={k}",
                                "--gl=angle", "--log=error"], cwd=REMOTION, capture_output=True, shell=True, timeout=600,
                               creationflags=0x08000000 if os.name == "nt" else 0)
            if r.returncode or not os.path.isfile(out):
                t = (r.stderr or b"").decode("utf-8", "ignore") + (r.stdout or b"").decode("utf-8", "ignore")
                dong = [x for x in t.splitlines() if x.strip() and "node_modules" not in x][-25:]
                return "\n".join(dong)[-3000:] or "dựng thử không ra ảnh", []
            a = np.asarray(Image.open(out).convert("L").resize((192, 108)), np.float32)
            if a.std() < 4:
                return f"frame {k} is blank / a flat colour (nothing visible) — check positions, opacity and timing", []
            # 03/11 user (cảnh 99, 106, 33: nền trống / tối, vật bé tí): phần lớn khung là một màu trơn -> lỗi
            trong = float((np.abs(a - np.median(a)) < 10).mean())
            if trong > 0.72:
                return (f"frame {k}: {trong:.0%} of the frame is one flat colour — the frame looks EMPTY. Cover it with the "
                        "full-frame background photo (AnhNen) and make the main subject big"), []
            if a.mean() < 22:
                return f"frame {k} is almost black (mean brightness {a.mean():.0f}/255) — keep the background photo visible", []
            ra.append(out)
    finally:
        if os.path.isfile(entry):
            os.remove(entry)
    return "", ra


def _chu_dai(pr):
    """Chữ hiện trên hình dài quá 9 từ (phụ đề cả câu) -> lỗi để AI sửa. 03/11 user: AI tự chèn cả câu lời đọc."""
    for k, v in (pr or {}).items():
        if isinstance(v, str) and not re.search(r"\.(png|jpe?g|webp|wav|mp4)$", v, re.I) and not v.startswith(("#", "rgb")) \
                and len(v.split()) > 9:
            return (f"prop '{k}' shows a long text ({len(v.split())} words): never show the narration as a caption; "
                    "on-screen texts are at most 8 words")
    return ""


def _chu_dai_code(code):
    """Như _chu_dai nhưng cho chữ viết thẳng trong code (chuỗi trong nháy hoặc chữ giữa thẻ JSX)."""
    for m in re.finditer(r"'([^'\n]{30,})'|\"([^\"\n]{30,})\"|>([^<>{}\n]{30,})<", code or ""):
        t = next(g for g in m.groups() if g)
        if code[max(0, m.start() - 12):m.start()].rstrip().endswith("describe("):
            continue                                                     # nhãn ô thông số trong Studio, không hiện lên hình
        chu = sum(ch.isalpha() or ch.isspace() for ch in t) / max(1, len(t))
        if len(t.split()) > 9 and chu > 0.85 and not re.search(r"[{};=():]|px\b|rgba|import |from ", t):
            return f"the code shows a long text «{t[:60]}…» ({len(t.split())} words): never show the narration as a caption"
    return ""


DUYET_AGY = True                       # 03/11 user: Antigravity (Gemini 3.8 Flash, có mắt) chấm khung hình + sửa code
AGY_TAC_NHAN = True                    # chưa đạt: Antigravity tự sửa + tự dựng thử (agy.tac_nhan_sua, quyền hẹp)


def _kiem(ma, code, pr, giay):
    """Ghi code + kiểm (chữ dài, dựng thử 6 khung, khung trống / tối). -> (lỗi, [(giây, png)])"""
    with open(os.path.join(THU_AI, f"{ma}.jsx"), "w", encoding="utf-8", newline="\n") as f:
        f.write(code + "\n")
    loi = _chu_dai(pr) or _chu_dai_code(code)
    if loi:
        return loi, []
    dau, cuoi = 0.6 * 30, (giay - 0.4) * 30                              # bỏ lúc cảnh đang mờ vào / mờ ra
    khung = [round(dau + (cuoi - dau) * k) for k in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
    loi, anh = _thu_dung(ma, pr, giay, khung)
    return loi, [(k / 30, a) for k, a in zip(khung, anh)]


def _viet_code(ma, hoi, props_mac, giay, bao, nc=None):
    """Hỏi AI viết code + vòng sửa lỗi + (nếu có) Antigravity nhìn khung hình chấm / sửa. -> (code, props) | (None, lỗi).
    nc: ngữ cảnh cho Antigravity {cau, y_chinh, mo_ta, anh}."""
    import agy
    nc = nc or {}
    dung_agy = DUYET_AGY and agy.co()
    os.makedirs(THU_AI, exist_ok=True)
    tl = hoi_llm(hoi, timeout=420)
    loi = ""
    thu = os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai")
    os.makedirs(thu, exist_ok=True)
    for lan in range(SUA_TOI_DA + 1):
        with open(os.path.join(thu, f"{ma}_tra_loi_{lan}.txt"), "w", encoding="utf-8") as f:   # để xem lại khi hỏng
            f.write(tl or "")
        code, pr = _tach_tra_loi(tl)
        if not code:
            loi = "the answer has no ```jsx code block"
        elif "export const Canh" not in code or "export const schema" not in code:
            loi = "the code must contain `export const schema` and `export const Canh`"
        else:
            pr = props_mac | pr
            loi, khung = _kiem(ma, code, pr, giay)
            if not loi:
                return _duyet_agy(ma, code, pr, giay, khung, nc, bao) if dung_agy else (code, pr)
        bao(f"code AI lỗi (lần {lan + 1}): {loi.splitlines()[0][:140] if loi else ''}")
        if lan == SUA_TOI_DA:
            break
        if dung_agy and code:                                            # Antigravity đọc lỗi + sửa (giỏi hơn Gemini web)
            bao(f"Antigravity sửa lỗi (lần {lan + 1})…")
            c2, p2 = _tach_tra_loi(agy.sua_code(nc.get("cau", ""), [loi], nc.get("mo_ta", ""), nc.get("anh", ""), code, pr))
            if c2 and "export const Canh" in c2:
                tl = f"```jsx\n{c2}\n```\n```json\n{json.dumps(p2 or pr, ensure_ascii=False)}\n```"
                continue
        tl = hoi_llm(_HOI_SUA.format(loi=loi, code=code or tl[:6000]), timeout=420)
    return None, loi


def _duyet_agy(ma, code, pr, giay, khung, nc, bao):
    """Code đã qua bộ đo: Antigravity NHÌN khung hình, chấm theo bảng kiểm; chưa đạt thì lấy code nó sửa — sửa hỏng bộ
    đo thì giữ bản đã qua. -> (code, props)"""
    import agy
    dat, diem, loi = agy.duyet_canh(nc.get("cau", ""), nc.get("y_chinh", ""), nc.get("mo_ta", ""), khung,
                                     [os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai")])
    if diem is None:
        bao("Antigravity không chấm được — giữ bản đã qua bộ đo")
        return code, pr
    bao(f"Antigravity chấm {diem}/10" + (" — đạt" if dat else f" — chưa đạt: {'; '.join(map(str, loi))[:160]}"))
    if dat:
        return code, pr
    # 03/11 (thử): Antigravity headless tự sửa code thì cứ đòi chạy lệnh (bị chặn trong sandbox) rồi quá giờ -> Antigravity
    # CHẤM + chỉ lỗi, Gemini web SỬA theo đúng nhận xét, Antigravity chấm lại: điểm cao hơn mới nhận
    c2 = None
    if AGY_TAC_NHAN:                                                     # 03/11: quyền hẹp -> Antigravity tự sửa, tự dựng,
        bao("Antigravity tự sửa + dựng thử + nhìn khung…")              # tự nhìn, lặp; vẫn qua bộ đo + chấm lại bên dưới
        c2, p2, tu = agy.tac_nhan_sua(ma, nc.get("cau", ""), nc.get("y_chinh", ""), nc.get("mo_ta", ""), nc.get("anh", ""),
                                      loi, code, pr, giay, bao=bao)
        bao(f"Antigravity tự chấm bản sửa: {tu}/10" if c2 else "Antigravity không ra bản sửa — chuyển Gemini")
    if not c2:
        bao("Gemini sửa theo nhận xét của Antigravity…")
        c2, p2 = _tach_tra_loi(hoi_llm(_HOI_GOP_Y.format(y_kien="; ".join(map(str, loi)), code=code,
                                                         props=json.dumps(pr, ensure_ascii=False)), timeout=420))
    if not c2 or "export const Canh" not in c2:
        return code, pr
    p2 = pr | (p2 or {})
    loi2, khung2 = _kiem(ma, c2, p2, giay)
    if loi2:
        bao(f"bản sửa không qua bộ đo ({loi2.splitlines()[0][:100]}) — giữ bản trước")
        _kiem(ma, code, pr, giay)                                         # ghi lại bản đã qua
        return code, pr
    _, diem2, loi_2 = agy.duyet_canh(nc.get("cau", ""), nc.get("y_chinh", ""), nc.get("mo_ta", ""), khung2,
                                     [os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai")])
    if diem2 is not None and int(diem2) < int(diem):
        bao(f"Antigravity chấm bản sửa {diem2}/10 (kém hơn {diem}) — giữ bản trước")
        _kiem(ma, code, pr, giay)
        return code, pr
    bao(f"dùng bản đã sửa — Antigravity chấm lại {diem2}/10" + (f": {'; '.join(map(str, loi_2))[:120]}" if loi_2 else ""))
    return c2, p2


# --- Root.tsx: import + mục Studio ------------------------------------------------------------------------------------------
def _root_import(ds_ma):
    """Ghi khối import các cảnh AI trong Root.tsx."""
    t = open(nhan_y.ROOT_TSX, encoding="utf-8").read()
    if MOC_IMP_DAU not in t:                                             # lần đầu: đặt khối import sau dòng import cuối
        i = t.rfind("\nimport ")
        j = t.index("\n", i + 1)
        t = t[:j + 1] + f"{MOC_IMP_DAU}\n{MOC_IMP_CUOI}\n" + t[j + 1:]
    a, b = t.index(MOC_IMP_DAU) + len(MOC_IMP_DAU), t.index(MOC_IMP_CUOI)
    dong = []
    co_giong = False
    for m in sorted(ds_ma):
        if not os.path.isfile(os.path.join(THU_AI, f"{m}.jsx")):
            continue
        dong.append(f"import {{Canh as {_ten_comp(m)}, schema as {_ten_comp(m)}Schema}} from './ai/{m}.jsx';")
        g = f"{nhan_y.THU_PUB}/giong_{m}.wav"
        dong.append(f"const {_ten_comp(m)}G = coGiong({_ten_comp(m)}, {json.dumps(g if os.path.isfile(os.path.join(nhan_y.PUB, g)) else '')});")
        co_giong = True
    if co_giong:
        dong.insert(0, "import {coGiong} from './ai/thu_vien.jsx';")
    t = t[:a] + "\n" + "\n".join(dong) + ("\n" if dong else "") + t[b:]
    with open(nhan_y.ROOT_TSX, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)


def _dang_ky(cac):
    """cac = {ma: props}: ghi import + mục Studio (giữ mục của mẫu / dự án khác)."""
    co = nhan_y._cho_sua_doc()                                          # noqa: SLF001
    muc = {k: v for k, v in co.items() if not k.startswith("ai-")}
    ma_co = {k[3:].replace("-", "_") for k in co if k.startswith("ai-")}
    for k, v in co.items():                                              # cảnh AI của dự án khác: giữ
        if k.startswith("ai-") and k[3:].replace("-", "_") not in cac:
            muc[k] = v
    for m, pr in cac.items():
        muc[_id_comp(m)] = (_ten_comp(m) + "G", pr)                       # lớp bọc có giọng đọc của câu
    # 03/11: mục Studio của cảnh AI mà tệp code không còn (viết lỗi) -> bỏ, nếu không cả Root hỏng (thiếu tên) và mọi
    # lần dựng đều hỏng
    muc = {k: v for k, v in muc.items()
           if not k.startswith("ai-") or os.path.isfile(os.path.join(THU_AI, k[3:].replace("-", "_") + ".jsx"))}
    _root_import({m for m in ma_co | set(cac) if os.path.isfile(os.path.join(THU_AI, f"{m}.jsx"))})
    nhan_y._cho_sua_ghi(muc)                                            # noqa: SLF001


# --- bản nháp ---------------------------------------------------------------------------------------------------------------
def ban_nhap_dich(du_an):
    """Bản nháp _hoan_chinh mới nhất của dự án (✨ tạo) — nơi ghi đè track nhấn ý. | None"""
    dd = thu_muc_nhap_capcut()
    ds = [p for p in glob.glob(os.path.join(dd, f"{du_an}*_hoan_chinh*")) if os.path.isfile(os.path.join(p, "draft_content.json"))
          and "_nhan_y" not in os.path.basename(p)]
    return max(ds, key=lambda p: os.path.getmtime(os.path.join(p, "draft_content.json"))) if ds else None


def _giu_khac(d, clip_ai):
    """03/11 user ("không thay được remotion cũ" — hai bản nháp lẫn nhau): track nhấn ý chỉ có MỘT bản nháp _hoan_chinh.
    Clip nhấn ý KHÔNG phải cảnh AI (vd chỗ dựng bằng cảnh mẫu, user mang sang) đang nằm trên track thì giữ nguyên, trừ
    chỗ chồng lên cảnh AI; tiếng của chúng (nằm trong khoảng clip) cũng giữ. -> (clip, sfx)"""
    thu_ai = os.path.normcase(os.path.join(CACHE_CHUNG, "nhan_y", "ai"))
    mv = {m["id"]: m.get("path") for m in d["materials"].get("videos", []) + d["materials"].get("audios", [])}
    ai = [(a, a + g) for a, g, _ in clip_ai]
    trung = lambda a, b: any(a < y and x < b for x, y in ai)            # noqa: E731
    clip, khoang = [], []
    for t in d["tracks"]:
        if t.get("name") != "nhan_y":
            continue
        for s_ in t["segments"]:
            f = mv.get(s_["material_id"]) or ""
            a = s_["target_timerange"]["start"] / 1e6
            b = a + s_["target_timerange"]["duration"] / 1e6
            if not os.path.isfile(f) or os.path.normcase(os.path.dirname(f)) == thu_ai or trung(a, b):
                continue
            clip.append((a, b - a, f))
            khoang.append((a, b))
    sfx = []
    for t in d["tracks"]:
        if t.get("name") != "nhan_y_sfx":
            continue
        for s_ in t["segments"]:
            a = s_["target_timerange"]["start"] / 1e6
            f = mv.get(s_["material_id"]) or ""
            if os.path.isfile(f) and any(x - 0.05 <= a < y for x, y in khoang):
                sfx.append((a, f, float(s_.get("volume", 1.0))))
    return clip, sfx


def capcut_dang_mo():
    """CapCut đang chạy? (đang mở bản nháp thì lúc đóng CapCut ghi bản của nó đè lên thay đổi của mình)"""
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"], capture_output=True,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    return b"CapCut.exe" in (r.stdout or b"")


def ghep(du_an, bao=None):
    """Thay track nhấn ý của bản nháp _hoan_chinh bằng mọi cảnh AI đã dựng (ghi đè tại chỗ). -> tên bản nháp | None"""
    import dung_tay
    bao = bao or (lambda m: log("  " + m))
    p = ban_nhap_dich(du_an)
    if not p:
        bao("chưa có bản nháp _hoan_chinh — chạy ✨ Hoàn thiện trước (các cảnh đã dựng sẽ tự ghép vào)")
        return None
    ds = doc_json(_ds(du_an), {}) or {}
    clip, sfx = [], []
    gd_f = os.path.join(thu_muc_du_an(du_an)[1], "giong_doc.wav")
    gd = nhan_y._ebur(gd_f)[0] if os.path.isfile(gd_f) else -18.0       # noqa: SLF001
    lan = {}
    for v in sorted(ds.values(), key=lambda z: z.get("t0", 0)):
        if v.get("trang_thai") != "xong" or not os.path.isfile(v.get("mp4") or ""):
            continue
        clip.append((v["t0"], v["giay"], v["mp4"]))
        for q in (v.get("sfx") or [])[:3]:
            a = nhan_y._sfx(q.get("loai"), lan.get(q.get("loai"), 0))     # noqa: SLF001
            lan[q.get("loai")] = lan.get(q.get("loai"), 0) + 1
            if a:
                vol = nhan_y._am_luong(a[0], gd, bool(q.get("chot")))     # noqa: SLF001
                if vol < 4.0:
                    sfx.append((round(max(0.0, v["t0"] + float(q.get("t") or 0) - a[1]), 3), a[0], vol))
    f = os.path.join(p, "draft_content.json")
    sao = f + ".truoc_nhan_y"                                            # bản gốc trước LẦN ĐẦU ghi (lấy lại được)
    if not os.path.isfile(sao):
        import shutil
        shutil.copy2(f, sao)
    d0 = nhan_y._doc(f)                                                  # noqa: SLF001
    giu_c, giu_s = _giu_khac(d0, clip)
    # nhớ clip giữ lại (✨ dựng lại _hoan_chinh từ đầu thì ghép lại được) + gộp với danh sách đã nhớ
    p_giu = os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_giu.json")
    nho = doc_json(p_giu, {}) or {}
    ai = [(a, a + g) for a, g, _ in clip]
    for a, g, f_ in nho.get("clip") or []:
        if os.path.isfile(f_) and not any(abs(a - x) < 0.05 for x, _, _ in giu_c) and not any(a < y and x < a + g for x, y in ai):
            giu_c.append((a, g, f_))
    for a, f_, v_ in nho.get("sfx") or []:
        if os.path.isfile(f_) and any(x - 0.05 <= a < x + g for x, g, _ in giu_c) and not any(abs(a - x) < 0.05 for x, _, _ in giu_s):
            giu_s.append((a, f_, v_))
    ghi_json(p_giu, {"clip": sorted(giu_c), "sfx": sorted(giu_s)})
    d = nhan_y._ghep(d0, clip + giu_c, sfx + giu_s)                      # noqa: SLF001
    for g in [f] + glob.glob(os.path.join(p, "Timelines", "*", "draft_content.json")):
        nhan_y._ghi(g, d)                                                # noqa: SLF001
        if os.path.isfile(g + ".bak"):
            os.remove(g + ".bak")
    dung_tay._sua_nhap(p, [c[2] for c in clip])                          # noqa: SLF001
    bao(f"đã ghi {len(clip)} cảnh Remotion AI + giữ {len(giu_c)} clip nhấn ý khác vào bản nháp '{os.path.basename(p)}'"
        + (" — ⚠ CapCut ĐANG MỞ: đóng hẳn CapCut rồi mở lại bản nháp (đang mở thì lúc đóng CapCut ghi đè mất thay đổi)"
           if capcut_dang_mo() else " — mở lại bản nháp trong CapCut"))
    return os.path.basename(p)


# --- dựng -------------------------------------------------------------------------------------------------------------------
def _giong(du_an, v):
    """Cắt đúng đoạn giọng đọc của cảnh ra remotion/public/nhan_y/giong_<ma>.wav (nghe khi sửa)."""
    from common import FFMPEG
    wav = os.path.join(thu_muc_du_an(du_an)[1], "giong_doc.wav")
    dich = os.path.join(nhan_y.PUB, nhan_y.THU_PUB, f"giong_{v['ma']}.wav")
    if os.path.isfile(wav):
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{v['t0']:.3f}", "-t", f"{float(v['giay']):.3f}", "-i", wav,
                        "-ac", "1", "-ar", "44100", dich], capture_output=True,
                       creationflags=0x08000000 if os.name == "nt" else 0)


def _render_nhieu(viec):
    """viec = [(ma, props, giay)] -> {ma: mp4 | None}. MỘT lượt Remotion (đóng gói một lần, dựng song song 3 clip)."""
    import nen_ban_do
    thu = os.path.join(CACHE_CHUNG, "nhan_y", "ai")
    os.makedirs(thu, exist_ok=True)
    ra, jobs = {}, []
    for ma, props, giay in viec:
        code = open(os.path.join(THU_AI, f"{ma}.jsx"), encoding="utf-8").read()
        out = os.path.join(thu, nhan_y._md5(ma, code, json.dumps(props, sort_keys=True), "giong") + ".mp4")   # noqa: SLF001
        ra[ma] = out
        if not (os.path.isfile(out) and os.path.getsize(out) > 5000):
            jobs.append({"comp": _id_comp(ma), "giay": giay, "out": out, "props": props})
    if jobs:
        nen_ban_do._render(jobs, thu, ten="cảnh Remotion AI")              # noqa: SLF001
    return {m: (o if os.path.isfile(o) and os.path.getsize(o) > 5000 else None) for m, o in ra.items()}


def _render(ma, props, giay):
    """Dựng mp4 của một mục Studio (đã đăng ký trong Root) -> đường mp4 | None."""
    return _render_nhieu([(ma, props, giay)])[ma]


def _mot_cho(du_an, y, cau, theo_i, bao, cu=None):
    """Dựng một chỗ đã duyệt -> bản ghi {…} (trang_thai xong / loi). cu: bản ghi lần trước (dùng lại thiết kế + ảnh khi
    chỉ có bước viết code hỏng — không thiết kế / vẽ lại tốn điểm Flow)."""
    c = theo_i.get(y["cau"])
    if not c:
        return {"trang_thai": "loi", "loi": "không thấy câu"}
    c_cuoi = theo_i.get(y.get("den_cau") or y["cau"], c)
    t0 = c["t0"]
    giay = round(min(14.0, max(3.0, c_cuoi["t1"] - t0 + 0.5)), 2)
    text = " ".join(theo_i[k]["text"] for k in range(y["cau"], (y.get("den_cau") or y["cau"]) + 1) if k in theo_i)
    tu = [(w, round(a - t0, 2)) for k in range(y["cau"], (y.get("den_cau") or y["cau"]) + 1) if k in theo_i
          for w, a, _ in theo_i[k].get("tu") or []]
    truoc, sau = theo_i.get(y["cau"] - 1, {}).get("text", ""), theo_i.get((y.get("den_cau") or y["cau"]) + 1, {}).get("text", "")
    ma = _ma(du_an, y["cau"])
    cu = cu or {}
    tk = cu.get("thiet_ke") if cu.get("thiet_ke") and cu.get("text") == text else None
    if tk:
        bao(f"câu {y['cau']}: dùng lại thiết kế + ảnh lần trước")
    else:
        bao(f"câu {y['cau']}: AI thiết kế cảnh…")
    tk = tk or rut_json(hoi_llm(_HOI_THIET_KE.format(giay=giay, truoc=truoc, cau=text, sau=sau, y_chinh=y.get("y_chinh") or "",
                                                tu=", ".join(f"{w}@{s}s" for w, s in tu),
                                                sfx_loai=", ".join(nhan_y._sfx_loai())), timeout=300)) or {}   # noqa: SLF001
    if not tk.get("mo_ta"):
        return {"trang_thai": "loi", "loi": "AI không trả thiết kế", "t0": t0, "giay": giay, "text": text}
    anh = list(cu.get("anh") or []) if cu.get("thiet_ke") is tk else []
    for a in ([] if anh else (tk.get("anh") or [])[:5]):
        bao(f"câu {y['cau']}: vẽ ảnh '{a.get('ten')}' ({a.get('loai')})…")
        r = _ve_anh(a, du_an)
        if r:
            anh.append(r)
        else:
            bao(f"câu {y['cau']}: ! không vẽ được ảnh '{a.get('ten')}'")
    mo_anh = "\n".join(f"  - {a['ten']} ({a['loai']}, {a['rong']}x{a['cao']}): '{a['file']}'" for a in anh) or "  (none)"
    bao(f"câu {y['cau']}: AI viết code cảnh ({tk.get('kieu', '2d')})…")
    hoi = _HOI_CODE.format(mo_ta=tk["mo_ta"], khung=round(giay * 30), giay=giay, cau=text,
                           tu=", ".join(f"{w}@{round(s * 30)}" for w, s in tu), anh=mo_anh)
    code, pr = _viet_code(ma, hoi, {}, giay, lambda m: bao(f"câu {y['cau']}: {m}"),
                          {"cau": text, "y_chinh": y.get("y_chinh") or "", "mo_ta": tk.get("mo_ta", ""), "anh": mo_anh})
    ban_ghi = {"ma": ma, "id": _id_comp(ma), "cau": y["cau"], "den_cau": y.get("den_cau") or y["cau"], "t0": t0, "giay": giay,
               "text": text, "thiet_ke": tk, "anh": anh, "tu": tu}
    if code is None:
        f_code = os.path.join(THU_AI, f"{ma}.jsx")
        if os.path.isfile(f_code):
            os.replace(f_code, f_code + ".loi")                           # không để code hỏng làm hỏng cả Root
        return ban_ghi | {"trang_thai": "loi", "loi": pr}
    pr["giay"] = giay
    loai_ok = set(nhan_y._sfx_loai())                                    # noqa: SLF001
    sfx = []
    for q in (tk.get("am") or [])[:3]:                                   # tiếng AI chọn, đặt theo giờ chữ đầu của cụm
        if isinstance(q, dict) and q.get("loai") in loai_ok:
            g = nhan_y._gio_cum(theo_i[y["cau"]], str(q.get("cum") or ""))   # noqa: SLF001
            sfx.append({"t": round((g - t0) if g is not None else 0.0, 2), "loai": q["loai"], "chot": bool(q.get("chot"))})
    return ban_ghi | {"trang_thai": "viet_xong", "props": pr, "sfx": sfx}


def dung(du_an, chi=None, bao=None, lam_lai=False, viet_lai=False):
    """Bước 3 cho mọi chỗ đã duyệt (chi: chỉ các câu này; lam_lai: bỏ cả phần đã chỉnh tay). -> {xong, loi, nhap}"""
    bao = bao or (lambda m: log("  " + m))
    kh = [y for y in doc_ke_hoach(du_an) if not y.get("bo") and (not chi or y["cau"] in chi)]
    if not kh:
        return {"xong": 0, "loi": 0, "nhap": None}
    cau = nhan_y._cau(du_an)                                           # noqa: SLF001
    theo_i = {c["i"]: c for c in cau}
    ds = doc_json(_ds(du_an), {}) or {}
    import threading
    from concurrent.futures import ThreadPoolExecutor
    khoa = threading.Lock()

    def mot(y):
        k = str(y["cau"])
        if not lam_lai and not viet_lai and ds.get(k, {}).get("trang_thai") == "xong" and (ds[k].get("sua_tay") or not chi):
            bao(f"câu {y['cau']}: đã dựng / chỉnh tay — giữ nguyên")
            return
        if not lam_lai and not viet_lai and ds.get(k, {}).get("trang_thai") == "viet_xong" and os.path.isfile(os.path.join(THU_AI, f"{ds[k]['ma']}.jsx")):
            return                                                       # code đã viết + dựng thử đạt: chỉ còn dựng video
        cu = dict(ds.get(k) or {})
        f_code = os.path.join(THU_AI, f"{cu.get('ma') or _ma(du_an, y['cau'])}.jsx")
        sao = f_code + ".truoc"
        if os.path.isfile(f_code):
            import shutil
            shutil.copy2(f_code, sao)                                    # code cũ còn chạy được
        try:
            r = _mot_cho(du_an, y, cau, theo_i, bao, None if lam_lai else cu)
        except Exception as e:                                           # noqa: BLE001  một chỗ hỏng không dừng cả loạt
            r = {"trang_thai": "loi", "loi": str(e)[:300], "cau": y["cau"]}
        # 03/11 (viết lại theo luật mới hỏng cả 9 cảnh -> mất cảnh cũ khỏi bản nháp): lượt mới hỏng thì GIỮ bản cũ
        if r.get("trang_thai") == "loi" and cu.get("trang_thai") in ("xong", "viet_xong")                 and (os.path.isfile(sao) or os.path.isfile(cu.get("mp4") or "")):
            if os.path.isfile(sao):
                os.replace(sao, f_code)                                  # có code cũ: trả lại; không thì vẫn giữ video cũ
            bao(f"câu {y['cau']}: lượt mới hỏng ({str(r.get('loi'))[:80]}) — giữ cảnh cũ")
            r = cu | {"loi_moi": r.get("loi", "")}
        elif os.path.isfile(sao):
            os.remove(sao)
        with khoa:
            ds[k] = r
            ghi_json(_ds(du_an), ds)
    # 03/11 user ("hình như đang chạy tuần tự"): SONG_SONG chỗ cùng lúc — phần lớn thời gian là chờ AI trả lời / Flow vẽ,
    # Gemini hỏi song song trên nhiều hồ sơ Chrome, Flow vẽ song song nhiều tài khoản
    with ThreadPoolExecutor(SONG_SONG) as ex:
        list(ex.map(mot, kh))
    viet = {v["ma"]: v["props"] for v in ds.values() if v.get("trang_thai") in ("viet_xong", "xong") and v.get("props")}
    for v in ds.values():
        if v.get("ma") in viet:
            _giong(du_an, v)
    if viet:
        _dang_ky(viet)
    can = [v for v in ds.values() if v.get("trang_thai") in ("viet_xong", "xong") and (not chi or v.get("cau") in chi)
           and os.path.isfile(os.path.join(THU_AI, f"{v.get('ma')}.jsx"))]      # không còn code: giữ video cũ, không dựng
    loi = sum(1 for v in ds.values() if v.get("trang_thai") == "loi" and (not chi or v.get("cau") in chi))
    bao(f"dựng video {len(can)} cảnh (một lượt, song song)…")
    mp4 = _render_nhieu([(v["ma"], _props_hien(v), v["giay"]) for v in can]) if can else {}
    xong = 0
    for v in can:
        if mp4.get(v["ma"]):
            v.update(trang_thai="xong", mp4=mp4[v["ma"]])
            xong += 1
        elif os.path.isfile(v.get("mp4") or ""):                         # dựng hỏng nhưng còn video cũ: giữ video cũ
            v.update(trang_thai="xong")
            bao(f"câu {v['cau']}: dựng lại hỏng — giữ video cũ")
        else:
            v.update(trang_thai="loi", loi="dựng video hỏng")
            loi += 1
    ghi_json(_ds(du_an), ds)
    return {"xong": xong, "loi": loi, "nhap": ghep(du_an, bao)}


def _props_hien(v):
    """Thông số hiện tại của cảnh: bản trong Root.tsx (Studio có thể đã sửa) hoặc bản AI."""
    co = nhan_y._cho_sua_doc().get(v["id"])                             # noqa: SLF001
    return co[1] if co else v.get("props") or {}


def ds_canh(du_an):
    """Danh sách cảnh cho 🖼: [{cau, text, trang_thai, loi, mp4, id, props, thiet_ke}]"""
    ds = doc_json(_ds(du_an), {}) or {}
    ra = []

    def nhan(ma):                                                        # nhãn tiếng Việt AI ghi trong schema (.describe)
        try:
            t = open(os.path.join(THU_AI, f"{ma}.jsx"), encoding="utf-8").read()
        except OSError:
            return {}
        return dict(re.findall(r"(\w+)\s*:\s*z\.[^\n]*?\.describe\(\s*['\"`]([^'\"`]+)['\"`]", t))
    for k, v in sorted(ds.items(), key=lambda z: int(z[0])):
        ra.append({"cau": v.get("cau", int(k)), "text": v.get("text", ""), "trang_thai": v.get("trang_thai"), "loi": v.get("loi", ""),
                   "mp4": v.get("mp4", ""), "id": v.get("id", ""), "props": _props_hien(v) if v.get("id") else {},
                   "mo_ta": (v.get("thiet_ke") or {}).get("mo_ta", ""), "kieu": (v.get("thiet_ke") or {}).get("kieu", ""),
                   "sua_tay": bool(v.get("sua_tay")), "nhan": nhan(v["ma"]) if v.get("ma") else {}})
    return ra


def luu_lai(du_an, cau, props=None, bao=None):
    """🖼 ✅ Lưu: (props mới từ bảng sửa nhanh, nếu có) -> ghi Root -> dựng lại -> ghi đè bản nháp."""
    bao = bao or (lambda m: log("  " + m))
    ds = doc_json(_ds(du_an), {}) or {}
    v = ds.get(str(cau))
    if not v or not v.get("ma"):
        raise ValueError("chưa có cảnh này")
    pr = _props_hien(v) | (props or {})
    _giong(du_an, v | {"giay": float(pr.get("giay") or v["giay"])})
    _dang_ky({v["ma"]: pr})
    v.update(props=pr, sua_tay=True)
    mp4 = _render(v["ma"], pr, float(pr.get("giay") or v["giay"]))
    if not mp4:
        raise ValueError("dựng lại hỏng — xem lại thông số / code")
    v.update(mp4=mp4, trang_thai="xong", giay=float(pr.get("giay") or v["giay"]))
    ghi_json(_ds(du_an), ds)
    return {"mp4": mp4, "nhap": ghep(du_an, bao)}


def gop_y(du_an, cau, y_kien, bao=None):
    """🖼 💬: AI sửa code cảnh theo góp ý của user -> dựng thử -> dựng lại -> ghi đè bản nháp."""
    bao = bao or (lambda m: log("  " + m))
    ds = doc_json(_ds(du_an), {}) or {}
    v = ds.get(str(cau))
    if not v or not v.get("ma"):
        raise ValueError("chưa có cảnh này")
    f_code = os.path.join(THU_AI, f"{v['ma']}.jsx")
    cu = open(f_code, encoding="utf-8").read()
    pr0 = _props_hien(v)
    code, pr = _viet_code(v["ma"], _HOI_GOP_Y.format(y_kien=y_kien, code=cu, props=json.dumps(pr0, ensure_ascii=False)),
                          pr0, v["giay"], bao)
    if code is None:
        with open(f_code, "w", encoding="utf-8", newline="\n") as f:      # sửa hỏng: trả lại code cũ
            f.write(cu)
        raise ValueError(f"AI sửa không chạy được: {str(pr)[:200]}")
    pr["giay"] = float(pr.get("giay") or v["giay"])
    v.update(props=pr, sua_tay=True)
    ghi_json(_ds(du_an), ds)
    return luu_lai(du_an, cau, pr, bao)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--du-an", required=True)
    ap.add_argument("--de-xuat", action="store_true")
    ap.add_argument("--dung", action="store_true")
    ap.add_argument("--cau", default=None)
    a = ap.parse_args()
    if a.de_xuat:
        print(json.dumps(de_xuat(a.du_an), ensure_ascii=False, indent=1))
    if a.dung:
        print(dung(a.du_an, [int(x) for x in a.cau.split(",")] if a.cau else None))


def mang_sang(du_an, tu_nhap, cau_ds, bao=None):
    """Mang các clip nhấn ý của bản nháp khác (vd bản _nhan_y của luồng cảnh mẫu) ở các câu cau_ds sang bản _hoan_chinh."""
    bao = bao or (lambda m: log("  " + m))
    d = nhan_y._doc(os.path.join(thu_muc_nhap_capcut(), tu_nhap, "draft_content.json"))   # noqa: SLF001
    cau = {c["i"]: c for c in nhan_y._cau(du_an)}                      # noqa: SLF001
    can = [(cau[i]["t0"] - 0.6, cau[i]["t1"] + 0.6) for i in cau_ds if i in cau]
    c_, s_ = _giu_khac(d, [])
    c_ = [x for x in c_ if any(a <= x[0] <= b for a, b in can)]
    s_ = [x for x in s_ if any(y[0] - 0.05 <= x[0] < y[0] + y[1] for y in c_)]
    p_giu = os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_giu.json")
    nho = doc_json(p_giu, {}) or {}
    ghi_json(p_giu, {"clip": sorted((nho.get("clip") or []) + [list(x) for x in c_]),
                     "sfx": sorted((nho.get("sfx") or []) + [list(x) for x in s_])})
    bao(f"mang {len(c_)} clip ({len(s_)} tiếng) từ '{tu_nhap}' sang")
    return ghep(du_an, bao)
