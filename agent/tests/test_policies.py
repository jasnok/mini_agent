from agent.models import AgentContext, ToolCall
from agent.policies import validate_tool_call


def test_unknown_tool_is_rejected():
    context = AgentContext(vehicle_number="12가3456")
    decision = validate_tool_call(
        ToolCall(name="delete_vehicle", arguments={"vehicle_number": "12가3456"}),
        context,
    )
    assert decision.allowed is False


def test_deny_reason_must_match_vehicle_status():
    context = AgentContext(
        vehicle_number="56다7890",
        vehicle_checked=True,
        registered=True,
        vehicle_status="BLOCKED",
    )
    decision = validate_tool_call(
        ToolCall(
            name="deny_gate",
            arguments={"vehicle_number": "56다7890", "reason": "NOT_FOUND"},
        ),
        context,
    )
    assert decision.allowed is False
