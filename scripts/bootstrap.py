"""WEARME environment bootstrap verification script.

Checks that the runtime environment meets all requirements before the
user attempts to run any WEARME module.

Run from the project root::

    python scripts/bootstrap.py

Exits with code 0 on success, 1 on first failure.
"""

import logging
import sys

logger = logging.getLogger("wearme.bootstrap")


def _check_python_version() -> None:
    """Verify Python >= 3.11."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        raise OSError(
            f"Python 3.11+ required, got {major}.{minor}. "
            "Please upgrade your Python interpreter."
        )
    logger.info("Python version: %d.%d [OK]", major, minor)


def _check_wearme_importable() -> None:
    """Verify the wearme package is importable (i.e. installed with pip -e)."""
    try:
        import wearme  # noqa: F401
        from wearme.core import constants, paths, units  # noqa: F401
        from wearme.io.json_io import load_json, save_json  # noqa: F401
    except ImportError as exc:
        raise OSError(
            "Cannot import wearme. "
            "Run: pip install -e '.[dev]' from the project root."
        ) from exc
    logger.info("wearme package importable [OK]")


def _check_data_directories() -> None:
    """Verify that required data sub-directories exist."""
    from wearme.core.paths import (
        BODY_MODELS_DIR,
        DATA_DIR,
        GARMENTS_DIR,
        SAMPLES_DIR,
        TEXTURES_DIR,
    )

    required = {
        "data/": DATA_DIR,
        "data/body_models/": BODY_MODELS_DIR,
        "data/garments/": GARMENTS_DIR,
        "data/textures/": TEXTURES_DIR,
        "data/samples/": SAMPLES_DIR,
    }

    missing = [label for label, path in required.items() if not path.exists()]
    if missing:
        raise OSError(
            "Missing data directories (run Phase 0 setup): "
            + ", ".join(missing)
        )
    logger.info("Data directories present [OK]")


def _check_configs_exist() -> None:
    """Verify that YAML config files exist."""
    from wearme.core.paths import APP_CONFIG, BODY_CONFIG, MATERIALS_CONFIG, SIM_CONFIG

    missing = [
        str(p) for p in (APP_CONFIG, BODY_CONFIG, MATERIALS_CONFIG, SIM_CONFIG)
        if not p.is_file()
    ]
    if missing:
        raise OSError(
            "Missing config files: " + ", ".join(missing)
        )
    logger.info("Config files present [OK]")


def main() -> None:
    """Run all bootstrap checks and exit appropriately."""
    logging.basicConfig(
        format="%(levelname)-8s %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )

    checks = [
        _check_python_version,
        _check_wearme_importable,
        _check_data_directories,
        _check_configs_exist,
    ]

    for check in checks:
        try:
            check()
        except OSError as exc:
            logger.error("Bootstrap failed: %s", exc)
            sys.exit(1)

    logger.info("Bootstrap complete - environment is ready.")


if __name__ == "__main__":
    main()
