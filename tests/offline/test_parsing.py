import polars as pl

from spice_mcp.adapters.dune.extract import _process_raw_table, infer_type


def test_process_raw_table_basic_types_and_nulls():
    # header + mixed types + nulls + ragged line
    raw = (
        "id,name,amount,ts\n"
        "1,Alice,10.5,2024-10-01 12:34:56.789 UTC\n"
        "2,<nil>,,2024-10-01 00:00:00.000 UTC\n"
        "3,Bob,7.0,2024-10-02 01:02:03.004 UTC,extra_col_that_is_ragged\n"
    )

    df = _process_raw_table(raw, types=None, all_types=None)

    assert df.shape[0] == 3
    assert df.columns == ["id", "name", "amount", "ts"]

    # type inference: id -> Int64, name -> String, amount -> Float64, ts -> Datetime
    dtypes = [str(t) for t in df.dtypes]
    assert "Int64" in dtypes[0]
    assert "String" in dtypes[1]
    assert "Float64" in dtypes[2]
    assert "Datetime" in dtypes[3]

    # value checks with null handling
    assert df["name"][1] is None
    assert df["amount"][1] is None
    # datetime parsed to polars Datetime
    assert isinstance(df["ts"].dtype, pl.Datetime) or df["ts"].dtype == pl.Datetime


def test_process_raw_table_all_types_must_cover_all_columns():
    raw = "a,b\n1,2\n"
    all_types = {"a": pl.Int64, "b": pl.Int64}
    df = _process_raw_table(raw, types=None, all_types=all_types)
    assert df.shape == (1, 2)
    assert [str(t) for t in df.dtypes] == [str(pl.Int64), str(pl.Int64)]


def test_infer_type_roundtrip_via_csv():
    s = pl.Series("x", ["1", "2", "3"])  # numeric as strings
    t = infer_type(s)
    # Should infer Int64 for numeric-only strings
    assert str(t) == str(pl.Int64()) or str(t) == str(pl.Int64)
