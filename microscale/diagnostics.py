"""Repeatable integration check executed by the actual frozen application."""
from pathlib import Path
from copy import deepcopy
import json
import logging
import sys
import time
import traceback

import numpy as np
import tifffile
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .gui import MainWindow
from .image_io import read_source, project_for, display_rgba, qimage_to_array
from .model import load_project, file_hash, Crop
from .rendering import compose, export_file
from .runtime import frozen, runtime_dir, user_data_dir


def run_self_test(app, output_dir):
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("Use an empty directory for --self-test to avoid stale output evidence.")
    report = {"frozen": frozen(), "executable": sys.executable, "user_data_dir": str(user_data_dir()), "synthetic": True, "checks": []}
    window = MainWindow()
    window.settings = QSettings(str(output_dir / "test-settings.ini"), QSettings.Format.IniFormat)
    window.recovery_dir = output_dir / "recovery"
    window.show()
    started = time.perf_counter()
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report["checks"].append(name)
    def settle():
        deadline = time.monotonic() + 75
        while window.jobs or window.render_busy or window.render_timer.isActive():
            app.processEvents()
            time.sleep(.01)
            if time.monotonic() > deadline:
                raise TimeoutError("Packaged background work timed out: " + window.notice.text())
        app.processEvents()
    try:
        window.open_examples()
        settle()
        check("GUI startup and persistent synthetic examples", window.document is not None and window.composition is not None)
        example_dir = runtime_dir("examples")
        check("Examples outside extraction directory", str(getattr(sys, "_MEIPASS", "not-frozen")) not in str(example_dir))
        window.load_image(example_dir / "SYNTHETIC_50nm_250px.png")
        settle()
        p = window.document.project
        initial_hash = file_hash(p.source_path)
        window.detect_source()
        settle()
        candidates = p.candidates
        index = next((i for i, c in enumerate(candidates) if c.get("length_nm") == 50 and abs(c["line_rect"][2] - 250) < 3), None)
        check("Bundled local OCR recognizes 50 nm / 250 px", index is not None)
        window.candidate_list.setCurrentRow(index)
        window.square.setChecked(True)
        window.use_candidate()
        window.endpoint_calibration()
        window.confirm_calibration()
        settle()
        window.treatment.setCurrentText("plate")
        window.apply_treatment()
        window.scale_form.enabled.setChecked(True)
        window.scale_form.length.setText("5 nm")
        window.apply_style()
        settle()
        check("Scale geometry 25 px", abs(window.composition.scale_length_px - 25) < .1)
        window.start_export(str(output_dir / "synthetic-result.png"))
        settle()
        check("PNG export", (output_dir / "synthetic-result.png").is_file())
        window.start_export(str(output_dir / "synthetic-result.svg"), "svg")
        settle()
        svg = (output_dir / "synthetic-result.svg").read_text(encoding="utf-8")
        check("SVG vector text and bar", "scale-bar" in svg and "<text" in svg)
        window.clipboard()
        settle()
        check("Full-resolution clipboard", QApplication.clipboard().image().size() == window.result_image.size())
        window.save_to(str(output_dir / "portable-project.json"))
        settle()
        restored = load_project(output_dir / "portable-project.json")
        check("Project save/load and masks", restored.to_dict() == p.to_dict() and bool(restored.masks))
        window.autosave()
        check("Recovery record", (window.recovery_dir / (p.document_id + ".recovery.json")).is_file())
        check("Input unchanged", file_hash(p.source_path) == initial_hash)
        source = read_source(example_dir / "SYNTHETIC_16bit_OME.tif")
        project = project_for(source)
        project.crop = Crop(rect=[17, 23, 210, 150])
        outputs = export_file(output_dir / "native-data.tif", source.pixels, display_rgba(source.pixels, project.display_low, project.display_high), project, "data-tiff")
        data = tifffile.imread(outputs[0])
        check("16-bit TIFF exact crop", data.dtype == np.uint16 and np.array_equal(data, source.pixels[23:173, 17:227]))
        window.properties.setCurrentIndex(2)
        window.view_tabs.setCurrentIndex(1)
        window.output_view.fit()
        window.notice.setText("Standalone verification passed. Synthetic input only; original pixels preserved.")
        app.processEvents()
        window.grab().save(str(output_dir / "packaged-gui.png"))
        report["status"] = "passed"
        code = 0
    except Exception:
        report["status"] = "failed"
        report["traceback"] = traceback.format_exc()
        report["ui_message"] = window.notice.text()
        logging.exception("Packaged self-test failed")
        code = 1
    finally:
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        (output_dir / "self-test.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        # Close only after this check's own queued jobs have completed.
        try:
            settle()
        finally:
            window.close()
            app.processEvents()
    return code
