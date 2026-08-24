"""팀 통합 계약의 주차장 Backend API Client."""

from typing import Any, Literal

from core.api_client import request, upload


Mode = Literal["workflow", "agent"]


def recognize_vehicle(filename: str, content: bytes, content_type: str) -> dict[str, Any]:
    return upload("/api/vehicle/recognize", {"image": (filename, content, content_type)}, {})


def execute_parking(mode: Mode, vehicle_number: str) -> dict[str, Any]:
    if mode == "workflow":
        return request("POST", "/api/workflow/parking", json={"vehicle_number": vehicle_number})
    return request("POST", "/api/agent/parking", json={
        "message": f"{vehicle_number} 차량이 들어가려고 합니다.",
        "vehicle_number": vehicle_number,
    })
