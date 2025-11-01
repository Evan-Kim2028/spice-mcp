from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MCPError:
    code: str
    message: str
    suggestions: tuple[str, ...] = ()
    context: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "data": {"suggestions": list(self.suggestions)},
        }
        if self.context:
            payload["context"] = _redact_context(self.context)
        return payload


def categorize_error(error: Exception) -> MCPError:
    """Return a structured MCPError with actionable suggestions."""
    msg = str(error) if error is not None else ""
    low = msg.lower()

    if isinstance(error, TimeoutError) or "timeout" in low or "timed out" in low:
        return MCPError(
            code="QUERY_TIMEOUT",
            message=msg or "Query timed out",
            suggestions=(
                "Increase timeout_seconds (e.g., 60 or 120).",
                "Reduce the scan window or LIMIT.",
                "Add WHERE filters to narrow the dataset.",
            ),
        )

    if "429" in low or "rate limit" in low:
        return MCPError(
            code="RATE_LIMIT",
            message=msg or "Dune API rate limit hit.",
            suggestions=(
                "Retry shortly; the client already applies exponential backoff.",
                "Use cached results or smaller LIMIT windows.",
            ),
        )

    if "401" in low or "unauthorized" in low or "api key" in low:
        return MCPError(
            code="AUTH_ERROR",
            message=msg or "Authentication failed.",
            suggestions=(
                "Ensure DUNE_API_KEY is exported before launching Codex.",
                "Rotate or verify the API key in Dune settings.",
            ),
        )

    if "query failed" in low or "sql" in low or "syntax" in low:
        return MCPError(
            code="QUERY_ERROR",
            message=msg or "Query execution failed.",
            suggestions=(
                "Validate SQL and parameters in the Dune UI.",
                "Check schema/table/column names.",
                "Ensure parameter names and types match the query definition.",
            ),
        )

    return MCPError(
        code="UNKNOWN_ERROR",
        message=msg or type(error).__name__,
        suggestions=(
            "Retry the request.",
            "Inspect error details for additional context.",
        ),
    )


def error_response(error: Exception, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Serialize an error into the standard MCP envelope."""
    cat = categorize_error(error)
    if context:
        cat.context = context
    payload: dict[str, Any] = {
        "ok": False,
        "error": cat.to_payload(),
    }
    return payload


def _redact_context(ctx: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in ctx.items():
        if isinstance(value, str) and any(token in key.lower() for token in ("api_key", "token", "secret")):
            redacted[key] = "****"
        else:
            redacted[key] = value
    return redacted
