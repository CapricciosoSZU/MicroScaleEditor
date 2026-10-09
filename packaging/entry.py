"""PyInstaller entry point; import the application using its package name."""
import ctypes
import multiprocessing
import os
from pathlib import Path
import sys
import traceback


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Some bundled libraries expect writable standard streams in windowed mode.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    try:
        from microscale.__main__ import main
        raise SystemExit(main())
    except Exception:
        folder = Path(os.environ.get("MICROSCALE_USER_DIR", "")) if os.environ.get("MICROSCALE_USER_DIR") else Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MicroScaleEditor"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "startup-error.log"
        path.write_text(traceback.format_exc(), encoding="utf-8")
        if "--self-test" not in sys.argv and "--recipe" not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None, f"MicroScale Editor could not start. Details:\n{path}", "MicroScale Editor", 0x10)
        raise SystemExit(1)
