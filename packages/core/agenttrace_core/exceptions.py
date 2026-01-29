"""Custom exceptions for AgentTrace."""


class AgentTraceError(Exception):
    """Base exception for all AgentTrace errors."""

    pass


class TraceNotFoundError(AgentTraceError):
    """Raised when a trace cannot be found."""

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        super().__init__(f"Trace not found: {trace_id}")


class CheckpointError(AgentTraceError):
    """Raised when checkpoint operations fail."""

    pass


class IngestionError(AgentTraceError):
    """Raised when trace ingestion fails."""

    pass


class ReplayError(AgentTraceError):
    """Raised when replay operations fail."""

    pass
