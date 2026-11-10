"""Facecam overlay edges found from the still room around the face. Run: python tests/test_facecam.py"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge.faces import cam_rect

rng = np.random.default_rng(0)
frames = rng.integers(0, 256, (30, 288, 512), dtype=np.uint8)        # busy gameplay
room = rng.integers(0, 256, (80, 140), dtype=np.uint8)               # still webcam background
frames[:, 20:100, 340:480] = room
for i, f in enumerate(frames):                                       # streamer moves a little
    x = 400 + (i % 5) * 2
    f[45:80, x - 10:x + 10] = rng.integers(0, 256, (35, 20))
frames[:, 250:270, 10:200] = 128                                     # static HUD bar far away

r = cam_rect(frames, 410, 55, 20)
assert r and all(abs(a - b) <= 2 for a, b in zip(r, (341, 21, 479, 99))), r

assert cam_rect(np.full((30, 288, 512), 90, np.uint8), 410, 55, 20) is None    # frozen picture: no edge
noisy = rng.integers(0, 256, (30, 288, 512), dtype=np.uint8)
assert cam_rect(noisy, 410, 55, 20) is None                                    # green-screen cam: nothing still
print("ok")
