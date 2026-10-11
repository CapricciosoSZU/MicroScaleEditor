"""Legacy below-label settings cannot change the fixed above-bar layout."""
from copy import deepcopy
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PySide6.QtGui import QFont, QPainterPath

from microscale.image_io import display_rgba, qimage_to_array, read_source
from microscale.model import Project, Style, load_project, save_project, velox_style
from microscale.rendering import compose, export_file, render_image


@pytest.mark.parametrize("outlined", [False, True])
@pytest.mark.parametrize("endcaps", [False, True])
@pytest.mark.parametrize("mode", ["native", "print"])
def test_main_and_inset_labels_always_above(black_project, tmp_path, outlined, endcaps, mode):
    source, p = black_project
    p.style = velox_style(enabled=True) if outlined else Style(enabled=True)
    p.style.endcaps = endcaps
    p.inset.enabled = True
    p.inset.style = deepcopy(p.style)
    p.output.mode = mode
    rgba = display_rgba(source.pixels, 0, 255)
    expected = render_image(compose(rgba, p))
    # Even in-memory state originating outside the UI uses the fixed layout.
    p.style.text_position = p.inset.style.text_position = "below"
    comp = compose(rgba, p)
    assert not any(i.severity == "error" for i in comp.issues)
    child = next(v["composition"] for v in comp.primitives if v["type"] == "inset")
    for current in (comp, child):
        bar = next(v for v in current.primitives if v.get("role") == "scale-bar")
        label = next(v for v in current.primitives if v.get("role") == "scale-label")
        font = QFont(label["font"])
        font.setPixelSize(label["size"])
        font.setBold(label["bold"])
        glyphs = QPainterPath()
        glyphs.addText(label["x"], label["y"], font, label["text"])
        cap = bar["rect"][3] * 2 if endcaps else 0
        assert glyphs.boundingRect().bottom() + label.get("outline_width", 0) <= bar["rect"][1] - cap
    np.testing.assert_array_equal(qimage_to_array(render_image(comp)), qimage_to_array(expected))
    export_file(tmp_path / "fixed.png", source.pixels, rgba, p, "png")
    np.testing.assert_array_equal(read_source(tmp_path / "fixed.png").pixels, qimage_to_array(expected))
    export_file(tmp_path / "fixed.svg", source.pixels, rgba, p, "svg")
    elements = list(ET.parse(tmp_path / "fixed.svg").iter())
    for prefix in ("main-", "main-inset-"):
        bar = next(e for e in elements if e.get("id", "").startswith(prefix + "scale-bar-") and not e.get("id").endswith("-fill"))
        text = next(e for e in elements if e.get("id", "").startswith(prefix + "scale-label-"))
        assert float(text.get("y")) < float(bar.get("y"))


def test_legacy_project_and_style_normalize_only_label_placement(black_project, tmp_path):
    _, p = black_project
    p.source_path = str(tmp_path / "SYNTHETIC_black.png")
    data = p.to_dict()
    data["style"]["text_position"] = data["inset"]["style"]["text_position"] = "below"
    restored = Project.from_dict(data)
    expected = deepcopy(data)
    expected["style"]["text_position"] = expected["inset"]["style"]["text_position"] = "above"
    assert restored.to_dict() == expected
    assert data["style"]["text_position"] == "below"
    assert Style(**data["style"]).text_position == "above"
    save_project(restored, tmp_path / "project.json")
    assert load_project(tmp_path / "project.json", verify=False).to_dict() == expected
