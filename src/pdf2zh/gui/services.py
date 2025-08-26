"""Service management for translation services."""

from pdf2zh.config import ConfigManager
from pdf2zh.translation.translator import BaseTranslator

from .config import GUIConfig


class ServiceManager:
    """Manages translation services and their configurations."""

    def __init__(self):
        self.config = GUIConfig()
        self._enabled_services = None

    @property
    def enabled_services(self) -> list[str]:
        """Get list of enabled services, cached after first access."""
        if self._enabled_services is None:
            self._enabled_services = self.config.get_enabled_services()
        return self._enabled_services

    def get_translator_class(self, service_name: str) -> BaseTranslator:
        """Get translator class by service name."""
        service_map = self.config.get_service_map()
        if service_name not in service_map:
            raise ValueError(f"Unknown service: {service_name}")
        return service_map[service_name]

    def get_translator_envs(self, service_name: str) -> dict:
        """Get environment variables configuration for a translator."""
        translator_class = self.get_translator_class(service_name)
        return translator_class.envs

    def prepare_translator_envs(self, service_name: str, env_values: list) -> dict:
        """Prepare environment variables for translator instantiation."""
        translator_class = self.get_translator_class(service_name)

        _envs = {}
        for i, (env_key, default_value) in enumerate(translator_class.envs.items()):
            if i < len(env_values):
                _envs[env_key] = env_values[i]
            else:
                _envs[env_key] = default_value

        # Handle API key substitution
        for k, v in _envs.items():
            if str(k).upper().endswith("API_KEY") and str(v) == "***":
                # Load Real API_KEYs from local configure file
                real_keys: str = ConfigManager.get_env_by_translatername(
                    translator_class, k, None
                )
                _envs[k] = real_keys

        return _envs

    def create_translator_instance(
        self,
        service_name: str,
        lang_from: str,
        lang_to: str,
        envs: dict,
        prompt=None,
        ignore_cache: bool = True,
    ) -> BaseTranslator:
        """Create a translator instance with the given parameters."""
        translator_class = self.get_translator_class(service_name)
        return translator_class(
            lang_from,
            lang_to,
            "",
            envs=envs,
            prompt=prompt,
            ignore_cache=ignore_cache,
        )

    def get_service_config_for_gradio(
        self, service_name: str, hidden_details: bool = False
    ) -> list:
        """Get service configuration formatted for Gradio updates."""
        translator_class = self.get_translator_class(service_name)

        _envs = []
        for i in range(4):  # Maximum 4 environment variables
            _envs.append({"visible": False, "value": ""})

        for i, (env_key, default_value) in enumerate(translator_class.envs.items()):
            if i >= 4:  # Limit to 4 environment variables
                break

            label = env_key
            value = ConfigManager.get_env_by_translatername(
                translator_class, env_key, default_value
            )
            visible = True

            if hidden_details:
                if "MODEL" not in str(label).upper() and value and hidden_details:
                    visible = False
                # Hidden Keys From Gradio
                if "API_KEY" in label.upper():
                    value = "***"  # We use "***" Present Real API_KEY

            _envs[i] = {
                "visible": visible,
                "label": label,
                "value": value,
            }

        # Handle custom prompt visibility
        if hasattr(translator_class, "CustomPrompt"):
            _envs.append({"visible": translator_class.CustomPrompt})
        else:
            _envs.append({"visible": False})

        return _envs

    def get_all_translator_classes(self) -> list[BaseTranslator]:
        """Get all available translator classes."""
        service_map = self.config.get_service_map()
        return list(service_map.values())


# Global instance
service_manager = ServiceManager()
