"""Pure sample calibration and geometry. Lengths: nm; coordinates: pixel edges."""
from __future__ import annotations

import math
import re
import cv2
import numpy as np

UNITS = {"nm": 1.0, "μm": 1000.0, "µm": 1000.0, "um": 1000.0, "Å": .1, "A": .1, "å": .1}


def positive(value: float, name: str = "Value") -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite.")
    return value


def parse_length(text: str) -> float:
    text = text.strip()
    if any(t in text for t in ("⁻", "−", "^-", "1/", "/nm", "/Å")) or re.search(r"(?:nm|μm|µm|um|Å)\s*-1", text):
        raise ValueError("Reciprocal units are not supported in real-space length mode.")
    match = re.fullmatch(r"\s*([+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(nm|μm|µm|um|Å|å|A)\s*", text)
    if not match:
        raise ValueError("Enter a positive real-space length, e.g. 5 nm, 0.5 μm or 10 Å.")
    return positive(float(match[1]) * UNITS[match[2]], "Length")


def format_length(nm: float) -> str:
    positive(nm, "Length")
    return f"{nm / 1000:g} μm" if nm >= 500 else f"{nm:g} nm"


def calibrate(length_nm: float, p1, p2) -> float:
    return positive(length_nm, "Length") / positive(math.dist(p1, p2), "Endpoint distance")


def suggestions(span_nm: float) -> list[float]:
    if not math.isfinite(span_nm) or span_nm <= 0:
        return []
    power = math.floor(math.log10(span_nm))
    return [m * 10.0**e for e in range(power - 3, power + 1) for m in (1, 2, 5)
            if .025 * span_nm <= m * 10.0**e <= .4 * span_nm]


def normalized_rect(p1, p2, ratio: float | None = None):
    x1, y1 = p1
    dx, dy = p2[0] - x1, p2[1] - y1
    if ratio:
        positive(ratio, "Aspect ratio")
        w, h = abs(dx), abs(dy)
        if h == 0 or w / max(h, 1e-15) > ratio:
            h = w / ratio
        else:
            w = h * ratio
        dx, dy = math.copysign(w, dx), math.copysign(h, dy)
    return [min(x1, x1 + dx), min(y1, y1 + dy), abs(dx), abs(dy)]


def constrain_rect(rect, shape):
    """Fit an ROI within the source while retaining its aspect ratio."""
    x, y, w, h = rect
    if min(w, h) <= 0:
        return rect
    factor = min(1., shape[1] / w, shape[0] / h)
    w, h = w * factor, h * factor
    return [min(max(0., x), shape[1] - w), min(max(0., y), shape[0] - h), w, h]


def polygon_valid(points):
    if len(points) < 3 or not np.isfinite(points).all():
        return False
    pts = np.asarray(points, dtype=float)
    if abs(cv2.contourArea(pts.astype(np.float32))) < 1:
        return False
    def cross(a, b, c):
        u, v = b - a, c - a
        return u[0] * v[1] - u[1] * v[0]
    n = len(pts)
    if any(np.linalg.norm(pts[i] - pts[(i + 1) % n]) < 1e-7 for i in range(n)):
        return False
    for i in range(n):
        for j in range(i + 1, n):
            if j in (i, (i + 1) % n) or i == (j + 1) % n:
                continue
            a, b, c, d = pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n]
            if cross(a, b, c) * cross(a, b, d) <= 0 and cross(c, d, a) * cross(c, d, b) <= 0:
                if max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0])) and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1])):
                    return False
    return True


def bounds(crop, shape):
    h, w = shape[:2]
    if crop.kind in ("polygon", "freehand"):
        if not polygon_valid(crop.points):
            raise ValueError("Polygon is empty, self-intersecting or invalid. Move/delete vertices.")
        pts = np.array(crop.points)
        x, y = pts.min(axis=0)
        x2, y2 = pts.max(axis=0)
    else:
        x, y, cw, ch = crop.rect
        if not np.isfinite(crop.rect).all() or min(cw, ch) <= 0:
            raise ValueError("Crop width and height must be positive and finite.")
        x2, y2 = x + cw, y + ch
    # Half-open integer bbox. No iterative coordinate rounding in project state.
    x, y, x2, y2 = max(0, math.floor(x)), max(0, math.floor(y)), min(w, math.ceil(x2)), min(h, math.ceil(y2))
    if x2 <= x or y2 <= y:
        raise ValueError("Crop does not intersect the source image.")
    return x, y, x2, y2


def crop_mask(crop, shape):
    x, y, x2, y2 = bounds(crop, shape)
    yy, xx = np.mgrid[y:y2, x:x2].astype(float)
    xx += .5
    yy += .5
    if crop.kind in ("circle", "ellipse"):
        a, b, w, h = crop.rect
        valid = ((xx - a - w / 2) / (w / 2))**2 + ((yy - b - h / 2) / (h / 2))**2 <= 1
    elif crop.kind in ("polygon", "freehand"):
        # Scanline even/odd test at pixel centers, independent of viewport zoom.
        valid = np.zeros(xx.shape, bool)
        for p, q in zip(crop.points, crop.points[1:] + crop.points[:1]):
            if p[1] != q[1]:
                valid ^= ((p[1] > yy) != (q[1] > yy)) & (xx < (q[0] - p[0]) * (yy - p[1]) / (q[1] - p[1]) + p[0])
    else:
        a, b, w, h = crop.rect
        valid = (xx >= a) & (xx < a + w) & (yy >= b) & (yy < b + h)
    return valid


def output_geometry(crop, shape, output):
    x, y, x2, y2 = bounds(crop, shape)
    width, height = x2 - x, y2 - y
    if output.mode == "print":
        target = positive(output.width_mm, "Panel width") / 25.4 * positive(output.dpi, "DPI")
        target = max(1, round(target))
        k = target / width
    elif output.mode == "width":
        k = positive(output.width_px, "Output width") / width
    else:
        k = positive(output.scale, "Output scale")
    # The raster extent is rounded; sampling uses a single k in both directions.
    ow, oh = max(1, round(width * k)), max(1, round(height * k))
    if ow * oh > 150_000_000:
        raise ValueError("Output exceeds 150 megapixels. Reduce the output dimensions.")
    return (x, y, x2, y2), k, (ow, oh)


def to_output(point, origin, k):
    return [(point[0] - origin[0]) * k, (point[1] - origin[1]) * k]


def to_source(point, origin, k):
    return [point[0] / k + origin[0], point[1] / k + origin[1]]


def distance(p1, p2, sx=None, sy=None):
    dx, dy = abs(p2[0] - p1[0]), abs(p2[1] - p1[1])
    if (dx > 1e-8 and sx is None) or (dy > 1e-8 and sy is None):
        return math.hypot(dx, dy), "px"
    return math.hypot(dx * (sx or 0), dy * (sy or 0)), "nm"
