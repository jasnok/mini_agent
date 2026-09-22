"""Mini Agent FastAPI 애플리케이션의 기본 동작을 확인하는 스모크 테스트."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["stage"] == "mini_agent_01_llm"


def test_provider_list_does_not_expose_api_keys() -> None:
    response = client.get("/api/providers")

    assert response.status_code == 200
    assert {item["provider"] for item in response.json()["providers"]} == {
        "mock",
        "openai",
        "gemini",
        "ollama",
    }
    assert "api_key" not in response.text.lower()


def test_mock_provider_generates_without_external_api() -> None:
    response = client.post(
        "/api/generate",
        json={"provider": "mock", "message": "부산 여행을 추천해 주세요."},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert response.json()["content"]


def test_travel_classifier_requests_missing_destination() -> None:
    response = client.post(
        "/api/travel/classify",
        json={"message": "여행을 준비해 줘."},
    )

    assert response.status_code == 200
    assert response.json()["next_action"] == "ask_user"
    assert "destination" in response.json()["missing_information"]


def test_unknown_endpoint_returns_not_found() -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
