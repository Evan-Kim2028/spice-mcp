## Contributing to spice-mcp

Thanks for your interest in contributing! This is a lightweight guide to get you productive quickly.

### Setup
- Python 3.13+
- Install dependencies:
  - Using uv: `uv sync`
  - Or pip: `pip install -e . && pip install -r <(python - <<'PY'\nimport tomllib,sys;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['tool']['rye']['dev-dependencies']))\nPY\n)`

### Running the server
- `python -m spice_mcp.mcp.server --env PYTHONPATH=$(pwd)/src`
- Or `spice-mcp` if installed as a console script

### Tests
- Tiered runner: `python tests/scripts/comprehensive_test_runner.py [-t 1 -t 3] [--stop] [--junit out.xml]`
- Pytest quick run (offline): `uv run pytest -q -m "not live"`
- Live tests: `export SPICE_TEST_LIVE=1 DUNE_API_KEY=...` then run as above

### Linting / Type checks
- Ruff: `uv run ruff check . && uv run ruff format .`
- MyPy (optional relaxed config): `uv run mypy`

### Pull requests
- Keep changes focused, add/adjust tests when possible
- Ensure no secrets are committed (`.env` is ignored and required for keys)
- Follow existing code style and patterns; avoid gratuitous new deps
