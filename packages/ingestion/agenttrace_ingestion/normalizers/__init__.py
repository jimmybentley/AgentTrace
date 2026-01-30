"""Framework-specific normalizers for OTLP spans."""

from .autogen import AutoGenNormalizer
from .base import BaseNormalizer
from .crewai import CrewAINormalizer
from .generic import GenericNormalizer
from .langgraph import LangGraphNormalizer

# Registry of normalizers by framework name
_NORMALIZERS: dict[str, BaseNormalizer] = {
    "langgraph": LangGraphNormalizer(),
    "autogen": AutoGenNormalizer(),
    "crewai": CrewAINormalizer(),
    "generic": GenericNormalizer(),
}


def get_normalizer(framework: str) -> BaseNormalizer:
    """
    Get the appropriate normalizer for a framework.

    Args:
        framework: Framework name (e.g., "langgraph", "autogen", "crewai")

    Returns:
        BaseNormalizer instance for the framework, or GenericNormalizer if unknown
    """
    framework_lower = framework.lower() if framework else "generic"
    return _NORMALIZERS.get(framework_lower, _NORMALIZERS["generic"])


__all__ = [
    "BaseNormalizer",
    "LangGraphNormalizer",
    "AutoGenNormalizer",
    "CrewAINormalizer",
    "GenericNormalizer",
    "get_normalizer",
]
