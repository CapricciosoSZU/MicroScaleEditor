import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import tifffile

from microscale.image_io import read_source, project_for, display_rgba
from microscale.model import Crop, file_hash, save_project
from microscale.rendering import compose, data_crop, export_file


def make_source(tmp_path, suffix, dtype, channels=1):
    yy, xx = np.mgrid[:120, :180]
    raw = (100 + xx * 11 + yy * 137).astype(dtype)
    if dtype == np.float32:
        raw = raw / np.float32(37.13)
    if channels > 1:
        raw = np.stack([raw, raw + 15, raw + 30], axis=-1)
        if channels == 4:
            raw = np.concatenate([raw, np.full((*raw.shape[:2], 1), np.iinfo(dtype).max, dtype)], axis=-1)
    path = tmp_path / ("source" + suffix)
    if suffix in (".tif", ".tiff"):
        tifffile.imwrite(path, raw, photometric="rgb" if channels > 1 else "minisblack")
    else:
        encoded = cv2.cvtColor(raw, cv2.COLOR_RGBA2BGRA if channels == 4 else cv2.COLOR_RGB2BGR) if channels > 1 else raw
        ok, data = cv2.imencode(suffix, encoded)
        assert ok
        data.tofile(str(path))
    source = read_source(path)
    p = project_for(source)
    p.display_low = 0
    p.display_high = 65535 if dtype == np.uint16 else 1000 if dtype == np.float32 else 255
    p.calibration.propose(.2, .2, "Synthetic calibration", True)
    p.calibration.confirm()
    p.style.enabled = True
    p.style.length_nm = 5
    p.style.anchor = "custom"
    p.style.x, p.style.y = 50, 50
    return source, p


@pytest.mark.parametrize("suffix,dtype,channels", [
    (".tif", np.uint16, 1), (".tiff", np.float32, 1),
    (".png", np.uint16, 1), (".png", np.uint16, 3), (".png", np.uint16, 4),
    (".png", np.uint8, 3),
])
def test_same_format_keeps_precision_with_visible_bar(tmp_path, suffix, dtype, channels):
    source, p = make_source(tmp_path, suffix, dtype, channels)
    original_hash = file_hash(source.path)
    rgba = display_rgba(source.pixels, p.display_low, p.display_high)
    outputs = export_file(tmp_path / "figure.wrong", source.pixels, rgba, p, "source")
    path = Path(outputs[0])
    assert path.suffix == suffix
    result = read_source(path).pixels
    assert result.dtype == dtype and result.shape == source.pixels.shape
    np.testing.assert_array_equal(result[:35, :40], source.pixels[:35, :40])
    comp = compose(rgba, p)
    bar = next(v for v in comp.primitives if v.get("role") == "scale-bar")["rect"]
    x, y, w, h = map(round, bar)
    assert np.all(result[y + 1:y + h - 1, x + 1:x + w - 1] == p.display_high)
    meta = json.loads(Path(str(path) + ".json").read_text())
    assert meta["bit_depth"] == np.dtype(dtype).itemsize * 8
    assert meta["role"] == "source-format presentation"
    assert not meta["display_mapping_baked_into_sample"]
    assert file_hash(source.path) == original_hash
    assert not source.pixels.flags.writeable


def test_higher_resolution_float_tiff_retains_precision(tmp_path):
    source, p = make_source(tmp_path, ".tif", np.float32)
    p.output.scale = 2
    p.output.rotation_deg = 90
    rgba = display_rgba(source.pixels, p.display_low, p.display_high)
    outputs = export_file(tmp_path / "figure.tif", source.pixels, rgba, p, "source")
    result = read_source(outputs[0]).pixels
    expected, _, _ = data_crop(source.pixels, p)
    assert result.shape == (360, 240) and result.dtype == np.float32
    np.testing.assert_array_equal(result[200:300, 10:150], expected[200:300, 10:150])
    assert np.unique(result[200:300, 10:150]).size > 256
    meta = json.loads(Path(outputs[0] + ".json").read_text())
    assert meta["sx"] == .1 and meta["scale_length_px"] == 50
    assert meta["interpolated"]


@pytest.mark.parametrize("channels", [1, 3, 4])
def test_native_inset_is_not_quantized_to_8_bits(tmp_path, channels):
    source, p = make_source(tmp_path, ".png", np.uint16, channels)
    p.style.enabled = False
    p.inset.enabled = True
    p.inset.roi = Crop(rect=[5, 5, 80, 60])
    p.inset.width, p.inset.x, p.inset.y = 80, 95, 55
    rgba = display_rgba(source.pixels, p.display_low, p.display_high)
    outputs = export_file(tmp_path / "inset.png", source.pixels, rgba, p, "source")
    data = read_source(outputs[0]).pixels
    np.testing.assert_array_equal(data[60:105, 100:165], source.pixels[10:55, 10:75])
    assert np.unique(data[60:105, 100:165]).size > 256


def test_custom_angle_native_png_alpha_and_gray_background(tmp_path):
    for channels in (1, 4):
        folder = tmp_path / str(channels)
        folder.mkdir()
        source, p = make_source(folder, ".png", np.uint16, channels)
        p.style.enabled = False
        p.output.rotation_deg = 27
        rgba = display_rgba(source.pixels, p.display_low, p.display_high)
        outputs = export_file(folder / "rotated.png", source.pixels, rgba, p, "source")
        data = read_source(outputs[0]).pixels
        valid = compose(rgba, p).valid
        assert not valid.all()
        if channels == 4:
            assert np.all(data[~valid, 3] == 0)
        else:
            assert np.all(data[~valid] == 65535)


def test_jpeg_same_format_and_default_recipe_export(tmp_path):
    source, p = make_source(tmp_path, ".jpg", np.uint8, 3)
    p.output.scale = 2
    rgba = display_rgba(source.pixels, p.display_low, p.display_high)
    outputs = export_file(tmp_path / "photo.png", source.pixels, rgba, p, "source")
    data = read_source(outputs[0]).pixels
    assert Path(outputs[0]).suffix == ".jpg"
    assert data.shape == (240, 360, 3) and data.dtype == np.uint8
    meta = json.loads(Path(outputs[0] + ".json").read_text())
    assert meta["lossy_reencoding"] and meta["jpeg_quality"] == 98
    project = tmp_path / "project.json"
    save_project(p, project)
    result = subprocess.run([sys.executable, "-m", "microscale", "--recipe", str(project), "--output", str(tmp_path / "replay.jpg")], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    np.testing.assert_array_equal(read_source(tmp_path / "replay.jpg").pixels, data)
