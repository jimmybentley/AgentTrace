"""Example: Manual instrumentation with AgentTrace SDK.

This example shows how to use the AgentTracer class to manually instrument
a multi-agent application.

Usage:
    python manual_example.py

Note:
    Make sure the AgentTrace backend is running at http://localhost:4318
"""

import asyncio

from agenttrace import AgentTracer

# Initialize tracer
tracer = AgentTracer(
    endpoint="http://localhost:4318",
    service_name="manual-example",
    framework="custom",
)


@tracer.agent("Researcher", role="researcher", model="gpt-4")
async def research(topic: str) -> dict:
    """Research a topic and return findings."""
    print(f"[Researcher] Researching topic: {topic}")

    # Simulate research work
    await asyncio.sleep(1)

    findings = {
        "topic": topic,
        "summary": f"Research findings on {topic}",
        "key_points": [
            "Point 1: Important finding",
            "Point 2: Another discovery",
            "Point 3: Critical insight",
        ],
        "sources": 5,
    }

    return findings


@tracer.agent("Writer", role="writer", model="claude-3-opus")
async def write(findings: dict) -> str:
    """Write an article based on research findings."""
    print(f"[Writer] Writing article based on {findings['topic']}")

    # Simulate writing work
    await asyncio.sleep(1.5)

    article = f"""
# Article: {findings['topic']}

## Summary
{findings['summary']}

## Key Points
"""

    for point in findings["key_points"]:
        article += f"- {point}\n"

    article += f"\nBased on {findings['sources']} sources."

    return article


@tracer.tool("web_search")
async def web_search(query: str) -> list[str]:
    """Search the web for information."""
    print(f"[Tool: web_search] Searching for: {query}")

    # Simulate search
    await asyncio.sleep(0.5)

    return [
        f"Result 1 for: {query}",
        f"Result 2 for: {query}",
        f"Result 3 for: {query}",
    ]


@tracer.tool("fact_check")
async def fact_check(statement: str) -> bool:
    """Check if a statement is factual."""
    print(f"[Tool: fact_check] Checking: {statement}")

    # Simulate fact checking
    await asyncio.sleep(0.3)

    return True


async def main():
    """Run the multi-agent workflow."""
    print("Starting multi-agent workflow...")
    print("-" * 50)

    # Start a trace
    with tracer.trace("research-and-write", metadata={"user_id": "user123", "version": "1.0"}):
        # Step 1: Research
        topic = "AI in Healthcare 2025"
        findings = await research(topic)

        # Create a checkpoint after research
        tracer.checkpoint("after_research", {"findings": findings})

        # Record message handoff
        tracer.message("Researcher", "Writer", findings, "handoff")

        # Step 2: Additional search
        search_results = await web_search(topic)
        findings["sources"] = len(search_results)

        # Step 3: Write article
        article = await write(findings)

        # Step 4: Fact check
        is_valid = await fact_check("AI is improving healthcare outcomes")

        # Create final checkpoint
        tracer.checkpoint("after_writing", {"article": article, "verified": is_valid})

        print("-" * 50)
        print("Workflow completed!")
        print("\nGenerated Article:")
        print(article)
        print(f"\nFact check passed: {is_valid}")


if __name__ == "__main__":
    asyncio.run(main())
    print("\nTrace sent to AgentTrace at http://localhost:4318")
    print("View it in the web UI at http://localhost:5173")
