"""Generic JSON load/save utilities.

Provides type-safe wrappers around the stdlib ``json`` module with
consistent error handling and automatic parent-directory creation on save.

Usage::

    from wearme.io.json_io import load_json, save_json

    data = load_json(path)
    save_json({"key": "value"}, path)
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_json(path: Path | str) -> Any:
    """Load and parse a JSON file.

    Args:
        path: Path to the JSON file. Accepts ``pathlib.Path`` or ``str``.

    Returns:
        The deserialised Python object (dict, list, etc.).

    Raises:
        FileNotFoundError: If *path* does not exist.
        json.JSONDecodeError: If the file content is not valid JSON.
    """
    file_path = Path(path)
    logger.debug("Loading JSON from %s", file_path)
    with file_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(data: Any, path: Path | str, *, indent: int = 2) -> None:
    """Serialise *data* to a JSON file.

    Creates parent directories automatically if they do not exist.

    Args:
        data: Python object to serialise. Must be JSON-serialisable.
        path: Destination file path. Accepts ``pathlib.Path`` or ``str``.
        indent: Pretty-print indentation level. Defaults to 2.

    Raises:
        TypeError: If *data* contains objects that are not JSON-serialisable.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Saving JSON to %s", file_path)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)
