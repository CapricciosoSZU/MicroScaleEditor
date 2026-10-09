"""Deterministic, explicitly SYNTHETIC data; not real microscopy validation."""
from pathlib import Path
import json
import cv2
import numpy as np
import tifffile
from .image_io import write_png


def synthetic_texture(size=1024, seed=713):
    rng = np.random.default_rng(seed)
    field = rng.normal(100, 18, (size, size)).astype(np.float32)
    field = cv2.GaussianBlur(field, (0, 0), 1.8)
    for _ in range(350):
        x, y = rng.integers(20, size - 20, 2)
        r = int(rng.integers(3, 24))
        cv2.circle(field, (int(x), int(y)), r, float(rng.uniform(30, 220)), -1)
        cv2.circle(field, (int(x), int(y)), r, float(rng.uniform(140, 250)), 1)
    gray = np.clip(field, 0, 255).astype(np.uint8)
    cv2.putText(gray, "SYNTHETIC - NOT SEM/TEM", (25, 40), cv2.FONT_HERSHEY_SIMPLEX, .7, 245, 2, cv2.LINE_AA)
    return np.dstack([gray, gray, gray, np.full_like(gray, 255)])


def generate_examples(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "manifest.json"
    if manifest_path.exists() and (folder / "SYNTHETIC_clean.png").exists():
        return folder
    clean = synthetic_texture()
    write_png(folder / "SYNTHETIC_clean.png", clean)
    marked = clean.copy()
    marked[895:995, 630:1000, :3] = 20
    # Exact solid bar [700, 950) = 250 source pixels, 50 nm => 0.2 nm/px.
    marked[966:974, 700:950, :3] = 255
    cv2.putText(marked, "50 nm", (739, 950), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255, 255, 255, 255), 2, cv2.LINE_AA)
    write_png(folder / "SYNTHETIC_50nm_250px.png", marked)
    ref = clean.copy()
    ref[908:998, 600:1010, :3] = 0
    ref[966:974, 700:900, :3] = 255
    cv2.putText(ref, "100 nm", (718, 950), cv2.FONT_HERSHEY_SIMPLEX, 1., (255, 255, 255, 255), 2, cv2.LINE_AA)
    write_png(folder / "SYNTHETIC_reference_0.5nm.png", ref)
    write_png(folder / "SYNTHETIC_work_2x.png", cv2.resize(clean, (2048, 2048), interpolation=cv2.INTER_LINEAR))
    footer = np.full((100, 1024, 4), 255, np.uint8)
    footer[..., :3] = 15
    cv2.putText(footer, "SYNTHETIC instrument footer - excluded from sample scale", (15, 50), cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255, 255), 1)
    write_png(folder / "SYNTHETIC_reference_footer.png", np.concatenate([ref, footer]))
    write_png(folder / "SYNTHETIC_different_field.png", synthetic_texture(seed=824))
    yy, xx = np.mgrid[:512, :640]
    data = ((xx * 71 + yy * 43) % 65536).astype(np.uint16)
    tifffile.imwrite(folder / "SYNTHETIC_16bit_OME.tif", data, ome=True, metadata={"axes": "YX", "PhysicalSizeX": .2, "PhysicalSizeXUnit": "nm", "PhysicalSizeY": .2, "PhysicalSizeYUnit": "nm"})
    manifest_path.write_text(json.dumps({"synthetic": True, "not_real_SEM_TEM_validation": True, "50nm_bar": {"file": "SYNTHETIC_50nm_250px.png", "edges": [[700, 970], [950, 970]], "length_nm": 50, "sx_nm_per_px": .2}, "paired": {"reference": "SYNTHETIC_reference_0.5nm.png", "work": "SYNTHETIC_work_2x.png", "r": 2, "reference_sx": .5, "work_sx": .25}}, indent=2), encoding="utf-8")
    return folder
