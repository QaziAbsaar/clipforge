"""The work behind the buttons: import a video, find clips, frame them on the face, render."""
import json, os, re, subprocess
import numpy as np

from clipforge import ai, analyze, audiolib, captions, faces
from clipforge.render import RES, render_clip
from clipforge.segments import HOOK_WORDS, snap, text_score
from clipforge.source import download, download_section, youtube_chat
from clipforge.transcribe import load_json, transcribe_file
from clipforge.util import Cancelled, probe, which
from . import db


def vdir(vid):
    return os.path.join(db.DATA, "originals", str(vid))


def wdir(vid):
    p = os.path.join(db.DATA, "work", str(vid))
    os.makedirs(p, exist_ok=True)
    return p


def prog(video_id, pct, stage=None):
    """What the progress bar on the video shows (0-100) and the sentence under it."""
    pct = max(0.0, min(100.0, pct))
    if stage is None:
        db.ex("update videos set progress=? where id=?", (round(pct, 1), video_id))
    else:
        db.ex("update videos set progress=?, stage=? where id=?", (round(pct, 1), stage, video_id))


def ai_key():
    return os.environ.get("ANTHROPIC_API_KEY") or db.setting("anthropic_key")


def clip_source(clip, video):
    """Live moments are cut into their own small file; everything else comes from the video."""
    return clip.get("src") or video["path"]


# ---------------- import ----------------
NO_SOUND = "This video has no sound, so ClipForge can't find its best moments."
TOO_SHORT = "This video is too short. Use one that is at least 5 seconds long."


def ingest(job, video_id, params):
    v = db.q("select * from videos where id=?", (video_id,), one=True)
    os.makedirs(vdir(video_id), exist_ok=True)
    title = v["title"]
    prog(video_id, 0, "Getting your video")
    if v["source"].startswith(("http://", "https://")):
        hd = int(params.get("max_height") or 1080)
        quick = bool(params.get("quick"))     # small copy to find clips; full quality fetched per clip at render
        path, info = download(job, v["source"], vdir(video_id), 360 if quick else hd,
                              params.get("cookies_browser") or None,
                              on_progress=lambda f: prog(video_id, f * 95, "Downloading a quick copy" if quick
                                                         else "Downloading the video"))
        db.ex("update videos set hd=?, cookies=? where id=?",
              (hd if quick else 0, params.get("cookies_browser") or None, video_id))
        title = (info or {}).get("title") or title
        if "youtube.com" in v["source"] or "youtu.be" in v["source"]:
            prog(video_id, 96, "Reading the chat replay")
            events = youtube_chat(v["source"], os.path.splitext(path)[0], params.get("cookies_browser") or None)
            if len(events) >= 20:
                with open(os.path.join(wdir(video_id), "chat.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(f"{t:.2f} {m.replace(chr(10), ' ')}" for t, m in events))
                job.log(f"Chat replay: {len(events)} messages.")
    else:
        path = v["path"]
    ffprobe = which("ffprobe")
    p = probe(ffprobe, path)
    audio = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                            "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    info_path = os.path.splitext(path)[0] + ".info.json"
    db.ex("update videos set path=?,title=?,duration=?,w=?,h=?,fps=?,size=?,has_audio=?,info_path=?,error=null "
          "where id=?", (path, title, p["duration"], p["w"], p["h"], p["fps"], os.path.getsize(path),
                         1 if audio else 0, info_path if os.path.exists(info_path) else None, video_id))
    if not audio:
        raise RuntimeError(NO_SOUND)
    if p["duration"] < 5:
        raise RuntimeError(TOO_SHORT)
    prog(video_id, 100, "Ready to analyze")


# ---------------- chat logs ----------------
_TS = re.compile(r"^\[?(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\]?\s*(.*)$")


def parse_chat_events(text):
    """Chat log lines like '[0:12:34] name: message' or '754.5 message' -> [(seconds, message)]."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        m = _TS.match(line)
        if m:
            h, mi, s, msg = m.groups()
            out.append((int(h or 0) * 3600 + int(mi) * 60 + float(s), msg))
            continue
        parts = line.split(None, 1)
        try:
            out.append((float(parts[0]), parts[1] if len(parts) > 1 else ""))
        except Exception:
            pass
    return out


# ---------------- find clips ----------------
def _mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _reasons(peak, comp, words, hooks, wps, q_first, ai_info):
    r = []
    if ai_info and ai_info.get("reason"):
        r.append("AI editor: " + ai_info["reason"])
    if comp["audio"] >= 0.15:
        r.append(f"Loudness peak at {_mmss(peak)}: {comp['audio']:.0%} of the loudest moment in this video.")
    if comp.get("motion") is not None and comp["motion"] >= 0.3:
        r.append(f"Big on-screen action here: {comp['motion']:.0%} of the wildest moment.")
    if comp["heat"] is not None:
        r.append(f"YouTube 'most replayed' signal here: {comp['heat']:.0%}.")
    if comp["chat"] is not None:
        r.append(f"Chat reaction here: {comp['chat']:.0%} of the biggest chat burst.")
    if hooks:
        r.append("Hook words in the speech: " + ", ".join(sorted(set(hooks))[:6]) + ".")
    if q_first:
        r.append("Opens with a question.")
    if words:
        r.append(f"Speech density: {wps:.1f} words per second. Cut starts and ends at sentence boundaries.")
    else:
        r.append("No speech detected here. Cut points are time-based, so check them by ear.")
    return r


def _resolve_overlaps(chosen, min_clip=5.0):
    """Clips may not overlap: where two touch, the boundary moves to the middle. Too-short leftovers are dropped."""
    chosen = sorted(chosen, key=lambda c: c["s"])
    out = []
    for c in chosen:
        if out and c["s"] < out[-1]["e"]:
            mid = (c["s"] + out[-1]["e"]) / 2
            out[-1]["e"] = c["s"] = mid
            if out[-1]["e"] - out[-1]["s"] < min_clip:
                out.pop()
            if c["e"] - c["s"] < min_clip:
                continue
        out.append(c)
    return out


def analyze_video(job, video_id, p):
    v = db.q("select * from videos where id=?", (video_id,), one=True)
    if v["has_audio"] == 0:
        raise RuntimeError(NO_SOUND)
    if (v["duration"] or 0) < 5:
        raise RuntimeError(TOO_SHORT)
    ffmpeg = which("ffmpeg")
    work = wdir(video_id)
    src, dur, fps = v["path"], v["duration"], v["fps"] or 30
    n = max(1, min(int(p.get("clips", 20)), 100))
    length = max(8.0, min(float(p.get("length", 30)), 90.0))
    min_len, max_len = max(6.0, length * 0.6), max(length * 1.7, 18.0)
    many = n >= 30
    min_score = 0.0 if many else float(p.get("min_score", 0.1))
    gap = length if many else max(length, float(p.get("min_gap", 45)))
    model, device = p.get("model", "base"), p.get("device", "cpu")
    compute = "int8" if device == "cpu" else "float16"
    pad = 5.0
    db.ex("update videos set status='analyzing', error=null where id=?", (video_id,))

    # 1) the whole video's audio, cheaply
    prog(video_id, 2, "Listening to the whole video")
    acache = os.path.join(work, "audio_score.npy")
    if os.path.exists(acache):
        a = np.load(acache)
    else:
        raw = os.path.join(work, "audio.raw")
        job.run([ffmpeg, "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(analyze.SR), "-f", "s16le", raw])
        a = analyze.audio_score(analyze.loudness_db(raw))
        os.remove(raw)
        np.save(acache, a)
    prog(video_id, 14, "Checking the crowd signals")
    heat = None
    if v["info_path"] and os.path.exists(v["info_path"]):
        with open(v["info_path"], encoding="utf-8") as f:
            heat = analyze.heat_score(json.load(f).get("heatmap"), len(a))
    chat = None
    chat_file = os.path.join(work, "chat.txt")
    if os.path.exists(chat_file):
        with open(chat_file, encoding="utf-8", errors="ignore") as f:
            chat = analyze.chat_events_score(parse_chat_events(f.read()), len(a))
    prog(video_id, 16, "Watching for big on-screen moments")
    mcache = os.path.join(work, "motion_score.npy")
    if os.path.exists(mcache):
        motion = np.load(mcache)
    else:
        job.check()
        motion = analyze.motion_score(ffmpeg, src, len(a))
        if motion is not None:
            np.save(mcache, motion)
    score = analyze.combine(a, heat, chat, motion)
    k = max(1, len(score) // 400)
    curve = [round(float(score[i:i + k].max()), 3) for i in range(0, len(score), k)]
    db.ex("update videos set curve=? where id=?", (db.dumps({"step": k * analyze.FRAME, "v": curve}), video_id))

    # 2) candidate moments
    lead, tail = length * 0.65, length * 0.35
    n_cand = min(int(n * (1.6 if many else 3)), max(1, int(dur / gap)))
    cands = analyze.pick_windows(score, n_cand, gap, min_score, lead, tail, dur)
    if not cands:
        raise RuntimeError("No exciting moments stood out in this video. Try a shorter clip length.")
    for c in cands:
        c["ws"], c["we"] = max(0.0, c["start"] - pad), min(dur, c["end"] + pad)
    covered = sum(c["we"] - c["ws"] for c in cands)

    # 3) transcribe: once for the whole video if the clips cover most of it, otherwise only the good moments
    prog(video_id, 20, "Reading what is said")
    if covered >= 0.45 * dur or len(cands) > 40:
        tj = os.path.join(work, f"full_{model}.json")
        if not os.path.exists(tj):
            wav = os.path.join(work, "full.wav")
            if not os.path.exists(wav):
                job.run([ffmpeg, "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])
            res = transcribe_file(wav, model, device, compute, p.get("language") or None,
                                  on_progress=lambda f: (job.check(), prog(video_id, 22 + f * 58, "Reading what is said")))
            with open(tj, "w", encoding="utf-8") as f:
                json.dump(res, f)
        allw = load_json(tj)
        for c in cands:
            c["words"] = [w for w in allw if w["start"] >= c["ws"] - 0.01 and w["end"] <= c["we"] + 0.01]
    else:
        for i, c in enumerate(cands, 1):
            job.check()
            prog(video_id, 22 + 58 * i / len(cands), f"Reading what is said ({i} of {len(cands)})")
            key = f"win_{int(c['ws'] * 1000)}_{int(c['we'] * 1000)}"
            wav, tj = os.path.join(work, key + ".wav"), os.path.join(work, key + ".json")
            if not os.path.exists(tj):
                if not os.path.exists(wav):
                    job.run([ffmpeg, "-y", "-ss", f"{c['ws']:.3f}", "-t", f"{c['we'] - c['ws']:.3f}", "-i", src,
                             "-vn", "-ac", "1", "-ar", "16000", wav])
                with open(tj, "w", encoding="utf-8") as f:
                    json.dump(transcribe_file(wav, model, device, compute, p.get("language") or None), f)
            c["words"] = [{"w": w["w"], "start": w["start"] + c["ws"], "end": w["end"] + c["ws"]} for w in load_json(tj)]

    # 4) clean cut points and a first score
    prog(video_id, 82, "Choosing where each clip starts and ends")
    for c in cands:
        c["s"], c["e"] = snap(c["words"], c["start"], c["end"], min_len, max_len, dur, fps)
        c["cw"] = [w for w in c["words"] if w["start"] >= c["s"] - 0.01 and w["end"] <= c["e"] + 0.01]
        c["text"] = text_score(c["cw"], c["e"] - c["s"])

    # 5) optional smarter scoring with an AI editor
    key = ai_key()
    ai_res = {}
    if key:
        prog(video_id, 86, "Asking the AI editor")
        ai_res = ai.score_clips(key, [{"id": str(i), "text": " ".join(w["w"] for w in c["cw"])}
                                      for i, c in enumerate(cands) if c["cw"]], log=job.log)
    for i, c in enumerate(cands):
        c["ai"] = ai_res.get(str(i))
        sig = c["score"]
        c["final"] = (0.5 * sig + 0.1 * c["text"] + 0.4 * c["ai"]["score"]) if c["ai"] else (0.7 * sig + 0.3 * c["text"])

    # 6) best N, no overlaps
    prog(video_id, 94, "Ranking the clips")
    chosen = _resolve_overlaps(sorted(cands, key=lambda x: -x["final"])[:n])
    db.ex("delete from clips where video_id=? and status='candidate'", (video_id,))
    client = db.q("select * from clients where id=?", (v["client_id"],), one=True) if v.get("client_id") else None
    tpl_default = (client or {}).get("template") or "yellow_pop"
    music_default = (client or {}).get("music") or ""
    for c in chosen:
        idx = min(int(c["peak"] / analyze.FRAME), len(a) - 1)
        comp = {"audio": float(a[idx]), "heat": None if heat is None else float(heat[idx]),
                "motion": None if motion is None else float(motion[idx]),
                "chat": None if chat is None else float(chat[idx]), "speech": float(c["text"]),
                "ai": c["ai"]["score"] if c["ai"] else None}
        txt = " ".join(w["w"] for w in c["cw"]).lower()
        hooks = [h for h in HOOK_WORDS if h in txt]
        first = " ".join(w["w"] for w in c["cw"][:12])
        wps = len(c["cw"]) / max(c["e"] - c["s"], 1)
        title = (c["ai"] or {}).get("title") or (re.split(r"(?<=[.!?])\s", " ".join(w["w"] for w in c["cw"]))[0]
                                                  if c["cw"] else "Untitled clip")[:70]
        db.ex("insert into clips(video_id,start,end,peak,ws,we,score,scores,reasons,words,title,template,layout,res,"
              "crop_x,music,sfx_intro,sfx_peak,captions,status,render_status,created) "
              "values(?,?,?,?,?,?,?,?,?,?,?,?,'pip',1080,0.5,?,'','',1,'candidate','none',?)",
              (video_id, c["s"], c["e"], c["peak"], c["ws"], c["we"], round(c["final"], 4), db.dumps(comp),
               db.dumps(_reasons(c["peak"], comp, c["cw"], hooks, wps, "?" in first, c["ai"])),
               db.dumps(c["words"]), title, tpl_default, music_default, db.now()))
    db.ex("update videos set status='ready', progress=100, stage='', error=null where id=?", (video_id,))
    job.log(f"{len(chosen)} clips ranked.")


# ---------------- captions for a clip ----------------
def clip_words(clip):
    """Words inside the clip on the clip timeline, each remembering its index in the stored word list."""
    words = json.loads(clip["words"])
    return [{"w": w["w"], "start": w["start"] - clip["start"], "end": w["end"] - clip["start"], "i": i}
            for i, w in enumerate(words)
            if w["start"] >= clip["start"] - 0.01 and w["end"] <= clip["end"] + 0.01]


def auto_sfx(clip):
    """Effects that make a clip hit harder: whoosh in, riser into the big moment, boom on it, pops on reaction words.
    Times are on the video timeline (like start/end), so trimming never moves them off their moment."""
    s, dur = clip["start"], clip["end"] - clip["start"]
    peak = clip["peak"] - s
    if not 0.5 < peak < dur - 0.3:
        peak = dur * 0.4
    out = [{"f": "whoosh.wav", "t": 0.0, "v": 0.5}]
    if peak > 2:
        out.append({"f": "riser.wav", "t": peak - 1.5, "v": 0.35})
    out.append({"f": "boom.wav", "t": peak, "v": 0.8})
    words = clip_words(clip)
    toks = [re.sub(r"[^a-z0-9 ]", "", w["w"].lower()) for w in words]
    last = -9.0
    for i, w in enumerate(words):
        said = " ".join(toks[i:i + 3])
        if (any(said == h or said.startswith(h + " ") for h in HOOK_WORDS) and abs(w["start"] - peak) > 1.5
                and w["start"] - last >= 2 and 0.3 < w["start"] < dur - 0.3):
            out.append({"f": "pop.wav", "t": w["start"], "v": 0.6})
            last = w["start"]
            if sum(e["f"] == "pop.wav" for e in out) == 3:
                break
    return [dict(e, t=round(s + e["t"], 3)) for e in sorted(out, key=lambda e: e["t"])
            if audiolib.resolve("sfx", e["f"])]


def clip_cues(clip):
    return captions.build_cues(clip_words(clip))


def edit_cue(clip, first, last, text):
    words = json.loads(clip["words"])
    if not (0 <= first <= last < len(words)):
        raise ValueError("bad cue range")
    toks = text.split()
    if not toks:
        raise ValueError("Caption text can't be empty.")
    if len(toks) == last - first + 1:                            # same word count: keep each word's timing
        for t, i in zip(toks, range(first, last + 1)):
            words[i]["w"] = t
    else:                                                        # spread new words across the same time span
        t0, t1 = words[first]["start"], words[last]["end"]
        total = sum(len(t) + 1 for t in toks)
        cur, new = t0, []
        for t in toks:
            d = (t1 - t0) * (len(t) + 1) / total
            new.append({"w": t, "start": round(cur, 3), "end": round(cur + d, 3)})
            cur += d
        words[first:last + 1] = new
    return words


# ---------------- face framing + render ----------------
def get_track(job, clip, video):
    """Face-following crop path for a clip (cached until the clip's start or end changes)."""
    if clip["track"]:
        t = json.loads(clip["track"])
        if abs(t["start"] - clip["start"]) < 0.01 and abs(t["end"] - clip["end"]) < 0.01:
            return t
    t = faces.track(which("ffmpeg"), clip_source(clip, video), video["w"], video["h"], clip["start"], clip["end"],
                    fps=5, should_stop=job.check if job else None)
    t["start"], t["end"] = clip["start"], clip["end"]
    db.ex("update clips set track=? where id=?", (db.dumps(t), clip["id"]))
    return t


def get_cam(job, clip, video):
    """Facecam box for the stacked layout (cached until the clip's start or end changes)."""
    if clip["cam"]:
        c = json.loads(clip["cam"])
        if "box" in c and abs(c["start"] - clip["start"]) < 0.01 and abs(c["end"] - clip["end"]) < 0.01:
            return c
    if job:
        job.check()
    c = faces.find_facecam(which("ffmpeg"), clip_source(clip, video), video["w"], video["h"], clip["start"], clip["end"])
    c["start"], c["end"] = clip["start"], clip["end"]
    db.ex("update clips set cam=? where id=?", (db.dumps(c), clip["id"]))
    return c


def framing(clip, video):
    """What the browser preview needs to mimic the face-following crop or the stacked layout."""
    if clip["layout"] in ("stack", "pip"):
        c = get_cam(None, clip, video)
        if c["kind"] != "camera":
            return {"stack": True, "pip": clip["layout"] == "pip", "size": faces.PIP_SIZE, "ptop": faces.PIP_TOP,
                    "kind": c["kind"], "cam": c["cam"], "box": c["box"], "w": video["w"], "h": video["h"],
                    "top": faces.TOP_SHARE, "found": 1.0 if c["cam"] else 0.0, "pts": []}
    t = get_track(None, clip, video)
    room = max(video["w"] - t["cw"], 1)
    return {"found": t["found"], "cw": t["cw"], "w": video["w"], "h": video["h"],
            "pts": [[p[0], round(p[1] / room, 4)] for p in t["pts"]]}


def _hd_part(job, c, v, info, track):
    """Quick-copy videos: fetch just this clip in full quality and move the face boxes to its size.
    Returns None (render from the quick copy) if the link no longer works."""
    out = os.path.join(vdir(v["id"]), f"hd_{c['id']}_{c['start']:.2f}_{c['end']:.2f}.mp4")
    job.log(f"Getting this part in {v['hd']}p...")
    try:
        download_section(job, v["source"], out, c["start"], c["end"], v["hd"], v["cookies"])
        p = probe(which("ffprobe"), out)
    except Cancelled:
        raise
    except Exception as e:
        job.log(f"Couldn't get the full-quality part ({str(e)[:200]}). Using the quick copy instead.")
        return None
    k = p["w"] / v["w"]
    if track:
        track = dict(track)
        for key in ("cam", "box"):
            if track.get(key):
                track[key] = [int(n * k) // 2 * 2 for n in track[key]]
        if track.get("pts"):
            track["pts"] = [[t, x * k] for t, x in track["pts"]]
    return out, 0.0, c["end"] - c["start"], {**info, "w": p["w"], "h": p["h"], "fps": p["fps"]}, track


def render(job, clip_id, p):
    c = db.q("select * from clips where id=?", (clip_id,), one=True)
    v = db.q("select * from videos where id=?", (c["video_id"],), one=True)
    ffmpeg = which("ffmpeg")
    info = {"w": v["w"], "h": v["h"], "fps": v["fps"], "duration": v["duration"]}
    cues = clip_cues(c) if c["captions"] else []
    work = wdir(c["video_id"])
    ass = os.path.join(work, f"clip_{clip_id}.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write(captions.to_ass(cues, c["template"]))
    out_dir = os.path.join(db.DATA, "exports")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"clip_{clip_id}.mp4")
    last = {"p": -1}

    def setp(frac):
        pct = round(frac * 100)
        if pct != last["p"]:
            last["p"] = pct
            db.ex("update clips set render_progress=? where id=?", (pct, clip_id))
    setp(0.01)
    track, layout = None, c["layout"]
    wide = v["w"] / v["h"] > 9 / 16 + 0.01
    if layout in ("stack", "pip") and wide:
        cam = get_cam(job, c, v)
        job.log({"facecam": "Facecam found: placed over the gameplay." if layout == "pip" else "Facecam found: stacked above the gameplay.", "camera": "Full camera shot: following the face.",
                 "none": "No facecam: showing the whole gameplay."}[cam["kind"]])
        if cam["kind"] == "camera":
            layout = "follow"
        else:
            track = {"cam": cam["cam"], "box": cam["box"]}
    if layout == "follow" and wide:
        track = get_track(job, c, v)
        job.log(f"Face found in {track['found']:.0%} of the clip.")
    src, start, end = clip_source(c, v), c["start"], c["end"]
    if v["hd"] and not c["src"]:
        src, start, end, info, track = _hd_part(job, c, v, info, track) or (src, start, end, info, track)
    setp(0.12)
    dur = c["end"] - c["start"]
    sfx = []
    path = audiolib.resolve("sfx", c["sfx_intro"])
    if path:
        sfx.append((path, 0.0, 0.7))
    for e in json.loads(c["sfx"] or "[]"):                 # placed effects, stored on the video timeline
        path = audiolib.resolve("sfx", e["f"])
        if path and c["start"] - 0.01 <= e["t"] < c["end"]:        # times are rounded to 1 ms
            sfx.append((path, max(e["t"] - c["start"], 0.0), e["v"]))
    music = audiolib.resolve("music", c["music"])
    job.log(f"Rendering {dur:.0f}s clip at {RES[c['res']][0]}x{RES[c['res']][1]}...")
    render_clip(job, ffmpeg, src, info, start, end, ass, out, layout, c["crop_x"],
                res=c["res"], music=music, music_vol=0.18, duck=True, sfx=sfx, track=track,
                on_progress=lambda f: setp(0.12 + 0.88 * f))
    db.ex("update clips set render_status='done', render_progress=100, render_path=? where id=?", (out, clip_id))
