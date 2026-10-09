"""Check a copied EXE in an isolated Unicode path without Python on PATH."""
from pathlib import Path
import json
import hashlib
import os
import shutil
import subprocess
import sys
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
directory = root / "test-output" / ("portable \u72ec\u7acb\u68c0\u67e5 " + uuid4().hex[:8])
directory.mkdir(parents=True, exist_ok=True)
exe = directory / "MicroScaleEditor.exe"
shutil.copy2(root / "dist" / exe.name, exe)
env = dict(os.environ)
for key in list(env):
    if key.upper().startswith(("PYTHON", "CONDA")) or key.upper() in {"VIRTUAL_ENV", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "MICROSCALE_USER_DIR"}:
        env.pop(key)
env["PATH"] = str(Path(env.get("SystemRoot", r"C:\Windows")) / "System32")
env["MICROSCALE_USER_DIR"] = str(directory / "User data")
report_dir = directory / "Check results"
(root / "test-output" / "latest-exe-check.txt").write_text(str(report_dir), encoding="utf-8")
result = subprocess.run([str(exe), "--self-test", str(report_dir)], cwd=directory, env=env, timeout=180)
report = json.loads((report_dir / "self-test.json").read_text(encoding="utf-8"))
print(json.dumps(report, indent=2, ensure_ascii=True))
if result.returncode or report["status"] != "passed" or not report["frozen"]:
    raise SystemExit(result.returncode or 1)
digest = hashlib.sha256(exe.read_bytes()).hexdigest()
assert digest == hashlib.sha256((root / "dist" / exe.name).read_bytes()).hexdigest()
summary = {"version": "0.1.0", "executable": exe.name, "sha256": digest, "size_bytes": exe.stat().st_size,
           "status": report["status"], "frozen": report["frozen"], "synthetic_inputs": True,
           "python_removed_from_path": True, "separate_unicode_directory": True,
           "checks": report["checks"], "check_elapsed_seconds": report["elapsed_seconds"]}
(root / "docs" / "RELEASE_VALIDATION.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
(root / "docs" / "images").mkdir(parents=True, exist_ok=True)
shutil.copy2(report_dir / "packaged-gui.png", root / "docs" / "images" / "editor.png")
