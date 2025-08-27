"""
Document processing classes for PDF translation.

This module provides classes for managing PDF document processing,
page selection, and translation workflows in a more maintainable way.
"""

import asyncio
import gc
import io
import logging
from asyncio import CancelledError
from string import Template
from typing import Any, BinaryIO, Dict, List, Optional, Set, Tuple

import numpy as np
import pymupdf
import tqdm
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pymupdf import Document, Font

from pdf2zh.core.doclayout import OnnxModel
from pdf2zh.core.pdfinterp import PDFPageInterpreterEx

logger = logging.getLogger(__name__)


class PageSelector:
    """Handles page selection logic and validation."""

    def __init__(self, total_pages: int):
        self.total_pages = total_pages

    def normalize_pages(
        self, pages: Optional[List[int]] = None
    ) -> Tuple[Set[int], Set[int]]:
        """
        Normalize page selection and return sets of pages to translate and preserve.

        Args:
            pages: List of page indices to translate (0-based). If None, translate all pages.

        Returns:
            Tuple of (pages_to_translate, pages_to_preserve)
        """
        if pages is None:
            # Translate all pages
            pages_to_translate = set(range(self.total_pages))
            pages_to_preserve = set()
        else:
            # Validate page indices
            valid_pages = set()
            for page_idx in pages:
                if 0 <= page_idx < self.total_pages:
                    valid_pages.add(page_idx)
                else:
                    logger.warning(
                        f"Page index {page_idx} is out of range [0, {self.total_pages - 1}]"
                    )

            pages_to_translate = valid_pages
            pages_to_preserve = set(range(self.total_pages)) - pages_to_translate

        logger.info(
            f"Will translate {len(pages_to_translate)} pages, preserve {len(pages_to_preserve)} pages"
        )
        return pages_to_translate, pages_to_preserve


class FontManager:
    """Manages font installation and configuration for PDF documents."""

    def __init__(self, lang_out: str):
        self.lang_out = lang_out.lower()
        self.font_list = [("tiro", None)]
        self._setup_fonts()

    def _setup_fonts(self):
        """Setup fonts for the target language."""
        from pdf2zh.utils.font_utils import NOTO_NAME, download_remote_fonts

        font_path = download_remote_fonts(self.lang_out)
        noto = Font(NOTO_NAME, font_path)
        self.font_list.append((NOTO_NAME, font_path))
        self.noto_name = NOTO_NAME
        self.noto = noto

    def install_fonts_to_document(self, doc: Document) -> Dict[str, int]:
        """Install fonts to all pages in the document."""
        font_id = {}
        for page in doc:
            for font in self.font_list:
                font_id[font[0]] = page.insert_font(font[0], font[1])
        return font_id

    def apply_fonts_to_resources(self, doc: Document, font_id: Dict[str, int]):
        """Apply fonts to document resources."""
        import re

        xreflen = doc.xref_length()
        for xref in range(1, xreflen):
            for label in ["Resources/", ""]:  # 可能是基于 xobj 的 res
                try:  # xref 读写可能出错
                    font_res = doc.xref_get_key(xref, f"{label}Font")
                    target_key_prefix = f"{label}Font/"
                    if font_res[0] == "xref":
                        resource_xref_id = re.search("(\\d+) 0 R", font_res[1]).group(1)
                        xref = int(resource_xref_id)
                        font_res = ("dict", doc.xref_object(xref))
                        target_key_prefix = ""

                    if font_res[0] == "dict":
                        for font in self.font_list:
                            target_key = f"{target_key_prefix}{font[0]}"
                            font_exist = doc.xref_get_key(xref, target_key)
                            if font_exist[0] == "null":
                                doc.xref_set_key(
                                    xref,
                                    target_key,
                                    f"{font_id[font[0]]} 0 R",
                                )
                except Exception:
                    pass


class PDFDocumentProcessor:
    """Main class for processing PDF documents with translation."""

    def __init__(
        self,
        stream: bytes,
        lang_out: str,
        chunk_size: int = 20,
        skip_subset_fonts: bool = False,
    ):
        self.original_stream = stream
        self.lang_out = lang_out
        self.chunk_size = chunk_size
        self.skip_subset_fonts = skip_subset_fonts

        # Initialize document
        self.doc_original = Document(stream=stream)
        self.total_pages = self.doc_original.page_count

        # Initialize components
        self.page_selector = PageSelector(self.total_pages)
        self.font_manager = FontManager(lang_out)

        logger.info(
            f"Initialized PDF processor for document with {self.total_pages} pages"
        )

    def process_document(
        self,
        pages: Optional[List[int]] = None,
        progress_callback=None,
        **translation_kwargs,
    ) -> Tuple[bytes, bytes]:
        """
        Process the document with translation, preserving all pages.

        Args:
            pages: List of page indices to translate. If None, translate all pages.
            progress_callback: Optional callback for progress updates.
            **translation_kwargs: Additional arguments for translation.

        Returns:
            Tuple of (mono_pdf_bytes, dual_pdf_bytes)
        """
        pages_to_translate, pages_to_preserve = self.page_selector.normalize_pages(
            pages
        )

        # Create output documents for all pages
        doc_mono_final = Document()
        doc_dual_final = Document()

        # First, add all original pages to both documents
        for page_idx in range(self.total_pages):
            doc_mono_final.insert_pdf(
                self.doc_original, from_page=page_idx, to_page=page_idx
            )
            doc_dual_final.insert_pdf(
                self.doc_original, from_page=page_idx, to_page=page_idx
            )

        if pages_to_translate:
            # Process translation for selected pages
            translated_pages = self._translate_pages(
                list(pages_to_translate), progress_callback, **translation_kwargs
            )

            # Replace translated pages in documents
            self._replace_translated_pages(
                doc_mono_final, doc_dual_final, translated_pages
            )

        # Create final outputs
        mono_bytes = doc_mono_final.write(deflate=True, garbage=3, use_objstms=1)
        dual_bytes = self._create_dual_document(doc_dual_final, doc_mono_final)

        # Cleanup
        doc_mono_final.close()
        doc_dual_final.close()

        logger.info("Document processing complete")

        return mono_bytes, dual_bytes

    def _translate_pages(
        self,
        pages_to_translate: List[int],
        progress_callback=None,
        **translation_kwargs,
    ) -> Dict[int, Document]:
        """
        Translate specific pages and return them as a dictionary.

        Args:
            pages_to_translate: List of page indices to translate.
            progress_callback: Optional callback for progress updates.
            **translation_kwargs: Additional arguments for translation.

        Returns:
            Dictionary mapping page_idx to translated Document (single page).
        """

        translated_pages = {}

        # Process pages in chunks to manage memory
        page_chunks = [
            pages_to_translate[i : i + self.chunk_size]
            for i in range(0, len(pages_to_translate), self.chunk_size)
        ]

        total_pages_to_translate = len(pages_to_translate)

        with tqdm.tqdm(
            total=total_pages_to_translate, desc="Translating pages"
        ) as progress_bar:
            for chunk_pages in page_chunks:
                if (
                    translation_kwargs.get("cancellation_event")
                    and translation_kwargs["cancellation_event"].is_set()
                ):
                    from asyncio import CancelledError

                    raise CancelledError("Translation cancelled")

                # Create working copy for this chunk
                temp_stream = io.BytesIO()
                self.doc_original.save(temp_stream)
                temp_stream.seek(0)
                doc_working = Document(stream=temp_stream)

                # Setup fonts
                font_id = self.font_manager.install_fonts_to_document(doc_working)
                self.font_manager.apply_fonts_to_resources(doc_working, font_id)

                # Prepare for translation
                fp = io.BytesIO()
                doc_working.save(fp)

                # Perform translation using the existing translate_patch function
                obj_patch = translate_patch(
                    fp,
                    pages=chunk_pages,
                    doc_zh=doc_working,
                    noto_name=self.font_manager.noto_name,
                    noto=self.font_manager.noto,
                    progress_bar=progress_bar,
                    **translation_kwargs,
                )

                # Apply patches
                for obj_id, ops_new in obj_patch.items():
                    doc_working.update_stream(obj_id, ops_new.encode())

                # Subset fonts if requested
                if not self.skip_subset_fonts:
                    try:
                        doc_working.subset_fonts(fallback=True)
                    except Exception as e:
                        logger.error(f"Error subsetting fonts: {e}")

                # Extract translated pages
                for page_idx in chunk_pages:
                    if 0 <= page_idx < self.total_pages:
                        # Create single-page document for this translated page
                        single_page_doc = Document()
                        single_page_doc.insert_pdf(
                            doc_working, from_page=page_idx, to_page=page_idx
                        )
                        translated_pages[page_idx] = single_page_doc

                # Cleanup
                doc_working.close()
                gc.collect()

                if progress_callback:
                    progress_callback(progress_bar)

        return translated_pages

    def _replace_translated_pages(
        self,
        doc_mono: Document,
        doc_dual: Document,
        translated_pages: Dict[int, Document],
    ):
        """
        Replace pages in the output documents with translated versions.

        Args:
            doc_mono: Monolingual document to update.
            doc_dual: Document for dual-language output.
            translated_pages: Dictionary of translated pages.
        """
        for page_idx, translated_doc in translated_pages.items():
            if 0 <= page_idx < len(doc_mono):
                # Delete original page and insert translated page
                doc_mono.delete_page(page_idx)
                doc_mono.insert_pdf(
                    translated_doc, from_page=0, to_page=0, start_at=page_idx
                )

                # For dual document, keep original at the same position
                # (dual document creation will handle side-by-side layout)

    def _create_dual_document(
        self, doc_original: Document, doc_translated: Document
    ) -> bytes:
        """
        Create a dual-language document with original and translated pages side by side.

        Args:
            doc_original: Document with original pages.
            doc_translated: Document with translated pages.

        Returns:
            Bytes of the dual-language PDF.
        """
        doc_dual = Document()

        for page_idx in tqdm.tqdm(
            range(min(len(doc_original), len(doc_translated))),
            desc="Creating dual-language document",
        ):
            # Get pages
            page_original = doc_original[page_idx]
            page_translated = doc_translated[page_idx]

            # Get dimensions
            rect_original = page_original.rect
            rect_translated = page_translated.rect

            # Create new page with combined width
            new_width = rect_original.width + rect_translated.width
            new_height = max(rect_original.height, rect_translated.height)
            new_page = doc_dual.new_page(width=new_width, height=new_height)

            # Insert original page on the left
            new_page.show_pdf_page(
                pymupdf.Rect(0, 0, rect_original.width, rect_original.height),
                doc_original,
                page_idx,
            )

            # Insert translated page on the right
            new_page.show_pdf_page(
                pymupdf.Rect(rect_original.width, 0, new_width, rect_translated.height),
                doc_translated,
                page_idx,
            )

        # Final font subsetting
        if not self.skip_subset_fonts:
            try:
                doc_dual.subset_fonts(fallback=True)
            except Exception:
                pass

        result = doc_dual.write(deflate=True, garbage=3, use_objstms=1)
        doc_dual.close()
        return result

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, "doc_original"):
            self.doc_original.close()


def translate_patch(
    inf: BinaryIO,
    pages: Optional[list[int]] = None,
    vfont: str = "",
    vchar: str = "",
    thread: int = 0,
    doc_zh: Document = None,
    lang_in: str = "",
    lang_out: str = "",
    service: str = "",
    noto_name: str = "",
    noto: Font = None,
    callback: object = None,
    cancellation_event: asyncio.Event = None,
    model: OnnxModel = None,
    envs: Dict = None,
    prompt: Template = None,
    ignore_cache: bool = False,
    progress_bar: tqdm.tqdm = None,
    **kwarg: Any,
) -> Dict:
    """
    Translate pages in a PDF document and return object patches.

    Args:
        inf: Input PDF stream
        pages: List of page indices to translate
        vfont: Vertical font name
        vchar: Vertical character
        thread: Number of threads for translation
        doc_zh: PyMuPDF Document object
        lang_in: Source language
        lang_out: Target language
        service: Translation service
        noto_name: Noto font name
        noto: Noto font object
        callback: Progress callback function
        cancellation_event: Event for cancellation
        model: ONNX model for layout detection
        envs: Environment variables
        prompt: Translation prompt template
        ignore_cache: Whether to ignore cache
        progress_bar: Progress bar object
        **kwarg: Additional keyword arguments

    Returns:
        Dictionary of object patches
    """
    # Lazy import to avoid circular import
    from pdf2zh.core.converter import TranslateConverter

    rsrcmgr = PDFResourceManager()
    layout = {}
    device = TranslateConverter(
        rsrcmgr,
        vfont,
        vchar,
        thread,
        layout,
        lang_in,
        lang_out,
        service,
        noto_name,
        noto,
        envs,
        prompt,
        ignore_cache,
    )

    assert device is not None
    obj_patch = {}
    interpreter = PDFPageInterpreterEx(rsrcmgr, device, obj_patch)
    if pages:
        total_pages = len(pages)
    else:
        total_pages = doc_zh.page_count

    parser = PDFParser(inf)
    doc = PDFDocument(parser)

    should_close_pbar = False
    if progress_bar is None:
        progress_bar = tqdm.tqdm(total=total_pages)
        should_close_pbar = True

    try:
        for pageno, page in enumerate(PDFPage.create_pages(doc)):
            if cancellation_event and cancellation_event.is_set():
                raise CancelledError("task cancelled")
            if pages and (pageno not in pages):
                continue
            progress_bar.update(1)
            if callback:
                callback(progress_bar)
            page.pageno = pageno
            pix = doc_zh[page.pageno].get_pixmap()
            image = np.frombuffer(pix.samples, np.uint8).reshape(
                pix.height, pix.width, 3
            )[:, :, ::-1]
            page_layout = model.predict(image, imgsz=int(pix.height / 32) * 32)[0]
            # kdtree 是不可能 kdtree 的，不如直接渲染成图片，用空间换时间
            box = np.ones((pix.height, pix.width))
            h, w = box.shape
            vcls = [
                "abandon",
                "figure",
                "table",
                "isolate_formula",
                "formula_caption",
            ]
            for i, d in enumerate(page_layout.boxes):
                if page_layout.names[int(d.cls)] not in vcls:
                    x0, y0, x1, y1 = d.xyxy.squeeze()
                    x0, y0, x1, y1 = (
                        np.clip(int(x0 - 1), 0, w - 1),
                        np.clip(int(h - y1 - 1), 0, h - 1),
                        np.clip(int(x1 + 1), 0, w - 1),
                        np.clip(int(h - y0 + 1), 0, h - 1),
                    )
                    box[y0:y1, x0:x1] = i + 2
            for i, d in enumerate(page_layout.boxes):
                if page_layout.names[int(d.cls)] in vcls:
                    x0, y0, x1, y1 = d.xyxy.squeeze()
                    x0, y0, x1, y1 = (
                        np.clip(int(x0 - 1), 0, w - 1),
                        np.clip(int(h - y1 - 1), 0, h - 1),
                        np.clip(int(x1 + 1), 0, w - 1),
                        np.clip(int(h - y0 + 1), 0, h - 1),
                    )
                    box[y0:y1, x0:x1] = 0
            layout[page.pageno] = box
            # 新建一个 xref 存放新指令流
            page.page_xref = doc_zh.get_new_xref()  # hack 插入页面的新 xref
            doc_zh.update_object(page.page_xref, "<<>>")
            doc_zh.update_stream(page.page_xref, b"")
            doc_zh[page.pageno].set_contents(page.page_xref)
            interpreter.process_page(page)
    finally:
        if should_close_pbar:
            progress_bar.close()

    device.close()
    return obj_patch


def translate_stream(
    stream: bytes,
    pages: Optional[List[int]] = None,
    lang_in: str = "",
    lang_out: str = "",
    service: str = "",
    thread: int = 0,
    vfont: str = "",
    vchar: str = "",
    callback: object = None,
    cancellation_event=None,
    model=None,
    envs: Dict = None,
    prompt=None,
    skip_subset_fonts: bool = False,
    ignore_cache: bool = False,
    chunk_size: int = 20,  # Process this many pages at a time
    **kwarg,
) -> Tuple[bytes, bytes]:
    """
    Translate a PDF document stream while preserving all pages.

    This function preserves the entire document structure:
    - Selected pages are translated
    - Non-selected pages remain in their original form
    - Both mono and dual documents contain all pages

    Args:
        stream: PDF document as bytes
        pages: List of page indices to translate (0-based). If None, translate all pages.
        lang_in: Source language
        lang_out: Target language
        service: Translation service
        thread: Number of threads for translation
        vfont: Vertical font name
        vchar: Vertical character
        callback: Progress callback function
        cancellation_event: Event for cancellation
        model: ONNX model for layout detection
        envs: Environment variables
        prompt: Translation prompt template
        skip_subset_fonts: Whether to skip font subsetting
        ignore_cache: Whether to ignore cache
        chunk_size: Number of pages to process in each chunk
        **kwarg: Additional keyword arguments

    Returns:
        Tuple of (mono_pdf_bytes, dual_pdf_bytes) containing all pages
    """
    # Create document processor with the new modular architecture
    processor = PDFDocumentProcessor(
        stream=stream,
        lang_out=lang_out,
        chunk_size=chunk_size,
        skip_subset_fonts=skip_subset_fonts,
    )

    # Process the document using the new modular approach
    return processor.process_document(
        pages=pages,
        lang_in=lang_in,
        lang_out=lang_out,
        service=service,
        thread=thread,
        vfont=vfont,
        vchar=vchar,
        callback=callback,
        cancellation_event=cancellation_event,
        model=model,
        envs=envs,
        prompt=prompt,
        ignore_cache=ignore_cache,
        **kwarg,
    )
