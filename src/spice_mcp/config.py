from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from .adapters.http_client import HttpClientConfig


@dataclass(frozen=True)
class DuneConfig:
    """Dune Analytics API configuration."""

    api_key: str  # Required
    api_url: str = "https://api.dune.com/api/v1"


@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration."""

    mode: Literal["enabled", "read_only", "refresh", "disabled"] = "enabled"
    cache_dir: str | None = None
    max_size_mb: int = 500


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    query_history_path: str | None = None
    artifact_root: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class Config:
    """Main application configuration."""

    dune: DuneConfig
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    http: HttpClientConfig = field(default_factory=HttpClientConfig)
    max_concurrent_queries: int = 5
    default_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        api_key = os.getenv("DUNE_API_KEY")
        if not api_key:
            raise ValueError(
                "DUNE_API_KEY environment variable is required. "
                "Get your API key from https://dune.com/settings/api"
            )

        return cls(
            dune=DuneConfig(
                api_key=api_key,
                api_url=os.getenv("DUNE_API_URL", "https://api.dune.com/api/v1"),
            ),
            cache=CacheConfig(
                mode=os.getenv("SPICE_CACHE_MODE", "enabled"),
                cache_dir=os.getenv("SPICE_CACHE_DIR"),
                max_size_mb=int(os.getenv("SPICE_CACHE_MAX_SIZE_MB", "500")),
            ),
            logging=LoggingConfig(
                query_history_path=os.getenv("SPICE_QUERY_HISTORY"),
                artifact_root=os.getenv("SPICE_ARTIFACT_ROOT"),
                enabled=os.getenv("SPICE_LOGGING_ENABLED", "true").lower()
                == "true",
            ),
            http=HttpClientConfig(
                timeout_seconds=float(os.getenv("SPICE_HTTP_TIMEOUT", "15")),
                max_retries=int(os.getenv("SPICE_HTTP_RETRIES", "3")),
                backoff_initial=float(os.getenv("SPICE_HTTP_BACKOFF", "0.35")),
                backoff_max=float(os.getenv("SPICE_HTTP_BACKOFF_MAX", "5.0")),
            ),
            default_timeout_seconds=int(os.getenv("SPICE_TIMEOUT_SECONDS", "30")),
            max_concurrent_queries=int(os.getenv("SPICE_MAX_CONCURRENT_QUERIES", "5")),
        )
