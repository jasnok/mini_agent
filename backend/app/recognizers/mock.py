"""외부 OCR 없이 결정적으로 실습할 수 있는 교육용 번호판 인식기입니다."""

import re


VEHICLE_NUMBER_PATTERN = re.compile(r"\d{2,3}[가-힣]\d{4}")


class MockVehicleRecognizer:
    """파일명에 포함된 차량 번호만 읽으며 이미지 내용을 추측하지 않습니다."""

    def recognize(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> str | None:
        del content_type, content
        match = VEHICLE_NUMBER_PATTERN.search(filename)
        return match.group(0) if match else None


mock_vehicle_recognizer = MockVehicleRecognizer()
