import pytest


@pytest.mark.asyncio
async def test_resource_templates_and_reads(monkeypatch, tmp_path):
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

    # Templates should be registered
    templates = await server.app.get_resource_templates()
    assert "spice:history/tail/{n}" in templates
    assert "spice:artifact/{sha}" in templates

    # Read tail (last 2 lines)
    tail = await server.app._read_resource_mcp("spice:history/tail/2")
    content = tail[0].content if tail else ""
    assert "{\"b\":2}" in content and "{\"c\":3}" in content

    # Read artifact
    art = await server.app._read_resource_mcp(f"spice:artifact/{sha}")
    content2 = art[0].content if art else ""
    assert "select 1" in content2


@pytest.mark.asyncio
async def test_enum_validation_for_dune_query(monkeypatch):
    # Ensure env for potential init, but expect validation to fail before execution
    monkeypatch.setenv("DUNE_API_KEY", "k")

    from spice_mcp.mcp import server

    with pytest.raises(Exception):
        await server.app._call_tool_mcp(
            "dune_query", {"query": "select 1", "format": "not-valid"}
        )
