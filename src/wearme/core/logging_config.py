"""Logging configuration for the WEARME project.

Call ``setup_logging()`` once at application entry-point to configure the
root logger with a consistent format.

Usage::

    from wearme.core.logging_config import setup_logging
    setup_logging("DEBUG")
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger for WEARME.

    Sets up a StreamHandler writing to stdout with a timestamped formatter.
    Safe to call multiple times — re-calling reconfigures the root logger.

    Args:
        level: Logging level string. One of DEBUG, INFO, WARNING, ERROR,
               CRITICAL. Case-insensitive. Defaults to "INFO".

    Raises:
        ValueError: If *level* is not a recognised logging level name.
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level!r}")

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates on re-configuration
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
