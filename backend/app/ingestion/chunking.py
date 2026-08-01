from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextChunk:
    content: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any]


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    text_length = len(text)
    base_metadata = dict(metadata or {})

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            split_at = _find_readable_boundary(text, start, end, chunk_size)
            if split_at is not None:
                end = split_at

        raw_content = text[start:end]
        leading_space = len(raw_content) - len(raw_content.lstrip())
        content = raw_content.strip()
        content_start = start + leading_space
        content_end = content_start + len(content)

        if content:
            chunk_metadata = {
                **base_metadata,
                "char_start": content_start,
                "char_end": content_end,
            }
            chunks.append(
                TextChunk(
                    content=content,
                    chunk_index=len(chunks),
                    token_count=max(1, (len(content) + 3) // 4),
                    metadata=chunk_metadata,
                )
            )

        if end >= text_length:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def _find_readable_boundary(
    text: str,
    start: int,
    end: int,
    chunk_size: int,
) -> int | None:
    minimum_boundary = start + (chunk_size // 2)
    for separator in ("\n\n", "\n", ". ", " "):
        boundary = text.rfind(separator, minimum_boundary, end)
        if boundary != -1:
            return boundary + len(separator)
    return None
