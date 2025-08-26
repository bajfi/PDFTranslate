"""Translation business logic separated from UI concerns."""

import asyncio
import logging
import os
import uuid
from asyncio import CancelledError
from pathlib import Path
from string import Template

from babeldoc.docvision.doclayout import OnnxModel
from pdf2zh.core.doclayout import ModelInstance
from pdf2zh.high_level import translate
from pdf2zh.translation.translator import OpenAITranslator

from .config import GUIConfig
from .services import service_manager

logger = logging.getLogger(__name__)

# Global state for translation cancellation
cancellation_event_map = {}

# BabelDoc model initialization
BABELDOC_MODEL = OnnxModel.load_available()


class TranslationSession:
    """Manages a single translation session."""

    def __init__(self):
        self.session_id = uuid.uuid4()
        self.cancellation_event = asyncio.Event()
        cancellation_event_map[self.session_id] = self.cancellation_event

    def cancel(self):
        """Cancel the translation session."""
        logger.info(f"Stopping translation for session {self.session_id}")
        self.cancellation_event.set()

    def cleanup(self):
        """Clean up the session."""
        if self.session_id in cancellation_event_map:
            del cancellation_event_map[self.session_id]


class TranslationService:
    """Handles the core translation logic."""

    def __init__(self):
        self.config = GUIConfig()

    def parse_page_range(self, page_range: str, page_input: str) -> list:
        """Parse page range selection into a list of page indices."""
        page_map = self.config.get_page_map()

        if page_range != "Others":
            return page_map[page_range]

        selected_page = []
        for p in page_input.split(","):
            if "-" in p:
                start, end = p.split("-")
                selected_page.extend(range(int(start) - 1, int(end)))
            else:
                selected_page.append(int(p) - 1)
        return selected_page

    def prepare_translation_params(
        self,
        file_path: str,
        service: str,
        lang_from: str,
        lang_to: str,
        pages: list,
        threads: int,
        prompt: str,
        skip_subset_fonts: bool,
        ignore_cache: bool,
        vfont: str,
        env_values: list,
        session: TranslationSession,
        output_dir: str = None,
        callback_fn=None,
    ) -> dict:
        """Prepare parameters for translation."""

        # Setup output directory with custom path if provided
        if output_dir and output_dir.strip():
            output = Path(output_dir)
        else:
            output = Path("pdf2zh_files")
        output.mkdir(parents=True, exist_ok=True)

        # Get translator and prepare environment
        translator_class = service_manager.get_translator_class(service)
        _envs = service_manager.prepare_translator_envs(service, env_values)

        # Convert language codes
        lang_from = self.config.LANGUAGE_MAP[lang_from]
        lang_to = self.config.LANGUAGE_MAP[lang_to]

        return {
            "files": [str(file_path)],
            "pages": pages,
            "lang_in": lang_from,
            "lang_out": lang_to,
            "service": translator_class.name,
            "output": output,
            "thread": int(threads),
            "callback": callback_fn,
            "cancellation_event": session.cancellation_event,
            "envs": _envs,
            "prompt": Template(prompt) if prompt else None,
            "skip_subset_fonts": skip_subset_fonts,
            "ignore_cache": ignore_cache,
            "vfont": vfont,
            "model": ModelInstance.value,
        }

    def translate_pdf(
        self, params: dict, use_babeldoc: bool = False
    ) -> tuple[str, str, str]:
        """Execute the PDF translation."""
        try:
            if use_babeldoc:
                return self._babeldoc_translate(**params)
            else:
                translate(**params)
                return self._get_output_files(params["files"][0], params["output"])
        except CancelledError:
            raise
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    def _get_output_files(
        self, input_file: str, output_dir: Path
    ) -> tuple[str, str, str]:
        """Get the output file paths after translation."""
        filename = os.path.splitext(os.path.basename(input_file))[0]
        file_mono = output_dir / f"{filename}-mono.pdf"
        file_dual = output_dir / f"{filename}-dual.pdf"

        if not file_mono.exists() or not file_dual.exists():
            raise RuntimeError("Translation output files not found")

        return str(file_mono), str(file_mono), str(file_dual)

    def _babeldoc_translate(self, **kwargs) -> tuple[str, str, str]:
        """Execute translation using BabelDoc."""
        from babeldoc.high_level import init as babeldoc_init

        babeldoc_init()

        from babeldoc.high_level import async_translate as babeldoc_translate
        from babeldoc.main import create_progress_handler
        from babeldoc.translation_config import TranslationConfig as YadtConfig

        # Get translator instance
        translator = None
        for translator_class in service_manager.get_all_translator_classes():
            if kwargs["service"] == translator_class.name:
                translator = service_manager.create_translator_instance(
                    kwargs["service"],
                    kwargs["lang_in"],
                    kwargs["lang_out"],
                    kwargs["envs"],
                    kwargs["prompt"],
                    kwargs["ignore_cache"],
                )
                break

        if translator is None:
            raise ValueError("Unsupported translation service")

        # Process each file
        for file in kwargs["files"]:
            file = file.strip("\"'")
            yadt_config = YadtConfig(
                input_file=file,
                font=None,
                pages=",".join((str(x) for x in getattr(kwargs, "raw_pages", []))),
                output_dir=kwargs["output"],
                doc_layout_model=BABELDOC_MODEL,
                translator=translator,
                debug=False,
                lang_in=kwargs["lang_in"],
                lang_out=kwargs["lang_out"],
                no_dual=False,
                no_mono=False,
                qps=kwargs["thread"],
                use_rich_pbar=False,
                disable_rich_text_translate=not isinstance(
                    translator, OpenAITranslator
                ),
                skip_clean=kwargs["skip_subset_fonts"],
                report_interval=0.5,
            )

            async def yadt_translate_coro(yadt_config):
                progress_context, progress_handler = create_progress_handler(
                    yadt_config
                )

                with progress_context:
                    async for event in babeldoc_translate(yadt_config):
                        progress_handler(event)
                        if yadt_config.debug:
                            logger.debug(event)
                        if kwargs["callback"]:
                            kwargs["callback"](progress_context)
                        if kwargs["cancellation_event"].is_set():
                            yadt_config.cancel_translation()
                            raise CancelledError
                        if event["type"] == "finish":
                            result = event["translate_result"]
                            logger.info("Translation Result:")
                            logger.info(f"  Original PDF: {result.original_pdf_path}")
                            logger.info(f"  Time Cost: {result.total_seconds:.2f}s")
                            logger.info(f"  Mono PDF: {result.mono_pdf_path or 'None'}")
                            logger.info(f"  Dual PDF: {result.dual_pdf_path or 'None'}")
                            return (
                                str(result.mono_pdf_path),
                                str(result.mono_pdf_path),
                                str(result.dual_pdf_path),
                            )

                import gc

                gc.collect()

            return asyncio.run(yadt_translate_coro(yadt_config))


def stop_translation_session(session_id: str) -> None:
    """Stop a translation session by its ID."""
    if session_id and session_id in cancellation_event_map:
        logger.info(f"Stopping translation for session {session_id}")
        cancellation_event_map[session_id].set()


# Global service instance
translation_service = TranslationService()
