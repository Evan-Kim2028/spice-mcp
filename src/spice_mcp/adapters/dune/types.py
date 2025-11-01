from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, NotRequired, TypedDict

import polars as pl

Query = int | str

Performance = Literal['medium', 'large']


class Execution(TypedDict):
    execution_id: str
    timestamp: NotRequired[int | None]


class ExecuteKwargs(TypedDict):
    query_id: int | None
    api_key: str | None
    parameters: Mapping[str, Any] | None
    performance: Performance


class PollKwargs(TypedDict):
    api_key: str | None
    poll_interval: float
    verbose: bool
    timeout_seconds: float | None


class RetrievalKwargs(TypedDict):
    limit: int | None
    offset: int | None
    sample_count: int | None
    sort_by: str | None
    columns: Sequence[str] | None
    extras: Mapping[str, Any] | None
    types: Sequence[type[pl.DataType]] | Mapping[str, type[pl.DataType]] | None
    all_types: (
        Sequence[type[pl.DataType]] | Mapping[str, type[pl.DataType]] | None
    )
    verbose: bool


class OutputKwargs(TypedDict):
    execute_kwargs: ExecuteKwargs
    result_kwargs: RetrievalKwargs
    cache: bool
    save_to_cache: bool
    cache_dir: str | None
    include_execution: bool
