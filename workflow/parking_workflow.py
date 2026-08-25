"""LLM 없이 공통 주차 Tool을 순서대로 실행하는 Workflow입니다."""

from collections.abc import Callable
from time import perf_counter
from typing import Any


Tool = Callable[..., dict[str, Any]]
ALLOWED_ERROR_CODES = {
    "TOOL_NOT_ALLOWED",
    "TOOL_VALIDATION_ERROR",
    "TOOL_EXECUTION_ERROR",
    "DATABASE_UNAVAILABLE",
}


def _common_tools_unavailable(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise RuntimeError("공통 주차 Tool이 아직 연결되지 않았습니다.")


try:
    # Database / Tool 담당자가 제공하는 단일 구현을 Workflow와 Agent가 함께 사용합니다.
    from tools.parking_tools import check_vehicle, deny_gate, open_gate
except ModuleNotFoundError as error:
    if error.name not in {"tools", "tools.parking_tools"}:
        raise
    # 담당 브랜치 단위 테스트에서는 아래 이름을 계약형 Fake로 교체합니다.
    check_vehicle = _common_tools_unavailable
    deny_gate = _common_tools_unavailable
    open_gate = _common_tools_unavailable


def run_parking_workflow(vehicle_number: str) -> dict[str, Any]:
    """차량 조회 후 상태에 맞는 Gate Tool 하나만 호출합니다."""
    trace: list[dict[str, Any]] = []
    normalized = _validate_required_vehicle_number(vehicle_number)
    if normalized is None:
        trace.append(_trace(1, "input_validation", "failed", error_code="TOOL_VALIDATION_ERROR"))
        return _result(
            success=False,
            vehicle_number=None,
            registered=False,
            vehicle_status=None,
            gate_opened=False,
            message="차량 번호를 입력해 주세요.",
            status="needs_clarification",
            termination_reason="needs_clarification",
            trace=trace,
            error={"code": "TOOL_VALIDATION_ERROR", "message": "차량 번호가 필요합니다."},
        )

    trace.append(_trace(1, "input_validation", "completed"))
    checked = _call_tool(
        check_vehicle,
        "check_vehicle",
        {"vehicle_number": normalized},
        step=2,
        stage="vehicle_check",
    )
    trace.append(checked["trace"])
    if checked["error"] is not None:
        return _tool_error_result(normalized, trace, checked["error"])

    vehicle = checked["data"]
    if not _valid_vehicle_result(vehicle):
        error = {"code": "TOOL_EXECUTION_ERROR", "message": "차량 조회 결과 형식이 유효하지 않습니다."}
        trace[-1].update(status="error", error_code=error["code"])
        return _tool_error_result(normalized, trace, error)

    canonical_vehicle_number = vehicle["vehicle_number"]
    vehicle_status = vehicle["status"]
    registered = vehicle["registered"]
    action = "open_gate" if vehicle_status == "APPROVED" else "deny_gate"
    trace.append(
        _trace(
            3,
            "policy_decision",
            "completed",
            result={"vehicle_status": vehicle_status, "action": action},
        )
    )

    arguments = {"vehicle_number": canonical_vehicle_number}
    gate_tool: Tool = open_gate
    if action == "deny_gate":
        arguments["reason"] = vehicle_status
        gate_tool = deny_gate

    executed = _call_tool(gate_tool, action, arguments, step=4, stage="tool_execution")
    trace.append(executed["trace"])
    if executed["error"] is not None:
        return _tool_error_result(canonical_vehicle_number, trace, executed["error"], registered, vehicle_status)

    gate = executed["data"]
    if not _valid_gate_result(gate, canonical_vehicle_number):
        error = {"code": "TOOL_EXECUTION_ERROR", "message": "Gate Tool 결과 형식이 유효하지 않습니다."}
        trace[-1].update(status="error", error_code=error["code"])
        return _tool_error_result(canonical_vehicle_number, trace, error, registered, vehicle_status)

    allowed = vehicle_status == "APPROVED"
    if gate["gate_opened"] is not allowed:
        error = {"code": "TOOL_EXECUTION_ERROR", "message": "Gate Tool 결과가 출입 정책과 일치하지 않습니다."}
        trace[-1].update(status="error", error_code=error["code"])
        return _tool_error_result(canonical_vehicle_number, trace, error, registered, vehicle_status)

    return _result(
        success=True,
        vehicle_number=canonical_vehicle_number,
        registered=registered,
        vehicle_status=vehicle_status,
        gate_opened=gate["gate_opened"],
        message=gate["message"],
        status="completed" if allowed else "rejected",
        termination_reason="completed" if allowed else "policy_rejected",
        trace=trace,
        error=None,
    )


def _validate_required_vehicle_number(value: object) -> str | None:
    """공통 Tool의 최종 정규화 규칙을 복제하지 않고 필수 입력만 검사합니다."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _call_tool(
    tool: Tool,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    step: int,
    stage: str,
) -> dict[str, Any]:
    started = perf_counter()
    try:
        data = tool(**arguments)
    except Exception as error:
        code = getattr(error, "code", "TOOL_EXECUTION_ERROR")
        if code not in ALLOWED_ERROR_CODES:
            code = "TOOL_EXECUTION_ERROR"
        safe_error = {"code": code, "message": _safe_error_message(code, tool_name)}
        return {
            "data": None,
            "error": safe_error,
            "trace": _trace(
                step,
                stage,
                "error",
                tool_name=tool_name,
                arguments=arguments,
                error_code=code,
                elapsed_ms=_elapsed_ms(started),
            ),
        }

    if isinstance(data, dict) and data.get("success") is False and isinstance(data.get("error"), dict):
        raw_error = data["error"]
        code = raw_error.get("code", "TOOL_EXECUTION_ERROR")
        if code not in ALLOWED_ERROR_CODES:
            code = "TOOL_EXECUTION_ERROR"
        safe_error = {"code": code, "message": _safe_error_message(code, tool_name)}
        return {
            "data": None,
            "error": safe_error,
            "trace": _trace(
                step,
                stage,
                "error",
                tool_name=tool_name,
                arguments=arguments,
                error_code=code,
                elapsed_ms=_elapsed_ms(started),
            ),
        }

    return {
        "data": data,
        "error": None,
        "trace": _trace(
            step,
            stage,
            "completed",
            tool_name=tool_name,
            arguments=arguments,
            result=_trace_result(data),
            elapsed_ms=_elapsed_ms(started),
        ),
    }


def _valid_vehicle_result(result: object) -> bool:
    if not isinstance(result, dict):
        return False
    status = result.get("status")
    registered = result.get("registered")
    return (
        isinstance(result.get("vehicle_number"), str)
        and bool(result["vehicle_number"])
        and status in {"APPROVED", "BLOCKED", "NOT_FOUND"}
        and isinstance(registered, bool)
        and registered is (status != "NOT_FOUND")
    )


def _valid_gate_result(result: object, vehicle_number: str) -> bool:
    return (
        isinstance(result, dict)
        and result.get("success") is True
        and result.get("vehicle_number") == vehicle_number
        and isinstance(result.get("gate_opened"), bool)
        and isinstance(result.get("message"), str)
    )


def _trace_result(data: object) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    return {
        key: data[key]
        for key in ("status", "registered", "gate_opened", "success")
        if key in data
    }


def _trace(
    step: int,
    stage: str,
    status: str,
    *,
    tool_name: str | None = None,
    arguments: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
    elapsed_ms: int | None = None,
) -> dict[str, Any]:
    item = {"step": step, "stage": stage, "status": status}
    optional = {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
        "error_code": error_code,
        "elapsed_ms": elapsed_ms,
    }
    item.update({key: value for key, value in optional.items() if value is not None})
    return item


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _safe_error_message(code: str, tool_name: str) -> str:
    if code == "DATABASE_UNAVAILABLE":
        return "차량 데이터베이스를 사용할 수 없습니다."
    if code == "TOOL_VALIDATION_ERROR":
        return "Tool 입력값이 유효하지 않습니다."
    if code == "TOOL_NOT_ALLOWED":
        return "허용되지 않은 Tool입니다."
    return f"{tool_name} Tool 실행 중 오류가 발생했습니다."


def _tool_error_result(
    vehicle_number: str,
    trace: list[dict[str, Any]],
    error: dict[str, Any],
    registered: bool = False,
    vehicle_status: str | None = None,
) -> dict[str, Any]:
    reason_by_code = {
        "TOOL_NOT_ALLOWED": "tool_not_allowed",
        "TOOL_VALIDATION_ERROR": "tool_validation_error",
        "TOOL_EXECUTION_ERROR": "tool_execution_error",
        "DATABASE_UNAVAILABLE": "database_unavailable",
    }
    return _result(
        success=False,
        vehicle_number=vehicle_number,
        registered=registered,
        vehicle_status=vehicle_status,
        gate_opened=False,
        message=error["message"],
        status="error",
        termination_reason=reason_by_code[error["code"]],
        trace=trace,
        error=error,
    )


def _result(
    *,
    success: bool,
    vehicle_number: str | None,
    registered: bool,
    vehicle_status: str | None,
    gate_opened: bool,
    message: str,
    status: str,
    termination_reason: str,
    trace: list[dict[str, Any]],
    error: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "success": success,
        "vehicle_number": vehicle_number,
        "registered": registered,
        "vehicle_status": vehicle_status,
        "gate_opened": gate_opened,
        "message": message,
        "execution_type": "workflow",
        "status": status,
        "trace": trace,
        "termination_reason": termination_reason,
        "error": error,
    }
