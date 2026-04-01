"""Manual body editor — Phase 2.

Wraps ``BodyParameters`` with a UI-friendly slider interface, linked
propagation, undo/redo (up to 50 snapshots), and batch update mode.

The editor exposes ~20 primary sliders that map directly to anatomical
param names.  Sliders for ``height_m`` and ``weight_kg`` automatically
trigger allometric scaling / weight redistribution when changed.

Usage::

    from wearme.body.manual_editor import BodyEditor
    from wearme.body.body_params import BodyParameters

    editor = BodyEditor()
    editor.set_slider("height_m", 1.70)          # triggers allometric scale
    editor.set_slider("chest_circ_m", 0.92)
    editor.undo()                                 # reverts chest change
    editor.redo()                                 # reapplies it

    # Batch multiple sliders as one undo snapshot:
    editor.begin_batch()
    editor.set_slider("waist_circ_m", 0.72)
    editor.set_slider("hip_circ_m",   0.98)
    editor.commit_batch()

    params = editor.params                        # deep copy of current state
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from wearme.body.body_params import BodyParameters
from wearme.body.proportions import PARAM_REGISTRY

logger = logging.getLogger(__name__)

_MAX_HISTORY: int = 50


# ── Slider definitions ────────────────────────────────────────────────────────

@dataclass
class SliderDefinition:
    """Metadata for one UI slider.

    Attributes:
        name:          Anatomical param key (must be in ``PARAM_REGISTRY``).
        label:         Human-readable French label.
        group:         UI grouping category.
        min_val:       Minimum allowed slider value.
        max_val:       Maximum allowed slider value.
        default:       Default value.
        unit:          Display unit string (``"m"`` | ``"kg"`` | ``"°"`` | ``""``).
        description:   Short description.
    """
    name:        str
    label:       str
    group:       str
    min_val:     float
    max_val:     float
    default:     float
    unit:        str
    description: str


#: Primary sliders exposed to the UI (~20 controls).
#: All ``name`` values map directly to ``BodyParameters._params`` keys.
SLIDER_DEFINITIONS: list[SliderDefinition] = [
    # ── Global ────────────────────────────────────────────────────────────────
    SliderDefinition("height_m",         "Taille",                 "global",       1.40,  2.20,  1.695, "m",  "Taille debout — déclenche le rescaling allométrique"),
    SliderDefinition("weight_kg",        "Poids",                  "global",       40.0,  200.0, 72.5,  "kg", "Poids corporel — redistribue les circonférences"),
    # ── Trunk circumferences ──────────────────────────────────────────────────
    SliderDefinition("chest_circ_m",     "Tour de poitrine",       "trunk_circ",   0.70,  1.50,  0.945, "m",  "Circonférence maximale de la poitrine"),
    SliderDefinition("underbust_circ_m", "Tour sous-poitrine",     "trunk_circ",   0.60,  1.30,  0.858, "m",  "Tour sous la poitrine (bande de soutien-gorge)"),
    SliderDefinition("waist_circ_m",     "Tour de taille",         "trunk_circ",   0.55,  1.40,  0.785, "m",  "Tour à la taille la plus étroite"),
    SliderDefinition("abdomen_circ_m",   "Tour d'abdomen",         "trunk_circ",   0.60,  1.50,  0.855, "m",  "Tour au niveau du nombril"),
    SliderDefinition("hip_circ_m",       "Tour de hanches",        "trunk_circ",   0.75,  1.50,  0.980, "m",  "Tour aux hanches les plus larges"),
    # ── Trunk widths ──────────────────────────────────────────────────────────
    SliderDefinition("shoulder_width_m", "Largeur d'épaules",      "trunk_width",  0.30,  0.60,  0.393, "m",  "Largeur biacromiale"),
    SliderDefinition("back_width_m",     "Largeur du dos",         "trunk_width",  0.25,  0.50,  0.340, "m",  "Largeur du dos au niveau des omoplates"),
    # ── Upper limbs ───────────────────────────────────────────────────────────
    SliderDefinition("arm_length_m",     "Longueur de bras",       "upper_limb",   0.50,  0.90,  0.595, "m",  "Épaule → poignet"),
    SliderDefinition("upper_arm_circ_m", "Tour de biceps",         "upper_limb",   0.20,  0.55,  0.320, "m",  "Tour du bras au biceps"),
    SliderDefinition("wrist_circ_m",     "Tour de poignet",        "upper_limb",   0.13,  0.25,  0.162, "m",  "Tour au poignet"),
    # ── Lower limbs ───────────────────────────────────────────────────────────
    SliderDefinition("inseam_m",         "Entrejambe",             "lower_limb",   0.60,  1.00,  0.778, "m",  "Longueur de l'entrejambe"),
    SliderDefinition("thigh_circ_m",     "Tour de cuisse",         "lower_limb",   0.40,  0.85,  0.573, "m",  "Tour de cuisse à la partie la plus large"),
    SliderDefinition("knee_circ_m",      "Tour de genou",          "lower_limb",   0.28,  0.55,  0.375, "m",  "Tour au genou"),
    SliderDefinition("calf_circ_m",      "Tour de mollet",         "lower_limb",   0.28,  0.58,  0.373, "m",  "Tour au mollet le plus large"),
    # ── Garment surface ───────────────────────────────────────────────────────
    SliderDefinition("front_length_m",   "Longueur devant",        "garment",      0.30,  0.55,  0.408, "m",  "Longueur du devant (épaule → taille)"),
    SliderDefinition("back_length_m",    "Longueur dos",           "garment",      0.33,  0.58,  0.433, "m",  "Longueur du dos (nuque → taille)"),
    SliderDefinition("dart_width_m",     "Pince poitrine",         "garment",      0.00,  0.12,  0.025, "m",  "Largeur de pince de poitrine"),
    SliderDefinition("shoulder_slope_deg","Inclinaison épaules",   "garment",      10.0,  35.0,  22.0,  "°",  "Angle de pente des épaules"),
]

_SLIDER_MAP: dict[str, SliderDefinition] = {s.name: s for s in SLIDER_DEFINITIONS}


# ── BodyEditor ────────────────────────────────────────────────────────────────

class BodyEditor:
    """Interactive body editor with named sliders, undo/redo, and batch mode.

    Args:
        params: Initial body parameters.  A deep copy is made so the
                original is not mutated.
    """

    def __init__(self, params: BodyParameters | None = None) -> None:
        self._params:  BodyParameters       = deepcopy(params) if params is not None else BodyParameters()
        self._history: list[BodyParameters] = []   # undo stack
        self._future:  list[BodyParameters] = []   # redo stack
        self._batch:   bool                 = False
        self._batch_buf: dict[str, float]   = {}

    # ── Public property ───────────────────────────────────────────────────────

    @property
    def params(self) -> BodyParameters:
        """Return a deep copy of the current body parameters."""
        return self._params.copy()

    # ── Slider interface ──────────────────────────────────────────────────────

    def set_slider(self, name: str, value: float) -> None:
        """Apply a slider value.

        If in batch mode, queues the change for atomic commit.
        Otherwise saves an undo snapshot first, then applies immediately.

        Args:
            name:  Param name — must appear in :data:`SLIDER_DEFINITIONS`
                   **or** be a valid PARAM_REGISTRY key.
            value: New value in the param's native units.

        Raises:
            KeyError:   Unknown param name.
            ValueError: Value out of bounds.
        """
        # Validate that the param exists and value is in range
        if name not in PARAM_REGISTRY:
            raise KeyError(f"Unknown param {name!r}.")

        if self._batch:
            self._batch_buf[name] = value
            return

        self._push_history()
        self._params.set_param(name, value, propagate=True)
        logger.debug("set_slider(%r, %r)", name, value)

    def get_slider(self, name: str) -> float:
        """Read the current value of a param.

        Args:
            name: Param name.

        Returns:
            Current value in native units.

        Raises:
            KeyError: Unknown param name.
        """
        if name not in PARAM_REGISTRY:
            raise KeyError(f"Unknown param {name!r}.")
        return float(self._params._params.get(name, PARAM_REGISTRY[name].default_neutral))

    # ── Batch mode ────────────────────────────────────────────────────────────

    def begin_batch(self) -> None:
        """Enter batch mode.

        Subsequent :meth:`set_slider` calls are queued.  Call
        :meth:`commit_batch` to apply them all atomically (single undo step).
        """
        self._batch     = True
        self._batch_buf = {}

    def commit_batch(self) -> None:
        """Apply all batched changes atomically (single undo snapshot).

        Propagation (allometric / weight redistribution) runs once at the
        end rather than after each individual change.
        """
        if not self._batch_buf:
            self._batch = False
            return

        self._push_history()

        # Apply non-propagating params first, then height/weight last
        height_val  = self._batch_buf.pop("height_m",  None)
        weight_val  = self._batch_buf.pop("weight_kg", None)

        for name, value in self._batch_buf.items():
            self._params.set_param(name, value, propagate=False)

        if weight_val is not None:
            self._params.set_param("weight_kg", weight_val, propagate=True)
        if height_val is not None:
            self._params.set_param("height_m",  height_val, propagate=True)

        self._batch     = False
        self._batch_buf = {}
        logger.debug("commit_batch — %d params applied", len(self._batch_buf) + (height_val is not None) + (weight_val is not None))

    def discard_batch(self) -> None:
        """Discard all queued batch changes without applying."""
        self._batch     = False
        self._batch_buf = {}

    # ── Undo / redo ───────────────────────────────────────────────────────────

    def undo(self) -> None:
        """Revert to the previous state."""
        if not self._history:
            return
        self._future.append(self._params.copy())
        self._params = self._history.pop()
        logger.debug("undo — history depth=%d", len(self._history))

    def redo(self) -> None:
        """Reapply the last undone change."""
        if not self._future:
            return
        self._history.append(self._params.copy())
        self._params = self._future.pop()
        logger.debug("redo — future depth=%d", len(self._future))

    def can_undo(self) -> bool:
        """Return True if there are states to undo."""
        return len(self._history) > 0

    def can_redo(self) -> bool:
        """Return True if there are states to redo."""
        return len(self._future) > 0

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset to population defaults, saving an undo snapshot."""
        self._push_history()
        self._params = BodyParameters(gender=self._params.gender)
        logger.debug("reset to defaults (gender=%r)", self._params.gender)

    # ── Lock helpers ──────────────────────────────────────────────────────────

    def lock(self, name: str) -> None:
        """Freeze *name* so future rescaling does not modify it."""
        self._params.lock(name)

    def unlock(self, name: str) -> None:
        """Release *name* from the lock."""
        self._params.unlock(name)

    # ── UI helper ─────────────────────────────────────────────────────────────

    def slider_definitions(self) -> list[dict[str, Any]]:
        """Return all slider definitions with current values.

        Useful for building UI components.

        Returns:
            List of dicts with keys: name, label, group, min, max, default,
            unit, description, current_value, locked.
        """
        return [
            {
                "name":          s.name,
                "label":         s.label,
                "group":         s.group,
                "min":           s.min_val,
                "max":           s.max_val,
                "default":       s.default,
                "unit":          s.unit,
                "description":   s.description,
                "current_value": self.get_slider(s.name),
                "locked":        self._params.is_locked(s.name),
            }
            for s in SLIDER_DEFINITIONS
        ]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _push_history(self) -> None:
        """Save a copy of the current state onto the undo stack."""
        self._history.append(self._params.copy())
        self._future.clear()   # new change invalidates redo branch
        if len(self._history) > _MAX_HISTORY:
            self._history.pop(0)
