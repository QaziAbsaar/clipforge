"""SQLite storage (single file, no server needed)."""
import json, os, sqlite3, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("CLIPFORGE_DATA") or os.path.join(ROOT, "data")
_lock = threading.RLock()
_conn = None

SCHEMA = """
create table if not exists clients(
  id integer primary key, name text, template text default 'yellow_pop', music text default '', created real);
create table if not exists videos(
  id integer primary key, title text, source text, path text, status text, error text,
  duration real, w integer, h integer, fps real, size integer, has_audio integer,
  info_path text, curve text, created real, client_id integer, kind text, progress real default 0, stage text default '');
create table if not exists clips(
  id integer primary key, video_id integer, start real, end real, peak real, ws real, we real,
  score real, scores text, reasons text, words text, title text,
  template text, layout text, res integer, crop_x real, music text, sfx_intro text, sfx_peak text,
  captions integer, status text, render_status text, render_path text, created real,
  render_progress real default 0, src text, track text, downloaded integer default 0, stream_offset real default 0);
create table if not exists jobs(
  id integer primary key, type text, ref_id integer, params text, status text,
  log text default '', error text, created real, started real, finished real);
create table if not exists settings(key text primary key, value text);
"""

MIGRATE = {
    "videos": [("client_id", "integer"), ("kind", "text"), ("progress", "real default 0"), ("stage", "text default ''")],
    "clips": [("render_progress", "real default 0"), ("src", "text"), ("track", "text"), ("downloaded", "integer default 0"), ("stream_offset", "real default 0")],
}


def conn():
    global _conn
    if _conn is None:
        os.makedirs(DATA, exist_ok=True)
        _conn = sqlite3.connect(os.path.join(DATA, "clipforge.db"), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        for table, cols in MIGRATE.items():                     # upgrade databases from older versions
            have = [r[1] for r in _conn.execute(f"pragma table_info({table})").fetchall()]
            for name, decl in cols:
                if name not in have:
                    _conn.execute(f"alter table {table} add column {name} {decl}")
        _conn.commit()
    return _conn


def q(sql, args=(), one=False):
    with _lock:
        rows = [dict(r) for r in conn().execute(sql, args).fetchall()]
    return (rows[0] if rows else None) if one else rows


def ex(sql, args=()):
    with _lock:
        cur = conn().execute(sql, args)
        conn().commit()
        return cur.lastrowid


def now():
    return time.time()


def dumps(x):
    return json.dumps(x, ensure_ascii=False)


def setting(key, default=""):
    r = q("select value from settings where key=?", (key,), one=True)
    return r["value"] if r else default


def set_setting(key, value):
    ex("insert into settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value", (key, value))
