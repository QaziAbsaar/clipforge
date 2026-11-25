"""Start a built ClipForge exe and check it works.
Run: python tests/test_dist_smoke.py path/to/ClipForge.exe   (skips when no path is given)"""
import json, os, subprocess, sys, tempfile, time, urllib.request

if len(sys.argv) < 2:
    print("skip: pass the path to the built ClipForge exe")
    sys.exit(0)

exe = os.path.abspath(sys.argv[1])
data = tempfile.mkdtemp()
env = dict(os.environ, CLIPFORGE_PORT="7890", CLIPFORGE_DATA=data)
proc = subprocess.Popen([exe], env=env)


def get(path):
    with urllib.request.urlopen("http://127.0.0.1:7890" + path, timeout=5) as r:
        return r.status, json.loads(r.read() or b"null")


try:
    for _ in range(90):                              # the first start unpacks a lot, give it time
        time.sleep(1)
        try:
            if get("/healthz")[0] == 200:
                break
        except Exception:
            pass
        if proc.poll() is not None:
            raise SystemExit(f"ClipForge exited with code {proc.returncode}")
    else:
        raise SystemExit("ClipForge did not start in 90 s")

    _, health = get("/api/health")
    print("health:", health)
    missing = [k for k, ok in health.items() if not ok]
    assert not missing, f"missing in the build: {missing}"
    _, settings = get("/api/settings")
    assert settings.get("voice"), "voice-over (piper) is missing in the build"
    assert get("/api/videos")[0] == 200
    with urllib.request.urlopen("http://127.0.0.1:7890/", timeout=5) as r:
        assert b"ClipForge" in r.read()
    print("ok")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    log = os.path.join(data, "clipforge.log")
    if os.path.exists(log):
        print("--- clipforge.log ---")
        print(open(log, encoding="utf-8", errors="replace").read()[-4000:])
