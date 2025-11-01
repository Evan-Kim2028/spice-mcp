from __future__ import annotations

import polars as pl

from spice_mcp.core.models import (
    QueryRequest,
    QueryResult,
    ResultMetadata,
    ResultPreview,
)
from spice_mcp.service_layer.query_service import QueryService


class StubExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, request: QueryRequest) -> QueryResult:
        self.calls.append(request)
        df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        lf = df.lazy()
        preview = ResultPreview(
            rowcount=3,
            columns=list(df.columns),
            data_preview=lf.limit(10).collect().to_dicts(),
        )
        meta = ResultMetadata(execution={"execution_id": "e-1"}, duration_ms=12, metadata={"state": "completed"})
        return QueryResult(preview=preview, info=meta, lazyframe=lf)

    def fetch_metadata(self, request: QueryRequest, *, execution=None) -> ResultMetadata:
        return ResultMetadata(execution=execution or {}, duration_ms=0, metadata={"state": "completed"})


def test_query_service_shapes_output():
    executor = StubExecutor()
    svc = QueryService(executor)

    out = svc.execute(query="SELECT 1", limit=2, include_execution=True)

    assert set(["rowcount", "columns", "data_preview", "execution", "duration_ms"]).issubset(out)
    assert out["rowcount"] == 3
    assert out["columns"] == ["a", "b"]
    assert isinstance(out["data_preview"], list)
    assert len(out["data_preview"]) == 3
    assert out["execution"]["execution_id"] == "e-1"
    assert out.get("metadata") == {"state": "completed"}


def test_query_service_return_raw_data():
    executor = StubExecutor()
    svc = QueryService(executor)

    out = svc.execute(query="SELECT 1", return_raw=True)

    assert out["data"] == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3, "b": "z"}]
