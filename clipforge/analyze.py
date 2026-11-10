"""Stage 1: find exciting moments cheaply (no transcription): loudness spikes,
YouTube 'most replayed' heatmap, optional chat-message timestamps."""
import numpy as np

FRAME = 0.5  # seconds per analysis frame
SR = 16000


def loudness_db(raw_path):
    n = int(SR * FRAME)
    out = []
    with open(raw_path, "rb") as f:
        while True:
            buf = np.frombuffer(f.read(n * 2 * 2000), dtype=np.int16)
            if buf.size < n:
                break
            m = buf.size // n
            a = buf[: m * n].astype(np.float32).reshape(m, n) / 32768.0
            out.append(20 * np.log10(np.sqrt((a ** 2).mean(1)) + 1e-6))
    return np.concatenate(out) if out else np.zeros(1)


def _smooth(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode="same")


def audio_score(db):
    """How far above the local (60 s) baseline is the loudness, smoothed over 4 s."""
    blk = int(60 / FRAME)
    centers, meds = [], []
    for i in range(0, len(db), blk):
        seg = db[i:i + blk]
        centers.append(i + len(seg) / 2)
        meds.append(np.median(seg))
    base = np.interp(np.arange(len(db)), centers, meds)
    spread = max(float(np.median(np.abs(db - base)) * 1.4826), 2.0)
    exc = np.clip((db - base) / spread, 0, None)
    s = _smooth(exc, 4 / FRAME)
    return np.clip(s / max(float(np.percentile(s, 99.5)), 1e-6), 0, 1)


def heat_score(heatmap, n_frames):
    if not heatmap:
        return None
    mids = np.array([(h["start_time"] + h["end_time"]) / 2 for h in heatmap])
    vals = np.array([h["value"] for h in heatmap], dtype=float)
    t = (np.arange(n_frames) + 0.5) * FRAME
    h = np.interp(t, mids, vals)
    return h / max(h.max(), 1e-6)


def chat_score(stamps, n_frames):
    if not stamps:
        return None
    hist, _ = np.histogram(stamps, bins=n_frames, range=(0, n_frames * FRAME))
    s = _smooth(hist.astype(float), 10 / FRAME)
    return np.clip(s / max(float(np.percentile(s, 99.5)), 1e-6), 0, 1)


CHAT_HYPE = ("clip", "clip it", "clip that", "no way", "nowaaay", "omg", "wtf", "lol", "lmao", "lmfao", "kek", "w ",
             "pog", "poggers", "holy", "insane", "crazy", "bro", "what", "wild", "dead", "cooked", "\U0001F602", "\U0001F480")


def chat_events_score(events, n_frames):
    """events: [(seconds, text_or_None)]. Messages per second compared with the chat's own normal level, and
    reaction words ('clip that', 'no way', LOL...) count extra. Returns 0-1 per analysis frame."""
    if not events:
        return None
    n_sec = int(n_frames * FRAME) + 1
    rate = np.zeros(n_sec); hype = np.zeros(n_sec)
    for t, txt in events:
        i = int(t)
        if 0 <= i < n_sec:
            rate[i] += 1
            if txt and any(k in txt.lower() for k in CHAT_HYPE):
                hype[i] += 1
    x = _smooth(rate + 1.5 * hype, 6)
    blk = 300                                              # compare with the surrounding 5 minutes
    base = np.array([np.median(x[max(0, i - blk // 2):i + blk // 2 + 1]) for i in range(0, n_sec, 5)])
    base = np.repeat(base, 5)[:n_sec]
    spread = max(float(np.median(np.abs(x - base)) * 1.4826), 0.5)
    z = np.clip((x - base) / spread, 0, None) / 6.0
    per_frame = np.repeat(np.clip(z, 0, 1), int(1 / FRAME))[:n_frames]
    return np.pad(per_frame, (0, max(0, n_frames - len(per_frame))))


def combine(audio, heat, chat):
    parts = [(audio, 0.5)]
    if heat is not None:
        parts.append((heat, 0.3))
    if chat is not None:
        parts.append((chat, 0.2))
    tot = sum(w for _, w in parts)
    s = sum(x[: len(audio)] * w for x, w in parts) / tot
    return np.clip(s, 0, 1)


def pick_windows(score, n, min_gap, min_score, lead, tail, duration):
    """Greedy peak picking: best peaks first, at least min_gap seconds apart."""
    picks = []
    for i in np.argsort(-score):
        if score[i] < min_score or len(picks) >= n:
            break
        t = (i + 0.5) * FRAME
        if all(abs(t - p["peak"]) >= min_gap for p in picks):
            picks.append({"peak": t, "score": float(score[i]),
                          "start": max(0.0, t - lead), "end": min(duration, t + tail)})
    picks.sort(key=lambda p: p["peak"])
    return picks
