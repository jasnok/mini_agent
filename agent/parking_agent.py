"""Public entry point for the parking AI agent."""

from __future__ import annotations

import re

from .errors import AgentConfigurationError
from .models import AgentErrorInfo, ParkingAgentResult, TraceItem
from .ports import AgentProvider, ExternalToolExecutor, ToolExecutor
from .providers import get_default_provider
from .runtime import run_agent_cycle


VEHICLE_NUMBER_PATTERN = re.compile(r"\d{2,3}[가-힣]\d{4}")


async def run_parking_agent(
    message: str,
    vehicle_number: str | None = None,
    *,
    provider: AgentProvider | None = None,
    tool_executor: ToolExecutor | None = None,
) -> dict:
    """Run the bounded parking agent and return the shared team response shape."""
    selected_vehicle_number = _select_vehicle_number(message, vehicle_number)
    if selected_vehicle_number is None:
        result = ParkingAgentResult(
            success=False,
            vehicle_number=None,
            registered=False,
            vehicle_status=None,
            gate_opened=False,
            message="차량 번호를 알려주세요.",
            status="needs_clarification",
            trace=[
                TraceItem(
                    step=1,
                    stage="input_validation",
                    status="needs_clarification",
                )
            ],
            termination_reason="needs_clarification",
            error=None,
        )
        return result.model_dump(mode="json")

    try:
        selected_provider = provider or get_default_provider()
        selected_executor = tool_executor or ExternalToolExecutor()
    except AgentConfigurationError as exc:
        result = ParkingAgentResult(
            success=False,
            vehicle_number=selected_vehicle_number,
            registered=False,
            vehicle_status=None,
            gate_opened=False,
            message=str(exc),
            status="error",
            trace=[
                TraceItem(
                    step=0,
                    stage="terminated",
                    status="error",
                    error_code=exc.code,
                )
            ],
            termination_reason=exc.termination_reason,
            error=AgentErrorInfo(code=exc.code, message=str(exc)),
        )
        return result.model_dump(mode="json")

    result = await run_agent_cycle(
        message=message,
        vehicle_number=selected_vehicle_number,
        provider=selected_provider,
        tool_executor=selected_executor,
    )
    return result.model_dump(mode="json")


def _select_vehicle_number(message: str, explicit: str | None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip().replace(" ", "").replace("-", "")
    match = VEHICLE_NUMBER_PATTERN.search(message or "")
    return match.group(0) if match else None
