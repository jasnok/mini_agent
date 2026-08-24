"""Pydantic models owned by the parking agent boundary."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


VehicleStatus = Literal["APPROVED", "BLOCKED", "NOT_FOUND"]
AgentStatus = Literal["completed", "needs_clarification", "rejected", "error"]


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    success: bool
    tool_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str = ""


class AgentErrorInfo(BaseModel):
    code: str
    message: str


class TraceItem(BaseModel):
    step: int
    stage: str
    status: str
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    elapsed_ms: int = 0


class ParkingAgentResult(BaseModel):
    success: bool
    vehicle_number: str | None
    registered: bool
    vehicle_status: VehicleStatus | None
    gate_opened: bool
    message: str
    execution_type: Literal["agent"] = "agent"
    status: AgentStatus
    trace: list[TraceItem] = Field(default_factory=list)
    termination_reason: str
    error: AgentErrorInfo | None = None


class AgentContext(BaseModel):
    vehicle_number: str
    vehicle_checked: bool = False
    registered: bool = False
    vehicle_status: VehicleStatus | None = None
    gate_action: Literal["open_gate", "deny_gate"] | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
