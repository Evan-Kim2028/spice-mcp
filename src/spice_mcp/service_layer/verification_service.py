"""
Verification Service - Verifies tables exist in Dune with persistent caching.

This service provides lazy verification of table existence, caching results
to avoid repeated queries. Cache persists across server restarts.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from ..adapters.dune.client import DuneAdapter

logger = logging.getLogger(__name__)

# Cache entry expires after 1 week (604800 seconds)
CACHE_TTL_SECONDS = 604800


class VerificationService:
    """
    Service for verifying table existence in Dune with persistent caching.
    
    Verifies tables exist before returning them to users, ensuring only
    queryable tables are surfaced. Uses persistent cache to avoid repeated
    verification queries.
    """

    def __init__(self, cache_path: Path, dune_adapter: DuneAdapter):
        """
        Initialize verification service.
        
        Args:
            cache_path: Path to JSON file for persistent cache storage
            dune_adapter: DuneAdapter instance for querying table existence
        """
        self.cache_path = cache_path
        self.dune_adapter = dune_adapter
        self._cache: dict[str, dict[str, Any]] = self._load_cache()

    def verify_tables_batch(
        self, tables: list[tuple[str, str]]
    ) -> dict[str, bool]:
        """
        Verify multiple tables exist in Dune.
        
        Uses cache for fast lookups, queries Dune only for uncached tables.
        Results are cached for future use.
        
        Args:
            tables: List of (schema, table) tuples to verify
            
        Returns:
            Dict mapping "schema.table" -> bool (exists or not)
        """
        results: dict[str, bool] = {}
        to_check: list[tuple[str, str]] = []

        # Check cache first
        for schema, table in tables:
            fqn = f"{schema}.{table}"
            cached = self._get_cached(fqn)
            if cached is not None:
                results[fqn] = cached
            else:
                to_check.append((schema, table))

        # Verify uncached tables
        if to_check:
            logger.info(f"Verifying {len(to_check)} uncached tables")
            for schema, table in to_check:
                try:
                    exists = self._verify_single(schema, table)
                    fqn = f"{schema}.{table}"
                    results[fqn] = exists
                    self._cache_result(fqn, exists)
                except Exception as e:
                    # Do not hard-cache transient failures as negative results.
                    # Leave the table unverified so callers can choose to keep it.
                    logger.warning(
                        f"Failed to verify {schema}.{table}: {e}. Skipping cache and leaving unverified."
                    )
                    # Intentionally omit from results and cache on failure

        return results

    def _verify_single(self, schema: str, table: str) -> bool:
        """
        Verify a single table exists using lightweight DESCRIBE query.
        
        Uses SHOW COLUMNS which is fast and doesn't require full table scan.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            # Use describe_table which internally uses SHOW COLUMNS
            # This is lightweight and fast
            self.dune_adapter.describe_table(schema, table)
            return True
        except Exception:
            # If describe fails, table doesn't exist
            return False

    def _get_cached(self, table: str) -> bool | None:
        """
        Get verification result from cache if fresh.
        
        Args:
            table: Fully qualified table name (schema.table)
            
        Returns:
            bool if cached and fresh, None if cache miss or stale
        """
        if table not in self._cache:
            return None

        entry = self._cache[table]
        timestamp = entry.get("timestamp", 0)
        age = time.time() - timestamp

        if age < CACHE_TTL_SECONDS:
            return entry.get("exists", False)
        else:
            # Cache entry is stale, remove it
            del self._cache[table]
            self._save_cache()
            return None

    def _cache_result(self, table: str, exists: bool) -> None:
        """
        Cache verification result with current timestamp.
        
        Args:
            table: Fully qualified table name
            exists: Whether table exists
        """
        self._cache[table] = {
            "exists": exists,
            "timestamp": time.time(),
        }
        self._save_cache()

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        """
        Load verification cache from disk.
        
        Returns:
            Dict mapping table -> cache entry
        """
        if not self.cache_path.exists():
            return {}

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                cache = json.load(f)
                # Validate cache structure
                if isinstance(cache, dict):
                    return cache
                return {}
        except Exception as e:
            logger.warning(f"Failed to load verification cache: {e}")
            return {}

    def _save_cache(self) -> None:
        """Persist verification cache to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save verification cache: {e}")

    def clear_cache(self) -> None:
        """Clear verification cache (useful for testing or forced refresh)."""
        self._cache = {}
        if self.cache_path.exists():
            self.cache_path.unlink()
