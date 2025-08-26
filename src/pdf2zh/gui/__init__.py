"""GUI components for PDF translation.

This package provides a modular GUI implementation with better separation
of concerns and improved maintainability.

Architecture:
- config: Configuration constants and settings
- services: Translation service management
- translation: Core translation business logic
- file_manager: File operations and authentication
- components: Reusable UI components
- gui_controller: Main GUI controller that orchestrates everything
- gui: Main entry point for backward compatibility
"""

from .gui import babeldoc_translate_file, setup_gui, stop_translate_file, translate_file

__all__ = [
    "setup_gui",
    "translate_file",
    "stop_translate_file",
    "babeldoc_translate_file",
]
