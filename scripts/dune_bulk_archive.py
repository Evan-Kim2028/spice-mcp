#!/usr/bin/env python3
"""Bulk archive or unarchive Dune queries from a file of query IDs.

Reads query IDs from a file (one per line) and performs bulk archive/unarchive
operations. Optionally verifies query ownership before archiving.

Usage:
    python scripts/dune_bulk_archive.py archive query_ids.txt [--verify-owner]
    python scripts/dune_bulk_archive.py unarchive query_ids.txt [--verify-owner]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Add parent directory to path to import spice_mcp
sys.path.insert(0, str(Path(__file__).parent.parent))

from spice_mcp.adapters.dune.admin import DuneAdminAdapter
from spice_mcp.adapters.http_client import HttpClient, HttpClientConfig
from spice_mcp.config import Config


def load_query_ids(file_path: Path) -> list[int]:
    """Load query IDs from file (one per line)."""
    query_ids = []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                try:
                    query_ids.append(int(line))
                except ValueError:
                    print(f"Warning: Skipping invalid line: {line}", file=sys.stderr)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    return query_ids


def verify_query_accessible(admin: DuneAdminAdapter, query_id: int) -> bool:
    """Verify query exists and is accessible."""
    try:
        admin.get(query_id)
        return True
    except Exception:
        return False


def bulk_archive(
    query_ids: list[int],
    action: str,  # "archive" or "unarchive"
    verify_owner: bool = False,
    api_key: str | None = None,
) -> None:
    """Perform bulk archive/unarchive operations."""
    if api_key is None:
        api_key = os.getenv("DUNE_API_KEY")
        if not api_key:
            print("Error: DUNE_API_KEY environment variable required", file=sys.stderr)
            sys.exit(1)
    
    config = Config.from_env()
    http_client = HttpClient(config.http)
    admin = DuneAdminAdapter(api_key, http_client=http_client, http_config=config.http)
    
    method = admin.archive if action == "archive" else admin.unarchive
    
    success_count = 0
    error_count = 0
    
    print(f"Processing {len(query_ids)} queries for {action}...")
    
    for i, query_id in enumerate(query_ids, 1):
        try:
            # Verify owner if requested
            if verify_owner:
                if not verify_query_accessible(admin, query_id):
                    print(f"[{i}/{len(query_ids)}] Query {query_id}: Not accessible, skipping", file=sys.stderr)
                    error_count += 1
                    continue
            
            # Perform archive/unarchive
            result = method(query_id)
            status = result.get("status", "unknown")
            print(f"[{i}/{len(query_ids)}] Query {query_id}: {status}")
            success_count += 1
            
            # Rate limiting: small delay between requests
            time.sleep(0.1)
            
        except Exception as e:
            print(f"[{i}/{len(query_ids)}] Query {query_id}: Error - {e}", file=sys.stderr)
            error_count += 1
    
    print(f"\nSummary: {success_count} succeeded, {error_count} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk archive or unarchive Dune queries"
    )
    parser.add_argument(
        "action",
        choices=["archive", "unarchive"],
        help="Action to perform",
    )
    parser.add_argument(
        "query_ids_file",
        type=str,
        help="File containing query IDs (one per line)",
    )
    parser.add_argument(
        "--verify-owner",
        action="store_true",
        help="Verify query ownership before archiving",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Dune API key (default: DUNE_API_KEY env var)",
    )
    
    args = parser.parse_args()
    
    # Load query IDs
    query_ids_file = Path(args.query_ids_file)
    query_ids = load_query_ids(query_ids_file)
    
    if not query_ids:
        print("No query IDs found in file", file=sys.stderr)
        sys.exit(1)
    
    # Perform bulk operation
    bulk_archive(
        query_ids,
        args.action,
        verify_owner=args.verify_owner,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    main()

