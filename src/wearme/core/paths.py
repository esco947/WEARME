"""Centralised path constants for the WEARME project.

All file-system paths are derived from ``PROJECT_ROOT`` so that the package
can be run from any working directory without hardcoded paths.

Usage::

    from wearme.core.paths import DATA_DIR, CONFIGS_DIR
"""

from pathlib import Path

# src/wearme/core/paths.py  →  ../../../../  (4 levels up = project root)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

SRC_DIR: Path = PROJECT_ROOT / "src"
CONFIGS_DIR: Path = PROJECT_ROOT / "configs"
DATA_DIR: Path = PROJECT_ROOT / "data"
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
TESTS_DIR: Path = PROJECT_ROOT / "tests"

# Data sub-directories
BODY_MODELS_DIR: Path = DATA_DIR / "body_models"
GARMENTS_DIR: Path = DATA_DIR / "garments"
TEXTURES_DIR: Path = DATA_DIR / "textures"
SAMPLES_DIR: Path = DATA_DIR / "samples"

# Config files
APP_CONFIG: Path = CONFIGS_DIR / "app.yaml"
BODY_CONFIG: Path = CONFIGS_DIR / "body.yaml"
MATERIALS_CONFIG: Path = CONFIGS_DIR / "materials.yaml"
SIM_CONFIG: Path = CONFIGS_DIR / "sim.yaml"
