from dataclasses import dataclass, replace

from app.repositories.document_chunk_repository import ChunkSearchMatch


@dataclass(frozen=True)
class ContextBuildResult:
    context: str
    included_matches: list[ChunkSearchMatch]


def build_context(
    matches: list[ChunkSearchMatch],
    *,
    max_chars: int,
) -> ContextBuildResult:
    blocks: list[str] = []
    included_matches: list[ChunkSearchMatch] = []
    used_chars = 0

    for source_number, match in enumerate(matches, start=1):
        header = (
            f"[source {source_number}]\n"
            f"document_id: {match.document_id}\n"
            f"chunk_id: {match.chunk_id}\n"
            f"document_title: {match.document_title}\n"
            "content:\n"
        )
        separator_size = 2 if blocks else 0
        remaining = max_chars - used_chars - separator_size
        if remaining <= len(header):
            break

        content = match.content[: remaining - len(header)]
        if not content:
            break

        block = f"{header}{content}"
        blocks.append(block)
        included_matches.append(replace(match, content=content))
        used_chars += separator_size + len(block)

        if len(content) < len(match.content):
            break

    return ContextBuildResult(
        context="\n\n".join(blocks),
        included_matches=included_matches,
    )
