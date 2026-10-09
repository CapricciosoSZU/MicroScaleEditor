"""Rotation is one recorded transform, shared by display and scientific exports."""
from copy import deepcopy
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import tifffile

from microscale.geometry import output_geometry, rotated_spacing, scale_calibration_message
from microscale.image_io import Source, display_rgba, project_for, qimage_to_array, read_source
from microscale.model import Crop, History, Project, save_project, load_project
from microscale.rendering import compose, data_crop, export_file, render_image, change_view


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.float32])
@pytest.mark.parametrize("angle,turns", [(90, -1), (-90, 1), (180, 2)])
def test_quarter_turn_native_data_exact_and_metadata(tmp_path, dtype, angle, turns):
    raw = np.arange(72, dtype=dtype).reshape(8, 9)
    path = tmp_path / "source.tif"
    tifffile.imwrite(path, raw)
    source = read_source(path)
    p = project_for(source)
    p.crop = Crop(rect=[1, 2, 6, 5])
    p.calibration.propose(.2, .4, "Synthetic anisotropic sample")
    p.calibration.confirm()
    p.output.rotation_deg = angle
    rgba = display_rgba(source.pixels, 0, 71)
    result = export_file(tmp_path / "rotated.tif", source.pixels, rgba, p, "data-tiff")
    actual = read_source(result[0])
    np.testing.assert_array_equal(actual.pixels, np.rot90(raw[2:7, 1:7], turns))
    assert actual.pixels.dtype == dtype
    assert actual.metadata["sx"] == (.2 if angle == 180 else .4)
    assert actual.metadata["sy"] == (.4 if angle == 180 else .2)
    meta = json.loads((tmp_path / "rotated.tif.json").read_text())
    assert not meta["interpolated"]
    assert meta["rotation_deg_clockwise"] == (-180 if angle == 180 else angle)
    assert np.all(read_source(tmp_path / "rotated_valid-mask.png").pixels == 255)
    np.testing.assert_array_equal(source.pixels, raw)
    assert not source.pixels.flags.writeable


def test_custom_angle_affine_geometry_and_linear_ramp(tmp_path):
    yy, xx = np.mgrid[:90, :140]
    raw = (xx + 2 * yy).astype(np.float32)
    raw.setflags(write=False)
    p = project_for(Source(raw, {}, "synthetic", "hash"))
    p.crop = Crop(rect=[20, 10, 80, 60])
    p.output.rotation_deg = 30
    p.calibration.propose(.2, .2, "Equal independently known axes")
    p.calibration.confirm()
    rgba = display_rgba(raw, 0, 320)
    original = deepcopy(p.to_dict())
    comp = compose(rgba, p)
    assert comp.base.shape[:2] == (92, 100)
    data, valid, _ = data_crop(raw, p)
    for point in ([30.5, 20.5], [55.5, 45.5], [90.5, 60.5]):
        assert comp.to_source(comp.to_output(point)) == pytest.approx(point)
    for oy, ox in ((40, 40), (50, 50), (45, 60)):
        assert valid[oy, ox]
        sx, sy = comp.to_source([ox + .5, oy + .5])
        assert data[oy, ox] == pytest.approx((sx - .5) + 2 * (sy - .5), abs=.06)
    assert np.array_equal(comp.base[..., 3] > 0, valid)
    assert p.to_dict() == original
    p.output.mode, p.output.width_px = "width", 200
    assert output_geometry(p.crop, raw.shape, p.output)[2] == (200, 184)
    export_file(tmp_path / "custom.tif", raw, rgba, p, "data-tiff")
    meta = json.loads((tmp_path / "custom.tif.json").read_text())
    assert meta["interpolated"] and meta["sx"] == pytest.approx(.1)
    assert meta["source_to_output_edge_matrix"] == compose(rgba, p).matrix.tolist()


def test_rotation_directional_calibration_and_horizontal_bar(black_project):
    source, p = black_project
    rgba = display_rgba(source.pixels, 0, 255)
    p.style.anchor = "bottom-right"
    p.calibration.sy = .4
    p.output.rotation_deg = 90
    assert compose(rgba, p).scale_length_px == pytest.approx(12.5)
    p.calibration.sy = None
    comp = compose(rgba, p)
    assert comp.scale_rect is None
    assert any("output horizontal direction" in i.message for i in comp.issues)
    p.output.rotation_deg = 180
    assert compose(rgba, p).scale_length_px == 25
    p.output.rotation_deg = 30
    assert "equal x/y" in scale_calibration_message(p.calibration, 30)
    p.calibration.sy = .4
    assert rotated_spacing(p.calibration, 30) == (None, None)
    p.calibration.sy = .2
    comp = compose(rgba, p)
    assert comp.scale_length_px == 25
    assert not [i for i in comp.issues if i.severity == "error"]
    bar = next(item for item in comp.primitives if item.get("role") == "scale-bar")
    x, y, w, h = bar["rect"]
    rendered = qimage_to_array(render_image(comp))
    assert np.all(rendered[round(y + h / 2), math.ceil(x):math.floor(x + w), :3] == 255)
    assert p.calibration.status == "Confirmed"


def test_rotated_masks_guides_inset_svg_and_project_replay(black_project, tmp_path):
    source, p = black_project
    p.output.rotation_deg = 90
    p.style.anchor = "bottom-right"
    p.output.export_guides = True
    p.measurements = [{"points": [[100, 100], [180, 100]]}]
    p.protected = [[[60, 260], [100, 260], [100, 300], [60, 300]]]
    p.inset.enabled = True
    p.inset.roi = Crop(rect=[30, 30, 100, 80])
    p.inset.x, p.inset.y, p.inset.width = 30, 40, 160
    p.inset.style.enabled = True
    rgba = display_rgba(source.pixels, 0, 255)
    comp = compose(rgba, p)
    measure = next(i for i in comp.primitives if i.get("role") == "measurement")
    assert measure["points"] == [[300, 100], [300, 180]]
    child = next(i["composition"] for i in comp.primitives if i["type"] == "inset")
    assert child.rotation_deg == 90 and child.base.shape[:2] == (200, 160)
    assert child.scale_length_px == 50
    assert any("overlaps protected" in i.message for i in comp.issues)
    p.inset.enabled = False
    comp = compose(rgba, p)
    export_file(tmp_path / "rotation.svg", source.pixels, rgba, p, "svg")
    svg = ET.parse(tmp_path / "rotation.svg").getroot()
    assert (svg.attrib["width"], svg.attrib["height"]) == ("400", "600")
    bar = next(n for n in svg.iter() if n.attrib.get("id", "").startswith("main-scale-bar"))
    assert float(bar.attrib["width"]) == 25
    save_project(p, tmp_path / "project.json")
    restored = load_project(tmp_path / "project.json", verify=False)
    np.testing.assert_array_equal(qimage_to_array(render_image(comp)), qimage_to_array(render_image(compose(rgba, restored))))
    p.style.enabled = False
    p.output.export_guides = False
    expected = compose(rgba, p, original=True)
    np.testing.assert_array_equal(qimage_to_array(change_view(expected, compose(rgba, p))), qimage_to_array(render_image(expected)))
    legacy = Project().to_dict()
    legacy["output"].pop("rotation_deg")
    legacy["calibration"].pop("endpoints_dirty")
    assert Project.from_dict(legacy).output.rotation_deg == 0


def test_nonfinite_rotation_rejected(black_project):
    source, p = black_project
    p.output.rotation_deg = float("nan")
    with pytest.raises(ValueError, match="finite"):
        output_geometry(p.crop, source.pixels.shape, p.output)
