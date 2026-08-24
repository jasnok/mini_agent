from __future__ import annotations

from typing import Any

from agent.models import AgentContext, ToolCall, ToolExecutionResult


class FakeToolExecutor:
    def __init__(self, status: str = "APPROVED", failure_code: str | None = None):
        self.status = status
        self.failure_code = failure_code
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def tool_schemas(self):
        return [
            {"name": "check_vehicle", "input_schema": {"type": "object"}},
            {"name": "open_gate", "input_schema": {"type": "object"}},
            {"name": "deny_gate", "input_schema": {"type": "object"}},
        ]

    async def execute(self, name: str, arguments: dict[str, Any]):
        self.calls.append((name, arguments))
        if self.failure_code:
            code = self.failure_code
            self.failure_code = None
            return ToolExecutionResult(
                success=False,
                tool_name=name,
                error_code=code,
                message="failed",
            )
        vehicle_number = arguments["vehicle_number"]
        if name == "check_vehicle":
            return ToolExecutionResult(
                success=True,
                tool_name=name,
                data={
                    "vehicle_number": vehicle_number,
                    "registered": self.status != "NOT_FOUND",
                    "status": self.status,
                },
            )
        opened = name == "open_gate"
        return ToolExecutionResult(
            success=True,
            tool_name=name,
            data={
                "vehicle_number": vehicle_number,
                "gate_opened": opened,
                "message": "문이 열렸습니다." if opened else "출입할 수 없습니다.",
            },
        )


class ScriptedProvider:
    name = "scripted"
    model = "test"

    def __init__(self, calls: list[ToolCall]):
        self.calls = list(calls)

    async def choose_tool(
        self,
        *,
        message: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        context: AgentContext,
    ) -> ToolCall:
        del message, system_prompt, tools, context
        return self.calls.pop(0)
