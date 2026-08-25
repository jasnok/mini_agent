"""다른 담당 모듈의 공개 실행 함수를 Backend Router에 연결합니다."""

from collections.abc import Awaitable, Callable
from typing import Any

from app.errors import IntegrationDependencyError


WorkflowRunner = Callable[[str], dict[str, Any]]
AgentRunner = Callable[[str, str | None], Awaitable[dict[str, Any]]]


def _run_parking_workflow(vehicle_number: str) -> dict[str, Any]:
    try:
        from workflow.parking_workflow import run_parking_workflow
    except ImportError as error:
        raise IntegrationDependencyError("Parking Workflow가 아직 연결되지 않았습니다.") from error
    return run_parking_workflow(vehicle_number)


async def _run_parking_agent(message: str, vehicle_number: str | None) -> dict[str, Any]:
    try:
        from agent.parking_agent import run_parking_agent
    except ImportError as error:
        raise IntegrationDependencyError("Parking Agent가 아직 연결되지 않았습니다.") from error
    return await run_parking_agent(message=message, vehicle_number=vehicle_number)


def get_parking_workflow_runner() -> WorkflowRunner:
    return _run_parking_workflow


def get_parking_agent_runner() -> AgentRunner:
    return _run_parking_agent
