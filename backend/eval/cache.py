"""A disk cache in front of the embedding provider.

The harness re-indexes the whole corpus on every run, and an eval you avoid
running because it costs money is an eval that stops being run. Caching by
content hash means a re-run with unchanged chunking costs nothing, and a
chunking change pays only for the chunks whose text actually moved.

Cached by text and model, not by chunk id: two chunks with identical text are
the same embedding, and changing the model must not silently reuse the old
one's vectors.
"""

import hashlib
import json
import logging
from pathlib import Path

from app.embeddings.provider import EmbeddingProvider


logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent / ".cache"


class CachingEmbeddingProvider:
    """Wraps a real provider. Only unseen text reaches the API."""

    def __init__(
        self,
        inner: EmbeddingProvider,
        model: str,
        cache_dir: Path = CACHE_DIR,
    ) -> None:
        self._inner = inner
        self._model = model
        self._path = cache_dir / f"{_safe(model)}.json"
        self._entries: dict[str, list[float]] = self._load()
        self.hits = 0
        self.misses = 0

    def _load(self) -> dict[str, list[float]]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Ignoring unreadable embedding cache at %s", self._path)
            return {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._entries), encoding="utf-8")

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self._model}\n{text}".encode()).hexdigest()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        keys = [self._key(text) for text in texts]
        missing = [
            (index, text)
            for index, (key, text) in enumerate(zip(keys, texts))
            if key not in self._entries
        ]
        self.hits += len(texts) - len(missing)
        self.misses += len(missing)

        if missing:
            fresh = self._inner.embed_texts([text for _, text in missing])
            for (index, _), vector in zip(missing, fresh):
                self._entries[keys[index]] = vector

        return [self._entries[key] for key in keys]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def _safe(model: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in model)
