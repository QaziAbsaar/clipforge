"""Frame-accurate cut + 9:16 (1080p / 1440p / 4K) + burned-in captions + music/SFX mix."""
import os

ENC = {
    "libx264": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19"],
    "h264_qsv": ["-c:v", "h264_qsv", "-global_quality", "22"],   # Intel Quick Sync - test on your PC
    "h264_nvenc": ["-c:v", "h264_nvenc", "-cq", "22"],           # NVIDIA - only if your GPU supports it
}
RES = {1080: (1080, 1920), 1440: (1440, 2560), 2160: (2160, 3840)}


def _audio_graph(music, music_vol, duck, sfx, first_input):
    voice = "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
    if not music and not sfx:
        return voice + "[aout]", []
    inputs, parts, mix, n = [], [], ["[voice]"], first_input
    parts.append(voice + (",asplit=2[voice][sc]" if (music and duck) else "[voice]"))
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        parts.append(f"[{n}:a]aresample=48000,volume={music_vol}[mus]")
        if duck:
            parts.append("[mus][sc]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=350[md]")
            mix.append("[md]")
        else:
            mix.append("[mus]")
        n += 1
    for k, (path, at, vol) in enumerate(sfx):
        ms = int(max(at, 0) * 1000)
        inputs += ["-i", path]
        parts.append(f"[{n}:a]aresample=48000,adelay={ms}|{ms},volume={vol}[s{k}]")
        mix.append(f"[s{k}]")
        n += 1
    parts.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0,"
                 "alimiter=limit=0.95[aout]")
    return ";".join(parts), inputs


def render_clip(job, ffmpeg, src, info, start, end, ass_path, out_path, layout="follow", crop_x=0.5,
                encoder="libx264", fps=30, res=1080, music=None, music_vol=0.18, duck=True, sfx=(),
                track=None, on_progress=None):
    W, H = RES[res]
    w, h = info["w"], info["h"]
    dur = end - start
    tmp = os.path.dirname(os.path.abspath(ass_path))
    ass = os.path.basename(ass_path)  # relative name avoids Windows 'C:' escaping problems
    cam = (track or {}).get("cam") if layout in ("stack", "pip") else None
    if layout == "pip" and cam and w / h > 9 / 16 + 0.01:
        # gameplay fills the frame, facecam floats in a small box at the top centre
        from .faces import PIP_SIZE, PIP_TOP
        gw = int(h * 9 / 16) // 2 * 2
        gx = int((w - gw) * min(max(crop_x, 0), 1)) // 2 * 2
        cx, cy, cw_, ch_ = track.get("box") or cam
        pw = int(W * PIP_SIZE) // 2 * 2
        fc = (f"[0:v]split[a][b];[b]crop={gw}:{h}:{gx}:0,scale={W}:{H}:flags=lanczos[bg];"
              f"[a]crop={cw_}:{ch_}:{cx}:{cy},scale={pw}:-2:flags=lanczos[pip];"
              f"[bg][pip]overlay=(W-w)/2:{int(H * PIP_TOP)},setsar=1,ass={ass}[v]")
    elif layout == "stack" and cam and w / h > 9 / 16 + 0.01:
        # facecam on top, gameplay underneath: the standard gaming Shorts/Reels/TikTok layout
        from .faces import TOP_SHARE
        th = int(H * TOP_SHARE) // 2 * 2
        bh = H - th
        gw = min(w, int(h * W / bh)) // 2 * 2
        gx = int((w - gw) * min(max(crop_x, 0), 1)) // 2 * 2
        cx, cy, cw_, ch_ = cam
        fc = (f"[0:v]split[a][b];[a]crop={cw_}:{ch_}:{cx}:{cy},scale={W}:{th}:flags=lanczos[top];"
              f"[b]crop={gw}:{h}:{gx}:0,scale={W}:{bh}:flags=lanczos[bot];[top][bot]vstack,setsar=1,ass={ass}[v]")
    elif layout in ("blur", "stack", "pip") or w / h <= 9 / 16 + 0.01:     # stack without a facecam: whole gameplay, blurred fill
        fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"boxblur=25:6[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,ass={ass}[v]")
    elif layout == "follow" and track and track.get("pts"):
        from .faces import crop_width, write_sendcmd
        cw = crop_width(h)
        cmd_name = os.path.splitext(ass)[0] + ".cmd"
        x0 = write_sendcmd(track["pts"], os.path.join(tmp, cmd_name))
        fc = (f"[0:v]sendcmd=f={cmd_name},crop={cw}:{h}:{x0}:0,scale={W}:{H}:flags=lanczos,setsar=1,ass={ass}[v]")
    else:
        cw = int(h * 9 / 16) // 2 * 2
        x = int((w - cw) * min(max(crop_x, 0), 1)) // 2 * 2
        fc = f"[0:v]crop={cw}:{h}:{x}:0,scale={W}:{H}:flags=lanczos,setsar=1,ass={ass}[v]"
    af, extra_in = _audio_graph(music, music_vol, duck, sfx, 1)
    cmd = ([ffmpeg, "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", os.path.abspath(src)] + extra_in +
           ["-filter_complex", fc + ";" + af, "-map", "[v]", "-map", "[aout]"] + ENC[encoder] +
           ["-r", str(fps), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{dur:.3f}", "-movflags", "+faststart", os.path.abspath(out_path)])
    if on_progress:
        def line(s):
            if s.startswith("out_time_us=") or s.startswith("out_time_ms="):
                try:
                    on_progress(min(0.99, int(s.split("=")[1]) / 1e6 / dur))
                except ValueError:
                    pass
        job.run_lines(cmd[:1] + ["-progress", "pipe:1", "-nostats"] + cmd[1:], line, cwd=tmp)
    else:
        job.run(cmd, cwd=tmp)
