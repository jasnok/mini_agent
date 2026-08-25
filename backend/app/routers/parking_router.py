"""Parking Workflow와 Agent를 공통 HTTP 계약으로 연결합니다."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.dependencies import (
    AgentRunner,
    WorkflowRunner,
    get_parking_agent_runner,
    get_parking_workflow_runner,
)
from app.errors import IntegrationDependencyError, IntegrationTimeoutError
from app.schemas.parking import (
    ParkingAgentRequest,
    ParkingExecutionResponse,
    ParkingWorkflowRequest,
)


parking_router = APIRouter(tags=["주차장 · 실행"])


def _validated_result(result: dict[str, Any], execution_type: str) -> ParkingExecutionResponse:
    response = ParkingExecutionResponse.model_validate(result)
    if response.execution_type != execution_type:
        raise ValueError("실행 결과의 execution_type이 호출한 API와 일치하지 않습니다.")
    return response


def _dependency_error(error: Exception) -> HTTPException:
    if isinstance(error, (TimeoutError, IntegrationTimeoutError)):
        return HTTPException(status_code=504, detail="외부 처리 시간이 초과되었습니다.")
    if isinstance(error, IntegrationDependencyError):
        return HTTPException(status_code=502, detail="필요한 실행 서비스를 사용할 수 없습니다.")
    return HTTPException(status_code=500, detail="주차장 요청 처리 중 내부 오류가 발생했습니다.")


@parking_router.post("/api/workflow/parking", response_model=ParkingExecutionResponse)
def execute_parking_workflow(
    payload: ParkingWorkflowRequest,
    runner: WorkflowRunner = Depends(get_parking_workflow_runner),
) -> ParkingExecutionResponse:
    try:
        return _validated_result(runner(payload.vehicle_number), "workflow")
    except (ValidationError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Workflow가 올바른 결과를 반환하지 않았습니다.") from error
    except Exception as error:
        raise _dependency_error(error) from error


@parking_router.post("/api/agent/parking", response_model=ParkingExecutionResponse)
async def execute_parking_agent(
    payload: ParkingAgentRequest,
    runner: AgentRunner = Depends(get_parking_agent_runner),
) -> ParkingExecutionResponse:
    try:
        result = await runner(payload.message or "", payload.vehicle_number)
        return _validated_result(result, "agent")
    except (ValidationError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Agent가 올바른 결과를 반환하지 않았습니다.") from error
    except Exception as error:
        raise _dependency_error(error) from error
