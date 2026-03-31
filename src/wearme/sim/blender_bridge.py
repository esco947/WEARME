"""Blender Python API bridge for SMPL mesh operations.

This module is designed to run **inside Blender's embedded Python interpreter**
(invoked via ``blender --background --python <script.py>``).  It uses the
``bpy`` module which is only available in that context.

Typical usage in a Blender headless script::

    import sys
    sys.path.insert(0, "/path/to/wearme/src")   # inject wearme package

    from wearme.sim.blender_bridge import (
        clear_body_objects,
        import_body_from_glb,
        load_body_mesh,
        export_scene_glb,
        export_scene_obj,
    )

    clear_body_objects()
    import_body_from_glb("/tmp/body.glb")
    export_scene_glb("/tmp/body_rigged.glb")

Outside Blender (e.g. unit tests), importing this module is safe but
calling any public function raises :class:`RuntimeError`.

See also ``blender --background --python`` in the Blender docs for headless
scripting.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# bpy is only available inside Blender's Python interpreter.
# We guard the import so the module can be loaded in regular Python
# for documentation, type-checking, and test discovery purposes.
try:
    import bpy  # type: ignore[import-not-found]

    _BPY_AVAILABLE = True
except ModuleNotFoundError:
    _BPY_AVAILABLE = False

#: Prefix applied to every Blender object managed by WEARME so they can be
#: found and cleaned up without touching user-created geometry.
WEARME_PREFIX = "WEARME_"


def _require_bpy() -> None:
    """Raise :class:`RuntimeError` if called outside a Blender Python context."""
    if not _BPY_AVAILABLE:
        raise RuntimeError(
            "wearme.sim.blender_bridge requires a Blender Python context "
            "(bpy is not available in this environment).  "
            "Run your script via: blender --background --python <script.py>"
        )


# ── Scene management ────────────────────────────────────────────────────────────


def clear_body_objects() -> int:
    """Remove all WEARME-managed mesh objects from the active Blender scene.

    Identifies objects whose name starts with :data:`WEARME_PREFIX` and
    deletes them together with their mesh data blocks.

    Returns:
        Number of objects removed.
    """
    _require_bpy()

    targets = [
        obj
        for obj in bpy.data.objects
        if obj.name.startswith(WEARME_PREFIX) and obj.type == "MESH"
    ]
    for obj in targets:
        bpy.data.objects.remove(obj, do_unlink=True)

    logger.info("Removed %d WEARME object(s) from scene", len(targets))
    return len(targets)


# ── Mesh import ─────────────────────────────────────────────────────────────────


def import_body_from_glb(glb_path: Path | str) -> list[str]:
    """Import a GLB file into the active Blender scene.

    Uses Blender's built-in glTF importer.  All imported mesh objects are
    renamed with the :data:`WEARME_PREFIX` so they can be tracked later.

    Args:
        glb_path: Path to the ``.glb`` file to import.

    Returns:
        List of names assigned to the imported objects.

    Raises:
        FileNotFoundError: If *glb_path* does not exist.
        RuntimeError: If called outside Blender.
    """
    _require_bpy()

    glb_path = Path(glb_path)
    if not glb_path.is_file():
        raise FileNotFoundError(f"GLB file not found: {glb_path}")

    before: set = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    new_objects = [obj for obj in bpy.data.objects if obj not in before]

    imported_names: list[str] = []
    mesh_objects = [obj for obj in new_objects if obj.type == "MESH"]
    for i, obj in enumerate(mesh_objects):
        new_name = (
            f"{WEARME_PREFIX}Body"
            if len(mesh_objects) == 1
            else f"{WEARME_PREFIX}Body_{i}"
        )
        obj.name = new_name
        imported_names.append(new_name)

    logger.info("Imported %d object(s) from %s", len(imported_names), glb_path)
    return imported_names


def load_body_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    name: str = "WEARME_Body",
) -> str:
    """Create a Blender mesh object directly from numpy arrays.

    Avoids writing a temporary file by building the Blender mesh data
    in memory via the ``bpy.data.meshes`` API.

    Any existing object with the same *name* is removed first.

    Args:
        vertices: Vertex coordinates. Shape ``(N, 3)``, in metres.
        faces: Triangle indices. Shape ``(F, 3)``, 0-based.
        name: Name for both the Blender object and its mesh data block.

    Returns:
        Name of the created Blender object.

    Raises:
        RuntimeError: If called outside Blender.
    """
    _require_bpy()

    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()

    logger.info(
        "Created Blender mesh %r (%d verts, %d faces)",
        name,
        len(vertices),
        len(faces),
    )
    return name


# ── Export ──────────────────────────────────────────────────────────────────────


def export_scene_glb(output_path: Path | str) -> Path:
    """Export the active Blender scene (or WEARME objects only) to a GLB file.

    When WEARME-prefixed objects exist, only those are exported.  Otherwise
    all objects in the scene are exported.

    Args:
        output_path: Destination path for the ``.glb`` file.  Parent
            directories are created automatically.

    Returns:
        Resolved path of the written file.

    Raises:
        RuntimeError: If called outside Blender.
    """
    _require_bpy()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    wearme_objects = [
        obj
        for obj in bpy.data.objects
        if obj.name.startswith(WEARME_PREFIX) and obj.type == "MESH"
    ]

    bpy.ops.object.select_all(action="DESELECT")
    if wearme_objects:
        for obj in wearme_objects:
            obj.select_set(True)
        use_selection = True
    else:
        use_selection = False

    bpy.ops.export_scene.gltf(
        filepath=str(out),
        export_format="GLB",
        use_selection=use_selection,
    )

    logger.info("Scene exported to GLB: %s", out)
    return out


def export_scene_obj(output_path: Path | str) -> Path:
    """Export the active Blender scene (or WEARME objects only) to an OBJ file.

    When WEARME-prefixed objects exist, only those are exported.  Otherwise
    all objects in the scene are exported.

    Args:
        output_path: Destination path for the ``.obj`` file.  Parent
            directories are created automatically.

    Returns:
        Resolved path of the written file.

    Raises:
        RuntimeError: If called outside Blender.
    """
    _require_bpy()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    wearme_objects = [
        obj
        for obj in bpy.data.objects
        if obj.name.startswith(WEARME_PREFIX) and obj.type == "MESH"
    ]

    bpy.ops.object.select_all(action="DESELECT")
    if wearme_objects:
        for obj in wearme_objects:
            obj.select_set(True)
        use_selection = True
    else:
        use_selection = False

    bpy.ops.wm.obj_export(
        filepath=str(out),
        export_selected_objects=use_selection,
    )

    logger.info("Scene exported to OBJ: %s", out)
    return out
