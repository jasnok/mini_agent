from fastapi.testclient import TestClient

from app.dependencies import get_parking_agent_runner, get_parking_workflow_runner
from app.errors import IntegrationDependencyError
from app.main import app


client = TestClient(app)


def _result(vehicle_status: str = "APPROVED", execution_type: str = "workflow") -> dict:
    approved = vehicle_status == "APPROVED"
    found = vehicle_status != "NOT_FOUND"
    return {
        "success": True,
        "vehicle_number": "12가3456",
        "registered": found,
        "vehicle_status": vehicle_status,
        "gate_opened": approved,
        "message": "문이 열렸습니다." if approved else "출입할 수 없습니다.",
        "execution_type": execution_type,
        "status": "completed",
        "trace": [],
        "termination_reason": "completed",
        "error": None,
    }


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_workflow_api_uses_common_response_contract() -> None:
    app.dependency_overrides[get_parking_workflow_runner] = lambda: lambda vehicle_number: _result()
    response = client.post("/api/workflow/parking", json={"vehicle_number": "12가3456"})
    assert response.status_code == 200
    assert response.json()["execution_type"] == "workflow"
    assert response.json()["vehicle_status"] == "APPROVED"


def test_agent_requires_message_or_vehicle_number() -> None:
    response = client.post("/api/agent/parking", json={})
    assert response.status_code == 422


def test_agent_api_accepts_message_only() -> None:
    async def runner(message: str, vehicle_number: str | None) -> dict:
        assert message == "입차하고 싶어요"
        assert vehicle_number is None
        return _result("NOT_FOUND", "agent")

    app.dependency_overrides[get_parking_agent_runner] = lambda: runner
    response = client.post("/api/agent/parking", json={"message": "입차하고 싶어요"})
    assert response.status_code == 200
    assert response.json()["execution_type"] == "agent"
    assert response.json()["vehicle_status"] == "NOT_FOUND"
    assert response.json()["success"] is True


def test_invalid_integration_response_returns_502() -> None:
    app.dependency_overrides[get_parking_workflow_runner] = lambda: lambda vehicle_number: {"unexpected": True}
    response = client.post("/api/workflow/parking", json={"vehicle_number": "12가3456"})
    assert response.status_code == 502
    assert "unexpected" not in response.text


def test_missing_external_module_returns_safe_502() -> None:
    def runner(vehicle_number: str) -> dict:
        raise IntegrationDependencyError("sensitive import detail")

    app.dependency_overrides[get_parking_workflow_runner] = lambda: runner
    response = client.post("/api/workflow/parking", json={"vehicle_number": "12가3456"})
    assert response.status_code == 502
    assert "sensitive" not in response.text


def test_agent_timeout_returns_504() -> None:
    async def runner(message: str, vehicle_number: str | None) -> dict:
        raise TimeoutError("provider secret")

    app.dependency_overrides[get_parking_agent_runner] = lambda: runner
    response = client.post("/api/agent/parking", json={"vehicle_number": "12가3456"})
    assert response.status_code == 504
    assert "secret" not in response.text
