"""Parametric body model data container — Phase 2.

Defines ``BodyParameters``, the central data structure that holds all
parameters needed to describe a human body shape.  Phase 2 adds a 55-param
anatomical system (``_params`` dict) alongside the original SMPL fields so
that both old and new code paths remain fully supported.

Backward-compatibility guarantee:
    * ``BodyParameters(gender=g, betas=arr, height_m=h, weight_kg=w)``
      continues to work without change.
    * ``params.betas``, ``params.pose``, ``params.trans`` remain accessible
      dataclass fields (consumed by ``smpl_bridge.generate_vertices``).
    * ``params.height_m`` and ``params.weight_kg`` remain readable attributes.

New API (Phase 2):
    * ``params._params``   — dict of 55+ anatomical floats
    * ``params._locked``   — set of param names frozen against rescaling
    * ``params.set_param(name, value, propagate=True)``
    * ``params.lock(name)`` / ``params.unlock(name)``
    * ``params.to_dict()`` emits a ``"params"`` key; ``from_dict`` handles
      both old (no ``"params"`` key) and new format.

Usage::

    from wearme.body.body_params import BodyParameters

    body = BodyParameters()                       # neutral defaults
    body = BodyParameters(gender="female", height_m=1.65)
    body.set_param("hip_circ_m", 0.95)            # + propagation off
    body.set_param("height_m", 1.70, propagate=True)   # rescales all lengths
    body.lock("dart_width_m")                     # survives future rescaling
    d = body.to_dict()
    body2 = BodyParameters.from_dict(d)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from wearme.body.proportions import (
    PARAM_REGISTRY,
    allometric_scale,
    get_defaults,
    validate_param,
    weight_redistribute,
)
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

#: Number of SMPL pose parameters (24 joints × 3 Rodrigues)
SMPL_POSE_DIMS: int = 72


# ── BodyParameters ─────────────────────────────────────────────────────────────

@dataclass
class BodyParameters:
    """All parameters needed to describe a human body shape in WEARME.

    SMPL fields (backward-compatible):
        gender:    SMPL model selection — ``"neutral"`` | ``"male"`` | ``"female"``.
        betas:     SMPL shape coefficients, shape ``(10,)``.
        pose:      SMPL pose (Rodrigues), shape ``(72,)``.  Default: T-pose.
        trans:     Root translation in world space (m), shape ``(3,)``.
        height_m:  Approximate standing height (m).  Mirrors ``_params["height_m"]``.
        weight_kg: Approximate weight (kg).  Mirrors ``_params["weight_kg"]``.

    Phase-2 fields (private, not in constructor):
        _params:  Dict of 55 anatomical measurements + derived bmi.
        _locked:  Set of param names frozen against allometric / weight rescaling.
    """

    gender:    str        = "neutral"
    betas:     np.ndarray = field(default_factory=lambda: np.zeros(SMPL_SHAPE_DIMS, dtype=np.float64))
    pose:      np.ndarray = field(default_factory=lambda: np.zeros(SMPL_POSE_DIMS, dtype=np.float64))
    trans:     np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    height_m:  float      = BODY_HEIGHT_DEFAULT_M
    weight_kg: float      = BODY_WEIGHT_DEFAULT_KG

    # ── Phase-2 private state (not part of __init__) ─────────────────────────
    _params: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _locked: set[str]         = field(default_factory=set,  init=False, repr=False)

    def __post_init__(self) -> None:
        # Bootstrap _params from population defaults, then override with
        # the height_m / weight_kg supplied to the constructor.
        self._params = get_defaults(self.gender)
        self._params["height_m"]  = float(self.height_m)
        self._params["weight_kg"] = float(self.weight_kg)
        h = float(self.height_m)
        w = float(self.weight_kg)
        self._params["bmi"] = w / (h * h) if h > 0 else 25.0

    # ── Core param API ────────────────────────────────────────────────────────

    def set_param(self, name: str, value: float, propagate: bool = True) -> None:
        """Set one anatomical parameter with optional cascade.

        For ``height_m`` with ``propagate=True``: triggers allometric scaling
        of all height-dependent params (limb lengths, landmarks…).

        For ``weight_kg`` with ``propagate=True``: triggers sex-specific
        weight redistribution across circumferences and widths.

        Args:
            name:      Param key from ``PARAM_REGISTRY``.
            value:     New value in the param's native units (metres / kg /
                       degrees).
            propagate: Whether to trigger cascading updates.

        Raises:
            KeyError:   Unknown parameter name.
            ValueError: Value out of bounds, or param is read-only.
        """
        validate_param(name, value)  # raises KeyError / ValueError

        if name in self._locked:
            return

        if propagate and name == "height_m":
            allometric_scale(self._params, float(value), self._locked)
            self.height_m = float(value)
        elif propagate and name == "weight_kg":
            weight_redistribute(self._params, float(value), self.gender, self._locked)
            self.weight_kg = float(value)
        else:
            self._params[name] = float(value)
            if name == "height_m":
                self.height_m = float(value)
                h = float(value)
                w = self._params.get("weight_kg", BODY_WEIGHT_DEFAULT_KG)
                self._params["bmi"] = w / (h * h) if h > 0 else 25.0
            elif name == "weight_kg":
                self.weight_kg = float(value)
                h = self._params.get("height_m", BODY_HEIGHT_DEFAULT_M)
                self._params["bmi"] = float(value) / (h * h) if h > 0 else 25.0

    def lock(self, name: str) -> None:
        """Freeze *name* so it is skipped by allometric / weight rescaling.

        Args:
            name: Any param name (does not have to be in PARAM_REGISTRY).
        """
        self._locked.add(name)

    def unlock(self, name: str) -> None:
        """Release a previously locked param.

        Args:
            name: Param name to unlock.
        """
        self._locked.discard(name)

    def is_locked(self, name: str) -> bool:
        """Return whether *name* is currently locked."""
        return name in self._locked

    # ── Derived property ──────────────────────────────────────────────────────

    @property
    def bmi(self) -> float:
        """Body Mass Index, computed from ``_params``."""
        return self._params.get("bmi", 25.0)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """Validate all parameters.

        Checks:
        * Gender is a known value.
        * SMPL array shapes are correct.
        * SMPL betas are within ``[BETA_MIN, BETA_MAX]``.
        * height_m and weight_kg are within configured limits.
        * All settable anatomical params are within PARAM_REGISTRY bounds.

        Raises:
            ValueError: On any violation.
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
            raise ValueError(f"trans must have shape (3,), got {self.trans.shape}.")

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

        for name, value in self._params.items():
            bounds = PARAM_REGISTRY.get(name)
            if bounds is None or bounds.read_only:
                continue
            if not (bounds.min_val <= value <= bounds.max_val):
                raise ValueError(
                    f"Anatomical param {name!r} = {value:.4f} is outside "
                    f"[{bounds.min_val}, {bounds.max_val}]."
                )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary.

        Returns a *new-format* dict with both the SMPL arrays and the full
        anatomical params, so ``from_dict`` can restore the complete state.

        Returns:
            Dictionary suitable for ``json.dumps``.
        """
        return {
            "gender":    self.gender,
            "params":    dict(self._params),           # full 55-param dict
            "locked":    sorted(self._locked),
            "betas":     self.betas.tolist(),
            "pose":      self.pose.tolist(),
            "trans":     self.trans.tolist(),
            # Legacy keys kept for old readers / migration scripts
            "height_m":  self.height_m,
            "weight_kg": self.weight_kg,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BodyParameters:
        """Deserialise from a dictionary.

        Handles both the legacy format (no ``"params"`` key — just
        ``betas`` / ``height_m`` / ``weight_kg``) and the new Phase-2
        format (has ``"params"`` key with all 55 anatomical values).

        Args:
            data: Dict as produced by :meth:`to_dict` or the old format.

        Returns:
            New ``BodyParameters`` instance.

        Raises:
            ValueError: If the data fails validation.
        """
        gender    = str(data.get("gender", "neutral"))
        betas     = np.array(data.get("betas",  [0.0] * SMPL_SHAPE_DIMS), dtype=np.float64)
        pose      = np.array(data.get("pose",   [0.0] * SMPL_POSE_DIMS),  dtype=np.float64)
        trans     = np.array(data.get("trans",  [0.0, 0.0, 0.0]),         dtype=np.float64)

        raw_params: dict[str, float] | None = data.get("params")
        if raw_params is not None:
            height_m  = float(raw_params.get("height_m",  BODY_HEIGHT_DEFAULT_M))
            weight_kg = float(raw_params.get("weight_kg", BODY_WEIGHT_DEFAULT_KG))
        else:
            height_m  = float(data.get("height_m",  BODY_HEIGHT_DEFAULT_M))
            weight_kg = float(data.get("weight_kg", BODY_WEIGHT_DEFAULT_KG))

        obj = cls(
            gender=gender, betas=betas, pose=pose, trans=trans,
            height_m=height_m, weight_kg=weight_kg,
        )

        if raw_params is not None:
            for name, value in raw_params.items():
                if name in PARAM_REGISTRY:
                    obj._params[name] = float(value)
            obj._locked = set(data.get("locked", []))

        return obj

    # ── Copy ──────────────────────────────────────────────────────────────────

    def copy(self) -> BodyParameters:
        """Return a deep copy with independent numpy arrays and param dict."""
        new = BodyParameters(
            gender=self.gender,
            betas=self.betas.copy(),
            pose=self.pose.copy(),
            trans=self.trans.copy(),
            height_m=self.height_m,
            weight_kg=self.weight_kg,
        )
        # Overwrite the freshly-bootstrapped _params with our actual state
        new._params = dict(self._params)
        new._locked = set(self._locked)
        return new
