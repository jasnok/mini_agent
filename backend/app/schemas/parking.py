"""주차장 팀 통합 API의 요청·응답 Pydantic 계약입니다."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


VehicleStatus = Literal["APPROVED", "BLOCKED", "NOT_FOUND"]
ExecutionType = Literal["workflow", "agent"]
ParkingStatus = Literal["completed", "needs_clarification", "rejected", "error"]
TerminationReason = Literal[
    "completed",
    "needs_clarification",
    "tool_not_allowed",
    "tool_validation_error",
    "tool_execution_error",
    "database_unavailable",
    "provider_timeout",
    "provider_error",
    "invalid_provider_response",
    "repeated_tool_call",
    "max_steps_exceeded",
    "policy_rejected",
]


class ParkingWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_number: str = Field(min_length=1, max_length=32)


class ParkingAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str | None = Field(default=None, max_length=2000)
    vehicle_number: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def require_message_or_vehicle_number(self) -> "ParkingAgentRequest":
        if not (self.message and self.message.strip()) and not (
            self.vehicle_number and self.vehicle_number.strip()
        ):
            raise ValueError("message와 vehicle_number 중 하나 이상이 필요합니다.")
        return self


class ParkingError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ParkingTraceItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int = Field(ge=1)
    stage: str = Field(min_length=1)
    status: str = Field(min_length=1)
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    elapsed_ms: int | None = Field(default=None, ge=0)


class ParkingExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    vehicle_number: str | None = None
    registered: bool = False
    vehicle_status: VehicleStatus | None = None
    gate_opened: bool = False
    message: str = Field(min_length=1)
    execution_type: ExecutionType
    status: ParkingStatus
    trace: list[ParkingTraceItem] = Field(default_factory=list)
    termination_reason: TerminationReason
    error: ParkingError | None = None

    @model_validator(mode="after")
    def validate_result_semantics(self) -> "ParkingExecutionResponse":
        if self.status == "error" and self.success:
            raise ValueError("error 상태는 success=false여야 합니다.")
        if not self.success and self.error is None:
            raise ValueError("success=false 결과에는 error가 필요합니다.")
        if self.vehicle_status == "APPROVED" and self.registered is False:
            raise ValueError("APPROVED 차량은 registered=true여야 합니다.")
        if self.vehicle_status == "NOT_FOUND" and self.registered:
            raise ValueError("NOT_FOUND 차량은 registered=false여야 합니다.")
        if self.gate_opened and self.vehicle_status != "APPROVED":
            raise ValueError("APPROVED 차량만 gate_opened=true일 수 있습니다.")
        return self


class VehicleRecognizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    vehicle_number: str | None = None
    message: str = Field(min_length=1)
