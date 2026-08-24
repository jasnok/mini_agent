"""Internal exceptions used to classify safe agent failures."""


class AgentError(Exception):
    """Base error with a stable public code and termination reason."""

    code = "AGENT_ERROR"
    termination_reason = "provider_error"


class AgentConfigurationError(AgentError):
    code = "AGENT_CONFIGURATION_ERROR"
    termination_reason = "provider_error"


class ProviderTimeoutError(AgentError):
    code = "PROVIDER_TIMEOUT"
    termination_reason = "provider_timeout"


class ProviderError(AgentError):
    code = "PROVIDER_ERROR"
    termination_reason = "provider_error"


class InvalidProviderResponseError(AgentError):
    code = "INVALID_PROVIDER_RESPONSE"
    termination_reason = "invalid_provider_response"
