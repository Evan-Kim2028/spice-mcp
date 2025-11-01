from __future__ import annotations

from typing import Any

from ...core.errors import error_response
from ...service_layer.sui_service import SuiService
from .base import MCPTool


class SuiPackageOverviewTool(MCPTool):
    """Overview of Sui packages: events, transactions, objects (small preview)."""

    def __init__(self, sui_service: SuiService):
        self.sui_service = sui_service

    @property
    def name(self) -> str:
        return "sui_package_overview"

    @property
    def description(self) -> str:
        return (
            "Return a compact overview (counts + previews) of Sui package activity "
            "over a time window, with polling timeouts."
        )

    def get_parameter_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "packages": {"type": "array", "items": {"type": "string"}},
                "hours": {"type": "integer", "default": 72},
                "timeout_seconds": {"type": "number", "default": 30},
            },
            "required": ["packages"],
            "additionalProperties": False,
        }

    async def execute(
        self, *, packages: list[str], hours: int = 72, timeout_seconds: float | None = 30
    ) -> dict[str, Any]:
        try:
            return self.sui_service.package_overview(
                packages,
                hours=hours,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            return error_response(
                exc,
                context={
                    "tool": "sui_package_overview",
                    "packages": packages,
                    "hours": hours,
                },
            )
