"""Build a reproducible, explicitly synthetic demo project and independent exports."""
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from microscale.examples import generate_examples
from microscale.image_io import read_source
from microscale.model import save_project, Crop
from microscale.image_io import project_for
from microscale.rendering import export_file


def main():
    app = QApplication.instance() or QApplication([])
    folder = generate_examples(ROOT / "examples")
    source = read_source(folder / "SYNTHETIC_clean.png")
    p = project_for(source)
    p.calibration.propose(.2, .2, "Synthetic example manifest; not measured microscopy", True)
    p.calibration.confirm()
    p.style.enabled = True
    p.style.plate = True
    p.style.length_nm = 5
    p.style.font_size = 26
    p.inset.enabled = True
    p.inset.roi = Crop(rect=[420., 350., 80., 80.])
    p.inset.x, p.inset.y, p.inset.width = 32., 90., 320.
    p.inset.style.enabled = True
    p.inset.style.length_nm = 5
    p.inset.style.plate = True
    p.inset.style.font_size = 20
    p.output.label = "(a) SYNTHETIC"
    p.output.label_y = 48
    p.notes = "Explicitly synthetic demonstration. Inset is a digital 4x crop, not an independent micrograph. 5 nm: main 25 px; inset 100 px."
    project_path = folder / "SYNTHETIC_demo.micro.json"
    save_project(p, project_path)
    # The published demo travels with its synthetic input image.
    data = json.loads(project_path.read_text(encoding="utf-8"))
    data["source_path"] = Path(p.source_path).name
    project_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    for kind, suffix in (("png", ".png"), ("svg", ".svg")):
        outputs = export_file(folder / ("SYNTHETIC_demo_output" + suffix), source.pixels, source.pixels, p, kind)
        for filename in outputs:
            if str(filename).endswith(".json"):
                sidecar = Path(filename)
                metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                if "recipe" in metadata:
                    metadata["recipe"]["source_path"] = Path(p.source_path).name
                    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(outputs)
    print(project_path)


if __name__ == "__main__":
    main()
