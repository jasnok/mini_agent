"""팀 통합 계약과 동일한 형태의 Backend 응답 fixture."""

from copy import deepcopy
from typing import Any, Literal


Mode = Literal["workflow", "agent"]

MOCK_SCENARIOS: dict[str, dict[str, Any] | None] = {
    "등록 차량 · 12가3456": {"success": True, "vehicle_number": "12가3456", "registered": True, "vehicle_status": "APPROVED", "gate_opened": True, "message": "문이 열렸습니다."},
    "등록 차량 · 34나5678": {"success": True, "vehicle_number": "34나5678", "registered": True, "vehicle_status": "APPROVED", "gate_opened": True, "message": "문이 열렸습니다."},
    "차단 차량 · 56다7890": {"success": True, "vehicle_number": "56다7890", "registered": True, "vehicle_status": "BLOCKED", "gate_opened": False, "message": "차단 차량은 출입할 수 없습니다."},
    "미등록 차량 · 99가9999": {"success": True, "vehicle_number": "99가9999", "registered": False, "vehicle_status": "NOT_FOUND", "gate_opened": False, "message": "등록되지 않은 차량입니다."},
    "번호판 인식 실패": {"success": False, "vehicle_number": None, "registered": False, "vehicle_status": None, "gate_opened": False, "message": "번호판을 인식하지 못했습니다.", "status": "error", "termination_reason": "tool_execution_error", "error": {"code": "RECOGNITION_FAILED", "message": "번호판을 인식하지 못했습니다."}},
    "DB 연결 오류": {"success": False, "vehicle_number": "12가3456", "registered": False, "vehicle_status": None, "gate_opened": False, "message": "차량 조회 중 오류가 발생했습니다.", "status": "error", "termination_reason": "database_unavailable", "error": {"code": "DATABASE_UNAVAILABLE", "message": "차량 조회 중 오류가 발생했습니다."}},
    "네트워크 오류": None,
}


def _trace(vehicle_number: str | None, vehicle_status: str | None, mode: Mode) -> list[dict[str, Any]]:
    if vehicle_number is None:
        return [{"step": 1, "stage": "input_validation", "status": "error", "error_code": "RECOGNITION_FAILED", "elapsed_ms": 8}]
    return [
        {"step": 1, "stage": "input_validation", "status": "completed", "elapsed_ms": 1},
        {"step": 2, "stage": "vehicle_check", "status": "completed", "tool_name": "check_vehicle", "arguments": {"vehicle_number": vehicle_number}, "result": {"status": vehicle_status}, "error_code": None, "elapsed_ms": 15},
        {"step": 3, "stage": "policy_decision" if mode == "workflow" else "tool_selection", "status": "completed", "elapsed_ms": 12},
        {"step": 4, "stage": "final_answer", "status": "completed", "elapsed_ms": 2},
    ]


def get_mock_response(scenario: str, mode: Mode) -> dict[str, Any]:
    response = MOCK_SCENARIOS[scenario]
    if response is None:
        raise ConnectionError("Backend 서버에 연결할 수 없습니다.")
    result = deepcopy(response)
    result.setdefault("status", "completed")
    result.setdefault("termination_reason", "completed")
    result.setdefault("error", None)
    result["execution_type"] = mode
    result["trace"] = _trace(result["vehicle_number"], result["vehicle_status"], mode)
    if (result.get("error") or {}).get("code") == "DATABASE_UNAVAILABLE":
        result["trace"] = [{"step": 1, "stage": "vehicle_check", "status": "error", "tool_name": "check_vehicle", "error_code": "DATABASE_UNAVAILABLE", "elapsed_ms": 5000}]
    return result
