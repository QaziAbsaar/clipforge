"""Clip edges snap to speech but never shrink below the minimum. Run: python tests/test_snap.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge.segments import snap  # noqa: E402

one = [{"w": "Misses.", "start": 51.7, "end": 52.4}]                 # streamer says one word near the moment
s, e = snap(one, 28.0, 60.0, 12.0, 50.0, 64.0, 30)
assert e - s >= 12 and s <= 28.0 and e >= 60.0, (s, e)
s, e = snap([], 10.0, 30.0, 12.0, 50.0, 100.0, 30)
assert (s, e) == (10.0, 30.0), (s, e)
talk = [{"w": f"w{i}.", "start": i * 0.5, "end": i * 0.5 + 0.4} for i in range(200)]
s, e = snap(talk, 20.0, 40.0, 12.0, 50.0, 100.0, 30)
assert 12 <= e - s <= 50, (s, e)
print("ok")
