"""Text chunking utilities for vector store ingestion."""

from __future__ import annotations


# Minimum and maximum chunk size in characters
CHUNK_MIN_SIZE = 500
CHUNK_MAX_SIZE = 800
CHUNK_OVERLAP = 100


def chunk_text(text: str, min_size: int = CHUNK_MIN_SIZE, max_size: int = CHUNK_MAX_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks of approximately max_size characters.

    Args:
        text: Input text to chunk
        min_size: Minimum chunk size (chunks smaller than this are merged with next)
        max_size: Maximum chunk size
        overlap: Number of overlapping characters between adjacent chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= max_size:
        return [text]

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + max_size
        if end >= text_len:
            # Last chunk - take everything remaining
            chunks.append(text[start:])
            break

        # Try to break at sentence or paragraph boundary within last 100 chars
        break_point = _find_break_point(text, start, end)
        chunks.append(text[start:break_point])

        # Next start position: we go back by overlap to create the sliding window
        start = start + max_size - overlap

    # Merge any chunks smaller than min_size with the previous one
    result: list[str] = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        if not result:
            result.append(chunk)
        elif len(result[-1]) < min_size:
            result[-1] = result[-1] + " " + chunk
        else:
            result.append(chunk)

    return result


def _find_break_point(text: str, start: int, end: int) -> int:
    """Find a good sentence/paragraph break point near end."""
    search_start = max(start, end - 100)

    # Try sentence endings: 。；！
    for i in range(end - 1, search_start - 1, -1):
        if i < 0 or i >= len(text):
            continue
        ch = text[i]
        if ch in "。；！":
            return i + 1

    # Try comma/pause separators: ，
    for i in range(end - 1, search_start - 1, -1):
        if i < 0 or i >= len(text):
            continue
        if text[i] in "，、":
            return i + 1

    # Try newline break
    for i in range(end - 1, search_start - 1, -1):
        if i < 0 or i >= len(text):
            continue
        if text[i] == "\n":
            return i + 1

    # Fallback: split at max_size (end of window)
    return end