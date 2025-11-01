from spice_mcp.adapters.dune import urls


def test_get_query_id_various_forms():
    assert urls.get_query_id(1234) == 1234
    assert urls.get_query_id("1234") == 1234
    assert (
        urls.get_query_id("https://dune.com/queries/1234/whatever") == 1234
    )
    assert (
        urls.get_query_id(
            "https://api.dune.com/api/v1/query/1234/results"
        )
        == 1234
    )


def test_add_args_to_url_and_flattening():
    u = "https://api.test/path"
    out = urls.add_args_to_url(
        u,
        parameters={
            "limit": 10,
            "nested": {"a": 1, "b": 2},
            "list": [1, 2, 3],
            "none": None,
        },
    )
    # order not guaranteed, but all must be present and correctly flattened
    assert out.startswith(u + "?")
    assert "limit=10" in out
    assert "nested.a=1" in out and "nested.b=2" in out
    assert "list=1,2,3" in out
    assert "none=" not in out


def test_get_results_urls():
    u_csv = urls.get_query_results_url(999, parameters={"limit": 1}, csv=True)
    assert u_csv.startswith("https://api.dune.com/api/v1/query/999/results/csv?")

    u_json = urls.get_query_results_url(999, parameters={}, csv=False)
    # When no parameters are provided, trailing '?' may be omitted
    assert u_json == "https://api.dune.com/api/v1/query/999/results"

    u_exec = urls.get_execution_results_url("abc", {"offset": 5})
    assert u_exec.startswith(
        "https://api.dune.com/api/v1/execution/abc/results/csv?"
    )
    assert "offset=5" in u_exec
