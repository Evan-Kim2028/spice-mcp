from __future__ import annotations

import json

from spice_mcp.logging.query_history import (
    DisabledQueryHistory,
    QueryHistory,
)


def test_query_history_record_and_artifact(tmp_path):
    history_path = tmp_path / "q.jsonl"
    artifacts_root = tmp_path / "artifacts"

    qh = QueryHistory(history_path, artifacts_root)

    qid = "e-123"
    qtext = "SELECT 1"
    qsha = qh.compute_query_sha256(qtext)
    qh.write_sql_artifact(qtext, qsha)
    qh.record(
        execution_id=qid,
        query_type="raw_sql",
        query_preview=qtext,
        status="success",
        duration_ms=12,
        rowcount=1,
        query_sha256=qsha,
        cache_hit=False,
    )

    # file written
    assert history_path.exists()
    lines = history_path.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["execution_id"] == qid
    assert rec["rowcount"] == 1
    assert "artifacts" in rec

    # artifact dedup: second write should reuse same path
    qh.write_sql_artifact(qtext, qsha)
    artifact_file = artifacts_root / "queries" / "by_sha" / f"{qsha}.sql"
    assert artifact_file.exists()
    assert artifact_file.read_text() == qtext


def test_query_history_disabled_env(monkeypatch):
    monkeypatch.setenv("SPICE_QUERY_HISTORY", "disabled")
    qh = QueryHistory.from_env()
    assert isinstance(qh, DisabledQueryHistory)
    # no exceptions on record
    qh.record(execution_id="x", query_type="raw_sql", query_preview="q", status="success", duration_ms=1)

