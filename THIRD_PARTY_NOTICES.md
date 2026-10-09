# Third-party notices

MicroScale Editor uses the following independent projects. Their names and copyrights belong to their respective owners. Their license terms apply to their own components; this document does not assign an additional license to MicroScale Editor's original code.

The `third-party-licenses` directory contains notices copied from the installed distributions, a version inventory, and supplementary upstream texts. Some package notices also cover bundled native libraries. The portable release ZIP includes this directory.

| Component | Version in the validated build | Upstream source |
|---|---|---|
| Python | 3.13.5 | https://www.python.org/downloads/release/python-3135/ |
| PySide6 / Shiboken6 / Qt | 6.9.3 | https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://download.qt.io/archive/qt/6.9/6.9.3/ |
| NumPy | 2.2.6 | https://github.com/numpy/numpy/tree/v2.2.6 |
| OpenCV Python | 4.12.0.88 | https://github.com/opencv/opencv-python |
| tifffile | 2026.9.20 | https://github.com/cgohlke/tifffile |
| imagecodecs | 2026.8.16 | https://github.com/cgohlke/imagecodecs |
| RapidOCR ONNX Runtime backend | 1.2.3 | https://github.com/RapidAI/RapidOCR |
| ONNX Runtime | 1.31.0 | https://github.com/microsoft/onnxruntime |
| Pillow | 12.3.0 | https://github.com/python-pillow/Pillow |
| Shapely / GEOS | 2.2.0 / bundled GEOS | https://github.com/shapely/shapely |
| pyclipper | 1.4.0 | https://github.com/fonttools/pyclipper |
| PyYAML | 6.0.3 | https://github.com/yaml/pyyaml |
| six | 1.17.0 | https://github.com/benjaminp/six |
| FlatBuffers | 25.12.19 | https://github.com/google/flatbuffers |
| packaging | 26.3 | https://github.com/pypa/packaging |
| protobuf | 7.36.2 | https://github.com/protocolbuffers/protobuf |
| PyInstaller | 6.12.0 | https://github.com/pyinstaller/pyinstaller/tree/v6.12.0 |

The Qt components used by the editor are dynamically loaded. The applicable open-source license texts and upstream notices accompany this distribution; the commercial-license text shipped by the wheel is retained as an upstream notice and is not a claim that this project holds a commercial Qt license. See [Qt for Python's license documentation](https://doc.qt.io/qtforpython-6.9/licenses.html).

The application source, dependency versions, and PyInstaller spec are included in the repository. You may rebuild the application with compatible modified Qt/PySide6 libraries using the process in `PACKAGING.md`; MicroScale Editor imposes no restriction on debugging modifications to those libraries. Upstream Qt/PySide source archives and their build instructions are linked above.

RapidOCR's package supplies the bundled recognition models and dictionary. The model files are used as installed, without modification. Its Apache license text is included from the upstream project. ONNX Runtime and OpenCV include their own third-party notices.

`scripts/collect_licenses.py` reproduces notice collection for installed distributions. Supplementary upstream license texts should be retained when refreshing that directory. Build tools and test-only packages are not necessarily included in the executable; the inventory records the checked distributions rather than claiming every listed file is loaded at runtime.
