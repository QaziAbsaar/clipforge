"""Word-level transcription with faster-whisper. Output schema (relative to the wav start):
{"words": [{"w": "hello", "start": 0.12, "end": 0.40}, ...]}"""
import json
import threading
import wave

import numpy as np

_model = None
_lock = threading.Lock()      # the web app and live mode may transcribe at the same time


def _load_wav(path):
    # Window files are 16 kHz mono 16-bit WAVs, so no extra decoder (PyAV) is needed.
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_file(wav, model="small", device="cpu", compute="int8", language=None, on_progress=None):
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(model, device=device, compute_type=compute)
    audio = _load_wav(wav)
    total = max(len(audio) / 16000.0, 0.1)
    words = []
    with _lock:
        segs, _ = _model.transcribe(audio, word_timestamps=True, vad_filter=True,
                                    language=language, condition_on_previous_text=False)
        for s in segs:
            if on_progress:
                on_progress(min(1.0, s.end / total))
            for w in (s.words or []):
                t = w.word.strip()
                if t:
                    words.append({"w": t, "start": round(w.start, 3), "end": round(w.end, 3)})
    return {"words": words}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["words"]
