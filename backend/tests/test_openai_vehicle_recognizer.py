from types import SimpleNamespace

from app.recognizers.openai_vision import (
    OpenAIVehicleRecognizer,
    VehicleRecognitionResult,
    normalize_vehicle_number,
)


class FakeResponses:
    def __init__(self, result: VehicleRecognitionResult) -> None:
        self.result = result
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.result)


def test_openai_recognizer_sends_image_and_normalizes_number() -> None:
    responses = FakeResponses(
        VehicleRecognitionResult(recognized=True, vehicle_number="34 나-7890")
    )
    recognizer = OpenAIVehicleRecognizer(SimpleNamespace(responses=responses))

    result = recognizer.recognize(
        filename="camera.png",
        content_type="image/png",
        content=b"image-bytes",
    )

    assert result == "34나7890"
    image = responses.kwargs["input"][0]["content"][1]
    assert image["type"] == "input_image"
    assert image["image_url"].startswith("data:image/png;base64,")
    assert responses.kwargs["store"] is False


def test_openai_recognizer_returns_none_when_not_recognized() -> None:
    responses = FakeResponses(
        VehicleRecognitionResult(recognized=False, vehicle_number=None)
    )
    recognizer = OpenAIVehicleRecognizer(SimpleNamespace(responses=responses))

    assert recognizer.recognize(
        filename="camera.png",
        content_type="image/png",
        content=b"image-bytes",
    ) is None


def test_normalize_vehicle_number_rejects_invalid_text() -> None:
    assert normalize_vehicle_number("34 나-7890") == "34나7890"
    assert normalize_vehicle_number("번호는 34나7890입니다") is None
    assert normalize_vehicle_number("1234") is None
