import pytest


@pytest.mark.asyncio
async def test_missing_env_raises_on_init(monkeypatch):
    # Ensure no API key so Config.from_env fails
    monkeypatch.delenv("DUNE_API_KEY", raising=False)
    monkeypatch.setenv("SPICE_MCP_SKIP_DOTENV", "1")

    from spice_mcp.mcp import server

    # Reset init state
    server.CONFIG = None
    server.QUERY_HISTORY = None
    server.DUNE_ADAPTER = None
    server.QUERY_SERVICE = None
    server.DISCOVERY_SERVICE = None
    server.SUI_SERVICE = None
    server.EXECUTE_QUERY_TOOL = None

    with pytest.raises(ValueError):
        server._ensure_initialized()


def test_main_invokes_app_run(monkeypatch):
    # Provide valid env so _ensure_initialized succeeds
    monkeypatch.setenv("DUNE_API_KEY", "k")

    from spice_mcp.mcp import server

    called = {"run": False}

    def fake_run(*_args, **_kwargs):
        called["run"] = True

    monkeypatch.setattr(server, "app", server.app)
    monkeypatch.setattr(server.app, "run", fake_run)

    server.main()

    assert called["run"] is True
