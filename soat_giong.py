# -*- coding: utf-8 -*-
"""Soát GIỌNG ĐỌC OmniVoice sau khi đọc (18/10 user): nuốt / đọc méo chữ (nhất là cụm số) và NGẮT NGHỈ giữa cụm từ
khi chưa tới dấu câu. Câu lỗi -> đọc lại bằng seed khác (tối đa LAN_DOC_LAI lượt), giữ bản ÍT LỖI NHẤT; câu vẫn lỗi
được liệt kê trong báo cáo, không bỏ qua im lặng.

Bộ nghe chính: wav2vec2 tiếng Việt (CTC) — ghi đúng TỪNG ÂM TIẾT nghe được, không tự đổi ra chữ số như Whisper (Whisper
nghe "ba phìn trăm tám mươi sáu nghìn" vẫn ghi "386.000" nên che mất lỗi). Đo 18/10 trên fish: bắt "ba phìn trăm"
(câu 8), mất "phẩy" (câu 47), mất "một nghìn chín trăm" ở năm thứ hai (câu 9).

1/11 user ("từ sai bắt buộc đọc lại cho đúng, ngắt nghỉ không đúng chỗ cũng phải đọc lại"): bản cũ chỉ báo 1/160 câu
chosoi. Đo trên 198 câu mẫu cố tình đọc sai có đáp án: bản cũ bắt 33% lỗi thanh, 47% âm đầu, 37% âm cuối, 13% ngắt giữa
từ ghép, vì bỏ dấu thanh khi so chữ và miễn ngắt trước cả danh sách dài từ nối. Bản này:
  * TỪ SAI: so CÓ dấu thanh, sau khi gộp âm đồng âm giọng Bắc (s=x, ch=tr, d=gi=r). Bộ nghe một mình nghe nhầm ~35% câu
    sạch nên một âm tiết chỉ tính sai khi có HAI bằng chứng độc lập trong ba: wav2vec2 lệch, Whisper lệch, căn ép điểm
    thấp (kém nhãn tốt nhất cùng khung > 0,6 log-xác suất).
  * NGẮT SAI: đo chỗ lặng ngay TẠI ranh từng cặp chữ bằng năng lượng so với mức giọng của chính câu (ranh lấy từ căn ép)
    nên không cần bộ nghe ghi đúng hai chữ hai bên. Ngưỡng theo vị trí, xem _ngat.
Lỗi tính cho một câu:
  * NUỐT: thiếu âm tiết so với kịch bản — trong cụm số thiếu >= 1, chữ thường thiếu >= 2 (nghe nhầm lẻ 1 âm bỏ qua).
  * CHÈN TRONG SỐ: âm tiết lạ chen giữa cụm số ("ba phìn trăm").
  * SAI / MÉO: xem trên. * NGẮT: xem _ngat.
2/11 user: câu sai từ hoặc ngắt sai đọc lại tối đa LAN_DOC_LAI lượt; câu chỉ còn ngắt sai thì tự cắt lặng; còn lỗi thì báo.
  Tên/từ nước ngoài (Murray, Darling…) không chấm — bộ nghe tiếng Việt không ghi được, nhưng vẫn căn để giữ đúng mốc."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unicodedata
from difflib import SequenceMatcher


from common import log

MO_HINH = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"
LAN_DOC_LAI = 3             # 2/11 user: tối đa 3 lượt đọc lại (bản 1/11 để 4 lượt, mỗi lượt nạp lại OmniVoice + Whisper nên lâu;
#                             thử 1 lượt rồi user chọn lại 3), giữ bản ít lỗi nhất
BAT_NGAT = True             # 2/11 user ("ok làm vậy đi"): ngắt sai vẫn là lý do ĐỌC LẠI; đọc lại xong mà câu chỉ còn ngắt
#                             sai thì TỰ CẮT đoạn lặng (rut_ngat, giữ độ dài câu) — đo chosoi: đọc lại sửa 15/18 câu ngắt sai
PHIEN_BAN = 3               # 1/11: thêm từ sai hai bộ nghe + đo ngắt theo ranh chữ -> kết quả soát bản 2 phải soát lại
NGUONG_AM = -2.0            # 19/10 user ("khoảng hai trăm năm trước… thức ăn dự phòng" lọt): điểm căn chỉnh ép của một âm
#                             tiết dưới ngưỡng = nuốt / đọc méo. Đo cho_digo 3.415 âm: 99% >= -1,3; "dự" bị nuốt -5,5,
#                             "đưa" bị nuốt -13, "già" đọc thành "ra" -4,0
CHENH_SAI = -0.6            # 1/11: âm tiết kém nhãn tốt nhất cùng khung quá mức này = một bằng chứng (đo: 1% âm câu sạch)
# 1/11: ngưỡng ngắt (giây lặng), đo chosoi 5.043 ranh chữ không dấu câu + 187 ranh có dấu câu, 54 câu mẫu sạch không báo nhầm
NGAT_TU = 0.12              # giữa HAI ÂM CỦA MỘT TỪ GHÉP ("lạ ‖ lẫm"): câu sạch lớn nhất 0,11 s
NGAT_SO = 0.20              # giữa hai chữ của cùng một cụm số ("chín trăm ‖ bảy mươi")
NGAT_SAI = 0.28             # giữa hai từ, từ sau không mở vế mới ("nhỏ ‖ lại")
NGAT_MO = 0.50              # trước từ mở vế ("… ‖ và"): người đọc cũng ngắt, chỉ tính khi dài bất thường
DUNG_PHAY = 0.60            # dấu phẩy: 95% câu chosoi <= 0,48 s
DUNG_CHAM = 1.00            # dấu chấm trong câu
GIU_SAI, GIU_MO, GIU_DAU = 0.08, 0.25, 0.35   # 2/11: tự cắt lặng, giây còn lại: giữa cụm / trước từ mở vế / sau dấu câu
TRAN_LANG = 30              # dB dưới mức giọng của câu (phân vị 95) thì coi là lặng; hơi thở nhẹ cũng tính lặng
SO = set("không một mốt hai ba bốn tư năm lăm sáu bảy tám chín mười mươi trăm nghìn ngàn triệu tỷ tỉ linh lẻ rưỡi "
         "phẩy phần".split())
MO_VE = set("và rồi mà nhưng khi để nhằm thì hay hoặc nếu rằng vì bởi nên song tuy dù chứ như khiến buộc sau trước trong "
            "ngay cũng đã sẽ".split())
_AM = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnpqrstvx])?[aeiouy]+(ch|nh|ng|[cmnpt])?$")
_S = {}
_KHOA = threading.Lock()


def _chuan(s):
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def _nfc(s):
    return unicodedata.normalize("NFC", re.sub(r"[^\w]", "", s.lower()))


def _am_bac(s):
    """Âm tiết CÓ dấu thanh, gộp các phụ âm đầu đọc như nhau ở giọng Bắc (bộ nghe không phân biệt được)."""
    s = _nfc(s)
    for a, b in (("ngh", "ng"), ("gh", "g"), ("gi", "d"), ("tr", "ch"), ("r", "d"), ("s", "x"), ("k", "c")):
        if s.startswith(a):
            return b + s[len(a):]
    return s


def _ngoai(tok):
    """Từ không phải âm tiết tiếng Việt (Murray, Darling, feet…) -> bộ nghe tiếng Việt không ghi đúng được."""
    c = _chuan(tok)
    return bool(c) and (not _AM.match(c) or any(ch in c for ch in "fjwz"))


def _may():
    with _KHOA:
        if "m" not in _S:
            import torch
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            _S["p"] = Wav2Vec2Processor.from_pretrained(MO_HINH)
            _S["dev"] = "cuda" if torch.cuda.is_available() else "cpu"
            _S["m"] = Wav2Vec2ForCTC.from_pretrained(MO_HINH).to(_S["dev"]).eval()
    return _S["p"], _S["m"], _S["dev"]


def _doc_wav(wav):
    import soundfile as sf
    a, sr = sf.read(wav, dtype="float32")
    return (a.mean(1) if a.ndim > 1 else a), sr


def _nghe_lp(a, sr):
    """([(âm tiết, t0, t1)] bộ nghe ghi được (giây), ma trận log-xác suất từng khung, giây mỗi khung)."""
    import librosa
    import torch
    pr, md, dev = _may()
    a = librosa.resample(a, orig_sr=sr, target_sr=16000)
    x = pr(a, sampling_rate=16000, return_tensors="pt").input_values.to(dev)
    with torch.no_grad():
        lg = md(x).logits[0].float()
    ids = lg.argmax(-1).cpu().numpy()
    kq = pr.tokenizer.decode(ids, output_word_offsets=True)
    lp = torch.log_softmax(lg, -1).cpu()
    buoc = len(a) / 16000 / lp.shape[0]                      # một khung CTC ~ 20 ms
    tu = [(w["word"], w["start_offset"] * 320 / 16000, w["end_offset"] * 320 / 16000) for w in kq.word_offsets]
    return tu, lp, buoc


def _can_ep(toks, lp):
    """Căn ÉP mọi âm tiết kịch bản vào file giọng (CTC forced alignment): từng âm [{tb, chenh, f0, f1}], âm không căn được
    None. tb = trung bình log-xác suất; chenh = kém nhãn tốt nhất cùng khung bao nhiêu (0 = chính là nhãn nghe được rõ
    nhất). Âm bị nuốt / méo điểm rất thấp. Từ nước ngoài vẫn đưa vào để giọng của nó không đổ lên chữ bên cạnh."""
    import numpy as np
    import torch
    import torchaudio.functional as F
    pr = _may()[0]
    voc = pr.tokenizer.get_vocab()
    sep, blank = voc.get("|"), pr.tokenizer.pad_token_id
    ids, cua = [], []
    for k, t in enumerate(toks):
        if re.search(r"\d", t[0]):                           # chữ số: giọng đọc thành chữ, không căn theo ký tự số
            continue
        cc = [voc[ch] for ch in _nfc(t[0]) if ch in voc]
        if not cc:
            continue
        if ids and sep is not None:
            ids.append(sep)
            cua.append(-1)
        ids += cc
        cua += [k] * len(cc)
    if not ids or len(ids) >= lp.shape[0]:
        return [None] * len(toks)
    ali = F.forced_align(lp.unsqueeze(0), torch.tensor([ids], dtype=torch.int32), blank=blank)[0][0].tolist()
    gom = [([], [], []) for _ in toks]
    ti, truoc = -1, None
    for f, tok in enumerate(ali):
        if tok == blank:
            truoc = None
            continue
        if tok != truoc:
            ti += 1
            truoc = tok
        if 0 <= ti < len(cua) and cua[ti] >= 0:
            d, c, ff = gom[cua[ti]]
            d.append(float(lp[f, tok]))
            c.append(float(lp[f, tok] - lp[f].max()))
            ff.append(f)
    return [{"tb": float(np.mean(d)), "chenh": float(np.mean(c)), "f0": ff[0], "f1": ff[-1]} if d else None
            for d, c, ff in gom]


def _tu_ghep(toks):
    """Tập k: âm k và k+1 thuộc CÙNG một từ ghép (tách từ pyvi). Không có pyvi: báo một lần, bỏ ngưỡng từ ghép."""
    try:
        from pyvi import ViTokenizer
    except ImportError:
        if "pyvi" not in _S:
            _S["pyvi"] = True
            log("    ! soát giọng: chưa cài pyvi (pip install pyvi) — KHÔNG kiểm tra được ngắt giữa từ ghép")
        return set()
    tach = ViTokenizer.tokenize(" ".join(_nfc(t[0]) or "x" for t in toks)).split()
    ra, i = set(), 0
    for w in tach:
        p = w.split("_")
        ra.update(range(i, i + len(p) - 1))
        i += len(p)
    return ra if i == len(toks) else set()


def _lang_khung(a, sr):
    """Mảng True/False mỗi 10 ms: lặng so với mức giọng của chính câu."""
    import numpy as np
    hop = max(1, int(0.01 * sr))
    e = np.sqrt(np.convolve(a * a, np.ones(hop * 2) / (hop * 2), "same"))[::hop]
    db = 20 * np.log10(e + 1e-6)
    return db < np.percentile(db, 95) - TRAN_LANG


def _cho_ngat(toks, am, lang, buoc):
    """Mọi chỗ ngắt sai: [(mô tả, khung lặng đầu, khung lặng cuối, giây giữ lại khi cắt)] (khung 10 ms). Lặng tại ranh hai
    chữ = đoạn lặng dài nhất từ cuối chữ trước đến đầu chữ sau:
      có dấu câu -> chỉ sai khi dài bất thường (DUNG_PHAY / DUNG_CHAM), cắt còn GIU_DAU;
      trước từ mở vế NGAT_MO, cắt còn GIU_MO; trong từ ghép NGAT_TU, trong cụm số NGAT_SO, còn lại NGAT_SAI, cắt còn GIU_SAI."""
    ghep = _tu_ghep(toks)
    ra = []
    for k in range(len(toks) - 1):
        if not am[k] or not am[k + 1] or toks[k][2] or toks[k + 1][2]:
            continue
        i0 = max(0, int(am[k]["f1"] * buoc * 100) - 5)
        i1 = min(len(lang), int(am[k + 1]["f0"] * buoc * 100) + 8)
        tot, dau = (0, 0), None
        for i in range(i0, i1 + 1):
            if i < i1 and lang[i]:
                dau = i if dau is None else dau
            elif dau is not None:
                tot = max(tot, (i - dau, dau))
                dau = None
        d = tot[0] / 100
        tr, sau = toks[k], _nfc(toks[k + 1][0])
        if tr[1]:
            nguong, giu = (DUNG_CHAM if re.search(r"[.!?…]$", tr[0]) else DUNG_PHAY), GIU_DAU
        elif k in ghep:
            nguong, giu = NGAT_TU, GIU_SAI
        elif _nfc(tr[0]) in SO and sau in SO:
            nguong, giu = NGAT_SO, GIU_SAI
        elif sau in MO_VE:
            nguong, giu = NGAT_MO, GIU_MO
        else:
            nguong, giu = NGAT_SAI, GIU_SAI
        if d >= nguong:
            ra.append((f"«{tr[0]} ‖ {toks[k + 1][0]}» lặng {d:.2f}s", tot[1], tot[1] + tot[0], giu))
    return ra


def _lech(a, b):
    """Chỉ số âm tiết của a không khớp b (đã gộp âm đồng âm)."""
    a, b = [_am_bac(x) for x in a], [_am_bac(x) for x in b]
    ra = set()
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal" and a:
            ra.update(min(i, len(a) - 1) for i in range(i1, max(i2, i1 + 1)))
    return ra


def _tach_tok(text):
    """[(âm tiết, có dấu câu sau, nước ngoài)] của câu."""
    toks = []
    for t in str(text).split():
        phan = [p for p in re.split(r"-", t) if _chuan(p)]
        for k, p in enumerate(phan):
            toks.append((p, k == len(phan) - 1 and bool(re.search(r"[,;:.!?…]$", t)), _ngoai(p)))
    return toks


def rut_ngat(text, wav):
    """2/11 user: đọc lại vẫn ngắt sai -> cắt ngắn ĐÚNG các đoạn lặng bộ soát báo (_cho_ngat) trong file giọng, thêm lặng
    cuối câu để giữ nguyên độ dài (mốc câu không đổi). Trả [mô tả chỗ đã cắt]."""
    import wave
    import numpy as np
    toks = _tach_tok(text)
    a_, sr = _doc_wav(wav)
    _w, lp, buoc = _nghe_lp(a_, sr)
    cho = _cho_ngat(toks, _can_ep(toks, lp), _lang_khung(a_, sr), buoc)
    cat = [(x[1], x[2], x[3]) for x in cho if (x[2] - x[1]) / 100 > x[3]]
    ra = [f"{x[0]} -> {x[3]:.2f}s" for x in cho if (x[2] - x[1]) / 100 > x[3]]
    if not cat:
        return []
    with wave.open(wav, "rb") as w:
        ts, du_lieu = w.getparams(), w.readframes(w.getnframes())
    if ts.sampwidth != 2:
        raise ValueError(f"{wav}: chỉ hỗ trợ wav 16 bit")
    x = np.frombuffer(du_lieu, dtype=np.int16).reshape(-1, ts.nchannels).astype("float32")
    n_goc, phai = len(x), int(0.005 * sr)                    # nối 5 ms cho khỏi tiếng tách ở chỗ cắt
    for d0, d1, con in reversed(cat):
        s0, s1 = int(d0 * sr / 100), int(d1 * sr / 100)
        giu = int(con * sr / 2)
        a, b = s0 + giu, s1 - giu
        tron = np.linspace(0, 1, phai, dtype="float32")[:, None]
        giua = x[a - phai:a] * (1 - tron) + x[b:b + phai] * tron
        x = np.concatenate([x[:a - phai], giua, x[b + phai:]])
    x = np.concatenate([x, np.zeros((n_goc - len(x), ts.nchannels), dtype="float32")])
    with wave.open(wav, "wb") as w:
        w.setparams(ts)
        w.writeframes(np.clip(x, -32768, 32767).astype(np.int16).tobytes())
    return ra


def _do_cau(text, wav):
    """Đo một file giọng bằng bộ nghe chính; None nếu câu không có chữ. Kết luận ở _ket_luan."""
    toks = _tach_tok(text)
    if not toks:
        return None
    a_, sr = _doc_wav(wav)
    w, lp, buoc = _nghe_lp(a_, sr)
    am = _can_ep(toks, lp)
    a, b = [_chuan(t[0]) for t in toks], [_chuan(x[0]) for x in w]
    loi = []
    sm = SequenceMatcher(None, a, b, autojunk=False)
    so = lambda i: 0 <= i < len(a) and _nfc(toks[i][0]) in SO    # noqa: E731
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or any(toks[i][2] for i in range(max(0, i1 - 1), min(len(a), i2 + 1))):
            continue
        thieu, du = (i2 - i1) - (j2 - j1), (j2 - j1) - (i2 - i1)
        trong_so = any(so(i) for i in range(i1, i2)) or (so(i1 - 1) and so(i2))
        doan = " ".join(t[0] for t in toks[max(0, i1 - 2):i2 + 1])
        nghe_ra = " ".join(x[0] for x in w[j1:j2]) or "∅"
        if thieu >= (1 if trong_so else 2):
            loi.append(("nuot", f"«{doan}» nghe ra «{nghe_ra}»"))
        elif du >= 1 and trong_so:
            loi.append(("chen", f"«{doan}» nghe ra «{nghe_ra}»"))
    if BAT_NGAT:
        loi += [("ngat", x[0]) for x in _cho_ngat(toks, am, _lang_khung(a_, sr), buoc)]
    gan_ngoai = {i for i in range(len(toks)) if any(toks[j][2] for j in range(max(0, i - 1), min(len(toks), i + 2)))}
    lech = _lech([t[0] for t in toks], [x[0] for x in w]) - gan_ngoai
    nghi = {i for i, x in enumerate(am) if x and x["chenh"] <= CHENH_SAI and i not in gan_ngoai}
    return {"toks": toks, "am": am, "loi": loi, "lech": lech, "nghi": nghi, "gan_ngoai": gan_ngoai}


def _ket_luan(r, whisper):
    """Danh sách lỗi cuối của một câu. whisper = âm tiết Whisper nghe được, None nếu không chạy được Whisper (khi đó chỉ
    còn hai bằng chứng wav2vec2 lệch + điểm thấp)."""
    toks, am = r["toks"], r["am"]
    so_tu = {i for i, t in enumerate(toks) if _nfc(t[0]) in SO}      # Whisper đổi số ra chữ số: không dùng ở cụm số
    lech2 = (_lech([t[0] for t in toks], whisper) - r["gan_ngoai"] - so_tu) if whisper else set()
    sai = (r["nghi"] & (r["lech"] | lech2)) | (r["lech"] & lech2)
    loi = list(r["loi"])
    for i in sorted(sai):
        doan = " ".join(t[0] for t in toks[max(0, i - 2):i + 3])
        diem = f" điểm {am[i]['chenh']:.1f}" if am[i] else ""
        loi.append(("sai", f"«{doan}» từ «{toks[i][0]}»{diem}" + (" (hai bộ nghe lệch)" if i in r["lech"] & lech2 else "")))
    for i, x in enumerate(am):
        if x and x["tb"] < NGUONG_AM and i not in sai and i not in r["gan_ngoai"]:
            loi.append(("meo", f"«{' '.join(t[0] for t in toks[max(0, i - 2):i + 3])}» âm «{toks[i][0]}» điểm {x['tb']:.1f}"))
    return loi


def _whisper(ds):
    """{khoá: [âm tiết]} Whisper nghe lại các file [(khoá, wav)] (env OmniVoice), None nếu không chạy được."""
    from giong import OMNI_PY
    goc = os.path.dirname(os.path.abspath(__file__))
    tam = tempfile.mkdtemp(prefix="soat_wh_")
    vao, ra = os.path.join(tam, "vao.json"), os.path.join(tam, "ra.json")
    try:
        with open(vao, "w", encoding="utf-8") as f:
            json.dump([{"id": k, "wav": os.path.abspath(w)} for k, w in ds], f, ensure_ascii=False)
        p = subprocess.run([OMNI_PY, os.path.join(goc, "tts", "whisper_tu.py"), vao, ra], capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=3600,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        if p.returncode != 0:
            log("    ! soát giọng: Whisper lỗi: " + p.stderr.decode("utf-8", "ignore")[-200:])
            return None
        with open(ra, encoding="utf-8") as f:
            da = json.load(f)
        return {k: [x for c in v for x in re.split(r"[\s-]+", c["w"]) if _nfc(x)] for k, v in da.items()}
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        log(f"    ! soát giọng: Whisper lỗi: {str(e)[:160]}")
        return None
    finally:
        shutil.rmtree(tam, ignore_errors=True)


def soat_nhieu(ds):
    """ds = [(khoá, chữ kịch bản, wav)] -> {khoá: [(loại, mô tả)]}. Câu không đo được ghi loại 'khong_soat' (vẫn tính lỗi).
    Whisper chỉ nghe các câu wav2vec2 đã nghi — câu không có dấu hiệu nào thì không tốn thêm thời gian."""
    do, ra = {}, {}
    for k, text, wav in ds:
        try:
            r = _do_cau(text, wav)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! soát giọng câu {k} lỗi: {str(e)[:100]}")
            ra[k] = [("khong_soat", f"không đo được: {str(e)[:80]}")]
            continue
        if r is None:
            ra[k] = []
        else:
            do[k] = r
    can = [(str(k), w) for k, _t, w in ds if k in do and (do[k]["lech"] or do[k]["nghi"])]
    wh = _whisper(can) if can else {}
    for k, r in do.items():
        ra[k] = _ket_luan(r, None if wh is None else wh.get(str(k)))
    return ra


def soat_cau(text, wav):
    """Lỗi của một file giọng so với kịch bản: [(loại, mô tả)]."""
    return soat_nhieu([(0, text, wav)])[0]


def _diem(loi):
    return sum(1 if l_ == "ngat" else 2 for l_, _ in loi)


def _dem_loai(ds):
    ra = {}
    for loi in ds:
        for l_ in {x[0] for x in loi}:
            ra[l_] = ra.get(l_, 0) + 1
    return ra


def soat_va_doc_lai(canh, thu_muc, lenh_doc):
    """Soát mọi file giọng <thu_muc>/<id:04d>.wav; câu lỗi đọc lại tối đa LAN_DOC_LAI lượt (seed khác) bằng
    lenh_doc(jobs_json, out_dir, seed) -> mã thoát; giữ bản ít lỗi nhất. Kết quả soát nhớ ở <thu_muc>/_soat.json
    theo (cỡ file, mtime) — chạy lại không soát lại. Trả báo cáo {so_cau, phat_hien, theo_loai, doc_lai, luot, thay,
    con_loi: {id: [(loại, mô tả)]}}, cũng ghi ở <thu_muc>/_bao_cao_soat.json; câu không đo / không đọc lại được nằm trong
    con_loi."""
    p_cache = os.path.join(thu_muc, "_soat.json")
    try:
        with open(p_cache, encoding="utf-8") as f:
            da = json.load(f)
    except (OSError, ValueError):
        da = {}

    def dau(wav):
        st = os.stat(wav)
        return f"{st.st_size}:{int(st.st_mtime)}"

    loi_cua, can_do = {}, []
    theo_id = {c["id"]: c for c in canh}
    for c in canh:
        wav = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if not os.path.isfile(wav):
            loi_cua[c["id"]] = [("khong_soat", "chưa có file giọng")]
            continue
        m = da.get(str(c["id"]))
        if m and m.get("dau") == dau(wav) and m.get("text") == c["text"] and m.get("v") == PHIEN_BAN:
            loi = [tuple(x) for x in m["loi"] if BAT_NGAT or x[0] != "ngat"]
            if loi:
                loi_cua[c["id"]] = loi
        else:
            can_do.append((c["id"], c["text"], wav))
    for cid, loi in soat_nhieu(can_do).items():
        if not any(x[0] == "khong_soat" for x in loi):
            wav = os.path.join(thu_muc, f"{cid:04d}.wav")
            da[str(cid)] = {"dau": dau(wav), "text": theo_id[cid]["text"], "loi": loi, "v": PHIEN_BAN}
        if loi:
            loi_cua[cid] = loi
    _ghi(p_cache, da)
    p_bc = os.path.join(thu_muc, "_bao_cao_soat.json")
    bc = {"so_cau": len(canh), "phat_hien": len(loi_cua), "theo_loai": _dem_loai(loi_cua.values()),
          "doc_lai": sorted(loi_cua), "luot": 0, "thay": [], "con_loi": {}}
    if not loi_cua:
        log(f"    soát giọng: {len(canh)} câu, không câu nào sai từ / nuốt chữ / ngắt sai")
        _ghi(p_bc, bc)
        return bc
    log(f"    soát giọng: {len(loi_cua)}/{len(canh)} câu lỗi "
        f"({sum(1 for v in loi_cua.values() for x in v if x[0] != 'ngat')} chỗ sai từ/nuốt/méo, "
        f"{sum(1 for v in loi_cua.values() for x in v if x[0] == 'ngat')} chỗ ngắt sai) -> đọc lại tối đa {LAN_DOC_LAI} lượt")
    for cid, loi in sorted(loi_cua.items()):
        log(f"      cảnh {cid}: " + "; ".join(x[1] for x in loi[:3]))
    tot = {cid: (_diem(loi), None, loi) for cid, loi in loi_cua.items()}    # (điểm, file tốt nhất, lỗi)
    tam = os.path.join(thu_muc, "_doc_lai")
    goc_seed = int(time.time()) % 1000000                    # 1/11: seed cố định thì bấm sửa lần hai lại ra đúng bản cũ
    for lan in range(1, LAN_DOC_LAI + 1):
        con = [cid for cid, v in tot.items() if v[0] > 0]
        if not con:
            break
        out = os.path.join(tam, str(lan))
        os.makedirs(out, exist_ok=True)
        jobs = os.path.join(tam, f"jobs_{lan}.json")
        with open(jobs, "w", encoding="utf-8") as f:
            json.dump([{"idx": cid, "text": theo_id[cid]["text"]} for cid in con], f, ensure_ascii=False)
        rc = lenh_doc(jobs, out, goc_seed + 7919 * lan)
        bc["luot"] = lan
        if rc != 0:
            log(f"    ! đọc lại lượt {lan} lỗi (mã {rc})")
            break
        moi = {}
        for cid in con:
            f_moi = os.path.join(out, f"{cid:04d}.wav")
            if os.path.isfile(f_moi) and os.path.getsize(f_moi) >= 2000:
                moi[cid] = f_moi
            else:
                log(f"    ! đọc lại lượt {lan}: cảnh {cid} không ra file giọng")
        for cid, loi in soat_nhieu([(c, theo_id[c]["text"], f) for c, f in moi.items()]).items():
            if not any(x[0] == "khong_soat" for x in loi) and _diem(loi) < tot[cid][0]:
                tot[cid] = (_diem(loi), moi[cid], loi)
        log(f"    soát giọng lượt {lan}: đọc lại {len(con)} câu, còn {sum(1 for v in tot.values() if v[0] > 0)} câu lỗi")
    for cid, (d, f_moi, loi) in tot.items():
        if not f_moi:
            continue
        dich = os.path.join(thu_muc, f"{cid:04d}.wav")
        goc = os.path.join(thu_muc, "_ban_goc", f"{cid:04d}.wav")   # giữ bản đọc đầu tiên (nghe so sánh / khôi phục)
        if not os.path.isfile(goc):
            os.makedirs(os.path.dirname(goc), exist_ok=True)
            shutil.copyfile(dich, goc)
        shutil.copyfile(f_moi, dich)
        da[str(cid)] = {"dau": dau(dich), "text": theo_id[cid]["text"], "loi": loi, "v": PHIEN_BAN}
        bc["thay"].append(cid)
    # 2/11 user: đọc lại hết lượt mà câu chỉ còn ngắt sai -> cắt đoạn lặng sai chỗ ngay trong file giọng (không đọc thêm)
    chi_ngat = [cid for cid, v in tot.items() if v[2] and all(x[0] == "ngat" for x in v[2])]
    bc["cat_lang"] = {}
    for cid in chi_ngat:
        dich = os.path.join(thu_muc, f"{cid:04d}.wav")
        goc = os.path.join(thu_muc, "_ban_goc", f"{cid:04d}.wav")
        try:
            if not os.path.isfile(goc):
                os.makedirs(os.path.dirname(goc), exist_ok=True)
                shutil.copyfile(dich, goc)
            cat = rut_ngat(theo_id[cid]["text"], dich)
        except Exception as e:                               # noqa: BLE001
            log(f"    ! cắt lặng cảnh {cid} lỗi: {str(e)[:100]}")
            continue
        if cat:
            bc["cat_lang"][cid] = cat
            log(f"    soát giọng: cắt lặng cảnh {cid}: " + "; ".join(cat))
    for cid, loi in soat_nhieu([(c, theo_id[c]["text"], os.path.join(thu_muc, f"{c:04d}.wav")) for c in bc["cat_lang"]]).items():
        tot[cid] = (_diem(loi), tot[cid][1], loi)
        if not any(x[0] == "khong_soat" for x in loi):
            da[str(cid)] = {"dau": dau(os.path.join(thu_muc, f"{cid:04d}.wav")), "text": theo_id[cid]["text"], "loi": loi,
                            "v": PHIEN_BAN}
        if cid not in bc["thay"]:
            bc["thay"].append(cid)
    _ghi(p_cache, da)
    shutil.rmtree(tam, ignore_errors=True)
    bc["thay"].sort()
    bc["con_loi"] = {cid: v[2] for cid, v in sorted(tot.items()) if v[2]}
    log(f"    soát giọng: thay {len(bc['thay'])}/{len(loi_cua)} câu (đọc lại tốt hơn hoặc cắt lặng {len(bc['cat_lang'])} câu); còn {len(bc['con_loi'])} câu chưa hết lỗi")
    for cid, loi in bc["con_loi"].items():
        log(f"    ! CÒN LỖI cảnh {cid}: " + "; ".join(x[1] for x in loi[:3]))
    _ghi(p_bc, bc)
    return bc


def _ghi(p, da):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(da, f, ensure_ascii=False)


if __name__ == "__main__":                                   # python soat_giong.py <thư mục giọng> <jobs.json>: chỉ soát, in lỗi
    import sys
    thu, jobs_p = sys.argv[1], sys.argv[2]
    with open(jobs_p, encoding="utf-8") as f:
        jobs = json.load(f)
    kq = soat_nhieu([(j["idx"], j["text"], os.path.join(thu, f"{j['idx']:04d}.wav")) for j in jobs
                     if os.path.isfile(os.path.join(thu, f"{j['idx']:04d}.wav"))])
    n = 0
    for k, loi in sorted(kq.items()):
        if loi:
            n += 1
            print(f"câu {k:>3}: " + "; ".join(f"[{a}] {b}" for a, b in loi))
    print(f"--- {n}/{len(jobs)} câu có lỗi")
