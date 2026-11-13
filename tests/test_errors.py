"""Tool failures reach the user as one plain reason, not a log dump. Run: python tests/test_errors.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge.util import Job, probe, which  # noqa: E402

script = "import sys; sys.stderr.write('WARNING: no JS runtime\\nERROR: [youtube] abc: This video is unavailable\\n'); sys.exit(1)"
try:
    Job(log=lambda m: None).run([sys.executable, "-c", script])
    raise AssertionError("should fail")
except RuntimeError as e:
    assert str(e).endswith("failed: This video is unavailable"), e

bad = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
bad.write(os.urandom(5000)); bad.close()
try:
    probe(which("ffprobe"), bad.name)
    raise AssertionError("should fail")
except RuntimeError as e:
    assert "damaged" in str(e), e
print("ok")
