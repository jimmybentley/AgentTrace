"""Tests for agent communication graph construction."""


from agenttrace_analysis.graph import AgentGraph, AgentNode, CommunicationEdge


def test_agent_node_creation():
    """Test creating an agent node with metrics."""
    node = AgentNode(
        agent_id="agent-1",
        name="TestAgent",
        role="coordinator",
        model="gpt-4",
        span_count=5,
        total_tokens=1000,
        total_cost_usd=0.05,
        error_count=1,
        avg_latency_ms=250.5,
    )

    assert node.agent_id == "agent-1"
    assert node.name == "TestAgent"
    assert node.role == "coordinator"
    assert node.model == "gpt-4"
    assert node.span_count == 5
    assert node.total_tokens == 1000
    assert node.total_cost_usd == 0.05
    assert node.error_count == 1
    assert node.avg_latency_ms == 250.5


def test_agent_node_to_dict():
    """Test serializing agent node to dictionary."""
    node = AgentNode(
        agent_id="agent-1",
        name="TestAgent",
        span_count=5,
        total_tokens=1000,
    )

    result = node.to_dict()

    assert result["agent_id"] == "agent-1"
    assert result["name"] == "TestAgent"
    assert result["metrics"]["span_count"] == 5
    assert result["metrics"]["total_tokens"] == 1000


def test_communication_edge_creation():
    """Test creating a communication edge."""
    edge = CommunicationEdge(
        from_agent="agent-1",
        to_agent="agent-2",
        message_count=3,
        message_types=["request", "response"],
        total_tokens_transferred=500,
        avg_latency_ms=100.0,
    )

    assert edge.from_agent == "agent-1"
    assert edge.to_agent == "agent-2"
    assert edge.message_count == 3
    assert len(edge.message_types) == 2
    assert edge.total_tokens_transferred == 500


def test_communication_edge_to_dict():
    """Test serializing communication edge to dictionary."""
    edge = CommunicationEdge(
        from_agent="agent-1",
        to_agent="agent-2",
        message_count=3,
        message_types=["request", "response", "request"],
    )

    result = edge.to_dict()

    assert result["from_agent"] == "agent-1"
    assert result["to_agent"] == "agent-2"
    assert result["metrics"]["message_count"] == 3
    # Should deduplicate message types
    assert len(result["metrics"]["message_types"]) == 2


def test_empty_graph():
    """Test creating an empty graph."""
    graph = AgentGraph()

    result = graph.to_dict()

    assert result["nodes"] == []
    assert result["edges"] == []
    assert result["metrics"]["node_count"] == 0
    assert result["metrics"]["edge_count"] == 0


def test_graph_add_agent():
    """Test adding agents to graph."""
    graph = AgentGraph()

    node1 = AgentNode(agent_id="agent-1", name="Agent1")
    node2 = AgentNode(agent_id="agent-2", name="Agent2")

    graph.add_agent(node1)
    graph.add_agent(node2)

    result = graph.to_dict()

    assert result["metrics"]["node_count"] == 2
    assert len(result["nodes"]) == 2


def test_graph_add_edge():
    """Test adding edges to graph."""
    graph = AgentGraph()

    # Add nodes first
    graph.add_agent(AgentNode(agent_id="agent-1", name="Agent1"))
    graph.add_agent(AgentNode(agent_id="agent-2", name="Agent2"))

    # Add edge
    edge = CommunicationEdge(from_agent="agent-1", to_agent="agent-2", message_count=5)
    graph.add_edge(edge)

    result = graph.to_dict()

    assert result["metrics"]["edge_count"] == 1
    assert len(result["edges"]) == 1
    assert result["edges"][0]["from_agent"] == "agent-1"
    assert result["edges"][0]["to_agent"] == "agent-2"


def test_graph_find_isolated_agents():
    """Test finding agents with no communication."""
    graph = AgentGraph()

    # Add agents
    graph.add_agent(AgentNode(agent_id="agent-1", name="Agent1"))
    graph.add_agent(AgentNode(agent_id="agent-2", name="Agent2"))
    graph.add_agent(AgentNode(agent_id="agent-3", name="Agent3"))

    # Add edge only between agent-1 and agent-2
    graph.add_edge(CommunicationEdge(from_agent="agent-1", to_agent="agent-2", message_count=1))

    isolated = graph.find_isolated_agents()

    assert len(isolated) == 1
    assert "agent-3" in isolated


def test_graph_find_bottlenecks():
    """Test finding bottleneck agents with high in-degree."""
    graph = AgentGraph()

    # Create a star topology: agent-1, agent-2, agent-3 all send to agent-4
    graph.add_agent(AgentNode(agent_id="agent-1", name="Agent1"))
    graph.add_agent(AgentNode(agent_id="agent-2", name="Agent2"))
    graph.add_agent(AgentNode(agent_id="agent-3", name="Agent3"))
    graph.add_agent(AgentNode(agent_id="agent-4", name="Agent4"))

    graph.add_edge(CommunicationEdge(from_agent="agent-1", to_agent="agent-4", message_count=1))
    graph.add_edge(CommunicationEdge(from_agent="agent-2", to_agent="agent-4", message_count=1))
    graph.add_edge(CommunicationEdge(from_agent="agent-3", to_agent="agent-4", message_count=1))

    bottlenecks = graph.find_bottlenecks()

    # agent-4 has in-degree 3, average is 0.75, threshold is 1.5
    # 3 > 1.5, so it's a bottleneck
    assert "agent-4" in bottlenecks


def test_graph_has_cycles():
    """Test detecting cycles in graph."""
    graph = AgentGraph()

    # Create cycle: agent-1 -> agent-2 -> agent-1
    graph.add_agent(AgentNode(agent_id="agent-1", name="Agent1"))
    graph.add_agent(AgentNode(agent_id="agent-2", name="Agent2"))

    graph.add_edge(CommunicationEdge(from_agent="agent-1", to_agent="agent-2", message_count=1))
    graph.add_edge(CommunicationEdge(from_agent="agent-2", to_agent="agent-1", message_count=1))

    result = graph.to_dict()

    assert result["metrics"]["has_cycles"] is True


def test_graph_get_node():
    """Test retrieving a node by ID."""
    graph = AgentGraph()
    node = AgentNode(agent_id="agent-1", name="Agent1")
    graph.add_agent(node)

    retrieved = graph.get_node("agent-1")

    assert retrieved is not None
    assert retrieved.agent_id == "agent-1"
    assert retrieved.name == "Agent1"


def test_graph_get_edge():
    """Test retrieving an edge by agent IDs."""
    graph = AgentGraph()

    graph.add_agent(AgentNode(agent_id="agent-1", name="Agent1"))
    graph.add_agent(AgentNode(agent_id="agent-2", name="Agent2"))

    edge = CommunicationEdge(from_agent="agent-1", to_agent="agent-2", message_count=5)
    graph.add_edge(edge)

    retrieved = graph.get_edge("agent-1", "agent-2")

    assert retrieved is not None
    assert retrieved.message_count == 5


def test_graph_density():
    """Test calculating graph density."""
    graph = AgentGraph()

    # Add 3 nodes with 2 edges (sparse graph)
    graph.add_agent(AgentNode(agent_id="agent-1", name="Agent1"))
    graph.add_agent(AgentNode(agent_id="agent-2", name="Agent2"))
    graph.add_agent(AgentNode(agent_id="agent-3", name="Agent3"))

    graph.add_edge(CommunicationEdge(from_agent="agent-1", to_agent="agent-2", message_count=1))
    graph.add_edge(CommunicationEdge(from_agent="agent-2", to_agent="agent-3", message_count=1))

    result = graph.to_dict()

    # Density = 2 / (3 * 2) = 0.333
    assert 0.3 < result["metrics"]["density"] < 0.4
