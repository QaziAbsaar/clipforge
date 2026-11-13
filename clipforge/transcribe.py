"""Word-level transcription with faster-whisper. Output schema (relative to the wav start):
{"words": [{"w": "hello", "start": 0.12, "end": 0.40}, ...]}"""
import json
import os
import threading
import wave

import numpy as np

DEVICE = os.environ.get("CLIPFORGE_DEVICE", "")   # "cuda" = NVIDIA GPU, much faster when many streams run
_model = None
_loaded = None                # (model, device, compute) of the loaded model
_lock = threading.Lock()      # the web app and live mode may transcribe at the same time


CHUNK, PAD = 600.0, 5.0      # long audio goes in 10-minute pieces so memory stays flat (a 3 h file whole took ~7 GB)


def _load_wav(path, start=0.0, end=None):
    # Window files are 16 kHz mono 16-bit WAVs, so no extra decoder (PyAV) is needed.
    with wave.open(path, "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        a, b = int(start * sr), n if end is None else min(n, int(end * sr))
        w.setpos(min(a, n))
        data = w.readframes(max(b - a, 0))
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


def transcribe_file(wav, model="small", device="cpu", compute="int8", language=None, on_progress=None):
    global _model, _loaded
    if DEVICE:
        device, compute = DEVICE, ("int8" if DEVICE == "cpu" else "float16")
    with _lock:
        if _model is None or _loaded != (model, device, compute):   # reload when Settings change the accuracy
            from faster_whisper import WhisperModel
            _model = WhisperModel(model, device=device, compute_type=compute)
            _loaded = (model, device, compute)
    total = max(wav_seconds(wav), 0.1)
    words, pos = [], 0.0
    while pos < total:
        # each piece reads PAD seconds extra on both sides; a word belongs to the piece it starts in
        off = max(pos - PAD, 0.0)
        audio = _load_wav(wav, off, pos + CHUNK + PAD)
        with _lock:
            segs, _ = _model.transcribe(audio, word_timestamps=True, vad_filter=True,
                                        language=language, condition_on_previous_text=False)
            for s in segs:
                if on_progress:
                    on_progress(min(1.0, (off + s.end) / total))
                for w in (s.words or []):
                    t, st = w.word.strip(), off + w.start
                    if t and pos <= st < pos + CHUNK:
                        words.append({"w": t, "start": round(st, 3), "end": round(off + w.end, 3)})
        pos += CHUNK
    return {"words": words}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["words"]
