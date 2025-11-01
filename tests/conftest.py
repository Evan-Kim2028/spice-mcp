import os

import pytest


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    # Ensure a dummy API key is present for code paths that read env
    monkeypatch.setenv("DUNE_API_KEY", os.getenv("DUNE_API_KEY", "test_key"))
    # Disable live network usage by default
    monkeypatch.delenv("SPICE_TEST_LIVE", raising=False)
    yield

