"""A clip edited after export is made again when approved. Run: python tests/test_reapprove.py"""
import os, sys, tempfile

os.environ["CLIPFORGE_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge_web import db, server  # noqa: E402

old = os.path.join(os.environ["CLIPFORGE_DATA"], "old.mp4")
open(old, "wb").close()
vid = db.ex("insert into videos(title,status) values('v','ready')")
cid = db.ex("insert into clips(video_id,start,end,status,render_status,render_path) values(?,0,10,'approved','done',?)",
            (vid, old))
assert server.approve_clip(cid)["needs_render"] is False          # unchanged: download the file it has
db.ex("update clips set render_status='stale' where id=?", (cid,))  # what an edit does
assert server.approve_clip(cid)["needs_render"] is True
assert db.q("select render_status from clips where id=?", (cid,), one=True)["render_status"] == "queued"
print("ok")
