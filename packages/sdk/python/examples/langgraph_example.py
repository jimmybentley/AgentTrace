"""Example: Instrumenting a LangGraph application with AgentTrace.

This example shows how to use auto-instrumentation for LangGraph applications.

Usage:
    pip install agenttrace[langgraph]
    python langgraph_example.py

Note:
    Make sure the AgentTrace backend is running at http://localhost:4318
"""

import asyncio

# Auto-instrument LangGraph BEFORE importing LangGraph
import agenttrace

agenttrace.instrument(["langgraph"])

# Now import and use LangGraph as normal
from langgraph.graph import StateGraph


# Define state type
class AgentState(dict):
    """State for our agent graph."""

    pass


# Define node functions
def planner(state: AgentState) -> AgentState:
    """Planning agent that creates a plan."""
    print("[Planner] Creating plan...")
    task = state.get("task", "")

    plan = {
        "steps": [
            f"Step 1: Analyze {task}",
            f"Step 2: Research {task}",
            f"Step 3: Synthesize findings for {task}",
        ],
        "estimated_time": "30 minutes",
    }

    return {"plan": plan, "task": task}


def researcher(state: AgentState) -> AgentState:
    """Research agent that gathers information."""
    print("[Researcher] Researching...")
    plan = state.get("plan", {})

    findings = {
        "sources": 5,
        "key_facts": [
            "Fact 1: Important discovery",
            "Fact 2: Significant trend",
            "Fact 3: Critical data point",
        ],
        "confidence": 0.85,
    }

    return {"plan": plan, "findings": findings}


def synthesizer(state: AgentState) -> AgentState:
    """Synthesis agent that combines findings."""
    print("[Synthesizer] Synthesizing results...")
    findings = state.get("findings", {})

    result = {
        "summary": "Comprehensive analysis completed",
        "key_insights": findings.get("key_facts", []),
        "confidence": findings.get("confidence", 0.0),
        "recommendation": "Proceed with implementation",
    }

    return {"result": result}


def build_graph() -> StateGraph:
    """Build the LangGraph workflow."""
    # Create graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("planner", planner)
    graph.add_node("researcher", researcher)
    graph.add_node("synthesizer", synthesizer)

    # Add edges
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "synthesizer")

    # Set entry and finish points
    graph.set_entry_point("planner")
    graph.set_finish_point("synthesizer")

    return graph


async def main():
    """Run the LangGraph workflow."""
    print("Building LangGraph workflow...")
    graph = build_graph()
    app = graph.compile()

    print("\nRunning workflow...")
    print("-" * 50)

    # Run the graph
    result = app.invoke({"task": "Analyze market trends in AI"})

    print("-" * 50)
    print("\nWorkflow completed!")
    print(f"\nResult: {result.get('result', {})}")


if __name__ == "__main__":
    asyncio.run(main())
    print("\nTrace sent to AgentTrace at http://localhost:4318")
    print("View it in the web UI at http://localhost:5173")
