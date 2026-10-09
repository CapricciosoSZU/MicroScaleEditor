"""Collect notices shipped with the installed runtime and build distributions."""
from importlib import metadata
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "third-party-licenses"
NAMES = ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "numpy", "opencv-python", "tifffile", "imagecodecs", "rapidocr-onnxruntime", "onnxruntime", "Pillow", "shapely", "pyclipper", "PyYAML", "six", "flatbuffers", "packaging", "protobuf", "pyinstaller")

def main():
    DEST.mkdir(exist_ok=True)
    inventory = []
    for name in NAMES:
        dist = metadata.distribution(name)
        copied = []
        for relative in dist.files or []:
            basename = Path(relative).name.lower()
            if not any(basename.startswith(prefix) for prefix in ("license", "copying", "copyright", "thirdpartynotices", "notice")) or basename.endswith((".xml", ".py", ".pyc")):
                continue
            source = Path(dist.locate_file(relative))
            if not source.is_file():
                continue
            destination = DEST / name / str(relative).replace("../", "parent/").replace("..\\", "parent/")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(destination.relative_to(DEST).as_posix())
        inventory.append({"name": name, "version": dist.version, "home_page": dist.metadata.get("Home-page"), "project_urls": dist.metadata.get_all("Project-URL", []), "license_expression": dist.metadata.get("License-Expression"), "notices": copied})
    python_license = next((Path(sys.base_prefix) / name for name in ("LICENSE_PYTHON.txt", "LICENSE.txt", "LICENSE") if (Path(sys.base_prefix) / name).is_file()), None)
    if python_license is None:
        raise RuntimeError("Python license text not found in the base interpreter; obtain the matching upstream text.")
    shutil.copy2(python_license, DEST / "LICENSE_PYTHON.txt")
    (DEST / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(f"Collected {sum(len(item['notices']) for item in inventory)} notices from {len(inventory)} distributions.")

if __name__ == "__main__":
    main()
