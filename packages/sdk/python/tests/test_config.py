"""Tests for configuration management."""

import os

import pytest

from agenttrace.config import AgentTraceConfig, configure, get_config


def test_config_defaults():
    """Test default configuration values."""
    config = AgentTraceConfig()
    assert config.endpoint == "http://localhost:4318"
    assert config.service_name == "agenttrace-app"
    assert config.enabled is True


def test_config_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("AGENTTRACE_ENDPOINT", "http://custom:4318")
    monkeypatch.setenv("AGENTTRACE_SERVICE_NAME", "custom-service")
    monkeypatch.setenv("AGENTTRACE_ENABLED", "false")

    config = AgentTraceConfig.from_env()
    assert config.endpoint == "http://custom:4318"
    assert config.service_name == "custom-service"
    assert config.enabled is False


def test_get_config():
    """Test getting global configuration."""
    config = get_config()
    assert isinstance(config, AgentTraceConfig)


def test_configure():
    """Test updating global configuration."""
    configure(endpoint="http://test:4318", service_name="test-app")

    config = get_config()
    assert config.endpoint == "http://test:4318"
    assert config.service_name == "test-app"


def test_configure_partial():
    """Test partial configuration update."""
    # First configure
    configure(endpoint="http://test:4318", service_name="test-app")

    # Update only endpoint
    configure(endpoint="http://new:4318")

    config = get_config()
    assert config.endpoint == "http://new:4318"
    assert config.service_name == "test-app"  # Should remain unchanged
