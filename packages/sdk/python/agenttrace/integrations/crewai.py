"""CrewAI auto-instrumentation for AgentTrace.

This module patches CrewAI to automatically emit AgentTrace-compatible spans
without requiring manual instrumentation.

Usage:
    >>> from agenttrace.integrations.crewai import instrument_crewai
    >>> instrument_crewai()
    >>>
    >>> # Now all CrewAI crew executions will emit traces
    >>> from crewai import Crew, Agent, Task
    >>> # ... your CrewAI code
"""

import functools
import logging
from typing import Any

from opentelemetry.trace import Status, StatusCode

from agenttrace._otel import get_tracer, setup_opentelemetry
from agenttrace._serialize import serialize
from agenttrace.config import get_config

logger = logging.getLogger(__name__)

_instrumented = False


def instrument_crewai() -> None:
    """Auto-instrument CrewAI to emit AgentTrace-compatible spans.

    Call this once at application startup. After calling, all CrewAI
    crew executions will automatically emit traces to the configured
    AgentTrace endpoint.

    Example:
        >>> from agenttrace.integrations.crewai import instrument_crewai
        >>> instrument_crewai()
        >>>
        >>> # Now use CrewAI as normal
        >>> from crewai import Crew, Agent, Task
        >>> crew = Crew(agents=[...], tasks=[...])
        >>> result = crew.kickoff()
    """
    global _instrumented

    if _instrumented:
        logger.debug("CrewAI already instrumented")
        return

    config = get_config()
    if not config.enabled:
        logger.info("AgentTrace disabled, skipping CrewAI instrumentation")
        return

    # Set up OpenTelemetry
    setup_opentelemetry(config)

    try:
        # Import CrewAI components
        from crewai import Agent, Crew, Task

        # Patch Crew.kickoff
        _patch_crew(Crew)

        # Patch Agent.execute_task
        _patch_agent(Agent)

        # Patch Task execution
        _patch_task(Task)

        _instrumented = True
        logger.info("CrewAI instrumented successfully")

    except ImportError as e:
        logger.warning(f"Failed to instrument CrewAI: {e}. Is crewai installed?")
    except Exception as e:
        logger.error(f"Error instrumenting CrewAI: {e}")


def _patch_crew(crew_class: Any) -> None:
    """Patch Crew.kickoff to create parent trace span.

    Args:
        crew_class: The Crew class to patch
    """
    if hasattr(crew_class, "kickoff"):
        original_kickoff = crew_class.kickoff

        @functools.wraps(original_kickoff)
        def patched_kickoff(self, inputs: Any = None, **kwargs):
            """Patched kickoff that creates parent trace span."""
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span("crewai.kickoff") as span:
                span.set_attribute("agenttrace.framework", "crewai")
                span.set_attribute("agenttrace.kind", "crew_execution")
                span.set_attribute("agenttrace.input", serialize(inputs))

                # Add crew metadata
                if hasattr(self, "agents"):
                    span.set_attribute("crewai.agent_count", len(self.agents))

                if hasattr(self, "tasks"):
                    span.set_attribute("crewai.task_count", len(self.tasks))

                try:
                    result = original_kickoff(self, inputs, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        crew_class.kickoff = patched_kickoff


def _patch_agent(agent_class: Any) -> None:
    """Patch Agent.execute_task to create agent execution spans.

    Args:
        agent_class: The Agent class to patch
    """
    if hasattr(agent_class, "execute_task"):
        original_execute_task = agent_class.execute_task

        @functools.wraps(original_execute_task)
        def patched_execute_task(self, task: Any, context: Any = None, **kwargs):
            """Patched execute_task that creates agent spans."""
            tracer = get_tracer(__name__)

            agent_name = getattr(self, "name", "unknown")
            agent_role = getattr(self, "role", "unknown")

            with tracer.start_as_current_span(f"crewai.agent:{agent_name}") as span:
                span.set_attribute("crewai.agent_name", agent_name)
                span.set_attribute("crewai.agent_role", agent_role)
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.role", agent_role)
                span.set_attribute("agent.framework", "crewai")
                span.set_attribute("agenttrace.kind", "agent_call")

                # Add task info
                if task:
                    task_desc = getattr(task, "description", "")
                    span.set_attribute("crewai.task_description", task_desc[:200])

                # Add model info if available
                if hasattr(self, "llm"):
                    llm = self.llm
                    if hasattr(llm, "model_name"):
                        span.set_attribute("agent.model", llm.model_name)

                input_data = {"task": task, "context": context}
                span.set_attribute("agenttrace.input", serialize(input_data))

                try:
                    result = original_execute_task(self, task, context, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        agent_class.execute_task = patched_execute_task


def _patch_task(task_class: Any) -> None:
    """Patch Task execution methods.

    Args:
        task_class: The Task class to patch
    """
    if hasattr(task_class, "execute"):
        original_execute = task_class.execute

        @functools.wraps(original_execute)
        def patched_execute(self, agent: Any = None, context: Any = None, **kwargs):
            """Patched execute that creates task spans."""
            tracer = get_tracer(__name__)

            task_desc = getattr(self, "description", "unknown")

            with tracer.start_as_current_span("crewai.task") as span:
                span.set_attribute("crewai.task_description", task_desc[:200])
                span.set_attribute("agenttrace.kind", "task_execution")
                span.set_attribute("agenttrace.input", serialize(context))

                try:
                    result = original_execute(self, agent, context, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        task_class.execute = patched_execute


def is_instrumented() -> bool:
    """Check if CrewAI has been instrumented.

    Returns:
        True if instrumented, False otherwise
    """
    return _instrumented
