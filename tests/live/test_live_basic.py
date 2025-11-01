import os

import pytest

from spice_mcp.adapters.dune import query as spice_query

pytestmark = pytest.mark.live


def _should_run_live():
    return bool(os.getenv("SPICE_TEST_LIVE") == "1" and os.getenv("DUNE_API_KEY"))


@pytest.mark.skipif(not _should_run_live(), reason="live tests disabled by default")
def test_live_spice_query_smoke():
    df = spice_query(4388, limit=5, timeout_seconds=20, verbose=False)
    assert df is not None
    assert df.shape[0] >= 0
