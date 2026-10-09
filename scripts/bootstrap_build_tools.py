"""Offline fallback: reuse installed build-only distributions from base Python.

Copies only explicitly named distribution-owned files into this project's venv.
Never modifies the base environment, runtime dependencies, or external scripts.
"""
from importlib import metadata
from pathlib import Path
import shutil
import sys


def main():
    target = Path(sys.prefix) / "Lib" / "site-packages"
    source = Path(sys.base_prefix) / "Lib" / "site-packages"
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Run this using the project's virtual-environment Python.")
    wanted = {"pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile", "pywin32-ctypes", "setuptools"}
    normalize = lambda name: name.lower().replace("_", "-")
    available = {normalize(dist.metadata["Name"]): dist for dist in metadata.distributions(path=[str(source)])}
    for name in sorted(wanted):
        try:
            present = metadata.distribution(name)
            print(f"Already available: {name} {present.version}")
            continue
        except metadata.PackageNotFoundError:
            pass
        if name not in available:
            raise RuntimeError(f"Base Python has no {name}; install requirements-build.txt instead.")
        dist = available[name]
        for relative in dist.files or []:
            if ".." in relative.parts or relative.is_absolute():
                continue
            original = Path(dist.locate_file(relative))
            destination = target / relative
            if original.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
        # Conda distributions can use egg-info whose SOURCES omit its own metadata.
        metadata_path = Path(dist._path)
        if metadata_path.is_dir():
            shutil.copytree(metadata_path, target / metadata_path.name, dirs_exist_ok=True)
        print(f"Copied build tool: {name} {dist.version} from {source}")


if __name__ == "__main__":
    main()
