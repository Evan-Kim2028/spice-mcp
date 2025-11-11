#!/usr/bin/env python3
"""Collect query IDs from query history logs.

Parses logs/queries.jsonl (or ~/.spice_mcp/logs/queries.jsonl) to extract
query IDs from admin actions (create/update/fork) and optionally filters
by ID range.

Usage:
    python scripts/dune_collect_query_ids.py [--start-id START] [--end-id END] [--output OUTPUT]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def find_query_history_path() -> Path | None:
    """Find query history JSONL file."""
    # Try repo-relative first
    repo_path = Path.cwd() / "logs" / "queries.jsonl"
    if repo_path.exists():
        return repo_path
    
    # Fallback to home directory
    home_path = Path.home() / ".spice_mcp" / "logs" / "queries.jsonl"
    if home_path.exists():
        return home_path
    
    # Check environment variable
    if env_path := os.getenv("SPICE_QUERY_HISTORY"):
        env_path_obj = Path(env_path)
        if env_path_obj.exists():
            return env_path_obj
    
    return None


def collect_query_ids(
    history_path: Path,
    start_id: int | None = None,
    end_id: int | None = None,
) -> list[int]:
    """Collect query IDs from history file."""
    query_ids: set[int] = set()
    
    try:
        with history_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # Look for query_id in admin actions
                    if record.get("action_type") == "admin_action":
                        query_id = record.get("query_id")
                        if query_id is not None:
                            query_id_int = int(query_id)
                            # Apply range filter if specified
                            if start_id is not None and query_id_int < start_id:
                                continue
                            if end_id is not None and query_id_int > end_id:
                                continue
                            query_ids.add(query_id_int)
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
    except FileNotFoundError:
        print(f"Error: History file not found: {history_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading history file: {e}", file=sys.stderr)
        sys.exit(1)
    
    return sorted(query_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Collect query IDs from query history logs"
    )
    parser.add_argument(
        "--start-id",
        type=int,
        help="Minimum query ID to include (inclusive)",
    )
    parser.add_argument(
        "--end-id",
        type=int,
        help="Maximum query ID to include (inclusive)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout, one ID per line)",
    )
    parser.add_argument(
        "--history-path",
        type=str,
        help="Path to queries.jsonl file (default: auto-detect)",
    )
    
    args = parser.parse_args()
    
    # Find history file
    if args.history_path:
        history_path = Path(args.history_path)
    else:
        history_path = find_query_history_path()
    
    if history_path is None:
        print("Error: Could not find query history file", file=sys.stderr)
        print("Expected: logs/queries.jsonl or ~/.spice_mcp/logs/queries.jsonl", file=sys.stderr)
        sys.exit(1)
    
    # Collect query IDs
    query_ids = collect_query_ids(history_path, args.start_id, args.end_id)
    
    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for qid in query_ids:
                f.write(f"{qid}\n")
        print(f"Collected {len(query_ids)} query IDs to {output_path}")
    else:
        for qid in query_ids:
            print(qid)
        if query_ids:
            print(f"# Total: {len(query_ids)} query IDs", file=sys.stderr)


if __name__ == "__main__":
    main()

