"""Deterministic backend safety policy for LLM-proposed tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import AgentContext, ToolCall


ALLOWED_TOOLS = frozenset({"check_vehicle", "open_gate", "deny_gate"})


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""


def validate_tool_call(call: ToolCall, context: AgentContext) -> PolicyDecision:
    if call.name not in ALLOWED_TOOLS:
        return PolicyDecision(False, "허용되지 않은 Tool입니다.")

    if call.arguments.get("vehicle_number") != context.vehicle_number:
        return PolicyDecision(False, "조회 차량과 Tool 대상 차량이 일치하지 않습니다.")

    if call.name == "check_vehicle":
        if context.vehicle_checked:
            return PolicyDecision(False, "차량 조회가 이미 완료되었습니다.")
        return PolicyDecision(True)

    if not context.vehicle_checked or context.vehicle_status is None:
        return PolicyDecision(False, "Gate Tool 전에 차량 조회가 필요합니다.")

    if context.gate_action is not None:
        return PolicyDecision(False, "한 요청에서는 Gate Tool을 한 번만 실행할 수 있습니다.")

    if call.name == "open_gate":
        if context.vehicle_status != "APPROVED":
            return PolicyDecision(False, "APPROVED 차량만 문을 열 수 있습니다.")
        return PolicyDecision(True)

    reason = call.arguments.get("reason")
    if context.vehicle_status not in {"BLOCKED", "NOT_FOUND"}:
        return PolicyDecision(False, "승인 차량에 deny_gate를 실행할 수 없습니다.")
    if reason != context.vehicle_status:
        return PolicyDecision(False, "거부 사유가 차량 조회 상태와 일치하지 않습니다.")
    return PolicyDecision(True)


def repeated_call_key(call: ToolCall) -> tuple[str, str]:
    normalized = repr(sorted((key, _stable_value(value)) for key, value in call.arguments.items()))
    return call.name, normalized


def _stable_value(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _stable_value(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_stable_value(item) for item in value)
    return value
