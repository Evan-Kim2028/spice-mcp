from __future__ import annotations

import os


def resolve_raw_sql_template_id() -> int:
    """Return a stable template ID used for executing raw SQL text.

    Tests stub HTTP boundaries and only require a consistent integer. This
    placeholder can be adjusted if upstream semantics change.
    """
    env_value = os.getenv("SPICE_RAW_SQL_QUERY_ID")
    if env_value:
        try:
            return int(env_value.strip())
        except (ValueError, AttributeError):
            # Invalid environment variable, fallback to default
            pass
    return 4060379
