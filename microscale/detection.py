"""Local candidate evidence, editable masks and conservative content registration."""
from __future__ import annotations

import logging
import math
import re
import threading
import time
import importlib

import cv2
import numpy as np

from .geometry import parse_length, polygon_valid

log = logging.getLogger(__name__)
_ocr = None
_ocr_lock = threading.Lock()


def gray8(rgba):
    if rgba.ndim == 2:
        return rgba.astype(np.uint8)
    return cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY)


def local_ocr(rgb):
    """Optional backend, bundled local ONNX models; no network call or account."""
    global _ocr
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError("OCR unavailable. Install: .venv\\Scripts\\python -m pip install -r requirements-ocr.txt. Manual endpoints and masks remain available.") from exc
    with _ocr_lock:
        if _ocr is None:
            class LocalRapidOCR(RapidOCR):
                @staticmethod
                def init_module(module_name, class_name):
                    # RapidOCR 1.2 uses top-level dynamic imports via sys.path.
                    # Package-qualified imports work in source and frozen builds.
                    name = module_name if module_name.startswith("rapidocr_onnxruntime.") else "rapidocr_onnxruntime." + module_name
                    return getattr(importlib.import_module(name), class_name)
            # RapidOCR 1.2.x ignores thread-count kwargs. Bound its local ONNX
            # session factory during construction; never alter installed files.
            import rapidocr_onnxruntime.utils as ort_utils
            factory = getattr(ort_utils, "SessionOptions", None)
            if factory is not None:
                def options():
                    value = factory()
                    value.intra_op_num_threads = 2
                    value.inter_op_num_threads = 1
                    value.add_session_config_entry("session.intra_op.allow_spinning", "0")
                    value.add_session_config_entry("session.inter_op.allow_spinning", "0")
                    return value
                ort_utils.SessionOptions = options
            try:
                _ocr = LocalRapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
            finally:
                if factory is not None:
                    ort_utils.SessionOptions = factory
        result, _ = _ocr(cv2.cvtColor(rgb[..., :3], cv2.COLOR_RGB2BGR))
    return [{"points": np.asarray(box).tolist(), "text": text, "confidence": float(score)} for box, text, score in (result or [])]


def detect(rgba, region=None, use_ocr=True, progress=lambda n, s: None):
    started = time.perf_counter()
    h, w = rgba.shape[:2]
    x0, y0, x2, y2 = (0, 0, w, h) if region is None else [int(v) for v in region]
    x0, y0, x2, y2 = max(0, x0), max(0, y0), min(w, x2), min(h, y2)
    roi = rgba[y0:y2, x0:x2]
    if roi.size == 0:
        raise ValueError("Detection region is empty.")
    gray = gray8(roi)
    progress(15, "Finding bright and dark horizontal segments")
    lines = []
    for polarity, threshold in (("bright", cv2.THRESH_BINARY), ("dark", cv2.THRESH_BINARY_INV)):
        _, binary = cv2.threshold(gray, 0, 255, threshold | cv2.THRESH_OTSU)
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((1, max(12, int(gray.shape[1] * .025))), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(opened)
        for label in range(1, count):
            x, y, bw, bh, area = stats[label].tolist()
            if bw < 12 or bh > max(18, gray.shape[0] * .025) or bw / max(bh, 1) < 4 or bw > .9 * gray.shape[1]:
                continue
            # A long specimen edge remains a low-confidence candidate without length text.
            lines.append({"endpoints": [[float(x + x0), float(y + y0 + bh / 2)], [float(x + x0 + bw), float(y + y0 + bh / 2)]],
                          "line_rect": [x + x0, y + y0, bw, bh], "polarity": polarity, "length_nm": None,
                          "text": "", "text_points": [], "confidence": .15,
                          "rule": "Solid-bar outer edges; inspect end ticks manually before confirmation."})
    progress(40, "Reading nearby text with local OCR")
    texts, warning = [], ""
    if use_ocr:
        try:
            texts = local_ocr(roi)
            for item in texts:
                item["points"] = (np.array(item["points"]) + [x0, y0]).tolist()
            reciprocal = [item["text"] for item in texts if any(token in item["text"] for token in ("⁻", "1/nm", "1/Å", "nm-1", "Å-1", "nm^-", "Å^-"))]
            if reciprocal:
                warning = "Reciprocal-space units detected: " + ", ".join(reciprocal) + ". This editor supports real-space lengths only; no calibration was inferred from that text."
        except Exception as exc:
            warning = str(exc)
            log.exception("OCR failed; retaining manual workflow")
    for line in lines:
        x, y, bw, bh = line["line_rect"]
        matches = []
        for item in texts:
            pts = np.asarray(item["points"])
            tx, ty = pts.mean(axis=0)
            text = item["text"].replace("O", "0")
            if abs(tx - x - bw / 2) > max(bw * .9, 60) or abs(ty - y) > max(90, h * .12):
                continue
            try:
                nm = parse_length(text)
            except ValueError:
                continue
            d = abs(ty - y) + .3 * abs(tx - x - bw / 2)
            matches.append((d, nm, item))
        if matches:
            _, nm, item = min(matches, key=lambda m: m[0])
            line.update(length_nm=nm, text=item["text"], text_points=item["points"], confidence=min(.95, .5 + .45 * item["confidence"]))
    lines.sort(key=lambda item: item["confidence"], reverse=True)
    progress(100, f"{len(lines)} segment candidates; manual confirmation required")
    log.info("Detection %.3fs shape=%s candidates=%d text=%d", time.perf_counter() - started, rgba.shape, len(lines), len(texts))
    return {"candidates": lines[:100], "texts": texts, "warning": warning}


def candidate_masks(candidate):
    strokes = [{"layer": "line", "kind": "rect", "rect": candidate["line_rect"], "erase": False}]
    if candidate.get("text_points"):
        strokes.append({"layer": "text", "kind": "polygon", "points": candidate["text_points"], "erase": False})
    return strokes


def build_masks(project, shape):
    h, w = shape[:2]
    masks = {name: np.zeros((h, w), np.uint8) for name in ("line", "text", "background")}
    for stroke in project.masks:
        mask = masks[stroke["layer"]]
        color = 0 if stroke.get("erase") else 255
        if stroke["kind"] == "rect":
            x, y, width, height = stroke["rect"]
            x1, y1, x2, y2 = max(0, math.floor(x)), max(0, math.floor(y)), min(w, math.ceil(x + width)), min(h, math.ceil(y + height))
            if x2 > x1 and y2 > y1:
                mask[y1:y2, x1:x2] = color
        elif stroke["kind"] == "polygon":
            cv2.fillPoly(mask, [np.round(stroke["points"]).astype(np.int32)], color)
        else:
            points = np.round(stroke["points"]).astype(np.int32)
            radius = max(1, round(stroke.get("radius", 5)))
            if len(points) > 1:
                cv2.polylines(mask, [points], False, color, radius * 2)
            for point in points:
                cv2.circle(mask, tuple(point), radius, color, -1)
    for layer, iterations in project.mask_morph.items():
        if iterations:
            op = cv2.dilate if iterations > 0 else cv2.erode
            masks[layer] = op(masks[layer], np.ones((3, 3), np.uint8), iterations=abs(int(iterations)))
    return masks


def _fit_pairs(reference_points, work_points):
    ref = np.asarray(reference_points, dtype=np.float64)
    work = np.asarray(work_points, dtype=np.float64)
    if len(ref) < 3 or len(ref) != len(work) or not np.isfinite(ref).all() or not np.isfinite(work).all():
        raise ValueError("Provide at least three corresponding, non-collinear points in reference and source order.")
    if np.linalg.matrix_rank(ref - ref.mean(0), tol=1e-3) < 2:
        raise ValueError("Corresponding points must span a two-dimensional region.")
    matrix, inliers = cv2.estimateAffinePartial2D(ref, work, method=cv2.RANSAC, ransacReprojThreshold=2.5, maxIters=5000, confidence=.999, refineIters=20)
    if matrix is None:
        raise ValueError("Cannot fit a reliable similarity transform.")
    r = math.hypot(matrix[0, 0], matrix[1, 0])
    angle = math.degrees(math.atan2(matrix[1, 0], matrix[0, 0]))
    if r <= 0 or abs(angle) > .5:
        raise ValueError(f"Rotation ({angle:.2f}°), reflection or invalid scale detected. This version supports translation and uniform scaling only.")
    # Refit permitted geometry exactly: one positive sampling factor + translation.
    good = inliers.ravel().astype(bool)
    a, b = ref[good], work[good]
    ac, bc = a - a.mean(0), b - b.mean(0)
    r = float((ac * bc).sum() / (ac * ac).sum())
    translation = b.mean(0) - r * a.mean(0)
    matrix = np.array([[r, 0., translation[0]], [0., r, translation[1]]])
    residual = np.linalg.norm(ref * r + translation - work, axis=1)
    return matrix, good, residual


def register(reference_rgba, work_rgba, manual=None, progress=lambda n, s: None):
    started = time.perf_counter()
    ref, work = gray8(reference_rgba), gray8(work_rgba)
    progress(10, "Matching image content")
    if manual is None:
        # Common working resolution makes 1x / 2x versions equally identifiable.
        scales = [min(1., 1600 / max(im.shape)) for im in (ref, work)]
        images = [cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1 else im for im, s in zip((ref, work), scales)]
        sift = cv2.SIFT_create(nfeatures=5000, contrastThreshold=.025)
        kp1, d1 = sift.detectAndCompute(images[0], None)
        kp2, d2 = sift.detectAndCompute(images[1], None)
        if d1 is None or d2 is None:
            raise ValueError("Insufficient image texture. Use manual corresponding points.")
        pairs = cv2.BFMatcher().knnMatch(d1, d2, k=2)
        matches = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < .7 * b.distance]
        if len(matches) < 12:
            raise ValueError("Too few distinct content correspondences. Calibration remains pending.")
        rp = np.array([kp1[m.queryIdx].pt for m in matches]) / scales[0]
        wp = np.array([kp2[m.trainIdx].pt for m in matches]) / scales[1]
    else:
        rp, wp = np.asarray(manual[0]), np.asarray(manual[1])
    progress(60, "Validating sampling scale and overlap")
    matrix, good, residual = _fit_pairs(rp, wp)
    r = float(matrix[0, 0])
    required = 3 if manual is not None else 12
    coverage = float(cv2.contourArea(cv2.convexHull(np.float32(wp[good]))) / (work.shape[0] * work.shape[1]))
    if good.sum() < required or good.mean() < .45 or np.median(residual[good]) > 1.5 or coverage < .02:
        raise ValueError("Weak, clustered or inconsistent correspondences. Review manual points; no calibration transferred.")
    # Check independent pixel content after registration; exclude occluding labels
    # using robust patch correlations. Never derive scale from image/footer size.
    check_scale = min(1., 1000 / max(work.shape))
    size = (max(1, round(work.shape[1] * check_scale)), max(1, round(work.shape[0] * check_scale)))
    check_matrix = matrix.copy() * check_scale
    warped = cv2.warpAffine(ref, check_matrix, size)
    valid = cv2.warpAffine(np.ones(ref.shape, np.uint8), check_matrix, size, flags=cv2.INTER_NEAREST) > 0
    target = cv2.resize(work, size, interpolation=cv2.INTER_AREA)
    correlations = []
    for y in range(0, size[1] - 48, 64):
        for x in range(0, size[0] - 48, 64):
            sl = np.s_[y:y + 64, x:x + 64]
            mask = valid[sl]
            a, b = warped[sl][mask], target[sl][mask]
            if len(a) > 1500 and min(a.std(), b.std()) > 5:
                correlations.append(float(np.corrcoef(a, b)[0, 1]))
    corr = float(np.median(correlations)) if correlations else 0.
    if corr < .55:
        raise ValueError(f"Image content validation failed (patch correlation {corr:.2f}). Different field of view or insufficient overlap.")
    result = {"matrix": matrix.tolist(), "r": r, "inliers": int(good.sum()), "matches": len(rp), "coverage": coverage,
              "median_error_px": float(np.median(residual[good])), "correlation": corr, "method": "manual points + content verification" if manual is not None else "SIFT + RANSAC + content verification",
              "reference_points": rp[good][:200].tolist(), "work_points": wp[good][:200].tolist(), "verified": True}
    progress(100, "Pair validated; inspect overlap before confirming calibration")
    log.info("Registration %.3fs %s", time.perf_counter() - started, {k: v for k, v in result.items() if k not in ("reference_points", "work_points")})
    return result
