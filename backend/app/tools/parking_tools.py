from typing import Any

from app.repositories.vehicle_repository import vehicle_repository
from backend.app.repositories import lab_repository

def lookup_vehicle(plate_number: str) -> dict:
    """차량 등록 사실만 조회하는 읽기 전용 Tool입니다."""
    vehicle = vehicle_repository.find_by_plate(plate_number)

    return {
        "plate_number": plate_number,
        "registered": vehicle is not None,
        "status": vehicle.status if vehicle else None,
        "valid_until": vehicle.valid_until if vehicle else None,
        "version": vehicle.version if vehicle else None,
    }

def parking_entry(plate_number: str) -> dict[str, Any]:
    """Workflow가 승인과 사용자 확인을 끝낸 뒤 호출하는 게이트 상태 변경 Tool입니다."""
    vehicle = lab_repository.vehicles.get(plate_number)
    if vehicle is None: return {"opened": False, "reason": "등록되지 않은 차량입니다."}
    if not vehicle["active"]: return {"opened": False, "reason": "출입 권한이 비활성 상태입니다."}
    lab_repository.gate_open = True
    return {"opened": True, "plate_number": plate_number}