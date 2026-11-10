"""Watch list + live session end. Run from the project folder: python tests/test_live_watch.py
Needs FFmpeg. Uses a temporary data folder and a local file played like a stream (no internet)."""
import os, subprocess, sys, tempfile, time

TMP = tempfile.mkdtemp()
os.environ.update(CLIPFORGE_DATA=TMP, CLIPFORGE_TEST_SOURCES="1", CLIPFORGE_TEST_READRATE="4")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge_web import db, live  # noqa: E402

SRC = os.path.join(TMP, "stream.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:d=12:r=30", "-f", "lavfi",
                "-i", "sine=d=12", "-shortest", "-c:v", "libx264", "-c:a", "aac", SRC], check=True)

# watch list validation
try:
    live.set_watch_list("https://twitch.tv/videos"); raise SystemExit("should reject")
except ValueError:
    pass
assert live.set_watch_list("https://twitch.tv/a\nhttps://twitch.tv/a\n https://kick.com/b ") == ["https://twitch.tv/a", "https://kick.com/b"]

started = []
class Fake:
    def __init__(s, url): s.url, s.stopped = url, False
def starter(u):
    started.append(u); live.SESSIONS[len(started) + 1000] = Fake(u)

live.check_watch_list(lambda u: u.endswith("/a"), starter)
assert started == ["https://twitch.tv/a"], started
assert live.WATCH == {"https://twitch.tv/a": "Recording", "https://kick.com/b": "Offline"}, live.WATCH
live.check_watch_list(lambda u: True, starter)          # a: already recording, b: starts
assert started == ["https://twitch.tv/a", "https://kick.com/b"]
# manual stop pauses until the channel goes offline
live.SESSIONS.clear(); live._paused.add("https://twitch.tv/a")
live.check_watch_list(lambda u: u.endswith("/a"), starter)
assert live.WATCH["https://twitch.tv/a"] == "Live, but you stopped it" and len(started) == 2
live.check_watch_list(lambda u: False, starter)
live.check_watch_list(lambda u: u.endswith("/a"), starter)
assert started[-1] == "https://twitch.tv/a"
# limit
live.SESSIONS.clear(); live.MAX_LIVE = 0
live.check_watch_list(lambda u: True, starter)
assert live.WATCH["https://kick.com/b"].startswith("Live, waiting")
live.SESSIONS.clear(); live.MAX_LIVE = 6
print("watch logic ok")

# stream end finishes the session by itself
vid = live.start(SRC, cfg={"warmup": 999})
for _ in range(60):
    time.sleep(1)
    if live.get(vid).stopped:
        break
v = db.q("select status from videos where id=?", (vid,), one=True)
assert live.get(vid).stopped and v["status"] == "ready", (live.get(vid).state, v)
print("stream end ok")
