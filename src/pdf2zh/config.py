"""
Configuration Manager for PDFTranslator.

This module provides a thread-safe singleton ConfigManager class that handles
configuration data persistence and retrieval for the PDFTranslator application.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional


class ConfigManager:
    """
    Thread-safe singleton configuration manager.

    This class manages configuration data for the PDFTranslator application,
    providing thread-safe access to configuration values stored in a JSON file.
    """

    _instance: Optional["ConfigManager"] = None
    _lock = RLock()  # use RLock for reentrant locking

    @classmethod
    def get_instance(cls) -> ConfigManager:
        """Get singleton instance."""
        # Check if instance exists, if not create it
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ConfigManager instance."""
        # Avoid re-initialization
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized: bool = True

        self._config_path: Path = (
            Path.home() / ".config" / "PDFMathTranslate" / "config.json"
        )
        self._config_data: Dict[str, Any] = {}

        # Here we do not acquire a lock,
        # as the outer layer may have already done so (get_instance),
        # and RLock is also fine
        self._ensure_config_exists()

    def _ensure_config_exists(self, isInit: bool = True) -> None:
        """Ensure config.json exists."""
        if not self._config_path.exists():
            if isInit:
                self._config_path.parent.mkdir(parents=True, exist_ok=True)
                self._config_data = {}  # 默认配置内容
                self._save_config()
            else:
                raise ValueError(f"config file {self._config_path} not found!")
        else:
            self._load_config()

    def _load_config(self) -> None:
        """Load config.json."""
        with self._lock:  # Add lock for thread safety
            with self._config_path.open("r", encoding="utf-8") as f:
                self._config_data = json.load(f)

    def _save_config(self) -> None:
        """Save config.json - should be called within a lock."""
        # Remove circular references
        cleaned_data = self._remove_circular_references(self._config_data)
        with self._config_path.open("w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=4, ensure_ascii=False)

    def _remove_circular_references(self, obj: Any, seen: Optional[set] = None) -> Any:
        """Remove circular references from config data."""
        if seen is None:
            seen = set()
        obj_id = id(obj)
        # when encountering a processed object, treat it as a circular reference
        if obj_id in seen:
            return None
        seen.add(obj_id)

        if isinstance(obj, dict):
            return {
                k: self._remove_circular_references(v, seen) for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self._remove_circular_references(i, seen) for i in obj]
        return obj

    @classmethod
    def custome_config(cls, file_path: str) -> None:
        """Use custom config file."""
        custom_path = Path(file_path)
        if not custom_path.exists():
            raise ValueError(f"Config file {custom_path} not found!")

        with cls._lock:
            instance = cls()
            instance._config_path = custom_path
            # set isInit=False，if not exists then raise error
            instance._ensure_config_exists(isInit=False)
            cls._instance = instance

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get config value."""
        instance = cls.get_instance()

        # First check if key exists in config data (read-only operation)
        with instance._lock:
            if key in instance._config_data:
                return instance._config_data[key]

        # Check environment variables and update config if found
        if key in os.environ:
            value = os.environ[key]
            with instance._lock:
                instance._config_data[key] = value
                instance._save_config()
            return value

        # Set and save default value if provided
        if default is not None:
            with instance._lock:
                instance._config_data[key] = default
                instance._save_config()
            return default

        # Return None if nothing found
        return default

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set config value."""
        instance = cls.get_instance()
        with instance._lock:
            instance._config_data[key] = value
            instance._save_config()

    @classmethod
    def get_translator_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get env by translator name."""
        instance = cls.get_instance()
        translators = instance._config_data.get("translators", [])
        for translator in translators:
            if translator.get("name") == name:
                return translator["envs"]
        return None

    @classmethod
    def set_translator_by_name(
        cls, name: str, new_translator_envs: Dict[str, Any]
    ) -> None:
        """Set/update translator envs by name."""
        instance = cls.get_instance()
        with instance._lock:
            translators = instance._config_data.get("translators", [])
            for translator in translators:
                if translator.get("name") == name:
                    translator["envs"] = copy.deepcopy(new_translator_envs)
                    instance._save_config()
                    return
            translators.append(
                {"name": name, "envs": copy.deepcopy(new_translator_envs)}
            )
            instance._config_data["translators"] = translators
            instance._save_config()

    @classmethod
    def get_env_by_translatername(
        cls, translater_name: Any, name: str, default: Any = None
    ) -> Any:
        """Get env by translator name."""
        instance = cls.get_instance()

        with instance._lock:
            translators = instance._config_data.get("translators", [])

            # Find existing translator
            for translator in translators:
                if translator.get("name") == translater_name.name:
                    envs = translator.get("envs", {})
                    if name in envs and envs[name] is not None:
                        return envs[name]
                    else:
                        # Set default value for existing translator
                        envs[name] = default
                        instance._save_config()
                        return default

            # Translator not found, create new one
            new_translator = {
                "name": translater_name.name,
                "envs": copy.deepcopy(translater_name.envs)
                if hasattr(translater_name, "envs")
                else {},
            }
            new_translator["envs"][name] = default
            translators.append(new_translator)
            instance._config_data["translators"] = translators
            instance._save_config()
            return default

    @classmethod
    def delete(cls, key: str) -> None:
        """Delete config value and save."""
        instance = cls.get_instance()
        with instance._lock:
            if key in instance._config_data:
                del instance._config_data[key]
                instance._save_config()

    @classmethod
    def clear(cls) -> None:
        """Clear all config values and save."""
        instance = cls.get_instance()
        with instance._lock:
            instance._config_data = {}
            instance._save_config()

    @classmethod
    def all(cls) -> Dict[str, Any]:
        """Return all config items."""
        instance = cls.get_instance()
        # Return a copy to prevent external modification
        with instance._lock:
            return copy.deepcopy(instance._config_data)

    @classmethod
    def remove(cls) -> None:
        """Remove the config file."""
        instance = cls.get_instance()
        with instance._lock:
            if instance._config_path.exists():
                os.remove(instance._config_path)
