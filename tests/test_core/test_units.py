"""Tests for wearme.core.units."""

import pytest

from wearme.core.units import (
    cm_to_m,
    inches_to_m,
    m_to_cm,
    m_to_inches,
    m_to_mm,
    mm_to_m,
)

# ── cm ↔ m ───────────────────────────────────────────────────────────────────


def test_cm_to_m_basic() -> None:
    assert cm_to_m(100.0) == pytest.approx(1.0)


def test_m_to_cm_basic() -> None:
    assert m_to_cm(1.0) == pytest.approx(100.0)


def test_cm_to_m_round_trip() -> None:
    original = 175.0
    assert m_to_cm(cm_to_m(original)) == pytest.approx(original)


def test_cm_to_m_zero() -> None:
    assert cm_to_m(0.0) == pytest.approx(0.0)


def test_m_to_cm_zero() -> None:
    assert m_to_cm(0.0) == pytest.approx(0.0)


def test_cm_to_m_negative() -> None:
    assert cm_to_m(-50.0) == pytest.approx(-0.5)


# ── mm ↔ m ───────────────────────────────────────────────────────────────────


def test_mm_to_m_basic() -> None:
    assert mm_to_m(1000.0) == pytest.approx(1.0)


def test_m_to_mm_basic() -> None:
    assert m_to_mm(1.0) == pytest.approx(1000.0)


def test_mm_to_m_round_trip() -> None:
    original = 15.0
    assert m_to_mm(mm_to_m(original)) == pytest.approx(original)


def test_mm_to_m_zero() -> None:
    assert mm_to_m(0.0) == pytest.approx(0.0)


# ── inches ↔ m ───────────────────────────────────────────────────────────────


def test_inches_to_m_one_inch() -> None:
    assert inches_to_m(1.0) == pytest.approx(0.0254)


def test_m_to_inches_basic() -> None:
    assert m_to_inches(0.0254) == pytest.approx(1.0)


def test_inches_to_m_round_trip() -> None:
    original = 72.0  # 6 feet
    assert m_to_inches(inches_to_m(original)) == pytest.approx(original)


# ── cross-unit consistency ────────────────────────────────────────────────────


def test_1m_equals_100cm() -> None:
    assert m_to_cm(1.0) == pytest.approx(100.0)
    assert cm_to_m(100.0) == pytest.approx(1.0)


def test_1m_equals_1000mm() -> None:
    assert m_to_mm(1.0) == pytest.approx(1000.0)
    assert mm_to_m(1000.0) == pytest.approx(1.0)


def test_10cm_equals_100mm() -> None:
    metres = cm_to_m(10.0)
    assert m_to_mm(metres) == pytest.approx(100.0)
