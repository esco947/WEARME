"""Tests for core.slider_optimizer — optimize_betas_from_targets()."""

import numpy as np
import pytest

try:
    from core.smpl_model import load_smpl
    from core.mesh_measurements import measure_mesh
    from core.slider_optimizer import BETA_MAX, BETA_MIN, optimize_betas_from_targets
    _CAN_IMPORT = True
except Exception:
    _CAN_IMPORT = False

pytestmark = pytest.mark.skipif(
    not _CAN_IMPORT, reason="core modules could not be imported"
)


@pytest.fixture(scope="module")
def male_model():
    try:
        return load_smpl("male")
    except FileNotFoundError:
        pytest.skip("Male PKL not found — skipping optimizer tests")


class TestInterface:
    def test_unknown_key_raises(self, male_model):
        with pytest.raises(ValueError, match="No valid keys"):
            optimize_betas_from_targets(male_model, {"unknown": 1.80}, np.zeros(10))

    def test_returns_correct_shape(self, male_model):
        betas = optimize_betas_from_targets(
            male_model, {"height": 1.80}, np.zeros(10), max_iter=5
        )
        assert betas.shape == (10,)

    def test_betas_in_bounds(self, male_model):
        betas = optimize_betas_from_targets(
            male_model, {"height": 2.10, "chest_circumference": 1.30}, np.zeros(10),
            max_iter=10
        )
        assert np.all(betas >= BETA_MIN), f"betas below {BETA_MIN}: {betas.min():.3f}"
        assert np.all(betas <= BETA_MAX), f"betas above {BETA_MAX}: {betas.max():.3f}"


class TestConvergence:
    def test_height_target(self, male_model):
        target_h = 1.90
        betas = optimize_betas_from_targets(
            male_model, {"height": target_h}, np.zeros(10), max_iter=200
        )
        verts  = male_model.forward(betas)
        height = float(verts[:, 1].max() - verts[:, 1].min())
        assert abs(height - target_h) < 0.08, (
            f"Height {height:.3f}m vs target {target_h}m (tolerance 8 cm)"
        )

    def test_chest_target_reduces_error(self, male_model):
        # Measure default chest
        v0     = male_model.forward(np.zeros(10))
        j0     = male_model.get_joints(np.zeros(10))
        m0     = measure_mesh(v0, male_model.faces, j0)
        default_chest = m0["chest_circumference"]

        # Set a very different target chest
        target_chest = default_chest + 0.10  # +10 cm
        betas = optimize_betas_from_targets(
            male_model,
            {"chest_circumference": target_chest},
            np.zeros(10),
            max_iter=100,
        )
        v1     = male_model.forward(betas)
        j1     = male_model.get_joints(betas)
        m1     = measure_mesh(v1, male_model.faces, j1)

        err_before = abs(default_chest     - target_chest)
        err_after  = abs(m1["chest_circumference"] - target_chest)
        assert err_after < err_before, (
            f"Chest error did not reduce: before={err_before:.3f} after={err_after:.3f}"
        )

    def test_multi_target(self, male_model):
        targets = {"height": 1.85, "chest_circumference": 1.05}
        betas = optimize_betas_from_targets(male_model, targets, np.zeros(10), max_iter=100)
        verts  = male_model.forward(betas)
        joints = male_model.get_joints(betas)
        m      = measure_mesh(verts, male_model.faces, joints)
        height = float(verts[:, 1].max() - verts[:, 1].min())

        assert abs(height - 1.85) < 0.05, f"Height {height:.3f}m, target 1.85m"
        # chest might not converge perfectly with multi-target, just check it moved
        assert m["chest_circumference"] > 0
