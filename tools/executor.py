"""주차 Agent가 호출할 수 있는 공통 Tool allowlist 실행기입니다."""

from typing import Any, Callable

from tools.parking_tools import check_vehicle, deny_gate, open_gate


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "check_vehicle": check_vehicle,
    "open_gate": open_gate,
    "deny_gate": deny_gate,
}


def _vehicle_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"vehicle_number": {"type": "string"}},
        "required": ["vehicle_number"],
        "additionalProperties": False,
    }


def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "check_vehicle",
            "description": "차량번호를 DB에서 조회하여 APPROVED, BLOCKED, NOT_FOUND 상태를 반환합니다.",
            "input_schema": _vehicle_schema(),
        },
        {
            "name": "open_gate",
            "description": "APPROVED 차량의 출입문을 엽니다.",
            "input_schema": _vehicle_schema(),
        },
        {
            "name": "deny_gate",
            "description": "BLOCKED 또는 NOT_FOUND 차량의 출입을 거절합니다.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "vehicle_number": {"type": "string"},
                    "reason": {"type": "string", "enum": ["BLOCKED", "NOT_FOUND"]},
                },
                "required": ["vehicle_number", "reason"],
                "additionalProperties": False,
            },
        },
    ]


def execute_tool_safely(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        return {
            "success": False,
            "tool_name": name,
            "error_code": "TOOL_NOT_ALLOWED",
            "message": "허용되지 않은 Tool입니다.",
        }
    try:
        data = tool(**arguments)
        return {"success": True, "tool_name": name, "data": data, "message": data.get("message", "")}
    except TypeError:
        return {
            "success": False,
            "tool_name": name,
            "error_code": "TOOL_VALIDATION_ERROR",
            "message": "Tool 입력값이 올바르지 않습니다.",
        }
    except Exception as error:
        code = getattr(error, "code", "TOOL_EXECUTION_ERROR")
        return {
            "success": False,
            "tool_name": name,
            "error_code": code,
            "message": "차량 정보를 처리하지 못했습니다.",
        }
