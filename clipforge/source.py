"""Download a video link with yt-dlp (cached per video id and quality)."""
import json, os, re, subprocess

from .util import which

_PCT = re.compile(r"\[download\]\s+([\d.]+)%")


def _fmt(h):
    return f"bv*[vcodec^=avc1][height<={h}]+ba[ext=m4a]/bv*[height<={h}]+ba/b[height<={h}]/b"


def download(job, url, outdir, max_height=1080, cookies_browser=None, on_progress=None):
    """Returns (path_to_mp4, info_dict_or_None). on_progress(0..1) is called while downloading."""
    ytdlp = which("yt-dlp")
    extra = ["--cookies-from-browser", cookies_browser] if cookies_browser else []
    r = subprocess.run([ytdlp, "--get-id", "--no-playlist"] + extra + [url], capture_output=True, text=True)
    vid = (r.stdout.strip().splitlines() or ["video"])[0]
    base = os.path.join(outdir, f"source_{vid}_{max_height}")
    if not os.path.exists(base + ".mp4"):
        fmt = _fmt(max_height)
        job.log(f"Downloading up to {max_height}p...")
        state = {"parts": 0}

        def line(s):
            if "Destination:" in s:
                state["parts"] += 1
            m = _PCT.search(s)
            if m and on_progress:
                p = float(m.group(1)) / 100
                on_progress(p * 0.9 if state["parts"] <= 1 else 0.9 + p * 0.1)
        job.run_lines([ytdlp, "-f", fmt, "--merge-output-format", "mp4", "--write-info-json", "--no-playlist",
                       "--newline", "-o", base + ".%(ext)s"] + extra + [url], line)
    info = None
    if os.path.exists(base + ".info.json"):
        with open(base + ".info.json", encoding="utf-8") as f:
            info = json.load(f)
    return base + ".mp4", info


def download_section(job, url, out, start, end, max_height=1080, cookies_browser=None):
    """Only start..end seconds of a link at full quality. The cut is exact, so the file starts at `start`."""
    if not os.path.exists(out):
        extra = ["--cookies-from-browser", cookies_browser] if cookies_browser else []
        job.run([which("yt-dlp"), "-f", _fmt(max_height), "--merge-output-format", "mp4", "--no-playlist",
                 "--download-sections", f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts",
                 "-o", out] + extra + [url])
    return out


def youtube_chat(url, base, cookies_browser=None):
    """Download a YouTube stream's chat replay (if it has one) and return [(seconds, message)]. Never raises."""
    path = base + ".live_chat.json"
    if not os.path.exists(path):
        extra = ["--cookies-from-browser", cookies_browser] if cookies_browser else []
        try:
            subprocess.run([which("yt-dlp"), "--skip-download", "--write-subs", "--sub-langs", "live_chat",
                            "--no-playlist", "-o", base + ".%(ext)s"] + extra + [url], capture_output=True, timeout=3600)
        except Exception:
            return []
    if not os.path.exists(path):
        return []
    return parse_live_chat(path)


def parse_live_chat(path):
    out = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)["replayChatItemAction"]
                t = int(d["videoOffsetTimeMsec"]) / 1000
                for a in d["actions"]:
                    r = a.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer")
                    if r:
                        out.append((t, "".join(x.get("text", "") for x in r.get("message", {}).get("runs", []))))
            except (KeyError, ValueError, TypeError):
                continue
    return out
