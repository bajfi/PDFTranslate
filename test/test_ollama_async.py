#!/usr/bin/env python3
"""
Test script to demonstrate async ollama translation support.
"""

import asyncio
import time

from pdf2zh.translator import OllamaTranslator


async def test_async_translation():
    """Test async translation with ollama"""
    print("Testing Async Ollama Translation...")

    # Initialize translator
    translator = OllamaTranslator(
        lang_in="en",
        lang_out="zh",
        model="gemma3",  # Using a smaller model for testing
        ignore_cache=True,
    )

    # Test texts
    test_texts = [
        "Hello, world!",
        "This is a test sentence for translation.",
        "Artificial intelligence is transforming the world.",
        "Machine learning algorithms are becoming more sophisticated.",
        "The future of technology looks promising.",
    ]

    print(f"Translating {len(test_texts)} texts...")

    # Test async translation
    start_time = time.time()

    # Create async tasks
    tasks = [translator.atranslate(text) for text in test_texts]
    results = await asyncio.gather(*tasks)

    async_time = time.time() - start_time

    print(f"\nAsync Translation Results (took {async_time:.2f}s):")
    for original, translated in zip(test_texts, results):
        print(f"EN: {original}")
        print(f"ZH: {translated}")
        print("-" * 50)

    return async_time, results


def test_sync_translation():
    """Test sync translation with ollama for comparison"""
    print("\nTesting Sync Ollama Translation...")

    # Initialize translator
    translator = OllamaTranslator(
        lang_in="en",
        lang_out="zh",
        model="gemma3",  # Using a smaller model for testing
        ignore_cache=True,
    )

    # Test texts (same as async test)
    test_texts = [
        "Hello, world!",
        "This is a test sentence for translation.",
        "Artificial intelligence is transforming the world.",
        "Machine learning algorithms are becoming more sophisticated.",
        "The future of technology looks promising.",
    ]

    print(f"Translating {len(test_texts)} texts...")

    # Test sync translation
    start_time = time.time()

    results = []
    for text in test_texts:
        result = translator.translate(text)
        results.append(result)

    sync_time = time.time() - start_time

    print(f"\nSync Translation Results (took {sync_time:.2f}s):")
    for original, translated in zip(test_texts, results):
        print(f"EN: {original}")
        print(f"ZH: {translated}")
        print("-" * 50)

    return sync_time, results


async def main():
    """Main test function"""
    print("=" * 60)
    print("Ollama Async Translation Test")
    print("=" * 60)

    try:
        # Test async translation
        async_time, async_results = await test_async_translation()

        # Test sync translation for comparison
        sync_time, sync_results = test_sync_translation()

        print("\n" + "=" * 60)
        print("Performance Comparison:")
        print(f"Async Time: {async_time:.2f}s")
        print(f"Sync Time:  {sync_time:.2f}s")
        if sync_time > 0:
            speedup = sync_time / async_time if async_time > 0 else float("inf")
            print(f"Speedup:    {speedup:.2f}x")
        print("=" * 60)

    except Exception as e:
        print(f"Error during testing: {e}")
        print("Make sure Ollama is running and has the required model available.")
        print("You can start Ollama with: ollama serve")
        print("And install a model with: ollama pull gemma2:2b")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
