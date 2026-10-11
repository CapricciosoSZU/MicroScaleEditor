"""Source-coordinate editing. Qt view transforms affect viewing only."""
from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from .geometry import normalized_rect, polygon_valid, distance, constrain_rect
from .image_io import array_to_qimage


class ImageView(QGraphicsView):
    zoomChanged = Signal(float)
    beforeChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.image_item = self.scene().addPixmap(QPixmap())
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setBackgroundBrush(QColor("#272c35"))
        self._pan = None

    def set_image(self, image, fit=False):
        self.image_item.setPixmap(QPixmap.fromImage(image))
        self.scene().setSceneRect(self.image_item.boundingRect())
        if fit:
            self.fit()

    def fit(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoomChanged.emit(self.transform().m11())

    def actual_size(self):
        # One output pixel per physical monitor pixel, including high-DPI Windows.
        self.resetTransform()
        dpr = self.viewport().devicePixelRatioF()
        self.scale(1. / dpr, 1. / dpr)
        self.zoomChanged.emit(self.transform().m11())

    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        if .015 < self.transform().m11() * factor < 100:
            self.scale(factor, factor)
            self.zoomChanged.emit(self.transform().m11())
        event.accept()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        # Fixed scene-space checker; never a render/export layer.
        scene = rect.intersected(self.sceneRect())
        tile = max(8., 16 / max(.01, self.transform().m11()))
        painter.save()
        painter.setClipRect(scene)
        painter.fillRect(scene, QColor("#d5d9df"))
        start_x, start_y = math.floor(scene.left() / tile), math.floor(scene.top() / tile)
        for y in range(start_y, math.ceil(scene.bottom() / tile)):
            for x in range(start_x, math.ceil(scene.right() / tile)):
                if (x + y) % 2 == 0:
                    painter.fillRect(QRectF(x * tile, y * tile, tile, tile), QColor("#f4f5f6"))
        painter.restore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_B and not event.isAutoRepeat():
            self.beforeChanged.emit(True)
            event.accept()
        elif event.key() == Qt.Key.Key_F:
            self.fit()
        elif event.key() == Qt.Key.Key_1:
            self.actual_size()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_B and not event.isAutoRepeat():
            self.beforeChanged.emit(False)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self.beforeChanged.emit(False)
        super().focusOutEvent(event)


class EditorCanvas(ImageView):
    edited = Signal(str, object)
    message = Signal(str)
    scaleDoubleClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)
        self.mode = "Edit crop"
        self.shape = "rectangle"
        self.ratio = None
        self.project = None
        self.composition = None
        self.show_masks = True
        self.show_guides = True
        self.before = False
        self.mask_layer = "line"
        self.brush_radius = 8.
        self.result_item = self.scene().addPixmap(QPixmap())
        self.mask_item = self.scene().addPixmap(QPixmap())
        self.mask_item.setOpacity(.42)
        self.start = None
        self.draft = None
        self.points = []
        self.drag_target = None
        self.endpoint_pointer = None
        self.selected_vertex = None

    def set_context(self, project, composition, source_image, result_image, mask_image=None, fit=False):
        self.project, self.composition = project, composition
        self.set_image(source_image, fit)
        self.result_item.setPixmap(QPixmap.fromImage(result_image))
        matrix = composition.matrix
        transform = QTransform(matrix[0, 0], matrix[1, 0], matrix[0, 1], matrix[1, 1], matrix[0, 2], matrix[1, 2])
        inverse, ok = transform.inverted()
        if not ok:
            raise ValueError("Output transform is not invertible.")
        self.result_item.setTransform(inverse)
        self.mask_item.setPixmap(QPixmap.fromImage(mask_image) if mask_image is not None else QPixmap())
        self.mask_item.setVisible(self.show_masks and not self.before)
        self.viewport().update()

    def set_mode(self, mode):
        self.mode = mode
        self.points = []
        self.start = None
        self.draft = None
        self.drag_target = None
        self.endpoint_pointer = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if mode == "Pan" else QGraphicsView.DragMode.NoDrag)
        self.viewport().update()

    def source_position(self, event):
        point = self.mapToScene(event.position().toPoint())
        rect = self.sceneRect()
        return [max(0., min(rect.width(), point.x())), max(0., min(rect.height(), point.y()))]

    def scene_rect_for_output(self, rect):
        x, y, w, h = rect
        pts = np.array([self.composition.to_source(p) for p in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))])
        lo, hi = pts.min(0), pts.max(0)
        return [*lo.tolist(), *(hi - lo).tolist()]

    def handles(self, crop):
        if crop.kind in ("polygon", "freehand"):
            return crop.points
        x, y, w, h = crop.rect
        return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

    def mousePressEvent(self, event):
        if not self.project or self.mode == "Pan":
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan = event.position().toPoint()
            event.accept()
            return
        point = self.source_position(event)
        if event.button() == Qt.MouseButton.RightButton:
            self.finish_polygon()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        tolerance = 9 / self.transform().m11()
        if self.mode in ("Crop polygon", "Mask polygon", "Protect polygon"):
            self.points.append(point)
            self.viewport().update()
            return
        self.start = point
        self.drag_target = None
        if self.mode in ("Edit crop", "Edit inset ROI"):
            crop = self.project.crop if self.mode == "Edit crop" else self.project.inset.roi
            self.draft = deepcopy(crop)
            vertices = self.handles(crop)
            if crop.kind in ("polygon", "freehand") and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                index = min(range(len(vertices)), key=lambda i: point_segment_distance(point, vertices[i], vertices[(i + 1) % len(vertices)]))
                self.draft.points.insert(index + 1, point)
                self.selected_vertex = index + 1
                self.drag_target = ("vertex", index + 1)
            else:
                for i, vertex in enumerate(vertices):
                    if math.dist(point, vertex) < tolerance:
                        self.drag_target = ("vertex" if crop.kind in ("polygon", "freehand") else "corner", i)
                        self.selected_vertex = i
                        break
                if not self.drag_target and crop_path(crop).contains(QPointF(*point)):
                    self.drag_target = ("move", deepcopy(crop))
        elif self.mode == "Move scale" and self.composition.scale_rect:
            self.drag_target = ("scale", self.composition.scale_rect[:2])
        elif self.mode == "Move inset" and self.composition.inset_rect:
            rect = self.composition.inset_rect
            corner = self.composition.to_source([rect[0] + rect[2], rect[1] + rect[3]])
            if math.dist(point, corner) < tolerance * 2:
                self.drag_target = ("inset-size", self.project.inset.width)
            else:
                self.drag_target = ("inset", [self.project.inset.x, self.project.inset.y])
        elif self.mode == "Endpoints":
            pts = self.project.calibration.endpoints
            nearest = min(range(2), key=lambda i: math.dist(point, pts[i]))
            self.draft = deepcopy(pts)
            if math.dist(point, pts[nearest]) < tolerance:
                self.drag_target = ("endpoint", nearest)
            else:
                self.draft = [point, point]
                self.drag_target = ("endpoint", 1)
            self.update_endpoint(point, event.modifiers())
        elif self.mode in ("Mask brush", "Mask erase", "Crop freehand"):
            self.points = [point]
        self.viewport().update()

    def mouseMoveEvent(self, event):
        if self._pan is not None:
            pos = event.position().toPoint()
            delta = pos - self._pan
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan = pos
            return
        if not self.project or self.mode == "Pan":
            return super().mouseMoveEvent(event)
        if self.start is None:
            return
        point = self.source_position(event)
        if self.drag_target:
            kind, value = self.drag_target
            if kind == "vertex":
                self.draft.points[value] = point
            elif kind == "corner":
                opposite = self.handles(self.project.crop if self.mode == "Edit crop" else self.project.inset.roi)[(value + 2) % 4]
                ratio = 1. if self.draft.kind in ("square", "circle") else self.ratio if self.mode == "Edit crop" else (1. if self.project.inset.circular else None)
                self.draft.rect = normalized_rect(opposite, point, ratio)
                self.draft.rect = constrain_rect(self.draft.rect, self.project.source_shape)
            elif kind == "move":
                dx, dy = point[0] - self.start[0], point[1] - self.start[1]
                vertices = self.handles(value)
                dx = min(max(dx, -min(p[0] for p in vertices)), self.project.source_shape[1] - max(p[0] for p in vertices))
                dy = min(max(dy, -min(p[1] for p in vertices)), self.project.source_shape[0] - max(p[1] for p in vertices))
                self.draft.rect = [value.rect[0] + dx, value.rect[1] + dy, *value.rect[2:]]
                self.draft.points = [[p[0] + dx, p[1] + dy] for p in value.points]
            elif kind == "endpoint":
                self.update_endpoint(point, event.modifiers())
            else:
                self.draft = point
        elif self.mode in ("Mask brush", "Mask erase", "Crop freehand"):
            if math.dist(point, self.points[-1]) > max(.8, 2 / self.transform().m11()):
                self.points.append(point)
        else:
            self.draft = normalized_rect(self.start, point, self.ratio if self.mode == "Draw crop" else 1. if self.mode == "Draw inset ROI" and self.project.inset.circular else None)
            if self.mode in ("Draw crop", "Draw inset ROI"):
                self.draft = constrain_rect(self.draft, self.project.source_shape)
        self.viewport().update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan = None
            return
        if self.mode == "Pan":
            return super().mouseReleaseEvent(event)
        if self.start is None or not self.project:
            return
        point = self.source_position(event)
        if self.drag_target:
            kind, value = self.drag_target
            if kind in ("move", "corner", "vertex"):
                if self.draft.kind not in ("polygon", "freehand") or polygon_valid(self.draft.points):
                    self.edited.emit("crop" if self.mode == "Edit crop" else "inset-roi", self.draft)
                else:
                    self.message.emit("Invalid polygon: move or delete a crossing vertex.")
            elif kind == "endpoint":
                self.update_endpoint(point, event.modifiers())
                self.edited.emit("endpoints", self.draft)
            elif kind in ("scale", "inset"):
                end, start = self.composition.to_output(point), self.composition.to_output(self.start)
                delta = [end[i] - start[i] for i in (0, 1)]
                self.edited.emit(kind + "-position", [value[i] + delta[i] for i in (0, 1)])
            elif kind == "inset-size":
                self.edited.emit("inset-width", max(16., value + self.composition.to_output(point)[0] - self.composition.to_output(self.start)[0]))
        elif self.mode in ("Mask brush", "Mask erase"):
            self.edited.emit("mask", {"kind": "brush", "layer": self.mask_layer, "points": self.points or [point], "radius": self.brush_radius, "erase": self.mode == "Mask erase"})
        elif self.mode == "Crop freehand":
            points = self.points
            if len(points) > 2 and math.dist(points[0], points[-1]) < 2 / self.transform().m11():
                points = points[:-1]
            if polygon_valid(points):
                self.edited.emit("crop-polygon", ["freehand", points])
            else:
                self.message.emit("Freehand region is invalid; draw a simple closed region.")
        elif self.mode.startswith("Measure"):
            if self.mode == "Measure horizontal":
                point[1] = self.start[1]
            elif self.mode == "Measure vertical":
                point[0] = self.start[0]
            self.edited.emit("measure", {"points": [self.start, point], "mode": self.mode})
        elif self.draft and isinstance(self.draft, list) and len(self.draft) == 4 and min(self.draft[2:]) >= 1:
            if self.mode == "Draw crop":
                self.edited.emit("crop-rect", [self.shape, self.draft])
            elif self.mode == "Draw inset ROI":
                self.edited.emit("inset-rect", self.draft)
            elif self.mode == "Mask rectangle":
                self.edited.emit("mask", {"kind": "rect", "layer": self.mask_layer, "rect": self.draft, "erase": False})
            elif self.mode == "Detect region":
                x, y, w, h = self.draft
                self.edited.emit("detect-region", [x, y, x + w, y + h])
        self.start, self.draft, self.drag_target = None, None, None
        self.endpoint_pointer = None
        if self.mode not in ("Crop polygon", "Mask polygon", "Protect polygon"):
            self.points = []
        self.viewport().update()

    def update_endpoint(self, point, modifiers):
        """Keep the other endpoint fixed; constrain in source coordinates."""
        self.endpoint_pointer = list(point)
        index = self.drag_target[1]
        point = list(point)
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            point[1] = self.draft[1 - index][1]
        self.draft[index] = point

    def finish_polygon(self):
        points = self.points
        if len(points) > 1 and math.dist(points[0], points[-1]) < .1:
            points = points[:-1]
        if not polygon_valid(points):
            self.message.emit("Need at least three non-crossing vertices. Click more points or press Esc.")
            return
        if self.mode == "Crop polygon":
            self.edited.emit("crop-polygon", ["polygon", points])
        elif self.mode == "Mask polygon":
            self.edited.emit("mask", {"kind": "polygon", "points": points, "layer": self.mask_layer, "erase": False})
        elif self.mode == "Protect polygon":
            self.edited.emit("protect", points)
        self.points = []
        self.viewport().update()

    def mouseDoubleClickEvent(self, event):
        if self.mode in ("Crop polygon", "Mask polygon", "Protect polygon"):
            self.finish_polygon()
        elif self.composition and self.composition.scale_rect and QRectF(*self.scene_rect_for_output(self.composition.scale_rect)).contains(QPointF(*self.source_position(event))):
            self.scaleDoubleClicked.emit()
        else:
            super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Shift and self.start is not None and self.endpoint_pointer is not None:
            self.update_endpoint(self.endpoint_pointer, Qt.KeyboardModifier.ShiftModifier)
            self.viewport().update()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.points:
            self.finish_polygon()
        elif event.key() == Qt.Key.Key_Escape:
            self.points, self.start, self.draft = [], None, None
            self.drag_target, self.endpoint_pointer = None, None
            self.viewport().update()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.project and self.selected_vertex is not None and self.project.crop.kind in ("polygon", "freehand"):
            crop = deepcopy(self.project.crop)
            if len(crop.points) > 3:
                crop.points.pop(min(self.selected_vertex, len(crop.points) - 1))
                if polygon_valid(crop.points):
                    self.edited.emit("crop", crop)
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down) and self.mode == "Move scale" and self.composition and self.composition.scale_rect:
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx = step * ((event.key() == Qt.Key.Key_Right) - (event.key() == Qt.Key.Key_Left))
            dy = step * ((event.key() == Qt.Key.Key_Down) - (event.key() == Qt.Key.Key_Up))
            self.edited.emit("scale-position", [self.composition.scale_rect[0] + dx, self.composition.scale_rect[1] + dy])
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Shift and self.start is not None and self.endpoint_pointer is not None:
            self.update_endpoint(self.endpoint_pointer, Qt.KeyboardModifier.NoModifier)
            self.viewport().update()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def drawForeground(self, painter, rect):
        if not self.project or self.before:
            return
        painter.save()
        pen = QPen(QColor("#45d4c5"), 0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        crop = self.draft if self.mode == "Edit crop" and hasattr(self.draft, "kind") else self.project.crop
        painter.drawPath(crop_path(crop))
        if self.mode in ("Edit crop", "Edit inset ROI"):
            selected = crop if self.mode == "Edit crop" else self.draft if hasattr(self.draft, "kind") else self.project.inset.roi
            painter.drawPath(crop_path(selected))
            radius = 4 / self.transform().m11()
            painter.setBrush(QColor("#45d4c5"))
            for point in self.handles(selected):
                painter.drawEllipse(QPointF(*point), radius, radius)
            painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.mode == "Endpoints":
            pts = self.draft if self.drag_target and self.drag_target[0] == "endpoint" else self.project.calibration.endpoints
            painter.setPen(QPen(QColor("#ffcb55"), 0))
            painter.drawLine(QPointF(*pts[0]), QPointF(*pts[1]))
            for p in pts:
                radius = 5 / self.transform().m11()
                painter.drawEllipse(QPointF(*p), radius, radius)
        if self.show_guides:
            if self.composition:
                for issue in self.composition.issues:
                    if issue.rect and issue.severity in ("warning", "error"):
                        warning_pen = QPen(QColor("#ff6b85" if issue.severity == "error" else "#ffc857"), 0, Qt.PenStyle.DashLine)
                        painter.setPen(warning_pen)
                        painter.drawRect(QRectF(*self.scene_rect_for_output(issue.rect)))
            for points in self.project.protected:
                painter.setPen(QPen(QColor("#ff6178"), 0))
                painter.drawPath(points_path(points, True))
            for measure in self.project.measurements:
                painter.setPen(QPen(QColor("#59d9ff"), 0))
                pts = measure["points"]
                painter.drawLine(QPointF(*pts[0]), QPointF(*pts[1]))
                d, unit = distance(*pts, self.project.calibration.usable_x, self.project.calibration.usable_y)
                painter.save()
                painter.translate(*pts[1])
                painter.scale(1 / self.transform().m11(), 1 / self.transform().m11())
                painter.drawText(QPointF(5, -5), f"{d:.4g} {unit}")
                painter.restore()
        if self.points:
            painter.setPen(QPen(QColor("#e6bbff"), 0))
            painter.drawPath(points_path(self.points, False))
        if isinstance(self.draft, list) and len(self.draft) == 4 and isinstance(self.draft[0], (float, int)):
            painter.setPen(QPen(QColor("#ffe69e"), 0))
            painter.drawRect(QRectF(*self.draft))
        painter.restore()


def points_path(points, closed):
    path = QPainterPath()
    if points:
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        if closed:
            path.closeSubpath()
    return path


def crop_path(crop):
    if crop.kind in ("polygon", "freehand"):
        return points_path(crop.points, True)
    path = QPainterPath()
    if crop.kind in ("circle", "ellipse"):
        path.addEllipse(QRectF(*crop.rect))
    else:
        path.addRect(QRectF(*crop.rect))
    return path


def point_segment_distance(p, a, b):
    p, a, b = np.array(p), np.array(a), np.array(b)
    v = b - a
    t = np.clip(np.dot(p - a, v) / max(1e-12, np.dot(v, v)), 0, 1)
    return np.linalg.norm(p - a - t * v)
