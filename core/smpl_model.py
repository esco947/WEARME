"""SMPL body model — pure NumPy forward pass.

Wraps the SMPL v1.1.0 PKL files in an ``SMPLModel`` class that accepts raw
numpy arrays (betas, pose, trans) directly, without the BodyParameters
dataclass from the old architecture.

Betas are the single source of truth. Measurements are always derived from
the mesh, never from a parameter matrix.

Supported models:
    - male:   basicmodel_m_lbs_10_207_0_v1.1.0.pkl
    - female: basicmodel_f_lbs_10_207_0_v1.1.0.pkl

Usage::

    from core.smpl_model import load_smpl
    import numpy as np

    model = load_smpl("male")
    verts = model.forward(np.zeros(10))   # (6890, 3)
    joints = model.get_joints(np.zeros(10))  # (24, 3)
"""

from __future__ import annotations

import logging
import pickle
import shutil
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# core/smpl_model.py → ../../ = project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BODY_MODELS_DIR = _PROJECT_ROOT / "data" / "body_models"
_SMPL_MODEL_DIR = (
    _PROJECT_ROOT / "smpl_model" / "SMPL_python_v.1.1.0" / "smpl"
)

_PKL_NAMES: dict[str, str] = {
    "male":   "basicmodel_m_lbs_10_207_0_v1.1.0.pkl",
    "female": "basicmodel_f_lbs_10_207_0_v1.1.0.pkl",
}

N_BETAS = 10
BETA_MIN = -5.0
BETA_MAX = 5.0

# ── chumpy compatibility ───────────────────────────────────────────────────────


class _ChProxy:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._arr: np.ndarray | None = None

    def __setstate__(self, state: Any) -> None:
        if isinstance(state, dict) and "x" in state:
            self._arr = np.asarray(state["x"])
        elif state is not None:
            try:
                self._arr = np.asarray(state)
            except Exception:
                pass

    def __array__(self, dtype: Any = None) -> np.ndarray:
        arr = self._arr if self._arr is not None else np.zeros(0)
        return arr if dtype is None else arr.astype(dtype)


class _SMPLUnpickler(pickle.Unpickler):
    def __init__(self, file: Any) -> None:
        super().__init__(file, encoding="latin1")

    def find_class(self, module: str, name: str) -> Any:
        if "chumpy" in module:
            return _ChProxy
        return super().find_class(module, name)


# ── Rodrigues / LBS helpers ────────────────────────────────────────────────────


def _rodrigues(rvec: np.ndarray) -> np.ndarray:
    angle = float(np.linalg.norm(rvec))
    if angle < 1e-8:
        return np.eye(3, dtype=np.float64)
    axis = rvec / angle
    c, s = np.cos(angle), np.sin(angle)
    t = 1.0 - c
    x, y, z = axis
    return np.array(
        [
            [t * x * x + c,     t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c,     t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c    ],
        ],
        dtype=np.float64,
    )


def _lrotmin(pose: np.ndarray) -> np.ndarray:
    features: list[np.ndarray] = []
    for j in range(1, 24):
        R = _rodrigues(pose[j * 3: j * 3 + 3])
        features.append((R - np.eye(3)).ravel())
    return np.concatenate(features)  # (207,)


def _global_transforms(
    pose: np.ndarray,
    joints: np.ndarray,
    kintree: np.ndarray,
) -> np.ndarray:
    parent = kintree[0]
    local = np.zeros((24, 4, 4), dtype=np.float64)
    for j in range(24):
        R = _rodrigues(pose[j * 3: j * 3 + 3])
        t = joints[j] if j == 0 else joints[j] - joints[parent[j]]
        local[j, :3, :3] = R
        local[j, :3, 3] = t
        local[j, 3, 3] = 1.0

    G = np.zeros_like(local)
    G[0] = local[0]
    for j in range(1, 24):
        G[j] = G[parent[j]] @ local[j]

    result = np.zeros_like(G)
    for j in range(24):
        rest = np.eye(4, dtype=np.float64)
        rest[:3, 3] = joints[j]
        result[j] = G[j] @ np.linalg.inv(rest)
    return result


def _to_array(obj: Any) -> np.ndarray:
    if hasattr(obj, "toarray"):
        return np.array(obj.toarray())
    if hasattr(obj, "todense"):
        return np.array(obj.todense())
    return np.array(obj)


# ── SMPLModel class ────────────────────────────────────────────────────────────


class SMPLModel:
    """Loaded SMPL model that generates vertices from betas/pose/trans.

    Args:
        model_path: Path to the ``.pkl`` file.
        num_betas:  Number of shape components to use (clamped to actual count).
    """

    def __init__(self, model_path: str | Path, num_betas: int = N_BETAS) -> None:
        path = Path(model_path)
        logger.info("Loading SMPL model from %s", path)

        with path.open("rb") as fh:
            raw: dict[str, Any] = _SMPLUnpickler(fh).load()

        shapedirs_full = _to_array(raw["shapedirs"]).astype(np.float64)
        self._num_betas = min(num_betas, shapedirs_full.shape[2])

        self._v_template  = _to_array(raw["v_template"]).astype(np.float64)
        self._shapedirs   = shapedirs_full[..., : self._num_betas]
        self._posedirs    = _to_array(raw["posedirs"]).astype(np.float64)
        self._j_regressor = _to_array(raw["J_regressor"]).astype(np.float64)
        self._kintree     = _to_array(raw["kintree_table"]).astype(np.int32)
        self._weights     = _to_array(raw["weights"]).astype(np.float64)
        self._faces       = _to_array(raw["f"]).astype(np.int32)

    @property
    def num_betas(self) -> int:
        return self._num_betas

    @property
    def faces(self) -> np.ndarray:
        return self._faces

    def forward(
        self,
        betas: np.ndarray,
        pose: np.ndarray | None = None,
        trans: np.ndarray | None = None,
    ) -> np.ndarray:
        """Run the SMPL forward pass.

        Args:
            betas: Shape coefficients, shape ``(num_betas,)``, range [-5, +5].
            pose:  Axis-angle rotations for 24 joints, shape ``(72,)``.
                   Defaults to T-pose (zeros).
            trans: Global translation, shape ``(3,)``. Defaults to origin.

        Returns:
            Vertices ``(6890, 3)`` in metres.
        """
        betas = np.clip(
            np.asarray(betas, dtype=np.float64)[: self._num_betas],
            BETA_MIN, BETA_MAX,
        )
        pose  = np.zeros(72, dtype=np.float64) if pose is None else np.asarray(pose, dtype=np.float64)
        trans = np.zeros(3,  dtype=np.float64) if trans is None else np.asarray(trans, dtype=np.float64)

        # 1. Shape blend shapes
        v_shaped = self._v_template + np.einsum("ijk,k->ij", self._shapedirs, betas)

        # 2. Joint regression
        joints = self._j_regressor @ v_shaped  # (24, 3)

        # 3. Pose blend shapes
        pose_feats = _lrotmin(pose)
        v_posed = v_shaped + np.einsum("ijk,k->ij", self._posedirs, pose_feats)

        # 4. Global transforms
        transforms = _global_transforms(pose, joints, self._kintree)

        # 5. LBS
        t_flat = self._weights @ transforms.reshape(24, 16)  # (6890, 16)
        t_mat  = t_flat.reshape(6890, 4, 4)
        v_homo = np.concatenate([v_posed, np.ones((6890, 1), dtype=np.float64)], axis=1)
        v_final = np.einsum("nij,nj->ni", t_mat, v_homo)[:, :3]

        # 6. Translation
        return v_final + trans[np.newaxis, :]

    def get_joints(
        self,
        betas: np.ndarray,
        pose: np.ndarray | None = None,
        trans: np.ndarray | None = None,
    ) -> np.ndarray:
        """Return the 24 SMPL joint positions in world space.

        Uses the joint regressor applied to the shaped mesh (T-pose), then
        applies global pose transforms to get the posed joint positions.

        Args:
            betas: Shape coefficients ``(num_betas,)``.
            pose:  Pose ``(72,)``. Defaults to T-pose (zeros).
            trans: Translation ``(3,)``. Defaults to origin.

        Returns:
            Joint positions ``(24, 3)`` in metres.
        """
        betas = np.clip(
            np.asarray(betas, dtype=np.float64)[: self._num_betas],
            BETA_MIN, BETA_MAX,
        )
        pose  = np.zeros(72, dtype=np.float64) if pose is None else np.asarray(pose, dtype=np.float64)
        trans = np.zeros(3,  dtype=np.float64) if trans is None else np.asarray(trans, dtype=np.float64)

        # Shape blend shapes → T-pose anatomical joint positions
        v_shaped = self._v_template + np.einsum("ijk,k->ij", self._shapedirs, betas)
        joints_tpose = self._j_regressor @ v_shaped  # (24, 3)

        if not np.any(pose):
            # T-pose: anatomical positions are the final positions
            return joints_tpose + trans[np.newaxis, :]

        # Posed: compute global transforms G (before rest-pose subtraction)
        # then read world positions from G[:, :3, 3]
        parent = self._kintree[0]
        local = np.zeros((24, 4, 4), dtype=np.float64)
        for j in range(24):
            R = _rodrigues(pose[j * 3: j * 3 + 3])
            t = joints_tpose[j] if j == 0 else joints_tpose[j] - joints_tpose[parent[j]]
            local[j, :3, :3] = R
            local[j, :3, 3] = t
            local[j, 3, 3] = 1.0
        G = np.zeros_like(local)
        G[0] = local[0]
        for j in range(1, 24):
            G[j] = G[parent[j]] @ local[j]

        joints_posed = G[:, :3, 3]  # world-space positions after posing
        return joints_posed + trans[np.newaxis, :]


# ── Module-level cache + convenience loader ────────────────────────────────────

_model_cache: dict[str, SMPLModel] = {}


def load_smpl(gender: str, num_betas: int = N_BETAS) -> SMPLModel:
    """Return a cached :class:`SMPLModel` for *gender* (``"male"`` or ``"female"``).

    Args:
        gender:    ``"male"`` or ``"female"``.
        num_betas: Shape components to use (≤ 10 for standard SMPL v1.1.0).

    Returns:
        Loaded and cached :class:`SMPLModel`.

    Raises:
        ValueError: If *gender* is not recognised.
        FileNotFoundError: If the PKL file cannot be found.
    """
    if gender not in _PKL_NAMES:
        raise ValueError(
            f"Unknown gender {gender!r}. Must be 'male' or 'female'."
        )

    cache_key = f"{gender}:{num_betas}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    filename = _PKL_NAMES[gender]
    primary  = _BODY_MODELS_DIR / filename
    if not primary.is_file():
        fallback = _SMPL_MODEL_DIR / "models" / filename
        if fallback.is_file():
            logger.info("Copying %s → data/body_models/", filename)
            _BODY_MODELS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fallback, primary)
        else:
            raise FileNotFoundError(
                f"SMPL model for gender={gender!r} not found.\n"
                f"  Checked: {primary}\n"
                f"  Checked: {fallback}\n"
                "Copy the .pkl file into data/body_models/."
            )

    model = SMPLModel(primary, num_betas=num_betas)
    _model_cache[cache_key] = model
    return model
