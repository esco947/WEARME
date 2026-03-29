"""Unit conversion utilities.

All internal computations use SI units (metres, kilograms).
These helpers convert to/from common display units.

Usage::

    from wearme.core.units import cm_to_m, m_to_cm
"""


def cm_to_m(value: float) -> float:
    """Convert centimetres to metres.

    Args:
        value: Length in centimetres.

    Returns:
        Length in metres.
    """
    return value / 100.0


def m_to_cm(value: float) -> float:
    """Convert metres to centimetres.

    Args:
        value: Length in metres.

    Returns:
        Length in centimetres.
    """
    return value * 100.0


def mm_to_m(value: float) -> float:
    """Convert millimetres to metres.

    Args:
        value: Length in millimetres.

    Returns:
        Length in metres.
    """
    return value / 1000.0


def m_to_mm(value: float) -> float:
    """Convert metres to millimetres.

    Args:
        value: Length in metres.

    Returns:
        Length in millimetres.
    """
    return value * 1000.0


def inches_to_m(value: float) -> float:
    """Convert inches to metres.

    Args:
        value: Length in inches.

    Returns:
        Length in metres.
    """
    return value * 0.0254


def m_to_inches(value: float) -> float:
    """Convert metres to inches.

    Args:
        value: Length in metres.

    Returns:
        Length in inches.
    """
    return value / 0.0254
