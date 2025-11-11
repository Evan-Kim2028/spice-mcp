from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


class DisabledQueryHistory:
    """No-op implementation when logging disabled."""

    def record(self, *args, **kwargs):
        pass

    def write_sql_artifact(self, *args, **kwargs):
        return None


class QueryHistory:
    """Always-on JSONL query history with fallback paths."""

    def __init__(self, history_path: Path, artifact_root: Path):
        self.history_path = history_path
        self.artifact_root = artifact_root

        # Ensure directories exist
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> QueryHistory | DisabledQueryHistory:
        """Load from environment with fallback paths."""
        # Primary: Environment variable or repo-relative
        if history_env := os.getenv("SPICE_QUERY_HISTORY"):
            if history_env.lower() == "disabled":
                return DisabledQueryHistory()
            history_path = Path(history_env)
        else:
            # Try repo-relative first
            repo_path = Path.cwd() / "logs" / "queries.jsonl"
            if repo_path.parent.exists():
                history_path = repo_path
            else:
                # Fallback to home directory
                history_path = (
                    Path.home() / ".spice_mcp" / "logs" / "queries.jsonl"
                )

        # Artifact root
        if artifact_env := os.getenv("SPICE_ARTIFACT_ROOT"):
            artifact_root = Path(artifact_env)
        else:
            artifact_root = history_path.parent / "artifacts"

        return cls(history_path, artifact_root)

    def record(
        self,
        execution_id: str,
        query_type: str,  # "query_id", "url", "raw_sql"
        query_preview: str,  # First 200 chars
        status: str,  # "success", "error", "timeout"
        duration_ms: int,
        rowcount: int | None = None,
        query_sha256: str | None = None,
        reason: str | None = None,
        cache_hit: bool = False,
        error: str | None = None,
        action_type: str = "query_execution",  # "query_execution" or "admin_action"
        **extra_fields,
    ) -> None:
        """Record query execution or admin action to JSONL."""
        record = {
            "action_type": action_type,
            "execution_id": execution_id,
            "ts": int(datetime.now().timestamp()),
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "query_preview": query_preview[:200],
            "status": status,
            "duration_ms": duration_ms,
            "rowcount": rowcount,
            "query_sha256": query_sha256,
            "cache_hit": cache_hit,
            "reason": reason,
            "error": error,
            **extra_fields,
        }

        # Add artifact paths if available
        if query_sha256:
            record["artifacts"] = {
                "sql_path": str(
                    self.artifact_root
                    / "queries"
                    / "by_sha"
                    / f"{query_sha256}.sql"
                )
            }

        # Write to JSONL (atomic append)
        try:
            with self.history_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            # Never raise - log warning and continue
            import logging

            logging.warning(f"Failed to write query history: {e}")

    def compute_query_sha256(self, query: str) -> str:
        """Compute SHA-256 hash of query text."""
        return hashlib.sha256(query.encode("utf-8")).hexdigest()

    def write_sql_artifact(self, query: str, query_sha256: str):
        """Write SQL to artifact storage (deduplicated by SHA-256)."""
        queries_dir = self.artifact_root / "queries" / "by_sha"
        queries_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = queries_dir / f"{query_sha256}.sql"

        # Only write if doesn't exist (deduplication)
        if not artifact_path.exists():
            try:
                artifact_path.write_text(query, encoding="utf-8")
            except Exception as e:
                import logging

                logging.warning(f"Failed to write SQL artifact: {e}")

        return artifact_path

