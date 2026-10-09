# User guide

Original arrays remain read-only. Edits are recorded as parameters and masks. Specimen calibration is reviewed separately from display and layout.

## Three input workflows

### Clean source

Open the image. Source shows dimensions and bit depth. OME-TIFF PhysicalSizeX/Y and MicroScale sample-space fields become **Pending** evidence; inspect them, then **Confirm calibration**.

For manual calibration, enter horizontal spacing s_x, optional vertical spacing s_y, and nm/px or μm/px. Choose **Use manual calibration**. A known horizontal axis does not establish the vertical axis: explicitly select **Assume square pixels** if justified.

For a known feature length, enter its physical length, choose **Pick endpoints**, and place/drag the two endpoints. **Use endpoints**, review, then confirm. Uncalibrated cropping/export is allowed with physical bars disabled.

### Source with an existing scale bar

Expand **Source → Old scale detection and mask tools**, then **Detect + OCR**. Select a candidate and **Use candidate**. Inspect the endpoints, number, and unit at useful zoom. Correct errors manually; missing OCR and ambiguous candidates do not prevent endpoint calibration.

Use endpoints and confirm calibration. Choose an old-annotation treatment before adding a new bar.

### Clean source plus reference

Open the clean source, then **Set calibration reference**. Automatic matching uses SIFT, RANSAC, spatial coverage, and overlapping-patch correlation. Sampling is inferred from content, never merely from file dimensions.

Review registered overlap or flicker. Same sampling, appended footers, crop offsets, and uniform resizing are supported. If automatic matching fails, **Ctrl+click at least three distributed, noncollinear pairs** in the same order across the images and validate. Manual points still need content verification.

Use reference OCR, manual nm/px, or a length and endpoints. **Transfer calibration as pending**, then confirm in the main editor. Unreliable pairing blocks transfer. Registration never resamples the source.

## Cropping and navigation

- Shapes: rectangle, square, circle, ellipse, polygon, freehand. W:H means width:height. Fixed ratios alter the ROI rather than stretching the specimen.
- **Draw crop** creates a region; **Edit crop** moves its interior or resizes its corners.
- Polygon: click vertices; Enter or right-click closes. Drag to edit, Ctrl+click to insert, Delete to remove a selected vertex.
- Freehand: drag and release to close; correct self-intersections.
- Nonrectangular output uses the ROI bounding box. Outside pixels can be transparent, white, black, or a custom color. The checkerboard is not exported.
- Scroll to zoom; middle-drag or Pan to move. Fit/100%, F/1 are available. Output 100% accounts for monitor scaling.

Crops use source coordinates. Canvas shortcuts do not fire while editing text fields.

## Scale-bar styling

Confirm calibration, enable the bar, enter a length such as **5 nm**, then **Apply style / length**. At 0.2 nm/px, this is 25 native pixels and 50 pixels at 2× output. Editable suggestions follow a 1/2/5 sequence.

White, black, and white-plate presets are available. Adjust thickness, color, ticks, font, bold, label position, spacing, and plate. Choose a nine-grid anchor or custom placement.

**Move scale** drags the group. Arrows move 1 output pixel; Shift+arrow moves 10. Double-click the label area to edit physical length. Group x/y are output coordinates; moving the bar does not change its length.

Save style templates independently. **Copy settings** copies chosen styles/output settings; calibration is excluded by default. Explicitly copied calibration becomes Pending for review on the new source.

## Existing annotations and masks

Line/text/background masks are independent blue/pink/yellow layers. Use rectangles, polygons, brush, eraser, or one-source-pixel expansion/contraction. **Detect region** limits detection to an area. **Ignore false candidate** records rejected detections.

Calibration endpoints are separate from treatment masks. Solid bars use outer edges [x, x + width); end-tick bars use tick centerlines. Review antialiased edges at local 50% contrast. Automatic candidates assume solid bars; end caps need manual review. Never calibrate from combined text, plate, and line width.

Available treatments:

1. Use a clean source when available.
2. **Crop off selected footer**, specifying the first footer row.
3. **solid**, only for a confirmed uniform annotation region.
4. Keep, crop, or cover burned-in annotations with an opaque **plate**.

Only selected masks change. Covering specimen pixels cannot restore hidden information. No inpainting or generative fill is provided.

## Linked inset

Under **Crop → Linked inset**, **Draw source ROI** selects the source region. ROI x/y/width/height are source coordinates; panel x/y/width are final output pixels.

**Move inset** moves the panel. Drag the lower-right corner to resize. Neither operation alters the source ROI. A circular inset requires a square ROI.

The inset uses the original plus recorded treatment layers, excluding the main image's new bars/text/borders. Its scale derives independently from its panel size. An 80 px ROI displayed at 320 px gives a 100 px bar for 5 nm at 0.2 nm/px. An inset is a digital crop, not a separate observation.

## Measure and review

**Measure**, **Measure horizontal**, and **Measure vertical** use source coordinates. Unknown physical directions report pixels. **Protect polygon** marks key areas; checks and dashed overlays show crop/treatment/annotation overlap. Helper layers stay out of exports unless enabled.

Hold **B** with canvas focus to show the original under the identical crop, scale, and display window. Release to return. **Show changes** uses the same baseline; resampling alone is not reported as an extra edit. Reference overlap/flicker is a separate registration view.

## Export

Use native 1×, a uniform factor, a target width, or print dimensions. Print mode converts mm/DPI to pixels and typography points. Height follows aspect ratio; independent axis resampling is unavailable.

**Export check** reviews calibration, physical lengths, text/plate/panel boundaries, nonrectangular boundaries, short bars/small text, protection, known old annotations, and output metadata. Select an item to locate it. Errors block final export; warnings can be addressed or accepted. Detection cannot guarantee every old annotation is found.

PNG uses recorded window mapping to 8-bit RGBA. Presentation TIFF includes separate source-dtype data. Data TIFF never burns treatment or annotations into values; native 1× crops are exact. Resampling is recorded. Nonrectangular data retains bounding-box values plus a separate validity mask.

SVG embeds the raster image and independent editable bars, ticks, labels, and inset objects. JSON sidecars record calibration, hashes, transform, display window, and recipe. Output sample-space TIFF fields are updated for sampling. DPI/PPI and nominal magnification never imply nm/px.

**Copy finished image** uses output resolution regardless of view zoom. Inputs cannot be overwritten; other collisions receive numbered suffixes. Unicode and space-containing paths are supported.

## Projects, recovery, and replay

Project JSON records versions, source/reference paths and hashes, calibration evidence, assumptions, crops, inset, masks, protection, measurements, styles, display mapping, and output settings. Content-addressed .npz mask files sit beside the project. Undo/redo stores parameters rather than copying original arrays.

After a short idle interval, atomic autosaves and .bak files go to **%LOCALAPPDATA%\MicroScaleEditor\recovery**. **Recover autosave** opens either. Manual project saves also retain a valid backup.

Projects reference source images rather than embedding them. Keep images when moving a project, or **Relink source**. Hash mismatches are rejected; another image needs a new project/calibration. Exported PNG/TIFF/SVG contain their own display content.

```powershell
.\launch.ps1 -Debug -Examples
.\.venv\Scripts\python.exe -m microscale --recipe examples\SYNTHETIC_demo.micro.json --output replay.png --format png
```

Source logs are in logs/microscale.log. VS Code launch configurations are included. See [PACKAGING.md](../PACKAGING.md) for EXE paths and diagnostics.
