"""AutoGen auto-instrumentation for AgentTrace.

This module patches AutoGen to automatically emit AgentTrace-compatible spans
without requiring manual instrumentation.

Usage:
    >>> from agenttrace.integrations.autogen import instrument_autogen
    >>> instrument_autogen()
    >>>
    >>> # Now all AutoGen agent interactions will emit traces
    >>> from autogen import ConversableAgent
    >>> # ... your AutoGen code
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


def instrument_autogen() -> None:
    """Auto-instrument AutoGen to emit AgentTrace-compatible spans.

    Call this once at application startup. After calling, all AutoGen
    agent interactions will automatically emit traces to the configured
    AgentTrace endpoint.

    Example:
        >>> from agenttrace.integrations.autogen import instrument_autogen
        >>> instrument_autogen()
        >>>
        >>> # Now use AutoGen as normal
        >>> from autogen import ConversableAgent
        >>> agent = ConversableAgent("assistant")
        >>> # ... agent interactions
    """
    global _instrumented

    if _instrumented:
        logger.debug("AutoGen already instrumented")
        return

    config = get_config()
    if not config.enabled:
        logger.info("AgentTrace disabled, skipping AutoGen instrumentation")
        return

    # Set up OpenTelemetry
    setup_opentelemetry(config)

    try:
        # Import AutoGen components
        from autogen import ConversableAgent

        # Patch ConversableAgent methods
        _patch_conversable_agent(ConversableAgent)

        _instrumented = True
        logger.info("AutoGen instrumented successfully")

    except ImportError as e:
        logger.warning(f"Failed to instrument AutoGen: {e}. Is pyautogen installed?")
    except Exception as e:
        logger.error(f"Error instrumenting AutoGen: {e}")


def _patch_conversable_agent(agent_class: Any) -> None:
    """Patch ConversableAgent to capture message passing.

    Args:
        agent_class: The ConversableAgent class to patch
    """
    # Patch send method
    if hasattr(agent_class, "send"):
        original_send = agent_class.send

        @functools.wraps(original_send)
        def patched_send(self, message: Any, recipient: Any, request_reply: bool = None, **kwargs):
            """Patched send that creates spans for inter-agent messages."""
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span("autogen.send") as span:
                span.set_attribute("autogen.agent_name", self.name)
                recipient_name = recipient.name if hasattr(recipient, "name") else str(recipient)
                span.set_attribute("autogen.recipient_name", recipient_name)
                span.set_attribute("agent.name", self.name)
                span.set_attribute("agent.framework", "autogen")
                span.set_attribute("agenttrace.kind", "agent_message")
                span.set_attribute("message.from_agent", self.name)
                span.set_attribute("message.to_agent", recipient_name)
                span.set_attribute("message.type", "request")
                span.set_attribute("agenttrace.input", serialize(message))

                try:
                    result = original_send(self, message, recipient, request_reply, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        agent_class.send = patched_send

    # Patch receive method
    if hasattr(agent_class, "receive"):
        original_receive = agent_class.receive

        @functools.wraps(original_receive)
        def patched_receive(self, message: Any, sender: Any, request_reply: bool = None, **kwargs):
            """Patched receive that creates spans for receiving messages."""
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span("autogen.receive") as span:
                span.set_attribute("autogen.agent_name", self.name)
                sender_name = sender.name if hasattr(sender, "name") else str(sender)
                span.set_attribute("autogen.sender_name", sender_name)
                span.set_attribute("agent.name", self.name)
                span.set_attribute("agent.framework", "autogen")
                span.set_attribute("agenttrace.kind", "agent_message")
                span.set_attribute("message.from_agent", sender_name)
                span.set_attribute("message.to_agent", self.name)
                span.set_attribute("message.type", "response")
                span.set_attribute("agenttrace.input", serialize(message))

                try:
                    result = original_receive(self, message, sender, request_reply, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        agent_class.receive = patched_receive

    # Patch generate_reply method
    if hasattr(agent_class, "generate_reply"):
        original_generate_reply = agent_class.generate_reply

        @functools.wraps(original_generate_reply)
        def patched_generate_reply(self, messages: Any = None, sender: Any = None, **kwargs):
            """Patched generate_reply that creates spans for LLM calls."""
            tracer = get_tracer(__name__)

            with tracer.start_as_current_span("autogen.generate_reply") as span:
                span.set_attribute("autogen.agent_name", self.name)
                span.set_attribute("agent.name", self.name)
                span.set_attribute("agent.framework", "autogen")
                span.set_attribute("agenttrace.kind", "llm_call")
                span.set_attribute("agenttrace.input", serialize(messages))

                # Try to get model info
                if hasattr(self, "llm_config") and self.llm_config:
                    model = self.llm_config.get("model")
                    if model:
                        span.set_attribute("agent.model", model)

                try:
                    result = original_generate_reply(self, messages, sender, **kwargs)
                    span.set_attribute("agenttrace.output", serialize(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        agent_class.generate_reply = patched_generate_reply


def is_instrumented() -> bool:
    """Check if AutoGen has been instrumented.

    Returns:
        True if instrumented, False otherwise
    """
    return _instrumented
