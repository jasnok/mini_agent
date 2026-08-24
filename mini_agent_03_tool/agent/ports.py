"""Interfaces that keep the agent independent from team-owned providers and tools."""

from __future__ import annotations

import inspect
from importlib import import_module
from typing import Any, Protocol

from .errors import AgentConfigurationError
from .models import AgentContext, ToolCall, ToolExecutionResult


class AgentProvider(Protocol):
    name: str
    model: str

    async def choose_tool(
        self,
        *,
        message: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        context: AgentContext,
    ) -> ToolCall: ...


class ToolExecutor(Protocol):
    def tool_schemas(self) -> list[dict[str, Any]]: ...

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolExecutionResult: ...


class ExternalToolExecutor:
    """Adapter for the common top-level ``tools.executor`` supplied by teammate 3.

    The import is delayed so the agent can be developed and tested before that
    package is merged. The common executor is expected to expose
    ``get_tool_schemas()`` and ``execute_tool_safely(name, arguments)``.
    """

    def __init__(self) -> None:
        try:
            module = import_module("tools.executor")
            self._schema_function = getattr(module, "get_tool_schemas")
            self._execute_function = getattr(module, "execute_tool_safely")
        except (ImportError, AttributeError) as exc:
            raise AgentConfigurationError(
                "공통 Tool Executor가 연결되지 않았습니다."
            ) from exc

    def tool_schemas(self) -> list[dict[str, Any]]:
        schemas = self._schema_function()
        return [dict(item) for item in schemas]

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolExecutionResult:
        raw = self._execute_function(name, arguments)
        if inspect.isawaitable(raw):
            raw = await raw
        if hasattr(raw, "model_dump"):
            raw = raw.model_dump(mode="json")
        if not isinstance(raw, dict):
            raise AgentConfigurationError("공통 Tool Executor 응답 형식이 올바르지 않습니다.")
        payload = dict(raw)
        payload.setdefault("tool_name", name)
        payload.setdefault("data", {})
        payload.setdefault("message", "")
        return ToolExecutionResult.model_validate(payload)
