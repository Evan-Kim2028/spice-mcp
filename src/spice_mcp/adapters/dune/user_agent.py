"""User agent utility to avoid importing overloaded functions."""

ADAPTER_VERSION = "0.1.4"


def get_user_agent() -> str:
    """Get user agent string for HTTP requests."""
    return f"spice-mcp/{ADAPTER_VERSION}"

