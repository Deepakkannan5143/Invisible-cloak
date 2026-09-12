"""Privacy-aware logging helpers.

Raw sensitive values must never reach logs. Debug logging is opt-in via the
``CLOAK_DEBUG`` environment variable (default off); even then, any value passed
through :func:`mask_for_log` is redacted to a shape-preserving placeholder.
"""

from __future__ import annotations

import logging
import os

DEBUG = os.getenv("CLOAK_DEBUG", "false").strip().lower() in ("1", "true", "yes", "on")

logger = logging.getLogger("cloak")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[cloak] %(levelname)s %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)


def mask_for_log(value: str, keep: int = 2) -> str:
    """Redact a value for logging: keep the first/last ``keep`` chars only.

    Never returns the full value. Used so even debug logs cannot leak PII.
    """
    if value is None:
        return "<none>"
    s = str(value)
    if len(s) <= keep * 2:
        return "•" * len(s)
    return f"{s[:keep]}{'•' * (len(s) - keep * 2)}{s[-keep:]}"


def debug(msg: str, *args: object) -> None:
    """Log at DEBUG only when CLOAK_DEBUG is enabled."""
    if DEBUG:
        logger.debug(msg, *args)


def info(msg: str, *args: object) -> None:
    logger.info(msg, *args)
