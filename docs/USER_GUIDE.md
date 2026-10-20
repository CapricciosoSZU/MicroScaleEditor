# MicroScale Editor — English user manual

[English](USER_GUIDE.md) · [简体中文（zh-CN）](USER_GUIDE.zh-CN.md) · [Project home](../README.md) · [Windows download](https://github.com/CapricciosoSZU/MicroScaleEditor/releases/latest)

Applies to **v0.2.5**. Manual revised **2026-10-20**. The application interface is English; bold names below match its controls. Numerical examples are illustrative, not measurements of your images.

The editor uses a consistent dark interface regardless of the Windows light/dark setting. Image lists, property panels, menus, inputs, and Qt dialogs share readable colors. Native Windows file pickers and window decorations remain managed by Windows. This changes only the interface, not image pixels, scale-bar colors, or export appearance.

MicroScale Editor prepares calibrated SEM/TEM real-space figures. It keeps original image arrays read-only and records cropping, annotation treatment, calibration, and styling separately. Work stays on your computer.

## Contents

1. [Quick start](#quick-start)
2. [Open images and find the controls](#opening-several-images)
3. [Calibrate your image](#three-input-workflows)
4. [Draw and position a scale bar](#scale-bar-styling)
5. [Crop and navigate](#cropping-and-navigation)
6. [Handle an existing scale bar](#existing-annotations-and-masks)
7. [Add a linked inset](#linked-inset)
8. [Measure and review](#measure-and-review)
9. [Export a figure or scientific data](#export)
10. [Save projects and recover work](#projects-recovery-and-replay)
11. [Keyboard and mouse shortcuts](#shortcuts)
12. [Troubleshooting](#troubleshooting)
13. [Supported scope and further help](#scope-and-help)

<a id="quick-start"></a>
## 1. Quick start

For an image with a readable existing scale bar:

1. Click **Open image…** and choose the image.
2. Select **Edit • source coordinates** in the center and **Source** on the right.
3. Click **Pick endpoints**, then **press and drag** from one end of the existing bar to the other. For a horizontal reference, hold **Shift** through mouse release. Zoom in and refine the endpoints as needed.
4. With **Shift** held, the two endpoint **y** values stay equal; you can also set them numerically. **After positioning the endpoints**, enter the existing bar's label in **Known length**, such as `50 nm`.
5. Select **Assume square pixels** only if you have reason to use equal horizontal and vertical sampling. Click **Use endpoints**, review the proposed calibration, then **Confirm calibration**.
6. Open **Scale bar**. Choose a **Preset**, click **Use preset**, then check **Draw a physical scale bar**. Enter the desired **Physical length**, choose **Position**, and click **Apply style / length**.
7. Review the original annotation too: [keep it, crop it away, or apply a documented treatment](#existing-annotations-and-masks). Adding a new bar does not remove an old one.
8. Inspect **Output pixel preview**. In **Export**, click **Export check / locate**, choose **Format**, then **Export…**. Use **Save project…** to retain editable work.

If the source has no readable bar, use known sample spacing, supported metadata, or a verified matching reference as described below. Choose **File → Synthetic examples** to practice on generated examples.

<a id="opening-several-images"></a>
## 2. Open images and find the controls

Download and run `MicroScaleEditor.exe`. No separate Python installation is needed. The title bar shows the version. The initial window centers on the monitor containing the pointer and fits its usable area; it respects later manual positioning.

**Open image…** accepts PNG, JPEG, and supported single-page TIFF files, including LZW-compressed TIFF. To import several files in the same dialog, use **Ctrl+click**, **Shift+click**, or **Ctrl+A**. Imported images appear in the left-hand list. Click a list item to work on that image.

Each image has its own calibration and edits. Importing a group does not calibrate all of them or export them together. **Export is per image** in v0.2.5. Large groups retain their full source arrays in memory; use smaller groups if needed.

| Area | Purpose |
|---|---|
| Left-hand image list | Select a source; open, save, or recover a project |
| **Edit • source coordinates** | Place endpoints, draw crops and masks, move bars and insets |
| **Output pixel preview** | Inspect the composed result; use the edit view to change geometry |
| **Source** | Calibration, reference matching, old annotations, display window |
| **Crop** | Crop shape and linked inset |
| **Scale bar** | New bar length, appearance, and placement |
| **Export** | Output dimensions, checks, format, and clipboard |

![MicroScale Editor showing Scale bar controls on a SYNTHETIC example](images/editor.png)

*Interface example using synthetic data; this is not a specimen image.*

Scroll inside the right-hand panel to reach controls below the visible area. Click collapsed sections such as **Old scale detection and mask tools** to expand them.

**Apply fields before moving on.** Many forms apply only when you click their corresponding **Use…** or **Apply…** button. A committed operation can reload unapplied values. Endpoint dragging now preserves the draft known length, but checking that length after placing the endpoints remains good practice. Choose a preset before editing the new bar's length and style.

<a id="three-input-workflows"></a>
## 3. Calibrate your image

Calibration establishes the real distance represented by one source pixel. It is separate from the length of the new bar you draw.

| Field | Meaning | Example |
|---|---|---|
| **Source → Known length** | The real length of the existing bar or measured reference segment | An existing bar labeled `50 nm` |
| **Horizontal s_x** | Real distance per source pixel along x | `0.2` with **Sample units** set to `nm/px` |
| **Vertical s_y (optional)** | Real distance per source pixel along y | Enter only when known, or use a justified square-pixel assumption |
| **Scale bar → Physical length** | The real length you want the new bar to represent | A new bar labeled `5 nm` |

Example: an existing **50 nm** bar spanning **250 source pixels** gives `50 / 250 = 0.2 nm/px`. A new **5 nm** bar is then **25 pixels** wide at native 1× output, or **50 pixels** at 2× output. These numbers are a worked example, not a calibration to copy onto another image.

### 3.1 Understand calibration status

| Status | What it means |
|---|---|
| **Uncalibrated** | No usable sample spacing has been established |
| **Pending** | A value has been proposed but still needs review and confirmation |
| **Confirmed** | You have accepted the current calibration evidence |

The new scale bars are horizontal and require **confirmed horizontal spacing**. A horizontal reference alone does not establish vertical spacing. Without **Assume square pixels**, a perfectly horizontal segment calibrates x only; a vertical segment calibrates y only. An oblique segment requires a justified square-pixel assumption.

Square pixels are an assumption about specimen sampling, not a claim based on the image being square. DPI/PPI, screen zoom, and a microscope's nominal magnification such as `×70k` do not establish nm/px here.

### 3.2 Method A — manually measure an existing bar

1. Open the image and select **Source** and **Edit • source coordinates**.
2. Zoom in on the existing scale bar using the mouse wheel.
3. Click **Pick endpoints**. Press at one end of the bar, drag to the other, then release. Hold **Shift** through mouse release to constrain the line horizontally. This is a drag gesture, not two separate clicks.
4. Refine the endpoint handles, or type coordinates in **Endpoint 1 · x / y** and **Endpoint 2 · x / y**. Holding **Shift** while moving either endpoint keeps the other endpoint fixed and their y values equal. Pressing or releasing Shift during a drag updates the preview immediately; without Shift, placement is free.
5. After the endpoints are set, enter the printed label in **Known length**, including its unit. For example, enter `5 nm` only when that is the existing bar's actual label.
6. Decide whether **Assume square pixels** is justified. Leaving it unchecked is sufficient to create a horizontal bar from a horizontal reference.
7. Click **Use endpoints**. Review the displayed spacing and evidence.
8. Click **Confirm calibration** and verify that the status is **Confirmed**.

Use the **bar itself**, not the width of its text or background plate. For a solid bar, use its outer edges. For a ruler with end ticks, use the centerlines of the two ticks defining the labeled span. If `500 nm` describes the whole ruler, measure that whole span, not one tick interval. For antialiased edges, inspect the boundary at approximately half the local contrast.

Changing endpoints makes the calibration pending again. Re-enter/check **Known length**, click **Use endpoints**, and confirm again after any correction.

After confirmation, the endpoint tool switches to **Pan** to prevent accidental endpoint edits. Cropping alone preserves confirmed calibration. The **Scale bar** tab shows a live calibration message; **Review calibration** opens the Source tab if a bar is hidden. An endpoint change must be applied with **Use endpoints** before it can be confirmed again.

### 3.3 Method B — use detection and OCR as a starting point

1. Expand **Source → Old scale detection and mask tools**.
2. Click **Detect + OCR**. To restrict detection, click **Detect region** and drag a rectangle around the old annotation in the edit view.
3. Select a candidate in the list and click **Use candidate**.
4. Inspect and correct its endpoints. Then check **Known length**, including the number and unit. Finish with **Use endpoints → Confirm calibration**.

**Use candidate** also adds line/text/background masks for later treatment; it does not by itself erase the annotation. **Ignore false candidate** marks an incorrect detection as ignored.

Detection prioritizes horizontal solid bars. Tick rulers and partial bars need particular care. OCR suggestions are not automatically confirmed. If OCR misses or misreads the label, use Method A instead. An unreadable or incomplete reference cannot establish a reliable length by guessing.

### 3.4 Method C — enter known spacing or review metadata

If you have reliable specimen spacing:

1. In **Source**, choose **Sample units** (`nm/px` or `μm/px`).
2. Enter **Horizontal s_x** and, if independently known, **Vertical s_y (optional)**.
3. If justified, check **Assume square pixels**; this sets vertical spacing equal to the supplied horizontal spacing.
4. Click **Use manual calibration**, review the evidence, then **Confirm calibration**.

Supported OME-TIFF physical sizes and MicroScale sample-space metadata load as **Pending** evidence. Review their values and origin before confirming. General instrument/vendor metadata may not be recognized.

If both axes are independently known, enter both together using **Use manual calibration**. Applying a new endpoint calibration replaces the current axis values; separate horizontal and vertical endpoint operations do not accumulate two axes.

### 3.5 Method D — calibrate a clean source using a matching reference

Use this when a clean source and an annotated reference show the same underlying image content. Similar filenames or equal dimensions are not sufficient evidence.

1. Open the **clean source** first. Click **Source → Set calibration reference…** and select the annotated reference.
2. Click **Automatic content registration**. Inspect **Registered reference / source overlap** and optionally enable **Flicker registered reference / source (pair check only)**.
3. If automatic matching fails, return to **Correspondence points**. **Ctrl+click at least three distributed, noncollinear matching points in each image**, in the same order. Click **Verify manual point pairs** and inspect the overlap. Use **Clear points** to start the pairs again.
4. Select **Assume square pixels in source and reference** only when justified. Without it, use a horizontal reference segment.
5. Establish the reference spacing. Either enter a reliable **Reference s_x (nm/px)**, or use **Detect reference scale + OCR → Use selected reference candidate**, review **Reference bar length**, **Reference p1 x / y**, and **Reference p2 x / y**, then click **Compute reference calibration from endpoints**. You can enter these coordinates and length manually too.
6. Click **Transfer calibration as pending**. Back in the main window, review the transferred evidence and click **Confirm calibration**.

Red correspondence points establish image matching; yellow reference endpoints establish the bar length. They have different purposes. The transfer button stays disabled until registration succeeds. Matching supports translation and uniform scaling, including matching crops or appended footers; unreliable matches and unsupported transformations are rejected. Registration does not resample the clean source.

### 3.6 When calibration sources disagree

The evidence panel compares proposed values against earlier evidence using **Review threshold (%)**, initially 2%. A conflict blocks confirmation until reviewed. Check the unit, endpoints, metadata, and source/reference identity. After deciding the current proposal is correct, select **Reviewed conflict: choose current source**, then **Confirm calibration**. Changing bar appearance does not require recalibration.

<a id="scale-bar-styling"></a>
## 4. Draw and position a scale bar

### 4.1 Create the bar

1. Verify that horizontal calibration is **Confirmed**.
2. Open the **Scale bar** tab.
3. Newly opened images use **Velox-style**: white lettering and bar with black outlines, a left-aligned label above the bar, and bottom-left placement. To apply it to an existing project, choose **Preset → Velox-style → Use preset**. **White**, **Black**, and **White on dark plate** remain available. Apply the preset before entering other style edits.
4. Check **Draw a physical scale bar**.
5. Enter **Physical length**, including the unit, such as `5 nm`, `500 nm`, or `1 μm`. You can also select **Quick physical length** or **Suggested lengths**; then check the populated field.
6. Choose **Position**, such as `bottom-right`, and adjust **Margin (output px)**.
7. Click **Apply style / length**. Inspect the bar and its label in **Output pixel preview**.

The app calculates the bar's width from calibration. You do not draw its width freehand. To change the represented length, edit **Physical length** and apply again. To hide it, uncheck **Draw a physical scale bar** and apply.

**Velox-style** follows the Thermo Fisher Velox appearance in the supplied reference. Initial font, bar, outline, and margin sizes scale with the image size. Existing saved projects and templates retain their other appearance settings; labels always appear above the bar, including when loading a legacy `below` setting. Applying the preset preserves the current physical length and calibration; it does not automatically enable a bar or confirm calibration. The black bar border lies inside the calibrated outer edges: measure the full outer span, not just the inner white portion.

![Velox-style scale bar on a synthetic gradient](images/velox-style.png)

### 4.2 Move the bar and label together

1. Return to **Edit • source coordinates**.
2. In **Scale bar**, click **Drag group**. The toolbar changes to **Move scale**.
3. Drag the bar group to the desired position. With the canvas focused, arrow keys move it by 1 output pixel; **Shift+arrow** moves it by 10.

For numeric placement, choose **Position → custom**, enter **Group x (output px)** and **Group y (output px)**, then apply. These specify the top-left of the whole group, including label/plate space. Dragging switches the group to custom placement. Moving it does not change its physical length.

Double-click the bar/label group in the edit view to enter a new physical length. Keep the whole group inside the valid crop; corners outside a circular or polygon crop are not valid placement areas.

### 4.3 Adjust appearance and reuse a style

| Control | Use |
|---|---|
| **Color** | Color name or `#RRGGBB`, such as `#ffffff` or `#000000` |
| **Bar thickness (px)** | Thickness in output pixels in native/width modes |
| **Background plate** | Add a plate behind the new bar and label |
| **Outline bar and text** | Enable an outline around the lettering and inside the bar; no rectangular background plate is needed |
| **Outline color / Outline width (px)** | Set the outline appearance in the expanded details; width must be less than half the bar thickness and length |
| **Label position** | **Always above the bar**; fixed in main images, insets, previews, clipboard, and exports. Legacy `below` settings load as `above` |
| **Text alignment** | Align label and bar left, center, or right within their shared group |
| **Font, end ticks and background details** | Expand for **End ticks**, **Font family**, **Font size (px)**, **Bold**, **Text gap (px)**, **Plate color**, and **Plate opacity** |

After editing these controls, click **Apply style / length**. In **print** output mode, font size and bar thickness use **Export → Print font / bar (pt)** instead of the pixel fields. Available font families depend on the computer.

In print mode the outline scales with the bar thickness. The **2× / 4×** resolution buttons also scale outline width with the rest of the layout. Outlines are retained in preview, PNG, annotated TIFF/source-format exports, clipboard, and editable SVG text. Plain White/Black presets turn outlining off. Use v0.2.5 or later to reopen projects or templates saved with the new outline fields.

**Save template… / Load template…** store and restore bar styles. **Copy settings… / Paste settings** transfer selected styles/output settings between open images. Calibration is excluded by default. If explicitly copied, it becomes **Pending** and must be reviewed for the destination image.

<a id="cropping-and-navigation"></a>
## 5. Crop and navigate

1. Open **Crop**. Choose **Shape**: `rectangle`, `square`, `circle`, `ellipse`, `polygon`, or `freehand`.
2. Choose **Aspect W:H** if needed. `Custom` uses the value in **Custom W:H**. A fixed ratio changes the crop; it does not stretch the specimen.
3. Use **Draw crop** in the edit view. For rectangular/elliptical shapes, drag the region. For a polygon, click vertices and press **Enter** or right-click to close. Freehand closes when you release the mouse.
4. Drawing automatically switches the toolbar to **Edit crop**. Drag inside the selection to move it. Drag a rectangle edge/corner or an ellipse/circle handle to resize it; square/circle and fixed aspect ratios stay locked. The pointer shows the available action. For numeric rectangular geometry, edit **Source x / y** and **Width / height**, then **Apply geometry**.
5. Choose **Outside shape** (`transparent`, `white`, `black`, or `custom`) and click **Apply background**.

To replace a selection, click **Draw crop** again, then draw the new region (including inside the previous selection). Press **Esc** during a drag to cancel that gesture. **Undo / Redo** restores completed moves and resizes. Moving stays within the source image and does not change confirmed calibration.

For polygon/freehand crops, drag vertices to edit them, Ctrl+click to insert a vertex, and Delete to remove the selected vertex. Keep at least three non-crossing vertices. Nonrectangular exports use the crop's bounding rectangle; the outside area follows the chosen background. The preview checkerboard is not exported.

Use the wheel to zoom, middle-drag or **Pan** to move, **Fit** to see the full view, and **100%** to inspect pixels. Zoom changes the view only. Crop coordinates remain source pixels, while bar placement uses output pixels.

<a id="image-rotation"></a>
### Rotate the output image

1. Open **Crop → Image rotation**.
2. Use **Rotate left 90°**, **Rotate right 90°**, or **Rotate 180°** for a turn relative to the current orientation.
3. For a custom orientation, enter **Angle (° clockwise)** between −180 and 180, then click **Apply rotation**. Positive values rotate clockwise; negative values rotate counterclockwise. This field sets the total angle, rather than adding a turn.
4. Inspect **Output pixel preview**, which opens automatically. **Reset rotation** returns to 0°. Undo/redo, project saves, PNG/TIFF/SVG exports, and the clipboard retain the selected angle.

Rotation applies to the cropped output before new bars, labels, and inset panels are laid out. The canvas expands to contain the whole rotated crop; outside pixels use **Outside shape**. New scale bars stay horizontal. Anchored bars are moved into the valid rotated region when they fit; custom positions remain under your control. The inset sample follows the main rotation, with its own horizontal bar.

**Edit • source coordinates** continues to show the original coordinate orientation for calibration, crop, mask, and ROI editing. Use **Output pixel preview** to see the final rotated image. Changing the output width sizes the expanded rotated canvas. Source arrays and files are unchanged.

At native 1×, quarter turns are exact pixel permutations; custom angles interpolate pixels, including in data TIFFs. Rotation, interpolation, and the source-to-output transform are recorded in export sidecars. A validity mask identifies the retained region.

A 90°/270° turn exchanges the horizontal and vertical sampling directions. If only source x is calibrated, the rotated horizontal direction is unknown and its bar is hidden. Custom-angle physical bars and output axis metadata require confirmed equal x/y spacing; use a justified square-pixel assumption or independently established equal values. With unequal or missing spacing, you can rotate the image, but physical bars must be disabled for presentation export. The app does not invent the missing calibration.

<a id="existing-annotations-and-masks"></a>
## 6. Handle an existing scale bar

Calibrate from an old bar before excluding it from the figure. Then choose an appropriate treatment:

| Choice | Procedure and effect |
|---|---|
| Keep it | Set **Treatment → keep**, then **Apply treatment**; the existing pixels remain |
| Use a clean source | Use the matching-reference workflow to transfer calibration onto the clean image |
| Crop off a footer | Click **Crop off selected footer** and enter the first footer row in source coordinates; all rows from there downward are excluded |
| Fill a uniform annotation area | Mark the area, choose **solid** and **Opaque fill color**, review and check **Uniform annotation background confirmed**, then **Apply treatment** |
| Cover explicitly | Mark the area, choose **plate** and **Opaque fill color**, then **Apply treatment**; this is opaque coverage of the selected mask area |

The footer command replaces the current crop with a full-width rectangle ending at that row. Use normal crop tools when you need a different shape or width.

In **Source → Old scale detection and mask tools**, **Mask layer** selects `line`, `text`, or `background`. Their overlays are blue, pink, and yellow. Use **Rectangle**, **Polygon**, **Brush**, or **Eraser** in the edit view; **Expand 1 px**, **Shrink 1 px**, and **Clear layer** affect the selected layer. Treatment uses the resulting masks across layers. Check both the old line and its text.

The toolbar's **Masks** checkbox controls overlay visibility, not whether treatment is applied. After changing masks used for `solid` treatment, review the area and confirm the uniform background again before reapplying. Calibration endpoints and treatment masks are separate.

The new bar's **Background plate** is a style setting; it does not automatically identify or remove an old annotation. Neither a plate nor a solid fill restores specimen detail hidden under burned-in text. There is no inpainting or generative filling.

<a id="linked-inset"></a>
## 7. Add a linked inset

An inset is a magnified digital crop of the current source, not a separate observation.

1. In **Crop → Linked inset · digital crop of this source**, choose **Circular (square source ROI)** if needed, then click **Draw source ROI** and drag the source region in the edit view.
2. Check **Show linked inset**. Review **ROI x / y**, **ROI width / height**, **Panel x / y (output)**, and **Panel width (output px)**, then click **Apply inset**.
3. Click **Move / resize panel** to move the panel in the edit view or drag its lower-right corner to resize it. **Edit source ROI** changes the sampled source region instead.
4. Click **Inset scale style…** to enable and style the inset's own scale bar, then **Apply** in that dialog. Review the result and export checks.

ROI coordinates refer to source pixels; panel coordinates and width refer to output pixels. A circular inset requires a square source ROI. Moving or resizing the panel does not change which source region it samples.

The inset uses the original plus recorded treatment layers, excluding the main image's newly drawn bar and labels. It shares the source calibration but calculates its bar width from its own enlargement. Example: an 80 px source ROI shown at 320 px gives a 100 px bar for `5 nm` at `0.2 nm/px`.

**Export inset…** exports it separately using the format currently selected in **Export**.

<a id="measure-and-review"></a>
## 8. Measure and review

Choose **Measure**, **Measure horizontal**, or **Measure vertical** in the toolbar and drag a segment in the edit view. Measurements use source coordinates. If the required physical spacing is unknown, the result is reported in pixels. Use **Clear measurements** to remove them.

**Protect polygon** marks an important specimen region. Click vertices and close the polygon. Export checks can flag overlaps with crops, treatment masks, bars, or insets. Use **Clear protected regions** to remove these markers.

Hold **B** with the canvas focused to show the original under the same crop, output scale, and display window. Release it to return. **Show changes** compares against that same baseline; changing output sampling alone is not shown as an edit. These checks do not certify scientific correctness or prove every old annotation has been found.

Display contrast is controlled under **Source → Display mapping → Low / high → Apply display window**. This affects presentation mapping, not the original source values. Measurement/protection guides are excluded from exports unless **Export → Include measurement / protected guides** is enabled and applied.

<a id="export"></a>
## 9. Export a figure or scientific data

### 9.1 Set size, check, and save

1. Open **Export**. Under **Resolution**, click **2×** or **4×** for a larger image, or **1×** for native sampling. These buttons immediately scale the image, scale-bar font/thickness/margins, and inset layout together. For a specific size, choose **Mode**: `native` uses **Native uniform factor**; `width` uses **Custom width (px)** with proportional height; `print` uses **Panel width (mm)**, **DPI**, and **Print font / bar (pt)**.
2. Set **Panel label** and its position if wanted. Click **Apply output layout**.
3. Inspect **Output pixel preview**, optionally using **View output at 1:1 pixels**.
4. Click **Export check / locate**. Click issues with a location to inspect them. Resolve errors before presentation export; warnings are advisory and require your judgment.
5. Keep the default **Format → Same as source (original bit depth)** to retain the input file type and sample precision with the new scale bar. Click **Export…**, select the destination, and wait for the **Exported:** message.

Changing output size recalculates the bar from physical calibration. The 2×/4× buttons rescale the existing annotation layout; entering a factor or width manually keeps pixel-based style settings fixed, so review text and margins afterward. The initial sampling is 1×. A 2048 × 2048 image becomes 4096 × 4096 at 2× or 8192 × 8192 at 4×; this interpolates existing samples and does not create additional specimen detail. Export size is independent of screen zoom. Independent horizontal/vertical stretching is unavailable.

### 9.2 Choose the appropriate format

| **Format** option | Result |
|---|---|
| **Same as source (original bit depth)** — default | Annotated TIFF, PNG, or JPEG matching the source file type, dtype/bit depth, and channel count; supports uint16 PNG/TIFF and float32 TIFF |
| **PNG presentation** | 8-bit RGBA figure with the recorded display mapping and annotations; transparency supported |
| **TIFF presentation + data** | 8-bit presentation TIFF plus a separate original-dtype `_data.tif` and validity mask |
| **TIFF data only** | Source-dtype crop without burned-in treatment or new annotations; exact source values at native 1× with quarter-turn rotation only |
| **SVG editable annotations** | Embedded raster image plus separately editable bar, tick, label, and inset objects; the microscopy pixels remain raster |

**Same as source** renders directly from source samples. At native 1× with quarter turns, TIFF/PNG values outside annotations and treatment remain exact. Enlarging or rotating by a custom angle interpolates at the original dtype. The display window maps annotation colors into source values; it is not baked into specimen pixels. External viewers may display scientific TIFF contrast differently. Grayscale inputs stay grayscale, so colored annotations become gray. RGBA inputs retain alpha; inputs without alpha use white outside an irregular crop when `transparent` is selected. Choose **PNG presentation** when you need an 8-bit color/transparent figure matching the display mapping. TIFF uses lossless Deflate; PNG is lossless; JPEG is re-encoded at quality 98 and remains lossy. Original vendor metadata and compression settings are not copied wholesale.

Every export has a JSON sidecar recording calibration, source hash, display window, transform, and recipe. Source-format figures and data TIFFs also write a `_valid-mask.png`. For data TIFFs, pixels outside an irregular crop remain in the bounding rectangle, and the mask identifies the valid region. Keep these companion files with the data. Annotated outputs contain deliberately changed pixels; use **TIFF data only** for source values without treatment or new annotations.

At non-native output sizes or custom rotation angles, data TIFFs are resampled and that fact is recorded. Use `native` with factor `1` and a multiple of 90° for exact source-value crops. **TIFF data only** does not burn a visible scale bar into the data and bypasses presentation-annotation checks. If you want a visible bar, use a presentation format.

**Copy finished image** copies the rendered presentation at output resolution, regardless of view zoom. It applies presentation export checks. Input images cannot be overwritten; existing output names receive numbered suffixes. Unicode and space-containing paths are supported.

### 9.3 Export without calibration

You can crop and export an uncalibrated image. Disable **Draw a physical scale bar** in the main style and in any enabled inset style, apply those changes, then run the export check. A guessed scale must not be presented as a confirmed physical length.

<a id="projects-recovery-and-replay"></a>
## 10. Save projects and recover work

**Save project…** stores calibration evidence, assumptions, crop, masks, inset, measurements, styles, display mapping, and output settings. **Open project…** restores them. Project JSON files reference the original images rather than embedding their pixels. Associated `.npz` mask files sit beside the project; retain those too.

Keep source/reference images available when moving a project. **File → Relink source…** accepts the same source content at a new location; a mismatched hash is rejected. A different image needs its own project and calibration. Exported PNG/TIFF/SVG files contain their own image content, while their recipes still refer to the original sources.

**Undo / Redo** restores parameter changes without duplicating the source arrays. After a short idle interval, the app writes recovery projects and `.bak` backups to `%LOCALAPPDATA%\MicroScaleEditor\recovery`. Click **Recover autosave…** to open a recovery file or backup. Manual saves also keep a backup.

Portable EXE logs are under `%LOCALAPPDATA%\MicroScaleEditor\logs\microscale.log`. Source-run logs normally use the repository's `logs/microscale.log`.

For source users, a saved recipe can be replayed in a separate process:

```powershell
.\.venv\Scripts\python.exe -m microscale --recipe examples\SYNTHETIC_demo.micro.json --output replay.png --format png
```

Omitting `--format` now selects `source`; an explicit `--format png` produces the 8-bit presentation. See [Windows packaging](../PACKAGING.md) for EXE command-line usage and diagnostics.

<a id="shortcuts"></a>
## 11. Keyboard and mouse shortcuts

| Action | Shortcut or gesture |
|---|---|
| Open images / open project | Ctrl+O / Ctrl+Shift+O |
| Save project / save as | Ctrl+S / Ctrl+Shift+S |
| Export / copy finished image | Ctrl+E / Ctrl+Shift+C |
| Undo / redo | Ctrl+Z / Ctrl+Y |
| Zoom / pan | Mouse wheel / middle-drag, or **Pan** |
| Fit / 100% | F / 1 with the canvas focused |
| Compare original | Hold B with the canvas focused |
| Place calibration endpoints | **Pick endpoints**, then press-drag-release; hold Shift for a horizontal line, including endpoint adjustments |
| Move bar group | **Drag group**, then drag; arrows = 1 output px, Shift+arrows = 10 |
| Edit new bar length | Double-click its group in the edit view |
| Finish polygon / cancel current drawing | Enter or right-click / Esc |
| Edit polygon vertices | Drag; Ctrl+click inserts; Delete removes the selected vertex |
| Reference correspondence point | Ctrl+click each matching location in the reference dialog |

Canvas shortcuts require canvas focus; they do not apply while typing in a form field. Use the edit view for drawing and moving objects.

<a id="troubleshooting"></a>
## 12. Troubleshooting

| Symptom | What to check |
|---|---|
| Pale labels on white side panels in Windows light mode | Close the older instance and launch v0.2.5 or later. The editor now uses its own complete dark palette; changing Windows to dark mode is unnecessary. |
| No new bar appears | Read the live message above the scale controls and use **Review calibration**; confirm spacing for the rotated horizontal direction; check **Draw a physical scale bar**; click **Apply style / length**; use a contrasting color and inspect export issues |
| Calibration is still **Pending** | Click **Use endpoints** or **Use manual calibration**, review evidence, then **Confirm calibration**; resolve a reported evidence conflict if needed |
| “An oblique segment…” error | Hold Shift while drawing or adjusting calibration endpoints, or enter equal y values for a horizontal reference; use square pixels only when justified |
| Known length or a style field resets | Finish endpoint dragging or choosing a preset first, then enter values and click the corresponding **Use / Apply** button before another operation |
| Scale label/bar/plate is outside the valid crop | Move the whole group inward, reduce its physical length or font/plate size, or change the crop; inspect irregular-crop boundaries |
| The bar looks too long or too short | Check `nm` versus `μm`, the measured endpoint span, **Known length** versus **Physical length**, and the output factor |
| The old bar remains | A new bar does not erase existing pixels. Review the old-annotation treatment and include both its line and text |
| Dragging seems ineffective | Switch from **Output pixel preview** to **Edit • source coordinates**, choose the intended tool, and apply pending form values |
| A float/16-bit TIFF looks dark or low contrast | Review **Source → Display mapping**. Use data TIFF export to preserve the original values rather than relying on the 8-bit preview |
| `COMPRESSION.LZW` requires `imagecodecs` | Close the old application and run the current EXE (v0.2.5). For a source install, update runtime requirements with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| Reference transfer is disabled or rejected | Verify actual matching content and registration; review point pairs/overlap. Unsupported distortion or a different field of view cannot be fixed by matching filenames |
| An exported TIFF has no visible bar | **TIFF data only** intentionally excludes annotations. Choose the default **Same as source (original bit depth)** for a source-precision TIFF with a bar, or another presentation format |
| Opening many files uses too much memory | Work in smaller groups; all imported sources retain full-resolution arrays. There is no batch export queue |
| Window seems to use the old startup position | Check the version in the title bar, close the old instance, then launch v0.2.5. Centering happens on initial show, not after every manual move |

<a id="scope-and-help"></a>
## 13. Supported scope and further help

- Real-space lengths accept `nm`, `μm`, `µm`, `um`, and `Å`. Reciprocal/FFT units are not supported.
- Supported inputs are PNG, JPEG, and single-page TIFF. DM3/DM4, PDF, multipage TIFF workflows, and general vendor metadata interpretation are outside this version.
- Multiple-image import is supported; batch export is not.
- Reference registration supports translation and uniform scaling. Significant rotation, reflection, anisotropic scaling, distortion, insufficient texture, and different fields of view are rejected.
- Processing uses full-resolution memory. The 150 MP output cap is not a guarantee that every composition fits available RAM.
- Fonts depend on the host system. Exact text reproduction requires the same font environment.
- OCR, detected endpoints, metadata, and calibration transfer require review. Successful file import does not establish calibration accuracy.

For a bug report, include the application version, steps to reproduce, relevant log excerpts, and a shareable example. Review files before publishing them: projects, sidecars, and logs can contain local paths and image identifiers.

[Project introduction](../README.md) · [Validation scope](../VALIDATION.md) · [Build and packaging](../PACKAGING.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
