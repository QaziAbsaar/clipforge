"""Optional smarter scoring with Claude. The transcript of each candidate clip is sent to the Anthropic API.
Without an API key the app uses its built-in scoring. Any failure here is non-fatal."""
import json, os, re, urllib.request

MODEL = os.environ.get("CLIPFORGE_AI_MODEL", "claude-haiku-5-5")
URL = "https://api.anthropic.com/v1/messages"

SYSTEM = (
    "You are an editor who picks short-form clips (TikTok, Reels, Shorts) from streams and videos. "
    "You only see transcripts. Judge ONLY what the transcript supports and never invent dialogue or events. "
    "Reply with JSON only, no prose and no code fences."
)

PROMPT = """For each candidate clip below, return one JSON object with these keys:
id (copy it), humor, surprise, story, hype (each 0-10, how strongly the transcript shows it),
complete (true if the clip has its setup AND its payoff or reaction; false if it starts or ends mid-thought),
title (max 8 words, written by you as a hook, NOT a quote of the transcript),
reason (one short sentence on why it would or would not work as a clip).
Return a JSON array, one object per clip.

Clips:
{clips}"""


def _post(api_key, body, timeout=60):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def parse(text):
    """Pull the JSON array out of a model reply (tolerates code fences or a little extra text)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("["), text.rfind("]")
    if a < 0 or b < a:
        raise ValueError("no JSON array in reply")
    out = {}
    for o in json.loads(text[a:b + 1]):
        try:
            hi = max(float(o.get("humor", 0)), float(o.get("surprise", 0)), float(o.get("hype", 0)), float(o.get("story", 0)))
            avg = (float(o.get("humor", 0)) + float(o.get("surprise", 0)) + float(o.get("story", 0)) + float(o.get("hype", 0))) / 4
            score = min(1.0, (0.6 * hi + 0.4 * avg) / 10)
            if o.get("complete") is False:
                score *= 0.75
            out[str(o["id"])] = {"score": round(score, 3), "complete": bool(o.get("complete", True)),
                                 "title": str(o.get("title", ""))[:90], "reason": str(o.get("reason", ""))[:220],
                                 "humor": o.get("humor"), "surprise": o.get("surprise")}
        except (KeyError, TypeError, ValueError):
            continue
    return out


def score_clips(api_key, items, log=print, post=_post):
    """items: [{'id': str, 'text': str}]. Returns {id: {...}} (may be partial). Never raises."""
    results = {}
    for i in range(0, len(items), 20):
        batch = items[i:i + 20]
        listing = "\n\n".join(f"[id={c['id']}]\n{c['text'][:1400]}" for c in batch)
        try:
            resp = post(api_key, {"model": MODEL, "max_tokens": 3000, "system": SYSTEM,
                                  "messages": [{"role": "user", "content": PROMPT.format(clips=listing)}]})
            text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
            results.update(parse(text))
        except Exception as e:  # network, bad key, bad reply: fall back to built-in scoring
            log(f"AI scoring skipped for one batch ({str(e)[:120]})")
    return results


def test_key(api_key, post=_post):
    resp = post(api_key, {"model": MODEL, "max_tokens": 5, "messages": [{"role": "user", "content": "Say ok"}]}, timeout=30)
    return bool(resp.get("content"))
