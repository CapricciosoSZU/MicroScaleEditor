"""Small, JSON-serializable project state; history never owns source arrays."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from copy import deepcopy
import hashlib
import json
import logging
import os
from pathlib import Path
import uuid

import numpy as np
from . import __version__
from .geometry import positive


@dataclass
class Calibration:
    sx: float | None = None
    sy: float | None = None
    status: str = "Uncalibrated"
    source: str = "None"
    square_pixels: bool = False
    evidence: list = field(default_factory=list)
    conflict_threshold: float = .02
    endpoints: list = field(default_factory=lambda: [[0., 0.], [250., 0.]])
    length_nm: float = 50.
    endpoints_dirty: bool = False
    rule: str = "Solid bar: outer half-open edges. End ticks: center-to-center. Antialiasing: 50% local contrast."

    def propose(self, sx, sy, source, square=False, extra=None):
        sx = positive(sx, "Horizontal nm/px") if sx is not None else None
        sy = positive(sy, "Vertical nm/px") if sy is not None else None
        self.evidence.append({"sx": sx, "sy": sy, "source": source, "details": extra or {}})
        self.sx, self.sy, self.source, self.square_pixels = sx, sy, source, square
        self.status = "Pending"
        self.endpoints_dirty = False

    def conflicts(self):
        found = []
        for item in self.evidence:
            diffs = [abs(item[key] / value - 1) for key, value in (("sx", self.sx), ("sy", self.sy)) if value and item.get(key)]
            if diffs and max(diffs) > self.conflict_threshold:
                found.append((item["source"], max(diffs)))
        return found

    def confirm(self, resolve=False):
        if self.endpoints_dirty:
            raise ValueError("Endpoints changed. Check Known length and click Use endpoints before confirming calibration.")
        if self.sx is None and self.sy is None:
            raise ValueError("No physical calibration is available.")
        if self.conflicts() and not resolve:
            raise ValueError("Calibration sources disagree. Review evidence and explicitly choose the current source.")
        self.status = "Confirmed"

    @property
    def usable_x(self):
        return self.sx if self.status == "Confirmed" else None

    @property
    def usable_y(self):
        return self.sy if self.status == "Confirmed" else None


@dataclass
class Crop:
    kind: str = "rectangle"
    rect: list = field(default_factory=lambda: [0., 0., 512., 512.])
    points: list = field(default_factory=list)
    ratio: str = "Free"
    background: str = "transparent"


@dataclass
class Style:
    enabled: bool = False
    length_nm: float = 5.
    color: str = "#ffffff"
    thickness: float = 5.
    endcaps: bool = False
    font: str = "Arial"
    font_size: float = 22.
    bold: bool = True
    text_position: str = "above"
    gap: float = 6.
    plate: bool = False
    plate_color: str = "#000000"
    plate_opacity: float = .8
    anchor: str = "bottom-right"
    margin: float = 20.
    x: float = 20.
    y: float = 20.
    outline: bool = False
    outline_color: str = "#000000"
    outline_width: float = 2.5
    text_align: str = "center"

    def __post_init__(self):
        # Accept the legacy field in projects/templates, with one label layout.
        self.text_position = "above"


def velox_style(size=(1024, 1024), *, enabled=False, length_nm=5.):
    """Reference-inspired appearance only; physical length still needs calibration."""
    factor = max(.25, min(size) / 1024.)
    return Style(enabled=enabled, length_nm=length_nm, color="#ffffff", thickness=10 * factor,
                 font="Arial", font_size=47 * factor, bold=False, text_position="above",
                 text_align="left", gap=11 * factor, anchor="bottom-left", margin=12 * factor,
                 outline=True, outline_color="#000000", outline_width=2.5 * factor)


@dataclass
class Output:
    mode: str = "native"
    scale: float = 1.
    width_px: int = 1024
    width_mm: float = 85.
    dpi: float = 300.
    font_pt: float = 9.
    line_pt: float = 1.
    label: str = ""
    label_x: float = 16.
    label_y: float = 16.
    export_guides: bool = False
    rotation_deg: float = 0.


@dataclass
class Inset:
    enabled: bool = False
    roi: Crop = field(default_factory=lambda: Crop(rect=[100., 100., 100., 100.]))
    x: float = 30.
    y: float = 30.
    width: float = 200.
    circular: bool = False
    border_color: str = "#ffd166"
    style: Style = field(default_factory=lambda: Style(length_nm=5., font_size=14., thickness=3., margin=12.))


@dataclass
class Project:
    schema_version: int = 1
    software_version: str = __version__
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str = ""
    source_hash: str = ""
    source_shape: list = field(default_factory=list)
    source_dtype: str = ""
    calibration: Calibration = field(default_factory=Calibration)
    crop: Crop = field(default_factory=Crop)
    style: Style = field(default_factory=Style)
    output: Output = field(default_factory=Output)
    inset: Inset = field(default_factory=Inset)
    reference: dict = field(default_factory=dict)
    masks: list = field(default_factory=list)
    mask_morph: dict = field(default_factory=lambda: {"line": 0, "text": 0, "background": 0})
    candidates: list = field(default_factory=list)
    treatment: str = "keep"
    treatment_color: str = "#000000"
    pure_color_confirmed: bool = False
    protected: list = field(default_factory=list)
    measurements: list = field(default_factory=list)
    display_low: float | None = None
    display_high: float | None = None
    notes: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = deepcopy(data)
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported project schema version.")
        data.pop("mask_file", None)
        data.pop("mask_sha256", None)
        data["calibration"] = Calibration(**data.get("calibration", {}))
        data["crop"] = Crop(**data.get("crop", {}))
        data["style"] = Style(**data.get("style", {}))
        data["output"] = Output(**data.get("output", {}))
        inset = data.get("inset", {})
        inset["roi"] = Crop(**inset.get("roi", {}))
        inset["style"] = Style(**inset.get("style", {}))
        data["inset"] = Inset(**inset)
        return cls(**data)


class History:
    def __init__(self, project, limit=80):
        self.limit = limit
        self.states = [project.to_dict()]
        self.index = 0

    def push(self, project):
        current = project.to_dict()
        if self.states[self.index] == current:
            return
        self.states = self.states[:self.index + 1] + [current]
        self.states = self.states[-self.limit:]
        self.index = len(self.states) - 1

    def step(self, delta):
        self.index = max(0, min(len(self.states) - 1, self.index + delta))
        return Project.from_dict(self.states[self.index])


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, data, backup=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with open(temporary, "w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    if backup and path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            atomic_json(path.with_name(path.name + ".bak"), previous, backup=False)
        except ValueError:
            logging.getLogger(__name__).warning("Preserving valid backup because current JSON is damaged: %s", path)
    os.replace(temporary, path)


def save_project(project, path, write_masks=True):
    path = Path(path).resolve()
    if str(path).casefold() in {project.source_path.casefold(), str(project.reference.get("path", "")).casefold()}:
        raise ValueError("Project cannot overwrite an input image.")
    data = project.to_dict()
    if write_masks and project.source_shape:
        from .detection import build_masks
        masks = build_masks(project, project.source_shape[:2])
        # Content-addressed sidecars preserve the previous valid recovery record.
        content_hash = hashlib.sha256(b"".join(masks[k].tobytes() for k in sorted(masks))).hexdigest()[:16]
        mask_path = path.with_name(path.stem + ".masks-" + content_hash + ".npz")
        if not mask_path.exists():
            with open(mask_path.with_suffix(".tmp"), "wb") as stream:
                np.savez_compressed(stream, **masks)
            os.replace(mask_path.with_suffix(".tmp"), mask_path)
        data["mask_file"] = mask_path.name
        data["mask_sha256"] = file_hash(mask_path)
    atomic_json(path, data)


def load_project(path, verify=True):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    project = Project.from_dict(data)
    if not Path(project.source_path).is_absolute():
        project.source_path = str((path.parent / project.source_path).resolve())
    if verify and Path(project.source_path).exists() and file_hash(project.source_path) != project.source_hash:
        raise ValueError("Source hash mismatch. Relink the original file; calibration was not applied.")
    if data.get("mask_file"):
        mask_path = path.parent / data["mask_file"]
        if not mask_path.exists() or file_hash(mask_path) != data["mask_sha256"]:
            raise ValueError("Mask sidecar is missing or modified. Restore it or use the parameter-only recovery file.")
    return project


def relink_source(project, path):
    path = Path(path).resolve()
    if file_hash(path) != project.source_hash:
        raise ValueError("This file does not match the recorded SHA-256. Open it as a new image with independent calibration.")
    project.source_path = str(path)
