"""Tests for wearme.core.paths."""

from pathlib import Path

from wearme.core import paths


def test_project_root_is_directory() -> None:
    """PROJECT_ROOT must point to an existing directory."""
    assert paths.PROJECT_ROOT.is_dir(), (
        f"PROJECT_ROOT not found: {paths.PROJECT_ROOT}"
    )


def test_project_root_contains_pyproject() -> None:
    """PROJECT_ROOT must contain pyproject.toml (sanity check)."""
    assert (paths.PROJECT_ROOT / "pyproject.toml").is_file()


def test_configs_dir_is_relative_to_root() -> None:
    """CONFIGS_DIR must be a sub-directory of PROJECT_ROOT."""
    assert paths.CONFIGS_DIR == paths.PROJECT_ROOT / "configs"


def test_data_dir_is_relative_to_root() -> None:
    """DATA_DIR must be a sub-directory of PROJECT_ROOT."""
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"


def test_src_dir_is_relative_to_root() -> None:
    """SRC_DIR must be a sub-directory of PROJECT_ROOT."""
    assert paths.SRC_DIR == paths.PROJECT_ROOT / "src"


def test_data_subdirs_are_relative_to_data() -> None:
    """All DATA sub-directory constants must be children of DATA_DIR."""
    assert paths.BODY_MODELS_DIR == paths.DATA_DIR / "body_models"
    assert paths.GARMENTS_DIR == paths.DATA_DIR / "garments"
    assert paths.TEXTURES_DIR == paths.DATA_DIR / "textures"
    assert paths.SAMPLES_DIR == paths.DATA_DIR / "samples"


def test_config_paths_are_yaml_files() -> None:
    """Config path constants must have .yaml extension."""
    for config_path in (
        paths.APP_CONFIG,
        paths.BODY_CONFIG,
        paths.MATERIALS_CONFIG,
        paths.SIM_CONFIG,
    ):
        assert config_path.suffix == ".yaml", f"Expected .yaml: {config_path}"


def test_all_path_constants_are_path_objects() -> None:
    """Every exported path constant must be a pathlib.Path instance."""
    path_attrs = [
        "PROJECT_ROOT", "SRC_DIR", "CONFIGS_DIR", "DATA_DIR",
        "SCRIPTS_DIR", "DOCS_DIR", "TESTS_DIR",
        "BODY_MODELS_DIR", "GARMENTS_DIR", "TEXTURES_DIR", "SAMPLES_DIR",
        "APP_CONFIG", "BODY_CONFIG", "MATERIALS_CONFIG", "SIM_CONFIG",
    ]
    for attr in path_attrs:
        value = getattr(paths, attr)
        assert isinstance(value, Path), f"{attr} is not a Path: {type(value)}"
