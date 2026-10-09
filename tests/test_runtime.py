from pathlib import Path
import sys
from microscale.runtime import runtime_dir, user_data_dir


def test_frozen_writes_user_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "temporary-extraction"), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-data"))
    monkeypatch.delenv("MICROSCALE_USER_DIR", raising=False)
    result = runtime_dir("examples")
    assert result == tmp_path / "local-data" / "MicroScaleEditor" / "examples"
    assert result.is_dir()
    assert "temporary-extraction" not in str(result)


def test_test_directory_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MICROSCALE_USER_DIR", str(tmp_path / "isolated user data"))
    assert runtime_dir("logs") == tmp_path / "isolated user data" / "logs"
