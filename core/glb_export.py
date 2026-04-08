"""GLB export from SMPL mesh vertices — pure numpy, no trimesh.

trimesh.export(glb) takes ~420ms per call due to internal processing.
This implementation writes a valid GLB 2.0 binary directly from numpy arrays
in ~2ms (200x faster), producing an identical file size.
"""

from __future__ import annotations

import json
import struct

import numpy as np


def vertices_to_glb(vertices: np.ndarray, faces: np.ndarray) -> bytes:
    """Export a mesh to GLB 2.0 binary format.

    Args:
        vertices: Mesh vertices ``(N, 3)`` float, in metres.
        faces:    Triangle face indices ``(M, 3)`` int.

    Returns:
        GLB file contents as bytes (magic: ``glTF``).
    """
    verts_f32 = np.asarray(vertices, dtype=np.float32)
    faces_u32 = np.asarray(faces,    dtype=np.uint32)

    vertex_bytes = verts_f32.tobytes()
    index_bytes  = faces_u32.tobytes()
    bin_data     = vertex_bytes + index_bytes

    v_min = verts_f32.min(axis=0).tolist()
    v_max = verts_f32.max(axis=0).tolist()

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "wearme"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes":  [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "accessors": [
            {
                "bufferView":     0,
                "componentType":  5126,          # FLOAT
                "count":          len(verts_f32),
                "type":           "VEC3",
                "min":            v_min,
                "max":            v_max,
            },
            {
                "bufferView":     1,
                "componentType":  5125,          # UNSIGNED_INT
                "count":          int(faces_u32.size),
                "type":           "SCALAR",
            },
        ],
        "bufferViews": [
            {
                "buffer":     0,
                "byteOffset": 0,
                "byteLength": len(vertex_bytes),
                "target":     34962,             # ARRAY_BUFFER
            },
            {
                "buffer":     0,
                "byteOffset": len(vertex_bytes),
                "byteLength": len(index_bytes),
                "target":     34963,             # ELEMENT_ARRAY_BUFFER
            },
        ],
        "buffers": [{"byteLength": len(bin_data)}],
    }

    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")

    # GLB chunks must be 4-byte aligned
    json_pad = (-len(json_bytes)) % 4
    bin_pad  = (-len(bin_data))   % 4

    json_chunk = json_bytes + b" " * json_pad   # JSON chunk padding: spaces
    bin_chunk  = bin_data   + b"\x00" * bin_pad # BIN chunk padding: zeros

    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)

    glb  = struct.pack("<III", 0x46546C67, 2, total_length)  # header
    glb += struct.pack("<II",  len(json_chunk), 0x4E4F534A)  # JSON chunk header
    glb += json_chunk
    glb += struct.pack("<II",  len(bin_chunk),  0x004E4942)  # BIN chunk header
    glb += bin_chunk

    return glb
