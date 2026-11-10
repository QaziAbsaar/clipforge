"""Download a video link with yt-dlp (cached per video id and quality)."""
import json, os, re, subprocess

from .util import which

_PCT = re.compile(r"\[download\]\s+([\d.]+)%")


def download(job, url, outdir, max_height=1080, cookies_browser=None, on_progress=None):
    """Returns (path_to_mp4, info_dict_or_None). on_progress(0..1) is called while downloading."""
    ytdlp = which("yt-dlp")
    extra = ["--cookies-from-browser", cookies_browser] if cookies_browser else []
    r = subprocess.run([ytdlp, "--get-id", "--no-playlist"] + extra + [url], capture_output=True, text=True)
    vid = (r.stdout.strip().splitlines() or ["video"])[0]
    base = os.path.join(outdir, f"source_{vid}_{max_height}")
    if not os.path.exists(base + ".mp4"):
        fmt = (f"bv*[vcodec^=avc1][height<={max_height}]+ba[ext=m4a]/bv*[height<={max_height}]+ba/"
               f"b[height<={max_height}]/b")
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
