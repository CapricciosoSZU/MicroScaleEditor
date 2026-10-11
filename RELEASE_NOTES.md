# MicroScale Editor v0.2.1

Adds a Velox-style scale bar, matching the supplied Thermo Fisher Velox reference appearance.

## Scale-bar appearance

- **Velox-style** is the default for newly opened images and new inset styles: white fill, black outlines, regular Arial lettering above the bar, left alignment, and bottom-left placement.
- Existing saved projects and templates keep their previous appearance. Apply **Scale bar → Preset → Velox-style → Use preset** to use the new style in an existing project.
- Added **Outline bar and text**, **Outline color**, **Outline width (px)**, and **Text alignment** controls. The plain White/Black presets disable outlines.
- The black border is drawn inside the calibrated bar span. Its full outer width represents the physical length; the inner white portion is shorter. Text outline bounds are included in crop/export checks.
- Outlines work in the preview, clipboard, PNG, native-precision TIFF/PNG/JPEG, linked insets, and SVG. SVG labels remain editable text with a stroke.
- 2×/4× output scales outline width with the layout; print mode scales it with bar thickness. Appearance changes preserve calibration and physical length.
- Original-format/bit-depth export remains the default. New images still require reviewed calibration before drawing a physical scale bar.

## Manuals / 使用手册

Both manuals document the preset, default behavior, outline controls, and the correct bar measurement boundary. Public illustrations are synthetic; the supplied reference image remains private.

新图像默认使用 **Velox-style**：白色文字和条形、黑色描边、文字在上方左对齐、整组位于左下角。已有项目请通过 **Scale bar → Preset → Velox-style → Use preset** 应用。校准长度对应条形完整外边缘跨度，不能只量中间白色部分。英文和简体中文手册均已更新。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)
- [Validation scope](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/VALIDATION.md)

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no separate Python installation required.
- **MicroScaleEditor-v0.2.1-Windows-x64.zip** — application, bilingual manuals, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — checksums for the downloads.

Save work before closing an older copy, then run the new EXE and check **v0.2.1** in its title bar. Open projects/templates containing the new outline fields in v0.2.1 or later. The application is unsigned and has no automatic updater.
