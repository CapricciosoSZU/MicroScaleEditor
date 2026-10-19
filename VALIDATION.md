# Validation record

Date: **2026-10-19**. Version: **0.2.4**. Platform: local Windows x64.

The source suite passed **116 tests in 93.51 seconds**, with no skipped tests. The final frozen EXE passed **35 general checks plus the complete 59-image corpus check** (36 top-level checks) in **150.72 seconds**, from a separate Unicode directory with Python/Conda variables removed and PATH restricted to Windows System32. Every image in this run passed GUI loading, independent decoding comparison, PNG export, project save/load, exact native TIFF cropping, source-format export with original bit depth, and unchanged source hashes. Lossless source-format crops matched the source samples exactly; JPEG is re-encoded. The exact binary hash and completed results are recorded in `docs/RELEASE_VALIDATION.json`.

Public examples are explicitly **synthetic**. Private validation for this binary covers **59 images**: 58 images from the previously supplied TEM folder and the supplied 4096 × 4096 uint8 TIFF style reference. The original 71-image SEM folder is no longer available at its supplied location and was not rerun for v0.2.4; its last complete frozen validation was in v0.2.3 (130 images total). It includes LZW-compressed float32 TEM images. The reference appearance was inspected locally; only a synthetic style illustration is distributed. Input files, filenames, detailed logs, and real-image screenshots remain local. Another physical computer and a clean Windows VM remain untested. Successful import and appearance matching do not establish calibration accuracy.

## Source acceptance coverage

| Area | Observed result |
|---|---|
| Application theme | Light/dark startup palettes, all property tabs, painted image-list pixels, menus, combo popups, progress, top-level Qt dialogs, and active/inactive/disabled/selected/placeholder text pass. Tested foreground/background palette pairs meet a 4.5:1 contrast ratio |
| Calibration | 50 nm / 250 px gives 0.2 nm/px; 5 nm produces 25 px geometry and the expected rendered bar cross-section |
| Output scale | 1×/2×/4× GUI presets preserve physical length and scale annotation layout; a 5 nm bar grows from 25 to 50 to 100 output pixels |
| Label placement | Labels always sit above main and inset bars. Legacy below settings normalize on project/template load; both GUI previews, end ticks, outlined/plain text, print mode, PNG, and editable SVG pass |
| Velox-style | New main/inset styles use white fill and black outlines. Legacy projects retain unoutlined styles. 1×/2×/4× raster scans preserve the calibrated outer span; text/tick bounds, print thickness, native uint16 export, editable SVG, and GUI template roundtrips pass |
| Default format | The actual GUI export dialog and a separate recipe process default to the source file type and bit depth |
| Source precision | Annotated uint16 TIFF/PNG, float32 TIFF, RGB/RGBA, native-precision insets, grayscale mapping, rotated transparency, and JPEG re-encoding pass |
| Rotation | 90°/180°/270° are exact sample permutations at native 1×; custom-angle float ramps agree with the inverse affine transform; axis exchange, masks, bars, insets, dragging, SVG, history, and project replay pass |
| Shift endpoint constraint | GUI drags at different zooms, either endpoint, live Shift toggling, final release coordinates, undo, saved projects, and horizontal-only calibration pass |
| Calibration feedback | Cropping retains confirmation; endpoint edits set Pending and hide the bar with actionable feedback; confirmation exits the endpoint tool |
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

The self-test retains the following 11 original checks, plus centered startup and four LZW dtype/channel regressions (uint8 gray, uint16 gray, RGBA, float32 with floating-point prediction). Seven added checks cover exact quarter-turn samples, crop/calibration retention, rotated dimensions, custom-angle bar placement, preview/export agreement, saved rotation, and endpoint feedback. Four more verify the default source format, 2× annotated uint16 PNG and float32 TIFF precision, and the GUI resolution preset. Two further checks verify the default Velox-style appearance and editable SVG outlines. Two label-placement checks verify legacy main/inset settings and fixed rendering above the bar. Two Shift-drag checks verify horizontal source endpoints and the retained calibration-review requirement. Two theme checks verify readable application panels from injected light/dark startup palettes and save screenshots. The private corpus adds one top-level aggregate check.

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

Local reports are under `test-output`, intentionally excluded from Git. A checked screenshot is included at `docs/images/editor.png`. Theme startup screenshots were also inspected locally. Theme tests inject palettes through Qt without changing Windows personalization; live Windows theme switching and native Windows file-picker appearance were not automated.

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

The 116 tests include real Qt mouse/keyboard events, independent recipe processes, compression decoding, scientific precision comparisons, and geometry checks. The GUI export regression uses the default format dialog, verifies 2×/4× annotation layout and dimensions, checks undo, and decodes the resulting 16-bit TIFF. Nine style cases and one additional GUI case cover outlined geometry and preset/template compatibility. Ten additional cases cover fixed label placement and legacy template/project compatibility. Six further GUI cases cover Shift-constrained endpoint interaction. Two additional GUI cases cover theme inheritance and contrast. Event processing is interleaved with waits that release the Python GIL so workers can complete.

## Performance and limits

Synthetic 1024² previews were approximately 0.10–0.14 seconds in this environment; masks and candidates add work. 2048² pairing and inset interaction passed. These observations are not performance guarantees.

OCR initialization limits ONNX threads without changing installed third-party source. Candidate checks use local regions. Preview jobs use debouncing and reject stale results. Raster text uses Qt glyph outlines for reproducibility with the same fonts; SVG retains editable text.

Unverified areas include calibration accuracy on real data, complex vendor metadata, other machines, and different font environments. OCR and registration evidence require review. Single-page TIFF is supported; DM3/DM4, batch export queues, FFT, PDF, inpainting, and generative filling are outside this version. The 150 MP ceiling does not guarantee enough memory.

## Private real-image workflow

Each supported image is opened through the GUI, compared against the independent Pillow decoder, exported as PNG, saved/reloaded as a project, cropped to a native-data TIFF, and exported in its original format. Crop values and dtype must match the source slice exactly for data TIFF and lossless source-format outputs. File type, bit depth, and dimensions are checked for all source-format outputs, including JPEG; input SHA-256 must remain unchanged. Float32 TEM samples stay float32. Synthetic calibrated images separately test visible annotations at higher resolution; no calibration is invented for the private microscope corpus.

OCR is exercised on representative images from each compression class. Candidate counts are execution evidence, not ground truth for scale calibration. No detected real-image calibration is automatically confirmed. DOCX documents and a database file are outside the supported image formats. Public release evidence contains only anonymous counts and format/dtype summaries.

```powershell
.\.venv\Scripts\python.exe scripts\verify_exe.py --test-images C:\path\to\sem --test-images E:\path\to\tem
```
