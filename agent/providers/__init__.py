"""Provider factory for the parking agent."""

from __future__ import annotations

import os

from ..errors import AgentConfigurationError
from .mock import MockAgentProvider
from .openai import OpenAIAgentProvider


def get_default_provider():
    provider_name = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider_name == "mock":
        return MockAgentProvider()
    if provider_name == "openai":
        return OpenAIAgentProvider()
    raise AgentConfigurationError(f"지원하지 않는 LLM Provider입니다: {provider_name}")


__all__ = ["get_default_provider", "MockAgentProvider", "OpenAIAgentProvider"]
