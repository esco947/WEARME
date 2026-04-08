"""Tests for core.smpl_model — SMPLModel class and load_smpl helper."""

import numpy as np
import pytest

# Skip the entire module if PKL files are absent (CI without model data)
pytest.importorskip("trimesh")  # ensure trimesh present for later phases too

try:
    from core.smpl_model import BETA_MAX, BETA_MIN, N_BETAS, SMPLModel, load_smpl
    _CAN_LOAD = True
except Exception:
    _CAN_LOAD = False

pytestmark = pytest.mark.skipif(
    not _CAN_LOAD, reason="core.smpl_model could not be imported"
)


@pytest.fixture(scope="module")
def male_model() -> SMPLModel:
    try:
        return load_smpl("male")
    except FileNotFoundError:
        pytest.skip("Male PKL not found — skipping SMPL tests")


@pytest.fixture(scope="module")
def female_model() -> SMPLModel:
    try:
        return load_smpl("female")
    except FileNotFoundError:
        pytest.skip("Female PKL not found — skipping SMPL tests")


class TestSMPLModelForward:
    def test_default_shape_vertices(self, male_model):
        betas = np.zeros(N_BETAS)
        verts = male_model.forward(betas)
        assert verts.shape == (6890, 3), f"Expected (6890,3), got {verts.shape}"
        assert not np.any(np.isnan(verts)), "NaN in vertices"
        assert not np.any(np.isinf(verts)), "Inf in vertices"

    def test_height_range(self, male_model):
        betas = np.zeros(N_BETAS)
        verts = male_model.forward(betas)
        height = float(verts[:, 1].max() - verts[:, 1].min())
        assert 1.60 <= height <= 1.90, f"Height {height:.3f}m out of expected [1.60, 1.90]"

    def test_betas_change_shape(self, male_model):
        zeros = np.zeros(N_BETAS)
        modified = zeros.copy()
        modified[0] = 3.0
        v_zero = male_model.forward(zeros)
        v_mod  = male_model.forward(modified)
        max_diff = float(np.abs(v_zero - v_mod).max())
        assert max_diff > 1e-3, "betas[0]=+3 should change vertices noticeably"

    def test_female_loads(self, female_model):
        betas = np.zeros(N_BETAS)
        verts = female_model.forward(betas)
        assert verts.shape == (6890, 3)
        assert not np.any(np.isnan(verts))

    def test_betas_clamped(self, male_model):
        # Betas beyond ±5 should be clamped, not crash
        extreme = np.full(N_BETAS, 100.0)
        verts = male_model.forward(extreme)
        assert verts.shape == (6890, 3)
        assert not np.any(np.isnan(verts))

    def test_tpose_translation(self, male_model):
        betas = np.zeros(N_BETAS)
        trans = np.array([1.0, 0.0, 0.0])
        v_origin = male_model.forward(betas)
        v_trans  = male_model.forward(betas, trans=trans)
        diff = v_trans - v_origin
        assert np.allclose(diff[:, 0], 1.0, atol=1e-6), "Translation not applied correctly"


class TestSMPLModelJoints:
    def test_joints_shape(self, male_model):
        joints = male_model.get_joints(np.zeros(N_BETAS))
        assert joints.shape == (24, 3), f"Expected (24,3), got {joints.shape}"
        assert not np.any(np.isnan(joints))

    def test_joints_change_with_betas(self, male_model):
        j0 = male_model.get_joints(np.zeros(N_BETAS))
        j1 = male_model.get_joints(np.array([3.0] + [0.0] * 9))
        assert float(np.abs(j0 - j1).max()) > 1e-4


class TestSMPLModelProperties:
    def test_faces_shape(self, male_model):
        assert male_model.faces.shape == (13776, 3)

    def test_num_betas(self, male_model):
        assert male_model.num_betas == N_BETAS

    def test_beta_constants(self):
        assert BETA_MIN == -5.0
        assert BETA_MAX == 5.0


class TestLoadSmpl:
    def test_unknown_gender_raises(self):
        with pytest.raises(ValueError, match="Unknown gender"):
            load_smpl("neutral")

    def test_caching(self, male_model):
        model2 = load_smpl("male")
        assert model2 is male_model, "load_smpl should return cached instance"
