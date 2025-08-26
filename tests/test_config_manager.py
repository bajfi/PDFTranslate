"""
Tests for ConfigManager class.

This module contains comprehensive tests for the ConfigManager singleton class,
including thread safety tests and configuration management functionality.
"""

import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pdf2zh.config import ConfigManager

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def setup_function(function):
    """Set up test environment with temporary config file."""
    global temp_dir, temp_config
    temp_dir = tempfile.mkdtemp()
    temp_config = os.path.join(temp_dir, "config.json")
    with open(temp_config, "w", encoding="utf-8") as f:
        json.dump({}, f)
    ConfigManager.custome_config(temp_config)
    ConfigManager.clear()


def teardown_function(function):
    """Clean up test environment."""
    if Path(temp_config).exists():
        shutil.rmtree(temp_dir)
    ConfigManager._instance = None


def test_set_and_get():
    """Test basic set and get functionality."""
    ConfigManager.set("foo", "bar")
    assert ConfigManager.get("foo") == "bar"


def test_get_default():
    """Test getting value with default when key doesn't exist."""
    assert ConfigManager.get("not_exist", default=123) == 123
    # Verify that default was saved
    assert ConfigManager.get("not_exist") == 123


def test_get_none_default():
    """Test getting value with None default when key doesn't exist."""
    assert ConfigManager.get("not_exist_none", default=None) is None


def test_delete():
    """Test deleting configuration values."""
    ConfigManager.set("foo", "bar")
    ConfigManager.delete("foo")
    assert ConfigManager.get("foo") is None


def test_delete_nonexistent():
    """Test deleting a non-existent key doesn't raise error."""
    ConfigManager.delete("nonexistent_key")  # Should not raise


def test_clear():
    """Test clearing all configuration values."""
    ConfigManager.set("a", 1)
    ConfigManager.set("b", 2)
    ConfigManager.clear()
    assert ConfigManager.all() == {}


def test_all():
    """Test getting all configuration items."""
    ConfigManager.set("x", 1)
    ConfigManager.set("y", 2)
    all_items = ConfigManager.all()
    assert all_items["x"] == 1 and all_items["y"] == 2

    # Test that returned dict is a copy (modifications don't affect original)
    all_items["z"] = 3
    assert "z" not in ConfigManager.all()


def test_remove():
    """Test removing the config file."""
    ConfigManager.set("foo", "bar")
    ConfigManager.remove()
    assert not Path(temp_config).exists()


def test_remove_nonexistent_file():
    """Test removing a non-existent config file doesn't raise error."""
    ConfigManager.remove()  # First removal
    ConfigManager.remove()  # Should not raise error


def test_thread_safety():
    """Test thread safety with concurrent access."""
    results = {}

    def writer(thread_id: int):
        """Write values in a thread-safe manner."""
        for i in range(10):
            key = f"thread_{thread_id}_key_{i}"
            value = f"thread_{thread_id}_value_{i}"
            ConfigManager.set(key, value)
            results[key] = value
            time.sleep(0.001)  # Small delay to increase chance of race conditions

    # Create multiple threads
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Verify all values were set correctly
    for key, expected_value in results.items():
        assert ConfigManager.get(key) == expected_value


def test_custome_config():
    """Test using a custom config file."""
    # Should load from a new file
    new_config = os.path.join(temp_dir, "new_config.json")
    with open(new_config, "w", encoding="utf-8") as f:
        json.dump({"abc": 42}, f)
    ConfigManager.custome_config(new_config)
    assert ConfigManager.get("abc") == 42


def test_custome_config_nonexistent():
    """Test using a custom config file that doesn't exist."""
    nonexistent_config = os.path.join(temp_dir, "nonexistent.json")
    with pytest.raises(ValueError, match="Config file .* not found"):
        ConfigManager.custome_config(nonexistent_config)


def test_env_variable(monkeypatch: "MonkeyPatch"):
    """Test reading configuration from environment variables."""
    monkeypatch.setenv("FOO_ENV", "env_value")
    assert ConfigManager.get("FOO_ENV") == "env_value"
    # Verify it was saved to config
    assert ConfigManager.get("FOO_ENV") == "env_value"


def test_set_translator_by_name_and_get():
    """Test setting and getting translator configurations."""
    envs = {"API_KEY": "123", "MODEL": "gpt-4"}
    ConfigManager.set_translator_by_name("test_trans", envs)
    retrieved_envs = ConfigManager.get_translator_by_name("test_trans")
    assert retrieved_envs == envs


def test_get_translator_by_name_nonexistent():
    """Test getting a non-existent translator returns None."""
    assert ConfigManager.get_translator_by_name("nonexistent") is None


def test_update_existing_translator():
    """Test updating an existing translator configuration."""
    # Set initial translator
    initial_envs = {"API_KEY": "123"}
    ConfigManager.set_translator_by_name("test_trans", initial_envs)

    # Update translator
    updated_envs = {"API_KEY": "456", "MODEL": "gpt-4"}
    ConfigManager.set_translator_by_name("test_trans", updated_envs)

    # Verify update
    retrieved_envs = ConfigManager.get_translator_by_name("test_trans")
    assert retrieved_envs == updated_envs


class MockTranslator:
    """Mock translator class for testing."""

    def __init__(self, name: str, envs: dict = None):
        """Initialize mock translator."""
        self.name = name
        self.envs = envs or {}


def test_get_env_by_translatername_existing():
    """Test getting environment variable for existing translator."""
    # Set up translator first
    envs = {"API_KEY": "secret123", "MODEL": "gpt-4"}
    ConfigManager.set_translator_by_name("test_translator", envs)

    # Create mock translator
    translator = MockTranslator("test_translator")

    # Test getting existing env
    api_key = ConfigManager.get_env_by_translatername(
        translator, "API_KEY", default="default_key"
    )
    assert api_key == "secret123"


def test_get_env_by_translatername_with_default():
    """Test getting environment variable with default for new translator."""
    translator = MockTranslator("new_translator", {"EXISTING": "value"})

    # Test getting non-existing env with default
    result = ConfigManager.get_env_by_translatername(
        translator, "NEW_ENV", default="default_value"
    )
    assert result == "default_value"

    # Verify it was saved
    saved_envs = ConfigManager.get_translator_by_name("new_translator")
    assert saved_envs["NEW_ENV"] == "default_value"


def test_get_env_by_translatername_none_default():
    """Test getting environment variable with None default."""
    translator = MockTranslator("another_translator")

    result = ConfigManager.get_env_by_translatername(
        translator, "SOME_ENV", default=None
    )
    assert result is None


def test_singleton_pattern():
    """Test that ConfigManager follows singleton pattern."""
    instance1 = ConfigManager.get_instance()
    instance2 = ConfigManager.get_instance()
    assert instance1 is instance2


def test_concurrent_singleton_creation():
    """Test thread-safe singleton creation."""
    # Reset singleton
    ConfigManager._instance = None

    instances = []

    def create_instance():
        instances.append(ConfigManager.get_instance())

    threads = [threading.Thread(target=create_instance) for _ in range(10)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All instances should be the same object
    for instance in instances:
        assert instance is instances[0]


def test_circular_reference_handling():
    """Test handling of circular references in config data."""
    # Create a circular reference
    data = {"a": {"b": {}}}
    data["a"]["b"]["c"] = data["a"]  # Circular reference

    ConfigManager.set("circular", data)

    # Should not raise an error when saving
    retrieved = ConfigManager.get("circular")
    assert "a" in retrieved
    assert "b" in retrieved["a"]


def test_config_persistence():
    """Test that configuration persists across instance resets."""
    ConfigManager.set("persistent_key", "persistent_value")

    # Reset instance but keep config file
    ConfigManager._instance = None

    # Create new instance with same config file
    ConfigManager.custome_config(temp_config)

    # Value should still be there
    assert ConfigManager.get("persistent_key") == "persistent_value"
