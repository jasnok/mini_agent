"""번호판 이미지 입력을 검증하고 독립 Recognizer에 연결합니다."""

from app.core.config import settings
from app.errors import ImageTooLargeError, RecognitionDependencyError, UnsupportedImageError
from app.recognizers.base import VehicleRecognizer
from app.recognizers.mock import mock_vehicle_recognizer
from app.schemas.parking import VehicleRecognizeResponse


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _matches_signature(content_type: str, content: bytes) -> bool:
    checks = {
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP",
    }
    return checks.get(content_type, False)


def validate_vehicle_image(content_type: str | None, content: bytes) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise UnsupportedImageError("JPEG, PNG, WEBP 이미지만 업로드할 수 있습니다.")
    if not content or not _matches_signature(content_type, content):
        raise UnsupportedImageError("파일 내용과 이미지 형식이 일치하지 않습니다.")
    if len(content) > settings.max_image_size_mb * 1024 * 1024:
        raise ImageTooLargeError(f"이미지는 {settings.max_image_size_mb}MB 이하여야 합니다.")
    return content_type


def recognize_vehicle(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    recognizer: VehicleRecognizer = mock_vehicle_recognizer,
) -> VehicleRecognizeResponse:
    validated_content_type = validate_vehicle_image(content_type, content)
    try:
        vehicle_number = recognizer.recognize(
            filename=filename,
            content_type=validated_content_type,
            content=content,
        )
    except TimeoutError:
        raise
    except Exception as error:
        raise RecognitionDependencyError("번호판 인식기를 호출할 수 없습니다.") from error

    if vehicle_number is None:
        return VehicleRecognizeResponse(
            success=False,
            vehicle_number=None,
            message="차량 번호를 인식하지 못했습니다.",
        )
    return VehicleRecognizeResponse(
        success=True,
        vehicle_number=vehicle_number,
        message="차량 번호를 인식했습니다.",
    )
