"""Shared helpers for provider implementations."""

from __future__ import annotations

from typing import Any


def openai_tool_definitions(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for tool in tools:
        schema = tool.get("input_schema", tool.get("parameters", {}))
        definitions.append(
            {
                "type": "function",
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": schema,
            }
        )
    return definitions
