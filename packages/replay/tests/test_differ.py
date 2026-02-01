"""Tests for diff computation."""


from agenttrace_replay.differ import compute_diff, format_diff_for_display


class TestComputeDiff:
    """Tests for compute_diff function."""

    def test_no_changes(self):
        """Test diff with identical inputs."""
        original = {"key": "value", "number": 42}
        replay = {"key": "value", "number": 42}

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is False
        assert diff["summary"] == "No changes detected"
        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["changed"]) == 0

    def test_value_changed(self):
        """Test diff with changed values."""
        original = {"key": "old_value", "number": 42}
        replay = {"key": "new_value", "number": 42}

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is True
        assert "1 value changed" in diff["summary"]
        assert len(diff["changed"]) == 1
        assert "key" in str(diff["changed"])

    def test_field_added(self):
        """Test diff with added fields."""
        original = {"key": "value"}
        replay = {"key": "value", "new_field": "new_value"}

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is True
        assert "1 field added" in diff["summary"]
        assert len(diff["added"]) == 1

    def test_field_removed(self):
        """Test diff with removed fields."""
        original = {"key": "value", "removed_field": "removed_value"}
        replay = {"key": "value"}

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is True
        assert "1 field removed" in diff["summary"]
        assert len(diff["removed"]) == 1

    def test_type_change(self):
        """Test diff with type changes."""
        original = {"number": 42}
        replay = {"number": "42"}

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is True
        assert len(diff["type_changes"]) == 1

    def test_nested_changes(self):
        """Test diff with nested structure changes."""
        original = {"outer": {"inner": "old_value"}}
        replay = {"outer": {"inner": "new_value"}}

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is True
        assert len(diff["changed"]) == 1

    def test_list_order_ignored(self):
        """Test that list order is ignored."""
        original = {"items": [1, 2, 3]}
        replay = {"items": [3, 2, 1]}

        diff = compute_diff(original, replay)

        # With ignore_order=True, this should show no changes
        assert diff["has_changes"] is False

    def test_complex_diff(self):
        """Test diff with multiple types of changes."""
        original = {
            "unchanged": "value",
            "changed": "old",
            "removed": "gone",
            "nested": {"key": "old_value"},
        }
        replay = {
            "unchanged": "value",
            "changed": "new",
            "added": "here",
            "nested": {"key": "new_value"},
        }

        diff = compute_diff(original, replay)

        assert diff["has_changes"] is True
        assert len(diff["added"]) == 1
        assert len(diff["removed"]) == 1
        assert len(diff["changed"]) == 2  # "changed" and "nested.key"


class TestFormatDiffForDisplay:
    """Tests for format_diff_for_display function."""

    def test_format_no_changes(self):
        """Test formatting when there are no changes."""
        diff = {
            "has_changes": False,
            "summary": "No changes detected",
            "added": [],
            "removed": [],
            "changed": {},
            "type_changes": {},
        }

        formatted = format_diff_for_display(diff)

        assert "Summary: No changes detected" in formatted
        assert "Added fields:" not in formatted
        assert "Removed fields:" not in formatted

    def test_format_with_changes(self):
        """Test formatting with various changes."""
        diff = {
            "has_changes": True,
            "summary": "1 field added, 1 value changed",
            "added": ["new_field"],
            "removed": [],
            "changed": {"old_field": {"old": "old_value", "new": "new_value"}},
            "type_changes": {},
        }

        formatted = format_diff_for_display(diff)

        assert "Summary:" in formatted
        assert "Added fields:" in formatted
        assert "+ new_field" in formatted
        assert "Changed values:" in formatted
        assert "~ old_field" in formatted
        assert "old: old_value" in formatted
        assert "new: new_value" in formatted

    def test_format_type_changes(self):
        """Test formatting type changes."""
        diff = {
            "has_changes": True,
            "summary": "1 type change",
            "added": [],
            "removed": [],
            "changed": {},
            "type_changes": {
                "number": {
                    "old_type": "<class 'int'>",
                    "new_type": "<class 'str'>",
                    "old_value": 42,
                    "new_value": "42",
                }
            },
        }

        formatted = format_diff_for_display(diff)

        assert "Type changes:" in formatted
        assert "! number" in formatted
