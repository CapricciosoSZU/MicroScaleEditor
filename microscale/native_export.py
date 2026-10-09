"""Source-format figures: retain sample precision and blend annotations separately."""
import math
from pathlib import Path

import cv2
import numpy as np
import tifffile

from .detection import build_masks
from .image_io import qimage_to_array, write_png
from .model import atomic_json
from .rendering import Composition, data_crop, inset_project, render_image, rgb


def source_suffix(project):
    suffix = Path(project.source_path).suffix.lower()
    if suffix not in (".tif", ".tiff", ".png", ".jpg", ".jpeg"):
        raise ValueError("Same as source supports TIFF, PNG and JPEG inputs.")
    return suffix


def cast_samples(values, dtype):
    if np.issubdtype(dtype, np.integer):
        limits = np.iinfo(dtype)
        values = np.clip(np.rint(values), limits.min, limits.max)
    return values.astype(dtype)


def alpha_max(dtype):
    return float(np.iinfo(dtype).max) if np.issubdtype(dtype, np.integer) else 1.


def color_samples(colors, project, grayscale):
    colors = np.asarray(colors, dtype=np.float64)
    if grayscale:
        colors = colors @ np.array([.2126, .7152, .0722])
    return project.display_low + colors / 255. * (project.display_high - project.display_low)


def blend_samples(destination, colors, alpha, mask):
    """Source-over on selected pixels only; untouched samples never pass through float."""
    if not mask.any():
        return
    a = alpha[mask].astype(np.float64)
    gray = destination.ndim == 2
    values = destination[mask].astype(np.float64)
    incoming = colors if colors.ndim == (1 if gray else 2) else colors[mask]
    if gray:
        mixed = incoming * a + values * (1 - a)
    elif destination.shape[2] == 4:
        old_alpha = np.clip(values[:, 3] / alpha_max(destination.dtype), 0, 1)
        result_alpha = a + old_alpha * (1 - a)
        mixed = values.copy()
        mixed[:, :3] = (incoming * a[:, None] + values[:, :3] * (old_alpha * (1 - a))[:, None]) / np.maximum(result_alpha[:, None], 1e-30)
        mixed[:, 3] = result_alpha * alpha_max(destination.dtype)
    else:
        mixed = incoming * a[:, None] + values * (1 - a[:, None])
    destination[mask] = cast_samples(mixed, destination.dtype)


def blend_annotation(destination, overlay, project, valid):
    alpha = overlay[..., 3].astype(np.float64) / 255.
    mask = (alpha > 0) & valid
    colors = color_samples(overlay[mask, :3], project, destination.ndim == 2)
    blend_samples(destination, colors, alpha, mask)


def native_source(source, project):
    if project.treatment == "keep":
        return source
    image = source.copy()
    masks = build_masks(project, source.shape[:2])
    selected = np.maximum.reduce(list(masks.values())) > 0
    value = color_samples(rgb(project.treatment_color), project, source.ndim == 2)
    if source.ndim == 3 and source.shape[2] == 4:
        value = np.append(value, alpha_max(source.dtype))
    image[selected] = cast_samples(value, source.dtype)
    return image


def paste_inset(destination, child, valid, x, y, parent_valid):
    """Place the native-precision inset, including fractional panel translations."""
    left, top = max(0, math.floor(x)), max(0, math.floor(y))
    right = min(destination.shape[1], math.ceil(x + child.shape[1]))
    bottom = min(destination.shape[0], math.ceil(y + child.shape[0]))
    if right <= left or bottom <= top:
        return
    alpha = valid.astype(np.float64)
    colors = child.astype(np.float64)
    if child.ndim == 3 and child.shape[2] == 4:
        alpha *= np.clip(colors[..., 3] / alpha_max(child.dtype), 0, 1)
        colors = colors[..., :3]
    premultiplied = colors * (alpha if colors.ndim == 2 else alpha[..., None])
    matrix = np.array([[1., 0., x - left], [0., 1., y - top]])
    size = (right - left, bottom - top)
    warped_alpha = cv2.warpAffine(alpha, matrix, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    warped = cv2.warpAffine(premultiplied, matrix, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    mask = (warped_alpha > 0) & parent_valid[top:bottom, left:right]
    colors = warped[mask] / (warped_alpha[mask] if colors.ndim == 2 else warped_alpha[mask, None])
    blend_samples(destination[top:bottom, left:right], colors, warped_alpha, mask)


def render_native(source, project, composition):
    if source.dtype == np.uint8 and project.display_low == 0 and project.display_high == 255:
        # The standard preview already has the full precision of an 8-bit source.
        rgba = qimage_to_array(render_image(composition))
        if source.ndim == 3 and source.shape[2] == 4:
            return rgba, composition.valid
        colors = rgba[..., :3].copy()
        if project.crop.background == "transparent":
            colors[~composition.valid] = 255
        data = cast_samples(colors @ np.array([.2126, .7152, .0722]), source.dtype) if source.ndim == 2 else colors
        return data, composition.valid
    data, valid, _ = data_crop(native_source(source, project), project)
    background = project.crop.background
    if background == "transparent" and data.ndim == 3 and data.shape[2] == 4:
        data[~valid, 3] = 0
    else:
        background = {"transparent": "#ffffff", "white": "#ffffff", "black": "#000000"}.get(background, background)
        value = color_samples(rgb(background), project, data.ndim == 2)
        if data.ndim == 3 and data.shape[2] == 4:
            value = np.append(value, alpha_max(data.dtype))
        data[~valid] = cast_samples(value, data.dtype)
    pending = []
    def flush():
        if pending:
            layer = Composition(np.zeros_like(composition.base), valid, list(pending), composition.k, composition.bbox)
            blend_annotation(data, qimage_to_array(render_image(layer)), project, valid)
            pending.clear()
    for primitive in composition.primitives:
        if primitive["type"] == "inset":
            flush()
            child_comp = primitive["composition"]
            child, child_valid = render_native(source, inset_project(project), child_comp)
            paste_inset(data, child, child_valid, primitive["x"], primitive["y"], valid)
        else:
            pending.append(primitive)
    flush()
    return data, valid


def write_native_figure(path, source, project, composition, metadata):
    data, valid = render_native(source, project, composition)
    suffix = source_suffix(project)
    metadata = {**metadata, "role": "source-format presentation", "output_dtype": str(data.dtype),
        "bit_depth": data.dtype.itemsize * 8, "annotations_applied": True,
        "display_mapping_baked_into_sample": False, "grayscale_annotations": data.ndim == 2,
        "transparent_outside": project.crop.background == "transparent" and data.ndim == 3 and data.shape[2] == 4,
        "annotation_mapping": "Display low/high map annotation colors into source values; grayscale uses Rec.709 luminance."}
    if suffix in (".tif", ".tiff"):
        tifffile.imwrite(path, data, photometric="minisblack" if data.ndim == 2 else "rgb", compression="deflate",
            resolution=(project.output.dpi, project.output.dpi), resolutionunit="INCH",
            metadata={"microscale": {k: value for k, value in metadata.items() if k != "recipe"}})
    else:
        encoded_data = cv2.cvtColor(data, cv2.COLOR_RGBA2BGRA if data.shape[2] == 4 else cv2.COLOR_RGB2BGR) if data.ndim == 3 else data
        parameters = [cv2.IMWRITE_JPEG_QUALITY, 98] if suffix in (".jpg", ".jpeg") else [cv2.IMWRITE_PNG_COMPRESSION, 6]
        ok, encoded = cv2.imencode(suffix, encoded_data, parameters)
        if not ok:
            raise OSError("Could not encode source-format figure.")
        encoded.tofile(str(path))
        if suffix in (".jpg", ".jpeg"):
            metadata["jpeg_quality"] = 98
            metadata["lossy_reencoding"] = True
    mask_path = path.with_name(path.stem + "_valid-mask.png")
    write_png(mask_path, valid.astype(np.uint8) * 255)
    metadata["validity_mask"] = mask_path.name
    atomic_json(str(path) + ".json", metadata)
    return [str(path), str(mask_path)]
