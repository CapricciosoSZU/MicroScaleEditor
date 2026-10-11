"""Outlined annotations preserve physical geometry, precision and saved styles."""
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import tifffile

from microscale.image_io import Source, display_rgba, project_for, qimage_to_array, read_source
from microscale.model import Project, Style, load_project, save_project, velox_style
from microscale.rendering import compose, export_file, render_image


def setup_image(dtype=np.uint8):
    raw = np.full((320, 640), 128 if dtype == np.uint8 else 32768, dtype)
    raw.setflags(write=False)
    source = Source(raw, {}, "SYNTHETIC_style.tif", "synthetic")
    p = project_for(source)
    p.display_low, p.display_high = 0, np.iinfo(dtype).max
    p.calibration.propose(1, 1, "Synthetic test only", True)
    p.calibration.confirm()
    p.style = velox_style((1024, 1024), enabled=True, length_nm=200)
    return source, p


def test_default_and_legacy_project_appearance():
    source, p = setup_image()
    new = project_for(source)
    assert new.style.outline and new.inset.style.outline
    assert not new.style.enabled and new.calibration.status == "Uncalibrated"
    assert new.style.anchor == "bottom-left" and not new.style.bold
    legacy = p.to_dict()
    legacy["style"] = {k:v for k,v in vars(Style()).items() if k not in {"outline", "outline_color", "outline_width", "text_align"}}
    restored = Project.from_dict(legacy)
    assert restored.style == Style()
    assert not restored.style.outline and restored.style.text_align == "center"


@pytest.mark.parametrize("factor", [1, 2, 4])
def test_outline_outer_span_is_calibrated_and_inside_group(factor):
    source, p = setup_image()
    p.output.scale = factor
    # Match the resolution preset's appearance scaling.
    for key in ("font_size", "thickness", "gap", "margin", "outline_width"):
        setattr(p.style, key, getattr(p.style, key) * factor)
    comp = compose(display_rgba(source.pixels, 0, 255), p)
    assert not any(i.severity == "error" for i in comp.issues)
    bar = next(v for v in comp.primitives if v.get("role") == "scale-bar")
    x,y,w,h = bar["rect"]
    assert w == 200 * factor and comp.scale_length_px / factor == 200
    raster = qimage_to_array(render_image(comp))
    scan = raster[int(y+h/2), :, 0]
    changed = np.flatnonzero(scan != 128)
    assert changed[0] == round(x) and changed[-1] == round(x+w)-1
    assert scan[round(x)] == 0 and scan[round(x+w/2)] == 255
    assert scan[round(x+w)-1] == 0
    gx,gy,gw,gh = comp.scale_rect
    changed_pixels = np.any(raster[..., :3] != 128, axis=2)
    ys,xs = np.where(changed_pixels)
    assert xs.min() >= np.floor(gx) and xs.max() < np.ceil(gx+gw)
    assert ys.min() >= np.floor(gy) and ys.max() < np.ceil(gy+gh)


def test_native_precision_svg_and_project_outline_roundtrip(tmp_path):
    source, p = setup_image(np.uint16)
    source.path = p.source_path = str(tmp_path / "source.tif")
    tifffile.imwrite(source.path, source.pixels)
    rgba = display_rgba(source.pixels, 0, 65535)
    outputs = export_file(tmp_path / "outlined.tif", source.pixels, rgba, p, "source")
    data = read_source(outputs[0]).pixels
    comp = compose(rgba, p)
    x,y,w,h = next(v for v in comp.primitives if v.get("role") == "scale-bar")["rect"]
    assert data.dtype == np.uint16
    assert data[int(y+h/2),int(x)] == 0
    assert data[int(y+h/2),int(x+w/2)] == 65535
    np.testing.assert_array_equal(data[:100], source.pixels[:100])
    export_file(tmp_path / "outlined.svg", source.pixels, rgba, p, "svg")
    elements = list(ET.parse(tmp_path / "outlined.svg").iter())
    bar = next(e for e in elements if e.get("id", "").startswith("main-scale-bar-") and not e.get("id").endswith("-fill"))
    assert float(bar.get("width")) == 200 and bar.get("fill") == "#000000"
    text = next(e for e in elements if e.tag.endswith("}text"))
    assert text.get("stroke") == "#000000" and text.get("paint-order") == "stroke fill"
    assert float(text.get("stroke-width")) == 5
    save_project(p, tmp_path / "project.json")
    restored = load_project(tmp_path / "project.json", verify=False)
    assert restored.style == p.style


def test_outline_rejects_invisible_fill_and_checks_label_bounds():
    source, p = setup_image()
    p.style.outline_width = p.style.thickness / 2
    comp = compose(display_rgba(source.pixels, 0, 255), p)
    assert any("Outline is too wide" in i.message and i.severity == "error" for i in comp.issues)
    p.style.outline_width = 2.5
    p.style.anchor, p.style.x, p.style.y = "custom", 600, 250
    comp = compose(display_rgba(source.pixels, 0, 255), p)
    assert any("outside the valid crop" in i.message for i in comp.issues)


def test_print_outline_tracks_point_based_bar_thickness():
    source, p = setup_image()
    p.style = velox_style((4096,4096), enabled=True, length_nm=200)
    p.output.mode = "print"
    comp = compose(display_rgba(source.pixels, 0, 255), p)
    assert not any(i.severity == "error" for i in comp.issues)
    bar = next(v for v in comp.primitives if v.get("role") == "scale-bar")
    assert bar["outline_width"] / bar["rect"][3] == pytest.approx(.25)


@pytest.mark.parametrize("align", ["left", "right"])
def test_aligned_end_ticks_stay_inside_checked_group(align):
    source, p = setup_image()
    p.style.endcaps = True
    p.style.text_align = align
    p.style.anchor, p.style.x, p.style.y = "custom", 0, 0
    comp = compose(display_rgba(source.pixels, 0, 255), p)
    gx,gy,gw,gh = comp.scale_rect
    for v in comp.primitives:
        if v.get("role") == "scale-endcap":
            x,y,w,h = v["rect"]
            assert gx <= x and x+w <= gx+gw
            assert gy <= y and y+h <= gy+gh
    assert not any(i.severity == "error" for i in comp.issues)
