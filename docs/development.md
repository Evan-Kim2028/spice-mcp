# Development Guide

This document summarizes local development workflows for spice-mcp.

## Tooling

- Tests: `pytest` (+ `responses`, `vcrpy`, `hypothesis`)
- Lint/Format: `ruff` (lint + import sort + formatting)
- Types: `mypy`

Install dev tools via uv: `uv sync`.

## Commands

```
uv run ruff format
uv run ruff check .
uv run mypy src tests
uv run pytest -q -m "not live" --cov=src/spice_mcp --cov-report=term-missing
```

Enable live tests explicitly:
`SPICE_TEST_LIVE=1 DUNE_API_KEY=... uv run pytest -q --cov=src/spice_mcp --cov-report=term-missing`

## Tests Layout

- `tests/offline/`: pure unit tests; no network.
- `tests/http_stubbed/`: HTTP boundary via `responses`.
- `tests/tools/`: service + MCP tool unit tests.
- `tests/mcp/`: FastMCP contract tests with stubbed services (preview/raw/metadata, Sui resources).
- `tests/fastmcp/`: registration/metadata smoke tests for FastMCP wiring.
- `tests/style/`: static safety checks (lazyframe enforcement, etc.).
- `tests/live/`: opt-in integrations; require `SPICE_TEST_LIVE=1` and `DUNE_API_KEY`.

Most unit/contract tests construct stub implementations of the ports in `src/spice_mcp/core/ports.py`. See `tests/tools/test_query_service.py` and `tests/mcp/test_tool_contracts.py` for examples.

## Style

- Follow Ruff + ruff-format defaults (88 cols, py313).
- Prefer small, focused functions and explicit typing in `src/`.
- Tests prioritize readability over strict typing.
- Export `SPICE_MCP_SKIP_DOTENV=1` when running tests that expect the API key to be unset.
- Polars LazyFrames are mandatory in application code. Use helpers in `spice_mcp.polars_utils` and keep eager `.collect()` in that module only. The style test `tests/style/test_polars_lazy.py` enforces this convention.
