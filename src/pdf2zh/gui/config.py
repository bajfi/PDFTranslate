"""GUI Configuration Constants and Mappings."""

import typing as T

from pdf2zh.config import ConfigManager
from pdf2zh.translation.translator import (
    AnythingLLMTranslator,
    ArgosTranslator,
    AzureOpenAITranslator,
    AzureTranslator,
    BaseTranslator,
    BingTranslator,
    DeepLTranslator,
    DeepLXTranslator,
    DeepseekTranslator,
    DifyTranslator,
    GeminiTranslator,
    GoogleTranslator,
    GrokTranslator,
    GroqTranslator,
    ModelScopeTranslator,
    OllamaTranslator,
    OpenAIlikedTranslator,
    OpenAITranslator,
    QwenMtTranslator,
    SiliconTranslator,
    TencentTranslator,
    X302AITranslator,
    XinferenceTranslator,
    ZhipuTranslator,
)


class GUIConfig:
    """Configuration class for GUI settings and mappings."""

    # Service mapping
    SERVICE_MAP: dict[str, BaseTranslator] = {
        "Google": GoogleTranslator,
        "Ollama": OllamaTranslator,
        "Bing": BingTranslator,
        "DeepL": DeepLTranslator,
        "DeepLX": DeepLXTranslator,
        "Xinference": XinferenceTranslator,
        "AzureOpenAI": AzureOpenAITranslator,
        "OpenAI": OpenAITranslator,
        "Zhipu": ZhipuTranslator,
        "ModelScope": ModelScopeTranslator,
        "Silicon": SiliconTranslator,
        "Gemini": GeminiTranslator,
        "Azure": AzureTranslator,
        "Tencent": TencentTranslator,
        "Dify": DifyTranslator,
        "AnythingLLM": AnythingLLMTranslator,
        "Argos Translate": ArgosTranslator,
        "Grok": GrokTranslator,
        "Groq": GroqTranslator,
        "DeepSeek": DeepseekTranslator,
        "OpenAI-liked": OpenAIlikedTranslator,
        "Ali Qwen-Translation": QwenMtTranslator,
        "302.AI": X302AITranslator,
    }

    # Language mapping
    LANGUAGE_MAP = {
        "Simplified Chinese": "zh",
        "Traditional Chinese": "zh-TW",
        "English": "en",
        "French": "fr",
        "German": "de",
        "Japanese": "ja",
        "Korean": "ko",
        "Russian": "ru",
        "Spanish": "es",
        "Italian": "it",
    }

    # Page range mapping
    PAGE_MAP = {
        "All": None,
        "First": [0],
        "First 5 pages": list(range(0, 5)),
        "Others": None,
    }

    # Demo configuration
    DEMO_SERVICE_MAP = {
        "Google": GoogleTranslator,
    }

    DEMO_PAGE_MAP = {
        "First": [0],
        "First 20 pages": list(range(0, 20)),
    }

    # CSS styles
    CUSTOM_CSS = """
        .secondary-text {color: #999 !important;}
        footer {visibility: hidden}
        .env-warning {color: #dd5500 !important;}
        .env-success {color: #559900 !important;}

        /* Add dashed border to input-file class */
        .input-file {
            border: 1.2px dashed #165DFF !important;
            border-radius: 6px !important;
        }

        .progress-bar-wrap {
            border-radius: 8px !important;
        }

        .progress-bar {
            border-radius: 8px !important;
        }

        .pdf-canvas canvas {
            width: 100%;
        }

        /* Elegant Output Settings Styling */
        .section-header {
            margin-bottom: 8px !important;
            color: #2c3e50 !important;
            font-weight: 600 !important;
        }

        .output-row {
            gap: 12px !important;
            align-items: end !important;
            margin: 0 !important;
        }

        .output-textbox {
            border-radius: 8px !important;
            border: 1.5px solid #e1e5e9 !important;
            transition: all 0.2s ease !important;
        }

        /* Universal selector for output textbox to prevent wrapping */
        .output-textbox * {
            white-space: nowrap !important;
            overflow-x: scroll !important;
            overflow-y: hidden !important;
            word-wrap: normal !important;
            word-break: normal !important;
            scrollbar-width: thin !important;
        }

        /* Custom scrollbar styling for webkit browsers */
        .output-textbox input::-webkit-scrollbar,
        .output-textbox textarea::-webkit-scrollbar,
        .output-textbox *::-webkit-scrollbar {
            height: 6px !important;
        }

        .output-textbox input::-webkit-scrollbar-track,
        .output-textbox textarea::-webkit-scrollbar-track,
        .output-textbox *::-webkit-scrollbar-track {
            background: #f1f1f1 !important;
            border-radius: 3px !important;
        }

        .output-textbox input::-webkit-scrollbar-thumb,
        .output-textbox textarea::-webkit-scrollbar-thumb,
        .output-textbox *::-webkit-scrollbar-thumb {
            background: #c1c1c1 !important;
            border-radius: 3px !important;
        }

        .output-textbox input::-webkit-scrollbar-thumb:hover,
        .output-textbox textarea::-webkit-scrollbar-thumb:hover,
        .output-textbox *::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8 !important;
        }

        .output-textbox:focus-within {
            border-color: #165DFF !important;
            box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.1) !important;
        }

        .browse-btn {
            align-self: center !important;
            min-height: 48px !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            margin-right: 12px !important;
            font-size: 14px !important;
        }

        .browse-btn:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        }

        /* Hide processing indicators during folder browse */
        .browse-btn:active + .progress-container {
            display: none !important;
        }
    """

    # reCAPTCHA script for demo
    DEMO_RECAPTCHA_SCRIPT = """
        <script src="https://www.google.com/recaptcha/api.js?render=explicit" async defer></script>
        <script type="text/javascript">
            var onVerify = function(token) {
                el=document.getElementById('verify').getElementsByTagName('textarea')[0];
                el.value=token;
                el.dispatchEvent(new Event('input'));
            };
        </script>
    """

    @classmethod
    def is_demo_mode(cls) -> bool:
        """Check if running in demo mode."""
        return bool(ConfigManager.get("PDF2ZH_DEMO"))

    @classmethod
    def get_client_key(cls) -> str:
        """Get client key for demo mode."""
        return ConfigManager.get("PDF2ZH_CLIENT_KEY", "")

    @classmethod
    def get_server_key(cls) -> str:
        """Get server key for demo mode."""
        return ConfigManager.get("PDF2ZH_SERVER_KEY", "")

    @classmethod
    def get_enabled_services(cls) -> list[str]:
        """Get list of enabled services."""
        enabled_services: T.Optional[T.List[str]] = ConfigManager.get(
            "ENABLED_SERVICES"
        )

        if isinstance(enabled_services, list):
            default_services = ["Google", "Bing"]
            enabled_services_names = [str(_).lower().strip() for _ in enabled_services]
            enabled_services = [
                k
                for k in cls.SERVICE_MAP.keys()
                if str(k).lower().strip() in enabled_services_names
            ]
            if len(enabled_services) == 0:
                raise RuntimeError("No services available.")
            enabled_services = default_services + enabled_services
        else:
            enabled_services = list(cls.SERVICE_MAP.keys())

        return enabled_services

    @classmethod
    def should_hide_gradio_details(cls) -> bool:
        """Check if Gradio details should be hidden."""
        return bool(ConfigManager.get("HIDDEN_GRADIO_DETAILS"))

    @classmethod
    def get_default_lang_from(cls) -> str:
        """Get default source language."""
        return ConfigManager.get("PDF2ZH_LANG_FROM", "English")

    @classmethod
    def get_default_lang_to(cls) -> str:
        """Get default target language."""
        return ConfigManager.get("PDF2ZH_LANG_TO", "Simplified Chinese")

    @classmethod
    def get_default_vfont(cls) -> str:
        """Get default vfont regex."""
        return ConfigManager.get("PDF2ZH_VFONT", "")

    @classmethod
    def get_service_map(cls) -> dict[str, BaseTranslator]:
        """Get the appropriate service map based on demo mode."""
        return cls.DEMO_SERVICE_MAP if cls.is_demo_mode() else cls.SERVICE_MAP

    @classmethod
    def get_page_map(cls) -> dict:
        """Get the appropriate page map based on demo mode."""
        return cls.DEMO_PAGE_MAP if cls.is_demo_mode() else cls.PAGE_MAP
