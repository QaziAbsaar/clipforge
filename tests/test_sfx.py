"""Auto sound effects land on the right moments. Run: python tests/test_sfx.py"""
import json, os, sys, tempfile

os.environ["CLIPFORGE_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge_web import engine  # noqa: E402

words = [{"w": w, "start": t, "end": t + 0.3} for w, t in
         [("ok", 101.0), ("no", 102.0), ("way", 102.3), ("bro", 104.0), ("look", 108.0), ("wasted", 111.0), ("yo", 111.5)]]
clip = {"start": 100.0, "end": 120.0, "peak": 108.0, "words": json.dumps(words)}
fx = engine.auto_sfx(clip)
got = [(e["f"], e["t"]) for e in fx]
assert got[0] == ("whoosh.wav", 100.0), got
assert ("riser.wav", 106.5) in got and ("boom.wav", 108.0) in got, got
pops = [t for f, t in got if f == "pop.wav"]
assert pops == [102.0, 104.0, 111.0], pops          # 2 s apart, none next to the boom, 'yo' too close to 'wasted'
assert all(100 <= t < 120 for _, t in got)
print("ok")
