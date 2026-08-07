import re
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class TextChunk:
    content: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any]


# A markdown ATX heading: one to six hashes, a space, then the title.
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# Below this, a section is too small to stand alone as a retrievable answer
# and is merged into the next one. A two-line section embeds to a vector that
# is mostly noise about its own brevity.
MINIMUM_SECTION_CHARS = 200


@dataclass(frozen=True)
class Section:
    """One heading and the text under it, with the headings above it."""

    heading_path: list[str]
    text: str

    @property
    def title(self) -> str:
        return " › ".join(self.heading_path)


def split_sections(text: str) -> list[Section]:
    """Split markdown on its headings, keeping each heading's ancestry.

    Returns a single unheaded section for text with no headings, which is what
    makes this safe to run over a PDF or a plain text file.
    """
    matches = list(_HEADING.finditer(text))
    if not matches:
        stripped = text.strip()
        return [Section(heading_path=[], text=stripped)] if stripped else []

    sections: list[Section] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(Section(heading_path=[], text=preamble))

    path: list[str] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        # Drop any headings at this level or deeper before adding this one, so
        # the path is the chain of ancestors rather than every heading seen.
        path = path[: level - 1] + [title]

        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if body:
            sections.append(Section(heading_path=list(path), text=body))

    return sections


def _merge_short_sections(sections: list[Section]) -> list[Section]:
    """Fold sections too small to answer anything into a neighbour.

    Backwards by preference, forwards when there is nothing behind — a short
    section at the top of a document is the common case, and leaving it alone
    would produce exactly the tiny chunk this avoids everywhere else.

    Only within the same top-level heading: merging across one would join two
    genuinely different topics, which is the problem, not the fix.
    """
    merged: list[Section] = []
    carried: Section | None = None

    for section in sections:
        if carried is not None:
            if carried.heading_path[:1] == section.heading_path[:1]:
                section = Section(
                    heading_path=section.heading_path,
                    text=f"{carried.title}\n{carried.text}\n\n{section.text}",
                )
            else:
                merged.append(carried)
            carried = None

        if len(section.text) >= MINIMUM_SECTION_CHARS:
            merged.append(section)
            continue

        if merged and section.heading_path[:1] == merged[-1].heading_path[:1]:
            previous = merged.pop()
            merged.append(
                Section(
                    heading_path=previous.heading_path,
                    text=f"{previous.text}\n\n{section.title}\n{section.text}",
                )
            )
        else:
            # Nothing behind it to join. Hold it for the next section instead.
            carried = section

    if carried is not None:
        merged.append(carried)
    return merged


def chunk_document(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    """Chunk on the document's own structure, falling back to character windows.

    A fixed character window splits wherever the count runs out, which lands
    mid-sentence and mid-topic, and at a window larger than the document it
    produces one chunk holding everything — a single embedding averaging every
    topic the document covers. Neither is a good unit to retrieve: the question
    "when do you charge for a pre-order?" wants the paragraph about pre-orders,
    not a vector standing for the whole stock policy.

    Sections that are still too long for one chunk fall back to the character
    window, so this never produces an oversized chunk.

    Each chunk is prefixed with its heading path. The prefix costs a few tokens
    and buys the chunk its context: "Charged at dispatch, not at the time of
    ordering" is ambiguous alone and unambiguous under "Stock and availability
    › Pre-orders". It is also what the reader sees quoted as a source.
    """
    base_metadata = dict(metadata or {})
    sections = _merge_short_sections(split_sections(text))
    chunks: list[TextChunk] = []

    for section in sections:
        heading = section.title
        prefix = f"{heading}\n\n" if heading else ""
        section_metadata = {
            **base_metadata,
            "heading_path": section.heading_path,
            "heading": heading or None,
        }

        # The prefix is part of what gets embedded, so the budget for the body
        # has to allow for it.
        body_budget = max(chunk_size - len(prefix), chunk_size // 2)

        if len(section.text) <= body_budget:
            content = f"{prefix}{section.text}"
            chunks.append(
                TextChunk(
                    content=content,
                    chunk_index=len(chunks),
                    token_count=max(1, (len(content) + 3) // 4),
                    metadata=section_metadata,
                )
            )
            continue

        for piece in chunk_text(
            section.text,
            chunk_size=body_budget,
            chunk_overlap=min(chunk_overlap, max(body_budget - 1, 0)),
            metadata=section_metadata,
        ):
            content = f"{prefix}{piece.content}"
            chunks.append(
                replace(
                    piece,
                    content=content,
                    chunk_index=len(chunks),
                    token_count=max(1, (len(content) + 3) // 4),
                )
            )

    return chunks


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
