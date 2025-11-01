"""Dune adapter built from the vendored spice client.

This module provides a thin façade used by the new service layer while
keeping the battle-tested logic that the original spice client offered.

Only synchronous interfaces are exposed.
"""

from . import urls  # re-export for callers needing low-level helpers
from .extract import query  # noqa: F401

__all__ = ["query", "urls"]
