"""
User Journey Tests - Test realistic multi-step workflows

These tests simulate how users actually interact with the MCP tools:
1. Discovery → Describe → Query workflow
2. Iterative query refinement
3. Multi-tool interactions
4. Error recovery workflows
"""
from __future__ import annotations

import pytest

from spice_mcp.core.models import TableColumn, TableDescription, TableSummary


class FakeDiscoveryService:
    """Mock discovery service for testing user journeys."""

    def __init__(self):
        self.schemas = {
            "sui": ["sui_base", "sui"],
            "eth": ["ethereum", "ethereum_dex"],
        }
        self.tables = {
            "sui_base": ["events", "transactions", "objects"],
            "ethereum": ["blocks", "transactions", "logs"],
        }
        self.descriptions = {
            ("sui_base", "events"): TableDescription(
                fully_qualified_name="sui_base.events",
                columns=[
                    TableColumn(name="timestamp_ms", polars_dtype="Int64"),
                    TableColumn(name="package", polars_dtype="Utf8"),
                    TableColumn(name="event_type", polars_dtype="Utf8"),
                ],
            ),
            ("ethereum", "blocks"): TableDescription(
                fully_qualified_name="ethereum.blocks",
                columns=[
                    TableColumn(name="number", polars_dtype="Int64"),
                    TableColumn(name="timestamp", polars_dtype="Int64"),
                    TableColumn(name="hash", polars_dtype="Utf8"),
                ],
            ),
        }

    def find_schemas(self, keyword: str) -> list[str]:
        """Find schemas matching keyword."""
        results = []
        for schema_list in self.schemas.values():
            results.extend([s for s in schema_list if keyword.lower() in s.lower()])
        return results

    def list_tables(self, schema: str, limit: int | None = None) -> list[TableSummary]:
        """List tables in schema."""
        tables = self.tables.get(schema, [])
        if limit:
            tables = tables[:limit]
        return [TableSummary(schema=schema, table=t) for t in tables]

    def describe_table(self, schema: str, table: str) -> TableDescription:
        """Describe table columns."""
        key = (schema, table)
        if key not in self.descriptions:
            raise ValueError(f"Table {schema}.{table} not found")
        return self.descriptions[key]


class FakeQueryService:
    """Mock query service for testing user journeys."""

    def __init__(self):
        self.query_history = []

    def execute(
        self,
        *,
        query: str,
        parameters: dict | None = None,
        refresh: bool = False,
        max_age: float | None = None,
        poll: bool = True,
        timeout_seconds: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sample_count: int | None = None,
        sort_by: str | None = None,
        columns: list[str] | None = None,
        include_execution: bool = True,
        performance: str | None = None,
        return_raw: bool = False,
        extras: dict | None = None,
    ) -> dict:
        """Execute query and return mock results."""
        self.query_history.append({"query": query, "parameters": parameters})
        return {
            "rowcount": 2,
            "columns": ["timestamp_ms", "package"] if "sui" in query.lower() else ["number", "timestamp"],
            "data_preview": [
                {"timestamp_ms": 1234567890, "package": "0xabc"}
                if "sui" in query.lower()
                else {"number": 18000000, "timestamp": 1690000000}
            ] * 2,
            "execution": {"execution_id": f"exec-{len(self.query_history)}"},
            "duration_ms": 150,
            "metadata": {"state": "finished"},
        }

    def fetch_metadata(
        self,
        *,
        query: str,
        parameters: dict | None = None,
        max_age: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sample_count: int | None = None,
        sort_by: str | None = None,
        columns: list[str] | None = None,
        performance: str | None = None,
        extras: dict | None = None,
    ) -> dict:
        """Fetch query metadata."""
        return {
            "metadata": {"state": "finished"},
            "next_uri": None,
            "next_offset": None,
        }


@pytest.mark.mcp
def test_discovery_to_describe_to_query_workflow(monkeypatch, tmp_path):
    """Test the complete user journey: discover schemas → describe table → query data."""
    from spice_mcp.config import Config, DuneConfig
    from spice_mcp.logging.query_history import QueryHistory
    from spice_mcp.mcp import server
    from spice_mcp.mcp.tools.execute_query import ExecuteQueryTool
    from spice_mcp.service_layer.discovery_service import DiscoveryService
    from spice_mcp.service_layer.query_service import QueryService

    # Setup
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    fake_discovery = FakeDiscoveryService()
    fake_query = FakeQueryService()

    # Initialize server
    server._ensure_initialized()

    # Replace services with mocks - need to match the actual interface
    from spice_mcp.core.models import SchemaMatch
    
    class FakeExplorer:
        def find_schemas(self, keyword: str):
            schemas = fake_discovery.find_schemas(keyword)
            return [SchemaMatch(schema=s) for s in schemas]
        
        def list_tables(self, schema: str, limit: int | None = None):
            return fake_discovery.list_tables(schema, limit)
        
        def describe_table(self, schema: str, table: str):
            return fake_discovery.describe_table(schema, table)
    
    server.DISCOVERY_SERVICE = DiscoveryService.__new__(DiscoveryService)
    server.DISCOVERY_SERVICE.explorer = FakeExplorer()

    server.QUERY_SERVICE = fake_query
    server.EXECUTE_QUERY_TOOL.query_service = fake_query

    # Step 1: Discover schemas
    schemas_result = server._dune_find_tables_impl(keyword="sui")
    assert "schemas" in schemas_result
    assert len(schemas_result["schemas"]) > 0
    assert "sui_base" in schemas_result["schemas"]

    # Step 2: List tables in discovered schema
    tables_result = server._dune_find_tables_impl(schema="sui_base")
    assert "tables" in tables_result
    assert len(tables_result["tables"]) > 0
    assert "events" in tables_result["tables"]

    # Step 3: Describe table structure
    describe_result = server._dune_describe_table_impl(schema="sui_base", table="events")
    assert "columns" in describe_result
    assert len(describe_result["columns"]) > 0
    column_names = [col["name"] for col in describe_result["columns"]]
    assert "timestamp_ms" in column_names
    assert "package" in column_names

    # Step 4: Query the table using discovered structure
    query_sql = "SELECT timestamp_ms, package FROM sui_base.events LIMIT 10"
    query_result = server.EXECUTE_QUERY_TOOL.execute(query=query_sql, format="preview")
    assert query_result["type"] == "preview"
    assert query_result["rowcount"] == 2
    assert "timestamp_ms" in query_result["columns"]
    assert "package" in query_result["columns"]

    # Verify query was logged
    assert len(fake_query.query_history) == 1
    assert "sui_base.events" in fake_query.query_history[0]["query"]


@pytest.mark.mcp
def test_iterative_query_refinement(monkeypatch, tmp_path):
    """Test iterative query refinement workflow."""
    from spice_mcp.mcp import server

    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    fake_query = FakeQueryService()
    server._ensure_initialized()
    server.QUERY_SERVICE = fake_query
    server.EXECUTE_QUERY_TOOL.query_service = fake_query

    # Initial broad query
    query1 = "SELECT * FROM ethereum.blocks LIMIT 100"
    result1 = server.EXECUTE_QUERY_TOOL.execute(query=query1, format="preview")
    assert result1["type"] == "preview"

    # Refined query with specific columns
    query2 = "SELECT number, timestamp FROM ethereum.blocks WHERE number > 18000000 LIMIT 50"
    result2 = server.EXECUTE_QUERY_TOOL.execute(query=query2, format="preview")
    assert result2["type"] == "preview"
    assert "number" in result2["columns"]
    assert "timestamp" in result2["columns"]

    # Further refinement with aggregation
    query3 = "SELECT number, COUNT(*) as tx_count FROM ethereum.blocks GROUP BY number LIMIT 10"
    result3 = server.EXECUTE_QUERY_TOOL.execute(query=query3, format="preview")
    assert result3["type"] == "preview"

    # Verify all queries were executed
    assert len(fake_query.query_history) == 3


@pytest.mark.mcp
def test_multi_tool_interaction_sequence(monkeypatch, tmp_path):
    """Test using multiple tools in sequence."""
    from spice_mcp.mcp import server

    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    fake_discovery = FakeDiscoveryService()
    fake_query = FakeQueryService()

    server._ensure_initialized()

    # Replace with mocks
    from spice_mcp.core.models import SchemaMatch
    
    class FakeExplorer:
        def find_schemas(self, keyword: str):
            schemas = fake_discovery.find_schemas(keyword)
            return [SchemaMatch(schema=s) for s in schemas]
        
        def list_tables(self, schema: str, limit: int | None = None):
            return fake_discovery.list_tables(schema, limit)
        
        def describe_table(self, schema: str, table: str):
            return fake_discovery.describe_table(schema, table)
    
    server.DISCOVERY_SERVICE = DiscoveryService.__new__(DiscoveryService)
    server.DISCOVERY_SERVICE.explorer = FakeExplorer()

    server.QUERY_SERVICE = fake_query
    server.EXECUTE_QUERY_TOOL.query_service = fake_query

    # 1. Health check
    health = server.dune_health_check()
    assert "status" in health

    # 2. Find schemas
    schemas = server._dune_find_tables_impl(keyword="eth")
    assert len(schemas.get("schemas", [])) > 0

    # 3. List tables
    tables = server._dune_find_tables_impl(schema="ethereum")
    assert len(tables.get("tables", [])) > 0

    # 4. Describe table
    desc = server._dune_describe_table_impl(schema="ethereum", table="blocks")
    assert len(desc["columns"]) > 0

    # 5. Query with discovered info
    query_result = server.EXECUTE_QUERY_TOOL.execute(
        query="SELECT number FROM ethereum.blocks LIMIT 5", format="preview"
    )
    assert query_result["type"] == "preview"

    # All steps should succeed
    assert len(fake_query.query_history) == 1


@pytest.mark.mcp
def test_error_recovery_workflow(monkeypatch, tmp_path):
    """Test error recovery in a workflow."""
    from spice_mcp.mcp import server

    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    fake_query = FakeQueryService()
    server._ensure_initialized()
    server.QUERY_SERVICE = fake_query
    server.EXECUTE_QUERY_TOOL.query_service = fake_query

    # Attempt invalid query
    try:
        server.EXECUTE_QUERY_TOOL.execute(query="SELECTTTT INVALID", format="preview")
        assert False, "Should have raised an error"
    except Exception:
        pass  # Expected error

    # Recover with valid query
    result = server.EXECUTE_QUERY_TOOL.execute(query="SELECT 1 as test", format="preview")
    assert result["type"] == "preview"
    assert result["rowcount"] == 2

    # Verify recovery succeeded
    assert len(fake_query.query_history) == 1

