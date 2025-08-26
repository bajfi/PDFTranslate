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

    def create_file_input_section(self):
        """Create file input section."""
        components = {}

        demo_label = "## File | < 5 MB" if self.config.is_demo_mode() else "## File"
        gr.Markdown(demo_label)

        components["file_type"] = gr.Radio(
            choices=["File", "Link"],
            label="Type",
            value="File",
        )

        components["file_input"] = gr.File(
            label="File",
            file_count="single",
            file_types=[".pdf"],
            type="filepath",
            elem_classes=["input-file"],
        )

        components["link_input"] = gr.Textbox(
            label="Link",
            visible=False,
            interactive=True,
        )

        return components

    def create_translation_options(self):
        """Create translation options section."""
        components = {}

        gr.Markdown("## Option")

        enabled_services = self.config.get_enabled_services()
        components["service"] = gr.Dropdown(
            label="Service",
            choices=enabled_services,
            value=enabled_services[0],
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

        # Language selection
        with gr.Row():
            components["lang_from"] = gr.Dropdown(
                label="Translate from",
                choices=list(self.config.LANGUAGE_MAP.keys()),
                value=self.config.get_default_lang_from(),
            )
            components["lang_to"] = gr.Dropdown(
                label="Translate to",
                choices=list(self.config.LANGUAGE_MAP.keys()),
                value=self.config.get_default_lang_to(),
            )

        # Page range selection
        page_choices = list(self.config.get_page_map().keys())
        components["page_range"] = gr.Radio(
            choices=page_choices,
            label="Pages",
            value=page_choices[0],
        )

        components["page_input"] = gr.Textbox(
            label="Page range",
            visible=False,
            interactive=True,
        )

        return components

    def create_advanced_options(self):
        """Create advanced options accordion."""
        components = {}

        with gr.Accordion("Open for More Experimental Options!", open=False):
            gr.Markdown("#### Experimental")

            components["threads"] = gr.Textbox(
                label="number of threads", interactive=True, value="4"
            )

            components["skip_subset_fonts"] = gr.Checkbox(
                label="Skip font subsetting", interactive=True, value=False
            )

            components["ignore_cache"] = gr.Checkbox(
                label="Ignore cache", interactive=True, value=True
            )

            components["vfont"] = gr.Textbox(
                label="Custom formula font regex (vfont)",
                interactive=True,
                value=self.config.get_default_vfont(),
            )

            components["prompt"] = gr.Textbox(
                label="Custom Prompt for llm", interactive=True, visible=False
            )

            components["use_babeldoc"] = gr.Checkbox(
                label="Use BabelDOC", interactive=True, value=False
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
        return (
            gr.update(visible=file_type == "File"),
            gr.update(visible=file_type == "Link"),
        )

    def on_select_page(self, choice):
        """Handle page range selection change."""
        if choice == "Others":
            return gr.update(visible=True)
        else:
            return gr.update(visible=False)

    def on_vfont_change(self, value):
        """Handle vfont configuration change."""
        from pdf2zh.config import ConfigManager

        ConfigManager.set("PDF2ZH_VFONT", value)
        return value

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
