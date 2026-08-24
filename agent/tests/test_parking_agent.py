import asyncio

from agent.parking_agent import run_parking_agent
from agent.providers.mock import MockAgentProvider

from .fakes import FakeToolExecutor


def run(coro):
    return asyncio.run(coro)


def test_missing_vehicle_number_needs_clarification():
    result = run(run_parking_agent("차량이 들어가려고 합니다."))

    assert result["status"] == "needs_clarification"
    assert result["termination_reason"] == "needs_clarification"
    assert result["vehicle_number"] is None


def test_explicit_vehicle_number_has_priority():
    executor = FakeToolExecutor("APPROVED")
    result = run(
        run_parking_agent(
            "99가9999 차량입니다.",
            "12가3456",
            provider=MockAgentProvider(),
            tool_executor=executor,
        )
    )

    assert result["vehicle_number"] == "12가3456"
    assert [name for name, _ in executor.calls] == ["check_vehicle", "open_gate"]


def test_approved_vehicle_opens_gate():
    executor = FakeToolExecutor("APPROVED")
    result = run(
        run_parking_agent(
            "12가3456 차량이 들어갑니다.",
            provider=MockAgentProvider(),
            tool_executor=executor,
        )
    )

    assert result["success"] is True
    assert result["vehicle_status"] == "APPROVED"
    assert result["gate_opened"] is True
    assert [name for name, _ in executor.calls] == ["check_vehicle", "open_gate"]


def test_blocked_and_not_found_use_deny_gate():
    for status in ("BLOCKED", "NOT_FOUND"):
        executor = FakeToolExecutor(status)
        result = run(
            run_parking_agent(
                "56다7890 차량입니다.",
                provider=MockAgentProvider(),
                tool_executor=executor,
            )
        )

        assert result["success"] is True
        assert result["vehicle_status"] == status
        assert result["gate_opened"] is False
        assert [name for name, _ in executor.calls] == ["check_vehicle", "deny_gate"]
        assert executor.calls[-1][1]["reason"] == status


def test_database_error_never_calls_gate_tool():
    executor = FakeToolExecutor(failure_code="DATABASE_UNAVAILABLE")
    result = run(
        run_parking_agent(
            "12가3456 차량입니다.",
            provider=MockAgentProvider(),
            tool_executor=executor,
        )
    )

    assert result["success"] is False
    assert result["termination_reason"] == "database_unavailable"
    assert [name for name, _ in executor.calls] == ["check_vehicle"]
