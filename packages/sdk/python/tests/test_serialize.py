"""Tests for serialization utilities."""

from agenttrace._serialize import serialize, truncate_string


def test_serialize_simple_types():
    """Test serialization of simple types."""
    assert serialize(42) == "42"
    assert serialize("hello") == '"hello"'
    assert serialize([1, 2, 3]) == "[1, 2, 3]"
    assert serialize({"key": "value"}) == '{"key": "value"}'


def test_serialize_custom_object():
    """Test serialization of custom objects."""

    class TestObj:
        def __init__(self):
            self.name = "test"
            self.value = 42

    obj = TestObj()
    result = serialize(obj)
    assert "TestObj" in result
    assert "name" in result
    assert "test" in result


def test_serialize_truncation():
    """Test that long strings are truncated."""
    long_string = "x" * 20000
    result = serialize(long_string)
    assert len(result) <= 10020  # max_length + "... (truncated)"
    assert "truncated" in result


def test_truncate_string():
    """Test string truncation."""
    assert truncate_string("hello") == "hello"
    assert truncate_string("x" * 2000, max_length=100) == "x" * 100 + "... (truncated)"
