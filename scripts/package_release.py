"""Package the verified Windows binary, docs, and notices; write checksums."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def main():
    exe = DIST / "MicroScaleEditor.exe"
    evidence = json.loads((ROOT / "docs/RELEASE_VALIDATION.json").read_text(encoding="utf-8"))
    if evidence.get("status") != "passed" or not evidence.get("frozen") or digest(exe) != evidence.get("sha256"):
        raise RuntimeError("Verify the exact EXE using scripts/verify_exe.py before packaging.")
    archive = DIST / "MicroScaleEditor-v0.1.0-Windows-x64.zip"
    files = [ROOT / name for name in ("README.md", "PACKAGING.md", "VALIDATION.md", "RELEASE_NOTES.md", "THIRD_PARTY_NOTICES.md")]
    files += [path for folder in ("docs", "third-party-licenses", "examples") for path in (ROOT / folder).rglob("*") if path.is_file() and not path.name.endswith(".bak")]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        zipped.write(exe, "MicroScaleEditor/MicroScaleEditor.exe")
        for path in files:
            zipped.write(path, "MicroScaleEditor/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError("Release archive failed integrity validation.")
    checksums = "".join(f"{digest(path)}  {path.name}\n" for path in (exe, archive))
    (DIST / "SHA256SUMS.txt").write_text(checksums, encoding="ascii")
    print(checksums, end="")
    print(f"ZIP integrity checked; {len(files) + 1} entries.")

if __name__ == "__main__":
    main()
