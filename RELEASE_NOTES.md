# MicroScale Editor v0.2.2

Scale-bar labels now always appear above the bar, as requested.

## Fixed label placement

- **Label position: Always above the bar** replaces the above/below selector.
- The same placement applies to main images, linked insets, all presets, previews, clipboard, raster exports, and editable SVG.
- Existing projects and style templates with `text_position: below` load with the label above. Other appearance settings, physical length, and calibration are preserved. Original project/template files are unchanged until saved.
- Velox-style remains the default for new images. Original-format and bit-depth export remain the default.

## Manuals / 使用手册

Both manuals now describe the fixed label placement and legacy-project behavior.

比例尺文字统一固定在条形上方，适用于主图、放大图、所有预设、预览、剪贴板及导出。界面显示 **Label position: Always above the bar**，不再提供上下位置选择。旧版项目和模板中的 `below` 设置在载入后转为 `above`，其他外观参数、物理长度和校准保持原值。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)
- [Validation scope](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/VALIDATION.md)

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no separate Python installation required.
- **MicroScaleEditor-v0.2.2-Windows-x64.zip** — application, bilingual manuals, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — checksums for the downloads.

Save work before closing an older copy, then run the new EXE and check **v0.2.2** in its title bar. The application is unsigned and has no automatic updater.
