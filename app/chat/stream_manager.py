import re
from collections.abc import AsyncGenerator

from app.chat.streaming_buffer import StreamingBuffer


def _clean_thinking_block(text: str, *, strip: bool = True) -> str:
    """Modelin <thinking> bloklarını temizler."""
    if not text:
        return ""
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    return cleaned.strip() if strip else cleaned


async def thinking_filter_async(
    source: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """
    Streaming yanıttan <thinking> bloklarını filtreler.

    Args:
        source: Kaynak stream

    Yields:
        str: Filtrelenmiş içerik parçaları
    """
    open_tag = "<thinking>"
    close_tag = "</thinking>"
    buffer_obj = StreamingBuffer(max_chunks=100)  # Small buffer for filter
    thinking_mode = False

    try:
        async for chunk in source:
            if not chunk:
                continue

            buffer_obj.append(chunk)
            buffer_str = "".join(buffer_obj.chunks)  # Get current content without finalizing

            while True:
                if thinking_mode:
                    end_idx = buffer_str.find(close_tag)
                    if end_idx == -1:
                        break
                    buffer_str = buffer_str[end_idx + len(close_tag) :]
                    buffer_obj.clear()
                    buffer_obj.append(buffer_str)
                    thinking_mode = False
                    continue

                start_idx = buffer_str.find(open_tag)
                if start_idx == -1:
                    if buffer_str:
                        cleaned = _clean_thinking_block(buffer_str, strip=False)
                        if cleaned:
                            yield cleaned
                    buffer_obj.clear()
                    break

                if start_idx > 0:
                    segment = buffer_str[:start_idx]
                    cleaned = _clean_thinking_block(segment, strip=False)
                    if cleaned:
                        yield cleaned

                buffer_str = buffer_str[start_idx + len(open_tag) :]
                buffer_obj.clear()
                buffer_obj.append(buffer_str)
                thinking_mode = True

        # Final cleanup
        buffer_str = "".join(buffer_obj.chunks)
        if buffer_str and not thinking_mode:
            cleaned = _clean_thinking_block(buffer_str, strip=False)
            if cleaned:
                yield cleaned

    finally:
        buffer_obj.clear()  # Cleanup
