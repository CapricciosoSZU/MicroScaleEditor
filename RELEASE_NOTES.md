# MicroScale Editor v0.2.0

Adds source-format export as the default, higher-resolution output controls, image rotation, and clearer feedback when calibration prevents a scale bar from appearing.

## Original format and higher-resolution output

- **Same as source (original bit depth)** is the default in the application and recipe replay. Exports retain TIFF/PNG/JPEG file type, dtype/bit depth, and channel count with the new scale bar.
- 16-bit PNG/TIFF and float32 TIFF are rendered from source samples, including native-precision insets. The specimen is not reduced to the 8-bit preview. Annotation colors are mapped through the recorded display range.
- **Export → Resolution → 1× / 2× / 4×** scales the image and scale-bar/inset layout together. Physical calibration and scale-bar length remain unchanged. Initial sampling is 1×; larger output interpolates existing pixels and does not create new microscope detail.
- Grayscale stays grayscale; RGBA retains alpha. Inputs without alpha use white outside a transparent crop. TIFF/PNG are lossless; JPEG is re-encoded at quality 98. Original vendor metadata/compression are not copied wholesale.
- Source-format figures include JSON recipes and validity masks. Existing PNG presentation, TIFF presentation/data, and editable SVG options remain available.

## Image rotation

- Open **Crop → Image rotation** for left/right 90° turns, 180°, reset, or a custom **Angle (° clockwise)**.
- Rotation applies to the cropped output, expanding the canvas to keep the crop visible. **Output pixel preview** opens automatically; source-coordinate editing retains the original orientation.
- New scale bars and labels stay horizontal. Anchored bars move into the valid rotated region when they fit. Inset content follows the rotation and keeps its own horizontal bar.
- Native 1× quarter turns preserve source sample values and dtype exactly. Custom angles interpolate pixels; exports record the angle, interpolation, transform, and validity mask.
- Quarter turns exchange calibration axes where appropriate. Custom-angle physical bars require confirmed equal x/y spacing. Missing spacing is never guessed.
- Rotation is retained in projects, undo/redo, PNG/TIFF/SVG exports, and the clipboard. Original arrays and source files remain unchanged.

## Scale-bar feedback

- The Scale bar tab now displays a live explanation when calibration hides the bar, with a **Review calibration** button.
- Calibration confirmation exits the endpoint tool to prevent accidental endpoint changes.
- Changed endpoints must be applied using **Use endpoints** before reconfirmation. Dragging preserves the draft known length.
- Cropping retains confirmed calibration; regression checks cover both canvas cropping and numeric crop changes.
- A stale confirmation message is replaced when the current calibration becomes pending.

## Manuals / 使用手册

The portable ZIP includes English and Simplified Chinese manuals, updated for source-format export, higher-resolution controls, rotation, and calibration feedback. The application interface remains English.

便携 ZIP 包含更新后的英文和简体中文手册，软件界面保持英文。默认 **Same as source (original bit depth)** 保留源文件格式和位深并加入新比例尺；**Export → Resolution → 2× / 4×** 同步放大图像与标注布局。旋转操作位于 **Crop → Image rotation**；任意角度可填写 **Angle (° clockwise)** 后点击 **Apply rotation**。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)
- [Validation scope](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/VALIDATION.md)

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no separate Python installation required.
- **MicroScaleEditor-v0.2.0-Windows-x64.zip** — application, bilingual manuals, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — checksums for the downloads.

Save work in any older running copy before closing it. Launch the new EXE and check **v0.2.0** in its title bar. The application is unsigned and has no automatic updater. Private microscopy inputs and filenames are not distributed.
