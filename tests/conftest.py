"""Shared pytest fixtures for the WEARME test suite."""

import json
from pathlib import Path

import pytest


@pytest.fixture()
def sample_json_file(tmp_path: Path) -> Path:
    """Return a temporary JSON file containing a simple dict."""
    data = {"name": "test", "value": 42, "nested": {"ok": True}}
    file_path = tmp_path / "sample.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")
    return file_path


@pytest.fixture()
def empty_json_file(tmp_path: Path) -> Path:
    """Return a temporary JSON file containing an empty dict."""
    file_path = tmp_path / "empty.json"
    file_path.write_text("{}", encoding="utf-8")
    return file_path
