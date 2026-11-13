"""Long audio is transcribed in pieces; every word comes back once, in order. Run: python tests/test_transcribe.py"""
import os, sys, tempfile, wave
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge import transcribe as tr  # noqa: E402


class Stub:                                       # "hears" one word at every whole second of the piece it gets
    def transcribe(self, audio, **kw):
        n = len(audio) // 16000
        return [NS(end=n, words=[NS(word=f" w{i}", start=i + 0.1, end=i + 0.5) for i in range(n)])], None


path = os.path.join(tempfile.mkdtemp(), "a.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0\0" * 16000 * 25)
tr._model, tr._loaded, tr.CHUNK, tr.PAD = Stub(), ("base", "cpu", "int8"), 10.0, 2.0
starts = [round(x["start"], 1) for x in tr.transcribe_file(path, "base", "cpu", "int8")["words"]]
assert starts == [i + 0.1 for i in range(25)], starts
print("ok")
