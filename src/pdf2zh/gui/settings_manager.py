"""GUI Settings persistence module for saving and loading user preferences."""

import logging
from typing import Any, Dict

from pdf2zh.config import ConfigManager

logger = logging.getLogger(__name__)


class GUISettingsManager:
    """Manages saving and loading GUI user preferences."""

    # Default settings for the GUI
    DEFAULT_SETTINGS = {
        "service": "Google",  # Will be set to first available service
        "lang_from": "English",
        "lang_to": "Simplified Chinese",
        "page_range": None,  # Will be set to first available option
        "output_dir": "",
        "threads": "4",
        "skip_subset_fonts": False,
        "ignore_cache": True,
        "vfont": "",
        "use_babeldoc": False,
        "prompt": "",
        "file_type": "File",
    }

    @classmethod
    def get_settings_key(cls) -> str:
        """Get the configuration key for GUI settings."""
        return "gui_user_settings"

    @classmethod
    def save_setting(cls, key: str, value: Any) -> None:
        """Save a single GUI setting.

        This method saves a single setting by loading the current config
        (not merged with defaults), updating the specific setting, and then
        saving back using save_all_settings which applies proper filtering
        to prevent None values from being saved.

        Args:
            key: The setting key
            value: The setting value
        """
        try:
            # Get current settings from config (not merged with defaults)
            # This avoids saving defaults that shouldn't be saved
            current_settings = ConfigManager.get(cls.get_settings_key(), {})

            # Update the specific setting
            current_settings[key] = value

            # Save back to config using save_all_settings to apply filtering
            cls.save_all_settings(current_settings)

            logger.debug(f"Saved GUI setting: {key} = {value}")

        except Exception as e:
            logger.error(f"Failed to save GUI setting {key}: {e}")

    @classmethod
    def load_setting(cls, key: str, default: Any = None) -> Any:
        """Load a single GUI setting.

        Args:
            key: The setting key
            default: Default value if setting not found

        Returns:
            The setting value or default
        """
        try:
            all_settings = cls.load_all_settings()
            return all_settings.get(key, default)
        except Exception as e:
            logger.error(f"Failed to load GUI setting {key}: {e}")
            return default

    @classmethod
    def load_all_settings(cls) -> Dict[str, Any]:
        """Load all GUI settings.

        This method loads settings from config and merges them with defaults.
        Importantly, it filters out None values from the config to prevent
        them from overriding the default values. This ensures that boolean
        settings like ignore_cache use their default values when not explicitly set.

        Returns:
            Dictionary of all GUI settings with proper defaults
        """
        try:
            settings = ConfigManager.get(cls.get_settings_key(), {})

            # Ensure settings is a dictionary
            if not isinstance(settings, dict):
                logger.warning(
                    "GUI settings in config is not a dictionary, resetting to defaults"
                )
                settings = {}

            # Merge with defaults to ensure all keys exist
            # Only merge non-None values to preserve defaults for None values
            # This is crucial for boolean settings that might be saved as null/None
            merged_settings = cls.DEFAULT_SETTINGS.copy()
            for key, value in settings.items():
                if value is not None:
                    merged_settings[key] = value

            return merged_settings

        except Exception as e:
            logger.error(f"Failed to load GUI settings: {e}")
            return cls.DEFAULT_SETTINGS.copy()

    @classmethod
    def save_all_settings(cls, settings: Dict[str, Any]) -> None:
        """Save all GUI settings.

        Args:
            settings: Dictionary of all GUI settings
        """
        try:
            # Filter out None values and ensure we only save known settings
            # This prevents None values from being saved to config file
            filtered_settings = {}
            for key, value in settings.items():
                if key in cls.DEFAULT_SETTINGS and value is not None:
                    filtered_settings[key] = value

            ConfigManager.set(cls.get_settings_key(), filtered_settings)
            logger.debug(f"Saved all GUI settings: {filtered_settings}")

        except Exception as e:
            logger.error(f"Failed to save GUI settings: {e}")

    @classmethod
    def get_service_setting(cls, available_services: list) -> str:
        """Get the saved service setting with fallback to first available.

        Args:
            available_services: List of available services

        Returns:
            The service name to use
        """
        saved_service = cls.load_setting("service")

        # If no saved service or saved service not available, use first available
        if not saved_service or saved_service not in available_services:
            if available_services:
                return available_services[0]
            return "Google"  # Ultimate fallback

        return saved_service

    @classmethod
    def get_page_range_setting(cls, available_ranges: list) -> str:
        """Get the saved page range setting with fallback to first available.

        Args:
            available_ranges: List of available page ranges

        Returns:
            The page range to use
        """
        saved_range = cls.load_setting("page_range")

        # If no saved range or saved range not available, use first available
        if not saved_range or saved_range not in available_ranges:
            if available_ranges:
                return available_ranges[0]
            return "All"  # Ultimate fallback

        return saved_range

    @classmethod
    def reset_settings(cls) -> None:
        """Reset all GUI settings to defaults."""
        try:
            ConfigManager.delete(cls.get_settings_key())
            logger.info("Reset GUI settings to defaults")
        except Exception as e:
            logger.error(f"Failed to reset GUI settings: {e}")

    @classmethod
    def migrate_old_settings(cls) -> None:
        """Migrate settings from old configuration keys if they exist."""
        try:
            # Check for old individual settings and migrate them
            old_settings_map = {
                "service": "PDF2ZH_SERVICE",
                "lang_from": "PDF2ZH_LANG_FROM",
                "lang_to": "PDF2ZH_LANG_TO",
                "output_dir": "PDF2ZH_OUTPUT_DIR",
                "vfont": "PDF2ZH_VFONT",
            }

            current_settings = cls.load_all_settings()
            migrated_any = False

            for new_key, old_key in old_settings_map.items():
                old_value = ConfigManager.get(old_key)
                if old_value is not None and new_key not in current_settings:
                    current_settings[new_key] = old_value
                    migrated_any = True
                    logger.info(f"Migrated setting {old_key} -> {new_key}: {old_value}")

            if migrated_any:
                cls.save_all_settings(current_settings)

        except Exception as e:
            logger.error(f"Failed to migrate old settings: {e}")
