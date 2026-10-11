# Windows packaging

`dist/v0.2.1/MicroScaleEditor.exe` is a single-file Windows x64 program containing Python, Qt, OpenCV, tifffile, imagecodecs (including LZW TIFF), and RapidOCR/ONNX CPU models. It runs without this repository, a virtual environment, a separate Python installation, or model downloads.

The portable ZIP also includes English and Simplified Chinese user manuals and third-party license notices. Retain those notices when redistributing.

## Runtime data

Double-click the EXE. **File → Synthetic examples** generates explicitly synthetic inputs. Startup extracts bundled libraries to a temporary directory; disk speed and antivirus scanning affect startup time. Normal exit cleans up extraction files.

Persistent data lives under `%LOCALAPPDATA%\MicroScaleEditor`:

| Path | Purpose |
|---|---|
| `examples` | Generated synthetic source images |
| `logs\microscale.log` | Rotating application log |
| `recovery` | Autosaved projects and backups |
| `startup-error.log` | Unexpected startup failures, if any |

The portable application installs no service and has no automatic updater. It is not code-signed.

## Rebuilding

Use a Windows x64 Python environment:

```powershell
.\setup.ps1 -OCR
.\build_exe.ps1 -InstallBuildTools
# Later builds
.\build_exe.ps1
```

Validated build: Python 3.13.5, PyInstaller 6.12.0, hooks-contrib 2025.1. Runtime and build requirements are separate. The spec collects OCR models, dynamically imported detector modules, and required DLLs. Imagecodecs extension modules and native libraries are collected explicitly because TIFF codecs load lazily. Conda-backed virtual environments need explicit decimal/ctypes DLL collection when those libraries exist.

For an offline base Anaconda installation that already has the required build tools, `scripts/bootstrap_build_tools.py` copies only the listed build distributions into the virtual environment. It changes neither the base installation nor runtime packages. Normal builds should install `requirements-build.txt`.

## Verify the binary

```powershell
# Copies the EXE to a Unicode path and strips Python/Conda environment variables
.\.venv\Scripts\python.exe scripts\verify_exe.py
# Direct diagnostic invocation; opens a real Qt window
Start-Process -FilePath '.\dist\v0.2.1\MicroScaleEditor.exe' -ArgumentList '--self-test', 'C:\checks\microscale' -Wait
# Replay a saved project
Start-Process -FilePath '.\dist\v0.2.1\MicroScaleEditor.exe' -ArgumentList '--recipe', 'C:\data\project.json', '--output', 'C:\data\result.png', '--format', 'png' -WindowStyle Hidden -Wait
```

Recipe replay defaults to `--format source`, retaining the input file type and bit depth with annotations. The output extension is adjusted to match the source. Use explicit `--format png` for the 8-bit presentation shown above.

The diagnostic folder contains `self-test.json`, a screenshot, and exports. Success requires `status: passed` and `frozen: true`. It checks actual local OCR, calibrated bars, rotation, higher-resolution native-precision exports, default source format, PNG/SVG, clipboard, mask save/load, recovery, input hashes, and exact 16-bit TIFF cropping.

`MICROSCALE_USER_DIR` isolates persistent data for diagnostics. It is unnecessary for normal use. This verifies a restricted process environment on the build machine; another physical computer or clean Windows VM remains untested.

## Release contents

- `MicroScaleEditor.exe`: standalone application.
- `MicroScaleEditor-v0.2.1-Windows-x64.zip`: the same application, documentation, and third-party notices.
- `SHA256SUMS.txt`: checksums for both downloads.

The repository excludes virtual environments, builds, binaries, logs, temporary checks, and recovery files. Executables are published in GitHub Releases.

## Local microscopy validation

To test private files recursively in the actual EXE, run:

```powershell
.\.venv\Scripts\python.exe scripts\verify_exe.py --test-images C:\path\to\images
```

This reads supported images, opens them in the GUI, compares decoding with Pillow, exports PNG and native TIFF crops, saves/reloads projects, and checks original hashes. Detailed results stay under ignored `test-output`; only anonymous counts enter the public release report. Recognition runs on one image per compression class, without asserting calibration accuracy. The three DOCX files in the supplied test folder are outside the editor's supported image formats.
