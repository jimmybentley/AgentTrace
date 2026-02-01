"""Example: Using standalone decorators without AgentTracer instance.

This example shows how to use the standalone decorators for simple use cases.

Usage:
    python decorator_example.py

Note:
    Configure via environment variables:
    export AGENTTRACE_ENDPOINT=http://localhost:4318
    export AGENTTRACE_SERVICE_NAME=decorator-example
"""

import asyncio
import os

from agenttrace.decorators import agent, tool, trace

# Configure via environment (or use defaults)
os.environ.setdefault("AGENTTRACE_ENDPOINT", "http://localhost:4318")
os.environ.setdefault("AGENTTRACE_SERVICE_NAME", "decorator-example")


@agent(name="TaskPlanner", role="planner")
async def plan_task(description: str) -> dict:
    """Plan a task into steps."""
    print(f"[TaskPlanner] Planning task: {description}")
    await asyncio.sleep(0.5)

    return {
        "task": description,
        "steps": [
            "Analyze requirements",
            "Design solution",
            "Implement",
            "Test",
            "Deploy",
        ],
        "priority": "high",
    }


@agent(name="TaskExecutor", role="executor")
async def execute_task(plan: dict) -> dict:
    """Execute a task plan."""
    print(f"[TaskExecutor] Executing plan for: {plan['task']}")
    await asyncio.sleep(1)

    return {
        "task": plan["task"],
        "status": "completed",
        "steps_completed": len(plan["steps"]),
        "duration": "45 minutes",
    }


@tool(name="progress_tracker")
async def track_progress(task_id: str, progress: int) -> None:
    """Track task progress."""
    print(f"[Tool: progress_tracker] Task {task_id} is {progress}% complete")
    await asyncio.sleep(0.2)


@tool(name="validator")
def validate_result(result: dict) -> bool:
    """Validate task result."""
    print(f"[Tool: validator] Validating result for task: {result.get('task')}")
    return result.get("status") == "completed"


async def main():
    """Run the workflow with standalone decorators."""
    print("Starting workflow with standalone decorators...")
    print("-" * 50)

    # Use the trace context manager
    with trace("task-execution-workflow", metadata={"environment": "production"}):
        # Plan the task
        plan = await plan_task("Deploy new feature to production")

        # Track progress
        await track_progress("task-001", 25)

        # Execute the task
        result = await execute_task(plan)

        # Track progress
        await track_progress("task-001", 75)

        # Validate result
        is_valid = validate_result(result)

        # Track final progress
        await track_progress("task-001", 100)

        print("-" * 50)
        print("\nWorkflow completed!")
        print(f"Result: {result}")
        print(f"Validation passed: {is_valid}")


if __name__ == "__main__":
    asyncio.run(main())
    print("\nTrace sent to AgentTrace at http://localhost:4318")
    print("View it in the web UI at http://localhost:5173")
