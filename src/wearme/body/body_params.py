"""Parametric body model data container.

Defines ``BodyParameters``, the central data structure that holds all
parameters needed to describe and generate a body shape. The class supports
creation with defaults, validation against configured limits, and JSON
round-trip serialisation.

Usage::

    from wearme.body.body_params import BodyParameters

    body = BodyParameters()           # neutral, mean shape, T-pose
    body = BodyParameters(gender="female", height_m=1.65)
    body.validate()                   # raises ValueError on bad values
    d = body.to_dict()                # → JSON-serialisable dict
    body2 = BodyParameters.from_dict(d)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from wearme.core.constants import (
    BODY_HEIGHT_DEFAULT_M,
    BODY_HEIGHT_MAX_M,
    BODY_HEIGHT_MIN_M,
    BODY_WEIGHT_DEFAULT_KG,
    BODY_WEIGHT_MAX_KG,
    BODY_WEIGHT_MIN_KG,
    SMPL_SHAPE_DIMS,
)

logger = logging.getLogger(__name__)

_VALID_GENDERS: frozenset[str] = frozenset({"neutral", "male", "female"})

#: Absolute beta coefficient limits (±4σ from SMPL training distribution)
BETA_MIN: float = -4.0
BETA_MAX: float = 4.0

#: Number of pose parameters (24 joints × 3 Rodrigues)
SMPL_POSE_DIMS: int = 72


def _default_betas() -> np.ndarray:
    return np.zeros(SMPL_SHAPE_DIMS, dtype=np.float64)


def _default_pose() -> np.ndarray:
    return np.zeros(SMPL_POSE_DIMS, dtype=np.float64)


def _default_trans() -> np.ndarray:
    return np.zeros(3, dtype=np.float64)


@dataclass
class BodyParameters:
    """All parameters needed to describe a human body shape in WEARME.

    Attributes:
        gender: Body gender for SMPL model selection.
            One of ``"neutral"``, ``"male"``, ``"female"``.
        betas: SMPL shape coefficients. Shape ``(10,)``.
            Controls principal shape axes from the SMPL training distribution.
            Typical range: ``[-4, 4]`` per dimension.
        pose: SMPL pose parameters in Rodrigues representation. Shape ``(72,)``.
            24 joints × 3 rotation components. Default is T-pose (all zeros).
        trans: Root translation in world space (metres). Shape ``(3,)``.
        height_m: Approximate standing height in metres (indicative slider value).
            Does not directly control SMPL geometry — use betas for shape.
        weight_kg: Approximate body weight in kg (indicative slider value).
    """

    gender: str = "neutral"
    betas: np.ndarray = field(default_factory=_default_betas)
    pose: np.ndarray = field(default_factory=_default_pose)
    trans: np.ndarray = field(default_factory=_default_trans)
    height_m: float = BODY_HEIGHT_DEFAULT_M
    weight_kg: float = BODY_WEIGHT_DEFAULT_KG

    def validate(self) -> None:
        """Validate all parameters against configured limits.

        Raises:
            ValueError: If any parameter is outside its allowed range or has
                an incorrect shape.
        """
        if self.gender not in _VALID_GENDERS:
            raise ValueError(
                f"Invalid gender {self.gender!r}. "
                f"Must be one of {sorted(_VALID_GENDERS)}."
            )

        if self.betas.shape != (SMPL_SHAPE_DIMS,):
            raise ValueError(
                f"betas must have shape ({SMPL_SHAPE_DIMS},), "
                f"got {self.betas.shape}."
            )
        if np.any(self.betas < BETA_MIN) or np.any(self.betas > BETA_MAX):
            raise ValueError(
                f"All betas must be in [{BETA_MIN}, {BETA_MAX}]. "
                f"Got min={self.betas.min():.3f}, max={self.betas.max():.3f}."
            )

        if self.pose.shape != (SMPL_POSE_DIMS,):
            raise ValueError(
                f"pose must have shape ({SMPL_POSE_DIMS},), "
                f"got {self.pose.shape}."
            )

        if self.trans.shape != (3,):
            raise ValueError(
                f"trans must have shape (3,), got {self.trans.shape}."
            )

        if not (BODY_HEIGHT_MIN_M <= self.height_m <= BODY_HEIGHT_MAX_M):
            raise ValueError(
                f"height_m must be in [{BODY_HEIGHT_MIN_M}, {BODY_HEIGHT_MAX_M}], "
                f"got {self.height_m}."
            )

        if not (BODY_WEIGHT_MIN_KG <= self.weight_kg <= BODY_WEIGHT_MAX_KG):
            raise ValueError(
                f"weight_kg must be in [{BODY_WEIGHT_MIN_KG}, {BODY_WEIGHT_MAX_KG}], "
                f"got {self.weight_kg}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary.

        All numpy arrays are converted to plain Python lists.

        Returns:
            Dictionary suitable for ``json.dump``.
        """
        return {
            "gender": self.gender,
            "betas": self.betas.tolist(),
            "pose": self.pose.tolist(),
            "trans": self.trans.tolist(),
            "height_m": self.height_m,
            "weight_kg": self.weight_kg,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BodyParameters:
        """Deserialise from a dictionary (e.g. loaded from JSON).

        Args:
            data: Dictionary as produced by ``to_dict()``.

        Returns:
            A new ``BodyParameters`` instance.

        Raises:
            KeyError: If a required key is missing.
            ValueError: If the data fails validation.
        """
        params = cls(
            gender=data["gender"],
            betas=np.array(data["betas"], dtype=np.float64),
            pose=np.array(data["pose"], dtype=np.float64),
            trans=np.array(data["trans"], dtype=np.float64),
            height_m=float(data["height_m"]),
            weight_kg=float(data["weight_kg"]),
        )
        params.validate()
        return params

    def copy(self) -> BodyParameters:
        """Return a deep copy of this instance.

        Returns:
            New ``BodyParameters`` with independent numpy arrays.
        """
        return BodyParameters(
            gender=self.gender,
            betas=self.betas.copy(),
            pose=self.pose.copy(),
            trans=self.trans.copy(),
            height_m=self.height_m,
            weight_kg=self.weight_kg,
        )
