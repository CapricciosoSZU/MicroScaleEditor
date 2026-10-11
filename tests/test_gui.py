"""Runs real Qt widgets, mouse/keyboard events, workers, clipboard and files."""
from copy import deepcopy
import time
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QPointF, Qt, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from microscale.gui import MainWindow, ReferenceDialog
from microscale.image_io import read_source, qimage_to_array
from microscale.model import load_project
from microscale.rendering import compose, render_image


def wait_until(predicate, timeout=45000):
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        QApplication.processEvents()
        # Let Python worker threads run: QTest.qWait may retain the GIL on Windows.
        time.sleep(.01)
        if time.monotonic() > deadline:
            raise AssertionError("GUI condition timed out")


def settled(window):
    wait_until(lambda: not window.jobs and not window.render_busy and not window.render_timer.isActive())


@pytest.fixture
def window(qapp, tmp_path):
    widget = MainWindow()
    widget.settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    widget.recovery_dir = tmp_path / "recovery"
    widget.show()
    QTest.qWait(100)
    yield widget
    settled(widget)
    widget.close()
    QApplication.processEvents()


def drag(canvas, start, end):
    a, b = canvas.mapFromScene(QPointF(*start)), canvas.mapFromScene(QPointF(*end))
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=a)
    for step in range(1, 6):
        point = a + (b - a) * (step / 5)
        QTest.mouseMove(canvas.viewport(), point, delay=15)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=b)


def click(canvas, point, modifier=Qt.KeyboardModifier.NoModifier):
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, modifier, canvas.mapFromScene(QPointF(*point)))


def open_clean(window, examples):
    window.load_image(examples / "SYNTHETIC_clean.png")
    wait_until(lambda: window.document is not None)
    settled(window)
    assert window.composition is not None


def test_startup_centered_and_manual_position_preserved(window):
    QApplication.processEvents()
    available = window.screen().availableGeometry()
    frame = window.frameGeometry()
    assert available.contains(frame)
    assert (frame.center() - available.center()).manhattanLength() <= 2
    window.move(window.pos().x() + 12, window.pos().y() + 9)
    QApplication.processEvents()
    moved = window.pos()
    window.hide()
    window.show()
    QApplication.processEvents()
    assert window.pos() == moved


def test_multi_select_import_keeps_each_source_state(window, examples, tmp_path, monkeypatch):
    import tifffile
    compressed = tmp_path / "batch LZW.tif"
    tifffile.imwrite(compressed, np.arange(64 * 80, dtype=np.uint16).reshape(64, 80), compression="lzw")
    paths = [str(examples / "SYNTHETIC_clean.png"), str(examples / "SYNTHETIC_16bit_OME.tif"), str(compressed)]
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args, **kwargs: (paths, "Images"))
    window.open_images()
    settled(window)
    assert window.image_list.count() == 3
    assert {doc.source.path for doc in window.documents} == {str(Path(p).resolve()) for p in paths}
    for index, doc in enumerate(window.documents):
        window.image_list.setCurrentRow(index)
        settled(window)
        assert window.document is doc
        expected = "Pending" if doc.source.path.endswith("SYNTHETIC_16bit_OME.tif") else "Uncalibrated"
        assert doc.project.calibration.status == expected
        assert not doc.source.pixels.flags.writeable


def calibrate_manual(window):
    window.sx.setText("0.2")
    window.square.setChecked(True)
    window.manual_calibration()
    window.confirm_calibration()
    settled(window)


def test_gui_workflow_a_mouse_crops_history_measure_and_protect(window, examples, tmp_path):
    open_clean(window, examples)
    assert window.document.project.calibration.status == "Uncalibrated"
    calibrate_manual(window)
    window.crop_kind.setCurrentText("rectangle")
    window.ratio.setCurrentText("4:3")
    window.draw_crop()
    drag(window.canvas, [100, 100], [700, 500])
    settled(window)
    rect = window.document.project.crop.rect
    assert rect[2] / rect[3] == pytest.approx(4 / 3, abs=.01)
    window.tool.setCurrentText("Edit crop")
    old = deepcopy(window.document.project.crop.rect)
    drag(window.canvas, [350, 300], [390, 340])
    settled(window)
    assert window.document.project.crop.rect[0] == pytest.approx(old[0] + 40, abs=3)
    window.canvas.setFocus()
    window.undo(-1)
    settled(window)
    assert window.document.project.crop.rect == old
    window.undo(1)
    settled(window)
    for shape in ("square", "circle", "ellipse"):
        window.crop_kind.setCurrentText(shape)
        window.ratio.setCurrentText("Free")
        window.draw_crop()
        drag(window.canvas, [150, 150], [700, 550])
        settled(window)
        p = window.document.project
        assert p.crop.kind == shape
        if shape in ("square", "circle"):
            assert p.crop.rect[2] == pytest.approx(p.crop.rect[3])
    window.crop_kind.setCurrentText("polygon")
    window.draw_crop()
    for point in ([100, 100], [700, 130], [650, 700], [120, 630]):
        click(window.canvas, point)
    QTest.keyClick(window.canvas, Qt.Key.Key_Return)
    settled(window)
    assert len(window.document.project.crop.points) == 4
    window.tool.setCurrentText("Edit crop")
    drag(window.canvas, [100, 100], [150, 160])
    settled(window)
    assert window.document.project.crop.points[0] == pytest.approx([150, 160], abs=3)
    click(window.canvas, [400, 150], Qt.KeyboardModifier.ControlModifier)
    settled(window)
    assert len(window.document.project.crop.points) == 5
    QTest.keyClick(window.canvas, Qt.Key.Key_Delete)
    settled(window)
    assert len(window.document.project.crop.points) == 4
    window.tool.setCurrentText("Measure horizontal")
    drag(window.canvas, [200, 220], [400, 280])
    settled(window)
    measure = window.document.project.measurements[-1]
    assert measure["points"][0][1] == measure["points"][1][1]
    window.tool.setCurrentText("Protect polygon")
    for point in ([200, 200], [300, 200], [300, 300]):
        click(window.canvas, point)
    QTest.keyClick(window.canvas, Qt.Key.Key_Return)
    settled(window)
    assert window.document.project.protected
    window.save_to(str(tmp_path / "GUI project.json"))
    settled(window)
    saved = load_project(tmp_path / "GUI project.json")
    assert saved.crop == window.document.project.crop
    window.open_project_path(str(tmp_path / "GUI project.json"))
    wait_until(lambda: len(window.documents) == 2)
    settled(window)
    assert window.document.project.protected == saved.protected
    assert window.document.project.measurements == saved.measurements


def test_gui_workflow_b_ocr_masks_endpoints_export(window, examples, tmp_path):
    window.load_image(examples / "SYNTHETIC_50nm_250px.png")
    wait_until(lambda: window.document is not None)
    settled(window)
    window.detect_source()
    settled(window)
    candidates = window.document.project.candidates
    index = next(i for i, c in enumerate(candidates) if c.get("length_nm") == 50 and abs(c["line_rect"][2] - 250) < 3)
    window.candidate_list.setCurrentRow(index)
    window.square.setChecked(True)
    window.use_candidate()
    settled(window)
    assert window.document.project.masks
    assert window.document.project.calibration.status == "Pending"
    window.endpoint_calibration()
    window.confirm_calibration()
    settled(window)
    assert window.document.project.calibration.sx == pytest.approx(.2)
    window.tool.setCurrentText("Mask brush")
    window.canvas.fit()
    drag(window.canvas, [650, 910], [680, 910])
    settled(window)
    assert window.document.project.masks[-1]["kind"] == "brush"
    window.tool.setCurrentText("Mask erase")
    click(window.canvas, [660, 910])
    settled(window)
    assert window.document.project.masks[-1]["erase"]
    window.treatment.setCurrentText("plate")
    window.apply_treatment()
    window.scale_form.enabled.setChecked(True)
    window.scale_form.length.setText("5 nm")
    window.apply_style()
    settled(window)
    assert window.composition.scale_length_px == pytest.approx(25)
    window.start_export(str(tmp_path / "final.png"))
    settled(window)
    assert (tmp_path / "final.png").exists()
    window.clipboard()
    settled(window)
    clipboard = QApplication.clipboard().image()
    assert clipboard.width() == 1024
    np.testing.assert_array_equal(qimage_to_array(clipboard), qimage_to_array(window.result_image))


def test_gui_workflow_c_pairing_overlay_and_inset(window, examples):
    window.load_image(examples / "SYNTHETIC_work_2x.png")
    wait_until(lambda: window.document is not None)
    settled(window)
    ref = read_source(examples / "SYNTHETIC_reference_footer.png")
    dialog = ReferenceDialog(window, ref, window.document)
    dialog.show()
    QTest.qWait(100)
    dialog.auto_register()
    wait_until(lambda: dialog.registration is not None, 30000)
    settled(window)
    assert dialog.registration["r"] == pytest.approx(2, rel=.001)
    assert not dialog.overlap.image_item.pixmap().isNull()
    dialog.reference_sx.setText("0.5")
    dialog.square.setChecked(True)
    dialog.transfer_calibration()
    result = dialog.result_data
    p = window.document.project
    p.reference = result
    p.calibration.propose(result["sx_reference"] / result["r"], result["sx_reference"] / result["r"], "GUI paired synthetic", True, result)
    window.commit()
    window.confirm_calibration()
    settled(window)
    assert p.calibration.sx == pytest.approx(.25, rel=.001)
    window.draw_inset()
    drag(window.canvas, [400, 400], [600, 600])
    settled(window)
    roi = deepcopy(p.inset.roi)
    assert p.inset.enabled
    window.tool.setCurrentText("Move inset")
    window.canvas.fit()
    drag(window.canvas, [100, 100], [170, 170])
    settled(window)
    assert p.inset.roi == roi
    assert p.inset.x > 50
    window.inset_roi_fields[0].setValue(500)
    window.apply_inset()
    settled(window)
    assert p.inset.roi.rect[0] == 500
    assert p.reference["verified"]


def test_view_zoom_before_diff_clipboard_and_scale_drag(window, examples, tmp_path):
    open_clean(window, examples)
    calibrate_manual(window)
    window.scale_form.enabled.setChecked(True)
    window.apply_style()
    settled(window)
    expected = qimage_to_array(window.result_image)
    for factor in (.5, 1., 2.):
        window.canvas.resetTransform()
        window.canvas.scale(factor, factor)
        window.start_export(str(tmp_path / f"zoom-{factor}.png"))
        settled(window)
        np.testing.assert_array_equal(read_source(tmp_path / f"zoom-{factor}.png").pixels, expected)
    window.canvas.fit()
    window.tool.setCurrentText("Move scale")
    before_length = window.composition.scale_length_px
    rect = window.composition.scale_rect
    drag(window.canvas, [rect[0] + 5, rect[1] + 5], [rect[0] - 35, rect[1] - 35])
    settled(window)
    assert window.document.project.style.anchor == "custom"
    assert window.composition.scale_length_px == before_length
    old_x = window.document.project.style.x
    QTest.keyClick(window.canvas, Qt.Key.Key_Left)
    settled(window)
    assert window.document.project.style.x == old_x - 1
    QTest.keyPress(window.canvas, Qt.Key.Key_B)
    assert window.before
    np.testing.assert_array_equal(qimage_to_array(window.output_view.image_item.pixmap().toImage()), qimage_to_array(window.original_image))
    QTest.keyRelease(window.canvas, Qt.Key.Key_B)
    assert not window.before
    window.difference.setChecked(True)
    assert window.diff_image is not None
    window.difference.setChecked(False)
    window.preview_actual()
    assert window.output_view.transform().m11() * window.output_view.viewport().devicePixelRatioF() == pytest.approx(1)
    screenshot_folder = Path(__file__).resolve().parent.parent / "test-output"
    screenshot_folder.mkdir(exist_ok=True)
    window.grab().save(str(screenshot_folder / "gui-output-preview.png"))
    window.view_tabs.setCurrentIndex(0)
    window.canvas.fit()
    window.grab().save(str(screenshot_folder / "gui-editor.png"))


def test_late_detection_not_applied_to_new_image(window, examples):
    open_clean(window, examples)
    original = window.document
    window.detect_source()
    window.add_source(read_source(examples / "SYNTHETIC_different_field.png"))
    settled(window)
    assert window.document is not original
    assert window.document.project.candidates == []


def test_freehand_mask_polygon_resize_and_endpoint_drag(window, examples):
    open_clean(window, examples)
    window.tool.setCurrentText("Crop freehand")
    canvas = window.canvas
    points = [[130, 130], [300, 110], [540, 150], [550, 450], [300, 500], [140, 400], [130, 130]]
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.mapFromScene(QPointF(*points[0])))
    for point in points[1:]:
        QTest.mouseMove(canvas.viewport(), canvas.mapFromScene(QPointF(*point)), delay=20)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.mapFromScene(QPointF(*points[-1])))
    settled(window)
    assert window.document.project.crop.kind == "freehand"
    window.tool.setCurrentText("Mask polygon")
    for point in [[200, 200], [240, 200], [250, 250], [200, 250]]:
        click(canvas, point)
    QTest.keyClick(canvas, Qt.Key.Key_Return)
    settled(window)
    assert window.document.project.masks[-1]["kind"] == "polygon"
    window.crop_kind.setCurrentText("rectangle")
    window.ratio.setCurrentText("16:9")
    window.draw_crop()
    drag(canvas, [700, 700], [1023, 1023])
    settled(window)
    p = window.document.project
    assert p.crop.rect[2] / p.crop.rect[3] == pytest.approx(16 / 9)
    assert p.crop.rect[0] + p.crop.rect[2] <= 1024
    assert p.crop.rect[1] + p.crop.rect[3] <= 1024
    window.tool.setCurrentText("Edit crop")
    x, y, w, h = p.crop.rect
    drag(canvas, [x + w, y + h], [x + w - 60, y + h - 40])
    settled(window)
    assert p.crop.rect[2] < w
    assert p.crop.rect[2] / p.crop.rect[3] == pytest.approx(16 / 9)
    window.tool.setCurrentText("Endpoints")
    drag(canvas, [200, 300], [450, 300])
    settled(window)
    assert np.linalg.norm(np.array(p.calibration.endpoints[1]) - p.calibration.endpoints[0]) == pytest.approx(250, abs=3)
    window.square.setChecked(True)
    window.known_length.setText("50 nm")
    window.endpoint_calibration()
    window.confirm_calibration()
    settled(window)
    assert p.calibration.sx == pytest.approx(.2, abs=.005)


def test_reference_manual_corresponding_mouse_points(window, examples):
    open_clean(window, examples)
    reference = read_source(examples / "SYNTHETIC_reference_0.5nm.png")
    dialog = ReferenceDialog(window, reference, window.document)
    dialog.show()
    QTest.qWait(80)
    for point in [[150, 150], [750, 200], [300, 700], [750, 750]]:
        click(dialog.ref_view, point, Qt.KeyboardModifier.ControlModifier)
        click(dialog.work_view, point, Qt.KeyboardModifier.ControlModifier)
    dialog.manual_register()
    wait_until(lambda: dialog.registration is not None)
    assert dialog.registration["r"] == pytest.approx(1, abs=.004)
    assert dialog.registration["inliers"] == 4
    dialog.flicker.setChecked(True)
    dialog.flicker_tick()
    assert dialog.flicker_state
    dialog.reject()


def test_display_reset_and_solid_mask_confirmation(window, examples):
    open_clean(window, examples)
    original = window.document.rgba.copy()
    window.display_low.setValue(50)
    window.display_high.setValue(200)
    window.apply_display()
    settled(window)
    assert not np.array_equal(original, window.document.rgba)
    window.reset()
    settled(window)
    np.testing.assert_array_equal(window.document.rgba, original)
    window.pure_confirmed.setChecked(True)
    window.treatment.setCurrentText("solid")
    window.apply_treatment()
    window.canvas_edit("mask", {"layer": "line", "kind": "rect", "rect": [10, 10, 20, 10]})
    settled(window)
    assert window.document.project.treatment == "keep"
    assert not window.document.project.pure_color_confirmed


def test_crop_retains_calibration_and_pending_bar_explains_itself(window, examples):
    open_clean(window, examples)
    window.tool.setCurrentText("Endpoints")
    for widget, value in zip(window.endpoint_fields, (100, 100, 350, 100)):
        widget.setValue(value)
    window.known_length.setText("50 nm")
    window.endpoint_calibration()
    window.confirm_calibration()
    assert window.tool.currentText() == "Pan"
    window.scale_form.enabled.setChecked(True)
    window.scale_form.length.setText("5 nm")
    window.apply_style()
    calibration = deepcopy(window.document.project.calibration)
    window.canvas_edit("crop-rect", ["rectangle", [100, 100, 577, 577]])
    settled(window)
    assert window.document.project.calibration == calibration
    assert window.composition.scale_length_px == 25
    for field, value in zip(window.crop_fields, (150, 150, 400, 300)):
        field.setValue(value)
    window.apply_crop()
    settled(window)
    assert window.document.project.calibration == calibration
    window.known_length.setText("25 nm")
    window.tool.setCurrentText("Endpoints")
    drag(window.canvas, [100, 100], [120, 100])
    settled(window)
    assert window.document.project.calibration.status == "Pending"
    assert window.known_length.text() == "25 nm"
    assert window.composition.scale_rect is None
    assert "endpoints changed" in window.scale_state.text()
    assert "endpoints changed" in window.notice.text()
    with pytest.raises(ValueError, match="Use endpoints"):
        window.confirm_calibration()
    window.undo(-1)
    settled(window)
    assert window.document.project.calibration.status == "Confirmed"
    assert window.composition.scale_length_px == 25
    assert "hidden" not in window.scale_state.text()


def test_rotation_buttons_preview_drag_export_and_undo(window, examples, tmp_path):
    from PySide6.QtWidgets import QPushButton
    open_clean(window, examples)
    calibrate_manual(window)
    window.canvas_edit("crop-rect", ["rectangle", [100, 120, 500, 300]])
    window.scale_form.enabled.setChecked(True)
    window.scale_form.length.setText("5 nm")
    window.apply_style()
    settled(window)
    original = window.document.source.pixels.copy()
    button = next(b for b in window.findChildren(QPushButton) if b.text() == "Rotate right 90°")
    button.click()
    settled(window)
    assert window.document.project.output.rotation_deg == 90
    assert window.view_tabs.currentIndex() == 1
    assert window.result_image.width() == 300 and window.result_image.height() == 500
    assert window.composition.scale_length_px == 25
    window.view_tabs.setCurrentIndex(0)
    window.canvas.fit()
    window.tool.setCurrentText("Move scale")
    x, y, w, h = window.composition.scale_rect
    a = window.composition.to_source([x + w / 2, y + h / 2])
    b = window.composition.to_source([x + w / 2 - 20, y + h / 2 - 10])
    drag(window.canvas, a, b)
    settled(window)
    assert window.document.project.style.x == pytest.approx(x - 20, abs=2)
    assert window.document.project.style.y == pytest.approx(y - 10, abs=2)
    p = window.document.project
    p.style.anchor = "bottom-right"
    window.commit()
    window.rotation_degrees.setValue(17.5)
    next(b for b in window.findChildren(QPushButton) if b.text() == "Apply rotation").click()
    settled(window)
    assert window.document.project.output.rotation_deg == 17.5
    assert not [i for i in window.composition.issues if i.severity == "error"]
    window.start_export(str(tmp_path / "rotated.png"))
    settled(window)
    np.testing.assert_array_equal(read_source(tmp_path / "rotated.png").pixels, qimage_to_array(window.result_image))
    window.save_to(str(tmp_path / "rotated-project.json"))
    settled(window)
    assert load_project(tmp_path / "rotated-project.json").output.rotation_deg == 17.5
    window.undo(-1)
    settled(window)
    assert window.document.project.output.rotation_deg == 90
    window.undo(1)
    settled(window)
    assert window.document.project.output.rotation_deg == 17.5
    np.testing.assert_array_equal(window.document.source.pixels, original)
    window.properties.setCurrentIndex(1)
    window.grab().save(str(Path(__file__).resolve().parent.parent / "test-output/rotation-gui.png"))


def test_default_source_export_and_resolution_presets(window, examples, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QPushButton
    window.load_image(examples / "SYNTHETIC_16bit_OME.tif")
    settled(window)
    assert window.export_kind.currentText() == "Same as source (original bit depth)"
    calibrate_manual(window)
    window.canvas_edit("crop-rect", ["rectangle", [100, 100, 400, 300]])
    window.scale_form.enabled.setChecked(True)
    window.scale_form.length.setText("5 nm")
    window.apply_style()
    settled(window)
    before = deepcopy(window.document.project)
    assert before.style.outline
    for factor in (2, 4):
        next(b for b in window.findChildren(QPushButton) if b.text() == f"{factor}×").click()
        settled(window)
        p = window.document.project
        assert p.calibration == before.calibration and p.crop == before.crop
        assert p.style.font_size == before.style.font_size * factor
        assert p.style.thickness == before.style.thickness * factor
        assert p.style.outline_width == before.style.outline_width * factor
        assert window.composition.scale_length_px == 25 * factor
        assert (window.result_image.width(), window.result_image.height()) == (400 * factor, 300 * factor)
        assert not any(i.severity == "error" for i in window.composition.issues)
    window.undo(-1)
    settled(window)
    assert window.document.project.output.scale == 2
    assert window.document.project.style.font_size == before.style.font_size * 2
    target = tmp_path / "default-export.tif"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: (str(target), ""))
    window.export_dialog()
    settled(window)
    data = read_source(target).pixels
    assert data.dtype == np.uint16 and data.shape == (600, 800)
    assert np.unique(data[:200, :200]).size > 256
    assert "Exported:" in window.notice.text()


def test_velox_preset_template_and_legacy_switch(window, examples, tmp_path, monkeypatch):
    open_clean(window, examples)
    assert window.preset.currentText() == "Velox-style"
    assert window.document.project.style.outline
    calibrate_manual(window)
    calibration = deepcopy(window.document.project.calibration)
    window.scale_form.enabled.setChecked(True)
    window.scale_form.length.setText("50 nm")
    window.apply_style()
    window.preset.setCurrentText("White")
    window.apply_preset()
    assert not window.document.project.style.outline
    window.preset.setCurrentText("Velox-style")
    window.apply_preset()
    settled(window)
    style = deepcopy(window.document.project.style)
    assert style.outline and style.text_align == "left"
    assert style.enabled and style.length_nm == 50 and style.anchor == "bottom-left"
    assert window.document.project.calibration == calibration
    target = tmp_path / "style.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: (str(target), ""))
    window.save_template()
    window.preset.setCurrentText("Black")
    window.apply_preset()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(target), ""))
    window.load_template()
    settled(window)
    assert window.document.project.style == style
    assert window.composition.scale_length_px == 250


def test_legacy_below_template_applies_above_in_both_previews(window, examples, tmp_path, monkeypatch):
    import json
    from dataclasses import asdict
    from PySide6.QtWidgets import QLabel, QPushButton
    open_clean(window, examples)
    calibrate_manual(window)
    calibration = deepcopy(window.document.project.calibration)
    style = asdict(window.document.project.style)
    style.update(enabled=True, length_nm=50, text_position="below")
    template = tmp_path / "legacy-below.json"
    template.write_text(json.dumps({"style_template_version": 1, "style": style}), encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(template), ""))
    window.load_template()
    assert "text_position" not in window.scale_form.fields
    assert any(label.text() == "Always above the bar" for label in window.scale_form.findChildren(QLabel))
    next(b for b in window.findChildren(QPushButton) if b.text() == "Apply style / length").click()
    settled(window)
    assert window.document.project.style.text_position == "above"
    assert window.document.project.calibration == calibration
    bar = next(v for v in window.composition.primitives if v.get("role") == "scale-bar")
    label = next(v for v in window.composition.primitives if v.get("role") == "scale-label")
    assert label["y"] < bar["rect"][1]
    for item in (window.canvas.result_item, window.output_view.image_item):
        np.testing.assert_array_equal(qimage_to_array(item.pixmap().toImage()), qimage_to_array(window.result_image))


def endpoint_mouse_move(canvas, point, modifiers=Qt.KeyboardModifier.NoModifier):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    pos = canvas.mapFromScene(QPointF(*point))
    event = QMouseEvent(QEvent.Type.MouseMove, QPointF(pos), QPointF(canvas.viewport().mapToGlobal(pos)),
                       Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, modifiers)
    QApplication.sendEvent(canvas.viewport(), event)


@pytest.mark.parametrize("zoom", [.75, 2.0])
def test_shift_draws_horizontal_calibration_at_any_zoom(window, examples, tmp_path, zoom):
    open_clean(window, examples)
    window.tool.setCurrentText("Endpoints")
    window.canvas.scale(zoom, zoom)
    window.known_length.setText("50 nm")
    window.square.setChecked(False)
    canvas = window.canvas
    a, b = [200, 250], [430, 310]
    start = canvas.mapFromScene(QPointF(*a))
    end = canvas.mapFromScene(QPointF(*b))
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, start)
    endpoint_mouse_move(canvas, b, Qt.KeyboardModifier.ShiftModifier)
    assert canvas.draft[0][1] == canvas.draft[1][1]
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, end)
    settled(window)
    p = window.document.project
    assert p.calibration.endpoints[0][1] == p.calibration.endpoints[1][1]
    assert p.calibration.status == "Pending"
    assert window.known_length.text() == "50 nm" and not window.square.isChecked()
    x1, _, x2, _ = [field.value() for field in window.endpoint_fields]
    window.endpoint_calibration()
    assert p.calibration.sx == pytest.approx(50 / abs(x2 - x1))
    assert p.calibration.sy is None
    window.confirm_calibration()
    settled(window)
    assert p.calibration.status == "Confirmed"
    window.save_to(str(tmp_path / "horizontal.json"))
    settled(window)
    assert load_project(tmp_path / "horizontal.json").calibration == p.calibration


@pytest.mark.parametrize("index", [0, 1])
def test_shift_moves_either_endpoint_around_fixed_opposite(window, examples, index):
    open_clean(window, examples)
    original = [[150., 250.], [400., 300.]]
    window.canvas_edit("endpoints", deepcopy(original))
    settled(window)
    window.tool.setCurrentText("Endpoints")
    canvas = window.canvas
    target = [original[index][0] + 25, original[index][1] + 80]
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, canvas.mapFromScene(QPointF(*original[index])))
    endpoint_mouse_move(canvas, target, Qt.KeyboardModifier.ShiftModifier)
    assert canvas.draft[1-index] == original[1-index]
    assert canvas.draft[index][1] == original[1-index][1]
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, canvas.mapFromScene(QPointF(*target)))
    settled(window)
    pts = window.document.project.calibration.endpoints
    assert pts[1-index] == original[1-index] and pts[index][1] == original[1-index][1]
    window.undo(-1)
    settled(window)
    assert window.document.project.calibration.endpoints == original


def test_shift_toggle_updates_endpoint_preview_without_mouse_movement(window, examples):
    open_clean(window, examples)
    window.tool.setCurrentText("Endpoints")
    canvas = window.canvas
    a, b = [150, 250], [430, 330]
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.mapFromScene(QPointF(*a)))
    endpoint_mouse_move(canvas, b)
    free = deepcopy(canvas.draft)
    assert free[0][1] != free[1][1]
    QTest.keyPress(canvas, Qt.Key.Key_Shift)
    assert canvas.draft[0][1] == canvas.draft[1][1]
    QTest.keyRelease(canvas, Qt.Key.Key_Shift)
    assert canvas.draft == free
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.mapFromScene(QPointF(*b)))
    settled(window)
    assert window.document.project.calibration.endpoints == free


def test_shift_release_event_uses_final_pointer_without_move_event(window, examples):
    open_clean(window, examples)
    window.tool.setCurrentText("Endpoints")
    canvas = window.canvas
    a, b = [150, 250], [430, 330]
    start, end = [canvas.mapFromScene(QPointF(*p)) for p in (a, b)]
    expected_x = canvas.mapToScene(end).x()
    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, end)
    settled(window)
    pts = window.document.project.calibration.endpoints
    assert pts[0][1] == pts[1][1] and pts[1][0] == pytest.approx(expected_x)
