"""GLB/glTF binary export for SMPL body meshes.

Provides standalone functions to export raw vertex/face arrays to GLB,
as well as higher-level helpers that accept :class:`~wearme.body.body_params.BodyParameters`
directly.

Requires ``trimesh`` (already a project dependency).

Usage::

    from wearme.io.glb_export import body_to_glb, body_to_glb_bytes
    from wearme.body.smpl_bridge import load_model_data
    from wearme.body.body_params import BodyParameters

    model = load_model_data("neutral")
    params = BodyParameters(height_m=1.80)
    path = body_to_glb(params, model, "output/body.glb")
    raw  = body_to_glb_bytes(params, model)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# ── Internal helpers ────────────────────────────────────────────────────────────


def _scale_to_height(
    vertices: np.ndarray,
    height_m: float | None,
) -> np.ndarray:
    """Uniformly scale *vertices* so the Y-axis span equals *height_m*.

    SMPL uses Y-up convention.  The scaling is a no-op when *height_m* is
    ``None`` or the mesh has zero extent.

    Args:
        vertices: Vertex array. Shape ``(N, 3)``.
        height_m: Target height in metres.  Pass ``None`` to skip scaling.

    Returns:
        Scaled vertex array (copy).
    """
    if height_m is None or height_m <= 0:
        return vertices.copy()

    y_min = float(vertices[:, 1].min())
    y_max = float(vertices[:, 1].max())
    mesh_height = y_max - y_min
    if mesh_height <= 0:
        return vertices.copy()

    scale = height_m / mesh_height
    logger.debug("Scaling mesh to height_m=%.3f (factor %.4f)", height_m, scale)
    return vertices * scale


# ── Low-level export (raw arrays) ──────────────────────────────────────────────


def export_glb(
    vertices: np.ndarray,
    faces: np.ndarray,
    path: Path | str,
    *,
    height_m: float | None = None,
) -> Path:
    """Export raw vertex/face arrays to a GLB file.

    Args:
        vertices: Vertex coordinates. Shape ``(N, 3)``, in metres.
        faces: Triangle face indices. Shape ``(F, 3)``.
        path: Destination file path.  Parent directories are created
            automatically.
        height_m: If provided, the mesh is uniformly scaled so its
            Y-axis span equals *height_m* before export.

    Returns:
        Resolved path of the written file.
    """
    import trimesh  # noqa: PLC0415

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    verts = _scale_to_height(vertices, height_m)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    glb_bytes = bytes(mesh.export(file_type="glb"))
    out.write_bytes(glb_bytes)
    logger.info("GLB written to %s (%d bytes)", out, len(glb_bytes))
    return out


def export_glb_bytes(
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    height_m: float | None = None,
) -> bytes:
    """Export raw vertex/face arrays to GLB bytes (no file written).

    Args:
        vertices: Vertex coordinates. Shape ``(N, 3)``, in metres.
        faces: Triangle face indices. Shape ``(F, 3)``.
        height_m: Optional height rescaling (see :func:`export_glb`).

    Returns:
        Raw GLB binary content.
    """
    import trimesh  # noqa: PLC0415

    verts = _scale_to_height(vertices, height_m)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    glb_bytes = bytes(mesh.export(file_type="glb"))
    logger.debug("GLB bytes generated: %d bytes", len(glb_bytes))
    return glb_bytes


# ── High-level export (BodyParameters) ─────────────────────────────────────────


def body_to_glb(
    params: object,
    model_data: object,
    path: Path | str,
    *,
    height_m: float | None = None,
) -> Path:
    """Generate and export a GLB from a :class:`~wearme.body.body_params.BodyParameters` instance.

    Runs the SMPL forward pass, rescales to *height_m* (or ``params.height_m``
    when not specified), and writes a GLB file.

    Args:
        params: Body shape and pose parameters
            (:class:`~wearme.body.body_params.BodyParameters`).
        model_data: Loaded SMPL model data
            (:class:`~wearme.body.smpl_bridge.SMPLModelData`).
        path: Destination GLB file path.
        height_m: Override target height in metres.
            Defaults to ``params.height_m``.

    Returns:
        Resolved path of the written GLB file.
    """
    from wearme.body.smpl_bridge import generate_vertices  # noqa: PLC0415

    vertices = generate_vertices(params, model_data)  # type: ignore[arg-type]
    target_height = height_m if height_m is not None else params.height_m  # type: ignore[attr-defined]
    return export_glb(vertices, model_data.faces, path, height_m=target_height)  # type: ignore[attr-defined]


def body_to_glb_bytes(
    params: object,
    model_data: object,
    *,
    height_m: float | None = None,
) -> bytes:
    """Generate GLB bytes from a :class:`~wearme.body.body_params.BodyParameters` instance.

    No file is written.

    Args:
        params: Body shape and pose parameters.
        model_data: Loaded SMPL model data.
        height_m: Override target height in metres.
            Defaults to ``params.height_m``.

    Returns:
        Raw GLB binary content.
    """
    from wearme.body.smpl_bridge import generate_vertices  # noqa: PLC0415

    vertices = generate_vertices(params, model_data)  # type: ignore[arg-type]
    target_height = height_m if height_m is not None else params.height_m  # type: ignore[attr-defined]
    return export_glb_bytes(vertices, model_data.faces, height_m=target_height)  # type: ignore[attr-defined]
