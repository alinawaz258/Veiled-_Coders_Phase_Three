"""Utility helpers used across the AI microservice."""

from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Create and return a module-level logger with a standard format."""

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a value to the provided [low, high] range."""

    return max(low, min(value, high))


def safe_ratio(value: float, max_value: float) -> float:
    """Normalize values into [0, 1] while safely handling bad inputs."""

    if max_value <= 0:
        return 0.0
    return clamp(value / max_value, 0.0, 1.0)


def ensure_directory(path: Path) -> None:
    """Create the directory if it does not already exist."""

    path.mkdir(parents=True, exist_ok=True)
