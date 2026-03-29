"""SMPL body model inference bridge (pure numpy).

Loads SMPL model data from ``.pkl`` files and runs forward inference
(shape blending + Linear Blend Skinning) entirely in numpy — no chumpy
or automatic differentiation required.

Supported model files (SMPL v1.1.0):
    - ``basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl``
    - ``basicmodel_m_lbs_10_207_0_v1.1.0.pkl``
    - ``basicmodel_f_lbs_10_207_0_v1.1.0.pkl``

The bridge first looks for model files in ``data/body_models/``.
If not found, it falls back to the ``smpl_model/`` source directory
(local installation, not versioned).

Usage::

    from wearme.body.smpl_bridge import load_model_data, generate_vertices
    from wearme.body.body_params import BodyParameters

    model = load_model_data("neutral")
    vertices = generate_vertices(BodyParameters(), model)  # (6890, 3)
"""

from __future__ import annotations

import logging
import pickle
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from wearme.body.body_params import BodyParameters
from wearme.core.paths import BODY_MODELS_DIR, SMPL_MODEL_DIR

# ── chumpy compatibility ───────────────────────────────────────────────────────
# The SMPL v1.1.0 .pkl files were serialised with chumpy arrays.
# We do NOT need chumpy for inference — only the underlying numpy data.
# The custom unpickler below intercepts any chumpy class reference and
# substitutes a lightweight proxy that exposes the numpy array via __array__.


class _ChProxy:
    """Minimal proxy for chumpy Ch/array objects stored in SMPL .pkl files.

    When unpickling, chumpy sets the object's state via ``__setstate__``.
    The state dict contains an ``'x'`` key with the raw numpy array.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._arr: np.ndarray | None = None

    def __setstate__(self, state: Any) -> None:
        if isinstance(state, dict) and "x" in state:
            self._arr = np.asarray(state["x"])
        elif state is not None:
            try:
                self._arr = np.asarray(state)
            except Exception:  # noqa: BLE001
                pass

    def __array__(self, dtype: Any = None) -> np.ndarray:
        arr = self._arr if self._arr is not None else np.zeros(0)
        return arr if dtype is None else arr.astype(dtype)


class _SMPLUnpickler(pickle.Unpickler):
    """Unpickler that replaces any chumpy class with :class:`_ChProxy`.

    Uses latin-1 encoding so that Python 2-serialised .pkl files (which
    contain raw byte strings) are decoded correctly.
    """

    def __init__(self, file: Any) -> None:
        super().__init__(file, encoding="latin1")

    def find_class(self, module: str, name: str) -> Any:
        if "chumpy" in module:
            return _ChProxy
        return super().find_class(module, name)

logger = logging.getLogger(__name__)

# ── PKL file names ─────────────────────────────────────────────────────────────

_PKL_NAMES: dict[str, str] = {
    "neutral": "basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl",
    "male": "basicmodel_m_lbs_10_207_0_v1.1.0.pkl",
    "female": "basicmodel_f_lbs_10_207_0_v1.1.0.pkl",
}


# ── Data container ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SMPLModelData:
    """Immutable container for the raw SMPL model arrays.

    Attributes:
        gender: Model gender identifier.
        v_template: Base mesh vertices at mean shape. Shape ``(6890, 3)``.
        shapedirs: Shape blend-shape basis. Shape ``(6890, 3, 10)``.
        posedirs: Pose blend-shape basis. Shape ``(6890, 3, 207)``.
        j_regressor: Joint regressor matrix. Shape ``(24, 6890)``.
        kintree_table: Kinematic tree (parent links). Shape ``(2, 24)``.
        weights: Per-vertex blend weights. Shape ``(6890, 24)``.
        faces: Triangle face indices. Shape ``(13776, 3)``.
    """

    gender: str
    v_template: np.ndarray   # (6890, 3)
    shapedirs: np.ndarray    # (6890, 3, 10)
    posedirs: np.ndarray     # (6890, 3, 207)
    j_regressor: np.ndarray  # (24, 6890)
    kintree_table: np.ndarray  # (2, 24)
    weights: np.ndarray      # (6890, 24)
    faces: np.ndarray        # (13776, 3)


# ── Model loading ──────────────────────────────────────────────────────────────


def _resolve_pkl_path(gender: str) -> Path:
    """Find the .pkl file for *gender*, checking data/body_models/ first.

    Copies the file from smpl_model/ to data/body_models/ if needed so that
    future calls find it in the canonical location.

    Args:
        gender: One of ``"neutral"``, ``"male"``, ``"female"``.

    Returns:
        Resolved path to the existing .pkl file.

    Raises:
        FileNotFoundError: If the file cannot be found in either location.
        ValueError: If *gender* is not a recognised value.
    """
    if gender not in _PKL_NAMES:
        raise ValueError(
            f"Unknown gender {gender!r}. Must be one of {list(_PKL_NAMES)}."
        )
    filename = _PKL_NAMES[gender]

    # Primary: data/body_models/
    primary = BODY_MODELS_DIR / filename
    if primary.is_file():
        return primary

    # Fallback: smpl_model/ local installation
    fallback = SMPL_MODEL_DIR / "models" / filename
    if fallback.is_file():
        logger.info(
            "Copying SMPL model %s from smpl_model/ to data/body_models/",
            filename,
        )
        BODY_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fallback, primary)
        return primary

    raise FileNotFoundError(
        f"SMPL model file for gender={gender!r} not found.\n"
        f"  Checked: {primary}\n"
        f"  Checked: {fallback}\n"
        "Copy the .pkl files into data/body_models/ or place them under "
        "smpl_model/SMPL_python_v.1.1.0/smpl/models/."
    )


def _to_array(obj: Any) -> np.ndarray:
    """Convert scipy sparse matrix or chumpy array to a dense numpy array."""
    if hasattr(obj, "toarray"):
        return np.array(obj.toarray())
    if hasattr(obj, "todense"):
        return np.array(obj.todense())
    return np.array(obj)


def load_model_data(gender: str = "neutral") -> SMPLModelData:
    """Load SMPL model data from the .pkl file for the given gender.

    Args:
        gender: One of ``"neutral"``, ``"male"``, ``"female"``.
            Defaults to ``"neutral"``.

    Returns:
        :class:`SMPLModelData` with all model arrays as numpy arrays.

    Raises:
        FileNotFoundError: If the model file cannot be located.
    """
    pkl_path = _resolve_pkl_path(gender)
    logger.info("Loading SMPL model (%s) from %s", gender, pkl_path)

    with pkl_path.open("rb") as fh:
        raw: dict[str, Any] = _SMPLUnpickler(fh).load()  # noqa: S301

    # shapedirs may have more than SMPL_SHAPE_DIMS columns (e.g. 300 in some
    # model variants that include expression components).  We keep only the
    # first SMPL_SHAPE_DIMS (10) columns — the standard body-shape axes.
    from wearme.core.constants import SMPL_SHAPE_DIMS  # noqa: PLC0415

    shapedirs_full = _to_array(raw["shapedirs"]).astype(np.float64)
    shapedirs = shapedirs_full[..., :SMPL_SHAPE_DIMS]

    return SMPLModelData(
        gender=gender,
        v_template=_to_array(raw["v_template"]).astype(np.float64),
        shapedirs=shapedirs,
        posedirs=_to_array(raw["posedirs"]).astype(np.float64),
        j_regressor=_to_array(raw["J_regressor"]).astype(np.float64),
        kintree_table=_to_array(raw["kintree_table"]).astype(np.int32),
        weights=_to_array(raw["weights"]).astype(np.float64),
        faces=_to_array(raw["f"]).astype(np.int32),
    )


# ── LBS math ──────────────────────────────────────────────────────────────────


def _rodrigues_to_matrix(rvec: np.ndarray) -> np.ndarray:
    """Convert a Rodrigues rotation vector to a 3×3 rotation matrix.

    Args:
        rvec: Rodrigues vector. Shape ``(3,)``.

    Returns:
        Rotation matrix. Shape ``(3, 3)``.
    """
    angle = float(np.linalg.norm(rvec))
    if angle < 1e-8:
        return np.eye(3, dtype=np.float64)
    axis = rvec / angle
    c, s = np.cos(angle), np.sin(angle)
    t = 1.0 - c
    x, y, z = axis
    return np.array(
        [
            [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
        ],
        dtype=np.float64,
    )


def _lrotmin(pose: np.ndarray) -> np.ndarray:
    """Compute pose blend-shape features (SMPL's lrotmin).

    Converts pose Rodrigues vectors for joints 1-23 (skipping root) to
    flattened rotation-minus-identity matrices.

    Args:
        pose: Full pose vector. Shape ``(72,)``.

    Returns:
        Pose blend-shape feature vector. Shape ``(207,)``
        = 23 joints × 9 (flattened R − I).
    """
    features: list[np.ndarray] = []
    for j in range(1, 24):  # skip root (joint 0)
        rvec = pose[j * 3 : j * 3 + 3]
        R = _rodrigues_to_matrix(rvec)
        features.append((R - np.eye(3)).ravel())
    return np.concatenate(features)  # (207,)


def _global_rigid_transforms(
    pose: np.ndarray,
    joints: np.ndarray,
    kintree_table: np.ndarray,
) -> np.ndarray:
    """Compute global 4×4 rigid transforms for all 24 SMPL joints.

    Args:
        pose: Pose vector. Shape ``(72,)``.
        joints: Joint positions. Shape ``(24, 3)``.
        kintree_table: Kinematic tree. Shape ``(2, 24)``.
            Row 0 = parent indices, row 1 = child indices.

    Returns:
        Global transforms. Shape ``(24, 4, 4)``.
    """
    parent: np.ndarray = kintree_table[0]  # parent[i] = parent joint of joint i

    # Local transforms (joint-relative)
    local: np.ndarray = np.zeros((24, 4, 4), dtype=np.float64)
    for j in range(24):
        R = _rodrigues_to_matrix(pose[j * 3 : j * 3 + 3])
        t = joints[j] if j == 0 else joints[j] - joints[parent[j]]
        local[j, :3, :3] = R
        local[j, :3, 3] = t
        local[j, 3, 3] = 1.0

    # Global transforms via kinematic chain
    global_transforms: np.ndarray = np.zeros_like(local)
    global_transforms[0] = local[0]
    for j in range(1, 24):
        global_transforms[j] = global_transforms[parent[j]] @ local[j]

    # Subtract rest-pose joint contribution
    result: np.ndarray = np.zeros_like(global_transforms)
    for j in range(24):
        rest = np.eye(4, dtype=np.float64)
        rest[:3, 3] = joints[j]
        result[j] = global_transforms[j] @ np.linalg.inv(rest)

    return result


# ── Public inference API ───────────────────────────────────────────────────────


def generate_vertices(
    params: BodyParameters,
    model_data: SMPLModelData,
) -> np.ndarray:
    """Generate mesh vertices for a given body configuration.

    Runs the full SMPL forward pass:
    shape blending → joint regression → pose blending → LBS → translation.

    Args:
        params: Body parameters (betas, pose, trans).
        model_data: Loaded SMPL model data.

    Returns:
        Final posed and shaped vertices. Shape ``(6890, 3)``, in metres.
    """
    betas = params.betas
    pose = params.pose
    trans = params.trans

    # 1. Shape blend shapes
    # shapedirs: (6890, 3, 10)  betas: (10,) → v_shaped: (6890, 3)
    v_shaped = (
        model_data.v_template
        + np.einsum("ijk,k->ij", model_data.shapedirs, betas)
    )

    # 2. Joint regression from shaped vertices
    joints = model_data.j_regressor @ v_shaped  # (24, 3)

    # 3. Pose blend shapes
    pose_features = _lrotmin(pose)  # (207,)
    # posedirs: (6890, 3, 207)  pose_features: (207,) → v_posed: (6890, 3)
    v_posed = v_shaped + np.einsum("ijk,k->ij", model_data.posedirs, pose_features)

    # 4. Global rigid transforms
    transforms = _global_rigid_transforms(pose, joints, model_data.kintree_table)
    # transforms: (24, 4, 4)

    # 5. Linear Blend Skinning
    # weights: (6890, 24)   transforms.reshape(24,16): (24, 16)
    # T: (6890, 4, 4) blended transform per vertex
    t_flat = model_data.weights @ transforms.reshape(24, 16)  # (6890, 16)
    t_mat = t_flat.reshape(6890, 4, 4)

    v_homo = np.concatenate(
        [v_posed, np.ones((6890, 1), dtype=np.float64)], axis=1
    )  # (6890, 4)

    v_final = np.einsum("nij,nj->ni", t_mat, v_homo)[:, :3]  # (6890, 3)

    # 6. Translation
    v_final += trans[np.newaxis, :]

    return v_final


def get_joint_positions(
    params: BodyParameters,
    model_data: SMPLModelData,
) -> np.ndarray:
    """Return the 24 SMPL joint positions for a given body configuration.

    Computes joints from the shaped (but not yet posed) vertices, then
    applies the global rigid transforms from the pose.

    Args:
        params: Body parameters.
        model_data: Loaded SMPL model data.

    Returns:
        Transformed joint positions. Shape ``(24, 3)``, in metres.
    """
    betas = params.betas
    pose = params.pose
    trans = params.trans

    # Shape
    v_shaped = (
        model_data.v_template
        + np.einsum("ijk,k->ij", model_data.shapedirs, betas)
    )
    joints = model_data.j_regressor @ v_shaped  # (24, 3)

    # Apply global transforms to extract joint positions
    transforms = _global_rigid_transforms(pose, joints, model_data.kintree_table)
    # The joint position is the translation column of each transform
    joints_posed = transforms[:, :3, 3] + trans[np.newaxis, :]  # (24, 3)

    return joints_posed
