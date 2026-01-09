"""Logging configuration for Megaplan SDK."""

from __future__ import annotations

import logging
from typing import Any

# Create logger for the SDK
logger = logging.getLogger("megaplan_sdk")
logger.setLevel(logging.WARNING)

# Create formatter
formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def setup_logging(level: str = "WARNING") -> None:
    """Setup logging for SDK.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logger.setLevel(getattr(logging, level.upper()))


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive data from dict for logging.

    Args:
        data: Dictionary to sanitize.

    Returns:
        Sanitized dictionary with sensitive values redacted.
    """
    sensitive_keys = {
        "password",
        "access_token",
        "refresh_token",
        "Authorization",
        "token",
        "secret",
        "api_key",
        "apiKey",
    }

    return {k: "***REDACTED***" if k in sensitive_keys else v for k, v in data.items()}
