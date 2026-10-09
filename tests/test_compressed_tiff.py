"""Compressed TIFF regressions use generated pixels, never private microscopy."""
import numpy as np
import pytest
import tifffile

from microscale.image_io import read_source, project_for, display_rgba
from microscale.model import Crop, file_hash
from microscale.rendering import export_file


@pytest.mark.parametrize("dtype,channels,predictor", [(np.uint8, 1, False), (np.uint16, 1, True), (np.uint8, 4, False), (np.float32, 1, True)])
def test_lzw_decode_preserves_samples_and_native_crop(tmp_path, dtype, channels, predictor):
    shape = (87, 113) if channels == 1 else (87, 113, channels)
    rng = np.random.default_rng(814)
    pixels = rng.normal(2000, 3000, shape).astype(dtype) if dtype == np.float32 else rng.integers(0, np.iinfo(dtype).max, size=shape, dtype=dtype)
    path = tmp_path / "compressed source.tif"
    options = {"photometric": "minisblack" if channels == 1 else "rgb"}
    if channels == 4:
        options["extrasamples"] = ["unassalpha"]
    tifffile.imwrite(path, pixels, compression="lzw", predictor=predictor, **options)
    before = file_hash(path)
    source = read_source(path)
    assert source.pixels.dtype == dtype and not source.pixels.flags.writeable
    np.testing.assert_array_equal(source.pixels, pixels)
    p = project_for(source)
    p.crop = Crop(rect=[7, 11, 57, 39])
    outputs = export_file(tmp_path / "data.tif", source.pixels, display_rgba(source.pixels, p.display_low, p.display_high), p, "data-tiff")
    actual = tifffile.imread(outputs[0])
    assert actual.dtype == dtype
    np.testing.assert_array_equal(actual, pixels[11:50, 7:64])
    assert file_hash(path) == before
