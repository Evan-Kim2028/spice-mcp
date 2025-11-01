from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QueryRequest:
    """Normalized representation of a Dune query request."""

    query: int | str
    parameters: Mapping[str, Any] | None = None
    refresh: bool = False
    max_age: float | None = None
    poll: bool = True
    timeout_seconds: float | None = None
    limit: int | None = None
    offset: int | None = None
    sample_count: int | None = None
    sort_by: str | None = None
    columns: Sequence[str] | None = None
    extras: Mapping[str, Any] | None = None
    performance: str | None = None
    include_execution: bool = True


@dataclass(slots=True)
class ResultPreview:
    rowcount: int
    columns: list[str]
    data_preview: list[dict[str, Any]]


@dataclass(slots=True)
class ResultMetadata:
    """Subset of Dune execution metadata surfaced to MCP clients."""

    execution: dict[str, Any]
    duration_ms: int
    metadata: dict[str, Any] | None = None
    next_offset: int | None = None
    next_uri: str | None = None


@dataclass(slots=True)
class QueryResult:
    """Normalized result returned by QueryExecutor implementations."""

    preview: ResultPreview
    info: ResultMetadata
    lazyframe: Any | None = None


@dataclass(slots=True)
class SchemaMatch:
    schema: str


@dataclass(slots=True)
class TableSummary:
    schema: str
    table: str


@dataclass(slots=True)
class TableColumn:
    name: str
    dune_type: str | None = None
    polars_dtype: str | None = None
    comment: str | None = None
    extra: str | None = None


@dataclass(slots=True)
class TableDescription:
    fully_qualified_name: str
    columns: list[TableColumn] = field(default_factory=list)


@dataclass(slots=True)
class SuiPackageOverview:
    package_ids: list[str]
    window_hours: int
    events_preview: list[dict[str, Any]] | None = None
    transactions_preview: list[dict[str, Any]] | None = None
    objects_preview: list[dict[str, Any]] | None = None
    stats: dict[str, Any] = field(default_factory=dict)
