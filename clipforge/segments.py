"""Clip boundaries (snap to sentence starts/ends) and a simple speech score."""
import math

HOOK_WORDS = ["no way", "what the", "oh my", "crazy", "insane", "bro", "dude", "wait", "bruh", "omg",
              "wtf", "nah", "stop", "scream", "never", "can't believe", "unbelievable", "let's go", "yo",
              # GTA / gaming reactions
              "wasted", "busted", "oh no", "get out", "the cops", "five stars", "5 stars", "glitch", "crashed",
              "exploded", "what just happened", "are you serious", "no no no", "oh my god", "run run", "go go go",
              "i'm dead", "we're dead", "clip that", "let him cook"]
SENT = (".", "?", "!")


def _starts_sentence(words, i):
    return i == 0 or words[i - 1]["w"].endswith(SENT) or words[i]["start"] - words[i - 1]["end"] > 0.7


def _ends_sentence(words, i):
    return (i == len(words) - 1 or words[i]["w"].endswith(SENT)
            or words[i + 1]["start"] - words[i]["end"] > 0.7)


def snap(words, t0, t1, min_len, max_len, duration, fps):
    """Move start back to a sentence start and end forward to a sentence end (never mid-word)."""
    if words:
        i = next((k for k, w in enumerate(words) if w["end"] > t0), len(words) - 1)
        lim = words[i]["start"] - 10
        while i > 0 and not _starts_sentence(words, i) and words[i - 1]["start"] > lim:
            i -= 1
        s = words[i]["start"] - 0.15
        j = max((k for k, w in enumerate(words) if w["start"] < t1), default=i)
        j = max(j, i)
        lim = t1 + 8
        while j < len(words) - 1 and not _ends_sentence(words, j) and words[j]["end"] < lim:
            j += 1
        e = words[j]["end"] + 0.25
        while e - s < min_len and j < len(words) - 1:      # too short: add more speech
            j += 1
            e = words[j]["end"] + 0.25
        if e - s > max_len:                                 # too long: end at last sentence end that fits
            k = max((k for k in range(i, j + 1) if words[k]["end"] - s <= max_len and _ends_sentence(words, k)),
                    default=None)
            e = (words[k]["end"] + 0.25) if k is not None else s + max_len
    else:
        s, e = t0, t1
    s, e = max(0.0, s), min(duration, e)
    s = math.floor(s * fps) / fps                           # land on the frame grid
    e = math.ceil(e * fps) / fps
    return s, min(e, duration)


def text_score(words, dur):
    if not words:
        return 0.0
    txt = " ".join(w["w"] for w in words).lower()
    first = " ".join(w["w"] for w in words[:12]).lower()
    s = min(sum(txt.count(k) for k in HOOK_WORDS), 4) * 0.15 + min(txt.count("!"), 4) * 0.05
    s += 0.2 if "?" in first else 0.0
    s += min(len(words) / max(dur, 1) / 3.0, 1.0) * 0.3
    return min(s, 1.0)


