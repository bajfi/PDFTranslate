"""
Tests for the document processor functionality.

This module tests the new PDF document processing classes to ensure
they work correctly and preserve all pages while translating only selected ones.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

from pymupdf import Document

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdf2zh.document_processor import FontManager, PageSelector, PDFDocumentProcessor


class TestPageSelector(unittest.TestCase):
    """Test the PageSelector class."""

    def setUp(self):
        self.total_pages = 10
        self.selector = PageSelector(self.total_pages)

    def test_normalize_pages_all_pages(self):
        """Test that None translates all pages."""
        pages_to_translate, pages_to_preserve = self.selector.normalize_pages(None)

        expected_translate = set(range(self.total_pages))
        expected_preserve = set()

        self.assertEqual(pages_to_translate, expected_translate)
        self.assertEqual(pages_to_preserve, expected_preserve)

    def test_normalize_pages_partial_selection(self):
        """Test partial page selection."""
        selected_pages = [1, 3, 5, 7]
        pages_to_translate, pages_to_preserve = self.selector.normalize_pages(
            selected_pages
        )

        expected_translate = {1, 3, 5, 7}
        expected_preserve = {0, 2, 4, 6, 8, 9}

        self.assertEqual(pages_to_translate, expected_translate)
        self.assertEqual(pages_to_preserve, expected_preserve)

    def test_normalize_pages_out_of_range(self):
        """Test handling of out-of-range page indices."""
        selected_pages = [1, 5, 15, -1]  # 15 and -1 are out of range
        pages_to_translate, pages_to_preserve = self.selector.normalize_pages(
            selected_pages
        )

        expected_translate = {1, 5}  # Only valid pages
        expected_preserve = {0, 2, 3, 4, 6, 7, 8, 9}

        self.assertEqual(pages_to_translate, expected_translate)
        self.assertEqual(pages_to_preserve, expected_preserve)

    def test_normalize_pages_empty_selection(self):
        """Test empty page selection."""
        pages_to_translate, pages_to_preserve = self.selector.normalize_pages([])

        expected_translate = set()
        expected_preserve = set(range(self.total_pages))

        self.assertEqual(pages_to_translate, expected_translate)
        self.assertEqual(pages_to_preserve, expected_preserve)


class TestFontManager(unittest.TestCase):
    """Test the FontManager class."""

    @patch("pdf2zh.document_processor.download_remote_fonts")
    @patch("pdf2zh.document_processor.Font")
    def setUp(self, mock_font, mock_download):
        mock_download.return_value = "/fake/font/path.ttf"
        mock_font.return_value = Mock()
        self.font_manager = FontManager("zh")

    def test_font_list_initialization(self):
        """Test that font list is properly initialized."""
        self.assertIsInstance(self.font_manager.font_list, list)
        self.assertGreaterEqual(len(self.font_manager.font_list), 2)  # tiro + noto
        self.assertEqual(self.font_manager.font_list[0], ("tiro", None))

    @patch("pymupdf.Document")
    def test_install_fonts_to_document(self, mock_doc_class):
        """Test font installation to document."""
        # Create mock document with mock pages
        mock_doc = Mock()
        mock_page1 = Mock()
        mock_page2 = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([mock_page1, mock_page2]))

        # Configure insert_font to return different IDs for different fonts
        def insert_font_side_effect(name, path):
            if name == "tiro":
                return 1
            elif name == "noto":
                return 2
            return 0

        mock_page1.insert_font.side_effect = insert_font_side_effect
        mock_page2.insert_font.side_effect = insert_font_side_effect

        # Test font installation
        font_id = self.font_manager.install_fonts_to_document(mock_doc)

        # Verify fonts were installed
        self.assertIn("tiro", font_id)
        self.assertIn("noto", font_id)
        self.assertEqual(
            mock_page1.insert_font.call_count, len(self.font_manager.font_list)
        )
        self.assertEqual(
            mock_page2.insert_font.call_count, len(self.font_manager.font_list)
        )


class TestPDFDocumentProcessor(unittest.TestCase):
    """Test the PDFDocumentProcessor class."""

    def setUp(self):
        # Create a minimal PDF document for testing
        self.test_pdf_bytes = self._create_test_pdf()

    def _create_test_pdf(self) -> bytes:
        """Create a simple test PDF with multiple pages."""
        doc = Document()

        # Add 5 test pages
        for i in range(5):
            page = doc.new_page()
            page.insert_text((50, 50), f"Test Page {i + 1}", fontsize=12)

        pdf_bytes = doc.write()
        doc.close()
        return pdf_bytes

    @patch("pdf2zh.document_processor.download_remote_fonts")
    @patch("pdf2zh.document_processor.Font")
    def test_processor_initialization(self, mock_font, mock_download):
        """Test processor initialization."""
        mock_download.return_value = "/fake/font/path.ttf"
        mock_font.return_value = Mock()

        processor = PDFDocumentProcessor(
            stream=self.test_pdf_bytes, lang_out="zh", chunk_size=2
        )

        self.assertEqual(processor.total_pages, 5)
        self.assertEqual(processor.chunk_size, 2)
        self.assertIsInstance(processor.page_selector, PageSelector)
        self.assertIsInstance(processor.font_manager, FontManager)

    @patch("pdf2zh.document_processor.download_remote_fonts")
    @patch("pdf2zh.document_processor.Font")
    @patch("pdf2zh.document_processor.translate_patch")
    def test_process_document_all_pages(
        self, mock_translate_patch, mock_font, mock_download
    ):
        """Test processing all pages."""
        mock_download.return_value = "/fake/font/path.ttf"
        mock_font.return_value = Mock()
        mock_translate_patch.return_value = {}

        processor = PDFDocumentProcessor(
            stream=self.test_pdf_bytes, lang_out="zh", chunk_size=2
        )

        # Mock the translation process
        mono_bytes, dual_bytes = processor.process_document(
            pages=None,  # Translate all pages
            lang_in="en",
            lang_out="zh",
            service="google",
            thread=1,
        )

        # Verify output
        self.assertIsInstance(mono_bytes, bytes)
        self.assertIsInstance(dual_bytes, bytes)

        # Verify documents can be opened
        mono_doc = Document(stream=mono_bytes)
        dual_doc = Document(stream=dual_bytes)

        self.assertEqual(mono_doc.page_count, 5)  # All pages preserved
        self.assertEqual(dual_doc.page_count, 5)  # All pages in dual format

        mono_doc.close()
        dual_doc.close()

    @patch("pdf2zh.document_processor.download_remote_fonts")
    @patch("pdf2zh.document_processor.Font")
    @patch("pdf2zh.document_processor.translate_patch")
    def test_process_document_partial_pages(
        self, mock_translate_patch, mock_font, mock_download
    ):
        """Test processing only selected pages."""
        mock_download.return_value = "/fake/font/path.ttf"
        mock_font.return_value = Mock()
        mock_translate_patch.return_value = {}

        processor = PDFDocumentProcessor(
            stream=self.test_pdf_bytes, lang_out="zh", chunk_size=2
        )

        # Translate only pages 1 and 3 (0-based indexing)
        mono_bytes, dual_bytes = processor.process_document(
            pages=[1, 3], lang_in="en", lang_out="zh", service="google", thread=1
        )

        # Verify output
        self.assertIsInstance(mono_bytes, bytes)
        self.assertIsInstance(dual_bytes, bytes)

        # Verify documents can be opened and have all pages
        mono_doc = Document(stream=mono_bytes)
        dual_doc = Document(stream=dual_bytes)

        self.assertEqual(mono_doc.page_count, 5)  # All pages preserved
        self.assertEqual(dual_doc.page_count, 5)  # All pages in dual format

        mono_doc.close()
        dual_doc.close()


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        # Create a test PDF
        self.test_pdf_bytes = self._create_test_pdf()

    def _create_test_pdf(self) -> bytes:
        """Create a test PDF with text content."""
        doc = Document()

        # Add pages with different content
        contents = [
            "This is page 1 with English text.",
            "Page 2 contains more English content.",
            "The third page has additional text.",
            "Page 4 with different content.",
            "Final page 5 with concluding text.",
        ]

        for i, content in enumerate(contents):
            page = doc.new_page()
            page.insert_text((50, 50), content, fontsize=12)

        pdf_bytes = doc.write()
        doc.close()
        return pdf_bytes

    @patch("pdf2zh.high_level.download_remote_fonts")
    @patch("pdf2zh.high_level.Font")
    @patch("pdf2zh.high_level.translate_patch")
    def test_translate_stream_preserves_all_pages(
        self, mock_translate_patch, mock_font, mock_download
    ):
        """Test that the new translate_stream preserves all pages."""
        from pdf2zh.high_level import translate_stream

        mock_download.return_value = "/fake/font/path.ttf"
        mock_font.return_value = Mock()
        mock_translate_patch.return_value = {}

        # Translate only pages 1 and 3
        mono_bytes, dual_bytes = translate_stream(
            stream=self.test_pdf_bytes,
            pages=[1, 3],
            lang_in="en",
            lang_out="zh",
            service="google",
            thread=1,
            model=Mock(),
            envs={},
            chunk_size=2,
        )

        # Verify both outputs have all 5 pages
        mono_doc = Document(stream=mono_bytes)
        dual_doc = Document(stream=dual_bytes)

        self.assertEqual(
            mono_doc.page_count, 5, "Mono document should have all 5 pages"
        )
        self.assertEqual(
            dual_doc.page_count, 5, "Dual document should have all 5 pages"
        )

        mono_doc.close()
        dual_doc.close()


if __name__ == "__main__":
    unittest.main()
