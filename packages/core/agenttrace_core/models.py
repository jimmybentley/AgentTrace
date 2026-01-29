"""Core data models for AgentTrace."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Trace(BaseModel):
    """A single multi-agent execution (e.g., one user request)."""

    trace_id: UUID = Field(default_factory=uuid4)
    name: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    status: str = Field(default="running")  # running, completed, failed, timeout
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Aggregated metrics
    total_tokens: int | None = None
    total_cost_usd: Decimal | None = None
    total_latency_ms: int | None = None
    agent_count: int | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "user_query_processing",
                "start_time": "2026-01-29T10:00:00Z",
                "status": "running",
            }
        }
    )


class Agent(BaseModel):
    """Agent definition within a trace."""

    agent_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    name: str
    role: str | None = None  # e.g., "planner", "coder", "reviewer"
    model: str | None = None  # e.g., "claude-3-opus", "gpt-4"
    framework: str | None = None  # e.g., "langgraph", "autogen", "crewai"
    config: dict[str, Any] = Field(default_factory=dict)

    # Aggregated metrics for this agent in this trace
    total_spans: int | None = None
    total_tokens: int | None = None
    total_cost_usd: Decimal | None = None
    error_count: int | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "660e8400-e29b-41d4-a716-446655440001",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Planner",
                "role": "planner",
                "model": "claude-3-opus-20240229",
                "framework": "langgraph",
            }
        }
    )


class Span(BaseModel):
    """Individual operation within a trace."""

    span_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    parent_span_id: UUID | None = None
    agent_id: UUID | None = None

    name: str
    kind: str  # llm_call, tool_call, agent_message, checkpoint, handoff
    start_time: datetime
    end_time: datetime | None = None
    status: str = "ok"  # ok, error, timeout

    # LLM-specific fields
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None

    # Content (encrypted at rest in production)
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    # OpenTelemetry semantic attributes
    attributes: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "span_id": "770e8400-e29b-41d4-a716-446655440002",
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "llm_call",
                "kind": "llm_call",
                "start_time": "2026-01-29T10:00:01Z",
                "status": "ok",
                "model": "claude-3-opus-20240229",
                "input_tokens": 100,
                "output_tokens": 50,
            }
        }
    )


class AgentInfo(BaseModel):
    """Agent metadata extracted during normalization."""

    name: str
    role: str | None = None
    model: str | None = None
    framework: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class MessageInfo(BaseModel):
    """Inter-agent message data."""

    from_agent: str | None = None
    to_agent: str | None = None
    message_type: str = "request"  # request, response, broadcast, handoff
    content: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class NormalizedSpan(BaseModel):
    """Normalized span output from framework-specific normalizers."""

    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str
    kind: str
    start_time: datetime
    end_time: datetime | None = None
    status: str = "ok"

    # Agent information (if this span is associated with an agent)
    agent: AgentInfo | None = None

    # Inter-agent messages extracted from this span
    messages: list[MessageInfo] = Field(default_factory=list)

    # LLM-specific fields
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None

    # Content
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    # OpenTelemetry semantic attributes
    attributes: dict[str, Any] = Field(default_factory=dict)
