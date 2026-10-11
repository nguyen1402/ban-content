# -*- coding: utf-8 -*-
"""
capcut_tts_core.py — Engine TTS dùng lại capcut_common_task_client.

Điểm mới so với bản trước:
  - Tự sinh device ngẫu nhiên (device_id / iid / tdid) và xoay device khi gặp
    shark block (ret = -6), rồi thử lại.
  - Xử lý đa luồng (mặc định 5 luồng) cho cả file SRT.

Đặt file này cùng thư mục với capcut_common_task_client.py.
"""
import json
import os
import random
import re
import subprocess
import hide_console  # noqa: F401 — ẩn cửa sổ đen ffmpeg/ffprobe trên Windows
import threading
import time
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

import requests
import capcut_common_task_client as cap


# ---------------------------------------------------------------------------
# Device: sinh ngẫu nhiên 3 ID kiểu snowflake 19 chữ số (giống mẫu 76xxxxxx...)
# ---------------------------------------------------------------------------
def random_device_id():
    return str(random.randint(7_600_000_000_000_000_000, 7_699_999_999_999_999_999))


def base_device_from(device_json_path=None):
    """Device nền: lấy DEFAULT_DEVICE rồi override bằng file (nếu có)."""
    device = deepcopy(cap.DEFAULT_DEVICE)
    if device_json_path and os.path.exists(device_json_path):
        with open(device_json_path, "r", encoding="utf-8") as f:
            device.update(json.load(f))
    return device


def randomize_device(base):
    """Trả về bản sao của base với 3 thông số nhận dạng được random hoàn toàn."""
    d = deepcopy(base)
    d["device_id"] = random_device_id()
    d["iid"] = random_device_id()
    d["tdid"] = random_device_id()
    return d


def load_voices(path):
    """Đọc Voice.json -> list dict. Bỏ qua bản ghi thiếu voice_type/resource_id."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    voices = []
    for v in data:
        if v.get("voice_type") and v.get("resource_id"):
            voices.append({
                "voice_type": v["voice_type"],
                "resource_id": str(v["resource_id"]),
                "display_name": v.get("display_name") or v["voice_type"],
                "lang": v.get("lang") or v.get("lan") or "",
            })
    return voices


def write_device_json(device, path):
    """Ghi ra device.json gồm các trường người dùng hay quan tâm."""
    keys = ["device_id", "iid", "tdid", "appvr", "version_name",
            "version_code", "lan", "loc", "region"]
    out = {k: device[k] for k in keys if k in device}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out


# ---------------------------------------------------------------------------
# Dựng request từ device in-memory (mượn các hàm của client gốc)
# ---------------------------------------------------------------------------
def _sign(url, device, headers):
    lower = {k.lower(): v for k, v in headers.items()}
    if "sign" not in lower:
        headers["sign"] = cap.make_sign_header(
            url, device["appvr"], lower["device-time"], device["tdid"])
    return headers


def build_tts_new(device, text, voice, resource_id, rate):
    babi, body = cap.tts_new_body([text], voice, resource_id, rate, device)
    body_text = cap.compact_json(body)
    query = cap.common_query(device, babi, include_region=True)
    url = cap.BASE + "/lv/v1/common_task/new?" + urlencode(query)
    headers = _sign(url, device, cap.base_headers(device, body_text, appid=True))
    return url, headers, body_text


def build_tts_query(device, task_id, token):
    body = cap.query_body(task_id, token, "sami_text_to_speech", "")
    body_text = cap.compact_json(body)
    query = cap.common_query(device, None, include_region=False)
    url = cap.BASE + "/lv/v1/common_task/query?" + urlencode(query)
    headers = _sign(url, device, cap.base_headers(device, body_text, appid=True))
    return url, headers, body_text


# ---------------------------------------------------------------------------
# Ngoại lệ riêng cho shark block
# ---------------------------------------------------------------------------
class SharkBlock(RuntimeError):
    pass


class TaskFailed(RuntimeError):
    """Server nhận task nhưng XỬ LÝ HỎNG (status=failed) — khác shark/lỗi mạng. Thường là
    text KHÔNG đọc được (vd lẫn chữ Hán). Thử lại y nguyên hay hỏng đúng chỗ cũ, nên có
    trần riêng để BỎ QUA thay vì thử vô hạn (treo cả loạt)."""
    pass


class Stopped(Exception):
    """Người dùng bấm Dừng — không thử lại."""
    pass


def _post(url, headers, body_text, label):
    resp = requests.post(url, headers=headers, data=body_text.encode("utf-8"), timeout=60)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"[{label}] HTTP {resp.status_code}: {resp.text[:200]}")
    ret = str(data.get("ret", "0"))
    if ret == "-6" or "shark" in str(data.get("errmsg", "")).lower():
        raise SharkBlock(f"[{label}] shark block (ret=-6)")
    if resp.status_code >= 400 or ret not in ("0", "0.0"):
        raise RuntimeError(f"[{label}] ret={ret} errmsg={data.get('errmsg')}")
    return data


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def speed_factor(rate):
    """Chuyển giá trị tốc độ người dùng nhập thành hệ số nhân (float).
       1.1 / '1.1' / '1.1x' / '110%' -> 1.1   (1.0 = tốc độ gốc)
       Giá trị lạ / rỗng -> 1.0
    """
    if rate is None:
        return 1.0
    s = str(rate).strip().lower()
    if not s:
        return 1.0
    try:
        if s.endswith("%"):
            return float(s[:-1]) / 100.0
        if s.endswith("x"):
            s = s[:-1].strip()
        return float(s)
    except ValueError:
        return 1.0


def _atempo_chain(factor):
    """atempo chỉ nhận 0.5–2.0 mỗi lần; nối nhiều tầng để đạt hệ số bất kỳ."""
    parts = []
    f = float(factor)
    while f > 2.0:
        parts.append(2.0); f /= 2.0
    while f < 0.5:
        parts.append(0.5); f /= 0.5
    parts.append(f)
    return ",".join(f"atempo={p:.6f}" for p in parts)


def change_speed(in_path, out_path, factor):
    """Đổi tốc độ audio bằng ffmpeg atempo (giữ nguyên cao độ giọng)."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", in_path, "-filter:a", _atempo_chain(factor),
         out_path, "-loglevel", "error"],
        check=True)
    return out_path


# BỌC NHÁY LÚC ĐỌC (30/09/2026). Bước dịch đã bọc nháy chữ cái lẻ ('a', 'ô', 'y', 'e')
# cho giọng CapCut đọc đúng, nhưng luật "đầu câu SRT chỉ chữ/số" (sach_dau_cau) cắt mất
# nháy của chữ ĐỨNG ĐẦU DÒNG: 'E' là → E là, 'Ô' kìa → Ô kìa (72 + 74 dòng ở 2 phim).
# Đo trên CẢ HAI giọng Thanh Niên Tự Tin (BV075) và Cô Gái Hoạt Ngôn (BV074): không nháy
# thì đọc thành "EM là", "ÔNG kia", "ANH, quả đúng"; có nháy thì đọc đúng "e/ô/à". File
# SRT giữ nguyên (đúng luật đầu câu), chỉ chữ GỬI CHO GIỌNG ĐỌC được bọc lại. Chỉ giọng
# TIẾNG VIỆT (tra Voice.json) — tiếng Anh có "a" đứng lẻ khắp nơi.
_GIONG_VIET = None


def _la_giong_viet(voice):
    global _GIONG_VIET
    if _GIONG_VIET is None:
        try:
            _GIONG_VIET = {v["voice_type"] for v in load_voices(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Voice.json"))
                if v["lang"].lower().startswith("vi")}
        except Exception:
            _GIONG_VIET = set()
    return voice in _GIONG_VIET


def boc_nhay_cho_giong_doc(text, voice):
    if not text or not _la_giong_viet(voice):
        return text
    from srt_translate_core import quote_standalone_letters
    return quote_standalone_letters(text)


class TTSEngine:
    def __init__(self, base_device, voice="BV074_streaming",
                 resource_id="7102355709945188865", rate="1.0",
                 randomize_each=True, max_attempts=0, save_devices_dir=None,
                 task_fail_cap=10):
        self.base_device = base_device
        self.voice = voice
        self.resource_id = resource_id
        # Task đọc THẤT BẠI (status=failed) liên tiếp bao nhiêu lần thì BỎ QUA câu đó thay
        # vì thử vô hạn. Khác shark/mạng (vẫn thử mãi + xoay device). 0 = không cap.
        self.task_fail_cap = task_fail_cap
        # Tốc độ được xử lý cục bộ bằng ffmpeg (server bỏ qua prosody rate).
        self.speed = speed_factor(rate)
        self.rate = "1.0"                         # luôn gửi tốc độ gốc cho API
        self._ffmpeg_ok = has_ffmpeg()
        self._warned_no_ffmpeg = False
        self.randomize_each = randomize_each
        self.max_attempts = max_attempts          # 0 = lặp tới khi được
        self.save_devices_dir = save_devices_dir
        self._save_lock = threading.Lock()

    def _fresh_device(self):
        dev = randomize_device(self.base_device)
        if self.save_devices_dir:
            with self._save_lock:
                os.makedirs(self.save_devices_dir, exist_ok=True)
                write_device_json(
                    dev, os.path.join(self.save_devices_dir, f"device_{dev['device_id']}.json"))
        return dev

    def _initial_device(self):
        return self._fresh_device() if self.randomize_each else deepcopy(self.base_device)

    @staticmethod
    def _sleep_with_stop(seconds, stop_event):
        end = time.time() + seconds
        while time.time() < end:
            if stop_event and stop_event.is_set():
                return
            time.sleep(0.2)

    def _create(self, device, text, voice=None, resource_id=None):
        url, headers, body = build_tts_new(device, text, voice or self.voice,
                                           resource_id or self.resource_id, self.rate)
        task = _post(url, headers, body, "tts-new")["data"]["tasks"][0]
        return task["id"], task["token"]

    def _wait(self, device, task_id, token, timeout=180, interval=2.0, stop_event=None):
        deadline = time.time() + timeout
        while True:
            if stop_event and stop_event.is_set():
                raise Stopped()
            url, headers, body = build_tts_query(device, task_id, token)
            task = _post(url, headers, body, "tts-query")["data"]["tasks"][0]
            status = task.get("status")
            if status == "succeed":
                payload = json.loads(task["payload"])
                subs = payload.get("audio_subtitles") or []
                if not subs or not subs[0].get("speech_url"):
                    raise RuntimeError("Xong nhưng không có speech_url.")
                return subs[0]["speech_url"]
            if status in ("failed", "fail", "error"):
                # MOI lý do THẬT của server ra, đừng để "Task thất bại." trơ trọi (bấy lâu
                # nuốt mất khiến không biết vì sao). Dump các trường nhỏ + lỗi trong payload.
                detail = (task.get("message") or task.get("err_msg")
                          or task.get("error") or task.get("fail_reason") or "")
                if not detail:
                    pl = task.get("payload")
                    if isinstance(pl, str) and pl:
                        try:
                            pj = json.loads(pl)
                            detail = (pj.get("message") or pj.get("error")
                                      or pj.get("err_msg") or pj.get("BaseResp", {}).get(
                                          "StatusMessage") or "")
                        except Exception:
                            detail = pl[:200]
                info = {k: v for k, v in task.items()
                        if k != "payload" and not (isinstance(v, str) and len(v) > 120)}
                raise TaskFailed("Task thất bại."
                                 + (f" → {detail}" if detail else "")
                                 + f"  [server: {info}]")
            if time.time() > deadline:
                raise TimeoutError(f"Quá {timeout}s, trạng thái '{status}'.")
            self._sleep_with_stop(interval, stop_event)

    @staticmethod
    def _download(url, path):
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        return path

    def synth_one(self, text, out_path, on_log=None, stop_event=None,
                  voice=None, resource_id=None):
        """3 bước cho 1 đoạn text. Mọi lỗi đều thử lại tới khi được
        (trừ khi người dùng bấm Dừng, hoặc vượt max_attempts nếu đặt > 0).

        voice/resource_id: ĐÈ giọng cho RIÊNG đoạn này (lồng tiếng theo nhân vật).
        Bỏ trống -> dùng giọng chung của engine, y như trước."""
        log = on_log or (lambda *_: None)
        text = boc_nhay_cho_giong_doc(text, voice or self.voice)
        device = self._initial_device()
        attempt = 0
        task_fails = 0          # số lần server XỬ LÝ HỎNG (không tính shark/mạng)
        while True:
            if stop_event and stop_event.is_set():
                raise Stopped()
            try:
                task_id, token = self._create(device, text, voice, resource_id)
                url = self._wait(device, task_id, token, stop_event=stop_event)
                if abs(self.speed - 1.0) < 1e-3:
                    self._download(url, out_path)
                elif not self._ffmpeg_ok:
                    self._download(url, out_path)
                    if not self._warned_no_ffmpeg:
                        log("   (thiếu ffmpeg → không đổi được tốc độ, giữ tốc độ gốc)")
                        self._warned_no_ffmpeg = True
                else:
                    tmp = out_path + ".raw.mp3"
                    self._download(url, tmp)
                    try:
                        change_speed(tmp, out_path, self.speed)
                    finally:
                        if os.path.exists(tmp):
                            os.remove(tmp)
                if attempt:
                    log(f"   thành công sau {attempt} lần thử lại")
                return out_path
            except Stopped:
                raise
            except SharkBlock as e:
                reason = "shark block"
                device = self._fresh_device()           # đổi device ngay
            except TaskFailed as e:
                # Server xử lý task HỎNG (thường: text không đọc được, vd lẫn chữ Hán).
                # Thử vài lần với device mới phòng khi chỉ trục trặc tạm; hỏng LIÊN TIẾP
                # tới trần thì BỎ QUA câu này (ném lên để synth_srt bắt) — không treo loạt.
                task_fails += 1
                reason = str(e)
                if self.task_fail_cap and task_fails >= self.task_fail_cap:
                    raise RuntimeError(
                        f"Bỏ qua sau {task_fails} lần task đọc thất bại liên tiếp "
                        f"(text có thể không đọc được — vd còn lẫn chữ Hán). {reason}")
                if self.randomize_each:
                    device = self._fresh_device()
            except Exception as e:
                reason = str(e) or e.__class__.__name__
                if self.randomize_each:
                    device = self._fresh_device()        # lấy device mới cho lần sau

            attempt += 1
            if self.max_attempts and attempt >= self.max_attempts:
                raise RuntimeError(f"Hết {self.max_attempts} lần thử: {reason}")
            backoff = min(2.0 + attempt, 15.0)           # nghỉ tăng dần, trần 15s
            log(f"   lỗi ({reason}) → thử lại lần {attempt} sau {backoff:.0f}s")
            self._sleep_with_stop(backoff, stop_event)

    def synth_srt(self, segments, parts_dir, threads=5, on_progress=None,
                  stop_event=None, name_fmt="{:04d}.mp3"):
        """Chạy đa luồng. Trả về list (start_ms, end_ms, file_path) theo thứ tự SRT.

        Mỗi segment có thể mang khóa 'voice' (+ 'resource_id') để đọc bằng giọng
        RIÊNG — dùng cho lồng tiếng theo nhân vật nam/nữ. Thiếu -> giọng chung."""
        os.makedirs(parts_dir, exist_ok=True)
        progress = on_progress or (lambda *_: None)
        results = {}
        done = 0
        total = len(segments)
        lock = threading.Lock()

        def work(i, seg):
            if stop_event and stop_event.is_set():
                raise Stopped()
            if seg.get("skip"):          # câu CỐ Ý bỏ đọc (vd lẫn chữ Hán) -> không có file,
                return i, None           #   bộ ghép tự coi beat đó không có giọng (giữ hình).
            path = os.path.join(parts_dir, name_fmt.format(i + 1))
            self.synth_one(seg["text"], path,
                           on_log=lambda m, n=i: progress(log=f"[{n + 1}]{m}"),
                           stop_event=stop_event,
                           voice=seg.get("voice"), resource_id=seg.get("resource_id"))
            return i, path

        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = {ex.submit(work, i, seg): i for i, seg in enumerate(segments)}
            for fut in as_completed(futs):
                i = futs[fut]
                try:
                    idx, path = fut.result()
                    results[idx] = (segments[idx]["start"], segments[idx]["end"], path)
                    ok = True
                except Exception as e:
                    ok = False
                    progress(error=f"Dòng {i + 1}: {e}")
                with lock:
                    done += 1
                progress(done=done, total=total,
                         text=segments[i]["text"], ok=ok)
                if stop_event and stop_event.is_set():
                    ex.shutdown(wait=False, cancel_futures=True)
                    break

        return [results[i] for i in sorted(results)]


# ---------------------------------------------------------------------------
# SRT + ghép audio
# ---------------------------------------------------------------------------
def _srt_time_to_ms(t):
    t = t.strip().replace(".", ",")
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def parse_srt(text, giu_cau_rong=False):
    """SRT -> [{start, end, text}]. Mặc định BỎ câu không có chữ.

    giu_cau_rong=True: câu rỗng vẫn GIỮ CHỖ dưới dạng {"text": "", "skip": True} để
    file giọng đánh số theo ĐÚNG vị trí câu trong SRT. Bắt buộc khi thư mục giọng
    đánh số sẽ đưa sang dub_stretch — bên đó đếm cả câu rỗng, file N ghép vào câu N.
    Bỏ câu rỗng ở đây thì từ câu rỗng đầu tiên trở đi mọi file lệch lên một câu tới
    hết phim (ca thật 18/09/2026: phim 7685736520170343449, câu 1595 bị ĐỂ TRỐNG
    -> 1595.wav là giọng của câu 1596, …; 2879 file cho 2881 câu).
    """
    segments = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2 and not (giu_cau_rong and lines and "-->" in lines[0]):
            continue
        i = 0 if "-->" in lines[0] else 1
        if i >= len(lines) or "-->" not in lines[i]:
            continue
        start_s, end_s = [x.strip() for x in lines[i].split("-->")]
        body = " ".join(lines[i + 1:]).strip()
        if body:
            segments.append({"start": _srt_time_to_ms(start_s),
                             "end": _srt_time_to_ms(end_s), "text": body})
        elif giu_cau_rong:
            segments.append({"start": _srt_time_to_ms(start_s),
                             "end": _srt_time_to_ms(end_s), "text": "", "skip": True})
    return segments


# Mỗi dòng TXT chiếm bao nhiêu mili giây trên trục giả. Chỉ để giữ THỨ TỰ và để
# các hàm dùng chung (synth_srt / assemble_sequential) không phải biết mình đang
# đọc SRT hay TXT — KHÔNG phải độ dài thật của câu đọc ra.
TXT_SLOT_MS = 2000


def parse_txt_lines(text, slot_ms=TXT_SLOT_MS):
    """File .txt -> segments giống parse_srt: MỖI DÒNG LÀ MỘT CÂU.

    Dòng trống bị bỏ; phần còn lại giữ NGUYÊN VĂN (không gộp, không tách câu theo
    dấu chấm) vì người dùng đã tự xuống dòng đúng chỗ mình muốn ngắt.

    start/end là mốc GIẢ, cách đều nhau: TXT không có thời gian nên chỉ dùng được
    kiểu xuất 'đánh số' và 'nối liền'; đừng đem ghép theo timeline.
    """
    segments = []
    for line in (text or "").splitlines():
        body = line.strip()
        if not body:
            continue
        start = len(segments) * slot_ms
        segments.append({"start": start, "end": start + slot_ms, "text": body})
    return segments


def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def assemble_timeline(seg_files, out_path, attenuate=True, overflow_volume=0.7):
    """Đặt mỗi clip tại mốc start. Nếu clip dài hơn ô (end-start), phần thừa
    bị hạ âm lượng còn `overflow_volume` (mặc định 70%, tức giảm 30%).

    seg_files: list (start_ms, end_ms, file_path)
    """
    inputs, filters, labels = [], [], []
    for n, (start_ms, end_ms, fp) in enumerate(seg_files):
        inputs += ["-i", fp]
        chain = f"[{n}]"
        if attenuate:
            slot_sec = max(0, (end_ms - start_ms)) / 1000.0
            # chỉ áp dụng khi t >= độ dài ô -> phần nằm trong ô giữ nguyên, phần thừa bị hạ
            chain += f"volume={overflow_volume}:enable='gte(t,{slot_sec:.3f})',"
        chain += f"adelay={start_ms}|{start_ms}[d{n}]"
        filters.append(chain)
        labels.append(f"[d{n}]")
    fg = ";".join(filters) + ";" + "".join(labels) + \
        f"amix=inputs={len(seg_files)}:normalize=0:dropout_transition=0[a]"
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", fg,
                    "-map", "[a]", out_path, "-loglevel", "error"], check=True)
    return out_path


def assemble_sequential(seg_files, out_path):
    """Nối các clip liền nhau, bỏ qua khoảng trống. seg_files: list (start, end, path)."""
    list_txt = out_path + ".list.txt"
    with open(list_txt, "w", encoding="utf-8") as f:
        for item in seg_files:
            fp = item[-1]
            f.write(f"file '{os.path.abspath(fp)}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt,
                    "-c", "copy", out_path, "-loglevel", "error"], check=True)
    os.remove(list_txt)
    return out_path
