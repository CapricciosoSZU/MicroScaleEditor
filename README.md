# MicroScale Editor

**A local desktop editor for calibrated, traceable SEM/TEM real-space images.**

Crop images, review calibration evidence, edit scale-bar annotations, create linked insets, and export presentation figures alongside preserved scientific data. The interface is English. Processing stays local, with no account, cloud service, or GPU required.

[Download for Windows](https://github.com/CapricciosoSZU/MicroScaleEditor/releases/latest) · [User guide](docs/USER_GUIDE.md) · [Build instructions](PACKAGING.md) · [Validation](VALIDATION.md)

![Packaged MicroScale Editor running on a synthetic example](docs/images/editor.png)

> All publicly included images are explicitly **SYNTHETIC**. Private SEM/TEM files are used only for local validation; neither those images nor their filenames are published. See the validation record for the tested scope.

## Features

- **Calibration with evidence:** manual sample spacing, endpoint measurements, OME-TIFF physical sizes, local OCR candidates, and transfer from a matching reference. Calibration remains pending until reviewed and confirmed.
- **Six crop shapes:** rectangle, square, circle, ellipse, polygon, and freehand, with fixed/custom aspect ratios and transparent output.
- **Editable scale bars:** physical length, position, font, color, thickness, end ticks, background plate, and reusable styles. A 5 nm bar at 0.2 nm/px is 25 native output pixels.
- **Explicit annotation treatment:** separate line/text/background masks, with keep, crop, solid-fill, and opaque-plate workflows. Original pixels remain read-only.
- **Linked insets:** select a source ROI and move or resize its output panel, with an independently calculated scale bar.
- **Review tools:** source-coordinate measurements, protected regions, before/after comparison, change overlays, and export checks.
- **Traceable outputs:** PNG, presentation TIFF, source-dtype data TIFF, editable SVG annotations, JSON recipes, source hashes, project history, and recovery.
- **Offline OCR:** Windows downloads include RapidOCR, ONNX Runtime CPU, and recognition models; no runtime model download.
- **Compressed TIFF input:** bundled imagecodecs decoders support LZW images, including 8-bit, 16-bit, RGBA, and 32-bit floating-point samples.
- **Multiple-image import:** select several files in **Open image…** using Ctrl/Shift/Ctrl+A. Each image has independent calibration and edits. Exports are currently performed per image.

## Get started on Windows

1. Download `MicroScaleEditor.exe` from the [latest release](https://github.com/CapricciosoSZU/MicroScaleEditor/releases/latest). The portable ZIP adds documentation and third-party notices.
2. Double-click the EXE. No Python installation is needed. It opens centered on the monitor containing the pointer and fits within the usable screen area. Initial extraction of bundled libraries may take a few seconds.
3. Choose **File → Synthetic examples** to try a known example, or open your own image.
4. Review and confirm sample calibration, choose a crop, adjust the bar, and run **Export check**.

The portable Windows x64 release has no installer or automatic updater. Logs, generated examples, and recovery files live under `%LOCALAPPDATA%\MicroScaleEditor`. Source images are not overwritten. The binary is not code-signed.

### A simple scale-bar workflow

For an image with a known **50 nm / 250 px** bar:

1. Open it and select **Source → Old scale detection and mask tools → Detect + OCR**.
2. Select a candidate and inspect its endpoints, number, and unit. Correct them manually when needed.
3. Use the endpoints, explicitly confirm any square-pixel assumption, and confirm calibration.
4. Choose how to treat the old annotation. A plate covers pixels; it cannot recover hidden specimen information.
5. Enable the new bar, enter `5 nm`, and apply the style: **25 px** at native sampling, **50 px** at 2× output.

See the [user guide](docs/USER_GUIDE.md) for clean-source, annotated-source, and paired-reference workflows.

## Export formats

| Format | Contents |
|---|---|
| PNG | 8-bit RGBA presentation using the recorded display window; transparency supported |
| TIFF presentation + data | An 8-bit presentation TIFF plus a separate original-dtype `_data.tif` |
| TIFF data only | Source values cropped without burning annotations or treatment layers into them; exact at native 1× sampling |
| SVG | Embedded raster image with independent editable bars, labels, and inset objects |

Every export includes a JSON sidecar with the transform, source hash, calibration, display mapping, and recipe. Nonrectangular data TIFFs retain original bounding-box values and use a separate validity mask. DPI/PPI and nominal magnification are never treated as specimen calibration.

![Synthetic output with a linked inset and separate scale bars](examples/SYNTHETIC_demo_output.png)

## Run from source

Python 3.11–3.13 is supported by the declared dependencies. The validated environment is Python 3.13.5 on Windows; other versions and platforms have not been tested here.

```powershell
git clone https://github.com/CapricciosoSZU/MicroScaleEditor.git
cd MicroScaleEditor
.\setup.ps1 -OCR
.\launch.ps1 -Examples
```

Use `-Python 'C:\path\to\python.exe'` to choose an interpreter. Setup creates an isolated `.venv`. OCR is optional for source installations; manual calibration, cropping, masks, and export work without it.

```powershell
# Open the portable demonstration project
.\.venv\Scripts\python.exe -m microscale examples\SYNTHETIC_demo.micro.json
# Install OCR later
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
# Rebuild the Windows application
.\build_exe.ps1 -InstallBuildTools
```

Core dependencies: NumPy, OpenCV, PySide6, tifffile, and imagecodecs. Tested versions are in `requirements-lock.txt`; build tools are in `requirements-build.txt`.

## Reproduce and test

```powershell
# Uses real Qt windows, input events, OCR, and the clipboard
.\.venv\Scripts\python.exe -m pytest -q
# Replay a project in a separate process
.\.venv\Scripts\python.exe -m microscale --recipe examples\SYNTHETIC_demo.micro.json --output replay.png --format png
# Generate the synthetic demonstration
.\.venv\Scripts\python.exe scripts\build_demo.py
# Test a copied EXE with Python removed from its process search path
.\.venv\Scripts\python.exe scripts\verify_exe.py
```

Checks cover synthetic geometry, compressed TIFF decoding, multiple-image import, centered startup, bundled OCR, PNG/SVG, clipboard, recovery, and native data preservation. Private SEM/TEM folders are also exercised locally. The exact EXE checksum and results are in [RELEASE_VALIDATION.json](docs/RELEASE_VALIDATION.json); the scope and limits are in [VALIDATION.md](VALIDATION.md). This is local Windows verification, not a clean-machine or calibration-accuracy certification.

## Project structure

| Module | Responsibility |
|---|---|
| `image_io.py` | Read-only source arrays, metadata, display mapping, Qt image ownership |
| `geometry.py` | Units, coordinates, crops, physical scale calculations |
| `detection.py` | Local OCR, annotation masks, reference registration |
| `model.py` | Project state, history, hashes, atomic saves, recovery |
| `rendering.py` | Shared composition, export checks, file export |
| `canvas.py` | Source/output viewing and interactive editing |
| `gui.py` | Property panels, document lifecycle, background work |
| `runtime.py` / `diagnostics.py` | Persistent paths and standalone EXE checks |

Edits change parameters and masks, not original arrays. Background results are checked against the current document and revision so stale detection results cannot enter a newly opened image.

## Current limits

- Real-space nm, μm, µm, um, and Å are supported; reciprocal units are rejected.
- A horizontal bar establishes horizontal spacing only. Vertical spacing needs independent evidence or an explicit square-pixel assumption.
- Reference pairing supports translation and uniform scaling. Significant rotation, reflection, distortion, anisotropic scaling, low texture, and different fields of view are rejected.
- Detection prioritizes horizontal bars. OCR, endpoints, metadata, and match quality require review.
- Single-page TIFF is supported. Complex vendor metadata, DM3/DM4, FFT, PDF, batch queues, inpainting, and generative filling are outside this version.
- Rendering uses full-resolution memory. The 150 MP output cap does not guarantee enough RAM for every composition.
- Text uses host fonts; identical reproduction requires the same font environment.

For bugs, include the version, reproduction steps, relevant log excerpts, and a shareable input. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for bundled components and source links.
