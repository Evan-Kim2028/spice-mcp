import polars as pl
import responses

from spice_mcp.adapters.dune import extract, urls


@responses.activate
def test_pagination_concatenation_capped_by_limit(monkeypatch):
    # Prepare initial CSV and a next page
    qid = 555
    # First request should reflect the requested limit
    params = {"limit": 2, "offset": 0}

    first_csv = "a,b\n1,2\n"
    next_csv = "a,b\n3,4\n5,6\n"

    first_url = urls.get_query_results_url(
        qid, parameters={**params, "performance": "medium"}
    )
    # Next URI is provided by the API; we simulate a different (wider) page
    next_url = urls.add_args_to_url(
        f"https://api.dune.com/api/v1/query/{qid}/results/csv",
        parameters={"limit": 10, "offset": 1},
    )

    responses.add(
        responses.GET,
        first_url,
        body=first_csv,
        headers={
            "x-dune-next-uri": next_url,
            "x-dune-next-offset": "1",
        },
        status=200,
        content_type="text/csv",
    )
    responses.add(
        responses.GET,
        next_url,
        body=next_csv,
        status=200,
        content_type="text/csv",
    )

    df = extract._get_results(
        query_id=qid,
        api_key="dummy",
        limit=2,  # request only 2 rows, despite more across pages
        offset=0,
        verbose=False,
    )

    assert isinstance(df, pl.DataFrame)
    assert df.shape == (2, 2)
    assert list(df.columns) == ["a", "b"]
    # Ensure next page was requested exactly once
    assert len(responses.calls) == 2
