"""WEARME Body Loader — Blender 4.x Addon.

Minimal addon that lets you:

- Load a body mesh from a WEARME-generated GLB file
- Export the current WEARME body mesh to GLB or OBJ

Installation
------------
1. Zip the ``blender_addon/`` directory.
2. In Blender: Edit → Preferences → Add-ons → Install → select the zip.
3. Enable **"3D View: WEARME Body Loader"**.

The addon injects the ``wearme`` package into Blender's ``sys.path`` on
registration so that :mod:`wearme.sim.blender_bridge` is importable without
needing to install ``wearme`` into Blender's bundled Python.
"""

from __future__ import annotations

import sys
from pathlib import Path

bl_info = {
    "name": "WEARME Body Loader",
    "author": "Axel SAMVELYAN",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > WEARME",
    "description": "Load and export SMPL body meshes via the WEARME pipeline",
    "doc_url": "",
    "category": "3D View",
}

# ── sys.path injection ──────────────────────────────────────────────────────────
# Blender bundles its own Python interpreter.  External packages must be
# injected by inserting the wearme src/ directory into sys.path.
# Expected layout:
#   <project_root>/
#       blender_addon/   ← this file
#       src/wearme/      ← the package to inject

_ADDON_DIR: Path = Path(__file__).resolve().parent
_PROJECT_ROOT: Path = _ADDON_DIR.parent
_SRC_DIR: Path = _PROJECT_ROOT / "src"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ── Deferred panel import (requires bpy at registration time) ──────────────────
# We import panels lazily inside register()/unregister() so that the module
# can be parsed for bl_info without needing bpy to be fully initialised.


def register() -> None:
    """Register all WEARME addon classes with Blender."""
    import bpy  # type: ignore[import-not-found]  # noqa: PLC0415

    from blender_addon.panels.main_panel import (  # noqa: PLC0415
        WEARME_OT_ClearBody,
        WEARME_OT_ExportGLB,
        WEARME_OT_ExportOBJ,
        WEARME_OT_LoadGLB,
        WEARME_PT_MainPanel,
    )

    for cls in (
        WEARME_PT_MainPanel,
        WEARME_OT_LoadGLB,
        WEARME_OT_ClearBody,
        WEARME_OT_ExportGLB,
        WEARME_OT_ExportOBJ,
    ):
        bpy.utils.register_class(cls)


def unregister() -> None:
    """Unregister all WEARME addon classes from Blender."""
    import bpy  # type: ignore[import-not-found]  # noqa: PLC0415

    from blender_addon.panels.main_panel import (  # noqa: PLC0415
        WEARME_OT_ClearBody,
        WEARME_OT_ExportGLB,
        WEARME_OT_ExportOBJ,
        WEARME_OT_LoadGLB,
        WEARME_PT_MainPanel,
    )

    for cls in reversed(
        (
            WEARME_PT_MainPanel,
            WEARME_OT_LoadGLB,
            WEARME_OT_ClearBody,
            WEARME_OT_ExportGLB,
            WEARME_OT_ExportOBJ,
        )
    ):
        bpy.utils.unregister_class(cls)
