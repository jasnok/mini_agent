"""Deterministic provider used for local development and tests."""

from __future__ import annotations

from typing import Any

from ..models import AgentContext, ToolCall


class MockAgentProvider:
    name = "mock"
    model = "parking-policy-mock"

    async def choose_tool(
        self,
        *,
        message: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        context: AgentContext,
    ) -> ToolCall:
        del message, system_prompt, tools
        if not context.vehicle_checked:
            return ToolCall(
                name="check_vehicle",
                arguments={"vehicle_number": context.vehicle_number},
            )
        if context.vehicle_status == "APPROVED":
            return ToolCall(
                name="open_gate",
                arguments={"vehicle_number": context.vehicle_number},
            )
        return ToolCall(
            name="deny_gate",
            arguments={
                "vehicle_number": context.vehicle_number,
                "reason": context.vehicle_status,
            },
        )
