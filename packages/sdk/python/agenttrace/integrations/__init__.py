"""Framework integrations for auto-instrumentation.

This module provides convenient functions for auto-instrumenting
popular multi-agent frameworks with AgentTrace.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def get_available_integrations() -> List[str]:
    """Get list of available framework integrations.

    Returns:
        List of framework names that can be instrumented
    """
    available = []

    try:
        import langgraph  # noqa: F401

        available.append("langgraph")
    except ImportError:
        pass

    try:
        import autogen  # noqa: F401

        available.append("autogen")
    except ImportError:
        pass

    try:
        import crewai  # noqa: F401

        available.append("crewai")
    except ImportError:
        pass

    return available


def instrument_frameworks(frameworks: List[str] | None = None) -> None:
    """Instrument specified frameworks or all available frameworks.

    Args:
        frameworks: List of framework names to instrument.
                   If None, instruments all available frameworks.
                   Options: "langgraph", "autogen", "crewai"

    Example:
        >>> from agenttrace.integrations import instrument_frameworks
        >>> instrument_frameworks(["langgraph"])

    Raises:
        ValueError: If a specified framework is not available
    """
    if frameworks is None:
        # Instrument all available frameworks
        frameworks = get_available_integrations()
        logger.info(f"Auto-instrumenting all available frameworks: {frameworks}")

    for framework in frameworks:
        framework = framework.lower()

        if framework == "langgraph":
            try:
                from agenttrace.integrations.langgraph import instrument_langgraph

                instrument_langgraph()
                logger.info("LangGraph instrumented")
            except ImportError:
                raise ValueError(
                    "LangGraph not installed. Install with: pip install agenttrace[langgraph]"
                )

        elif framework == "autogen":
            try:
                from agenttrace.integrations.autogen import instrument_autogen

                instrument_autogen()
                logger.info("AutoGen instrumented")
            except ImportError:
                raise ValueError(
                    "AutoGen not installed. Install with: pip install agenttrace[autogen]"
                )

        elif framework == "crewai":
            try:
                from agenttrace.integrations.crewai import instrument_crewai

                instrument_crewai()
                logger.info("CrewAI instrumented")
            except ImportError:
                raise ValueError(
                    "CrewAI not installed. Install with: pip install agenttrace[crewai]"
                )

        else:
            raise ValueError(
                f"Unknown framework: {framework}. Available: langgraph, autogen, crewai"
            )


__all__ = [
    "instrument_frameworks",
    "get_available_integrations",
]
