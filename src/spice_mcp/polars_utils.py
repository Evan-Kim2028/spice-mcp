from __future__ import annotations

import polars as pl


def collect_preview(lf: pl.LazyFrame, limit: int) -> list[dict[str, object]]:
    """Collect a small preview from a lazy frame."""
    if limit <= 0:
        return []
    return lf.limit(limit).collect().to_dicts()


def collect_all(lf: pl.LazyFrame) -> list[dict[str, object]]:
    """Materialize the full lazy frame to a list of dictionaries."""
    return lf.collect().to_dicts()
