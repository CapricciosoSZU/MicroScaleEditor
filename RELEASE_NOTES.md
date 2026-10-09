# MicroScale Editor v0.1.0

First public release of a local SEM/TEM real-space image editor for Windows x64.

## Downloads

- **MicroScaleEditor.exe** — standalone application; no Python installation required.
- **MicroScaleEditor-v0.1.0-Windows-x64.zip** — the application with English documentation and third-party notices.
- **SHA256SUMS.txt** — integrity checksums for both downloads.

Double-click the EXE, then choose **File → Synthetic examples** for known calibration inputs. Included OCR models run locally without a download, account, or GPU.

## Features

- Manual, endpoint, OME metadata, OCR-assisted, and paired-reference calibration with explicit confirmation.
- Six crop shapes, configurable physical bars, separate annotation masks, and linked source insets.
- Measurements, protected regions, before/after comparison, export checks, history, and recovery.
- PNG, original-dtype data TIFF, presentation TIFF, and editable SVG annotations with recipes and source hashes.
- English interface, user guide, build instructions, and reproducible synthetic examples.

## Verification

**54 source tests passed**, plus **11 integration checks inside the actual EXE**. The EXE ran from an independent Unicode path with Python/Conda removed from its process environment. Checks included bundled OCR, scale geometry, PNG/SVG, clipboard, recovery, source integrity, and 16-bit TIFF cropping.

All validation inputs are synthetic. Real SEM/TEM data and a clean Windows machine remain untested. Recognition and registration provide evidence for review; annotation treatment cannot recover hidden specimen pixels.

The application is portable and unsigned. Persistent examples, logs, and recovery records live under `%LOCALAPPDATA%\MicroScaleEditor`. See the repository README, user guide, and validation record for details.
