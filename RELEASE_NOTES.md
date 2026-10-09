# MicroScale Editor v0.1.1

Fixes LZW-compressed TIFF loading and centers the editor on startup.

## Fixes and improvements

- Bundles imagecodecs and its native decoder modules. LZW TIFFs open without installing anything separately.
- Preserves grayscale, RGBA, uint16, and float32 data; native TIFF crops retain the original values and dtype.
- Centers the initial window on the monitor containing the pointer, using the usable screen area. Later manual positioning is respected.
- Displays the version in the title bar so an old running copy can be distinguished from the updated application.
- Adds local validation of private image folders, with only anonymous results included in public release evidence.

## Verification

**60 source tests passed.** Local real-image coverage comprises **127 images** across two private SEM/TEM folders: 96 TIFFs, 28 JPEGs, and 3 PNGs. This includes 31 LZW TIFFs, of which 30 contain 32-bit floating-point data.

The final standalone binary passed all 127 images, plus 16 general checks, with Python removed from its process search path. Checks cover decoding, centered startup, OCR execution, PNG/SVG, clipboard, project recovery, exact native TIFF crops, and unchanged input hashes. The exact EXE hash and results are in `docs/RELEASE_VALIDATION.json`.

Private images and filenames are not distributed. Successful import and export do not establish calibration accuracy; scale evidence still requires review.

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no Python installation required.
- **MicroScaleEditor-v0.1.1-Windows-x64.zip** — application, English documentation, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — download checksums.

Use the new executable instead of an already-open v0.1.0 instance. The application remains unsigned; persistent data stays under `%LOCALAPPDATA%\MicroScaleEditor`.

To import several images, choose **Open image…** and select files with Ctrl, Shift, or Ctrl+A. Each source retains independent calibration and edits. Export remains per image.
