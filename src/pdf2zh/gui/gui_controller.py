"""Refactored main GUI controller with improved separation of concerns."""

import logging

import gradio as gr
import requests

from .components import (
    action_components,
    event_handlers,
    input_components,
    output_components,
    ui_theme,
)
from .config import GUIConfig
from .file_manager import auth_manager, file_manager
from .translation import (
    TranslationSession,
    stop_translation_session,
    translation_service,
)

logger = logging.getLogger(__name__)


class PDFTranslatorGUI:
    """Main GUI controller that orchestrates all components."""

    def __init__(self):
        self.config = GUIConfig()
        self.demo = None
        self._create_interface()

    def _create_interface(self):
        """Create the main Gradio interface."""
        # Setup theme and head content
        theme = ui_theme.create_theme()
        head_content = (
            self.config.DEMO_RECAPTCHA_SCRIPT if self.config.is_demo_mode() else ""
        )

        with gr.Blocks(
            title="PDFTranslate - PDF Translation with preserved formats",
            theme=theme,
            css=self.config.CUSTOM_CSS,
            head=head_content,
        ) as self.demo:
            # Header
            gr.Markdown(
                "# [PDFTranslate @ GitHub](https://github.com/bajfi/PDFTranslate.git)"
            )

            # Main layout
            with gr.Row():
                # Left column - inputs and controls
                with gr.Column(scale=1):
                    file_components = input_components.create_file_input_section()
                    option_components = input_components.create_translation_options()
                    advanced_components = input_components.create_advanced_options()
                    demo_components = input_components.create_demo_components()
                    action_btns = action_components.create_action_buttons()
                    state_components = action_components.create_state_components()

                # Right column - preview and outputs
                with gr.Column(scale=2):
                    preview_components = output_components.create_preview_section()

            # Output section (below main layout)
            output_components_dict = output_components.create_output_section()

            # Combine all components for easy access
            all_components = {
                **file_components,
                **option_components,
                **advanced_components,
                **demo_components,
                **action_btns,
                **state_components,
                **preview_components,
                **output_components_dict,
            }

            # Setup event handlers
            self._setup_event_handlers(all_components)

    def _setup_event_handlers(self, components):
        """Setup all event handlers for the interface."""

        # Service selection handler
        components["service"].select(
            event_handlers.on_select_service,
            components["service"],
            components["envs"] + [components["prompt"]],
        )

        # File type selection handler
        components["file_type"].select(
            event_handlers.on_select_filetype,
            components["file_type"],
            [components["file_input"], components["link_input"]],
            js=event_handlers.get_recaptcha_js(),
        )

        # Page range selection handler
        components["page_range"].select(
            event_handlers.on_select_page,
            components["page_range"],
            components["page_input"],
        )

        # Language change handlers
        components["lang_from"].change(
            event_handlers.on_lang_from_change,
            inputs=components["lang_from"],
            outputs=None,
        )

        components["lang_to"].change(
            event_handlers.on_lang_to_change,
            inputs=components["lang_to"],
            outputs=None,
        )

        # Advanced options change handlers
        components["threads"].change(
            event_handlers.on_threads_change,
            inputs=components["threads"],
            outputs=None,
        )

        components["skip_subset_fonts"].change(
            event_handlers.on_skip_subset_fonts_change,
            inputs=components["skip_subset_fonts"],
            outputs=None,
        )

        components["ignore_cache"].change(
            event_handlers.on_ignore_cache_change,
            inputs=components["ignore_cache"],
            outputs=None,
        )

        components["use_babeldoc"].change(
            event_handlers.on_use_babeldoc_change,
            inputs=components["use_babeldoc"],
            outputs=None,
        )

        components["prompt"].change(
            event_handlers.on_prompt_change,
            inputs=components["prompt"],
            outputs=None,
        )

        # VFont configuration handler
        components["vfont"].change(
            event_handlers.on_vfont_change, inputs=components["vfont"], outputs=None
        )

        # Output directory change handler
        components["output_dir"].change(
            event_handlers.on_output_dir_change,
            inputs=components["output_dir"],
            outputs=None,
        )

        # Browse output directory handler (no progress needed for file dialog)
        components["browse_output_btn"].click(
            event_handlers.on_browse_output_click,
            inputs=[],
            outputs=components["output_dir"],
            show_progress="hidden",  # Hide progress for folder selection
        )

        # Reset settings handler
        if "reset_settings_btn" in components:
            components["reset_settings_btn"].click(
                event_handlers.on_reset_settings,
                inputs=[],
                outputs=None,
            )

        # File upload handler
        components["file_input"].upload(
            lambda x: x,
            inputs=components["file_input"],
            outputs=components["preview"],
            js=event_handlers.get_recaptcha_js(),
        )

        # Translation button handler
        components["translate_btn"].click(
            self._handle_translation,
            inputs=[
                components["file_type"],
                components["file_input"],
                components["link_input"],
                components["output_dir"],
                components["service"],
                components["lang_from"],
                components["lang_to"],
                components["page_range"],
                components["page_input"],
                components["prompt"],
                components["threads"],
                components["skip_subset_fonts"],
                components["ignore_cache"],
                components["vfont"],
                components["use_babeldoc"],
                components["recaptcha_response"],
                components["state"],
                *components["envs"],
            ],
            outputs=[
                components["output_file_mono"],
                components["preview"],
                components["output_file_dual"],
                components["output_file_mono"],
                components["output_file_dual"],
                components["output_title"],
            ],
        )

        # Cancellation button handler
        components["cancellation_btn"].click(
            self._handle_cancellation,
            inputs=[components["state"]],
        )

    def _handle_translation(
        self,
        file_type,
        file_input,
        link_input,
        output_dir,
        service,
        lang_from,
        lang_to,
        page_range,
        page_input,
        prompt,
        threads,
        skip_subset_fonts,
        ignore_cache,
        vfont,
        use_babeldoc,
        recaptcha_response,
        state,
        progress=gr.Progress(),
        *envs,
    ):
        """Handle translation request with proper error handling and progress updates."""

        # Verify reCAPTCHA if in demo mode
        if self.config.is_demo_mode() and not self._verify_recaptcha(
            recaptcha_response
        ):
            raise gr.Error("reCAPTCHA verification failed")

        # Create new translation session
        session = TranslationSession()
        state["session_id"] = str(session.session_id)

        try:
            progress(0, desc="Starting translation...")

            # Prepare input file
            file_path = file_manager.prepare_input_file(
                file_type, file_input, link_input, output_dir
            )

            # Parse page range
            pages = translation_service.parse_page_range(page_range, page_input)

            # Create progress callback
            def progress_callback(t):
                desc = getattr(t, "desc", "Translating...")
                if desc == "":
                    desc = "Translating..."
                progress(t.n / t.total, desc=desc)

            # Prepare translation parameters
            try:
                threads_int = int(threads)
            except ValueError:
                threads_int = 1

            params = translation_service.prepare_translation_params(
                file_path=file_path,
                service=service,
                lang_from=lang_from,
                lang_to=lang_to,
                pages=pages,
                threads=threads_int,
                prompt=prompt,
                skip_subset_fonts=skip_subset_fonts,
                ignore_cache=ignore_cache,
                vfont=vfont,
                env_values=list(envs),
                session=session,
                output_dir=output_dir,
                callback_fn=progress_callback,
            )

            # Execute translation
            file_mono, _, file_dual = translation_service.translate_pdf(
                params, use_babeldoc
            )

            # Validate output
            if not file_manager.validate_output_files(file_mono, file_dual):
                raise gr.Error("Translation completed but output files not found")

            progress(1.0, desc="Translation complete!")

            # Clean up session
            session.cleanup()

            return (
                str(file_mono),
                str(file_mono),
                str(file_dual),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=True),
            )

        except Exception as e:
            # Clean up session on error
            session.cleanup()
            if "reCAPTCHA" in str(e):
                raise
            elif "cancelled" in str(e).lower():
                raise gr.Error("Translation cancelled")
            else:
                logger.error(f"Translation failed: {e}")
                raise gr.Error(f"Translation failed: {str(e)}")

    def _handle_cancellation(self, state):
        """Handle translation cancellation."""
        session_id = state.get("session_id")
        if session_id:
            stop_translation_session(session_id)

    def _verify_recaptcha(self, response: str) -> bool:
        """Verify reCAPTCHA response for demo mode."""
        if not self.config.is_demo_mode():
            return True

        if not response:
            return False

        recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
        server_key = self.config.get_server_key()
        data = {"secret": server_key, "response": response}

        try:
            result = requests.post(recaptcha_url, data=data, timeout=10).json()
            return result.get("success", False)
        except Exception as e:
            logger.error(f"reCAPTCHA verification failed: {e}")
            return False

    def launch(
        self, share: bool = False, auth_file: list = ["", ""], server_port: int = 7860
    ):
        """Launch the GUI with the given parameters."""

        user_list, html = auth_manager.parse_user_passwd(auth_file)

        # Common launch parameters
        launch_params = {
            "debug": True,
            "inbrowser": True,
            "share": share,
            "server_port": server_port,
        }

        # Demo mode has special handling
        if self.config.is_demo_mode():
            self.demo.launch(server_name="0.0.0.0", max_file_size="5mb", inbrowser=True)
            return

        # Add authentication if provided
        if user_list:
            launch_params.update(
                {
                    "auth": user_list,
                    "auth_message": html,
                }
            )

        # Try different server names with fallback
        server_names = ["0.0.0.0", "127.0.0.1", None]  # None means default

        for server_name in server_names:
            try:
                if server_name:
                    launch_params["server_name"] = server_name
                else:
                    # Remove server_name for default behavior
                    launch_params.pop("server_name", None)
                    launch_params["share"] = True  # Force share for last attempt

                self.demo.launch(**launch_params)
                break

            except Exception as e:
                if server_name == server_names[-1]:  # Last attempt
                    logger.error(f"Failed to launch GUI: {e}")
                    raise
                else:
                    error_msg = f"Error launching GUI using {server_name or 'default'}."
                    if "proxy" in str(e).lower():
                        error_msg += (
                            " This may be caused by global mode of proxy software."
                        )
                    logger.warning(error_msg)
                    continue


# Main functions for backward compatibility
def setup_gui(
    share: bool = False, auth_file: list = ["", ""], server_port=7860
) -> None:
    """Setup and launch the GUI - main entry point."""
    gui = PDFTranslatorGUI()
    gui.launch(share=share, auth_file=auth_file, server_port=server_port)


# Legacy function exports for compatibility
def translate_file(*args, **kwargs):
    """Legacy translation function - redirects to new implementation."""
    gui = PDFTranslatorGUI()
    return gui._handle_translation(*args, **kwargs)


def stop_translate_file(state: dict) -> None:
    """Legacy stop function - redirects to new implementation."""
    session_id = state.get("session_id")
    if session_id:
        stop_translation_session(session_id)


def babeldoc_translate_file(**kwargs):
    """Legacy babeldoc function - now handled within translation service."""
    # This is handled within the translation service now
    # Keep for backward compatibility if needed
    return translation_service.translate_pdf(kwargs, use_babeldoc=True)


# For auto-reloading while developing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    setup_gui()
