"""Tests for wearme.io.obj_export."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from wearme.io.obj_export import export_obj


# ── Synthetic mesh fixture ──────────────────────────────────────────────────────

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


def _read_obj(path: Path) -> dict:
    """Parse a minimal OBJ file into vertices and faces."""
    verts, faces = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("v "):
            parts = line.split()
            verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif line.startswith("f "):
            parts = line.split()
            faces.append([int(p) for p in parts[1:]])
    return {"verts": verts, "faces": faces}


class TestExportObj:
    def test_writes_file(self, tmp_path: Path) -> None:
        out = tmp_path / "body.obj"
        result = export_obj(_VERTS, _FACES, out)
        assert result == out
        assert out.exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        out = tmp_path / "sub" / "body.obj"
        export_obj(_VERTS, _FACES, out)
        assert out.exists()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        out = str(tmp_path / "body.obj")
        result = export_obj(_VERTS, _FACES, out)
        assert Path(result).exists()

    def test_vertex_count(self, tmp_path: Path) -> None:
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out)
        data = _read_obj(out)
        assert len(data["verts"]) == len(_VERTS)

    def test_face_count(self, tmp_path: Path) -> None:
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out)
        data = _read_obj(out)
        assert len(data["faces"]) == len(_FACES)

    def test_one_based_face_indices(self, tmp_path: Path) -> None:
        """OBJ spec requires 1-based vertex indices."""
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out)
        data = _read_obj(out)
        for face in data["faces"]:
            assert all(idx >= 1 for idx in face), "Face indices must be 1-based"

    def test_vertex_values_correct(self, tmp_path: Path) -> None:
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out)
        data = _read_obj(out)
        for parsed, expected in zip(data["verts"], _VERTS.tolist()):
            for p, e in zip(parsed, expected):
                assert abs(p - e) < 1e-5

    def test_height_scaling(self, tmp_path: Path) -> None:
        target = 1.75
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out, height_m=target)
        data = _read_obj(out)
        ys = [v[1] for v in data["verts"]]
        y_span = max(ys) - min(ys)
        assert abs(y_span - target) < 1e-4

    def test_no_scaling_when_height_none(self, tmp_path: Path) -> None:
        out_raw = tmp_path / "raw.obj"
        out_none = tmp_path / "none.obj"
        export_obj(_VERTS, _FACES, out_raw)
        export_obj(_VERTS, _FACES, out_none, height_m=None)
        assert out_raw.read_text(encoding="utf-8") == out_none.read_text(encoding="utf-8")

    def test_zero_height_skips_scaling(self, tmp_path: Path) -> None:
        out_raw = tmp_path / "raw.obj"
        out_zero = tmp_path / "zero.obj"
        export_obj(_VERTS, _FACES, out_raw)
        export_obj(_VERTS, _FACES, out_zero, height_m=0.0)
        assert out_raw.read_text(encoding="utf-8") == out_zero.read_text(encoding="utf-8")

    def test_comment_line_present(self, tmp_path: Path) -> None:
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out, comment="Test comment")
        text = out.read_text(encoding="utf-8")
        assert "# Test comment" in text

    def test_no_comment_when_empty(self, tmp_path: Path) -> None:
        out = tmp_path / "body.obj"
        export_obj(_VERTS, _FACES, out, comment="")
        text = out.read_text(encoding="utf-8")
        # The first line should not be a comment header
        first_non_empty = next(
            (l for l in text.splitlines() if l.strip() and not l.startswith("#")), ""
        )
        assert first_non_empty.startswith("v ")

    def test_flat_mesh_no_crash(self, tmp_path: Path) -> None:
        flat_verts = np.array([[0, 0, 0], [1, 0, 0], [0.5, 0, 1]], dtype=np.float64)
        flat_faces = np.array([[0, 1, 2]], dtype=np.int32)
        out = tmp_path / "flat.obj"
        export_obj(flat_verts, flat_faces, out, height_m=1.75)
        assert out.exists()


class TestBlenderBridgeImportable:
    """Verify blender_bridge can be imported outside Blender without errors."""

    def test_import_succeeds(self) -> None:
        from wearme.sim import blender_bridge  # noqa: PLC0415

        assert hasattr(blender_bridge, "clear_body_objects")
        assert hasattr(blender_bridge, "import_body_from_glb")
        assert hasattr(blender_bridge, "load_body_mesh")
        assert hasattr(blender_bridge, "export_scene_glb")
        assert hasattr(blender_bridge, "export_scene_obj")

    def test_bpy_not_available_flag(self) -> None:
        from wearme.sim import blender_bridge  # noqa: PLC0415

        # Outside Blender _BPY_AVAILABLE must be False
        assert blender_bridge._BPY_AVAILABLE is False  # noqa: SLF001

    def test_functions_raise_outside_blender(self) -> None:
        from wearme.sim import blender_bridge  # noqa: PLC0415

        with pytest.raises(RuntimeError, match="bpy"):
            blender_bridge.clear_body_objects()

        with pytest.raises(RuntimeError, match="bpy"):
            blender_bridge.import_body_from_glb("/nonexistent.glb")

        with pytest.raises(RuntimeError, match="bpy"):
            blender_bridge.export_scene_glb("/tmp/out.glb")

        with pytest.raises(RuntimeError, match="bpy"):
            blender_bridge.export_scene_obj("/tmp/out.obj")
