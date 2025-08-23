"""
Translation utilities for PDF processing.

This module contains the core translation functions that are shared
across different modules, helping to avoid circular imports.
"""

import asyncio
import logging
from asyncio import CancelledError
from string import Template
from typing import Any, BinaryIO, Dict, Optional

import numpy as np
import tqdm
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pymupdf import Document, Font

from pdf2zh.converter import TranslateConverter
from pdf2zh.doclayout import OnnxModel
from pdf2zh.pdfinterp import PDFPageInterpreterEx

logger = logging.getLogger(__name__)


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
            vcls = ["abandon", "figure", "table", "isolate_formula", "formula_caption"]
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
