from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


PNG = b"\x89PNG\r\n\x1a\n" + b"mock-image"


def test_vehicle_recognition_uses_mock_filename() -> None:
    response = client.post(
        "/api/vehicle/recognize",
        files={"image": ("12가3456.png", PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "vehicle_number": "12가3456",
        "message": "차량 번호를 인식했습니다.",
    }


def test_vehicle_recognition_can_return_not_recognized() -> None:
    response = client.post(
        "/api/vehicle/recognize",
        files={"image": ("unknown.png", PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["vehicle_number"] is None


def test_vehicle_recognition_rejects_unsupported_type() -> None:
    response = client.post(
        "/api/vehicle/recognize",
        files={"image": ("plate.txt", b"not-image", "text/plain")},
    )
    assert response.status_code == 422


def test_vehicle_recognition_rejects_signature_mismatch() -> None:
    response = client.post(
        "/api/vehicle/recognize",
        files={"image": ("12가3456.png", b"not-png", "image/png")},
    )
    assert response.status_code == 422
