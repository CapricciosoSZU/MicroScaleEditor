from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest
import tifffile

from microscale.geometry import calibrate, parse_length, format_length, crop_mask, distance, polygon_valid, output_geometry
from microscale.image_io import array_to_qimage, display_rgba, qimage_to_array, read_source, project_for, write_png
from microscale.model import Crop, History, load_project, save_project, file_hash, relink_source, atomic_json
from microscale.rendering import compose, render_image, export_file, inset_project, data_crop, change_view
from microscale.detection import register, detect, local_ocr, build_masks


def measured_raster_width(comp):
    bar = next(p for p in comp.primitives if p.get("role") == "scale-bar")
    x, y, w, h = bar["rect"]
    raster = qimage_to_array(render_image(comp))
    scan = raster[int(y + h / 2), :, :3]
    selected = np.all(scan == 255, axis=1)
    # Pixel-center/AA endpoint tolerance: interior white run within 2 pixels.
    return int(selected.sum()), w


def test_calibration_raster_crop_and_resample(black_project):
    source, p = black_project
    assert calibrate(50, (0, 0), (250, 0)) == .2
    rgba = display_rgba(source.pixels, 0, 255)
    comp = compose(rgba, p)
    observed, geometry = measured_raster_width(comp)
    assert geometry == 25
    assert abs(observed - 25) <= 1
    p.crop.rect = [20, 20, 400, 300]
    observed, geometry = measured_raster_width(compose(rgba, p))
    assert geometry == 25 and abs(observed - 25) <= 1
    p.output.scale = 2
    result = compose(rgba, p)
    observed, geometry = measured_raster_width(result)
    assert geometry == 50 and abs(observed - 50) <= 1
    assert result.base.shape[:2] == (600, 800)


@pytest.mark.parametrize("text,nm", [("0.5 μm", 500), ("0.5µm", 500), (".5um", 500), ("10 Å", 1), ("5nm", 5), ("2.5e-1 nm", .25)])
def test_units(text, nm):
    assert parse_length(text) == nm
    assert parse_length(format_length(nm)) == nm


@pytest.mark.parametrize("text", ["0 nm", "-5 nm", "nan nm", "inf nm", "nm", "1/nm", "5 nm⁻¹", "5 Å^-1", "5 nm-1", "5 px", "1e999 nm"])
def test_invalid_lengths(text):
    with pytest.raises(ValueError):
        parse_length(text)


def test_zero_endpoints_and_directions():
    with pytest.raises(ValueError):
        calibrate(5, [0, 0], [0, 0])
    assert distance([0, 0], [25, 0], .2, None) == (5, "nm")
    assert distance([0, 0], [0, 25], .2, None) == (25, "px")
    assert distance([0, 0], [3, 4], .2, .4)[0] == pytest.approx(math.hypot(.6, 1.6))


@pytest.mark.parametrize("kind", ["rectangle", "square", "circle", "ellipse", "polygon", "freehand"])
def test_all_crops_output_alpha_and_native_pixels(black_project, tmp_path, kind):
    source, p = black_project
    p.style.enabled = False
    p.crop = Crop(kind=kind, rect=[50, 50, 200, 200 if kind in ("square", "circle") else 150], points=[[50, 50], [250, 70], [210, 200], [80, 160]])
    rgba = display_rgba(source.pixels, 0, 255)
    outputs = export_file(tmp_path / f"{kind}.png", source.pixels, rgba, p)
    decoded = read_source(outputs[0]).pixels
    expected = crop_mask(p.crop, source.pixels.shape)
    assert np.array_equal(decoded[..., 3], expected.astype(np.uint8) * 255)
    assert np.all(decoded[expected, :3] == 0)


def test_invalid_polygon():
    assert not polygon_valid([[0, 0], [100, 100], [0, 100], [100, 0]])
    assert not polygon_valid([[0, 0], [10, 10], [20, 20]])


def test_pair_scale_footer_offsets_and_different_fov(examples):
    ref = read_source(examples / "SYNTHETIC_reference_0.5nm.png").pixels
    work = read_source(examples / "SYNTHETIC_work_2x.png").pixels
    match = register(ref, work)
    assert match["r"] == pytest.approx(2, rel=.001)
    p = project_for(read_source(examples / "SYNTHETIC_work_2x.png"))
    p.calibration.propose(.5 / match["r"], .5 / match["r"], "Matched synthetic reference", True)
    p.calibration.confirm()
    p.style.enabled, p.style.length_nm = True, 100
    comp = compose(work, p)
    assert comp.scale_length_px == pytest.approx(400, abs=.5)
    footer = read_source(examples / "SYNTHETIC_reference_footer.png").pixels
    result = register(footer, work)
    assert result["r"] == pytest.approx(2, rel=.001)
    cropped_work = work[240:1640, 300:1700]
    offset = register(ref, cropped_work)
    assert offset["r"] == pytest.approx(2, rel=.001)
    assert np.array(offset["matrix"])[:, 2] == pytest.approx([-300, -240], abs=2)
    same = register(ref, read_source(examples / "SYNTHETIC_clean.png").pixels)
    assert same["r"] == pytest.approx(1, rel=.001)
    with pytest.raises(ValueError):
        register(ref, read_source(examples / "SYNTHETIC_different_field.png").pixels)


def test_manual_pair_validation(examples):
    ref = read_source(examples / "SYNTHETIC_clean.png").pixels
    work = cv2.resize(ref, (2048, 2048))
    points = [[100, 100], [700, 200], [300, 700], [800, 800]]
    matched = register(ref, work, (points, (np.array(points) * 2).tolist()))
    assert matched["r"] == pytest.approx(2)
    with pytest.raises(ValueError):
        register(ref, work, ([[1, 1], [10, 10], [100, 100]], [[2, 2], [20, 20], [200, 200]]))


def test_metadata_raw_uint16_identity_and_no_dpi_calibration(examples, tmp_path):
    source = read_source(examples / "SYNTHETIC_16bit_OME.tif")
    p = project_for(source)
    assert p.calibration.sx == .2 and p.calibration.status == "Pending"
    p.calibration.confirm()
    p.crop = Crop(rect=[17, 23, 210, 150])
    rgba = display_rgba(source.pixels, p.display_low, p.display_high)
    outputs = export_file(tmp_path / "数据 裁剪.tif", source.pixels, rgba, p, "data-tiff")
    actual = tifffile.imread(outputs[0])
    assert actual.dtype == np.uint16
    np.testing.assert_array_equal(actual, source.pixels[23:173, 17:227])
    assert read_source(outputs[0]).metadata["sx"] == .2
    p.output.scale = 2
    outputs2 = export_file(tmp_path / "scaled.tif", source.pixels, rgba, p, "tiff")
    assert read_source(outputs2[0]).metadata["sx"] == .1
    assert any("_data" in name for name in outputs2)
    dpi_path = tmp_path / "DPI_only.tif"
    tifffile.imwrite(dpi_path, source.pixels, resolution=(300, 300), resolutionunit="INCH")
    assert project_for(read_source(dpi_path)).calibration.status == "Uncalibrated"


def test_local_treatment_does_not_touch_other_pixels(examples):
    source = read_source(examples / "SYNTHETIC_50nm_250px.png")
    p = project_for(source)
    p.masks = [{"layer": "line", "kind": "rect", "rect": [700, 966, 250, 8]}]
    p.treatment, p.treatment_color = "plate", "#123456"
    after = qimage_to_array(render_image(compose(source.pixels, p)))
    mask = build_masks(p, source.pixels.shape[:2])["line"] > 0
    np.testing.assert_array_equal(after[~mask], source.pixels[~mask])
    np.testing.assert_array_equal(after[mask, :3], np.tile([0x12, 0x34, 0x56], (mask.sum(), 1)))


def test_linked_inset_own_transform_and_roi_updates(black_project):
    source, p = black_project
    # Spatially varying underlying sample makes ROI updates observable.
    yy, xx = np.mgrid[:400, :600]
    rgba = display_rgba(((xx + yy) % 200).astype(np.uint8), 0, 255)
    p.style.enabled = False
    p.inset.enabled = True
    p.inset.roi = Crop(rect=[20, 20, 80, 80])
    p.inset.width, p.inset.x, p.inset.y = 320, 250, 20
    p.inset.style.enabled = True
    p.inset.style.length_nm = 5
    comp = compose(rgba, p)
    child = next(item["composition"] for item in comp.primitives if item["type"] == "inset")
    assert child.k == 4
    assert child.scale_length_px == 100
    original_roi = deepcopy(p.inset.roi)
    p.inset.x -= 50
    moved = compose(rgba, p)
    assert p.inset.roi == original_roi
    child2 = next(item["composition"] for item in moved.primitives if item["type"] == "inset")
    np.testing.assert_array_equal(child.base, child2.base)
    p.inset.roi.rect[0] += 20
    updated = compose(rgba, p)
    child3 = next(item["composition"] for item in updated.primitives if item["type"] == "inset")
    assert not np.array_equal(child.base, child3.base)
    p.crop.rect = [10, 10, 580, 380]
    assert p.inset.roi.rect[0] == 40


def test_export_checks_shapes_protection_and_default_guides(black_project):
    source, p = black_project
    rgba = display_rgba(source.pixels, 0, 255)
    p.style.anchor, p.style.x, p.style.y = "custom", 0, 0
    p.crop = Crop(kind="circle", rect=[0, 0, 400, 400])
    comp = compose(rgba, p)
    assert any(i.severity == "error" and i.target == "scale" for i in comp.issues)
    p.crop = Crop(rect=[0, 0, 600, 400])
    p.protected = [[[0, 0], [150, 0], [150, 150], [0, 150]]]
    p.measurements = [{"points": [[10, 10], [300, 300]]}]
    comp = compose(rgba, p)
    assert any(i.severity == "warning" and "protected" in i.message for i in comp.issues)
    assert not any(item.get("role") == "measurement" for item in comp.primitives)
    p.output.export_guides = True
    assert any(item.get("role") == "measurement" for item in compose(rgba, p).primitives)
    p.style.length_nm = 10000
    assert any(i.severity == "error" for i in compose(rgba, p).issues)


def test_comparison_uses_identical_sampling(black_project):
    source, p = black_project
    p.style.enabled = False
    p.output.scale = 1.375
    p.crop = Crop(kind="ellipse", rect=[30, 20, 400, 280])
    rgba = display_rgba(source.pixels, 0, 255)
    before, after = compose(rgba, p, original=True), compose(rgba, p)
    np.testing.assert_array_equal(qimage_to_array(change_view(before, after)), qimage_to_array(render_image(before)))


def test_roundtrip_autosave_history_relink_and_input_hash(examples, tmp_path):
    source = read_source(examples / "SYNTHETIC_clean.png")
    original_hash = file_hash(source.path)
    p = project_for(source)
    p.crop = Crop(kind="polygon", points=[[100, 100], [600, 80], [700, 700], [90, 500]])
    p.calibration.propose(.2, .2, "Manual", True)
    p.calibration.confirm()
    p.masks = [{"kind": "rect", "rect": [200, 200, 50, 50], "layer": "line"}]
    p.treatment = "plate"
    p.inset.enabled = True
    p.inset.x, p.inset.y = 120, 120
    p.inset.roi.rect = [300, 300, 100, 100]
    p.protected = [[[250, 250], [350, 250], [350, 350]]]
    p.measurements = [{"points": [[200, 200], [400, 200]]}]
    path = tmp_path / "中文 project.json"
    save_project(p, path)
    loaded = load_project(path)
    assert loaded.to_dict() == p.to_dict()
    np.testing.assert_array_equal(qimage_to_array(render_image(compose(source.pixels, p))), qimage_to_array(render_image(compose(source.pixels, loaded))))
    history = History(p)
    p.style.color = "#123456"
    history.push(p)
    assert history.step(-1).style.color == "#ffffff"
    assert history.step(1).style.color == "#123456"
    recovery = tmp_path / "recovery.json"
    save_project(p, recovery, write_masks=False)
    p.style.length_nm = 10
    save_project(p, recovery, write_masks=False)
    assert load_project(str(recovery) + ".bak").style.length_nm == 5
    match = tmp_path / "relinked source.png"
    shutil.copy2(source.path, match)
    relink_source(p, match)
    with pytest.raises(ValueError):
        relink_source(p, examples / "SYNTHETIC_different_field.png")
    assert file_hash(source.path) == original_hash
    with pytest.raises(ValueError):
        export_file(p.source_path, source.pixels, source.pixels, p)


def test_svg_real_vectors_and_standalone_assets(black_project, tmp_path):
    source, p = black_project
    rgba = display_rgba(source.pixels, 0, 255)
    p.output.label = "(a)"
    outputs = export_file(tmp_path / "figure.svg", source.pixels, rgba, p, "svg")
    root = ET.parse(outputs[0]).getroot()
    ns = {"s": "http://www.w3.org/2000/svg"}
    rects = root.findall(".//s:rect", ns)
    bar = next(r for r in rects if "scale-bar" in r.attrib.get("id", ""))
    assert float(bar.attrib["width"]) == 25
    texts = [text.text for text in root.findall(".//s:text", ns)]
    assert "5 nm" in texts and "(a)" in texts
    assert all(image.attrib["href"].startswith("data:image/png;base64,") for image in root.findall(".//s:image", ns))


def test_conflict_no_average_and_style_does_not_invalidate(black_project):
    _, p = black_project
    p.calibration.propose(.5, .5, "Other", True)
    assert p.calibration.sx == .5 and p.calibration.conflicts()
    with pytest.raises(ValueError):
        p.calibration.confirm()
    p.calibration.confirm(resolve=True)
    p.style.color = "#ff0000"
    assert p.calibration.status == "Confirmed"


def test_qimage_owns_array_memory():
    a = np.full((16, 20, 4), 177, np.uint8)
    image = array_to_qimage(a)
    a[:] = 0
    assert (qimage_to_array(image) == 177).all()


def test_detection_ocr_missing_and_editable_masks(examples, monkeypatch):
    import microscale.detection as module
    source = read_source(examples / "SYNTHETIC_50nm_250px.png")
    def unavailable(_):
        raise RuntimeError("Synthetic unavailable backend test")
    monkeypatch.setattr(module, "local_ocr", unavailable)
    result = detect(source.pixels)
    assert result["warning"] and result["candidates"]
    bar = next(c for c in result["candidates"] if abs(c["line_rect"][2] - 250) < 3 and c["line_rect"][1] > 900)
    assert math.dist(*bar["endpoints"]) == pytest.approx(250, abs=1)
    p = project_for(source)
    p.masks = [{"layer": "text", "kind": "rect", "rect": [10, 10, 30, 30]}, {"layer": "text", "kind": "brush", "points": [[20, 20], [30, 20]], "radius": 3, "erase": True}]
    mask = build_masks(p, source.pixels.shape)["text"]
    assert mask[12, 12] == 255 and mask[20, 20] == 0


def test_real_local_ocr_backend(examples):
    pytest.importorskip("rapidocr_onnxruntime")
    image = read_source(examples / "SYNTHETIC_50nm_250px.png").pixels
    result = detect(image)
    assert not result["warning"], result["warning"]
    recognized = [c for c in result["candidates"] if c.get("length_nm") == 50 and abs(c["line_rect"][2] - 250) < 3]
    assert recognized, result["texts"]


def test_print_geometry_and_dpi_metadata_independence(black_project):
    source, p = black_project
    p.style.anchor = "bottom-right"
    rgba = display_rgba(source.pixels, 0, 255)
    p.output.dpi = 600
    assert compose(rgba, p).scale_length_px == 25
    p.output.mode, p.output.width_mm, p.output.dpi = "print", 50.8, 300
    p.output.font_pt, p.output.line_pt = 9.6, 1.2
    comp = compose(rgba, p)
    assert comp.base.shape[1] == 600 and comp.k == 1
    bar = next(item for item in comp.primitives if item.get("role") == "scale-bar")
    text = next(item for item in comp.primitives if item.get("role") == "scale-label")
    assert bar["rect"][3] == 5
    assert text["size"] == 40
    p.output.dpi = 600
    comp2 = compose(rgba, p)
    assert comp2.base.shape[1] == 1200 and comp2.scale_length_px == 50


def test_candidate_residue_and_reciprocal_ocr(examples, monkeypatch):
    import microscale.detection as module
    source = read_source(examples / "SYNTHETIC_50nm_250px.png")
    candidate = {"line_rect": [700, 966, 250, 8], "endpoints": [[700, 970], [950, 970]], "text_points": [[739, 920], [875, 920], [875, 954], [739, 954]], "confidence": .9}
    p = project_for(source)
    p.candidates = [candidate]
    assert any(issue.target == "old-scale" for issue in compose(source.pixels, p).issues)
    p.treatment = "plate"
    p.masks = [{"kind": "rect", "rect": [700, 966, 250, 8], "layer": "line"}]
    assert any(issue.target == "old-scale" for issue in compose(source.pixels, p).issues)  # text remains
    p.masks.append({"kind": "rect", "rect": [730, 910, 170, 50], "layer": "text"})
    assert not any(issue.target == "old-scale" for issue in compose(source.pixels, p).issues)
    monkeypatch.setattr(module, "local_ocr", lambda image: [{"points": [[700, 900], [850, 900], [850, 940], [700, 940]], "text": "5 nm⁻¹", "confidence": .98}])
    result = detect(source.pixels)
    assert "Reciprocal" in result["warning"]
    assert all(c.get("length_nm") is None for c in result["candidates"])


def test_corrupt_primary_preserves_valid_recovery(tmp_path, black_project):
    _, p = black_project
    path = tmp_path / "recover.json"
    save_project(p, path, write_masks=False)
    p.style.length_nm = 8
    save_project(p, path, write_masks=False)
    backup = Path(str(path) + ".bak")
    previous = backup.read_bytes()
    path.write_text("{invalid", encoding="utf-8")
    p.style.length_nm = 9
    save_project(p, path, write_masks=False)
    assert backup.read_bytes() == previous
    assert load_project(path).style.length_nm == 9


def test_source_hash_drift_is_rejected(examples, tmp_path):
    path = tmp_path / "source.png"
    shutil.copy2(examples / "SYNTHETIC_clean.png", path)
    p = project_for(read_source(path))
    project_path = tmp_path / "project.json"
    save_project(p, project_path)
    shutil.copy2(examples / "SYNTHETIC_different_field.png", path)
    with pytest.raises(ValueError, match="hash mismatch"):
        load_project(project_path)
