# -*- coding: utf-8 -*-
"""CĂN GIỜ TỪNG CHỮ theo GIỌNG ĐỌC THẬT (12/10 user: thẻ ảnh highlight hiện/ẩn chưa khớp lời — giờ câu trong cảnh trước
đây chia theo số chữ, lệch vài giây). Cắt giọng của từng cảnh từ giong_doc.wav, chạy wav2vec2 CTC tiếng Việt
(nguyenvulebinh/wav2vec2-base-vietnamese-250h, GPU), căn bắt buộc (torchaudio forced_align) với chính lời cảnh
-> mốc [bắt đầu, kết thúc] (giây, tính từ đầu cảnh) cho TỪNG TOKEN (tách theo khoảng trắng) của c["text"] — đúng khuôn
c["moc_tu"] mà tao_srt của dung_hoan_chinh dùng. Cache ra/<dự án>/moc_tu.json theo lời + giờ cảnh."""
import hashlib
import os
import re
import unicodedata

from common import doc_json, ghi_json, log

MO_HINH = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"
_M = {}


def _nap():
    if not _M:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        pr = Wav2Vec2Processor.from_pretrained(MO_HINH)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        _M.update(pr=pr, m=Wav2Vec2ForCTC.from_pretrained(MO_HINH).to(dev).eval(), dev=dev, t=torch,
                  vocab=pr.tokenizer.get_vocab())
    return _M


def _chu_token(tok):
    """Ký tự đưa vào căn của một token: thường hoá, NFC, số -> chữ (đọc số), bỏ ký tự ngoài bảng."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tts"))
    t = unicodedata.normalize("NFC", tok.lower())
    if re.search(r"\d", t):
        try:
            import tach_so
            t = tach_so.noi_gach(t).replace("-", " ")
        except Exception:                                    # noqa: BLE001
            pass
    V = _nap()["vocab"]
    return [ch for ch in t if ch in V and ch != "|"] + ([] if " " not in t else [])


def can_canh(am, sr, text):
    """am: mảng float32 mono của giọng cảnh. Trả [[bd, kt]] cho từng token của text (None nếu căn hỏng)."""
    import numpy as np
    import torchaudio.functional as AF
    M = _nap()
    torch = M["t"]
    if sr != 16000:
        import librosa
        am = librosa.resample(am, orig_sr=sr, target_sr=16000)
    toks = text.split()
    nhom = [_chu_token(t) for t in toks]
    nhan, chi = [], []                                      # chuỗi đích + token sở hữu từng ký tự
    for k, g in enumerate(nhom):
        if not g:
            continue
        if nhan:
            nhan.append(M["vocab"]["|"])
            chi.append(-1)
        for ch in g:
            nhan.append(M["vocab"][ch])
            chi.append(k)
    if not nhan:
        return None
    x = M["pr"](am, sampling_rate=16000, return_tensors="pt").input_values.to(M["dev"])
    with torch.no_grad():
        lp = torch.log_softmax(M["m"](x).logits.float(), dim=-1).cpu()
    T = lp.shape[1]
    if T < len(nhan):
        return None
    di, _ = AF.forced_align(lp, torch.tensor([nhan], dtype=torch.int32), blank=M["pr"].tokenizer.pad_token_id)
    di = di[0].tolist()
    giay = len(am) / 16000 / T                               # giây mỗi khung logits (~0,02)
    # gán khung cho từng ký tự đích theo thứ tự xuất hiện (bỏ blank, gộp lặp)
    vt, truoc, moc = -1, None, {}
    for f, tk in enumerate(di):
        if tk == M["pr"].tokenizer.pad_token_id:
            truoc = None
            continue
        if tk != truoc:
            vt += 1
        truoc = tk
        if 0 <= vt < len(chi) and chi[vt] >= 0:
            a, b = moc.get(chi[vt], (f, f))
            moc[chi[vt]] = (min(a, f), max(b, f))
    ra, cuoi = [], 0.0
    for k in range(len(toks)):
        if k in moc:
            a, b = moc[k]
            ra.append([round(a * giay, 3), round((b + 1) * giay, 3)])
            cuoi = ra[-1][1]
        else:                                                # token không đọc (dấu gạch, ký hiệu): dính token trước
            ra.append([cuoi, cuoi])
    del np
    return ra


def gan_moc(du_an, canh, wav):
    """Điền c["moc_tu"] cho mọi cảnh (kiểu mới). Trả số cảnh căn được."""
    import soundfile as sf
    from common import thu_muc_du_an
    out = thu_muc_du_an(du_an)[1]
    cache = os.path.join(out, "moc_tu.json")
    da = doc_json(cache, {}) or {}
    am_toan, sr = None, None
    n = 0
    for c in canh:
        k = hashlib.md5(f"{c['text']}|{c['bat_dau']:.3f}|{c['dai']:.3f}".encode("utf-8")).hexdigest()[:16]
        if k not in da:
            if am_toan is None:
                am_toan, sr = sf.read(wav, dtype="float32")
                if am_toan.ndim > 1:
                    am_toan = am_toan.mean(1)
            a, b = int(c["bat_dau"] * sr), int((c["bat_dau"] + c["dai"]) * sr)
            try:
                da[k] = can_canh(am_toan[a:b], sr, c["text"])
            except Exception as e:                           # noqa: BLE001
                log(f"    ! căn chữ cảnh {c.get('id')}: {str(e)[:80]}")
                da[k] = None
        if da[k] and len(da[k]) == len(c["text"].split()):
            c["moc_tu"] = da[k]
            n += 1
    ghi_json(cache, da)
    log(f"    căn giờ từng chữ theo giọng đọc: {n}/{len(canh)} cảnh")
    return n
