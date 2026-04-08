"""Tests for core.mesh_measurements — measure_mesh()."""

import numpy as np
import pytest

try:
    from core.smpl_model import load_smpl
    from core.mesh_measurements import measure_mesh
    _CAN_IMPORT = True
except Exception:
    _CAN_IMPORT = False

pytestmark = pytest.mark.skipif(
    not _CAN_IMPORT, reason="core modules could not be imported"
)

EXPECTED_KEYS = {
    "height",
    "chest_circumference",
    "waist_circumference",
    "hip_circumference",
    "shoulder_width",
    "inseam",
}


@pytest.fixture(scope="module")
def male_mesh():
    try:
        model = load_smpl("male")
    except FileNotFoundError:
        pytest.skip("Male PKL not found — skipping measurement tests")
    betas = np.zeros(10)
    verts  = model.forward(betas)
    joints = model.get_joints(betas)
    faces  = model.faces
    return verts, faces, joints


@pytest.fixture(scope="module")
def male_model():
    try:
        return load_smpl("male")
    except FileNotFoundError:
        pytest.skip("Male PKL not found")


class TestMeasureKeys:
    def test_all_keys_present(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert EXPECTED_KEYS == set(m.keys()), f"Missing/extra keys: {set(m.keys()) ^ EXPECTED_KEYS}"

    def test_returns_dict(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert isinstance(m, dict)


class TestMeasureRanges:
    def test_chest_range(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert 0.85 <= m["chest_circumference"] <= 1.15, (
            f"Chest {m['chest_circumference']:.3f}m outside [0.85, 1.15]"
        )

    def test_waist_range(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert 0.75 <= m["waist_circumference"] <= 1.05, (
            f"Waist {m['waist_circumference']:.3f}m outside [0.75, 1.05]"
        )

    def test_hip_range(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert 0.85 <= m["hip_circumference"] <= 1.15, (
            f"Hip {m['hip_circumference']:.3f}m outside [0.85, 1.15]"
        )

    def test_all_positive(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        for key, val in m.items():
            assert val > 0, f"{key}={val} is not positive"

    def test_all_below_3m(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        for key, val in m.items():
            assert val < 3.0, f"{key}={val} is unrealistically large"

    def test_height_range(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert 1.60 <= m["height"] <= 1.90, (
            f"Height {m['height']:.3f}m outside [1.60, 1.90]"
        )

    def test_shoulder_positive(self, male_mesh):
        verts, faces, joints = male_mesh
        m = measure_mesh(verts, faces, joints)
        assert 0.30 <= m["shoulder_width"] <= 0.60, (
            f"Shoulder width {m['shoulder_width']:.3f}m outside [0.30, 0.60]"
        )


class TestMeasureSensitivity:
    def test_heavier_larger_chest(self, male_model):
        b0 = np.zeros(10)
        b1 = b0.copy()
        b1[1] = -3.0  # beta[1] INVERTED: negative = heavier

        v0, f = male_model.forward(b0), male_model.faces
        v1     = male_model.forward(b1)
        j0    = male_model.get_joints(b0)
        j1    = male_model.get_joints(b1)

        m0 = measure_mesh(v0, f, j0)
        m1 = measure_mesh(v1, f, j1)

        assert m1["chest_circumference"] > m0["chest_circumference"], (
            f"Expected heavier beta to increase chest: "
            f"{m0['chest_circumference']:.3f} → {m1['chest_circumference']:.3f}"
        )

    def test_no_joints_fallback(self, male_mesh):
        verts, faces, _ = male_mesh
        m = measure_mesh(verts, faces, joints=None)
        assert set(m.keys()) == EXPECTED_KEYS
        assert all(v > 0 for v in m.values())
