"""Diff computation for replay outputs.

This module provides utilities for computing structured diffs between
original and replay outputs, making it easy to understand what changed.
"""

from typing import Any

from deepdiff import DeepDiff


def compute_diff(original: Any, replay: Any) -> dict:
    """Compute structured diff between original and replay outputs.

    Uses DeepDiff to perform a deep comparison and generates both
    a structured diff and a human-readable summary.

    Args:
        original: The original output from the trace
        replay: The output from the replay

    Returns:
        A dictionary containing:
        - has_changes: Whether any differences were found
        - added: List of keys/values added in replay
        - removed: List of keys/values removed in replay
        - changed: Dict of values that differ between original and replay
        - type_changes: Dict of type mismatches
        - summary: Human-readable summary of changes
    """
    # DeepDiff with ignore_order for better comparison of lists
    diff = DeepDiff(original, replay, ignore_order=True, verbose_level=2)

    return {
        "has_changes": bool(diff),
        "added": _extract_items(diff.get("dictionary_item_added", [])),
        "removed": _extract_items(diff.get("dictionary_item_removed", [])),
        "changed": _format_changes(diff.get("values_changed", {})),
        "type_changes": _format_type_changes(diff.get("type_changes", {})),
        "summary": _generate_summary(diff),
    }


def _extract_items(items: list | set) -> list:
    """Extract items from DeepDiff format to a simple list."""
    if isinstance(items, set):
        items = list(items)

    # DeepDiff returns items in format like "root['key']"
    # Convert to simpler format
    result = []
    for item in items:
        if isinstance(item, str):
            # Extract the key path
            result.append(item.replace("root", "").replace("['", ".").replace("']", "").lstrip("."))
        else:
            result.append(str(item))

    return result


def _format_changes(changes: dict) -> dict:
    """Format value changes into a more readable structure."""
    formatted = {}

    for key, change in changes.items():
        # Extract the key path
        clean_key = key.replace("root", "").replace("['", ".").replace("']", "").lstrip(".")

        formatted[clean_key] = {
            "old": change.get("old_value"),
            "new": change.get("new_value"),
        }

    return formatted


def _format_type_changes(type_changes: dict) -> dict:
    """Format type changes into a more readable structure."""
    formatted = {}

    for key, change in type_changes.items():
        clean_key = key.replace("root", "").replace("['", ".").replace("']", "").lstrip(".")

        formatted[clean_key] = {
            "old_type": str(change.get("old_type", "")),
            "new_type": str(change.get("new_type", "")),
            "old_value": change.get("old_value"),
            "new_value": change.get("new_value"),
        }

    return formatted


def _generate_summary(diff: DeepDiff) -> str:
    """Generate a human-readable summary of the diff.

    Args:
        diff: DeepDiff result

    Returns:
        Human-readable summary string
    """
    if not diff:
        return "No changes detected"

    parts = []

    # Count additions
    added = diff.get("dictionary_item_added", [])
    if added:
        count = len(added) if not isinstance(added, set) else len(list(added))
        parts.append(f"{count} field{'s' if count != 1 else ''} added")

    # Count removals
    removed = diff.get("dictionary_item_removed", [])
    if removed:
        count = len(removed) if not isinstance(removed, set) else len(list(removed))
        parts.append(f"{count} field{'s' if count != 1 else ''} removed")

    # Count value changes
    changed = diff.get("values_changed", {})
    if changed:
        count = len(changed)
        parts.append(f"{count} value{'s' if count != 1 else ''} changed")

    # Count type changes
    type_changes = diff.get("type_changes", {})
    if type_changes:
        count = len(type_changes)
        parts.append(f"{count} type change{'s' if count != 1 else ''}")

    # Count list changes
    iterable_added = diff.get("iterable_item_added", {})
    iterable_removed = diff.get("iterable_item_removed", {})
    if iterable_added or iterable_removed:
        total = len(iterable_added) + len(iterable_removed)
        parts.append(f"{total} list item{'s' if total != 1 else ''} modified")

    if not parts:
        return "Unknown changes detected"

    return ", ".join(parts)


def format_diff_for_display(diff: dict) -> str:
    """Format a diff dictionary into a human-readable string.

    Args:
        diff: Diff dictionary from compute_diff()

    Returns:
        Formatted string suitable for display
    """
    lines = []

    lines.append(f"Summary: {diff['summary']}")
    lines.append("")

    if diff["added"]:
        lines.append("Added fields:")
        for field in diff["added"]:
            lines.append(f"  + {field}")
        lines.append("")

    if diff["removed"]:
        lines.append("Removed fields:")
        for field in diff["removed"]:
            lines.append(f"  - {field}")
        lines.append("")

    if diff["changed"]:
        lines.append("Changed values:")
        for field, change in diff["changed"].items():
            lines.append(f"  ~ {field}")
            lines.append(f"    old: {change['old']}")
            lines.append(f"    new: {change['new']}")
        lines.append("")

    if diff["type_changes"]:
        lines.append("Type changes:")
        for field, change in diff["type_changes"].items():
            lines.append(f"  ! {field}")
            lines.append(f"    {change['old_type']} -> {change['new_type']}")
        lines.append("")

    return "\n".join(lines)
