from __future__ import annotations

import pytest


@pytest.fixture
def mock_server(monkeypatch, tmp_path):
    """Initialise the FastMCP server with stubbed services for integration tests."""

    from spice_mcp.core.models import TableColumn, TableDescription, TableSummary
    from spice_mcp.mcp import server

    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    # Reset global state to force a clean init
    server.CONFIG = None
    server.QUERY_HISTORY = None
    server.DUNE_ADAPTER = None
    server.QUERY_SERVICE = None
    server.DISCOVERY_SERVICE = None
    server.SUI_SERVICE = None
    server.EXECUTE_QUERY_TOOL = None
    server.SUI_OVERVIEW_TOOL = None

    server._ensure_initialized()

    class FakeQueryService:
        def execute(
            self,
            *,
            query,
            parameters=None,
            refresh=False,
            max_age=None,
            poll=True,
            timeout_seconds=None,
            limit=None,
            offset=None,
            sample_count=None,
            sort_by=None,
            columns=None,
            extras=None,
            include_execution=True,
            performance=None,
            return_raw: bool = False,
        ):
            base = {
                "rowcount": 1,
                "columns": ["_col0"],
                "data_preview": [{"_col0": 1}],
                "execution": {"execution_id": "exec-1"},
                "duration_ms": 123,
                "metadata": {"state": "ok"},
                "next_uri": None,
                "next_offset": None,
            }
            if return_raw:
                base["data"] = [{"_col0": 1}]
            return base

        def fetch_metadata(
            self,
            *,
            query,
            parameters=None,
            max_age=None,
            limit=None,
            offset=None,
            sample_count=None,
            sort_by=None,
            columns=None,
            extras=None,
            performance=None,
        ):
            return {
                "metadata": {"state": "ok"},
                "next_uri": None,
                "next_offset": None,
            }

    class FakeDiscoveryService:
        def find_schemas(self, keyword: str) -> list[str]:
            return ["sui_base"]

        def list_tables(self, schema: str, limit: int | None = None):
            return [TableSummary(schema=schema, table="events")]

        def describe_table(self, schema: str, table: str) -> TableDescription:
            return TableDescription(
                fully_qualified_name=f"{schema}.{table}",
                columns=[TableColumn(name="col1", polars_dtype="String")],
            )

    class FakeSuiService:
        def events_preview(self, packages, *, hours: int, limit: int):
            return {
                "rowcount": limit,
                "columns": ["timestamp_ms", "package"],
                "data_preview": [{"timestamp_ms": 123, "package": "0xabc"}],
            }

        def package_overview(self, packages, *, hours: int, timeout_seconds: float | None = None):
            return {
                "ok": True,
                "events_preview": [{"event": "e1"}],
                "transactions_preview": [{"tx": "t1"}],
                "objects_preview": [{"obj": "o1"}],
            }

    server.QUERY_SERVICE = FakeQueryService()
    server.EXECUTE_QUERY_TOOL.query_service = server.QUERY_SERVICE

    server.DISCOVERY_SERVICE = FakeDiscoveryService()

    server.SUI_SERVICE = FakeSuiService()
    server.SUI_OVERVIEW_TOOL.sui_service = server.SUI_SERVICE

    yield server
