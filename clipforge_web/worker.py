"""Runs the heavy work (import, find clips, render) one task at a time in the background.
Renders go first, so an approved clip never waits behind a long analysis.
There is no queue screen: each video or clip shows its own progress."""
import json, os, threading, time, traceback

from clipforge.util import Cancelled, Job
from . import db, engine

FUNCS = {"ingest": engine.ingest, "analyze": engine.analyze_video, "render": engine.render}


def stop_file(job_id):
    d = os.path.join(db.DATA, "jobs")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{job_id}.stop")


def _usable(v):
    return bool(v and v["path"] and os.path.exists(v["path"]) and v["duration"])


def _fail(row, msg, cancelled=False):
    if row["type"] == "render":
        db.ex("update clips set render_status=?, render_progress=0 where id=?",
              ("none" if cancelled else "failed", row["ref_id"]))
        return
    v = db.q("select * from videos where id=?", (row["ref_id"],), one=True)
    db.ex("update videos set status=?, error=?, progress=0, stage='' where id=?",
          ("ready" if _usable(v) else "error", msg[:500], row["ref_id"]))


def _loop():
    db.ex("update jobs set status='failed', error='Interrupted (app was closed)' where status='running'")
    for v in db.q("select id,path,duration from videos where status in ('importing','analyzing')"):
        db.ex("update videos set status=?, error='Interrupted when the app was closed. Try again.', progress=0, stage='' "
              "where id=?", ("ready" if _usable(v) else "error", v["id"]))
    db.ex("update clips set render_status='none', render_progress=0 where render_status in ('queued','running')")
    while True:
        row = db.q("select * from jobs where status='queued' order by type='render' desc, id limit 1", one=True)
        if not row:
            time.sleep(0.4)
            continue
        sf = stop_file(row["id"])
        if os.path.exists(sf):
            os.remove(sf)
        db.ex("update jobs set status='running', started=? where id=?", (db.now(), row["id"]))
        if row["type"] == "render":
            db.ex("update clips set render_status='running' where id=?", (row["ref_id"],))
        job = Job(stop_file=sf, log=lambda m, jid=row["id"]: db.ex(
            "update jobs set log = log || ? where id=?", (str(m) + "\n", jid)))
        job.show_output = False
        params = json.loads(row["params"] or "{}")
        status, err = "done", None
        try:
            if row["type"] == "analyze":
                params.setdefault("model", db.setting("model", "base"))
            FUNCS[row["type"]](job, row["ref_id"], params)
            if row["type"] == "ingest" and params.get("then_analyze") is not None:
                db.ex("update videos set status='analyzing', progress=0, stage='Getting ready' where id=?", (row["ref_id"],))
                enqueue("analyze", row["ref_id"], params["then_analyze"])
            elif row["type"] == "ingest":
                db.ex("update videos set status='ready', progress=100, stage='' where id=?", (row["ref_id"],))
        except Cancelled:
            status = "cancelled"
            _fail(row, "Cancelled.", cancelled=True)
        except Exception as e:
            status, err = "failed", (str(e) or e.__class__.__name__)[-700:]
            traceback.print_exc()
            _fail(row, err)
        db.ex("update jobs set status=?, error=?, finished=? where id=?", (status, err, db.now(), row["id"]))


def start():
    threading.Thread(target=_loop, daemon=True).start()


def enqueue(type_, ref_id, params=None):
    if type_ == "render":
        db.ex("update clips set render_status='queued', render_progress=0 where id=?", (ref_id,))
    return db.ex("insert into jobs(type,ref_id,params,status,created) values(?,?,?,'queued',?)",
                 (type_, ref_id, db.dumps(params or {}), db.now()))


def cancel_for(type_filter, ref_id):
    """Stop everything running or waiting for one video (type_filter 'video') or one clip render ('render')."""
    q = ("select * from jobs where ref_id=? and status in ('queued','running') and type "
         + ("='render'" if type_filter == "render" else "!='render'"))
    for r in db.q(q, (ref_id,)):
        if r["status"] == "queued":
            db.ex("update jobs set status='cancelled', finished=? where id=?", (db.now(), r["id"]))
            _fail(r, "Cancelled.", cancelled=True)
        else:
            open(stop_file(r["id"]), "w").close()
