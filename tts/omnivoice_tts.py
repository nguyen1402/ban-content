# -*- coding: utf-8 -*-
"""
omnivoice_tts.py — Engine TTS CỤC BỘ thứ hai: **OmniVoice** (k2-fsa), clone giọng từ
clip mẫu. Chạy bằng PYTHON CỦA VENV riêng `omnivoice-env` (torch 2.8+cu128) — TÁCH khỏi
env chính (torch 2.6) để không phá Demucs/PaddleOCR.

CÙNG GIAO DIỆN CLI + CÙNG FORMAT LOG với piper_tts_local.py, nên `OmniVoiceEngine`
(vieneu_engine.py) tái dùng y nguyên parser tiến độ (`câu#idx: Xs`). Nhờ vậy GUI/dub_stretch
không phải sửa gì: chỉ đổi python+script của subprocess.

Đặc điểm:
  - Model `k2-fsa/OmniVoice` (~613M) + Whisper-large-v3-turbo (tự chép clip mẫu, khỏi
    nhập ref_text). Tải sẵn trong cache HF ở lần chạy đầu.
  - Clone tức thì từ `--ref` (clip 3–10s). Ép `language="Vietnamese"` cho chuẩn nhất.
  - Output **24kHz** wav (v3 là 48kHz) — dub_stretch/ffmpeg đều nhận .wav nên an toàn.

Ref (clip mẫu) mã hoá MỘT lần đầu chạy rồi tái dùng cho mọi câu (Whisper chỉ chạy 1 lần).
"""
import os
import sys
import json
import time
import argparse
import shutil
import subprocess

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ẩn cửa sổ đen tiến trình con (ffmpeg đổi tốc độ) trên Windows.
try:
    import hide_console  # noqa: F401
except Exception:
    pass


def log(msg):
    print(msg, flush=True)


# --- Đổi TỐC ĐỘ nói giữ cao độ bằng ffmpeg atempo (engine tự lập, không dùng chung code) ---
def _atempo_chain(rate):
    parts, r = [], float(rate)
    while r > 2.0:
        parts.append(2.0); r /= 2.0
    while r < 0.5:
        parts.append(0.5); r /= 0.5
    parts.append(r)
    return ",".join(f"atempo={p:.6f}" for p in parts)


def _apply_rate(path, rate):
    try:
        if abs(float(rate) - 1.0) < 1e-3:
            return
    except (TypeError, ValueError):
        return
    tmp = path + ".spd.wav"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", path,
           "-filter:a", _atempo_chain(rate), tmp]
    try:
        subprocess.run(cmd, check=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        os.replace(tmp, path)
    except Exception as e:
        log(f"[omni] ! đổi tốc độ lỗi (giữ nguyên): {e}")
        try:
            os.remove(tmp)
        except OSError:
            pass


# --------------------------------------------------------------------------- #
#  Nạp model + tạo prompt clone giọng (1 lần)
# --------------------------------------------------------------------------- #
_MODEL = None
_PROMPT = None

# OmniVoice mặc định cắt khoảng lặng rồi fade 100ms cuối. Khi bộ ước lượng thời lượng cấp
# thiếu vài frame, 100ms đó chính là âm cuối của câu và bị fade như "nuốt chữ". Wrapper lấy
# waveform thô và tự kiểm tra mép cuối. Không chèn đệm vào file vì dub_stretch dùng chính
# độ dài WAV để giãn video; chỉ 100ms đầu + 250ms cuối trên mỗi câu đã đủ làm lệch cả phim.
SAMPLE_RATE = 24000
TAIL_WINDOW_SEC = 0.06
TAIL_ACTIVITY_RATIO = 0.08
TAIL_MIN_RMS = 8e-4
MIN_AUDIO_SEC = 0.08
MIN_SPEECH_RMS = 5e-4
MIN_SPEECH_PEAK = 2e-3
EMPTY_RETRY_ATTEMPTS = 2
LEAD_FRAME_SEC = 0.02
LEAD_KEEP_SEC = 0.08
LEAD_SILENCE_DB = -50.0
LEAD_SPEECH_REL_DB = 30.0    # lời thật = mạnh hơn (peak của CHÍNH câu - 30dB)
LEAD_EDGE_REL_DB = 45.0      # mép phụ âm đầu: còn trên mức này thì lùi lại, đừng cắt
LEAD_RUN_FRAMES = 3          # phải 60ms liên tiếp mới tính là đã vào lời
LEAD_LOUD_REL_DB = 25.0      # to hơn mức này thì dù CHỈ 1 frame vẫn là lời, không được cắt
LEAD_BACKOFF_FRAMES = 6      # trần lùi 120ms: phụ âm đầu không dài hơn thế, vệt nhiễu thì có

# --- Vệt RÁC mở đầu (cụm ngắn -> im thật -> lời). Xem _drop_lead_blip, đo trên 100 câu thật. ---
# Ngưỡng đặt vào GIỮA hai nhóm, không sát mép: mỗi trục còn dư ~2x biên an toàn.
BLIP_ACTIVE_REL_DB = 35.0    # 'có âm' = trên (đỉnh - 35dB); dùng để chia cụm/khe
BLIP_MAX_SEC = 0.30          # cụm rác đo được 0.04-0.16s; quá dài thì là lời, bỏ qua
BLIP_GAP_MIN_SEC = 0.10      # phải IM THẬT sau cụm (rác 0.12-0.38s); lời không tịt kiểu đó
BLIP_QUIET_REL_DB = 12.0     # rác thấp hơn đỉnh 17.7-28.6dB, lời chỉ 0-3.1dB -> chốt ở 12
BLIP_LOW_HZ = 1000.0         # mốc dải thấp: giọng có thanh dồn năng lượng dưới mức này
BLIP_LOW_RATIO_MAX = 0.50    # rác 0.2-26.4% dưới 1kHz, lời 81.8-98.1% -> chốt ở 50%


# bán-content: KHÔNG sửa chính tả, KHÔNG đổi chữ "nói giảm nói tránh" — máy đọc đúng chữ người dùng viết
# (yêu cầu 11/10/2026). Hai bước này chỉ có ở capcut-tts-api; ở đây cố ý để trống, kể cả khi ai đó chép module sang.
def _sua_chinh_ta(text):
    return text


def _lam_diu(text):
    return text, 0

# Số dài viết bằng chữ: OmniVoice nuốt "trăm/mươi/nghìn" ("hai mươi tám nghìn ba trăm bảy mươi sáu" -> "hai tám ba bảy
# sáu"). Nối gạch các chữ trong cụm số thì đọc đủ: đo 11/10/2026 trên 21 câu thật, 243/243 chữ số đúng (viết rời 223/243).
try:
    from tach_so import noi_gach as _noi_gach_so
except Exception:                                    # pragma: no cover
    def _noi_gach_so(text):
        return text

#: Đếm dồn cả lô để cuối lượt báo MỘT dòng.
DEM_LAM_DIU = [0]


def _text_may_doc(text):
    """Chuỗi ĐƯA VÀO MODEL: sửa chính tả rồi bổ sung dấu kết câu.

    Chỉ dùng cho model. Text gốc vẫn giữ nguyên ở log/SRT — người xem đọc đúng bản dịch,
    chỉ có máy đọc là nhận bản đã nắn phát âm.
    """
    # Làm dịu chạy TRƯỚC bảng chính tả: bảng chính tả đổi mặt chữ ("câm" -> "kâm")
    # thì bảng làm dịu không còn khớp được nữa.
    diu, n = _lam_diu(text)
    DEM_LAM_DIU[0] += n
    return _ensure_terminal_punctuation(_sua_chinh_ta(_noi_gach_so(diu)))


def _ensure_terminal_punctuation(text):
    """Bổ sung dấu kết câu cho model, không thay đổi text gốc dùng ở log/SRT."""
    text = (text or "").strip()
    if not text:
        return text

    closing = '\"\'”’)]}'
    cut = len(text)
    while cut and text[cut - 1] in closing:
        cut -= 1
    body = text[:cut].rstrip()
    suffix = text[cut:]
    if not body:
        return text
    if body[-1] in ".!?…。！？":
        return body + suffix
    if body[-1] in ",;:":
        body = body[:-1].rstrip()
    return body + "." + suffix


# --- Ghim ngẫu nhiên (seed) ---
# OmniVoice greedy ở khâu chọn token (`class_temperature=0.0`) NHƯNG vẫn ngẫu nhiên ở khâu
# chọn VỊ TRÍ: `position_temperature=5.0` -> `_gumbel_sample` gọi `torch.rand_like`
# (omnivoice/models/omnivoice.py). Đo 03/08: cùng câu + cùng clip mẫu ra 1.5s rồi 1.9s, khác file.
# Ghim `torch.manual_seed` khoá đúng nguồn ngẫu nhiên đó. KHÔNG làm giọng hay hơn — làm TÁI LẬP.
SEED_DEFAULT = 1234        # BẬT sẵn; --seed -1 = tắt, chạy ngẫu nhiên như bản cũ
RETRY_SEED_STEP = 9973     # bước nhảy seed mỗi lượt đọc lại — xem _bump_seed, KHÔNG được để 0


def _seed(n):
    """Ghim máy sinh số ngẫu nhiên của torch (ghim luôn GPU). n=None -> không ghim."""
    if n is None:
        return
    try:
        import torch
        torch.manual_seed(int(n) & 0x7FFFFFFF)
    except Exception as e:
        log(f"[omni] ! ghim seed lỗi ({e}) -> đọc ngẫu nhiên như bản cũ")


def _bump_seed(seed, k):
    """Seed cho lượt đọc lại thứ k. BẮT BUỘC khác seed lượt đầu: `_retry_tail` đọc lại với y hệt
    tham số và trông cậy HOÀN TOÀN vào ngẫu nhiên để ra bản khác. Ghim cùng seed cho mọi lượt =
    đọc lại ra ĐÚNG bản rỗng/đuôi-còn-âm cũ, tức giết lớp cứu câu trong im lặng."""
    return None if seed is None else seed + RETRY_SEED_STEP * k


def _raw_generate_kwargs(num_step):
    """Tắt trim/fade/pad mặc định để không làm mất âm nhỏ ở đuôi câu."""
    return {
        "num_step": num_step,
        "postprocess_output": False,
        "fade_duration": 0.0,
        "pad_duration": 0.0,
    }


def _generate_raw(text, num_step=32, duration=None, seed=None):
    """Sinh một waveform chưa trim/fade; dùng cả cho chạy lẻ và cứu câu lỗi trong batch."""
    _seed(seed)
    kw = _raw_generate_kwargs(num_step)
    kw.update(text=_text_may_doc(text), language="Vietnamese")
    if duration is not None:
        kw["duration"] = float(duration)
    if _PROMPT is not None:
        kw["voice_clone_prompt"] = _PROMPT
    return _MODEL.generate(**kw)[0]


def _as_mono_float(audio):
    import numpy as np

    wave = np.asarray(audio, dtype=np.float32).squeeze()
    return wave if wave.ndim == 1 else wave.reshape(-1)


def _tail_has_audio(audio, sample_rate=SAMPLE_RATE):
    """True khi 60ms sát EOF vẫn còn năng lượng đáng kể — dấu hiệu câu chạm biên."""
    import numpy as np

    wave = _as_mono_float(audio)
    if wave.size < 2:
        return False
    window = min(wave.size, max(1, int(sample_rate * TAIL_WINDOW_SEC)))
    tail_rms = float(np.sqrt(np.mean(np.square(wave[-window:], dtype=np.float64))))
    all_rms = float(np.sqrt(np.mean(np.square(wave, dtype=np.float64))))
    return tail_rms >= max(TAIL_MIN_RMS, all_rms * TAIL_ACTIVITY_RATIO)


def _tail_activity(audio, sample_rate=SAMPLE_RATE):
    """Điểm tương đối để chọn bản sinh lại có khoảng kết tự nhiên hơn."""
    import numpy as np

    wave = _as_mono_float(audio)
    if wave.size < 2:
        return float("inf")
    window = min(wave.size, max(1, int(sample_rate * TAIL_WINDOW_SEC)))
    tail_rms = float(np.sqrt(np.mean(np.square(wave[-window:], dtype=np.float64))))
    all_rms = float(np.sqrt(np.mean(np.square(wave, dtype=np.float64))))
    return tail_rms / max(all_rms, 1e-9)


def _has_speech(audio, sample_rate=SAMPLE_RATE):
    """Chặn WAV rỗng/toàn im lặng như file 550.wav từng làm ffprobe trả N/A."""
    import numpy as np

    wave = _as_mono_float(audio)
    if wave.size < int(sample_rate * MIN_AUDIO_SEC):
        return False
    rms = float(np.sqrt(np.mean(np.square(wave, dtype=np.float64))))
    peak = float(np.max(np.abs(wave))) if wave.size else 0.0
    return rms >= MIN_SPEECH_RMS and peak >= MIN_SPEECH_PEAK


def _retry_tail(text, audio, num_step=32, seed=None):
    """Cứu audio rỗng và đuôi sát EOF nhưng không tăng duration/tốc độ của câu.
    Mọi lượt đọc lại đều đổi seed (_bump_seed) — ghim y seed thì đọc lại vô nghĩa."""
    candidate = audio
    for attempt in range(1, EMPTY_RETRY_ATTEMPTS + 1):
        if _has_speech(candidate):
            break
        log(f"[omni] audio rỗng/im lặng — đọc lại riêng lần {attempt}/{EMPTY_RETRY_ATTEMPTS}")
        candidate = _generate_raw(text, num_step=num_step, seed=_bump_seed(seed, attempt))
    if not _has_speech(candidate):
        raise RuntimeError("OmniVoice trả audio rỗng/im lặng sau khi đọc lại")

    if not _tail_has_audio(candidate):
        return candidate

    # Sinh lại NGANG tốc độ; chỉ nhận bản mới nếu mép cuối yên hơn. Không ép duration dài
    # thêm vì cách đó làm chậm lời và khiến dub_stretch kéo dài video.
    log("[omni] đuôi còn âm — đọc lại riêng cùng tốc độ")
    # +100 để không đụng dải seed của vòng cứu-audio-rỗng ở trên (cùng câu, khác lý do đọc lại).
    retry = _generate_raw(text, num_step=num_step, seed=_bump_seed(seed, 100))
    if _has_speech(retry) and _tail_activity(retry) < _tail_activity(candidate):
        return retry
    return candidate


def _frame_db(wave, sample_rate):
    """Đường bao dB theo frame 20ms (kèm số mẫu/frame) — dùng để dò điểm vào lời."""
    import numpy as np

    frame_n = max(1, int(sample_rate * LEAD_FRAME_SEC))
    pad = (-wave.size) % frame_n
    padded = np.concatenate((wave, np.zeros(pad, dtype=np.float32))) if pad else wave
    rms = np.sqrt(np.mean(np.square(padded.reshape(-1, frame_n), dtype=np.float64), axis=1))
    return 20.0 * np.log10(np.maximum(rms, 1e-9)), frame_n


def _first_speech_frame(db):
    """Frame vào lời: chuỗi LEAD_RUN_FRAMES frame đủ mạnh, HOẶC một frame rất to đứng sớm hơn.

    Nhánh "một frame rất to" để chừa các câu mở bằng âm bật ngắn (đo tập 01: 92 câu, mạnh
    nhất chỉ kém peak 5dB) — thà bỏ lỡ cắt còn hơn nuốt mất chữ đầu.
    """
    import numpy as np

    peak_db = float(db.max())
    loud = np.flatnonzero(db >= peak_db - LEAD_LOUD_REL_DB)
    first_loud = int(loud[0]) if loud.size else None

    run = 0
    for i, value in enumerate(db):
        run = run + 1 if value >= peak_db - LEAD_SPEECH_REL_DB else 0
        if run >= LEAD_RUN_FRAMES:
            start = i - LEAD_RUN_FRAMES + 1
            return (start if first_loud is None else min(start, first_loud)), peak_db
    return first_loud, peak_db


def _trim_leading_silence(audio, sample_rate=SAMPLE_RATE):
    """Cắt riêng silence ĐẦU, giữ 80ms lấy hơi; tuyệt đối không đụng phần đuôi.

    OmniVoice hay mở câu bằng một vệt nhiễu/hơi rất nhỏ (-36..-48dB) dài 0.1-0.3s rồi IM
    HẲN thêm 0.2-0.5s mới vào lời. Ngưỡng tuyệt đối bắt phải vệt đó và dừng ngay ở 0.04s
    nên coi như không cắt được gì (đo tập 01: 353/1691 câu còn dư >0.2s, tối đa 0.66s).
    Vì vậy dò theo peak của CHÍNH câu + đòi 60ms liên tiếp, rồi lùi lại theo mép để không
    cắt mất phụ âm đầu (s, th, kh...). Không tìm ra lời thì giữ nguyên cách cũ.
    """
    import numpy as np

    wave = _as_mono_float(audio)
    if wave.size < 2:
        return wave.copy()

    db, frame_n = _frame_db(wave, sample_rate)
    speech, peak_db = _first_speech_frame(db)
    if speech is None:
        active = np.flatnonzero(db >= LEAD_SILENCE_DB)
        if not active.size:
            return wave.copy()
        speech = int(active[0])
    else:
        # Vệt nhiễu đầu câu (-39..-48dB) nằm TRÊN ngưỡng mép nên bước lùi đi xuyên qua nó
        # rồi dừng tận 0.04s, nhỏ hơn cả 80ms chừa hơi -> không cắt được gì (86 câu ở tập
        # 01, lùi tới 0.34s). Chặn bằng trần: 638 câu cắt đúng chỉ cần lùi tối đa 0.06s.
        edge_db = max(peak_db - LEAD_EDGE_REL_DB, LEAD_SILENCE_DB)
        limit = max(0, speech - LEAD_BACKOFF_FRAMES)
        while speech > limit and db[speech - 1] >= edge_db:
            speech -= 1

    keep_n = max(0, int(sample_rate * LEAD_KEEP_SEC))
    cut = max(0, speech * frame_n - keep_n)
    return wave[cut:].copy()


def _drop_lead_blip(audio, sample_rate=SAMPLE_RATE):
    """Vứt VỆT RÁC mở đầu: cụm ngắn -> IM THẬT -> rồi mới vào lời.

    Vì sao cần lớp riêng: `_trim_leading_silence` dò theo ĐỘ TO, mà vệt này có khi chỉ thua
    đỉnh 17dB nên lọt qua `LEAD_LOUD_REL_DB=25` (được coi là lời, cấm cắt). Nới ngưỡng đó
    thì cắt mất phụ âm đầu của câu lành — đúng thứ nó sinh ra để chống. Nên KHÔNG đụng vào
    hằng số cũ, chỉ thêm lớp này chạy TRƯỚC nó, bắt theo HÌNH DẠNG + PHỔ TẦN.

    Đo trên 100 câu thật (D:\\hoathinh\\video\\111, giọng OmniVoice) — 8 câu dính, 2 đặc trưng
    tách bạch hoàn toàn, không chồng lấn:
        rác  : nl<1kHz 0.2-26.4% | thấp hơn đỉnh 17.7-28.6 dB  (014 017 027 035 066 075 084 095)
        lời  : nl<1kHz 81.8-98.1% | thấp hơn đỉnh  0.0-3.1 dB  (008 015 048 080 087 091 096 100)
    Giọng có THANH nên nặng ở dải thấp; vệt hơi/nhiễu thì không. Đòi ĐỦ CẢ BỐN điều kiện để
    một câu lành phải sai đồng thời trên hai trục độc lập mới bị cắt oan.
    """
    import numpy as np

    wave = _as_mono_float(audio)
    if wave.size < 2:
        return wave.copy()

    db, frame_n = _frame_db(wave, sample_rate)
    act = db >= db.max() - BLIP_ACTIVE_REL_DB
    if not act.any():
        return wave.copy()

    i = int(np.argmax(act))                 # frame có âm đầu tiên
    j = i
    while j < len(act) and act[j]:
        j += 1                              # hết cụm đầu
    k = j
    while k < len(act) and not act[k]:
        k += 1                              # hết khe im
    if k >= len(act):
        return wave.copy()                  # sau khe không còn gì -> đây là đuôi, không đụng

    f = frame_n / sample_rate
    if (j - i) * f > BLIP_MAX_SEC or (k - j) * f < BLIP_GAP_MIN_SEC:
        return wave.copy()
    if float(db.max() - db[i:j].max()) < BLIP_QUIET_REL_DB:
        return wave.copy()                  # to ngang lời -> là lời, không phải vệt rác

    seg = wave[i * frame_n:j * frame_n]
    if seg.size < 64:
        return wave.copy()
    spec = np.abs(np.fft.rfft(seg * np.hanning(seg.size)))**2
    tong = float(spec.sum())
    if tong <= 0:
        return wave.copy()
    freq = np.fft.rfftfreq(seg.size, 1 / sample_rate)
    if float(spec[freq < BLIP_LOW_HZ].sum() / tong) > BLIP_LOW_RATIO_MAX:
        return wave.copy()                  # nặng dải thấp = có thanh = lời thật

    keep_n = max(0, int(sample_rate * LEAD_KEEP_SEC))
    cut = max(0, k * frame_n - keep_n)      # cắt tới đầu lời, vẫn chừa 80ms lấy hơi
    log(f"[omni] bỏ vệt rác đầu câu {cut / sample_rate:.2f}s (cụm {(j - i) * f:.2f}s + im {(k - j) * f:.2f}s)")
    return wave[cut:].copy()


def _finish_audio(audio, sample_rate=SAMPLE_RATE):
    """Chỉ bỏ silence đầu gây trễ; không pad/fade/trim đuôi và không làm chậm lời."""
    return _trim_leading_silence(_drop_lead_blip(audio, sample_rate), sample_rate)


def _remove_stale_output(path):
    """Nếu sinh lại thất bại, không để WAV rỗng cũ bị hiểu nhầm là kết quả mới."""
    try:
        os.remove(path)
    except OSError:
        pass


def _cache_path(ref):
    """File cache prompt giọng cạnh clip mẫu: voices/<tên>.wav -> voices/<tên>.wav.omni.pt"""
    return (ref + ".omni.pt") if ref else None


def _cache_valid(ref, cache):
    """Cache còn dùng được nếu tồn tại và MỚI HƠN clip mẫu (cắt lại clip -> cache hết hạn)."""
    try:
        return os.path.isfile(cache) and os.path.getmtime(cache) >= os.path.getmtime(ref)
    except OSError:
        return False


def _ensure_model(ref, device):
    """Nạp OmniVoice + prompt giọng. CACHE prompt (.omni.pt) để LẦN SAU khỏi chạy Whisper:
    cache hợp lệ -> nạp thẳng prompt, KHÔNG nạp Whisper (nhẹ + nhanh). Chỉ chạy 1 lần/tiến trình."""
    global _MODEL, _PROMPT
    if _MODEL is not None:
        return
    import torch
    from omnivoice import OmniVoice, VoiceClonePrompt
    dev = "cuda:0" if str(device).startswith("cuda") else str(device)
    cache = _cache_path(ref)
    use_cache = bool(ref) and _cache_valid(ref, cache)
    need_asr = bool(ref) and not use_cache      # CHỈ nạp Whisper khi phải chép clip mẫu

    t0 = time.time()
    log("[omni] nạp OmniVoice" + (" + Whisper (chép clip mẫu lần đầu)" if need_asr
        else " (prompt giọng đã cache — KHỎI Whisper)" if use_cache else "") + "…")
    _MODEL = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice", device_map=dev, dtype=torch.float16, load_asr=need_asr)
    log(f"[omni] sẵn sàng sau {time.time()-t0:.0f}s | 24kHz")
    if not ref:
        return

    if use_cache:
        try:
            t0 = time.time()
            _PROMPT = VoiceClonePrompt.load(cache)
            log(f"[omni] nạp prompt giọng từ cache ({time.time()-t0:.1f}s, bỏ qua Whisper)")
            return
        except Exception as e:
            log(f"[omni] ! cache prompt hỏng ({str(e)[:40]}) — tạo lại…")
            try:
                _MODEL.load_asr_model()   # model nạp không kèm Whisper -> nạp bù để chép
            except Exception:
                pass

    # Cache miss / hỏng: chép clip mẫu bằng Whisper rồi LƯU cache cho lần sau.
    t0 = time.time()
    _PROMPT = _MODEL.create_voice_clone_prompt(ref_audio=ref)   # ref_text=None -> Whisper chép
    log(f"[omni] mã hoá clip mẫu xong ({time.time()-t0:.1f}s)")
    try:
        _PROMPT.save(cache)
        log(f"[omni] đã lưu cache prompt giọng: {os.path.basename(cache)}")
    except Exception as e:
        log(f"[omni] ! lưu cache prompt lỗi (bỏ qua): {str(e)[:40]}")


def _synth(text, out_path, rate, num_step=32, seed=None):
    """Sinh 1 câu -> wav 24kHz, rồi đổi tốc độ nếu cần."""
    import soundfile as sf
    _remove_stale_output(out_path)
    audio = _retry_tail(text, _generate_raw(text, num_step, seed=seed), num_step, seed=seed)
    sf.write(out_path, _finish_audio(audio), SAMPLE_RATE)
    _apply_rate(out_path, rate)


def _synth_batch(texts, outs, rate, num_step=32, seed=None):
    """Sinh CẢ LÔ trong 1 lượt generate (song song trên GPU).
    Đã đo: độ dài từng câu batch ≈ chạy lẻ, câu ngắn KHÔNG phình (khác batch v3).

    BATCH ĐÁNG GIÁ TỚI ~16 RỒI THÔI (đo 03/08/2026, RTX 3060, num_step=16, 200 câu thật,
    CÓ _sort_jobs_by_length):
        batch 8 -> 135.7s | 16 -> 107.4s (1.26x) | 32 -> 106.1s | 50 -> 105.5s (1.29x)
    Lãi ăn hết ở nấc 8->16; từ 16 lên 50 chỉ thêm 2% nhưng VRAM thì vẫn tăng thẳng.
    Đỉnh VRAM đo trong tiến trình: batch 4=3.1GB, 8=3.8GB, 16=5.1GB, 50=8.4-9.2GB.
    Card 12GB mà Windows đã giữ ~3GB -> batch 50 chạm trần.

    CẢNH BÁO khi lô nhỏ hơn batch: cả tập gói vào MỘT lô ôm trọn dải dài-ngắn, đệm theo
    câu dài nhất nên phí rất nặng (đo: 50 câu/batch 50 = 365.7s, chậm 2.7x so với batch 8).
    Sắp xếp theo độ dài chỉ cứu được khi có NHIỀU lô.

    Tổng thời lượng âm ra GIỐNG NHAU ở mọi batch (364.6-365.6s trên 200 câu, 0 câu hỏng)
    -> batch thuần túy là cần gạt tốc độ/VRAM, không đụng gì tới chất lượng."""
    import soundfile as sf
    for out in outs:
        _remove_stale_output(out)
    synth_texts = [_text_may_doc(text) for text in texts]
    kw = _raw_generate_kwargs(num_step)
    kw.update(text=synth_texts, language=["Vietnamese"] * len(texts))
    if _PROMPT is not None:
        kw["voice_clone_prompt"] = [_PROMPT] * len(texts)
    # Ghim MỘT lần cho cả lô: generate tiêu thụ số ngẫu nhiên đan xen giữa các câu nên không
    # ghim riêng từng câu được. Đổi cỡ lô -> cùng seed vẫn ra khác (giống batch v3).
    _seed(seed)
    audios = _MODEL.generate(**kw)
    for k, (text, au, out) in enumerate(zip(texts, audios, outs)):
        au = _retry_tail(text, au, num_step, seed=None if seed is None else seed + k)
        sf.write(out, _finish_audio(au), SAMPLE_RATE)
        _apply_rate(out, rate)


def _gop_cau_trung(jobs):
    """Câu TRÙNG CHỮ chỉ đọc một lần (yêu cầu 24/09/2026): trả (việc phải đọc, {idx gốc:
    [idx dùng chung]}). So sau khi gộp khoảng trắng; hoa/thường và dấu câu vẫn tính là
    khác vì đổi ngữ điệu. Câu gốc = lần xuất hiện ĐẦU TIÊN."""
    nhom = {}
    for j in jobs:
        nhom.setdefault(" ".join(str(j.get("text") or "").split()), []).append(j)
    viec = [ds[0] for ds in nhom.values()]
    ban_sao = {int(ds[0]["idx"]): [int(x["idx"]) for x in ds[1:]]
               for ds in nhom.values() if len(ds) > 1}
    return viec, ban_sao


def _sort_jobs_by_length(jobs):
    """Gom câu có độ dài gần nhau vào cùng batch, vẫn giữ nguyên idx để đặt đúng tên file SRT."""
    return sorted(jobs, key=lambda job: len((job.get("text") or "").strip()))


# --------------------------------------------------------------------------- #
#  CLI (hợp đồng chung của engine local: --text/--out và --jobs-json/--out-dir)
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="OmniVoice TTS cục bộ, clone giọng từ clip mẫu.")
    ap.add_argument("--text", help="Chế độ 1 câu: nội dung cần đọc.")
    ap.add_argument("--out", help="Chế độ 1 câu: file wav ra.")
    ap.add_argument("--jobs-json", help="Chế độ SRT: JSON [{idx,text}] cần đọc.")
    ap.add_argument("--out-dir", help="Chế độ SRT: thư mục ghi <idx>.wav.")
    ap.add_argument("--name-fmt", default="{:04d}.wav", help="Định dạng tên file (mặc định {:04d}.wav).")
    ap.add_argument("--ref", default=None, help="Clip mẫu giọng (3–10s). Bỏ trống = giọng model tự chọn.")
    ap.add_argument("--voice", default=None, help="Bỏ qua (giữ cho khớp CLI v3).")
    ap.add_argument("--temperature", type=float, default=0.5, help="Bỏ qua (OmniVoice dùng mặc định tinh chỉnh sẵn).")
    ap.add_argument("--rate", type=float, default=1.0, help="Tốc độ nói (giữ cao độ), >1 nhanh hơn.")
    ap.add_argument("--batch", type=int, default=8, help="Số câu sinh CÙNG lô trên GPU (nhanh ~1.7×; VRAM ~4GB ở lô 6). 1 = tuần tự.")
    # KHÔNG khóa vào 16/24/32 nữa: đó chỉ là 3 mốc gợi ý, model nhận số bước bất kỳ.
    # Khóa lại thì không dò được các mức ở giữa (17, 18, 20…) để tìm điểm ngọt.
    # Mặc định 24: người dùng nghe A/B 32/24/16/8 (03/08/2026) và chốt 24 là đủ chất,
    # trong khi nhanh hơn 32 khoảng 1.27x (mỗi bước ~1.3s cho lô 16 câu, đo trên 3060).
    ap.add_argument("--num-step", type=int, default=24,
                    help="Số bước sinh OmniVoice (số nguyên bất kỳ >=1; gợi ý: "
                         "16 nhanh, 24 cân bằng — mặc định, 32 chất lượng).")
    ap.add_argument("--device", default="cuda", help="cuda | cpu.")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT,
                    help=f"Ghim ngẫu nhiên -> render lại RA Y HỆT (mặc định {SEED_DEFAULT}). "
                         f"Đổi số = đổ lại xúc xắc, ra lượt đọc khác. -1 = tắt ghim.")
    args = ap.parse_args(argv)

    ref = args.ref if (args.ref and os.path.isfile(args.ref)) else None
    if args.ref and not ref:
        log(f"[omni] ! không thấy clip mẫu '{args.ref}' — dùng giọng model tự chọn.")

    seed = None if args.seed < 0 else args.seed
    log(f"[omni] seed = {seed if seed is not None else 'TẮT (ngẫu nhiên mỗi lượt)'}")

    # ---- Chế độ 1 câu ----
    if args.text is not None:
        if not args.out:
            log("[omni] ! thiếu --out."); return 2
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        _ensure_model(ref, args.device)
        t0 = time.time()
        _synth(args.text, args.out, args.rate, args.num_step, seed=seed)
        log(f"[omni] 1/1 câu#1: {time.time()-t0:.1f}s")
        return 0

    # ---- Chế độ SRT (jobs-json) ----
    if args.jobs_json:
        if not args.out_dir:
            log("[omni] ! thiếu --out-dir."); return 2
        with open(args.jobs_json, encoding="utf-8") as f:
            jobs = json.load(f)
        os.makedirs(args.out_dir, exist_ok=True)
        _ensure_model(ref, args.device)
        jobs = [j for j in jobs if (j.get("text") or "").strip()]
        total = len(jobs)
        bs = max(1, int(args.batch))
        jobs, ban_sao = _gop_cau_trung(jobs)
        if ban_sao:
            n_sao = sum(len(v) for v in ban_sao.values())
            log(f"[omni] {n_sao} câu TRÙNG chữ với câu khác -> đọc 1 lần rồi dùng chung "
                f"(còn {len(jobs)}/{total} câu phải đọc)")
        jobs = _sort_jobs_by_length(jobs)
        if total > 1:
            log(f"[omni] xếp {len(jobs)} câu theo độ dài trước khi chia lô | batch={bs} | num_step={args.num_step}")
        ok = 0
        done = 0

        def _dung_chung(idx, loi=None):
            """Chép file vừa đọc sang các câu trùng chữ (log y như câu đọc thật để GUI
            đếm đủ tiến độ). `loi` = câu gốc hỏng -> các bản sao cũng báo hỏng."""
            nonlocal ok, done
            goc = os.path.join(args.out_dir, args.name_fmt.format(idx))
            for x in ban_sao.get(idx, []):
                done += 1
                dich = os.path.join(args.out_dir, args.name_fmt.format(x))
                try:
                    if loi is not None:
                        raise RuntimeError(loi)
                    _remove_stale_output(dich)
                    shutil.copyfile(goc, dich)
                    ok += 1
                    log(f"[omni] {done}/{total} câu#{x}: 0.0s (dùng chung câu#{idx})")
                except Exception as e:
                    log(f"[omni] ! câu#{x} lỗi, bỏ qua: {e}")
        for i in range(0, len(jobs), bs):
            chunk = jobs[i:i + bs]
            idxs = [int(j["idx"]) for j in chunk]
            texts = [j["text"].strip() for j in chunk]
            outs = [os.path.join(args.out_dir, args.name_fmt.format(x)) for x in idxs]
            t0 = time.time()
            try:
                # Seed theo VỊ TRÍ lô -> chạy lại cả file ra y hệt.
                seed_lo = None if seed is None else seed + i
                if len(chunk) == 1:
                    _synth(texts[0], outs[0], args.rate, args.num_step, seed=seed_lo)
                else:
                    _synth_batch(texts, outs, args.rate, args.num_step, seed=seed_lo)
                dt = (time.time() - t0) / len(chunk)   # chia đều cho log tiến độ
                for idx in idxs:
                    done += 1
                    ok += 1
                    log(f"[omni] {done}/{total} câu#{idx}: {dt:.1f}s")
                    _dung_chung(idx)
            except Exception as e:
                # Cả lô lỗi -> lùi về TỪNG CÂU (một câu hỏng không kéo cả lô).
                log(f"[omni] ! lô lỗi ({e}) — đọc lại từng câu…")
                for idx, text, out in zip(idxs, texts, outs):
                    done += 1
                    t1 = time.time()
                    try:
                        _synth(text, out, args.rate, args.num_step)
                        ok += 1
                        log(f"[omni] {done}/{total} câu#{idx}: {time.time()-t1:.1f}s")
                        _dung_chung(idx)
                    except Exception as e2:
                        log(f"[omni] ! câu#{idx} lỗi, bỏ qua: {e2}")
                        _dung_chung(idx, loi=e2)
        log(f"[omni] XONG {ok}/{total} câu -> {args.out_dir}")
        return 0

    log("[omni] ! cần --text/--out hoặc --jobs-json/--out-dir.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
