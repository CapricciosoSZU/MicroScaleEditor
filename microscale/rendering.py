"""One output-coordinate composition for preview, clipboard, PNG, TIFF and SVG."""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass, field
import json
import logging
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import tifffile
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen

from .geometry import bounds, crop_mask, format_length, output_geometry, positive, to_output
from .image_io import array_to_qimage, qimage_to_array, write_png, available_output
from .detection import build_masks
from .model import Crop, Output, atomic_json

log = logging.getLogger(__name__)


@dataclass
class Issue:
    severity: str
    message: str
    target: str
    rect: list | None = None


@dataclass
class Composition:
    base: np.ndarray
    valid: np.ndarray
    primitives: list
    k: float
    bbox: tuple
    issues: list = field(default_factory=list)
    scale_rect: list | None = None
    scale_length_px: float | None = None
    inset_rect: list | None = None


def rgb(color):
    c = QColor(color)
    if not c.isValid():
        raise ValueError(f"Invalid color: {color}")
    return [c.red(), c.green(), c.blue()]


def processed_source(rgba, project):
    image = rgba.copy()
    if project.treatment not in ("keep", "solid", "plate"):
        raise ValueError("Unknown old-scale treatment.")
    if project.treatment == "solid" and not project.pure_color_confirmed:
        raise ValueError("Confirm the selected mask is a uniform annotation background before clearing it.")
    if project.treatment in ("solid", "plate"):
        masks = build_masks(project, rgba.shape[:2])
        combined = np.maximum.reduce(list(masks.values())) > 0
        image[combined, :3] = rgb(project.treatment_color)
        image[combined, 3] = 255
    return image


def resample(image, size, k, nearest=False):
    if k == 1 and (image.shape[1], image.shape[0]) == size:
        return image.copy()
    # OpenCV pixel-center coordinates require the half-pixel offset. Use the
    # same k on both axes, even when the enclosing raster extent is rounded.
    transform = np.array([[k, 0., (k - 1) / 2], [0., k, (k - 1) / 2]], np.float64)
    return cv2.warpAffine(image, transform, size, flags=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def make_base(rgba, crop, output):
    bbox, k, size = output_geometry(crop, rgba.shape, output)
    x, y, x2, y2 = bbox
    base = resample(rgba[y:y2, x:x2], size, k)
    valid = resample(crop_mask(crop, rgba.shape).astype(np.uint8), size, k, True).astype(bool)
    if crop.background == "transparent":
        base[..., 3] = np.where(valid, base[..., 3], 0)
    else:
        color = {"white": "#ffffff", "black": "#000000"}.get(crop.background, crop.background)
        base[~valid] = [*rgb(color), 255]
    return base, valid, bbox, k


def font_for(style, output):
    size = output.font_pt / 72 * output.dpi if output.mode == "print" else style.font_size
    size = positive(size, "Font size")
    font = QFont(style.font)
    # Qt pixel size is integral; the actual size is recorded in SVG and checks.
    font.setPixelSize(max(1, round(size)))
    font.setBold(style.bold)
    return font


def scale_primitives(style, calibration, k, size, output):
    if not style.enabled:
        return [], None, None
    if calibration.usable_x is None:
        raise ValueError("A confirmed horizontal calibration is required for the scale bar.")
    length = positive(style.length_nm, "Scale length") * k / calibration.usable_x
    thickness = output.line_pt / 72 * output.dpi if output.mode == "print" else style.thickness
    thickness = positive(thickness, "Bar thickness")
    font = font_for(style, output)
    label = format_length(style.length_nm)
    fm = QFontMetricsF(font)
    text_bounds = fm.boundingRect(label)
    tw, th = text_bounds.width(), text_bounds.height()
    pad = max(4., thickness) if style.plate else 0.
    cap = thickness * 2 if style.endcaps else 0.
    bar_height = thickness + cap * 2
    content_width = max(length + (thickness if style.endcaps else 0), tw)
    width, height = content_width + 2 * pad, bar_height + style.gap + th + 2 * pad
    if style.anchor == "custom":
        x, y = style.x, style.y
    else:
        vertical, horizontal = style.anchor.split("-")
        x = style.margin if horizontal == "left" else (size[0] - width) / 2 if horizontal == "center" else size[0] - style.margin - width
        y = style.margin if vertical == "top" else (size[1] - height) / 2 if vertical == "middle" else size[1] - style.margin - height
    primitives = []
    if style.plate:
        primitives.append({"type": "rect", "rect": [x, y, width, height], "color": style.plate_color, "opacity": style.plate_opacity, "role": "scale-background"})
    bx = x + (width - length) / 2
    by = y + pad + cap + (th + style.gap if style.text_position == "above" else 0)
    primitives.append({"type": "rect", "rect": [bx, by, length, thickness], "color": style.color, "role": "scale-bar"})
    if style.endcaps:
        for ex in (bx, bx + length):
            primitives.append({"type": "rect", "rect": [ex - thickness / 2, by - cap, thickness, bar_height], "color": style.color, "role": "scale-endcap"})
    ty = y + pad if style.text_position == "above" else by + thickness + cap + style.gap
    tx = x + (width - tw) / 2
    primitives.append({"type": "text", "text": label, "x": tx - text_bounds.left(), "y": ty - text_bounds.top(),
                       "font": style.font, "size": font.pixelSize(), "bold": style.bold, "color": style.color, "role": "scale-label"})
    return primitives, [x, y, width, height], length


def contained(rect, valid):
    x, y, w, h = rect
    if not np.isfinite(rect).all() or x < -1e-7 or y < -1e-7 or x + w > valid.shape[1] + 1e-7 or y + h > valid.shape[0] + 1e-7:
        return False
    x1, y1, x2, y2 = math.floor(x), math.floor(y), math.ceil(x + w), math.ceil(y + h)
    return x2 > x1 and y2 > y1 and bool(valid[y1:y2, x1:x2].all())


def roi_points(crop):
    if crop.kind in ("polygon", "freehand"):
        return crop.points
    x, y, w, h = crop.rect
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def compose(rgba, project, original=False, include_inset=True):
    started = time.perf_counter()
    pixels = rgba if original else processed_source(rgba, project)
    base, valid, bbox, k = make_base(pixels, project.crop, project.output)
    composition = Composition(base, valid, [], k, bbox)
    if original:
        return composition
    width, height = base.shape[1], base.shape[0]
    c = project.calibration
    if c.status != "Confirmed":
        composition.issues.append(Issue("error" if project.style.enabled else "info", "Calibration is unavailable or pending. Physical bars require confirmation; uncalibrated image export is allowed.", "calibration"))
    try:
        prim, rect, length = scale_primitives(project.style, c, k, (width, height), project.output)
        composition.primitives.extend(prim)
        composition.scale_rect, composition.scale_length_px = rect, length
        if rect and not contained(rect, valid):
            composition.issues.append(Issue("error", "Scale bar, label or background is outside the valid crop. Move it or change physical length/crop.", "scale", rect))
        if length and length < 15:
            composition.issues.append(Issue("warning", f"Short scale bar: {length:.2f} output pixels.", "scale", rect))
        if project.style.enabled and font_for(project.style, project.output).pixelSize() < 12:
            composition.issues.append(Issue("warning", "Scale text is smaller than 12 output pixels.", "scale", rect))
        if length and not math.isclose(length * c.usable_x / k, project.style.length_nm, rel_tol=1e-10):
            composition.issues.append(Issue("error", "Scale geometry and physical label disagree.", "scale", rect))
    except ValueError as exc:
        composition.issues.append(Issue("error", str(exc), "scale"))
    if project.output.label:
        font = font_for(project.style, project.output)
        fm = QFontMetricsF(font)
        tr = fm.boundingRect(project.output.label)
        x, y = project.output.label_x, project.output.label_y
        rect = [x, y, tr.width(), tr.height()]
        composition.primitives.append({"type": "text", "text": project.output.label, "x": x - tr.left(), "y": y - tr.top(), "font": project.style.font,
                                       "size": font.pixelSize(), "bold": project.style.bold, "color": project.style.color, "role": "panel-label"})
        if not contained(rect, valid):
            composition.issues.append(Issue("error", "Panel label is outside the valid crop.", "panel-label", rect))
    if project.inset.enabled and include_inset:
        ins = project.inset
        child_project = inset_project(project)
        child = compose(rgba, child_project, include_inset=False)
        iw, ih = child.base.shape[1], child.base.shape[0]
        composition.inset_rect = [ins.x, ins.y, iw, ih]
        if not contained(composition.inset_rect, valid):
            composition.issues.append(Issue("error", "Inset panel is outside the valid main crop.", "inset", composition.inset_rect))
        composition.primitives.append({"type": "inset", "composition": child, "x": ins.x, "y": ins.y, "role": "inset"})
        for issue in child.issues:
            if issue.severity != "info":
                composition.issues.append(Issue(issue.severity, "Inset: " + issue.message, "inset", composition.inset_rect))
        pts = [to_output(p, bbox, k) for p in roi_points(ins.roi)]
        if ins.roi.kind in ("circle", "ellipse"):
            a, b, rw, rh = ins.roi.rect
            composition.primitives.append({"type": "ellipse", "rect": [*to_output([a, b], bbox, k), rw * k, rh * k], "color": ins.border_color, "width": 2., "role": "inset-source-roi"})
        else:
            composition.primitives.append({"type": "path", "points": pts, "closed": True, "color": ins.border_color, "width": 2., "role": "inset-source-roi"})
        composition.primitives.append({"type": "ellipse" if ins.circular else "outline", "rect": composition.inset_rect, "color": ins.border_color, "width": 2., "role": "inset-border"})
    if project.output.export_guides:
        for measure in project.measurements:
            composition.primitives.append({"type": "path", "points": [to_output(p, bbox, k) for p in measure["points"]], "closed": False, "color": "#37d5ee", "width": 1., "role": "measurement"})
        for points in project.protected:
            composition.primitives.append({"type": "path", "points": [to_output(p, bbox, k) for p in points], "closed": True, "color": "#ff5d73", "width": 1., "role": "protected-guide"})
    _spatial_checks(project, composition, rgba.shape)
    log.debug("Compose %.3fs source=%s output=%sx%s k=%s calibration=%s", time.perf_counter() - started, rgba.shape, width, height, k, c.sx)
    return composition


def inset_project(project):
    child = deepcopy(project)
    child.crop = deepcopy(project.inset.roi)
    child.crop.kind = "circle" if project.inset.circular else "rectangle"
    if project.inset.circular and not math.isclose(child.crop.rect[2], child.crop.rect[3], abs_tol=.01):
        raise ValueError("Circular inset requires a square source ROI. Adjust the ROI; sample data is never stretched.")
    child.crop.background = "transparent"
    child.output = Output(mode="width", width_px=round(project.inset.width), dpi=project.output.dpi)
    if project.output.mode == "print":
        child.output.mode = "print"
        child.output.width_mm = project.inset.width / project.output.dpi * 25.4
        child.output.font_pt = project.output.font_pt
        child.output.line_pt = project.output.line_pt
    child.style = deepcopy(project.inset.style)
    child.inset.enabled = False
    child.protected = []
    child.measurements = []
    return child


def _spatial_checks(project, comp, shape):
    masks = build_masks(project, shape[:2]) if project.masks or project.candidates or project.protected else None
    combined = np.maximum.reduce(list(masks.values())) > 0 if masks else np.zeros((1, 1), bool)
    x, y, x2, y2 = comp.bbox
    retained = crop_mask(project.crop, shape)
    for i, points in enumerate(project.protected):
        protection = np.zeros(shape[:2], np.uint8)
        cv2.fillPoly(protection, [np.round(points).astype(np.int32)], 1)
        local = protection[y:y2, x:x2].astype(bool)
        kept = retained
        pts = np.asarray([to_output(point, comp.bbox, comp.k) for point in points])
        low, high = pts.min(0), pts.max(0)
        protection_rect = [*low.tolist(), *(high - low).tolist()]
        if int((local & kept).sum()) < int(protection.sum()):
            comp.issues.append(Issue("warning", f"Protected region {i + 1} is touched by the crop boundary.", "protected", protection_rect))
        if project.treatment != "keep" and (protection.astype(bool) & combined).any():
            comp.issues.append(Issue("warning", f"Old-scale treatment overlaps protected region {i + 1}.", "protected", protection_rect))
        out = resample(protection[y:y2, x:x2], (comp.base.shape[1], comp.base.shape[0]), comp.k, True) > 0
        annotations = [("scale", comp.scale_rect), ("inset", comp.inset_rect)]
        for primitive in comp.primitives:
            if primitive.get("role") == "panel-label":
                font = font_for(project.style, project.output)
                tr = QFontMetricsF(font).boundingRect(primitive["text"])
                annotations.append(("panel label", [primitive["x"] + tr.left(), primitive["y"] + tr.top(), tr.width(), tr.height()]))
        for name, rect in annotations:
            if rect:
                a, b, w, h = rect
                if out[max(0, math.floor(b)):max(0, math.ceil(b + h)), max(0, math.floor(a)):max(0, math.ceil(a + w))].any():
                    comp.issues.append(Issue("warning", f"{name.title()} overlaps protected region {i + 1}.", name, rect))
    for candidate in project.candidates:
        if candidate.get("ignored"):
            continue
        bx, by, bw, bh = candidate["line_rect"]
        text = np.asarray(candidate.get("text_points") or [[bx, by], [bx + bw, by + bh]])
        ax, ay = max(x, math.floor(min(bx, text[:, 0].min()))), max(y, math.floor(min(by, text[:, 1].min())))
        ax2, ay2 = min(x2, math.ceil(max(bx + bw, text[:, 0].max()))), min(y2, math.ceil(max(by + bh, text[:, 1].max())))
        if ax2 <= ax or ay2 <= ay:
            continue
        local_candidate = deepcopy(candidate)
        local_candidate["line_rect"] = [bx - ax, by - ay, bw, bh]
        local_candidate["text_points"] = (text - [ax, ay]).tolist() if candidate.get("text_points") else []
        regions = candidate_masks_local(local_candidate, (ay2 - ay, ax2 - ax))
        remains = regions & retained[ay - y:ay2 - y, ax - x:ax2 - x]
        if project.treatment != "keep" and combined.shape == shape[:2]:
            remains &= ~combined[ay:ay2, ax:ax2]
        if remains.any():
            comp.issues.append(Issue("warning", "A known old-scale candidate remains. Inspect the line and associated text; detection is not exhaustive.", "old-scale", [*to_output([bx, by], comp.bbox, comp.k), bw * comp.k, bh * comp.k]))
    comp.issues.append(Issue("info", f"Presentation: 8-bit RGBA; fixed display mapping {project.display_low:g}…{project.display_high:g}. Data TIFF retains source dtype {project.source_dtype}. Transparency={'yes' if (comp.base[..., 3] < 255).any() else 'no'}.", "output"))
    if project.calibration.usable_x:
        comp.issues.append(Issue("info", f"Output calibration: sx={project.calibration.usable_x / comp.k:.9g} nm/px; k={comp.k:.9g}. Screen zoom and DPI metadata do not enter sample calibration.", "calibration"))


def candidate_masks_local(candidate, shape):
    from .detection import candidate_masks
    from .model import Project
    p = Project(masks=candidate_masks(candidate))
    return np.maximum.reduce(list(build_masks(p, shape).values())) > 0


def paint_primitive(painter, primitive):
    p = primitive
    painter.save()
    painter.setOpacity(float(p.get("opacity", 1)))
    color = QColor(p.get("color", "#ffffff"))
    painter.setPen(QPen(color, p.get("width", 1.)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    kind = p["type"]
    if kind == "rect":
        painter.fillRect(QRectF(*p["rect"]), color)
    elif kind in ("ellipse", "outline"):
        if kind == "ellipse":
            painter.drawEllipse(QRectF(*p["rect"]))
        else:
            painter.drawRect(QRectF(*p["rect"]))
    elif kind == "text":
        font = QFont(p["font"])
        font.setPixelSize(p["size"])
        font.setBold(p["bold"])
        # Rasterize glyph outlines consistently. Native screen text engines can
        # vary a handful of antialiased pixels between Windows processes.
        path = QPainterPath()
        path.addText(QPointF(p["x"], p["y"]), font, p["text"])
        painter.fillPath(path, color)
    elif kind == "path":
        path = QPainterPath()
        if p["points"]:
            path.moveTo(*p["points"][0])
            for point in p["points"][1:]:
                path.lineTo(*point)
            if p["closed"]:
                path.closeSubpath()
            painter.drawPath(path)
    elif kind == "inset":
        painter.drawImage(QPointF(p["x"], p["y"]), render_image(p["composition"]))
    painter.restore()


def render_image(composition):
    image = array_to_qimage(composition.base)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        for primitive in composition.primitives:
            paint_primitive(painter, primitive)
    finally:
        painter.end()
    # Auxiliary ROI strokes can cross outside the crop; all composition respects
    # actual shape coverage, not a rectangular screenshot or checkerboard.
    data = qimage_to_array(image)
    data[~composition.valid] = composition.base[~composition.valid]
    return array_to_qimage(data)


def change_view(original, result):
    a, b = qimage_to_array(render_image(original)), qimage_to_array(render_image(result))
    changed = np.any(a != b, axis=2) & result.valid
    out = a.copy()
    out[changed, :3] = (out[changed, :3].astype(float) * .35 + np.array([255, 65, 155]) * .65).astype(np.uint8)
    return array_to_qimage(out)


def export_svg(path, comp):
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    def element(tag, attrs=None, parent=None):
        return ET.SubElement(parent, f"{{{ns}}}{tag}", {k: str(v) for k, v in (attrs or {}).items()}) if parent is not None else ET.Element(f"{{{ns}}}{tag}", {k: str(v) for k, v in (attrs or {}).items()})
    root = element("svg", {"width": comp.base.shape[1], "height": comp.base.shape[0], "viewBox": f"0 0 {comp.base.shape[1]} {comp.base.shape[0]}"})
    element("title", parent=root).text = "MicroScale Editor: raster sample with editable vector annotations"
    def build(parent, composition, prefix):
        height, width = composition.valid.shape
        # Coverage encoded as a PNG alpha mask; sample remains a raster object.
        mask_rgba = np.full((height, width, 4), 255, np.uint8)
        mask_rgba[..., 3] = composition.valid.astype(np.uint8) * 255
        def data_uri(array):
            ok, encoded = cv2.imencode(".png", cv2.cvtColor(array, cv2.COLOR_RGBA2BGRA))
            if not ok:
                raise OSError("Could not embed SVG raster.")
            return "data:image/png;base64," + base64.b64encode(encoded).decode("ascii")
        element("image", {"id": prefix + "sample", "width": width, "height": height, "href": data_uri(composition.base)}, parent)
        defs = element("defs", parent=parent)
        mask = element("mask", {"id": prefix + "crop-mask", "maskUnits": "userSpaceOnUse", "x": 0, "y": 0, "width": width, "height": height}, defs)
        element("image", {"width": width, "height": height, "href": data_uri(mask_rgba)}, mask)
        group = element("g", {"mask": f"url(#{prefix}crop-mask)"}, parent)
        for i, p in enumerate(composition.primitives):
            attrs = {"id": prefix + p.get("role", "annotation") + f"-{i}", "opacity": p.get("opacity", 1)}
            if p["type"] == "rect":
                x, y, w, h = p["rect"]
                element("rect", {**attrs, "x": x, "y": y, "width": w, "height": h, "fill": p["color"]}, group)
            elif p["type"] == "text":
                element("text", {**attrs, "x": p["x"], "y": p["y"], "font-family": p["font"], "font-size": p["size"], "font-weight": "bold" if p["bold"] else "normal", "fill": p["color"]}, group).text = p["text"]
            elif p["type"] in ("ellipse", "outline"):
                x, y, w, h = p["rect"]
                geometry = {"cx": x + w / 2, "cy": y + h / 2, "rx": w / 2, "ry": h / 2} if p["type"] == "ellipse" else {"x": x, "y": y, "width": w, "height": h}
                element("ellipse" if p["type"] == "ellipse" else "rect", {**attrs, **geometry, "fill": "none", "stroke": p["color"], "stroke-width": p["width"]}, group)
            elif p["type"] == "path":
                points = p["points"]
                d = "M " + " L ".join(f"{pt[0]} {pt[1]}" for pt in points) + (" Z" if p["closed"] else "")
                element("path", {**attrs, "d": d, "fill": "none", "stroke": p["color"], "stroke-width": p["width"]}, group)
            elif p["type"] == "inset":
                inner = element("g", {**attrs, "transform": f"translate({p['x']} {p['y']})"}, group)
                build(inner, p["composition"], prefix + "inset-")
    build(root, comp, "main-")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def data_crop(source, project):
    bbox, k, size = output_geometry(project.crop, source.shape, project.output)
    x, y, x2, y2 = bbox
    crop = source[y:y2, x:x2]
    if k == 1:
        return crop.copy(), crop_mask(project.crop, source.shape), k
    original_dtype = crop.dtype
    working = crop.astype(np.float64) if original_dtype not in (np.uint8, np.uint16, np.int16, np.float32, np.float64) else crop
    data = resample(working, size, k)
    if data.dtype != original_dtype:
        data = data.astype(original_dtype)
    return data, resample(crop_mask(project.crop, source.shape).astype(np.uint8), size, k, True).astype(bool), k


def export_file(path, source, rgba, project, kind="png", progress=lambda n, s: None):
    started = time.perf_counter()
    progress(10, "Rendering from source pixels and recorded parameters")
    comp = compose(rgba, project, original=(kind == "data-tiff"))
    errors = [issue.message for issue in comp.issues if issue.severity == "error"]
    if kind != "data-tiff" and errors:
        raise ValueError("Export check failed:\n" + "\n".join(errors))
    path = available_output(path, (project.source_path, project.reference.get("path")))
    meta = {"software": "MicroScale Editor", "unit": "nm", "status": project.calibration.status,
            "sx": project.calibration.usable_x / comp.k if project.calibration.usable_x else None,
            "sy": project.calibration.usable_y / comp.k if project.calibration.usable_y else None,
            "k": comp.k, "source_hash": project.source_hash, "source_dtype": str(source.dtype),
            "display_low": project.display_low, "display_high": project.display_high,
            "scale_length_px": comp.scale_length_px, "scale_length_nm": project.style.length_nm if project.style.enabled else None,
            "warnings": [i.message for i in comp.issues if i.severity == "warning"], "recipe": project.to_dict()}
    outputs = []
    progress(55, "Writing independent output files")
    if kind in ("data-tiff", "tiff"):
        data, valid, k = data_crop(source, project)
        data_path = path if kind == "data-tiff" else available_output(path.with_name(path.stem + "_data.tif"), (project.source_path, project.reference.get("path")))
        tifffile.imwrite(data_path, data, metadata={"microscale": {**{key: value for key, value in meta.items() if key != "recipe"}, "role": "unaltered data crop" if k == 1 else "resampled data crop"}}, photometric="rgb" if data.ndim == 3 else "minisblack")
        outputs.append(str(data_path))
        validity_path = data_path.with_name(data_path.stem + "_valid-mask.png")
        # data pixels outside an irregular ROI remain in the bbox data file;
        # the explicit companion mask identifies the scientific retained region.
        ok, encoded = cv2.imencode(".png", valid.astype(np.uint8) * 255)
        if not ok:
            raise OSError("Cannot encode validity mask.")
        encoded.tofile(str(validity_path))
        outputs.append(str(validity_path))
        atomic_json(str(data_path) + ".json", {**meta, "role": "data", "validity_mask": validity_path.name, "treatments_applied": False})
    if kind == "svg":
        export_svg(path, comp)
    elif kind == "png":
        image = render_image(comp)
        image.setDotsPerMeterX(round(project.output.dpi / .0254))
        image.setDotsPerMeterY(round(project.output.dpi / .0254))
        if not image.save(str(path), "PNG"):
            raise OSError("Cannot save PNG.")
    elif kind == "tiff":
        tifffile.imwrite(path, qimage_to_array(render_image(comp)), photometric="rgb", resolution=(project.output.dpi, project.output.dpi), resolutionunit="INCH", metadata={"microscale": {**{key: value for key, value in meta.items() if key != "recipe"}, "role": "8-bit presentation"}})
    elif kind != "data-tiff":
        raise ValueError("Unknown export format.")
    if kind != "data-tiff":
        outputs.insert(0, str(path))
        atomic_json(str(path) + ".json", {**meta, "role": "presentation", "outputs": [Path(p).name for p in outputs]})
    progress(100, "Export complete")
    log.info("Export %.3fs kind=%s outputs=%s source=%s k=%s", time.perf_counter() - started, kind, outputs, source.shape, comp.k)
    return outputs
