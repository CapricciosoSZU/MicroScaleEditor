# Run: .venv\Scripts\python -m PyInstaller --noconfirm MicroScaleEditor.spec
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

root = Path(SPECPATH)
datas = collect_data_files("rapidocr_onnxruntime")
datas += [(str(root / name), "docs") for name in ("README.md", "PACKAGING.md", "THIRD_PARTY_NOTICES.md")]
datas += [(str(root / "docs" / "USER_GUIDE.md"), "docs"), (str(root / "third-party-licenses"), "third-party-licenses")]
binaries = collect_dynamic_libs("onnxruntime")
binaries += collect_dynamic_libs("imagecodecs")
# Conda-backed venvs do not expose these stdlib extension dependencies to
# PyInstaller's normal DLL search. Include them when present; python.org
# builds resolve their own equivalents through the standard hooks.
for dll in ("libmpdec-4.dll", "ffi.dll"):
    candidate = Path(sys.base_prefix) / "Library" / "bin" / dll
    if candidate.is_file():
        binaries.append((str(candidate), "."))
hiddenimports = collect_submodules("rapidocr_onnxruntime")
# TIFF codecs are loaded lazily: static analysis alone can miss their .pyd files.
hiddenimports += collect_submodules("imagecodecs", filter=lambda name: name not in {"imagecodecs.__main__", "imagecodecs.numcodecs", "imagecodecs.zarr"})
hiddenimports += ["onnxruntime.capi.onnxruntime_pybind11_state", "PIL.Image", "PIL.PngImagePlugin", "PIL.JpegImagePlugin", "PIL.TiffImagePlugin"]

a = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "matplotlib", "scipy", "pandas", "IPython", "tkinter", "torch", "tensorflow", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtTest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="MicroScaleEditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    version=str(root / "packaging" / "version.txt"),
    icon=str(root / "packaging" / "microscale.ico"),
)
