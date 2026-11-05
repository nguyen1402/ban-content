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
import time

AQ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQ)
for p in (ROOT, AQ):
    if p not in sys.path:
        sys.path.insert(0, p)

from common import CACHE_CHUNG, doc_json, ghi_json, hoi_llm, log, rut_json, thu_muc_du_an, thu_muc_nhap_capcut  # noqa: E402
import nhan_y  # noqa: E402

REMOTION = os.path.join(ROOT, "remotion")
THU_AI = os.path.join(REMOTION, "src", "ai")
SONG_SONG = 6                          # số chỗ dựng cùng lúc (04/11 user: 3 -> 6; ô trên 📝 chỉnh 1..SONG_SONG_TOI_DA)
SONG_SONG_TOI_DA = 9                   # = số hồ sơ Gemini dùng được (mỗi hồ sơ trả lời một câu một lúc)
SUA_TOI_DA = 3                         # số lượt gửi lỗi lại cho AI sửa code
MOI_GIAY = 45.0                        # bước 1: khoảng một chỗ mỗi bấy nhiêu giây (chỉ để AI biết mật độ, không bắt đủ số)
MOC_IMP_DAU, MOC_IMP_CUOI = "// NHAN_Y_AI_IMPORT_BAT_DAU", "// NHAN_Y_AI_IMPORT_KET_THUC"


def _kh(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_ke_hoach.json")


def _ds(du_an):
    return os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_ai.json")


_KHOA_DS = __import__("threading").Lock()


def _ghi_ds(du_an, moi):
    """04/11 (thử lopxe: hai lượt dựng cùng lúc, lượt xong sau ghi cả tệp đè mất câu 4, 8 của lượt kia): chỉ ghi các cảnh
    của mình — đọc lại tệp ngay trước khi ghi rồi cập nhật đúng các khoá đó."""
    with _KHOA_DS:
        ds = doc_json(_ds(du_an), {}) or {}
        ds.update(moi)
        ghi_json(_ds(du_an), ds)


RAM_TOI_THIEU = 18.0                   # 05/11 user ("an toàn tránh bị quá tải"): RAM trống dưới bấy nhiêu % thì CHƯA nhận
#                                        cảnh mới — cảnh đang làm cứ làm, đợi RAM nhả ra (Chrome rảnh tự đóng) mới làm tiếp


def _cho_ram(bao, cau):
    try:
        import ca_bai
    except Exception:                                                    # noqa: BLE001
        return
    bao_roi = False
    for _ in range(360):                                                 # tối đa ~30 phút rồi cứ làm (không treo mãi)
        gb, pt = ca_bai.ram_trong()
        if pt >= RAM_TOI_THIEU:
            return
        if not bao_roi:
            bao(f"câu {cau}: RAM trống còn {pt:.0f}% ({gb:.1f} GB) — chờ bớt tải rồi mới làm cảnh này…")
            bao_roi = True
        time.sleep(5)


class TienDo:
    """04/11 user ("phải cho tôi biết nó đang làm câu nào… để tôi theo dõi tiến trình"): ra/<dự án>/nhan_y_tien_do.json
    (trang 📝 đọc mỗi vài giây) + nhật ký ra/<dự án>/nhan_y_nhat_ky.txt (mỗi dòng có giờ + câu)."""

    def __init__(self, du_an, cau, viec, song_song):
        import threading
        out = thu_muc_du_an(du_an)[1]
        self.f, self.f_nk = os.path.join(out, "nhan_y_tien_do.json"), os.path.join(out, "nhan_y_nhat_ky.txt")
        self.k = threading.Lock()
        self.t0 = time.time()
        self.d = {"viec": viec, "dang_chay": True, "bat_dau": self.t0, "song_song": int(song_song), "buoc": "",
                  "cau": {str(c): {"tt": "cho", "dong": "", "luc": 0} for c in cau}, "ket": ""}
        self._ghi()
        self.nk(f"===== {viec}: {len(cau)} câu ({', '.join(map(str, cau[:30]))}{'…' if len(cau) > 30 else ''})")

    def nk(self, m):
        with self.k, open(self.f_nk, "a", encoding="utf-8") as f:
            f.write(time.strftime("%d/%m %H:%M:%S ") + str(m) + "\n")

    def _ghi(self):
        x = list(self.d["cau"].values())
        moi = [v for v in x if v.get("moi")]
        con = sum(1 for v in x if v["tt"] in ("cho", "dang"))
        tb = (sum(v["luc"] - v["bd"] for v in moi) / len(moi)) if moi else None
        self.d.update(so_xong=sum(1 for v in x if v["tt"] == "xong"), so_loi=sum(1 for v in x if v["tt"] == "loi"), con=con,
                      tb_giay=round(tb) if tb else None, luc=time.time(),
                      con_giay=round(tb * con / max(1, self.d["song_song"])) if tb and con else (0 if not con else None))
        ghi_json(self.f, self.d)

    def bao_qua(self, bao):
        def b(m, *_):
            r = re.match(r"câu (\d+): (.*)", str(m))
            with self.k:
                v = self.d["cau"].get(r.group(1)) if r else None
                if v is not None and v["tt"] in ("cho", "dang"):
                    if v["tt"] == "cho":
                        v["bd"] = time.time()
                    v.update(tt="dang", dong=r.group(2)[:160], luc=time.time())
                self._ghi()
            self.nk(m)
            bao(m)
        return b

    def _ket(self, c, tt, dong):
        with self.k:
            v = self.d["cau"].setdefault(str(c), {})
            v.update(tt=tt, dong=dong, luc=time.time(), moi="bd" in v)
            self._ghi()
        self.nk(f"câu {c}: {'✔' if tt == 'xong' else '✖'} {dong}")

    def xong(self, c, dong=""):
        self._ket(c, "xong", dong)

    def loi(self, c, dong=""):
        self._ket(c, "loi", dong)

    def buoc(self, m):
        with self.k:
            self.d["buoc"] = m
            self._ghi()
        self.nk(m)

    def het(self, m):
        with self.k:
            self.d.update(dang_chay=False, ket=m, buoc="", het=time.time())
            self._ghi()
        self.nk(f"===== XONG: {m} ({(time.time() - self.t0) / 60:.0f} phút)")


def doc_tien_do(du_an):
    """Tiến độ lượt dựng gần nhất; tiến trình chết giữa chừng (không cập nhật > 15 phút) -> dang_chay False, bi_dung True."""
    d = doc_json(os.path.join(thu_muc_du_an(du_an)[1], "nhan_y_tien_do.json"), {}) or {}
    if d.get("dang_chay") and time.time() - float(d.get("luc") or 0) > 900:
        d.update(dang_chay=False, bi_dung=True)
    return d


AI_CANH = "deepseek"                   # 05/11 (lần 2) user: "nếu để hỏi dựng kĩ thì deepseek kĩ hơn gemini" -> DeepSeek, với
#                                        câu lệnh kiểu đạo diễn + nhịp êm (lần 1 cảnh loạn vì khớp từng chữ). Trước đó:
# 04/11 thử DeepSeek DeepThink (hồ sơ dự án, miễn phí) cho thiết kế + code cảnh; 05/11 user:
#                                        "gemini ổn hơn, deepseek kỹ nhưng cảnh loạn, chưa hiện xong đã mất" -> về Gemini.
#                                        thử câu 30 lopxe: 6 nhịp / 7 ảnh / chuyển động đa dạng so với Gemini Flash 3 / 3.
#                                        "" = Gemini (common.hoi_llm) như cũ; DeepSeek hỏng thì tự lùi về Gemini


AI_THIET_KE = ""                       # 05/11 user (so 5 cảnh đầu: Gemini thiết kế gọn, rõ, đúng lời; DeepSeek viết code ổn định
AI_CODE = "deepseek"                   # 5/5 qua bộ đo, Gemini 3/5): "Gemini thiết kế" + DeepSeek viết code. "" = Gemini


# 05/11 user: "việc viết code bắt buộc phải là deepseek vì 1 số cảnh do gemini viết code nó lủng lủng" -> khâu code KHÔNG
# lùi về Gemini: DeepSeek chưa trả lời thì hỏi lại (hồ sơ khác), mọi hồ sơ DeepSeek hỏng thì chờ chúng hồi; hết cách thì
# cảnh báo lỗi (lượt dựng giữ cảnh cũ), không để Gemini viết.
CODE_CHI_DEEPSEEK = True
CHO_DU_ANH = True              # 05/11 user: thiếu ảnh -> hàng chờ, KHÔNG mượn ảnh cảnh khác
VONG_CHO_ANH = 3               # số vòng vẽ bù trong một lượt dựng
CHO_FLOW_RANH = 25 * 60        # mỗi vòng chờ tối đa chừng này cho có hồ sơ Flow hết nghỉ
DS_HOI_LAI = 3                 # số lượt hỏi lại DeepSeek khi không trả lời
DS_CHO_HOI = 35 * 60           # mọi hồ sơ DeepSeek đang bị gác (30 phút): chờ tối đa chừng này
DS_GIO_CODE = 600              # giây chờ DeepThink trả lời một câu viết code (nghĩ lâu với cảnh nhiều ảnh)


def _hoi_deepseek_bat_buoc(prompt, timeout):
    import deepseek_chrome
    han = time.time() + DS_CHO_HOI
    lan = 0
    while True:
        if deepseek_chrome.co():
            lan += 1
            try:
                t = deepseek_chrome.hoi(prompt, timeout=max(timeout, DS_GIO_CODE))
            except Exception as e:                                       # noqa: BLE001
                log(f"    (DeepSeek lỗi: {str(e)[:100]})")
                t = ""
            if t:
                return t
            if lan >= DS_HOI_LAI:
                raise RuntimeError(f"DeepSeek không trả lời sau {lan} lượt hỏi (không để Gemini viết code)")
            log(f"    (DeepSeek chưa trả lời — hỏi lại DeepSeek, lượt {lan + 1}/{DS_HOI_LAI})")
            continue
        if time.time() > han:
            raise RuntimeError("không hồ sơ DeepSeek nào dùng được (không để Gemini viết code)")
        log("    (mọi hồ sơ DeepSeek đang bị gác — chờ 60 s rồi thử lại, không lùi về Gemini)")
        time.sleep(60)


def _hoi_ai(prompt, timeout=420, vai=None):
    """Câu hỏi cảnh -> câu trả lời. vai 'thiet_ke' (thiết kế + tự soát) / 'code' (viết + sửa code) chọn AI riêng
    (AI_THIET_KE / AI_CODE); không vai thì AI_CANH. DeepSeek không được thì lùi về Gemini."""
    ai_ = {"thiet_ke": AI_THIET_KE, "code": AI_CODE}.get(vai, AI_CANH)
    if ai_ == "chatgpt":                                                # 05/11: ChatGPT thiết kế (không được thì Gemini)
        try:
            import chatgpt_chrome
            t = chatgpt_chrome.hoi(prompt, timeout=timeout)
            if t:
                return t
            log("    (ChatGPT không trả lời — hỏi Gemini)")
        except Exception as e:                                           # noqa: BLE001
            log(f"    (ChatGPT lỗi: {str(e)[:100]} — hỏi Gemini)")
        return hoi_llm(prompt, timeout=timeout)
    if ai_ == "deepseek" and vai == "code" and CODE_CHI_DEEPSEEK:
        return _hoi_deepseek_bat_buoc(prompt, timeout)
    if ai_ == "deepseek":
        try:
            import deepseek_chrome
            if deepseek_chrome.co():
                t = deepseek_chrome.hoi(prompt, timeout=timeout)
                if t:
                    return t
                log("    (DeepSeek không trả lời — hỏi Gemini)")
        except Exception as e:                                           # noqa: BLE001
            log(f"    (DeepSeek lỗi: {str(e)[:100]} — hỏi Gemini)")
    return hoi_llm(prompt, timeout=timeout)


def _cau_ke_hoach(du_an):
    """04/11 (lopxe: 📝 đánh số theo kich_ban_cau.srt 121 câu, Remotion theo nhan_y._cau 124 câu -> từ câu 14 tích câu này
    dựng câu khác): câu ĐÚNG số + giờ của danh sách 📝 (cho_phu.doc_cau), giờ từng chữ lấy từ nhan_y._cau theo thời gian.
    Không có kich_ban_cau.srt thì dùng nhan_y._cau như cũ. -> [{i, t0, t1, text, tu: [(chữ, bd, kt)]}]"""
    goc = nhan_y._cau(du_an)                                             # noqa: SLF001
    try:
        import cho_phu
        kc = cho_phu.doc_cau(thu_muc_du_an(du_an)[1])
    except Exception:                                                    # noqa: BLE001
        kc = []
    if not kc:
        return goc
    tu = sorted((a, w, b) for c in goc for w, a, b in c.get("tu") or [])
    ra = []
    for c in kc:
        t0, t1 = float(c["t0"]), float(c["t1"])
        ra.append({"i": int(c["i"]), "t0": t0, "t1": t1, "text": c["text"],
                   "tu": [(w, a, b) for a, w, b in tu if t0 - 0.08 <= a < t1 - 0.02]})
    return ra


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
    cau = _cau_ke_hoach(du_an)                                           # noqa: SLF001
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
thing before the narration names it; the biggest visual change lands on the most important words; no shaking; make it
cinematic and specific to THIS sentence, not generic.
PHOTO-DRIVEN (04/11 the user's review of earlier shots: hand-drawn vector cracks / plants / water looked ugly, the subject
vanished mid-shot, wrong pictures):
  - Every REAL thing (animal, person, plant, water, soil, crack, gully, building, vehicle, object) is shown ONLY with an
    image you order below. Code draws only text, arrows, rings, map lines, number counters, simple charts.
  - One image per beat: when the narration names a new thing, the picture changes to (or adds) an image OF THAT THING.
    The subject the sentence is about is on screen from the first to the last frame. Each image prompt must show exactly
    what its beat says (e.g. "a natural sponge of soil holding water" -> a macro photo of dark spongy topsoil soaked with
    water, not a field or a forest).
  - 2D: layered photos (background + cut-outs in front, parallax), close-ups, split screens, photo cards. Use 3D only for a
    very simple object; never "3D geology / 3D landscape" animations.
VISUAL EFFECTS — the shot must clearly MOVE the whole time (frames 1 s apart must look different), with effects tied to
words: slow continuous motion on every photo (pan, tilt, drift, pull-back or push — vary it, not always a zoom-in); parallax between layers; on the key word a fast punch-in (scale +10-15% in 6-8
frames, eased) or a whip-pan / slide to the next image; reveals with wipes, masks, a light sweep across the photo, a
before/after split, a quick light flash (2-3 frames, white overlay at most 60% opacity) on an impact word; counters that count up; arrows / rings that
draw on. At least one effect every ~1.5 s. No shaking, no jitter, no wobbling stickers, no freeze.
TEXT — keep the screen almost free of text (04/11 the user: "quá nhiều chữ"): by DEFAULT NO TEXT AT ALL. Only when the
sentence states a number, a year / date or a proper name the viewer must remember, show ONE short text (max 4 words,
e.g. "1.500.000 con bò", "1895", "Tucson"), numbers as digits, Vietnamese. No labels, no titles, no captions, no
explanations, never words that repeat the narration. Let the pictures and motion tell it.
BEATS — the action must follow the voice exactly (04/11 the user: "chưa khớp hành động"): split the sentence into beats
(one per change of meaning — see THINK LIKE A DIRECTOR).
A beat starts at the moment its words are spoken and shows EXACTLY what those words say (the picture of the thing named,
a move / zoom to it, its action happening, a counter for its number, an arrow / ring onto it). Nothing changes between
beats except slow continuous motion; nothing appears before its words. For each beat give "cum" = 1-4 words copied
EXACTLY from the sentence where the beat starts, and "hien" = what appears / changes then (which image, which effect).
Every change is its OWN beat in "nhip" (never "at 'X' cut to…" inside another beat's "hien") — the editor computes the exact
frame of each beat from its "cum". Order at least one image for every beat that shows a new thing.
THINK LIKE A DIRECTOR, NOT A WORD-BY-WORD ILLUSTRATOR (05/11 the user: "truyền tải nội dung 1 cách thông minh thay vì cứ
khư khư khớp từng tí 1"; also "không cố định — mỗi câu cần thể hiện những gì để khán giả xem hiểu được vấn đề"):
  1. First write "y_tuong": ONE clear visual idea for the whole shot — how a viewer with the sound OFF would still get the
     point (a metaphor, a cause next to its effect, a before / after, a number made visible, a place on a map, a process as
     its steps...). Then "y_hieu": the 1-4 ideas the viewer must understand.
  2. Build the shot around that idea. A beat changes only when the MEANING changes — not for every noun. Each beat is held
     long enough to be read (~2.5 s or more), so the shot feels calm and confident, never flashing ("cảnh loạn, chưa hiện
     xong đã mất").
  3. Compose in DEPTH, freely: decide for each beat what is in the background, what sits in front of it (a cut-out, an inset
     close-up, a photo card, a map, a diagram, a counter, an arrow / ring onto the exact thing...), and how they move. You
     are free to invent the treatment — just do not make a flat slideshow of full-frame photos that only zoom; use layers
     where they help understanding. At most one plain slow push per shot.
  Examples of shots the user liked (for the LEVEL of storytelling, not to copy):
   - "Trang trại King Anvil được thành lập năm 1895, rộng hơn cả thủ đô Washington": sepia top-down photo of the 1895 ranch
     with a light sweep → the year 1895 appears → slide to a satellite map, the ranch area circled in red → split with a
     Washington DC map drawn to the same scale so the comparison is obvious.
   - "Giải pháp duy nhất là dựng các đập bê tông… chi phí 70.000 USD vượt ngân sách": a blueprint pushes in → the concrete
     dam wipes up from below with muddy flood water in front → a cost counter climbs to $70,000 and turns red as it passes the
     budget → the rancher, small and alone, looks at it.
   - "Rãnh xói sâu hoắm chạy cắt ngang trang trại": wide ranch photo with the ranch sign in front → punch-in on the ground as a
     red line draws along the gully → the farmhouse cut-out appears beside it so the scale is clear.
Decide whether it is 2D (layered photos, cut-outs, graphics) or 3D (only a simple real 3D object).
Never ask the image generator to draw the face of a real, named person.{that}
Also list the still images the AI image generator must draw for it (photorealistic, no text in images) — one for every
idea that needs its own picture (usually 2-6):
  "nen" = full 16:9 background or scene photo; "tach" = ONE object / person drawn alone on white (we cut it out);
  "can" = an extreme close-up 16:9 photo of a detail, seen straight-on and centered.
SOUND DESIGN: 3-5 sound effects, each tied to words of the sentence, "loai" one of: {sfx_loai}. Use: a whoosh
("luot-qua" / "chuyen-canh") on each picture change or slide, a hit ("dap-dau" / "va-cham-lon", "chot": true) on the key
word, a matching real sound where the narration has one (water, wind, animals, footsteps, machines, paper, fire...),
"ui-click" / "dong-ho" under counters, "lap-lanh" / "pop" on reveals. Only ONE "chot": true per shot.
Return ONLY JSON: {{"y_tuong": "<Vietnamese: the one visual idea of the shot>",
"y_hieu": ["<Vietnamese: each idea the viewer must understand>"], "kieu": "2d"|"3d",
"mo_ta": "<the shot, beat by beat, which words trigger what, and which LAYERS are on screen>",
"nhip": [{{"cum": "<1-4 words copied from the sentence>", "y": "<which idea of y_hieu>",
  "hien": "<what appears / changes>", "lop": "<background / front layers / graphics on screen during this beat>"}}],
"anh": [{{"ten": "<short_key>", "loai": "nen"|"tach"|"can", "ve": "<English prompt>"}}],
"am": [{{"cum": "<1-4 words copied from the sentence>", "loai": "...", "chot": true|false}}]}}"""


# 05/11 user: thử ChatGPT thiết kế ("nó phân tích kĩ … dạy nó cách giữ lại điểm đặc trưng để không bị quá nhanh"; "bảo nó
# đừng trả lời dài quá, đủ phân tích để dựng remotion thôi"). So 3 cảnh: ChatGPT hiểu ý câu sâu hơn nhưng chia 11-18 nhịp
# / 14 s và ít ảnh tách -> lời dặn riêng + đo nhịp trước khi vẽ ảnh (không tốn Flow).
_THEM_CHATGPT = """
KEEP THE ANSWER SHORT: only the JSON. Vietnamese fields brief — "y_tuong" 1-2 sentences, "mo_ta" at most 5 sentences, each
"hien" / "lop" one sentence. Enough analysis for the editor to build the shot, no essay.
PACING FOR THE VIEWER'S EYE (the user: "quá nhanh khiến người xem không nhìn thấy gì"): a viewer needs about 2 seconds to
recognise a NEW picture. So:
  - each idea gets ONE main picture that stays on screen at least ~2.5 s; never change the main picture faster than that;
  - smaller moments inside the same idea are LAYERS on that same picture (a ring or arrow onto the detail, a punch-in on it,
    a counter, an inset close-up sliding in) — they are part of the beat, not new beats;
  - keep the subject of the sentence recognisable through the whole shot so the eye always has something to hold on to;
  - this shot is {giay:.1f} s: use at most {toi_da} beats in "nhip".
LAYERS: the main background should have at least one thing in FRONT of it during most of the shot — a cut-out ("tach")
or an inset close-up ("can"), a map, a diagram or a counter. Order those images."""

THIET_KE_DO_NHIP = True                # đo nhịp bản thiết kế ChatGPT, quá dày / không có lớp -> trả lại sửa (tối đa 2 lượt)


def _toi_da_nhip(giay):
    return max(2, round(giay / 1.6))


def _kiem_nhip_tk(tk, tu, giay):
    """'' | lỗi: bản thiết kế quá nhiều nhịp / nhịp quá sát nhau (theo giờ giọng đọc) / không có ảnh đặt phía trước."""
    k = [f for f, _, _ in _khung_nhip(tk, tu)]
    n = len(tk.get("nhip") or [])
    loi = []
    if n > _toi_da_nhip(giay):
        loi.append(f"{n} beats in a {giay:.1f} s shot is too fast for the eye — merge them into at most {_toi_da_nhip(giay)} "
                   "beats (smaller moments become layers on the same picture)")
    sat = [(a, b) for a, b in zip(k, k[1:]) if b - a < 36]
    if sat:
        loi.append(f"{len(sat)} beats start less than 1.2 s after the previous one (e.g. at {sat[0][0] / 30:.1f} s and "
                   f"{sat[0][1] / 30:.1f} s) — the viewer cannot see them; merge them")
    loai = {str(a.get("loai")) for a in tk.get("anh") or [] if isinstance(a, dict)}
    if not loai & {"tach", "can"}:
        loi.append("only full-frame background photos — order at least one cut-out ('tach') or close-up ('can') to put in "
                   "front of the background")
    return "; ".join(loi)


# 05/11 user: "1 số cảnh nó làm rất tốt nhưng 1 số cảnh thì hơi chán" + sợ "rập khuôn" -> CÁCH A: Gemini nghĩ 3 phương án
# theo 3 HƯỚNG KHÁC NHAU (song song), ChatGPT làm giám khảo (sở trường phân tích) chấm theo nguyên tắc — không theo mẫu —
# và trừ điểm phương án giống cách thể hiện của các cảnh ngay trước (cả bài đổi nhịp, không lặp). Chỉ tốn hỏi chữ.
THIET_KE_3_HUONG = True
_HUONG = [
    "Tell it mainly through a VISUAL METAPHOR or a striking image that makes the idea felt.",
    "Tell it mainly through a COMPARISON made visible — before / after, side by side, a scale or a number the eye can see.",
    "Tell it mainly as a PROCESS or CAUSE → EFFECT unfolding on one main picture, step by step with the words.",
]
_THEM_HUONG = """
DIRECTION FOR THIS VERSION: {huong} If this direction truly cannot fit the sentence, pick another strong direction — but
make it clearly different from a plain slow push over background photos."""

_HOI_CHON = """You are the director of a documentary YouTube channel choosing ONE shot plan for this narration sentence.
Sentence (Vietnamese, {giay:.1f} s): «{cau}»
How the PREVIOUS shots of the video were told (do not repeat their treatment — the video must keep changing):
{truoc}
Candidate plans (JSON):
{ung}
Judge each by these PRINCIPLES (not by any template):
  1. Sound off, would a viewer still understand the point of this sentence?
  2. Is there one clear idea with a moment of surprise / impact exactly on the key words?
  3. Depth: is there something in front of the background (cut-out, inset, map, diagram, counter), not a flat slideshow?
  4. Calm pacing: each picture stays long enough to be seen (~2.5 s), not flashing.
  5. Faithful: right things, right era, nothing shown before it is named, no invented numbers / dates.
  6. FRESH: clearly different from the previous shots' treatments listed above (another device, another kind of motion).
Return ONLY JSON: {{"diem": [<score 0-10 for each candidate in order>], "chon": <index of the best, 0-based>,
"ly_do": "<Vietnamese, one sentence: why it wins>"}}"""


def _cach_ke(tk):
    """Tóm cách thể hiện của một thiết kế (cho giám khảo so độ 'khác')."""
    tk = tk or {}
    loai = ", ".join(sorted({str(a.get("loai")) for a in tk.get("anh") or [] if isinstance(a, dict)}))
    return f"{str(tk.get('y_tuong') or tk.get('mo_ta') or '')[:220]} [ảnh: {loai}; {len(tk.get('nhip') or [])} nhịp]"


def _thiet_ke_3_huong(hoi_tk, text, giay, truoc_tk, bao):
    """3 phương án song song (Gemini) -> giám khảo (ChatGPT, không được thì Gemini) chọn. -> thiết kế | {}"""
    from concurrent.futures import ThreadPoolExecutor

    def mot(h):
        for _ in range(2):
            tk = rut_json(_hoi_ai(hoi_tk + _THEM_HUONG.format(huong=h), timeout=420, vai="thiet_ke")) or {}
            if isinstance(tk, dict) and tk.get("mo_ta"):
                return tk
        return None
    with ThreadPoolExecutor(3) as ex:
        ung = [t for t in ex.map(mot, _HUONG) if t]
    if len(ung) <= 1:
        return ung[0] if ung else {}
    truoc = "\n".join(f"  - {_cach_ke(t)}" for t in truoc_tk if t) or "  (this is the first shot)"
    hoi = _HOI_CHON.format(giay=giay, cau=text, truoc=truoc,
                           ung="\n".join(f"[{k}] {json.dumps({x: t.get(x) for x in ('y_tuong', 'mo_ta', 'nhip', 'anh')}, ensure_ascii=False)[:3500]}"
                                         for k, t in enumerate(ung)))
    kq = {}
    try:
        import chatgpt_chrome
        kq = rut_json(chatgpt_chrome.hoi(hoi, timeout=300)) or {}
    except Exception as e:                                               # noqa: BLE001
        log(f"    (giám khảo ChatGPT lỗi: {str(e)[:80]})")
    if not isinstance(kq, dict) or "chon" not in kq:
        kq = rut_json(hoi_llm(hoi, timeout=300)) or {}
    try:
        k = max(0, min(len(ung) - 1, int(kq.get("chon"))))
    except (TypeError, ValueError):
        k = 0
    bao(f"3 phương án, điểm {kq.get('diem')} — chọn số {k + 1}: {str(kq.get('ly_do') or '')[:120]}")
    tk = dict(ung[k])
    tk["_phuong_an"] = [{"y_tuong": t.get("y_tuong"), "huong": i} for i, t in enumerate(ung)]
    tk["_chon"] = {"k": k, "diem": kq.get("diem"), "ly_do": kq.get("ly_do")}
    return tk


TU_SOAT = True                         # 05/11 user: AI tự soát bản thiết kế (chỉ bằng chữ) trước khi viết code
_HOI_SOAT = """You are the film editor reviewing a motion designer's plan for ONE documentary shot before it is built.
Narration sentence (Vietnamese, {giay:.1f} s): «{cau}»
The plan (JSON): {tk}
Check it honestly against what the user asked for:
  1. Does "y_tuong" make the POINT of the sentence clear to a viewer with the sound off — told smartly, not by
     illustrating every word?
  2. Is it composed in depth (background + something in front / an inset / a map / a diagram / a counter / an arrow onto the
     exact thing) where that helps understanding — or is it a flat slideshow of full-frame photos that only zoom?
  3. Does any picture come back later or get shown twice? (it must not)
  4. Is there more than ONE on-screen text (numbers / years / proper names excepted)? Any label or caption repeating the
     narration? (there must not be)
  5. Is it calm: each beat held ~2.5 s or more, no flashing changes?
  6. Is every real thing shown with an ordered image, and does every image prompt show exactly its beat?
If it already passes all six, return {{"ok": true}}. Otherwise return the FULL improved plan in the same JSON format
(same keys: y_tuong, y_hieu, kieu, mo_ta, nhip, anh, am), keeping what was good and fixing what was not. Only JSON."""


def _soat_thiet_ke(tk, cau, giay, bao):
    """Một lượt soát bằng chữ (không dựng thử): đạt -> giữ; chưa -> dùng bản AI sửa (đủ khoá) -> thiết kế."""
    bao("AI tự soát bản thiết kế…")
    r = rut_json(_hoi_ai(_HOI_SOAT.format(giay=giay, cau=cau, tk=json.dumps(tk, ensure_ascii=False)), timeout=420, vai="thiet_ke")) or {}
    if isinstance(r, dict) and r.get("mo_ta") and r.get("nhip") and r.get("anh"):
        bao("tự soát: đã sửa lại thiết kế")
        return r | {"_da_soat": True}
    bao("tự soát: thiết kế đạt" if isinstance(r, dict) and r.get("ok") else "tự soát: không trả lời — giữ bản đầu")
    return tk | {"_da_soat": True}


def _ve_anh(a, du_an):
    """Một ảnh trong danh sách thiết kế -> {ten, loai, file (đường public), rong, cao} | None."""
    from PIL import Image
    loai, ve = a.get("loai"), str(a.get("ve") or "")
    if not ve:                                                           # 04/11 lopxe câu 116: AI ghi câu lệnh vào "nen" / "prompt"
        ve = next((str(x) for k, x in a.items() if k not in ("ten", "loai") and isinstance(x, str) and len(x) > 25), "")
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


_THAT_TK = """
REAL PEOPLE / EVENTS in this sentence. The user saved REAL photos of them; the code step receives these photos as images of
type "that". Whenever one of them is shown, show it ONLY through its real photo (a framed portrait, a photo card that slides
in, a full-frame photo with slow push, a split screen...), never as a drawing. Drawn images ("anh") may show the setting,
objects or crowds far away, never these people:
{ds}"""

_TAI_HIEN_TK = """
REAL PEOPLE / EVENTS in this sentence WITHOUT any real photo. Be historically exact (era, place, clothing, weapons,
vehicles, buildings of that time) and recreate them: a period-correct reenactment or historical-painting style scene,
a map of where it happened (area circled, route drawn), the year / date big on screen, a timeline, real numbers counting
up, or a key object of the event in close-up (weapon, flag, letter, newspaper of the time). Never draw the face of these
people: silhouettes, from behind, hands, or far away; or show their name and years over a period background:
{ds}"""


FLOW_TOI_DA = 4                        # 04/11 (lopxe: 9 cảnh × 3-7 ảnh cùng lúc -> Flow chặn 'unusual activity' gần hết tài
#                                        khoản, nghỉ 60 phút): số ảnh vẽ CÙNG LÚC trên Flow trong cả lượt dựng
FLOW_THU_LAI = 2                       # ảnh hỏng vẽ lại thêm bấy nhiêu lần (cách nhau FLOW_CHO_LAI giây)
FLOW_CHO_LAI = 45
_FLOW_KHOA = __import__("threading").BoundedSemaphore(FLOW_TOI_DA)


def _ve_ca_canh(ds, du_an, bao):
    """Vẽ các ảnh của một cảnh: song song tối đa 3 ảnh nhưng cả lượt không quá FLOW_TOI_DA ảnh cùng lúc trên Flow; ảnh hỏng
    vẽ lại FLOW_THU_LAI lần. -> [ảnh vẽ được] (giữ thứ tự)."""
    from concurrent.futures import ThreadPoolExecutor

    def mot(a):
        for lan in range(FLOW_THU_LAI + 1):
            if lan:
                bao(f"vẽ lại ảnh '{a.get('ten')}' (lần {lan + 1})…")
                time.sleep(FLOW_CHO_LAI * lan)
            else:
                bao(f"vẽ ảnh '{a.get('ten')}' ({a.get('loai')})…")
            with _FLOW_KHOA:
                try:
                    r = _ve_anh(a, du_an)
                except Exception as e:                                   # noqa: BLE001
                    log(f"    ! vẽ ảnh '{a.get('ten')}': {str(e)[:120]}")
                    r = None
            if r:
                return r
        bao(f"! không vẽ được ảnh '{a.get('ten')}' sau {FLOW_THU_LAI + 1} lần")
        return None
    if not ds:
        return []
    with ThreadPoolExecutor(min(3, len(ds))) as ex:
        return [r for r in ex.map(mot, ds) if r]


def _viet_lai_tach(a, cau):
    """Câu lệnh ảnh tách vẽ mãi không tách được -> câu lệnh mới: MỘT vật / cụm gọn, nằm trọn trong khung, nền trắng. | ''"""
    hoi = ("An image generator keeps failing to draw this as an ISOLATED cut-out on white (it fills the whole frame with a scene "
           f"instead). Narration of the shot (Vietnamese): «{cau}». Image key: {a.get('ten')}. Failing prompt: «{a.get('ve')}».\n"
           "Rewrite it so it shows the SAME idea as ONE solid object or ONE tight group touching each other (e.g. a compact heap, a "
           "single item mid-action), small enough to sit fully inside the frame with wide empty pure-white margins on every side, "
           "no ground, no scene, no shadow, photorealistic. Return ONLY the new English prompt, one sentence.")
    try:
        t = (hoi_llm(hoi, timeout=180) or "").strip().strip('"«»` ')
    except Exception:                                                    # noqa: BLE001
        return ""
    return t.splitlines()[0][:400] if len(t) > 25 else ""


def _muon_anh(du_an, cau, thieu):
    """Ảnh không vẽ được -> mượn ảnh CÙNG LOẠI của cảnh gần nhất (trước / sau, trong 4 câu) — cùng đoạn lời nên cùng bối cảnh.
    Ảnh mượn mang tên ảnh thiếu (code AI dùng như ảnh của mình), đánh dấu muon để lần sau vẽ lại."""
    ds = doc_json(_ds(du_an), {}) or {}
    gan = sorted((abs(int(k) - cau), int(k)) for k, v in ds.items() if k.isdigit() and int(k) != cau and abs(int(k) - cau) <= 4
                 and v.get("anh"))
    ra, dung = [], set()
    for a in thieu:
        for _, k in gan:
            x = next((b for b in ds[str(k)]["anh"] if b.get("loai") == a.get("loai") and b.get("file") not in dung
                      and os.path.isfile(os.path.join(nhan_y.PUB, b.get("file") or ""))), None)
            if x:
                dung.add(x["file"])
                ra.append(dict(x, ten=a.get("ten"), muon=True))
                break
    return ra


def _anh_that(du_an, text):
    """04/11 user: nhân vật / sự kiện lịch sử thật mà câu nhắc + ảnh thật user lưu (🏛 lich_su) -> (mô tả cho thiết kế,
    [{ten, loai: 'that', file, rong, cao}], khoá các mục). Ảnh làm nét tại máy rồi chép vào remotion/public/nhan_y/."""
    from PIL import Image
    try:
        import lich_su
        ds = lich_su.nhac_trong(du_an, text)
    except Exception as e:                                               # noqa: BLE001
        log(f"  ! [nhấn ý AI] đọc 🏛 lịch sử: {str(e)[:100]}")
        return "", [], []
    anh = []
    for x in ds:
        for n, f in enumerate(x["anh"][:3]):
            ten_f = f"that_{nhan_y._md5('that', f, os.path.getmtime(f))}.jpg"   # noqa: SLF001
            dich = os.path.join(nhan_y.PUB, nhan_y.THU_PUB, ten_f)
            try:
                rong, cao = lich_su.lam_net(f, dich) if not os.path.isfile(dich) else Image.open(dich).size
            except Exception as e:                                       # noqa: BLE001
                log(f"  ! [nhấn ý AI] ảnh thật {f}: {str(e)[:80]}")
                continue
            anh.append({"ten": f"{x['ten']} {n + 1}".strip(), "loai": "that", "file": f"{nhan_y.THU_PUB}/{ten_f}",
                        "rong": rong, "cao": cao, "khoa": x["khoa"]})
    co = {a["khoa"] for a in anh}
    dong = lambda x: f"  - {x['ten']} ({x['ten_goc']}{', ' + x['thoi_ky'] if x['thoi_ky'] else ''}): {x['mo_ta']}"   # noqa: E731
    mo = "\n".join(dong(x) for x in ds if x["khoa"] in co)
    # 04/11 user ("sự kiện có mà không tìm được ảnh thì sao"): mục chưa có ảnh vẫn báo AI để tái hiện đúng thời kỳ
    tai_hien = "\n".join(dong(x) for x in ds if x["khoa"] not in co)
    khoa = sorted(co) + sorted("~" + x["khoa"] for x in ds if x["khoa"] not in co)   # đổi -> thiết kế lại cảnh
    return (_THAT_TK.format(ds=mo) if mo else "") + (_TAI_HIEN_TK.format(ds=tai_hien) if tai_hien else ""), anh, khoa


# --- bước 3c: AI viết code ------------------------------------------------------------------------------------------------
_HOI_CODE = """Write the Remotion (React, JSX, Remotion 4) component for this shot. Design: {mo_ta}
Canvas 1920x1080, 30 fps, duration {khung} frames ({giay:.1f} s). Sentence: «{cau}».
Word timings (frame where each word starts): {tu}.
BEATS with their EXACT start frames (computed from the recorded voice). Each beat's change (image in, zoom / slide to the
thing, counter start, arrow draw-on) MUST start at its frame (+-3 frames) — use these numbers literally in from={{…}} /
interpolate ranges; between beats only slow continuous motion:
{nhip}
Images you may use (paths for src(), already drawn; "tach" are transparent PNG cut-outs; "that" are REAL photos of the
named real person / event — use them whenever that person / event is shown, never draw them instead):
{anh}
Use ONLY these images, with the path EXACTLY as written (e.g. src('nhan_y/abc.jpg')): never add '/public', never call
staticFile yourself, never invent another file name, NEVER use any http(s) URL (internet images are blocked). Anything else must be drawn with HTML / SVG / CSS or 3D.
STRICT CONTRACT (the file is executed as-is):
- Start with these imports exactly (use only what you need from them):
  import React from 'react';
  import {{AbsoluteFill, Easing, Img, Interactive, interpolate, spring, random, useCurrentFrame, useVideoConfig}} from 'remotion';
  import {{z}} from 'zod';
  import {{src, kep, FONT, VANG, EM, AnhNen, AnhLia, ChuNoi, SoDem, Nhan, VongBut, MuiTen, HienDan}} from './thu_vien.jsx';
  For 3D also: import {{ThreeCanvas}} from '@remotion/three'; import * as THREE from 'three';
- Library (local frame 0 = when its block appears): AnhNen({{anh, tu, den, goc, toi}}) full-frame photo with slow push —
  tu / den are ZOOM SCALES from / to (e.g. tu={{1}} den={{1.08}}), NOT frames; goc is a CSS origin string like '50% 40%';
  toi 0..0.5 darkens. To show it only for part of the shot, wrap it in an Interactive.Div with from / durationInFrames;
  AnhLia({{anh, huong, quang, phong, toi}}) full-frame photo PANNING ('trai' | 'phai' | 'len' | 'xuong', quang = px); a pull-back
  is AnhNen with tu={{1.15}} den={{1}}. Vary them — not every photo a zoom-in;
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
- NEVER show the narration sentence as a subtitle / caption / karaoke text. On-screen text: NONE, unless the design
  has its one short key text (a number / year / name, at most 4 words). No labels, titles or captions.
- NEVER draw a real thing (plant, water, soil, crack, gully, rock, building, animal, person, vehicle) with SVG paths, CSS
  shapes or strokes — show it only with the given images. SVG / CSS only for text, arrows, rings, map lines, counters.
- The subject of the sentence is on screen the WHOLE shot; when one image's block ends the next one has already started
  (no empty gap, no empty board, no "?" placeholder).
- Never wrap an Interactive.Div in a frame condition like {{frame >= 82 && (…)}} — its from / durationInFrames already
  decide when it shows (the user edits those numbers by hand; a condition around it would ignore the edit).
- EACH PICTURE ONCE, TO THE END: a picture is mounted in ONE Interactive.Div only (if several beats keep the same
  picture, that one block spans them all — re-mounting it restarts its zoom). Never go back to an earlier picture; the last
  beat's picture stays until the final frame of the shot (no old image showing again, no effect restarting at the end).
- MOTION: something clearly moves the whole time (every photo slowly pushes / pans, layers move at different speeds) and
  each beat of the design has its effect (punch-in, slide, wipe, light sweep, flash cut, draw-on) at the frame of its word.
  Two frames 1 s apart must never look the same.
- The frame must be FULL the whole time: a full-frame background photo (AnhNen with one of the "nen" / "can" / "that" images,
  or a full 3D scene) covers the frame from the first to the last frame. No flat-colour or dark empty backgrounds, no
  black frames, no fading to black (the editor fades the clip).
- Make things BIG: the main subject fills at least about 40% of the frame height; key text font size >= 90 px,
  labels >= 56 px. Few large elements, not many tiny ones. If a cut-out is used it must be at least 500 px tall/wide.
- No decorative glows, blobs, particles or lens flares that do not mean anything in the narration.
- The background photo must stay SHARP and recognisable: never put CSS blur on it or on a full-frame layer (at most
  blur(4px) on a small far element); never cover it with a dark layer above 50% opacity.
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


_DUOI_TEP = r"\.(?:jpe?g|png|webp|gif|svg|mp3|wav|mp4|webm|ttf|otf|woff2?)"


def _pub_nho(ma, chu):
    """Thư mục public NHỎ cho một lần dựng: chỉ các tệp mà code + thông số nhắc tới (đường tương đối trong remotion/public),
    liên kết cứng (không chép; khác ổ thì chép). -> đường thư mục."""
    import shutil
    d = os.path.join(CACHE_CHUNG, "nhan_y", "pub_tam", f"{ma}_{os.getpid()}_{time.time_ns() % 10 ** 9}")
    os.makedirs(d, exist_ok=True)
    for f in set(re.findall(r"[\w\-./]+" + _DUOI_TEP, chu or "", re.I)):
        f = re.sub(r"^/?(public/)?", "", f)
        nguon, dich = os.path.join(nhan_y.PUB, f), os.path.join(d, f)
        if not os.path.isfile(nguon) or os.path.exists(dich):
            continue
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        try:
            os.link(nguon, dich)
        except OSError:
            shutil.copy2(nguon, dich)
    return d


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
    pub = _pub_nho(ma, open(os.path.join(THU_AI, mod or ma + ".jsx"), encoding="utf-8").read() + json.dumps(props, ensure_ascii=False))
    try:
        for k in khung_thu:
            out = os.path.join(thu, f"{ma}_{k}.png")
            if os.path.isfile(out):
                os.remove(out)
        # 04/11 user ("tối ưu nhanh nhất"): MỘT lần đóng gói + MỘT trình duyệt cho mọi khung, public nhỏ (chỉ ảnh cảnh dùng)
        # — trước mỗi khung một `npx remotion still` chép cả public 4,1 GB (~20 s / khung)
        env = dict(os.environ)
        try:
            import do_hoa
            if do_hoa._chrome():                                         # noqa: SLF001
                env["BROWSER_EXE"] = do_hoa._chrome()                    # noqa: SLF001
        except Exception:                                                # noqa: BLE001
            pass
        r = subprocess.run(["node", "thu_khung.mjs", entry, pub, thu, ma, ",".join(str(k) for k in khung_thu)], cwd=REMOTION,
                           capture_output=True, timeout=900, env=env, creationflags=0x08000000 if os.name == "nt" else 0)
        t = (r.stdout or b"").decode("utf-8", "ignore") + (r.stderr or b"").decode("utf-8", "ignore")
        for k in khung_thu:
            out = os.path.join(thu, f"{ma}_{k}.png")
            if not os.path.isfile(out):
                dong = [x for x in t.replace("LOI ", "").splitlines() if x.strip() and "node_modules" not in x][-25:]
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
        import shutil
        shutil.rmtree(pub, ignore_errors=True)
    return "", ra


def _chu_dai(pr):
    """Chữ hiện trên hình dài quá 9 từ (phụ đề cả câu) -> lỗi để AI sửa. 03/11 user: AI tự chèn cả câu lời đọc."""
    for k, v in (pr or {}).items():
        if isinstance(v, str) and not re.search(r"\.(png|jpe?g|webp|wav|mp4)$", v, re.I) and not v.startswith(("#", "rgb")) \
                and len(v.split()) > 5:
            return (f"prop '{k}' shows a long text ({len(v.split())} words): on-screen text is at most ONE short text of "
                    "at most 4 words (a number / year / name) — shorten or remove it")
    chu = [k for k, v in (pr or {}).items() if isinstance(v, str) and re.search(r"[^\W\d_]", v)
           and not re.search(r"\.(png|jpe?g|webp|wav|mp4)$|^https?:|^#|^rgb|px$|^\d+(\.\d+)?%$|^(ease|linear|bold|center|left|right)", v, re.I)]
    if len(chu) > 2:                                                     # 04/11 user: "quá nhiều chữ"
        return (f"too many on-screen texts ({len(chu)}: {', '.join(chu[:5])}): keep at most ONE short text "
                "(number / year / name), remove the others — let the pictures tell it")
    return ""


def _chu_dai_code(code):
    """Như _chu_dai nhưng cho chữ viết thẳng trong code (chuỗi trong nháy hoặc chữ giữa thẻ JSX)."""
    # 04/11 (lopxe câu 38, 42 báo nhầm): chú thích // … và /* … */ không hiện lên hình
    code = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", code or "", flags=re.S)
    for m in re.finditer(r"'([^'\n]{30,})'|\"([^\"\n]{30,})\"|>([^<>{}\n]{30,})<", code):
        t = next(g for g in m.groups() if g)
        truoc = code[max(0, m.start() - 12):m.start()].rstrip()
        if truoc.endswith(("describe(", "name=", "name:", "name =")):
            continue                                                     # nhãn ô thông số / tên phần tử trong Studio, không hiện lên hình
        chu = sum(ch.isalpha() or ch.isspace() for ch in t) / max(1, len(t))
        if len(t.split()) > 5 and chu > 0.85 and not re.search(r"[{};=():]|px\b|rgba|import |from ", t):
            return f"the code shows a long text «{t[:60]}…» ({len(t.split())} words): never show the narration as a caption"
    return ""


DUYET_AGY = False                      # 03/11 user: Antigravity chấm khung hình + sửa code; 04/11 user tắt ("không cần thằng
#                                        antigravity chấm nữa") — user tự xem ở 🎞 Duyệt cảnh, góp ý cho AI sửa
AGY_TAC_NHAN = True                    # chưa đạt: Antigravity tự sửa + tự dựng thử (agy.tac_nhan_sua, quyền hẹp)
AGY_VONG = 2                           # 04/11 (thử lopxe): 4 vòng tự sửa ~15-25 phút/cảnh mà điểm tự chấm 10/10 lúc chấm lại
#                                        chỉ 3/10 -> vòng thêm ít ích; 2 vòng + một lượt Gemini sửa theo lỗi chấm lại (nhanh)
GEMINI_SUA_TIEP = False                # 04/11 thử lopxe lượt 2: Gemini sửa theo lời chấm 0/6 cảnh tăng điểm -> tắt


# 05/11 user ("hết câu rồi vẫn dùng lại ảnh nền cũ xong hiệu ứng zoom lại… thiếu chuyên nghiệp"; đo v2 lopxe: 38/97
# cảnh gắn lại cùng một ảnh ở khối sau -> zoom chạy lại / quay về ảnh cũ, 2 cảnh ảnh cuối hết trước cảnh)
_ANH_LOP = re.compile(r"<(AnhNen|AnhLia)\b[^>]*?\banh\s*=\s*\{([^}]*)\}|<Img\b[^>]*?\bsrc\s*=\s*\{\s*src\(([^)]*)\)\s*\}")


def _khoi_div(code):
    """[(đầu thẻ mở, cuối thẻ đóng, from, dur)] của mọi <Interactive.Div> (ghép cặp đóng / mở theo tầng)."""
    ra, ngan = [], []
    for m in re.finditer(r"<Interactive\.Div\b|</Interactive\.Div>", code):
        if m.group().startswith("</"):
            if ngan:
                a, f, d = ngan.pop()
                ra.append((a, m.end(), f, d))
            continue
        i, sau = m.end(), 0                                   # cuối thẻ mở (quét ngoặc)
        while i < len(code):
            if code[i] == "{":
                sau += 1
            elif code[i] == "}":
                sau -= 1
            elif code[i] == ">" and sau == 0:
                break
            i += 1
        the = code[m.start():i + 1]
        if the.rstrip(">").rstrip().endswith("/"):
            continue                                          # tự đóng, không chứa gì
        f = re.search(r"\bfrom\s*=\s*\{\s*(\d+)\s*\}", the)
        d = re.search(r"\bdurationInFrames\s*=\s*\{\s*(\d+)\s*\}", the)
        ngan.append((m.start(), int(f.group(1)) if f else None, int(d.group(1)) if d else None))
    return ra


def _kiem_lop(code, giay):
    """'' | lỗi: (1) cùng một ảnh nền dùng ở hai khối khác nhau = quay lại ảnh cũ; (2) khối ảnh nền cuối cùng hết trước khi
    cảnh hết (ảnh cũ bên dưới lộ ra / hiệu ứng chạy lại)."""
    body = code.split("export const Canh", 1)[-1]
    off = len(code) - len(body)
    khoi = _khoi_div(code)
    dung = {}
    het_anh = []
    tong = round(giay * 30)
    for m in _ANH_LOP.finditer(body):
        x = re.sub(r"\s+", "", (m.group(2) or m.group(3) or ""))
        if not x:
            continue
        vt = m.start() + off
        trong = [k for k in khoi if k[0] < vt < k[1]]
        k = min(trong, key=lambda k: k[1] - k[0]) if trong else None   # khối gần nhất chứa ảnh
        dung.setdefault(x, set()).add(k)
        if k and m.group(1) and k[2] is not None and k[3] is not None:
            # thời điểm tuyệt đối: cộng from của các khối cha
            cha = sum(c[2] or 0 for c in trong if c is not k)
            het_anh.append(cha + k[2] + k[3])
    lap = [x for x, ks in dung.items() if len(ks) > 1]
    if lap:
        return (f"the same picture {lap[0]} is mounted again in a later Interactive.Div — its zoom / effect RESTARTS or the shot "
                "goes BACK to an earlier image (the user: 'hết câu rồi vẫn dùng lại ảnh nền cũ, hiệu ứng zoom lại, thiếu chuyên "
                "nghiệp'). Show each picture in ONE block only: if several beats use it, make that one block span all of them; "
                "never return to an earlier picture; the last beat's picture stays to the final frame")
    if het_anh and max(het_anh) < tong - 4:
        return (f"the last background picture ends at frame {max(het_anh)} but the shot lasts {tong} frames — the end "
                "shows an old picture / restarts an effect. Extend the last beat's picture to the final frame")
    return ""


PHU_LOP_TOI_THIEU = 0.3              # 05/11: cảnh có lớp trước ảnh nền ít hơn bấy nhiêu thời gian = phẳng (đo v2: 23/97 dưới 35%)

def _la_ten_rieng(t):
    """Tên riêng / địa danh: 1-3 từ viết hoa chữ đầu (Tucson, King Anvil, Washington DC); chữ IN HOA dài kiểu nhãn
    ("LỐP XE LỚP ĐÁY") không phải tên riêng (từ in hoa quá 4 chữ cái)."""
    w = t.split()
    if len(w) >= 2 and all(x.isupper() for x in w):                     # "ĐAI NHỰA": nhãn in hoa, không phải tên
        return False
    return 1 <= len(w) <= 3 and all(x[:1].isupper() and (len(x) <= 4 or not x.isupper()) for x in w)


def _chu_tren_hinh(code, pr):
    """Mọi chữ hiện trên hình (05/11 user: "chữ xuất hiện vẫn bị nhiều"): chữ giữa thẻ JSX, chu= của ChuNoi / Nhan,
    {props.x} giữa thẻ. Bỏ số liệu (không có chữ cái) và tên riêng (1-3 từ viết hoa). -> [chữ]"""
    code = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", code or "", flags=re.S)
    body = code.split("export const Canh", 1)[-1]
    pr = pr or {}
    ra = []

    def them(t):
        t = re.sub(r"\s+", " ", str(t or "")).strip()
        if (len(t) >= 4 and re.search(r"[^\W\d_]", t)                       # "km", "ha", "con": đơn vị đi kèm số, không tính and not re.search(r"[=&|;(){}?]|=>", t)
                and not _la_ten_rieng(t) and t not in ra):
            ra.append(t)
    for m in re.finditer(r">([^<>{}]+)<", body):
        them(m.group(1))
    for m in re.finditer(r">\s*\{\s*(?:props\.)?(\w+)\s*\}\s*<", body):
        if isinstance(pr.get(m.group(1)), str):
            them(pr[m.group(1)])
    for m in re.finditer(r"<(?:ChuNoi|Nhan)\b[^>]*?\bchu\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|\{\s*(?:props\.)?(\w+)\s*\})", body):
        them(m.group(1) or m.group(2) or (pr.get(m.group(3)) if isinstance(pr.get(m.group(3)), str) else ""))
    return ra


def _phu_lop(code, giay):
    """Tỉ lệ thời gian của cảnh có ít nhất một lớp KHÁC ảnh nền (ảnh tách, ảnh chèn, bản đồ, sơ đồ, số đếm, chữ…)."""
    body = code.split("export const Canh", 1)[-1]
    off = len(code) - len(body)
    khoi = _khoi_div(code)
    tong = max(1, round(giay * 30))
    co = [False] * tong
    for k in khoi:
        a, b, f, d = k
        if f is None or d is None or a < off:
            continue
        trong = code[a:b]
        con = [c for c in khoi if a < c[0] and c[1] <= b]                 # bỏ phần của khối con (khối con tự tính)
        rieng = trong
        for c in sorted(con, key=lambda c: -c[0]):
            rieng = rieng[:c[0] - a] + rieng[c[1] - a:]
        chi_nen = re.search(r"<(AnhNen|AnhLia)\b", rieng) and not re.search(
            r"<(Img|svg|ChuNoi|SoDem|Nhan|VongBut|MuiTen|ThreeCanvas)\b|>[^<>{}]*[^\W\d_\s][^<>{}]*<", rieng)
        if chi_nen or not re.search(r"<\w", rieng.split(">", 1)[-1]):
            continue
        cha = sum(c[2] or 0 for c in khoi if c[0] < a and b <= c[1])
        for i in range(max(0, cha + f), min(tong, cha + f + d)):
            co[i] = True
    return sum(co) / tong


def _kiem_chu_lop(code, pr, giay):
    """'' | lỗi: quá một chữ trên hình (trừ số / tên riêng), hoặc cảnh gần như chỉ có ảnh nền (phẳng)."""
    chu = _chu_tren_hinh(code, pr)
    if len(chu) > 1:
        return (f"too many on-screen texts ({len(chu)}: {' | '.join(chu[:4])}) — the user: 'chữ xuất hiện vẫn bị nhiều'. Keep at "
                "most ONE short text besides numbers / years / proper names; let the pictures tell the rest")
    p = _phu_lop(code, giay)
    if p < PHU_LOP_TOI_THIEU:
        return (f"only {p:.0%} of the shot has anything in front of the background photos — it is a flat slideshow (the user: "
                "'nhiều cảnh xếp lớp còn yếu, cần có lớp thể hiện'). Where it helps understanding, add something in front "
                "(a cut-out, an inset close-up, a photo card, a map, a diagram, a counter, an arrow / ring on the exact thing)")
    return ""


def _kiem(ma, code, pr, giay):
    """Ghi code + kiểm (chữ dài, dựng thử 6 khung, khung trống / tối). -> (lỗi, [(giây, png)])"""
    with open(os.path.join(THU_AI, f"{ma}.jsx"), "w", encoding="utf-8", newline="\n") as f:
        f.write(code + "\n")
    loi = _chu_dai(pr) or _chu_dai_code(code) or _kiem_lop(code, giay) or _kiem_chu_lop(code, pr, giay)
    if loi:
        return loi, []
    dau, cuoi = 0.6 * 30, (giay - 0.4) * 30                              # bỏ lúc cảnh đang mờ vào / mờ ra
    khung = [round(dau + (cuoi - dau) * k) for k in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
    loi, anh = _thu_dung(ma, pr, giay, khung)
    return loi, [(k / 30, a) for k, a in zip(khung, anh)]


def _khung_nhip(tk, tu):
    """04/11 user ("chưa khớp hành động"): nhịp thiết kế (cum = chữ chép từ câu) -> [(khung, cum, hien)] theo giờ chữ thật
    của giọng đọc; cụm không khớp nguyên văn thì lấy chữ đầu khớp, không khớp gì thì bỏ."""
    ds = [nhan_y._bo_dau(w) for w, _ in tu]                              # noqa: SLF001
    ra = []
    for x in tk.get("nhip") or []:
        if not isinstance(x, dict):
            continue
        can = nhan_y._bo_dau(str(x.get("cum") or "")).split()             # noqa: SLF001
        if not can:
            continue
        j = next((j for j in range(len(ds) - len(can) + 1) if ds[j:j + len(can)] == can), None)
        if j is None:
            j = next((j for j, w in enumerate(ds) if w == can[0]), None)
        if j is not None:
            ra.append((round(tu[j][1] * 30), str(x.get("cum")), str(x.get("hien") or "")[:200]))
    return sorted(ra)


def _sua_duong_anh(code, pr, mo_anh):
    """04/11 (lopxe: 5/7 cảnh lỗi vì AI tự đặt tên ảnh 'nen1.jpg', 'can1.jpg', 'dong_co_mua_he.jpg' -> 404): đường ảnh
    không có trong danh sách của cảnh -> thay bằng ảnh cùng loại (nen / can / tach đoán theo tên), không có thì ảnh đầu."""
    co = re.findall(r"'((?:nhan_y)/[^']+\.(?:jpe?g|png|webp))'", mo_anh or "")
    if not co:
        return code, pr
    loai = {}
    for dong in (mo_anh or "").splitlines():
        m = re.search(r"\((nen|tach|can|that)\b.*?'([^']+)'", dong)
        if m:
            loai.setdefault(m.group(1), []).append(m.group(2))

    # 04/11 (lopxe lượt full: Gemini sửa lỗi không có danh sách ảnh -> thay ảnh bằng link unsplash / example.com)
    def la_anh(f):
        return bool(re.search(r"\.(jpe?g|png|webp)(\?.*)?$", f, re.I) or re.match(r"https?://", f))

    def thay(f, goi_y=""):
        if f in co or not la_anh(f):
            return f
        t = (goi_y + " " + os.path.basename(f.split("?")[0])).lower()
        for k in (("tach", "png", "cut"), ("can", "close", "macro"), ("that", "real", "photo"), ("nen", "bg", "back")):
            if any(x in t for x in k) and loai.get(k[0]):
                return loai[k[0]][0]
        return (loai.get("nen") or co)[0]
    if code:
        code = re.sub(r"(['\"`])((?:/?public/)?(?:nhan_y/)?[\w\-./]+\.(?:jpe?g|png|webp))\1",
                      lambda m: m.group(1) + thay(re.sub(r"^/?public/", "", m.group(2))) + m.group(1), code)
        code = re.sub(r"(['\"`])(https?://[^'\"`\s]+)\1", lambda m: m.group(1) + thay(m.group(2)) + m.group(1), code)
    if isinstance(pr, dict):
        pr = {k: (thay(re.sub(r"^/?public/", "", v), k) if isinstance(v, str) and la_anh(v) else v) for k, v in pr.items()}
    return code, pr


def _viet_code(ma, hoi, props_mac, giay, bao, nc=None):
    """Hỏi AI viết code + vòng sửa lỗi + (nếu có) Antigravity nhìn khung hình chấm / sửa. -> (code, props) | (None, lỗi).
    nc: ngữ cảnh cho Antigravity {cau, y_chinh, mo_ta, anh}."""
    import agy
    nc = nc or {}
    dung_agy = DUYET_AGY and agy.co()
    os.makedirs(THU_AI, exist_ok=True)
    tl = _hoi_ai(hoi, timeout=420, vai="code")
    loi = ""
    thu = os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai")
    os.makedirs(thu, exist_ok=True)
    for lan in range(SUA_TOI_DA + 1):
        with open(os.path.join(thu, f"{ma}_tra_loi_{lan}.txt"), "w", encoding="utf-8") as f:   # để xem lại khi hỏng
            f.write(tl or "")
        code, pr = _tach_tra_loi(tl)
        code, pr = _sua_duong_anh(code, pr, nc.get("anh") or "")
        if not code:
            loi = "the answer has no ```jsx code block"
        elif "export const Canh" not in code or "export const schema" not in code:
            loi = "the code must contain `export const schema` and `export const Canh`"
        else:
            pr = props_mac | pr
            loi, khung = _kiem(ma, code, pr, giay)
            if not loi and KIEM_SO and nc.get("cau"):
                loi = _kiem_so(ma, pr, giay, nc, bao)
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
        tl = _hoi_ai(vai="code", prompt=_HOI_SUA.format(loi=loi, code=code or tl[:6000])
                     + (f"\nImages you may use — ONLY these, with src('<path>') exactly as written; NEVER any http(s) URL:\n{nc['anh']}"
                        if nc.get("anh") else ""), timeout=420)
    return None, loi


# 05/11 user: "1 số chỗ số liệu bị sai khi dựng remotion … hỏi lại và đảm bảo nó đúng hơn" -> code qua bộ đo rồi thì ĐỌC
# CHỮ THẬT trên khung (dựng thử cỡ nhỏ), số nào hiện ra mà lời kể (câu này + câu trước / sau) không nói -> trả lỗi để AI
# sửa đúng số đó (vòng sửa như các lỗi khác).
KIEM_SO = True


def _kiem_so(ma, pr, giay, nc, bao):
    import so_lieu
    try:
        sai, loi_d = so_lieu.kiem_hinh(ma, pr, giay, nc["cau"], nc.get("quanh", ""))
    except Exception as e:                                               # noqa: BLE001  bộ đọc hỏng: không chặn cảnh
        bao(f"(không đọc được số trên hình: {str(e)[:80]})")
        return ""
    if not sai:
        return ""
    loi_so = sorted(so_lieu.so_trong_loi(nc["cau"]))
    bao("số trên hình không khớp lời: " + ", ".join(f"{so_lieu.dinh_dang(n)} («{t}»)" for n, t in sai))
    return ("WRONG NUMBERS ON SCREEN — the viewer will read these but the narration never says them: "
            + "; ".join(f"{so_lieu.dinh_dang(n)} (shown as «{t}»)" for n, t in sai)
            + ". The narration of this shot says: «" + nc["cau"] + "»"
            + (f" — its numbers are: {', '.join(so_lieu.dinh_dang(n) for n in loi_so)}" if loi_so else " — it gives NO exact number")
            + ". Every number / year / amount on screen must be EXACTLY one the narration says (same value; '40.000', '1870' "
              "and '3 triệu' style is fine). Do not invent dates, years, counts or amounts: fix the value to the spoken one, "
              "or remove that number (show the idea with pictures instead). Keep everything else of the shot as it is.")


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
    nc.update(diem=int(diem), loi_cham=[str(x) for x in loi or []])     # 04/11: điểm lưu vào bản ghi cảnh (🔧 sửa cảnh yếu)
    if dat:
        return code, pr
    if not nc.get("tu_sua", True):                                       # ⚡ dựng nhanh: chấm thôi, sửa sau bằng 🔧
        bao("⚡ dựng nhanh — để 🔧 sửa sau")
        return code, pr
    # 03/11 (thử): Antigravity headless tự sửa code thì cứ đòi chạy lệnh (bị chặn trong sandbox) rồi quá giờ -> Antigravity
    # CHẤM + chỉ lỗi, Gemini web SỬA theo đúng nhận xét, Antigravity chấm lại: điểm cao hơn mới nhận
    c2 = None
    if AGY_TAC_NHAN:                                                     # 03/11: quyền hẹp -> Antigravity tự sửa, tự dựng,
        bao("Antigravity tự sửa + dựng thử + nhìn khung…")              # tự nhìn, lặp; vẫn qua bộ đo + chấm lại bên dưới
        c2, p2, tu = agy.tac_nhan_sua(ma, nc.get("cau", ""), nc.get("y_chinh", ""), nc.get("mo_ta", ""), nc.get("anh", ""),
                                      loi, code, pr, giay, vong=AGY_VONG, bao=bao)
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
    if diem2 is not None:
        nc.update(diem=int(diem2), loi_cham=[str(x) for x in loi_2 or []])
    if GEMINI_SUA_TIEP and diem2 is not None and int(diem2) < agy.DAT and loi_2:
        # 04/11: lỗi chấm lại thường cụ thể (chữ bị cắt ở giây x, nền nhoè) -> một lượt Gemini sửa đúng chỗ đó (~1-2 phút)
        bao("Gemini sửa tiếp theo lỗi chấm lại…")
        c3, p3 = _tach_tra_loi(hoi_llm(_HOI_GOP_Y.format(y_kien="; ".join(map(str, loi_2)), code=c2,
                                                         props=json.dumps(p2, ensure_ascii=False)), timeout=420))
        if c3 and "export const Canh" in c3:
            p3 = p2 | (p3 or {})
            loi3, khung3 = _kiem(ma, c3, p3, giay)
            if not loi3:
                _, diem3, _ = agy.duyet_canh(nc.get("cau", ""), nc.get("y_chinh", ""), nc.get("mo_ta", ""), khung3,
                                             [os.path.join(CACHE_CHUNG, "nhan_y", "thu_ai")])
                if diem3 is not None and int(diem3) > int(diem2):
                    bao(f"bản Gemini sửa tiếp: {diem3}/10 — dùng")
                    return c3, p3
                bao(f"bản Gemini sửa tiếp: {diem3}/10 — không hơn, giữ bản {diem2}/10")
            else:
                bao("bản Gemini sửa tiếp không qua bộ đo — giữ bản trước")
            _kiem(ma, c2, p2, giay)                                       # ghi lại bản đang dùng
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
        for q in (v.get("sfx") or [])[:5]:
            a = nhan_y._sfx(q.get("loai"), lan.get(q.get("loai"), 0))     # noqa: SLF001
            lan[q.get("loai")] = lan.get(q.get("loai"), 0) + 1
            if a:
                vol = nhan_y._am_luong(a[0], gd, bool(q.get("chot")))     # noqa: SLF001
                if vol < 4.0:
                    sfx.append((round(max(0.0, v["t0"] + float(q.get("t") or 0) - a[1]), 3), a[0], vol))
    # 04/11 (lopxe: câu 8, 101 bị _ghep bỏ vì cảnh trước lố 0,1-0,3 s — đuôi +0,5 s sau câu): cắt cảnh trước tới lúc cảnh
    # sau bắt đầu thay vì bỏ cảnh sau
    clip.sort()
    for j in range(len(clip) - 1):
        t0, g, f_ = clip[j]
        if t0 + g > clip[j + 1][0] and clip[j + 1][0] - t0 >= 0.5:
            clip[j] = (t0, round(clip[j + 1][0] - t0, 3), f_)
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
        # 04/11: public nhỏ chỉ gồm tệp các cảnh cần dựng nhắc tới (Root.tsx import mọi cảnh nhưng chỉ cảnh dựng mới nạp ảnh)
        chu = "".join(open(os.path.join(THU_AI, f"{ma}.jsx"), encoding="utf-8").read() + json.dumps(props, ensure_ascii=False)
                      + f" nhan_y/giong_{ma}.wav " for ma, props, _ in viec)    # giọng đọc: Root.tsx gắn qua coGiong
        pub = _pub_nho("dung", chu)
        try:
            nen_ban_do._render(jobs, thu, ten="cảnh Remotion AI", pub=pub)   # noqa: SLF001
        finally:
            import shutil
            shutil.rmtree(pub, ignore_errors=True)
    return {m: (o if os.path.isfile(o) and os.path.getsize(o) > 5000 else None) for m, o in ra.items()}


def _render(ma, props, giay):
    """Dựng mp4 của một mục Studio (đã đăng ký trong Root) -> đường mp4 | None."""
    return _render_nhieu([(ma, props, giay)])[ma]


def _mot_cho(du_an, y, cau, theo_i, bao, cu=None, tu_sua=True):
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
    mo_that, anh_that, khoa_that = _anh_that(du_an, text)
    # thiết kế cũ chỉ dùng lại khi cùng lời VÀ cùng mục 🏛 lịch sử (user vừa thêm ảnh -> thiết kế lại cho có người thật)
    tk = cu.get("thiet_ke") if cu.get("thiet_ke") and cu.get("text") == text and (cu.get("khoa_that") or []) == khoa_that else None
    cho = cu.get("cho") if isinstance(cu.get("cho"), dict) else None     # 05/11: cảnh đang chờ đủ ảnh -> vẽ bù, không thiết kế lại
    if cho and cho.get("thiet_ke") and cho.get("text") == text and (cho.get("khoa_that") or []) == khoa_that:
        tk = cho["thiet_ke"]
        bao(f"câu {y['cau']}: cảnh đang chờ ảnh — dùng lại thiết kế, chỉ vẽ bù ảnh còn thiếu")
    else:
        cho = None
    if tk:
        bao(f"câu {y['cau']}: dùng lại thiết kế + ảnh lần trước")
    else:
        bao(f"câu {y['cau']}: AI thiết kế cảnh…")
    hoi_tk = _HOI_THIET_KE.format(giay=giay, truoc=truoc, cau=text, sau=sau, y_chinh=y.get("y_chinh") or "",
                                  tu=", ".join(f"{w}@{s}s" for w, s in tu),
                                  sfx_loai=", ".join(nhan_y._sfx_loai()), that=mo_that)   # noqa: SLF001
    if AI_THIET_KE == "chatgpt":
        hoi_tk += _THEM_CHATGPT.format(giay=giay, toi_da=_toi_da_nhip(giay))
    if not tk and THIET_KE_3_HUONG and AI_THIET_KE != "chatgpt":
        bao(f"câu {y['cau']}: AI nghĩ 3 phương án…")
        ds_cu = doc_json(_ds(du_an), {}) or {}
        truoc_tk = [v.get("thiet_ke") for v in sorted((v for v in ds_cu.values() if int(v.get("cau") or 0) < y["cau"]),
                                                      key=lambda v: int(v["cau"]))[-3:]]
        tk = _thiet_ke_3_huong(hoi_tk, text, giay, truoc_tk, lambda m: bao(f"câu {y['cau']}: {m}"))
    for lan in range(3 if not tk else 0):                                # 04/11 lopxe câu 20: một lượt hỏng là mất cả cảnh
        tk = rut_json(_hoi_ai(hoi_tk, timeout=420, vai="thiet_ke")) or {}
        if isinstance(tk, dict) and tk.get("mo_ta"):
            break
        bao(f"câu {y['cau']}: AI chưa trả thiết kế — hỏi lại ({lan + 2}/3)")
    # 05/11: đo nhịp bản thiết kế TRƯỚC khi vẽ ảnh — quá dày / không có lớp thì trả lại sửa (không tốn lượt Flow)
    for lan in range(2 if AI_THIET_KE == "chatgpt" and THIET_KE_DO_NHIP and isinstance(tk, dict) and tk.get("mo_ta")
                     and not cu.get("thiet_ke") is tk else 0):
        loi_n = _kiem_nhip_tk(tk, tu, giay)
        if not loi_n:
            break
        bao(f"câu {y['cau']}: thiết kế quá dày / thiếu lớp — trả lại sửa ({loi_n[:90]})")
        tk2 = rut_json(_hoi_ai(hoi_tk + "\n\nYour previous plan (JSON): " + json.dumps(tk, ensure_ascii=False)
                               + "\nPROBLEM: " + loi_n + ". Return the corrected plan, same JSON format.",
                               timeout=420, vai="thiet_ke")) or {}
        if isinstance(tk2, dict) and tk2.get("mo_ta"):
            tk = tk2
    tk = tk if isinstance(tk, dict) else {}
    if not tk.get("mo_ta"):
        return {"trang_thai": "loi", "loi": "AI không trả thiết kế", "t0": t0, "giay": giay, "text": text}
    if TU_SOAT and cu.get("thiet_ke") is not tk and not tk.get("_da_soat"):
        tk0 = tk
        tk = _soat_thiet_ke(tk, text, giay, lambda m: bao(f"câu {y['cau']}: {m}"))
        tk = tk | {k: tk0[k] for k in ("_chon", "_phuong_an") if k in tk0}         # giữ kết quả giám khảo (cách A)
        if AI_THIET_KE == "chatgpt" and THIET_KE_DO_NHIP and tk is not tk0 and _kiem_nhip_tk(tk, tu, giay) \
                and not _kiem_nhip_tk(tk0, tu, giay):
            bao(f"câu {y['cau']}: bản tự soát làm nhịp dày lại — giữ bản trước soát")
            tk = dict(tk0, _da_soat=True)
    anh = [a for a in (cho or cu).get("anh") or [] if a.get("loai") != "that" and not a.get("muon")] \
        if (cho or cu).get("thiet_ke") is tk else []
    co_ten = {a.get("ten") for a in anh}
    can_ve = [a for a in (tk.get("anh") or [])[:8] if isinstance(a, dict) and a.get("ten") not in co_ten]   # chạy lại: vẽ bù ảnh thiếu
    # 05/11 (lopxe câu 1: "dòng thác hàng trăm lốp… trên nền trắng" — Flow vẽ cả cảnh kín khung, 12 lần đều hỏng): ảnh TÁCH đã
    # hỏng ở vòng trước -> AI viết lại câu lệnh cho vẽ được thành MỘT vật / cụm gọn trên nền trắng (vẫn đúng ý cảnh)
    hong = dict((cho or {}).get("hong") or {})
    for a in can_ve:
        if a.get("loai") == "tach" and hong.get(a.get("ten"), 0) >= 1:
            moi = _viet_lai_tach(a, text)
            if moi:
                bao(f"câu {y['cau']}: ảnh tách '{a.get('ten')}' vẽ hỏng {hong[a.get('ten')]} vòng — viết lại câu lệnh: {moi[:90]}")
                a["ve"] = moi
    anh += _ve_ca_canh(can_ve, du_an, lambda m: bao(f"câu {y['cau']}: {m}"))
    thieu = [a for a in can_ve if a.get("ten") not in {x.get("ten") for x in anh}]
    if thieu and CHO_DU_ANH:
        # 05/11 user: "mượn tạm ảnh thì không được … bắt buộc đủ ảnh thì dựng, không thì cho vào hàng chờ, đủ ảnh thì dựng sau"
        # -> không viết code; giữ thiết kế + ảnh ĐÃ vẽ (vòng sau chỉ vẽ bù ảnh thiếu); bản nháp vẫn giữ cảnh cũ
        bao(f"câu {y['cau']}: thiếu {len(thieu)} ảnh ({', '.join(str(a.get('ten')) for a in thieu)}) — vào hàng chờ, đủ ảnh mới dựng")
        cho = {"thiet_ke": tk, "anh": list(anh), "text": text, "khoa_that": khoa_that, "luc": time.time(),
               "hong": {**hong, **{a.get("ten"): hong.get(a.get("ten"), 0) + 1 for a in thieu}}}
        return dict(cu, ma=ma, cau=y["cau"], den_cau=y.get("den_cau") or y["cau"], t0=t0, giay=giay, text=text,
                    tu=tu, trang_thai="loi", cho_anh=True, cho=cho,
                    loi=f"chờ vẽ đủ ảnh (còn thiếu {len(thieu)}) — đủ ảnh mới dựng")
    if thieu:                                                            # (CHO_DU_ANH tắt) mượn ảnh cùng loại cảnh bên cạnh
        muon = _muon_anh(du_an, y["cau"], thieu)
        if muon:
            bao(f"câu {y['cau']}: mượn {len(muon)} ảnh của cảnh bên cạnh thay ảnh không vẽ được")
        anh += muon
    if not anh and not anh_that:
        # 04/11 (lopxe: Flow chặn 'unusual activity' -> câu 119-121 không ảnh nào, AI viết code bịa tên ảnh): không viết code
        # khi không có ảnh — lưu thiết kế, để vòng sau vẽ lại
        _ghi_ds(du_an, {str(y["cau"]): dict(cu, ma=ma, cau=y["cau"], den_cau=y.get("den_cau") or y["cau"], t0=t0, giay=giay,
                                            text=text, thiet_ke=tk, anh=[], tu=tu, khoa_that=khoa_that, trang_thai="loi",
                                            cho_anh=True, loi="không vẽ được ảnh nào (Flow đang chặn / lỗi) — vẽ lại sau")})
        return dict(cu, ma=ma, cau=y["cau"], den_cau=y.get("den_cau") or y["cau"], t0=t0, giay=giay, text=text, thiet_ke=tk,
                    anh=[], tu=tu, khoa_that=khoa_that, trang_thai="loi", cho_anh=True,
                    loi="không vẽ được ảnh nào (Flow đang chặn / lỗi) — vẽ lại sau")
    if anh_that:
        bao(f"câu {y['cau']}: dùng {len(anh_that)} ảnh thật — " + ", ".join(a["ten"] for a in anh_that))
    # 04/11 user ("bị dừng thì khi làm tiếp không làm lại"): lưu thiết kế + ảnh ngay -> chạy lại dùng lại, chỉ viết code lại
    _ghi_ds(du_an, {str(y["cau"]): dict(cu, ma=ma, cau=y["cau"], den_cau=y.get("den_cau") or y["cau"], t0=t0, giay=giay,
                                        text=text, thiet_ke=tk, anh=list(anh), tu=tu, khoa_that=khoa_that,
                                        trang_thai=cu.get("trang_thai") or "dang")})
    anh += anh_that
    mo_anh = "\n".join(f"  - {a['ten']} ({a['loai']}, {a['rong']}x{a['cao']}): '{a['file']}'" for a in anh) or "  (none)"
    bao(f"câu {y['cau']}: AI viết code cảnh ({tk.get('kieu', '2d')})…")
    nhip = _khung_nhip(tk, tu)
    hoi = _HOI_CODE.format(mo_ta=tk["mo_ta"], khung=round(giay * 30), giay=giay, cau=text,
                           tu=", ".join(f"{w}@{round(s * 30)}" for w, s in tu), anh=mo_anh,
                           nhip="\n".join(f"  - frame {k} ({k / 30:.1f} s) «{c}»: {h}" for k, c, h in nhip) or "  (none — follow the word timings)")
    nc = {"cau": text, "y_chinh": y.get("y_chinh") or "", "mo_ta": tk.get("mo_ta", ""), "anh": mo_anh, "tu_sua": tu_sua,
          "quanh": f"{truoc} {sau}"}
    code, pr = _viet_code(ma, hoi, {}, giay, lambda m: bao(f"câu {y['cau']}: {m}"), nc)
    ban_ghi = {"ai_code": "deepseek" if CODE_CHI_DEEPSEEK and AI_CODE == "deepseek" else (AI_CODE or "gemini"),   # 05/11
               "ma": ma, "id": _id_comp(ma), "cau": y["cau"], "den_cau": y.get("den_cau") or y["cau"], "t0": t0, "giay": giay,
               "text": text, "thiet_ke": tk, "anh": anh, "tu": tu, "khoa_that": khoa_that,
               "diem": nc.get("diem"), "loi_cham": nc.get("loi_cham") or []}
    if code is None:
        f_code = os.path.join(THU_AI, f"{ma}.jsx")
        if os.path.isfile(f_code):
            os.replace(f_code, f_code + ".loi")                           # không để code hỏng làm hỏng cả Root
        # 05/11 (lopxe câu 1: code hỏng -> giữ cảnh cũ, mất luôn thiết kế + ảnh vừa vẽ): giữ chúng trong "cho" để lần sau
        # (🔁 viết lại / chạy lại) chỉ viết lại code, không thiết kế / vẽ lại
        cho_code = {"thiet_ke": tk, "anh": [a for a in anh if a.get("loai") != "that"], "text": text, "khoa_that": khoa_that,
                    "luc": time.time(), "hong": {}, "chi_code": True}
        return ban_ghi | {"trang_thai": "loi", "loi": pr, "cho": cho_code}
    pr["giay"] = giay
    loai_ok = set(nhan_y._sfx_loai())                                    # noqa: SLF001
    sfx = []
    for q in (tk.get("am") or [])[:5]:                                   # tiếng AI chọn, đặt theo giờ chữ đầu của cụm
        if isinstance(q, dict) and q.get("loai") in loai_ok:
            g = nhan_y._gio_cum(theo_i[y["cau"]], str(q.get("cum") or ""))   # noqa: SLF001
            sfx.append({"t": round((g - t0) if g is not None else 0.0, 2), "loai": q["loai"], "chot": bool(q.get("chot"))})
    return ban_ghi | {"trang_thai": "viet_xong", "props": pr, "sfx": sfx}


def dung(du_an, chi=None, bao=None, lam_lai=False, viet_lai=False, song_song=None, tu_sua=True, ghep_cuoi=True):
    """Bước 3 cho mọi chỗ đã duyệt (chi: chỉ các câu này; lam_lai: bỏ cả phần đã chỉnh tay; song_song: số chỗ cùng lúc,
    mặc định SONG_SONG; tu_sua=False: ⚡ dựng nhanh — Antigravity chỉ chấm, không tự sửa). -> {xong, loi, nhap}"""
    bao = bao or (lambda m: log("  " + m))
    kh = [y for y in doc_ke_hoach(du_an) if not y.get("bo") and (not chi or y["cau"] in chi)]
    if not kh:
        return {"xong": 0, "loi": 0, "nhap": None}
    cau = _cau_ke_hoach(du_an)                                           # noqa: SLF001
    theo_i = {c["i"]: c for c in cau}
    ds = doc_json(_ds(du_an), {}) or {}
    import threading
    from concurrent.futures import ThreadPoolExecutor
    khoa = threading.Lock()
    td = TienDo(du_an, [y["cau"] for y in kh], "🎞 dựng" + ("" if tu_sua else " ⚡ nhanh"), song_song or SONG_SONG)
    bao = td.bao_qua(bao)

    bat_dau = time.time()

    def mot(y):
        k = str(y["cau"])
        dang_cho = bool(ds.get(k, {}).get("cho_anh") or (ds.get(k, {}).get("cho") or {}).get("chi_code"))   # 05/11: chờ ảnh /
        #                                                                  chờ viết lại code -> phải làm tiếp
        # 04/11 user: chạy lại (bị dừng / bấm lại) thì làm TIẾP — cảnh đã có video giữ nguyên; làm lại thì 🔁 từng cảnh
        if not lam_lai and not viet_lai and not dang_cho and ds.get(k, {}).get("trang_thai") == "xong" and os.path.isfile(ds[k].get("mp4") or ""):
            td.xong(y["cau"], "đã có từ trước")
            return
        if not lam_lai and not viet_lai and not dang_cho and ds.get(k, {}).get("trang_thai") == "viet_xong" and os.path.isfile(os.path.join(THU_AI, f"{ds[k]['ma']}.jsx")):
            td.xong(y["cau"], "code có từ trước — chờ dựng video")
            return                                                       # code đã viết + dựng thử đạt: chỉ còn dựng video
        _cho_ram(bao, y["cau"])
        cu = dict(ds.get(k) or {})
        f_code = os.path.join(THU_AI, f"{cu.get('ma') or _ma(du_an, y['cau'])}.jsx")
        sao = f_code + ".truoc"
        if os.path.isfile(f_code):
            import shutil
            shutil.copy2(f_code, sao)                                    # code cũ còn chạy được
        try:
            # làm lại: bỏ bản cũ, NHƯNG giữ hàng chờ ảnh của chính lượt này (vòng vẽ bù không thiết kế lại)
            cho = cu.get("cho") if isinstance(cu.get("cho"), dict) and float(cu["cho"].get("luc") or 0) >= bat_dau else None
            r = _mot_cho(du_an, y, cau, theo_i, bao, ({"cho": cho} if cho else None) if lam_lai else cu, tu_sua=tu_sua)
        except Exception as e:                                           # noqa: BLE001  một chỗ hỏng không dừng cả loạt
            r = {"trang_thai": "loi", "loi": str(e)[:300], "cau": y["cau"]}
        # 03/11 (viết lại theo luật mới hỏng cả 9 cảnh -> mất cảnh cũ khỏi bản nháp): lượt mới hỏng thì GIỮ bản cũ
        if r.get("trang_thai") == "loi" and cu.get("trang_thai") in ("xong", "viet_xong")                 and (os.path.isfile(sao) or os.path.isfile(cu.get("mp4") or "")):
            if os.path.isfile(sao):
                os.replace(sao, f_code)                                  # có code cũ: trả lại; không thì vẫn giữ video cũ
            bao(f"câu {y['cau']}: lượt mới hỏng ({str(r.get('loi'))[:80]}) — giữ cảnh cũ")
            r = cu | {"loi_moi": r.get("loi", "")} | ({"cho_anh": not r["cho"].get("chi_code"), "cho": r["cho"]} if r.get("cho")
                                                       else {"cho_anh": False, "cho": None})
        elif os.path.isfile(sao):
            os.remove(sao)
        with khoa:
            ds[k] = r
            _ghi_ds(du_an, {k: r})
        if r.get("trang_thai") == "loi":
            td.loi(y["cau"], str(r.get("loi") or "")[:200])
        else:
            td.xong(y["cau"], f"{r.get('diem')}/10" if r.get("diem") is not None else "")
    # 03/11 user ("hình như đang chạy tuần tự"): SONG_SONG chỗ cùng lúc — phần lớn thời gian là chờ AI trả lời / Flow vẽ,
    # Gemini hỏi song song trên nhiều hồ sơ Chrome, Flow vẽ song song nhiều tài khoản
    n_ss = max(1, min(SONG_SONG_TOI_DA, int(song_song or SONG_SONG)))
    bao(f"dựng {len(kh)} chỗ, {n_ss} chỗ cùng lúc" + ("" if tu_sua else " (⚡ nhanh: chưa tự sửa)") + "…")
    with ThreadPoolExecutor(n_ss) as ex:
        list(ex.map(mot, kh))
    # 04/11: cảnh không vẽ được ảnh (Flow chặn lúc dồn) -> vẽ bù khi Flow đã rảnh, ít cảnh cùng lúc. 05/11 user ("bắt buộc đủ
    # ảnh … cho vào hàng chờ, đủ ảnh thì dựng sau"): tới VONG_CHO_ANH vòng, mỗi vòng chờ có hồ sơ Flow hết nghỉ
    import flow_ve
    for vong in range(VONG_CHO_ANH):
        cho = [y for y in kh if (ds.get(str(y["cau"])) or {}).get("cho_anh")]
        if not cho:
            break
        han = time.time() + CHO_FLOW_RANH
        while flow_ve.so_ho_so_dung_duoc() == 0 and time.time() < han:
            td.buoc(f"⏳ {len(cho)} cảnh chờ đủ ảnh — mọi hồ sơ Flow đang nghỉ, chờ…")
            time.sleep(30)
        bao(f"vòng vẽ bù {vong + 1}/{VONG_CHO_ANH}: {len(cho)} cảnh chờ đủ ảnh — 2 cảnh cùng lúc…")
        with ThreadPoolExecutor(2) as ex:
            list(ex.map(mot, cho))
    con = [y["cau"] for y in kh if (ds.get(str(y["cau"])) or {}).get("cho_anh")]
    if con:
        bao(f"⏳ còn {len(con)} cảnh chưa đủ ảnh (câu {', '.join(map(str, con))}) — bản nháp giữ cảnh cũ; chạy lại sau để dựng nốt")
    viet = {v["ma"]: v["props"] for v in ds.values() if v.get("trang_thai") in ("viet_xong", "xong") and v.get("props")}
    for v in ds.values():
        if v.get("ma") in viet:
            _giong(du_an, v)
    if viet:
        _dang_ky(viet)
    can = [v for v in ds.values() if v.get("trang_thai") in ("viet_xong", "xong") and (not chi or v.get("cau") in chi)
           and os.path.isfile(os.path.join(THU_AI, f"{v.get('ma')}.jsx"))]      # không còn code: giữ video cũ, không dựng
    loi = sum(1 for v in ds.values() if v.get("trang_thai") == "loi" and (not chi or v.get("cau") in chi))
    td.buoc(f"dựng video {len(can)} cảnh (một lượt, song song)")
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
    _ghi_ds(du_an, {str(v["cau"]): v for v in can})
    if not ghep_cuoi:                                                    # 05/11: 🗑 dựng lại MỘT cảnh -> người gọi tự thay cảnh đó
        td.het(f"xong {xong} cảnh, lỗi {loi}")
        return {"xong": xong, "loi": loi, "nhap": None}
    td.buoc("ghép vào bản nháp")
    nhap = ghep(du_an, bao)
    td.het(f"xong {xong} cảnh, lỗi {loi}" + (f" — đã ghép vào '{nhap}'" if nhap else " — chưa có bản nháp _hoan_chinh"))
    return {"xong": xong, "loi": loi, "nhap": nhap}



def ds_yeu(du_an, nguong=None):
    """Cảnh đã dựng mà điểm Antigravity < nguong (mặc định agy.DAT), không tính cảnh user đã chỉnh tay. -> [câu]"""
    import agy
    nguong = nguong or agy.DAT
    ds = doc_json(_ds(du_an), {}) or {}
    return sorted(v["cau"] for v in ds.values() if v.get("trang_thai") in ("xong", "viet_xong") and not v.get("sua_tay")
                  and v.get("diem") is not None and int(v["diem"]) < nguong
                  and os.path.isfile(os.path.join(THU_AI, f"{v.get('ma')}.jsx")))


def sua_yeu(du_an, chi=None, bao=None, song_song=None):
    """🔧 (04/11 user: dựng nhanh cả bài trước, sửa sau): Antigravity tự sửa các cảnh yếu (chi, mặc định ds_yeu) TỪ CODE
    ĐANG CÓ — không thiết kế / vẽ / viết lại — rồi dựng lại video + ghép bản nháp. -> {sua, tot_hon, nhap}"""
    bao = bao or (lambda m: log("  " + m))
    chi = list(chi or ds_yeu(du_an))
    if not chi:
        return {"sua": 0, "tot_hon": 0, "nhap": None}
    ds = doc_json(_ds(du_an), {}) or {}
    from concurrent.futures import ThreadPoolExecutor
    tot = []
    td = TienDo(du_an, chi, "🔧 sửa cảnh yếu", song_song or SONG_SONG)
    bao = td.bao_qua(bao)

    def mot(i):
        v = dict(ds.get(str(i)) or {})
        if not v.get("ma"):
            td.loi(i, "chưa có cảnh")
            return
        b = lambda m: bao(f"câu {i}: {m}")                               # noqa: E731
        code = open(os.path.join(THU_AI, f"{v['ma']}.jsx"), encoding="utf-8").read()
        pr = _props_hien(v)
        loi, khung = _kiem(v["ma"], code, pr, v["giay"])
        if loi:
            b(f"code hiện tại không qua bộ đo ({loi.splitlines()[0][:80]}) — bỏ qua")
            td.loi(i, "code hiện tại không qua bộ đo")
            return
        nc = {"cau": v.get("text", ""), "y_chinh": "", "mo_ta": (v.get("thiet_ke") or {}).get("mo_ta", ""),
              "anh": "\n".join(f"  - {a['ten']} ({a['loai']}, {a['rong']}x{a['cao']}): '{a['file']}'" for a in v.get("anh") or []),
              "tu_sua": True}
        c2, p2 = _duyet_agy(v["ma"], code, pr, v["giay"], khung, nc, b)
        if c2 != code or p2 != pr:
            tot.append(i)
        v.update(props=p2 | {"giay": v["giay"]}, trang_thai="viet_xong", diem=nc.get("diem", v.get("diem")),
                 loi_cham=nc.get("loi_cham", v.get("loi_cham") or []))
        ds[str(i)] = v
        _ghi_ds(du_an, {str(i): v})
        td.xong(i, f"{v.get('diem')}/10" + (" (bản sửa)" if i in tot else " (giữ bản cũ)"))

    n_ss = max(1, min(SONG_SONG_TOI_DA, int(song_song or SONG_SONG)))
    bao(f"🔧 sửa {len(chi)} cảnh yếu, {n_ss} cảnh cùng lúc…")
    with ThreadPoolExecutor(n_ss) as ex:
        list(ex.map(mot, chi))
    can = [ds[str(i)] for i in chi if ds.get(str(i), {}).get("trang_thai") == "viet_xong"]
    for v in can:
        _giong(du_an, v)
    if can:
        _dang_ky({v["ma"]: v["props"] for v in can})
    mp4 = _render_nhieu([(v["ma"], _props_hien(v), v["giay"]) for v in can]) if can else {}
    for v in can:
        v.update(trang_thai="xong", mp4=mp4.get(v["ma"]) or v.get("mp4"))
    _ghi_ds(du_an, {str(v["cau"]): v for v in can})
    td.buoc("thay từng cảnh đã sửa trong bản nháp")
    import sua_canh                                                      # 05/11 user: chỉ cảnh sửa ghi đè bản nháp
    nhap = None
    for v in can:
        if v.get("cau") in tot:
            nhap = sua_canh.ghep_mot(du_an, v["cau"], bao) or nhap
    td.het(f"sửa {len(chi)} cảnh, {len(tot)} cảnh có bản tốt hơn" + (f" — đã thay trong '{nhap}'" if nhap else ""))
    return {"sua": len(chi), "tot_hon": len(tot), "nhap": nhap}


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
    _ghi_ds(du_an, {str(cau): v})
    import sua_canh                                                      # 04/11 user: chỉ cảnh này ghi đè bản nháp
    return {"mp4": mp4, "nhap": sua_canh.ghep_mot(du_an, cau, bao)}


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
    _ghi_ds(du_an, {str(cau): v})
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
    cau = {c["i"]: c for c in _cau_ke_hoach(du_an)}                      # noqa: SLF001
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
