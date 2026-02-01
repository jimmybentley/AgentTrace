"""Configuration management for AgentTrace SDK."""

from dataclasses import dataclass
from os import environ


@dataclass
class AgentTraceConfig:
    """Configuration for AgentTrace SDK.

    Attributes:
        endpoint: OTLP HTTP endpoint URL
        service_name: Name of this service/application
        enabled: Whether tracing is enabled
    """

    endpoint: str = "http://localhost:4318"
    service_name: str = "agenttrace-app"
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "AgentTraceConfig":
        """Create configuration from environment variables.

        Environment variables:
            AGENTTRACE_ENDPOINT: OTLP endpoint URL
            AGENTTRACE_SERVICE_NAME: Service name
            AGENTTRACE_ENABLED: Enable/disable tracing (true/false)

        Returns:
            Configuration instance
        """
        return cls(
            endpoint=environ.get("AGENTTRACE_ENDPOINT", "http://localhost:4318"),
            service_name=environ.get("AGENTTRACE_SERVICE_NAME", "agenttrace-app"),
            enabled=environ.get("AGENTTRACE_ENABLED", "true").lower() == "true",
        )


_config: AgentTraceConfig | None = None


def get_config() -> AgentTraceConfig:
    """Get global configuration.

    Returns:
        Global configuration instance
    """
    global _config
    if _config is None:
        _config = AgentTraceConfig.from_env()
    return _config


def configure(**kwargs) -> None:
    """Update global configuration.

    Args:
        endpoint: OTLP endpoint URL
        service_name: Service name
        enabled: Enable/disable tracing

    Example:
        >>> import agenttrace
        >>> agenttrace.configure(endpoint="http://localhost:4318", service_name="my-app")
    """
    global _config
    current = get_config()
    _config = AgentTraceConfig(
        endpoint=kwargs.get("endpoint", current.endpoint),
        service_name=kwargs.get("service_name", current.service_name),
        enabled=kwargs.get("enabled", current.enabled),
    )
