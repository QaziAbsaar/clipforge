"""Face tracking for vertical framing, with a simple active-speaker focus (mouth movement).
Honest limits: classic face detector, works best on clear, front-facing webcam-style faces."""
import subprocess

import numpy as np

_cascade = None


def _detector():
    global _cascade
    if _cascade is None:
        import cv2
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if _cascade.empty():
            raise RuntimeError("Face detector files are missing. Reinstall: pip install \"opencv-python-headless<5\"")
    return _cascade


def _even(v):
    return int(v) // 2 * 2


def crop_width(h):
    return _even(h * 9 / 16)


def _read_frames(ffmpeg, src, start, end, W, H, fps, sw=512):
    sh = _even(round(sw * H / W))
    cmd = [ffmpeg, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", src,
           "-vf", f"fps={fps},scale={sw}:{sh}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (sw * sh)
    return np.frombuffer(raw[: n * sw * sh], dtype=np.uint8).reshape(n, sh, sw), sw / W


def track(ffmpeg, src, W, H, start, end, fps=8, should_stop=None):
    """Returns {'pts': [[t, crop_left_px], ...], 'found': share_of_frames_with_a_face, 'cw': crop_width}.
    t is seconds from the clip start; crop_left_px is the left edge of the 9:16 window in source pixels."""
    import cv2
    cw = crop_width(H)
    frames, scale = _read_frames(ffmpeg, src, start, end, W, H, fps)
    det = _detector()
    min_face = max(20, int(frames.shape[2] * 0.03)) if len(frames) else 20
    tracks, prev, target, last_switch = [], None, None, -99
    raw_targets, found = [], 0
    for i, g in enumerate(frames):
        if should_stop and i % 20 == 0:
            should_stop()
        faces = det.detectMultiScale(g, scaleFactor=1.1, minNeighbors=5, minSize=(min_face, min_face))
        dets = []
        for (x, y, w, h) in faces:
            motion = 0.0
            if prev is not None:                       # mouth area = lower part of the face box
                y0, y1 = y + int(h * 0.6), y + h
                a, b = g[y0:y1, x:x + w].astype(np.int16), prev[y0:y1, x:x + w].astype(np.int16)
                if a.size and a.shape == b.shape:
                    motion = float(np.abs(a - b).mean())
            dets.append({"x": (x + w / 2) / scale, "size": w / scale, "motion": motion})
        for t in tracks:
            t["seen"] = False
        for d in dets:                                 # match detections to known faces by position
            best = min(tracks, key=lambda t: abs(t["x"] - d["x"]), default=None)
            if best is not None and abs(best["x"] - d["x"]) < max(d["size"] * 1.5, 40):
                best["x"], best["size"], best["seen"] = d["x"], d["size"], True
                best["motion"] = 0.7 * best["motion"] + 0.3 * d["motion"]
                best["n"] += 1
            else:
                tracks.append({"x": d["x"], "size": d["size"], "motion": d["motion"], "seen": True, "n": 1, "miss": 0})
        for t in tracks:
            t["miss"] = 0 if t["seen"] else t["miss"] + 1
        tracks = [t for t in tracks if t["miss"] < fps * 2]
        visible = [t for t in tracks if t["seen"]]
        if visible:
            found += 1
            cur = target if target in visible else None
            if cur is None:
                target = max(visible, key=lambda t: t["size"] * (1 + t["motion"]))
                last_switch = i
            else:
                top = max(visible, key=lambda t: t["motion"])
                if top is not cur and top["n"] >= 3 and top["motion"] > 1.6 * cur["motion"] + 0.6 \
                        and i - last_switch >= fps * 1.2:
                    target, last_switch = top, i
            raw_targets.append(target["x"])
        else:
            raw_targets.append(None)
        prev = g
    # fill gaps: hold the last position for ~3 s, then drift back to centre
    out, last, gap = [], None, 0
    for t in raw_targets:
        if t is not None:
            last, gap = t, 0
        else:
            gap += 1
            if gap > fps * 3:
                last = W / 2
        out.append(last if last is not None else W / 2)
    # camera smoothing with a dead zone so it doesn't jitter
    cam = out[0] if out else W / 2
    pts = []
    dead = 0.10 * cw
    for i, tx in enumerate(out):
        if abs(tx - cam) > dead:
            cam += (tx - cam) * 0.3
        left = min(max(cam - cw / 2, 0), W - cw)
        pts.append([round(i / fps, 3), round(left, 1)])
    return {"pts": pts, "found": (found / len(frames)) if len(frames) else 0.0, "cw": cw}


def write_sendcmd(pts, path, out_fps=30):
    """FFmpeg 'sendcmd' file that moves the crop window smoothly (one command per output frame, changes only)."""
    if not pts:
        return 0
    ts = np.array([p[0] for p in pts]); xs = np.array([p[1] for p in pts])
    end = ts[-1] + 1.0 / 8
    lines, last = [], None
    for t in np.arange(0, end, 1.0 / out_fps):
        x = _even(np.interp(t, ts, xs))
        if x != last:
            lines.append(f"{t:.3f} crop x {x};")
            last = x
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return _even(xs[0])


TOP_SHARE = 0.4                        # stacked layout: facecam gets the top 40% of the 9:16 frame, gameplay the rest
PIP_SIZE, PIP_TOP = 0.5, 0.03          # pip layout: facecam box width and top gap, as share of the frame
STILL = 10                             # pixel brightness spread (0-255) below which a spot counts as still


def cam_rect(frames, cx, cy, fw):
    """Edges of the facecam overlay around a face, in frame px, as (x0, y0, x1, y1), or None if unclear.
    The streamer's room barely changes while the gameplay around it keeps moving, so the overlay is the
    still area that surrounds the face. Fails (None) on borderless or green-screen cams and frozen gameplay."""
    import cv2
    if len(frames) < 5:
        return None
    fh, fwid = frames.shape[1:]
    still = (frames.std(axis=0) < STILL).astype(np.uint8)
    still = cv2.morphologyEx(still, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))   # break thin links to static HUD bits
    n, labels, stats, _ = cv2.connectedComponentsWithStats(still, connectivity=4)
    r = fw / 2
    wx0, wx1 = int(max(cx - 3 * r, 0)), int(min(cx + 3 * r, fwid))
    wy0, wy1 = int(max(cy - 3 * r, 0)), int(min(cy + 2 * r, fh))
    near = labels[wy0:wy1, wx0:wx1]
    ids, counts = np.unique(near[near > 0], return_counts=True)
    keep = [i for i, c in zip(ids, counts) if c >= 0.05 * near.size]
    if not keep:
        return None
    x0, y0 = min(stats[i, 0] for i in keep), min(stats[i, 1] for i in keep)
    x1 = max(stats[i, 0] + stats[i, 2] for i in keep)
    y1 = max(stats[i, 1] + stats[i, 3] for i in keep)
    x0, y0, x1, y1 = min(x0, cx - r), min(y0, cy - r), max(x1, cx + r), max(y1, cy + r)
    w, h = x1 - x0, y1 - y0
    if not (0.6 <= w / h <= 2.6) or w * h > 0.35 * fwid * fh or w > 8 * fw:
        return None                                       # merged with other static stuff; don't trust it
    return x0 + 1, y0 + 1, x1 - 1, y1 - 1                 # 1px inside so no gameplay line leaks in


def find_facecam(ffmpeg, src, W, H, start, end, out_w=1080, out_h=1920):
    """Gaming streams: find a fixed facecam overlay. Returns {'cam': [x, y, w, h] | None, 'box': ..., 'kind': ...}
    in source px. 'box' is the whole overlay (pip layout); 'cam' is the part of it that fits the stacked top panel.
    kind 'facecam' = small steady face (overlay), 'camera' = big face (talking head, use follow instead), 'none'."""
    frames, scale = _read_frames(ffmpeg, src, start, end, W, H, fps=1)
    det = _detector()
    hits = []
    for g in frames:
        min_face = max(16, int(g.shape[1] * 0.025))
        faces = det.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(min_face, min_face))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2])
            hits.append((x + w / 2, y + h / 2, w))
    if len(frames) == 0 or len(hits) < max(2, 0.3 * len(frames)):
        return {"cam": None, "box": None, "kind": "none"}
    fx, fy, ff = (float(np.median([h[i] for h in hits])) for i in range(3))
    cx, cy, fw = fx / scale, fy / scale, ff / scale
    if fw > 0.22 * W:
        return {"cam": None, "box": None, "kind": "camera"}
    rect = cam_rect(frames, fx, fy, ff)
    if rect:
        bx, by = rect[0] / scale, rect[1] / scale
        bw, bh = (rect[2] - rect[0]) / scale, (rect[3] - rect[1]) / scale
    else:                                                 # guess the overlay from the face size
        bw, bh = min(fw * 3.6, W * 0.5), min(fw * 2.2, H)
        bx, by = min(max(cx - bw / 2, 0), W - bw), min(max(cy - bh * 0.45, 0), H - bh)
    aspect = out_w / (out_h * TOP_SHARE)                   # shape of the top panel: cut it out of the overlay
    cw, ch = (bh * aspect, bh) if bw / bh > aspect else (bw, bw / aspect)
    x = min(max(cx - cw / 2, bx), bx + bw - cw)
    y = min(max(cy - ch * 0.45, by), by + bh - ch)       # face a little above the panel centre
    return {"cam": [_even(x), _even(y), _even(cw), _even(ch)],
            "box": [_even(bx), _even(by), _even(bw), _even(bh)], "kind": "facecam", "exact": bool(rect)}
