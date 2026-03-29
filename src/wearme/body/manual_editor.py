"""Manual body editor — slider-to-beta mapping.

Provides a human-friendly slider interface that maps intuitive parameters
(height, weight, build) to the underlying SMPL beta coefficients. The
mapping is based on the known semantic directions of the first several
SMPL PCA shape axes for the neutral model.

SMPL shape principal components (neutral model, empirical observations):
    beta[0]: overall height / body scale (positive = taller)
    beta[1]: body width (negative = heavier/wider, positive = leaner)
    beta[2]: chest/torso fullness (positive = fuller chest)
    beta[3]: hip width (positive = wider hips)
    beta[4]: limb length (positive = longer limbs)

Note: The SMPL PCA axes are data-driven and do not have strict semantic
meanings. These mappings are approximate and intended for interactive use.

Usage::

    from wearme.body.manual_editor import BodyEditor
    from wearme.body.body_params import BodyParameters

    params = BodyParameters()
    editor = BodyEditor(params)

    editor.set_slider("height", 1.80)
    editor.set_slider("weight", 90.0)
    result = editor.params
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np

from wearme.body.body_params import BodyParameters
from wearme.core.constants import (
    BODY_HEIGHT_DEFAULT_M,
    BODY_HEIGHT_MAX_M,
    BODY_HEIGHT_MIN_M,
    BODY_WEIGHT_DEFAULT_KG,
    BODY_WEIGHT_MAX_KG,
    BODY_WEIGHT_MIN_KG,
)

logger = logging.getLogger(__name__)


@dataclass
class SliderDefinition:
    """Definition of a single slider.

    Attributes:
        name: Unique slider identifier.
        label: Human-readable label.
        min_val: Minimum slider value.
        max_val: Maximum slider value.
        default: Default slider value.
        unit: Display unit string.
        description: Short description of what the slider controls.
    """

    name: str
    label: str
    min_val: float
    max_val: float
    default: float
    unit: str
    description: str


#: All available sliders in the manual body editor.
SLIDER_DEFINITIONS: list[SliderDefinition] = [
    SliderDefinition(
        name="height",
        label="Height",
        min_val=BODY_HEIGHT_MIN_M,
        max_val=BODY_HEIGHT_MAX_M,
        default=BODY_HEIGHT_DEFAULT_M,
        unit="m",
        description="Overall standing height (drives beta[0] and height_m)",
    ),
    SliderDefinition(
        name="weight",
        label="Weight",
        min_val=BODY_WEIGHT_MIN_KG,
        max_val=BODY_WEIGHT_MAX_KG,
        default=BODY_WEIGHT_DEFAULT_KG,
        unit="kg",
        description="Approximate body weight (drives beta[1] and weight_kg)",
    ),
    SliderDefinition(
        name="chest",
        label="Chest fullness",
        min_val=-3.0,
        max_val=3.0,
        default=0.0,
        unit="",
        description="Chest / upper torso fullness (drives beta[2])",
    ),
    SliderDefinition(
        name="hips",
        label="Hip width",
        min_val=-3.0,
        max_val=3.0,
        default=0.0,
        unit="",
        description="Hip width (drives beta[3])",
    ),
    SliderDefinition(
        name="limbs",
        label="Limb length",
        min_val=-3.0,
        max_val=3.0,
        default=0.0,
        unit="",
        description="Relative limb length (drives beta[4])",
    ),
]

_SLIDER_MAP: dict[str, SliderDefinition] = {s.name: s for s in SLIDER_DEFINITIONS}


def _normalise(value: float, slider: SliderDefinition) -> float:
    """Normalise a slider value to the range [-1, 1].

    Args:
        value: Raw slider value in physical units.
        slider: Slider definition.

    Returns:
        Normalised value in [-1, 1].
    """
    span = slider.max_val - slider.min_val
    return 2.0 * (value - slider.min_val) / span - 1.0


def _denormalise(normalised: float, slider: SliderDefinition) -> float:
    """Convert a [-1, 1] normalised value back to physical units.

    Args:
        normalised: Value in [-1, 1].
        slider: Slider definition.

    Returns:
        Value in physical units.
    """
    return slider.min_val + (normalised + 1.0) / 2.0 * (slider.max_val - slider.min_val)


class BodyEditor:
    """Interactive body editor with named sliders.

    Each slider maps to one or more SMPL beta coefficients and/or the
    ``height_m`` / ``weight_kg`` indicative fields of :class:`BodyParameters`.

    Args:
        params: Initial body parameters. A deep copy is made internally so
            the original is not mutated.
    """

    def __init__(self, params: BodyParameters | None = None) -> None:
        self._params: BodyParameters = (
            deepcopy(params) if params is not None else BodyParameters()
        )

    @property
    def params(self) -> BodyParameters:
        """Return a copy of the current body parameters."""
        return deepcopy(self._params)

    def set_slider(self, name: str, value: float) -> None:
        """Apply a slider value to the body parameters.

        Args:
            name: Slider name. Must be one of the keys in
                :data:`SLIDER_DEFINITIONS`.
            value: New slider value in the slider's physical units.

        Raises:
            KeyError: If *name* is not a known slider.
            ValueError: If *value* is outside the slider's ``[min_val, max_val]``
                range.
        """
        if name not in _SLIDER_MAP:
            raise KeyError(
                f"Unknown slider {name!r}. "
                f"Available: {sorted(_SLIDER_MAP)}."
            )
        slider = _SLIDER_MAP[name]
        if not (slider.min_val <= value <= slider.max_val):
            raise ValueError(
                f"Slider {name!r} value {value} is outside "
                f"[{slider.min_val}, {slider.max_val}]."
            )

        norm = _normalise(value, slider)
        # beta range: -4 to 4 → scale normalised to [-3, 3] to stay within limits
        beta_value = norm * 3.0

        if name == "height":
            self._params.height_m = value
            self._params.betas[0] = beta_value
            logger.debug("Set height=%.3fm (beta[0]=%.2f)", value, beta_value)

        elif name == "weight":
            self._params.weight_kg = value
            # Negative beta[1] = heavier/wider in SMPL neutral model
            self._params.betas[1] = -beta_value
            logger.debug("Set weight=%.1fkg (beta[1]=%.2f)", value, -beta_value)

        elif name == "chest":
            self._params.betas[2] = beta_value
            logger.debug("Set chest (beta[2]=%.2f)", beta_value)

        elif name == "hips":
            self._params.betas[3] = beta_value
            logger.debug("Set hips (beta[3]=%.2f)", beta_value)

        elif name == "limbs":
            self._params.betas[4] = beta_value
            logger.debug("Set limbs (beta[4]=%.2f)", beta_value)

    def get_slider(self, name: str) -> float:
        """Read the current effective value of a slider.

        Args:
            name: Slider name.

        Returns:
            Current slider value in physical units.

        Raises:
            KeyError: If *name* is not a known slider.
        """
        if name not in _SLIDER_MAP:
            raise KeyError(f"Unknown slider {name!r}.")
        slider = _SLIDER_MAP[name]

        if name == "height":
            return self._params.height_m
        if name == "weight":
            return self._params.weight_kg

        # Reverse-map from beta to normalised slider
        beta_idx = {"chest": 2, "hips": 3, "limbs": 4}[name]
        beta = float(self._params.betas[beta_idx])
        norm = beta / 3.0
        return float(_denormalise(np.clip(norm, -1.0, 1.0), slider))

    def reset(self) -> None:
        """Reset all sliders to their default values."""
        self._params = BodyParameters()
        logger.debug("Editor reset to defaults.")

    def slider_definitions(self) -> list[dict[str, Any]]:
        """Return all slider definitions as plain dictionaries.

        Useful for building UI components.

        Returns:
            List of dicts with keys: name, label, min, max, default, unit,
            description, current_value.
        """
        return [
            {
                "name": s.name,
                "label": s.label,
                "min": s.min_val,
                "max": s.max_val,
                "default": s.default,
                "unit": s.unit,
                "description": s.description,
                "current_value": self.get_slider(s.name),
            }
            for s in SLIDER_DEFINITIONS
        ]
