"""
PDF Translator GUI - Refactored for better maintainability.

This module now serves as the main entry point that delegates to the
refactored components for improved separation of concerns.
"""

# Import the refactored GUI controller
from .gui_controller import (
    babeldoc_translate_file,
    setup_gui,
    stop_translate_file,
    translate_file,
)

# Re-export for backward compatibility
__all__ = [
    "setup_gui",
    "translate_file",
    "stop_translate_file",
    "babeldoc_translate_file",
]

# For auto-reloading while developing
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    setup_gui()
