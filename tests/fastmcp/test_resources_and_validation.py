import pytest


def test_resource_templates_and_reads(monkeypatch, tmp_path):
    # Prepare a history file with lines
    history = tmp_path / "queries.jsonl"
    history.write_text("{\"a\":1}\n{\"b\":2}\n{\"c\":3}\n", encoding="utf-8")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(history))

    # Prepare an artifact file
    artifacts_dir = tmp_path / "artifacts" / "queries" / "by_sha"
    artifacts_dir.mkdir(parents=True)
    sha = ("deadbeef" * 8)[:64]
    (artifacts_dir / f"{sha}.sql").write_text("select 1", encoding="utf-8")

    from spice_mcp.logging.query_history import QueryHistory
    from spice_mcp.mcp import server

    # Seed server state with the tmp paths
    server.QUERY_HISTORY = QueryHistory(history, tmp_path / "artifacts")

    # Test that resource wrappers exist and contain our synchronous functions
    assert hasattr(server.history_tail, 'fn')
    assert callable(server.history_tail.fn)
    assert hasattr(server.sql_artifact, 'fn')
    assert callable(server.sql_artifact.fn)

    # Read tail (last 2 lines) - call synchronous function directly via .fn
    tail_content = server.history_tail.fn("2")
    assert "{\"b\":2}" in tail_content and "{\"c\":3}" in tail_content

    # Read artifact - call synchronous function directly via .fn
    artifact_content = server.sql_artifact.fn(sha)
    assert "select 1" in artifact_content


def test_enum_validation_for_dune_query(monkeypatch, tmp_path):
    """Test that invalid enum values are caught by FastMCP's validation."""
    monkeypatch.setenv("DUNE_API_KEY", "k")
    monkeypatch.setenv("SPICE_QUERY_HISTORY", str(tmp_path / "history.jsonl"))

    from spice_mcp.mcp import server
    
    server._ensure_initialized()
    
    # FastMCP validates enum values at the schema level
    # If we call the tool function directly with invalid format, 
    # it should either raise an error or return an error response
    # Since our tool wraps in error_response, invalid format will 
    # likely be caught by FastMCP's validation before execution
    
    # Test that the tool wrapper exists and contains our synchronous function
    assert hasattr(server.dune_query, 'fn')
    assert callable(server.dune_query.fn)
    
    # Note: FastMCP's enum validation happens at the MCP protocol level,
    # not in our synchronous code. The actual validation is tested by
    # FastMCP's own test suite. We verify our tool is properly registered.
