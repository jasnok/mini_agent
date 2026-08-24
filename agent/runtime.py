"""Bounded parking agent loop with deterministic safety checks."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from .errors import AgentError, InvalidProviderResponseError
from .models import (
    AgentContext,
    AgentErrorInfo,
    ParkingAgentResult,
    ToolExecutionResult,
    TraceItem,
)
from .policies import repeated_call_key, validate_tool_call
from .ports import AgentProvider, ToolExecutor
from .prompts import PARKING_AGENT_SYSTEM_PROMPT


MAX_TOOL_CALLS = 3
SAFE_ERROR_MESSAGES = {
    "TOOL_NOT_ALLOWED": "허용되지 않은 Tool 요청이 거부되었습니다.",
    "TOOL_VALIDATION_ERROR": "Tool 입력값을 확인해 주세요.",
    "TOOL_EXECUTION_ERROR": "Tool 실행 중 오류가 발생했습니다.",
    "DATABASE_UNAVAILABLE": "차량 정보를 조회할 수 없습니다. 잠시 후 다시 시도해 주세요.",
}


async def run_agent_cycle(
    *,
    message: str,
    vehicle_number: str,
    provider: AgentProvider,
    tool_executor: ToolExecutor,
) -> ParkingAgentResult:
    context = AgentContext(vehicle_number=vehicle_number)
    trace: list[TraceItem] = [
        TraceItem(step=0, stage="input_validation", status="completed")
    ]
    seen_calls: set[tuple[str, str]] = set()

    try:
        schemas = tool_executor.tool_schemas()
    except AgentError as exc:
        return _error_result(context, trace, exc.code, exc.termination_reason, str(exc))
    except Exception:
        return _error_result(
            context,
            trace,
            "AGENT_CONFIGURATION_ERROR",
            "provider_error",
            "공통 Tool 설정을 불러오지 못했습니다.",
        )

    for step in range(1, MAX_TOOL_CALLS + 1):
        selection_started = perf_counter()
        try:
            call = await provider.choose_tool(
                message=message,
                system_prompt=PARKING_AGENT_SYSTEM_PROMPT,
                tools=schemas,
                context=context,
            )
        except AgentError as exc:
            trace.append(
                TraceItem(
                    step=step,
                    stage="tool_selection",
                    status="error",
                    error_code=exc.code,
                    elapsed_ms=_elapsed(selection_started),
                )
            )
            return _error_result(context, trace, exc.code, exc.termination_reason, str(exc))
        except Exception:
            error = InvalidProviderResponseError("LLM 응답을 처리하지 못했습니다.")
            return _error_result(context, trace, error.code, error.termination_reason, str(error))

        trace.append(
            TraceItem(
                step=step,
                stage="tool_selection",
                status="completed",
                tool_name=call.name,
                arguments=call.arguments,
                elapsed_ms=_elapsed(selection_started),
            )
        )

        call_key = repeated_call_key(call)
        if call_key in seen_calls:
            return _error_result(
                context,
                trace,
                "REPEATED_TOOL_CALL",
                "repeated_tool_call",
                "동일한 Tool 호출이 반복되어 안전하게 종료했습니다.",
                status="rejected",
            )
        seen_calls.add(call_key)

        policy = validate_tool_call(call, context)
        if not policy.allowed:
            trace.append(
                TraceItem(
                    step=step,
                    stage="tool_validation",
                    status="rejected",
                    tool_name=call.name,
                    arguments=call.arguments,
                    error_code="POLICY_REJECTED",
                )
            )
            return _error_result(
                context,
                trace,
                "POLICY_REJECTED",
                "policy_rejected",
                policy.reason,
                status="rejected",
            )

        execution_started = perf_counter()
        try:
            tool_result = await tool_executor.execute(call.name, call.arguments)
        except Exception:
            tool_result = ToolExecutionResult(
                success=False,
                tool_name=call.name,
                error_code="TOOL_EXECUTION_ERROR",
                message="Tool 실행 중 오류가 발생했습니다.",
            )
        trace.append(
            TraceItem(
                step=step,
                stage="tool_execution",
                status="completed" if tool_result.success else "error",
                tool_name=call.name,
                arguments=call.arguments,
                result=tool_result.data,
                error_code=tool_result.error_code,
                elapsed_ms=_elapsed(execution_started),
            )
        )

        if not tool_result.success:
            code = tool_result.error_code or "TOOL_EXECUTION_ERROR"
            return _error_result(
                context,
                trace,
                code,
                _tool_termination_reason(code),
                SAFE_ERROR_MESSAGES.get(code, "Tool을 안전하게 실행하지 못했습니다."),
            )

        validation_error = _apply_tool_result(context, call.name, tool_result)
        if validation_error:
            return _error_result(
                context,
                trace,
                "TOOL_EXECUTION_ERROR",
                "tool_execution_error",
                validation_error,
            )

        if context.gate_action is not None:
            return _completed_result(context, trace, tool_result)

    return _error_result(
        context,
        trace,
        "MAX_STEPS_EXCEEDED",
        "max_steps_exceeded",
        "최대 Tool 호출 횟수에 도달했습니다.",
        status="rejected",
    )


def _apply_tool_result(
    context: AgentContext,
    tool_name: str,
    result: ToolExecutionResult,
) -> str | None:
    context.tool_results.append({"tool_name": tool_name, "data": result.data})
    if tool_name == "check_vehicle":
        status = result.data.get("status")
        if status not in {"APPROVED", "BLOCKED", "NOT_FOUND"}:
            return "차량 조회 Tool이 알 수 없는 상태를 반환했습니다."
        if result.data.get("vehicle_number") != context.vehicle_number:
            return "차량 조회 결과의 차량 번호가 요청과 일치하지 않습니다."
        context.vehicle_checked = True
        context.vehicle_status = status
        context.registered = bool(result.data.get("registered", status != "NOT_FOUND"))
        return None

    if result.data.get("vehicle_number") != context.vehicle_number:
        return "Gate Tool 결과의 차량 번호가 요청과 일치하지 않습니다."
    gate_opened = result.data.get("gate_opened")
    if tool_name == "open_gate" and gate_opened is not True:
        return "문 열기 Tool이 개방 성공 결과를 반환하지 않았습니다."
    if tool_name == "deny_gate" and gate_opened is not False:
        return "출입 거부 Tool 결과가 안전한 닫힘 상태가 아닙니다."
    context.gate_action = tool_name
    return None


def _completed_result(
    context: AgentContext,
    trace: list[TraceItem],
    tool_result: ToolExecutionResult,
) -> ParkingAgentResult:
    opened = context.gate_action == "open_gate" and bool(
        tool_result.data.get("gate_opened", False)
    )
    message = tool_result.data.get("message") or (
        "등록 차량으로 확인되어 문을 열었습니다."
        if opened
        else "차량 상태에 따라 출입을 허용하지 않았습니다."
    )
    trace.append(
        TraceItem(
            step=len(trace),
            stage="terminated",
            status="completed",
            result={"termination_reason": "completed"},
        )
    )
    return ParkingAgentResult(
        success=True,
        vehicle_number=context.vehicle_number,
        registered=context.registered,
        vehicle_status=context.vehicle_status,
        gate_opened=opened,
        message=message,
        status="completed",
        trace=trace,
        termination_reason="completed",
    )


def _error_result(
    context: AgentContext,
    trace: list[TraceItem],
    code: str,
    termination_reason: str,
    message: str,
    *,
    status: str = "error",
) -> ParkingAgentResult:
    trace.append(
        TraceItem(
            step=len(trace),
            stage="terminated",
            status=status,
            error_code=code,
            result={"termination_reason": termination_reason},
        )
    )
    return ParkingAgentResult(
        success=False,
        vehicle_number=context.vehicle_number,
        registered=context.registered,
        vehicle_status=context.vehicle_status,
        gate_opened=False,
        message=message,
        status=status,
        trace=trace,
        termination_reason=termination_reason,
        error=AgentErrorInfo(code=code, message=message),
    )


def _tool_termination_reason(code: str) -> str:
    return {
        "TOOL_NOT_ALLOWED": "tool_not_allowed",
        "TOOL_VALIDATION_ERROR": "tool_validation_error",
        "DATABASE_UNAVAILABLE": "database_unavailable",
    }.get(code, "tool_execution_error")


def _elapsed(started: float) -> int:
    return round((perf_counter() - started) * 1000)
