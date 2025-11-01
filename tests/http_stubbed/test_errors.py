import types

import responses

from spice_mcp.adapters.dune import extract, urls


@responses.activate
def test_get_results_404_returns_none():
    qid = 123
    u = urls.get_query_results_url(qid, parameters={"limit": 1, "performance": "medium"})
    responses.add(responses.GET, u, body="", status=404)
    out = extract._get_results(query_id=qid, api_key="k", limit=1, verbose=False)
    assert out is None


def test_poll_execution_retries_429_then_completes(monkeypatch):
    calls = {"n": 0}

    def fake_get(*_a, **_kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return types.SimpleNamespace(
                status_code=429,
                json=lambda: {"error": "rate limit"},
            )
        else:
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "is_execution_finished": True,
                    "state": "QUERY_STATE_COMPLETED",
                    "execution_started_at": "2024-10-01T00:00:00.000Z",
                },
            )

    # patch requests and time
    import requests as _requests
    monkeypatch.setattr(_requests, "get", fake_get)
    monkeypatch.setattr(
        extract,
        "time",
        types.SimpleNamespace(time=lambda: 1000.0, sleep=lambda s: None),
    )

    extract._poll_execution(
        {"execution_id": "e1"},
        api_key="k",
        poll_interval=0.1,
        verbose=False,
        timeout_seconds=2.0,
    )
    assert calls["n"] >= 2


@responses.activate
def test_get_latest_execution_not_found_returns_none():
    qid = 42
    url = urls.get_query_results_url(qid, parameters={"limit": 0}, csv=False)
    responses.add(
        responses.GET,
        url,
        json={
            "error": "not found: No execution found for the latest version of the given query"
        },
        status=404,
    )

    out = extract.get_latest_execution({
        "query_id": qid,
        "api_key": "k",
        "parameters": None,
        "performance": "medium",
    })
    assert out is None
