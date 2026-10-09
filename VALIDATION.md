# Validation record

Date: **2026-10-09**. Version: **0.1.0**. Platform: local Windows x64.

The source suite passed **54 tests in 34.86 seconds**, with no skipped tests. The actual single-file EXE passed **11 integration checks**, after copying it to a separate path containing spaces and non-ASCII characters, removing Python/Conda environment variables, and restricting PATH to Windows System32.

All inputs are explicitly **synthetic**. Real SEM/TEM instrument data, another physical computer, and a clean Windows VM have not been validated. OCR and reference registration use their real implementations.

## Source acceptance coverage

| Area | Observed result |
|---|---|
| Calibration | 50 nm / 250 px gives 0.2 nm/px; 5 nm produces 25 px geometry and the expected rendered bar cross-section |
| Output scale | Native cropping preserves 25 px; 2× output gives 50 px and matching dimensions |
| View independence | Exports at 50%, 100%, and 200% view zoom decode to identical pixels |
| Reference transfer | 1024² to 2048² content matching gives approximately 2× sampling; 0.5 becomes 0.25 nm/px |
| Reference rejection | Same sampling, footer additions, and crop offsets pass; different fields fail; manual points still need content verification |
| Units and invalid values | nm, μm, µm, um, and Å parse; reciprocal units, nonpositive/nonfinite values, overflow, missing units, and zero endpoint distances fail |
| Crop interaction | All six shapes export; actual events create, move, resize, constrain, close freehand, and edit polygon vertices; alpha matches the shape mask |
| Detection and masks | Bright/dark candidates, manual fallback without OCR, brush/eraser/polygon masks, and endpoint dragging pass |
| Real OCR | RapidOCR reads 50 nm and matches approximately 250 px on the marked synthetic input |
| Linked inset | ROI changes affect pixels; moving the panel preserves the ROI; 80 px shown at 320 px gives a 100 px inset bar for 5 nm |
| Measurements | Source coordinates and axis constraints work; unknown directions report pixels; helper layers stay out of exports by default |
| Protection/comparison | Crop/treatment/annotation overlap hints work; before/difference share the same geometry and display window |
| Raw data | Native 16-bit OME-TIFF crops preserve uint16 values exactly; DPI-only TIFF does not invent calibration |
| Treatment integrity | Only selected masks change; outside pixels and source hashes remain unchanged; editing solid masks withdraws confirmation |
| Projects/recovery | JSON and mask sidecars preserve state; valid backups survive a corrupted main JSON |
| Relinking | Matching hashes pass; mismatches fail; loaded source arrays remain read-only |
| SVG/clipboard | Independent SVG bar rectangles and text, embedded image data, and full-resolution clipboard content |
| GUI/replay | Three input workflows, editing, reopening, export, and clipboard pass; a separate recipe process produces identical PNG pixels |
| Runtime paths | Frozen data stays outside temporary extraction; diagnostic user-directory overrides work |

Additional checks cover calibration conflicts without averaging, square-pixel assumptions, print-size/DPI/point conversion, QImage memory ownership, stale background-result rejection, and display-window reset.

## Actual EXE checks

1. Start a Qt window and generate persistent synthetic examples.
2. Verify examples live outside the one-file extraction directory.
3. Load bundled OCR models and recognize 50 nm / 250 px.
4. Confirm 25 px geometry for a 5 nm bar.
5. Export PNG.
6. Export SVG with vector text and bar.
7. Copy the finished image at full resolution.
8. Save and reload a project with masks.
9. Write recovery state.
10. Preserve the input image hash.
11. Export an exact native 16-bit TIFF crop.

Local reports are under `test-output`, intentionally excluded from Git. A checked screenshot is included at `docs/images/editor.png`.

## Environment and reproduction

- Python 3.13.5, PySide6 6.9.3, OpenCV 4.12.0.88, NumPy 2.2.6.
- RapidOCR 1.2.3 and ONNX Runtime 1.31.0, using local CPU models.
- PyInstaller 6.12.0 and hooks-contrib 2025.1.
- `pip check`: no dependency conflicts.
- Complete versions: `requirements-lock.txt` and `requirements-build.txt`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=test-output\pytest-results.xml
.\build_exe.ps1
.\.venv\Scripts\python.exe scripts\verify_exe.py
```

The 54 tests comprise 43 core/parameterized cases, 8 GUI cases, 1 independent recipe process, and 2 runtime-path cases. GUI checks use real Qt mouse and keyboard events. Event processing is interleaved with waits that release the Python GIL so workers can complete.

## Performance and limits

Synthetic 1024² previews were approximately 0.10–0.14 seconds in this environment; masks and candidates add work. 2048² pairing and inset interaction passed. These observations are not performance guarantees.

OCR initialization limits ONNX threads without changing installed third-party source. Candidate checks use local regions. Preview jobs use debouncing and reject stale results. Raster text uses Qt glyph outlines for reproducibility with the same fonts; SVG retains editable text.

Unverified areas include real instruments, vendor metadata, other machines, and different font environments. OCR and registration evidence require review. Single-page TIFF is supported; DM3/DM4, batches, FFT, PDF, inpainting, and generative filling are outside this version. The 150 MP ceiling does not guarantee enough memory.
