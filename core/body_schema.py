"""Slider definitions for the avatar manual editor.

``SLIDERS`` is the authoritative list of user-adjustable body measurements.
It mirrors the keys returned by ``core.mesh_measurements.measure_mesh()``.

Defaults are based on ANSUR II 50th-percentile values (male/female).
All ``min_val`` / ``max_val`` / ``default_*`` values are in **cm** for the
UI, but the API exchanges them in **metres** (divide by 100).

Usage::

    from core.body_schema import SLIDERS
    for s in SLIDERS:
        print(s.key, s.default_male, s.unit)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SliderDef:
    """Definition of one body measurement slider."""

    key:            str    # measurement key, matches measure_mesh() output
    label:          str    # human-readable French label
    unit:           str    # "cm" (display) or "m" (API)
    min_val:        float  # minimum value in cm
    max_val:        float  # maximum value in cm
    default_male:   float  # ANSUR II 50th pct male (cm)
    default_female: float  # ANSUR II 50th pct female (cm)
    step:           float  # slider increment (cm)


SLIDERS: list[SliderDef] = [
    SliderDef(
        key="height",
        label="Taille",
        unit="cm",
        min_val=150.0,
        max_val=210.0,
        default_male=175.5,
        default_female=162.0,
        step=0.5,
    ),
    SliderDef(
        key="chest_circumference",
        label="Tour de poitrine",
        unit="cm",
        min_val=75.0,
        max_val=135.0,
        default_male=99.0,
        default_female=91.0,
        step=0.5,
    ),
    SliderDef(
        key="waist_circumference",
        label="Tour de taille",
        unit="cm",
        min_val=60.0,
        max_val=120.0,
        default_male=84.0,
        default_female=73.0,
        step=0.5,
    ),
    SliderDef(
        key="hip_circumference",
        label="Tour de hanches",
        unit="cm",
        min_val=80.0,
        max_val=130.0,
        default_male=97.0,
        default_female=99.0,
        step=0.5,
    ),
    SliderDef(
        key="shoulder_width",
        label="Largeur épaules",
        unit="cm",
        min_val=35.0,
        max_val=55.0,
        default_male=45.0,
        default_female=40.0,
        step=0.5,
    ),
    SliderDef(
        key="inseam",
        label="Entrejambe",
        unit="cm",
        min_val=65.0,
        max_val=95.0,
        default_male=81.0,
        default_female=75.0,
        step=0.5,
    ),
]

# Convenience set of valid slider keys
SLIDER_KEYS: frozenset[str] = frozenset(s.key for s in SLIDERS)
