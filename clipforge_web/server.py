"""ClipForge web app: API + the page. Local use: binds to 127.0.0.1 only unless a password is set."""
import asyncio, hashlib, hmac, json, os, re, shutil
from typing import Optional

from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from clipforge import ai, audiolib
from clipforge.captions import TEMPLATES
from clipforge.render import RES
from . import db, engine, live, worker

app = FastAPI(title="ClipForge")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
EXTS = {".mp4", ".mov", ".mkv", ".webm"}
CLIP_FIELDS = {"title", "template", "layout", "res", "crop_x", "music", "sfx_intro", "captions", "status"}


@app.on_event("startup")
def _start():
    db.conn()
    db.ex("update videos set status='ready', stage='' where status='live'")      # live sessions don't survive a restart
    worker.start()


# ---------------- sign-in (one shared team password; set CLIPFORGE_PASSWORD to turn it on) ----------------
PASSWORD = os.environ.get("CLIPFORGE_PASSWORD", "")
SECRET = (os.environ.get("CLIPFORGE_SECRET") or PASSWORD or "local").encode()


def _token():
    return hmac.new(SECRET, b"clipforge-session", hashlib.sha256).hexdigest()


LOCAL_HOSTS = ("127.0.0.1", "localhost")


@app.middleware("http")
async def auth(request: Request, call_next):
    host = request.headers.get("host", "")
    # Without a password only this computer may talk to the app. Checking Host stops DNS-rebinding sites.
    if not PASSWORD and host.rsplit(":", 1)[0] not in LOCAL_HOSTS:
        return JSONResponse({"detail": "ClipForge only accepts requests from this computer."}, status_code=403)
    # Stop other websites from sending forms or uploads here (a browser always sends Origin on cross-site POSTs).
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin.split("://", 1)[-1] != host:
        return JSONResponse({"detail": "Request from another website was blocked."}, status_code=403)
    if PASSWORD and request.url.path not in ("/login", "/api/login", "/healthz"):
        if not hmac.compare_digest(request.cookies.get("cf_session", ""), _token()):
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "Please sign in again."}, status_code=401)
            return RedirectResponse("/login")
    return await call_next(request)


LOGIN_HTML = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>ClipForge</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#11141d;color:#e7eaf3;font:15px "Segoe UI",system-ui,sans-serif}
form{width:min(340px,90vw);background:#1a1f2e;border:1px solid #303952;border-radius:14px;padding:26px}
h1{font:700 22px Bahnschrift,"Segoe UI",sans-serif;margin:0 0 16px}h1 i{font-style:normal;color:#8c9bff}
input,button{width:100%;font:inherit;border-radius:8px;padding:10px 11px;margin-top:10px;box-sizing:border-box}
input{background:#11141d;border:1px solid #303952;color:inherit}button{background:#8c9bff;border:0;color:#10131c;font-weight:600;cursor:pointer}
p{color:#ee7384;min-height:1.2em;margin:10px 0 0}</style>
<form id=f><h1>Clip<i>Forge</i></h1><label for=pw>Team password</label><input id=pw type=password autofocus autocomplete=current-password>
<button>Sign in</button><p id=e role=alert></p></form>
<script>f.onsubmit=async ev=>{ev.preventDefault();const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw.value})});
if(r.ok)location='/';else e.textContent='That password is not right.'}</script>"""


@app.get("/login")
def login_page():
    return HTMLResponse(LOGIN_HTML)


@app.post("/api/login")
async def login(request: Request, body: dict = Body(...)):
    if not PASSWORD:
        return {"ok": True}
    if not hmac.compare_digest(str(body.get("password", "")).encode(), PASSWORD.encode()):
        await asyncio.sleep(1)
        raise HTTPException(401, "Wrong password.")
    resp = JSONResponse({"ok": True})
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    resp.set_cookie("cf_session", _token(), httponly=True, samesite="lax", secure=secure, max_age=60 * 60 * 24 * 30)
    return resp


@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("cf_session")
    return resp


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/me")
def me():
    return {"auth": bool(PASSWORD)}


@app.get("/api/health")
def health():
    """What this computer is missing, so the page can say so in plain words."""
    from clipforge.util import which

    def has(name):
        try:
            which(name)
            return True
        except Exception:
            return False

    def can(mod):
        try:
            __import__(mod)
            return True
        except Exception:
            return False
    faces = False
    try:
        from clipforge import faces as f
        f._detector()
        faces = True
    except Exception:
        pass
    return {"ffmpeg": has("ffmpeg") and has("ffprobe"), "yt_dlp": has("yt-dlp"), "whisper": can("faster_whisper"),
            "faces": faces, "streamlink": has("streamlink")}


# ---------------- settings ----------------
@app.get("/api/settings")
def get_settings():
    env = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {"ai": env or bool(db.setting("anthropic_key")), "ai_from_env": env, "model": db.setting("model", "base")}


@app.post("/api/settings")
def set_settings(body: dict = Body(...)):
    if "anthropic_key" in body:
        db.set_setting("anthropic_key", str(body["anthropic_key"]).strip())
    if body.get("model") in ("base", "small", "medium"):
        db.set_setting("model", body["model"])
    return get_settings()


@app.post("/api/settings/test")
def test_ai():
    key = engine.ai_key()
    if not key:
        raise HTTPException(400, "Add an API key first.")
    try:
        ok = ai.test_key(key)
    except Exception as e:
        raise HTTPException(400, f"The key didn't work: {str(e)[:120]}")
    return {"ok": ok}


# ---------------- clients ----------------
@app.get("/api/clients")
def clients():
    return db.q("select * from clients order by name collate nocase")


@app.post("/api/clients")
def add_client(body: dict = Body(...)):
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Give the client a name.")
    cid = db.ex("insert into clients(name,created) values(?,?)", (name[:80], db.now()))
    return db.q("select * from clients where id=?", (cid,), one=True)


@app.patch("/api/clients/{cid}")
def patch_client(cid: int, body: dict = Body(...)):
    if not db.q("select id from clients where id=?", (cid,), one=True):
        raise HTTPException(404, "Client not found.")
    tpl, music = body.get("template"), body.get("music")
    if tpl is not None and tpl not in TEMPLATES:
        raise HTTPException(400, "Unknown caption style.")
    if music not in (None, "", "random") and not audiolib.resolve("music", music):
        raise HTTPException(400, f"'{music}' isn't in the audio library.")
    for col, val in (("name", (body.get("name") or "").strip()[:80] or None), ("template", tpl), ("music", music)):
        if val is not None:
            db.ex(f"update clients set {col}=? where id=?", (val, cid))
    return db.q("select * from clients where id=?", (cid,), one=True)


@app.delete("/api/clients/{cid}")
def delete_client(cid: int):
    db.ex("update videos set client_id=null where client_id=?", (cid,))
    db.ex("delete from clients where id=?", (cid,))
    return {"ok": True}


# ---------------- videos ----------------
def _video(vid):
    v = db.q("select * from videos where id=?", (vid,), one=True)
    if not v:
        raise HTTPException(404, "Video not found.")
    return v


def _video_out(v):
    o = {k: x for k, x in v.items() if k not in ("path", "info_path", "curve")}
    o["curve"] = json.loads(v["curve"]) if v["curve"] else None
    o["has_file"] = bool(v["path"])
    return o


@app.get("/api/videos")
def videos():
    out = []
    for v in db.q("select * from videos order by id desc"):
        c = db.q("select count(*) n, sum(status='approved') a from clips where video_id=?", (v["id"],), one=True)
        out.append(dict(_video_out(v), clips=c["n"], approved=c["a"] or 0))
    return out


@app.get("/api/videos/{vid}")
def video(vid: int):
    return _video_out(_video(vid))


def _then(body):
    return {"clips": max(1, min(int(body.get("clips", 20)), 100)), "length": float(body.get("length", 30))}


@app.post("/api/videos/link")
def add_links(body: dict = Body(...)):
    urls = [u.strip() for u in body.get("urls", []) if u.strip()]
    if not urls:
        raise HTTPException(400, "Paste at least one video link.")
    ids = []
    for u in urls:
        if not u.lower().startswith(("http://", "https://")):
            raise HTTPException(400, f"That isn't a web link: {u[:60]}")
        vid = db.ex("insert into videos(title,source,status,created,client_id,kind,stage) values(?,?,?,?,?,?,?)",
                    (u, u, "importing", db.now(), body.get("client_id"), "link", "Getting your video"))
        worker.enqueue("ingest", vid, {"max_height": body.get("max_height", 1080), "cookies_browser": body.get("cookies_browser"),
                                       "then_analyze": _then(body)})
        ids.append(vid)
    return {"ids": ids}


@app.post("/api/videos/upload")
async def upload(client_id: Optional[int] = None, clips: int = 20, length: float = 30, file: UploadFile = File(...)):
    name = os.path.basename(file.filename or "video")
    ext = os.path.splitext(name)[1].lower()
    if ext not in EXTS:
        raise HTTPException(400, "Use an MP4, MOV, MKV or WebM file.")
    vid = db.ex("insert into videos(title,source,status,created,client_id,kind,stage) values(?,?,?,?,?,?,?)",
                (name, "upload", "importing", db.now(), client_id, "file", "Receiving the file"))
    d = engine.vdir(vid)
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, "source" + ext)
    with open(dest, "wb") as f:
        while True:
            chunk = await file.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    db.ex("update videos set path=? where id=?", (dest, vid))
    worker.enqueue("ingest", vid, {"then_analyze": _then({"clips": clips, "length": length})})
    return {"id": vid}


@app.delete("/api/videos/{vid}")
def delete_video(vid: int):
    _video(vid)
    s = live.get(vid)
    if s and s.state not in ("stopped", "error"):
        raise HTTPException(409, "Stop the live recording first.")
    worker.cancel_for("video", vid)
    busy = db.q("select id from jobs where ref_id=? and type!='render' and status='running'", (vid,))
    if busy:
        raise HTTPException(409, "This video is busy right now. Wait a moment and try again.")
    for c in db.q("select id from clips where video_id=?", (vid,)):
        p = os.path.join(db.DATA, "exports", f"clip_{c['id']}.mp4")
        if os.path.exists(p):
            os.remove(p)
    db.ex("delete from clips where video_id=?", (vid,))
    db.ex("delete from videos where id=?", (vid,))
    for d in (engine.vdir(vid), os.path.join(db.DATA, "work", str(vid)), os.path.join(db.DATA, "live", str(vid))):
        shutil.rmtree(d, ignore_errors=True)
    live.SESSIONS.pop(vid, None)
    return {"ok": True}


@app.get("/api/videos/{vid}/file")
def video_file(vid: int):
    v = _video(vid)
    if not v["path"] or not os.path.exists(v["path"]):
        raise HTTPException(404, "Video file is missing.")
    return FileResponse(v["path"], media_type="video/mp4" if v["path"].endswith(".mp4") else None)


@app.post("/api/videos/{vid}/chat")
async def chat_log(vid: int, file: UploadFile = File(...)):
    _video(vid)
    text = (await file.read()).decode("utf-8", errors="ignore")
    n = len(engine.parse_chat_events(text))
    if n < 5:
        raise HTTPException(400, "Couldn't find chat timestamps. Use one line per message, starting with a time like [0:12:34] or 754.5.")
    with open(os.path.join(engine.wdir(vid), "chat.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return {"messages": n}


@app.post("/api/videos/{vid}/analyze")
def analyze(vid: int, params: dict = Body(default={})):
    v = _video(vid)
    if v["kind"] == "live" or not v["path"]:
        raise HTTPException(409, "This video can't be analyzed again.")
    if v["status"] in ("importing", "analyzing"):
        raise HTTPException(409, "This video is already being analyzed.")
    db.ex("update videos set status='analyzing', progress=0, stage='Getting ready', error=null where id=?", (vid,))
    worker.enqueue("analyze", vid, params)
    return {"ok": True}


@app.post("/api/videos/{vid}/retry")
def retry(vid: int, params: dict = Body(default={})):
    v = _video(vid)
    if v["status"] in ("importing", "analyzing"):
        raise HTTPException(409, "Already working on it.")
    if v["path"] and v["duration"]:
        db.ex("update videos set status='analyzing', progress=0, stage='Getting ready', error=null where id=?", (vid,))
        worker.enqueue("analyze", vid, params or {"clips": 20, "length": 30})
    elif v["source"].startswith("http"):
        db.ex("update videos set status='importing', progress=0, stage='Getting your video', error=null where id=?", (vid,))
        worker.enqueue("ingest", vid, {"then_analyze": _then(params or {})})
    else:
        raise HTTPException(409, "Upload the file again.")
    return {"ok": True}


@app.post("/api/videos/{vid}/cancel")
def cancel_video(vid: int):
    _video(vid)
    worker.cancel_for("video", vid)
    return {"ok": True}


@app.get("/api/videos/{vid}/clips")
def video_clips(vid: int):
    _video(vid)
    return [_clip_out(c) for c in db.q("select * from clips where video_id=? order by score desc", (vid,))]


# ---------------- clips ----------------
def _clip(cid):
    c = db.q("select * from clips where id=?", (cid,), one=True)
    if not c:
        raise HTTPException(404, "Clip not found.")
    return c


def _clip_out(c):
    o = {k: v for k, v in c.items() if k not in ("words", "render_path", "track", "src", "cam")}
    o["scores"] = json.loads(c["scores"] or "{}")
    o["reasons"] = json.loads(c["reasons"] or "[]")
    o["rendered"] = bool(c["render_path"] and os.path.exists(c["render_path"]))
    if c["render_status"] == "failed":
        j = db.q("select error from jobs where type='render' and ref_id=? and status='failed' order by id desc limit 1",
                 (c["id"],), one=True)
        o["render_error"] = (j or {}).get("error") or "The clip could not be made."
    return o


@app.get("/api/clips/{cid}")
def clip(cid: int):
    return _clip_out(_clip(cid))


@app.patch("/api/clips/{cid}")
def patch_clip(cid: int, body: dict = Body(...)):
    c = _clip(cid)
    v = _video(c["video_id"])
    sets, vals = [], []
    for k, val in body.items():
        if k in ("start", "end"):
            continue
        if k not in CLIP_FIELDS:
            raise HTTPException(400, f"Can't change '{k}'.")
        if k == "template" and val not in TEMPLATES:
            raise HTTPException(400, "Unknown caption style.")
        if k == "layout" and val not in ("stack", "follow", "crop", "blur"):
            raise HTTPException(400, "Framing must be stack, follow, crop or blur.")
        if k == "res" and int(val) not in RES:
            raise HTTPException(400, "Resolution must be 1080, 1440 (2K) or 2160 (4K).")
        if k == "status" and val not in ("candidate", "approved", "rejected"):
            raise HTTPException(400, "Unknown status.")
        if k in ("music", "sfx_intro") and val not in ("", "random") and not audiolib.resolve(
                "music" if k == "music" else "sfx", val):
            raise HTTPException(400, f"'{val}' isn't in the audio library.")
        sets.append(f"{k}=?")
        vals.append(int(val) if k in ("res", "captions") else (float(val) if k == "crop_x" else val))
    if "start" in body or "end" in body:
        limit = v["duration"] if not c["src"] else (c["we"] or v["duration"])
        s, e = float(body.get("start", c["start"])), float(body.get("end", c["end"]))
        s, e = max(0.0, s), min(limit, e)
        if e - s < 3:
            raise HTTPException(400, "A clip must be at least 3 seconds long.")
        if e - s > 180:
            raise HTTPException(400, "A clip can be at most 3 minutes long.")
        sets += ["start=?", "end=?"]
        vals += [round(s, 3), round(e, 3)]
    if not sets:
        return _clip_out(c)
    if any(not x.startswith(("status", "title")) for x in sets) and c["render_status"] == "done":
        sets.append("render_status='stale'")
    db.ex(f"update clips set {','.join(sets)} where id=?", vals + [cid])
    return _clip_out(_clip(cid))


@app.get("/api/clips/{cid}/source")
def clip_source(cid: int):
    c = _clip(cid)
    p = engine.clip_source(c, _video(c["video_id"]))
    if not p or not os.path.exists(p):
        raise HTTPException(404, "The source video is missing.")
    return FileResponse(p, media_type="video/mp4" if p.endswith(".mp4") else None)


@app.get("/api/clips/{cid}/framing")
def clip_framing(cid: int):
    c = _clip(cid)
    v = _video(c["video_id"])
    if v["w"] and v["h"] and v["w"] / v["h"] <= 9 / 16 + 0.01:
        return {"found": 1, "pts": [], "cw": v["w"], "w": v["w"], "h": v["h"]}
    try:
        return engine.framing(c, v)
    except Exception as e:
        raise HTTPException(500, f"Face tracking failed: {str(e)[:160]}")


@app.get("/api/clips/{cid}/cues")
def cues(cid: int):
    c = _clip(cid)
    out = []
    for cue in engine.clip_cues(c):
        ws = cue["words"]
        out.append({"first": ws[0]["i"], "last": ws[-1]["i"], "start": round(cue["start"], 3), "end": round(cue["end"], 3),
                    "text": " ".join(w["w"] for w in ws),
                    "words": [{"w": w["w"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in ws]})
    return out


@app.patch("/api/clips/{cid}/cue")
def patch_cue(cid: int, body: dict = Body(...)):
    c = _clip(cid)
    try:
        words = engine.edit_cue(c, int(body["first"]), int(body["last"]), str(body["text"]))
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    db.ex("update clips set words=?, render_status=case when render_status='done' then 'stale' else render_status end where id=?",
          (db.dumps(words), cid))
    return cues(cid)


@app.post("/api/clips/{cid}/approve")
def approve(cid: int):
    """Approve = keep it. If it isn't rendered yet it gets made now; the page downloads it when it's ready."""
    c = _clip(cid)
    db.ex("update clips set status='approved', downloaded=0 where id=?", (cid,))
    fresh = c["render_status"] == "done" and c["render_path"] and os.path.exists(c["render_path"])
    if not fresh and c["render_status"] not in ("queued", "running"):
        worker.enqueue("render", cid, {})
    return {"needs_render": not fresh, "clip": _clip_out(_clip(cid))}


@app.post("/api/clips/{cid}/cancel")
def cancel_render(cid: int):
    _clip(cid)
    worker.cancel_for("render", cid)
    return {"ok": True}


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s or "clip").strip("_")[:60] or "clip"


@app.get("/api/clips/{cid}/download")
def download(cid: int):
    c = _clip(cid)
    if not (c["render_path"] and os.path.exists(c["render_path"])):
        raise HTTPException(404, "This clip isn't ready yet.")
    db.ex("update clips set downloaded=1 where id=?", (cid,))
    v = _video(c["video_id"])
    return FileResponse(c["render_path"], media_type="video/mp4",
                        filename=f"ClipForge_{_slug(v['title'])[:30]}_{_slug(c['title'])}.mp4")


# ---------------- live ----------------
@app.post("/api/live")
def live_start(body: dict = Body(...)):
    try:
        vid = live.start(str(body.get("url", "")).strip(), body.get("client_id"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {"id": vid}


@app.post("/api/live/{vid}/clip")
def live_clip(vid: int):
    s = live.get(vid)
    if not s or s.state != "recording":
        raise HTTPException(409, "This stream isn't recording right now.")
    s.clip_now()
    return {"ok": True}


@app.post("/api/live/{vid}/stop")
def live_stop(vid: int):
    live.stop(vid)
    return {"ok": True}


@app.get("/api/live/{vid}/stats")
def live_stats(vid: int):
    s = live.get(vid)
    if not s:
        raise HTTPException(404, "Not a live session.")
    return s.stats()


# ---------------- styles + audio ----------------
@app.get("/api/templates")
def templates():
    return TEMPLATES


@app.get("/api/audio")
def audio():
    return {"music": audiolib.list_files("music"), "sfx": audiolib.list_files("sfx")}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
