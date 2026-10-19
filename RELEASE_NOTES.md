# MicroScale Editor v0.2.4

Fix unreadable side panels when Windows uses light mode.

## Interface fix

- The source-image list and all four property panels now use the same dark palette as the editor canvas.
- Menus, tabs, buttons, text fields, spin boxes, combo-box popups, progress indicators, tooltips, and Qt dialogs use consistent foreground/background colors.
- Active, inactive, selected, placeholder, and disabled text have explicit palette colors. The UI no longer combines pale labels with system-white panel backgrounds.
- The application selects Qt's Fusion widget style and requests a dark color scheme locally. Windows personalization settings are not changed. Native Windows file pickers and window decorations are still managed by Windows.
- Image data, physical calibration, scale-bar styling, and export defaults are unchanged. English and Simplified Chinese manuals are updated.

## 中文说明

修复 Windows 亮色模式下左侧图像列表、右侧属性栏出现白底浅色文字的问题。应用内控件统一使用深色配色，无需更改 Windows 系统主题。保存当前工作并关闭旧版本，再启动 v0.2.4 即可；本次更新不改变图像、校准值、比例尺颜色或导出结果。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)
- [Validation scope](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/VALIDATION.md)

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no separate Python installation required.
- **MicroScaleEditor-v0.2.4-Windows-x64.zip** — application, bilingual manuals, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — checksums for the downloads.

Save work before closing an older copy, then run the new EXE and check **v0.2.4** in its title bar. The application is unsigned and has no automatic updater.
