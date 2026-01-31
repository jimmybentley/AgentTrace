"""Agent communication graph construction and analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import asyncpg
import networkx as nx


@dataclass
class AgentNode:
    """Node representing an agent in the communication graph."""

    agent_id: str
    name: str
    role: str | None = None
    model: str | None = None

    # Metrics
    span_count: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    error_count: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "model": self.model,
            "metrics": {
                "span_count": self.span_count,
                "total_tokens": self.total_tokens,
                "total_cost_usd": self.total_cost_usd,
                "error_count": self.error_count,
                "avg_latency_ms": self.avg_latency_ms,
            },
        }


@dataclass
class CommunicationEdge:
    """Edge representing communication between two agents."""

    from_agent: str
    to_agent: str

    # Metrics
    message_count: int = 0
    message_types: list[str] = field(default_factory=list)
    total_tokens_transferred: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize edge to dictionary."""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "metrics": {
                "message_count": self.message_count,
                "message_types": list(set(self.message_types)),
                "total_tokens_transferred": self.total_tokens_transferred,
                "avg_latency_ms": self.avg_latency_ms,
            },
        }


class AgentGraph:
    """Agent communication graph with analysis capabilities."""

    def __init__(self):
        """Initialize an empty agent graph."""
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, AgentNode] = {}
        self._edges: dict[tuple[str, str], CommunicationEdge] = {}

    @classmethod
    async def from_trace(cls, trace_id: str, db: asyncpg.Pool) -> AgentGraph:
        """
        Build agent communication graph from stored trace data.

        Args:
            trace_id: Trace ID to build graph from
            db: Database connection pool

        Returns:
            AgentGraph instance with nodes and edges populated
        """
        graph = cls()

        async with db.acquire() as conn:
            # Fetch all agents involved in this trace
            agents = await conn.fetch(
                """
                SELECT DISTINCT a.agent_id, a.name, a.role, a.model, a.framework, a.config
                FROM agents a
                JOIN spans s ON s.agent_id = a.agent_id
                WHERE s.trace_id = $1
                """,
                trace_id,
            )

            # Build agent nodes with metrics
            for agent_row in agents:
                agent_id = agent_row["agent_id"]

                # Aggregate metrics for this agent from spans
                metrics = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as span_count,
                        COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                        COALESCE(SUM(cost_usd), 0.0) as total_cost_usd,
                        COALESCE(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END), 0) as error_count,
                        COALESCE(AVG(EXTRACT(EPOCH FROM (end_time - start_time)) * 1000), 0.0) as avg_latency_ms
                    FROM spans
                    WHERE trace_id = $1 AND agent_id = $2
                    """,
                    trace_id,
                    agent_id,
                )

                node = AgentNode(
                    agent_id=agent_id,
                    name=agent_row["name"],
                    role=agent_row["role"],
                    model=agent_row["model"],
                    span_count=metrics["span_count"],
                    total_tokens=metrics["total_tokens"],
                    total_cost_usd=float(metrics["total_cost_usd"]),
                    error_count=metrics["error_count"],
                    avg_latency_ms=float(metrics["avg_latency_ms"]),
                )
                graph.add_agent(node)

            # Fetch inter-agent messages and build edges
            messages = await conn.fetch(
                """
                SELECT
                    from_agent,
                    to_agent,
                    message_type,
                    content,
                    timestamp
                FROM agent_messages
                WHERE trace_id = $1 AND from_agent IS NOT NULL AND to_agent IS NOT NULL
                ORDER BY timestamp
                """,
                trace_id,
            )

            # Group messages by (from_agent, to_agent) pair
            edge_data: dict[tuple[str, str], list[dict]] = {}
            for msg in messages:
                key = (msg["from_agent"], msg["to_agent"])
                if key not in edge_data:
                    edge_data[key] = []
                edge_data[key].append(msg)

            # Create edges with aggregated metrics
            for (from_agent, to_agent), msgs in edge_data.items():
                message_types = [msg["message_type"] for msg in msgs]

                # Calculate total tokens from message content
                total_tokens = 0
                for msg in msgs:
                    content = msg.get("content") or {}
                    if isinstance(content, dict):
                        # Rough estimate: count characters in content
                        content_str = str(content)
                        total_tokens += len(content_str) // 4  # Rough token estimate

                # Calculate average latency (time between consecutive messages)
                latencies = []
                for i in range(1, len(msgs)):
                    if msgs[i]["timestamp"] and msgs[i - 1]["timestamp"]:
                        delta = msgs[i]["timestamp"] - msgs[i - 1]["timestamp"]
                        latencies.append(delta.total_seconds() * 1000)

                avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

                edge = CommunicationEdge(
                    from_agent=from_agent,
                    to_agent=to_agent,
                    message_count=len(msgs),
                    message_types=message_types,
                    total_tokens_transferred=total_tokens,
                    avg_latency_ms=avg_latency,
                )
                graph.add_edge(edge)

        return graph

    def add_agent(self, node: AgentNode) -> None:
        """Add an agent node to the graph."""
        self._nodes[node.agent_id] = node
        self._graph.add_node(node.agent_id, data=node)

    def add_edge(self, edge: CommunicationEdge) -> None:
        """Add a communication edge to the graph."""
        key = (edge.from_agent, edge.to_agent)
        self._edges[key] = edge
        self._graph.add_edge(edge.from_agent, edge.to_agent, data=edge)

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary for API responses."""
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges.values()],
            "metrics": {
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "density": (nx.density(self._graph) if len(self._nodes) > 1 else 0.0),
                "has_cycles": not nx.is_directed_acyclic_graph(self._graph)
                if len(self._nodes) > 0
                else False,
            },
        }

    def find_bottlenecks(self) -> list[str]:
        """
        Identify agents with high in-degree (bottleneck agents).

        Returns:
            List of agent IDs that are bottlenecks (in-degree > 2x average)
        """
        if len(self._nodes) == 0:
            return []

        in_degrees = dict(self._graph.in_degree())
        if not in_degrees:
            return []

        avg_in_degree = sum(in_degrees.values()) / len(in_degrees)
        threshold = avg_in_degree * 2

        bottlenecks = [agent_id for agent_id, degree in in_degrees.items() if degree > threshold]
        return bottlenecks

    def find_isolated_agents(self) -> list[str]:
        """
        Find agents with no incoming or outgoing communication.

        Returns:
            List of agent IDs with degree 0
        """
        isolated = []
        for agent_id in self._nodes:
            if self._graph.degree(agent_id) == 0:
                isolated.append(agent_id)
        return isolated

    def get_node(self, agent_id: str) -> AgentNode | None:
        """Get agent node by ID."""
        return self._nodes.get(agent_id)

    def get_edge(self, from_agent: str, to_agent: str) -> CommunicationEdge | None:
        """Get communication edge between two agents."""
        return self._edges.get((from_agent, to_agent))
