"""OpenAI Responses API adapter for parking tool selection."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from ..errors import (
    AgentConfigurationError,
    InvalidProviderResponseError,
    ProviderError,
    ProviderTimeoutError,
)
from ..models import AgentContext, ToolCall
from .base import openai_tool_definitions


class OpenAIAgentProvider:
    name = "openai"

    def __init__(self) -> None:
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise AgentConfigurationError("OPENAI_API_KEY가 설정되지 않았습니다.")
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise AgentConfigurationError("openai 패키지가 설치되지 않았습니다.") from exc
        self._client = AsyncOpenAI(api_key=api_key, timeout=self.timeout_seconds)

    async def choose_tool(
        self,
        *,
        message: str,
        system_prompt: str,
        tools: list[dict[str, Any]],
        context: AgentContext,
    ) -> ToolCall:
        context_text = context.model_dump_json(exclude={"tool_results"})
        prompt = f"사용자 요청: {message}\n현재 검증 상태: {context_text}"
        try:
            response = await asyncio.wait_for(
                self._client.responses.create(
                    model=self.model,
                    instructions=system_prompt,
                    input=prompt,
                    tools=openai_tool_definitions(tools),
                    tool_choice="required",
                ),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError("LLM 응답 시간이 초과되었습니다.") from exc
        except Exception as exc:
            raise ProviderError("LLM Provider 호출에 실패했습니다.") from exc

        tool_call = next(
            (item for item in response.output if getattr(item, "type", None) == "function_call"),
            None,
        )
        if tool_call is None:
            raise InvalidProviderResponseError("LLM이 Tool Call을 반환하지 않았습니다.")
        try:
            arguments = json.loads(tool_call.arguments)
            return ToolCall(name=tool_call.name, arguments=arguments)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise InvalidProviderResponseError("LLM Tool Call 형식이 올바르지 않습니다.") from exc
