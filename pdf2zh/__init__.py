import logging

from pdf2zh.document_processor import (
    FontManager,
    PageSelector,
    PDFDocumentProcessor,
    translate_stream,
)
from pdf2zh.high_level import translate

log = logging.getLogger(__name__)

__version__ = "1.9.11"
__author__ = "Byaidu"
__all__ = [
    "translate",
    "translate_stream",
    "PDFDocumentProcessor",
    "PageSelector",
    "FontManager",
]
