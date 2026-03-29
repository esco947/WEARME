"""WEARME environment bootstrap verification script.

Checks that the runtime environment meets all requirements before the
user attempts to run any WEARME module.

Run from the project root::

    python scripts/bootstrap.py

Exits with code 0 on success, 1 on first failure.
"""

import sys
import logging

logger = logging.getLogger("wearme.bootstrap")


def _check_python_version() -> None:
    """Verify Python >= 3.11."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        raise EnvironmentError(
            f"Python 3.11+ required, got {major}.{minor}. "
            "Please upgrade your Python interpreter."
        )
    logger.info("Python version: %d.%d ✓", major, minor)


def _check_wearme_importable() -> None:
    """Verify the wearme package is importable (i.e. installed with pip -e)."""
    try:
        import wearme  # noqa: F401
        from wearme.core import paths, constants, units  # noqa: F401
        from wearme.io.json_io import load_json, save_json  # noqa: F401
    except ImportError as exc:
        raise EnvironmentError(
            "Cannot import wearme. "
            "Run: pip install -e '.[dev]' from the project root."
        ) from exc
    logger.info("wearme package importable ✓")


def _check_data_directories() -> None:
    """Verify that required data sub-directories exist."""
    from wearme.core.paths import (
        DATA_DIR,
        BODY_MODELS_DIR,
        GARMENTS_DIR,
        TEXTURES_DIR,
        SAMPLES_DIR,
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
        raise EnvironmentError(
            "Missing data directories (run Phase 0 setup): "
            + ", ".join(missing)
        )
    logger.info("Data directories present ✓")


def _check_configs_exist() -> None:
    """Verify that YAML config files exist."""
    from wearme.core.paths import APP_CONFIG, BODY_CONFIG, MATERIALS_CONFIG, SIM_CONFIG

    missing = [
        str(p) for p in (APP_CONFIG, BODY_CONFIG, MATERIALS_CONFIG, SIM_CONFIG)
        if not p.is_file()
    ]
    if missing:
        raise EnvironmentError(
            "Missing config files: " + ", ".join(missing)
        )
    logger.info("Config files present ✓")


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
        except EnvironmentError as exc:
            logger.error("Bootstrap failed: %s", exc)
            sys.exit(1)

    logger.info("Bootstrap complete — environment is ready.")


if __name__ == "__main__":
    main()
