import os, shutil, subprocess, sys, threading, webbrowser
import uvicorn


def open_window(url):
    """Open ClipForge in its own app-style window (no browser tabs) using Edge or Chrome; else the normal browser."""
    pf = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
          os.environ.get("LOCALAPPDATA", "")]
    cands = [shutil.which("msedge"), shutil.which("chrome")]
    for base in pf:
        cands += [os.path.join(base, r"Microsoft\Edge\Application\msedge.exe"),
                  os.path.join(base, r"Google\Chrome\Application\chrome.exe")]
    for c in cands:
        if c and os.path.exists(c):
            try:
                subprocess.Popen([c, f"--app={url}", "--window-size=1480,920"])
                return
            except Exception:
                pass
    webbrowser.open(url)


def main():
    host = os.environ.get("CLIPFORGE_HOST", "127.0.0.1")
    port = int(os.environ.get("CLIPFORGE_PORT", "8000"))
    if host not in ("127.0.0.1", "localhost") and not os.environ.get("CLIPFORGE_PASSWORD"):
        sys.exit("Refusing to open ClipForge to the network without a password. "
                 "Set CLIPFORGE_PASSWORD first (or keep CLIPFORGE_HOST unset to stay on this computer only).")
    if host in ("127.0.0.1", "localhost"):
        threading.Timer(1.5, lambda: open_window(f"http://127.0.0.1:{port}")).start()
    uvicorn.run("clipforge_web.server:app", host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
