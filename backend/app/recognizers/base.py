"""교체 가능한 번호판 인식기의 최소 인터페이스입니다."""

from typing import Protocol


class VehicleRecognizer(Protocol):
    def recognize(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> str | None:
        """인식한 차량 번호를 반환하고, 인식하지 못하면 None을 반환합니다."""
