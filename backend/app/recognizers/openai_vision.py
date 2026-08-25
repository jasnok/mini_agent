"""OpenAI Vision으로 이미지 내용에서 한국 차량번호를 인식합니다."""

import base64
import re
from typing import Any

from openai import APITimeoutError, OpenAI
from pydantic import BaseModel, ConfigDict

from app.core.config import settings


VEHICLE_NUMBER_PATTERN = re.compile(r"\d{2,3}[가-힣]\d{4}")


class VehicleRecognitionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recognized: bool
    vehicle_number: str | None


def normalize_vehicle_number(value: str | None) -> str | None:
    """공백·구분자를 제거하고 지원하는 한국 차량번호 형식만 반환합니다."""
    if not value:
        return None
    normalized = re.sub(r"[\s-]", "", value)
    return normalized if VEHICLE_NUMBER_PATTERN.fullmatch(normalized) else None


class OpenAIVehicleRecognizer:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def recognize(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> str | None:
        del filename
        if self._client is None and not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

        encoded = base64.b64encode(content).decode("ascii")
        image_url = f"data:{content_type};base64,{encoded}"
        client = self._client or OpenAI(api_key=settings.openai_api_key)

        try:
            response = client.responses.parse(
                model=settings.openai_vision_model,
                instructions=(
                    "이미지에서 한국 차량번호를 판독하는 인식기입니다. "
                    "실제 번호판뿐 아니라 교육용 시연에서 종이나 화면에 손으로 쓴 차량번호도 판독하세요. "
                    "숫자 2~3자리, 한글 1자, 숫자 4자리 형식의 단일 후보가 보이면 recognized=true로 답하세요. "
                    "공백과 하이픈을 제외한 번호만 반환하세요. 해당 형식의 후보가 없거나 여러 개면 "
                    "recognized=false, vehicle_number=null로 답하세요. 보이지 않는 문자를 새로 만들어내지 마세요."
                ),
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "이 사진에서 한국 차량번호 하나를 정확히 판독하세요.",
                            },
                            {
                                "type": "input_image",
                                "image_url": image_url,
                                "detail": "high",
                            },
                        ],
                    }
                ],
                text_format=VehicleRecognitionResult,
                max_output_tokens=100,
                store=False,
                timeout=settings.request_timeout_seconds,
            )
        except APITimeoutError as error:
            raise TimeoutError("OpenAI 번호판 인식 시간이 초과되었습니다.") from error

        result = response.output_parsed
        if result is None or not result.recognized:
            return None
        return normalize_vehicle_number(result.vehicle_number)


openai_vehicle_recognizer = OpenAIVehicleRecognizer()
