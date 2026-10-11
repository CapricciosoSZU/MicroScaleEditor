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
from .model import load_project, file_hash, Crop, Project
from .rendering import compose, data_crop, export_file
from .runtime import frozen, runtime_dir, user_data_dir


def run_self_test(app, output_dir, test_images=None):
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("Use an empty directory for --self-test to avoid stale output evidence.")
    report = {"frozen": frozen(), "executable": sys.executable, "user_data_dir": str(user_data_dir()), "synthetic_inputs_only": not bool(test_images), "checks": []}
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
        available = window.screen().availableGeometry()
        frame = window.frameGeometry()
        check("Startup centered within usable screen", available.contains(frame) and (frame.center() - available.center()).manhattanLength() <= 2)
        check("Same as source is the default GUI export", window.export_kind.currentText() == "Same as source (original bit depth)")
        check("Velox-style is the default for new images", window.document.project.style.outline and window.document.project.style.anchor == "bottom-left" and window.preset.currentText() == "Velox-style")
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
        legacy = p.to_dict()
        legacy["style"]["text_position"] = legacy["inset"]["style"]["text_position"] = "below"
        normalized = Project.from_dict(legacy)
        check("Legacy main/inset labels normalize above", normalized.style.text_position == normalized.inset.style.text_position == "above")
        normalized.style.text_position = "below"
        fixed = compose(window.document.rgba, normalized)
        fixed_bar = next(v for v in fixed.primitives if v.get("role") == "scale-bar")
        fixed_text = next(v for v in fixed.primitives if v.get("role") == "scale-label")
        check("Label stays above regardless of legacy state", fixed_text["y"] < fixed_bar["rect"][1])
        window.start_export(str(output_dir / "synthetic-result.png"))
        settle()
        check("PNG export", (output_dir / "synthetic-result.png").is_file())
        window.start_export(str(output_dir / "synthetic-result.svg"), "svg")
        settle()
        svg = (output_dir / "synthetic-result.svg").read_text(encoding="utf-8")
        check("SVG vector text and bar", "scale-bar" in svg and "<text" in svg)
        check("SVG retains editable outlined lettering", 'paint-order="stroke fill"' in svg and 'stroke="#000000"' in svg)
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
        project.output.rotation_deg = 90
        rotated_outputs = export_file(output_dir / "quarter-turn-data.tif", source.pixels,
            display_rgba(source.pixels, project.display_low, project.display_high), project, "data-tiff")
        check("Quarter-turn TIFF preserves exact uint16 samples", np.array_equal(tifffile.imread(rotated_outputs[0]), np.rot90(data, -1)))
        for dtype, channels, predictor in ((np.uint8, 1, False), (np.uint16, 1, True), (np.uint8, 4, False), (np.float32, 1, True)):
            shape = (64, 96) if channels == 1 else (64, 96, channels)
            rng = np.random.default_rng(251)
            original = rng.normal(2000, 3000, shape).astype(dtype) if dtype == np.float32 else rng.integers(0, np.iinfo(dtype).max, shape, dtype=dtype)
            compressed = output_dir / f"synthetic-lzw-{np.dtype(dtype)}-{channels}.tif"
            tifffile.imwrite(compressed, original, compression="lzw", predictor=predictor, photometric="minisblack" if channels == 1 else "rgb")
            decoded = read_source(compressed)
            check(f"Bundled LZW {np.dtype(dtype)} {channels}-channel exact decode", decoded.pixels.dtype == original.dtype and np.array_equal(decoded.pixels, original))
        for dtype, suffix in ((np.uint16, ".png"), (np.float32, ".tif")):
            values = np.arange(120 * 180, dtype=dtype).reshape(120, 180)
            if dtype == np.float32:
                values /= np.float32(37.13)
            path = output_dir / ("synthetic-native-precision" + suffix)
            if suffix == ".png":
                import cv2
                ok, encoded = cv2.imencode(suffix, values)
                if not ok:
                    raise OSError("Cannot encode synthetic PNG")
                encoded.tofile(str(path))
            else:
                tifffile.imwrite(path, values)
            native = read_source(path)
            recipe = project_for(native)
            recipe.calibration.propose(.2, .2, "Synthetic verification only", True)
            recipe.calibration.confirm()
            recipe.style.enabled = True
            recipe.style.length_nm = 5
            recipe.output.scale = 2
            preview = display_rgba(native.pixels, recipe.display_low, recipe.display_high)
            outputs = export_file(output_dir / ("native-precision-figure" + suffix), native.pixels, preview, recipe, "source")
            result = read_source(outputs[0]).pixels
            expected, _, _ = data_crop(native.pixels, recipe)
            check(f"2x annotated {np.dtype(dtype)} source-format export retains sample precision", result.dtype == dtype and result.shape == (240, 360) and np.array_equal(result[:100], expected[:100]) and np.unique(result[:100]).size > 256 and not np.array_equal(result, expected))
        window.canvas_edit("crop-rect", ["rectangle", [100, 100, 700, 600]])
        settle()
        check("Cropping retains confirmed calibration and scale", p.calibration.status == "Confirmed" and window.composition.scale_length_px == 25)
        window.rotate_image(90)
        settle()
        check("Quarter-turn GUI preview swaps dimensions", window.result_image.width() == 600 and window.result_image.height() == 700)
        window.set_rotation(17.5)
        settle()
        check("Custom-angle horizontal bar fits rotated crop", window.composition.scale_length_px == 25 and not any(i.severity == "error" for i in window.composition.issues))
        window.start_export(str(output_dir / "custom-rotation.png"))
        settle()
        check("Rotated PNG equals preview", np.array_equal(read_source(output_dir / "custom-rotation.png").pixels, qimage_to_array(window.result_image)))
        window.save_to(str(output_dir / "rotation-project.json"))
        settle()
        check("Rotation saved in project", load_project(output_dir / "rotation-project.json").output.rotation_deg == 17.5)
        window.canvas_edit("endpoints", [[100., 100.], [350., 100.]])
        settle()
        check("Pending scale has actionable visible feedback", window.composition.scale_rect is None and "endpoints changed" in window.scale_state.text() and "endpoints changed" in window.notice.text())
        window.known_length.setText("50 nm")
        window.square.setChecked(True)
        window.endpoint_calibration()
        window.confirm_calibration()
        settle()
        original_font = p.style.font_size
        original_size = window.result_image.size()
        window.set_output_resolution(2)
        settle()
        check("GUI resolution preset doubles image and calibrated bar", window.composition.scale_length_px == 50 and p.style.font_size == original_font * 2 and window.result_image.size() == original_size * 2 and p.output.scale == 2)
        window.set_output_resolution(1)
        settle()
        window.properties.setCurrentIndex(2)
        window.view_tabs.setCurrentIndex(1)
        window.output_view.fit()
        window.notice.setText("Standalone verification passed. Synthetic input only; original pixels preserved.")
        app.processEvents()
        window.grab().save(str(output_dir / "packaged-gui.png"))
        if test_images is not None:
            report["external_images"] = []
            for dataset_index, folder in enumerate(test_images):
                records = validate_external_images(window, settle, folder, output_dir / "local-images" / f"dataset-{dataset_index + 1}")
                for record in records:
                    record["dataset_index"] = dataset_index + 1
                report["external_images"].extend(records)
            check("All supplied local images passed", all(item["status"] == "passed" for item in report["external_images"]))
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


def validate_external_images(window, settle, input_dir, output_dir):
    """Read-only local corpus checks. Filenames and results are never uploaded."""
    from PIL import Image
    input_dir = input_dir.resolve()
    candidates = [input_dir] if input_dir.is_file() else input_dir.rglob("*")
    files = sorted(p for p in candidates if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".png", ".jpg", ".jpeg"})
    if not files:
        raise ValueError("No supported images found in the supplied test folder.")
    if input_dir.is_file():
        input_dir = input_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    ocr_seen = set()
    for index, path in enumerate(files):
        record = {"file": str(path.relative_to(input_dir)), "checks": []}
        def require(name, condition):
            if not condition:
                raise AssertionError(name)
            record["checks"].append(name)
        try:
            initial_hash = file_hash(path)
            # Bound the diagnostic process's memory; this is a fresh test window.
            window.document = None
            window.image_list.clear()
            window.documents.clear()
            window.load_image(path)
            settle()
            doc = window.document
            require("GUI loaded requested source", doc is not None and Path(doc.source.path) == path and window.composition is not None)
            source, p = doc.source, doc.project
            record.update(shape=list(source.pixels.shape), dtype=str(source.pixels.dtype))
            require("Source array is read-only", not source.pixels.flags.writeable)
            with Image.open(path) as independent:
                reference = np.asarray(independent)
                if independent.mode == "P":
                    reference = np.asarray(independent.convert("RGBA" if "transparency" in independent.info else "RGB"))
            require("Independent Pillow decoder agrees", source.pixels.dtype == reference.dtype and np.array_equal(source.pixels, reference))
            compression = "PNG/JPEG"
            if path.suffix.lower() in {".tif", ".tiff"}:
                with tifffile.TiffFile(path) as tif:
                    compression = tif.pages[0].compression.name
            record["compression"] = compression
            if compression not in ocr_seen:
                window.detect_source()
                settle()
                require("OCR worker completed", "#ff8392" not in window.notice.styleSheet())
                record["ocr_candidates"] = len(p.candidates)
                record["ocr_is_calibration_ground_truth"] = False
                ocr_seen.add(compression)
            png = output_dir / f"image-{index:03d}.png"
            window.start_export(str(png))
            settle()
            require("GUI PNG export", png.is_file() and read_source(png).pixels.shape == doc.rgba.shape)
            project_file = output_dir / f"image-{index:03d}.json"
            window.save_to(str(project_file))
            settle()
            require("Project save and reload", load_project(project_file).to_dict() == p.to_dict())
            cropped = deepcopy(p)
            h, w = source.pixels.shape[:2]
            x, y, cw, ch = w // 8, h // 8, w // 2, h // 2
            cropped.crop = Crop(rect=[x, y, cw, ch])
            cropped.style.enabled = False
            outputs = export_file(output_dir / f"image-{index:03d}-crop.tif", source.pixels, doc.rgba, cropped, "data-tiff")
            crop = tifffile.imread(outputs[0])
            require("Native data crop exact", crop.dtype == source.pixels.dtype and np.array_equal(crop, source.pixels[y:y + ch, x:x + cw]))
            outputs = export_file(output_dir / f"image-{index:03d}-source{path.suffix}", source.pixels, doc.rgba, cropped, "source")
            figure = read_source(outputs[0]).pixels
            require("Source-format crop retains file type and bit depth", Path(outputs[0]).suffix == path.suffix.lower() and figure.dtype == source.pixels.dtype and figure.shape == crop.shape)
            if path.suffix.lower() not in {".jpg", ".jpeg"}:
                require("Lossless source-format crop retains exact samples", np.array_equal(figure, crop))
            require("Original file unchanged", file_hash(path) == initial_hash)
            record["status"] = "passed"
        except Exception:
            record["status"] = "failed"
            record["traceback"] = traceback.format_exc()
            record["ui_message"] = window.notice.text()
        records.append(record)
        (output_dir / "report.json").write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.info("Local image verification %s/%s: %s", index + 1, len(files), record["status"])
    return records
