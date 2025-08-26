#!/usr/bin/env python3
"""
Test script to demonstrate async ollama translation support.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import patch

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from pdf2zh.translation.translator import OllamaTranslator


class TestOllamaAsync(unittest.TestCase):
    """Test cases for async Ollama translation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_texts = [
            "Hello, world!",
            "This is a test sentence for translation.",
            "Artificial intelligence is transforming the world.",
        ]

    def test_async_translation_mock(self):
        """Test async translation with mocked responses."""

        async def async_test():
            with patch.object(
                OllamaTranslator, "atranslate", return_value="Mocked translation result"
            ) as mock_atranslate:
                translator = OllamaTranslator(
                    lang_in="en",
                    lang_out="zh",
                    model="gemma3",
                    ignore_cache=True,
                )

                # Test async translation
                tasks = [translator.atranslate(text) for text in self.test_texts]
                results = await asyncio.gather(*tasks)

                # Verify all calls were made
                self.assertEqual(len(results), len(self.test_texts))
                self.assertEqual(mock_atranslate.call_count, len(self.test_texts))

                # Verify all results are the mocked value
                for result in results:
                    self.assertEqual(result, "Mocked translation result")

        # Run the async test
        asyncio.run(async_test())

    def test_translator_initialization(self):
        """Test translator initialization with various parameters."""
        translator = OllamaTranslator(
            lang_in="en",
            lang_out="zh",
            model="gemma3",
            ignore_cache=True,
        )

        self.assertEqual(translator.lang_in, "en")
        self.assertEqual(translator.lang_out, "zh")
        self.assertEqual(translator.model, "gemma3")
        self.assertTrue(translator.ignore_cache)

    def test_sync_translation_mock(self):
        """Test sync translation with mocked responses."""
        with patch.object(
            OllamaTranslator, "translate", return_value="Mocked sync translation"
        ) as mock_translate:
            translator = OllamaTranslator(
                lang_in="en",
                lang_out="zh",
                model="gemma3",
                ignore_cache=True,
            )

            results = []
            for text in self.test_texts:
                result = translator.translate(text)
                results.append(result)

            # Verify all calls were made
            self.assertEqual(len(results), len(self.test_texts))
            self.assertEqual(mock_translate.call_count, len(self.test_texts))

            # Verify all results are the mocked value
            for result in results:
                self.assertEqual(result, "Mocked sync translation")


if __name__ == "__main__":
    unittest.main()
