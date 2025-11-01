from __future__ import annotations

import logging
import os


def configure_logging(level: str | None = None) -> None:
    """Best-effort logging configuration for the MCP server and adapters."""
    level_name = level or os.getenv("SPICE_LOG_LEVEL", "WARNING")
    try:
        log_level = getattr(logging, level_name.upper(), logging.WARNING)
    except Exception:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
