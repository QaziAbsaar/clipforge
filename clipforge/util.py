"""Process control (cancel / stop file), ffprobe helper."""
import json, os, shutil, subprocess, sys, tempfile, threading, time


class Cancelled(Exception):
    pass


def which(name, bin_dir=None):
    exe = name + (".exe" if os.name == "nt" else "")
    dirs = [bin_dir] if bin_dir else []
    p = shutil.which(name)
    if p:
        return p
    # pip puts tools in Python's Scripts folder, which is not always on PATH; winget uses its Links folder
    dirs += [os.path.join(sys.prefix, "Scripts"), os.path.join(os.path.dirname(sys.executable), "Scripts"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")]
    for d in dirs:
        c = os.path.join(d, exe)
        if d and os.path.exists(c):
            return c
    raise RuntimeError(f"'{name}' not found. Run Install-Windows.bat, or install it and restart ClipForge.")


def kill_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            p.kill()
    except Exception:
        pass


class Job:
    """Runs child processes and lets you stop everything: Ctrl+C, job.cancel(),
    or by creating the stop file (e.g. a STOP file in the output folder)."""

    def __init__(self, stop_file=None, log=print):
        self.stop_file = stop_file
        self.log = log
        self.cancelled = threading.Event()
        self.procs = set()
        self.show_output = True
        self.lock = threading.Lock()

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            for p in list(self.procs):
                kill_tree(p)

    def check(self):
        if self.stop_file and os.path.exists(self.stop_file):
            self.cancelled.set()
        if self.cancelled.is_set():
            self.cancel()
            raise Cancelled()

    def run(self, cmd, cwd=None, show=False):
        self.check()
        err = tempfile.TemporaryFile()
        p = subprocess.Popen(cmd, cwd=cwd, stdout=None if (show and self.show_output) else subprocess.DEVNULL, stderr=err)
        with self.lock:
            self.procs.add(p)
        try:
            while p.poll() is None:
                time.sleep(0.2)
                self.check()
        finally:
            with self.lock:
                self.procs.discard(p)
        err.seek(0)
        text = err.read().decode(errors="replace")
        err.close()
        if p.returncode != 0:
            raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(str, cmd[:2]))}\n{text[-1500:]}")
        return text


def _run_lines(self, cmd, on_line, cwd=None):
    """Like run(), but hands every output line to on_line() while the program runs (for progress bars)."""
    self.check()
    err = tempfile.TemporaryFile()
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=err, text=True, bufsize=1, errors="replace")
    with self.lock:
        self.procs.add(p)

    def reader():
        for line in p.stdout:
            try:
                on_line(line.strip())
            except Exception:
                pass
    th = threading.Thread(target=reader, daemon=True)
    th.start()
    try:
        while p.poll() is None:
            time.sleep(0.2)
            self.check()
    finally:
        with self.lock:
            self.procs.discard(p)
    th.join(timeout=3)
    err.seek(0)
    text = err.read().decode(errors="replace")
    err.close()
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(str, cmd[:2]))}\n{text[-1500:]}")
    return text


Job.run_lines = _run_lines


def probe(ffprobe, path):
    r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate",
                        "-show_entries", "format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    s = d["streams"][0]
    n, _, den = s["r_frame_rate"].partition("/")
    fps = float(n) / float(den or 1)
    return {"w": int(s["width"]), "h": int(s["height"]), "fps": fps or 30.0,
            "duration": float(d["format"]["duration"])}
