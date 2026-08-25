import asyncio

from agent.errors import ProviderTimeoutError
from agent.models import ToolCall
from agent.parking_agent import run_parking_agent

from .fakes import FakeToolExecutor, ScriptedProvider


def run(coro):
    return asyncio.run(coro)


def test_gate_before_vehicle_check_is_rejected():
    executor = FakeToolExecutor()
    provider = ScriptedProvider(
        [ToolCall(name="open_gate", arguments={"vehicle_number": "12가3456"})]
    )

    result = run(
        run_parking_agent(
            "12가3456",
            provider=provider,
            tool_executor=executor,
        )
    )

    assert result["status"] == "rejected"
    assert result["termination_reason"] == "policy_rejected"
    assert executor.calls == []


def test_wrong_gate_for_blocked_vehicle_is_rejected():
    executor = FakeToolExecutor("BLOCKED")
    provider = ScriptedProvider(
        [
            ToolCall(name="check_vehicle", arguments={"vehicle_number": "56다7890"}),
            ToolCall(name="open_gate", arguments={"vehicle_number": "56다7890"}),
        ]
    )

    result = run(
        run_parking_agent(
            "56다7890",
            provider=provider,
            tool_executor=executor,
        )
    )

    assert result["termination_reason"] == "policy_rejected"
    assert [name for name, _ in executor.calls] == ["check_vehicle"]


def test_repeated_call_is_stopped_before_second_execution():
    executor = FakeToolExecutor("APPROVED")
    repeated = ToolCall(name="check_vehicle", arguments={"vehicle_number": "12가3456"})
    provider = ScriptedProvider([repeated, repeated])

    result = run(
        run_parking_agent(
            "12가3456",
            provider=provider,
            tool_executor=executor,
        )
    )

    assert result["termination_reason"] == "repeated_tool_call"
    assert len(executor.calls) == 1


def test_trace_contains_order_and_termination_reason():
    executor = FakeToolExecutor("APPROVED")
    result = run(
        run_parking_agent(
            "12가3456",
            tool_executor=executor,
        )
    )

    stages = [item["stage"] for item in result["trace"]]
    assert stages[0] == "input_validation"
    assert stages[-1] == "terminated"
    assert result["trace"][-1]["result"]["termination_reason"] == "completed"


def test_provider_timeout_never_executes_a_tool():
    class TimeoutProvider:
        name = "timeout"
        model = "test"

        async def choose_tool(self, **kwargs):
            del kwargs
            raise ProviderTimeoutError("LLM 응답 시간이 초과되었습니다.")

    executor = FakeToolExecutor("APPROVED")
    result = run(
        run_parking_agent(
            "12가3456",
            provider=TimeoutProvider(),
            tool_executor=executor,
        )
    )

    assert result["termination_reason"] == "provider_timeout"
    assert result["gate_opened"] is False
    assert executor.calls == []


def test_inconsistent_open_gate_result_is_an_error():
    class ClosedGateExecutor(FakeToolExecutor):
        async def execute(self, name, arguments):
            result = await super().execute(name, arguments)
            if name == "open_gate":
                result.data["gate_opened"] = False
            return result

    executor = ClosedGateExecutor("APPROVED")
    result = run(
        run_parking_agent(
            "12가3456",
            tool_executor=executor,
        )
    )

    assert result["success"] is False
    assert result["termination_reason"] == "tool_execution_error"
    assert result["gate_opened"] is False
