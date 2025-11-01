from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MCPTool(ABC):
    """Abstract base class for all MCP tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for MCP registration."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable tool description."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute tool logic and return result dictionary."""
        raise NotImplementedError

    @abstractmethod
    def get_parameter_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool parameters."""
        raise NotImplementedError

    @property
    def category(self) -> str:
        """Tool category for organization."""
        return "query"

    @property
    def usage_examples(self) -> list[dict[str, Any]]:
        """Usage examples for documentation."""
        return []

