"""Dune adapter built from the vendored spice client.

This module provides a thin façade used by the new service layer while
keeping the battle-tested logic that the original spice client offered.
"""

from . import urls  # re-export for callers needing low-level helpers
from .extract import async_query, query  # noqa: F401

__all__ = ["query", "async_query", "urls"]
