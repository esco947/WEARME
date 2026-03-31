"""Tests for wearme.io.glb_export."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from wearme.io.glb_export import export_glb, export_glb_bytes


# ── Synthetic mesh fixture ──────────────────────────────────────────────────────

# Minimal valid mesh: a tetrahedron (4 vertices, 4 triangular faces)
_VERTS = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.5, 1.0, 0.0],
        [0.5, 0.5, 1.0],
    ],
    dtype=np.float64,
)
_FACES = np.array(
    [
        [0, 1, 2],
        [0, 1, 3],
        [0, 2, 3],
        [1, 2, 3],
    ],
    dtype=np.int32,
)

# GLB magic bytes (ASCII "glTF")
_GLB_MAGIC = b"glTF"


class TestExportGlbBytes:
    def test_returns_bytes(self) -> None:
        result = export_glb_bytes(_VERTS, _FACES)
        assert isinstance(result, bytes)

    def test_glb_magic_header(self) -> None:
        result = export_glb_bytes(_VERTS, _FACES)
        assert result[:4] == _GLB_MAGIC, "GLB must start with 'glTF' magic"

    def test_non_empty(self) -> None:
        result = export_glb_bytes(_VERTS, _FACES)
        assert len(result) > 12  # GLB header alone is 12 bytes

    def test_height_scaling_changes_output(self) -> None:
        raw = export_glb_bytes(_VERTS, _FACES)
        scaled = export_glb_bytes(_VERTS, _FACES, height_m=1.75)
        # The scaled GLB should differ from the unscaled one
        assert raw != scaled

    def test_height_none_skips_scaling(self) -> None:
        a = export_glb_bytes(_VERTS, _FACES, height_m=None)
        b = export_glb_bytes(_VERTS, _FACES)
        assert a == b

    def test_zero_height_skips_scaling(self) -> None:
        a = export_glb_bytes(_VERTS, _FACES, height_m=0.0)
        b = export_glb_bytes(_VERTS, _FACES)
        assert a == b

    def test_negative_height_skips_scaling(self) -> None:
        a = export_glb_bytes(_VERTS, _FACES, height_m=-1.0)
        b = export_glb_bytes(_VERTS, _FACES)
        assert a == b


class TestExportGlb:
    def test_writes_file(self, tmp_path: Path) -> None:
        out = tmp_path / "body.glb"
        result = export_glb(_VERTS, _FACES, out)
        assert result == out
        assert out.exists()

    def test_written_content_is_valid_glb(self, tmp_path: Path) -> None:
        out = tmp_path / "body.glb"
        export_glb(_VERTS, _FACES, out)
        assert out.read_bytes()[:4] == _GLB_MAGIC

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "deep" / "body.glb"
        export_glb(_VERTS, _FACES, out)
        assert out.exists()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        out = str(tmp_path / "body.glb")
        result = export_glb(_VERTS, _FACES, out)
        assert Path(result).exists()

    def test_height_scaling_applied(self, tmp_path: Path) -> None:
        out_raw = tmp_path / "raw.glb"
        out_scaled = tmp_path / "scaled.glb"
        export_glb(_VERTS, _FACES, out_raw)
        export_glb(_VERTS, _FACES, out_scaled, height_m=1.80)
        assert out_raw.read_bytes() != out_scaled.read_bytes()

    def test_flat_mesh_skips_scaling(self, tmp_path: Path) -> None:
        """Mesh with zero Y-extent should not crash; scaling is skipped."""
        flat_verts = np.array(
            [[0, 0, 0], [1, 0, 0], [0.5, 0, 1]], dtype=np.float64
        )
        flat_faces = np.array([[0, 1, 2]], dtype=np.int32)
        out = tmp_path / "flat.glb"
        export_glb(flat_verts, flat_faces, out, height_m=1.75)
        assert out.exists()


class TestScaleToHeightInternal:
    """Validate the scaling logic via the public bytes API."""

    def test_target_height_respected(self) -> None:
        target = 1.75
        glb = export_glb_bytes(_VERTS, _FACES, height_m=target)
        # Re-import via trimesh to check the actual mesh height
        import io

        import trimesh

        scene = trimesh.load(io.BytesIO(glb), file_type="glb")
        if isinstance(scene, trimesh.Scene):
            mesh = next(iter(scene.geometry.values()))
        else:
            mesh = scene
        y_span = float(mesh.vertices[:, 1].max() - mesh.vertices[:, 1].min())
        assert abs(y_span - target) < 1e-4, f"Expected height {target}, got {y_span}"
