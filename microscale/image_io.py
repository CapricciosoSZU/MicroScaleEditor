"""Read-only scientific arrays; presentation mapping has explicit, fixed limits."""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import tifffile
from PySide6.QtGui import QImage

from .geometry import UNITS
from .model import Project, Crop, file_hash, velox_style

log = logging.getLogger(__name__)


@dataclass
class Source:
    pixels: np.ndarray
    metadata: dict
    path: str
    sha256: str


def read_source(path):
    path = str(Path(path).resolve())
    metadata = {}
    if Path(path).suffix.lower() in (".tif", ".tiff"):
        with tifffile.TiffFile(path) as tif:
            if len(tif.pages) != 1:
                raise ValueError("Multi-page TIFF is not supported. Export a single real-space image first.")
            array = tif.asarray()
            if array.ndim == 3 and array.shape[0] in (3, 4) and array.shape[-1] not in (3, 4):
                array = np.moveaxis(array, 0, -1)
            if tif.ome_metadata:
                root = ET.fromstring(tif.ome_metadata)
                pixels = root.find(".//{*}Pixels")
                if pixels is not None:
                    for axis in ("X", "Y"):
                        unit = pixels.get(f"PhysicalSize{axis}Unit", "µm")
                        value = pixels.get(f"PhysicalSize{axis}")
                        if value and unit in UNITS and float(value) > 0:
                            metadata["s" + axis.lower()] = float(value) * UNITS[unit]
                    metadata["calibration_source"] = "OME PhysicalSize (sample space)"
            description = tif.pages[0].description
            if description:
                try:
                    own = json.loads(description).get("microscale", {})
                    if own.get("unit") == "nm" and own.get("status") == "Confirmed":
                        metadata.update({k: own[k] for k in ("sx", "sy") if own.get(k)})
                        metadata["calibration_source"] = "MicroScale sample-space metadata"
                except (ValueError, AttributeError):
                    pass
            # TIFF ResolutionUnit / DPI and nominal magnification are deliberately ignored.
    else:
        array = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if array is None:
            raise ValueError("Cannot decode the image. Supported inputs: PNG, JPEG, single-page TIFF.")
        if array.ndim == 3:
            array = cv2.cvtColor(array, cv2.COLOR_BGRA2RGBA if array.shape[2] == 4 else cv2.COLOR_BGR2RGB)
    if array.ndim not in (2, 3) or (array.ndim == 3 and array.shape[-1] not in (3, 4)):
        raise ValueError("Expected a grayscale, RGB or RGBA real-space image.")
    if array.dtype.kind not in "uif" or not np.isfinite(array).all():
        raise ValueError("Image must contain finite numeric samples.")
    array = np.ascontiguousarray(array)
    array.setflags(write=False)
    source = Source(array, metadata, path, file_hash(path))
    log.info("Read %s shape=%s dtype=%s calibration=%s", path, array.shape, array.dtype, metadata)
    return source


def project_for(source):
    h, w = source.pixels.shape[:2]
    p = Project(source_path=source.path, source_hash=source.sha256, source_shape=list(source.pixels.shape), source_dtype=str(source.pixels.dtype), crop=Crop(rect=[0., 0., float(w), float(h)]))
    p.style = velox_style((w, h))
    p.inset.style = velox_style((p.inset.width, p.inset.width))
    if source.pixels.dtype == np.uint8:
        p.display_low, p.display_high = 0., 255.
    else:
        p.display_low, p.display_high = float(source.pixels.min()), float(source.pixels.max())
        if p.display_high == p.display_low:
            p.display_high += 1
    if source.metadata.get("sx") or source.metadata.get("sy"):
        p.calibration.propose(source.metadata.get("sx"), source.metadata.get("sy"), source.metadata["calibration_source"])
    return p


def display_rgba(array, low=None, high=None):
    low = float(array.min()) if low is None else low
    high = float(array.max()) if high is None else high
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError("Display high must be finite and greater than display low.")
    mapped = np.clip((array.astype(np.float32) - low) * (255. / (high - low)), 0, 255).round().astype(np.uint8)
    if mapped.ndim == 2:
        mapped = np.repeat(mapped[..., None], 3, axis=2)
    if mapped.shape[-1] == 3:
        mapped = np.concatenate([mapped, np.full((*mapped.shape[:2], 1), 255, np.uint8)], axis=2)
    else:
        # Alpha is coverage, never intensity-windowed with sample data.
        alpha = array[..., 3]
        denominator = np.iinfo(array.dtype).max if array.dtype.kind in "ui" else 1.
        mapped[..., 3] = np.clip(alpha.astype(float) / denominator * 255, 0, 255).round().astype(np.uint8)
    return np.ascontiguousarray(mapped)


def array_to_qimage(rgba):
    rgba = np.ascontiguousarray(rgba, dtype=np.uint8)
    # copy() owns the memory independently of temporary NumPy objects and threads.
    return QImage(rgba.data, rgba.shape[1], rgba.shape[0], rgba.strides[0], QImage.Format.Format_RGBA8888).copy()


def qimage_to_array(image):
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine())[:, :image.width() * 4].reshape(image.height(), image.width(), 4).copy()


def write_png(path, rgba):
    converted = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA) if rgba.ndim == 3 and rgba.shape[2] == 4 else rgba
    ok, buffer = cv2.imencode(".png", converted)
    if not ok:
        raise OSError("PNG encoding failed.")
    buffer.tofile(str(path))


def available_output(path, inputs=()):
    path = Path(path).resolve()
    if str(path).casefold() in {str(Path(i).resolve()).casefold() for i in inputs if i}:
        raise ValueError("Export cannot overwrite an input image. Choose another filename.")
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate, n = path, 1
    while candidate.exists() or candidate.with_suffix(candidate.suffix + ".json").exists():
        candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")
        n += 1
    return candidate
