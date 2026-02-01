"""Internal OpenTelemetry setup utilities."""

import logging
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from agenttrace.config import AgentTraceConfig

logger = logging.getLogger(__name__)

_initialized = False


def setup_opentelemetry(config: "AgentTraceConfig") -> None:
    """Set up OpenTelemetry with OTLP exporter.

    Args:
        config: AgentTrace configuration

    Note:
        This function should only be called once. Subsequent calls will be ignored.
    """
    global _initialized

    if _initialized:
        logger.debug("OpenTelemetry already initialized, skipping setup")
        return

    if not config.enabled:
        logger.info("AgentTrace tracing is disabled")
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": config.service_name,
                "agenttrace.version": "0.1.0",
            }
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Create OTLP exporter
        # The endpoint should be the base URL, exporter will append /v1/traces
        exporter = OTLPSpanExporter(endpoint=f"{config.endpoint}/v1/traces", timeout=10)

        # Add batch span processor for efficient export
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        _initialized = True
        logger.info(f"AgentTrace initialized with endpoint: {config.endpoint}")

    except Exception as e:
        logger.warning(f"Failed to initialize AgentTrace: {e}. Tracing will be disabled.")


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Name for the tracer (typically __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def is_initialized() -> bool:
    """Check if OpenTelemetry has been initialized.

    Returns:
        True if initialized, False otherwise
    """
    return _initialized
