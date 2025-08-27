"""UI components for the PDF translator GUI."""

import gradio as gr
from gradio_pdf import PDF

from .config import GUIConfig
from .services import service_manager


class UITheme:
    """Manages UI theming and styling."""

    def __init__(self):
        self.config = GUIConfig()

    def get_custom_blue_theme(self):
        """Get custom blue color theme."""
        return gr.themes.Color(
            c50="#E8F3FF",
            c100="#BEDAFF",
            c200="#94BFFF",
            c300="#6AA1FF",
            c400="#4080FF",
            c500="#165DFF",  # Primary color
            c600="#0E42D2",
            c700="#0A2BA6",
            c800="#061D79",
            c900="#03114D",
            c950="#020B33",
        )

    def create_theme(self):
        """Create the main theme for the application."""
        return gr.themes.Default(
            primary_hue=self.get_custom_blue_theme(),
            spacing_size="md",
            radius_size="lg",
        )


class InputComponents:
    """Creates input-related UI components."""

    def __init__(self):
        self.config = GUIConfig()
        # Migrate old settings when initializing
        from .settings_manager import GUISettingsManager

        GUISettingsManager.migrate_old_settings()

    def create_file_input_section(self):
        """Create file input section."""
        from .settings_manager import GUISettingsManager

        components = {}

        demo_label = "## File | < 5 MB" if self.config.is_demo_mode() else "## File"
        gr.Markdown(demo_label)

        # Load saved file type
        saved_file_type = GUISettingsManager.load_setting("file_type", "File")

        components["file_type"] = gr.Radio(
            choices=["File", "Link"],
            label="Type",
            value=saved_file_type,
        )

        components["file_input"] = gr.File(
            label="File",
            file_count="single",
            file_types=[".pdf"],
            type="filepath",
            elem_classes=["input-file"],
            visible=saved_file_type == "File",
        )

        components["link_input"] = gr.Textbox(
            label="Link",
            visible=saved_file_type == "Link",
            interactive=True,
        )

        # Load saved output directory
        saved_output_dir = GUISettingsManager.load_setting("output_dir", "pdf2zh_files")

        # Output directory section - cleaner layout
        with gr.Group():
            gr.Markdown("### Output Settings", elem_classes=["section-header"])
            with gr.Row(elem_classes=["output-row"]):
                components["output_dir"] = gr.Textbox(
                    label="📁 Output Directory",
                    value=saved_output_dir,
                    placeholder="Choose where to save your translated files...",
                    interactive=True,
                    scale=4,
                    elem_classes=["output-textbox"],
                )
                components["browse_output_btn"] = gr.Button(
                    "Browse",
                    size="md",
                    scale=1,
                    variant="secondary",
                    elem_classes=["browse-btn"],
                )

        return components

    def create_translation_options(self):
        """Create translation options section."""
        from .settings_manager import GUISettingsManager

        components = {}

        gr.Markdown("## Option")

        enabled_services = self.config.get_enabled_services()
        saved_service = GUISettingsManager.get_service_setting(enabled_services)

        components["service"] = gr.Dropdown(
            label="Service",
            choices=enabled_services,
            value=saved_service,
        )

        # Environment variable inputs (initially hidden)
        components["envs"] = []
        for i in range(3):
            components["envs"].append(
                gr.Textbox(
                    visible=False,
                    interactive=True,
                )
            )

        # Load saved languages
        saved_lang_from = GUISettingsManager.load_setting(
            "lang_from", self.config.get_default_lang_from()
        )
        saved_lang_to = GUISettingsManager.load_setting(
            "lang_to", self.config.get_default_lang_to()
        )

        # Language selection
        with gr.Row():
            components["lang_from"] = gr.Dropdown(
                label="Translate from",
                choices=list(self.config.LANGUAGE_MAP.keys()),
                value=saved_lang_from,
            )
            components["lang_to"] = gr.Dropdown(
                label="Translate to",
                choices=list(self.config.LANGUAGE_MAP.keys()),
                value=saved_lang_to,
            )

        # Page range selection
        page_choices = list(self.config.get_page_map().keys())
        saved_page_range = GUISettingsManager.get_page_range_setting(page_choices)

        components["page_range"] = gr.Radio(
            choices=page_choices,
            label="Pages",
            value=saved_page_range,
        )

        components["page_input"] = gr.Textbox(
            label="Page range",
            visible=saved_page_range == "Others",
            interactive=True,
        )

        return components

    def create_advanced_options(self):
        """Create advanced options accordion."""
        import multiprocessing

        from .settings_manager import GUISettingsManager

        components = {}

        # Load saved advanced settings
        saved_threads = GUISettingsManager.load_setting("threads", "4")
        # Convert saved threads to integer, with fallback to 4
        try:
            saved_threads_int = int(saved_threads)
        except (ValueError, TypeError):
            saved_threads_int = 4

        saved_skip_subset_fonts = GUISettingsManager.load_setting(
            "skip_subset_fonts", False
        )
        saved_ignore_cache = GUISettingsManager.load_setting("ignore_cache", True)
        saved_vfont = GUISettingsManager.load_setting(
            "vfont", self.config.get_default_vfont()
        )
        saved_use_babeldoc = GUISettingsManager.load_setting("use_babeldoc", False)
        saved_prompt = GUISettingsManager.load_setting("prompt", "")

        # Calculate reasonable max threads (2x CPU cores,)
        cpu_cores = multiprocessing.cpu_count()
        max_threads = cpu_cores * 2

        with gr.Accordion("Open for More Experimental Options!", open=False):
            gr.Markdown("#### Experimental")

            components["threads"] = gr.Slider(
                minimum=1,
                maximum=max_threads,
                step=1,
                label=f"Number of threads (1-{max_threads}, detected {cpu_cores} CPU cores)",
                value=min(
                    saved_threads_int, max_threads
                ),  # Ensure value is within range
                interactive=True,
            )

            components["skip_subset_fonts"] = gr.Checkbox(
                label="Skip font subsetting",
                interactive=True,
                value=saved_skip_subset_fonts,
            )

            components["ignore_cache"] = gr.Checkbox(
                label="Ignore cache", interactive=True, value=saved_ignore_cache
            )

            components["vfont"] = gr.Textbox(
                label="Custom formula font regex (vfont)",
                interactive=True,
                value=saved_vfont,
            )

            components["prompt"] = gr.Textbox(
                label="Custom Prompt for llm",
                interactive=True,
                visible=False,
                value=saved_prompt,
            )

            components["use_babeldoc"] = gr.Checkbox(
                label="Use BabelDOC", interactive=True, value=saved_use_babeldoc
            )

            # Settings management section
            gr.Markdown("#### Settings Management")
            components["reset_settings_btn"] = gr.Button(
                "Reset All Settings to Defaults",
                variant="secondary",
                size="sm",
            )

        return components

    def create_demo_components(self):
        """Create demo-specific components (reCAPTCHA)."""
        components = {}

        if self.config.is_demo_mode():
            components["recaptcha_response"] = gr.Textbox(
                label="reCAPTCHA Response", elem_id="verify", visible=False
            )
            components["recaptcha_box"] = gr.HTML('<div id="recaptcha-box"></div>')
        else:
            components["recaptcha_response"] = gr.Textbox(visible=False)
            components["recaptcha_box"] = gr.HTML("")

        return components


class OutputComponents:
    """Creates output-related UI components."""

    def create_output_section(self):
        """Create output file section."""
        components = {}

        components["output_title"] = gr.Markdown("## Translated", visible=False)
        components["output_file_mono"] = gr.File(
            label="Download Translation (Mono)", visible=False
        )
        components["output_file_dual"] = gr.File(
            label="Download Translation (Dual)", visible=False
        )

        return components

    def create_preview_section(self):
        """Create PDF preview section."""
        components = {}

        gr.Markdown("## Preview")
        components["preview"] = PDF(label="Document Preview", visible=True, height=2000)

        return components


class ActionComponents:
    """Creates action buttons and controls."""

    def create_action_buttons(self):
        """Create action buttons."""
        components = {}

        components["translate_btn"] = gr.Button("Translate", variant="primary")
        components["cancellation_btn"] = gr.Button("Cancel", variant="secondary")

        return components

    def create_state_components(self):
        """Create state management components."""
        components = {}

        components["state"] = gr.State({"session_id": None})

        return components


class EventHandlers:
    """Manages UI event handlers and callbacks."""

    def __init__(self):
        self.config = GUIConfig()

    def on_select_service(self, service, evt: gr.EventData):
        """Handle service selection change."""
        # Save the selected service
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("service", service)

        hidden_details = self.config.should_hide_gradio_details()
        env_updates = service_manager.get_service_config_for_gradio(
            service, hidden_details
        )

        # Convert to gradio updates
        gradio_updates = []
        for update_data in env_updates[:-1]:  # Skip the last one (prompt)
            gradio_updates.append(gr.update(**update_data))

        # Handle prompt visibility
        prompt_update = env_updates[-1]
        gradio_updates.append(gr.update(**prompt_update))

        return gradio_updates

    def on_select_filetype(self, file_type):
        """Handle file type selection change."""
        # Save the selected file type
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("file_type", file_type)

        return (
            gr.update(visible=file_type == "File"),
            gr.update(visible=file_type == "Link"),
        )

    def on_select_page(self, choice):
        """Handle page range selection change."""
        # Save the selected page range
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("page_range", choice)

        if choice == "Others":
            return gr.update(visible=True)
        else:
            return gr.update(visible=False)

    def on_vfont_change(self, value):
        """Handle vfont configuration change."""
        # Save vfont to both old and new locations for compatibility
        from pdf2zh.config import ConfigManager

        from .settings_manager import GUISettingsManager

        ConfigManager.set("PDF2ZH_VFONT", value)
        GUISettingsManager.save_setting("vfont", value)
        # Don't return anything since outputs=None in the handler

    def on_output_dir_change(self, output_dir):
        """Handle output directory change."""
        from .file_manager import file_manager
        from .settings_manager import GUISettingsManager

        # Save the output directory
        GUISettingsManager.save_setting("output_dir", output_dir)

        # Update the file manager's output directory
        file_manager.set_output_directory(output_dir)
        # Don't return anything since outputs=None in the handler

    def on_lang_from_change(self, lang_from):
        """Handle source language change."""
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("lang_from", lang_from)
        # Don't return anything since outputs=None in the handler

    def on_lang_to_change(self, lang_to):
        """Handle target language change."""
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("lang_to", lang_to)
        # Don't return anything since outputs=None in the handler

    def on_threads_change(self, threads):
        """Handle threads setting change."""
        from .settings_manager import GUISettingsManager

        # Convert to string for consistent storage
        threads_str = str(int(threads)) if threads is not None else "4"
        GUISettingsManager.save_setting("threads", threads_str)
        # Don't return anything since outputs=None in the handler

    def on_skip_subset_fonts_change(self, skip_subset_fonts):
        """Handle skip subset fonts setting change."""
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("skip_subset_fonts", skip_subset_fonts)
        # Don't return anything since outputs=None in the handler

    def on_ignore_cache_change(self, ignore_cache):
        """Handle ignore cache setting change."""
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("ignore_cache", ignore_cache)
        # Don't return anything since outputs=None in the handler

    def on_use_babeldoc_change(self, use_babeldoc):
        """Handle use babeldoc setting change."""
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("use_babeldoc", use_babeldoc)
        # Don't return anything since outputs=None in the handler

    def on_prompt_change(self, prompt):
        """Handle custom prompt change."""
        from .settings_manager import GUISettingsManager

        GUISettingsManager.save_setting("prompt", prompt)
        # Don't return anything since outputs=None in the handler

    def on_reset_settings(self):
        """Handle reset settings button click."""
        from .settings_manager import GUISettingsManager

        try:
            GUISettingsManager.reset_settings()
            gr.Info(
                "✅ Settings have been reset to defaults. Please refresh the page to see the changes."
            )
        except Exception as e:
            gr.Warning(f"❌ Failed to reset settings: {str(e)}")
        # Don't return anything since outputs=None in the handler

    def on_browse_output_click(self):
        """Handle browse button click for output directory."""
        import gradio as gr

        try:
            import os
            import tkinter as tk
            from tkinter import filedialog

            # Create a root window but don't show it
            root = tk.Tk()
            root.withdraw()

            # Make sure it appears on top
            root.attributes("-topmost", True)
            root.focus_force()

            # Open directory selection dialog
            directory = filedialog.askdirectory(
                title="Select Output Directory for Translated Files",
                initialdir=os.path.expanduser("~"),
            )

            # Destroy the root window
            root.destroy()

            if directory:
                # Provide user feedback
                return gr.update(value=directory)
            # User cancelled - no change
            return gr.update()

        except Exception as e:
            # If tkinter fails for other reasons
            gr.Warning(
                f"❌ Directory selection failed: {str(e)}. Please type the path manually."
            )
            return gr.update()

    def get_recaptcha_js(self):
        """Get reCAPTCHA JavaScript for demo mode."""
        if not self.config.is_demo_mode():
            return ""

        client_key = self.config.get_client_key()
        return f"""
        (a,b)=>{{
            try{{
                grecaptcha.render('recaptcha-box',{{
                    'sitekey':'{client_key}',
                    'callback':'onVerify'
                }});
            }}catch(error){{}}
            return [a];
        }}
        """

    def get_reset_recaptcha_js(self):
        """Get JavaScript to reset reCAPTCHA after translation."""
        if not self.config.is_demo_mode():
            return ""

        return "()=>{grecaptcha.reset()}"


# Global instances for easy access
ui_theme = UITheme()
input_components = InputComponents()
output_components = OutputComponents()
action_components = ActionComponents()
event_handlers = EventHandlers()
event_handlers = EventHandlers()
