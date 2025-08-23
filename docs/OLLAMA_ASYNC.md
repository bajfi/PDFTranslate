# Ollama Async Client Implementation

This document describes the implementation of async client support for Ollama in the PDF translator.

## Overview

The async implementation provides better performance when translating multiple text segments by allowing concurrent translation requests to the Ollama server, rather than processing them sequentially.

## Key Features

### 1. Backward Compatibility

- All existing synchronous code continues to work without changes
- The `OllamaTranslator` class maintains its original sync interface
- Async functionality is additive, not replacing existing functionality

### 2. Async Methods Added

#### BaseTranslator Class

- `atranslate(text, ignore_cache=False) -> str`: Async version of translate method
- `ado_translate(text) -> str`: Async version of do_translate method (override this in subclasses)

#### OllamaTranslator Class

- `ado_translate(text) -> str`: Implements async translation using `ollama.AsyncClient`
- `_get_async_client() -> ollama.AsyncClient`: Lazy initialization of async client

### 3. Smart Translation Selection

The converter automatically detects if the translator supports async and uses it when:

- The translator has `ado_translate` method
- Thread count > 1 (indicating desire for concurrent processing)

## Performance Benefits

### Async vs Sync Comparison

- **Sync**: Translations processed sequentially, one after another
- **Async**: Multiple translations can be processed concurrently
- **Speedup**: Can achieve 2-5x speedup depending on text volume and server capacity

### Concurrency Control

- Uses `asyncio.Semaphore` to limit concurrent requests
- Prevents overwhelming the Ollama server
- Respects the `thread` parameter for maximum concurrency

## Implementation Details

### 1. Lazy Client Initialization

```python
def _get_async_client(self) -> ollama.AsyncClient:
    """Lazy initialization of async client"""
    if self.async_client is None:
        self.async_client = ollama.AsyncClient(
            host=self.envs["OLLAMA_HOST"],
            timeout=60.0
        )
    return self.async_client
```

### 2. Async Translation Method

```python
async def ado_translate(self, text: str) -> str:
    """Async implementation of translation using ollama AsyncClient"""
    if (max_token := len(text) * 5) > self.options["num_predict"]:
        self.options["num_predict"] = max_token

    async_client = self._get_async_client()

    response = await async_client.chat(
        model=self.model,
        messages=self.prompt(text, self.prompt_template),
        options=self.options,
    )
    content = self._remove_cot_content(response.message.content or "")
    return content.strip()
```

### 3. Event Loop Handling

The implementation handles various event loop scenarios:

- Running in an existing async context
- No event loop present
- Event loop conflicts

## Usage Examples

### Basic Async Usage

```python
import asyncio
from pdf2zh.translator import OllamaTranslator

async def translate_multiple():
    translator = OllamaTranslator(
        lang_in="en",
        lang_out="zh",
        model="gemma2:2b"
    )

    texts = ["Hello", "World", "Async translation"]

    # Concurrent translation
    tasks = [translator.atranslate(text) for text in texts]
    results = await asyncio.gather(*tasks)

    return results

# Run the async function
results = asyncio.run(translate_multiple())
```

### Automatic Async in PDF Translation

The PDF translation process automatically uses async when available:

```python
# This will automatically use async if translator supports it
pdf2zh.translate_pdf(
    input_file="document.pdf",
    output_file="document_zh.pdf",
    service="ollama",
    thread=4  # Enables concurrent processing
)
```

## Error Handling

### Graceful Fallback

If async translation fails for any reason, the system automatically falls back to synchronous translation:

```python
try:
    # Try async translation
    news = await async_translate_all()
    log.debug("Used async translation with ollama AsyncClient")
except Exception as e:
    log.warning(f"Async translation failed, falling back to sync: {e}")
    # Fall back to synchronous translation
    with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread) as executor:
        news = list(executor.map(worker, sstk))
```

### Common Issues and Solutions

1. **Ollama Server Not Running**
   - Error: Connection refused
   - Solution: Start Ollama with `ollama serve`

2. **Model Not Available**
   - Error: Model not found
   - Solution: Install model with `ollama pull <model_name>`

3. **Event Loop Conflicts**
   - Error: RuntimeError about event loops
   - Solution: Automatic handling with thread-based fallback

## Configuration

### Environment Variables

The async client uses the same configuration as the sync client:

- `OLLAMA_HOST`: Server host (default: <http://127.0.0.1:11434>)
- `OLLAMA_MODEL`: Model name (default: gemma3)

### Performance Tuning

- Adjust `thread` parameter to control concurrency
- Monitor Ollama server capacity
- Consider model size and server resources

## Testing

Run the test script to verify async functionality:

```bash
python test_ollama_async.py
```

This will:

1. Test async translation performance
2. Compare with sync translation
3. Report performance improvements
4. Verify correctness of translations

## Future Enhancements

1. **Streaming Support**: Add support for streaming responses
2. **Connection Pooling**: Implement connection reuse for better performance
3. **Load Balancing**: Support multiple Ollama servers
4. **Metrics**: Add detailed performance metrics and monitoring
