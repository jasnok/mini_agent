"""Backend의 공개 HTTP 경계에서 사용하는 안전한 예외입니다."""


class BackendServiceError(Exception):
    """클라이언트에 내부 원문을 노출하지 않아야 하는 Service 오류입니다."""


class UnsupportedImageError(BackendServiceError):
    """이미지 형식 또는 실제 파일 내용이 지원되지 않습니다."""


class ImageTooLargeError(BackendServiceError):
    """업로드 이미지가 설정된 크기 제한을 초과했습니다."""


class RecognitionDependencyError(BackendServiceError):
    """번호판 인식 의존성을 정상적으로 호출할 수 없습니다."""


class IntegrationDependencyError(BackendServiceError):
    """Workflow 또는 Agent 통합 의존성을 호출할 수 없습니다."""


class IntegrationTimeoutError(BackendServiceError):
    """외부 Workflow, Agent 또는 Provider 처리가 제한 시간을 초과했습니다."""


class InvalidIntegrationResponseError(BackendServiceError):
    """외부 담당 모듈이 공통 계약과 다른 결과를 반환했습니다."""
