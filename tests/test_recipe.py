"""Independent-process replay is the same native-Qt raster as the GUI core."""
from pathlib import Path
import subprocess
import sys
import numpy as np

from microscale.image_io import read_source, project_for
from microscale.model import save_project, Crop
from microscale.rendering import compose, render_image
from microscale.image_io import qimage_to_array


def test_independent_process_recipe_pixels(examples, tmp_path):
    source = read_source(examples / "SYNTHETIC_clean.png")
    p = project_for(source)
    p.calibration.propose(.2, .2, "Synthetic", True)
    p.calibration.confirm()
    p.style.enabled, p.style.plate = True, True
    p.output.label = "(a) SYNTHETIC"
    p.inset.enabled = True
    p.inset.roi = Crop(rect=[400, 300, 80, 80])
    p.inset.x, p.inset.y, p.inset.width = 30, 100, 320
    p.inset.style.enabled = True
    p.inset.style.plate = True
    project_path, output_path = tmp_path / "recipe.json", tmp_path / "replay.png"
    save_project(p, project_path)
    expected = qimage_to_array(render_image(compose(source.pixels, p)))
    result = subprocess.run([sys.executable, "-m", "microscale", "--recipe", str(project_path), "--output", str(output_path)], capture_output=True, text=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 0, result.stderr
    np.testing.assert_array_equal(read_source(output_path).pixels, expected)
