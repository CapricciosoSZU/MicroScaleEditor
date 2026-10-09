"""English desktop UI, parameter history and revision-checked background work."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
import time
import traceback

import cv2
import numpy as np
from PySide6.QtCore import QObject, QPointF, QRectF, QRunnable, QSettings, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QKeySequence, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QToolBar, QVBoxLayout, QWidget)

from .canvas import EditorCanvas, ImageView
from .detection import build_masks, candidate_masks, detect, register
from .geometry import bounds, calibrate, distance, format_length, normalized_rect, output_geometry, parse_length, positive, suggestions, constrain_rect
from .image_io import Source, array_to_qimage, display_rgba, project_for, qimage_to_array, read_source
from .model import Calibration, Crop, History, Project, Style, atomic_json, file_hash, load_project, relink_source, save_project
from .rendering import change_view, compose, export_file, inset_project, render_image
from .runtime import runtime_dir, user_data_dir
from . import __version__

log = logging.getLogger(__name__)


class JobSignals(QObject):
    result = Signal(object)
    failed = Signal(str, str)
    progress = Signal(int, str)


class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = JobSignals()

    def run(self):
        try:
            self.signals.result.emit(self.function(self.signals.progress.emit))
        except Exception as exc:
            details = traceback.format_exc()
            log.error("Background job failed\n%s", details)
            self.signals.failed.emit(str(exc), details)


@dataclass
class Document:
    source: Source
    project: Project
    history: History
    rgba: np.ndarray
    path: str = ""
    revision: int = 0


def combo(items):
    widget = QComboBox()
    widget.addItems(items)
    return widget


def number(value=0., minimum=-1e7, maximum=1e7, decimals=3):
    widget = QDoubleSpinBox()
    widget.setRange(minimum, maximum)
    widget.setDecimals(decimals)
    widget.setValue(value)
    widget.setKeyboardTracking(False)
    return widget


def row(*widgets):
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return box


class Details(QWidget):
    """One set of controls, revealed as needed without duplicated edit logic."""
    def __init__(self, title, content, expanded=False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton(("▾ " if expanded else "▸ ") + title)
        button.setCheckable(True)
        button.setChecked(expanded)
        content.setVisible(expanded)
        def toggle(checked):
            content.setVisible(checked)
            button.setText(("▾ " if checked else "▸ ") + title)
        button.toggled.connect(toggle)
        layout.addWidget(button)
        layout.addWidget(content)


class StyleForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = {}
        self.layout = QFormLayout(self)
        self.layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.enabled = QCheckBox("Draw a physical scale bar")
        self.layout.addRow(self.enabled)
        self.length = QLineEdit("5 nm")
        self.length.setObjectName("scaleLength")
        self.layout.addRow("Physical length", self.length)
        specs = [("color", "Color", QLineEdit("#ffffff")), ("thickness", "Bar thickness (px)", number(5, .1)),
                 ("endcaps", "End ticks", QCheckBox()), ("font", "Font family", QLineEdit("Arial")),
                 ("font_size", "Font size (px)", number(22, 1)), ("bold", "Bold", QCheckBox()),
                 ("text_position", "Text", combo(["above", "below"])), ("gap", "Text gap (px)", number(6, 0)),
                 ("plate", "Background plate", QCheckBox()), ("plate_color", "Plate color", QLineEdit("#000000")),
                 ("plate_opacity", "Plate opacity", number(.8, 0, 1)),
                 ("anchor", "Position", combo([f"{v}-{h}" for v in ("top", "middle", "bottom") for h in ("left", "center", "right")] + ["custom"])),
                 ("margin", "Margin (output px)", number(20, 0)), ("x", "Group x (output px)", number(20)), ("y", "Group y (output px)", number(20))]
        advanced_widget = QWidget()
        advanced = QFormLayout(advanced_widget)
        advanced.setContentsMargins(0, 0, 0, 0)
        advanced.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        advanced_keys = {"endcaps", "font", "font_size", "bold", "text_position", "gap", "plate_color", "plate_opacity"}
        for key, label, control in specs:
            self.fields[key] = control
            (advanced if key in advanced_keys else self.layout).addRow(label, control)
        self.layout.addRow(Details("Font, end ticks and background details", advanced_widget))

    def load(self, style):
        self.enabled.setChecked(style.enabled)
        self.length.setText(format_length(style.length_nm))
        for key, control in self.fields.items():
            value = getattr(style, key)
            if isinstance(control, QCheckBox):
                control.setChecked(value)
            elif isinstance(control, QComboBox):
                control.setCurrentText(value)
            elif isinstance(control, QDoubleSpinBox):
                control.setValue(value)
            else:
                control.setText(value)

    def value(self):
        style = Style(enabled=self.enabled.isChecked(), length_nm=parse_length(self.length.text()))
        for key, control in self.fields.items():
            if isinstance(control, QCheckBox):
                value = control.isChecked()
            elif isinstance(control, QComboBox):
                value = control.currentText()
            elif isinstance(control, QDoubleSpinBox):
                value = control.value()
            else:
                value = control.text()
            setattr(style, key, value)
        for color in (style.color, style.plate_color):
            if not QColor(color).isValid():
                raise ValueError("Use a color name or #RRGGBB.")
        return style


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MicroScale Editor {__version__}")
        self.resize(1480, 920)
        self._startup_positioned = False
        self._startup_screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self.documents = []
        self.document = None
        self.jobs = set()
        self.syncing = False
        self.composition = None
        self.result_image = None
        self.original_image = None
        self.diff_image = None
        self.render_busy = False
        self.render_pending = False
        self.needs_fit = False
        self.before = False
        self.copied = None
        self.settings = QSettings("MicroScale", "Editor")
        self.recovery_dir = user_data_dir() / "recovery"
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(160)
        self.render_timer.timeout.connect(self.request_render)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(900)
        self.autosave_timer.timeout.connect(self.autosave)
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._startup_positioned:
            self._startup_positioned = True
            self._center_startup_window()
            # Native title-bar/frame margins settle after the first show event.
            QTimer.singleShot(0, self._center_startup_window)

    def _center_startup_window(self):
        screen = self._startup_screen or self.screen()
        if screen is None or self.isMaximized() or self.isFullScreen():
            return
        available = screen.availableGeometry()
        handle = self.windowHandle()
        if handle is not None and handle.screen() is not screen:
            handle.setScreen(screen)
        frame = self.frameGeometry()
        extra_w = max(0, frame.width() - self.width())
        extra_h = max(0, frame.height() - self.height())
        self.resize(max(1, min(1480, available.width() - extra_w - 32)),
                    max(1, min(920, available.height() - extra_h - 32)))
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def safe(self, function):
        def call(*_):
            try:
                return function()
            except Exception as exc:
                log.exception("UI action failed")
                self.notify(str(exc), error=True)
        return call

    def button(self, text, function):
        button = QPushButton(text)
        button.clicked.connect(self.safe(function))
        return button

    def notify(self, message, error=False):
        self.notice.setText(message)
        self.notice.setStyleSheet("color: #ff8392" if error else "color: #9be1d7")
        self.statusBar().showMessage(message, 12000)

    def require_document(self):
        if self.document is None:
            raise ValueError("Open a source image first.")
        return self.document.project

    def _build_ui(self):
        splitter = QSplitter()
        self.setCentralWidget(splitter)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("SOURCE IMAGES"))
        left_layout.addWidget(self.button("Open image…", self.open_images))
        self.image_list = QListWidget()
        self.image_list.setObjectName("imageList")
        self.image_list.currentRowChanged.connect(self.select_document)
        left_layout.addWidget(self.image_list)
        left_layout.addWidget(self.button("Open project…", self.open_project_dialog))
        left_layout.addWidget(self.button("Recover autosave…", self.recover_dialog))
        left_layout.addWidget(self.button("Save project…", self.save_dialog))
        splitter.addWidget(left)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.view_tabs = QTabWidget()
        self.canvas = EditorCanvas()
        self.canvas.setObjectName("sourceCanvas")
        self.output_view = ImageView()
        self.output_view.setObjectName("outputPreview")
        self.view_tabs.addTab(self.canvas, "Edit • source coordinates")
        self.view_tabs.addTab(self.output_view, "Output pixel preview")
        center_layout.addWidget(self.view_tabs)
        self.notice = QLabel("Open an image or use File → Synthetic examples. No calibration is inferred from DPI.")
        self.notice.setWordWrap(True)
        center_layout.addWidget(self.notice)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        center_layout.addWidget(self.progress)
        splitter.addWidget(center)
        self.properties = QTabWidget()
        self.properties.setMinimumWidth(330)
        self.source_form = self._tab("Source")
        self.crop_form = self._tab("Crop")
        self.scale_form_layout = self._tab("Scale bar")
        self.export_form = self._tab("Export")
        self._source_ui()
        self._crop_ui()
        self._scale_ui()
        self._export_ui()
        splitter.addWidget(self.properties)
        splitter.setSizes([170, 920, 390])
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.tool = combo(["Edit crop", "Draw crop", "Crop polygon", "Crop freehand", "Pan", "Endpoints", "Move scale",
                           "Draw inset ROI", "Edit inset ROI", "Move inset", "Mask rectangle", "Mask polygon", "Mask brush", "Mask erase", "Detect region",
                           "Measure", "Measure horizontal", "Measure vertical", "Protect polygon"])
        self.tool.setObjectName("toolSelector")
        self.tool.currentTextChanged.connect(self.canvas.set_mode)
        toolbar.addWidget(self.tool)
        for label, action in (("Fit", self.fit), ("100%", self.actual_size), ("Undo", lambda: self.undo(-1)), ("Redo", lambda: self.undo(1)), ("Reset", self.reset)):
            toolbar.addWidget(self.button(label, action))
        self.mask_toggle = QCheckBox("Masks")
        self.mask_toggle.setChecked(True)
        self.mask_toggle.toggled.connect(self.toggle_masks)
        toolbar.addWidget(self.mask_toggle)
        self.guide_toggle = QCheckBox("Guides")
        self.guide_toggle.setChecked(True)
        self.guide_toggle.toggled.connect(self.toggle_guides)
        toolbar.addWidget(self.guide_toggle)
        self.difference = QCheckBox("Show changes")
        self.difference.toggled.connect(self.update_comparison)
        toolbar.addWidget(self.difference)
        toolbar.addWidget(QLabel("  Hold B: Original"))
        self.canvas.edited.connect(self.canvas_edit)
        self.canvas.message.connect(self.notify)
        self.canvas.scaleDoubleClicked.connect(self.edit_length)
        for view in (self.canvas, self.output_view):
            view.beforeChanged.connect(self.set_before)
            view.zoomChanged.connect(lambda _: self.update_status())
        self.view_tabs.currentChanged.connect(lambda _: self.update_status())
        menu = self.menuBar().addMenu("File")
        for text, shortcut, function in (("Open image…", "Ctrl+O", self.open_images), ("Open project…", "Ctrl+Shift+O", self.open_project_dialog),
                                         ("Save project…", "Ctrl+S", self.save_dialog), ("Export…", "Ctrl+E", self.export_dialog),
                                         ("Save project as…", "Ctrl+Shift+S", lambda: self.save_dialog(save_as=True)),
                                         ("Copy finished image", "Ctrl+Shift+C", self.clipboard), ("Relink source…", "", self.relink_dialog),
                                         ("Synthetic examples", "", self.open_examples)):
            act = QAction(text, self)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(self.safe(function))
            menu.addAction(act)
        edit = self.menuBar().addMenu("Edit")
        for text, shortcut, function in (("Undo", "Ctrl+Z", lambda: self.undo(-1)), ("Redo", "Ctrl+Y", lambda: self.undo(1))):
            act = QAction(text, self)
            act.setShortcut(shortcut)
            act.triggered.connect(self.safe(function))
            edit.addAction(act)
        help_menu = self.menuBar().addMenu("Help")
        action = QAction("Coordinate and pixel rules", self)
        action.triggered.connect(lambda: QMessageBox.information(self, "Measurement rules", "Solid bars use outer pixel edges [x, x + width). Tick bars use tick centerlines. Inspect antialiasing at 50% local contrast.\n\nAll ROI/mask/measurement geometry is stored in source pixels. Scale styles use output pixels. Print fonts/lines use pt. Wheel zoom and monitor DPI never change sample calibration.\n\nPolygon: click vertices; Enter/right-click closes; edit by dragging vertices; Ctrl-click inserts; Delete removes. Middle mouse pans. Hold B compares original/result at identical geometry.\n\nMasks cannot recover covered sample pixels. Opaque coverage is an annotation, not restoration."))
        help_menu.addAction(action)
        self.setStyleSheet("QMainWindow, QDialog {background:#202630; color:#e6edf5;} QLabel,QCheckBox,QGroupBox {color:#e6edf5;} QTabWidget::pane {border:1px solid #455162;} QPushButton {padding:5px 8px;} QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QListWidget,QPlainTextEdit {min-height:23px;} QGroupBox {margin-top:12px; padding-top:14px;}")

    def _tab(self, title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        scroll.setWidget(widget)
        self.properties.addTab(scroll, title)
        return layout

    def _source_ui(self):
        f = self.source_form
        self.source_info = QLabel("No source image")
        self.source_info.setWordWrap(True)
        f.addRow(self.source_info)
        f.addRow(self.button("Set calibration reference…", self.reference_dialog))
        self.sx = QLineEdit()
        self.sx.setPlaceholderText("e.g. 0.2")
        self.sx.setObjectName("calibrationX")
        self.sy = QLineEdit()
        self.cal_unit = combo(["nm/px", "μm/px"])
        f.addRow("Sample units", self.cal_unit)
        f.addRow("Horizontal s_x", self.sx)
        f.addRow("Vertical s_y (optional)", self.sy)
        self.square = QCheckBox("Assume square pixels")
        f.addRow(self.square)
        f.addRow(self.button("Use manual calibration", self.manual_calibration))
        self.known_length = QLineEdit("50 nm")
        f.addRow("Known length", self.known_length)
        self.endpoint_fields = [number(0), number(0), number(250), number(0)]
        f.addRow("Endpoint 1 · x / y", row(*self.endpoint_fields[:2]))
        f.addRow("Endpoint 2 · x / y", row(*self.endpoint_fields[2:]))
        f.addRow(row(self.button("Pick endpoints", lambda: self.tool.setCurrentText("Endpoints")), self.button("Use endpoints", self.endpoint_calibration)))
        self.conflict_threshold = number(2, 0, 100)
        f.addRow("Review threshold (%)", self.conflict_threshold)
        self.conflict_threshold.editingFinished.connect(self.safe(self.threshold_change))
        self.resolve_conflict = QCheckBox("Reviewed conflict: choose current source")
        f.addRow(self.resolve_conflict)
        f.addRow(self.button("Confirm calibration", self.confirm_calibration))
        self.evidence = QLabel("Uncalibrated")
        self.evidence.setWordWrap(True)
        self.evidence.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        f.addRow(self.evidence)
        group = QGroupBox("Old scale · detection and masks")
        g = QFormLayout(group)
        g.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        g.addRow(row(self.button("Detect + OCR", self.detect_source), self.button("Detect region", lambda: self.tool.setCurrentText("Detect region"))))
        self.candidate_list = QListWidget()
        self.candidate_list.setMaximumHeight(130)
        g.addRow(self.candidate_list)
        g.addRow(row(self.button("Use candidate", self.use_candidate), self.button("Ignore false candidate", self.ignore_candidate)))
        self.mask_layer = combo(["line", "text", "background"])
        self.mask_layer.currentTextChanged.connect(lambda text: setattr(self.canvas, "mask_layer", text))
        g.addRow("Mask layer", self.mask_layer)
        self.brush_size = number(8, 1, 200)
        self.brush_size.valueChanged.connect(lambda value: setattr(self.canvas, "brush_radius", value))
        g.addRow("Brush radius (source px)", self.brush_size)
        g.addRow(row(self.button("Rectangle", lambda: self.tool.setCurrentText("Mask rectangle")), self.button("Polygon", lambda: self.tool.setCurrentText("Mask polygon"))))
        g.addRow(row(self.button("Brush", lambda: self.tool.setCurrentText("Mask brush")), self.button("Eraser", lambda: self.tool.setCurrentText("Mask erase"))))
        g.addRow(row(self.button("Expand 1 px", lambda: self.morph(1)), self.button("Shrink 1 px", lambda: self.morph(-1)), self.button("Clear layer", self.clear_mask)))
        self.treatment = combo(["keep", "solid", "plate"])
        g.addRow("Treatment", self.treatment)
        self.treatment_color = QLineEdit("#000000")
        g.addRow("Opaque fill color", self.treatment_color)
        self.pure_confirmed = QCheckBox("Uniform annotation background confirmed")
        g.addRow(self.pure_confirmed)
        g.addRow(self.button("Apply treatment", self.apply_treatment))
        g.addRow(self.button("Crop off selected footer", self.crop_footer))
        hint = QLabel("Keep = leave pixels. Solid = confirmed flat annotation area. Plate = explicit opaque coverage, not recovered data. A clean paired source needs no removal.")
        hint.setWordWrap(True)
        g.addRow(hint)
        f.addRow(Details("Old scale detection and mask tools", group))
        display = QGroupBox("Display mapping · source data stays unchanged")
        df = QFormLayout(display)
        self.display_low = number(0, -1e20, 1e20)
        self.display_high = number(255, -1e20, 1e20)
        df.addRow("Low / high", row(self.display_low, self.display_high))
        df.addRow(self.button("Apply display window", self.apply_display))
        f.addRow(Details("Display mapping", display))

    def _crop_ui(self):
        f = self.crop_form
        self.crop_kind = combo(["rectangle", "square", "circle", "ellipse", "polygon", "freehand"])
        self.crop_kind.currentTextChanged.connect(self.select_shape)
        f.addRow("Shape", self.crop_kind)
        self.ratio = combo(["Free", "Original", "1:1", "4:3", "3:2", "16:9", "3:4", "2:3", "9:16", "Custom"])
        self.ratio.currentTextChanged.connect(lambda _: self.update_tool_geometry())
        self.custom_ratio = QLineEdit("4:3")
        f.addRow("Aspect W:H", self.ratio)
        f.addRow("Custom W:H", self.custom_ratio)
        self.crop_fields = [number(0), number(0), number(512, 1), number(512, 1)]
        f.addRow("Source x / y", row(*self.crop_fields[:2]))
        f.addRow("Width / height", row(*self.crop_fields[2:]))
        f.addRow(row(self.button("Apply geometry", self.apply_crop), self.button("Draw crop", self.draw_crop)))
        self.background = combo(["transparent", "white", "black", "custom"])
        self.bg_color = QLineEdit("#f2f2f2")
        f.addRow("Outside shape", self.background)
        f.addRow("Custom background", self.bg_color)
        f.addRow(self.button("Apply background", self.apply_background))
        self.crop_dimensions = QLabel("")
        self.crop_dimensions.setWordWrap(True)
        f.addRow(self.crop_dimensions)
        hint = QLabel("Polygon: click points; Enter/right-click closes. Edit crop: drag corners/vertices or move inside. Ctrl-click adds a vertex; Delete removes it. Freehand closes on release.")
        hint.setWordWrap(True)
        f.addRow(hint)
        inset = QGroupBox("Linked inset · digital crop of this source")
        g = QFormLayout(inset)
        g.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.inset_enabled = QCheckBox("Show linked inset")
        self.inset_circle = QCheckBox("Circular (square source ROI)")
        g.addRow(self.inset_enabled)
        g.addRow(self.inset_circle)
        g.addRow(row(self.button("Draw source ROI", self.draw_inset), self.button("Edit source ROI", lambda: self.tool.setCurrentText("Edit inset ROI"))))
        self.inset_roi_fields = [number(100), number(100), number(100, 1), number(100, 1)]
        g.addRow("ROI x / y", row(*self.inset_roi_fields[:2]))
        g.addRow("ROI width / height", row(*self.inset_roi_fields[2:]))
        self.inset_fields = [number(30), number(30), number(200, 16)]
        g.addRow("Panel x / y (output)", row(*self.inset_fields[:2]))
        g.addRow("Panel width (output px)", self.inset_fields[2])
        g.addRow(row(self.button("Apply inset", self.apply_inset), self.button("Move / resize panel", lambda: self.tool.setCurrentText("Move inset"))))
        g.addRow(row(self.button("Inset scale style…", self.inset_style_dialog), self.button("Export inset…", lambda: self.export_dialog(inset=True))))
        f.addRow(inset)
        f.addRow(row(self.button("Measure", lambda: self.tool.setCurrentText("Measure")), self.button("Protect polygon", lambda: self.tool.setCurrentText("Protect polygon"))))
        f.addRow(row(self.button("Clear measurements", self.clear_measures), self.button("Clear protected regions", self.clear_protected)))

    def _scale_ui(self):
        f = self.scale_form_layout
        self.preset = combo(["White", "Black", "White on dark plate"])
        f.addRow("Preset", self.preset)
        f.addRow(self.button("Use preset", self.apply_preset))
        self.quick_length = combo(["5 nm", "10 nm", "20 nm", "50 nm", "100 nm", "200 nm", "0.5 μm", "1 μm"])
        f.addRow("Quick physical length", self.quick_length)
        self.quick_length.activated.connect(lambda _: self.scale_form.length.setText(self.quick_length.currentText()))
        self.suggestions = combo([])
        self.suggestions.activated.connect(lambda _: self.scale_form.length.setText(self.suggestions.currentText()))
        f.addRow("Suggested lengths", self.suggestions)
        self.scale_form = StyleForm()
        f.addRow(self.scale_form)
        f.addRow(row(self.button("Apply style / length", self.apply_style), self.button("Drag group", lambda: self.tool.setCurrentText("Move scale"))))
        f.addRow(row(self.button("Save template…", self.save_template), self.button("Load template…", self.load_template)))
        f.addRow(row(self.button("Copy settings…", self.copy_settings), self.button("Paste settings", self.paste_settings)))
        f.addRow(QLabel("Appearance is separate from sample calibration."))

    def _export_ui(self):
        f = self.export_form
        self.output_mode = combo(["native", "width", "print"])
        self.output_scale = number(1, .01, 100, 5)
        self.output_width = number(1024, 1, 100000, 0)
        self.output_mm = number(85, .1, 2000)
        self.output_dpi = number(300, 1, 10000)
        self.font_pt = number(9, .1, 500)
        self.line_pt = number(1, .05, 100)
        f.addRow("Mode", self.output_mode)
        f.addRow("Native uniform factor", self.output_scale)
        f.addRow("Custom width (px)", self.output_width)
        f.addRow("Panel width (mm)", self.output_mm)
        f.addRow("DPI", self.output_dpi)
        f.addRow("Print font / bar (pt)", row(self.font_pt, self.line_pt))
        self.panel_label = QLineEdit()
        self.panel_x = number(16)
        self.panel_y = number(16)
        f.addRow("Panel label", self.panel_label)
        f.addRow("Label x / y (px)", row(self.panel_x, self.panel_y))
        self.export_guides = QCheckBox("Include measurement / protected guides")
        f.addRow(self.export_guides)
        f.addRow(self.button("Apply output layout", self.apply_output))
        f.addRow(self.button("Export check / locate", self.run_check))
        self.check_list = QListWidget()
        self.check_list.setMinimumHeight(220)
        self.check_list.setWordWrap(True)
        self.check_list.itemClicked.connect(self.locate_issue)
        f.addRow(self.check_list)
        self.export_kind = combo(["PNG presentation", "TIFF presentation + data", "TIFF data only", "SVG editable annotations"])
        f.addRow("Format", self.export_kind)
        f.addRow(self.button("Export…", self.export_dialog))
        f.addRow(self.button("Copy finished image", self.clipboard))
        f.addRow(self.button("View output at 1:1 pixels", self.preview_actual))
        label = QLabel("PNG: 8-bit presentation with stated display window. Data TIFF: original dtype; irregular ROI gets a validity-mask sidecar. SVG: embedded raster with separate vector objects.")
        label.setWordWrap(True)
        f.addRow(label)

    def submit(self, function, callback, valid=None, on_error=None):
        job = Job(function)
        self.jobs.add(job)
        def done(value):
            self.jobs.discard(job)
            if valid is None or valid():
                try:
                    callback(value)
                except Exception as exc:
                    log.exception("Result integration failed")
                    self.notify(str(exc), True)
            else:
                log.info("Discarded stale background result")
                self.notify("Discarded a result from an older image/edit revision.")
        def failed(message, details):
            self.jobs.discard(job)
            if on_error:
                on_error(message)
            elif valid is None or valid():
                self.notify(message, True)
        job.signals.result.connect(done)
        job.signals.failed.connect(failed)
        job.signals.progress.connect(lambda value, message: (self.progress.setValue(value), self.statusBar().showMessage(message)))
        self.pool.start(job)

    def open_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open source images", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff)")
        for path in paths:
            self.load_image(path)

    def load_image(self, path):
        self.submit(lambda progress: read_source(path), self.add_source)

    def add_source(self, source, project=None, path=""):
        if project is None:
            project = project_for(source)
            recent = self.settings.value("lastStyle", "")
            if recent:
                try:
                    project.style = Style(**json.loads(recent))
                    project.style.enabled = False
                except (ValueError, TypeError):
                    log.warning("Ignoring invalid recent style")
        if tuple(project.source_shape) != source.pixels.shape:
            raise ValueError("Source dimensions do not match the project.")
        rgba = display_rgba(source.pixels, project.display_low, project.display_high)
        rgba.setflags(write=False)
        doc = Document(source, project, History(project), rgba, path)
        self.documents.append(doc)
        self.image_list.addItem(Path(source.path).name)
        self.image_list.setCurrentRow(len(self.documents) - 1)

    def select_document(self, index):
        if self.document:
            self.autosave()
        if 0 <= index < len(self.documents):
            self.document = self.documents[index]
            self.composition = None
            self.result_image = self.original_image = self.diff_image = None
            self.needs_fit = True
            self.sync_controls()
            self.render_timer.start()

    def sync_controls(self):
        if not self.document:
            return
        self.syncing = True
        try:
            p = self.document.project
            c = p.calibration
            self.source_info.setText(f"{Path(p.source_path).name}\n{p.source_shape[1]} × {p.source_shape[0]} · {p.source_dtype}\nSHA-256 {p.source_hash[:16]}…\n{p.reference.get('path', 'No calibration reference')}")
            self.sx.setText(f"{c.sx:.12g}" if c.sx else "")
            self.sy.setText(f"{c.sy:.12g}" if c.sy else "")
            self.cal_unit.setCurrentText("nm/px")
            self.square.setChecked(c.square_pixels)
            self.known_length.setText(format_length(c.length_nm))
            for widget, value in zip(self.endpoint_fields, sum(c.endpoints, [])):
                widget.setValue(value)
            self.conflict_threshold.setValue(c.conflict_threshold * 100)
            self.resolve_conflict.setChecked(False)
            evidence = [f"{c.status} · {c.source}", "Square pixels: assumed" if c.square_pixels else "Axes calibrated independently; unknown axes remain unavailable."]
            for item in c.evidence[-8:]:
                delta = abs(item["sx"] / c.sx - 1) * 100 if item.get("sx") and c.sx else None
                evidence.append(f"{item['source']}: sx={item.get('sx')}, sy={item.get('sy')} nm/px" + (f" · Δx {delta:.3g}%" if delta is not None else ""))
            if c.conflicts():
                evidence.append("REVIEW: sources exceed software threshold (not instrument precision).")
            self.evidence.setText("\n".join(evidence))
            self.crop_kind.setCurrentText(p.crop.kind)
            self.ratio.setCurrentText(p.crop.ratio if p.crop.ratio in [self.ratio.itemText(i) for i in range(self.ratio.count())] else "Custom")
            if self.ratio.currentText() == "Custom":
                self.custom_ratio.setText(p.crop.ratio)
            for widget, value in zip(self.crop_fields, p.crop.rect):
                widget.setValue(value)
            self.background.setCurrentText(p.crop.background if p.crop.background in ("transparent", "white", "black") else "custom")
            if self.background.currentText() == "custom":
                self.bg_color.setText(p.crop.background)
            self.scale_form.load(p.style)
            self.treatment.setCurrentText(p.treatment)
            self.treatment_color.setText(p.treatment_color)
            self.pure_confirmed.setChecked(p.pure_color_confirmed)
            self.display_low.setValue(p.display_low)
            self.display_high.setValue(p.display_high)
            current = self.candidate_list.currentRow()
            self.candidate_list.clear()
            for i, item in enumerate(p.candidates):
                self.candidate_list.addItem(f"{i + 1}. {item.get('text') or 'No length text'} · score {item['confidence']:.2f} · {item['line_rect'][2]} px" + (" · ignored" if item.get("ignored") else ""))
            self.candidate_list.setCurrentRow(max(0, current))
            self.inset_enabled.setChecked(p.inset.enabled)
            self.inset_circle.setChecked(p.inset.circular)
            for widget, value in zip(self.inset_fields, (p.inset.x, p.inset.y, p.inset.width)):
                widget.setValue(value)
            for widget, value in zip(self.inset_roi_fields, p.inset.roi.rect):
                widget.setValue(value)
            self.output_mode.setCurrentText(p.output.mode)
            for widget, value in ((self.output_scale, p.output.scale), (self.output_width, p.output.width_px), (self.output_mm, p.output.width_mm), (self.output_dpi, p.output.dpi), (self.font_pt, p.output.font_pt), (self.line_pt, p.output.line_pt), (self.panel_x, p.output.label_x), (self.panel_y, p.output.label_y)):
                widget.setValue(value)
            self.panel_label.setText(p.output.label)
            self.export_guides.setChecked(p.output.export_guides)
            self.suggestions.clear()
            if c.usable_x:
                box = bounds(p.crop, p.source_shape)
                self.suggestions.addItems([format_length(value) for value in suggestions((box[2] - box[0]) * c.usable_x)])
            self.update_tool_geometry()
        finally:
            self.syncing = False

    def commit(self, sync=True):
        doc = self.document
        if not doc:
            return
        doc.history.push(doc.project)
        doc.revision += 1
        if sync:
            self.sync_controls()
        self.render_timer.start()
        self.autosave_timer.start()
        self.settings.setValue("lastStyle", json.dumps(asdict(doc.project.style)))

    def request_render(self):
        if not self.document:
            return
        if self.render_busy:
            self.render_pending = True
            return
        doc, revision = self.document, self.document.revision
        project, rgba = deepcopy(doc.project), doc.rgba
        self.render_busy = True
        self.render_pending = False
        def render(progress):
            start = time.perf_counter()
            result = compose(rgba, project)
            original = compose(rgba, project, original=True)
            result_image, original_image = render_image(result), render_image(original)
            diff = change_view(original, result)
            mask = np.zeros((*rgba.shape[:2], 4), np.uint8)
            if project.masks:
                all_masks = build_masks(project, rgba.shape[:2])
                for layer, color in (("line", [50, 210, 255]), ("text", [255, 85, 180]), ("background", [255, 190, 55])):
                    mask_values = all_masks[layer] > 0
                    mask[mask_values] = [*color, 255]
            log.info("Preview pipeline %.3fs source=%s output=%s", time.perf_counter() - start, rgba.shape, result.base.shape)
            return result, result_image, original_image, diff, array_to_qimage(mask)
        def ready(data):
            self.render_busy = False
            if self.document is doc and doc.revision == revision:
                self.composition, self.result_image, self.original_image, self.diff_image, mask = data
                fit = self.needs_fit
                self.needs_fit = False
                self.canvas.set_context(doc.project, self.composition, array_to_qimage(doc.rgba), self.result_image, mask, fit)
                self.output_view.set_image(self.result_image, fit)
                self.update_comparison()
                self.populate_checks()
                self.update_status()
            if self.render_pending or self.document is not doc or doc.revision != revision:
                self.render_timer.start()
        def failed(message):
            self.render_busy = False
            self.notify(message, True)
            if self.render_pending:
                self.render_timer.start()
        self.submit(render, ready, on_error=failed)

    def update_status(self):
        if not self.document:
            return
        p = self.document.project
        try:
            box, k, size = output_geometry(p.crop, p.source_shape, p.output)
            sx, sy = p.calibration.usable_x, p.calibration.usable_y
            physical = f"{(box[2] - box[0]) * sx:g} nm" if sx else "x unknown"
            physical += " × " + (f"{(box[3] - box[1]) * sy:g} nm" if sy else "y unknown")
            self.crop_dimensions.setText(f"Output {size[0]} × {size[1]} px\nRetained bbox: {physical}\nUniform sampling factor {k:g}")
            view = self.view_tabs.currentWidget()
            zoom = view.transform().m11() * view.viewport().devicePixelRatioF() * 100
            self.statusBar().showMessage(f"Source {p.source_shape[1]}×{p.source_shape[0]}  |  Output {size[0]}×{size[1]}  |  View {zoom:.0f}%  |  {p.calibration.status}  |  sx {p.calibration.sx} nm/px")
        except ValueError as exc:
            self.notify(str(exc), True)

    def fit(self):
        self.view_tabs.currentWidget().fit()

    def actual_size(self):
        self.view_tabs.currentWidget().actual_size()

    def preview_actual(self):
        self.view_tabs.setCurrentIndex(1)
        self.output_view.actual_size()

    def toggle_masks(self, value):
        self.canvas.show_masks = value
        self.canvas.mask_item.setVisible(value and not self.before)

    def toggle_guides(self, value):
        self.canvas.show_guides = value
        self.canvas.viewport().update()

    def set_before(self, value):
        self.before = value
        self.update_comparison()

    def update_comparison(self, *_):
        if self.result_image is None:
            return
        image = self.original_image if self.before else self.diff_image if self.difference.isChecked() else self.result_image
        self.output_view.set_image(image)
        self.canvas.result_item.setPixmap(QPixmap.fromImage(image))
        self.canvas.before = self.before
        self.canvas.mask_item.setVisible(self.canvas.show_masks and not self.before and not self.difference.isChecked())
        self.canvas.viewport().update()

    def manual_calibration(self):
        p = self.require_document()
        factor = 1000 if self.cal_unit.currentText() == "μm/px" else 1
        sx = positive(self.sx.text(), "s_x") * factor if self.sx.text().strip() else None
        sy = positive(self.sy.text(), "s_y") * factor if self.sy.text().strip() else None
        square = self.square.isChecked()
        if square and sx:
            sy = sx
        if sx is None and sy is None:
            raise ValueError("Enter at least one sample-space calibration.")
        p.calibration.propose(sx, sy, "Manual sample calibration", square)
        self.commit()

    def endpoint_calibration(self):
        p = self.require_document()
        values = [widget.value() for widget in self.endpoint_fields]
        pts = [values[:2], values[2:]]
        nm = parse_length(self.known_length.text())
        scale = calibrate(nm, *pts)
        dx, dy = abs(pts[1][0] - pts[0][0]), abs(pts[1][1] - pts[0][1])
        square = self.square.isChecked()
        if square:
            sx = sy = scale
        elif dy < 1e-6:
            sx, sy = scale, None
        elif dx < 1e-6:
            sx, sy = None, scale
        else:
            raise ValueError("An oblique segment cannot determine two independent axes. Explicitly assume square pixels or use an axis-aligned segment.")
        p.calibration.endpoints, p.calibration.length_nm = pts, nm
        p.calibration.propose(sx, sy, "Endpoint measurement", square, {"endpoints": pts, "length_nm": nm, "rule": p.calibration.rule})
        self.commit()

    def threshold_change(self):
        p = self.require_document()
        p.calibration.conflict_threshold = self.conflict_threshold.value() / 100
        if p.calibration.conflicts():
            p.calibration.status = "Pending"
        self.commit()

    def confirm_calibration(self):
        p = self.require_document()
        p.calibration.confirm(resolve=self.resolve_conflict.isChecked())
        self.commit()
        self.notify("Calibration confirmed and saved in project state. Style edits do not require reconfirmation.")

    def selected_candidate(self):
        p = self.require_document()
        index = self.candidate_list.currentRow()
        if not 0 <= index < len(p.candidates):
            raise ValueError("Select a detected candidate first.")
        return p.candidates[index]

    def detect_source(self, region=None):
        self.require_document()
        doc, revision = self.document, self.document.revision
        def ready(result):
            doc.project.candidates = result["candidates"]
            self.commit()
            self.notify(result["warning"] or f"Found {len(result['candidates'])} segment candidates. Review text, endpoints and masks before confirmation.")
        self.submit(lambda progress: detect(doc.rgba, region, progress=progress), ready, lambda: self.document is doc and doc.revision == revision)

    def use_candidate(self):
        item = self.selected_candidate()
        p = self.document.project
        p.masks.extend(candidate_masks(item))
        self.invalidate_solid_confirmation(p)
        p.calibration.endpoints = deepcopy(item["endpoints"])
        if item["length_nm"]:
            p.calibration.length_nm = item["length_nm"]
            scale = calibrate(item["length_nm"], *item["endpoints"])
            p.calibration.propose(scale, scale if self.square.isChecked() else None, "OCR candidate (requires endpoint review)", self.square.isChecked(), item)
        else:
            p.calibration.status = "Pending"
        self.commit()
        self.tool.setCurrentText("Endpoints")
        self.canvas.centerOn(QPointF(*item["endpoints"][0]))
        self.notify("Candidate masks added. Correct length and effective endpoints, then use and confirm calibration.")

    def ignore_candidate(self):
        self.selected_candidate()["ignored"] = True
        self.commit()

    def morph(self, change):
        p = self.require_document()
        layer = self.mask_layer.currentText()
        p.mask_morph[layer] = max(-20, min(20, p.mask_morph[layer] + change))
        self.invalidate_solid_confirmation(p)
        self.commit()

    def invalidate_solid_confirmation(self, project):
        if project.treatment == "solid":
            project.treatment = "keep"
            project.pure_color_confirmed = False
            self.notify("Mask changed. Review the newly selected area and confirm its uniform background before solid clearing.")

    def clear_mask(self):
        p = self.require_document()
        layer = self.mask_layer.currentText()
        p.masks = [stroke for stroke in p.masks if stroke["layer"] != layer]
        p.mask_morph[layer] = 0
        self.commit()

    def apply_treatment(self):
        p = self.require_document()
        treatment = self.treatment.currentText()
        if treatment == "solid" and not self.pure_confirmed.isChecked():
            raise ValueError("Confirm a uniform annotation background, or use explicit opaque plate coverage.")
        color = self.treatment_color.text()
        if not QColor(color).isValid():
            raise ValueError("Invalid treatment color.")
        p.treatment, p.treatment_color, p.pure_color_confirmed = treatment, color, self.pure_confirmed.isChecked()
        self.commit()

    def crop_footer(self):
        p = self.require_document()
        y, ok = QInputDialog.getInt(self, "Crop independent footer", "First footer row in source coordinates (all rows below will be excluded):", int(p.source_shape[0] * .9), 1, p.source_shape[0] - 1)
        if ok:
            p.crop = Crop(rect=[0., 0., float(p.source_shape[1]), float(y)])
            self.commit()

    def apply_display(self):
        p = self.require_document()
        low, high = self.display_low.value(), self.display_high.value()
        array = display_rgba(self.document.source.pixels, low, high)
        array.setflags(write=False)
        p.display_low, p.display_high = low, high
        self.document.rgba = array
        self.commit()

    def ratio_value(self):
        if self.crop_kind.currentText() in ("square", "circle"):
            return 1.
        text = self.ratio.currentText()
        if text == "Free":
            return None
        if text == "Original" and self.document:
            return self.document.source.pixels.shape[1] / self.document.source.pixels.shape[0]
        if text == "Custom":
            text = self.custom_ratio.text()
        w, h = text.split(":")
        return positive(w, "Aspect width") / positive(h, "Aspect height")

    def update_tool_geometry(self):
        try:
            self.canvas.ratio = self.ratio_value()
            self.canvas.shape = self.crop_kind.currentText()
        except ValueError:
            self.notify("Aspect ratio must use positive W:H, e.g. 4:3.", True)

    def select_shape(self, *_):
        if not self.syncing:
            self.update_tool_geometry()

    def draw_crop(self):
        self.require_document()
        self.update_tool_geometry()
        kind = self.crop_kind.currentText()
        self.tool.setCurrentText("Crop polygon" if kind == "polygon" else "Crop freehand" if kind == "freehand" else "Draw crop")
        self.view_tabs.setCurrentIndex(0)

    def apply_crop(self):
        p = self.require_document()
        kind = self.crop_kind.currentText()
        rect = [control.value() for control in self.crop_fields]
        ratio = self.ratio_value()
        if ratio:
            rect[3] = rect[2] / ratio
        rect = constrain_rect(rect, p.source_shape)
        new = deepcopy(p.crop)
        if kind in ("polygon", "freehand"):
            old = bounds(p.crop, p.source_shape)
            if p.crop.kind not in ("polygon", "freehand"):
                raise ValueError("Draw a polygon/freehand region before editing its bounding geometry.")
            fx, fy = rect[2] / (old[2] - old[0]), rect[3] / (old[3] - old[1])
            new.points = [[rect[0] + (point[0] - old[0]) * fx, rect[1] + (point[1] - old[1]) * fy] for point in p.crop.points]
        new.kind, new.rect = kind, rect
        new.ratio = self.custom_ratio.text() if self.ratio.currentText() == "Custom" else self.ratio.currentText()
        bounds(new, p.source_shape)
        p.crop = new
        self.commit()

    def apply_background(self):
        p = self.require_document()
        value = self.background.currentText()
        if value == "custom":
            value = self.bg_color.text()
            if not QColor(value).isValid():
                raise ValueError("Invalid background color.")
        p.crop.background = value
        self.commit()

    def canvas_edit(self, kind, value):
        try:
            p = self.require_document()
            if kind == "detect-region":
                self.detect_source(value)
                return
            if kind == "crop":
                p.crop = value
            elif kind == "crop-rect":
                p.crop.kind, p.crop.rect = value
                p.crop.points = []
                p.crop.ratio = self.custom_ratio.text() if self.ratio.currentText() == "Custom" else self.ratio.currentText()
            elif kind == "crop-polygon":
                p.crop.kind, p.crop.points = value
                box = bounds(p.crop, p.source_shape)
                p.crop.rect = [box[0], box[1], box[2] - box[0], box[3] - box[1]]
            elif kind == "endpoints":
                p.calibration.endpoints = value
                p.calibration.status = "Pending"
            elif kind == "mask":
                p.masks.append(value)
                self.invalidate_solid_confirmation(p)
            elif kind == "measure":
                p.measurements.append(value)
                d, unit = distance(*value["points"], p.calibration.usable_x, p.calibration.usable_y)
                self.notify(f"Measurement: {d:.6g} {unit}. Stored in source coordinates; not exported by default.")
            elif kind == "protect":
                p.protected.append(value)
            elif kind == "scale-position":
                p.style.anchor = "custom"
                p.style.x, p.style.y = value
            elif kind == "inset-position":
                p.inset.x, p.inset.y = value
            elif kind == "inset-width":
                p.inset.width = value
            elif kind == "inset-rect":
                p.inset.roi.rect = value
                p.inset.roi.kind = "circle" if p.inset.circular else "rectangle"
                p.inset.enabled = True
            elif kind == "inset-roi":
                p.inset.roi = value
            self.commit()
        except Exception as exc:
            log.exception("Canvas edit failed")
            self.notify(str(exc), True)

    def draw_inset(self):
        p = self.require_document()
        p.inset.circular = self.inset_circle.isChecked()
        self.canvas.project = p
        self.tool.setCurrentText("Draw inset ROI")
        self.view_tabs.setCurrentIndex(0)

    def apply_inset(self):
        p = self.require_document()
        ins = deepcopy(p.inset)
        ins.enabled, ins.circular = self.inset_enabled.isChecked(), self.inset_circle.isChecked()
        ins.roi.rect = [widget.value() for widget in self.inset_roi_fields]
        if ins.circular:
            ins.roi.rect[3] = ins.roi.rect[2]
        ins.roi.kind = "circle" if ins.circular else "rectangle"
        bounds(ins.roi, p.source_shape)
        ins.x, ins.y, ins.width = [control.value() for control in self.inset_fields]
        p.inset = ins
        self.commit()

    def inset_style_dialog(self):
        p = self.require_document()
        dialog = QDialog(self)
        dialog.setWindowTitle("Inset scale style · shares source calibration")
        form = StyleForm()
        form.load(p.inset.style)
        layout = QVBoxLayout(dialog)
        layout.addWidget(form)
        button = self.button("Apply", lambda: (setattr(p.inset, "style", form.value()), self.commit(), dialog.accept()))
        layout.addWidget(button)
        dialog.exec()

    def clear_measures(self):
        self.require_document().measurements = []
        self.commit()

    def clear_protected(self):
        self.require_document().protected = []
        self.commit()

    def apply_style(self):
        self.require_document().style = self.scale_form.value()
        self.commit()

    def apply_preset(self):
        p = self.require_document()
        text = self.preset.currentText()
        p.style.color = "#000000" if text == "Black" else "#ffffff"
        p.style.plate = text == "White on dark plate"
        p.style.plate_color = "#000000"
        self.commit()

    def edit_length(self):
        p = self.require_document()
        text, ok = QInputDialog.getText(self, "Physical scale length", "Real-space length:", text=format_length(p.style.length_nm))
        if ok:
            try:
                p.style.length_nm = parse_length(text)
                self.commit()
            except ValueError as exc:
                self.notify(str(exc), True)

    def save_template(self):
        style = self.scale_form.value()
        path, _ = QFileDialog.getSaveFileName(self, "Save style template", "style.json", "JSON (*.json)")
        if path:
            p = self.require_document()
            if str(Path(path).resolve()).casefold() in {p.source_path.casefold(), str(p.reference.get("path", "")).casefold()}:
                raise ValueError("A style template cannot overwrite an input image.")
            atomic_json(path, {"style_template_version": 1, "style": asdict(style)})

    def load_template(self):
        p = self.require_document()
        path, _ = QFileDialog.getOpenFileName(self, "Load style template", "", "JSON (*.json)")
        if path:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if data.get("style_template_version") != 1:
                raise ValueError("Not a supported style template.")
            p.style = Style(**data["style"])
            self.commit()

    def copy_settings(self):
        p = self.require_document()
        dialog = QDialog(self)
        dialog.setWindowTitle("Copy selected settings")
        layout = QVBoxLayout(dialog)
        style = QCheckBox("Scale appearance and physical length")
        style.setChecked(True)
        output = QCheckBox("Output layout")
        calibration = QCheckBox("Calibration (explicit choice; independent images may differ)")
        for box in (style, output, calibration):
            layout.addWidget(box)
        def copy():
            self.copied = {key: deepcopy(getattr(p, key)) for key, checkbox in (("style", style), ("output", output), ("calibration", calibration)) if checkbox.isChecked()}
            dialog.accept()
        layout.addWidget(self.button("Copy", copy))
        dialog.exec()

    def paste_settings(self):
        p = self.require_document()
        if not self.copied:
            raise ValueError("Copy settings first.")
        for key, value in self.copied.items():
            if key == "calibration":
                p.calibration.propose(value.sx, value.sy, "Explicitly copied calibration; confirm for this source", value.square_pixels)
            else:
                setattr(p, key, deepcopy(value))
        self.commit()

    def apply_output(self):
        p = self.require_document()
        output = deepcopy(p.output)
        output.mode = self.output_mode.currentText()
        output.scale, output.width_px = self.output_scale.value(), round(self.output_width.value())
        output.width_mm, output.dpi = self.output_mm.value(), self.output_dpi.value()
        output.font_pt, output.line_pt = self.font_pt.value(), self.line_pt.value()
        output.label, output.label_x, output.label_y = self.panel_label.text(), self.panel_x.value(), self.panel_y.value()
        output.export_guides = self.export_guides.isChecked()
        output_geometry(p.crop, p.source_shape, output)
        p.output = output
        self.commit()

    def populate_checks(self):
        self.check_list.clear()
        if not self.composition:
            return
        for issue in self.composition.issues:
            self.check_list.addItem(f"{issue.severity.upper()} · {issue.message}")
            item = self.check_list.item(self.check_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, issue)
            if issue.severity == "error":
                item.setForeground(QColor("#c72138"))
            elif issue.severity == "warning":
                item.setForeground(QColor("#98621a"))

    def run_check(self):
        self.require_document()
        self.properties.setCurrentIndex(3)
        self.request_render()
        self.notify("Checks update from the current recipe. Select an issue to locate it. Warnings are advisory; errors block presentation export.")

    def locate_issue(self, item):
        issue = item.data(Qt.ItemDataRole.UserRole)
        if issue.rect:
            self.view_tabs.setCurrentIndex(1)
            rect = QRectF(*issue.rect).adjusted(-30, -30, 30, 30)
            self.output_view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def export_dialog(self, inset=False):
        p = self.require_document()
        kinds = [("png", ".png"), ("tiff", ".tif"), ("data-tiff", ".tif"), ("svg", ".svg")]
        kind, suffix = kinds[self.export_kind.currentIndex()]
        path, _ = QFileDialog.getSaveFileName(self, "Export independent result", str(Path(p.source_path).with_name(Path(p.source_path).stem + ("_inset" if inset else "_edited") + suffix)), f"Output (*{suffix})")
        if path:
            if not Path(path).suffix:
                path += suffix
            self.start_export(path, kind, inset)

    def start_export(self, path, kind="png", inset=False):
        doc = self.document
        project = inset_project(doc.project) if inset else deepcopy(doc.project)
        self.submit(lambda progress: export_file(path, doc.source.pixels, doc.rgba, project, kind, progress), lambda outputs: self.notify("Exported: " + " · ".join(outputs)))

    def clipboard(self):
        doc = self.document
        self.require_document()
        project = deepcopy(doc.project)
        def render(progress):
            comp = compose(doc.rgba, project)
            errors = [i.message for i in comp.issues if i.severity == "error"]
            if errors:
                raise ValueError("Clipboard blocked by export check: " + "; ".join(errors))
            return render_image(comp)
        def ready(image):
            QApplication.clipboard().setImage(image)
            self.notify(f"Copied finished {image.width()} × {image.height()} pixel image, independent of view zoom.")
        self.submit(render, ready)

    def undo(self, direction):
        # Let focused text controls keep normal text undo/redo behavior.
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit) and focus.hasFocus():
            focus.undo() if direction < 0 else focus.redo()
            return
        if not self.document:
            return
        doc = self.document
        doc.project = doc.history.step(direction)
        doc.rgba = display_rgba(doc.source.pixels, doc.project.display_low, doc.project.display_high)
        doc.rgba.setflags(write=False)
        doc.revision += 1
        self.sync_controls()
        self.render_timer.start()
        self.autosave_timer.start()

    def reset(self):
        self.require_document()
        self.document.project = project_for(self.document.source)
        p = self.document.project
        self.document.rgba = display_rgba(self.document.source.pixels, p.display_low, p.display_high)
        self.document.rgba.setflags(write=False)
        self.commit()

    def autosave(self):
        if self.document:
            try:
                path = self.recovery_dir / (self.document.project.document_id + ".recovery.json")
                save_project(self.document.project, path, write_masks=False)
            except Exception as exc:
                log.exception("Autosave failed")
                self.notify(f"Autosave failed: {exc}", True)

    def save_dialog(self, save_as=False):
        p = self.require_document()
        path = "" if save_as else self.document.path
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save project", str(Path(p.source_path).with_suffix(".micro.json")), "Project (*.json)")
        if path:
            self.save_to(path)

    def save_to(self, path):
        doc = self.document
        project = deepcopy(self.require_document())
        def ready(_):
            doc.path = path
            self.notify("Project saved with masks and source hashes: " + path)
        self.submit(lambda progress: save_project(project, path), ready)

    def open_project_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "Project (*.json *.bak)")
        if path:
            self.open_project_path(path)

    def open_project_path(self, path):
        project = load_project(path)
        if not Path(project.source_path).exists():
            replacement, _ = QFileDialog.getOpenFileName(self, "Source missing · Relink original (SHA-256 must match)", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff)")
            if not replacement:
                self.notify("Source missing. Project remains on disk; use Open project again to relink.", True)
                return
            relink_source(project, replacement)
        saved_path = "" if ".recovery.json" in Path(path).name else path
        self.submit(lambda progress: read_source(project.source_path), lambda source: self.add_source(source, project, saved_path))

    def recover_dialog(self):
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Recover parameter autosave / valid backup", str(self.recovery_dir), "Recovery (*.json *.bak)")
        if path:
            self.open_project_path(path)

    def relink_dialog(self):
        p = self.require_document()
        path, _ = QFileDialog.getOpenFileName(self, "Relink source · exact file identity required", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff)")
        if path:
            relink_source(p, path)
            self.commit()

    def reference_dialog(self):
        self.require_document()
        path, _ = QFileDialog.getOpenFileName(self, "Calibration reference (same field of view)", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff)")
        if not path:
            return
        doc, revision = self.document, self.document.revision
        def ready(source):
            dialog = ReferenceDialog(self, source, doc)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if self.document is not doc or doc.revision != revision:
                    self.notify("Source changed while reviewing reference; pairing was not applied.", True)
                    return
                result = dialog.result_data
                doc.project.reference = result
                ref_sx = result["sx_reference"]
                square = result["square_pixels"]
                doc.project.calibration.propose(ref_sx / result["r"], ref_sx / result["r"] if square else None, "Content-validated reference", square, result)
                self.commit()
                self.notify("Pairing and reference evidence saved. Review and confirm the transferred calibration.")
        self.submit(lambda progress: read_source(path), ready, lambda: self.document is doc and doc.revision == revision)

    def open_examples(self):
        from .examples import generate_examples
        folder = runtime_dir("examples")
        generate_examples(folder)
        self.load_image(folder / "SYNTHETIC_clean.png")
        self.notify("Synthetic examples generated; these are not real SEM/TEM validation images.")

    def closeEvent(self, event):
        # Finish write jobs before Python/Qt object destruction. No hidden loss of exports.
        self.autosave()
        if self.jobs:
            self.notify("Finishing background work before closing…")
            event.ignore()
            QTimer.singleShot(300, self.close)
            return
        event.accept()


class PointView(ImageView):
    picked = Signal(object)

    def __init__(self):
        super().__init__()
        self.markers = []
        self.endpoints = []

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            p = self.mapToScene(event.position().toPoint())
            self.picked.emit([p.x(), p.y()])
            return
        super().mousePressEvent(event)

    def drawForeground(self, painter, rect):
        from PySide6.QtGui import QPen
        painter.setPen(QPen(QColor("#ff476a"), 0))
        for index, point in enumerate(self.markers):
            radius = 5 / self.transform().m11()
            painter.drawEllipse(QPointF(*point), radius, radius)
            painter.drawText(QPointF(point[0] + radius, point[1]), str(index + 1))
        if self.endpoints:
            painter.setPen(QPen(QColor("#ffce50"), 0))
            painter.drawLine(QPointF(*self.endpoints[0]), QPointF(*self.endpoints[1]))
            for point in self.endpoints:
                painter.drawEllipse(QPointF(*point), 5 / self.transform().m11(), 5 / self.transform().m11())


class ReferenceDialog(QDialog):
    def __init__(self, owner, reference, document):
        super().__init__(owner)
        self.owner, self.reference, self.document = owner, reference, document
        self.setWindowTitle("Calibration reference · verify content correspondence")
        self.resize(1150, 830)
        self.result_data = None
        self.registration = None
        self.candidates = []
        self.generation = 0
        self.rgba = display_rgba(reference.pixels, *self._window(reference.pixels))
        self.warped = None
        self.flicker_state = False
        self.timer = QTimer(self)
        self.timer.setInterval(450)
        self.timer.timeout.connect(self.flicker_tick)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Reference → Source: Ctrl-click corresponding points in each view, in matching order. At least 3 spread-out pairs. Pan normally; wheel zooms."))
        self.views = QTabWidget()
        pair_widget = QWidget()
        pair_layout = QHBoxLayout(pair_widget)
        self.ref_view, self.work_view = PointView(), PointView()
        self.ref_view.set_image(array_to_qimage(self.rgba))
        self.work_view.set_image(array_to_qimage(document.rgba))
        for name, view in (("Reference (with scale)", self.ref_view), ("Source (clean/native grid)", self.work_view)):
            container = QWidget()
            inner = QVBoxLayout(container)
            inner.addWidget(QLabel(name))
            inner.addWidget(view)
            pair_layout.addWidget(container)
        self.ref_view.picked.connect(lambda point: self.add_point(self.ref_view, point))
        self.work_view.picked.connect(lambda point: self.add_point(self.work_view, point))
        self.views.addTab(pair_widget, "Correspondence points")
        self.overlap = ImageView()
        self.views.addTab(self.overlap, "Registered reference / source overlap")
        layout.addWidget(self.views, 1)
        layout.addWidget(row(owner.button("Automatic content registration", self.auto_register), owner.button("Verify manual point pairs", self.manual_register), owner.button("Clear points", self.clear_points)))
        self.flicker = QCheckBox("Flicker registered reference / source (pair check only)")
        self.flicker.toggled.connect(self.toggle_flicker)
        layout.addWidget(self.flicker)
        self.status = QLabel("Pair not yet verified. File dimensions and names are not matching evidence.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        bottom = QHBoxLayout()
        controls = QFormLayout()
        self.reference_sx = QLineEdit(str(reference.metadata.get("sx", "")))
        self.calibration_method = reference.metadata.get("calibration_source", "Manual reference nm/px")
        self.reference_sx.textEdited.connect(lambda _: setattr(self, "calibration_method", "Manual reference nm/px"))
        self.reference_sx.setPlaceholderText("Reference nm/px, if known")
        controls.addRow("Reference s_x (nm/px)", self.reference_sx)
        self.square = QCheckBox("Assume square pixels in source and reference")
        controls.addRow(self.square)
        self.length = QLineEdit("50 nm")
        self.ends = [number(0), number(0), number(250), number(0)]
        controls.addRow("Reference bar length", self.length)
        controls.addRow("Reference p1 x / y", row(*self.ends[:2]))
        controls.addRow("Reference p2 x / y", row(*self.ends[2:]))
        controls.addRow(owner.button("Compute reference calibration from endpoints", self.compute_reference_scale))
        bottom.addLayout(controls)
        ocr_layout = QVBoxLayout()
        ocr_layout.addWidget(owner.button("Detect reference scale + OCR", self.detect_reference))
        self.list = QListWidget()
        ocr_layout.addWidget(self.list)
        ocr_layout.addWidget(owner.button("Use selected reference candidate", self.use_reference_candidate))
        bottom.addLayout(ocr_layout)
        layout.addLayout(bottom)
        self.transfer = owner.button("Transfer calibration as pending", self.transfer_calibration)
        self.transfer.setEnabled(False)
        layout.addWidget(self.transfer)
        QTimer.singleShot(0, lambda: (self.ref_view.fit(), self.work_view.fit()))

    @staticmethod
    def _window(array):
        return (0., 255.) if array.dtype == np.uint8 else (float(array.min()), max(float(array.min()) + 1., float(array.max())))

    def add_point(self, view, point):
        view.markers.append(point)
        view.viewport().update()
        self.generation += 1
        self.registration = None
        self.transfer.setEnabled(False)
        self.status.setText(f"Manual points: reference {len(self.ref_view.markers)}, source {len(self.work_view.markers)}. Verify matching pairs to transfer.")

    def clear_points(self):
        self.ref_view.markers, self.work_view.markers = [], []
        self.ref_view.viewport().update()
        self.work_view.viewport().update()
        self.generation += 1
        self.registration = None
        self.transfer.setEnabled(False)

    def auto_register(self):
        self.start_registration(None)

    def manual_register(self):
        self.start_registration((deepcopy(self.ref_view.markers), deepcopy(self.work_view.markers)))

    def start_registration(self, points):
        self.generation += 1
        generation = self.generation
        self.registration = None
        self.transfer.setEnabled(False)
        self.status.setText("Validating image-content correspondences…")
        def ready(result):
            self.registration = result
            self.transfer.setEnabled(True)
            self.status.setText(f"Verified r={result['r']:.8g} · {result['inliers']} inliers · median error {result['median_error_px']:.3g} source px · patch correlation {result['correlation']:.3f}. Inspect overlap and reference scale, then transfer.")
            shape = self.document.rgba.shape
            self.warped = cv2.warpAffine(self.rgba, np.array(result["matrix"]), (shape[1], shape[0]))
            blend = self.document.rgba.copy()
            valid = self.warped[..., 3] > 0
            blend[valid] = ((blend[valid].astype(float) + self.warped[valid].astype(float)) / 2).astype(np.uint8)
            self.overlap.set_image(array_to_qimage(blend), fit=True)
            self.views.setCurrentIndex(1)
        self.owner.submit(lambda progress: register(self.rgba, self.document.rgba, points, progress), ready,
                          lambda: self.isVisible() and generation == self.generation,
                          lambda message: self.status.setText("Unpaired / pending: " + message))

    def toggle_flicker(self, enabled):
        self.timer.start() if enabled else self.timer.stop()
        if not enabled and self.warped is not None:
            blend = self.document.rgba.copy()
            valid = self.warped[..., 3] > 0
            blend[valid] = ((blend[valid].astype(float) + self.warped[valid].astype(float)) / 2).astype(np.uint8)
            self.overlap.set_image(array_to_qimage(blend))

    def flicker_tick(self):
        if self.warped is not None:
            self.flicker_state = not self.flicker_state
            self.overlap.set_image(array_to_qimage(self.warped if self.flicker_state else self.document.rgba))

    def detect_reference(self):
        def ready(result):
            self.candidates = result["candidates"]
            self.list.clear()
            self.list.addItems([f"{item.get('text') or 'No text'} · {item['line_rect'][2]} px · score {item['confidence']:.2f}" for item in self.candidates])
            self.list.setCurrentRow(0)
            if result["warning"]:
                self.status.setText(result["warning"])
        self.owner.submit(lambda progress: detect(self.rgba, progress=progress), ready, self.isVisible)

    def use_reference_candidate(self):
        index = self.list.currentRow()
        if not 0 <= index < len(self.candidates):
            raise ValueError("Select a reference candidate.")
        item = self.candidates[index]
        for widget, value in zip(self.ends, sum(item["endpoints"], [])):
            widget.setValue(value)
        if item.get("length_nm"):
            self.length.setText(format_length(item["length_nm"]))
            self.compute_reference_scale()
        self.ref_view.endpoints = deepcopy(item["endpoints"])
        self.ref_view.viewport().update()
        self.status.setText("Review yellow reference endpoints numerically (solid edges / tick centers). Red numbered points are correspondence pairs.")

    def compute_reference_scale(self):
        values = [widget.value() for widget in self.ends]
        dx, dy = values[2] - values[0], values[3] - values[1]
        if abs(dy) > .01 and not self.square.isChecked():
            raise ValueError("A horizontal reference is required without an explicit square-pixel assumption.")
        self.reference_sx.setText(f"{calibrate(parse_length(self.length.text()), values[:2], values[2:]):.12g}")
        self.calibration_method = "Reference endpoint measurement"

    def transfer_calibration(self):
        if not self.registration:
            raise ValueError("Verify correspondence first.")
        sx = positive(self.reference_sx.text(), "Reference nm/px")
        self.result_data = {**self.registration, "path": self.reference.path, "sha256": self.reference.sha256, "sx_reference": sx,
                            "square_pixels": self.square.isChecked(), "scale_endpoints": [[self.ends[0].value(), self.ends[1].value()], [self.ends[2].value(), self.ends[3].value()]],
                            "scale_text": self.length.text(), "note": "Source pixels remain on their native grid; reference used only for validation/calibration."}
        self.result_data["calibration_method"] = self.calibration_method
        self.accept()

    def done(self, result):
        self.timer.stop()
        self.generation += 1
        super().done(result)
