"""Global constants for the WEARME project.

Business-logic constants (body limits, garment constraints, etc.) live here
so that they are never scattered as magic numbers across the codebase.
"""

APP_NAME: str = "WEARME"
VERSION: str = "0.1.0"

# ── Body ─────────────────────────────────────────────────────────────────────

#: Minimum standing height (metres)
BODY_HEIGHT_MIN_M: float = 1.40
#: Maximum standing height (metres)
BODY_HEIGHT_MAX_M: float = 2.20
#: Default standing height (metres)
BODY_HEIGHT_DEFAULT_M: float = 1.75

#: Minimum body weight (kg)
BODY_WEIGHT_MIN_KG: float = 40.0
#: Maximum body weight (kg)
BODY_WEIGHT_MAX_KG: float = 200.0
#: Default body weight (kg)
BODY_WEIGHT_DEFAULT_KG: float = 70.0

#: Number of SMPL shape coefficients used (β vector length)
SMPL_SHAPE_DIMS: int = 10

# ── Garment ───────────────────────────────────────────────────────────────────

#: Minimum seam allowance (metres)
SEAM_ALLOWANCE_MIN_M: float = 0.005
#: Default seam allowance (metres)
SEAM_ALLOWANCE_DEFAULT_M: float = 0.015

# ── File formats ─────────────────────────────────────────────────────────────

SUPPORTED_EXPORT_FORMATS: tuple[str, ...] = ("glb", "obj")
