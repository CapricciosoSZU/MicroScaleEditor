# MicroScale Editor v0.2.5

Draw a crop, then drag it immediately to choose the region you want.

## Crop interaction

- Completing any crop shape automatically selects **Edit crop**. Drag inside the selection to move it without switching tools.
- Rectangle edges and corner handles resize the selection. Circle/ellipse handles and polygon/freehand vertices remain editable. Pointer shapes indicate move and resize actions.
- Fixed aspect ratios are retained, and movement stays within the source image. Crop edits preserve confirmed calibration, source coordinates, undo/redo, and saved project geometry.
- Click **Draw crop** to replace the selection. Press **Esc** during a gesture to cancel it. Fast drags use the final release position.
- The English and Simplified Chinese manuals explain the updated workflow.

## Included interface fix

This build also includes the v0.2.4 dark-palette fix: image lists, property panels, menus, inputs, and Qt dialogs remain readable when Windows uses light mode. Windows personalization is unchanged; native file pickers and window decorations remain managed by Windows.

## 中文说明

画完裁剪框后会自动进入调整状态：拖动框内移动选区，拖动边缘或控制点调整大小，无需手动切换工具。需要重新画框时点击 **Draw crop**；拖动中按 **Esc** 取消，完成后可用 **Undo / Redo** 撤销或恢复。固定比例和已确认的校准保持不变。

本版同时包含 Windows 亮色模式下侧栏配色的修复，并更新中英文手册。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)
- [Validation scope](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/VALIDATION.md)

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no separate Python installation required.
- **MicroScaleEditor-v0.2.5-Windows-x64.zip** — application, bilingual manuals, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — checksums for the downloads.

Save work before closing an older copy, then run the new EXE and check **v0.2.5** in its title bar. The application is unsigned and has no automatic updater.
