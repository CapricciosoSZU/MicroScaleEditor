"""Writable user data must never live inside a frozen executable's extraction dir."""
from pathlib import Path
import os
import sys


def frozen():
    return bool(getattr(sys, "frozen", False))


def user_data_dir():
    override = os.environ.get("MICROSCALE_USER_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MicroScaleEditor"


def runtime_dir(name):
    base = user_data_dir() if frozen() or os.environ.get("MICROSCALE_USER_DIR") else Path(__file__).resolve().parent.parent
    folder = base / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder
