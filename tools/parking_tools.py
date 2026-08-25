"""PostgreSQL 차량 조회와 주차장 출입 동작의 공통 Tool입니다."""

from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.repositories.vehicle_repository import vehicle_repository


VEHICLE_NUMBER_PATTERN = re.compile(r"\d{2,3}[가-힣]\d{4}")


class DatabaseUnavailable(RuntimeError):
    code = "DATABASE_UNAVAILABLE"


def _normalize_vehicle_number(vehicle_number: str) -> str:
    normalized = re.sub(r"[\s-]", "", vehicle_number or "")
    if not VEHICLE_NUMBER_PATTERN.fullmatch(normalized):
        error = ValueError("차량 번호 형식이 올바르지 않습니다.")
        error.code = "TOOL_VALIDATION_ERROR"
        raise error
    return normalized


def check_vehicle(vehicle_number: str) -> dict[str, Any]:
    """DB에서 차량을 조회하고 출입 정책용 상태로 변환합니다."""
    normalized = _normalize_vehicle_number(vehicle_number)
    try:
        vehicle = vehicle_repository.find_by_plate(normalized)
    except Exception as error:
        raise DatabaseUnavailable("차량 데이터베이스를 사용할 수 없습니다.") from error

    if vehicle is None:
        return {
            "vehicle_number": normalized,
            "registered": False,
            "status": "NOT_FOUND",
        }

    valid_until = vehicle["valid_until"]
    expired = valid_until is not None and valid_until <= datetime.now(timezone.utc)
    status = "APPROVED" if vehicle["status"] == "active" and not expired else "BLOCKED"
    return {
        "vehicle_number": normalized,
        "registered": True,
        "status": status,
        "valid_until": valid_until.isoformat() if valid_until else None,
        "version": vehicle["version"],
    }


def open_gate(vehicle_number: str) -> dict[str, Any]:
    """승인 완료 후 사용하는 교육용 Gate 개방 Tool입니다."""
    normalized = _normalize_vehicle_number(vehicle_number)
    return {
        "success": True,
        "vehicle_number": normalized,
        "gate_opened": True,
        "message": "등록된 활성 차량으로 확인되어 출입문을 열었습니다.",
    }


def deny_gate(vehicle_number: str, reason: str) -> dict[str, Any]:
    """비활성·만료·미등록 차량의 Gate를 닫힌 상태로 유지합니다."""
    normalized = _normalize_vehicle_number(vehicle_number)
    messages = {
        "BLOCKED": "등록 차량이지만 현재 출입할 수 없습니다.",
        "NOT_FOUND": "등록되지 않은 차량입니다.",
    }
    return {
        "success": True,
        "vehicle_number": normalized,
        "gate_opened": False,
        "message": messages.get(reason, "차량 상태에 따라 출입을 허용하지 않았습니다."),
    }
