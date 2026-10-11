import os
from pathlib import Path
import pytest
import numpy as np
from PySide6.QtWidgets import QApplication
from microscale.examples import generate_examples
from microscale.image_io import Source, project_for
from microscale.model import Style


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(scope="session")
def examples(tmp_path_factory):
    return generate_examples(tmp_path_factory.mktemp("synthetic-examples"))


@pytest.fixture
def black_project():
    pixels = np.zeros((400, 600), np.uint8)
    pixels.setflags(write=False)
    source = Source(pixels, {}, "SYNTHETIC_black.png", "synthetic")
    p = project_for(source)
    # Legacy unoutlined baseline; outlined geometry has its own coverage.
    p.style = Style()
    p.calibration.propose(.2, .2, "Synthetic known reference", True)
    p.calibration.confirm()
    p.style.enabled = True
    p.style.length_nm = 5
    p.style.anchor = "custom"
    p.style.x, p.style.y = 50., 50.
    return source, p
