"""Entry point for the PyInstaller-built ClipForge executable."""
import os
import sys
import multiprocessing
import shutil
import subprocess

multiprocessing.freeze_support()

# The installer puts ffmpeg, ffprobe, yt-dlp and streamlink in bin\ next to ClipForge.exe
if getattr(sys, "frozen", False):
    _bin = os.path.join(os.path.dirname(sys.executable), "bin")
    os.environ["PATH"] = os.pathsep.join([_bin, os.path.join(_bin, "streamlink", "bin"), os.environ.get("PATH", "")])

# On Windows, suppress black console windows for all child processes (ffmpeg, yt-dlp, ffprobe)
if os.name == "nt" and not getattr(subprocess, "_clipforge_silent_applied", False):
    _RealPopen = subprocess.Popen

    class _SilentPopen(_RealPopen):
        def __init__(self, *args, **kwargs):
            cmd = args[0] if args else kwargs.get("args")
            is_browser = False
            if cmd and isinstance(cmd, (list, tuple)) and len(cmd) > 0:
                c0 = str(cmd[0]).lower()
                if "msedge" in c0 or "chrome" in c0:
                    is_browser = True
            if not is_browser:
                kwargs["creationflags"] = (kwargs.get("creationflags") or 0) | subprocess.CREATE_NO_WINDOW
                si = kwargs.get("startupinfo")
                if si is None:
                    si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                kwargs["startupinfo"] = si
                if "stdin" not in kwargs or kwargs.get("stdin") is None:
                    kwargs["stdin"] = subprocess.DEVNULL
            super().__init__(*args, **kwargs)

    subprocess.Popen = _SilentPopen
    subprocess._clipforge_silent_applied = True

# In Windows GUI mode (console=False), sys.stdout and sys.stderr are None.
# Redirect them to prevent crashes when libraries write or flush to stdout/stderr.
if sys.stdout is None or sys.stderr is None:
    try:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        data_dir = os.environ.get("CLIPFORGE_DATA") or os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        log_path = os.path.join(data_dir, "clipforge.log")
        log_f = open(log_path, "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = log_f
        if sys.stderr is None:
            sys.stderr = log_f
    except Exception:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")

# Sync cookies.txt on startup if found
try:
    from clipforge.source import find_cookie_file
    cf = find_cookie_file()
    if cf and os.path.isfile(cf):
        targets = []
        if getattr(sys, "frozen", False):
            targets.append(os.path.join(os.path.dirname(sys.executable), "cookies.txt"))
        for t in targets:
            if not os.path.exists(t) or os.path.getsize(t) != os.path.getsize(cf):
                try:
                    os.makedirs(os.path.dirname(t), exist_ok=True)
                    shutil.copy2(cf, t)
                except Exception:
                    pass
except Exception:
    pass

import clipforge_web.server
from clipforge_web.__main__ import main
main()
