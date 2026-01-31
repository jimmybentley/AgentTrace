"""MAST (Multi-Agent System Failure Taxonomy) definitions."""

from dataclasses import dataclass
from enum import Enum


class FailureCategory(str, Enum):
    """High-level failure categories in the MAST taxonomy."""

    SPECIFICATION = "specification"
    COORDINATION = "coordination"
    VERIFICATION = "verification"


@dataclass
class FailureMode:
    """Specific failure mode within a category."""

    category: FailureCategory
    name: str
    description: str

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
        }


# All 10 failure modes from the MAST taxonomy
FAILURE_MODES: dict[str, FailureMode] = {
    # SPECIFICATION failures (ambiguous or incorrect task definition)
    "ambiguous_goal": FailureMode(
        category=FailureCategory.SPECIFICATION,
        name="Ambiguous Goal",
        description="Task goal is underspecified or has multiple interpretations",
    ),
    "conflicting_constraints": FailureMode(
        category=FailureCategory.SPECIFICATION,
        name="Conflicting Constraints",
        description="Task constraints are mutually incompatible",
    ),
    "impossible_task": FailureMode(
        category=FailureCategory.SPECIFICATION,
        name="Impossible Task",
        description="Task requirements cannot be satisfied given available resources",
    ),
    # COORDINATION failures (agent interaction problems)
    "infinite_loop": FailureMode(
        category=FailureCategory.COORDINATION,
        name="Infinite Loop",
        description="Agents cycle repeatedly without making progress",
    ),
    "handoff_failure": FailureMode(
        category=FailureCategory.COORDINATION,
        name="Handoff Failure",
        description="Agent fails to correctly receive or process handoff from another agent",
    ),
    "resource_contention": FailureMode(
        category=FailureCategory.COORDINATION,
        name="Resource Contention",
        description="Multiple agents compete for the same resource causing conflicts",
    ),
    "message_format_error": FailureMode(
        category=FailureCategory.COORDINATION,
        name="Message Format Error",
        description="Inter-agent message does not conform to expected schema",
    ),
    # VERIFICATION failures (output quality issues)
    "hallucination": FailureMode(
        category=FailureCategory.VERIFICATION,
        name="Hallucination",
        description="Agent generates factually incorrect information",
    ),
    "incomplete_output": FailureMode(
        category=FailureCategory.VERIFICATION,
        name="Incomplete Output",
        description="Agent output is missing required information",
    ),
    "timeout": FailureMode(
        category=FailureCategory.VERIFICATION,
        name="Timeout",
        description="Agent execution exceeds allocated time limit",
    ),
}


def get_failure_mode(name: str) -> FailureMode | None:
    """Get failure mode by name."""
    return FAILURE_MODES.get(name)


def get_failure_modes_by_category(
    category: FailureCategory,
) -> list[FailureMode]:
    """Get all failure modes in a category."""
    return [mode for mode in FAILURE_MODES.values() if mode.category == category]
