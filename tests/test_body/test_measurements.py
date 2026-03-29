"""Tests for wearme.body.measurements.

These tests do NOT load SMPL .pkl files. They use a synthetic cylindrical
mesh to verify the measurement logic (cross-section detection, circumference
calculation) without external model dependencies.
"""

from __future__ import annotations

import numpy as np
import pytest
import trimesh

from wearme.body.measurements import _circumference_at_height, _section_length

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_cylinder(radius: float = 0.1, height: float = 1.0, sections: int = 64) -> trimesh.Trimesh:
    """Return a unit-radius vertical cylinder centred at y=height/2.

    The cylinder's axis is the Y axis (SMPL vertical convention).
    Bottom cap at y=0, top cap at y=height.

    Args:
        radius: Cylinder radius in metres.
        height: Cylinder height in metres.
        sections: Number of circumference subdivisions.

    Returns:
        Trimesh cylinder.
    """
    cyl = trimesh.creation.cylinder(
        radius=radius,
        height=height,
        sections=sections,
    )
    # trimesh.creation.cylinder creates cylinder along Z axis, centred at origin.
    # Rotate so axis is Y and bottom is at y=0.
    rotation = trimesh.transformations.rotation_matrix(
        np.pi / 2, [1, 0, 0]
    )
    cyl.apply_transform(rotation)
    # Translate so bottom is at y=0
    cyl.apply_translation([0, height / 2, 0])
    return cyl


# ── _section_length ────────────────────────────────────────────────────────────


def test_section_length_cylinder_midpoint() -> None:
    """Cross-section of a cylinder at mid-height equals 2π·r."""
    radius = 0.1
    cyl = _make_cylinder(radius=radius, height=1.0)
    expected = 2 * np.pi * radius

    measured = _section_length(cyl, y=0.5)
    # Allow 2% tolerance (discretisation error from finite sections)
    assert measured == pytest.approx(expected, rel=0.02)


def test_section_length_different_radii() -> None:
    """Larger radius gives proportionally larger cross-section length."""
    r1, r2 = 0.1, 0.2
    cyl1 = _make_cylinder(radius=r1, height=1.0)
    cyl2 = _make_cylinder(radius=r2, height=1.0)

    l1 = _section_length(cyl1, y=0.5)
    l2 = _section_length(cyl2, y=0.5)

    # Ratio should be approximately r2/r1 = 2
    assert l2 / l1 == pytest.approx(r2 / r1, rel=0.02)


def test_section_length_returns_zero_outside_mesh() -> None:
    """Section at a height outside the mesh returns 0.0."""
    cyl = _make_cylinder(height=1.0)
    assert _section_length(cyl, y=2.0) == pytest.approx(0.0)
    assert _section_length(cyl, y=-0.5) == pytest.approx(0.0)


# ── _circumference_at_height ─────────────────────────────────────────────────


def test_circumference_at_height_returns_float() -> None:
    """_circumference_at_height returns a float >= 0."""
    cyl = _make_cylinder(radius=0.1, height=1.0)
    vertices = np.array(cyl.vertices)
    result = _circumference_at_height(vertices, y=0.5)
    assert isinstance(result, float)
    assert result >= 0.0


def test_circumference_at_height_zero_when_no_points() -> None:
    """Returns 0.0 when no vertices fall in the slice."""
    cyl = _make_cylinder(height=1.0)
    vertices = np.array(cyl.vertices)
    assert _circumference_at_height(vertices, y=5.0) == pytest.approx(0.0)


def _ring_vertices(radius: float, y: float = 0.5, n: int = 64) -> np.ndarray:
    """Generate a ring of 3D vertices at height *y* with given *radius*."""
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    xs = radius * np.cos(angles)
    zs = radius * np.sin(angles)
    ys = np.full(n, y)
    return np.column_stack([xs, ys, zs])


def test_circumference_at_height_scales_with_radius() -> None:
    """Larger radius gives a larger circumference estimate from vertex ring."""
    r1, r2 = 0.1, 0.2
    v1 = _ring_vertices(r1, y=0.5)
    v2 = _ring_vertices(r2, y=0.5)

    # Use loose tolerance to capture all ring vertices
    c1 = _circumference_at_height(v1, y=0.5, tolerance=0.05)
    c2 = _circumference_at_height(v2, y=0.5, tolerance=0.05)

    assert c2 > c1


# ── Integration: consistent measurements ─────────────────────────────────────


def test_measurements_chest_greater_than_waist() -> None:
    """For the default neutral body, chest circumference > waist circumference.

    This test uses SMPL model data; skip if model files are not available.
    """
    pytest.importorskip("scipy")
    try:
        from wearme.body.body_params import BodyParameters
        from wearme.body.measurements import compute_measurements

        m = compute_measurements(BodyParameters())
        # Chest should be greater than waist for a neutral shape
        assert m["chest_m"] > m["waist_m"], (
            f"Expected chest > waist, got chest={m['chest_m']:.3f}, waist={m['waist_m']:.3f}"
        )
        # Height should be positive and plausible
        assert 1.4 <= m["height_m"] <= 2.2
    except FileNotFoundError:
        pytest.skip("SMPL model files not available.")
