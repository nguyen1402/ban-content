# -*- coding: utf-8 -*-
"""Soát GIỌNG ĐỌC OmniVoice sau khi đọc (18/10 user): nuốt / đọc méo chữ (nhất là cụm số) và NGẮT NGHỈ giữa cụm từ
khi chưa tới dấu câu. Câu lỗi -> đọc lại bằng seed khác (tối đa LAN_DOC_LAI lượt), giữ bản ÍT LỖI NHẤT.

Bộ nghe: wav2vec2 tiếng Việt (CTC) — ghi đúng TỪNG ÂM TIẾT nghe được, không tự đổi ra chữ số như Whisper (Whisper
nghe "ba phìn trăm tám mươi sáu nghìn" vẫn ghi "386.000" nên che mất lỗi). Đo 18/10 trên fish: bắt "ba phìn trăm"
(câu 8), mất "phẩy" (câu 47), mất "một nghìn chín trăm" ở năm thứ hai (câu 9).

Lỗi tính cho một câu:
  * NUỐT: thiếu âm tiết so với kịch bản — trong cụm số thiếu >= 1, chữ thường thiếu >= 2 (nghe nhầm lẻ 1 âm bỏ qua).
  * CHÈN TRONG SỐ: âm tiết lạ chen giữa cụm số ("ba phìn trăm").
  * NGẮT SAI: lặng giữa hai chữ KHÔNG có dấu câu — >= NGAT_SAI s (trừ trước liên từ/giới từ: người đọc cũng ngắt),
    hoặc >= NGAT_SO s giữa hai chữ của cùng một cụm số ("chín trăm ‖ bảy mươi").
  Tên/từ nước ngoài (Murray, Darling…) không soát — bộ nghe tiếng Việt không ghi được."""
import json
import os
import re
import subprocess
import threading
from difflib import SequenceMatcher


from common import FFMPEG, log

MO_HINH = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"
LAN_DOC_LAI = 3
NGAT_SAI = 0.30
NGAT_SO = 0.20
SO = set("không một mốt hai ba bốn tư năm lăm sáu bảy tám chín mười mươi trăm nghìn ngàn triệu tỷ tỉ linh lẻ rưỡi "
         "phẩy phần".split())
NOI = set("và rồi mà nhưng khi để nhằm thì vốn cùng hay hoặc cũng đã sẽ như nếu lại trước sau khiến từ trong bằng "
          "có ngoài thuộc mang chỉ không buộc sẵn rằng lên tiếp đến với cho của ở tại do vì nên nhờ là thành".split())
_AM = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnpqrstvx])?[aeiouy]+(ch|nh|ng|[cmnpt])?$")
_S = {}
_KHOA = threading.Lock()


def _chuan(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


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


def nghe(wav):
    """[(âm tiết, t0, t1)] bộ nghe ghi được (giây)."""
    import librosa
    import soundfile as sf
    import torch
    pr, md, dev = _may()
    a, sr = sf.read(wav, dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    a = librosa.resample(a, orig_sr=sr, target_sr=16000)
    x = pr(a, sampling_rate=16000, return_tensors="pt").input_values.to(dev)
    with torch.no_grad():
        ids = md(x).logits.argmax(-1)[0].cpu().numpy()
    kq = pr.tokenizer.decode(ids, output_word_offsets=True)
    buoc = 320 / 16000                                       # một khung CTC = 20 ms
    return [(w["word"], w["start_offset"] * buoc, w["end_offset"] * buoc) for w in kq.word_offsets]


def _lang(wav, d=0.2):
    err = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", wav, "-af", f"silencedetect=noise=-38dB:d={d}",
                          "-f", "null", "-"], capture_output=True, timeout=120,
                         creationflags=0x08000000 if os.name == "nt" else 0).stderr.decode("utf-8", "ignore")
    return [(float(e) - float(x), float(e), float(x)) for e, x in
            re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", err)]


def soat_cau(text, wav):
    """Lỗi của một file giọng so với kịch bản: [(loại, mô tả)]."""
    toks = []                                                # (âm tiết, có dấu câu sau, nước ngoài)
    for t in str(text).split():
        phan = [p for p in re.split(r"-", t) if _chuan(p)]
        for k, p in enumerate(phan):
            toks.append((p, k == len(phan) - 1 and bool(re.search(r"[,;:.!?…]$", t)), _ngoai(p)))
    if not toks:
        return []
    w = nghe(wav)
    a, b = [_chuan(t[0]) for t in toks], [_chuan(x[0]) for x in w]
    loi = []
    sm = SequenceMatcher(None, a, b, autojunk=False)
    so = lambda i: 0 <= i < len(a) and toks[i][0].lower() in SO    # noqa: E731
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
    # mốc từng âm tiết kịch bản (chỉ chỗ khớp) -> chỗ lặng nằm ở ranh hai chữ nào
    moc = {}
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            moc[i + k] = (w[j + k][1], w[j + k][2])
    for s0, s1, d in _lang(wav):
        giua = (s0 + s1) / 2
        ranh = [k for k in range(len(toks) - 1) if k in moc and k + 1 in moc and moc[k][1] - 0.15 <= giua <= moc[k + 1][0] + 0.15]
        if not ranh:
            continue
        k = ranh[0]
        if toks[k][1]:
            continue
        sau = toks[k + 1][0].lower()
        if (so(k) and so(k + 1) and d >= NGAT_SO) or (d >= NGAT_SAI and sau not in NOI):
            loi.append(("ngat", f"«{toks[k][0]} ‖ {toks[k + 1][0]}» lặng {d:.2f}s"))
    return loi


def _diem(loi):
    return sum(2 if l_ in ("nuot", "chen") else 1 for l_, _ in loi)


def soat_va_doc_lai(canh, thu_muc, lenh_doc):
    """Soát mọi file giọng <thu_muc>/<id:04d>.wav; câu lỗi đọc lại tối đa LAN_DOC_LAI lượt (seed khác) bằng
    lenh_doc(jobs_json, out_dir, seed) -> mã thoát; giữ bản ít lỗi nhất. Kết quả soát nhớ ở <thu_muc>/_soat.json
    theo (cỡ file, mtime) — chạy lại không soát lại. Trả số câu đã thay bản đọc."""
    p_cache = os.path.join(thu_muc, "_soat.json")
    try:
        with open(p_cache, encoding="utf-8") as f:
            da = json.load(f)
    except (OSError, ValueError):
        da = {}

    def dau(wav):
        st = os.stat(wav)
        return f"{st.st_size}:{int(st.st_mtime)}"

    loi_cua = {}
    for c in canh:
        wav = os.path.join(thu_muc, f"{c['id']:04d}.wav")
        if not os.path.isfile(wav):
            continue
        m = da.get(str(c["id"]))
        if m and m.get("dau") == dau(wav) and m.get("text") == c["text"]:
            loi = [tuple(x) for x in m["loi"]]
        else:
            try:
                loi = soat_cau(c["text"], wav)
            except Exception as e:                           # noqa: BLE001
                log(f"    ! soát giọng cảnh {c['id']} lỗi: {str(e)[:100]}")
                continue
            da[str(c["id"])] = {"dau": dau(wav), "text": c["text"], "loi": loi}
        if loi:
            loi_cua[c["id"]] = loi
    _ghi(p_cache, da)
    if not loi_cua:
        log(f"    soát giọng: {len(canh)} câu, không câu nào nuốt chữ / ngắt sai")
        return 0
    log(f"    soát giọng: {len(loi_cua)}/{len(canh)} câu lỗi "
        f"({sum(1 for v in loi_cua.values() for x in v if x[0] != 'ngat')} chỗ nuốt/méo, "
        f"{sum(1 for v in loi_cua.values() for x in v if x[0] == 'ngat')} chỗ ngắt sai) -> đọc lại tối đa {LAN_DOC_LAI} lượt")
    for cid, loi in sorted(loi_cua.items()):
        log(f"      cảnh {cid}: " + "; ".join(x[1] for x in loi[:3]))
    theo_id = {c["id"]: c for c in canh}
    tot = {cid: (_diem(loi), None, loi) for cid, loi in loi_cua.items()}    # (điểm, file tốt nhất, lỗi)
    tam = os.path.join(thu_muc, "_doc_lai")
    for lan in range(1, LAN_DOC_LAI + 1):
        con = [cid for cid, v in tot.items() if v[0] > 0]
        if not con:
            break
        out = os.path.join(tam, str(lan))
        os.makedirs(out, exist_ok=True)
        jobs = os.path.join(tam, f"jobs_{lan}.json")
        with open(jobs, "w", encoding="utf-8") as f:
            json.dump([{"idx": cid, "text": theo_id[cid]["text"]} for cid in con], f, ensure_ascii=False)
        rc = lenh_doc(jobs, out, 1234 + 7919 * lan)
        if rc != 0:
            log(f"    ! đọc lại lượt {lan} lỗi (mã {rc})")
            break
        for cid in con:
            f_moi = os.path.join(out, f"{cid:04d}.wav")
            if not os.path.isfile(f_moi) or os.path.getsize(f_moi) < 2000:
                continue
            try:
                loi = soat_cau(theo_id[cid]["text"], f_moi)
            except Exception:                                # noqa: BLE001
                continue
            if _diem(loi) < tot[cid][0]:
                tot[cid] = (_diem(loi), f_moi, loi)
    thay = 0
    import shutil
    for cid, (d, f_moi, loi) in tot.items():
        if not f_moi:
            continue
        dich = os.path.join(thu_muc, f"{cid:04d}.wav")
        goc = os.path.join(thu_muc, "_ban_goc", f"{cid:04d}.wav")   # giữ bản đọc đầu tiên (nghe so sánh / khôi phục)
        if not os.path.isfile(goc):
            os.makedirs(os.path.dirname(goc), exist_ok=True)
            shutil.copyfile(dich, goc)
        shutil.copyfile(f_moi, dich)
        da[str(cid)] = {"dau": dau(dich), "text": theo_id[cid]["text"], "loi": loi}
        thay += 1
    _ghi(p_cache, da)
    shutil.rmtree(tam, ignore_errors=True)
    con_loi = [cid for cid, v in tot.items() if v[0] > 0]
    log(f"    soát giọng: thay {thay} câu bằng bản đọc lại tốt hơn; còn {len(con_loi)} câu chưa hết lỗi"
        + (f" (cảnh {', '.join(map(str, con_loi[:15]))})" if con_loi else ""))
    return thay


def _ghi(p, da):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(da, f, ensure_ascii=False)


if __name__ == "__main__":                                   # python soat_giong.py <thư mục giọng> <jobs.json>: chỉ soát, in lỗi
    import sys
    thu, jobs_p = sys.argv[1], sys.argv[2]
    with open(jobs_p, encoding="utf-8") as f:
        jobs = json.load(f)
    n = 0
    for j in jobs:
        wav = os.path.join(thu, f"{j['idx']:04d}.wav")
        loi = soat_cau(j["text"], wav) if os.path.isfile(wav) else []
        if loi:
            n += 1
            print(f"câu {j['idx']:>3}: " + "; ".join(f"[{a}] {b}" for a, b in loi))
    print(f"--- {n}/{len(jobs)} câu có lỗi")
