from fastapi.testclient import TestClient

from app.main import app
from app.schemas import TravelImageAnalysis, VoiceTranslationResult
from app.services.media_service import (
    AudioTooLargeError,
    UnsupportedAudioTypeError,
    validate_audio,
)


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["stage"] == "mini_agent_01_llm"


def test_provider_list_does_not_expose_keys() -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200
    body = response.json()
    assert {item["provider"] for item in body["providers"]} == {
        "mock",
        "openai",
        "gemini",
        "ollama",
    }
    assert "api_key" not in response.text.lower()


def test_concept_compare_shows_rule_and_semantic_difference() -> None:
    response = client.post(
        "/api/concepts/compare",
        json={"message": "내일 비가 올까요?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow"]["route"] == "general"
    assert body["semantic_router"]["route"] == "weather"


def test_travel_classifier_asks_for_missing_destination() -> None:
    response = client.post(
        "/api/travel/classify",
        json={"message": "여행을 준비해 줘."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "travel_plan"
    assert body["next_action"] == "ask_user"
    assert "destination" in body["missing_information"]


def test_low_confidence_requests_clarification() -> None:
    response = client.post(
        "/api/travel/classify",
        json={"message": "도와주세요."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "needs_clarification"
    assert body["next_action"] == "ask_user"


def test_mock_provider_generate() -> None:
    response = client.post(
        "/api/generate",
        json={"provider": "mock", "message": "부산 여행"},
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"


def test_provider_compare_preserves_each_result() -> None:
    response = client.post(
        "/api/providers/compare",
        json={"providers": ["mock"], "message": "부산 여행"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] == 1
    assert body["results"][0]["status"] == "success"


def test_missing_openai_key_is_explicit() -> None:
    response = client.post(
        "/api/generate",
        json={"provider": "openai", "message": "부산 여행을 추천해 주세요."},
    )
    if response.status_code == 200:
        return
    assert response.status_code == 422
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_image_analysis_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.routers.media_router.analyze_image",
        lambda *_: TravelImageAnalysis(
            scene_type="landmark",
            summary="부산의 해변입니다.",
            travel_tips=["운영 시간을 확인하세요."],
        ),
    )
    response = client.post(
        "/api/media/image-analysis",
        files={"image": ("travel.png", b"fake", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["scene_type"] == "landmark"


def test_tts_marks_synthetic_audio(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.media_router.create_speech", lambda *_: b"mp3")
    response = client.post("/api/media/tts", json={"text": "안녕하세요.", "voice": "coral"})
    assert response.status_code == 200
    assert response.headers["x-synthetic-voice"] == "true"


def test_voice_translation_returns_text_and_audio(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.routers.media_router.translate_voice",
        lambda *_: VoiceTranslationResult(
            transcript="안녕하세요.",
            translation="Hello.",
            audio_base64="bXAz",
        ),
    )
    response = client.post(
        "/api/media/voice-translation",
        files={"audio": ("recording.wav", b"RIFFfakeWAVE", "audio/wav")},
        data={"source_language": "ko", "target_language": "en", "voice": "coral"},
    )
    assert response.status_code == 200
    assert response.json()["transcript"] == "안녕하세요."
    assert response.json()["translation"] == "Hello."
    assert response.json()["synthetic_voice"] is True


def test_voice_translation_rejects_unsupported_language() -> None:
    response = client.post(
        "/api/media/voice-translation",
        files={"audio": ("recording.wav", b"RIFFfakeWAVE", "audio/wav")},
        data={"source_language": "en", "target_language": "ko"},
    )
    assert response.status_code == 422


def test_voice_translation_maps_unsupported_media_type(monkeypatch) -> None:
    def reject(*_):
        raise UnsupportedAudioTypeError("지원하지 않는 형식")

    monkeypatch.setattr("app.routers.media_router.translate_voice", reject)
    response = client.post(
        "/api/media/voice-translation",
        files={"audio": ("recording.txt", b"text", "text/plain")},
    )
    assert response.status_code == 415


def test_voice_translation_maps_too_large(monkeypatch) -> None:
    def reject(*_):
        raise AudioTooLargeError("너무 큰 파일")

    monkeypatch.setattr("app.routers.media_router.translate_voice", reject)
    response = client.post(
        "/api/media/voice-translation",
        files={"audio": ("recording.wav", b"RIFFfakeWAVE", "audio/wav")},
    )
    assert response.status_code == 413


def test_validate_audio_accepts_wav_header() -> None:
    validate_audio("audio/wav", b"RIFF\x00\x00\x00\x00WAVEdata")


def test_validate_audio_rejects_mismatched_signature() -> None:
    try:
        validate_audio("audio/wav", b"not-a-wave")
    except UnsupportedAudioTypeError:
        return
    raise AssertionError("파일 시그니처 불일치를 거부해야 합니다.")


def test_video_app_is_served() -> None:
    response = client.get("/video/")
    assert response.status_code == 200
    assert "영상 속 한 장면" in response.text
