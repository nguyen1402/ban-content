# -*- coding: utf-8 -*-
"""Chạy Whisper (large-v3-turbo) trên các file giọng, lấy MỐC THỜI GIAN TỪNG TỪ.
Chạy bằng Python của omnivoice-env (transformers 5 + torch cu128), KHÔNG phải env chính.

    python whisper_tu.py vao.json ra.json
      vao.json: [{"id": 1, "wav": "...wav"}, ...]
      ra.json : {"1": [{"w": "trên", "t0": 0.12, "t1": 0.35}, ...], ...}
"""
import json
import sys
import time

import torch
from transformers import pipeline


def main():
    vao = json.load(open(sys.argv[1], encoding="utf-8"))
    t = time.time()
    asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo",
                   torch_dtype=torch.float16, device="cuda")
    print(f"[whisper] nạp model {time.time() - t:.1f}s", flush=True)
    ra = {}
    for i, it in enumerate(vao, 1):
        try:
            kq = asr(it["wav"], return_timestamps="word",
                     generate_kwargs={"language": "vi", "task": "transcribe"})
            ra[str(it["id"])] = [{"w": c["text"].strip(), "t0": round(c["timestamp"][0] or 0.0, 3),
                                  "t1": round(c["timestamp"][1] if c["timestamp"][1] is not None else (c["timestamp"][0] or 0.0), 3)}
                                 for c in kq.get("chunks", []) if c["text"].strip()]
        except Exception as e:                                   # noqa: BLE001
            ra[str(it["id"])] = []
            print(f"[whisper] ! {it['id']}: {str(e)[:120]}", flush=True)
        if i % 20 == 0 or i == len(vao):
            print(f"[whisper] {i}/{len(vao)}", flush=True)
    json.dump(ra, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
