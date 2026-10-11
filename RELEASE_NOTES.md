# MicroScale Editor v0.2.3

Hold Shift to draw a horizontal calibration line.

## Endpoint interaction

- In **Source → Pick endpoints**, hold **Shift** while dragging to keep both endpoints at the same source-image y coordinate. Keep Shift held until mouse release.
- Shift also works when moving either existing endpoint; the opposite endpoint stays fixed.
- Press or release Shift during a drag to switch between horizontal and free placement immediately. The final mouse-release position is used even when no move event arrives.
- The constraint is independent of view zoom. It neither assumes square pixels nor confirms calibration automatically: enter **Known length**, then **Use endpoints → Confirm calibration**.
- The Source panel and oblique-segment warning now explain the shortcut. English and Simplified Chinese manuals are updated.
- Scale-bar labels remain above the bar. Velox-style and original-format/bit-depth export remain the defaults.

## 使用方法

在 **Source → Pick endpoints** 中，按住 **Shift** 拖动画线，直到松开鼠标，两个端点会保持同一高度。微调已有任一端点时同样有效，对面的端点保持不动。拖动过程中松开 Shift 可恢复自由放置。之后填写 **Known length**，点击 **Use endpoints → Confirm calibration**；软件不会自动假设正方形像素或自动确认校准。

- [English manual](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.md)
- [简体中文手册](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/docs/USER_GUIDE.zh-CN.md)
- [Validation scope](https://github.com/CapricciosoSZU/MicroScaleEditor/blob/codex/initial-release/VALIDATION.md)

## Downloads

- **MicroScaleEditor.exe** — portable Windows x64 application; no separate Python installation required.
- **MicroScaleEditor-v0.2.3-Windows-x64.zip** — application, bilingual manuals, synthetic examples, and third-party notices.
- **SHA256SUMS.txt** — checksums for the downloads.

Save work before closing an older copy, then run the new EXE and check **v0.2.3** in its title bar. The application is unsigned and has no automatic updater.
