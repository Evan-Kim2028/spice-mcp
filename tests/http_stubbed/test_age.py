import responses

from spice_mcp.adapters.dune import extract, urls


@responses.activate
def test_latest_execution_age_computation():
    qid = 999
    # Construct JSON shape that includes execution_started_at
    started_ts = "2024-10-01T12:00:00.000Z"
    body = {
        "is_execution_finished": True,
        "execution_id": "e-1",
        "execution_started_at": started_ts,
        "state": "QUERY_STATE_COMPLETED",
    }
    url = urls.get_query_results_url(qid, parameters={}, csv=False)
    responses.add(
        responses.GET,
        url,
        json=body,
        status=200,
        content_type="application/json",
    )

    age = extract._get_query_latest_age(qid, verbose=False, api_key="k")
    assert age is not None
    assert age > 0
