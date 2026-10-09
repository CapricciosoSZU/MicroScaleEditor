# MicroScale Editor v0.1.1

Fixes LZW-compressed TIFF loading and centers the editor on startup.

## Updated manuals / 更新后的使用手册

The user manual was rewritten in English and Simplified Chinese on **2026-10-09**, with step-by-step calibration and scale-bar instructions, matching English button names, export guidance, and troubleshooting.

使用手册已于 **2026-10-09** 重写为英文和简体中文，提供校准、绘制比例尺、导出和常见问题的操作步骤。中文保留英文按钮名称，便于对照软件界面。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册（zh-CN）](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)

This is a documentation update for v0.1.1. The EXE and original application ZIP are unchanged; that ZIP contains the earlier English guide. Use the links above for the revised manuals.

本次为 v0.1.1 的文档更新，EXE 和原应用 ZIP 未替换；原 ZIP 内仍是早期英文指南，请通过以上链接阅读新版双语手册。

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
