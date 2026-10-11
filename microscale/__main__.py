from __future__ import annotations
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from .runtime import runtime_dir


def main():
    parser = argparse.ArgumentParser(description="MicroScale Editor · real-space SEM/TEM images")
    parser.add_argument("image", nargs="?", help="Image or project JSON to open")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--examples", action="store_true", help="Create and open explicitly synthetic examples")
    parser.add_argument("--recipe", help="Render a saved Project JSON without editor interaction")
    parser.add_argument("--output", help="Recipe output filename")
    parser.add_argument("--format", choices=["source", "png", "tiff", "data-tiff", "svg"], default="source")
    parser.add_argument("--self-test", metavar="FOLDER", help="Run the packaged GUI/OCR/export check and write its report")
    parser.add_argument("--test-images", metavar="FILE_OR_FOLDER", action="append", help="Also validate a local image or folder recursively during --self-test; repeat for multiple inputs; reports remain local")
    args = parser.parse_args()
    if args.test_images and not args.self_test:
        parser.error("--test-images requires --self-test")
    logs = runtime_dir("logs")
    handlers = [RotatingFileHandler(logs / "microscale.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")]
    if sys.stderr is not None:
        handlers.insert(0, logging.StreamHandler())
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=handlers)
    if args.recipe and sys.platform != "win32" and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("MicroScale Editor")
    app.setOrganizationName("MicroScale")
    if args.self_test:
        from .diagnostics import run_self_test
        return run_self_test(app, Path(args.self_test), [Path(path) for path in args.test_images] if args.test_images else None)
    if args.recipe:
        if not args.output:
            parser.error("--recipe requires --output")
        from .model import load_project
        from .image_io import read_source, display_rgba
        from .rendering import export_file
        p = load_project(args.recipe)
        source = read_source(p.source_path)
        result = export_file(args.output, source.pixels, display_rgba(source.pixels, p.display_low, p.display_high), p, args.format)
        print("\n".join(result))
        return 0
    from .gui import MainWindow
    window = MainWindow()
    window.show()
    if args.examples:
        window.open_examples()
    elif args.image:
        if args.image.lower().endswith((".json", ".bak")):
            window.open_project_path(args.image)
        else:
            window.load_image(args.image)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
