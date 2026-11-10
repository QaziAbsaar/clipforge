"""Several videos run at once, but never two tasks for the same video. Run: python tests/test_worker.py"""
import os, sys, tempfile, threading, time

os.environ.update(CLIPFORGE_DATA=tempfile.mkdtemp(), CLIPFORGE_WORKERS="3")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge_web import db, worker  # noqa: E402

running, peak, same, lock = {}, [0], [], threading.Lock()
def fake(job, ref, params):
    with lock:
        if ref in running:
            same.append(ref)
        running[ref] = 1
        peak[0] = max(peak[0], len(running))
    time.sleep(0.6)
    with lock:
        running.pop(ref)
worker.FUNCS["analyze"] = fake

for ref in (1, 2, 3, 4, 1):
    worker.enqueue("analyze", ref, {"model": "tiny"})
worker.start()
deadline = time.time() + 10
while db.q("select 1 from jobs where status in ('queued','running')") and time.time() < deadline:
    time.sleep(0.1)
assert not db.q("select 1 from jobs where status!='done'"), db.q("select * from jobs where status!='done'")
assert peak[0] == 3, peak
assert not same, same
print("ok")
